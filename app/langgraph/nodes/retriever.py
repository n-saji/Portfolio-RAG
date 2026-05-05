import os
from app.langgraph.graph import AgentState
from langchain_openai import OpenAIEmbeddings
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
        filter_kwargs = {"type": category}
    
    results = vectorstore.similarity_search_with_score(
        query=question,
        k=4,
        filter=filter_kwargs if filter_kwargs else None,
    )
    
    if not results:
        return {
            "documents": [],
            "confidence": 0.0,
            "retrieval_scores": [],
            "retrieval_metadata": [],
        }

    min_score = float(os.getenv("MIN_SCORE_THRESHOLD", 0.2))
    filtered = [res for res in results if res[1] >= min_score]
    if not filtered:
        print(f"---NO DOCS ABOVE MIN_SCORE_THRESHOLD ({min_score})---")
        return {
            "documents": [],
            "confidence": 0.0,
            "retrieval_scores": [],
            "retrieval_metadata": [],
        }

    docs = [res[0] for res in filtered]
    scores = [res[1] for res in filtered]
    metadata = [doc.metadata for doc in docs]

    max_confidence = max(scores)
    print(f"---RETRIEVAL CONFIDENCE (MAX): {max_confidence:.4f}---")
    print(f"---RETRIEVED DOCUMENTS---")

    return {
        "documents": docs,
        "confidence": max_confidence,
        "retrieval_scores": scores,
        "retrieval_metadata": metadata,
    }