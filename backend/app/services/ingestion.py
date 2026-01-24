# backend/app/services/ingestion.py
from __future__ import annotations

from typing import List
import hashlib

from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter


def make_chunk_id(kb_id: str, file_sha256: str, page: int, chunk_index: int) -> str:
    """
    Make a stable chunk_id for citations.
    Example: demo:29d36b...:p0:c3
    """
    return f"{kb_id}:{file_sha256}:p{page}:c{chunk_index}"


def load_and_chunk_pdf(
    pdf_path: str,
    kb_id: str = "default",
    filename: str = "",
    file_sha256: str = "",
) -> List[Document]:
    """
    Load a PDF and split it into chunks.
    Also attach metadata needed for Day8 citations:
      kb_id, filename, file_sha256, chunk_index, chunk_id, page/page_label/total_pages
    """

    # 1) Load PDF -> list[Document] (each is usually per-page)
    loader = PyPDFLoader(pdf_path)
    documents: List[Document] = loader.load()

    # 2) Split into smaller text chunks for retrieval
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
    )
    chunks: List[Document] = splitter.split_documents(documents)

    # 3) Attach stable citation metadata to each chunk
    for idx, doc in enumerate(chunks):
        md = doc.metadata or {}

        page = md.get("page", 0)
        page_label = md.get("page_label")
        total_pages = md.get("total_pages")

        md.update(
            {
                "kb_id": kb_id,
                "filename": filename,
                "file_sha256": file_sha256,
                "chunk_index": idx,
                "chunk_id": make_chunk_id(kb_id, file_sha256, page, idx),
                "page": page,
                "page_label": page_label,
                "total_pages": total_pages,
            }
        )

        doc.metadata = md

    return chunks