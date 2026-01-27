from typing import List, Dict
from langchain_core.documents import Document

def evaluate_retrieval(
    retrieved_docs: List[Document],
    used_chunk_ids: List[str],
) -> Dict[str, object]:
    retrieved_ids = {
        (doc.metadata or {}).get("chunk_id")
        for doc in retrieved_docs
    }

    used_set = set(used_chunk_ids)

    missing_from_retrieval = sorted(
        list(used_set - retrieved_ids)
    )

    return {
        "used_chunk_ids": used_chunk_ids,
        "missing_from_retrieval": missing_from_retrieval,
        "ok": len(missing_from_retrieval) == 0,
    }

