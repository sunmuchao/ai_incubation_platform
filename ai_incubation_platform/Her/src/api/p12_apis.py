"""
P12 行为实验室 API

# FUTURE: P12 行为实验室，暂不启用 - 前端未集成

包含：
1. 时机感知破冰 API
2. 情感调解 API

架构说明：
- API 层仅做参数校验、鉴权和响应格式化
- 业务逻辑在 Skill 层（EmotionMediatorSkill, LoveLanguageTranslatorSkill）
- Service 层提供数据库操作和外部服务调用
"""
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from db.database import get_db
from db.models import UserDB, ConversationDB

# 导入 Skills（AI 决策逻辑）
from agent.skills.emotion_mediator_skill import get_emotion_mediator_skill
from agent.skills.love_language_translator_skill import get_love_language_translator_skill
from agent.skills.silence_breaker_skill import get_silence_breaker_skill

# 导入服务（CRUD 操作）
from services.p12_behavior_lab_service import (
    shared_experience_service,
    silence_detection_service,
    icebreaker_topic_service
)
from services.p12_emotion_mediation_service import (
    emotion_warning_service,
    love_language_service,
    relationship_weather_service
)


# ==================== 时机感知破冰 API ====================

router_experiences = APIRouter(prefix="/api/p12/experiences", tags=["P12-时机感知破冰"])
router_silence = APIRouter(prefix="/api/p12/silence", tags=["P12-沉默检测"])
router_icebreaker = APIRouter(prefix="/api/p12/icebreaker", tags=["P12-破冰话题"])


@router_experiences.post("/detect")
async def detect_shared_experience(
    user_a_id: str = Body(..., embed=True),
    user_b_id: str = Body(..., embed=True),
    experience_type: str = Body(..., embed=True),
    reference_data: Dict[str, Any] = Body(..., embed=True),
    db=Depends(get_db)
):
    """
    检测并记录共同经历

    请求体:
    - user_a_id: 用户 A ID
    - user_b_id: 用户 B ID
    - experience_type: 经历类型 (conversation, activity, location, event)
    - reference_data: 相关数据 (包含 start_time, end_time, location, description 等)
    """
    experience_id = shared_experience_service.detect_shared_experience(
        user_a_id, user_b_id, experience_type, reference_data, db
    )

    if not experience_id:
        raise HTTPException(status_code=400, detail="Failed to detect shared experience")

    return {
        "success": True,
        "experience_id": experience_id,
        "message": "共同经历已记录"
    }


@router_experiences.get("/shared")
async def get_shared_experiences(
    user_a_id: str = Query(...),
    user_b_id: str = Query(...),
    experience_type: Optional[str] = Query(None),
    days: int = Query(default=30, ge=1),
    only_significant: bool = Query(default=False),
    db=Depends(get_db)
):
    """
    获取双方的共同经历

    参数:
    - user_a_id: 用户 A ID
    - user_b_id: 用户 B ID
    - experience_type: 可选的经历类型过滤
    - days: 查询天数范围
    - only_significant: 是否只返回显著经历
    """
    experiences = shared_experience_service.get_shared_experiences(
        user_a_id, user_b_id, experience_type, days, only_significant, db
    )

    return {
        "success": True,
        "count": len(experiences),
        "experiences": experiences
    }


@router_experiences.get("/memories")
async def get_significant_memories(
    user_a_id: str = Query(...),
    user_b_id: str = Query(...),
    limit: int = Query(default=10, ge=1, le=50),
    db=Depends(get_db)
):
    """
    获取重要回忆（显著经历）

    参数:
    - user_a_id: 用户 A ID
    - user_b_id: 用户 B ID
    - limit: 返回数量限制
    """
    memories = shared_experience_service.get_significant_memories(
        user_a_id, user_b_id, limit, db
    )

    return {
        "success": True,
        "count": len(memories),
        "memories": memories
    }


@router_silence.post("/detect")
async def detect_silence(
    conversation_id: str = Body(..., embed=True),
    user_a_id: str = Body(..., embed=True),
    user_b_id: str = Body(..., embed=True),
    db=Depends(get_db)
):
    """
    检测对话中的沉默

    请求体:
    - conversation_id: 对话 ID
    - user_a_id: 用户 A ID
    - user_b_id: 用户 B ID
    """
    silence_result = silence_detection_service.detect_silence(
        conversation_id, user_a_id, user_b_id, db
    )

    if not silence_result:
        return {
            "success": True,
            "silence_detected": False,
            "message": "未检测到沉默或沉默时长未达阈值"
        }

    return {
        "success": True,
        "silence_detected": True,
        "silence": silence_result
    }


