import streamlit as st
from PyPDF2 import PdfReader
from pdf2image import convert_from_path
from PIL import Image
import pytesseract
import fitz  # PyMuPDF
import spacy
import os
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

# Streamlit app
st.title("DocBot: Smart Document ChatBot")

uploaded_file = st.file_uploader("Upload your file", type=["pdf", "png", "jpg", "jpeg"])

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

def generate_response(user_prompt):
    try:
        # Define the system prompt
        system_prompt = "You are a helpful assistant, your name is DocBot, you help with document text"
        chatbot_symbol = "🤖" 
        
        # Concatenate the system and user prompts
        prompt = f"{system_prompt}\n\nUser Query: {user_prompt}\n\nAnswer:"
        
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
        
        # Add the chatbot symbol to the response
        chatbot_response_with_symbol = f"{chatbot_symbol} {chatbot_response}"
        
        # Return the response
        return chatbot_response_with_symbol
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
        # Check if PDF contains text or images
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

    st.subheader("Chat with your document")
    user_query = st.text_input("Ask a question about your document")

    if user_query:
        prompt = f"Document Text: {text_content}\n\nUser Query: {user_query}\n\nAnswer:"
        response = generate_response(prompt)
        st.write("Response: ", response)

# Clean up temp images
def cleanup_temp_images(output_folder="temp_images"):
    if os.path.exists(output_folder):
        for file in os.listdir(output_folder):
            file_path = os.path.join(output_folder, file)
            if os.path.isfile(file_path):
                os.unlink(file_path)

cleanup_temp_images()
