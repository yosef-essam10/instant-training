import os
import base64
import streamlit as st
import database as db
from agent import get_agent_reply

st.set_page_config(page_title="Instant AI Agent", page_icon="🤖", layout="wide")

LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "logo.png")

SUGGESTIONS = [
    "I want to start learning AI",
    "What is the Data Science track?",
    "How much does the SOC diploma cost?",
    "Is there any free content?",
    "Compare Frontend vs Fullstack",
]

st.markdown(
    """
    <style>
    [data-testid="stChatMessageContent"] * {
        unicode-bidi: plaintext;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = None


def get_logo_base64():
    if not os.path.exists(LOGO_PATH):
        return None
    with open(LOGO_PATH, "rb") as f:
        return base64.b64encode(f.read()).decode()


LOGO_B64 = get_logo_base64()


def start_new_chat():
    chat_id = db.create_chat()
    st.session_state.current_chat_id = chat_id


def open_chat(chat_id):
    st.session_state.current_chat_id = chat_id


def remove_chat(chat_id):
    db.delete_chat(chat_id)
    if st.session_state.current_chat_id == chat_id:
        st.session_state.current_chat_id = None


def send_message(text):
    if st.session_state.current_chat_id is None:
        start_new_chat()

    chat_id = st.session_state.current_chat_id
    db.add_message(chat_id, "user", text)
    db.set_title_from_first_message(chat_id, text)

    chat = db.get_chat(chat_id)
    history = [{"role": m["role"], "content": m["content"]} for m in chat["messages"]]

    reply = get_agent_reply(history)
    db.add_message(chat_id, "assistant", reply)


with st.sidebar:
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=150)
    st.markdown("### Instant AI Agent")
    st.divider()

    if st.button("New Chat", use_container_width=True):
        start_new_chat()
        st.rerun()

    st.markdown("#### Past Chats")
    for chat in db.get_all_chats():
        col_title, col_delete = st.columns([5, 1])
        with col_title:
            label = chat.get("title") or "New Chat"
            if st.button(label, key=f"open_{chat['chat_id']}", use_container_width=True):
                open_chat(chat["chat_id"])
                st.rerun()
        with col_delete:
            if st.button("🗑", key=f"delete_{chat['chat_id']}"):
                remove_chat(chat["chat_id"])
                st.rerun()

if LOGO_B64:
    st.markdown(
        f"""
        <div style="display:flex;justify-content:center;margin-top:10px;">
            <img src="data:image/png;base64,{LOGO_B64}" style="width:90px;height:90px;border-radius:50%;object-fit:cover;" />
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown(
    "<h1 style='text-align:center;'>Instant AI Agent</h1>",
    unsafe_allow_html=True,
)

if st.session_state.current_chat_id is None:
    st.markdown("<h3 style='text-align:center;'>How can I help you today?</h3>", unsafe_allow_html=True)
    cols = st.columns(len(SUGGESTIONS))
    for col, suggestion in zip(cols, SUGGESTIONS):
        with col:
            if st.button(suggestion, use_container_width=True):
                send_message(suggestion)
                st.rerun()
else:
    chat = db.get_chat(st.session_state.current_chat_id)
    if chat:
        for message in chat["messages"]:
            avatar = LOGO_PATH if message["role"] == "assistant" and os.path.exists(LOGO_PATH) else None
            with st.chat_message(message["role"], avatar=avatar):
                st.markdown(message["content"])

user_input = st.chat_input("Ask about Instant courses, diplomas, prices...")
if user_input:
    send_message(user_input)
    st.rerun()