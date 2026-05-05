import os
from typing import Any, Dict

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.services.memory_service import get_chat_history
from app.utils.helpers import (
    contains_company_name,
    extract_last_user_message,
    is_follow_up_question,
)

load_dotenv()

class QueryClassification(BaseModel):
    category: str = Field(
        description="The exact category of the user's query.",
        enum=["resume", "project", "unknown"]
    )

def classify_query_node(state: dict) -> Dict[str, Any]:
    """
    Analyzes the user's question and routes it to the correct workflow.
    """
    question = state["question"]
    session_id = state.get("session_id", "default")
    print(f"---CLASSIFYING QUERY: '{question}'---")

    if contains_company_name(question):
        print("---ROUTING TO: RESUME (COMPANY MATCH)---")
        return {"classification": "resume"}

    if is_follow_up_question(question):
        history = get_chat_history(session_id)
        last_user = extract_last_user_message(history)
        if last_user and contains_company_name(last_user):
            print("---ROUTING TO: RESUME (FOLLOW-UP COMPANY MATCH)---")
            return {"classification": "resume"}

    llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0, api_key=os.getenv("OPENAI_API_KEY"))
    structured_llm = llm.with_structured_output(QueryClassification)

    system_prompt = """You are the routing brain for Nikhil Saji's portfolio AI.
    Analyze the user's question and classify it into EXACTLY ONE of these categories:

    - 'resume': Questions about Nikhil's background, education, location, hobbies, contact info or about the companies where he has worked.
    - 'project': Questions about specific projects Nikhil has built.
    - 'unknown': Gibberish, highly inappropriate requests or questions completely unrelated to a software engineering portfolio.

    Do not answer the question. Only output the classification category."""

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{question}")
    ])

    # Chain it together and invoke
    classifier_chain = prompt | structured_llm
    result = classifier_chain.invoke({"question": question})

    print(f"---ROUTING TO: {result.category.upper()}---")
    
    return {"classification": result.category}


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