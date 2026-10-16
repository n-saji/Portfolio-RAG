import logging
import os

from fastapi import APIRouter, HTTPException, Request

from app.api.schemas import ChatRequest
from app.services.chat_service import answer
from app.services.memory_service import get_turns, save_exchange

router = APIRouter()
logger = logging.getLogger(__name__)


def _handle(payload: ChatRequest, session_id: str | None) -> dict:
    history = [turn.model_dump() for turn in payload.history] or get_turns(session_id)
    try:
        result = answer(payload.question, history)
    except Exception:
        logger.exception("chat request failed")
        raise HTTPException(status_code=503, detail="Portfolio chat is temporarily unavailable")
    save_exchange(session_id, payload.question, result["answer"])
    return result


@router.post("/chat")
def chat(payload: ChatRequest):
    result = _handle(payload, payload.session_id)
    return {"answer": result["answer"], "sources": result.get("sources", [])}


@router.post("/advanced-chat")
def advanced_chat(request: Request, payload: ChatRequest):
    session_id = getattr(request.state, "session_id", None) or payload.session_id
    result = _handle(payload, session_id)
    documents = result["documents"]
    kind = documents[0]["kind"] if documents else "unknown"
    classification = "project" if kind in {"project", "repository"} else "resume" if kind in {"career", "profile", "resume"} else "unknown"
    response = {
        "answer": result["answer"],
        "classification": classification,
        "debug_docs_retrieved": len(documents),
        "sources": result.get("sources", []),
    }
    if os.getenv("DEBUG_RAG", "false").lower() in {"1", "true", "yes"}:
        response["debug_retrieval"] = {
            "metadata": [{key: doc[key] for key in ("id", "kind", "entity", "url")} for doc in documents],
            "timings_ms": result["timings"],
        }
    return response
