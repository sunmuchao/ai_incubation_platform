"""
在线状态追踪服务

提供用户在线状态追踪功能：
- 实时在线状态
- 最后在线时间
- 设备信息记录
- 在线时长统计
"""
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
import logging
import uuid
import json

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.manager import db_manager
from services.websocket_notification_service import websocket_notification_service

logger = logging.getLogger(__name__)


class PresenceInfo:
    """在线状态信息"""
    def __init__(
        self,
        user_id: str,
        is_online: bool,
        last_seen_at: datetime,
        devices: List[str] = None,
        session_count: int = 0
    ):
        self.user_id = user_id
        self.is_online = is_online
        self.last_seen_at = last_seen_at
        self.devices = devices or []
        self.session_count = session_count

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "is_online": self.is_online,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
            "devices": self.devices,
            "session_count": self.session_count,
        }


class OnlinePresenceService:
    """在线状态追踪服务"""

    def __init__(self):
        # 内存缓存：用户 ID -> 在线状态
        self._presence_cache: Dict[str, PresenceInfo] = {}
        # 设备信息：用户 ID -> 设备列表
        self._device_cache: Dict[str, Set[str]] = {}
        # 会话计数
        self._session_counts: Dict[str, int] = {}
        # 在线用户集合
        self._online_users: Set[str] = set()
        # 最后在线时间
        self._last_seen: Dict[str, datetime] = {}

        # 配置
        self._offline_timeout_seconds = 300  # 5 分钟无活动视为离线
        self._cleanup_interval_seconds = 60  # 清理间隔

    async def mark_online(
        self,
        user_id: str,
        device_id: str = None,
        metadata: dict = None
    ) -> PresenceInfo:
        """
        标记用户在线

        Args:
            user_id: 用户 ID
            device_id: 设备 ID（可选）
            metadata: 额外元数据

        Returns:
            PresenceInfo: 在线状态信息
        """
        now = datetime.now()

        # 更新在线状态
        self._online_users.add(user_id)
        self._last_seen[user_id] = now

        # 更新设备信息
        if device_id:
            if user_id not in self._device_cache:
                self._device_cache[user_id] = set()
            self._device_cache[user_id].add(device_id)

        # 更新会话计数
        if user_id not in self._session_counts:
            self._session_counts[user_id] = 0
        self._session_counts[user_id] += 1

        # 更新缓存
        presence = PresenceInfo(
            user_id=user_id,
            is_online=True,
            last_seen_at=now,
            devices=list(self._device_cache.get(user_id, [])),
            session_count=self._session_counts[user_id]
        )
        self._presence_cache[user_id] = presence

        logger.debug(f"用户 {user_id} 标记为在线，设备：{device_id}")
        return presence

    async def mark_offline(
        self,
        user_id: str,
        device_id: str = None
    ) -> Optional[PresenceInfo]:
        """
        标记用户离线

        Args:
            user_id: 用户 ID
            device_id: 设备 ID（可选）

        Returns:
            PresenceInfo: 离线前的状态信息
        """
        if user_id in self._online_users:
            self._online_users.discard(user_id)

        # 移除设备
        if device_id and user_id in self._device_cache:
            self._device_cache[user_id].discard(device_id)
            if not self._device_cache[user_id]:
                del self._device_cache[user_id]

        # 更新最后在线时间
        self._last_seen[user_id] = datetime.now()

        # 更新缓存
        presence = PresenceInfo(
            user_id=user_id,
            is_online=False,
            last_seen_at=self._last_seen[user_id],
            devices=list(self._device_cache.get(user_id, [])),
            session_count=self._session_counts.get(user_id, 0)
        )

        # 从缓存中移除（保留最后状态）
        self._presence_cache[user_id] = presence

        logger.debug(f"用户 {user_id} 标记为离线，设备：{device_id}")
        return presence

    def is_online(self, user_id: str) -> bool:
        """
        检查用户是否在线

        Args:
            user_id: 用户 ID

        Returns:
            bool: 是否在线
        """
        # 优先检查 WebSocket 连接状态
        if websocket_notification_service.is_user_online(user_id):
            return True

        # 检查内存缓存
        return user_id in self._online_users

    def get_presence(self, user_id: str) -> Optional[PresenceInfo]:
        """
        获取用户在线状态

        Args:
            user_id: 用户 ID

        Returns:
            PresenceInfo: 在线状态信息
        """
        if user_id in self._presence_cache:
            return self._presence_cache[user_id]

        # 从 WebSocket 服务获取
        if websocket_notification_service.is_user_online(user_id):
            return PresenceInfo(
                user_id=user_id,
                is_online=True,
                last_seen_at=datetime.now(),
                devices=[],
                session_count=websocket_notification_service.get_user_connection_count(user_id)
            )

        # 返回离线状态
        last_seen = self._last_seen.get(user_id)
        return PresenceInfo(
            user_id=user_id,
            is_online=False,
            last_seen_at=last_seen,
            devices=[],
            session_count=0
        )

    def get_online_users(self) -> List[str]:
        """
        获取所有在线用户

        Returns:
            List[str]: 在线用户 ID 列表
        """
        # 从 WebSocket 服务获取实际的在线用户
        ws_online = set(websocket_notification_service.get_online_users())

        # 合并内存缓存
        all_online = ws_online | self._online_users

        return list(all_online)

    def get_user_count(self) -> int:
        """
        获取在线用户数

        Returns:
            int: 在线用户数
        """
        return len(self.get_online_users())

    def get_user_devices(self, user_id: str) -> List[str]:
        """
        获取用户设备列表

        Args:
            user_id: 用户 ID

        Returns:
            List[str]: 设备 ID 列表
        """
        return list(self._device_cache.get(user_id, set()))

    def get_last_seen(self, user_id: str) -> Optional[datetime]:
        """
        获取用户最后在线时间

        Args:
            user_id: 用户 ID

        Returns:
            datetime: 最后在线时间
        """
        return self._last_seen.get(user_id)

    def get_session_count(self, user_id: str) -> int:
        """
        获取用户会话数

        Args:
            user_id: 用户 ID

        Returns:
            int: 会话数
        """
        return self._session_counts.get(user_id, 0)

    async def cleanup_stale_presence(self) -> int:
        """
        清理过期的在线状态

        Returns:
            int: 清理的用户数
        """
        now = datetime.now()
        cleaned = 0

        # 检查 WebSocket 连接状态
        for user_id in list(self._online_users):
            if not websocket_notification_service.is_user_online(user_id):
                last_seen = self._last_seen.get(user_id)
                if last_seen and (now - last_seen).total_seconds() > self._offline_timeout_seconds:
                    self._online_users.discard(user_id)
                    cleaned += 1
                    logger.debug(f"清理过期在线状态：用户 {user_id}")

        return cleaned

    async def get_presence_stats(self) -> Dict[str, any]:
        """
        获取在线状态统计

        Returns:
            Dict[str, any]: 统计信息
        """
        online_count = self.get_user_count()
        total_users = len(self._presence_cache)

        # 设备分布
        device_distribution = {}
        for user_id, devices in self._device_cache.items():
            device_count = len(devices)
            if device_count > 0:
                device_distribution[device_count] = device_distribution.get(device_count, 0) + 1

        return {
            "online_users": online_count,
            "total_tracked_users": total_users,
            "device_distribution": device_distribution,
            "cleanup_interval_seconds": self._cleanup_interval_seconds,
            "offline_timeout_seconds": self._offline_timeout_seconds,
        }


# 全局服务实例
_presence_service: Optional[OnlinePresenceService] = None


def get_presence_service() -> OnlinePresenceService:
    """获取在线状态服务实例"""
    global _presence_service
    if _presence_service is None:
        _presence_service = OnlinePresenceService()
    return _presence_service
