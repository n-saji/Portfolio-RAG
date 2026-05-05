from typing import Any, Dict, List, TypedDict
from langchain_core.documents import Document

class AgentState(TypedDict):
    question: str
    classification: str
    documents: List[Document]
    answer: str
    session_id: str
    history: str
    confidence: float
    retrieval_scores: List[float]
    retrieval_metadata: List[Dict[str, Any]]

