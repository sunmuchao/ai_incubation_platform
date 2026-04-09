"""
AI 持续学习 API

L4 功能：用户偏好记忆、历史行为学习
"""
from fastapi import APIRouter, Depends, HTTPException, Body, Query
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

from db.database import get_db, SessionLocal
from services.ai_learning_service import ai_learning_service, AILearningService
from utils.logger import logger
from auth.jwt import get_current_user

router = APIRouter(prefix="/api/ai-learning", tags=["L4-AI 持续学习"])


# ============= 请求/响应模型 =============

class PreferenceRequest(BaseModel):
    """偏好请求"""
    category: str = Field(..., description="偏好类别")
    preference_key: str = Field(..., description="偏好键")
    preference_value: Any = Field(..., description="偏好值")
    preference_type: str = Field(default="like", description="偏好类型：like/dislike/neutral")
    subcategory: Optional[str] = Field(None, description="子类别")
    confidence_score: float = Field(default=0.5, ge=0, le=1, description="置信度")
    inference_method: str = Field(default="rule_based", description="推断方法")


class PreferenceResponse(BaseModel):
    """偏好响应"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None


class PatternRequest(BaseModel):
    """模式请求"""
    pattern_type: str = Field(..., description="模式类型")
    pattern_data: Dict[str, Any] = Field(..., description="模式数据")
    pattern_strength: float = Field(default=0.5, ge=0, le=1, description="模式强度")


class PatternResponse(BaseModel):
    """模式响应"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None


class WeightAdjustmentRequest(BaseModel):
    """权重调整请求"""
    before_weights: Dict[str, float] = Field(..., description="调整前权重")
    after_weights: Dict[str, float] = Field(..., description="调整后权重")
    adjustment_reason: str = Field(..., description="调整原因")
    trigger_event_id: Optional[str] = Field(None, description="触发事件 ID")
    ai_reasoning: Optional[str] = Field(None, description="AI 推理说明")


class WeightAdjustmentResponse(BaseModel):
    """权重调整响应"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None


class LearningProfileResponse(BaseModel):
    """学习画像响应"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None


# ============= 辅助函数 =============

def get_learning_service(db: Session = Depends(get_db)) -> AILearningService:
    """获取 AI 学习服务实例"""
    return ai_learning_service


# ============= 偏好记忆 API =============

@router.get("/preferences", response_model=List[Dict])
async def get_my_preferences(
    category: Optional[str] = Query(None, description="偏好类别"),
    min_confidence: float = Query(default=0.0, ge=0, le=1, description="最小置信度"),
    current_user: dict = Depends(get_current_user),
    service: AILearningService = Depends(get_learning_service)
):
    """
    获取我的偏好列表

    返回 AI 从用户行为中学习到的所有偏好
    """
    user_id = current_user.get("user_id")
    preferences = service.get_user_preferences(
        user_id=user_id,
        category=category,
        min_confidence=min_confidence,
    )

    return {
        "success": True,
        "data": [p.to_dict() for p in preferences],
        "total": len(preferences),
    }


@router.post("/preferences/add", response_model=PreferenceResponse)
async def add_preference(
    request: PreferenceRequest,
    current_user: dict = Depends(get_current_user),
    service: AILearningService = Depends(get_learning_service)
):
    """
    添加/更新用户偏好

    AI 从用户行为中自动学习并添加偏好
    """
    user_id = current_user.get("user_id")

    success, message, preference = service.add_preference(
        user_id=user_id,
        category=request.category,
        preference_key=request.preference_key,
        preference_value=request.preference_value,
        preference_type=request.preference_type,
        subcategory=request.subcategory,
        confidence_score=request.confidence_score,
        inference_method=request.inference_method,
    )

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return PreferenceResponse(
        success=True,
        data=preference.to_dict(),
        message=message
    )


