"""
P18 关系进阶 API - v1.18 关系进阶功能

API 端点:
- /api/relationship/state/* - 关系状态管理
- /api/dating-advice/* - 约会建议
- /api/love-guidance/* - 恋爱指导
- /api/chat-suggestion/* - 聊天建议
- /api/gift-recommendation/* - 礼物推荐
- /api/relationship/health/* - 关系健康度
"""
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field

from services.relationship_advanced_service import (
    relationship_state_service,
    dating_advice_service,
    love_guidance_service,
    chat_suggestion_service,
    gift_recommendation_service,
    relationship_health_service
)
from utils.logger import logger

router = APIRouter(prefix="/api", tags=["关系进阶功能"])


# ============= 请求/响应模型 =============

class RelationshipStateRequest(BaseModel):
    """关系状态设置请求"""
    new_state: str = Field(..., description="新的关系状态")
    transition_type: Optional[str] = Field("manual", description="转换类型")
    transition_reason: Optional[str] = Field(None, description="转换原因")
    trigger_event: Optional[str] = Field(None, description="触发事件")


class RelationshipStateResponse(BaseModel):
    """关系状态响应"""
    id: str
    state: str
    state_label: str
    state_description: Optional[str]
    confirmed_by_user1: bool
    confirmed_by_user2: bool
    state_changed_at: Optional[str]
    ai_confidence: float
    created_at: str


class DatingAdviceRequest(BaseModel):
    """约会建议请求"""
    advice_type: str = Field(..., description="建议类型")
    target_user_id: Optional[str] = Field(None, description="约会对象 ID")
    preferences: Optional[Dict[str, Any]] = Field(None, description="用户偏好")


class LoveGuidanceRequest(BaseModel):
    """恋爱指导请求"""
    guidance_type: str = Field(..., description="指导类型")
    scenario: Optional[str] = Field(None, description="场景描述")
    target_user_id: Optional[str] = Field(None, description="相关对象 ID")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文")


class ChatSuggestionRequest(BaseModel):
    """聊天建议请求"""
    suggestion_type: str = Field(..., description="建议类型")
    conversation_id: Optional[str] = Field(None, description="会话 ID")
    target_user_id: Optional[str] = Field(None, description="对象 ID")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文")


class GiftRecommendationRequest(BaseModel):
    """礼物推荐请求"""
    occasion: str = Field(..., description="场合")
    recipient_user_id: Optional[str] = Field(None, description="收礼人 ID")
    budget_min: Optional[float] = Field(None, description="预算下限")
    budget_max: Optional[float] = Field(None, description="预算上限")


# ============= 关系状态管理 API =============

