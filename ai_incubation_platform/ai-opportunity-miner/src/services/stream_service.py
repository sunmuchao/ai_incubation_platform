"""
实时数据流服务

实现轻量级实时数据流能力，支持：
1. 内存消息队列（轻量级，无需外部依赖）
2. 事件发布/订阅模式
3. 数据流持久化（可选）
4. 流式数据处理

架构设计：
┌─────────────────────────────────────────────────────────────┐
│                    StreamService                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  数据源层                                                     │
│  ├── EnterpriseStream - 企业数据流                          │
│  ├── PatentStream - 专利数据流                              │
│  ├── NewsStream - 新闻数据流                                │
│  └── SocialStream - 社交媒体数据流                          │
│        │                                                     │
│        ▼                                                     │
│  消息队列层                                                   │
│  ├── MemoryQueue - 内存队列（默认）                          │
│  └── KafkaQueue - Kafka 队列（可选扩展）                      │
│        │                                                     │
│        ▼                                                     │
│  事件处理层                                                   │
│  ├── EventRouter - 事件路由                                  │
│  ├── EventProcessor - 事件处理器                            │
│  └── AlertTrigger - 告警触发器                               │
│        │                                                     │
│        ▼                                                     │
│  推送层                                                       │
│  ├── WebSocket - 实时推送                                    │
│  └── Callback - 回调通知                                     │
└─────────────────────────────────────────────────────────────┘
"""
import asyncio
import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any, Set
from enum import Enum
from collections import defaultdict
import json
import queue

logger = logging.getLogger(__name__)


class StreamEventType(str, Enum):
    """流事件类型"""
    # 企业事件
    ENTERPRISE_CREATED = "enterprise.created"  # 新企业注册
    ENTERPRISE_UPDATED = "enterprise.updated"  # 企业信息更新
    ENTERPRISE_FUNDING = "enterprise.funding"  # 企业融资

    # 专利事件
    PATENT_PUBLISHED = "patent.published"  # 专利公开
    PATENT_GRANTED = "patent.granted"  # 专利授权
    PATENT_EXPIRED = "patent.expired"  # 专利失效

    # 新闻事件
    NEWS_PUBLISHED = "news.published"  # 新闻发布
    NEWS_TRENDING = "news.trending"  # 热门新闻

    # 社交媒体事件
    SOCIAL_POST = "social.post"  # 社交帖子
    SOCIAL_TRENDING = "social.trending"  # 热门话题

    # 系统事件
    SYSTEM_HEARTBEAT = "system.heartbeat"  # 心跳
    SYSTEM_ERROR = "system.error"  # 系统错误


class StreamPriority(str, Enum):
    """流优先级"""
    LOW = "low"  # 低优先级
    NORMAL = "normal"  # 普通优先级
    HIGH = "high"  # 高优先级
    URGENT = "urgent"  # 紧急


class StreamEvent:
    """流事件"""

    def __init__(
        self,
        event_type: StreamEventType,
        payload: Dict[str, Any],
        source: str = "unknown",
        priority: StreamPriority = StreamPriority.NORMAL,
        event_id: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ):
        self.event_id = event_id or str(uuid.uuid4())
        self.event_type = event_type
        self.payload = payload
        self.source = source
        self.priority = priority
        self.timestamp = timestamp or datetime.now()
        self.processed = False
        self.processed_at: Optional[datetime] = None
        self.processed_by: List[str] = []

    def mark_processed(self, processor: str):
        """标记已处理"""
        self.processed = True
        self.processed_at = datetime.now()
        self.processed_by.append(processor)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "payload": self.payload,
            "source": self.source,
            "priority": self.priority.value,
            "timestamp": self.timestamp.isoformat(),
            "processed": self.processed,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "processed_by": self.processed_by
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StreamEvent":
        """从字典创建"""
        event = cls(
            event_type=StreamEventType(data["event_type"]),
            payload=data["payload"],
            source=data.get("source", "unknown"),
            priority=StreamPriority(data.get("priority", "normal")),
            event_id=data.get("event_id"),
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else None
        )
        event.processed = data.get("processed", False)
        return event


