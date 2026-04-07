"""
实时数据处理服务 - P7 核心能力

提供实时指标计算、聚合和推送能力：
- 实时访客数统计
- 实时事件流处理
- 实时转化率计算
- 实时异常检测与告警
"""
import asyncio
from typing import Dict, List, Optional, Set, Callable, Any
from datetime import datetime, timedelta
from collections import defaultdict, deque
import logging
import time
from dataclasses import dataclass, field
import threading

logger = logging.getLogger(__name__)


@dataclass
class RealtimeMetrics:
    """实时指标数据"""
    timestamp: datetime
    active_visitors: int = 0  # 活跃访客数
    events_per_second: float = 0.0  # 每秒事件数
    page_views: int = 0  # 页面浏览数
    unique_visitors: int = 0  # 独立访客数
    conversion_rate: float = 0.0  # 转化率
    bounce_rate: float = 0.0  # 跳出率
    avg_session_duration: float = 0.0  # 平均会话时长 (秒)
    top_pages: List[Dict] = field(default_factory=list)  # 热门页面
    top_events: List[Dict] = field(default_factory=list)  # 热门事件
    traffic_sources: Dict[str, int] = field(default_factory=dict)  # 流量来源
    geographic_distribution: Dict[str, int] = field(default_factory=dict)  # 地域分布


@dataclass
class RealtimeEvent:
    """实时事件"""
    event_id: str
    event_name: str
    event_type: str
    timestamp: datetime
    user_id: Optional[str]
    session_id: str
    page_url: str
    properties: Dict[str, Any] = field(default_factory=dict)
    ip_address: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None


class RealtimeEventStore:
    """
    实时事件存储

    使用内存存储最近的实时事件，支持高效的时间窗口查询
    """

    def __init__(self, max_events: int = 10000, ttl_seconds: int = 300):
        """
        初始化实时事件存储

        Args:
            max_events: 最大存储事件数
            ttl_seconds: 事件过期时间 (秒)
        """
        self._events: deque = deque(maxlen=max_events)
        self._max_events = max_events
        self._ttl_seconds = ttl_seconds
        self._lock = threading.Lock()

        # 索引
        self._session_index: Dict[str, Set[str]] = defaultdict(set)  # session_id -> event_ids
        self._user_index: Dict[str, Set[str]] = defaultdict(set)  # user_id -> event_ids
        self._page_index: Dict[str, Set[str]] = defaultdict(set)  # page_url -> event_ids

    def add_event(self, event: RealtimeEvent):
        """添加实时事件"""
        with self._lock:
            self._events.append(event)
            self._session_index[event.session_id].add(event.event_id)
            if event.user_id:
                self._user_index[event.user_id].add(event.event_id)
            self._page_index[event.page_url].add(event.event_id)

    def get_recent_events(self, limit: int = 100) -> List[RealtimeEvent]:
        """获取最近的事件"""
        with self._lock:
            return list(self._events)[-limit:]

    def get_events_by_time_window(
        self,
        start_time: datetime,
        end_time: datetime,
        event_name: Optional[str] = None
    ) -> List[RealtimeEvent]:
        """按时间窗口获取事件"""
        with self._lock:
            result = []
            for event in self._events:
                if start_time <= event.timestamp <= end_time:
                    if event_name is None or event.event_name == event_name:
                        result.append(event)
            return result

    def get_active_sessions(self, window_seconds: int = 300) -> Set[str]:
        """获取活跃会话 (指定时间窗口内有活动的会话)"""
        cutoff = datetime.now() - timedelta(seconds=window_seconds)
        with self._lock:
            active = set()
            for event in self._events:
                if event.timestamp >= cutoff:
                    active.add(event.session_id)
            return active

    def cleanup_expired(self):
        """清理过期事件"""
        cutoff = datetime.now() - timedelta(seconds=self._ttl_seconds)
        with self._lock:
            # 移除过期事件
            while self._events and self._events[0].timestamp < cutoff:
                old_event = self._events.popleft()
                # 清理索引
                self._session_index[old_event.session_id].discard(old_event.event_id)
                if old_event.user_id:
                    self._user_index[old_event.user_id].discard(old_event.event_id)
                self._page_index[old_event.page_url].discard(old_event.event_id)


