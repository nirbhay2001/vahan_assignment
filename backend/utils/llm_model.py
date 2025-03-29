from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq

embeddings=HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
llm=ChatGroq(model_name="Gemma2-9b-It")