class StreamSubscription:
    """流订阅"""

    def __init__(
        self,
        subscription_id: str,
        subscriber_id: str,
        event_types: Optional[List[StreamEventType]] = None,
        sources: Optional[List[str]] = None,
        priorities: Optional[List[StreamPriority]] = None,
        callback: Optional[Callable[[StreamEvent], None]] = None,
        filter_expr: Optional[str] = None
    ):
        self.subscription_id = subscription_id
        self.subscriber_id = subscriber_id
        self.event_types = event_types or []  # 空表示订阅所有类型
        self.sources = sources or []  # 空表示订阅所有来源
        self.priorities = priorities or []  # 空表示订阅所有优先级
        self.callback = callback
        self.filter_expr = filter_expr
        self.created_at = datetime.now()
        self.is_active = True
        self.event_count = 0
        self.last_event_at: Optional[datetime] = None

    def matches(self, event: StreamEvent) -> bool:
        """检查事件是否匹配订阅条件"""
        if not self.is_active:
            return False

        # 事件类型匹配
        if self.event_types and event.event_type not in self.event_types:
            return False

        # 来源匹配
        if self.sources and event.source not in self.sources:
            return False

        # 优先级匹配
        if self.priorities and event.priority not in self.priorities:
            return False

        # TODO: filter_expr 表达式匹配（可以使用简单的表达式解析）
        if self.filter_expr:
            # 简化处理：检查 payload 中是否包含 filter_expr 指定的 key
            if self.filter_expr not in str(event.payload):
                return False

        return True

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "subscription_id": self.subscription_id,
            "subscriber_id": self.subscriber_id,
            "event_types": [et.value for et in self.event_types] if self.event_types else [],
            "sources": self.sources,
            "priorities": [p.value for p in self.priorities] if self.priorities else [],
            "filter_expr": self.filter_expr,
            "is_active": self.is_active,
            "event_count": self.event_count,
            "created_at": self.created_at.isoformat(),
            "last_event_at": self.last_event_at.isoformat() if self.last_event_at else None
        }


