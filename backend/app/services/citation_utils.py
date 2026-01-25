from __future__ import annotations

import re
from typing import Dict, List, Set, Tuple

CITATION_PATTERN = re.compile(r"\[(S\d+)\]")

def extract_citations(answer: str) -> List[str]:
    """
    Extract citation labels like S1, S2 from answer text.
    """
    return CITATION_PATTERN.findall(answer or "")

def validate_citations(answer: str, source_map: Dict[str, str]) -> Dict[str, object]:
    """
    Validate that citations in answer exist in source_map.
    Returns a report object for API.
    """
    used = extract_citations(answer)
    used_set: Set[str] = set(used)
    known_set: Set[str] = set(source_map.keys())

    missing = sorted(list(used_set - known_set))
    unused = sorted(list(known_set - used_set))

    return {
        "used": used,
        "missing": missing,  # answer 引用了但 source_map 不存在
        "unused": unused,    # source_map 有但 answer 没用到（可选）
        "ok": len(missing) == 0,
    }