"""
P13 情感调解增强 API 层

在 P12 基础上增强：
1. 爱之语画像 API
2. 关系趋势预测 API
3. 预警分级响应 API
"""
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from typing import Optional, List, Dict, Any
from datetime import datetime

from db.database import get_db
from services.p13_enhancement_service import (
    love_language_profile_service,
    relationship_trend_service,
    warning_response_service
)


# ==================== 爱之语画像 API ====================

router_love_language_profile = APIRouter(
    prefix="/api/p13/love-language-profile",
    tags=["P13-爱之语画像"]
)


@router_love_language_profile.post("/analyze")
async def analyze_user_love_language(
    user_id: str = Body(..., embed=True),
    db=Depends(get_db)
):
    """
    分析用户的爱之语偏好

    通过分析用户的历史对话和翻译记录来推断爱之语偏好
    """
    profile = love_language_profile_service.analyze_user_love_language(
        user_id=user_id,
        db_session=db
    )

    if not profile:
        raise HTTPException(status_code=400, detail="Failed to analyze love language profile")

    return {
        "success": True,
        "profile": love_language_profile_service.get_user_profile(user_id, db)
    }


@router_love_language_profile.get("/{user_id}")
async def get_user_love_language_profile(
    user_id: str,
    db=Depends(get_db)
):
    """
    获取用户的爱之语画像
    """
    profile = love_language_profile_service.get_user_profile(user_id, db)

    if not profile:
        return {
            "success": True,
            "profile": None,
            "message": "用户暂无爱之语画像，请先进行分析"
        }

    return {
        "success": True,
        "profile": profile
    }


@router_love_language_profile.get("/description/{love_language}")
async def get_love_language_description(
    love_language: str
):
    """
    获取爱之语类型的描述
    """
    description = love_language_profile_service.get_love_language_description(love_language)

    return {
        "success": True,
        "love_language": love_language,
        "description": description
    }


# ==================== 关系趋势预测 API ====================

router_relationship_trend = APIRouter(
    prefix="/api/p13/relationship-trend",
    tags=["P13-关系趋势预测"]
)


@router_relationship_trend.post("/predict")
async def generate_relationship_trend_prediction(
    user_a_id: str = Body(..., embed=True),
    user_b_id: str = Body(..., embed=True),
    prediction_period: str = Body(default="7d", embed=True),
    db=Depends(get_db)
):
    """
    生成关系趋势预测

    请求体:
    - user_a_id: 用户 A ID
    - user_b_id: 用户 B ID
    - prediction_period: 预测周期 (7d, 14d, 30d)
    """
    prediction = relationship_trend_service.generate_trend_prediction(
        user_a_id=user_a_id,
        user_b_id=user_b_id,
        prediction_period=prediction_period,
        db_session=db
    )

    return {
        "success": True,
        "prediction": prediction
    }


@router_relationship_trend.get("/{prediction_id}")
async def get_relationship_trend_prediction(
    prediction_id: str,
    db=Depends(get_db)
):
    """
    获取关系趋势预测记录
    """
    prediction = relationship_trend_service.get_prediction(prediction_id, db)

    if not prediction:
        raise HTTPException(status_code=404, detail="Prediction not found")

    return {
        "success": True,
        "prediction": prediction
    }


# ==================== 预警分级响应 API ====================

router_warning_response = APIRouter(
    prefix="/api/p13/warning-response",
    tags=["P13-预警分级响应"]
)


@router_warning_response.post("/strategy")
async def get_warning_response_strategy(
    warning_level: str = Body(..., embed=True),
    context: Optional[Dict[str, Any]] = Body(None, embed=True),
    db=Depends(get_db)
):
    """
    根据预警级别获取响应策略

    请求体:
    - warning_level: 预警级别 (low, medium, high, critical)
    - context: 可选的上下文信息
    """
    strategy = warning_response_service.get_response_strategy(
        warning_level=warning_level,
        context=context,
        db_session=db
    )

    if not strategy:
        raise HTTPException(status_code=404, detail="No strategy found for this warning level")

    return {
        "success": True,
        "strategy": strategy
    }


