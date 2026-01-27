from __future__ import annotations

import json
import os
from typing import Any, Dict, Iterable, Optional
from langchain_core.documents import Document

CHUNKS_DIRNAME = "chunks"          # <kb_dir>/chunks/
CHUNK_EXT = ".json"                # 每个 chunk 一个 json 文件

def chunks_dir(kb_dir: str) -> str:
    return os.path.join(kb_dir, CHUNKS_DIRNAME)

def chunk_path(kb_dir: str, chunk_id: str) -> str:
    # chunk_id 里有 ":"，对文件名不友好；做一个简单替换
    safe_name = chunk_id.replace(":", "_")
    return os.path.join(chunks_dir(kb_dir), safe_name + CHUNK_EXT)

def save_chunks(kb_dir: str, docs: Iterable[Document]) -> int:
    os.makedirs(chunks_dir(kb_dir), exist_ok=True)
    index_path = os.path.join(kb_dir, "chunk_index.json")

    index: Dict[str, str] = {}
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            index = json.load(f)

    n = 0
    for doc in docs:
        md = doc.metadata or {}
        chunk_id = md.get("chunk_id")
        if not chunk_id:
            continue

        rel_path = os.path.join(
            CHUNKS_DIRNAME,
            chunk_id.replace(":", "_") + CHUNK_EXT
        )

        payload = {
            "chunk_id": chunk_id,
            "page_content": doc.page_content,
            "metadata": md,
        }

        with open(os.path.join(kb_dir, rel_path), "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        index[chunk_id] = rel_path
        n += 1

    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    return n

def load_chunk(kb_dir: str, chunk_id: str) -> Dict[str, Any]:
    index_path = os.path.join(kb_dir, "chunk_index.json")
    if not os.path.exists(index_path):
        raise FileNotFoundError("chunk_index.json not found")

    with open(index_path, "r", encoding="utf-8") as f:
        index = json.load(f)

    rel_path = index.get(chunk_id)
    if not rel_path:
        raise FileNotFoundError(f"Chunk not found: {chunk_id}")

    path = os.path.join(kb_dir, rel_path)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def find_chunk_by_id(vs: FAISS, chunk_id: str) -> Optional[Document]:
    store = getattr(vs.docstore, "_dict", None)
    if not store:
        return None

    for doc in store.values():
        md = doc.metadata or {}
        if md.get("chunk_id") == chunk_id:
            return doc
    return None