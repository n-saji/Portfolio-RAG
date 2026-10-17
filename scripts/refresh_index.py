"""Build and verify a versioned Pinecone namespace, then optionally activate it."""

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import boto3
import tiktoken
from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone

ROOT = Path(__file__).resolve().parents[1]
EMBEDDING_MODEL = "text-embedding-3-small"
MAX_TOKENS = 380
OVERLAP = 45


def split_record(record: dict, encoder) -> list[dict]:
    """Keep Markdown headings with their text, then split oversized sections."""
    text = record["text"].strip()
    lines = text.splitlines()
    sections: list[tuple[str, str]] = []
    heading = record["name"]
    body: list[str] = []
    for line in lines:
        if line.startswith("#") and line.lstrip("#").startswith(" "):
            if body:
                sections.append((heading, "\n".join(body).strip()))
            heading = line.lstrip("# ").strip() or record["name"]
            body = []
        else:
            body.append(line)
    if body:
        sections.append((heading, "\n".join(body).strip()))
    if not sections:
        sections = [(record["name"], text)]

    chunks = []
    for heading, body_text in sections:
        tokens = encoder.encode(body_text)
        if not tokens:
            continue
        step = MAX_TOKENS - OVERLAP
        for start in range(0, len(tokens), step):
            part = encoder.decode(tokens[start:start + MAX_TOKENS]).strip()
            if not part:
                continue
            content = f"{record['name']} / {heading}\n{part}"
            chunk_id = hashlib.sha256(f"{record['id']}:{heading}:{start}:{part}".encode()).hexdigest()[:40]
            metadata = {
                "text": content, "record_id": record["id"], "type": record["type"],
                "section": record.get("section", ""), "name": record["name"],
                "source_url": record.get("source_url", ""),
                "source_date": record.get("source_date", ""),
                "verified_at": record.get("verified_at", ""),
                "record_type": record.get("record_type", "source"),
            }
            if record.get("repo"):
                metadata["repo"] = record["repo"]
            chunks.append({"id": chunk_id, "text": content, "metadata": metadata})
            if start + MAX_TOKENS >= len(tokens):
                break
    return chunks


def load_chunks(path: Path) -> tuple[list[dict], str]:
    snapshot = json.loads(path.read_text())
    records = snapshot["records"]
    if len(records) < 50 or not any(r["id"] == "profile-current-roles" for r in records):
        raise ValueError("Source snapshot lacks required career or project coverage")
    encoder = tiktoken.get_encoding("cl100k_base")
    chunks = [chunk for record in records for chunk in split_record(record, encoder)]
    ids = [chunk["id"] for chunk in chunks]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate chunk IDs")
    if not any("ACTFORE" in chunk["text"] for chunk in chunks):
        raise ValueError("Latest employer is absent from the index")
    if not any("SyncBeat" in chunk["text"] for chunk in chunks):
        raise ValueError("Latest project is absent from the index")
    content_hash = hashlib.sha256(
        json.dumps([(r["id"], r["text"]) for r in records], sort_keys=True).encode()
    ).hexdigest()[:16]
    return chunks, f"portfolio-v2-{content_hash}"


def lambda_client():
    session = boto3.Session(
        profile_name=os.getenv("AWS_PROFILE") or None,
        region_name=os.getenv("AWS_REGION", "us-east-2"),
    )
    return session.client("lambda")


def hydrate_index_settings(client, function_name: str) -> dict:
    config = client.get_function_configuration(FunctionName=function_name)
    variables = config.get("Environment", {}).get("Variables", {})
    for name in ("OPENAI_API_KEY", "PINECONE_API_KEY", "PINECONE_INDEX_NAME", "PINECONE_DIMENSIONS"):
        if not os.getenv(name) and variables.get(name):
            os.environ[name] = variables[name]
    return config


def activate(client, function_name: str, config: dict, namespace: str) -> None:
    variables = dict(config.get("Environment", {}).get("Variables", {}))
    if variables.get("PINECONE_NAMESPACE") == namespace:
        return
    variables["PINECONE_NAMESPACE"] = namespace
    client.update_function_configuration(
        FunctionName=function_name,
        Environment={"Variables": variables},
        RevisionId=config["RevisionId"],
    )
    client.get_waiter("function_updated").wait(FunctionName=function_name)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", type=Path, default=ROOT / "data/generated/records.json")
    parser.add_argument("--activate", action="store_true")
    parser.add_argument("--function-name", default="rag-portfolio")
    args = parser.parse_args()
    load_dotenv()
    chunks, namespace = load_chunks(args.records)
    client = lambda_client() if args.activate or not os.getenv("PINECONE_API_KEY") else None
    config = hydrate_index_settings(client, args.function_name) if client else None
    pinecone = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    index = pinecone.Index(os.environ["PINECONE_INDEX_NAME"])
    dimension = int(os.environ["PINECONE_DIMENSIONS"])
    if pinecone.describe_index(os.environ["PINECONE_INDEX_NAME"]).dimension != dimension:
        raise ValueError("Configured embedding dimension does not match Pinecone index")

    active = (config or {}).get("Environment", {}).get("Variables", {}).get("PINECONE_NAMESPACE", "")
    counts = index.describe_index_stats().namespaces
    existing = counts.get(namespace)
    if existing and existing.vector_count == len(chunks):
        print(f"Namespace already has {len(chunks)} vectors: {namespace}")
    else:
        if namespace == active:
            raise ValueError("Active namespace is incomplete; refusing to replace live vectors")
        if existing:
            index.delete(delete_all=True, namespace=namespace)
        openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"], timeout=30.0, max_retries=2)
        for offset in range(0, len(chunks), 64):
            batch = chunks[offset:offset + 64]
            result = openai_client.embeddings.create(
                model=EMBEDDING_MODEL,
                dimensions=dimension,
                input=[chunk["text"] for chunk in batch],
            )
            vectors = [
                {"id": chunk["id"], "values": embedding.embedding, "metadata": chunk["metadata"]}
                for chunk, embedding in zip(batch, result.data, strict=True)
            ]
            index.upsert(vectors=vectors, namespace=namespace)
        for _ in range(20):
            count = index.describe_index_stats().namespaces.get(namespace)
            if count and count.vector_count == len(chunks):
                break
            time.sleep(3)
        else:
            raise RuntimeError("Pinecone vector count did not match the source snapshot")
    sampled = index.fetch(ids=[chunk["id"] for chunk in chunks[:3]], namespace=namespace)
    if len(sampled.vectors) != 3:
        raise RuntimeError("Pinecone readback failed")
    if args.activate:
        os.environ["PINECONE_NAMESPACE"] = namespace
        sys.path.insert(0, str(ROOT))
        from scripts.evaluate_retrieval import main as evaluate_retrieval

        evaluate_retrieval()
        if client is None:
            client = lambda_client()
            config = client.get_function_configuration(FunctionName=args.function_name)
        activate(client, args.function_name, config, namespace)
    print(json.dumps({"namespace": namespace, "vectors": len(chunks), "activated": args.activate}))


if __name__ == "__main__":
    main()
