# database.py
from dotenv import load_dotenv
load_dotenv()

import os
from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "project_tutor")

client = MongoClient(MONGO_URI)
db = client[MONGO_DB_NAME]

# Documents collection (stores llm_output + metadata)
documents_collection = db["documents"]
