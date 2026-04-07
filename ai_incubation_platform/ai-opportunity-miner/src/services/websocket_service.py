"""
WebSocket 推送服务

实现 WebSocket 实时推送能力，支持：
1. 多客户端连接管理
2. 基于订阅的主题推送
3. 连接心跳检测
4. 断线重连处理

架构设计：
┌─────────────────────────────────────────────────────────────┐
│                 WebSocketService                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  连接管理层                                                   │
│  ├── ConnectionManager - 连接管理                            │
│  ├── HeartbeatMonitor - 心跳监控                            │
│  └── ReconnectHandler - 重连处理                            │
│        │                                                     │
│        ▼                                                     │
│  消息推送层                                                   │
│  ├── MessageRouter - 消息路由                                │
│  ├── TopicManager - 主题管理                                 │
│  └── BroadcastManager - 广播管理                            │
│        │                                                     │
│        ▼                                                     │
│  协议层                                                       │
│  ├── MessageParser - 消息解析                                │
│  └── ResponseBuilder - 响应构建                              │
└─────────────────────────────────────────────────────────────┘
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Set, Any, Callable
from enum import Enum

try:
    from fastapi import WebSocket, WebSocketDisconnect
    from starlette.websockets import WebSocketState
except ImportError:
    # 如果没有安装 fastapi，使用占位符
    WebSocket = Any
    WebSocketDisconnect = Exception
    WebSocketState = Any

from services.stream_service import StreamService, StreamEvent, StreamEventType, StreamPriority, get_stream_service

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """消息类型"""
    CONNECT = "connect"  # 连接
    DISCONNECT = "disconnect"  # 断开
    SUBSCRIBE = "subscribe"  # 订阅
    UNSUBSCRIBE = "unsubscribe"  # 取消订阅
    EVENT = "event"  # 事件通知
    HEARTBEAT = "heartbeat"  # 心跳
    ERROR = "error"  # 错误
    ACK = "ack"  # 确认


class ConnectionStatus(str, Enum):
    """连接状态"""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"


class WebSocketConnection:
    """WebSocket 连接包装类"""

    def __init__(self, websocket: WebSocket, client_id: str):
        self.websocket = websocket
        self.client_id = client_id
        self.status = ConnectionStatus.CONNECTING
        self.connected_at: Optional[datetime] = None
        self.last_message_at: Optional[datetime] = None
        self.last_heartbeat_at: Optional[datetime] = None
        self.subscriptions: Set[str] = set()  # subscription_ids
        self.message_count = 0
        self.client_info: Dict[str, Any] = {}

    async def send(self, message: Dict[str, Any]) -> bool:
        """发送消息"""
        if self.status != ConnectionStatus.CONNECTED:
            return False

        try:
            await self.websocket.send_json(message)
            self.last_message_at = datetime.now()
            self.message_count += 1
            return True
        except Exception as e:
            logger.error(f"Failed to send message to {self.client_id}: {e}")
            return False

    async def receive(self) -> Optional[Dict[str, Any]]:
        """接收消息"""
        try:
            data = await self.websocket.receive_text()
            return json.loads(data)
        except WebSocketDisconnect:
            return None
        except Exception as e:
            logger.error(f"Failed to receive message from {self.client_id}: {e}")
            return None

    async def accept(self):
        """接受连接"""
        await self.websocket.accept()
        self.status = ConnectionStatus.CONNECTED
        self.connected_at = datetime.now()
        logger.info(f"Client {self.client_id} connected")

    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """关闭连接"""
        if self.websocket.client_state == WebSocketState.CONNECTED:
            await self.websocket.close(code=code, reason=reason)
        self.status = ConnectionStatus.DISCONNECTED
        logger.info(f"Client {self.client_id} disconnected")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "client_id": self.client_id,
            "status": self.status.value,
            "connected_at": self.connected_at.isoformat() if self.connected_at else None,
            "last_message_at": self.last_message_at.isoformat() if self.last_message_at else None,
            "last_heartbeat_at": self.last_heartbeat_at.isoformat() if self.last_heartbeat_at else None,
            "subscriptions": list(self.subscriptions),
            "message_count": self.message_count,
            "client_info": self.client_info
        }


class ConnectionManager:
    """连接管理器"""

    def __init__(self):
        self.connections: Dict[str, WebSocketConnection] = {}
        self._lock: Optional[asyncio.Lock] = None

    def _ensure_lock(self):
        """确保锁已初始化"""
        if self._lock is None:
            self._lock = asyncio.Lock()

    async def add_connection(self, connection: WebSocketConnection):
        """添加连接"""
        self._ensure_lock()
        async with self._lock:
            self.connections[connection.client_id] = connection

    async def remove_connection(self, client_id: str) -> Optional[WebSocketConnection]:
        """移除连接"""
        self._ensure_lock()
        async with self._lock:
            return self.connections.pop(client_id, None)

    def get_connection(self, client_id: str) -> Optional[WebSocketConnection]:
        """获取连接"""
        return self.connections.get(client_id)

    def get_all_connections(self) -> List[WebSocketConnection]:
        """获取所有连接"""
        return list(self.connections.values())

    async def broadcast(self, message: Dict[str, Any], exclude: Optional[Set[str]] = None) -> int:
        """广播消息"""
        exclude = exclude or set()
        count = 0

        async with self._lock:
            for client_id, connection in self.connections.items():
                if client_id in exclude:
                    continue
                if connection.status == ConnectionStatus.CONNECTED:
                    if await connection.send(message):
                        count += 1

        return count

    async def send_to_client(self, client_id: str, message: Dict[str, Any]) -> bool:
        """发送消息到指定客户端"""
        connection = self.get_connection(client_id)
        if connection and connection.status == ConnectionStatus.CONNECTED:
            return await connection.send(message)
        return False

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        connected = sum(1 for c in self.connections.values() if c.status == ConnectionStatus.CONNECTED)
        return {
            "total_connections": len(self.connections),
            "connected_clients": connected,
            "disconnected_clients": len(self.connections) - connected
        }


class WebSocketService:
    """WebSocket 服务"""

    def __init__(
        self,
        stream_service: Optional[StreamService] = None,
        heartbeat_interval: int = 30,  # 心跳间隔（秒）
        timeout_seconds: int = 300,  # 超时时间（秒）
        max_message_size: int = 1024 * 1024  # 最大消息大小（1MB）
    ):
        self.stream_service = stream_service or get_stream_service()
        self.connection_manager = ConnectionManager()
        self.heartbeat_interval = heartbeat_interval
        self.timeout_seconds = timeout_seconds
        self.max_message_size = max_message_size

        self._running = False
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None

        # 消息处理器
        self._message_handlers: Dict[MessageType, Callable] = {
            MessageType.CONNECT: self._handle_connect,
            MessageType.DISCONNECT: self._handle_disconnect,
            MessageType.SUBSCRIBE: self._handle_subscribe,
            MessageType.UNSUBSCRIBE: self._handle_unsubscribe,
            MessageType.HEARTBEAT: self._handle_heartbeat,
        }

    async def start(self):
        """启动服务"""
        self._running = True
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("WebSocket service started")

    async def stop(self):
        """停止服务"""
        self._running = False

        # 取消后台任务
        for task in [self._heartbeat_task, self._cleanup_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # 关闭所有连接
        for connection in self.connection_manager.get_all_connections():
            await connection.close()

        logger.info("WebSocket service stopped")

    async def handle_client(self, websocket: WebSocket, client_id: str):
        """处理客户端连接"""
        connection = WebSocketConnection(websocket, client_id)

        try:
            # 接受连接
            await connection.accept()
            await self.connection_manager.add_connection(connection)

            # 发送欢迎消息
            await connection.send({
                "type": MessageType.CONNECT.value,
                "status": "success",
                "message": "Connected to WebSocket service",
                "client_id": client_id,
                "timestamp": datetime.now().isoformat()
            })

            # 处理消息循环
            while self._running and connection.status == ConnectionStatus.CONNECTED:
                try:
                    message = await connection.receive()
                    if message:
                        await self._process_message(connection, message)
                    else:
                        # 客户端断开
                        break
                except WebSocketDisconnect:
                    break
                except asyncio.TimeoutError:
                    # 超时，继续等待
                    continue

        except Exception as e:
            logger.error(f"Error handling client {client_id}: {e}")
        finally:
            # 清理连接
            await self._cleanup_connection(connection)

    async def _process_message(self, connection: WebSocketConnection, message: Dict[str, Any]):
        """处理消息"""
        msg_type = message.get("type", "").lower()

        # 更新最后消息时间
        connection.last_message_at = datetime.now()

        # 查找处理器
        handler = None
        for mt, h in self._message_handlers.items():
            if mt.value == msg_type:
                handler = h
                break

        if handler:
            try:
                await handler(connection, message)
            except Exception as e:
                logger.error(f"Message handler error: {e}")
                await connection.send({
                    "type": MessageType.ERROR.value,
                    "message": str(e)
                })
        else:
            logger.warning(f"Unknown message type: {msg_type}")
            await connection.send({
                "type": MessageType.ERROR.value,
                "message": f"Unknown message type: {msg_type}"
            })

    async def _handle_connect(self, connection: WebSocketConnection, message: Dict[str, Any]):
        """处理连接请求"""
        # 连接已经在 handle_client 中处理，这里只需要记录
        connection.client_info = message.get("info", {})
        logger.info(f"Client {connection.client_id} connected with info: {connection.client_info}")

    async def _handle_disconnect(self, connection: WebSocketConnection, message: Dict[str, Any]):
        """处理断开请求"""
        await connection.close()

    async def _handle_subscribe(self, connection: WebSocketConnection, message: Dict[str, Any]):
        """处理订阅请求"""
        event_types_str = message.get("event_types", [])
        event_types = [StreamEventType(et) for et in event_types_str if et]

        sources = message.get("sources", [])
        priorities_str = message.get("priorities", [])
        priorities = [StreamPriority(p) for p in priorities_str if p]

        # 在流服务中创建订阅
        subscription_id = self.stream_service.subscribe_with_callback(
            subscriber_id=connection.client_id,
            callback=lambda event: asyncio.create_task(self._on_stream_event(connection, event)),
            event_types=event_types if event_types else None,
            sources=sources if sources else None,
            priorities=priorities if priorities else None
        )

        connection.subscriptions.add(subscription_id)

        await connection.send({
            "type": MessageType.ACK.value,
            "action": "subscribe",
            "subscription_id": subscription_id,
            "status": "success"
        })

        logger.info(f"Client {connection.client_id} subscribed: {subscription_id}")

    async def _handle_unsubscribe(self, connection: WebSocketConnection, message: Dict[str, Any]):
        """处理取消订阅请求"""
        subscription_id = message.get("subscription_id")

        if subscription_id and subscription_id in connection.subscriptions:
            connection.subscriptions.discard(subscription_id)
            self.stream_service.unsubscribe(subscription_id)

            await connection.send({
                "type": MessageType.ACK.value,
                "action": "unsubscribe",
                "subscription_id": subscription_id,
                "status": "success"
            })

            logger.info(f"Client {connection.client_id} unsubscribed: {subscription_id}")

    async def _handle_heartbeat(self, connection: WebSocketConnection, message: Dict[str, Any]):
        """处理心跳请求"""
        connection.last_heartbeat_at = datetime.now()

        await connection.send({
            "type": MessageType.HEARTBEAT.value,
            "timestamp": datetime.now().isoformat(),
            "status": "ok"
        })

    async def _on_stream_event(self, connection: WebSocketConnection, event: StreamEvent):
        """处理流事件推送"""
        await connection.send({
            "type": MessageType.EVENT.value,
            "event": event.to_dict()
        })

    async def _cleanup_connection(self, connection: WebSocketConnection):
        """清理连接"""
        await self.connection_manager.remove_connection(connection.client_id)

        # 取消所有订阅
        for sub_id in list(connection.subscriptions):
            self.stream_service.unsubscribe(sub_id)
        connection.subscriptions.clear()

        await connection.close()
        logger.info(f"Cleaned up connection for {connection.client_id}")

    async def _heartbeat_loop(self):
        """心跳检测循环"""
        while self._running:
            try:
                await asyncio.sleep(self.heartbeat_interval)

                connections = self.connection_manager.get_all_connections()
                for connection in connections:
                    if connection.status != ConnectionStatus.CONNECTED:
                        continue

                    # 检查超时
                    if connection.last_message_at:
                        elapsed = (datetime.now() - connection.last_message_at).total_seconds()
                        if elapsed > self.timeout_seconds:
                            logger.warning(f"Client {connection.client_id} timeout, closing")
                            await connection.send({
                                "type": MessageType.DISCONNECT.value,
                                "reason": "Connection timeout"
                            })
                            await self._cleanup_connection(connection)
                            continue

                    # 发送心跳请求
                    if connection.last_heartbeat_at is None or \
                       (datetime.now() - connection.last_heartbeat_at).total_seconds() > self.heartbeat_interval:
                        await connection.send({
                            "type": MessageType.HEARTBEAT.value,
                            "timestamp": datetime.now().isoformat(),
                            "ping": True
                        })

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat loop error: {e}")

    async def _cleanup_loop(self):
        """清理循环（每分钟清理一次）"""
        while self._running:
            try:
                await asyncio.sleep(60)

                stats = self.stream_service.get_stats()
                conn_stats = self.connection_manager.get_stats()

                logger.info(f"Stats - Connections: {conn_stats}, Stream: {stats}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")

    def broadcast_event(self, event: StreamEvent, exclude: Optional[Set[str]] = None):
        """广播事件"""
        message = {
            "type": MessageType.EVENT.value,
            "event": event.to_dict(),
            "broadcast": True
        }

        asyncio.create_task(self.connection_manager.broadcast(message, exclude))

    async def send_to_client(self, client_id: str, event: StreamEvent):
        """发送事件到指定客户端"""
        message = {
            "type": MessageType.EVENT.value,
            "event": event.to_dict()
        }
        await self.connection_manager.send_to_client(client_id, message)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "websocket": self.connection_manager.get_stats(),
            "stream": self.stream_service.get_stats()
        }


# 全局单例
websocket_service = WebSocketService()
