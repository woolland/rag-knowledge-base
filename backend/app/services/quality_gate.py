from __future__ import annotations

from typing import Any, Dict, List

def apply_quality_gate(report: Dict[str, Any]) -> Dict[str, str]:
    """
    Accept either:
      A) citation report (flat): {"used":..., "missing":..., "ok":..., "parse_ok":...}
      B) evaluation report (nested): {"citation": {...}, "retrieval": {...}, "ok":...}
    """
    citation = report.get("citation", report)  # ✅关键：兼容 nested / flat

    # parse_ok / ok 字段兼容
    if citation.get("parse_ok") is False:
        return {"decision": "reject", "reason": "parse_failed"}

    used = citation.get("used") or []
    missing = citation.get("missing") or []
    ok = bool(citation.get("ok"))

    if not used:
        return {"decision": "reject", "reason": "no_citation_used"}

    if missing or not ok:
        return {"decision": "fallback", "reason": "missing_citation"}

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