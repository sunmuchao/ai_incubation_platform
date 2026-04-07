"""
P5 WebSocket 实时消息服务

提供:
- WebSocket 连接管理
- 在线状态追踪
- 实时消息推送
- 离线消息处理
"""

import uuid
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any
from collections import defaultdict

from sqlalchemy.orm import Session
from fastapi import WebSocket

from models.websocket_models import (
    WebSocketConnectionDB, UserPresenceDB, OfflineMessageDB,
    ConnectionStatus, MessageType
)
from models.db_models import UserDB


class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        # 存储活跃连接：user_id -> set of websocket
        self.active_connections: Dict[str, Set[WebSocket]] = defaultdict(set)
        # 存储连接到用户的映射：connection_id -> user_id
        self.connection_to_user: Dict[str, str] = {}
        # 存储用户到连接 ID 的映射：user_id -> set of connection_id
        self.user_connections: Dict[str, Set[str]] = defaultdict(set)

    async def connect(
        self,
        websocket: WebSocket,
        user_id: str,
        connection_id: str,
        tenant_id: str
    ) -> None:
        """接受 WebSocket 连接"""
        await websocket.accept()
        self.active_connections[user_id].add(websocket)
        self.connection_to_user[connection_id] = user_id
        self.user_connections[user_id].add(connection_id)

    def disconnect(
        self,
        websocket: WebSocket,
        user_id: str,
        connection_id: str
    ) -> None:
        """断开 WebSocket 连接"""
        if websocket in self.active_connections[user_id]:
            self.active_connections[user_id].remove(websocket)
        if connection_id in self.user_connections[user_id]:
            self.user_connections[user_id].remove(connection_id)
        if connection_id in self.connection_to_user:
            del self.connection_to_user[connection_id]

        # 如果用户没有活跃连接了，清理
        if not self.active_connections[user_id]:
            del self.active_connections[user_id]
            if user_id in self.user_connections:
                del self.user_connections[user_id]

    async def send_personal_message(
        self,
        user_id: str,
        message: dict
    ) -> int:
        """
        发送个人消息给用户的所有连接

        Returns:
            int: 成功发送的连接数
        """
        sent_count = 0
        if user_id in self.active_connections:
            for websocket in self.active_connections[user_id]:
                try:
                    await websocket.send_json(message)
                    sent_count += 1
                except Exception:
                    # 连接已断开，不处理
                    pass
        return sent_count

    async def broadcast_to_tenant(
        self,
        tenant_id: str,
        message: dict
    ) -> int:
        """
        广播消息给租户的所有用户

        Returns:
            int: 成功发送的连接数
        """
        sent_count = 0
        for user_id, websockets in self.active_connections.items():
            # TODO: 需要验证用户是否属于该租户
            for websocket in websockets:
                try:
                    await websocket.send_json(message)
                    sent_count += 1
                except Exception:
                    pass
        return sent_count

    def get_online_users(self) -> Set[str]:
        """获取所有在线用户 ID"""
        return set(self.active_connections.keys())

    def is_user_online(self, user_id: str) -> bool:
        """检查用户是否在线"""
        return user_id in self.active_connections and len(self.active_connections[user_id]) > 0

    def get_user_connection_count(self, user_id: str) -> int:
        """获取用户的连接数"""
        return len(self.active_connections.get(user_id, set()))


