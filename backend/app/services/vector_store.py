from __future__ import annotations
from typing import List

from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

def build_faiss_index(chunks: List[Document]) -> FAISS:
    """
    Build an in-memory FAISS index using local HuggingFace embeddings (no API key).
    """
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    return FAISS.from_documents(chunks, embeddings) #  Converts each chunk into a vector and Stores them into FAISS index


def search_top_k(vector_store: FAISS, query: str, k: int = 5) -> List[Document]:
    return vector_store.similarity_search(query, k=k) # Performs semantic search using vector similarity


