**Aurelo AI Tutor**

Aurelo AI Tutor is an AI-based learning tool that allows users to upload a PDF and receive summaries, MCQs, explanations, and answers to questions.
The project uses a simple custom Retrieval-Augmented Generation (RAG) approach.
The system extracts text from the PDF, stores embeddings in ChromaDB, and uses the Gemini API to generate responses based only on the document.
This project does not use LangChain.

What This Project Uses
Frontend

React (Create React App)

JavaScript

Axios for API calls

Backend

FastAPI

Python

PyMuPDF (PDF text extraction)

ChromaDB (embedding storage + retrieval)

Google Gemini API

HuggingFace embedding model

Manual RAG workflow (not LangChain)

Project Structure (Simple View)

The main project folder contains:

backend

FastAPI code

Gemini client

ChromaDB database setup

RAG logic (manual implementation)

requirements.txt

.env file (not uploaded to GitHub)

frontend

React application created using Create React App

Run using npm start

Other

.gitignore ensures .env, .venv, node_modules, and __pycache__ are not uploaded

Backend Setup (Simple Steps)

Go to the backend folder

Create a virtual environment and activate it

Install required packages (from requirements.txt)

Create a .env file inside backend and add your Gemini API key

Run the backend using uvicorn

Backend runs at:
http://127.0.0.1:8000

Frontend Setup (Simple Steps)

Go to the frontend folder

Install dependencies using npm install

Start React using npm start

Frontend runs at:
http://localhost:3000

How the System Works (Simple Explanation)

User uploads a PDF

Backend extracts text using PyMuPDF

Text is split into chunks

Chunks are converted into embeddings

Embeddings are stored in ChromaDB

When a question is asked:

Relevant chunks are retrieved

Sent to Gemini along with the question

Gemini generates an answer using only the retrieved context

Notes

.env must be created inside the backend folder

.env, .venv, node_modules, and __pycache__ are excluded from GitHub

React is run using npm start (not Vite)

LangChain is NOT used

Entire AI logic is based on Gemini + RAG + ChromaDB
