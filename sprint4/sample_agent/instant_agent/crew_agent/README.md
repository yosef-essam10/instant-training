# Instant AI Agent - Multi-Agent Procurement Assistant

A CrewAI-based multi-agent chatbot that searches, compares, and recommends
products from a local CSV catalog, with a Streamlit chat UI (with logo) and
MongoDB-backed chat history.

## How it works

- **`data/products.csv`** and **`data/company_context.csv`** hold the catalog
  and procurement policy. `knowledge_base.py` reads them directly with the
  built-in `csv` module — no external calls, so responses are fast and cheap
  on tokens.
- **`agent.py`** defines a 3-agent CrewAI crew that runs sequentially:
  1. **Search Agent** - finds matching products via a tool over the CSV catalog.
  2. **Analysis Agent** - ranks candidates by a price/rating value score.
  3. **Report Agent** - writes the final organized reply (Arabic or English,
     matching the user's language).
- **`database.py`** stores chats and messages in MongoDB (`chats` and
  `messages` collections) so the sidebar can list past conversations.
- **`app.py`** is the Streamlit chat interface, showing the logo in the
  sidebar and above the title, same layout as the reference screenshot.
- **`secret_config.py`** holds all credentials directly (Mongo URI, Groq key).

## Setup

1. Create a virtual environment and install dependencies:

   ```bash
   python -m venv venv
   venv\Scripts\activate        # Windows
   source venv/bin/activate     # macOS/Linux

   pip install -r requirements.txt
   ```

2. Run the app:

   ```bash
   streamlit run app.py
   ```

   ⚠️ **Security note:** the Groq key and Mongo password were shared in plain
   text in chat, so they're no longer private. Rotate/regenerate both in the
   Groq console and MongoDB Atlas, then update the values at the top of
   `secret_config.py`. Don't push this file to a public repository.

## Editing the product catalog

Edit `data/products.csv` directly to add/change products. Each row is one
product; the `specs` column packs key:value pairs separated by `|`
(e.g. `cpu:Intel i5|ram:16GB|storage:512GB SSD`). No generation script is
needed — the agent's tools read this file straight through
`knowledge_base.py`.

Edit `data/company_context.csv` (a simple `field,value` table) to change
procurement policy/context used by the agents.

## Project structure

```
instant_ai_agent/
├── agent.py              # CrewAI agents, tools, and crew runner
├── app.py                # Streamlit chat UI
├── database.py            # MongoDB chat/message persistence
├── knowledge_base.py       # CSV data loader + search/rank helpers
├── secret_config.py        # Credentials + settings
├── requirements.txt
├── data/
│   ├── products.csv
│   └── company_context.csv
└── assets/
    └── logo.png           # App logo shown in sidebar and header
```
