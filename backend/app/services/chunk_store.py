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
    """
    Persist chunk texts to disk for later lookup by chunk_id.
    Returns number of chunks written.
    """
    os.makedirs(chunks_dir(kb_dir), exist_ok=True)
    n = 0

    for doc in docs:
        md = doc.metadata or {}
        chunk_id = md.get("chunk_id")
        if not chunk_id:
            # 没有 chunk_id 就跳过（说明 ingestion 没注入 metadata）
            continue

        payload: Dict[str, Any] = {
            "chunk_id": chunk_id,
            "page_content": doc.page_content,
            "metadata": md,
        }

        with open(chunk_path(kb_dir, chunk_id), "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        n += 1

    return n

def load_chunk(kb_dir: str, chunk_id: str) -> Dict[str, Any]:
    """
    Load a single chunk payload by chunk_id.
    Raises FileNotFoundError if not found.
    """
    path = chunk_path(kb_dir, chunk_id)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Chunk not found: {chunk_id}")

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)