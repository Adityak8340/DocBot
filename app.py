import streamlit as st
from PyPDF2 import PdfReader
from pdf2image import convert_from_path
from PIL import Image
import pytesseract
import spacy
import os
from groq import Groq
import configparser
import json
import re

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

def extract_text_from_pdf_page(pdf_path, page_number):
    with open(pdf_path, "rb") as f:
        reader = PdfReader(f)
        page = reader.pages[page_number]
        text = page.extract_text()
    return text

def extract_text_from_image(image_path):
    return pytesseract.image_to_string(Image.open(image_path))

def extract_json_from_response(response):
    try:
        # Find the JSON part in the response using regex
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            json_str = json_match.group()
            # Clean up the JSON string (remove trailing commas, etc.)
            json_str = re.sub(r',\s*([\}\]])', r'\1', json_str)
            return json.loads(json_str)
        else:
            raise ValueError("JSON not found in the response")
    except json.JSONDecodeError as e:
        st.error(f"JSON decode error: {e}")
        st.write("API response was not in JSON format. Response content:", response)
        return {}
    except Exception as e:
        st.error(f"An error occurred: {e}")
        return {}

def generate_response(user_prompt, text_content):
    try:
        # Define the system prompt with strict attribute order
        system_prompt = (
            "Identify these attributes: account_credited, account_debited, amount, phone_no, email, bill_no, address, date, and note from the document. Your top priority is only to  provide a JSON formatted text with these attributes in this exact sequence. Make sure that json format should be in correct sequence."
        )
        
        # Concatenate the system and user prompts
        prompt = f"{system_prompt}\n\nDocument Text: {text_content}\n\nUser Query: {user_prompt}\n\nAnswer:"
        
        # Log the prompt being sent to the API
    
        
        # Call the Groq model with the combined prompt
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": f"Document Text: {text_content}\n\nUser Query: {user_prompt}"
                }
            ],
            model="llama3-8b-8192",
        )
        
        # Get the chatbot's response
        chatbot_response = chat_completion.choices[0].message.content.strip()
        
        # Log the raw response for debugging
        st.write("Raw API Response:", chatbot_response)
        
        # Extract JSON from response
        json_response = extract_json_from_response(chatbot_response)
        
        # Return the JSON response
        return json_response
    except Exception as e:
        st.error(f"An error occurred: {e}")
        return {}

progress_bar = st.empty()  # Create an empty placeholder for the progress bar

if uploaded_file:
    file_path = os.path.join("uploads", uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    file_extension = os.path.splitext(uploaded_file.name)[1].lower()

    if file_extension == ".pdf":
        st.write("Processing PDF...")
        json_results = []
        
        with open(file_path, "rb") as f:
            reader = PdfReader(f)
            total_pages = len(reader.pages)
            
            for i in range(total_pages):
                text_content = extract_text_from_pdf_page(file_path, i)
                if not text_content.strip():
                    st.write(f"Page {i + 1} contains images, using OCR...")
                    image_path = convert_pdf_to_images(file_path)[i]
                    text_content = extract_text_from_image(image_path)
                
                # Check if text_content is empty after OCR
                if not text_content.strip():
                    st.error(f"No text found on page {i + 1} even after OCR.")
                    continue
                
                # Generate JSON response for each page
                json_response = generate_response("Extract attributes from the document.", text_content)
                json_results.append(json_response)
                
                # Update progress bar
                progress_bar.progress((i + 1) / total_pages)
        
        st.success("PDF processed successfully.")
        st.json(json_results)  # Display the JSON results

        # Add download button for the JSON results
        json_str = json.dumps(json_results, indent=4)
        st.download_button(label="Download JSON", data=json_str, file_name="document_data.json", mime="application/json")
        
    else:
        st.write("Processing Image...")
        text_content = extract_text_from_image(file_path)
        
        # Check if text_content is empty after OCR
        if not text_content.strip():
            st.error("No text found in the uploaded image.")
        else:
            json_response = generate_response("Extract attributes from the document.", text_content)
            st.json([json_response])  # Display the JSON result

            # Add download button for the JSON result
            json_str = json.dumps([json_response], indent=4)
            st.download_button(label="Download JSON", data=json_str, file_name="document_data.json", mime="application/json")

# Clean up temp images
def cleanup_temp_images(output_folder="temp_images"):
    if os.path.exists(output_folder):
        for file in os.listdir(output_folder):
            file_path = os.path.join(output_folder, file)
            if os.path.isfile(file_path):
                os.unlink(file_path)

cleanup_temp_images()