class RealtimeMetricsCalculator:
    """
    实时指标计算器

    基于时间窗口计算各项实时指标
    """

    def __init__(self, event_store: RealtimeEventStore):
        self._event_store = event_store
        self._session_start_times: Dict[str, datetime] = {}
        self._session_page_counts: Dict[str, Set[str]] = defaultdict(set)
        self._conversion_events: List[RealtimeEvent] = []
        self._lock = threading.Lock()

    def calculate_metrics(self, window_seconds: int = 60) -> RealtimeMetrics:
        """
        计算实时指标

        Args:
            window_seconds: 时间窗口 (秒)

        Returns:
            实时指标对象
        """
        now = datetime.now()
        start_time = now - timedelta(seconds=window_seconds)

        # 获取时间窗口内的事件
        events = self._event_store.get_events_by_time_window(start_time, now)

        # 计算各项指标
        active_sessions = self._event_store.get_active_sessions(window_seconds)
        active_visitors = len(active_sessions)

        # 计算独立访客数
        unique_user_ids = set()
        for event in events:
            if event.user_id:
                unique_user_ids.add(event.user_id)
        unique_visitors = len(unique_user_ids) or active_visitors  # 如果没有 user_id，使用 session 数

        # 计算每秒事件数
        events_per_second = len(events) / window_seconds if window_seconds > 0 else 0

        # 计算页面浏览数
        page_views = sum(1 for e in events if e.event_name == 'page_view')

        # 计算转化率 (有购买或注册事件的会话比例)
        conversion_sessions = set()
        for event in events:
            if event.event_name in ['purchase', 'sign_up', 'conversion']:
                conversion_sessions.add(event.session_id)
        conversion_rate = len(conversion_sessions) / len(active_sessions) if active_sessions else 0

        # 计算跳出率 (只有一个页面浏览的会话比例)
        session_page_counts = defaultdict(set)
        for event in events:
            if event.event_name == 'page_view':
                session_page_counts[event.session_id].add(event.page_url)

        bounced_sessions = sum(1 for pages in session_page_counts.values() if len(pages) <= 1)
        bounce_rate = bounced_sessions / len(active_sessions) if active_sessions else 0

        # 计算平均会话时长
        session_durations = []
        for session_id in active_sessions:
            if session_id in self._session_start_times:
                duration = (now - self._session_start_times[session_id]).total_seconds()
                session_durations.append(duration)
        avg_session_duration = sum(session_durations) / len(session_durations) if session_durations else 0

        # 计算热门页面
        page_counts = defaultdict(int)
        for event in events:
            if event.event_name == 'page_view':
                page_counts[event.page_url] += 1
        top_pages = sorted(
            [{"page": page, "count": count} for page, count in page_counts.items()],
            key=lambda x: x["count"],
            reverse=True
        )[:10]

        # 计算热门事件
        event_counts = defaultdict(int)
        for event in events:
            event_counts[event.event_name] += 1
        top_events = sorted(
            [{"event": event, "count": count} for event, count in event_counts.items()],
            key=lambda x: x["count"],
            reverse=True
        )[:10]

        # 计算流量来源分布
        traffic_sources = defaultdict(int)
        for event in events:
            source = event.properties.get('referrer', 'direct')
            if source:
                traffic_sources[source] += 1

        # 计算地域分布
        geo_distribution = defaultdict(int)
        for event in events:
            if event.country:
                geo_distribution[event.country] += 1

        return RealtimeMetrics(
            timestamp=now,
            active_visitors=active_visitors,
            events_per_second=events_per_second,
            page_views=page_views,
            unique_visitors=unique_visitors,
            conversion_rate=conversion_rate,
            bounce_rate=bounce_rate,
            avg_session_duration=avg_session_duration,
            top_pages=top_pages,
            top_events=top_events,
            traffic_sources=dict(traffic_sources),
            geographic_distribution=dict(geo_distribution)
        )

    def update_session(self, session_id: str, page_url: str):
        """更新会话信息"""
        with self._lock:
            if session_id not in self._session_start_times:
                self._session_start_times[session_id] = datetime.now()
            self._session_page_counts[session_id].add(page_url)


class WebSocketConnectionManager:
    """
    WebSocket 连接管理器

    管理所有 WebSocket 客户端连接，支持消息广播
    """

    def __init__(self):
        self._connections: Dict[str, Any] = {}  # connection_id -> websocket
        self._subscriptions: Dict[str, Set[str]] = defaultdict(set)  # connection_id -> subscribed_channels
        self._lock = threading.Lock()

    async def connect(self, connection_id: str, websocket):
        """添加新的 WebSocket 连接"""
        with self._lock:
            self._connections[connection_id] = websocket
            logger.info(f"WebSocket connected: {connection_id}")

    async def disconnect(self, connection_id: str):
        """移除 WebSocket 连接"""
        with self._lock:
            if connection_id in self._connections:
                del self._connections[connection_id]
            if connection_id in self._subscriptions:
                del self._subscriptions[connection_id]
            logger.info(f"WebSocket disconnected: {connection_id}")

    def subscribe(self, connection_id: str, channel: str):
        """订阅频道"""
        with self._lock:
            self._subscriptions[connection_id].add(channel)

    def unsubscribe(self, connection_id: str, channel: str):
        """取消订阅频道"""
        with self._lock:
            if connection_id in self._subscriptions:
                self._subscriptions[connection_id].discard(channel)

    async def broadcast(self, channel: str, message: dict):
        """
        向指定频道广播消息

        Args:
            channel: 频道名称
            message: 消息内容
        """
        with self._lock:
            target_connections = [
                conn_id for conn_id, channels in self._subscriptions.items()
                if channel in channels
            ]

        for conn_id in target_connections:
            await self.send_message(conn_id, message)

    async def send_message(self, connection_id: str, message: dict):
        """向指定连接发送消息"""
        with self._lock:
            websocket = self._connections.get(connection_id)

        if websocket:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send message to {connection_id}: {e}")
                await self.disconnect(connection_id)