class MemoryEventQueue:
    """内存事件队列 - 使用线程安全的 queue.Queue"""

    def __init__(self, max_size: int = 10000, retention_hours: int = 24):
        self.max_size = max_size
        self.retention_hours = retention_hours
        self._queue = queue.Queue(maxsize=max_size)
        self._events: List[StreamEvent] = []
        self._lock: Optional[asyncio.Lock] = None

    def _ensure_lock(self):
        """确保锁已初始化（延迟初始化，绑定到当前事件循环）"""
        if self._lock is None:
            self._lock = asyncio.Lock()

    async def put(self, event: StreamEvent, block: bool = True) -> bool:
        """放入事件"""
        try:
            self._queue.put(event, block=block)

            self._ensure_lock()
            async with self._lock:
                self._events.append(event)
                # 清理旧事件
                await self._cleanup()

            return True
        except queue.Full:
            logger.warning("Event queue is full, dropping event")
            return False

    async def get(self, timeout: Optional[float] = None) -> Optional[StreamEvent]:
        """获取事件"""
        try:
            if timeout:
                return self._queue.get(timeout=timeout)
            return self._queue.get_nowait()
        except queue.Empty:
            return None

    def get_nowait(self) -> Optional[StreamEvent]:
        """非阻塞获取事件"""
        try:
            return self._queue.get_nowait()
        except queue.Empty:
            return None

    async def get_batch(self, max_count: int = 10, timeout: Optional[float] = None) -> List[StreamEvent]:
        """批量获取事件"""
        events = []
        for _ in range(max_count):
            event = await self.get(timeout=timeout if not events else 0)
            if event:
                events.append(event)
            else:
                break
        return events

    async def _cleanup(self):
        """清理过期事件"""
        cutoff = datetime.now() - timedelta(hours=self.retention_hours)
        self._events = [e for e in self._events if e.timestamp >= cutoff]
        if len(self._events) > self.max_size:
            self._events = self._events[-self.max_size:]

    async def get_history(
        self,
        event_types: Optional[List[StreamEventType]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[StreamEvent]:
        """获取历史事件"""
        self._ensure_lock()
        async with self._lock:
            events = self._events.copy()

        if event_types:
            events = [e for e in events if e.event_type in event_types]
        if start_time:
            events = [e for e in events if e.timestamp >= start_time]
        if end_time:
            events = [e for e in events if e.timestamp <= end_time]

        return events[-limit:]

    def size(self) -> int:
        """队列大小"""
        return self._queue.qsize()

    def stats(self) -> Dict[str, Any]:
        """统计信息"""
        return {
            "queue_size": self.size(),
            "max_size": self.max_size,
            "history_size": len(self._events),
            "retention_hours": self.retention_hours
        }


class StreamService:
    """流服务"""

    def __init__(self, queue_size: int = 10000, retention_hours: int = 24):
        self.queue_size = queue_size
        self.retention_hours = retention_hours
        self.queue: Optional[MemoryEventQueue] = None
        self.subscriptions: Dict[str, StreamSubscription] = {}
        self.subscriber_subscriptions: Dict[str, Set[str]] = defaultdict(set)  # subscriber_id -> subscription_ids
        self._lock: Optional[asyncio.Lock] = None
        self._running = False
        self._dispatch_task: Optional[asyncio.Task] = None
        self._event_handlers: Dict[StreamEventType, List[Callable]] = defaultdict(list)
        self._stats = {
            "events_published": 0,
            "events_dispatched": 0,
            "events_dropped": 0
        }

    def _ensure_initialized(self):
        """确保已初始化"""
        if self.queue is None:
            self.queue = MemoryEventQueue(max_size=self.queue_size, retention_hours=self.retention_hours)
        if self._lock is None:
            self._lock = asyncio.Lock()

    async def start(self):
        """启动流服务"""
        self._ensure_initialized()
        self._running = True
        self._dispatch_task = asyncio.create_task(self._dispatch_loop())
        logger.info("Stream service started")

    async def stop(self):
        """停止流服务"""
        self._running = False
        if self._dispatch_task:
            self._dispatch_task.cancel()
            try:
                await self._dispatch_task
            except asyncio.CancelledError:
                pass
        logger.info("Stream service stopped")

    async def _dispatch_loop(self):
        """事件分发循环"""
        while self._running:
            try:
                # 使用非阻塞 get 配合 asyncio.sleep 避免阻塞事件循环
                event = self.queue.get_nowait()
                # 检查事件是否为 None（超时情况）
                if event is None:
                    await asyncio.sleep(0.01)
                    continue
                await self._dispatch_event(event)
            except queue.Empty:
                # 队列为空，等待一小段时间后重试
                await asyncio.sleep(0.01)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in dispatch loop: {e}")
                await asyncio.sleep(0.1)  # 错误时等待更长时间

    async def publish(
        self,
        event_type: StreamEventType,
        payload: Dict[str, Any],
        source: str = "unknown",
        priority: StreamPriority = StreamPriority.NORMAL
    ) -> str:
        """发布事件"""
        self._ensure_initialized()
        event = StreamEvent(
            event_type=event_type,
            payload=payload,
            source=source,
            priority=priority
        )

        success = await self.queue.put(event)
        if success:
            self._stats["events_published"] += 1
            logger.debug(f"Published event: {event.event_id} - {event_type.value}")
        else:
            self._stats["events_dropped"] += 1

        return event.event_id

    async def _dispatch_event(self, event: StreamEvent):
        """分发事件到订阅者"""
        async with self._lock:
            subscriptions = list(self.subscriptions.values())

        notified = 0
        for sub in subscriptions:
            if sub.matches(event):
                sub.event_count += 1
                sub.last_event_at = datetime.now()

                if sub.callback:
                    try:
                        if asyncio.iscoroutinefunction(sub.callback):
                            await sub.callback(event)
                        else:
                            sub.callback(event)
                        notified += 1
                    except Exception as e:
                        logger.error(f"Callback error for subscriber {sub.subscriber_id}: {e}")

        # 调用注册的事件处理器
        handlers = self._event_handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Event handler error: {e}")

        self._stats["events_dispatched"] += notified
        logger.debug(f"Dispatched event {event.event_id} to {notified} subscribers")

    def subscribe(
        self,
        subscriber_id: str,
        event_types: Optional[List[StreamEventType]] = None,
        sources: Optional[List[str]] = None,
        priorities: Optional[List[StreamPriority]] = None,
        filter_expr: Optional[str] = None
    ) -> str:
        """订阅事件"""
        subscription_id = str(uuid.uuid4())
        subscription = StreamSubscription(
            subscription_id=subscription_id,
            subscriber_id=subscriber_id,
            event_types=event_types,
            sources=sources,
            priorities=priorities,
            filter_expr=filter_expr
        )

        self.subscriptions[subscription_id] = subscription
        self.subscriber_subscriptions[subscriber_id].add(subscription_id)

        logger.info(f"Created subscription {subscription_id} for {subscriber_id}")
        return subscription_id

    def subscribe_with_callback(
        self,
        subscriber_id: str,
        callback: Callable[[StreamEvent], None],
        event_types: Optional[List[StreamEventType]] = None,
        sources: Optional[List[str]] = None,
        priorities: Optional[List[StreamPriority]] = None
    ) -> str:
        """订阅事件并设置回调"""
        subscription_id = str(uuid.uuid4())
        subscription = StreamSubscription(
            subscription_id=subscription_id,
            subscriber_id=subscriber_id,
            event_types=event_types,
            sources=sources,
            priorities=priorities,
            callback=callback
        )

        self.subscriptions[subscription_id] = subscription
        self.subscriber_subscriptions[subscriber_id].add(subscription_id)

        logger.info(f"Created subscription {subscription_id} with callback for {subscriber_id}")
        return subscription_id

    def unsubscribe(self, subscription_id: str) -> bool:
        """取消订阅"""
        if subscription_id in self.subscriptions:
            subscription = self.subscriptions[subscription_id]
            self.subscriber_subscriptions[subscription.subscriber_id].discard(subscription_id)
            del self.subscriptions[subscription_id]
            logger.info(f"Removed subscription {subscription_id}")
            return True
        return False

    def unsubscribe_all(self, subscriber_id: str) -> int:
        """取消订阅者的所有订阅"""
        subscription_ids = list(self.subscriber_subscriptions.get(subscriber_id, []))
        count = 0
        for sub_id in subscription_ids:
            if self.unsubscribe(sub_id):
                count += 1
        del self.subscriber_subscriptions[subscriber_id]
        return count

    def register_handler(self, event_type: StreamEventType, handler: Callable[[StreamEvent], None]):
        """注册事件处理器"""
        self._event_handlers[event_type].append(handler)
        logger.info(f"Registered handler for event type: {event_type.value}")

    async def get_history(
        self,
        event_types: Optional[List[StreamEventType]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[StreamEvent]:
        """获取历史事件"""
        return await self.queue.get_history(event_types, start_time, end_time, limit)

    def get_subscriptions(self, subscriber_id: Optional[str] = None) -> List[Dict]:
        """获取订阅列表"""
        if subscriber_id:
            subscription_ids = self.subscriber_subscriptions.get(subscriber_id, [])
            return [
                self.subscriptions[sid].to_dict()
                for sid in subscription_ids
                if sid in self.subscriptions
            ]
        return [sub.to_dict() for sub in self.subscriptions.values()]

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self._stats,
            "active_subscriptions": len(self.subscriptions),
            "queue_stats": self.queue.stats()
        }


# 全局单例 - 延迟初始化
_stream_service: Optional[StreamService] = None


def get_stream_service() -> StreamService:
    """获取流服务单例（延迟初始化）"""
    global _stream_service
    if _stream_service is None:
        _stream_service = StreamService()
    return _stream_service


stream_service = get_stream_service()
