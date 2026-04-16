"""
SQLAlchemy 数据模型 - 通知领域

事件驱动主动通知系统：
- UserNotificationPreferenceDB: 用户偏好订阅表
- PendingNotificationDB: 通知队列表

架构说明：
- 新用户注册时触发检查，匹配偏好则写入队列
- Agent 对话开始时检查队列，主动推送通知
- 纯逻辑匹配，不用 AI，节省 Token
"""
from db.models.base import *

from datetime import datetime
import json


class UserNotificationPreferenceDB(Base):
    """用户通知偏好订阅表

    用户表达偏好（如"有深圳新人通知我"）时写入此表。

    示例：
    - trigger_type: "new_user_match"（新用户匹配）
    - conditions_json: {"location": "深圳", "gender": "female"}
    """
    __tablename__ = "user_notification_preferences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), nullable=False, index=True)  # 订阅用户
    trigger_type = Column(String(50), nullable=False, index=True)  # 触发类型
    conditions_json = Column(Text, default="{}")  # 匹配条件（JSON）
    is_active = Column(Boolean, default=True, index=True)  # 是否激活
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 唯一约束：同一用户同一类型只能有一条订阅
    __table_args__ = (
        # SQLite 不支持部分索引，用普通唯一约束
        # UniqueConstraint('user_id', 'trigger_type', name='uix_user_trigger'),
    )


class PendingNotificationDB(Base):
    """待推送通知队列表

    事件触发后写入此表，Agent 对话时检查并推送。

    状态流转：
    - pending → delivered → read
    """
    __tablename__ = "pending_notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    target_user_id = Column(String(36), nullable=False, index=True)  # 被通知的用户
    trigger_user_id = Column(String(36), nullable=True, index=True)  # 触发事件的用户（新注册的人）
    trigger_type = Column(String(50), nullable=False, index=True)  # 触发类型
    payload_json = Column(Text, default="{}")  # 通知内容（JSON）
    status = Column(String(20), default="pending", index=True)  # pending, delivered, read
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    delivered_at = Column(DateTime(timezone=True), nullable=True)  # 推送时间

    # 复合索引：快速查询某用户的待推送通知
    __table_args__ = (
        # Index('ix_target_status', 'target_user_id', 'status'),
    )


# ========== 支持的触发类型 ==========

TRIGGER_TYPES = {
    "new_user_match": "新用户匹配",
    "mutual_like": "互相喜欢",
    "message_reply": "对方回复了",
    "date_reminder": "约会提醒",
    "match_score_high": "高匹配度用户",
}

# ========== 匹配条件字段 ==========

MATCHABLE_FIELDS = [
    "location",       # 地点
    "gender",         # 性别
    "age_range",      # 年龄范围（格式："25-30"）
    "relationship_goal",  # 关系目标
    "interests",      # 兴趣（数组）
]


__all__ = [
    "UserNotificationPreferenceDB",
    "PendingNotificationDB",
    "TRIGGER_TYPES",
    "MATCHABLE_FIELDS",
]