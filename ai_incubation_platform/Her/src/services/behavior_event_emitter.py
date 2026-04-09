"""
行为事件发射器 - Behavior Event Emitter

在关键操作点自动发射行为事件，让 AI 感知层能够捕获用户的所有行为。

使用方式：
1. 在 API 端点中调用 emit_event()
2. 在业务服务中调用 emit_event()
3. 事件自动异步写入数据库

支持的事件类型：
- chat_message_sent: 发送消息
- chat_message_received: 收到消息
- profile_viewed: 查看资料
- swipe_like: 点赞
- swipe_pass: 跳过
- swipe_super_like: 超级喜欢
- match_accepted: 匹配成功
- date_scheduled: 预约约会
- date_completed: 完成约会
- profile_updated: 更新资料
- search_performed: 执行搜索
"""
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from functools import wraps
import asyncio
import threading

from db.database import SessionLocal
from db.models import BehaviorEventDB
from utils.logger import logger


class BehaviorEventEmitter:
    """
    行为事件发射器

    单例模式，全局可访问
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._event_queue = asyncio.Queue()
        self._workers_running = False
        self._worker_tasks = []

    def start(self):
        """启动异步工作器"""
        if self._workers_running:
            return
        self._workers_running = True
        logger.info("BehaviorEventEmitter started")

    def stop(self):
        """停止异步工作器"""
        self._workers_running = False
        logger.info("BehaviorEventEmitter stopped")

    async def _process_event(self, event_data: Dict[str, Any]):
        """异步处理事件，写入数据库"""
        from utils.db_session_manager import async_db_session_context
        async with async_db_session_context() as db:
            db_event = BehaviorEventDB(
                id=event_data["id"],
                user_id=event_data["user_id"],
                event_type=event_data["event_type"],
                target_id=event_data.get("target_id"),
                event_data=event_data.get("event_data", {}),
                created_at=event_data.get("created_at", datetime.now())
            )
            db.add(db_event)
            logger.debug(f"Event persisted: {event_data['event_type']} for user {event_data['user_id']}")

    def emit(
        self,
        user_id: str,
        event_type: str,
        target_id: Optional[str] = None,
        event_data: Optional[Dict[str, Any]] = None,
        sync: bool = False
    ) -> str:
        """
        发射行为事件

        Args:
            user_id: 用户 ID
            event_type: 事件类型
            target_id: 目标用户 ID（可选）
            event_data: 事件详情数据（可选）
            sync: 是否同步写入（默认异步）

        Returns:
            事件 ID
        """
        import uuid
        event_id = str(uuid.uuid4())

        event = {
            "id": event_id,
            "user_id": user_id,
            "event_type": event_type,
            "target_id": target_id,
            "event_data": event_data or {},
            "created_at": datetime.now()
        }

        if sync:
            # 同步写入
            asyncio.create_task(self._process_event(event))
        else:
            # 异步写入（默认）
            asyncio.create_task(self._process_event(event))

        logger.debug(f"Event emitted: {event_type} for user {user_id}")
        return event_id

    def emit_batch(self, events: list) -> int:
        """
        批量发射事件

        Args:
            events: 事件列表，每个事件为 dict

        Returns:
            发射的事件数量
        """
        for event in events:
            self.emit(**event)
        return len(events)


# 事件类型常量
EVENT_CHAT_MESSAGE_SENT = "chat_message_sent"
EVENT_CHAT_MESSAGE_RECEIVED = "chat_message_received"
EVENT_PROFILE_VIEWED = "profile_viewed"
EVENT_SWIPE_LIKE = "swipe_like"
EVENT_SWIPE_PASS = "swipe_pass"
EVENT_SWIPE_SUPER_LIKE = "swipe_super_like"
EVENT_MATCH_ACCEPTED = "match_accepted"
EVENT_MATCH_REJECTED = "match_rejected"
EVENT_DATE_SCHEDULED = "date_scheduled"
EVENT_DATE_COMPLETED = "date_completed"
EVENT_DATE_CANCELLED = "date_cancelled"
EVENT_PROFILE_UPDATED = "profile_updated"
EVENT_SEARCH_PERFORMED = "event_search_performed"
EVENT_RECOMMENDATION_VIEWED = "recommendation_viewed"
EVENT_RECOMMENDATION_CLICKED = "recommendation_clicked"
EVENT_NOTIFICATION_OPENED = "notification_opened"


# 全局单例
event_emitter = BehaviorEventEmitter()


def track_behavior(event_type: str, user_id_field: str = "user_id"):
    """
    行为追踪装饰器

    用法：
    @track_behavior(EVENT_CHAT_MESSAGE_SENT, user_id_field="sender_id")
    async def send_message(sender_id, receiver_id, content):
        ...

    Args:
        event_type: 事件类型
        user_id_field: 从函数参数中提取 user_id 的字段名
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 获取 user_id
            user_id = kwargs.get(user_id_field) or _get_arg_by_position(args, kwargs, user_id_field)

            # 执行原函数
            result = await func(*args, **kwargs)

            # 发射事件
            if user_id:
                event_data = {
                    "function": func.__name__,
                    "args": str(kwargs)[:500]  # 记录部分参数用于调试
                }
                event_emitter.emit(
                    user_id=user_id,
                    event_type=event_type,
                    event_data=event_data
                )

            return result
        return wrapper

        def _get_arg_by_position(args, kwargs, field_name):
            """从位置参数或关键字参数获取值"""
            if field_name in kwargs:
                return kwargs[field_name]
            # 尝试从位置参数获取（需要函数签名信息，简化处理）
            return None

    return decorator


