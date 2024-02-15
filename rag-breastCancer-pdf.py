import pymongo
import os
from dotenv import load_dotenv
import certifi
from PyPDF2 import PdfReader
from langchain.text_splitter import CharacterTextSplitter
import streamlit as st
import pandas as pd
from openai import OpenAI as OpenAIClient
from langchain.llms import OpenAI
from langchain import PromptTemplate


# Load variables 
load_dotenv()
clientOpenAI = OpenAIClient(api_key=os.environ['OPENAI_API_KEY'])
os.environ['SSL_CERT_FILE'] = certifi.where()
MONGODB_CONNECTION_STRING = os.environ.get('MONGODB_CONNECTION_STRING')

# Function to connect to MongoDB and return a collection
def connect_mongodb(col):
    client = pymongo.MongoClient(MONGODB_CONNECTION_STRING)
    db = client["demo_RAG_PDF"]
    return db[col]

def get_embedding(text, model="text-embedding-ada-002"):
    text = text.replace("\n", " ")
    response = clientOpenAI.embeddings.create(input=[text], model=model)
    embedding = response['choices'][0]['embedding'] if isinstance(response, dict) else response.data[0].embedding
    return embedding

# Function to process PDFs in a directory
def process_pdf_directory(directory_path):
    data = []
    files = os.listdir(directory_path)
    total_files = len(files)
    progress_bar = st.progress(0)
    status_placeholder = st.empty()

    for idx, filename in enumerate(files):
        if filename.endswith(".pdf"):
            status_placeholder.text(f"Processing file {filename} ({idx+1}/{total_files})...")
            pdf_path = os.path.join(directory_path, filename)
            with open(pdf_path, "rb") as f:
                pdf_reader = PdfReader(f)
                for page_number, page in enumerate(pdf_reader.pages, start=1):
                    data.append({
                        "text": page.extract_text(),
                        "filename": filename,
                        "page_number": page_number
                    })
            progress_bar.progress((idx+1)/total_files)

    status_placeholder.text("All files processed!")
    return data

# Function to store text embeddings in MongoDB
def store_text_embeddings(data):
    collection = connect_mongodb(col="patientGuides")
    text_splitter = CharacterTextSplitter(
        separator="\n",
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )

    total_chunks = len(data)
    progress_bar = st.progress(0)
    status_placeholder = st.empty()

    for idx, entry in enumerate(data):
        chunks = text_splitter.split_text(entry['text'])
        for chunk in chunks:
            embedding = get_embedding(chunk)
            document = {
                "text_chunk": chunk,
                "vector_embedding": embedding,
                "source": {
                    "filename": entry['filename'],
                    "page_number": entry['page_number']
                }
            }
            collection.insert_one(document)
        
        progress_bar.progress((idx+1)/total_chunks)
        status_placeholder.text(f"Storing chunks from {entry['filename']} ({idx+1}/{total_chunks}) in MongoDB...")

    status_placeholder.text("All text chunks stored in MongoDB!")

# Function to find similar documents based on embeddings
def find_similar_documents(embedding, k):
    print("Searching for similar documents in patientGuides...")
    collection = connect_mongodb(col="patientGuides")
    documents = list(collection.aggregate([{
        "$vectorSearch": {
            "index": "default",
            "path": "vector_embedding",
            "queryVector": embedding, 
            "numCandidates": 200, 
            "limit": k
        }
    }]))

    print(f"Found {len(documents)} similar documents in patientGuides.")
    
    return documents

# Function to answer user's question
def answer_question(user_question):
    print(f"Received question: {user_question}")
    llm = OpenAI(model="gpt-3.5-turbo-instruct", temperature=0.5)

    context = ""
    context_sources = []

    question_embedding = get_embedding(text=user_question)   
    documents = find_similar_documents(question_embedding, 10)
    df = pd.DataFrame(documents)
    for index, row in df[0:50].iterrows():
        context = context + " " + row.text_chunk
        context_sources.append(f"{row.get('source', {}).get('filename', 'Unknown Source')} - Page {row.get('source', {}).get('page_number', 'Unknown Page')}")

    template = """
    You are a chat bot who loves to help people! Given the following context sections, answer the
    question using only the given context. If you are unsure and the answer is not
    explicitly written in the documentation, say "Sorry, I don't know how to help with that."

    Context sections:
    {context}

    Question:
    {user_question}

    Answer:
    """

    prompt = PromptTemplate(template=template, input_variables=[
                            "context", "user_question"])

    prompt_text = prompt.format(context=context, user_question=user_question)

    response = llm(prompt_text)

    return response, context_sources

def main():
    query = ""
    st.title("Ask questions to Leafy Hospital 💬")
    
    st.header("1. Load Documents")
    dir_path = st.text_input("Enter the directory path containing PDFs:")
    if dir_path:
        combined_text = process_pdf_directory(dir_path)
        if combined_text:
            store_text_embeddings(combined_text)
            st.success("Documents loaded and embeddings stored!")
        else:
            st.warning("No text was extracted from the PDFs. Check the directory and files.")

    st.header("2. Ask Questions")
    
    query = st.text_input('Enter your question:')

    if query:
        response_text, context_sources = answer_question(query)
        styled_response = f"""
            <div style="background-color: #e6ffe6; padding: 10px; border-radius: 5px;">
            {response_text}
            </div>
            """
        st.markdown(styled_response, unsafe_allow_html=True)

        privacy_note = """
            <div style="font-size: 10px; color: grey; padding: 5px; border-top: 1px solid #e6e6e6; margin-top: 10px;">
            Note: this answer is created through Retrieval-Augmented Generation (RAG), using your own data in MongoDB and the LLM model text-embedding-ada-002.
            </div>
            """
        st.markdown(privacy_note, unsafe_allow_html=True)

        st.header("Provenance")

        provenance_sources = []
        provenance_sources.extend(context_sources)

        df = pd.DataFrame({'Provenance': provenance_sources})
        st.write(df.style.set_properties(**{'font-size': '10pt'}))

if __name__ == "__main__":
    main()
