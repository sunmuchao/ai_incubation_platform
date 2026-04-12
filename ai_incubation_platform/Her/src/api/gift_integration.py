"""
DigitalTwin: 礼物闭环集成 API

功能包括：
- 礼物推荐
- 订单管理
- 佣金追踪
- 礼物反馈
- 重要日期提醒
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

from db.database import get_db
from services.gift_integration_service import (
    GiftIntegrationService,
    get_occasion_name,
    get_budget_range_display,
    GIFT_OCCASIONS,
    BUDGET_RANGES,
)


router = APIRouter(prefix="/api/gifts", tags=["DigitalTwin-礼物闭环"])


# ============= 请求/响应模型 =============

class GiftSuggestionRequest(BaseModel):
    """礼物推荐请求"""
    occasion: str = Field(..., description="场合")
    budget_range: str = Field(..., description="预算范围")
    recipient_preferences: Dict[str, Any] = Field(default_factory=dict, description="接收人喜好")
    recipient_user_id: Optional[str] = Field(None, description="接收人用户 ID")
    limit: int = Field(default=10, ge=1, le=50, description="返回数量")


class GiftSuggestionResponse(BaseModel):
    """礼物推荐响应"""
    id: str
    platform: str
    platform_name: str
    name: str
    price: float
    category: str
    tags: List[str]
    image_url: str
    commission_rate: float
    commission_amount: float
    affiliate_link: str


class OrderPlaceRequest(BaseModel):
    """订单请求"""
    product_id: str = Field(..., description="产品 ID")
    recipient_user_id: str = Field(..., description="接收人用户 ID")
    delivery_address: str = Field(..., description="配送地址")
    recipient_name: str = Field(..., description="接收人姓名")
    recipient_phone: str = Field(..., description="接收人电话")
    gift_message: Optional[str] = Field(None, description="礼物留言")


class OrderResponse(BaseModel):
    """订单响应"""
    order_id: str
    product_id: str
    sender_user_id: str
    recipient_user_id: str
    tracking_no: str
    status: str
    gift_message: Optional[str]
    estimated_delivery: str
    created_at: str


class FeedbackRequest(BaseModel):
    """反馈请求"""
    order_id: str = Field(..., description="订单 ID")
    rating: int = Field(..., ge=1, le=5, description="评分")
    feedback_text: Optional[str] = Field(None, description="反馈文字")
    would_use_again: bool = Field(default=True, description="是否愿意再次使用")


class CommissionStatsResponse(BaseModel):
    """佣金统计响应"""
    user_id: str
    period: Dict[str, str]
    total_orders: int
    total_commission: float
    pending_commission: float
    paid_commission: float
    top_category: str
    average_order_value: int


class UpcomingEventResponse(BaseModel):
    """重要日期响应"""
    event: str
    event_name: str
    partner_name: str
    date: str
    days_remaining: int
    gift_suggestions: List[str]


# ============= 依赖注入 =============

def get_gift_service(db: Session = Depends(get_db)) -> GiftIntegrationService:
    """获取礼物服务"""
    return GiftIntegrationService(db)


# ============= 礼物推荐 API =============

@router.post("/suggestions", response_model=List[GiftSuggestionResponse])
async def get_gift_suggestions(
    request: GiftSuggestionRequest,
    user_id: str = Query(..., description="用户 ID"),
    service: GiftIntegrationService = Depends(get_gift_service),
):
    """
    获取礼物推荐

    基于场合、预算和接收人喜好推荐礼物。
    """
    suggestions = service.get_gift_suggestions(
        occasion=request.occasion,
        budget_range=request.budget_range,
        recipient_preferences=request.recipient_preferences,
        sender_user_id=user_id,
        recipient_user_id=request.recipient_user_id,
        limit=request.limit,
    )

    return [
        GiftSuggestionResponse(
            id=s["id"],
            platform=s["platform"],
            platform_name=s["platform_name"],
            name=s["name"],
            price=s["price"],
            category=s["category"],
            tags=s["tags"],
            image_url=s["image_url"],
            commission_rate=s["commission_rate"],
            commission_amount=s["commission_amount"],
            affiliate_link=s["affiliate_link"],
        )
        for s in suggestions
    ]


@router.get("/occasions/reference")
async def get_occasions_reference():
    """获取礼物场合参考数据"""
    return {
        "occasions": [
            {"key": key, "name": name}
            for key, name in GIFT_OCCASIONS.items()
        ],
    }


@router.get("/budget-ranges/reference")
async def get_budget_ranges_reference():
    """获取预算范围参考数据"""
    return {
        "budget_ranges": [
            {"key": key, "display": value[2]}
            for key, value in BUDGET_RANGES.items()
        ],
    }


# ============= 订单管理 API =============

@router.post("/orders/place", response_model=OrderResponse)
async def place_order(
    request: OrderPlaceRequest,
    user_id: str = Query(..., description="用户 ID"),
    service: GiftIntegrationService = Depends(get_gift_service),
):
    """下单订购"""
    delivery_info = {
        "address": request.delivery_address,
        "name": request.recipient_name,
        "phone": request.recipient_phone,
    }

    order = service.place_order(
        product_id=request.product_id,
        sender_user_id=user_id,
        recipient_user_id=request.recipient_user_id,
        delivery_info=delivery_info,
        gift_message=request.gift_message,
    )

    return OrderResponse(
        order_id=order["order_id"],
        product_id=order["product_id"],
        sender_user_id=order["sender_user_id"],
        recipient_user_id=order["recipient_user_id"],
        tracking_no=order["tracking_no"],
        status=order["status"],
        gift_message=order.get("gift_message"),
        estimated_delivery=order["estimated_delivery"],
        created_at=order["created_at"],
    )


@router.get("/orders/{order_id}/track")
async def track_order(
    order_id: str,
    service: GiftIntegrationService = Depends(get_gift_service),
):
    """追踪订单物流"""
    tracking = service.track_order(order_id)

    return {
        "success": True,
        "data": tracking,
    }


# ============= 佣金统计 API =============

@router.get("/commission/stats", response_model=CommissionStatsResponse)
async def get_commission_stats(
    user_id: str = Query(..., description="用户 ID"),
    start_date: Optional[str] = Query(None, description="开始日期"),
    end_date: Optional[str] = Query(None, description="结束日期"),
    service: GiftIntegrationService = Depends(get_gift_service),
):
    """获取佣金统计"""
    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None

    stats = service.get_commission_stats(user_id, start, end)

    return CommissionStatsResponse(
        user_id=stats["user_id"],
        period=stats["period"],
        total_orders=stats["total_orders"],
        total_commission=stats["total_commission"],
        pending_commission=stats["pending_commission"],
        paid_commission=stats["paid_commission"],
        top_category=stats["top_category"],
        average_order_value=stats["average_order_value"],
    )


# ============= 礼物反馈 API =============

@router.post("/feedback")
async def submit_gift_feedback(
    request: FeedbackRequest,
    user_id: str = Query(..., description="用户 ID"),
    service: GiftIntegrationService = Depends(get_gift_service),
):
    """提交礼物反馈"""
    result = service.submit_gift_feedback(
        order_id=request.order_id,
        recipient_user_id=user_id,
        rating=request.rating,
        feedback_text=request.feedback_text,
        would_use_again=request.would_use_again,
    )

    return {
        "success": True,
        "data": result,
    }


@router.get("/effectiveness/{sender_user_id}/{recipient_user_id}")
async def analyze_gift_effectiveness(
    sender_user_id: str,
    recipient_user_id: str,
    service: GiftIntegrationService = Depends(get_gift_service),
):
    """分析礼物有效性"""
    analysis = service.analyze_gift_effectiveness(
        sender_user_id=sender_user_id,
        recipient_user_id=recipient_user_id,
    )

    return {
        "success": True,
        "data": analysis,
    }


# ============= 重要日期提醒 API =============

@router.get("/upcoming-events", response_model=List[UpcomingEventResponse])
async def get_upcoming_events(
    user_id: str = Query(..., description="用户 ID"),
    days_ahead: int = Query(default=30, ge=1, le=90, description="提前天数"),
    service: GiftIntegrationService = Depends(get_gift_service),
):
    """获取即将到来的重要日期"""
    events = service.get_upcoming_events(user_id, days_ahead)

    return [
        UpcomingEventResponse(
            event=e["event"],
            event_name=get_occasion_name(e["event"]),
            partner_name=e["partner_name"],
            date=e["date"],
            days_remaining=e["days_remaining"],
            gift_suggestions=e["gift_suggestions"],
        )
        for e in events
    ]


@router.post("/reminders/set")
async def set_gift_reminder(
    event_name: str = Body(..., description="事件名称"),
    event_date: str = Body(..., description="事件日期 ISO 格式"),
    partner_name: str = Body(..., description="对方名称"),
    reminder_days_before: int = Body(default=7, description="提前多少天提醒"),
    user_id: str = Query(..., description="用户 ID"),
    service: GiftIntegrationService = Depends(get_gift_service),
):
    """设置礼物提醒"""
    event_date_dt = datetime.fromisoformat(event_date)

    result = service.set_gift_reminder(
        user_id=user_id,
        event_name=event_name,
        event_date=event_date_dt,
        partner_name=partner_name,
        reminder_days_before=reminder_days_before,
    )

    return {
        "success": True,
        "data": result,
    }
