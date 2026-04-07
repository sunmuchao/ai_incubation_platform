"""
事件处理器

实现事件驱动的业务逻辑处理，包括：
1. 事件路由和分发
2. 业务事件处理
3. 告警触发
4. 数据更新同步

架构设计：
┌─────────────────────────────────────────────────────────────┐
│                  EventProcessor                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  事件路由层                                                   │
│  ├── EventRouter - 事件路由                                  │
│  ├── EventFilter - 事件过滤器                                │
│  └── EventTransformer - 事件转换器                          │
│        │                                                     │
│        ▼                                                     │
│  业务处理层                                                   │
│  ├── EnterpriseProcessor - 企业事件处理                      │
│  ├── PatentProcessor - 专利事件处理                          │
│  ├── NewsProcessor - 新闻事件处理                            │
│  └── SocialProcessor - 社交事件处理                          │
│        │                                                     │
│        ▼                                                     │
│  告警触发层                                                   │
│  ├── AlertTrigger - 告警触发器                               │
│  ├── ThresholdMonitor - 阈值监控                            │
│  └── PatternDetector - 模式检测                              │
│        │                                                     │
│        ▼                                                     │
│  数据同步层                                                   │
│  ├── DataSync - 数据同步                                     │
│  └── CacheUpdater - 缓存更新                                 │
└─────────────────────────────────────────────────────────────┘
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable, Set
from collections import defaultdict

from services.stream_service import StreamService, StreamEvent, StreamEventType, StreamPriority, get_stream_service
from services.alert_engine import AlertEngine, alert_engine as global_alert_engine
from nlp.event_detector import BusinessEvent, EventType, EventSeverity

logger = logging.getLogger(__name__)


class EventContext:
    """事件上下文"""

    def __init__(self, event: StreamEvent):
        self.event = event
        self.processed_by: List[str] = []
        self.metadata: Dict[str, Any] = {}
        self.errors: List[str] = []
        self.results: Dict[str, Any] = {}
        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None

    def add_result(self, key: str, value: Any):
        """添加处理结果"""
        self.results[key] = value

    def add_error(self, error: str):
        """添加错误"""
        self.errors.append(error)

    def add_metadata(self, key: str, value: Any):
        """添加元数据"""
        self.metadata[key] = value

    def mark_processed(self, processor: str):
        """标记已处理"""
        self.processed_by.append(processor)

    @property
    def processing_time_ms(self) -> float:
        """处理时间（毫秒）"""
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds() * 1000

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "event_id": self.event.event_id,
            "event_type": self.event.event_type.value,
            "processed_by": self.processed_by,
            "processing_time_ms": self.processing_time_ms,
            "errors": self.errors,
            "results": self.results,
            "metadata": self.metadata
        }


class BaseEventProcessor:
    """基础事件处理器"""

    def __init__(self, name: str):
        self.name = name
        self._handlers: Dict[StreamEventType, Callable[[EventContext], None]] = {}

    def register_handler(self, event_type: StreamEventType, handler: Callable[[EventContext], None]):
        """注册事件处理器"""
        self._handlers[event_type] = handler
        logger.info(f"Registered handler for {event_type.value} in {self.name}")

    async def process(self, context: EventContext) -> bool:
        """处理事件"""
        event_type = context.event.event_type

        if event_type not in self._handlers:
            logger.debug(f"No handler for {event_type.value} in {self.name}")
            return False

        try:
            handler = self._handlers[event_type]
            if asyncio.iscoroutinefunction(handler):
                await handler(context)
            else:
                handler(context)

            context.mark_processed(self.name)
            return True

        except Exception as e:
            logger.error(f"Error in {self.name} processing {event_type.value}: {e}")
            context.add_error(f"{self.name}: {str(e)}")
            return False


class EnterpriseEventProcessor(BaseEventProcessor):
    """企业事件处理器"""

    def __init__(self):
        super().__init__("EnterpriseProcessor")
        self.register_handler(StreamEventType.ENTERPRISE_CREATED, self._handle_enterprise_created)
        self.register_handler(StreamEventType.ENTERPRISE_UPDATED, self._handle_enterprise_updated)
        self.register_handler(StreamEventType.ENTERPRISE_FUNDING, self._handle_enterprise_funding)

    async def _handle_enterprise_created(self, context: EventContext):
        """处理企业创建事件"""
        payload = context.event.payload
        company_name = payload.get("company_name", "Unknown")
        industry = payload.get("industry", "Unknown")

        logger.info(f"New enterprise registered: {company_name} in {industry}")

        # 添加到图谱（如果有图谱服务）
        context.add_result("graph_updated", True)
        context.add_metadata("company_name", company_name)
        context.add_metadata("industry", industry)

    async def _handle_enterprise_updated(self, context: EventContext):
        """处理企业更新事件"""
        payload = context.event.payload
        company_name = payload.get("company_name", "Unknown")
        changes = payload.get("changes", [])

        logger.info(f"Enterprise updated: {company_name}, changes: {changes}")

        # 检测重要变更
        important_changes = [c for c in changes if c.get("field") in ["registered_capital", "legal_representative", "status"]]
        if important_changes:
            context.add_metadata("important_update", True)
            context.add_result("alert_triggered", True)

    async def _handle_enterprise_funding(self, context: EventContext):
        """处理企业融资事件"""
        payload = context.event.payload
        company_name = payload.get("company_name", "Unknown")
        round_type = payload.get("round", "Unknown")
        amount = payload.get("amount", 0)

        logger.info(f"Funding event: {company_name} raised {amount} in {round_type} round")

        # 大额融资告警
        if amount >= 100000000:  # 1 亿
            context.add_metadata("large_funding", True)
            context.add_result("alert_triggered", True)

        context.add_metadata("company_name", company_name)
        context.add_metadata("round", round_type)
        context.add_metadata("amount", amount)


class PatentEventProcessor(BaseEventProcessor):
    """专利事件处理器"""

    def __init__(self):
        super().__init__("PatentProcessor")
        self.register_handler(StreamEventType.PATENT_PUBLISHED, self._handle_patent_published)
        self.register_handler(StreamEventType.PATENT_GRANTED, self._handle_patent_granted)
        self.register_handler(StreamEventType.PATENT_EXPIRED, self._handle_patent_expired)

    async def _handle_patent_published(self, context: EventContext):
        """处理专利公开事件"""
        payload = context.event.payload
        patent_title = payload.get("title", "Unknown")
        applicant = payload.get("applicant", "Unknown")
        patent_type = payload.get("type", "Unknown")

        logger.info(f"Patent published: {patent_title} by {applicant}")

        # 检测核心技术专利
        keywords = ["AI", "人工智能", "机器学习", "大模型", "芯片", "半导体"]
        is_core_tech = any(kw in patent_title for kw in keywords)
        if is_core_tech:
            context.add_metadata("core_technology", True)
            context.add_result("alert_triggered", True)

    async def _handle_patent_granted(self, context: EventContext):
        """处理专利授权事件"""
        payload = context.event.payload
        patent_title = payload.get("title", "Unknown")
        patent_number = payload.get("number", "Unknown")

        logger.info(f"Patent granted: {patent_title} ({patent_number})")

    async def _handle_patent_expired(self, context: EventContext):
        """处理专利失效事件"""
        payload = context.event.payload
        patent_title = payload.get("title", "Unknown")
        reason = payload.get("reason", "Unknown")

        logger.info(f"Patent expired: {patent_title}, reason: {reason}")


class NewsEventProcessor(BaseEventProcessor):
    """新闻事件处理器"""

    def __init__(self):
        super().__init__("NewsProcessor")
        self.register_handler(StreamEventType.NEWS_PUBLISHED, self._handle_news_published)
        self.register_handler(StreamEventType.NEWS_TRENDING, self._handle_news_trending)

    async def _handle_news_published(self, context: EventContext):
        """处理新闻发布事件"""
        payload = context.event.payload
        title = payload.get("title", "Unknown")
        source = payload.get("source", "Unknown")

        logger.info(f"News published: {title} from {source}")

        # 情感分析（如果有 NLP 服务）
        # sentiment = await nlp_service.analyze_sentiment(title)
        # context.add_result("sentiment", sentiment)

    async def _handle_news_trending(self, context: EventContext):
        """处理热门新闻事件"""
        payload = context.event.payload
        topic = payload.get("topic", "Unknown")
        heat_score = payload.get("heat_score", 0)

        logger.info(f"Trending news: {topic}, heat: {heat_score}")

        if heat_score >= 80:
            context.add_metadata("hot_topic", True)
            context.add_result("alert_triggered", True)


class SocialEventProcessor(BaseEventProcessor):
    """社交媒体事件处理器"""

    def __init__(self):
        super().__init__("SocialProcessor")
        self.register_handler(StreamEventType.SOCIAL_POST, self._handle_social_post)
        self.register_handler(StreamEventType.SOCIAL_TRENDING, self._handle_social_trending)

    async def _handle_social_post(self, context: EventContext):
        """处理社交帖子事件"""
        payload = context.event.payload
        content = payload.get("content", "")
        platform = payload.get("platform", "Unknown")

        logger.info(f"Social post on {platform}: {content[:50]}...")

    async def _handle_social_trending(self, context: EventContext):
        """处理热门话题事件"""
        payload = context.event.payload
        topic = payload.get("topic", "Unknown")
        mention_count = payload.get("mention_count", 0)

        logger.info(f"Trending topic: {topic}, mentions: {mention_count}")


class AlertTriggerProcessor(BaseEventProcessor):
    """告警触发处理器"""

    def __init__(self, alert_engine: Optional[AlertEngine] = None):
        super().__init__("AlertTriggerProcessor")
        self.alert_engine = alert_engine or global_alert_engine

        # 注册所有事件类型，因为任何事件都可能触发告警
        for event_type in StreamEventType:
            self.register_handler(event_type, self._handle_alert_check)

    async def _handle_alert_check(self, context: EventContext):
        """检查是否需要触发告警"""
        # 如果前面的处理器已经标记需要告警
        if context.results.get("alert_triggered"):
            event = context.event
            payload = event.payload

            # 转换为 BusinessEvent
            business_event = BusinessEvent(
                event_id=event.event_id,
                event_type=self._map_to_business_event_type(event.event_type),
                title=payload.get("title", f"Event: {event.event_type.value}"),
                summary=payload.get("summary", ""),
                companies=payload.get("companies", []),
                amount=payload.get("amount"),
                currency=payload.get("currency", "CNY"),
                severity=self._map_to_severity(event.priority),
                source=event.source,
                published_at=event.timestamp
            )

            # 触发告警引擎
            alerts = self.alert_engine.process_event(business_event)
            context.add_result("alerts_generated", len(alerts))
            context.add_result("alert_ids", [a.alert_id for a in alerts])

            logger.info(f"Generated {len(alerts)} alerts for event {event.event_id}")

    def _map_to_business_event_type(self, stream_type: StreamEventType) -> EventType:
        """映射事件类型"""
        mapping = {
            StreamEventType.ENTERPRISE_FUNDING: EventType.FUNDING,
            StreamEventType.ENTERPRISE_CREATED: EventType.COMPANY_UPDATE,
            StreamEventType.PATENT_PUBLISHED: EventType.PATENT,
            StreamEventType.NEWS_TRENDING: EventType.NEWS,
        }
        return mapping.get(stream_type, EventType.GENERAL)

    def _map_to_severity(self, priority: StreamPriority) -> EventSeverity:
        """映射严重性"""
        mapping = {
            StreamPriority.URGENT: EventSeverity.CRITICAL,
            StreamPriority.HIGH: EventSeverity.HIGH,
            StreamPriority.NORMAL: EventSeverity.MEDIUM,
            StreamPriority.LOW: EventSeverity.LOW,
        }
        return mapping.get(priority, EventSeverity.LOW)


class EventProcessor:
    """事件处理器（总控）"""

    def __init__(self, stream_service: Optional[StreamService] = None):
        self.stream_service = stream_service or get_stream_service()
        self.processors: List[BaseEventProcessor] = []
        self._running = False
        self._stats = {
            "events_processed": 0,
            "events_failed": 0,
            "avg_processing_time_ms": 0
        }
        self._processing_times: List[float] = []

        # 注册默认处理器
        self._register_default_processors()

    def _register_default_processors(self):
        """注册默认处理器"""
        self.processors.append(EnterpriseEventProcessor())
        self.processors.append(PatentEventProcessor())
        self.processors.append(NewsEventProcessor())
        self.processors.append(SocialEventProcessor())
        self.processors.append(AlertTriggerProcessor())

        logger.info(f"Registered {len(self.processors)} event processors")

    def add_processor(self, processor: BaseEventProcessor):
        """添加处理器"""
        self.processors.append(processor)
        logger.info(f"Added processor: {processor.name}")

    async def start(self):
        """启动处理器"""
        self._running = True

        # 注册流事件回调 - 为所有事件类型注册处理器
        for event_type in StreamEventType:
            self.stream_service.register_handler(event_type, self._handle_event)

        logger.info("Event processor started")

    async def stop(self):
        """停止处理器"""
        self._running = False
        logger.info("Event processor stopped")

    def _handle_event(self, event: StreamEvent):
        """处理流事件"""
        asyncio.create_task(self._process_event(event))

    async def _process_event(self, event: StreamEvent):
        """处理事件"""
        context = EventContext(event)

        try:
            for processor in self.processors:
                success = await processor.process(context)
                if not success:
                    logger.debug(f"Processor {processor.name} skipped event {event.event_id}")

            # 标记事件已处理
            event.mark_processed("EventProcessor")

            # 更新统计
            self._stats["events_processed"] += 1
            self._processing_times.append(context.processing_time_ms)
            if len(self._processing_times) > 1000:
                self._processing_times = self._processing_times[-1000:]
            self._stats["avg_processing_time_ms"] = sum(self._processing_times) / len(self._processing_times)

            logger.debug(f"Processed event {event.event_id} in {context.processing_time_ms:.2f}ms")

        except Exception as e:
            logger.error(f"Failed to process event {event.event_id}: {e}")
            self._stats["events_failed"] += 1
            context.add_error(str(e))

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self._stats,
            "processor_count": len(self.processors),
            "processors": [p.name for p in self.processors]
        }

    def get_context_history(self, limit: int = 100) -> List[Dict]:
        """获取处理历史（简化版）"""
        # 实际实现可能需要持久化上下文
        return []


# 全局单例
event_processor = EventProcessor()
