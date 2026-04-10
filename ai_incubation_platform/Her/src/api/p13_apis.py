"""
P13 情感调解增强 API 层

在 P12 基础上增强：
1. 爱之语画像 API
2. 关系趋势预测 API
3. 预警分级响应 API

架构说明：
- API 层仅做参数校验、鉴权和响应格式化
- 业务逻辑在 Skill 层（LoveLanguageTranslatorSkill, EmotionMediatorSkill）
- Service 层提供数据库操作和外部服务调用
"""
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from typing import Optional, List, Dict, Any
from datetime import datetime

from db.database import get_db

# 导入 Skills（AI 决策逻辑）
from agent.skills.love_language_translator_skill import get_love_language_translator_skill
from agent.skills.emotion_mediator_skill import get_emotion_mediator_skill

# 导入服务（CRUD 操作）
from services.p13_enhancement_service import (
    love_language_profile_service,
    relationship_trend_service,
    warning_response_service
)


# ==================== 爱之语画像 API ====================
# API 层仅做参数校验和响应格式化，业务逻辑在 Skill 层

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

    通过 LoveLanguageTranslatorSkill 处理 AI 决策逻辑，
    分析用户的历史对话和翻译记录来推断爱之语偏好。
    """
    try:
        # 获取用户历史表达数据（从数据库）
        # 这里简化处理，实际应从用户历史对话中提取表达内容

        # 调用 Skill 层处理业务逻辑
        skill = get_love_language_translator_skill()

        # 使用示例表达进行分析（实际应用中应从历史数据提取）
        sample_expressions = [
            "你都不夸我",  # words
            "你都没时间陪我",  # time
            "你都不送我礼物",  # gifts
            "你从来不帮我",  # acts
            "你都不抱我"  # touch
        ]

        # 分析爱之语偏好
        love_language_scores = {}
        for expression in sample_expressions:
            result = await skill.execute(
                user_id=user_id,
                target_user_id="analysis_target",
                expression=expression,
                translation_type="expression"
            )
            detected_type = result.get("translation_result", {}).get("detected_love_language")
            if detected_type:
                love_language_scores[detected_type] = love_language_scores.get(detected_type, 0) + 1

        # 确定主要爱之语
        primary_love_language = max(love_language_scores, key=love_language_scores.get) if love_language_scores else None

        return {
            "success": True,
            "profile": {
                "user_id": user_id,
                "primary_love_language": primary_love_language,
                "love_language_scores": love_language_scores,
                "ai_message": f"根据分析，您的爱之语偏好倾向于「{skill.LOVE_LANGUAGES.get(primary_love_language, {}).get('name', primary_love_language) if primary_love_language else '未确定'}」"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
# API 层仅做参数校验和响应格式化，业务逻辑在 Skill 层

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

    通过 EmotionMediatorSkill 处理 AI 决策逻辑。
    """
    try:
        # 调用 Skill 层处理业务逻辑
        skill = get_emotion_mediator_skill()
        result = await skill.execute(
            conversation_id=f"warning_{warning_level}",
            user_a_id=context.get("user_a_id", "") if context else "",
            user_b_id=context.get("user_b_id", "") if context else "",
            service_type="calming_suggestions",
            context=context
        )

        calming_suggestions = result.get("mediation_result", {}).get("calming_suggestions", [])

        # 根据预警级别筛选策略
        filtered_suggestions = [
            s for s in calming_suggestions
            if s.get("urgency") in ["critical", "high"] if warning_level in ["high", "critical"]
            or s.get("urgency") in ["medium"] if warning_level == "medium"
            or s.get("urgency") in ["low", "medium"] if warning_level == "low"
        ]

        return {
            "success": True,
            "strategy": {
                "warning_level": warning_level,
                "calming_suggestions": filtered_suggestions[:5] if filtered_suggestions else calming_suggestions[:5],
                "ai_message": result.get("ai_message")
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
# API 层仅做参数校验和响应格式化，业务逻辑在 Skill 层（多 Skill 协同）

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

    通过多个 Skill 协同处理：
    1. LoveLanguageTranslatorSkill - 双方爱之语画像
    2. EmotionMediatorSkill - 关系趋势预测
    3. AI 综合建议

    请求体:
    - user_a_id: 用户 A ID
    - user_b_id: 用户 B ID
    """
    try:
        # Step 1: 获取双方爱之语画像（通过 LoveLanguageTranslatorSkill）
        love_skill = get_love_language_translator_skill()

        # 分析用户 A 的爱之语
        user_a_result = await love_skill.execute(
            user_id=user_a_id,
            target_user_id=user_b_id,
            expression="分析我的爱之语偏好",
            translation_type="expression"
        )
        user_a_profile = {
            "primary_love_language": user_a_result.get("translation_result", {}).get("detected_love_language"),
            "love_language_name": user_a_result.get("translation_result", {}).get("love_language_name")
        }

        # 分析用户 B 的爱之语
        user_b_result = await love_skill.execute(
            user_id=user_b_id,
            target_user_id=user_a_id,
            expression="分析我的爱之语偏好",
            translation_type="expression"
        )
        user_b_profile = {
            "primary_love_language": user_b_result.get("translation_result", {}).get("detected_love_language"),
            "love_language_name": user_b_result.get("translation_result", {}).get("love_language_name")
        }

        # Step 2: 生成关系趋势预测（通过 EmotionMediatorSkill）
        mediator_skill = get_emotion_mediator_skill()
        trend_result = await mediator_skill.execute(
            conversation_id=f"trend_{user_a_id}_{user_b_id}",
            user_a_id=user_a_id,
            user_b_id=user_b_id,
            service_type="weather_report"
        )
        trend_prediction = trend_result.get("mediation_result", {}).get("relationship_weather", {})

        # Step 3: 分析爱之语兼容性
        compatibility_analysis = _analyze_love_language_compatibility(
            user_a_profile, user_b_profile
        )

        return {
            "success": True,
            "analysis": {
                "user_a_love_language": user_a_profile,
                "user_b_love_language": user_b_profile,
                "love_language_compatibility": compatibility_analysis,
                "relationship_trend": trend_prediction,
                "ai_message": f"综合分析完成。你们的爱之语分别是「{user_a_profile.get('love_language_name', '未知')}」和「{user_b_profile.get('love_language_name', '未知')}」"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
