"""
数据库模块导出 - P3 增强版
"""
from db.database import get_db, init_db, engine, Base
from db.models import (
    UserDB,
    MatchHistoryDB,
    ConversationDB,
    BehaviorEventDB,
    UserProfileUpdateDB,
    RelationshipProgressDB,
    SavedLocationDB
)
from db.repositories import UserRepository, MatchHistoryRepository

__all__ = [
    "get_db",
    "init_db",
    "engine",
    "Base",
    "UserDB",
    "MatchHistoryDB",
    "ConversationDB",
    "BehaviorEventDB",
    "UserProfileUpdateDB",
    "RelationshipProgressDB",
    "SavedLocationDB",
    "UserRepository",
    "MatchHistoryRepository",
]
