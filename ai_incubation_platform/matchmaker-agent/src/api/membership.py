"""
会员订阅 API
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime

from models.membership import (
    MembershipTier,
    MembershipFeature,
    MembershipCreate,
    MEMBERSHIP_FEATURES,
)
from services.membership_service import get_membership_service
from auth.jwt import get_current_user
from utils.logger import logger
from db.database import get_db


router = APIRouter(prefix="/api/membership", tags=["membership"])


# ==================== 请求/响应模型 ====================

class MembershipPlanResponse(BaseModel):
    """会员计划响应"""
    tier: str
    duration_months: int
    price: float
    original_price: float
    discount_rate: float
    features: List[str]
    popular: bool


class MembershipBenefitResponse(BaseModel):
    """会员权益响应"""
    feature: str
    name: str
    description: str
    icon: str


class MembershipStatusResponse(BaseModel):
    """会员状态响应"""
    tier: str
    status: str
    is_active: bool
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    auto_renew: bool
    features: List[str]
    limits: Dict[str, int]


class MembershipOrderRequest(BaseModel):
    """创建会员订单请求"""
    tier: str
    duration_months: int = 1
    payment_method: str = "wechat"
    auto_renew: bool = False
    coupon_code: Optional[str] = None


class MembershipOrderResponse(BaseModel):
    """会员订单响应"""
    id: str
    user_id: str
    tier: str
    duration_months: int
    amount: float
    status: str
    payment_url: Optional[str] = None
    created_at: str


class MembershipStatsResponse(BaseModel):
    """会员统计响应"""
    total_members: int
    standard_members: int
    premium_members: int
    new_members_this_month: int
    revenue_this_month: float


class CheckFeatureRequest(BaseModel):
    """检查功能权限请求"""
    feature: str


class CheckFeatureResponse(BaseModel):
    """检查功能权限响应"""
    allowed: bool
    message: str


class UseFeatureRequest(BaseModel):
    """使用功能请求"""
    action: str


# ==================== API 端点 ====================

@router.get("/plans", response_model=List[MembershipPlanResponse])
async def get_membership_plans():
    """
    获取所有会员计划

    返回不同等级、不同时长的会员计划及其价格、权益
    """
    db = next(get_db())
    membership_svc = get_membership_service(db)
    plans = membership_svc.get_membership_plans()
    return plans


@router.get("/benefits", response_model=List[MembershipBenefitResponse])
async def get_membership_benefits():
    """
    获取会员权益说明

    返回所有会员权益的详细说明
    """
    db = next(get_db())
    membership_svc = get_membership_service(db)
    benefits = membership_svc.get_membership_benefits()
    return benefits


@router.get("/status", response_model=MembershipStatusResponse)
async def get_membership_status(current_user: dict = Depends(get_current_user)):
    """
    获取当前用户的会员状态
    """
    user_id = current_user["user_id"]
    db = next(get_db())
    membership_svc = get_membership_service(db)
    membership = membership_svc.get_user_membership(user_id)

    # 获取当前等级的所有权益
    tier_features = []
    if membership.is_active():
        tier_features = [f.value for f in MEMBERSHIP_FEATURES.get(membership.tier, [])]

    # 获取限制
    limits = {}
    for limit_type in ["daily_likes", "daily_super_likes", "daily_rewinds", "daily_boosts"]:
        limits[limit_type] = membership.get_limit(limit_type)

    return MembershipStatusResponse(
        tier=membership.tier.value,
        status=membership.status,
        is_active=membership.is_active(),
        start_date=membership.start_date.isoformat() if membership.start_date else None,
        end_date=membership.end_date.isoformat() if membership.end_date else None,
        auto_renew=membership.auto_renew,
        features=tier_features,
        limits=limits,
    )


@router.post("/order", response_model=MembershipOrderResponse)
async def create_membership_order(
    request: MembershipOrderRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    创建会员订单

    - **tier**: 会员等级 (standard, premium)
    - **duration_months**: 订阅时长 (1, 3, 12)
    - **payment_method**: 支付方式 (wechat, alipay)
    - **auto_renew**: 是否自动续费
    - **coupon_code**: 优惠码 (可选)
    """
    user_id = current_user["user_id"]
    db = next(get_db())
    membership_svc = get_membership_service(db)

    # 验证订阅时长
    if request.duration_months not in [1, 3, 12]:
        raise HTTPException(status_code=400, detail="订阅时长必须是 1、3 或 12 个月")

    # 计算订单金额
    from models.membership import MembershipTier, MEMBERSHIP_PRICES
    tier = MembershipTier(request.tier)
    prices = MEMBERSHIP_PRICES[tier]
    duration_key = {1: "monthly", 3: "quarterly", 12: "yearly"}.get(
        request.duration_months, "monthly"
    )
    original_amount = prices.get(duration_key, prices["monthly"])

    # 应用优惠券
    final_amount = original_amount
    discount_amount = 0.0
    used_coupon_id = None

    if request.coupon_code:
        from services.payment_service import get_payment_service
        payment_svc = get_payment_service(db)

        from models.payment import ApplyCouponRequest
        apply_req = ApplyCouponRequest(
            coupon_code=request.coupon_code,
            tier=request.tier,
            duration_months=request.duration_months,
            amount=original_amount,
        )
        apply_result = payment_svc.apply_coupon(user_id, apply_req)

        if not apply_result.valid:
            raise HTTPException(status_code=400, detail=apply_result.message)

        discount_amount = apply_result.discount_amount
        final_amount = apply_result.final_amount

        # 获取用户优惠券 ID
        user_coupons = payment_svc.get_user_coupons(user_id, status="active")
        for uc in user_coupons:
            if uc.coupon_code == request.coupon_code.upper():
                used_coupon_id = uc.id
                break

    # 创建订单（使用 discount_code 和 final_amount）
    order = membership_svc.create_membership_order_with_amount(
        user_id=user_id,
        tier=tier,
        duration_months=request.duration_months,
        amount=final_amount,
        original_amount=original_amount,
        discount_code=request.coupon_code,
        payment_method=request.payment_method,
        auto_renew=request.auto_renew,
    )

    # TODO: 生成支付 URL（对接微信支付/支付宝）
    payment_url = None  # 实际需要对接支付接口

    return MembershipOrderResponse(
        id=order.id,
        user_id=order.user_id,
        tier=order.tier.value,
        duration_months=order.duration_months,
        amount=order.amount,
        status=order.status,
        payment_url=payment_url,
        created_at=order.created_at.isoformat(),
    )


