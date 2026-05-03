from app.langgraph.graph import AgentState
from langchain.agents import AgentState

def fallback_node(state: AgentState):
    """Fallback node that handles unknown classifications or low-confidence retrievals."""
    print("---FALLBACK TRIGGERED---")
    # This handles "unknown" classifications or inappropriate questions

    if "confidence" in state and state["confidence"] < 0.55:
        fallback_message = (
            "I don't have enough specific information in my context to answer that accurately. "
            "You might want to reach out to Nikhil directly for more details!"
        )
    else:
        fallback_message = (
            "I'm sorry, but I can only answer questions related to Nikhil's projects and resume. "
            "Please ask something specific about his work experience, skills or projects."
        )
    return {"answer": fallback_message}