"""
实时数据 API 路由 - P7

提供实时数据相关的 API 端点：
- WebSocket 实时指标推送
- 实时访客数查询
- 实时事件流查询
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException
from typing import Optional, List
import uuid
import logging
from datetime import datetime
import asyncio

from schemas.common import Response, ErrorCode
from analytics.realtime_service import (
    realtime_service,
    RealtimeEvent,
    RealtimeMetrics
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/realtime", tags=["realtime"])


@router.websocket("/ws/metrics")
async def websocket_metrics(websocket: WebSocket):
    """
    WebSocket 实时指标推送

    客户端连接后可接收实时更新的指标数据
    """
    connection_id = f"ws_{uuid.uuid4().hex[:8]}"
    await websocket.accept()

    try:
        # 连接处理
        await realtime_service.handle_websocket_connect(connection_id, websocket)

        # 默认订阅实时指标频道
        await realtime_service.handle_subscribe(connection_id, "realtime_metrics")

        # 发送欢迎消息
        await websocket.send_json({
            "type": "connected",
            "connection_id": connection_id,
            "message": "Successfully connected to realtime metrics stream"
        })

        # 保持连接并处理客户端消息
        while True:
            try:
                # 接收客户端消息（订阅/取消订阅等）
                data = await websocket.receive_json()
                message_type = data.get("type")

                if message_type == "subscribe":
                    channel = data.get("channel")
                    if channel:
                        await realtime_service.handle_subscribe(connection_id, channel)
                        await websocket.send_json({
                            "type": "subscribed",
                            "channel": channel
                        })

                elif message_type == "unsubscribe":
                    channel = data.get("channel")
                    if channel:
                        await realtime_service.handle_unsubscribe(connection_id, channel)
                        await websocket.send_json({
                            "type": "unsubscribed",
                            "channel": channel
                        })

                elif message_type == "ping":
                    await websocket.send_json({"type": "pong"})

            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error processing websocket message: {e}")
                break

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {connection_id}")
    finally:
        await realtime_service.handle_websocket_disconnect(connection_id)


@router.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    """
    WebSocket 实时事件流推送

    客户端连接后可接收实时事件流
    """
    connection_id = f"ws_{uuid.uuid4().hex[:8]}"
    await websocket.accept()

    try:
        await realtime_service.handle_websocket_connect(connection_id, websocket)
        await realtime_service.handle_subscribe(connection_id, "realtime_events")

        await websocket.send_json({
            "type": "connected",
            "connection_id": connection_id,
            "message": "Successfully connected to realtime events stream"
        })

        while True:
            try:
                data = await websocket.receive_json()
                message_type = data.get("type")

                if message_type == "subscribe":
                    channel = data.get("channel")
                    if channel:
                        await realtime_service.handle_subscribe(connection_id, channel)
                        await websocket.send_json({
                            "type": "subscribed",
                            "channel": channel
                        })

                elif message_type == "unsubscribe":
                    channel = data.get("channel")
                    if channel:
                        await realtime_service.handle_unsubscribe(connection_id, channel)
                        await websocket.send_json({
                            "type": "unsubscribed",
                            "channel": channel
                        })

                elif message_type == "ping":
                    await websocket.send_json({"type": "pong"})

            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error processing websocket message: {e}")
                break

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {connection_id}")
    finally:
        await realtime_service.handle_websocket_disconnect(connection_id)


@router.get("/visitors", response_model=Response)
async def get_realtime_visitors(
    window_seconds: int = Query(default=60, ge=10, le=3600, description="时间窗口 (秒)")
):
    """
    获取实时访客数

    Args:
        window_seconds: 时间窗口大小

    Returns:
        实时访客数据
    """
    try:
        metrics = realtime_service.get_current_metrics()

        if metrics is None:
            return Response(
                code=ErrorCode.SUCCESS,
                message="No metrics available yet",
                data={
                    "active_visitors": 0,
                    "unique_visitors": 0,
                    "window_seconds": window_seconds
                }
            )

        return Response(
            code=ErrorCode.SUCCESS,
            message="Success",
            data={
                "timestamp": metrics.timestamp.isoformat(),
                "active_visitors": metrics.active_visitors,
                "unique_visitors": metrics.unique_visitors,
                "window_seconds": window_seconds
            }
        )

    except Exception as e:
        logger.error(f"Error getting realtime visitors: {e}")
        return Response(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"Failed to get realtime visitors: {str(e)}"
        )


@router.get("/events", response_model=Response)
async def get_realtime_events(
    limit: int = Query(default=100, ge=1, le=1000, description="返回事件数量限制"),
    event_name: Optional[str] = Query(default=None, description="事件名称筛选")
):
    """
    获取实时事件流

    Args:
        limit: 返回事件数量
        event_name: 事件名称筛选

    Returns:
        实时事件列表
    """
    try:
        events = realtime_service.get_recent_events(limit)

        # 筛选事件名称
        if event_name:
            events = [e for e in events if e.get("event_name") == event_name]

        return Response(
            code=ErrorCode.SUCCESS,
            message="Success",
            data={
                "events": events,
                "count": len(events),
                "limit": limit
            }
        )

    except Exception as e:
        logger.error(f"Error getting realtime events: {e}")
        return Response(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"Failed to get realtime events: {str(e)}"
        )


@router.get("/metrics", response_model=Response)
async def get_realtime_metrics(
    window_seconds: int = Query(default=60, ge=10, le=3600, description="时间窗口 (秒)")
):
    """
    获取完整实时指标

    Args:
        window_seconds: 时间窗口大小

    Returns:
        完整实时指标数据
    """
    try:
        metrics = realtime_service.get_current_metrics()

        if metrics is None:
            return Response(
                code=ErrorCode.SUCCESS,
                message="No metrics available yet",
                data={}
            )

        return Response(
            code=ErrorCode.SUCCESS,
            message="Success",
            data={
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
        )

    except Exception as e:
        logger.error(f"Error getting realtime metrics: {e}")
        return Response(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"Failed to get realtime metrics: {str(e)}"
        )


@router.post("/ingest", response_model=Response)
async def ingest_realtime_event(event_data: dict):
    """
    接收实时事件

    用于从外部系统接入实时事件数据

    Args:
        event_data: 事件数据

    Returns:
        接收结果
    """
    try:
        # 验证必填字段
        required_fields = ["event_name", "session_id", "page_url"]
        for field in required_fields:
            if field not in event_data:
                raise ValueError(f"Missing required field: {field}")

        # 创建实时事件
        realtime_event = RealtimeEvent(
            event_id=event_data.get("event_id", f"evt_{uuid.uuid4().hex[:16]}"),
            event_name=event_data["event_name"],
            event_type=event_data.get("event_type", "custom"),
            timestamp=datetime.fromisoformat(event_data["timestamp"]) if "timestamp" in event_data else datetime.now(),
            user_id=event_data.get("user_id"),
            session_id=event_data["session_id"],
            page_url=event_data["page_url"],
            properties=event_data.get("properties", {}),
            ip_address=event_data.get("ip_address"),
            country=event_data.get("country"),
            city=event_data.get("city")
        )

        # 接收事件
        realtime_service.ingest_event(realtime_event)

        return Response(
            code=ErrorCode.SUCCESS,
            message="Event ingested successfully",
            data={
                "event_id": realtime_event.event_id
            }
        )

    except ValueError as e:
        return Response(
            code=ErrorCode.VALIDATION_ERROR,
            message=str(e)
        )
    except Exception as e:
        logger.error(f"Error ingesting event: {e}")
        return Response(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"Failed to ingest event: {str(e)}"
        )
