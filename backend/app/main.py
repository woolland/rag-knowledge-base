from __future__ import annotations

import json, os, tempfile, time
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from fastapi import FastAPI, UploadFile, File, Query, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse, ServerSentEvent

from langchain_core.documents import Document

from app.services.gemini_llm import generate_answer_gemini, stream_answer_gemini
from app.services.ingestion import load_and_chunk_pdf
from app.services.kb_store import kb_dir, kb_exists, load_kb, save_kb
from app.services.manifest_store import file_sha256, has_sha256, load_manifest, upsert_file_record
from app.services.prompting import build_context_with_citations
from app.services.reranker import rerank_docs
from app.services.vector_store import build_faiss_index, search_top_k
from app.services.chunk_store import save_chunks, load_chunk
from app.services.citation_utils import validate_citations
from app.services.eval_retrieval import evaluate_retrieval
from app.services.quality_gate import apply_quality_gate, build_fallback_answer

PROJECT_ROOT = Path(__file__).resolve().parents[2]  # .../rag-knowledge-base
DEFAULT_STORAGE_DIR = str(PROJECT_ROOT / "storage")
app = FastAPI(title="RAG Knowledge Base API")
class AskRequest(BaseModel):
    kb_id: str
    query: str
    fetch_k: int = 12
    top_k: int = 3

def build_eval_report(
    answer: str,
    source_map: Dict[str, str],
    retrieved_docs: List[Document],
) -> Dict[str, Any]:
    citation = validate_citations(answer=answer, source_map=source_map)

    used_chunk_ids = [source_map[sid] for sid in citation["used"] if sid in source_map]

    retrieval = evaluate_retrieval(
        retrieved_docs=retrieved_docs,
        used_chunk_ids=used_chunk_ids,
    )

    return {"citation": citation, "retrieval": retrieval, "ok": bool(citation["ok"]) and bool(retrieval["ok"])}

def get_base_dir() -> str:
    return os.getenv("KB_STORAGE_DIR", DEFAULT_STORAGE_DIR)

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...), kb_id: str = "default"):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        file_hash = file_sha256(tmp_path)
        chunks = load_and_chunk_pdf(tmp_path, kb_id=kb_id, filename=file.filename, file_sha256=file_hash)
        return {"filename": file.filename, "kb_id": kb_id, "num_chunks": len(chunks), "sample_chunk": chunks[0].page_content[:300] if chunks else ""}
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
        file_hash = file_sha256(tmp_path)
        chunks = load_and_chunk_pdf(tmp_path,kb_id=kb_id,filename=file.filename,file_sha256=file_hash)
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
        file_hash = file_sha256(tmp_path)
        chunks = load_and_chunk_pdf(tmp_path,kb_id=kb_id,filename=file.filename,file_sha256=file_hash)
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

@app.post("/ask-stream")
async def ask_stream(file: UploadFile = File(...), query: str = "What is the main topic?"):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    def event_generator() -> Generator[str, None, None]:
        token_count = 0
        try:
            yield sse("debug", {"step": "start"})

            file_hash = file_sha256(tmp_path)
            chunks = load_and_chunk_pdf(tmp_path,kb_id=kb_id,filename=file.filename,file_sha256=file_hash)
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

