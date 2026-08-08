import os
import json
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv
from tools import search_products, scrape_all, clean_products
from crew import run_comparison_and_report
from database import save_message, get_session_messages, list_sessions, create_session_id, delete_session

load_dotenv()

st.set_page_config(page_title="Instant Procurement Assistant", page_icon="🛒", layout="wide")

st.markdown("""
<style>
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #2b1055 0%, #43408f 100%);
}
section[data-testid="stSidebar"] * {
    color: #f5f5f7 !important;
}
section[data-testid="stSidebar"] input,
section[data-testid="stSidebar"] textarea {
    color: #1a1a1a !important;
    background-color: #ffffff !important;
}
.stButton>button {
    background: linear-gradient(90deg, #ff6a00, #ee0979);
    color: #ffffff !important;
    border: none;
    border-radius: 10px;
    padding: 0.5em 1.2em;
    font-weight: 600;
}
.stButton>button:hover {
    opacity: 0.85;
}
.chat-bubble-user {
    background: #2563eb;
    color: #ffffff;
    padding: 12px 16px;
    border-radius: 16px 16px 0 16px;
    margin: 8px 0;
    max-width: 85%;
    margin-left: auto;
}
.chat-bubble-assistant {
    background: #f3e8ff;
    color: #3b0764;
    padding: 12px 16px;
    border-radius: 16px 16px 16px 0;
    margin: 8px 0;
    max-width: 85%;
}
.product-card {
    background: rgba(147, 51, 234, 0.08);
    border: 1px solid rgba(147, 51, 234, 0.25);
    border-left: 5px solid #ff6a00;
    border-radius: 14px;
    padding: 16px;
    margin-bottom: 12px;
    color: inherit;
}
</style>
""", unsafe_allow_html=True)

if "session_id" not in st.session_state:
    st.session_state.session_id = create_session_id()
if "messages" not in st.session_state:
    st.session_state.messages = []
if "company_context" not in st.session_state:
    with open("config/company.json", "r") as f:
        st.session_state.company_context = json.load(f)

with st.sidebar:
    st.title("Instant 🛒")
    st.subheader("Company Context")
    ctx = st.session_state.company_context
    ctx["company"] = st.text_input("Company", ctx.get("company", "ABC"))
    ctx["budget"] = st.number_input("Budget ($)", value=float(ctx.get("budget", 1000)))
    ctx["product"] = st.text_input("Product", ctx.get("product", "Laptop"))
    ctx["minimum_ram"] = st.text_input("Minimum RAM", ctx.get("minimum_ram", "16GB"))
    ctx["preferred_cpu"] = st.text_input("Preferred CPU", ctx.get("preferred_cpu", "Intel i7 or Ryzen 7"))
    ctx["weight_price"] = st.slider("Price Weight", 0.0, 1.0, float(ctx.get("weight_price", 0.4)))
    ctx["weight_specs"] = round(1 - ctx["weight_price"], 2)
    st.caption(f"Specs weight: {ctx['weight_specs']}")

    st.divider()
    st.subheader("Sessions")
    for sid in list_sessions():
        cols = st.columns([4, 1])
        if cols[0].button(sid, key=f"load_{sid}"):
            st.session_state.session_id = sid
            history = get_session_messages(sid)
            st.session_state.messages = [
                {"role": h["role"], "content": h["content"], "html_report": h.get("html_report")}
                for h in history
            ]
            st.rerun()
        if cols[1].button("🗑", key=f"del_{sid}"):
            delete_session(sid)
            st.rerun()

    if st.button("New Chat"):
        st.session_state.session_id = create_session_id()
        st.session_state.messages = []
        st.rerun()

st.title("Instant Procurement Assistant")
st.caption("Multi-agent product research, comparison and reporting")

for msg in st.session_state.messages:
    bubble_class = "chat-bubble-user" if msg["role"] == "user" else "chat-bubble-assistant"
    st.markdown(f'<div class="{bubble_class}" dir="auto">{msg["content"]}</div>', unsafe_allow_html=True)
    if msg.get("html_report"):
        with st.expander("View Full Report"):
            components.html(msg["html_report"], height=600, scrolling=True)

query = st.chat_input("Ask for a product procurement search, e.g. Best laptops under 1000$")

if query:
    st.session_state.messages.append({"role": "user", "content": query})
    save_message(st.session_state.session_id, "user", query)
    st.markdown(f'<div class="chat-bubble-user" dir="auto">{query}</div>', unsafe_allow_html=True)

    with st.status("Running procurement pipeline...", expanded=True) as status:
        st.write("🔎 Searching products with Tavily")
        search_results = search_products(query)

        st.write(f"🌐 Extracting {len(search_results)} product pages")
        raw_products = scrape_all(search_results)

        st.write("🧹 Cleaning and normalizing data")
        products = clean_products(raw_products)

        st.write("⚖️ Comparing and ranking with Groq")
        ranking, html_report = run_comparison_and_report(products, st.session_state.company_context)

        status.update(label="Pipeline complete", state="complete")

    if products:
        st.subheader("Scraped Products")
        cols = st.columns(2)
        for i, product in enumerate(products):
            with cols[i % 2]:
                st.markdown(f"""
                <div class="product-card">
                <b>{product.get('name', 'Unknown')}</b><br>
                💵 {product.get('price', 'N/A')} | 🧠 {product.get('cpu', 'N/A')} | 💾 {product.get('ram', 'N/A')}
                </div>
                """, unsafe_allow_html=True)

    top_name = ranking[0]["name"] if ranking else "N/A"
    summary = f"Found and ranked {len(products)} products. Top pick: {top_name}."
    st.markdown(f'<div class="chat-bubble-assistant" dir="auto">{summary}</div>', unsafe_allow_html=True)

    with st.expander("View Full Report", expanded=True):
        components.html(html_report, height=600, scrolling=True)
        st.download_button("Download HTML Report", html_report, file_name="procurement_report.html", mime="text/html")

    st.session_state.messages.append({"role": "assistant", "content": summary, "html_report": html_report})
    save_message(st.session_state.session_id, "assistant", summary, html_report=html_report)