@router_silence.post("/{silence_id}/resolve")
async def resolve_silence(
    silence_id: str,
    resolution_method: str = Body(..., embed=True),
    db=Depends(get_db)
):
    """
    解决沉默事件

    参数:
    - silence_id: 沉默事件 ID
    - resolution_method: 解决方式 (ai_suggestion, natural_resume, user_action)
    """
    success = silence_detection_service.resolve_silence(
        silence_id, resolution_method, db
    )

    if not success:
        raise HTTPException(status_code=404, detail="Silence event not found")

    return {
        "success": True,
        "message": "沉默事件已解决"
    }


@router_icebreaker.get("/topics")
async def get_icebreaker_topics(
    category: Optional[str] = Query(None),
    scenario: Optional[str] = Query(None),
    depth_level: Optional[int] = Query(None, ge=1, le=5),
    limit: int = Query(default=10, ge=1, le=50),
    db=Depends(get_db)
):
    """
    获取破冰话题

    参数:
    - category: 话题分类
    - scenario: 适用场景
    - depth_level: 深度等级 (1-5)
    - limit: 返回数量限制
    """
    topics = icebreaker_topic_service.get_topics(
        category, scenario, None, depth_level, limit, db
    )

    return {
        "success": True,
        "count": len(topics),
        "topics": topics
    }


