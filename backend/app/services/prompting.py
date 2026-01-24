from __future__ import annotations
from typing import List, Dict, Tuple, Any
from langchain_core.documents import Document


def build_context_with_citations(docs: List[Document]) -> Tuple[str, List[Dict[str, Any]], Dict[str, str]]:
    """
    Build LLM context with [S1], [S2] markers and return:
    - context: string
    - sources: list of source metadata objects
    - source_map: { "S1": "<chunk_id>", ... }
    """
    context_blocks = []
    sources = []
    source_map: Dict[str, str] = {}

    for i, doc in enumerate(docs, start=1):
        sid = f"S{i}"
        md = doc.metadata or {}

        chunk_id = md.get("chunk_id", "")
        source_map[sid] = chunk_id

        context_blocks.append(
            f"[{sid}] (page={md.get('page_label', md.get('page'))}, chunk_id={chunk_id})\n"
            f"{doc.page_content.strip()}\n"
        )

        sources.append({
            "source_id": sid,
            "chunk_id": chunk_id,
            "chunk_index": md.get("chunk_index"),
            "kb_id": md.get("kb_id"),
            "filename": md.get("filename"),
            "file_sha256": md.get("file_sha256"),
            "page": md.get("page"),
            "page_label": md.get("page_label"),
            "total_pages": md.get("total_pages"),
            "content_preview": doc.page_content[:220],
            "metadata": md,
        })

    context = "\n---\n".join(context_blocks)
    return context, sources, source_map