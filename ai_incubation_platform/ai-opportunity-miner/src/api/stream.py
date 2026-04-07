"""
实时数据流 API

提供实时数据流相关的 API 端点：
1. WebSocket 连接端点
2. 数据订阅管理
3. 流历史记录查询
4. 流状态监控
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException, Body, Depends
from pydantic import BaseModel, Field

from services.stream_service import (
    stream_service,
    StreamService,
    StreamEventType,
    StreamPriority,
    StreamEvent
)
from services.websocket_service import (
    websocket_service,
    WebSocketService
)
from services.event_processor import (
    event_processor,
    EventProcessor
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/stream", tags=["实时数据流"])


# === 请求/响应模型 ===

class SubscribeRequest(BaseModel):
    """订阅请求"""
    event_types: Optional[List[str]] = Field(default=None, description="事件类型列表")
    sources: Optional[List[str]] = Field(default=None, description="数据源列表")
    priorities: Optional[List[str]] = Field(default=None, description="优先级列表")
    filter_expr: Optional[str] = Field(default=None, description="过滤表达式")


class SubscribeResponse(BaseModel):
    """订阅响应"""
    subscription_id: str
    status: str
    message: str


class UnsubscribeRequest(BaseModel):
    """取消订阅请求"""
    subscription_id: str


class StreamHistoryQuery(BaseModel):
    """流历史查询"""
    event_types: Optional[List[str]] = Field(default=None, description="事件类型列表")
    start_time: Optional[str] = Field(default=None, description="开始时间 (ISO 格式)")
    end_time: Optional[str] = Field(default=None, description="结束时间 (ISO 格式)")
    limit: int = Field(default=100, ge=1, le=1000, description="返回数量限制")


class StreamStatsResponse(BaseModel):
    """流统计响应"""
    events_published: int
    events_dispatched: int
    events_dropped: int
    active_subscriptions: int
    queue_size: int
    websocket_connections: int


# === WebSocket 端点 ===

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket 连接端点

    客户端连接后可以：
    1. 订阅特定事件类型
    2. 接收实时事件推送
    3. 发送心跳保持连接

    消息格式：
    - 订阅：{"type": "subscribe", "event_types": ["enterprise.funding", ...]}
    - 取消订阅：{"type": "unsubscribe", "subscription_id": "..."}
    - 心跳：{"type": "heartbeat"}

    服务端推送：
    - 事件：{"type": "event", "event": {...}}
    - 心跳响应：{"type": "heartbeat", "timestamp": "..."}
    - 确认：{"type": "ack", "action": "subscribe", "subscription_id": "..."}
    """
    # 生成客户端 ID（可以使用用户 ID 或会话 ID）
    client_id = f"client_{datetime.now().timestamp()}_{id(websocket)}"

    # 获取客户端信息（从 query params 或 headers）
    # 实际应用中应该进行认证和授权

    await websocket_service.handle_client(websocket, client_id)


# === 订阅管理端点 ===

@router.post("/subscribe", response_model=SubscribeResponse)
async def subscribe(request: SubscribeRequest, subscriber_id: str = Query(..., description="订阅者 ID")):
    """
    创建事件订阅

    - **subscriber_id**: 订阅者唯一标识
    - **event_types**: 要订阅的事件类型列表（可选，不填表示订阅所有类型）
    - **sources**: 数据源过滤（可选）
    - **priorities**: 优先级过滤（可选）
    - **filter_expr**: 过滤表达式（可选）

    可用的事件类型：
    - `enterprise.created` - 新企业注册
    - `enterprise.updated` - 企业信息更新
    - `enterprise.funding` - 企业融资
    - `patent.published` - 专利公开
    - `patent.granted` - 专利授权
    - `news.published` - 新闻发布
    - `news.trending` - 热门新闻
    - `social.post` - 社交帖子
    - `social.trending` - 热门话题
    """
    # 解析事件类型
    event_types = None
    if request.event_types:
        event_types = []
        for et in request.event_types:
            try:
                event_types.append(StreamEventType(et))
            except ValueError:
                logger.warning(f"Invalid event type: {et}")

    # 解析优先级
    priorities = None
    if request.priorities:
        priorities = []
        for p in request.priorities:
            try:
                priorities.append(StreamPriority(p))
            except ValueError:
                logger.warning(f"Invalid priority: {p}")

    subscription_id = stream_service.subscribe(
        subscriber_id=subscriber_id,
        event_types=event_types,
        sources=request.sources,
        priorities=priorities,
        filter_expr=request.filter_expr
    )

    return SubscribeResponse(
        subscription_id=subscription_id,
        status="success",
        message=f"Successfully subscribed to events"
    )


@router.post("/unsubscribe")
async def unsubscribe(request: UnsubscribeRequest):
    """
    取消事件订阅

    - **subscription_id**: 订阅 ID
    """
    success = stream_service.unsubscribe(request.subscription_id)

    if success:
        return {"status": "success", "message": "Subscription cancelled"}
    else:
        raise HTTPException(status_code=404, detail="Subscription not found")


