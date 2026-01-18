from typing import List
from langchain_core.documents import Document


def build_context(docs: List[Document], max_chars: int = 3500) -> str:
    """
    Merge retrieved chunks into a single context string.
    We cap length to avoid overly large responses.
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


def mock_generate_answer(query: str, docs: List[Document]) -> str:
    """
    A placeholder 'generation' function.
    It does NOT call an LLM.
    It produces a readable answer based on retrieved text.
    """
    if not docs:
        return "I don't know based on the provided document."

    # Use the first chunk as the main signal
    main = docs[0].page_content.strip().replace("\n", " ")
    main = main[:300]

    return f"(Mock Answer) Based on the retrieved context, the document is mainly about: {main}..."