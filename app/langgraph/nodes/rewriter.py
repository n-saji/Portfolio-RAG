from app.langgraph.graph import AgentState
from app.services.memory_service import get_chat_history
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import os

from app.utils.helpers import extract_last_n_conversations

def rewrite_query_node(state: AgentState) -> AgentState:
    """Rewrites a follow-up question into a standalone query using chat history."""
    
    question = state["question"]
    session_id = state.get("session_id", "default")
    history = get_chat_history(session_id)

    if not history:
        # Nothing to rewrite against, pass through as-is
        return {**state, "is_follow_up": False}

    history_text = extract_last_n_conversations(history, n = 2)

    llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0, api_key=os.getenv("OPENAI_API_KEY"))

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a query rewriter. Given a conversation history and a follow-up question,
            rewrite the follow-up into a complete, standalone question that contains all necessary context.
            Return ONLY the rewritten question. No explanation, no preamble."""),
        ("human", "Conversation history:\n{history}\n\nFollow-up question: {question}")
    ])

    chain = prompt | llm
    rewritten = chain.invoke({"history": history_text, "question": question}).content.strip()

    print(f"---REWRITER: '{question}' → '{rewritten}'---")

    # Overwrite question with the rewritten one, mark as no longer a follow-up
    return {**state, "question": rewritten, "is_follow_up": False}