from __future__ import annotations

import re
from typing import Dict, List, Set

# 1) 先抓所有方括号内容：[ ... ]
BRACKET_PATTERN = re.compile(r"\[([^\]]+)\]")

# 2) 在方括号内容中抓 S<number>
SOURCE_ID_PATTERN = re.compile(r"S\d+")


def extract_citations(answer: str) -> List[str]:
    """
    Extract citation labels from answer text.
    Supports:
      - [S1]
      - [S1, S2, S3]
      - [S1;S2] / [S1 | S2]
    Returns a de-duplicated list while preserving order.
    """
    text = answer or ""
    used: List[str] = []

    for m in BRACKET_PATTERN.finditer(text):
        inside = m.group(1)  # e.g. "S1, S2, S3"
        used.extend(SOURCE_ID_PATTERN.findall(inside))

    # de-dupe but keep order
    seen: Set[str] = set()
    out: List[str] = []
    for s in used:
        if s not in seen:
            out.append(s)
            seen.add(s)
    return out


def validate_citations(answer: str, source_map: Dict[str, str]) -> Dict[str, object]:
    """
    Validate that citations in answer exist in source_map.
    Returns a report object for API.

    Fields:
      - used: citations extracted from answer (order-preserving)
      - missing: cited in answer but not present in source_map
      - unused: present in source_map but not cited in answer
      - parse_ok: if answer contains [] but we fail to extract any S#
      - ok: engineering OK (no missing + parse_ok)
    """
    used = extract_citations(answer)

    used_set: Set[str] = set(used)
    known_set: Set[str] = set((source_map or {}).keys())

    missing = sorted(list(used_set - known_set))
    unused = sorted(list(known_set - used_set))

    text = answer or ""
    has_brackets = ("[" in text and "]" in text)
    parse_ok = (not has_brackets) or (len(used) > 0)

    return {
        "used": used,
        "missing": missing,
        "unused": unused,
        "parse_ok": parse_ok,
        "ok": (len(missing) == 0) and parse_ok,
    }