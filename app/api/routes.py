from fastapi import APIRouter, Request

from app.api.schemas import ChatRequest
from app.langgraph.edges import build_graph
from app.services.memory_service import save_exchange
from app.services.rag_service import build_portfolio_rag_chain

router = APIRouter()

@router.post("/chat")
async def chat(request: ChatRequest):
    chain = build_portfolio_rag_chain()
    response = chain.invoke({"input": request.question})
    return {"answer": response["answer"]}

@router.post("/advanced-chat")
async def advanced_chat(request: Request, payload: ChatRequest):
    if not payload.question:
        return {"answer": "Please provide a valid question."}
    session_id = getattr(request.state, "session_id", None) or payload.session_id
    agent_app = build_graph()
    inputs = {"question": payload.question, "session_id": session_id}
    result = agent_app.invoke(inputs)

    save_exchange(session_id=session_id, human_query=payload.question, ai_response=result["answer"])

    return {"answer": result["answer"], "classification": result.get("classification"),
        "debug_docs_retrieved": len(result.get("documents", []))}