from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Set

from app.services.kb_store import load_kb
from app.services.vector_store import search_top_k
from app.services.reranker import rerank_docs
from app.services.prompting import build_context_with_citations
from app.services.gemini_llm import generate_answer_gemini
from app.services.citation_utils import validate_citations
from app.services.eval_retrieval import evaluate_retrieval
from app.services.quality_gate import apply_quality_gate

# ------------------------------------------------------------
# Paths
# ------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[3]  # .../rag-knowledge-base
DEFAULT_STORAGE_DIR = str(PROJECT_ROOT / "storage")
EVAL_CASES_PATH = Path(__file__).resolve().parent / "eval_cases.json"
EVAL_OUT_DIR = Path(DEFAULT_STORAGE_DIR) / "eval_results"
EVAL_OUT_DIR.mkdir(parents=True, exist_ok=True)


def get_base_dir() -> str:
    return os.getenv("KB_STORAGE_DIR", DEFAULT_STORAGE_DIR)


def load_cases() -> List[Dict[str, Any]]:
    if not EVAL_CASES_PATH.exists():
        raise FileNotFoundError(f"Missing eval cases: {EVAL_CASES_PATH}")
    return json.loads(EVAL_CASES_PATH.read_text(encoding="utf-8"))


def _used_chunk_ids_from_citations(citation: Dict[str, Any], source_map: Dict[str, str]) -> List[str]:
    used_chunk_ids: List[str] = []
    for sid in citation.get("used", []):
        cid = source_map.get(sid)
        if cid:
            used_chunk_ids.append(cid)
    return used_chunk_ids


def run_one_case(case: Dict[str, Any], base_dir: str) -> Dict[str, Any]:
    """
    Run one eval case and return a structured report.
    """
    case_id = case["id"]
    kb_id = case["kb_id"]
    query = case["query"]
    expected_chunk_ids: Set[str] = set(case.get("expected_chunk_ids", []))

    # ---- Pipeline (same as /ask-kb) ----
    vs = load_kb(kb_id=kb_id, base_dir=base_dir)
    candidates = search_top_k(vs, query=query, k=12)
    results = rerank_docs(query=query, docs=candidates, top_k=3)

    context, sources, source_map = build_context_with_citations(results)
    answer = generate_answer_gemini(query=query, context=context)

    citation = validate_citations(answer=answer, source_map=source_map)
    used_chunk_ids = _used_chunk_ids_from_citations(citation=citation, source_map=source_map)

    retrieval = evaluate_retrieval(
        retrieved_docs=results,
        used_chunk_ids=used_chunk_ids,
    )

    # ---- Match expected evidence ----
    used_set = set(used_chunk_ids)
    evidence_hit = bool(expected_chunk_ids & used_set) if expected_chunk_ids else None

    # ---- Quality gate (use your existing gate) ----
    # apply_quality_gate expects a "citation-like report" in your current implementation.
    gate = apply_quality_gate(citation)

    return {
        "id": case_id,
        "kb_id": kb_id,
        "query": query,
        "answer": answer,
        "expected_chunk_ids": sorted(list(expected_chunk_ids)),
        "used_chunk_ids": used_chunk_ids,
        "citation": citation,
        "retrieval": retrieval,
        "evidence_hit": evidence_hit,  # None if you didn't provide expected evidence
        "quality_gate": gate,
        "sources_preview": [
            {
                "source_id": s.get("source_id"),
                "chunk_id": s.get("chunk_id"),
                "page_label": s.get("page_label"),
                "filename": s.get("filename"),
            }
            for s in (sources or [])
        ],
    }


def summarize(all_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(all_cases)
    if total == 0:
        return {"total": 0}

    citation_ok = sum(1 for c in all_cases if c["citation"].get("ok") is True)
    retrieval_ok = sum(1 for c in all_cases if c["retrieval"].get("ok") is True)

    # evidence_hit 只对写了 expected_chunk_ids 的 case 统计
    evidence_cases = [c for c in all_cases if c.get("evidence_hit") is not None]
    evidence_hit = sum(1 for c in evidence_cases if c.get("evidence_hit") is True)
    evidence_total = len(evidence_cases)

    return {
        "total": total,
        "citation_pass_rate": citation_ok / total,
        "retrieval_pass_rate": retrieval_ok / total,
        "evidence_hit_rate": (evidence_hit / evidence_total) if evidence_total > 0 else None,
        "evidence_cases": evidence_total,
    }


def main() -> None:
    base_dir = get_base_dir()
    cases = load_cases()

    reports: List[Dict[str, Any]] = []
    for case in cases:
        reports.append(run_one_case(case, base_dir=base_dir))

    out = {
        "summary": summarize(reports),
        "cases": reports,
    }

    out_path = EVAL_OUT_DIR / "day16_eval.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] Wrote eval report: {out_path}")


if __name__ == "__main__":
    main()