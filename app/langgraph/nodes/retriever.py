"""Hybrid evidence retrieval inside the original LangGraph retriever node."""

import os
import re
from functools import lru_cache

from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore

from app.langgraph.graph import AgentState

load_dotenv()

PROJECT_ALIASES = {
    "syncbeat": "SyncBeat",
    "expensely": "Expensely",
    "job tracker": "Job Tracker",
    "talky space": "Talky Space",
    "gatekeeper": "Gatekeeper",
    "portfolio rag": "Portfolio RAG Agent",
    "neural networks": "Neural Networks",
}
STOPWORDS = {"what", "where", "when", "how", "much", "many", "about", "have", "your", "you", "the", "and", "for", "with", "did", "are", "work", "project", "experience"}


@lru_cache(maxsize=2)
def vectorstore(index_name: str, dimension: int, namespace: str) -> PineconeVectorStore:
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small", dimensions=dimension)
    return PineconeVectorStore(
        index_name=index_name,
        embedding=embeddings,
        namespace=namespace or None,
    )


def _search(store: PineconeVectorStore, query: str, *, k: int, filter: dict | None = None):
    return store.similarity_search_with_score(query=query, k=k, filter=filter)


def _rerank(question: str, results: list[tuple]) -> list[tuple]:
    words = {word for word in re.findall(r"[a-z0-9]+", question.lower()) if len(word) > 2 and word not in STOPWORDS}
    ranked = []
    seen = set()
    for document, dense_score in results:
        key = (document.metadata.get("record_id"), document.page_content)
        if key in seen:
            continue
        seen.add(key)
        text = (document.metadata.get("name", "") + " " + document.page_content).lower()
        overlap = sum(word in text for word in words)
        name = document.metadata.get("name", "").lower()
        name_boost = 0.5 if name and name in question.lower() else 0
        core_boost = 0.15 if document.metadata.get("record_type") == "core" else 0
        ranked.append((document, float(dense_score), float(dense_score) + 0.08 * overlap + name_boost + core_boost))
    ranked.sort(key=lambda item: item[2], reverse=True)
    return [(document, score) for document, score, _ in ranked[:7]]


def retrieve_node(state: AgentState):
    question = state["question"]
    query = state.get("retrieval_query") or question
    store = vectorstore(
        os.environ["PINECONE_INDEX_NAME"],
        int(os.environ["PINECONE_DIMENSIONS"]),
        os.getenv("PINECONE_NAMESPACE", ""),
    )
    results = _search(store, query, k=12)

    if state.get("classification") == "resume":
        # Basic identity, roles, education and experience must remain available
        # even if a broad embedding search favors long project readmes.
        results.extend(_search(store, query, k=5, filter={"record_type": "core"}))
    else:
        normalized = question.lower()
        for alias, name in PROJECT_ALIASES.items():
            if alias in normalized:
                results.extend(_search(store, query, k=5, filter={"name": {"$eq": name}}))
                break

    ranked = _rerank(query, results)
    return {
        "documents": [document for document, _ in ranked],
        "confidence": max((score for _, score in ranked), default=0.0),
        "retrieval_scores": [score for _, score in ranked],
        "retrieval_metadata": [document.metadata for document, _ in ranked],
    }
