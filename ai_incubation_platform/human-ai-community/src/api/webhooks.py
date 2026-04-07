"""
Webhook 管理 API 路由

提供 Webhook 配置和管理接口：
- Webhook CRUD
- 事件订阅
- 投递记录
- 测试功能
"""
from fastapi import APIRouter, HTTPException, Query, Body
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import asyncio

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.webhook_service import webhook_service, WebhookEvent

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


# ==================== 请求模型 ====================

class CreateWebhookRequest(BaseModel):
    """创建 Webhook 请求"""
    name: str = Field(..., description="Webhook 名称")
    url: str = Field(..., description="Webhook URL")
    events: List[str] = Field(..., description="订阅的事件列表")
    is_active: bool = Field(default=True, description="是否启用")
    secret: Optional[str] = Field(default=None, description="HMAC 签名密钥")
    custom_headers: Optional[Dict[str, str]] = Field(default=None, description="自定义请求头")


class UpdateWebhookRequest(BaseModel):
    """更新 Webhook 请求"""
    name: Optional[str] = Field(default=None, description="Webhook 名称")
    url: Optional[str] = Field(default=None, description="Webhook URL")
    events: Optional[List[str]] = Field(default=None, description="订阅的事件列表")
    is_active: Optional[bool] = Field(default=None, description="是否启用")
    custom_headers: Optional[Dict[str, str]] = Field(default=None, description="自定义请求头")


class TestWebhookRequest(BaseModel):
    """测试 Webhook 请求"""
    custom_data: Optional[Dict[str, Any]] = Field(default=None, description="自定义测试数据")


# ==================== Webhook CRUD ====================

@router.get("")
async def list_webhooks(
    is_active: Optional[bool] = Query(default=None, description="按状态筛选"),
    limit: int = Query(default=100, ge=1, le=500)
):
    """获取 Webhook 列表"""
    webhooks = webhook_service.list_webhooks(is_active=is_active, limit=limit)
    return {
        "total": len(webhooks),
        "webhooks": [w.to_dict() for w in webhooks]
    }


