"""
创作者经济系统 API 路由
"""
from fastapi import APIRouter, HTTPException, Query, Body, Depends
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from models.economy import (
    SubscriptionTier, SubscriptionPeriod,
    SendTipRequest, CreateSubscriptionRequest,
    WalletBalanceResponse, TipResponse, SubscriptionResponse,
    CreatorDashboardResponse
)
from services.wallet_service import get_wallet_service, WalletService
from services.tip_service import get_tip_service, TipService
from services.subscription_service import get_subscription_service, SubscriptionService
from db.manager import db_manager

router = APIRouter(prefix="/api/economy", tags=["economy"])


# ==================== 请求/响应模型 ====================

class DepositRequest(BaseModel):
    """充值请求"""
    wallet_id: str
    amount: int = Field(..., gt=0, description="充值金额（分）")
    description: Optional[str] = "充值"


class WithdrawRequest(BaseModel):
    """提现请求"""
    wallet_id: str
    amount: int = Field(..., gt=0, description="提现金额（分）")
    description: Optional[str] = "提现"


class SendTipRequest(BaseModel):
    """发送打赏请求"""
    sender_id: str
    receiver_id: str
    amount: int = Field(..., gt=0, description="金额（分）")
    content_id: str
    content_type: str = Field(..., description="内容类型：post, comment")
    message: Optional[str] = None
    is_anonymous: bool = False


class TipListResponse(BaseModel):
    """打赏列表响应"""
    total: int
    tips: List[Dict[str, Any]]


class SubscriptionSummaryResponse(BaseModel):
    """订阅摘要响应"""
    creator_id: str
    total_subscribers: int
    active_subscribers: int
    by_tier: Dict[str, int]


class CreatorDashboardResponse(BaseModel):
    """创作者仪表板响应"""
    creator_id: str

    # 收入统计
    today_income: int
    week_income: int
    month_income: int
    total_income: int

    # 订阅统计
    total_subscribers: int
    active_subscribers: int

    # 打赏统计
    total_tips_received: int
    tips_this_month: int

    # 粉丝统计
    total_fans: int


# ==================== 钱包端点 ====================

@router.get("/wallet/{owner_id}", response_model=Dict[str, Any])
async def get_wallet(owner_id: str, owner_type: str = Query(default="member")):
    """
    获取用户钱包

    如果钱包不存在则自动创建
    """
    async with db_manager.get_session() as db:
        wallet_service = get_wallet_service(db)
        wallet = await wallet_service.get_or_create_wallet(owner_id, owner_type)

        return {
            "wallet_id": wallet.id,
            "owner_id": wallet.owner_id,
            "owner_type": wallet.owner_type,
            "balance": wallet.balance,
            "balance_yuan": wallet.balance / 100,
            "pending_balance": wallet.pending_balance,
            "total_income": wallet.total_income,
            "total_spent": wallet.total_spent,
            "creator_fund_balance": wallet.creator_fund_balance,
            "status": wallet.status.value,
        }


@router.post("/wallet/deposit")
async def deposit(request: DepositRequest):
    """
    充值

    向钱包充值金额
    """
    async with db_manager.get_session() as db:
        wallet_service = get_wallet_service(db)
        try:
            wallet = await wallet_service.deposit(
                wallet_id=request.wallet_id,
                amount=request.amount,
                description=request.description
            )
            return {
                "success": True,
                "wallet_id": wallet.id,
                "new_balance": wallet.balance,
                "new_balance_yuan": wallet.balance / 100,
            }
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))


@router.post("/wallet/withdraw")
async def withdraw(request: WithdrawRequest):
    """
    提现

    从钱包提现金额
    """
    async with db_manager.get_session() as db:
        wallet_service = get_wallet_service(db)
        try:
            wallet = await wallet_service.withdraw(
                wallet_id=request.wallet_id,
                amount=request.amount,
                description=request.description
            )
            return {
                "success": True,
                "wallet_id": wallet.id,
                "new_balance": wallet.balance,
                "new_balance_yuan": wallet.balance / 100,
            }
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))


@router.get("/wallet/{wallet_id}/transactions")
async def get_wallet_transactions(
    wallet_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    transaction_type: Optional[str] = None
):
    """
    获取钱包交易记录
    """
    async with db_manager.get_session() as db:
        wallet_service = get_wallet_service(db)

        transactions = await wallet_service.get_transactions(
            wallet_id=wallet_id,
            limit=limit,
            offset=offset,
            transaction_type=None  # TODO: 转换枚举
        )

        return {
            "wallet_id": wallet_id,
            "total": len(transactions),
            "transactions": [
                {
                    "id": tx.id,
                    "type": tx.transaction_type.value,
                    "amount": tx.amount,
                    "amount_yuan": tx.amount / 100,
                    "status": tx.status.value,
                    "description": tx.description,
                    "created_at": tx.created_at.isoformat(),
                }
                for tx in transactions
            ]
        }


# ==================== 打赏端点 ====================

