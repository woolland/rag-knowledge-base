from __future__ import annotations

import os
import time
from typing import Iterator


DEFAULT_MODEL = "gemini-2.5-flash-lite"

from app.services.prompting_hardened import build_strict_prompt


def _get_genai():
    """
    Lazy + compatible import for Google Gemini SDK.

    Supports:
    - google-genai (new): from google import genai
    - google-generativeai (legacy): import google.generativeai as genai
    """
    try:
        from google import genai  # new SDK
        return genai
    except Exception:
        try:
            import google.generativeai as genai  # legacy SDK
            return genai
        except Exception as e:
            raise ImportError(
                "Gemini SDK not available. "
                "Install google-genai or google-generativeai."
            ) from e


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


def stream_answer_gemini(
    query: str,
    context: str,
    model: str = DEFAULT_MODEL,
) -> Iterator[str]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set.")

    genai = _get_genai()
    client = genai.Client(api_key=api_key)
    
    # Day22: harden prompt
    pack = build_strict_prompt(query=query, context=context)

    # System instruction goes to config, user message to contents
    contents = [
        {"role": "user", "parts": [{"text": pack.user}]},
    ]
    config = {"system_instruction": pack.system}

    # Native streaming if available
    if hasattr(client.models, "generate_content_stream"):
        for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=config,
        ):
            text = getattr(chunk, "text", None)
            if text:
                yield text
        return

    # Fallback: fake streaming
    resp = client.models.generate_content(model=model, contents=contents, config=config)
    text = (getattr(resp, "text", "") or "").strip()
    for i in range(0, len(text), 50):
        yield text[i : i + 50]
        time.sleep(0.02)


def generate_answer_gemini(
    query: str,
    context: str,
    model: str = DEFAULT_MODEL,
) -> str:
    # MOCK LOGIC for regression testing
    mock_file = "/tmp/rag_mock_response.txt"
    if os.path.exists(mock_file):
        with open(mock_file, "r", encoding="utf-8") as f:
            return f.read().strip()

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set.")

    genai = _get_genai()
    client = genai.Client(api_key=api_key)
    
    # Day22: harden prompt
    pack = build_strict_prompt(query=query, context=context)

    # structured contents for google-genai
    # System instruction goes to config, user message to contents
    contents = [
        {"role": "user", "parts": [{"text": pack.user}]},
    ]
    config = {"system_instruction": pack.system}

    resp = client.models.generate_content(model=model, contents=contents, config=config)
    return (getattr(resp, "text", "") or "").strip()