def track_swipe_action(func: Callable):
    """
    专门用于追踪滑动操作的装饰器

    用法：
    @track_swipe_action
    async def swipe(user_id, target_id, action):
        ...
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        user_id = kwargs.get("user_id")
        target_id = kwargs.get("target_id")
        action = kwargs.get("action")

        # 执行原函数
        result = await func(*args, **kwargs)

        # 根据动作类型发射事件
        if user_id and action:
            if action == "like":
                event_type = EVENT_SWIPE_LIKE
            elif action == "pass":
                event_type = EVENT_SWIPE_PASS
            elif action == "super_like":
                event_type = EVENT_SWIPE_SUPER_LIKE
            else:
                event_type = f"swipe_{action}"

            event_emitter.emit(
                user_id=user_id,
                event_type=event_type,
                target_id=target_id,
                event_data={"action": action}
            )

        return result
    return wrapper


def track_profile_view(func: Callable):
    """
    专门用于追踪查看资料操作的装饰器

    用法：
    @track_profile_view
    async def view_profile(viewer_id, profile_id):
        ...
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        viewer_id = kwargs.get("viewer_id") or kwargs.get("user_id")
        profile_id = kwargs.get("profile_id") or kwargs.get("target_id")

        # 执行原函数
        result = await func(*args, **kwargs)

        # 发射事件
        if viewer_id and profile_id:
            event_emitter.emit(
                user_id=viewer_id,
                event_type=EVENT_PROFILE_VIEWED,
                target_id=profile_id,
                event_data={"view_duration": 0}  # 可以在前端计算停留时间
            )

        return result
    return wrapper


def track_chat_message(func: Callable):
    """
    专门用于追踪聊天消息的装饰器

    用法：
    @track_chat_message
    async def send_message(sender_id, receiver_id, content):
        ...
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        sender_id = kwargs.get("sender_id") or kwargs.get("user_id")
        receiver_id = kwargs.get("receiver_id")
        content = kwargs.get("content")

        # 执行原函数
        result = await func(*args, **kwargs)

        # 发射事件
        if sender_id:
            event_emitter.emit(
                user_id=sender_id,
                event_type=EVENT_CHAT_MESSAGE_SENT,
                target_id=receiver_id,
                event_data={
                    "content_preview": content[:100] if content else "",
                    "content_length": len(content) if content else 0
                }
            )

        return result
    return wrapper


# 启动事件发射器
event_emitter.start()