@router.delete("/preferences/remove")
async def remove_preference(
    category: str = Query(..., description="偏好类别"),
    preference_key: str = Query(..., description="偏好键"),
    current_user: dict = Depends(get_current_user),
    service: AILearningService = Depends(get_learning_service)
):
    """
    移除用户偏好

    用户可以手动移除 AI 学习到的不准确偏好
    """
    user_id = current_user.get("user_id")
    success, message = service.remove_preference(
        user_id=user_id,
        category=category,
        preference_key=preference_key,
    )

    return {
        "success": success,
        "message": message,
    }


# ============= 行为模式学习 API =============

@router.get("/patterns", response_model=List[Dict])
async def get_my_patterns(
    pattern_type: Optional[str] = Query(None, description="模式类型"),
    min_strength: float = Query(default=0.0, ge=0, le=1, description="最小模式强度"),
    validated_only: bool = Query(default=False, description="是否只返回已验证模式"),
    current_user: dict = Depends(get_current_user),
    service: AILearningService = Depends(get_learning_service)
):
    """
    获取我的行为模式

    返回 AI 从用户历史行为中学习到的模式
    """
    user_id = current_user.get("user_id")
    patterns = service.get_user_patterns(
        user_id=user_id,
        pattern_type=pattern_type,
        min_strength=min_strength,
        validated_only=validated_only,
    )

    return {
        "success": True,
        "data": [p.to_dict() for p in patterns],
        "total": len(patterns),
    }


@router.post("/patterns/learn", response_model=PatternResponse)
async def learn_pattern(
    request: PatternRequest,
    is_validated: bool = Query(default=False, description="是否已验证"),
    validation_source: str = Query(default="implicit", description="验证来源"),
    current_user: dict = Depends(get_current_user),
    service: AILearningService = Depends(get_learning_service)
):
    """
    学习行为模式

    AI 从用户行为中学习并识别模式
    """
    user_id = current_user.get("user_id")

    success, message, pattern = service.learn_pattern(
        user_id=user_id,
        pattern_type=request.pattern_type,
        pattern_data=request.pattern_data,
        pattern_strength=request.pattern_strength,
        is_validated=is_validated,
        validation_source=validation_source,
    )

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return PatternResponse(
        success=True,
        data=pattern.to_dict(),
        message=message
    )


@router.post("/patterns/{pattern_type}/validate")
async def validate_pattern(
    pattern_type: str,
    validation_source: str = Query(default="explicit", description="验证来源"),
    current_user: dict = Depends(get_current_user),
    service: AILearningService = Depends(get_learning_service)
):
    """
    验证行为模式

    用户确认 AI 学习到的模式是否准确
    """
    user_id = current_user.get("user_id")
    success, message = service.validate_pattern(
        user_id=user_id,
        pattern_type=pattern_type,
        validation_source=validation_source,
    )

    return {
        "success": success,
        "message": message,
    }


# ============= 匹配权重调整 API =============

@router.get("/weights/history")
async def get_weight_adjustment_history(
    limit: int = Query(default=20, ge=1, le=100, description="返回数量"),
    current_user: dict = Depends(get_current_user),
    service: AILearningService = Depends(get_learning_service)
):
    """
    获取权重调整历史

    返回 AI 对匹配权重的调整记录
    """
    user_id = current_user.get("user_id")
    adjustments = service.get_weight_adjustment_history(user_id, limit)

    return {
        "success": True,
        "data": [a.to_dict() for a in adjustments],
        "total": len(adjustments),
    }


@router.post("/weights/adjust", response_model=WeightAdjustmentResponse)
async def adjust_matching_weights(
    request: WeightAdjustmentRequest,
    current_user: dict = Depends(get_current_user),
    service: AILearningService = Depends(get_learning_service)
):
    """
    调整匹配权重

    AI 根据学习到的偏好自动调整匹配权重
    """
    user_id = current_user.get("user_id")

    success, message, adjustment = service.adjust_matching_weights(
        user_id=user_id,
        before_weights=request.before_weights,
        after_weights=request.after_weights,
        adjustment_reason=request.adjustment_reason,
        trigger_event_id=request.trigger_event_id,
        ai_reasoning=request.ai_reasoning,
    )

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return WeightAdjustmentResponse(
        success=True,
        data=adjustment.to_dict(),
        message=message
    )


