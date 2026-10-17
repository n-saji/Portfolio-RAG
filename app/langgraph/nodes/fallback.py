from app.langgraph.graph import AgentState

def fallback_node(state: AgentState):
    """Fallback node that handles unknown classifications or low-confidence retrievals."""
    if state.get("classification") == "unknown":
        return {"answer": "I'm best placed to talk about my work and projects. What would you like to know?"}
    return {"answer": "I'm not sure about that detail. Feel free to ask me about another part of my work."}
