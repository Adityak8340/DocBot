import streamlit as st
from PyPDF2 import PdfReader
from pdf2image import convert_from_path
from PIL import Image
import pytesseract
import os
import numpy as np
import faiss  # Vector database
from sentence_transformers import SentenceTransformer
import spacy
from groq import Groq
import configparser

# Load environment variables from .env file
config = configparser.ConfigParser()
config.read(".env")
api_key = config.get("GROQ", "GROQ_API_KEY")

# Initialize spaCy model
nlp = spacy.load("en_core_web_sm")

# Set up the Groq client
client = Groq(api_key=api_key)

# Initialize the Sentence Transformer model for embeddings
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')  # You can choose a different model if needed

# Streamlit app
st.title("DocBot: Smart Document ChatBot")

uploaded_file = st.file_uploader("Upload your file", type=["pdf", "png", "jpg", "jpeg"])

# Placeholder for text content and vector database
text_content = None
vector_db = None

def convert_pdf_to_images(pdf_path, output_folder="temp_images"):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    pages = convert_from_path(pdf_path, 300)
    image_paths = []
    for i, page in enumerate(pages):
        image_path = os.path.join(output_folder, f'page_{i}.png')
        page.save(image_path, 'PNG')
        image_paths.append(image_path)
    return image_paths

def extract_text_from_pdf(pdf_path):
    text = ""
    with open(pdf_path, "rb") as f:
        reader = PdfReader(f)
        for page in reader.pages:
            text += page.extract_text()
    return text

def extract_text_from_image(image_path):
    return pytesseract.image_to_string(Image.open(image_path))

def split_text_into_chunks(text, chunk_size=512):
    return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

def create_vector_db(chunks):
    embeddings = embedding_model.encode(chunks)
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(np.array(embeddings))
    return {'index': index, 'chunks': chunks}

def retrieve_relevant_chunks(query, vector_db):
    query_embedding = embedding_model.encode([query])
    D, I = vector_db['index'].search(np.array(query_embedding), k=5)  # Retrieve top 5 chunks
    return [vector_db['chunks'][i] for i in I[0]]

def generate_response(system_prompt, user_prompt):
    try:
        # Call the Groq model with the combined prompt
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                }
            ],
            model="llama3-8b-8192",
        )
        
        # Get the chatbot's response
        chatbot_response = chat_completion.choices[0].message.content.strip()
        
        # Return the response
        return chatbot_response
    except Exception as e:
        st.error(f"An error occurred: {e}")
        return "There was an error processing your request."
    
progress_bar = st.empty()  # Create an empty placeholder for the progress bar

if uploaded_file:
    file_path = os.path.join("uploads", uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    file_extension = os.path.splitext(uploaded_file.name)[1].lower()

    if file_extension == ".pdf":
        st.write("Processing PDF...")
        text_content = extract_text_from_pdf(file_path)
        if not text_content.strip():
            st.write("PDF contains images, using OCR...")
            image_paths = convert_pdf_to_images(file_path)
            text_content = ""
            for image_path in image_paths:
                text_content += extract_text_from_image(image_path)
        else:
            progress_bar.progress(100)  # Set progress to 100% if text extraction successful
            st.success("PDF read successfully.")
    else:
        st.write("Processing Image...")
        text_content = extract_text_from_image(file_path)
    
    progress_bar.progress(100)  # Set progress to 100% if text extraction successful

    # Split text into chunks and create a vector database
    chunks = split_text_into_chunks(text_content)
    vector_db = create_vector_db(chunks)

# Check if document is loaded and ready for interaction
if text_content and vector_db:
    st.subheader("Chat with your document")
    user_query = st.text_input("Ask a question about your document")

    if user_query:
        relevant_chunks = retrieve_relevant_chunks(user_query, vector_db)
        context = "\n".join(relevant_chunks)
        system_prompt = "You are a helpful assistant, your name is DocBot, you help with document text"
        response = generate_response(system_prompt, f"Context: {context}\n\nUser Query: {user_query}")
        st.write("Response: ", response)
else:
    st.write("Upload a file to begin processing.")
