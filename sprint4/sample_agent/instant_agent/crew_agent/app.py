"""
app.py
------
Streamlit chat interface for the Instant AI Agent (procurement assistant).
Run with:  streamlit run app.py
"""

import os
import base64
import streamlit as st

import database as db
from agent import run_procurement_agent
from secret_config import APP_TITLE, LOGO_PATH

st.set_page_config(page_title=APP_TITLE, page_icon="🤖", layout="wide")

# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .stApp { direction: auto; }

    .chat-bubble-user, .chat-bubble-agent {
        padding: 14px 18px;
        border-radius: 14px;
        margin: 8px 0;
        max-width: 85%;
        line-height: 1.9;
        font-size: 15.5px;
        white-space: pre-wrap;
        unicode-bidi: plaintext;   /* lets mixed Arabic/English render each in its natural direction */
        word-wrap: break-word;
    }

    /* Force readable text color regardless of light/dark theme, on every child element too */
    .chat-bubble-user, .chat-bubble-user * {
        background-color: #eef2f7 !important;
        color: #1f2937 !important;
    }
    .chat-bubble-agent, .chat-bubble-agent * {
        background-color: #ffffff !important;
        color: #1f2937 !important;
    }

    .chat-bubble-user {
        background-color: #eef2f7;
        margin-left: auto;
    }
    .chat-bubble-agent {
        background-color: #ffffff;
        border: 1px solid #e5e7eb;
    }
    .chat-bubble-agent ul, .chat-bubble-agent ol {
        margin: 6px 0;
        padding-inline-start: 22px;
    }
    .chat-bubble-agent strong { color: #102a5e !important; }

    .header-wrap { text-align: center; margin-top: 6px; margin-bottom: 18px; }
    .app-title { font-weight: 700; font-size: 28px; margin-top: 6px; color: inherit; }
    .sidebar-logo-wrap { text-align: center; margin-bottom: 10px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
if "chat_id" not in st.session_state:
    st.session_state.chat_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []


def start_new_chat():
    st.session_state.chat_id = None
    st.session_state.messages = []


def load_chat(chat_id: str):
    st.session_state.chat_id = chat_id
    st.session_state.messages = db.get_messages(chat_id)


@st.cache_data
def get_logo_base64():
    if os.path.exists(LOGO_PATH):
        with open(LOGO_PATH, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None


LOGO_B64 = get_logo_base64()


def logo_html(width: int) -> str:
    if not LOGO_B64:
        return ""
    return f"<img src='data:image/png;base64,{LOGO_B64}' width='{width}' />"


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(f"<div class='sidebar-logo-wrap'>{logo_html(90)}</div>", unsafe_allow_html=True)
    st.markdown(f"### {APP_TITLE}")

    if st.button("➕ New Chat", use_container_width=True):
        start_new_chat()

    st.markdown("---")
    st.markdown("**Past Chats**")

    try:
        chats = db.list_chats()
    except Exception as e:
        chats = []
        st.error(f"MongoDB connection error: {e}")

    for chat in chats:
        col1, col2 = st.columns([5, 1])
        with col1:
            if st.button(chat["title"] or "New Chat", key=f"chat_{chat['id']}", use_container_width=True):
                load_chat(chat["id"])
        with col2:
            if st.button("🗑️", key=f"del_{chat['id']}"):
                db.delete_chat(chat["id"])
                if st.session_state.chat_id == chat["id"]:
                    start_new_chat()
                st.rerun()

# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------
st.markdown(
    f"<div class='header-wrap'>{logo_html(90)}<div class='app-title'>{APP_TITLE}</div></div>",
    unsafe_allow_html=True,
)

for msg in st.session_state.messages:
    css_class = "chat-bubble-user" if msg["role"] == "user" else "chat-bubble-agent"
    st.markdown(f"<div class='{css_class}'>{msg['content']}</div>", unsafe_allow_html=True)

user_input = st.chat_input("Ask about products, prices, comparisons...")

if user_input:
    # Create chat on first message
    if st.session_state.chat_id is None:
        st.session_state.chat_id = db.create_chat(title=user_input)

    st.session_state.messages.append({"role": "user", "content": user_input})
    db.save_message(st.session_state.chat_id, "user", user_input)

    with st.spinner("Thinking..."):
        try:
            reply = run_procurement_agent(user_input, chat_history=st.session_state.messages)
        except Exception as e:
            reply = f" Something went wrong: {e}"

    st.session_state.messages.append({"role": "assistant", "content": reply})
    db.save_message(st.session_state.chat_id, "assistant", reply)

    st.rerun()