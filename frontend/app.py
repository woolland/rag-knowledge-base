import re
import requests
import streamlit as st
from typing import Dict, Any, List, Optional

BACKEND = "http://127.0.0.1:8000"

# -------------------------
# 1) Utilities
# -------------------------

def parse_citations(answer: str) -> List[str]:
    """
    Extract citation tokens like [S1], [S2] from the answer.
    Returns a deduped list preserving first-seen order.
    """
    found = re.findall(r"\[S(\d+)\]", answer or "")
    seen = set()
    out = []
    for n in found:
        key = f"S{n}"
        if key not in seen:
            seen.add(key)
            out.append(key)
    return out


def ask_kb(kb_id: str, query: str) -> Dict[str, Any]:
    """
    Call backend /ask-kb and return JSON payload.
    """
    url = f"{BACKEND}/ask-kb"
    resp = requests.post(url, params={"kb_id": kb_id, "query": query}, timeout=60)
    resp.raise_for_status()
    return resp.json()


def fetch_chunk(kb_id: str, chunk_id: str) -> Dict[str, Any]:
    """
    Fetch a chunk evidence payload by chunk_id.
    Note: path params may require URL encoding if chunk_id contains ':'.
    If you expose query version (/kb/chunk?kb_id=...&chunk_id=...), use that instead.
    """
    # safer encoding:
    url = f"{BACKEND}/kb/{kb_id}/chunk/{requests.utils.quote(chunk_id, safe='')}"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.json()


def source_label(sources: List[Dict[str, Any]], sid: str) -> str:
    """
    Build a human-readable label for a source (page/filename).
    """
    for s in sources:
        if s.get("source_id") == sid:
            page_label = s.get("page_label")
            filename = s.get("filename")
            if page_label and filename:
                return f"{sid} · p{page_label} · {filename}"
            if page_label:
                return f"{sid} · p{page_label}"
            return sid
    return sid


# -------------------------
# 2) UI
# -------------------------

st.set_page_config(page_title="RAG KB Chat", layout="wide")
st.title("RAG Knowledge Base · Clickable Citations (Day 11)")

# session state init
if "chunk_cache" not in st.session_state:
    st.session_state["chunk_cache"] = {}  # chunk_id -> payload
if "selected_source" not in st.session_state:
    st.session_state["selected_source"] = None
if "last_result" not in st.session_state:
    st.session_state["last_result"] = None

col_left, col_right = st.columns([1.4, 1.0])

with col_left:
    st.subheader("Ask")
    kb_id = st.text_input("KB ID", value="demo")
    query = st.text_input("Query", value="What is the plan for?")
    if st.button("Ask KB"):
        try:
            result = ask_kb(kb_id=kb_id, query=query)
            st.session_state["last_result"] = result
            st.session_state["selected_source"] = None
        except requests.HTTPError as e:
            st.error(f"Backend error: {e}")
        except requests.RequestException as e:
            st.error(f"Network error: {e}")

    result = st.session_state["last_result"]
    if result:
        answer = result.get("answer", "")
        sources = result.get("sources", [])
        source_map = result.get("source_map", {})  # Day9 you added
        citations = parse_citations(answer)

        st.markdown("### Answer")
        st.markdown(answer)

        st.markdown("### Citations")
        if not citations:
            st.info("No citations found in answer.")
        else:
            for sid in citations:
                label = source_label(sources, sid)
                if st.button(label, key=f"btn_{sid}"):
                    st.session_state["selected_source"] = sid

with col_right:
    st.subheader("Evidence Panel")

    result = st.session_state["last_result"]
    if not result:
        st.info("Ask a question to see evidence.")
    else:
        sources = result.get("sources", [])
        source_map = result.get("source_map", {})
        sid = st.session_state["selected_source"]

        if not sid:
            st.info("Click a citation (S1/S2/...) to open evidence.")
        else:
            chunk_id = source_map.get(sid)
            if not chunk_id:
                st.error(f"Missing source_map for {sid}.")
            else:
                # cache
                cache: Dict[str, Any] = st.session_state["chunk_cache"]
                if chunk_id not in cache:
                    try:
                        cache[chunk_id] = fetch_chunk(kb_id=kb_id, chunk_id=chunk_id)
                    except requests.HTTPError as e:
                        st.error(f"Backend error while loading chunk: {e}")
                    except requests.RequestException as e:
                        st.error(f"Network error while loading chunk: {e}")

                payload = cache.get(chunk_id)
                if payload:
                    md = payload.get("metadata", {})
                    st.markdown(f"**Source:** {sid}")
                    st.markdown(f"**chunk_id:** `{payload.get('chunk_id')}`")
                    st.markdown(f"**filename:** {md.get('filename')}")
                    st.markdown(f"**page_label:** {md.get('page_label')}")
                    st.markdown("---")
                    with st.expander("Show full chunk text", expanded=True):
                        st.write(payload.get("content") or payload.get("page_content") or "")