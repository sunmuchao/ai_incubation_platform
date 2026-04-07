"""
WebSocket 通知推送服务
"""
from typing import Dict, List, Set, Optional
import asyncio
import json
import logging
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
import uuid

logger = logging.getLogger(__name__)


class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        # 用户 ID 到 WebSocket 连接的映射
        self._active_connections: Dict[str, List[WebSocket]] = {}
        # 房间 ID 到用户 ID 列表的映射
        self._rooms: Dict[str, Set[str]] = {}

    async def connect(self, websocket: WebSocket, user_id: str) -> str:
        """接受 WebSocket 连接"""
        await websocket.accept()

        if user_id not in self._active_connections:
            self._active_connections[user_id] = []
        self._active_connections[user_id].append(websocket)

        logger.info(f"用户 {user_id} 建立 WebSocket 连接，当前连接数：{len(self._active_connections[user_id])}")
        return str(uuid.uuid4())

    def disconnect(self, websocket: WebSocket, user_id: str) -> None:
        """断开 WebSocket 连接"""
        if user_id in self._active_connections:
            if websocket in self._active_connections[user_id]:
                self._active_connections[user_id].remove(websocket)

            # 如果没有连接了，删除用户
            if not self._active_connections[user_id]:
                del self._active_connections[user_id]

        logger.info(f"用户 {user_id} 断开 WebSocket 连接")

    async def send_personal_message(self, message: dict, user_id: str) -> None:
        """发送个人消息"""
        if user_id not in self._active_connections:
            return

        disconnected = []
        for websocket in self._active_connections[user_id]:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"发送消息失败：{e}")
                disconnected.append(websocket)

        # 清理断开的连接
        for ws in disconnected:
            if ws in self._active_connections.get(user_id, []):
                self._active_connections[user_id].remove(ws)

    async def broadcast_to_room(self, message: dict, room_id: str) -> None:
        """广播消息到房间"""
        if room_id not in self._rooms:
            return

        for user_id in self._rooms[room_id]:
            await self.send_personal_message(message, user_id)

    def join_room(self, user_id: str, room_id: str) -> None:
        """加入房间"""
        if room_id not in self._rooms:
            self._rooms[room_id] = set()
        self._rooms[room_id].add(user_id)
        logger.info(f"用户 {user_id} 加入房间 {room_id}")

    def leave_room(self, user_id: str, room_id: str) -> None:
        """离开房间"""
        if room_id in self._rooms:
            self._rooms[room_id].discard(user_id)
            logger.info(f"用户 {user_id} 离开房间 {room_id}")

    def get_online_users(self) -> List[str]:
        """获取所有在线用户 ID"""
        return list(self._active_connections.keys())

    def is_user_online(self, user_id: str) -> bool:
        """检查用户是否在线"""
        return user_id in self._active_connections

    def get_user_connection_count(self, user_id: str) -> int:
        """获取用户的连接数"""
        return len(self._active_connections.get(user_id, []))


