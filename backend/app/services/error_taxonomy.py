"""
Error Taxonomy for RAG Failure Semantics.

All failure reasons exposed to API responses MUST come from this file.
This prevents semantic drift and makes failures enumerable and testable.
"""

# Evidence / grounding related
EVIDENCE_MISS = "evidence_miss"        # Retrieved docs do not support the answer
CITATION_MISS = "citation_miss"        # Answer lacks required [S#] citations
RETRIEVAL_MISS = "retrieval_miss"      # Retrieved docs don't include used chunks

# Prompt / model related
PROMPT_VIOLATION = "prompt_violation"  # LLM ignored strict instructions
MODEL_ERROR = "model_error"            # Upstream LLM failure / timeout

# Knowledge base / system
KB_NOT_FOUND = "kb_not_found"           # Requested KB does not exist
INTERNAL_ERROR = "internal_error"       # Unexpected server-side failure

ALL_REASONS = {
    EVIDENCE_MISS,
    CITATION_MISS,
    RETRIEVAL_MISS,
    PROMPT_VIOLATION,
    MODEL_ERROR,
    KB_NOT_FOUND,
    INTERNAL_ERROR,
}