@router.post("/tips/send", response_model=Dict[str, Any])
async def send_tip(request: SendTipRequest):
    """
    发送打赏

    向内容创作者发送打赏
    """
    async with db_manager.get_session() as db:
        tip_service = get_tip_service(db)
        try:
            tip = await tip_service.send_tip(
                sender_id=request.sender_id,
                receiver_id=request.receiver_id,
                amount=request.amount,
                content_id=request.content_id,
                content_type=request.content_type,
                message=request.message,
                is_anonymous=request.is_anonymous
            )

            return {
                "success": True,
                "tip_id": tip.id,
                "amount": tip.amount,
                "amount_yuan": tip.amount / 100,
                "tier": tip.tip_tier.value if tip.tip_tier else None,
                "status": tip.status.value,
            }
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))


@router.get("/tips/{tip_id}")
async def get_tip(tip_id: str):
    """
    获取打赏详情
    """
    async with db_manager.get_session() as db:
        tip_service = get_tip_service(db)
        tip = await tip_service.get_tip(tip_id)

        if not tip:
            raise HTTPException(status_code=404, detail="打赏记录不存在")

        return {
            "id": tip.id,
            "sender_id": tip.sender_id if not tip.is_anonymous else "anonymous",
            "receiver_id": tip.receiver_id,
            "amount": tip.amount,
            "tier": tip.tip_tier.value if tip.tip_tier else None,
            "content_id": tip.content_id,
            "message": tip.message if tip.is_public_message else None,
            "created_at": tip.created_at.isoformat(),
        }


@router.get("/tips/content/{content_type}/{content_id}")
async def get_tips_by_content(
    content_type: str,
    content_id: str,
    limit: int = Query(default=50, ge=1, le=100)
):
    """
    获取内容的打赏记录
    """
    async with db_manager.get_session() as db:
        tip_service = get_tip_service(db)
        tips = await tip_service.get_tips_by_content(content_id, content_type, limit)

        return {
            "content_id": content_id,
            "content_type": content_type,
            "total": len(tips),
            "tips": [
                {
                    "id": tip.id,
                    "sender_id": tip.sender_id if not tip.is_anonymous else "anonymous",
                    "amount": tip.amount,
                    "tier": tip.tip_tier.value if tip.tip_tier else None,
                    "message": tip.message if tip.is_public_message else None,
                    "created_at": tip.created_at.isoformat(),
                }
                for tip in tips
            ]
        }


@router.get("/tips/user/{user_id}/received")
async def get_tips_received(
    user_id: str,
    limit: int = Query(default=50, ge=1, le=100)
):
    """
    获取用户收到的打赏记录
    """
    async with db_manager.get_session() as db:
        tip_service = get_tip_service(db)
        tips = await tip_service.get_tips_by_receiver(user_id, limit)

        return {
            "user_id": user_id,
            "total": len(tips),
            "tips": [
                {
                    "id": tip.id,
                    "sender_id": tip.sender_id if not tip.is_anonymous else "anonymous",
                    "amount": tip.amount,
                    "tier": tip.tip_tier.value if tip.tip_tier else None,
                    "content_id": tip.content_id,
                    "created_at": tip.created_at.isoformat(),
                }
                for tip in tips
            ]
        }


@router.get("/tips/user/{user_id}/summary")
async def get_tip_summary(
    user_id: str,
    days: int = Query(default=30, ge=1, le=365)
):
    """
    获取用户收到的打赏统计
    """
    async with db_manager.get_session() as db:
        tip_service = get_tip_service(db)
        summary = await tip_service.get_tip_summary_by_receiver(user_id, days)

        return {
            "user_id": user_id,
            "period_days": summary["period_days"],
            "tip_count": summary["tip_count"],
            "total_amount": summary["total_amount"],
            "total_amount_yuan": summary["total_amount"] / 100,
            "avg_amount": summary["avg_amount"],
            "max_amount": summary["max_amount"],
            "by_tier": summary.get("by_tier", {}),
        }


# ==================== 订阅端点 ====================

@router.post("/subscriptions/create", response_model=Dict[str, Any])
async def create_subscription(request: CreateSubscriptionRequest):
    """
    创建订阅

    订阅创作者，解锁专属内容
    """
    async with db_manager.get_session() as db:
        subscription_service = get_subscription_service(db)
        try:
            subscription = await subscription_service.create_subscription(
                subscriber_id=request.subscriber_id,
                creator_id=request.creator_id,
                tier=request.tier,
                period=request.period
            )

            return {
                "success": True,
                "subscription_id": subscription.id,
                "subscriber_id": subscription.subscriber_id,
                "creator_id": subscription.creator_id,
                "tier": subscription.tier.value,
                "period": subscription.period.value,
                "price": subscription.price,
                "price_yuan": subscription.price / 100,
                "status": subscription.status.value,
                "start_date": subscription.start_date.isoformat(),
                "next_billing_date": subscription.next_billing_date.isoformat() if subscription.next_billing_date else None,
            }
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))


@router.post("/subscriptions/{subscription_id}/cancel")
async def cancel_subscription(subscription_id: str):
    """
    取消订阅
    """
    async with db_manager.get_session() as db:
        subscription_service = get_subscription_service(db)
        try:
            subscription = await subscription_service.cancel_subscription(subscription_id)

            return {
                "success": True,
                "subscription_id": subscription_id,
                "status": subscription.status.value,
                "cancelled_at": subscription.cancelled_at.isoformat() if subscription.cancelled_at else None,
            }
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))