@router.post("/weights/{adjustment_id}/approve")
async def approve_weight_adjustment(
    adjustment_id: int,
    current_user: dict = Depends(get_current_user),
    service: AILearningService = Depends(get_learning_service)
):
    """
    批准权重调整

    用户确认 AI 的权重调整是否合适
    """
    success, message = service.approve_weight_adjustment(adjustment_id)

    return {
        "success": success,
        "message": message,
    }


# ============= 学习画像 API =============

@router.get("/profile", response_model=LearningProfileResponse)
async def get_my_learning_profile(
    current_user: dict = Depends(get_current_user),
    service: AILearningService = Depends(get_learning_service)
):
    """
    获取我的学习画像

    返回 AI 对用户的认知进度和学习状态
    """
    user_id = current_user.get("user_id")
    profile = service.get_learning_profile(user_id)

    if not profile:
        return LearningProfileResponse(
            success=True,
            data=None,
            message="尚未生成学习画像"
        )

    return LearningProfileResponse(
        success=True,
        data=profile.to_dict(),
        message="学习画像获取成功"
    )


@router.get("/profile/suggestions")
async def get_learning_suggestions(
    current_user: dict = Depends(get_current_user),
    service: AILearningService = Depends(get_learning_service)
):
    """
    获取学习建议

    基于当前学习状态，生成改进建议
    """
    user_id = current_user.get("user_id")
    suggestions = service.generate_learning_suggestions(user_id)

    return {
        "success": True,
        "data": suggestions,
        "total": len(suggestions),
    }


# ============= 参考数据 API =============

@router.get("/reference/categories")
async def get_preference_categories():
    """
    获取偏好类别参考

    返回所有支持的偏好类别和说明
    """
    return {
        "success": True,
        "data": {
            "matching": {
                "name": "匹配偏好",
                "description": "对理想对象的偏好",
                "subcategories": ["age", "location", "education", "occupation", "lifestyle"],
            },
            "date": {
                "name": "约会偏好",
                "description": "对约会活动和地点的偏好",
                "subcategories": ["activity", "venue", "time", "budget"],
            },
            "gift": {
                "name": "礼物偏好",
                "description": "对礼物类型和场合的偏好",
                "subcategories": ["type", "occasion", "price_range"],
            },
            "communication": {
                "name": "沟通偏好",
                "description": "对沟通方式和风格的偏好",
                "subcategories": ["style", "frequency", "topic"],
            },
            "topic": {
                "name": "话题偏好",
                "description": "对聊天话题的偏好",
                "subcategories": ["hobbies", "values", "future_plans"],
            },
        }
    }


@router.get("/reference/pattern-types")
async def get_pattern_types_reference():
    """
    获取模式类型参考

    返回所有支持的行为模式类型
    """
    return {
        "success": True,
        "data": {
            "online_time": {
                "name": "活跃时间段",
                "description": "用户活跃的时间规律",
                "example": {"peak_hours": [20, 21, 22], "weekend_pattern": "active"},
            },
            "response_style": {
                "name": "回复风格",
                "description": "用户回复消息的风格",
                "example": {"avg_length": 50, "avg_response_time": 300, "emoji_usage": "high"},
            },
            "matching_preference": {
                "name": "匹配偏好",
                "description": "用户浏览和点赞的模式",
                "example": {"preferred_age_range": [25, 30], "preferred_distance": 10},
            },
            "communication_habit": {
                "name": "沟通习惯",
                "description": "用户的沟通习惯",
                "example": {"initiates_conversation": True, "prefers_voice": False},
            },
            "dating_preference": {
                "name": "约会偏好",
                "description": "用户的约会行为模式",
                "example": {"preferred_day": "weekend", "preferred_time": "afternoon"},
            },
        }
    }