@router_warning_response.post("/execute")
async def execute_warning_response(
    warning_id: str = Body(..., embed=True),
    strategy_id: str = Body(..., embed=True),
    recipient_user_id: str = Body(..., embed=True),
    response_content: str = Body(..., embed=True),
    delivery_method: str = Body(default="push_notification", embed=True),
    db=Depends(get_db)
):
    """
    执行预警响应

    请求体:
    - warning_id: 预警 ID
    - strategy_id: 策略 ID
    - recipient_user_id: 接收者 ID
    - response_content: 实际响应内容
    - delivery_method: 传递方式 (push_notification, in_app_message, email)
    """
    result = warning_response_service.execute_response(
        warning_id=warning_id,
        strategy_id=strategy_id,
        recipient_user_id=recipient_user_id,
        response_content=response_content,
        delivery_method=delivery_method,
        db_session=db
    )

    return {
        "success": True,
        "response_record": result
    }


@router_warning_response.post("/feedback")
async def submit_warning_response_feedback(
    record_id: str = Body(..., embed=True),
    feedback: str = Body(..., embed=True),
    emotion_change: Optional[float] = Body(None, embed=True),
    relationship_improvement: Optional[float] = Body(None, embed=True),
    db=Depends(get_db)
):
    """
    提交预警响应反馈

    请求体:
    - record_id: 响应记录 ID
    - feedback: 反馈 (helpful, neutral, unhelpful)
    - emotion_change: 情绪变化 (-1 到 1)
    - relationship_improvement: 关系改善程度 (0 到 1)
    """
    success = warning_response_service.submit_response_feedback(
        record_id=record_id,
        feedback=feedback,
        emotion_change=emotion_change,
        relationship_improvement=relationship_improvement,
        db_session=db
    )

    if not success:
        raise HTTPException(status_code=404, detail="Response record not found")

    return {
        "success": True,
        "message": "反馈已提交"
    }


@router_warning_response.get("/history/{user_id}")
async def get_user_warning_response_history(
    user_id: str,
    db=Depends(get_db)
):
    """
    获取用户的预警响应历史
    """
    history = warning_response_service.get_response_history(user_id, db)

    return {
        "success": True,
        "count": len(history),
        "history": history
    }


# ==================== P13 综合分析 API ====================

router_p13_comprehensive = APIRouter(
    prefix="/api/p13/comprehensive",
    tags=["P13-综合分析"]
)


@router_p13_comprehensive.post("/analyze")
async def comprehensive_relationship_analysis(
    user_a_id: str = Body(..., embed=True),
    user_b_id: str = Body(..., embed=True),
    db=Depends(get_db)
):
    """
    综合关系分析

    包含：
    1. 双方爱之语画像
    2. 关系趋势预测
    3. 潜在风险和建议

    请求体:
    - user_a_id: 用户 A ID
    - user_b_id: 用户 B ID
    """
    # 获取双方爱之语画像
    user_a_profile = love_language_profile_service.get_user_profile(user_a_id, db)
    user_b_profile = love_language_profile_service.get_user_profile(user_b_id, db)

    # 生成关系趋势预测
    trend_prediction = relationship_trend_service.generate_trend_prediction(
        user_a_id=user_a_id,
        user_b_id=user_b_id,
        prediction_period="7d",
        db_session=db
    )

    # 分析爱之语兼容性
    compatibility_analysis = None
    if user_a_profile and user_b_profile:
        compatibility_analysis = _analyze_love_language_compatibility(
            user_a_profile, user_b_profile
        )

    return {
        "success": True,
        "analysis": {
            "user_a_love_language": user_a_profile,
            "user_b_love_language": user_b_profile,
            "love_language_compatibility": compatibility_analysis,
            "relationship_trend": trend_prediction
        }
    }


def _analyze_love_language_compatibility(
    profile_a: Dict[str, Any],
    profile_b: Dict[str, Any]
) -> Dict[str, Any]:
    """分析爱之语兼容性"""
    primary_a = profile_a.get("primary_love_language")
    primary_b = profile_b.get("primary_love_language")

    # 相同爱之语 - 高度兼容
    if primary_a == primary_b:
        compatibility_score = 0.9
        description = "你们有相同的主要爱之语，更容易理解彼此的表达方式"
    else:
        # 不同爱之语 - 需要相互适应
        compatibility_score = 0.6
        description = "你们的爱之语不同，需要相互学习和适应对方的表达方式"

    # 给出建议
    suggestions = []
    if primary_a != primary_b:
        suggestions.append({
            "type": "understanding",
            "description": f"了解对方的爱之语是{primary_b}，学习用对方的方式表达爱"
        })
        suggestions.append({
            "type": "communication",
            "description": "坦诚沟通自己希望如何被爱，减少误解"
        })

    return {
        "compatibility_score": compatibility_score,
        "description": description,
        "user_a_primary": primary_a,
        "user_b_primary": primary_b,
        "suggestions": suggestions
    }
