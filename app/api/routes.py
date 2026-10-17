import os
import logging

from fastapi import APIRouter, HTTPException, Request
from starlette.concurrency import run_in_threadpool

from app.api.schemas import ChatRequest
from app.langgraph.edges import build_graph
from app.services.memory_service import clear_session_history, get_chat_messages, save_exchange

router = APIRouter()
logger = logging.getLogger(__name__)


def _is_truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}

@router.post("/chat")
async def chat(request: Request, payload: ChatRequest):
    return await advanced_chat(request, payload)

@router.post("/advanced-chat")
async def advanced_chat(request: Request, payload: ChatRequest):
    session_id = request.state.session_id
    agent_app = build_graph()
    inputs = {"question": payload.question.strip(), "session_id": session_id}
    try:
        result = await run_in_threadpool(agent_app.invoke, inputs)
    except Exception:
        logger.exception("Portfolio agent request failed")
        raise HTTPException(status_code=503, detail="Portfolio agent temporarily unavailable") from None

    save_exchange(session_id=session_id, human_query=payload.question.strip(), ai_response=result["answer"])

    response = {
        "answer": result["answer"],
        "classification": result.get("classification"),
        "debug_docs_retrieved": len(result.get("documents", [])),
    }

    if _is_truthy(os.getenv("DEBUG_RAG")):
        response["debug_retrieval"] = {
            "scores": result.get("retrieval_scores", []),
            "metadata": result.get("retrieval_metadata", []),
        }

    return response


@router.get("/history")
async def history(request: Request):
    """Return this browser's recent questions and answers for chat restoration."""
    return {"messages": get_chat_messages(request.state.session_id)}


@router.delete("/history")
async def delete_history(request: Request):
    clear_session_history(request.state.session_id)
    return {"messages": []}
