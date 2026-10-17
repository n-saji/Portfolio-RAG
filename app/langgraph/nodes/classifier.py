import os
from typing import Any, Dict
from app.services.memory_service import get_chat_history
from app.utils.helpers import extract_last_n_conversations
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

load_dotenv()

class QueryClassification(BaseModel):
    category: str = Field(
        description="The exact category of the user's query.",
        enum=["resume", "project", "unknown"]
    )
    section: str = Field(
        description="If category is 'resume', specify the relevant section. Optional for other categories.",
        enum = ["summary","skills","experience","education","additional_info"],
        default=""
    )
    tech: list[str] = Field(
        description="If category is 'resume' and section is 'experience' or category is 'project', list the relevant technologies. Optional otherwise.",
        default=[]
    )
    is_follow_up: bool = Field(
        description="Indicates if the question is a follow-up based on conversation history.",
        default=False
    )


def _standalone_project_question(question: str) -> bool:
    normalized = question.lower()
    return any(
        phrase in normalized for phrase in ("latest project", "newest project", "most recent project")
    ) and not any(employer in normalized for employer in ("actfore", "holiday channel", "wiz freight"))

def classify_query_node(state: dict) -> Dict[str, Any]:
    """
    Analyzes the user's question and routes it to the correct workflow.
    """
    question = state["question"]
    session_id = state.get("session_id", "default")
    history = get_chat_history(session_id)
    history_text = extract_last_n_conversations(history, n=2)
    print(f"---CLASSIFYING QUERY: '{question}'---")

    llm = ChatOpenAI(
        model=os.getenv("RAG_ROUTER_MODEL", "gpt-4.1-mini"),
        temperature=0,
        timeout=25,
        max_retries=2,
    )
    structured_llm = llm.with_structured_output(QueryClassification)

    system_prompt = """Route questions for Nikhil Saji's portfolio. Never answer them.
    resume: Nikhil's identity, current or past jobs, years of experience, education,
    skills, contact details, location, career transitions, or achievements at work.
    project: a named personal project, its architecture, code, technology, or link.
    unknown: requests unrelated to Nikhil, including generic coding, homework,
    creative writing, or questions about another person.
    Use conversation history only to interpret a short follow-up. Set is_follow_up
    only when the new question depends on a prior turn. Choose a resume section
    only when clear. Leave tech empty unless a specific technology is named.
    Previous assistant answers are not evidence of biographical facts."""

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "Conversation history:\n{history}\n\n question: {question}")
    ])

    # Chain it together and invoke
    classifier_chain = prompt | structured_llm
    result = classifier_chain.invoke({"question": question, "history": history_text})

    print(f"---ROUTING TO: {result.category.upper()}---")
    print(f"---SECTION: {result.section}---")
    print(f"---TECH: {result.tech}---")
    is_follow_up = bool(history_text and result.is_follow_up and not _standalone_project_question(question))
    print(f"---IS FOLLOW-UP: {is_follow_up}---")
    return {
        "classification": result.category,
        "section": result.section,
        "tech": result.tech,
        "is_follow_up": is_follow_up,
    }


if __name__ == "__main__":
    # Test cases
    test_queries = [
        "Where did you go to school?",                 # Should be 'resume'
        "What backend technologies power Expensely?",  # Should be 'project'
        "Explain how a RAG architecture works.",       # Should be 'unknown'
        "Write a poem about a flying dog.",            # Should be 'unknown'
    ]

    for q in test_queries:
        # Mocking the LangGraph state input
        mock_state = {"question": q}
        output_state = classify_query_node(mock_state)
        print(f"Result -> {output_state['classification']}\n")
