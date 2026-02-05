import json
import logging
import hashlib
from typing import Dict, Any, Optional

logger = logging.getLogger("rag.metrics")
logger.setLevel(logging.INFO)
# Ensure logs go to stdout/stderr so we can see them in Docker/Console
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(handler)

def emit_quality_metrics(
    kb_id: str,
    query: str,
    evaluation: Dict[str, Any],
    quality_gate: Dict[str, str],
):
    """
    Emits a structured JSON log for RAG quality monitoring.
    """
    try:
        # Use simple hash() as requested by user snippet, or sha256 for stability?
        # User snippet used hash(query). The example JSON showed "sha256:...".
        # I will use sha256 to match the example JSON's implication of stability.
        query_hash = "sha256:" + hashlib.sha256(query.encode("utf-8")).hexdigest()[:16]

        payload = {
            "event": "rag_quality",
            "kb_id": kb_id,
            "query_hash": query_hash,
            "metrics": {
                "quality_gate": quality_gate.get("decision"),
                "citation_ok": evaluation.get("citation", {}).get("ok"),
                "retrieval_ok": evaluation.get("retrieval", {}).get("ok"),
                "evidence_hit": evaluation.get("evidence_hit"),
            },
        }
        logger.info(json.dumps(payload, ensure_ascii=False))
    except Exception as e:
        # Fallback logger if something goes wrong, but don't crash main thread
        print(f"[metrics_error] {e}")
