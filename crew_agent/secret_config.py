"""
secret_config.py
-----------------
Holds all secrets and settings directly.

SECURITY NOTE: these credentials were shared in plain text in chat, which
means they are no longer private. Rotate/regenerate the Groq API key and the
MongoDB password once you're done testing, then update the values below.
Do not share this file or push it to a public repository.
"""

import os

# MongoDB
MONGO_URI = "" #put mongo_string here
MONGO_DB_NAME = "realcrew"
MONGO_CHATS_COLLECTION = "chats"
MONGO_MESSAGES_COLLECTION = "messages"

# Groq LLM
GROQ_API_KEY = "" #put your api here
GROQ_MODEL = "groq/llama-3.3-70b-versatile"

# App
APP_TITLE = "Instant AI Agent"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
LOGO_PATH = os.path.join(ASSETS_DIR, "logo.png")

REQUIRED_VARS = {
    "MONGO_URI": MONGO_URI,
    "GROQ_API_KEY": GROQ_API_KEY,
}


def validate_config():
    """Raise a clear error early if required secrets are missing."""
    missing = [name for name, value in REQUIRED_VARS.items() if not value]
    if missing:
        raise RuntimeError(
            f"Missing required config values: {', '.join(missing)}. "
            "Set them in secret_config.py before running the app."
        )