class WebSocketNotificationService:
    """WebSocket 通知推送服务"""

    def __init__(self):
        self._manager = ConnectionManager()
        self._notification_queue: Dict[str, List[dict]] = {}  # 离线消息队列
        self._max_queue_size = 100  # 每个用户最多缓存 100 条离线消息

    @property
    def manager(self) -> ConnectionManager:
        """获取连接管理器"""
        return self._manager

    async def handle_websocket_connection(
        self,
        websocket: WebSocket,
        user_id: str,
    ) -> None:
        """处理 WebSocket 连接"""
        connection_id = await self._manager.connect(websocket, user_id)

        try:
            # 发送连接成功消息
            await self._manager.send_personal_message({
                "type": "connected",
                "connection_id": connection_id,
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
            }, user_id)

            # 发送离线消息
            await self._send_queued_notifications(user_id)

            # 保持连接并处理消息
            await self._handle_websocket_messages(websocket, user_id)
        except WebSocketDisconnect:
            logger.info(f"用户 {user_id} WebSocket 断开连接")
        except Exception as e:
            logger.error(f"WebSocket 连接异常：{e}")
        finally:
            self._manager.disconnect(websocket, user_id)

    async def _handle_websocket_messages(
        self,
        websocket: WebSocket,
        user_id: str,
    ) -> None:
        """处理 WebSocket 消息"""
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)

                # 处理不同类型的消息
                msg_type = message.get("type")
                if msg_type == "ping":
                    await websocket.send_json({"type": "pong", "timestamp": datetime.now().isoformat()})
                elif msg_type == "join_room":
                    room_id = message.get("room_id")
                    if room_id:
                        self._manager.join_room(user_id, room_id)
                        await websocket.send_json({
                            "type": "room_joined",
                            "room_id": room_id,
                        })
                elif msg_type == "leave_room":
                    room_id = message.get("room_id")
                    if room_id:
                        self._manager.leave_room(user_id, room_id)
                        await websocket.send_json({
                            "type": "room_left",
                            "room_id": room_id,
                        })
                elif msg_type == "ack":
                    # 确认收到消息
                    notification_id = message.get("notification_id")
                    if notification_id:
                        logger.debug(f"用户 {user_id} 确认收到消息 {notification_id}")

            except WebSocketDisconnect:
                raise
            except json.JSONDecodeError:
                logger.warning(f"无效的 JSON 消息：{data}")
            except Exception as e:
                logger.error(f"处理 WebSocket 消息异常：{e}")

    async def push_notification(
        self,
        user_id: str,
        notification: dict,
    ) -> bool:
        """推送通知给用户"""
        message = {
            "type": "notification",
            "notification": notification,
            "timestamp": datetime.now().isoformat(),
        }

        if self._manager.is_user_online(user_id):
            await self._manager.send_personal_message(message, user_id)
            return True
        else:
            # 用户离线，加入队列
            self._queue_notification(user_id, notification)
            return False

    async def push_batch_notifications(
        self,
        notifications: List[dict],
    ) -> Dict[str, bool]:
        """批量推送通知"""
        results = {}
        for notification in notifications:
            recipient_id = notification.get("recipient_id")
            if recipient_id:
                success = await self.push_notification(recipient_id, notification)
                results[recipient_id] = success
        return results

    def _queue_notification(self, user_id: str, notification: dict) -> None:
        """将通知加入离线队列"""
        if user_id not in self._notification_queue:
            self._notification_queue[user_id] = []

        self._notification_queue[user_id].append({
            **notification,
            "queued_at": datetime.now().isoformat(),
        })

        # 限制队列大小
        if len(self._notification_queue[user_id]) > self._max_queue_size:
            self._notification_queue[user_id] = self._notification_queue[user_id][-self._max_queue_size:]

    async def _send_queued_notifications(self, user_id: str) -> None:
        """发送离线消息"""
        if user_id not in self._notification_queue:
            return

        notifications = self._notification_queue[user_id]
        if not notifications:
            return

        # 批量发送
        message = {
            "type": "queued_notifications",
            "notifications": notifications,
            "count": len(notifications),
            "timestamp": datetime.now().isoformat(),
        }

        try:
            await self._manager.send_personal_message(message, user_id)
            # 清空队列
            self._notification_queue[user_id] = []
        except Exception as e:
            logger.error(f"发送离线消息失败：{e}")

    def get_online_users(self) -> List[str]:
        """获取在线用户列表"""
        return self._manager.get_online_users()

    def is_user_online(self, user_id: str) -> bool:
        """检查用户是否在线"""
        return self._manager.is_user_online(user_id)

    def get_user_connection_count(self, user_id: str) -> int:
        """获取用户连接数"""
        return self._manager.get_user_connection_count(user_id)

    def join_room(self, user_id: str, room_id: str) -> None:
        """加入房间"""
        self._manager.join_room(user_id, room_id)

    def leave_room(self, user_id: str, room_id: str) -> None:
        """离开房间"""
        self._manager.leave_room(user_id, room_id)

    def join_channel_room(self, user_id: str, channel_id: str) -> None:
        """加入频道房间"""
        self._manager.join_room(user_id, f"channel:{channel_id}")

    def leave_channel_room(self, user_id: str, channel_id: str) -> None:
        """离开频道房间"""
        self._manager.leave_room(user_id, f"channel:{channel_id}")

    async def broadcast_to_channel(
        self,
        channel_id: str,
        notification: dict,
    ) -> int:
        """广播通知到频道"""
        room_id = f"channel:{channel_id}"
        if room_id not in self._manager._rooms:
            return 0

        message = {
            "type": "channel_notification",
            "channel_id": channel_id,
            "notification": notification,
            "timestamp": datetime.now().isoformat(),
        }

        count = 0
        for user_id in self._manager._rooms[room_id]:
            try:
                await self._manager.send_personal_message(message, user_id)
                count += 1
            except Exception as e:
                logger.error(f"广播到频道失败：{e}")

        return count


# 全局 WebSocket 通知服务实例
websocket_notification_service = WebSocketNotificationService()