@app.post("/ingest")
async def ingest(
    file: UploadFile = File(...),
    kb_id: str = "default",
    mode: str = Query(default="overwrite", pattern="^(overwrite|append)$"),
):
    """
    Day7: Ingest PDF into a persistent KB (FAISS saved on disk).
    mode:
      - overwrite: replace KB with this file
      - append: add this file's chunks into existing KB
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    base_dir = get_base_dir()

    try:
        file_hash = file_sha256(tmp_path)
        chunks = load_and_chunk_pdf(tmp_path,kb_id=kb_id,filename=file.filename,file_sha256=file_hash)

        # ✅ 1) append 去重：同一个 PDF 内容（sha256）已经 ingest 过就直接跳过
        saved_kb_dir = kb_dir(base_dir, kb_id)  # <base_dir>/kb/<kb_id>
        file_hash = file_sha256(tmp_path)

        # 只有当 KB 目录存在时才有“历史记录可去重”
        if mode == "append" and os.path.isdir(saved_kb_dir):
            m = load_manifest(saved_kb_dir)
            if has_sha256(m, file_hash):
                return {
                    "kb_id": kb_id,
                    "mode": mode,
                    "filename": file.filename,
                    "num_chunks": len(chunks),
                    "duplicate": True,
                    "skipped": True,
                    "saved_path": saved_kb_dir,
                    "manifest": {
                        "total_files": m.get("total_files", 0),
                        "total_chunks": m.get("total_chunks", 0),
                        "updated_at": m.get("updated_at"),
                    },
                }

        # ✅ 2) 正常 ingest：append -> load + add；overwrite -> rebuild
        if mode == "append" and kb_exists(base_dir, kb_id):
            vs = load_kb(kb_id=kb_id, base_dir=base_dir)
            vs.add_documents(chunks)
            saved_path = save_kb(vector_store=vs, kb_id=kb_id, base_dir=base_dir)
            saved_chunks = save_chunks(kb_dir=saved_path, docs=chunks)
        else:
            vs = build_faiss_index(chunks)
            saved_path = save_kb(vector_store=vs, kb_id=kb_id, base_dir=base_dir)
            saved_chunks = save_chunks(kb_dir=saved_path, docs=chunks)

        # ✅ 3) 更新 manifest（只在真正写入时更新）
        os.makedirs(saved_path, exist_ok=True)
        manifest = upsert_file_record(
            kb_dir=saved_path,
            filename=file.filename,
            file_path=tmp_path,
            num_chunks=len(chunks),
            mode=mode,
        )

        return {
            "kb_id": kb_id,
            "mode": mode,
            "filename": file.filename,
            "num_chunks": len(chunks),
            "saved_path": saved_path,
            "saved_chunks": saved_chunks,
            "manifest": {
                "total_files": manifest["total_files"],
                "total_chunks": manifest["total_chunks"],
                "updated_at": manifest["updated_at"],
            },
        }
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass


# Deprecated: use /kb/{kb_id}/chunk/{chunk_id}
@app.get("/kb/chunk-legacy")
async def get_chunk_legacy(
    kb_id: str = Query(...),
    chunk_id: str = Query(...),
):
    base_dir = get_base_dir()
    dir_ = kb_dir(base_dir, kb_id)
    payload = load_chunk(kb_dir=dir_, chunk_id=chunk_id)
    return payload

@app.get("/kb/{kb_id}/chunk/{chunk_id}")
def get_chunk_rest(kb_id: str, chunk_id: str):
    base_dir = get_base_dir()
    kb_path = kb_dir(base_dir, kb_id)

    try:
        payload = load_chunk(kb_dir=kb_path, chunk_id=chunk_id)
        return payload
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"chunk_id not found: {chunk_id}"
        )


@app.post("/ask-kb")
async def ask_kb(req:AskRequest):
    kb_id = req.kb_id
    query = req.query
    fetch_k = req.fetch_k
    top_k = req.top_k
    base_dir = get_base_dir()

    vs = load_kb(kb_id=kb_id, base_dir=base_dir)
    candidates = search_top_k(vs, query=query, k=fetch_k)
    results = rerank_docs(query=query, docs=candidates, top_k=top_k)

    context, sources, source_map = build_context_with_citations(results)
    answer = generate_answer_gemini(query=query, context=context)

    report = build_eval_report(answer=answer, source_map=source_map, retrieved_docs=results)
    gate = apply_quality_gate(report)

    if gate["decision"] == "fallback":
        answer = build_fallback_answer(sources)
    elif gate["decision"] == "reject":
        answer = "I could not generate a grounded answer for this query."

    return {
        "kb_id": kb_id,
        "query": query,
        "fetch_k": fetch_k,
        "top_k": top_k,
        "answer": answer,
        "sources": sources,
        "source_map": source_map,
        "evaluation": report,        # ✅ 建议叫 evaluation（更语义化）
        "quality_gate": gate,
    }

@app.post("/ask-kb-stream")
async def ask_kb_stream(kb_id: str, query: str = "What is the main topic?"):
    base_dir = get_base_dir()

    async def event_generator():
        token_count = 0
        final_text_parts = []
        source_map = {}
        sources = []
        results = []

        try:
            yield ServerSentEvent(event="debug", data=json.dumps({"step": "start", "kb_id": kb_id}, ensure_ascii=False))

            vs = load_kb(kb_id=kb_id, base_dir=base_dir)
            yield ServerSentEvent(event="debug", data=json.dumps({"step": "kb_loaded"}, ensure_ascii=False))

            fetch_k = 12
            candidates = search_top_k(vs, query=query, k=fetch_k)
            yield ServerSentEvent(event="debug", data=json.dumps({"step": "retrieved", "fetch_k": fetch_k, "got": len(candidates)}, ensure_ascii=False))

            top_k = 3
            results = rerank_docs(query=query, docs=candidates, top_k=top_k)
            yield ServerSentEvent(event="debug", data=json.dumps({"step": "reranked", "top_k": top_k, "got": len(results)}, ensure_ascii=False))

            context, sources, source_map = build_context_with_citations(results)
            yield ServerSentEvent(event="debug", data=json.dumps({"step": "context_built", "context_len": len(context)}, ensure_ascii=False))

            meta = {
                "type": "meta",
                "kb_id": kb_id,
                "query": query,
                "fetch_k": fetch_k,
                "top_k": top_k,
                "sources": sources,
                "source_map": source_map,
            }
            yield ServerSentEvent(event="meta", data=json.dumps(meta, ensure_ascii=False))

            yield ServerSentEvent(event="ping", data=json.dumps({"t": time.time(), "msg": "before_gemini_stream"}, ensure_ascii=False))

            for delta in stream_answer_gemini(query=query, context=context):
                token_count += 1
                final_text_parts.append(delta)
                yield ServerSentEvent(event="token", data=json.dumps({"type": "token", "delta": delta}, ensure_ascii=False))

        except FileNotFoundError:
            yield ServerSentEvent(event="error", data=json.dumps({"type": "error", "message": f"KB '{kb_id}' not found in {base_dir}"}, ensure_ascii=False))
        except Exception as e:
            yield ServerSentEvent(event="error", data=json.dumps({"type": "error", "message": str(e)}, ensure_ascii=False))
        finally:
            final_answer = "".join(final_text_parts).strip()

            report = build_eval_report(answer=final_answer, source_map=source_map, retrieved_docs=results)
            gate = apply_quality_gate(report)

            if gate["decision"] == "fallback":
                final_answer = build_fallback_answer(sources)
            elif gate["decision"] == "reject":
                final_answer = "I could not generate a grounded answer for this query."

            yield ServerSentEvent(
                event="done",
                data=json.dumps(
                    {
                        "type": "done",
                        "token_count": token_count,
                        "final_answer": final_answer,
                        "evaluation": report,
                        "quality_gate": gate,
                    },
                    ensure_ascii=False,
                ),
            )

    return EventSourceResponse(event_generator())

@app.get("/kb/chunk")
def get_chunk(
    kb_id: str = Query(...),
    chunk_id: str = Query(...),
    include_content: bool = Query(True),
):
    base_dir = get_base_dir()
    vs = load_kb(kb_id=kb_id, base_dir=base_dir)

    doc = find_chunk_by_id(vs, chunk_id=chunk_id)
    if doc is None:
        raise HTTPException(status_code=404, detail=f"chunk_id not found: {chunk_id}")

    md = doc.metadata or {}

    payload = {
        "kb_id": kb_id,
        "chunk_id": chunk_id,
        "page_content": doc.page_content if include_content else None,
        "metadata": md,
        # 这些扁平字段是 UI 友好的，可保留
        "filename": md.get("filename"),
        "page": md.get("page"),
        "page_label": md.get("page_label"),
        "chunk_index": md.get("chunk_index"),
    }
    return payload


