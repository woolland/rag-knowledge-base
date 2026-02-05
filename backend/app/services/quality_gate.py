from typing import Any, Dict, List

from app.services.error_taxonomy import (
    EVIDENCE_MISS,
    CITATION_MISS,
    RETRIEVAL_MISS,
)

def quality_gate_decision(evaluation: Dict[str, Any]) -> Dict[str, str]:
    """
    Decide whether to accept or reject the answer based on evaluation metrics.
    Strict quality gate: any failure in citation or retrieval leads to rejection.
    """
    citation = evaluation.get("citation", {})
    retrieval = evaluation.get("retrieval", {})
    evidence_hit = evaluation.get("evidence_hit", False)

    if not citation.get("ok"):
        return {"decision": "fallback", "reason": CITATION_MISS}

    if not retrieval.get("ok"):
        return {"decision": "fallback", "reason": RETRIEVAL_MISS}

    if not evidence_hit:
        return {"decision": "fallback", "reason": EVIDENCE_MISS}

    if not evaluation.get("ok", True):
        return {"decision": "fallback", "reason": EVIDENCE_MISS}

    return {"decision": "accept", "reason": "ok"}


def build_fallback_answer(sources: List[Dict[str, Any]], max_sources: int = 3) -> str:
    """
    Build a strictly-grounded fallback answer using sources only.
    No new claims. Only summarize what sources say.
    """
    if not sources:
        return "I could not find relevant evidence in the knowledge base."

    lines = [
        "I couldn't produce a fully grounded answer. Here is what I *can* confirm from the retrieved sources:",
        "",
    ]

    for s in sources[:max_sources]:
        sid = s.get("source_id", "")
        page = s.get("page_label", s.get("page", ""))
        preview = (s.get("content_preview") or "").strip().replace("\n", " ")
        if len(preview) > 180:
            preview = preview[:180] + "..."
        lines.append(f"- [{sid}] (page {page}) {preview}")

    return "\n".join(lines)