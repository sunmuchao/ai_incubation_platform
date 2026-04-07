"""
P5 WebSocket 实时消息 - 数据模型

支持:
- WebSocket 连接管理
- 在线状态追踪
- 离线消息存储
"""

from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from .db_models import Base


class ConnectionStatus(str, enum.Enum):
    """连接状态"""
    ONLINE = "online"  # 在线
    AWAY = "away"  # 离开
    OFFLINE = "offline"  # 离线
    BUSY = "busy"  # 忙碌
    DO_NOT_DISTURB = "do_not_disturb"  # 请勿打扰


class MessageType(str, enum.Enum):
    """消息类型"""
    TEXT = "text"  # 文本消息
    SYSTEM = "system"  # 系统消息
    NOTIFICATION = "notification"  # 通知消息
    ORDER_UPDATE = "order_update"  # 订单更新
    DISPUTE_UPDATE = "dispute_update"  # 争议更新
    PROPOSAL_UPDATE = "proposal_update"  # 提案更新


class WebSocketConnectionDB(Base):
    """WebSocket 连接记录"""
    __tablename__ = "websocket_connections"

    id = Column(String(64), primary_key=True)  # 连接 ID

    # 关联信息
    user_id = Column(String(64), ForeignKey("users.id"), nullable=False)  # 用户 ID
    tenant_id = Column(String(64), ForeignKey("tenants.id"), nullable=False)  # 租户 ID

    # 连接信息
    connection_id = Column(String(128), unique=True, nullable=False, index=True)  # 连接标识
    session_id = Column(String(128), nullable=True)  # 会话 ID
    client_ip = Column(String(45), nullable=True)  # 客户端 IP (支持 IPv6)
    user_agent = Column(String(512), nullable=True)  # 用户代理

    # 状态信息
    status = Column(SQLEnum(ConnectionStatus), default=ConnectionStatus.ONLINE)  # 连接状态
    is_active = Column(Boolean, default=True)  # 是否活跃

    # 时间戳
    connected_at = Column(DateTime, default=datetime.utcnow)  # 连接时间
    last_seen_at = Column(DateTime, default=datetime.utcnow)  # 最后活跃时间
    disconnected_at = Column(DateTime, nullable=True)  # 断开时间

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "connection_id": self.connection_id,
            "status": self.status.value,
            "is_active": self.is_active,
            "client_ip": self.client_ip,
            "connected_at": self.connected_at.isoformat() if self.connected_at else None,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
        }


class UserPresenceDB(Base):
    """用户在线状态"""
    __tablename__ = "user_presence"

    id = Column(String(64), primary_key=True)  # 记录 ID

    # 关联信息
    user_id = Column(String(64), ForeignKey("users.id"), nullable=False, unique=True)  # 用户 ID
    tenant_id = Column(String(64), ForeignKey("tenants.id"), nullable=False)  # 租户 ID

    # 状态信息
    status = Column(SQLEnum(ConnectionStatus), default=ConnectionStatus.OFFLINE)  # 在线状态
    custom_status = Column(String(100), nullable=True)  # 自定义状态消息
    is_active = Column(Boolean, default=False)  # 是否活跃

    # 时间戳
    last_active_at = Column(DateTime, nullable=True)  # 最后活跃时间
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # 更新时间

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "status": self.status.value,
            "custom_status": self.custom_status,
            "is_active": self.is_active,
            "last_active_at": self.last_active_at.isoformat() if self.last_active_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class OfflineMessageDB(Base):
    """离线消息"""
    __tablename__ = "offline_messages"

    id = Column(String(64), primary_key=True)  # 消息 ID

    # 关联信息
    recipient_id = Column(String(64), ForeignKey("users.id"), nullable=False)  # 接收者 ID
    sender_id = Column(String(64), ForeignKey("users.id"), nullable=True)  # 发送者 ID
    tenant_id = Column(String(64), ForeignKey("tenants.id"), nullable=False)  # 租户 ID

    # 消息内容
    message_type = Column(SQLEnum(MessageType), default=MessageType.TEXT)  # 消息类型
    title = Column(String(255), nullable=True)  # 消息标题
    content = Column(Text, nullable=False)  # 消息内容
    data = Column(Text, nullable=True)  # 附加数据 (JSON 字符串)

    # 投递状态
    is_delivered = Column(Boolean, default=False)  # 是否已投递
    is_read = Column(Boolean, default=False)  # 是否已读
    delivery_attempts = Column(Integer, default=0)  # 投递尝试次数

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)  # 创建时间
    delivered_at = Column(DateTime, nullable=True)  # 投递时间
    read_at = Column(DateTime, nullable=True)  # 阅读时间

    def to_dict(self):
        import json
        return {
            "id": self.id,
            "recipient_id": self.recipient_id,
            "sender_id": self.sender_id,
            "message_type": self.message_type.value,
            "title": self.title,
            "content": self.content,
            "data": json.loads(self.data) if self.data else None,
            "is_delivered": self.is_delivered,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "read_at": self.read_at.isoformat() if self.read_at else None,
        }


# 添加关联关系到 db_models
def add_websocket_relationships():
    """添加 WebSocket 关联关系"""
    from .db_models import UserDB, TenantDB

    # UserDB 关联
    if not hasattr(UserDB, 'websocket_connections'):
        UserDB.websocket_connections = relationship("WebSocketConnectionDB", back_populates="user", lazy="dynamic")

    if not hasattr(UserDB, 'presence'):
        UserDB.presence = relationship("UserPresenceDB", back_populates="user", uselist=False, lazy="joined")

    if not hasattr(UserDB, 'offline_messages'):
        UserDB.offline_messages = relationship("OfflineMessageDB", back_populates="recipient", lazy="dynamic")

    # TenantDB 关联
    if not hasattr(TenantDB, 'websocket_connections'):
        TenantDB.websocket_connections = relationship("WebSocketConnectionDB", back_populates="tenant", lazy="dynamic")

    if not hasattr(TenantDB, 'user_presence'):
        TenantDB.user_presence = relationship("UserPresenceDB", back_populates="tenant", lazy="dynamic")


# 建立反向关系
def _add_backrefs():
    """添加反向引用"""
    from .db_models import UserDB, TenantDB

    # WebSocketConnectionDB
    WebSocketConnectionDB.user = relationship("UserDB", back_populates="websocket_connections")
    WebSocketConnectionDB.tenant = relationship("TenantDB", back_populates="websocket_connections")

    # UserPresenceDB
    UserPresenceDB.user = relationship("UserDB", back_populates="presence")
    UserPresenceDB.tenant = relationship("TenantDB", back_populates="user_presence")

    # OfflineMessageDB
    OfflineMessageDB.recipient = relationship("UserDB", back_populates="offline_messages")
    OfflineMessageDB.tenant = relationship("TenantDB", back_populates="offline_messages")
