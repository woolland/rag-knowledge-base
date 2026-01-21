import streamlit as st
import requests

st.set_page_config(page_title="RAG Knowledge Base", layout="centered")

st.title("RAG Knowledge Base")
#st.caption("Day 2 · Frontend Skeleton")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display previous messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input box
user_input = st.chat_input("Ask something...")

if user_input:
    # Show user message
    st.session_state.messages.append(
        {"role": "user", "content": user_input}
    )
    with st.chat_message("user"):
        st.markdown(user_input)

    # Call backend /chat endpoint
    try:
        response = requests.post(
            "http://127.0.0.1:8000/chat",
            json={"query": user_input},
            timeout=10,
        )
        response.raise_for_status()
        answer = response.json().get("answer", "No answer")

    except Exception as e:
        answer = f"Error calling backend: {e}"

    # Show assistant message
    st.session_state.messages.append(
        {"role": "assistant", "content": answer}
    )
    with st.chat_message("assistant"):
        st.markdown(answer)