"""
虚拟礼物 API 路由

参考 Soul/探探的礼物系统：
- 获取礼物商店
- 发送礼物
- 查看收到的礼物
- 礼物统计
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from models.gift import (
    Gift,
    GiftSendRequest,
    GiftSendResponse,
    GiftTransaction,
    GiftStoreResponse,
    UserGiftStats,
)
from services.gift_service import get_gift_service, GiftService
from auth.jwt import get_current_user
from db.database import get_db
from utils.logger import logger

router = APIRouter(prefix="/api/gift", tags=["gift"])


# ==================== 请求/响应模型 ====================

class GiftResponse(BaseModel):
    """礼物响应"""
    id: str
    name: str
    type: str
    category: str
    price: float
    icon: str
    animation: Optional[str]
    description: str
    fullscreen: bool
    is_popular: bool
    is_new: bool


class SendGiftRequest(BaseModel):
    """发送礼物请求"""
    target_user_id: str
    gift_id: str
    count: int = 1
    message: Optional[str] = None


class ReceivedGiftResponse(BaseModel):
    """收到的礼物响应"""
    id: str
    sender_id: str
    sender_name: Optional[str]
    sender_avatar: Optional[str]
    gift_id: str
    gift_name: str
    gift_icon: str
    gift_type: str
    count: int
    price: float
    total_amount: float
    message: Optional[str]
    sent_at: str
    is_seen: bool


class GiftStatsResponse(BaseModel):
    """礼物统计响应"""
    user_id: str
    total_received: int
    total_received_amount: float
    total_sent: int
    total_sent_amount: float
    most_received_gift: Optional[str]
    most_sent_gift: Optional[str]
    unseen_count: int


# ==================== API 端点 ====================

@router.get("/store", response_model=GiftStoreResponse)
async def get_gift_store():
    """
    获取礼物商店

    返回所有礼物分类和礼物列表
    """
    db = next(get_db())
    gift_svc = get_gift_service(db)

    store = gift_svc.get_gift_store()

    return store


@router.get("/{gift_id}", response_model=GiftResponse)
async def get_gift(gift_id: str):
    """
    获取单个礼物信息

    Args:
        gift_id: 礼物 ID

    Returns:
        礼物详情
    """
    db = next(get_db())
    gift_svc = get_gift_service(db)

    gift = gift_svc.get_gift_by_id(gift_id)

    if not gift:
        raise HTTPException(status_code=404, detail="礼物不存在")

    return GiftResponse(
        id=gift.id,
        name=gift.name,
        type=gift.type.value,
        category=gift.category.value,
        price=gift.price,
        icon=gift.icon,
        animation=gift.animation,
        description=gift.description,
        fullscreen=gift.fullscreen,
        is_popular=gift.is_popular,
        is_new=gift.is_new,
    )


@router.post("/send", response_model=GiftSendResponse)
async def send_gift(
    request: SendGiftRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    发送礼物

    Args:
        target_user_id: 目标用户 ID
        gift_id: 礼物 ID
        count: 礼物数量（默认 1）
        message: 附带消息（可选）

    Returns:
        发送结果
    """
    user_id = current_user["user_id"]
    logger.info(f"Sending gift: {user_id} -> {request.target_user_id}, gift={request.gift_id}")

    if request.count < 1:
        raise HTTPException(status_code=400, detail="礼物数量必须大于 0")

    db = next(get_db())
    gift_svc = get_gift_service(db)

    result = gift_svc.send_gift(user_id, GiftSendRequest(
        target_user_id=request.target_user_id,
        gift_id=request.gift_id,
        count=request.count,
        message=request.message,
    ))

    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)

    return result


@router.get("/received", response_model=List[ReceivedGiftResponse])
async def get_received_gifts(
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """
    获取收到的礼物列表

    Args:
        limit: 返回数量上限

    Returns:
        收到的礼物列表
    """
    user_id = current_user["user_id"]
    db = next(get_db())
    gift_svc = get_gift_service(db)

    gifts = gift_svc.get_user_received_gifts(user_id, limit)

    # 获取发送者信息
    from db.repositories import UserRepository
    user_repo = UserRepository(db)

    results = []
    for g in gifts:
        sender = user_repo.get_by_id(g.sender_id)

        results.append(ReceivedGiftResponse(
            id=g.id,
            sender_id=g.sender_id,
            sender_name=sender.name if sender else None,
            sender_avatar=sender.avatar_url if sender else None,
            gift_id=g.gift_id,
            gift_name=g.gift_name,
            gift_icon=g.gift_icon,
            gift_type=g.gift_type.value,
            count=g.count,
            price=g.price,
            total_amount=g.total_amount,
            message=g.message,
            sent_at=g.sent_at.isoformat(),
            is_seen=g.is_seen,
        ))

    return results


@router.get("/sent", response_model=List[ReceivedGiftResponse])
async def get_sent_gifts(
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """
    获取发送的礼物列表

    Args:
        limit: 返回数量上限

    Returns:
        发送的礼物列表
    """
    user_id = current_user["user_id"]
    db = next(get_db())
    gift_svc = get_gift_service(db)

    gifts = gift_svc.get_user_sent_gifts(user_id, limit)

    # 获取接收者信息
    from db.repositories import UserRepository
    user_repo = UserRepository(db)

    results = []
    for g in gifts:
        receiver = user_repo.get_by_id(g.receiver_id)

        results.append(ReceivedGiftResponse(
            id=g.id,
            sender_id=user_id,
            sender_name=None,
            sender_avatar=None,
            gift_id=g.gift_id,
            gift_name=g.gift_name,
            gift_icon=g.gift_icon,
            gift_type=g.gift_type.value,
            count=g.count,
            price=g.price,
            total_amount=g.total_amount,
            message=g.message,
            sent_at=g.sent_at.isoformat(),
            is_seen=g.is_seen,
        ))

    return results


@router.get("/stats", response_model=GiftStatsResponse)
async def get_gift_stats(current_user: dict = Depends(get_current_user)):
    """
    获取用户礼物统计

    Returns:
        礼物统计数据
    """
    user_id = current_user["user_id"]
    db = next(get_db())
    gift_svc = get_gift_service(db)

    stats = gift_svc.get_user_stats(user_id)
    unseen_count = gift_svc.get_unseen_gifts_count(user_id)

    return GiftStatsResponse(
        user_id=user_id,
        total_received=stats.total_received,
        total_received_amount=stats.total_received_amount,
        total_sent=stats.total_sent,
        total_sent_amount=stats.total_sent_amount,
        most_received_gift=stats.most_received_gift,
        most_sent_gift=stats.most_sent_gift,
        unseen_count=unseen_count,
    )


@router.post("/{transaction_id}/seen")
async def mark_gift_seen(
    transaction_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    标记礼物已查看

    Args:
        transaction_id: 交易记录 ID

    Returns:
        标记结果
    """
    user_id = current_user["user_id"]

    db = next(get_db())
    gift_svc = get_gift_service(db)

    success = gift_svc.mark_gift_seen(transaction_id)

    if not success:
        raise HTTPException(status_code=404, detail="礼物记录不存在")

    return {
        "success": True,
        "message": "已标记为已查看",
    }


@router.get("/unseen-count")
async def get_unseen_gifts_count(current_user: dict = Depends(get_current_user)):
    """
    获取未查看礼物数量

    Returns:
        未查看礼物数量
    """
    user_id = current_user["user_id"]
    db = next(get_db())
    gift_svc = get_gift_service(db)

    count = gift_svc.get_unseen_gifts_count(user_id)

    return {
        "unseen_count": count,
    }