# Aurelo AI Tutor

Aurelo AI Tutor is an AI-based learning tool that allows users to upload a PDF and receive summaries, MCQs, explanations, and answers to questions.  
The project uses a simple custom **Retrieval-Augmented Generation (RAG)** approach.  
The system extracts text from the PDF, stores embeddings in **ChromaDB**, and uses the **Gemini API** to generate responses based only on the document.  
This project **does not use LangChain**.

## What This Project Uses

### Frontend
- React (Create React App)
- JavaScript
- Axios for API calls

### Backend
- FastAPI
- Python
- PyMuPDF (PDF text extraction)
- ChromaDB (embedding storage + retrieval)
- Google Gemini API
- HuggingFace embedding model
- Manual RAG workflow (**not LangChain**)

## Project Structure (Simple View)

The main project folder contains:

### backend
- FastAPI code  
- Gemini client  
- ChromaDB database setup  
- RAG logic (manual implementation)  
- requirements.txt  
- `.env` file (not uploaded to GitHub)

### frontend
- React application created using Create React App  
- Run using `npm start`

### Other
- `.gitignore` ensures `.env`, `.venv`, `node_modules`, and `__pycache__` are not uploaded

## Backend Setup (Simple Steps)

1. Go to the backend folder  
2. Create a virtual environment and activate it  
3. Install required packages (from `requirements.txt`)  
4. Create a `.env` file inside backend and add your Gemini API key  
5. Run the backend using:


Backend runs at: **http://127.0.0.1:8000**

## Frontend Setup (Simple Steps)

1. Go to the frontend folder  
2. Install dependencies using:  
3. Start React using:  

Frontend runs at: **http://localhost:3000**

## How the System Works (Simple Explanation)

1. User uploads a PDF  
2. Backend extracts text using PyMuPDF  
3. Text is split into chunks  
4. Chunks are converted into embeddings  
5. Embeddings are stored in ChromaDB  
6. When a question is asked:  
   - Relevant chunks are retrieved  
   - Sent to Gemini along with the question  
   - Gemini generates an answer using ONLY the retrieved context  

## Notes

- `.env` must be created inside the backend folder  
- `.env`, `.venv`, `node_modules`, and `__pycache__` are excluded from GitHub  
- React is run using `npm start` (not Vite)  
- **LangChain is NOT used**  
- Entire AI logic is based on **Gemini + RAG + ChromaDB**