@router.get("/relationship/state/{partner_id}", response_model=RelationshipStateResponse)
async def get_relationship_state(
    partner_id: str,
    current_user_id: str = Query(..., description="当前用户 ID")
):
    """获取与指定用户的关系状态"""
    try:
        state = relationship_state_service.get_relationship_state(current_user_id, partner_id)
        if not state:
            raise HTTPException(status_code=404, detail="关系状态不存在")
        return state
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting relationship state: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/relationship/state/{partner_id}")
async def set_relationship_state(
    partner_id: str,
    request: RelationshipStateRequest,
    current_user_id: str = Query(..., description="当前用户 ID")
):
    """设置关系状态"""
    try:
        state_id = relationship_state_service.set_relationship_state(
            user_id_1=current_user_id,
            user_id_2=partner_id,
            new_state=request.new_state,
            transition_type=request.transition_type,
            transition_reason=request.transition_reason,
            trigger_event=request.trigger_event,
            user_id_setting=current_user_id
        )
        return {"success": True, "state_id": state_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error setting relationship state: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/relationship/state/{partner_id}/history")
async def get_relationship_state_history(
    partner_id: str,
    current_user_id: str = Query(..., description="当前用户 ID"),
    limit: int = Query(20, ge=1, le=100)
):
    """获取关系状态变更历史"""
    try:
        history = relationship_state_service.get_state_history(
            user_id_1=current_user_id,
            user_id_2=partner_id,
            limit=limit
        )
        return {"history": history}
    except Exception as e:
        logger.error(f"Error getting state history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/relationship/state/{partner_id}/confirm")
async def confirm_relationship_state(
    partner_id: str,
    current_user_id: str = Query(..., description="当前用户 ID")
):
    """确认关系状态"""
    try:
        success = relationship_state_service.confirm_relationship_state(
            user_id_1=current_user_id,
            user_id_2=partner_id,
            confirming_user_id=current_user_id
        )
        return {"success": success}
    except Exception as e:
        logger.error(f"Error confirming relationship state: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============= 约会建议 API =============

@router.post("/dating-advice/generate")
async def generate_dating_advice(
    request: DatingAdviceRequest,
    current_user_id: str = Query(..., description="当前用户 ID")
):
    """生成约会建议"""
    try:
        advice_id = dating_advice_service.generate_advice(
            user_id=current_user_id,
            target_user_id=request.target_user_id,
            advice_type=request.advice_type,
            user_preferences=request.preferences
        )
        return {"success": True, "advice_id": advice_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating dating advice: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dating-advice")
async def get_dating_advice(
    current_user_id: str = Query(..., description="当前用户 ID"),
    status: Optional[str] = Query(None, description="筛选状态"),
    limit: int = Query(10, ge=1, le=50)
):
    """获取用户的约会建议列表"""
    try:
        advices = dating_advice_service.get_advice(
            user_id=current_user_id,
            status=status,
            limit=limit
        )
        return {"advices": advices}
    except Exception as e:
        logger.error(f"Error getting dating advice: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dating-advice/{advice_id}/accept")
async def accept_dating_advice(
    advice_id: str,
    current_user_id: str = Query(..., description="当前用户 ID")
):
    """接受约会建议"""
    try:
        success = dating_advice_service.accept_advice(advice_id)
        return {"success": success}
    except Exception as e:
        logger.error(f"Error accepting dating advice: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============= 恋爱指导 API =============

@router.post("/love-guidance/generate")
async def generate_love_guidance(
    request: LoveGuidanceRequest,
    current_user_id: str = Query(..., description="当前用户 ID")
):
    """生成恋爱指导"""
    try:
        guidance_id = love_guidance_service.generate_guidance(
            user_id=current_user_id,
            guidance_type=request.guidance_type,
            scenario=request.scenario,
            target_user_id=request.target_user_id,
            context=request.context
        )
        return {"success": True, "guidance_id": guidance_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating love guidance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/love-guidance")
async def get_love_guidance(
    current_user_id: str = Query(..., description="当前用户 ID"),
    guidance_type: Optional[str] = Query(None, description="筛选类型"),
    limit: int = Query(10, ge=1, le=50)
):
    """获取用户的恋爱指导列表"""
    try:
        guidances = love_guidance_service.get_guidance(
            user_id=current_user_id,
            guidance_type=guidance_type,
            limit=limit
        )
        return {"guidances": guidances}
    except Exception as e:
        logger.error(f"Error getting love guidance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============= 聊天建议 API =============

@router.post("/chat-suggestion/generate")
async def generate_chat_suggestion(
    request: ChatSuggestionRequest,
    current_user_id: str = Query(..., description="当前用户 ID")
):
    """生成聊天建议"""
    try:
        suggestion_id = chat_suggestion_service.generate_suggestion(
            user_id=current_user_id,
            suggestion_type=request.suggestion_type,
            conversation_id=request.conversation_id,
            target_user_id=request.target_user_id,
            context=request.context
        )
        return {"success": True, "suggestion_id": suggestion_id}
    except Exception as e:
        logger.error(f"Error generating chat suggestion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat-suggestion")
async def get_chat_suggestions(
    current_user_id: str = Query(..., description="当前用户 ID"),
    suggestion_type: Optional[str] = Query(None, description="筛选类型"),
    limit: int = Query(10, ge=1, le=50)
):
    """获取用户的聊天建议列表"""
    try:
        suggestions = chat_suggestion_service.get_suggestions(
            user_id=current_user_id,
            suggestion_type=suggestion_type,
            limit=limit
        )
        return {"suggestions": suggestions}
    except Exception as e:
        logger.error(f"Error getting chat suggestions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat-suggestion/{suggestion_id}/use")
async def use_chat_suggestion(
    suggestion_id: str,
    current_user_id: str = Query(..., description="当前用户 ID")
):
    """标记聊天建议已使用"""
    try:
        success = chat_suggestion_service.mark_used(suggestion_id)
        return {"success": success}
    except Exception as e:
        logger.error(f"Error marking suggestion used: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============= 礼物推荐 API =============

@router.post("/gift-recommendation/generate")
async def generate_gift_recommendation(
    request: GiftRecommendationRequest,
    current_user_id: str = Query(..., description="当前用户 ID")
):
    """生成礼物推荐"""
    try:
        budget_range = None
        if request.budget_min is not None and request.budget_max is not None:
            budget_range = (request.budget_min, request.budget_max)

        recommendation_id = gift_recommendation_service.generate_recommendation(
            user_id=current_user_id,
            occasion=request.occasion,
            recipient_user_id=request.recipient_user_id,
            budget_range=budget_range
        )
        return {"success": True, "recommendation_id": recommendation_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating gift recommendation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/gift-recommendation")
async def get_gift_recommendations(
    current_user_id: str = Query(..., description="当前用户 ID"),
    occasion: Optional[str] = Query(None, description="筛选场合"),
    limit: int = Query(10, ge=1, le=50)
):
    """获取用户的礼物推荐列表"""
    try:
        recommendations = gift_recommendation_service.get_recommendations(
            user_id=current_user_id,
            occasion=occasion,
            limit=limit
        )
        return {"recommendations": recommendations}
    except Exception as e:
        logger.error(f"Error getting gift recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============= 关系健康度 API =============

@router.post("/relationship/health/assess")
async def assess_relationship_health(
    partner_id: str,
    current_user_id: str = Query(..., description="当前用户 ID")
):
    """评估关系健康度"""
    try:
        result = relationship_health_service.assess_relationship_health(
            user_id_1=current_user_id,
            user_id_2=partner_id
        )
        return result
    except Exception as e:
        logger.error(f"Error assessing relationship health: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/relationship/health/{partner_id}")
async def get_relationship_health(
    partner_id: str,
    current_user_id: str = Query(..., description="当前用户 ID")
):
    """获取关系健康度评估历史"""
    # 这个端点可以扩展为返回历史评估记录
    return {"message": "此端点待实现", "partner_id": partner_id}
