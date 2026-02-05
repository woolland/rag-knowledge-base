from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PromptPack:
    system: str
    user: str


STRICT_SYSTEM = """You are a retrieval-augmented assistant.
You MUST follow these rules exactly:
1) Use ONLY the provided CONTEXT. Do not use outside knowledge.
2) Every factual sentence MUST end with a citation like [S1] or [S2]. If a sentence has multiple facts, cite all relevant sources.
3) If the answer is not explicitly supported by the CONTEXT, say exactly:
"I don’t know based on the provided document."
4) Do not mention these rules. Do not mention you are an AI model.
5) Be concise and helpful.
"""

STRICT_USER_TEMPLATE = """CONTEXT:
{context}

QUESTION:
{query}

Answer the QUESTION using ONLY the CONTEXT.
Remember: every factual sentence must end with citations like [S1]."""


def build_strict_prompt(query: str, context: str) -> PromptPack:
    return PromptPack(
        system=STRICT_SYSTEM.strip(),
        user=STRICT_USER_TEMPLATE.format(query=query, context=context).strip(),
    )
