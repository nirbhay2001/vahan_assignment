## Support AI Chatbot - Smart Conversational Assistant
This project is an AI-powered chatbot designed to provide intelligent responses to user queries. It can understand user inputs, maintain context, and generate meaningful follow-up responses.

![Chatbot UI](https://res.cloudinary.com/dgejijgss/image/upload/v1743283335/vahan_project_UI_response_image_tilild.jpg )

## 🚀 Key Features (Support AI Chatbot)

-  **AI-Powered Chatbot** for answering user queries about a fictional SaaS product  
-  **Chat History Management** using Redis for efficient storage and retrieval  
-  **Real-time User Interaction Tracking** to monitor chatbot responses  
-  **Query Analytics** to evaluate chatbot performance and accuracy  
-  **Response Validation Mechanism** to assess how accurately the chatbot answers user queries  
-  **Session-Based Chat Storage** for retrieving past conversations  
-  **Redis-Based Caching** to improve chatbot response time


## 🛠 Tech Stack

- **Backend:** Python, FastAPI, LangChain, LangGraph,HuggingFace,LLM 
- **Database:** Redis  
- **Containerization:** Docker, Docker Compose  
- **API Testing:** Postman

## 🔧 Setup Instructions  
 
### Steps to Set Up the Project:  

1. Clone the repository:  
   ```sh
   git clone https://github.com/nirbhay2001/vahan_assignment
   cd vahan_assignment


2. Environment Variables 
for backend folder `.env` file with the following variables:  

### **Backend (`backend/.env`)**
 
```sh
GROQ_API_KEY=<your groq api key>
LANGCHAIN_API_KEY=<your langchain api key>
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
```
3. Finally run the command to start project
```sh
For Backend:
1. cd backend
2. pip install -r requirement.txt
3. python main.py
For Frontend:
1. cd frontend
2. npm i
3. npm run dev

```
### **Note:** 
I tried using Docker for this project, but the build process was taking too much time. Since I was running the backend in a Python environment, I had not stored any dependencies in a requirements.txt file. However, when I included Docker, I needed the requirements.txt file, so I generated it using the command: 
```sh
pip freeze > requirements.txt
```
This added all the dependencies from my Python environment, including some that were not used in the project. I manually removed the unnecessary dependencies, but some were still causing long build times in Docker.
Due to this, I decided not to use Docker for setting up the project.
### **🏗 Projects Architecture**
This project utilizes LangGraph, LangChain, and ChromaDB for handling text embeddings and managing conversational flow. Below is the architectural breakdown of how different components interact to process user queries efficiently.
## Components Used
-  **LangGraph :** Enables a structured flow of execution with four nodes and one tool.  
-  **ChromaDB :**  Stores text embeddings for retrieving relevant documents. 
-  **Redis :** Maintains session-based chat history for users. 
-  **Langchain :** Helps in orchestrating LLM-based workflows.

## Nodes & Tools in LangGraph
The project consists of the following four nodes and one tool:
- **grade_documents Node**
- **support Node**
- **agent Node**
- **generate Node**
- **retriever_tool (Tool for retrieving documents from ChromaDB)**
 ## State Management
 LangGraph is stateful, allowing the project to maintain conversation history efficiently. The state stores both human messages (user queries) and AI messages (chatbot responses).
Additionally, user sessions are managed, where both the user's question and the chatbot's response are stored in Redis. The key for each entry is the user's session ID, while the value contains the chat history (user queries and bot responses).
## Workflow Execution
**1. Session Management**

- **When a user submits a question, the backend checks if the request header contains a session ID.**
- **If no session ID is found, a new one is generated and stored in a cookie to ensure that future user queries contain the same session ID.**
- **This session ID helps in maintaining a continuous conversation by storing the chat history in Redis.**

**2. Retrieving Previous Chats**
- **When a query is received, the backend extracts the session ID from the headers.**
- **It then checks Redis to see if there is any existing chat history for that session.**
- **If chat history exists, it is added to the LangGraph state, along with the new user query.**

**3. Processing the Query Using LangGraph**
- **Once the question is added to the LangGraph state, the agent node is triggered.**
- **The agent node retrieves relevant documents using retriever_tool, which fetches embeddings from ChromaDB.**
- **These retrieved documents are also added to the LangGraph state.**
- **The agent node then calls the grade_documents node.**

**Document Grading & Query Analysis**
- **The grade_documents node evaluates whether the retrieved documents are relevant to the user's question.**
- **It also checks whether the user query is similar to previous chat history.**
- **If the query is relevant to chat history or retrieved documents, it proceeds to the generate node.**
- **If not, it is sent to the support node.**

**Handling Responses**
- **Support Node: If the chatbot does not have enough information to answer the query, the support node informs the user that it lacks relevant details and provides contact information for the support team.**
  
- **Generate Node: If the query is related to previous chat history or retrieved documents, the generate node formulates a response based on the chat history context and documents. The generated response is then delivered to the user.**
  
![Architecture](https://res.cloudinary.com/dgejijgss/image/upload/v1743282967/vahan_project_Archte_image_jq3uui.jpg)

## Chatbot Analytics & Accuracy Tracking
The project includes an analytics route to track chatbot performance, including:
- **Total Questions Count:** Increment total_questions for every new user query.
- **Categorizing Questions:** Identify the type of question (e.g., travel, support, or others) and update question_types.
- **Detecting Repeat Questions:** Compare the current question with previous ones in the chat history and increment repeat_questions if a match is found..
- **API Endpoint:** Fetch Analytics data from this api (BaseUrl/analytics).

![Architecture](https://res.cloudinary.com/dgejijgss/image/upload/v1743283276/vahan_project_analytics_tracking_k3vjzt.png)




 
