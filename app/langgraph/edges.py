from langgraph.graph import StateGraph, START, END
from app.langgraph.graph import AgentState
from app.langgraph.nodes.classifier import classify_query_node
from app.langgraph.nodes.retriever import retrieve_node
from app.langgraph.nodes.generator import generate_node
from app.langgraph.nodes.fallback import fallback_node
from app.langgraph.nodes.rewriter import rewrite_query_node

# --- Conditional Edge Functions ---
def route_from_classifier(state: AgentState):
    """Routes to fallback if unknown, otherwise proceeds to retrieval."""
    if state["classification"] == "unknown":
        return "fallback"
    if state.get("is_follow_up"):
        return "rewriter"
    return "retriever"

def route_from_retriever(state: AgentState):
    """Only missing evidence triggers fallback; scores are ranking signals."""
    if not state["documents"]:
        return "fallback"
    return "generator"

# --- Build the Graph ---
def build_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("classifier", classify_query_node) 
    workflow.add_node("retriever", retrieve_node)
    workflow.add_node("generator", generate_node)
    workflow.add_node("fallback", fallback_node)
    workflow.add_node("rewriter", rewrite_query_node)

    workflow.add_edge(START, "classifier")
    
    workflow.add_conditional_edges(
        "classifier",
        route_from_classifier,
        {"retriever": "retriever", "fallback": "fallback", "rewriter": "rewriter"}
    )
    
    workflow.add_conditional_edges(
        "retriever",
        route_from_retriever,
        {"generator": "generator", "fallback": "fallback"}
    )
    
    workflow.add_edge("generator", END)
    workflow.add_edge("fallback", END)
    workflow.add_edge("rewriter", "retriever")
    app = workflow.compile()
    return app
