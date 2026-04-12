"""
玫瑰表达 API 路由

参考 Hinge 的玫瑰机制：
- 发送玫瑰表达特别喜欢
- 查看 Standout 列表（收到玫瑰的人）
- 购买额外玫瑰
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from models.rose import (
    RoseBalance,
    RoseSendRequest,
    RoseSendResponse,
    StandoutListResponse,
    RosePurchaseDB,
)
from services.rose_service import get_rose_service, RoseService
from auth.jwt import get_current_user
from db.database import get_db
from utils.logger import logger

router = APIRouter(prefix="/api/rose", tags=["rose"])


# ==================== 请求/响应模型 ====================

class RoseBalanceResponse(BaseModel):
    """玫瑰余额响应"""
    available_count: int
    sent_count: int
    monthly_allocation: int
    next_refresh_date: str
    purchase_available: bool


class StandoutUserResponse(BaseModel):
    """Standout 用户响应"""
    user_id: str
    name: str
    age: int
    avatar_url: Optional[str]
    location: str
    bio: str
    interests: List[str]
    rose_received_at: str
    rose_count: int
    latest_message: Optional[str]
    compatibility_score: float
    standout_expires_at: str
    is_seen: bool


class RespondStandoutRequest(BaseModel):
    """回应 Standout 请求"""
    standout_user_id: str
    action: str  # "like" or "pass"


class PurchaseRoseRequest(BaseModel):
    """购买玫瑰请求"""
    package_type: str  # "single", "bundle_3", "bundle_5"
    payment_method: str = "wechat"


class PurchaseRoseResponse(BaseModel):
    """购买玫瑰响应"""
    success: bool
    message: str
    purchase_id: Optional[str] = None
    payment_url: Optional[str] = None
    rose_count: int = 0


class RosePackageResponse(BaseModel):
    """玫瑰套餐响应"""
    type: str
    count: int
    price: float
    original_price: float
    discount: Optional[str]
    price_per_rose: float


# ==================== API 端点 ====================

@router.get("/balance", response_model=RoseBalanceResponse)
async def get_rose_balance(current_user: dict = Depends(get_current_user)):
    """
    获取用户玫瑰余额

    返回可用玫瑰数、已发送数、下月刷新时间等
    """
    user_id = current_user["user_id"]
    db = next(get_db())
    rose_svc = get_rose_service(db)

    balance = rose_svc.get_user_balance(user_id)

    return RoseBalanceResponse(
        available_count=balance.available_count,
        sent_count=balance.sent_count,
        monthly_allocation=balance.monthly_allocation,
        next_refresh_date=balance.next_refresh_date.isoformat(),
        purchase_available=balance.purchase_available,
    )


@router.post("/send", response_model=RoseSendResponse)
async def send_rose(
    request: RoseSendRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    发送玫瑰

    Args:
        target_user_id: 目标用户 ID
        message: 附带消息（可选，最多 100 字）

    Returns:
        发送结果，包括剩余玫瑰数和是否匹配
    """
    user_id = current_user["user_id"]
    logger.info(f"Sending rose: {user_id} -> {request.target_user_id}")

    # 验证附带消息长度
    if request.message and len(request.message) > 100:
        raise HTTPException(status_code=400, detail="附带消息不能超过 100 字")

    db = next(get_db())
    rose_svc = get_rose_service(db)

    result = rose_svc.send_rose(user_id, request)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)

    return result


@router.get("/standout", response_model=StandoutListResponse)
async def get_standout_list(current_user: dict = Depends(get_current_user)):
    """
    获取 Standout 列表

    显示所有向你发送玫瑰的用户，按匹配度和发送时间排序
    """
    user_id = current_user["user_id"]
    db = next(get_db())
    rose_svc = get_rose_service(db)

    standout_list = rose_svc.get_standout_list(user_id)

    return standout_list


