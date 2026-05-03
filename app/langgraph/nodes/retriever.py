import os
from app.langgraph.graph import AgentState
from langchain_openai import  OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore

# --- Node: Conditional Retriever ---
def retrieve_node(state: AgentState):
    print("---RETRIEVING DOCUMENTS---")
    question = state["question"]
    category = state["classification"]

    embeddings = OpenAIEmbeddings(model="text-embedding-3-small", dimensions=int(os.getenv("PINECONE_DIMENSIONS")))
    vectorstore = PineconeVectorStore(
        index_name=os.getenv("PINECONE_INDEX_NAME"), 
        embedding=embeddings,

    )

    search_kwargs = {"k": 3}
    
    if category in ["project", "resume"]:
        search_kwargs["filter"] = {"type": category}
    
    retriever = vectorstore.as_retriever(search_kwargs=search_kwargs)
    
    docs = retriever.invoke(question)
    return {"documents": docs}