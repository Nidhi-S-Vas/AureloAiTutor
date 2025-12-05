# rag.py
import os
import chromadb

CHROMA_DIR = os.getenv("CHROMA_PERSIST_DIR") or "./chroma_store"

client = chromadb.PersistentClient(path=CHROMA_DIR)

COLLECTION_NAME = "project_tutor_chunks"

# Create or load collection
try:
    collection = client.get_collection(COLLECTION_NAME)
except Exception:
    collection = client.create_collection(
        COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}  # cosine similarity
    )


def add_chunks_to_chroma(doc_id, chunk_ids, texts, embeddings, metadatas):
    """
    Add chunk embeddings to global Chroma collection.
    metadata contains {doc_id, chunk_id, start, end}
    """
    assert len(chunk_ids) == len(texts) == len(embeddings) == len(metadatas)

    # IDs must be globally unique → doc_id__chunk_id
    ids = [f"{doc_id}__{cid}" for cid in chunk_ids]

    # Force doc_id to be present in metadata
    for m, cid in zip(metadatas, chunk_ids):
        m["doc_id"] = doc_id
        m["chunk_id"] = cid

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas
    )


def query_similar_chunks(query_emb, doc_id=None, n_results=4):
    """
    Returns top matching chunks.
    If doc_id is provided, restrict retrieval to that document only.
    """

    if doc_id:
        # Use metadata filter to get only chunks of this PDF
        res = collection.query(
            query_embeddings=[query_emb],
            n_results=n_results,
            where={"doc_id": doc_id}
        )
    else:
        # No filtering (not recommended)
        res = collection.query(
            query_embeddings=[query_emb],
            n_results=n_results
        )

    ids = res.get("ids", [[]])[0]
    docs = res.get("documents", [[]])[0]
    metas = res.get("metadatas", [[]])[0]

    results = []
    for i in range(len(ids)):
        results.append({
            "id": ids[i],
            "document": docs[i],
            "metadata": metas[i]
        })

    return results
