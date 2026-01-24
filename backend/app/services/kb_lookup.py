from __future__ import annotations
from typing import Optional, Dict, Any, List
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document


def find_chunk_by_id(vs: FAISS, chunk_id: str) -> Optional[Document]:
    """
    Find a chunk Document by chunk_id from a loaded FAISS vector store.

    Implementation detail:
    - FAISS stores documents in vs.docstore (InMemoryDocstore)
    - We iterate all stored docs and match metadata["chunk_id"]
    """
    docstore = getattr(vs, "docstore", None)
    if docstore is None:
        return None

    store_dict = getattr(docstore, "_dict", None)
    if not store_dict:
        return None

    for _, doc in store_dict.items():
        md = doc.metadata or {}
        if md.get("chunk_id") == chunk_id:
            return doc

    return None