"""Stage, verify, then activate a versioned Pinecone namespace."""

import argparse
import json
import os
import time
from datetime import datetime, timezone

from app.knowledge import APPROVED, load_chunks
from app.services.providers import openai_client, pinecone_index


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--namespace", default=datetime.now(timezone.utc).strftime("portfolio-%Y%m%d-%H%M%S"))
    parser.add_argument("--activate", action="store_true", help="switch active namespace after verification")
    args = parser.parse_args()
    chunks = load_chunks()
    if not chunks:
        raise SystemExit("No approved chunks")
    index = pinecone_index()
    for start in range(0, len(chunks), 50):
        batch = chunks[start:start + 50]
        embeddings = openai_client().embeddings.create(
            model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
            dimensions=int(os.getenv("PINECONE_DIMENSIONS", "1024")),
            input=[item["text"] for item in batch],
        ).data
        vectors = [
            {"id": doc["id"], "values": embedding.embedding, "metadata": {"entity": doc["entity"], "kind": doc["kind"], "url": doc["url"]}}
            for doc, embedding in zip(batch, embeddings)
        ]
        result = index.upsert(vectors=vectors, namespace=args.namespace)
        if result.upserted_count != len(vectors):
            raise SystemExit(f"Only {result.upserted_count}/{len(vectors)} vectors staged; active namespace unchanged")
    # Query known first chunk rather than relying on eventually consistent counts.
    probe = openai_client().embeddings.create(
        model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
        dimensions=int(os.getenv("PINECONE_DIMENSIONS", "1024")),
        input=chunks[0]["text"],
    ).data[0].embedding
    for attempt in range(6):
        results = index.query(vector=probe, top_k=3, namespace=args.namespace)
        if chunks[0]["id"] in {match.id for match in results.matches}:
            break
        if attempt < 5:
            time.sleep(2)
    else:
        raise SystemExit("Staged namespace verification failed; active namespace unchanged")
    pointer = APPROVED / "index.json"
    old = json.loads(pointer.read_text()) if pointer.exists() else {}
    print(f"Verified {len(chunks)} chunks in {args.namespace}")
    if args.activate:
        pointer.write_text(json.dumps({"active_namespace": args.namespace, "previous_namespace": old.get("active_namespace"), "activated_at": datetime.now(timezone.utc).isoformat()}, indent=2) + "\n")
        print("Active namespace updated; commit data/approved/index.json for deployment")


if __name__ == "__main__":
    main()
