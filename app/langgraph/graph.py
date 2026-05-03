from typing import List, TypedDict
from langchain_core.documents import Document

class AgentState(TypedDict):
    question: str
    classification: str
    documents: List[Document]
    answer: str
    session_id: str
    history: str
    confidence: float

