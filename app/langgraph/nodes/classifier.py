from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from typing import Dict, Any
from dotenv import load_dotenv
import os

load_dotenv()

# 1. Define the strictly allowed outputs
class QueryClassification(BaseModel):
    category: str = Field(
        description="The exact category of the user's query.",
        enum=["personal", "project", "unknown"]
    )

def classify_query_node(state: dict) -> Dict[str, Any]:
    """
    Analyzes the user's question and routes it to the correct workflow.
    """
    question = state["question"]
    print(f"---CLASSIFYING QUERY: '{question}'---")

    # 2. Setup LLM to enforce the Pydantic schema
    # Temperature 0 is critical here for consistent routing
    llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0, api_key=os.getenv("OPENAI_API_KEY"))
    structured_llm = llm.with_structured_output(QueryClassification)

    # 3. The Classification Prompt
    system_prompt = """You are the routing brain for Nikhil Saji's portfolio AI.
    Analyze the user's question and classify it into EXACTLY ONE of these categories:

    - 'resume': Questions about Nikhil's background, education, location, hobbies, or contact info.
    - 'project': Questions about specific applications or products Nikhil has built (e.g., Expensely, full-stack tools).
    - 'unknown': Gibberish, highly inappropriate requests, or questions completely unrelated to a professional software engineering portfolio.

    Do not answer the question. Only output the classification category."""

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{question}")
    ])

    # 4. Chain it together and invoke
    classifier_chain = prompt | structured_llm
    result = classifier_chain.invoke({"question": question})

    print(f"---ROUTING TO: {result.category.upper()}---")
    
    # 5. Return the updated state
    return {"classification": result.category}


if __name__ == "__main__":
    # Test cases mapped to your four categories
    test_queries = [
        "Where did you go to school?",                 # Should be 'personal'
        "What backend technologies power Expensely?",  # Should be 'project'
        "Explain how a RAG architecture works.",       # Should be 'technical'
        "Write a poem about a flying dog.",            # Should be 'unknown'
    ]

    for q in test_queries:
        # Mocking the LangGraph state input
        mock_state = {"question": q}
        output_state = classify_query_node(mock_state)
        print(f"Result -> {output_state['classification']}\n")