"""
P6 - 用户认证与订阅管理 API

API 端点：
1. 用户注册、登录、信息管理
2. 订阅管理
3. 用量查询
4. 审计日志查询
"""
from fastapi import APIRouter, HTTPException, Depends, Query, Body, Request
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, EmailStr
from datetime import datetime

from config.database import get_db
from services.user_service import UserService, get_user_service

router = APIRouter(prefix="/api/p6/auth", tags=["P6 - 用户认证与订阅管理"])


# ==================== 请求/响应模型 ====================

class RegisterRequest(BaseModel):
    """注册请求"""
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    company_name: Optional[str] = None
    phone: Optional[str] = None


class LoginRequest(BaseModel):
    """登录请求"""
    username: str
    password: str


class UserResponse(BaseModel):
    """用户响应"""
    id: str
    username: str
    email: str
    full_name: Optional[str] = None
    company_name: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool
    subscription_tier: str
    subscription_expires_at: Optional[str] = None
    created_at: str


class SubscriptionPlanResponse(BaseModel):
    """订阅套餐响应"""
    tier: str
    name: str
    price: float
    limits: Dict[str, Any]


class UsageStatsResponse(BaseModel):
    """用量统计响应"""
    user_id: str
    subscription_tier: str
    usage_stats: Dict[str, int]
    period: Dict[str, str]


# ==================== 认证中间件 ====================

async def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
) -> Optional[Dict[str, Any]]:
    """获取当前用户（从请求头获取）"""
    # 从 Authorization 头获取用户 ID（简化处理，生产环境应使用 JWT）
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None

    user_id = auth_header.replace("Bearer ", "")
    user_service = get_user_service(db)
    user = user_service.get_user(user_id)

    if not user or not user.is_active:
        return None

    return user.to_dict()


async def require_auth(
    request: Request,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """要求认证"""
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="未授权访问")
    return user


# ==================== 用户管理 API ====================

@router.post("/register", response_model=UserResponse)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    """用户注册"""
    user_service = get_user_service(db)

    try:
        user = user_service.create_user(
            username=request.username,
            email=request.email,
            password=request.password,
            full_name=request.full_name,
            company_name=request.company_name,
            phone=request.phone,
        )
        return user.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login")
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """用户登录"""
    user_service = get_user_service(db)

    user = user_service.authenticate(request.username, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    # 生成简单 token（生产环境应使用 JWT）
    token = user.id

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user.to_dict(),
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """获取当前用户信息"""
    return current_user


@router.put("/me")
async def update_current_user(
    full_name: Optional[str] = None,
    company_name: Optional[str] = None,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    password: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """更新当前用户信息"""
    user_service = get_user_service(db)

    update_data = {}
    if full_name is not None:
        update_data["full_name"] = full_name
    if company_name is not None:
        update_data["company_name"] = company_name
    if phone is not None:
        update_data["phone"] = phone
    if email is not None:
        update_data["email"] = email
    if password is not None:
        update_data["password"] = password

    try:
        user = user_service.update_user(current_user["id"], **update_data)
        return user.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 订阅管理 API ====================

@router.get("/subscription/plans", response_model=List[SubscriptionPlanResponse])
async def get_subscription_plans(db: Session = Depends(get_db)):
    """获取所有订阅套餐"""
    user_service = get_user_service(db)

    plans = []
    for tier, plan in user_service.SUBSCRIPTION_PLANS.items():
        plans.append({
            "tier": tier,
            "name": plan["name"],
            "price": plan["price"],
            "limits": plan["limits"],
        })

    return plans


@router.get("/subscription/my-plan")
async def get_my_subscription(
    current_user: Dict[str, Any] = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """获取当前用户订阅信息"""
    user_service = get_user_service(db)

    plan = user_service.get_subscription_plan(current_user["subscription_tier"])
    limits = user_service.get_user_limits(current_user["id"])

    return {
        "tier": current_user["subscription_tier"],
        "plan_name": plan["name"],
        "price": plan["price"],
        "limits": limits,
        "subscription_started_at": current_user.get("subscription_started_at"),
        "subscription_expires_at": current_user.get("subscription_expires_at"),
    }


@router.post("/subscription/upgrade")
async def upgrade_subscription(
    tier: str = Query(..., description="订阅等级：free/pro/enterprise"),
    current_user: Dict[str, Any] = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """升级订阅"""
    user_service = get_user_service(db)

    try:
        user = user_service.upgrade_subscription(current_user["id"], tier)
        return {
            "message": f"订阅已升级到 {tier}",
            "subscription_tier": user.subscription_tier,
            "subscription_expires_at": user.subscription_expires_at.isoformat(),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/subscription/cancel")
async def cancel_subscription(
    current_user: Dict[str, Any] = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """取消订阅（降级到免费版）"""
    user_service = get_user_service(db)

    try:
        user = user_service.cancel_subscription(current_user["id"])
        return {
            "message": "订阅已取消，已降级到免费版",
            "subscription_tier": user.subscription_tier,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 用量管理 API ====================

@router.get("/usage/stats", response_model=UsageStatsResponse)
async def get_usage_stats(
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    current_user: Dict[str, Any] = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """获取用量统计"""
    user_service = get_user_service(db)

    stats = user_service.get_usage_stats(
        current_user["id"],
        start_date=start_date,
        end_date=end_date
    )

    return stats


@router.get("/usage/check-limit")
async def check_limit(
    feature: str = Query(..., description="功能名称"),
    limit_key: str = Query(..., description="限制类型"),
    current_user: Dict[str, Any] = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """检查用量限制"""
    user_service = get_user_service(db)

    within_limit = user_service.check_limit(
        current_user["id"],
        feature=feature,
        limit_key=limit_key
    )

    return {
        "within_limit": within_limit,
        "feature": feature,
        "limit_key": limit_key,
    }


# ==================== 审计日志 API ====================

@router.get("/audit-logs")
async def get_audit_logs(
    limit: int = Query(50, ge=1, le=200, description="获取日志数量"),
    current_user: Dict[str, Any] = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """获取用户审计日志"""
    user_service = get_user_service(db)

    logs = user_service.get_audit_logs(current_user["id"], limit=limit)

    return {
        "logs": [log.to_dict() for log in logs],
        "count": len(logs),
    }
