"""
P20 API 端点 - v1.20 AI 约会助手

AI 约会助手 API 包括：
- 智能聊天助手（回复建议/话题推荐）
- 约会策划引擎（地点/时间/活动）
- 关系咨询服务（情感问题解答）
- 情感分析服务（聊天记录分析）
- 恋爱日记（关系记录）
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime

from db.database import get_db
from services.ai_date_assistant_service import (
    ChatAssistantService,
    DatePlanningService,
    RelationshipConsultantService,
    EmotionAnalyzerService,
    LoveDiaryService
)
from models.p20_models import (
    ChatAssistantSuggestionDB, DatePlanDB, DateVenueDB,
    RelationshipConsultationDB, EmotionAnalysisDB,
    LoveDiaryEntryDB, LoveDiaryMemoryDB, RelationshipTimelineDB
)


router = APIRouter(prefix="/api", tags=["AI 约会助手 P20"])


# ============= P20-001: 智能聊天助手 API =============

@router.post("/chat-assistant/generate-reply", response_model=Dict[str, Any])
def generate_reply(
    user_id: str = Query(..., description="用户 ID"),
    received_message: str = Body(..., description="收到的消息"),
    conversation_id: Optional[str] = Body(None, description="会话 ID"),
    target_user_id: Optional[str] = Body(None, description="聊天对象 ID"),
    context: Optional[Dict[str, Any]] = Body(None, description="上下文信息"),
    db: Session = Depends(get_db)
):
    """生成回复建议"""
    service = ChatAssistantService(db)
    suggestion = service.generate_reply_suggestion(
        user_id=user_id,
        received_message=received_message,
        conversation_id=conversation_id,
        target_user_id=target_user_id,
        context=context
    )

    return {
        "id": suggestion.id,
        "suggestion_type": suggestion.suggestion_type,
        "suggested_text": suggestion.suggested_text,
        "alternatives": suggestion.alternative_suggestions,
        "tone": suggestion.tone,
        "reasoning": suggestion.reasoning,
        "confidence_score": suggestion.confidence_score,
        "created_at": suggestion.created_at.isoformat() if suggestion.created_at else None
    }


@router.post("/chat-assistant/recommend-topics", response_model=List[Dict[str, Any]])
def recommend_topics(
    user_id: str = Query(..., description="用户 ID"),
    target_user_id: str = Body(..., description="聊天对象 ID"),
    conversation_context: Optional[str] = Body(None, description="会话上下文"),
    db: Session = Depends(get_db)
):
    """推荐聊天话题"""
    service = ChatAssistantService(db)
    suggestions = service.recommend_topics(
        user_id=user_id,
        target_user_id=target_user_id,
        conversation_context=conversation_context
    )

    return [
        {
            "id": s.id,
            "topic": s.suggested_text,
            "reasoning": s.reasoning,
            "confidence": s.confidence_score
        }
        for s in suggestions
    ]


@router.post("/chat-assistant/suggest-emoji", response_model=Dict[str, Any])
def suggest_emoji(
    user_id: str = Query(..., description="用户 ID"),
    message_text: str = Body(..., description="消息文本"),
    context: Optional[str] = Body(None, description="上下文"),
    db: Session = Depends(get_db)
):
    """推荐表情符号"""
    service = ChatAssistantService(db)
    suggestion = service.suggest_emoji(
        user_id=user_id,
        message_text=message_text,
        context=context
    )

    return {
        "primary": suggestion.suggested_text,
        "alternatives": suggestion.alternative_suggestions,
        "confidence": suggestion.confidence_score
    }


@router.post("/chat-assistant/{suggestion_id}/use", response_model=Dict[str, bool])
def mark_suggestion_used(
    suggestion_id: str,
    modified_text: Optional[str] = Body(None, description="修改后的文本"),
    rating: Optional[int] = Body(None, description="评分 1-5"),
    db: Session = Depends(get_db)
):
    """标记建议已使用"""
    service = ChatAssistantService(db)
    success = service.mark_as_used(
        suggestion_id=suggestion_id,
        modified_text=modified_text,
        rating=rating
    )
    return {"success": success}


# ============= P20-002: 约会策划 API =============

@router.post("/date-planner/plan", response_model=Dict[str, Any])
def create_date_plan(
    user_id: str = Query(..., description="用户 ID"),
    partner_user_id: str = Body(..., description="约会对象 ID"),
    plan_type: str = Body("first_date", description="计划类型"),
    preferences: Optional[Dict[str, Any]] = Body(None, description="偏好设置"),
    db: Session = Depends(get_db)
):
    """创建约会计划"""
    service = DatePlanningService(db)
    plan = service.create_date_plan(
        user_id=user_id,
        partner_user_id=partner_user_id,
        plan_type=plan_type,
        preferences=preferences
    )

    return {
        "id": plan.id,
        "plan_type": plan.plan_type,
        "title": plan.title,
        "description": plan.description,
        "estimated_cost": plan.estimated_total,
        "activities": plan.activities,
        "status": plan.status,
        "reasoning": plan.reasoning,
        "created_at": plan.created_at.isoformat() if plan.created_at else None
    }


@router.get("/date-planner/venues", response_model=List[Dict[str, Any]])
def recommend_venues(
    city: str = Query(..., description="城市"),
    district: Optional[str] = Query(None, description="区域"),
    venue_type: Optional[str] = Query(None, description="地点类型"),
    budget_min: Optional[int] = Query(None, description="最低预算"),
    budget_max: Optional[int] = Query(None, description="最高预算"),
    suitable_for: Optional[str] = Query(None, description="适合场景"),
    db: Session = Depends(get_db)
):
    """推荐约会地点"""
    service = DatePlanningService(db)
    budget_range = None
    if budget_min is not None and budget_max is not None:
        budget_range = (budget_min, budget_max)

    venues = service.recommend_venues(
        city=city,
        district=district,
        venue_type=venue_type,
        budget_range=budget_range,
        suitable_for=suitable_for
    )

    return [
        {
            "id": v.id,
            "name": v.venue_name,
            "type": v.venue_type,
            "address": v.address,
            "district": v.district,
            "rating": v.rating,
            "price_level": v.price_level,
            "suitable_for_first_date": v.suitable_for_first_date,
            "ambiance_tags": v.ambiance_tags
        }
        for v in venues
    ]


@router.get("/date-planner/venues/{venue_id}", response_model=Dict[str, Any])
def get_venue_detail(venue_id: str, db: Session = Depends(get_db)):
    """获取地点详情"""
    service = DatePlanningService(db)
    venue = service.get_venue_detail(venue_id)

    if not venue:
        raise HTTPException(status_code=404, detail="地点不存在")

    return {
        "id": venue.id,
        "name": venue.venue_name,
        "type": venue.venue_type,
        "category": venue.category,
        "address": venue.address,
        "rating": venue.rating,
        "review_count": venue.review_count,
        "price_level": venue.price_level,
        "opening_hours": venue.opening_hours,
        "reservation_required": venue.reservation_required,
        "facilities": venue.facilities,
        "ambiance_tags": venue.ambiance_tags
    }


@router.post("/date-planner/{plan_id}/accept", response_model=Dict[str, bool])
def accept_date_plan(
    plan_id: str,
    user_id: str = Query(..., description="用户 ID"),
    db: Session = Depends(get_db)
):
    """接受约会计划"""
    service = DatePlanningService(db)
    success = service.accept_plan(plan_id=plan_id, user_id=user_id)
    return {"success": success}


@router.post("/date-planner/{plan_id}/complete", response_model=Dict[str, bool])
def complete_date_plan(
    plan_id: str,
    rating: Optional[int] = Body(None, description="评分 1-5"),
    feedback: Optional[str] = Body(None, description="反馈"),
    db: Session = Depends(get_db)
):
    """完成约会计划"""
    service = DatePlanningService(db)
    success = service.complete_plan(plan_id=plan_id, rating=rating, feedback=feedback)
    return {"success": success}


# ============= P20-003: 关系咨询 API =============

@router.post("/relationship-consultant/consult", response_model=Dict[str, Any])
def consult_relationship(
    user_id: str = Query(..., description="用户 ID"),
    question: str = Body(..., description="问题"),
    consult_type: str = Body(..., description="咨询类型"),
    context: Optional[str] = Body(None, description="背景信息"),
    partner_user_id: Optional[str] = Body(None, description="相关对象 ID"),
    db: Session = Depends(get_db)
):
    """获取咨询建议"""
    service = RelationshipConsultantService(db)
    consultation = service.consult(
        user_id=user_id,
        question=question,
        consult_type=consult_type,
        context=context,
        partner_user_id=partner_user_id
    )

    return {
        "id": consultation.id,
        "consult_type": consultation.consult_type,
        "question": consultation.question,
        "ai_response": consultation.ai_response,
        "key_points": consultation.key_points,
        "action_steps": consultation.action_steps,
        "psychological_basis": consultation.psychological_basis,
        "created_at": consultation.created_at.isoformat() if consultation.created_at else None
    }


@router.get("/relationship-consultant/faq", response_model=List[Dict[str, Any]])
def get_faq(
    category: Optional[str] = Query(None, description="分类"),
    limit: int = Query(10, description="数量限制"),
    db: Session = Depends(get_db)
):
    """获取常见问题"""
    service = RelationshipConsultantService(db)
    faqs = service.get_faq(category=category, limit=limit)

    return [
        {
            "id": f.id,
            "category": f.category,
            "question": f.question,
            "answer": f.answer,
            "helpful_count": f.helpful_count
        }
        for f in faqs
    ]


@router.get("/relationship-consultant/faq/search", response_model=List[Dict[str, Any]])
def search_faq(
    q: str = Query(..., description="搜索词"),
    db: Session = Depends(get_db)
):
    """搜索 FAQ"""
    service = RelationshipConsultantService(db)
    faqs = service.search_faq(query_text=q)

    return [
        {
            "id": f.id,
            "category": f.category,
            "question": f.question,
            "answer": f.answer,
            "helpful_count": f.helpful_count
        }
        for f in faqs
    ]


@router.post("/relationship-consultant/faq/{faq_id}/helpful", response_model=Dict[str, bool])
def mark_faq_helpful(
    faq_id: str,
    is_helpful: bool = Body(True, description="是否有用"),
    db: Session = Depends(get_db)
):
    """标记 FAQ 是否有用"""
    service = RelationshipConsultantService(db)
    success = service.mark_faq_helpful(faq_id=faq_id, is_helpful=is_helpful)
    return {"success": success}


# ============= P20-004: 情感分析 API =============

@router.post("/emotion-analyzer/analyze-conversation", response_model=Dict[str, Any])
def analyze_conversation(
    user_id: str = Query(..., description="用户 ID"),
    partner_user_id: str = Body(..., description="对象 ID"),
    conversation_id: Optional[str] = Body(None, description="会话 ID"),
    analysis_type: str = Body("full", description="分析类型"),
    db: Session = Depends(get_db)
):
    """分析聊天记录"""
    service = EmotionAnalyzerService(db)
    analysis = service.analyze_conversation(
        user_id=user_id,
        partner_user_id=partner_user_id,
        conversation_id=conversation_id,
        analysis_type=analysis_type
    )

    return {
        "id": analysis.id,
        "analysis_type": analysis.analysis_type,
        "sentiment_score": analysis.sentiment_score,
        "sentiment_label": analysis.sentiment_label,
        "emotion_scores": analysis.emotion_scores,
        "intensity_score": analysis.intensity_score,
        "engagement_score": analysis.engagement_score,
        "compatibility_score": analysis.compatibility_score,
        "insights": analysis.insights,
        "suggestions": analysis.suggestions,
        "created_at": analysis.created_at.isoformat() if analysis.created_at else None
    }


@router.get("/emotion-analyzer/sentiment-trend", response_model=List[Dict[str, Any]])
def get_sentiment_trend(
    user_id: str = Query(..., description="用户 ID"),
    partner_user_id: str = Query(..., description="对象 ID"),
    days: int = Query(7, description="天数"),
    db: Session = Depends(get_db)
):
    """获取情感趋势"""
    service = EmotionAnalyzerService(db)
    analyses = service.get_sentiment_trend(
        user_id=user_id,
        partner_user_id=partner_user_id,
        days=days
    )

    return [
        {
            "id": a.id,
            "sentiment_score": a.sentiment_score,
            "sentiment_label": a.sentiment_label,
            "compatibility_score": a.compatibility_score,
            "created_at": a.created_at.isoformat() if a.created_at else None
        }
        for a in analyses
    ]


@router.get("/emotion-analyzer/compatibility-score", response_model=Dict[str, Any])
def get_compatibility_score(
    user_id: str = Query(..., description="用户 ID"),
    partner_user_id: str = Query(..., description="对象 ID"),
    db: Session = Depends(get_db)
):
    """获取匹配度评分"""
    service = EmotionAnalyzerService(db)
    score = service.get_compatibility_score(
        user_id=user_id,
        partner_user_id=partner_user_id
    )

    return {
        "compatibility_score": score,
        "user_id": user_id,
        "partner_user_id": partner_user_id
    }


# ============= P20-005: 恋爱日记 API =============

@router.post("/love-diary/entry", response_model=Dict[str, Any])
def create_diary_entry(
    user_id: str = Query(..., description="用户 ID"),
    title: str = Body(..., description="标题"),
    content: str = Body(..., description="内容"),
    entry_type: str = Body("manual_entry", description="日记类型"),
    partner_user_id: Optional[str] = Body(None, description="相关对象 ID"),
    mood: Optional[str] = Body(None, description="心情"),
    entry_date: Optional[str] = Body(None, description="日记日期 ISO 格式"),
    is_private: bool = Body(False, description="是否私密"),
    db: Session = Depends(get_db)
):
    """创建日记条目"""
    service = LoveDiaryService(db)

    parse_date = None
    if entry_date:
        parse_date = datetime.fromisoformat(entry_date.replace("Z", "+00:00"))

    entry = service.create_entry(
        user_id=user_id,
        title=title,
        content=content,
        entry_type=entry_type,
        partner_user_id=partner_user_id,
        mood=mood,
        entry_date=parse_date,
        is_private=is_private
    )

    return {
        "id": entry.id,
        "title": entry.title,
        "entry_type": entry.entry_type,
        "mood": entry.mood,
        "is_private": entry.is_private,
        "entry_date": entry.entry_date.isoformat() if entry.entry_date else None,
        "created_at": entry.created_at.isoformat() if entry.created_at else None
    }


@router.get("/love-diary/entries", response_model=List[Dict[str, Any]])
def get_diary_entries(
    user_id: str = Query(..., description="用户 ID"),
    partner_user_id: Optional[str] = Query(None, description="相关对象 ID"),
    entry_type: Optional[str] = Query(None, description="日记类型"),
    limit: int = Query(20, description="数量限制"),
    offset: int = Query(0, description="偏移量"),
    db: Session = Depends(get_db)
):
    """获取日记列表"""
    service = LoveDiaryService(db)
    entries = service.get_entries(
        user_id=user_id,
        partner_user_id=partner_user_id,
        entry_type=entry_type,
        limit=limit,
        offset=offset
    )

    return [
        {
            "id": e.id,
            "title": e.title,
            "entry_type": e.entry_type,
            "mood": e.mood,
            "is_private": e.is_private,
            "entry_date": e.entry_date.isoformat() if e.entry_date else None,
            "created_at": e.created_at.isoformat() if e.created_at else None
        }
        for e in entries
    ]


@router.get("/love-diary/timeline", response_model=List[Dict[str, Any]])
def get_relationship_timeline(
    user_id_1: str = Query(..., description="用户 ID 1"),
    user_id_2: str = Query(..., description="用户 ID 2"),
    limit: int = Query(50, description="数量限制"),
    db: Session = Depends(get_db)
):
    """获取关系时间线"""
    service = LoveDiaryService(db)
    events = service.get_timeline(
        user_id_1=user_id_1,
        user_id_2=user_id_2,
        limit=limit
    )

    return [
        {
            "id": e.id,
            "event_type": e.event_type,
            "title": e.title,
            "description": e.description,
            "event_date": e.event_date.isoformat() if e.event_date else None,
            "location": e.location,
            "is_milestone": e.is_milestone
        }
        for e in events
    ]


@router.post("/love-diary/timeline", response_model=Dict[str, Any])
def add_timeline_event(
    user_id_1: str = Query(..., description="用户 ID 1"),
    user_id_2: str = Query(..., description="用户 ID 2"),
    event_type: str = Body(..., description="事件类型"),
    title: str = Body(..., description="标题"),
    event_date: str = Body(..., description="事件日期 ISO 格式"),
    description: Optional[str] = Body(None, description="描述"),
    location: Optional[str] = Body(None, description="地点"),
    is_milestone: bool = Body(False, description="是否里程碑"),
    db: Session = Depends(get_db)
):
    """添加时间线事件"""
    service = LoveDiaryService(db)

    parse_date = datetime.fromisoformat(event_date.replace("Z", "+00:00"))
    event = service.add_timeline_event(
        user_id_1=user_id_1,
        user_id_2=user_id_2,
        event_type=event_type,
        title=title,
        event_date=parse_date,
        description=description,
        location=location,
        is_milestone=is_milestone
    )

    return {
        "id": event.id,
        "event_type": event.event_type,
        "title": event.title,
        "event_date": event.event_date.isoformat() if event.event_date else None,
        "is_milestone": event.is_milestone
    }


@router.post("/love-diary/memory", response_model=Dict[str, Any])
def create_memory(
    user_id: str = Query(..., description="用户 ID"),
    memory_type: str = Body(..., description="回忆类型"),
    title: str = Body(..., description="标题"),
    description: str = Body(..., description="描述"),
    memory_date: str = Body(..., description="回忆日期 ISO 格式"),
    partner_user_id: Optional[str] = Body(None, description="相关对象 ID"),
    emotion: Optional[str] = Body(None, description="情感"),
    db: Session = Depends(get_db)
):
    """创建回忆记录"""
    service = LoveDiaryService(db)

    parse_date = datetime.fromisoformat(memory_date.replace("Z", "+00:00"))
    memory = service.create_memory(
        user_id=user_id,
        memory_type=memory_type,
        title=title,
        description=description,
        memory_date=parse_date,
        partner_user_id=partner_user_id,
        emotion=emotion
    )

    return {
        "id": memory.id,
        "memory_type": memory.memory_type,
        "title": memory.title,
        "memory_date": memory.memory_date.isoformat() if memory.memory_date else None
    }


@router.post("/love-diary/{entry_id}/share", response_model=Dict[str, bool])
def share_diary_entry(
    entry_id: str,
    user_id: str = Query(..., description="用户 ID"),
    db: Session = Depends(get_db)
):
    """分享日记给伴侣"""
    service = LoveDiaryService(db)
    success = service.share_entry(entry_id=entry_id, user_id=user_id)
    return {"success": success}
