import datetime
import uuid
from pymongo import MongoClient
from secret_config import MONGO_URI, MONGO_DB_NAME

_client = MongoClient(MONGO_URI)
_db = _client[MONGO_DB_NAME]
_chats = _db["chats"]


def create_chat(title="New Chat"):
    chat_id = str(uuid.uuid4())
    doc = {
        "chat_id": chat_id,
        "title": title,
        "created_at": datetime.datetime.utcnow(),
        "messages": [],
    }
    _chats.insert_one(doc)
    return chat_id


def get_all_chats():
    cursor = _chats.find({}, {"chat_id": 1, "title": 1, "created_at": 1}).sort("created_at", -1)
    return list(cursor)


def get_chat(chat_id):
    return _chats.find_one({"chat_id": chat_id})


def add_message(chat_id, role, content):
    message = {
        "role": role,
        "content": content,
        "timestamp": datetime.datetime.utcnow(),
    }
    _chats.update_one({"chat_id": chat_id}, {"$push": {"messages": message}})


def rename_chat(chat_id, title):
    _chats.update_one({"chat_id": chat_id}, {"$set": {"title": title}})


def delete_chat(chat_id):
    _chats.delete_one({"chat_id": chat_id})


def set_title_from_first_message(chat_id, text):
    chat = get_chat(chat_id)
    if chat and chat.get("title") == "New Chat":
        short_title = text.strip()[:40]
        rename_chat(chat_id, short_title if short_title else "New Chat")