class RealtimeService:
    """
    实时数据服务

    整合事件存储、指标计算和 WebSocket 推送
    """

    def __init__(self):
        self._event_store = RealtimeEventStore()
        self._metrics_calculator = RealtimeMetricsCalculator(self._event_store)
        self._ws_manager = WebSocketConnectionManager()
        self._running = False
        self._metrics_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None

        # 实时指标缓存
        self._cached_metrics: Optional[RealtimeMetrics] = None
        self._metrics_cache_ttl = 5  # 缓存 5 秒

    async def start(self):
        """启动实时服务"""
        self._running = True

        # 启动定期指标计算任务
        self._metrics_task = asyncio.create_task(self._metrics_calculation_loop())

        # 启动清理任务
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        logger.info("Realtime service started")

    async def stop(self):
        """停止实时服务"""
        self._running = False

        if self._metrics_task:
            self._metrics_task.cancel()
            try:
                await self._metrics_task
            except asyncio.CancelledError:
                pass

        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        logger.info("Realtime service stopped")

    async def _metrics_calculation_loop(self):
        """定期计算实时指标"""
        while self._running:
            try:
                # 计算最近 1 分钟的指标
                metrics = self._metrics_calculator.calculate_metrics(window_seconds=60)
                self._cached_metrics = metrics

                # 广播给所有订阅实时指标的客户端
                await self._ws_manager.broadcast("realtime_metrics", {
                    "type": "metrics",
                    "data": self._metrics_to_dict(metrics)
                })

                # 每秒计算一次
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error calculating metrics: {e}")
                await asyncio.sleep(1)

    async def _cleanup_loop(self):
        """定期清理过期数据"""
        while self._running:
            try:
                self._event_store.cleanup_expired()
                # 每 60 秒清理一次
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error cleaning up: {e}")

    def ingest_event(self, event: RealtimeEvent):
        """
        接收实时事件

        Args:
            event: 实时事件对象
        """
        self._event_store.add_event(event)
        self._metrics_calculator.update_session(event.session_id, event.page_url)

        # 尝试异步推送事件到订阅了实时事件的客户端
        # 如果没有运行的事件循环，则跳过异步推送
        try:
            loop = asyncio.get_running_loop()
            if loop:
                asyncio.create_task(self._ws_manager.broadcast("realtime_events", {
                    "type": "event",
                    "data": self._event_to_dict(event)
                }))
        except RuntimeError:
            # 没有运行的事件循环，跳过异步推送
            pass

        logger.debug(f"Ingested realtime event: {event.event_id}")

    def get_current_metrics(self) -> Optional[RealtimeMetrics]:
        """获取当前实时指标"""
        return self._cached_metrics

    def get_recent_events(self, limit: int = 100) -> List[Dict]:
        """获取最近的事件"""
        events = self._event_store.get_recent_events(limit)
        return [self._event_to_dict(e) for e in events]

    async def handle_websocket_connect(self, connection_id: str, websocket):
        """处理 WebSocket 连接"""
        await self._ws_manager.connect(connection_id, websocket)

    async def handle_websocket_disconnect(self, connection_id: str):
        """处理 WebSocket 断开"""
        await self._ws_manager.disconnect(connection_id)

    async def handle_subscribe(self, connection_id: str, channel: str):
        """处理频道订阅"""
        self._ws_manager.subscribe(connection_id, channel)

    async def handle_unsubscribe(self, connection_id: str, channel: str):
        """处理频道取消订阅"""
        self._ws_manager.unsubscribe(connection_id, channel)

    def _metrics_to_dict(self, metrics: RealtimeMetrics) -> Dict:
        """将指标转换为字典"""
        return {
            "timestamp": metrics.timestamp.isoformat(),
            "active_visitors": metrics.active_visitors,
            "events_per_second": metrics.events_per_second,
            "page_views": metrics.page_views,
            "unique_visitors": metrics.unique_visitors,
            "conversion_rate": round(metrics.conversion_rate, 4),
            "bounce_rate": round(metrics.bounce_rate, 4),
            "avg_session_duration": round(metrics.avg_session_duration, 2),
            "top_pages": metrics.top_pages,
            "top_events": metrics.top_events,
            "traffic_sources": metrics.traffic_sources,
            "geographic_distribution": metrics.geographic_distribution
        }

    def _event_to_dict(self, event: RealtimeEvent) -> Dict:
        """将事件转换为字典"""
        return {
            "event_id": event.event_id,
            "event_name": event.event_name,
            "event_type": event.event_type,
            "timestamp": event.timestamp.isoformat(),
            "user_id": event.user_id,
            "session_id": event.session_id,
            "page_url": event.page_url,
            "properties": event.properties,
            "ip_address": event.ip_address,
            "country": event.country,
            "city": event.city
        }


# 全局实时服务实例
realtime_service = RealtimeService()
