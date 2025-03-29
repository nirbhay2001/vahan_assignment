import os
import warnings
import logging
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Depends,Response
from pydantic import BaseModel
from session_manager import get_session_id, get_chat_history, update_chat_history
load_dotenv()
from utils.llm_model import llm
from chromadbService.dbService import retriever
from langchain.tools.retriever import create_retriever_tool
from typing import Annotated, Sequence, TypedDict, Literal
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import Field
from langgraph.prebuilt import tools_condition
from langgraph.graph import END, StateGraph, START
from langgraph.prebuilt import ToolNode
from fastapi.middleware.cors import CORSMiddleware
from contextvars import ContextVar
from analytics import update_analytics,analytics_data
warnings.filterwarnings("ignore")

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

session_id_var = ContextVar("session_id", default=None)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")
langchain_tracing = os.getenv("LANGCHAIN_TRACING_V2")
langchain_endpoint = os.getenv("LANGCHAIN_ENDPOINT")

if not all([GROQ_API_KEY, LANGCHAIN_API_KEY, langchain_tracing, langchain_endpoint]):
    raise ValueError("Missing required environment variables. Please check your .env file.")

os.environ["GROQ_API_KEY"] = GROQ_API_KEY
os.environ["LANGCHAIN_API_KEY"] = LANGCHAIN_API_KEY
os.environ["LANGCHAIN_TRACING_V2"] = langchain_tracing
os.environ["LANGCHAIN_ENDPOINT"] = langchain_endpoint

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  
    allow_credentials=True, 
    allow_methods=["*"],    
    allow_headers=["*"]     
)
if retriever is None:
    raise ValueError("Retriever is not initialized. Check dbService.py for errors.")
retriever_tool = create_retriever_tool(
    retriever,
    "retrieve_travel_documents",  
    "Search and return relevant information about flights, airlines, travel policies, and discounts.",
)
tools = [retriever_tool]
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

def grade_documents(state) -> Literal["generate", "support"]:
    print("---CHECK RELEVANCE---")
    session_id = session_id_var.get() 
    messages = state["messages"]
    print(f"Message Types: {[type(m).__name__ for m in messages]}")
    print(f"Message Contents: {[m.content[:50]+'...' if hasattr(m, 'content') else str(m)[:50] for m in messages]}")
    user_question = None
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            user_question = msg.content.lower()
            break
    if not user_question:
        print("---DECISION: NO USER QUESTION FOUND---")
        return "support"
    last_message = messages[-1]
    try:
        docs = (
            "\n".join(doc.page_content for doc in last_message.content)
            if hasattr(last_message.content, '__iter__') and not isinstance(last_message.content, str)
            else str(last_message.content)
        )
    except Exception as e:
        print(f"Document processing error: {e}")
        docs = ""
    if not docs.strip():
        print("---DECISION: NO DOCUMENTS FOUND---")
        return "support"
    full_history = "\n".join(
        f"{'User' if isinstance(m, HumanMessage) else 'Assistant'}: {m.content}"
        for m in messages 
        if isinstance(m, (HumanMessage, AIMessage)) and not (
            isinstance(m, AIMessage) and hasattr(m.content, '__iter__')  
        )
    )
    print(f"grade_documents full history",full_history)
    class Grade(BaseModel):
        binary_score: str = Field(description="Relevance score 'yes' or 'no'")
    llm_with_tool = llm.with_structured_output(Grade)
    template = """You are an AI grader assessing whether a retrieved document and chat history are relevant to a user's question.
        ### Conversation History:
        {conversation_history}
        ### Retrieved Documents:
        {context}
        ### User Question:
        {question}
        ## Decision-Making Rules:
        1️ If the document contains keywords, concepts, or direct answers related to the question, it is relevant.
        2️ If the conversation history has discussed similar topics and aligns with the question, it is relevant.
        3️ If both document and chat history are relevant, generate a response combining insights from both.
        4️ If only the document is relevant but chat history is not, respond based on the document only.
        5️ If neither the document nor chat history is relevant, return "no".
        6. you do not have to add or think about anything yourself other than context and conversation_history """
    try:
        result = (ChatPromptTemplate.from_template(template) | llm_with_tool).invoke({
            "question": user_question,
            "context": docs,
            "conversation_history": full_history
        })
        return "generate" if result.binary_score == "yes" else "support"
    except Exception as e:
        logger.error(f"Grading Error: {str(e)}")
        return "support"

def support(state):
    print("---RETURNING SUPPORT INFO---")
    support_info = """
    For further assistance, please contact:
    - Customer Support: +91-9876543210
    - Email: support@tripease.com
    - Website: www.tripease.com
    - WhatsApp Support: +91-9999999999"""
    return {"messages": [AIMessage(content=f"I couldn't find relevant information for your query. {support_info}")]}

def agent(state):
    print("---CALL AGENT---")
    messages = state["messages"]
    model = llm.bind_tools(tools)
    response = model.invoke(messages)
    print("documents response",response)
    return {"messages": [response]}


