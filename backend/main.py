from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import tempfile
import uuid
import logging
from datetime import datetime
import fitz  # PyMuPDF
import json
from typing import List

from database import documents_collection
from gemini_client import call_llm_once, get_embeddings
from rag import add_chunks_to_chroma, query_similar_chunks

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backend")

app = FastAPI(title="ProjectTutor API (RAG-first)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------
# PDF extract & chunk helpers
# ---------------------------
def extract_text_pages_from_pdf(path: str) -> List[str]:
    doc = fitz.open(path)
    return [(doc[p].get_text("text") or "") for p in range(len(doc))]


def chunk_text_from_pages(pages: List[str], chunk_size=1000, overlap=200):
    text = "\n\n".join(pages)
    L = len(text)
    chunks, start, cid = [], 0, 0

    while start < L:
        end = start + chunk_size
        part = text[start:end]

        if end < L:
            back = max(part.rfind("\n"), part.rfind(" "), part.rfind("."))
            if back > int(chunk_size * 0.3):
                end = start + back + 1
                part = text[start:end]

        part = part.strip()
        if part:
            chunks.append(
                {
                    "id": str(cid),
                    "text": part,
                    "start": start,
                    "end": min(end, L),
                }
            )
            cid += 1

        start = max(0, end - overlap)
        if end >= L:
            break

    return chunks


# ---------------------------
# Prompt templates (ESCAPED)
# ---------------------------

# SUMMARY: detailed but simple, length based on pages_count
SUMMARY_PROMPT = """
You MUST return ONLY valid JSON. No extra commentary.

{{
  "summary": ""
}}

Rules:
- Use ONLY the text in "Context" (do NOT add external facts).
- Write in very simple English for students.
- Be detailed and cover all important ideas. Do NOT make it too short.
- If pages_count <= 3: write 1–2 paragraphs (4–6 sentences each).
- If 4 <= pages_count <= 10: write 3–4 paragraphs.
- If pages_count > 10: write 4–6 paragraphs that cover all major headings/topics.

Context:
{context}

PagesCount: {pages_count}
"""

# NOTES: heading-wise sections, each with explanation + bullet points
NOTES_PROMPT = """
You MUST return ONLY valid JSON. No extra commentary.

The JSON MUST have exactly this shape:

{{
  "sections": [
    {{
      "heading": "",
      "explanation": "",
      "points": []
    }}
  ],
  "keywords": []
}}

Rules:
- Use ONLY the text in "Context" (do NOT add external facts).
- Identify the main headings or topics from the document (like "Steps to Implement ANN", "Recurrent Neural Networks", etc.).
- For each important heading, create ONE section.
- "heading": a short title.
- "explanation": 3–6 sentence paragraph explaining that heading in very simple language.
- "points": 4–8 bullet points for that heading (definitions, steps, formulas, key ideas).
- Try to cover all important parts of the document. Do NOT make the notes too small.
- Write everything so that a beginner can understand.

Context:
{context}

PagesCount: {pages_count}
"""

MCQ_PROMPT = """
Return ONLY a JSON array of MCQs. NO extra text.

[
  {{
    "id": "",
    "question": "",
    "options": ["", "", "", ""],
    "answer": "",
    "explanation": ""
  }}
]

Rules:
- Generate EXACTLY {num} MCQs.
- Difficulty: {difficulty}.
- Use ONLY the given Context (do not add outside facts).
- Each question must have 4 options, one correct.
- Keep questions short and clear.

Context:
{context}
"""

FILLUPS_PROMPT = """
Return ONLY a JSON array of fill-ups. NO extra text.

[
  {{
    "id": "",
    "text": "",
    "answer": ""
  }}
]

Rules:
- Generate EXACTLY {num} fill-ups.
- Difficulty: {difficulty}.
- Each text must contain exactly ONE blank shown as "____".
- Answer should be a short word or phrase.
- Use ONLY the given Context.

Context:
{context}
"""

CHAT_PROMPT = """
Use ONLY this context to answer. If the answer is not present, reply exactly:
"I could not find the answer in the document."

Context:
{context}

Question:
{question}
"""


# ---------------------------
# JSON extraction helper
# ---------------------------
def extract_json_from_text(raw: str):
    import re

    if not raw:
        return None

    # try object
    m = re.search(r"(\{[\s\S]*\})", raw)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass

    # try array
    m = re.search(r"(\[[\s\S]*\])", raw)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass

    # last fallback
    try:
        return json.loads(raw)
    except Exception:
        return None


# ---------------------------
# UPLOAD (RAG only)
# ---------------------------
@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files allowed.")

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    save_path = tmp.name
    tmp.write(await file.read())
    tmp.close()

    try:
        pages = extract_text_pages_from_pdf(save_path)
        if not pages or all(not p.strip() for p in pages):
            raise HTTPException(400, "PDF contains no readable text.")

        pages_count = len(pages)
        chunks = chunk_text_from_pages(pages, 1000, 200)
        if not chunks:
            raise HTTPException(400, "No substantial text after chunking.")

        texts = [c["text"] for c in chunks]
        ids = [c["id"] for c in chunks]

        embeddings = None
        try:
            embeddings = get_embeddings(texts)
            if not embeddings or len(embeddings) != len(texts):
                logger.warning("Embeddings length mismatch; disabling embeddings.")
                embeddings = None
        except Exception as ex:
            logger.warning(f"Embedding generation failed: {ex}")
            embeddings = None

        metadatas = [
            {"doc_filename": file.filename, "start": c["start"], "end": c["end"]}
            for c in chunks
        ]

        doc_id = str(uuid.uuid4())
        chroma_indexed = False

        if embeddings:
            add_chunks_to_chroma(doc_id, ids, texts, embeddings, metadatas)
            chroma_indexed = True

        documents_collection.insert_one(
            {
                "doc_id": doc_id,
                "filename": file.filename,
                "pages_count": pages_count,
                "chroma_indexed": chroma_indexed,
                "chunks_text": chunks,
                "llm_output": {},
                "created_at": datetime.utcnow(),
            }
        )

        logger.info(
            f"Uploaded {file.filename} → doc_id={doc_id} "
            f"(chunks={len(chunks)}, chroma_indexed={chroma_indexed})"
        )

        return {"status": "ok", "doc_id": doc_id, "chroma_indexed": chroma_indexed}

    finally:
        try:
            os.unlink(save_path)
        except Exception:
            pass


# ---------------------------
# SUMMARY (POST → JSON body)
# ---------------------------
@app.post("/summary")
def generate_summary(payload: dict):
    doc_id = payload.get("doc_id")
    if not doc_id:
        raise HTTPException(400, "doc_id missing")

    doc = documents_collection.find_one({"doc_id": doc_id})
    if not doc:
        raise HTTPException(404, "Document not found")

    pages_count = doc.get("pages_count", 0)
    # use more chunks for bigger docs
    top_k = 8 if pages_count <= 8 else 12

    q_emb = get_embeddings([f"summary of {doc['filename']}"])[0]
    hits = query_similar_chunks(q_emb, doc_id, n_results=top_k)
    if not hits:
        raise HTTPException(400, "No relevant chunks found for summary.")

    chunks = [h["document"] for h in hits]
    context = "\n---\n".join(chunks)
    prompt = SUMMARY_PROMPT.format(context=context, pages_count=pages_count)

    raw = call_llm_once(prompt)
    parsed = extract_json_from_text(raw)

    if not parsed or "summary" not in parsed:
        # fallback simple behaviour
        fallback_text = " ".join(chunks[:3])
        parsed = {"summary": fallback_text}

    llm_out = doc.get("llm_output", {})
    llm_out["summary"] = parsed.get("summary", "")

    documents_collection.update_one(
        {"doc_id": doc_id},
        {"$set": {"llm_output": llm_out}},
    )
    return {"summary": llm_out["summary"]}


# ---------------------------
# NOTES (heading-wise, POST → JSON body)
# ---------------------------
@app.post("/notes")
def generate_notes(payload: dict):
    doc_id = payload.get("doc_id")
    if not doc_id:
        raise HTTPException(400, "doc_id missing")

    doc = documents_collection.find_one({"doc_id": doc_id})
    if not doc:
        raise HTTPException(404, "Document not found")

    pages_count = doc.get("pages_count", 0)
    top_k = 10 if pages_count <= 10 else 14

    q_emb = get_embeddings([f"detailed notes for {doc['filename']}"])[0]
    hits = query_similar_chunks(q_emb, doc_id, n_results=top_k)
    if not hits:
        raise HTTPException(400, "No relevant chunks found for notes.")

    chunks = [h["document"] for h in hits]
    context = "\n---\n".join(chunks)
    prompt = NOTES_PROMPT.format(context=context, pages_count=pages_count)

    raw = call_llm_once(prompt)
    parsed = extract_json_from_text(raw)

    if (
        not parsed
        or not isinstance(parsed, dict)
        or "sections" not in parsed
        or not isinstance(parsed["sections"], list)
    ):
        # fallback: one generic section
        fallback_section = {
            "heading": "Main Ideas",
            "explanation": " ".join(chunks[:2]),
            "points": chunks[:5],
        }
        parsed = {
            "sections": [fallback_section],
            "keywords": [],
        }

    llm_out = doc.get("llm_output", {})
    llm_out["notes"] = parsed
    # keep keywords also at root if you want later usage
    llm_out["keywords"] = parsed.get("keywords", [])

    documents_collection.update_one(
        {"doc_id": doc_id},
        {"$set": {"llm_output": llm_out}},
    )
    return parsed


# ---------------------------
# MCQ GENERATION
# ---------------------------
@app.post("/mcq")
def generate_mcq(payload: dict):
    doc_id = payload.get("doc_id")
    if not doc_id:
        raise HTTPException(400, "doc_id missing")

    difficulty = payload.get("difficulty", "easy")
    num_raw = payload.get("num", 10)

    try:
        num = int(num_raw)
    except Exception:
        num = 10
    num = max(5, min(20, num))  # clamp 5–20

    doc = documents_collection.find_one({"doc_id": doc_id})
    if not doc:
        raise HTTPException(404, "Document not found")

    q_emb = get_embeddings([f"important topics from {doc['filename']}"])[0]
    hits = query_similar_chunks(q_emb, doc_id, n_results=10)

    if not hits:
        raise HTTPException(400, "No relevant chunks found for MCQ generation.")

    context = "\n---\n".join([h["document"] for h in hits])
    prompt = MCQ_PROMPT.format(context=context, difficulty=difficulty, num=num)

    raw = call_llm_once(prompt)
    parsed = extract_json_from_text(raw)
    if not parsed or not isinstance(parsed, list):
        parsed = []

    # Normalize & enforce IDs and progress fields
    normalized = []
    for idx, q in enumerate(parsed[:num]):
        if not isinstance(q, dict):
            continue
        nq = {
            "id": q.get("id") or f"{difficulty}_{idx+1}",
            "question": q.get("question", ""),
            "options": (q.get("options") or [])[:4],
            "answer": q.get("answer", ""),
            "explanation": q.get("explanation", ""),
            "user_answer": "",
            "result": "",
        }
        normalized.append(nq)

    llm = doc.get("llm_output", {})
    if "mcq" not in llm:
        llm["mcq"] = {}
    llm["mcq"][difficulty] = normalized

    documents_collection.update_one(
        {"doc_id": doc_id},
        {"$set": {"llm_output": llm}},
    )
    return {"difficulty": difficulty, "count": len(normalized)}


# ---------------------------
# MCQ PROGRESS SAVE
# ---------------------------
@app.post("/mcq/save-progress")
def save_mcq_progress(payload: dict):
    doc_id = payload.get("doc_id")
    difficulty = payload.get("difficulty")
    batch_ids = payload.get("batch_ids", [])
    answers = payload.get("answers", {})

    if not doc_id or not difficulty:
        raise HTTPException(400, "doc_id and difficulty are required.")

    doc = documents_collection.find_one({"doc_id": doc_id})
    if not doc:
        raise HTTPException(404, "Document not found")

    llm = doc.get("llm_output", {})
    mcq_data = llm.get("mcq", {})
    questions = mcq_data.get(difficulty, [])

    if not questions:
        raise HTTPException(400, "No MCQs found for this difficulty.")

    batch_set = set(batch_ids or [])
    ans_map = answers or {}

    for q in questions:
        qid = q.get("id")
        if not qid or qid not in batch_set:
            continue

        user = (ans_map.get(qid) or "").strip()
        correct = str(q.get("answer", "")).strip()

        if not user:
            q["user_answer"] = ""
            q["result"] = "not answered"
        else:
            q["user_answer"] = user
            q["result"] = "correct" if user == correct else "wrong"

    mcq_data[difficulty] = questions
    llm["mcq"] = mcq_data
    llm.setdefault("mcq_last_updated", datetime.utcnow().isoformat())

    documents_collection.update_one(
        {"doc_id": doc_id},
        {"$set": {"llm_output": llm}},
    )
    return {"status": "ok"}


# ---------------------------
# FILLUPS GENERATION
# ---------------------------
@app.post("/fillups")
def generate_fillups(payload: dict):
    doc_id = payload.get("doc_id")
    if not doc_id:
        raise HTTPException(400, "doc_id missing")

    difficulty = payload.get("difficulty", "easy")
    num_raw = payload.get("num", 10)

    try:
        num = int(num_raw)
    except Exception:
        num = 10
    num = max(5, min(20, num))  # clamp 5–20

    doc = documents_collection.find_one({"doc_id": doc_id})
    if not doc:
        raise HTTPException(404, "Document not found")

    q_emb = get_embeddings([f"key terms from {doc['filename']}"])[0]
    hits = query_similar_chunks(q_emb, doc_id, n_results=10)

    if not hits:
        raise HTTPException(400, "No relevant chunks found for fillups generation.")

    context = "\n---\n".join([h["document"] for h in hits])
    prompt = FILLUPS_PROMPT.format(context=context, difficulty=difficulty, num=num)

    raw = call_llm_once(prompt)
    parsed = extract_json_from_text(raw)
    if not parsed or not isinstance(parsed, list):
        parsed = []

    normalized = []
    for idx, q in enumerate(parsed[:num]):
        if not isinstance(q, dict):
            continue
        nq = {
            "id": q.get("id") or f"{difficulty}_{idx+1}",
            "text": q.get("text", ""),
            "answer": q.get("answer", ""),
            "user_answer": "",
            "result": "",
        }
        normalized.append(nq)

    llm = doc.get("llm_output", {})
    if "fillups" not in llm:
        llm["fillups"] = {}
    llm["fillups"][difficulty] = normalized

    documents_collection.update_one(
        {"doc_id": doc_id},
        {"$set": {"llm_output": llm}},
    )
    return {"difficulty": difficulty, "count": len(normalized)}


# ---------------------------
# FILLUPS PROGRESS SAVE
# ---------------------------
@app.post("/fillups/save-progress")
def save_fillups_progress(payload: dict):
    doc_id = payload.get("doc_id")
    difficulty = payload.get("difficulty")
    batch_ids = payload.get("batch_ids", [])
    answers = payload.get("answers", {})

    if not doc_id or not difficulty:
        raise HTTPException(400, "doc_id and difficulty are required.")

    doc = documents_collection.find_one({"doc_id": doc_id})
    if not doc:
        raise HTTPException(404, "Document not found")

    llm = doc.get("llm_output", {})
    fill_data = llm.get("fillups", {})
    questions = fill_data.get(difficulty, [])

    if not questions:
        raise HTTPException(400, "No fillups found for this difficulty.")

    batch_set = set(batch_ids or [])
    ans_map = answers or {}

    for q in questions:
        qid = q.get("id")
        if not qid or qid not in batch_set:
            continue

        user = (ans_map.get(qid) or "").strip().lower()
        correct = str(q.get("answer", "")).strip().lower()

        if not user:
            q["user_answer"] = ""
            q["result"] = "not answered"
        else:
            q["user_answer"] = user
            q["result"] = "correct" if user == correct else "wrong"

    fill_data[difficulty] = questions
    llm["fillups"] = fill_data
    llm.setdefault("fillups_last_updated", datetime.utcnow().isoformat())

    documents_collection.update_one(
        {"doc_id": doc_id},
        {"$set": {"llm_output": llm}},
    )
    return {"status": "ok"}


# ---------------------------
# CHAT (RAG → LLM)
# ---------------------------
@app.post("/chat")
def chat(payload: dict):
    doc_id = payload.get("doc_id")
    question = payload.get("question")

    if not doc_id or not question:
        raise HTTPException(400, "doc_id and question are required.")

    doc = documents_collection.find_one({"doc_id": doc_id})
    if not doc:
        raise HTTPException(404, "Document not found")

    q_emb = get_embeddings([question])[0]
    hits = query_similar_chunks(q_emb, doc_id, n_results=4)

    if not hits:
        return {"answer": "I could not find relevant information in the document."}

    context = "\n---\n".join(h["document"] for h in hits)
    prompt = CHAT_PROMPT.format(context=context, question=question)

    return {"answer": call_llm_once(prompt)}


# ---------------------------
# GETTERS
# ---------------------------
@app.get("/docs/{id}/summary")
def get_summary(id: str):
    d = documents_collection.find_one(
        {"doc_id": id}, {"_id": 0, "llm_output.summary": 1}
    )
    return {"summary": d.get("llm_output", {}).get("summary", "") if d else ""}


@app.get("/docs/{id}/notes")
def get_notes(id: str):
    d = documents_collection.find_one(
        {"doc_id": id}, {"_id": 0, "llm_output.notes": 1}
    )
    return {"notes": d.get("llm_output", {}).get("notes", {}) if d else {}}


@app.get("/docs/{id}/mcq")
def get_mcq(id: str):
    d = documents_collection.find_one(
        {"doc_id": id}, {"_id": 0, "llm_output.mcq": 1}
    )
    return d.get("llm_output", {}).get("mcq", {}) if d else {}


@app.get("/docs/{id}/fillups")
def get_fillups(id: str):
    d = documents_collection.find_one(
        {"doc_id": id}, {"_id": 0, "llm_output.fillups": 1}
    )
    return d.get("llm_output", {}).get("fillups", {}) if d else {}
