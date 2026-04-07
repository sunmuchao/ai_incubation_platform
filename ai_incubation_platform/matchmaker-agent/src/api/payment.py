"""
付费功能 API
- 优惠券管理
- 退款管理
- 发票管理
- 免费试用
- 订阅管理
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime

from models.payment import (
    CouponType, CouponStatus, CouponTier,
    RefundStatus, RefundReason,
    InvoiceType, InvoiceStatus,
    TrialStatus,
    SubscriptionStatus,
    CouponCreate, ApplyCouponRequest, ApplyCouponResponse,
    RefundCreateRequest, RefundApproveRequest, RefundRejectRequest,
    InvoiceCreateRequest, TrialStartRequest, SubscriptionCreateRequest,
)
from services.payment_service import get_payment_service
from auth.jwt import get_current_user
from db.database import get_db
from utils.logger import logger


router = APIRouter(prefix="/api/payment", tags=["payment"])


# ==================== 响应模型 ====================

class CouponResponse(BaseModel):
    """优惠券响应"""
    id: str
    code: str
    name: str
    description: str
    type: str
    value: float
    min_amount: float
    max_discount: Optional[float]
    applicable_tiers: List[str]
    usage_limit: Optional[int]
    per_user_limit: int
    new_user_only: bool
    valid_from: str
    valid_until: Optional[str]
    status: str


class UserCouponResponse(BaseModel):
    """用户优惠券响应"""
    id: str
    user_id: str
    coupon_code: str
    status: str
    used_at: Optional[str]
    claimed_at: str
    expires_at: Optional[str]
    coupon_name: str
    coupon_description: str


class RefundResponse(BaseModel):
    """退款响应"""
    id: str
    order_id: str
    refund_amount: float
    reason: str
    description: str
    status: str
    reviewed_at: Optional[str]
    review_note: str
    created_at: str


class InvoiceResponse(BaseModel):
    """发票响应"""
    id: str
    order_id: str
    invoice_number: str
    invoice_code: str
    invoice_type: str
    amount: float
    tax_amount: float
    buyer_name: str
    status: str
    invoice_url: Optional[str]
    created_at: str


class TrialResponse(BaseModel):
    """试用响应"""
    user_id: str
    tier: str
    duration_days: int
    started_at: Optional[str]
    ends_at: Optional[str]
    status: str
    converted_to_paid: bool


class SubscriptionResponse(BaseModel):
    """订阅响应"""
    user_id: str
    tier: str
    interval: str
    amount: float
    status: str
    current_period_start: str
    current_period_end: str
    cancel_at_period_end: bool


class PaymentStatsResponse(BaseModel):
    """支付统计响应"""
    total_orders: int
    paid_orders: int
    total_revenue: float
    refunded_amount: float
    net_revenue: float
    new_paying_users: int
    converted_from_trial: int


# ==================== 优惠券 API ====================

@router.get("/coupons/list")
async def list_coupons(current_user: dict = Depends(get_current_user)):
    """
    获取所有可用优惠券（仅管理员）
    TODO: 添加管理员权限验证
    """
    db = next(get_db())
    payment_svc = get_payment_service(db)

    # 这里简化处理，实际应该只返回活跃的优惠券
    from db.payment_models import CouponDB
    coupons = db.query(CouponDB).filter(CouponDB.status == "active").all()

    return [
        {
            "id": c.id,
            "code": c.code,
            "name": c.name,
            "type": c.type,
            "value": c.value,
            "min_amount": c.min_amount,
            "description": c.description,
        }
        for c in coupons
    ]


@router.post("/coupons/create")
async def create_coupon(
    request: CouponCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    创建优惠券（仅管理员）
    """
    db = next(get_db())
    payment_svc = get_payment_service(db)

    try:
        coupon = payment_svc.create_coupon({
            "code": request.code,
            "name": request.name,
            "description": request.description,
            "type": request.type.value,
            "value": request.value,
            "min_amount": request.min_amount,
            "max_discount": request.max_discount,
            "applicable_tiers": [t.value for t in request.applicable_tiers],
            "usage_limit": request.usage_limit,
            "per_user_limit": request.per_user_limit,
            "new_user_only": request.new_user_only,
            "valid_days": request.valid_days,
            "created_by": current_user.get("user_id"),
        })

        return {
            "success": True,
            "coupon": {
                "id": coupon.id,
                "code": coupon.code,
                "name": coupon.name,
            }
        }
    except Exception as e:
        logger.error(f"创建优惠券失败：{e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/coupons/claim")
