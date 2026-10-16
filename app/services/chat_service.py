"""Public chat entry point, backed by the LangGraph workflow."""

import logging
import time

from app.langgraph.graph import build_graph

logger = logging.getLogger(__name__)


def answer(question: str, history: list[dict[str, str]] | None = None) -> dict:
    started = time.perf_counter()
    state = build_graph().invoke({"question": question, "history": history or []})
    documents = state.get("documents", [])
    timings = {**state.get("timings", {}), "total_ms": round((time.perf_counter() - started) * 1000, 1)}
    logger.info("rag_timing path=%s %s", state.get("path"), timings)
    sources_by_url = {}
    for doc in documents:
        sources_by_url.setdefault(doc["url"], {"title": doc["title"], "url": doc["url"]})
    sources = list(sources_by_url.values())
    return {"answer": state["answer"], "documents": documents, "sources": sources, "timings": timings}
