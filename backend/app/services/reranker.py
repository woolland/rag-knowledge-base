from __future__ import annotations

from typing import List

from langchain_core.documents import Document
from sentence_transformers import CrossEncoder

_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"

_reranker: CrossEncoder | None = None


def _get_reranker() -> CrossEncoder:
    global _reranker
    if _reranker is None:
        _reranker = CrossEncoder(_MODEL_NAME)
    return _reranker


def rerank_docs(query: str, docs: List[Document], top_k: int = 3) -> List[Document]:
    """
    Re-rank retrieved docs using a cross-encoder.
    Input: query + candidate docs
    Output: top_k docs sorted by relevance (highest score first)
    """
    if not docs:
        return []

    model = _get_reranker()

    pairs = [(query, d.page_content) for d in docs]
    scores = model.predict(pairs)

    ranked = sorted(zip(docs, scores), key=lambda x: float(x[1]), reverse=True)
    return [d for d, _ in ranked[:top_k]]
