import re

from app.langgraph.graph import AgentState
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.services.memory_service import get_chat_history

FALLBACK_ANSWER = (
    "I don't have enough context to answer that, but you can reach out to Nikhil directly."
)

_STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "of",
    "to",
    "in",
    "at",
    "for",
    "with",
    "from",
    "on",
    "about",
    "tell",
    "me",
    "you",
    "your",
    "his",
    "her",
    "their",
    "he",
    "she",
    "they",
    "experience",
    "role",
    "roles",
    "job",
    "jobs",
    "company",
    "project",
    "projects",
    "work",
    "worked",
}


def _extract_entity_candidates(question: str) -> list[str]:
    candidates: set[str] = set()

    preposition_matches = re.findall(
        r"\b(?:in|at|for|with|from|on)\s+([A-Za-z][A-Za-z0-9&\-.]*(?:\s+[A-Za-z][A-Za-z0-9&\-.]*){0,2})",
        question,
        flags=re.IGNORECASE,
    )
    for match in preposition_matches:
        cleaned = re.sub(r"[\.,!?;:]+$", "", match).strip()
        words = [w for w in cleaned.split() if w.lower() not in _STOPWORDS]
        if words:
            candidates.add(" ".join(words))

    cap_matches = re.findall(r"\b[A-Z][A-Za-z0-9&\-.]{2,}\b", question)
    for match in cap_matches:
        if match.lower() not in _STOPWORDS:
            candidates.add(match)

    return sorted({c.strip() for c in candidates if c.strip()})

def generate_node(state: AgentState):
    print("---GENERATING ANSWER WITH MEMORY---")
    question = state["question"]
    documents = state["documents"]
    session_id = state.get("session_id", "default")
    classification = state.get("classification")

    chat_history = get_chat_history(session_id)
    
    # Format docs into a single string
    context = "\n\n".join(doc.page_content for doc in documents)

    llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
    
    prompt = ChatPromptTemplate.from_template(
        "You are Nikhil, a software engineer. Answer questions about yourself based ONLY on the context below. "
        "Use Conversation History for follow-up questions. "
        "If the answer isn't in the context, say you don't know.\n\n"
        "Rules:\n"
        "- Always speak in first person (I, my, me)\n"
        "- Answer in plain conversational prose, 2-3 sentences max\n"
        "- Never use bullet points, numbered lists, dashes, or headers\n"
        "- Mention things by name but do not enumerate every detail\n"
        "- Do not add commentary, opinions, or information not in the context\n"
        "- Never start your answer with phrases like 'Based on the context' or 'According to the context'\n\n"
        "Conversation History:\n{history}\n\n"
        "Context:\n{context}\n\n"
        "Question: {question}"
)

    
    # use StrOutputParser to get raw text back instead of an AIMessage object
    chain = prompt | llm | StrOutputParser()
    answer = chain.invoke({"question": question, "context": context, "history": chat_history})
    
    return {"answer": answer, "history": chat_history}