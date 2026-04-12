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
    SavedLocationDB,
    ConversationSessionDB,
    # 灰度配置模型
    FeatureFlagDB,
    ABExperimentDB,
    UserExperimentAssignmentDB,
)
from db.repositories import UserRepository, MatchHistoryRepository
from db.autonomous_models import (
    HeartbeatRuleStateDB,
    PushHistoryDB,
    TriggerEventDB,
    UserPushPreferencesDB,
    init_autonomous_tables,
)

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
    "ConversationSessionDB",
    "UserRepository",
    "MatchHistoryRepository",
    # 自主代理引擎模型
    "HeartbeatRuleStateDB",
    "PushHistoryDB",
    "TriggerEventDB",
    "UserPushPreferencesDB",
    "init_autonomous_tables",
    # 灰度配置模型
    "FeatureFlagDB",
    "ABExperimentDB",
    "UserExperimentAssignmentDB",
]
