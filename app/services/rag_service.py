import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_core.prompts import ChatPromptTemplate
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_classic.chains import create_retrieval_chain

# Load env variables (API keys)
load_dotenv()

def build_portfolio_rag_chain():
    # 1. Setup Retrieval (Your Pinecone setup)
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small", dimensions=int(os.getenv("PINECONE_DIMENSIONS")))
    vectorstore = PineconeVectorStore(
        index_name=os.getenv("PINECONE_INDEX_NAME"), 
        embedding=embeddings
    )
    # k=3 keeps context tight and reduces token costs
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

    # 2. Setup the LLM
    # temperature=0 is crucial here. You want factual answers about your experience, not creative fiction.
    llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)

    # 3. Create the Prompt Template
    # This is the "Persona" of your agent. 
    system_prompt = (
        "You are an AI assistant for Nikhil Saji's professional portfolio website. "
        "Your job is to answer questions about Nikhil's experience, projects, and skills "
        "based ONLY on the provided context. "
        "If you don't know the answer based on the context, explicitly say: "
        "'I don't have enough context to answer that, but you can reach out to Nikhil directly.' "
        "Keep your answers concise, professional, and highlight his impact. "
        "\n\n"
        "Context: {context}"
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
    ])

    # 4. Build the Chain
    # This chain handles stuffing the retrieved docs into the {context} variable
    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    
    # This chain handles fetching the docs AND returning them in the final output
    rag_chain = create_retrieval_chain(retriever, question_answer_chain)

    return rag_chain

# --- Testing the Chain ---
if __name__ == "__main__":
    print("Building RAG Chain...")
    chain = build_portfolio_rag_chain()
    
    query = "What technologies is Nikhil confident in and has used extensively?"
    print(f"\n🗣️ User Query: {query}")
    
    # Execute the chain
    response = chain.invoke({"input": query})
    
    print("\n" + "="*50)
    print("🤖 LLM ANSWER:")
    print("="*50)
    print(response["answer"])
    
    print("\n" + "="*50)
    print("🔍 DEBUG: RETRIEVED DOCUMENTS:")
    print("="*50)
    for i, doc in enumerate(response["context"]):
        print(f"\nDoc {i+1} Metadata: {doc.metadata}")
        print(f"Content: {doc.page_content[:150]}...")