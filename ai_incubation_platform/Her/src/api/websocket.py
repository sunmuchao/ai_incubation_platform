"""
WebSocket 推送服务

提供实时推送通道，让 Agent 主动消息直达前端对话界面。

核心功能：
- 维护用户 WebSocket 连接池
- 推送 Agent 主动消息到指定用户
- 支持心跳保活和断线重连

【主动性重构 v2】
- 原设计：极光推送（系统通知，可能 mock 模式）
- 新设计：WebSocket 推送（对话界面，像真实聊天一样）
- 效果：用户打开 App，红娘主动在对话里说话
"""
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect

from utils.logger import logger


# ==================== 连接池管理 ====================

# 活跃 WebSocket 连接池：user_id -> WebSocket
_active_connections: Dict[str, WebSocket] = {}

# 连接元数据：user_id -> {connected_at, last_ping_at}
_connection_metadata: Dict[str, Dict[str, Any]] = {}


async def connect_user(websocket: WebSocket, user_id: str):
    """
    用户连接 WebSocket

    Args:
        websocket: WebSocket 连接对象
        user_id: 用户 ID
    """
    await websocket.accept()

    # 如果已有连接，先关闭旧连接
    if user_id in _active_connections:
        try:
            await _active_connections[user_id].close()
            logger.info(f"[WebSocket] 关闭用户 {user_id} 的旧连接")
        except Exception as e:
            logger.warning(f"[WebSocket] 关闭旧连接失败: {e}")

    # 保存新连接
    _active_connections[user_id] = websocket
    _connection_metadata[user_id] = {
        "connected_at": datetime.now().isoformat(),
        "last_ping_at": datetime.now().isoformat(),
    }

    logger.info(f"[WebSocket] 用户 {user_id} 已连接，当前活跃连接数: {len(_active_connections)}")


async def disconnect_user(user_id: str):
    """
    用户断开 WebSocket 连接

    Args:
        user_id: 用户 ID
    """
    if user_id in _active_connections:
        del _active_connections[user_id]

    if user_id in _connection_metadata:
        del _connection_metadata[user_id]

    logger.info(f"[WebSocket] 用户 {user_id} 已断开，当前活跃连接数: {len(_active_connections)}")


def is_user_connected(user_id: str) -> bool:
    """
    检查用户是否在线

    Args:
        user_id: 用户 ID

    Returns:
        是否在线
    """
    return user_id in _active_connections


async def send_to_user(user_id: str, message_type: str, data: Dict[str, Any]) -> bool:
    """
    发送消息到指定用户

    Args:
        user_id: 用户 ID
        message_type: 消息类型（agent_message, ping, notification 等）
        data: 消息数据

    Returns:
        是否发送成功
    """
    if user_id not in _active_connections:
        logger.warning(f"[WebSocket] 用户 {user_id} 未在线，无法推送")
        return False

    websocket = _active_connections[user_id]

    try:
        message = {
            "type": message_type,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        }

        await websocket.send_json(message)
        logger.info(f"[WebSocket] 消息已推送到用户 {user_id}: {message_type}")
        return True

    except Exception as e:
        logger.error(f"[WebSocket] 推送失败: {e}")
        # 推送失败时，清理连接
        await disconnect_user(user_id)
        return False


# ==================== 主动消息推送 ====================

def push_proactive_message_to_user(
    user_id: str,
    message: str,
    heartbeat_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    推送 Agent 主动消息到用户（同步包装异步）

    由心跳执行器调用，将 Agent 的自然语言消息推送到前端对话界面。

    Args:
        user_id: 用户 ID
        message: Agent 的消息内容（自然语言）
        heartbeat_id: 心跳 ID（用于追踪）

    Returns:
        推送结果
    """
    result = {
        "user_id": user_id,
        "message": message,
        "heartbeat_id": heartbeat_id,
        "success": False,
        "online": is_user_connected(user_id),
    }

    if not result["online"]:
        logger.warning(f"[WebSocket] 用户 {user_id} 未在线，消息将缓存待推送")
        # TODO: 后续可以添加消息缓存机制，用户上线后自动推送
        return result

    # 使用 asyncio 运行异步推送
    try:
        # 尝试获取当前事件循环
        try:
            loop = asyncio.get_running_loop()
            # 如果已有事件循环，创建任务
            asyncio.create_task(send_to_user(user_id, "agent_message", {
                "content": message,
                "heartbeat_id": heartbeat_id,
                "is_proactive": True,  # 标记为主动消息
            }))
        except RuntimeError:
            # 没有事件循环，创建新循环运行
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(send_to_user(user_id, "agent_message", {
                "content": message,
                "heartbeat_id": heartbeat_id,
                "is_proactive": True,
            }))
            loop.close()

        result["success"] = True
        logger.info(f"[WebSocket] 主动消息推送成功: user={user_id}, message={message[:50]}...")

    except Exception as e:
        logger.error(f"[WebSocket] 主动消息推送失败: {e}")
        result["error"] = str(e)

    return result


# ==================== WebSocket 路由 ====================

from fastapi import APIRouter

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """
    WebSocket 连接端点

    用户连接后，可以接收 Agent 的主动消息。

    Args:
        websocket: WebSocket 连接
        user_id: 用户 ID
    """
    logger.info(f"[WebSocket] 新连接请求: user_id={user_id}")

    # 连接用户
    await connect_user(websocket, user_id)

    try:
        # 保持连接，处理心跳和消息
        while True:
            # 接收客户端消息（主要是心跳 ping）
            data = await websocket.receive_text()

            try:
                message = json.loads(data)

                # 处理心跳 ping
                if message.get("type") == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat(),
                    })
                    # 更新心跳时间
                    if user_id in _connection_metadata:
                        _connection_metadata[user_id]["last_ping_at"] = datetime.now().isoformat()

                # 其他消息类型（可扩展）
                elif message.get("type") == "ack":
                    # 用户确认收到消息
                    logger.info(f"[WebSocket] 用户 {user_id} 确认收到消息: {message.get('message_id')}")

            except json.JSONDecodeError:
                # 非 JSON 消息，忽略
                logger.warning(f"[WebSocket] 收到非 JSON 消息: {data[:50]}")

    except WebSocketDisconnect:
        logger.info(f"[WebSocket] 用户 {user_id} 主动断开连接")
        await disconnect_user(user_id)

    except Exception as e:
        logger.error(f"[WebSocket] 连接异常: {e}")
        await disconnect_user(user_id)


@router.get("/ws/status")
async def get_websocket_status():
    """
    获取 WebSocket 连接状态

    Returns:
        连接池状态信息
    """
    return {
        "active_connections": len(_active_connections),
        "connected_users": list(_active_connections.keys()),
        "metadata": _connection_metadata,
    }


@router.get("/ws/online/{user_id}")
async def check_user_online(user_id: str):
    """
    检查用户是否在线

    Args:
        user_id: 用户 ID

    Returns:
        是否在线
    """
    return {
        "user_id": user_id,
        "online": is_user_connected(user_id),
        "metadata": _connection_metadata.get(user_id),
    }


# ==================== 导出 ====================

__all__ = [
    "router",
    "connect_user",
    "disconnect_user",
    "is_user_connected",
    "send_to_user",
    "push_proactive_message_to_user",
]