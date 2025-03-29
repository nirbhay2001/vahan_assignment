import os
import warnings
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_chroma import Chroma
from utils.llm_model import embeddings, llm
from langchain_text_splitters import RecursiveCharacterTextSplitter
warnings.filterwarnings("ignore")
load_dotenv()

pdf_path = os.path.abspath("./pdfs/fictional_saas_product.pdf")
persist_directory = "./chroma_database"
retriever = None  
try:
    if not os.path.exists(persist_directory):
        os.makedirs(persist_directory)
    docs_list = []
    if not os.path.exists(pdf_path):
        print(f"pdf path under os.path.exists: {pdf_path}")
        raise FileNotFoundError(f"PDF file not found at: {pdf_path}")
    print(f"pdf path: {pdf_path}")
    loader = PyPDFLoader(pdf_path)
    docs = loader.load()
    docs_list.extend(docs)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
    splits = text_splitter.split_documents(docs_list)
    if os.path.exists(persist_directory) and os.listdir(persist_directory):
        vectorstore = Chroma(persist_directory=persist_directory, embedding_function=embeddings)
    else:
        vectorstore = Chroma.from_documents(documents=splits, embedding=embeddings, persist_directory=persist_directory)
    retriever = vectorstore.as_retriever(search_kwargs={
        "k": 1
    })
    print("PDF processing completed successfully!")
except FileNotFoundError as fe:
    print(f"File Error: {fe}")
except Exception as e:
    print(f"Error Occurred: {e}")

