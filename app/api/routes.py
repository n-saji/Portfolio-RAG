from fastapi import APIRouter

from app.api.schemas import ChatRequest
from app.langgraph.edges import build_graph
from app.services.rag_service import build_portfolio_rag_chain

router = APIRouter()

@router.post("/chat")
async def chat(request: ChatRequest):
    chain = build_portfolio_rag_chain()
    response = chain.invoke({"input": request.message})
    return {"answer": response["answer"]}

@router.post("/advanced-chat")
async def advanced_chat(request: ChatRequest):
    agent_app = build_graph()

    inputs = {"question": request.message}
    result = agent_app.invoke(inputs)

    return {"answer": result["answer"]}