@router.get("/subscriptions/{subscription_id}")
async def get_subscription(subscription_id: str):
    """
    获取订阅详情
    """
    async with db_manager.get_session() as db:
        subscription_service = get_subscription_service(db)
        subscription = await subscription_service.get_subscription(subscription_id)

        if not subscription:
            raise HTTPException(status_code=404, detail="订阅不存在")

        return {
            "id": subscription.id,
            "subscriber_id": subscription.subscriber_id,
            "creator_id": subscription.creator_id,
            "tier": subscription.tier.value,
            "period": subscription.period.value,
            "price": subscription.price,
            "status": subscription.status.value,
            "start_date": subscription.start_date.isoformat(),
            "next_billing_date": subscription.next_billing_date.isoformat() if subscription.next_billing_date else None,
        }


@router.get("/subscriptions/user/{user_id}/active")
async def get_active_subscriptions(user_id: str):
    """
    获取用户的活跃订阅
    """
    async with db_manager.get_session() as db:
        subscription_service = get_subscription_service(db)
        subscriptions = await subscription_service.get_subscriptions_by_subscriber(
            user_id,
            status=SubscriptionTier.ACTIVE if hasattr(SubscriptionTier, 'ACTIVE') else None
        )

        return {
            "user_id": user_id,
            "total": len(subscriptions),
            "subscriptions": [
                {
                    "id": sub.id,
                    "creator_id": sub.creator_id,
                    "tier": sub.tier.value,
                    "period": sub.period.value,
                    "start_date": sub.start_date.isoformat(),
                }
                for sub in subscriptions
            ]
        }


@router.get("/subscriptions/creator/{creator_id}/summary")
async def get_subscription_summary(creator_id: str):
    """
    获取创作者订阅统计
    """
    async with db_manager.get_session() as db:
        subscription_service = get_subscription_service(db)
        summary = await subscription_service.get_subscriber_count(creator_id)

        return {
            "creator_id": creator_id,
            "total_subscribers": summary["total"],
            "active_subscribers": summary["active"],
            "by_tier": summary["by_tier"],
        }


# ==================== 创作者仪表板 ====================

@router.get("/creator/{creator_id}/dashboard", response_model=CreatorDashboardResponse)
async def get_creator_dashboard(creator_id: str):
    """
    获取创作者仪表板数据

    包含收入、订阅、打赏、粉丝等统计数据
    """
    async with db_manager.get_session() as db:
        wallet_service = get_wallet_service(db)
        tip_service = get_tip_service(db)
        subscription_service = get_subscription_service(db)

        # 获取创作者钱包
        wallet = await wallet_service.get_wallet_by_owner(creator_id, "member")

        if not wallet:
            # 返回空数据
            return CreatorDashboardResponse(
                creator_id=creator_id,
                today_income=0,
                week_income=0,
                month_income=0,
                total_income=0,
                total_subscribers=0,
                active_subscribers=0,
                total_tips_received=0,
                tips_this_month=0,
                total_fans=0,
                fan_level_distribution={},
            )

        # 获取收入统计
        income_summary = await wallet_service.get_income_summary(wallet.id, days=30)

        # 获取打赏统计
        tip_summary_30 = await tip_service.get_tip_summary_by_receiver(creator_id, days=30)
        tip_summary_7 = await tip_service.get_tip_summary_by_receiver(creator_id, days=7)

        # 获取订阅统计
        subscription_summary = await subscription_service.get_subscriber_count(creator_id)
        revenue_summary = await subscription_service.get_revenue_summary(creator_id, days=30)

        # 计算总收入
        total_income = wallet.total_income

        return CreatorDashboardResponse(
            creator_id=creator_id,
            today_income=0,  # TODO: 实现按天统计
            week_income=tip_summary_7.get("total_amount", 0) + (revenue_summary.get("total_revenue", 0) // 7),
            month_income=tip_summary_30.get("total_amount", 0) + revenue_summary.get("total_revenue", 0),
            total_income=total_income,
            total_subscribers=subscription_summary["total"],
            active_subscribers=subscription_summary["active"],
            total_tips_received=tip_summary_30.get("tip_count", 0),
            tips_this_month=tip_summary_30.get("tip_count", 0),
            total_fans=0,  # TODO: 实现粉丝统计
            fan_level_distribution={},
        )


# ==================== 订阅等级配置 ====================

@router.get("/subscription-tiers")
async def get_subscription_tiers():
    """
    获取订阅等级配置
    """
    from services.subscription_service import SUBSCRIPTION_CONFIG, PERIOD_PRICING

    tiers = []
    for tier, config in SUBSCRIPTION_CONFIG.items():
        prices = {}
        for period, multiplier in PERIOD_PRICING.items():
            prices[period.value] = int(config["price_monthly"] * multiplier)

        tiers.append({
            "tier": tier.value,
            "name": config["name"],
            "prices": prices,
            "benefits": config["benefits"],
        })

    return {"tiers": tiers}