@router.get("/subscriptions")
async def get_subscriptions(
    subscriber_id: Optional[str] = Query(None, description="订阅者 ID（可选，不填返回所有订阅）")
):
    """获取订阅列表"""
    subscriptions = stream_service.get_subscriptions(subscriber_id)
    return {
        "success": True,
        "data": subscriptions,
        "count": len(subscriptions)
    }


# === 流历史查询端点 ===

@router.post("/history")
async def get_stream_history(request: StreamHistoryQuery):
    """
    查询历史事件

    - **event_types**: 事件类型过滤
    - **start_time**: 开始时间（ISO 格式）
    - **end_time**: 结束时间（ISO 格式）
    - **limit**: 返回数量限制
    """
    # 解析事件类型
    event_types = None
    if request.event_types:
        event_types = []
        for et in request.event_types:
            try:
                event_types.append(StreamEventType(et))
            except ValueError:
                logger.warning(f"Invalid event type: {et}")

    # 解析时间
    start_time = None
    end_time = None
    if request.start_time:
        try:
            start_time = datetime.fromisoformat(request.start_time)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_time format")

    if request.end_time:
        try:
            end_time = datetime.fromisoformat(request.end_time)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_time format")

    # 查询历史
    events = await stream_service.get_history(
        event_types=event_types,
        start_time=start_time,
        end_time=end_time,
        limit=request.limit
    )

    return {
        "success": True,
        "data": [e.to_dict() for e in events],
        "count": len(events)
    }


# === 统计监控端点 ===

@router.get("/stats", response_model=StreamStatsResponse)
async def get_stream_stats():
    """获取流统计信息"""
    stream_stats = stream_service.get_stats()
    websocket_stats = websocket_service.get_stats()

    return StreamStatsResponse(
        events_published=stream_stats["events_published"],
        events_dispatched=stream_stats["events_dispatched"],
        events_dropped=stream_stats["events_dropped"],
        active_subscriptions=stream_stats["active_subscriptions"],
        queue_size=stream_stats["queue_stats"]["queue_size"],
        websocket_connections=websocket_stats["websocket"]["connected_clients"]
    )


@router.get("/processors/stats")
async def get_processor_stats():
    """获取事件处理器统计"""
    return event_processor.get_stats()


# === 事件发布端点（用于测试和手动发布） ===

class PublishEventRequest(BaseModel):
    """发布事件请求"""
    event_type: str = Field(..., description="事件类型")
    payload: Dict[str, Any] = Field(..., description="事件数据")
    source: str = Field(default="api", description="事件来源")
    priority: str = Field(default="normal", description="优先级")


@router.post("/publish")
async def publish_event(request: PublishEventRequest):
    """
    发布事件（主要用于测试）

    生产环境中应该通过数据源适配器自动发布事件
    """
    try:
        event_type = StreamEventType(request.event_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid event type: {request.event_type}")

    try:
        priority = StreamPriority(request.priority)
    except ValueError:
        priority = StreamPriority.NORMAL

    event_id = await stream_service.publish(
        event_type=event_type,
        payload=request.payload,
        source=request.source,
        priority=priority
    )

    return {
        "success": True,
        "event_id": event_id,
        "message": "Event published successfully"
    }


# === 批量发布端点 ===

class BatchPublishRequest(BaseModel):
    """批量发布请求"""
    events: List[PublishEventRequest] = Field(..., description="事件列表")


@router.post("/publish/batch")
async def publish_events_batch(request: BatchPublishRequest):
    """
    批量发布事件

    用于数据迁移或批量导入场景
    """
    results = []
    success_count = 0

    for event_req in request.events:
        try:
            event_type = StreamEventType(event_req.event_type)
            priority = StreamPriority(event_req.priority) if event_req.priority else StreamPriority.NORMAL

            event_id = await stream_service.publish(
                event_type=event_type,
                payload=event_req.payload,
                source=event_req.source,
                priority=priority
            )

            results.append({
                "event_type": event_req.event_type,
                "event_id": event_id,
                "status": "success"
            })
            success_count += 1

        except Exception as e:
            results.append({
                "event_type": event_req.event_type,
                "error": str(e),
                "status": "failed"
            })

    return {
        "success": True,
        "total": len(request.events),
        "success_count": success_count,
        "failed_count": len(request.events) - success_count,
        "results": results
    }


# === WebSocket 连接管理端点 ===

@router.get("/connections")
async def get_connections():
    """获取 WebSocket 连接列表"""
    connections = websocket_service.connection_manager.get_all_connections()
    return {
        "success": True,
        "data": [c.to_dict() for c in connections],
        "count": len(connections)
    }


@router.get("/connections/stats")
async def get_connection_stats():
    """获取连接统计"""
    return websocket_service.connection_manager.get_stats()


# === 健康检查端点 ===

@router.get("/health")
async def health_check():
    """健康检查"""
    stats = websocket_service.get_stats()
    is_healthy = (
        stats["websocket"]["connected_clients"] >= 0 and  # WebSocket 服务正常
        stats["stream"]["events_published"] >= 0  # 流服务正常
    )

    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "timestamp": datetime.now().isoformat(),
        "stats": stats
    }
