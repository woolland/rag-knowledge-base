from typing import List, Dict, Any, Tuple
from langchain_core.documents import Document


def build_context_with_citations(
    docs: List[Document],
    max_chars: int = 4000
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Returns:
      - context string containing [Source S1 | page_label=... | page=...]
      - sources list aligned to those S# labels
    """
    parts: List[str] = []
    sources: List[Dict[str, Any]] = []
    total = 0

    for idx, doc in enumerate(docs, start=1):
        text = (doc.page_content or "").strip()
        if not text:
            continue

        md = doc.metadata or {}

        label = f"S{idx}"
        page = md.get("page")
        page_label = md.get("page_label")

        # ✅ Better header: contains both label + page info
        chunk = f"[Source {label} | page_label={page_label} | page={page}]\n{text}\n"

        if total + len(chunk) > max_chars:
            break

        parts.append(chunk)
        total += len(chunk)

        sources.append(
            {
                "source_id": label,
                "page": page,
                "page_label": page_label,
                "total_pages": md.get("total_pages"),
                "content_preview": text[:200],
                "metadata": md,
            }
        )

    context = "\n".join(parts)
    return context, sources