@router.post("/payment/callback")
async def payment_callback(request: Request):
    """
    支付回调接口

    接收支付平台的回调通知，更新订单状态并激活会员
    """
    try:
        data = await request.json()

        # 验证签名（实际使用时需要验证支付平台的签名）
        # verify_payment_signature(data)

        order_id = data.get("order_id")
        success = data.get("success", False)

        if not order_id:
            raise HTTPException(status_code=400, detail="缺少订单 ID")

        db = next(get_db())
        membership_svc = get_membership_service(db)

        # 处理支付结果
        order = membership_svc.process_payment(order_id, {"success": success})

        return {
            "success": True,
            "order_id": order.id,
            "status": order.status,
        }
    except Exception as e:
        logger.error(f"支付回调失败：{e}")
        raise HTTPException(status_code=500, detail="处理支付回调失败")


@router.post("/check-feature", response_model=CheckFeatureResponse)
async def check_feature_access(
    request: CheckFeatureRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    检查用户是否有权访问某个会员功能

    - **feature**: 功能标识 (如 unlimited_likes, super_likes 等)
    """
    user_id = current_user["user_id"]
    db = next(get_db())
    membership_svc = get_membership_service(db)

    try:
        feature = MembershipFeature(request.feature)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"未知的功能：{request.feature}")

    allowed = membership_svc.check_feature_access(user_id, feature)

    return CheckFeatureResponse(
        allowed=allowed,
        message="" if allowed else f"需要开通会员才能使用{feature.value}功能"
    )


@router.post("/check-limit")
async def check_action_limit(
    request: UseFeatureRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    检查用户是否可以执行某个动作

    - **action**: 动作类型 (like, super_like, rewind, boost)
    """
    user_id = current_user["user_id"]
    db = next(get_db())
    membership_svc = get_membership_service(db)

    allowed, message = membership_svc.check_action_limit(user_id, request.action)

    return {
        "allowed": allowed,
        "message": message,
    }


@router.post("/use-feature")
async def use_feature(
    request: UseFeatureRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    使用会员功能（计数类）

    - **action**: 功能类型 (super_like, rewind, boost)
    """
    user_id = current_user["user_id"]
    db = next(get_db())
    membership_svc = get_membership_service(db)

    # 映射 action 到 feature
    action_to_feature = {
        "super_like": MembershipFeature.SUPER_LIKES,
        "rewind": MembershipFeature.REWIND,
        "boost": MembershipFeature.BOOST,
    }

    if request.action not in action_to_feature:
        raise HTTPException(status_code=400, detail=f"不支持的动作：{request.action}")

    feature = action_to_feature[request.action]
    success, message = membership_svc.use_feature(user_id, feature)

    if not success:
        raise HTTPException(status_code=403, detail=message)

    return {
        "success": True,
        "message": message,
    }


@router.post("/cancel-subscription")
async def cancel_subscription(current_user: dict = Depends(get_current_user)):
    """
    取消自动续费

    用户可随时取消自动续费，已支付的费用不会退还
    """
    user_id = current_user["user_id"]
    db = next(get_db())
    membership_svc = get_membership_service(db)

    success = membership_svc.cancel_subscription(user_id)

    if not success:
        raise HTTPException(status_code=400, detail="没有活跃的订阅")

    return {
        "success": True,
        "message": "已取消自动续费，会员权益将持续到到期日",
    }


@router.get("/stats", response_model=MembershipStatsResponse)
async def get_membership_stats(current_user: dict = Depends(get_current_user)):
    """
    获取会员统计信息（仅管理员）

    TODO: 添加管理员权限验证
    """
    # TODO: 验证管理员权限
    # if not is_admin(current_user):
    #     raise HTTPException(status_code=403, detail="需要管理员权限")

    db = next(get_db())
    membership_svc = get_membership_service(db)
    stats = membership_svc.get_membership_stats()
    return MembershipStatsResponse(**stats)


@router.get("/compare")
async def compare_membership_tiers():
    """
    对比不同会员等级的权益
    """
    comparison = {
        "features": [],
        "tiers": ["free", "standard", "premium"],
    }

    # 获取所有权益
    all_features = list(MembershipFeature)

    for feature in all_features:
        feature_info = {
            "feature": feature.value,
            "availability": {}
        }

        for tier in MembershipTier:
            features = MEMBERSHIP_FEATURES.get(tier, [])
            feature_info["availability"][tier.value] = feature in features

        comparison["features"].append(feature_info)

    # 添加价格信息
    comparison["pricing"] = {}
    for tier in [MembershipTier.STANDARD, MembershipTier.PREMIUM]:
        prices = MEMBERSHIP_PRICES[tier]
        comparison["pricing"][tier.value] = prices

    return comparison