@router_icebreaker.post("/generate")
async def generate_icebreaker(
    conversation_id: str = Body(..., embed=True),
    user_a_id: str = Body(..., embed=True),
    user_b_id: str = Body(..., embed=True),
    context: Dict[str, Any] = Body(..., embed=True),
    db=Depends(get_db)
):
    """
    生成个性化破冰话题

    通过 SilenceBreakerSkill 处理 AI 决策逻辑。
    """
    try:
        # 调用 Skill 层处理业务逻辑
        skill = get_silence_breaker_skill()
        result = await skill.execute(
            conversation_id=conversation_id,
            user_a_id=user_a_id,
            user_b_id=user_b_id,
            context=context
        )

        generated_topics = result.get("generated_topics", [])

        return {
            "success": True,
            "icebreaker": {
                "topics": generated_topics,
                "ai_message": result.get("ai_message"),
                "silence_analysis": result.get("silence_analysis")
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router_icebreaker.post("/{icebreaker_id}/feedback")
async def submit_icebreaker_feedback(
    icebreaker_id: str,
    is_used: bool = Body(..., embed=True),
    effectiveness_score: Optional[float] = Body(None, embed=True),
    db=Depends(get_db)
):
    """
    记录破冰话题的反馈

    参数:
    - icebreaker_id: 破冰话题 ID
    - is_used: 是否被使用
    - effectiveness_score: 效果评分 (0-1)
    """
    success = icebreaker_topic_service.record_icebreaker_feedback(
        icebreaker_id, is_used, effectiveness_score, db_session=db
    )

    if not success:
        raise HTTPException(status_code=404, detail="Icebreaker not found")

    return {
        "success": True,
        "message": "反馈已记录"
    }


# ==================== 情感调解 API ====================
# API 层仅做参数校验和响应格式化，业务逻辑在 Skill 层

router_emotion = APIRouter(prefix="/api/p12/emotion", tags=["P12-情感调解"])
router_love_language = APIRouter(prefix="/api/p12/love-language", tags=["P12-爱之语翻译"])
router_weather = APIRouter(prefix="/api/p12/weather", tags=["P12-关系气象"])


@router_emotion.post("/analyze")
async def analyze_conversation_emotion(
    conversation_id: str = Body(..., embed=True),
    user_a_id: str = Body(..., embed=True),
    user_b_id: str = Body(..., embed=True),
    window_messages: int = Body(default=20, embed=True),
    db=Depends(get_db)
):
    """
    分析对话情绪，检测争吵风险

    通过 EmotionMediatorSkill 处理 AI 决策逻辑。
    """
    try:
        # 获取对话历史
        messages = db.query(ConversationDB).filter(
            ConversationDB.id == conversation_id
        ).first()

        conversation_history = []
        if messages:
            # 构建对话历史格式
            conversation_history = [{"content": msg.get("content", ""), "sender_id": msg.get("sender_id")}
                                    for msg in messages.messages[-window_messages:]] if hasattr(messages, 'messages') else []

        # 调用 Skill 层处理业务逻辑
        skill = get_emotion_mediator_skill()
        result = await skill.execute(
            conversation_id=conversation_id,
            user_a_id=user_a_id,
            user_b_id=user_b_id,
            service_type="conflict_detection",
            conversation_history=conversation_history
        )

        mediation_result = result.get("mediation_result", {})

        return {
            "success": True,
            "analysis": {
                "warning_level": mediation_result.get("warning_level"),
                "warning_score": mediation_result.get("warning_score", 0),
                "detected_issues": mediation_result.get("detected_issues", []),
                "calming_suggestions": mediation_result.get("calming_suggestions", []),
                "ai_message": result.get("ai_message")
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router_emotion.post("/{warning_id}/acknowledge")
async def acknowledge_warning(
    warning_id: str,
    db=Depends(get_db)
):
    """确认预警已读"""
    success = emotion_warning_service.acknowledge_warning(warning_id, db)

    if not success:
        raise HTTPException(status_code=404, detail="Warning not found")

    return {
        "success": True,
        "message": "预警已确认"
    }


@router_emotion.post("/{warning_id}/resolve")
async def resolve_warning(
    warning_id: str,
    relationship_improvement: Optional[float] = Body(None, embed=True),
    db=Depends(get_db)
):
    """解决预警"""
    success = emotion_warning_service.resolve_warning(
        warning_id, relationship_improvement, db
    )

    if not success:
        raise HTTPException(status_code=404, detail="Warning not found")

    return {
        "success": True,
        "message": "预警已解决"
    }


@router_emotion.get("/warnings/{user_id}")
async def get_user_warnings(
    user_id: str,
    days: int = Query(default=7, ge=1),
    only_unresolved: bool = Query(default=False),
    db=Depends(get_db)
):
    """获取用户的预警历史"""
    warnings = emotion_warning_service.get_user_warnings(
        user_id, days, only_unresolved, db
    )

    return {
        "success": True,
        "count": len(warnings),
        "warnings": warnings
    }


@router_love_language.post("/translate")
async def translate_expression(
    user_id: str = Body(..., embed=True),
    target_user_id: str = Body(..., embed=True),
    expression: str = Body(..., embed=True),
    db=Depends(get_db)
):
    """
    翻译爱的表达，解读真实意图

    通过 LoveLanguageTranslatorSkill 处理 AI 决策逻辑。
    """
    try:
        # 调用 Skill 层处理业务逻辑
        skill = get_love_language_translator_skill()
        result = await skill.execute(
            user_id=user_id,
            target_user_id=target_user_id,
            expression=expression,
            translation_type="expression"
        )

        translation_result = result.get("translation_result", {})

        return {
            "success": True,
            "translation": {
                "original_expression": translation_result.get("original_expression"),
                "detected_love_language": translation_result.get("detected_love_language"),
                "love_language_name": translation_result.get("love_language_name"),
                "true_intention": translation_result.get("true_intention"),
                "suggested_response": translation_result.get("suggested_response"),
                "response_examples": translation_result.get("response_examples", []),
                "ai_message": result.get("ai_message")
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router_love_language.post("/{translation_id}/feedback")
async def submit_translation_feedback(
    translation_id: str,
    feedback: str = Body(..., embed=True),  # accurate, partially_accurate, inaccurate
    db=Depends(get_db)
):
    """提交翻译反馈"""
    success = love_language_service.submit_feedback(translation_id, feedback, db)

    if not success:
        raise HTTPException(status_code=404, detail="Translation not found")

    return {
        "success": True,
        "message": "反馈已提交"
    }


@router_love_language.get("/history/{user_id}")
async def get_user_translations(
    user_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    db=Depends(get_db)
):
    """获取用户的翻译历史"""
    translations = love_language_service.get_user_translations(user_id, limit, db)

    return {
        "success": True,
        "count": len(translations),
        "translations": translations
    }


@router_weather.post("/generate")
async def generate_weather_report(
    user_a_id: str = Body(..., embed=True),
    user_b_id: str = Body(..., embed=True),
    report_period: str = Body(default="weekly", embed=True),
    db=Depends(get_db)
):
    """
    生成关系气象报告

    通过 EmotionMediatorSkill 处理 AI 决策逻辑。
    """
    try:
        # 调用 Skill 层处理业务逻辑
        skill = get_emotion_mediator_skill()
        result = await skill.execute(
            conversation_id=f"weather_{user_a_id}_{user_b_id}",
            user_a_id=user_a_id,
            user_b_id=user_b_id,
            service_type="weather_report"
        )

        weather_result = result.get("mediation_result", {}).get("relationship_weather", {})

        return {
            "success": True,
            "report": {
                "weather": weather_result.get("weather"),
                "weather_cn": weather_result.get("weather_cn"),
                "temperature": weather_result.get("temperature", 50),
                "description": weather_result.get("description"),
                "trend": weather_result.get("trend"),
                "trend_cn": weather_result.get("trend_cn"),
                "ai_message": result.get("ai_message")
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router_weather.get("/history/{user_id}")
async def get_user_weather_reports(
    user_id: str,
    report_period: Optional[str] = Query(None),
    limit: int = Query(default=10, ge=1, le=50),
    db=Depends(get_db)
):
    """获取用户的气象报告历史"""
    reports = relationship_weather_service.get_user_reports(
        user_id, report_period, limit, db
    )

    return {
        "success": True,
        "count": len(reports),
        "reports": reports
    }
