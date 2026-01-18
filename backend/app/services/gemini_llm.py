import os
from google import genai


def generate_answer_gemini(query: str, context: str, model: str = "models/gemini-2.5-flash-lite") -> str:
    """
    Generate an answer using Gemini API, grounded in retrieved context.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set. Please export it in your terminal.")

    client = genai.Client(api_key=api_key)

    prompt = f"""
You are a helpful assistant.
Answer the question using ONLY the context below.
If the answer is not in the context, say: "I don't know based on the provided document."

Context:
{context}

Question:
{query}
"""

    resp = client.models.generate_content(
        model=model,
        contents=prompt,
    )

    return (resp.text or "").strip()