@router.post("")
async def create_webhook(request: CreateWebhookRequest, creator_id: str = Query(...)):
    """
    创建 Webhook

    需要 manage_webhooks 权限
    """
    try:
        webhook = webhook_service.create_webhook(
            name=request.name,
            url=request.url,
            events=request.events,
            is_active=request.is_active,
            secret=request.secret,
            custom_headers=request.custom_headers,
            creator_id=creator_id
        )
        return {
            "success": True,
            "webhook": webhook.to_dict()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{webhook_id}")
async def get_webhook(webhook_id: str):
    """获取 Webhook 详情"""
    webhook = webhook_service.get_webhook(webhook_id)
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    return webhook.to_dict()


@router.put("/{webhook_id}")
async def update_webhook(webhook_id: str, request: UpdateWebhookRequest, operator_id: str = Query(...)):
    """更新 Webhook 配置"""
    webhook = webhook_service.update_webhook(
        webhook_id=webhook_id,
        name=request.name,
        url=request.url,
        events=request.events,
        is_active=request.is_active,
        custom_headers=request.custom_headers
    )

    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    return {
        "success": True,
        "webhook": webhook.to_dict(),
        "operator_id": operator_id
    }


@router.delete("/{webhook_id}")
async def delete_webhook(webhook_id: str, operator_id: str = Query(...)):
    """删除 Webhook"""
    success = webhook_service.delete_webhook(webhook_id)
    if not success:
        raise HTTPException(status_code=404, detail="Webhook not found")

    return {
        "success": True,
        "deleted_webhook_id": webhook_id,
        "operator_id": operator_id
    }


# ==================== 事件订阅管理 ====================

@router.get("/events")
async def get_available_events():
    """获取所有可订阅的事件类型"""
    return {
        "events": webhook_service.get_available_events()
    }


@router.post("/{webhook_id}/subscribe")
async def subscribe_event(
    webhook_id: str,
    event: str = Query(..., description="事件类型"),
    operator_id: str = Query(...)
):
    """订阅事件"""
    success = webhook_service.subscribe_event(webhook_id, event)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to subscribe (invalid event or webhook)")

    webhook = webhook_service.get_webhook(webhook_id)
    return {
        "success": True,
        "webhook_id": webhook_id,
        "subscribed_event": event,
        "total_events": len(webhook.events),
        "operator_id": operator_id
    }


@router.post("/{webhook_id}/unsubscribe")
async def unsubscribe_event(
    webhook_id: str,
    event: str = Query(..., description="事件类型"),
    operator_id: str = Query(...)
):
    """取消订阅事件"""
    success = webhook_service.unsubscribe_event(webhook_id, event)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to unsubscribe (invalid event or webhook)")

    webhook = webhook_service.get_webhook(webhook_id)
    return {
        "success": True,
        "webhook_id": webhook_id,
        "unsubscribed_event": event,
        "total_events": len(webhook.events),
        "operator_id": operator_id
    }


# ==================== 测试功能 ====================

@router.post("/{webhook_id}/test")
async def test_webhook(webhook_id: str, request: TestWebhookRequest = None):
    """
    测试 Webhook

    发送测试事件到 Webhook URL
    """
    webhook = webhook_service.get_webhook(webhook_id)
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    # 同步调用异步方法
    test_result = webhook_service.test_webhook(webhook_id)

    return {
        "success": test_result.get("success"),
        "webhook_id": webhook_id,
        "test_info": {
            "target_url": webhook.url,
            "events_subscribed": len(webhook.events),
            "has_secret": bool(webhook.secret),
            "test_payload": test_result.get("test_payload")
        }
    }


@router.post("/{webhook_id}/send")
async def send_webhook(
    webhook_id: str,
    event: str = Query(..., description="事件类型"),
    data: Dict[str, Any] = Body(..., description="事件数据")
):
    """
    手动发送 Webhook 通知

    用于测试或触发特定事件
    """
    webhook = webhook_service.get_webhook(webhook_id)
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    try:
        webhook_event = WebhookEvent(event)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid event type: {event}")

    # 异步发送
    async def send():
        return await webhook_service.send_webhook(webhook_id, webhook_event, data)

    # 运行异步任务
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        record = loop.run_until_complete(send())
    finally:
        loop.close()

    return {
        "success": record.status == "success",
        "delivery_record": record.to_dict()
    }


# ==================== 投递记录 ====================

@router.get("/{webhook_id}/deliveries")
async def get_delivery_records(
    webhook_id: str,
    status: Optional[str] = Query(default=None, description="按状态筛选"),
    limit: int = Query(default=100, ge=1, le=500)
):
    """获取 Webhook 投递记录"""
    webhook = webhook_service.get_webhook(webhook_id)
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    records = webhook_service.get_delivery_records(
        webhook_id=webhook_id,
        status=status,
        limit=limit
    )

    return {
        "webhook_id": webhook_id,
        "total": len(records),
        "records": records
    }


@router.get("/{webhook_id}/stats")
async def get_webhook_stats(webhook_id: str):
    """获取 Webhook 统计信息"""
    stats = webhook_service.get_webhook_stats(webhook_id)
    if "error" in stats:
        raise HTTPException(status_code=404, detail=stats["error"])

    return stats


# ==================== 批量操作 ====================

@router.post("/batch/activate")
async def batch_activate_webhooks(
    webhook_ids: List[str] = Body(...),
    operator_id: str = Query(...)
):
    """批量启用 Webhook"""
    results = {"success": 0, "failed": 0, "details": []}

    for webhook_id in webhook_ids:
        webhook = webhook_service.update_webhook(webhook_id, is_active=True)
        if webhook:
            results["success"] += 1
            results["details"].append({"webhook_id": webhook_id, "status": "activated"})
        else:
            results["failed"] += 1
            results["details"].append({"webhook_id": webhook_id, "status": "not_found"})

    return {
        "success": True,
        "results": results,
        "operator_id": operator_id
    }


@router.post("/batch/deactivate")
async def batch_deactivate_webhooks(
    webhook_ids: List[str] = Body(...),
    operator_id: str = Query(...)
):
    """批量停用 Webhook"""
    results = {"success": 0, "failed": 0, "details": []}

    for webhook_id in webhook_ids:
        webhook = webhook_service.update_webhook(webhook_id, is_active=False)
        if webhook:
            results["success"] += 1
            results["details"].append({"webhook_id": webhook_id, "status": "deactivated"})
        else:
            results["failed"] += 1
            results["details"].append({"webhook_id": webhook_id, "status": "not_found"})

    return {
        "success": True,
        "results": results,
        "operator_id": operator_id
    }


# ==================== 系统管理 ====================

@router.get("/system/config")
async def get_webhook_system_config():
    """获取 Webhook 系统配置"""
    return {
        "max_retries_default": 3,
        "timeout_seconds_default": 30,
        "max_delivery_records": 1000,
        "supported_content_types": ["application/json"],
        "signature_algorithm": "HMAC-SHA256"
    }
