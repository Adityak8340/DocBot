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
st.title("Payment Voucher to JSON Converter")

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
        # Define the system prompt with strict attribute order and an example
        system_prompt = (
            "Identify these attributes: account_credited, account_debited, amount, phone_no, email, bill_no, address, date, and note from the document. "
            "Your top priority is only to provide a JSON formatted text with these attributes in this exact sequence. "
            "Make sure that the JSON format is correct. Here is an example response:\n\n"
            "{\n"
            "\"account_credited\": \"HDFC BANK\",\n"
            "\"account_debited\": \"Anjul Industries\",\n"
            "\"amount\": 1432086,\n"
            "\"phone_no\": \"+91-9355992817\",\n"
            "\"email\": \"accounts@wasserfluss.cam\",\n"
            "\"bill_no\": \"WFIBP/23-24/007\",\n"
            "\"address\": \"Plat Na-492, Sector - 68, IkIT, Faridabacl -121004\",\n"
            "\"date\": \"4-Apr-23\",\n"
            "\"note\": \"INR Fourteen Lakh Thirty Two Thousand Eighty Six Only\"\n"
            "}\n"
        )
        
        # Concatenate the system and user prompts
        prompt = f"{system_prompt}\n\nDocument Text: {text_content}\n\nUser Query: {user_prompt}\n\nAnswer:"
        
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

def generate_query(json_data):
    query_template = (
        "{debited} paid INR {amount} to {credited} on {date}. "
        "The bill number is {bill_no} and the amount in words is {amount_in_words}. "
        "The contact details are {phone} and email is {email}. "
        "The address is {address}."
    )
    
    # Safely extract the amount and format it if it's an integer
    amount = json_data.get("amount", 0)
    if isinstance(amount, int):
        amount = f"{amount:,}"
    else:
        amount = str(amount)
    
    query = query_template.format(
        debited=json_data.get("account_debited", "Unknown"),
        amount=amount,
        credited=json_data.get("account_credited", "Unknown"),
        date=json_data.get("date", "Unknown"),
        bill_no=json_data.get("bill_no", "Unknown"),
        amount_in_words=json_data.get("note", "Unknown"),
        phone=json_data.get("phone_no", "Unknown"),
        email=json_data.get("email", "Unknown"),
        address=json_data.get("address", "Unknown")
    )
    return query


progress_bar = st.empty()  # Create an empty placeholder for the progress bar

if uploaded_file:
    file_path = os.path.join("uploads", uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    file_extension = os.path.splitext(uploaded_file.name)[1].lower()

    results = []  # Store both JSON and query

    if file_extension == ".pdf":
        st.write("Processing PDF...")
        
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
                
                if json_response:
                    query = generate_query(json_response)
                    results.append({
                        "query": query,
                        "output": json_response
                    })
                
                # Update progress bar
                progress_bar.progress((i + 1) / total_pages)
        
        st.success("PDF processed successfully.")
        st.json(results)  # Display the JSON and queries

    else:
        st.write("Processing Image...")
        text_content = extract_text_from_image(file_path)
        
        # Check if text_content is empty after OCR
        if not text_content.strip():
            st.error("No text found in the uploaded image.")
        else:
            json_response = generate_response("Extract attributes from the document.", text_content)
            if json_response:
                query = generate_query(json_response)
                results.append({
                    "query": query,
                    "output": json_response
                })
            st.json(results)  # Display the JSON and query

    # Add download button for the dataset
    if results:
        dataset_str = json.dumps(results, indent=4)
        st.download_button(
            label="Download Dataset",
            data=dataset_str,
            file_name="document_data.json",
            mime="application/json"
        )

# Clean up temp images
def cleanup_temp_images(output_folder="temp_images"):
    if os.path.exists(output_folder):
        for file in os.listdir(output_folder):
            file_path = os.path.join(output_folder, file)
            if os.path.isfile(file_path):
                os.unlink(file_path)

cleanup_temp_images()