def generate(state):
    print("---GENERATE---")
    messages = state["messages"]
    print(f"Debug - Message Types: {[type(m).__name__ for m in messages]}")
    print(f"Debug - Message Contents: {[m.content[:50]+'...' if hasattr(m, 'content') else str(m)[:50] for m in messages]}")
    user_question = None
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            user_question = msg.content
            break
    if not user_question:
        logger.warning(f"No HumanMessage found in messages. Total messages: {len(messages)}")
        return {"messages": [AIMessage(content="Please ask your question again.")]}
    last_message = messages[-1]
    retrieved_docs = ""
    if isinstance(last_message.content, str):
        retrieved_docs = last_message.content
    elif hasattr(last_message.content, '__iter__'):
        try:
            retrieved_docs = "\n\n".join(
                f"• {doc.page_content}" if hasattr(doc, 'page_content') else str(doc)
                for doc in last_message.content
            )
        except Exception as e:
            logger.error(f"Document join failed: {e}")
            retrieved_docs = str(last_message.content)
    else:
        retrieved_docs = str(last_message.content)

    if not retrieved_docs.strip():
        logger.warning("No valid documents found in last message")
        return {"messages": [AIMessage(content="I couldn't find relevant information.")]}
    full_history = "\n".join(
        f"{'User' if isinstance(m, HumanMessage) else 'Assistant'}: {m.content}"
        for m in messages 
        if isinstance(m, (HumanMessage, AIMessage)) and not (
            isinstance(m, AIMessage) and hasattr(m.content, '__iter__')  
        )
    )
    print(f"generate function ka  full history",full_history)
    template = """You are a travel expert assistant having a conversation with a user. 
        The full conversation history is provided below for context:
        {conversation_history}
        Relevant travel information from our database:
        {retrieved_docs}
        Current user question: {question}
        IMPORTANT INSTRUCTIONS:
        1. ALWAYS maintain context from the entire conversation history
        2. NEVER ask for information already provided
        3. For flight queries, always reference:
        - Origin city (from history)
        - Destination city (from history)
        - Airline (if mentioned)
        - Class (if mentioned)
        4. For follow-up questions, assume they relate to previous context
        5. Provide detailed, helpful responses based on available information not provide any information itself
        6. you do not have to add or think about anything yourself other than context and  conversation_history """
    try:
        prompt = ChatPromptTemplate.from_template(template)
        response = (prompt | llm | StrOutputParser()).invoke({
            "conversation_history": full_history,
            "retrieved_docs": retrieved_docs,
            "question": user_question
        })
        cleaned_response = " ".join(response.strip().split())
        return {"messages": [AIMessage(content=cleaned_response)]}
    except Exception as e:
        logger.error(f"Generation failed. Question: '{user_question}'. Error: {str(e)}")
        error_msg = """I'm having trouble generating a response. 
        For immediate help, please contact:
        • Phone: +91-9876543210
        • WhatsApp: +91-9999999999"""
        return {"messages": [AIMessage(content=error_msg)]}

workflow = StateGraph(AgentState)
workflow.add_node("agent", agent)
retrieve = ToolNode([retriever_tool])
workflow.add_node("retrieve", retrieve)
workflow.add_node("generate", generate)
workflow.add_node("support", support)
workflow.add_edge(START, "agent")
workflow.add_conditional_edges(
    "agent",
    tools_condition,
    {"tools": "retrieve", END: END},
)
workflow.add_conditional_edges(
    "retrieve",
    grade_documents,
    {
        "generate": "generate",
        "support": "support"
    }
)
workflow.add_edge("generate", END)
workflow.add_edge("support", END)
graph = workflow.compile()

class QueryRequest(BaseModel):
    question: str

@app.post("/ask")
def ask_question(request: Request, query: QueryRequest, response: Response, session_id: str = Depends(get_session_id)):
    logger.debug(f"\n{'='*50}\nincoming request debug\n{'='*50}")
    logger.debug(f"incoming cookies: {request.cookies}")
    logger.debug(f"headers: {dict(request.headers)}")
    logger.debug(f"session id from dependency: {session_id}")
    history = get_chat_history(session_id)
    logger.debug(f"\nsession history length: {len(history)}")
    print(f"session id for session_id_var ${session_id}")
    session_id_var.set(session_id)
    state = {"messages": []}
    for msg in history:
        state["messages"].extend([
            HumanMessage(content=msg["user"]),
            AIMessage(content=msg["bot"])
        ])
    logger.debug("\ncurrent conversation state:")
    for i, msg in enumerate(state["messages"]):
        logger.debug(f"{i}. {type(msg).__name__}: {msg.content[:100]}{'...' if len(msg.content) > 100 else ''}")
    user_message = HumanMessage(content=query.question)
    state["messages"].append(user_message)

    travel_keywords = ['flight', 'trip', 'travel', 'airline', 'book', 'booking',
                     'ticket', 'fare', 'journey', 'voyage', 'reservation']
    category = "travel" if any(keyword in query for keyword in travel_keywords) else "support"
    print(f"session id for update_analytics ${session_id}")
    update_analytics(query, category, session_id)
    try:
        bot_response = graph.invoke(state)
        if bot_response and "messages" in bot_response:
            bot_answer = bot_response["messages"][-1].content
            update_chat_history(session_id, query.question, bot_answer)
            if 'set-cookie' in response.headers:
                logger.debug(f"\nresponse cookie set: {response.headers['set-cookie']}")
            else:
                logger.warning("no cookie set in response!")
            return {"answer": bot_answer}
    except Exception as e:
        logger.error(f"Processing error: {str(e)}", exc_info=True)
        return {"answer": "there was an error processing your request."}
    return {"answer": "i couldn't process your request."}

@app.get("/analytics")
def get_analytics():
    return analytics_data