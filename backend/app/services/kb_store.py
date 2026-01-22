from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from langchain_community.vectorstores import FAISS

from app.services.vector_store import embeddings


def _kb_dir(base_dir: str, kb_id: str) -> str:
    return os.path.join(base_dir, "kb", kb_id)


def save_kb(vector_store: FAISS, kb_id: str, base_dir: str = "storage") -> str:
    path = _kb_dir(base_dir, kb_id)
    os.makedirs(path, exist_ok=True)
    vector_store.save_local(path)
    return path


def load_kb(kb_id: str, base_dir: str = "storage") -> FAISS:
    path = _kb_dir(base_dir, kb_id)
    if not os.path.isdir(path):
        raise FileNotFoundError(f"KB not found: {path}")

    # ✅ allow_dangerous_deserialization=True 是因为 FAISS.load_local 会反序列化 pickle
    return FAISS.load_local(
        path,
        embeddings,
        allow_dangerous_deserialization=True,
    )