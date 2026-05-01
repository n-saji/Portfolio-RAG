import os
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore

load_dotenv()

def test_retriever(query: str, filters: dict = None):
    print(f"\n🔍 Testing Query: '{query}'")
    print("-" * 50)

    embeddings = OpenAIEmbeddings(model="text-embedding-3-small", dimensions=int(os.getenv("PINECONE_DIMENSIONS")))
    index_name = os.getenv("PINECONE_INDEX_NAME")

    vectorstore = PineconeVectorStore(
        index_name=index_name,
        embedding=embeddings
    )

    search_kwargs = {"k": 3}
    if filters:
        search_kwargs["filter"] = filters

    retriever = vectorstore.as_retriever(search_kwargs=search_kwargs)

    retrieved_docs = retriever.invoke(query)

    if not retrieved_docs:
        print("❌ CRITICAL FAILURE: No documents retrieved!")
        return

    for i, doc in enumerate(retrieved_docs):
        print(f"\n📄 Result {i + 1} (Metadata: {doc.metadata})")
        print(f"Content Snippet: {doc.page_content[:200]}...") # Print first 200 chars
        print("-" * 50)

if __name__ == "__main__":
    # Test 1: A general semantic search
    test_retriever("What is the tech stack for Expensely?")

    # Test 2: Testing your metadata filters!
    test_retriever(
        query="What was the backend built with?", 
        filters={"name": "Talky Space"}
    )