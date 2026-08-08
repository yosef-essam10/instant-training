import os
from datetime import datetime
from pymongo import MongoClient


def get_client():
    return MongoClient(os.getenv("MONGO_URI"))


def get_db():
    client = get_client()
    return client[os.getenv("MONGO_DB_NAME", "crew_rag")]


def save_message(session_id, role, content, html_report=None):
    db = get_db()
    document = {
        "session_id": session_id,
        "role": role,
        "content": content,
        "timestamp": datetime.utcnow(),
    }
    if html_report:
        document["html_report"] = html_report
    db.chats.insert_one(document)


def get_session_messages(session_id):
    db = get_db()
    return list(db.chats.find({"session_id": session_id}).sort("timestamp", 1))


def list_sessions():
    db = get_db()
    return db.chats.distinct("session_id")


def delete_session(session_id):
    db = get_db()
    db.chats.delete_many({"session_id": session_id})


def create_session_id():
    return datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
