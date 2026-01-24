# backend/app/services/manifest_store.py
from __future__ import annotations

import json
import os
import time
import hashlib
from typing import Any, Dict

MANIFEST_NAME = "manifest.json"


def file_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest_path(kb_dir: str) -> str:
    return os.path.join(kb_dir, MANIFEST_NAME)


def load_manifest(kb_dir: str) -> Dict[str, Any]:
    mp = manifest_path(kb_dir)
    if not os.path.exists(mp):
        return {
            "kb_id": os.path.basename(kb_dir),
            "created_at": time.time(),
            "updated_at": time.time(),
            "files": [],
            "total_files": 0,
            "total_chunks": 0,
        }
    with open(mp, "r", encoding="utf-8") as f:
        return json.load(f)


def save_manifest(kb_dir: str, data: Dict[str, Any]) -> None:
    data["updated_at"] = time.time()
    with open(manifest_path(kb_dir), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def has_sha256(m: Dict[str, Any], sha256: str) -> bool:
    for rec in m.get("files", []):
        if rec.get("sha256") == sha256:
            return True
    return False


def upsert_file_record(
    kb_dir: str,
    filename: str,
    file_path: str,
    num_chunks: int,
    mode: str,
) -> Dict[str, Any]:
    m = load_manifest(kb_dir)

    rec = {
        "filename": filename,
        "sha256": file_sha256(file_path),
        "num_chunks": num_chunks,
        "ingested_at": time.time(),
        "mode": mode,
    }

    # overwrite: 清空 files；append: 追加（同名可重复，方便审计）
    if mode == "overwrite":
        m["files"] = [rec]
    else:
        m["files"].append(rec)

    m["total_files"] = len(m["files"])
    m["total_chunks"] = sum(x.get("num_chunks", 0) for x in m["files"])
    save_manifest(kb_dir, m)
    return m