from __future__ import annotations

from typing import Any, Dict, List

def apply_quality_gate(report: Dict[str, Any]) -> Dict[str, str]:
    """
    Decide if we accept the model answer based on citation_report.

    Returns:
      {
        "decision": "accept" | "fallback" | "reject",
        "reason": "ok" | "missing_citation" | "no_citation_used" | "parse_failed"
      }
    """
    # 如果你 report 里有 parse_ok/parse_failed 之类字段，就在这里先处理
    if report.get("parse_ok") is False:
        return {"decision": "reject", "reason": "parse_failed"}

    used = report.get("used") or []
    missing = report.get("missing") or []
    ok = bool(report.get("ok"))

    if not used:
        # 模型完全没引用
        return {"decision": "reject", "reason": "no_citation_used"}

    if missing or not ok:
        # 引用了不存在的 S# 或 report.ok=false
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