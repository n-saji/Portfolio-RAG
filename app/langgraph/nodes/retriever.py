import os
from app.langgraph.graph import AgentState
from langchain_openai import  OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore

# --- Node: Conditional Retriever ---
def retrieve_node(state: AgentState):
    print("---RETRIEVING DOCUMENTS---")
    question = state["question"]
    category = state["classification"]

    embeddings = OpenAIEmbeddings(model="text-embedding-3-small", 
                                  dimensions=int(os.getenv("PINECONE_DIMENSIONS")))
    vectorstore = PineconeVectorStore(
        index_name=os.getenv("PINECONE_INDEX_NAME"), 
        embedding=embeddings,
    )

    filter_kwargs = {}
    if category in ["project", "resume"]:
        filter_kwargs["filter"] = {"type": category}
    
    results = vectorstore.similarity_search_with_score(query=question,k=3,
                                                         filter=filter_kwargs if filter_kwargs else None)
    
    if not results:
        return {"documents": [], "confidence": 0.0}
    
    docs = [res[0] for res in results]
    scores = [res[1] for res in results]
    
    avg_confidence = sum(scores) / len(scores)
    print(f"---RETRIEVAL CONFIDENCE: {avg_confidence:.4f}---")

    return {"documents": docs, "confidence": avg_confidence}