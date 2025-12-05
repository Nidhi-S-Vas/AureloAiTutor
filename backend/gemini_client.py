# gemini_client.py
import os
import time
import google.generativeai as genai

LLM_MODEL = "gemini-2.5-flash"
EMBED_MODEL = "text-embedding-004"

def configure():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set in environment")
    genai.configure(api_key=api_key)

def call_llm_once(prompt: str, max_retries: int = 2) -> str:
    configure()
    model = genai.GenerativeModel(LLM_MODEL)
    for attempt in range(1, max_retries + 1):
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception:
            if attempt == max_retries:
                raise
            time.sleep(1 + attempt)

def embed_single(text):
    """
    Embed one text safely.
    Always returns 1536-dim vector for text-embedding-004
    """
    result = genai.embed_content(
        model=EMBED_MODEL,
        content=text,
    )
    # Always single embedding
    return result["embedding"]

def get_embeddings(texts, max_retries: int = 2):
    """
    Embed a LIST of texts.
    Proper batching (one-by-one) so all vectors match.
    Returns list of vectors of equal dimension.
    """
    configure()

    if isinstance(texts, str):
        texts = [texts]

    embeddings = []

    for t in texts:
        for attempt in range(1, max_retries + 1):
            try:
                emb = embed_single(t)
                embeddings.append(emb)
                break
            except Exception:
                if attempt == max_retries:
                    raise
                time.sleep(1 + attempt)

    return embeddings