async def claim_coupon(
    request: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    领取优惠券
    - **coupon_code**: 优惠码
    """
    coupon_code = request.get("coupon_code")
    if not coupon_code:
        raise HTTPException(status_code=400, detail="缺少优惠码")

    db = next(get_db())
    payment_svc = get_payment_service(db)

    success, message = payment_svc.claim_coupon(current_user["user_id"], coupon_code)

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return {"success": True, "message": message}


@router.get("/coupons/my", response_model=List[UserCouponResponse])
async def get_my_coupons(current_user: dict = Depends(get_current_user)):
    """
    获取我的优惠券
    """
    db = next(get_db())
    payment_svc = get_payment_service(db)

    user_coupons = payment_svc.get_user_coupons(current_user["user_id"])

    # 获取优惠券详情
    result = []
    for uc in user_coupons:
        coupon = payment_svc.get_coupon_by_code(uc.coupon_code)
        result.append(UserCouponResponse(
            id=uc.id,
            user_id=uc.user_id,
            coupon_code=uc.coupon_code,
            status=uc.status.value,
            used_at=uc.used_at.isoformat() if uc.used_at else None,
            claimed_at=uc.claimed_at.isoformat(),
            expires_at=uc.expires_at.isoformat() if uc.expires_at else None,
            coupon_name=coupon.name if coupon else "",
            coupon_description=coupon.description if coupon else "",
        ))

    return result


@router.post("/coupons/apply", response_model=ApplyCouponResponse)
async def apply_coupon(
    request: ApplyCouponRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    应用优惠券到订单

    - **coupon_code**: 优惠码
    - **tier**: 会员等级
    - **duration_months**: 订阅时长
    - **amount**: 订单金额
    """
    db = next(get_db())
    payment_svc = get_payment_service(db)

    return payment_svc.apply_coupon(current_user["user_id"], request)


# ==================== 退款 API ====================

@router.post("/refunds/create")
async def create_refund(
    request: RefundCreateRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    创建退款申请

    - **order_id**: 订单 ID
    - **reason**: 退款原因 (user_request, payment_failed, duplicate_order, system_error, other)
    - **description**: 详细描述
    """
    db = next(get_db())
    payment_svc = get_payment_service(db)

    try:
        refund = payment_svc.create_refund(
            order_id=request.order_id,
            user_id=current_user["user_id"],
            reason=request.reason,
            description=request.description,
        )

        return {
            "success": True,
            "refund_id": refund.id,
            "status": refund.status.value,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建退款申请失败：{e}")
        raise HTTPException(status_code=500, detail="创建退款申请失败")


@router.get("/refunds/my", response_model=List[RefundResponse])
async def get_my_refunds(current_user: dict = Depends(get_current_user)):
    """
    获取我的退款申请
    """
    db = next(get_db())
    payment_svc = get_payment_service(db)

    refunds = payment_svc.get_user_refunds(current_user["user_id"])

    return [
        RefundResponse(
            id=r.id,
            order_id=r.order_id,
            refund_amount=r.refund_amount,
            reason=r.reason.value,
            description=r.description,
            status=r.status.value,
            reviewed_at=r.reviewed_at.isoformat() if r.reviewed_at else None,
            review_note=r.review_note,
            created_at=r.created_at.isoformat(),
        )
        for r in refunds
    ]


@router.post("/refunds/approve")
async def approve_refund(
    request: RefundApproveRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    批准退款（仅管理员）
    """
    db = next(get_db())
    payment_svc = get_payment_service(db)

    try:
        payment_svc.approve_refund(
            refund_id=request.refund_id,
            reviewed_by=current_user["user_id"],
            note=request.note,
        )

        return {"success": True, "message": "退款已批准"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/refunds/reject")
async def reject_refund(
    request: RefundRejectRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    拒绝退款（仅管理员）
    """
    db = next(get_db())
    payment_svc = get_payment_service(db)

    try:
        payment_svc.reject_refund(
            refund_id=request.refund_id,
            reviewed_by=current_user["user_id"],
            note=request.note,
        )

        return {"success": True, "message": "退款已拒绝"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 发票 API ====================

@router.post("/invoices/create")
async def create_invoice(
    request: InvoiceCreateRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    创建发票申请

    - **order_id**: 订单 ID
    - **invoice_type**: 发票类型 (electronic, paper)
    - **buyer_name**: 购买方名称
    - **buyer_tax_id**: 购买方税号
    - **buyer_address**: 地址
    - **buyer_phone**: 电话
    - **buyer_bank**: 开户行及账号
    - **sent_to_email**: 发送邮箱 (电子发票)
    - **mailing_address**: 邮寄地址 (纸质发票)
    """
    db = next(get_db())
    payment_svc = get_payment_service(db)

    try:
        invoice = payment_svc.create_invoice(
            order_id=request.order_id,
            user_id=current_user["user_id"],
            invoice_data={
                "invoice_type": request.invoice_type.value,
                "buyer_name": request.buyer_name,
                "buyer_tax_id": request.buyer_tax_id,
                "buyer_address": request.buyer_address,
                "buyer_phone": request.buyer_phone,
                "buyer_bank": request.buyer_bank,
                "sent_to_email": request.sent_to_email,
                "mailing_address": request.mailing_address,
            }
        )

        return {
            "success": True,
            "invoice_id": invoice.id,
            "invoice_number": invoice.invoice_number,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/invoices/my", response_model=List[InvoiceResponse])
async def get_my_invoices(current_user: dict = Depends(get_current_user)):
    """
    获取我的发票
    """
    db = next(get_db())
    payment_svc = get_payment_service(db)

    invoices = payment_svc.get_user_invoices(current_user["user_id"])

    return [
        InvoiceResponse(
            id=i.id,
            order_id=i.order_id,
            invoice_number=i.invoice_number,
            invoice_code=i.invoice_code,
            invoice_type=i.invoice_type.value,
            amount=i.amount,
            tax_amount=i.tax_amount,
            buyer_name=i.buyer_name,
            status=i.status.value,
            invoice_url=i.invoice_url,
            created_at=i.created_at.isoformat(),
        )
        for i in invoices
    ]


@router.post("/invoices/{invoice_id}/issue")
async def issue_invoice(invoice_id: str, current_user: dict = Depends(get_current_user)):
    """
    开具发票（仅管理员）
    """
    db = next(get_db())
    payment_svc = get_payment_service(db)

    try:
        payment_svc.issue_invoice(invoice_id)
        return {"success": True, "message": "发票已开具"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/invoices/{invoice_id}/send")
async def send_invoice(
    invoice_id: str,
    request: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    发送发票（仅管理员）
    """
    email = request.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="缺少邮箱地址")

    db = next(get_db())
    payment_svc = get_payment_service(db)

    try:
        payment_svc.send_invoice(invoice_id, email)
        return {"success": True, "message": "发票已发送"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 免费试用 API ====================

@router.post("/trial/start")
async def start_trial(
    request: TrialStartRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    开始免费试用

    - **tier**: 试用会员等级 (默认 premium)
    - **duration_days**: 试用天数 (默认 7 天)
    """
    db = next(get_db())
    payment_svc = get_payment_service(db)

    success, message = payment_svc.start_free_trial(
        user_id=current_user["user_id"],
        tier=request.tier,
        duration_days=request.duration_days,
    )

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return {"success": True, "message": message}


@router.get("/trial/status")
async def get_trial_status(current_user: dict = Depends(get_current_user)):
    """
    获取试用状态
    """
    db = next(get_db())
    payment_svc = get_payment_service(db)

    trial = payment_svc.get_user_trial(current_user["user_id"])

    if not trial:
        return {"available": True, "message": "您有免费试用资格"}

    return {
        "available": False,
        "trial": {
            "tier": trial.tier,
            "duration_days": trial.duration_days,
            "started_at": trial.started_at.isoformat() if trial.started_at else None,
            "ends_at": trial.ends_at.isoformat() if trial.ends_at else None,
            "status": trial.status.value,
            "converted_to_paid": trial.converted_to_paid,
        }
    }


# ==================== 订阅管理 API ====================

@router.get("/subscription/status")
async def get_subscription_status(current_user: dict = Depends(get_current_user)):
    """
    获取订阅状态
    """
    db = next(get_db())
    payment_svc = get_payment_service(db)

    subscription = payment_svc.get_subscription(current_user["user_id"])

    if not subscription:
        return {"active": False, "message": "暂无活跃订阅"}

    return {
        "active": True,
        "subscription": {
            "tier": subscription.tier,
            "interval": subscription.interval,
            "amount": subscription.amount,
            "status": subscription.status.value,
            "current_period_start": subscription.current_period_start.isoformat(),
            "current_period_end": subscription.current_period_end.isoformat(),
            "cancel_at_period_end": subscription.cancel_at_period_end,
        }
    }


@router.post("/subscription/cancel")
async def cancel_subscription(
    request: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    取消订阅

    - **reason**: 取消原因 (可选)
    """
    db = next(get_db())
    payment_svc = get_payment_service(db)

    reason = request.get("reason", "")
    success = payment_svc.cancel_subscription(current_user["user_id"], reason)

    if not success:
        raise HTTPException(status_code=400, detail="没有活跃订阅")

    return {
        "success": True,
        "message": "订阅已取消，将持续使用到当前周期结束",
    }


# ==================== 统计 API ====================

@router.get("/stats")
async def get_payment_stats(current_user: dict = Depends(get_current_user)):
    """
    获取支付统计（仅管理员）
    """
    db = next(get_db())
    payment_svc = get_payment_service(db)

    stats = payment_svc.get_payment_stats()

    return {
        "total_orders": stats.total_orders,
        "paid_orders": stats.paid_orders,
        "total_revenue": stats.total_revenue,
        "refunded_amount": stats.refunded_amount,
        "net_revenue": stats.net_revenue,
        "new_paying_users": stats.new_paying_users,
        "converted_from_trial": stats.converted_from_trial,
    }


@router.get("/stats/coupons")
async def get_coupon_stats(current_user: dict = Depends(get_current_user)):
    """
    获取优惠券统计（仅管理员）
    """
    db = next(get_db())
    payment_svc = get_payment_service(db)

    stats = payment_svc.get_coupon_stats()

    return {
        "total_coupons": stats.total_coupons,
        "active_coupons": stats.active_coupons,
        "total_claimed": stats.total_claimed,
        "total_used": stats.total_used,
        "total_discount_amount": stats.total_discount_amount,
    }


@router.get("/stats/trials")
async def get_trial_stats(current_user: dict = Depends(get_current_user)):
    """
    获取试用统计（仅管理员）
    """
    db = next(get_db())
    payment_svc = get_payment_service(db)

    stats = payment_svc.get_trial_stats()

    return {
        "total_trials": stats.total_trials,
        "active_trials": stats.active_trials,
        "expired_trials": stats.expired_trials,
        "converted_trials": stats.converted_trials,
        "conversion_rate": stats.conversion_rate,
    }
