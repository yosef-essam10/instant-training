"""
database.py
------------
Handles all MongoDB access: creating chats, saving messages, and listing
chat history for the sidebar ("Past Chats").
"""

from datetime import datetime, timezone

from pymongo import MongoClient, DESCENDING
from bson.objectid import ObjectId

from secret_config import (
    MONGO_URI,
    MONGO_DB_NAME,
    MONGO_CHATS_COLLECTION,
    MONGO_MESSAGES_COLLECTION,
)

_client = None


def get_client():
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URI)
    return _client


def get_db():
    return get_client()[MONGO_DB_NAME]


def create_chat(title: str) -> str:
    db = get_db()
    doc = {
        "title": title[:60] if title else "New Chat",
        "created_at": datetime.now(timezone.utc),
    }
    result = db[MONGO_CHATS_COLLECTION].insert_one(doc)
    return str(result.inserted_id)


def list_chats(limit: int = 30):
    db = get_db()
    cursor = (
        db[MONGO_CHATS_COLLECTION]
        .find({})
        .sort("created_at", DESCENDING)
        .limit(limit)
    )
    return [{"id": str(doc["_id"]), "title": doc.get("title", "New Chat")} for doc in cursor]


def delete_chat(chat_id: str):
    db = get_db()
    db[MONGO_CHATS_COLLECTION].delete_one({"_id": ObjectId(chat_id)})
    db[MONGO_MESSAGES_COLLECTION].delete_many({"chat_id": chat_id})


def save_message(chat_id: str, role: str, content: str):
    db = get_db()
    db[MONGO_MESSAGES_COLLECTION].insert_one({
        "chat_id": chat_id,
        "role": role,
        "content": content,
        "created_at": datetime.now(timezone.utc),
    })


def get_messages(chat_id: str):
    db = get_db()
    cursor = (
        db[MONGO_MESSAGES_COLLECTION]
        .find({"chat_id": chat_id})
        .sort("created_at", 1)
    )
    return [{"role": doc["role"], "content": doc["content"]} for doc in cursor]
