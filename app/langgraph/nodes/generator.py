from app.langgraph.graph import AgentState
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.services.memory_service import get_chat_history

def generate_node(state: AgentState):
    print("---GENERATING ANSWER WITH MEMORY---")
    question = state["question"]
    documents = state["documents"]
    session_id = state.get("session_id", "default")

    chat_history = get_chat_history(session_id)
    
    # Format docs into a single string
    context = "\n\n".join(doc.page_content for doc in documents)

    llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
    
    prompt = ChatPromptTemplate.from_template(
        "You are an AI assistant for Nikhil's portfolio. "
        "Answer the question based ONLY on the following context. "
        "Use the Conversation History for context if the user asks a follow-up question. "
        "If you don't know the answer, say you don't know.\n\n"
        "Conversation History:\n{history}\n\n"
        "Question: {question}\n"
        "Context: {context}"

    )
    
    # use StrOutputParser to get raw text back instead of an AIMessage object
    chain = prompt | llm | StrOutputParser()
    answer = chain.invoke({"question": question, "context": context, "history": chat_history})
    
    return {"answer": answer, "history": chat_history}