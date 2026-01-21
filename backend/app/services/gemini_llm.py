from __future__ import annotations

import os
from typing import Iterator
from google import genai


DEFAULT_MODEL = "gemini-2.5-flash-lite"  #  [oai_citation:2‡GitHub](https://raw.githubusercontent.com/googleapis/python-genai/refs/heads/main/README.md)


import os
import time
from typing import Iterator
from google import genai

def build_prompt(query: str, context: str) -> str:
    return f"""
You are a helpful assistant.
Answer the question using ONLY the context below.
You MUST cite sources like [S1], [S2] in the answer.
If the answer is not in the context, say: "I don't know based on the provided document."

Context:
{context}

Question:
{query}
""".strip()

def stream_answer_gemini(query: str, context: str, model: str = DEFAULT_MODEL) -> Iterator[str]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set. Please export it in your terminal.")

    client = genai.Client(api_key=api_key)
    prompt = build_prompt(query=query, context=context)

    # ✅ 1) 真 streaming：如果 SDK 提供专用方法就用它
    if hasattr(client.models, "generate_content_stream"):
        stream = client.models.generate_content_stream(model=model, contents=prompt)
        for chunk in stream:
            text = getattr(chunk, "text", None)
            if text:
                yield text
        return

    # ✅ 2) 兜底：完全不传 stream 参数，做“伪 streaming”
    resp = client.models.generate_content(model=model, contents=prompt)
    full = (getattr(resp, "text", "") or "").strip()
    for i in range(0, len(full), 50):
        yield full[i:i + 50]
        time.sleep(0.02)

def generate_answer_gemini(query: str, context: str, model: str = DEFAULT_MODEL) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set. Please export it in your terminal.")

    client = genai.Client(api_key=api_key)
    prompt = build_prompt(query=query, context=context)

    resp = client.models.generate_content(model=model, contents=prompt)
    return (getattr(resp, "text", "") or "").strip()