class WebSocketService:
    """WebSocket 服务"""

    def __init__(self, db: Session, connection_manager: ConnectionManager = None):
        self.db = db
        self.connection_manager = connection_manager or ConnectionManager()

    # ============== 连接管理 ==============

    def register_connection(
        self,
        user_id: str,
        tenant_id: str,
        connection_id: str,
        session_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> WebSocketConnectionDB:
        """注册 WebSocket 连接"""
        connection = WebSocketConnectionDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            tenant_id=tenant_id,
            connection_id=connection_id,
            session_id=session_id,
            client_ip=client_ip,
            user_agent=user_agent,
            status=ConnectionStatus.ONLINE,
            is_active=True
        )

        self.db.add(connection)

        # 更新用户在线状态
        self._update_user_presence(user_id, tenant_id, ConnectionStatus.ONLINE)

        self.db.commit()
        self.db.refresh(connection)

        return connection

    def unregister_connection(
        self,
        user_id: str,
        tenant_id: str,
        connection_id: str
    ) -> None:
        """注销 WebSocket 连接"""
        # 更新连接记录
        connection = self.db.query(WebSocketConnectionDB).filter(
            WebSocketConnectionDB.connection_id == connection_id,
            WebSocketConnectionDB.user_id == user_id
        ).first()

        if connection:
            connection.status = ConnectionStatus.OFFLINE
            connection.disconnected_at = datetime.utcnow()
            connection.is_active = False

        # 检查用户是否还有其他活跃连接
        active_count = self.db.query(WebSocketConnectionDB).filter(
            WebSocketConnectionDB.user_id == user_id,
            WebSocketConnectionDB.is_active == True
        ).count()

        if active_count == 0:
            # 用户完全离线
            self._update_user_presence(user_id, tenant_id, ConnectionStatus.OFFLINE)

        self.db.commit()

    def update_connection_activity(
        self,
        connection_id: str
    ) -> None:
        """更新连接活跃时间"""
        connection = self.db.query(WebSocketConnectionDB).filter(
            WebSocketConnectionDB.connection_id == connection_id
        ).first()

        if connection:
            connection.last_seen_at = datetime.utcnow()
            connection.is_active = True
            self.db.commit()

    # ============== 在线状态 ==============

    def _update_user_presence(
        self,
        user_id: str,
        tenant_id: str,
        status: ConnectionStatus,
        custom_status: Optional[str] = None
    ) -> UserPresenceDB:
        """更新用户在线状态"""
        presence = self.db.query(UserPresenceDB).filter(
            UserPresenceDB.user_id == user_id
        ).first()

        if presence:
            presence.status = status
            presence.is_active = status == ConnectionStatus.ONLINE
            presence.last_active_at = datetime.utcnow() if status == ConnectionStatus.ONLINE else None
            if custom_status:
                presence.custom_status = custom_status
        else:
            presence = UserPresenceDB(
                id=str(uuid.uuid4()),
                user_id=user_id,
                tenant_id=tenant_id,
                status=status,
                is_active=status == ConnectionStatus.ONLINE,
                last_active_at=datetime.utcnow() if status == ConnectionStatus.ONLINE else None,
                custom_status=custom_status
            )
            self.db.add(presence)

        self.db.commit()
        self.db.refresh(presence)
        return presence

    def set_user_status(
        self,
        user_id: str,
        tenant_id: str,
        status: ConnectionStatus,
        custom_status: Optional[str] = None
    ) -> UserPresenceDB:
        """设置用户在线状态"""
        return self._update_user_presence(user_id, tenant_id, status, custom_status)

    def get_user_presence(self, user_id: str) -> Optional[UserPresenceDB]:
        """获取用户在线状态"""
        return self.db.query(UserPresenceDB).filter(
            UserPresenceDB.user_id == user_id
        ).first()

    def get_tenant_online_users(self, tenant_id: str) -> List[UserPresenceDB]:
        """获取租户在线用户列表"""
        return self.db.query(UserPresenceDB).filter(
            UserPresenceDB.tenant_id == tenant_id,
            UserPresenceDB.status == ConnectionStatus.ONLINE
        ).all()

    # ============== 离线消息 ==============

    def store_offline_message(
        self,
        recipient_id: str,
        tenant_id: str,
        message_type: MessageType,
        content: str,
        sender_id: Optional[str] = None,
        title: Optional[str] = None,
        data: Optional[dict] = None
    ) -> OfflineMessageDB:
        """存储离线消息"""
        offline_message = OfflineMessageDB(
            id=str(uuid.uuid4()),
            recipient_id=recipient_id,
            sender_id=sender_id,
            tenant_id=tenant_id,
            message_type=message_type,
            title=title,
            content=content,
            data=json.dumps(data) if data else None
        )

        self.db.add(offline_message)
        self.db.commit()
        self.db.refresh(offline_message)

        return offline_message

    async def send_message(
        self,
        recipient_id: str,
        message_type: MessageType,
        content: str,
        sender_id: Optional[str] = None,
        title: Optional[str] = None,
        data: Optional[dict] = None
    ) -> dict:
        """
        发送消息（实时或离线）

        Returns:
            dict: 发送结果
        """
        # 获取接收者租户 ID
        user = self.db.query(UserDB).filter(UserDB.id == recipient_id).first()
        if not user:
            raise ValueError(f"User {recipient_id} not found")
        tenant_id = user.tenant_id

        # 尝试实时推送
        sent_count = await self.connection_manager.send_personal_message(
            recipient_id,
            {
                "type": "message",
                "message_type": message_type.value,
                "title": title,
                "content": content,
                "data": data,
                "sender_id": sender_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

        if sent_count > 0:
            # 实时推送成功
            return {
                "status": "delivered",
                "sent_to_connections": sent_count
            }
        else:
            # 用户离线，存储为离线消息
            self.store_offline_message(
                recipient_id=recipient_id,
                tenant_id=tenant_id,
                sender_id=sender_id,
                message_type=message_type,
                content=content,
                title=title,
                data=data
            )
            return {
                "status": "stored_offline",
                "recipient_offline": True
            }

    def get_offline_messages(
        self,
        user_id: str,
        limit: int = 50
    ) -> List[OfflineMessageDB]:
        """获取用户的离线消息"""
        return self.db.query(OfflineMessageDB).filter(
            OfflineMessageDB.recipient_id == user_id,
            OfflineMessageDB.is_delivered == False
        ).order_by(OfflineMessageDB.created_at.desc()).limit(limit).all()

    def mark_message_delivered(self, message_id: str) -> None:
        """标记消息已投递"""
        message = self.db.query(OfflineMessageDB).filter(
            OfflineMessageDB.id == message_id
        ).first()

        if message and not message.is_delivered:
            message.is_delivered = True
            message.delivered_at = datetime.utcnow()
            message.delivery_attempts += 1
            self.db.commit()

    def mark_message_read(self, message_id: str) -> None:
        """标记消息已读"""
        message = self.db.query(OfflineMessageDB).filter(
            OfflineMessageDB.id == message_id
        ).first()

        if message:
            message.is_read = True
            message.read_at = datetime.utcnow()
            self.db.commit()

    def mark_all_messages_read(self, user_id: str) -> int:
        """标记用户所有消息为已读"""
        messages = self.db.query(OfflineMessageDB).filter(
            OfflineMessageDB.recipient_id == user_id,
            OfflineMessageDB.is_read == False
        ).all()

        count = len(messages)
        for message in messages:
            message.is_read = True
            message.read_at = datetime.utcnow()

        self.db.commit()
        return count

    # ============== 通知类型消息 ==============

    async def send_order_update(
        self,
        recipient_id: str,
        order_id: str,
        update_type: str,
        content: str,
        data: Optional[dict] = None
    ) -> dict:
        """发送订单更新通知"""
        return await self.send_message(
            recipient_id=recipient_id,
            message_type=MessageType.ORDER_UPDATE,
            content=content,
            title=f"订单 {update_type}",
            data={"order_id": order_id, **(data or {})}
        )

    async def send_dispute_update(
        self,
        recipient_id: str,
        dispute_id: str,
        update_type: str,
        content: str,
        data: Optional[dict] = None
    ) -> dict:
        """发送争议更新通知"""
        return await self.send_message(
            recipient_id=recipient_id,
            message_type=MessageType.DISPUTE_UPDATE,
            content=content,
            title=f"争议 {update_type}",
            data={"dispute_id": dispute_id, **(data or {})}
        )

    async def send_proposal_update(
        self,
        recipient_id: str,
        proposal_id: str,
        update_type: str,
        content: str,
        data: Optional[dict] = None
    ) -> dict:
        """发送提案更新通知"""
        return await self.send_message(
            recipient_id=recipient_id,
            message_type=MessageType.PROPOSAL_UPDATE,
            content=content,
            title=f"提案 {update_type}",
            data={"proposal_id": proposal_id, **(data or {})}
        )

    async def send_system_notification(
        self,
        recipient_id: str,
        title: str,
        content: str,
        data: Optional[dict] = None
    ) -> dict:
        """发送系统通知"""
        return await self.send_message(
            recipient_id=recipient_id,
            message_type=MessageType.SYSTEM,
            content=content,
            title=title,
            data=data
        )


# 全局连接管理器实例
_manager = ConnectionManager()


def get_connection_manager() -> ConnectionManager:
    """获取连接管理器实例"""
    return _manager


# 依赖注入
from config.database import get_db
from fastapi import Depends

def get_websocket_service(db: Session) -> WebSocketService:
    """获取 WebSocket 服务实例"""
    return WebSocketService(db, _manager)
