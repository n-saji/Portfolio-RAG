import os
from app.langgraph.graph import AgentState
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from app.services.memory_service import get_chat_history
from app.utils.helpers import extract_last_user_message, is_follow_up_question

# --- Node: Conditional Retriever ---
def retrieve_node(state: AgentState):
    print("---RETRIEVING DOCUMENTS---")
    question = state["question"]
    category = state["classification"]
    section = state.get("section", "")
    tech = state.get("tech", [])
    session_id = state.get("session_id", "default")

    search_query = question
    if is_follow_up_question(question):
        history = get_chat_history(session_id)
        last_user = extract_last_user_message(history)
        if last_user:
            search_query = f"{last_user} {question}"

    embeddings = OpenAIEmbeddings(model="text-embedding-3-small", 
                                  dimensions=int(os.getenv("PINECONE_DIMENSIONS")))
    vectorstore = PineconeVectorStore(
        index_name=os.getenv("PINECONE_INDEX_NAME"), 
        embedding=embeddings,
    )

    filter_kwargs = {}
    if category in ["project", "resume"]:
        filter_kwargs = {"type": category}
        if category == "resume" and section:
            filter_kwargs["section"] = section
        if tech:
            filter_kwargs["tech"] = {"$in": tech}
    
    results = vectorstore.similarity_search_with_score(
        query=search_query,
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

    for doc, score in zip(docs, scores):
        print(f"Score: {score:.4f} | Source: {doc.metadata.get('source', 'unknown')} | Content: {doc.page_content[:100]}...")

    max_confidence = max(scores)
    print(f"---RETRIEVAL CONFIDENCE (MAX): {max_confidence:.4f}---")
    print(f"---RETRIEVED DOCUMENTS---")

    return {
        "documents": docs,
        "confidence": max_confidence,
        "retrieval_scores": scores,
        "retrieval_metadata": metadata,
    }