@router.post("/standout/respond")
async def respond_to_standout(
    request: RespondStandoutRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    回应 Standout 用户

    Args:
        standout_user_id: Standout 用户 ID
        action: 动作（like 或 pass）

    Returns:
        回应结果
    """
    user_id = current_user["user_id"]

    if request.action not in ["like", "pass"]:
        raise HTTPException(status_code=400, detail="动作必须是 like 或 pass")

    db = next(get_db())
    rose_svc = get_rose_service(db)

    success, message = rose_svc.respond_to_standout(
        user_id,
        request.standout_user_id,
        request.action
    )

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return {
        "success": True,
        "message": message,
        "action": request.action,
    }


@router.post("/purchase", response_model=PurchaseRoseResponse)
async def purchase_roses(
    request: PurchaseRoseRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    购买玫瑰

    Args:
        package_type: 套餐类型 (single, bundle_3, bundle_5)
        payment_method: 支付方式 (wechat, alipay)

    Returns:
        购买结果，包括支付链接
    """
    user_id = current_user["user_id"]
    logger.info(f"Purchasing roses: user={user_id}, package={request.package_type}")

    db = next(get_db())
    rose_svc = get_rose_service(db)

    success, message, purchase = rose_svc.purchase_roses(
        user_id,
        request.package_type,
        request.payment_method
    )

    if not success:
        raise HTTPException(status_code=400, detail=message)

    # 支付链接生成（当前使用 mock URL，集成支付后生成真实链接）
    payment_url = None
    if request.payment_method == "wechat":
        payment_url = f"https://wx.tenpay.com/mock?order_id={purchase.id}"
    elif request.payment_method == "alipay":
        payment_url = f"https://openapi.alipay.com/mock?order_id={purchase.id}"

    return PurchaseRoseResponse(
        success=True,
        message=message,
        purchase_id=purchase.id if purchase else None,
        payment_url=payment_url,
        rose_count=purchase.rose_count if purchase else 0,
    )


@router.post("/purchase/{purchase_id}/complete")
async def complete_purchase(
    purchase_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    完成购买（支付成功后调用）

    Args:
        purchase_id: 购买记录 ID

    Returns:
        完成结果，包括新增的玫瑰数
    """
    user_id = current_user["user_id"]

    db = next(get_db())
    rose_svc = get_rose_service(db)

    # 验证购买记录属于当前用户
    purchase = db.query(RosePurchaseDB).filter(
        RosePurchaseDB.id == purchase_id,
        RosePurchaseDB.user_id == user_id
    ).first()

    if not purchase:
        raise HTTPException(status_code=404, detail="购买记录不存在")

    if purchase.payment_status == "paid":
        raise HTTPException(status_code=400, detail="该购买已完成")

    success = rose_svc.complete_purchase(purchase_id)

    if not success:
        raise HTTPException(status_code=500, detail="完成购买失败")

    # 获取更新后的余额
    balance = rose_svc.get_user_balance(user_id)

    return {
        "success": True,
        "message": f"成功获得 {purchase.rose_count} 个玫瑰",
        "roses_added": purchase.rose_count,
        "total_available": balance.available_count,
    }


@router.get("/packages", response_model=List[RosePackageResponse])
async def get_rose_packages():
    """
    获取玫瑰购买套餐列表

    返回所有可购买的玫瑰套餐及价格
    """
    db = next(get_db())
    rose_svc = get_rose_service(db)

    packages = rose_svc.get_rose_packages()

    return packages


@router.get("/transactions")
async def get_rose_transactions(
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """
    获取玫瑰交易记录

    显示用户发送和收到的玫瑰历史
    """
    user_id = current_user["user_id"]
    db = next(get_db())

    from models.rose import RoseTransactionDB
    from sqlalchemy import or_

    # 查询发送和收到的记录
    transactions = db.query(RoseTransactionDB).filter(
        or_(
            RoseTransactionDB.sender_id == user_id,
            RoseTransactionDB.receiver_id == user_id
        )
    ).order_by(RoseTransactionDB.sent_at.desc()).limit(limit).all()

    results = []
    for t in transactions:
        is_sender = t.sender_id == user_id
        results.append({
            "id": t.id,
            "direction": "sent" if is_sender else "received",
            "target_user_id": t.receiver_id if is_sender else t.sender_id,
            "rose_source": t.rose_source,
            "status": t.status,
            "message": t.message,
            "compatibility_score": t.compatibility_score,
            "is_seen": t.is_seen,
            "sent_at": t.sent_at.isoformat(),
            "seen_at": t.seen_at.isoformat() if t.seen_at else None,
        })

    return {
        "transactions": results,
        "total": len(results),
    }