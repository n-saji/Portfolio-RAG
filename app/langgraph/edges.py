from langgraph.graph import StateGraph, START, END
from app.langgraph.graph import AgentState
from app.langgraph.nodes.classifier import classify_query_node
from app.langgraph.nodes.retriever import retrieve_node
from app.langgraph.nodes.generator import generate_node
from app.langgraph.nodes.fallback import fallback_node

# --- Conditional Edge Functions ---
def route_from_classifier(state: AgentState):
    """Routes to fallback if unknown, otherwise proceeds to retrieval."""
    if state["classification"] == "unknown":
        return "fallback"
    return "retriever"

def route_from_retriever(state: AgentState):
    """If the retriever found nothing, fallback. Otherwise, generate."""
    if not state["documents"]:
        print("---NO DOCS FOUND: ROUTING TO FALLBACK---")
        return "fallback"
    return "generator"

# --- Build the Graph ---
def build_graph():
    workflow = StateGraph(AgentState)

    # 1. Add all nodes
    workflow.add_node("classifier", classify_query_node) # From Step 10
    workflow.add_node("retriever", retrieve_node)
    workflow.add_node("generator", generate_node)
    workflow.add_node("fallback", fallback_node)

    # 2. Add Edges
    workflow.add_edge(START, "classifier")
    
    # Conditional edge out of classifier
    workflow.add_conditional_edges(
        "classifier",
        route_from_classifier,
        {"retriever": "retriever", "fallback": "fallback"}
    )
    
    # Conditional edge out of retriever
    workflow.add_conditional_edges(
        "retriever",
        route_from_retriever,
        {"generator": "generator", "fallback": "fallback"}
    )
    
    # End edges
    workflow.add_edge("generator", END)
    workflow.add_edge("fallback", END)

    # Compile the graph into a runnable application
    app = workflow.compile()
    return app