"""Exact entity lookup, local BM25, and optional Pinecone dense search."""

import json
import logging
import math
import os
import re
import time
from collections import Counter
from functools import lru_cache

from app.knowledge import APPROVED, load_chunks, load_sources
from app.services.providers import openai_client, pinecone_index

logger = logging.getLogger(__name__)
STOP = {"a", "an", "and", "are", "as", "at", "about", "be", "can", "did", "do", "for", "from", "how", "i", "in", "is", "it", "me", "my", "of", "on", "or", "the", "their", "they", "to", "was", "were", "what", "when", "where", "which", "who", "with", "you", "your"}


def tokenize(text: str) -> list[str]:
    return [word for word in re.findall(r"[a-z0-9+#.]+", text.lower()) if word not in STOP and len(word) > 1]


@lru_cache(maxsize=1)
def corpus():
    chunks = load_chunks()
    terms = [Counter(tokenize(f"{c['title']} {c['text']}")) for c in chunks]
    frequency = Counter(word for row in terms for word in row)
    average = sum(sum(row.values()) for row in terms) / max(len(terms), 1)
    return chunks, terms, frequency, average


def lexical(query: str, limit: int = 6) -> list[dict]:
    chunks, terms, frequency, average = corpus()
    query_terms = set(tokenize(query))
    n = len(chunks)
    matches = []
    for doc, row in zip(chunks, terms):
        length = sum(row.values())
        score = 0.0
        for word in query_terms:
            tf = row[word]
            if not tf:
                continue
            idf = math.log(1 + (n - frequency[word] + 0.5) / (frequency[word] + 0.5))
            score += idf * (tf * 2.2) / (tf + 1.2 * (0.25 + 0.75 * length / max(average, 1)))
        if score > 0:
            matches.append((score, doc))
    return [doc for _, doc in sorted(matches, key=lambda item: item[0], reverse=True)[:limit]]


@lru_cache(maxsize=1)
def aliases() -> list[tuple[str, str]]:
    facts, sources = load_sources()
    result = []
    for item in facts["career"] + facts["profile"] + facts["featured_projects"]:
        for alias in [item["title"], *item.get("aliases", [])]:
            result.append((alias.lower(), item["id"]))
    for repo in sources["repositories"]:
        result.append((repo["name"].lower().replace("-", " "), repo["project_id"]))
    return sorted(set(result), key=lambda pair: len(pair[0]), reverse=True)


def exact(query: str) -> list[dict]:
    normalized = re.sub(r"[-_]+", " ", query.lower())
    entities = []
    for alias, entity in aliases():
        if re.search(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", normalized):
            entities.append(entity)
    if not entities and re.search(r"\b(?:your|my)\s+(?:job|role)\b|\bwhere (?:do|are) you work\b|\bwhat do you do for work\b", normalized):
        entities.append("holiday-channel-current")
    if re.search(r"\b(?:master'?s?|graduat(?:e|ed|ion)|degree|education|university|college|studied|study)\b", normalized):
        entities.append("education")
    if not entities:
        return []
    chunks, terms, _, _ = corpus()
    output = []
    seen = set()
    for entity in entities:
        for doc in chunks:
            if doc["entity"] == entity and doc["id"] not in seen:
                output.append(doc)
                seen.add(doc["id"])
    rows = {doc["id"]: row for doc, row in zip(chunks, terms)}
    query_words = set(tokenize(query))
    def priority(doc: dict) -> float:
        row = rows[doc["id"]]
        overlap = sum(min(row[word], 3) for word in query_words)
        reviewed_card = 2 if doc["kind"] in {"career", "project"} else 0
        return overlap / math.sqrt(max(sum(row.values()), 1)) + reviewed_card
    return sorted(output, key=priority, reverse=True)[:6]


def dense(query: str, timings: dict[str, float], limit: int = 6) -> list[dict]:
    if not os.getenv("OPENAI_API_KEY") or not os.getenv("PINECONE_API_KEY") or not os.getenv("PINECONE_INDEX_NAME"):
        return []
    started = time.perf_counter()
    try:
        embedding = openai_client().embeddings.create(
            model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
            dimensions=int(os.getenv("PINECONE_DIMENSIONS", "1024")),
            input=query,
        ).data[0].embedding
        timings["embedding_ms"] = round((time.perf_counter() - started) * 1000, 1)
        started = time.perf_counter()
        pointer = APPROVED / "index.json"
        namespace = json.loads(pointer.read_text())["active_namespace"] if pointer.exists() else os.getenv("PINECONE_NAMESPACE", "")
        result = pinecone_index().query(vector=embedding, top_k=limit, include_metadata=True, namespace=namespace)
        timings["pinecone_ms"] = round((time.perf_counter() - started) * 1000, 1)
        by_id = {doc["id"]: doc for doc in corpus()[0]}
        return [by_id[match.id] for match in result.matches if match.id in by_id]
    except Exception:
        logger.warning("dense retrieval failed; using local lexical results", exc_info=True)
        timings["dense_error"] = 1
        return []


def retrieve(question: str, history: list[dict[str, str]] | None = None) -> tuple[list[dict], dict[str, float]]:
    timings: dict[str, float] = {}
    started = time.perf_counter()
    previous = next((turn["content"] for turn in reversed(history or []) if turn["role"] == "user"), "")
    follow_up = bool(re.search(r"\b(it|that|those|there|this project|that role|and what|how about)\b", question.lower()))
    query = f"{previous} {question}" if follow_up and previous else question
    direct = exact(query)
    if direct:
        timings["local_retrieval_ms"] = round((time.perf_counter() - started) * 1000, 1)
        return direct[:5], timings
    local = lexical(query)
    timings["local_retrieval_ms"] = round((time.perf_counter() - started) * 1000, 1)
    remote = dense(query, timings)
    ranks = {}
    for group, weight in [(local, 1), (remote, 1)]:
        for rank, doc in enumerate(group):
            ranks[doc["id"]] = ranks.get(doc["id"], 0) + weight / (rank + 1)
    by_id = {doc["id"]: doc for doc in corpus()[0]}
    chosen = [by_id[key] for key, _ in sorted(ranks.items(), key=lambda item: item[1], reverse=True)[:5]]
    return chosen, timings
