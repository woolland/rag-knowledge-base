# backend/app/main.py

from fastapi import FastAPI, UploadFile, File
import tempfile
import os

from app.services.ingestion import load_and_chunk_pdf
from app.services.vector_store import build_faiss_index, search_top_k
from app.services.gemini_llm import generate_answer_gemini
from app.services.prompting import build_context

app = FastAPI(title="RAG Knowledge Base API")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """
    Upload a PDF and return chunking preview.
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        chunks = load_and_chunk_pdf(tmp_path)
        return {
            "filename": file.filename,
            "num_chunks": len(chunks),
            "sample_chunk": chunks[0].page_content[:300] if chunks else ""
        }
    finally:
        os.remove(tmp_path)


@app.post("/index-and-search")
async def index_and_search(file: UploadFile = File(...), query: str = "What is the main topic?"):
    """
    Upload a PDF, build a FAISS index, then run semantic search.
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        chunks = load_and_chunk_pdf(tmp_path)
        vector_store = build_faiss_index(chunks)
        results = search_top_k(vector_store, query=query, k=3)

        return {
            "filename": file.filename,
            "query": query,
            "num_chunks": len(chunks),
            "top_k": 3,
            "results_preview": [
                {
                    "content_preview": r.page_content[:200],
                    "metadata": r.metadata
                }
                for r in results
            ]
        }
    finally:
        os.remove(tmp_path)

@app.post("/ask")
async def ask(file: UploadFile = File(...), query: str = "What is the main topic?"):
    """
    Day5 goal: Retrieval
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        chunks = load_and_chunk_pdf(tmp_path)
        vector_store = build_faiss_index(chunks)

        top_k = 3
        results = search_top_k(vector_store, query=query, k=top_k)

        #context = build_context(results)
        context = build_context(results)
        answer = generate_answer_gemini(query=query, context=context)

        return {
            "filename": file.filename,
            "query": query,
            "num_chunks": len(chunks),
            "top_k": top_k,
            "answer": answer,
            "context_preview": context[:600],
            "sources": [
                {
                    "content_preview": r.page_content[:200],
                    "metadata": r.metadata,
                }
                for r in results
            ],
        }
    finally:
        os.remove(tmp_path)
