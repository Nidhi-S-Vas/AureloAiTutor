# Aurelo AI Tutor

Aurelo AI Tutor is an AI-based learning tool that allows users to upload a PDF and receive summaries, MCQs, explanations, and answers to questions.  
It uses a simple custom **RAG (Retrieval-Augmented Generation)** approach with **FastAPI**, **React**, **ChromaDB**, and **Gemini API**.  
This project **does not use LangChain**.

## What This Project Uses

### Frontend
- React (Create React App)
- JavaScript
- Axios

### Backend
- FastAPI
- Python
- PyMuPDF
- ChromaDB
- Google Gemini API
- HuggingFace embedding model
- Manual RAG (not LangChain)

## Project Structure (Simple)

- **backend** → FastAPI, Gemini client, ChromaDB, RAG logic, `.env`
- **frontend** → React app (`npm start`)
- `.gitignore` → hides `.env`, `.venv`, `node_modules`, `__pycache__`

## Backend Setup

- Go to backend folder  
- Create and activate virtual environment  
- Install requirements  
- Create `.env` (inside backend) with your Gemini key  
- Run: `uvicorn main:app --reload`

Backend URL: **http://127.0.0.1:8000**

## Frontend Setup

- Go to frontend folder  
- Run `npm install`  
- Run `npm start`

Frontend URL: **http://localhost:3000**

## How It Works

- PDF uploaded → text extracted  
- Text chunked → embeddings created  
- Stored in ChromaDB  
- Query retrieves relevant chunks  
- Gemini responds using retrieved context  

## Notes

- `.env` stays only in backend  
- React uses `npm start`  
- LangChain is NOT used  
