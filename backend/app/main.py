# backend/app/main.py

from fastapi import FastAPI, UploadFile, File
from fastapi.responses import StreamingResponse
import tempfile
import os

from app.services.ingestion import load_and_chunk_pdf
from app.services.vector_store import build_faiss_index, search_top_k
from app.services.reranker import rerank_docs
from app.services.prompting import build_context_with_citations
from app.services.gemini_llm import generate_answer_gemini, stream_answer_gemini
from sse_starlette.sse import EventSourceResponse
from typing import Any, Dict
import json, traceback, time

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
    Day6: Retrieval + Rerank + Better Citations (non-streaming)
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        chunks = load_and_chunk_pdf(tmp_path)
        vector_store = build_faiss_index(chunks)

        # 1) recall more candidates
        fetch_k = 12
        candidates = search_top_k(vector_store, query=query, k=fetch_k)

        # 2) rerank to top_k
        top_k = 3
        results = rerank_docs(query=query, docs=candidates, top_k=top_k)

        # 3) build cited context
        context, sources = build_context_with_citations(results)

        # 4) generate grounded answer (must cite [S#])
        answer = generate_answer_gemini(query=query, context=context)

        return {
            "filename": file.filename,
            "query": query,
            "num_chunks": len(chunks),
            "fetch_k": fetch_k,
            "top_k": top_k,
            "answer": answer,
            "context_preview": context[:600],
            "sources": sources,
        }
    finally:
        os.remove(tmp_path)

def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
    
import json
import time
from typing import Generator
from fastapi.responses import StreamingResponse

def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

@app.post("/ask-stream")
async def ask_stream(file: UploadFile = File(...), query: str = "What is the main topic?"):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    def event_generator() -> Generator[str, None, None]:
        token_count = 0
        try:
            yield sse("debug", {"step": "start"})

            chunks = load_and_chunk_pdf(tmp_path)
            yield sse("debug", {"step": "chunked", "num_chunks": len(chunks)})

            vector_store = build_faiss_index(chunks)
            yield sse("debug", {"step": "faiss_built"})

            fetch_k = 12
            candidates = search_top_k(vector_store, query=query, k=fetch_k)
            yield sse("debug", {"step": "retrieved", "fetch_k": fetch_k, "got": len(candidates)})

            top_k = 3
            results = rerank_docs(query=query, docs=candidates, top_k=top_k)
            yield sse("debug", {"step": "reranked", "top_k": top_k, "got": len(results)})

            context, sources = build_context_with_citations(results)
            yield sse("debug", {"step": "context_built", "context_len": len(context)})

            # 先发 meta（前端可先显示引用卡片）
            yield sse("meta", {
                "type": "meta",
                "filename": file.filename,
                "query": query,
                "num_chunks": len(chunks),
                "fetch_k": fetch_k,
                "top_k": top_k,
                "sources": sources,
            })

            yield sse("ping", {"t": time.time(), "msg": "before_gemini_stream"})

            for delta in stream_answer_gemini(query=query, context=context):
                token_count += 1
                yield sse("token", {"type": "token", "delta": delta})

        except Exception as e:
            yield sse("error", {"type": "error", "message": str(e)})
        finally:
            yield sse("done", {"type": "done", "token_count": token_count})
            try:
                os.remove(tmp_path)
            except Exception:
                pass

    return StreamingResponse(event_generator(), media_type="text/event-stream")