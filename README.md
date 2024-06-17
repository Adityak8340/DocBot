# 🤖 DocBot: Smart Document ChatBot

[streamlit-app-2024-06-11-16-06-53.webm](https://github.com/Adityak8340/DocBot/assets/140245948/76d76b92-ad7b-4f85-86df-ecc355a6c6ae)

DocBot is an intelligent document processing application with a chatbot interface. It can process various types of documents, including PDFs and images, extract essential information, and enable user interaction through a chat interface.

## ⭐️ Features

- **Document Upload**: Upload PDF, PNG, JPG, or JPEG files for processing.
- **Text Extraction**: Extract text content from uploaded documents.
- **Image Processing**: Convert PDF documents to images and extract text from images.
- **Chatbot Interface**: Interact with the document through a chatbot interface powered by Groq.
- **Natural Language Understanding**: Utilizes spaCy for natural language processing.
- **Dynamic Progress Bar**: Visual feedback on document processing progress.
- **Error Handling**: Provides error messages for any processing failures.

## ⚙️ Installation

1. Clone the repository:

    ```bash
    git clone https://github.com/yourusername/docbot.git
    ```

2. Install the required Python packages:

    ```bash
    pip install -r requirements.txt
    ```

3. Set up the environment variables:

    Create a `.env` file in the root directory and add the following:

    ```dotenv
    GROQ_API_KEY='your_groq_api_key'
    ```

4. Run the Streamlit app:

    ```bash
    streamlit run app.py
    ```

## 🚀 Usage

1. Run the Streamlit app using the provided installation instructions.
2. Upload your document using the file uploader.
3. Wait for the document to be processed.
4. Interact with the document by asking questions in the chatbot interface.

## 💻 Technologies Used

- [Streamlit](https://streamlit.io/) - For building the interactive web application.
- [PyPDF2](https://pythonhosted.org/PyPDF2/) - For PDF document processing.
- [pdf2image](https://github.com/Belval/pdf2image) - For converting PDFs to images.
- [PyMuPDF](https://pypi.org/project/PyMuPDF/) - For PDF document rendering.
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) - For extracting text from images.
- [spaCy](https://spacy.io/) - For natural language processing.
- [Groq](https://github.com/groq/groq-py) - For AI-powered chatbot interaction.
- [Pillow](https://python-pillow.org/) - For image processing.
