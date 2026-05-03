from app.langgraph.graph import AgentState
from langchain.agents import AgentState

def fallback_node(state: AgentState):
    print("---FALLBACK TRIGGERED---")
    # This handles "unknown" classifications or inappropriate questions
    fallback_message = (
        "I'm sorry, but I can only answer questions related to Nikhil's projects and resume. "
        "Please ask something specific about his work experience, skills, or projects."
    )
    return {"answer": fallback_message}