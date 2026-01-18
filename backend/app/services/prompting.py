from typing import List
from langchain_core.documents import Document


def build_context(docs: List[Document], max_chars: int = 4000) -> str:
    """
    Convert retrieved Documents into a single context string for the LLM.
    Truncate to avoid overly long prompts.
    """
    parts = []
    total = 0

    for i, doc in enumerate(docs, start=1):
        text = doc.page_content.strip()
        if not text:
            continue

        chunk = f"[Chunk {i}]\n{text}\n"
        if total + len(chunk) > max_chars:
            break

        parts.append(chunk)
        total += len(chunk)

    return "\n".join(parts)