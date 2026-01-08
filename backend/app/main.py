from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
import tempfile
import os

from backend.app.services.ingestion import load_and_chunk_pdf

app = FastAPI(title="RAG Knowledge Base API")

class ChatRequest(BaseModel):
    query: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat")
def chat(req: ChatRequest):
    return {"answer": "Mock answer"}


@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        chunks = load_and_chunk_pdf(tmp_path)

        return {
            "filename": file.filename,
            "num_chunks": len(chunks),
            "sample_chunk": chunks[0].page_content[:300]
        }
    finally:
        os.remove(tmp_path)