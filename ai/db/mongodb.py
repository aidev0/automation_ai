import os
from typing import List, Dict, Any, Optional
from pymongo import MongoClient

MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE")

def get_client() -> MongoClient:
    """Get MongoDB client."""
    return MongoClient(MONGODB_URI)

def get_db():
    """Get database instance."""
    client = get_client()
    return client[MONGODB_DATABASE]

def get_all_users() -> List[Dict[str, Any]]:
    """Get all users."""
    db = get_db()
    return list(db.users.find())

def get_all_chats(user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get all chats, optionally filtered by user_id."""
    db = get_db()
    query = {"user_id": user_id} if user_id else {}
    return list(db.chats.find(query))

def get_all_messages(chat_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get all messages, optionally filtered by chatId."""
    db = get_db()
    query = {"chatId": chat_id} if chat_id else {}
    return list(db.messages.find(query)) 