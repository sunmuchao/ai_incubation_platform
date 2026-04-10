"""
许愿模式 API 路由

提供许愿模式（Agentic Engine）的 API 接口：
- 模式切换
- 许愿对话
- 定价信息
- 使用统计
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

from matching.engine_base import EngineType, MatchRequest
from matching.engine_switch import get_engine_switch, EngineSwitch
from matching.agentic_engine import get_agentic_engine, get_advisor, WishModeAdvisor
from utils.logger import logger
from auth.jwt import decode_access_token


router = APIRouter(prefix="/api/wish-mode", tags=["wish-mode"])
security = HTTPBearer()


def get_current_user_id(credentials: HTTPAuthorizationCredentials) -> Optional[str]:
    """从 credentials 中获取用户 ID"""
    if credentials and credentials.credentials:
        return decode_access_token(credentials.credentials)
    return None


# ============= Pydantic 模型 =============

class ToggleWishModeRequest(BaseModel):
    """切换许愿模式请求"""
    user_id: Optional[str] = None  # 可选，从 JWT 获取


class ToggleWishModeResponse(BaseModel):
    """切换许愿模式响应"""
    success: bool
    engine_type: str
    reason: Optional[str] = None
    message: Optional[str] = None
    pricing: Optional[Dict[str, Any]] = None
    warning: Optional[str] = None
    payment_status: Optional[Dict[str, Any]] = None


class WishChatRequest(BaseModel):
    """许愿对话请求"""
    user_id: Optional[str] = None
    wish_description: str = Field(..., min_length=10, max_length=1000, description="用户愿望描述")
    limit: int = Field(default=5, ge=1, le=20, description="返回候选人数")
    conversation_history: Optional[List[Dict[str, str]]] = None


class WishChatResponse(BaseModel):
    """许愿对话响应"""
    success: bool
    candidates: Optional[List[Dict[str, Any]]] = None
    wish_analysis: Optional[Dict[str, Any]] = None
    disclaimer: Optional[str] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    remaining_count: Optional[int] = None


class PricingResponse(BaseModel):
    """定价响应"""
    pay_per_use: Dict[str, Any]
    subscription: Dict[str, Any]
    member_benefits: Dict[str, Any]
    disclaimer: str


class UsageStatisticsResponse(BaseModel):
    """使用统计响应"""
    total_sessions: int
    total_candidates: int
    first_used: Optional[str] = None
    last_used: Optional[str] = None
    by_type: Optional[Dict[str, int]] = None


# ============= API 端点 =============

@router.post("/toggle", response_model=ToggleWishModeResponse)
async def toggle_wish_mode(
    request: ToggleWishModeRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    engine_switch: EngineSwitch = Depends(get_engine_switch)
):
    """
    切换许愿模式

    检查用户付费状态，返回切换结果。

    Response:
    - success: 是否成功切换
    - engine_type: 当前引擎类型
    - reason: 失败原因（如果失败）
    - pricing: 定价信息（如果需要付费）
    - warning: 免责声明
    """
    # 从 JWT 获取用户 ID
    user_id = request.user_id or get_current_user_id(credentials)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID not found"
        )

    result = await engine_switch.switch_to_wish_mode(user_id)

    response = ToggleWishModeResponse(
        success=result.success,
        engine_type=result.engine_type.value,
        reason=result.reason,
        message=result.message,
        pricing=result.pricing,
        warning=result.warning,
        payment_status={
            "access": result.payment_status.access if result.payment_status else False,
            "type": result.payment_status.payment_type.value if result.payment_status else "none",
            "remaining_count": result.payment_status.remaining_count if result.payment_status else 0,
        } if result.payment_status else None
    )

    logger.info(
        f"WishModeAPI: toggle request from user={user_id}, "
        f"success={result.success}"
    )

    return response


@router.post("/chat", response_model=WishChatResponse)
async def wish_mode_chat(
    request: WishChatRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    engine_switch: EngineSwitch = Depends(get_engine_switch)
):
    """
    许愿模式对话

    用户描述需求，AI顾问分析并推荐。

    流程：
    1. 消耗次数（付费检查）
    2. AI 分析用户愿望
    3. 执行推荐
    4. 生成风险提示
    5. 返回结果
    """
    # 从 JWT 获取用户 ID
    user_id = request.user_id or get_current_user_id(credentials)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID not found"
        )

    # 构建匹配请求
    match_request = MatchRequest(
        user_id=user_id,
        limit=request.limit,
        wish_description=request.wish_description,
        conversation_history=request.conversation_history or []
    )

    # 执行许愿模式匹配
    result = await engine_switch.match(match_request, EngineType.AGENTIC)

    if not result.success:
        return WishChatResponse(
            success=False,
            error=result.error,
            error_code=result.error_code
        )

    # 转换候选人为字典格式
    candidates_dict = []
    for candidate in result.candidates:
        candidates_dict.append({
            "user_id": candidate.user_id,
            "name": candidate.name,
            "score": round(candidate.score * 100),
            "age": candidate.age,
            "location": candidate.location,
            "interests": candidate.interests[:5],
            "match_points": candidate.match_points,
            "attention_points": candidate.attention_points,
            "risk_warnings": candidate.risk_warnings,
            "reasoning": candidate.reasoning,
        })

    # 获取剩余次数
    usage = await engine_switch.get_user_usage(user_id)

    response = WishChatResponse(
        success=True,
        candidates=candidates_dict,
        wish_analysis={
            "core_needs": result.wish_analysis.core_needs if result.wish_analysis else [],
            "hard_conditions": result.wish_analysis.hard_conditions if result.wish_analysis else [],
            "soft_preferences": result.wish_analysis.soft_preferences if result.wish_analysis else [],
            "risk_level": result.wish_analysis.risk_analysis.level.value if result.wish_analysis and result.wish_analysis.risk_analysis else "medium",
            "risk_description": result.wish_analysis.risk_analysis.description if result.wish_analysis and result.wish_analysis.risk_analysis else "",
            "suggestions": result.wish_analysis.suggestions if result.wish_analysis else [],
        } if result.wish_analysis else None,
        disclaimer=result.disclaimer,
        remaining_count=usage.get("total_sessions", 0)
    )

    logger.info(
        f"WishModeAPI: chat request from user={user_id}, "
        f"candidates={len(result.candidates)}, "
        f"latency={result.latency_ms:.2f}ms"
    )

    return response


@router.post("/analyze")
async def analyze_wish(
    request: WishChatRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    advisor: WishModeAdvisor = Depends(get_advisor)
):
    """
    分析用户愿望（仅分析，不推荐）

    用于预览分析结果，帮助用户调整愿望描述。
    不消耗次数。
    """
    user_id = request.user_id or get_current_user_id(credentials)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID not found"
        )

    # 获取用户画像
    from matching.rule_engine import get_rule_engine
    user_profile = get_rule_engine().get_registered_users().get(user_id, {})

    # 分析愿望
    wish_analysis = await advisor.analyze_user_wish(
        request.wish_description,
        user_profile
    )

    return {
        "success": True,
        "analysis": {
            "core_needs": wish_analysis.core_needs,
            "hard_conditions": wish_analysis.hard_conditions,
            "soft_preferences": wish_analysis.soft_preferences,
            "risk_analysis": {
                "level": wish_analysis.risk_analysis.level.value,
                "description": wish_analysis.risk_analysis.description,
                "warning": wish_analysis.risk_analysis.warning,
                "pool_size_estimate": wish_analysis.risk_analysis.pool_size_estimate,
                "competition_level": wish_analysis.risk_analysis.competition_level,
                "potential_risks": wish_analysis.risk_analysis.potential_risks,
            },
            "suggestions": wish_analysis.suggestions,
            "disclaimer": wish_analysis.disclaimer,
        }
    }


@router.get("/pricing", response_model=PricingResponse)
async def get_pricing(
    engine_switch: EngineSwitch = Depends(get_engine_switch)
):
    """
    获取定价信息

    返回许愿模式的定价方案。
    """
    pricing = engine_switch.get_pricing()

    return PricingResponse(
        pay_per_use=pricing["pay_per_use"],
        subscription=pricing["subscription"],
        member_benefits=pricing["member_benefits"],
        disclaimer=pricing["disclaimer"]
    )


@router.get("/usage", response_model=UsageStatisticsResponse)
async def get_usage_statistics(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    engine_switch: EngineSwitch = Depends(get_engine_switch)
):
    """
    获取使用统计

    返回用户在许愿模式的使用情况。
    """
    user_id = get_current_user_id(credentials)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID not found"
        )

    usage = await engine_switch.get_user_usage(user_id)

    return UsageStatisticsResponse(
        total_sessions=usage.get("total_sessions", 0),
        total_candidates=usage.get("total_candidates", 0),
        first_used=usage.get("first_used"),
        last_used=usage.get("last_used"),
        by_type=usage.get("by_type")
    )


@router.post("/close")
async def close_wish_session(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    agentic_engine = Depends(get_agentic_engine)
):
    """
    关闭许愿会话

    结束当前许愿模式会话，返回常规模式。
    """
    user_id = get_current_user_id(credentials)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID not found"
        )

    # 查找并关闭会话
    sessions = agentic_engine._sessions
    for session_id, session in sessions.items():
        if session.user_id == user_id and not session.is_completed:
            agentic_engine.close_session(session_id)
            logger.info(f"WishModeAPI: closed session {session_id} for user {user_id}")

    return {
        "success": True,
        "message": "会话已关闭，已返回常规模式"
    }


@router.get("/disclaimer")
async def get_disclaimer(
    engine_switch: EngineSwitch = Depends(get_engine_switch)
):
    """
    获取免责声明

    返回许愿模式的免责声明内容。
    """
    return {
        "success": True,
        "disclaimer": engine_switch._disclaimer
    }


# ============= 管理端点（可选） =============

@router.post("/admin/record-payment")
async def admin_record_payment(
    user_id: str,
    payment_type: str,
    details: Dict[str, Any],
    engine_switch: EngineSwitch = Depends(get_engine_switch)
):
    """
    记录用户付费（管理端）

    仅用于测试或管理操作。
    """
    from matching.engine_switch import PaymentType

    try:
        pt = PaymentType(payment_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid payment type: {payment_type}"
        )

    result = await engine_switch._payment_checker.record_payment(
        user_id,
        pt,
        details
    )

    return {
        "success": True,
        "payment_status": {
            "access": result.access,
            "type": result.payment_type.value,
            "remaining_count": result.remaining_count,
        }
    }