"""
P14 实战演习 API

# FUTURE: P14 实战演习，暂不启用 - 前端未集成

核心理念：约会教练与保镖
包含：
1. 约会模拟沙盒 API
2. 约会辅助 API
3. 多代理协作 API
"""
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from typing import Optional, List, Dict, Any
from datetime import datetime

from db.database import get_db
from services.p14_date_simulation_service import date_simulation_service
from services.p14_date_assistant_service import (
    outfit_recommendation_service,
    venue_strategy_service,
    topic_kit_service
)


# ==================== 约会模拟沙盒 API ====================

router_avatar = APIRouter(prefix="/api/p14/avatar", tags=["P14-AI 分身"])
router_simulation = APIRouter(prefix="/api/p14/simulation", tags=["P14-约会模拟"])


@router_avatar.post("/create")
async def create_ai_avatar(
    user_id: str = Body(..., embed=True),
    avatar_name: str = Body(..., embed=True),
    personality: str = Body(default="outgoing", embed=True),
    interests: Optional[List[str]] = Body(None, embed=True),
    db=Depends(get_db)
):
    """创建 AI 约会分身"""
    avatar = date_simulation_service.create_avatar(
        user_id=user_id,
        avatar_name=avatar_name,
        personality=personality,
        interests=interests,
        db_session=db
    )
    return {"success": True, "avatar": {"id": avatar.id, "name": avatar.avatar_name}}


@router_avatar.get("/list/{user_id}")
async def get_user_avatars(user_id: str, db=Depends(get_db)):
    """获取用户的 AI 分身列表"""
    avatars = date_simulation_service.get_user_avatars(user_id, db)
    return {
        "success": True,
        "count": len(avatars),
        "avatars": [{"id": a.id, "name": a.avatar_name, "personality": a.personality} for a in avatars]
    }


@router_simulation.post("/start")
async def start_simulation(
    user_id: str = Body(..., embed=True),
    avatar_id: str = Body(..., embed=True),
    scenario: str = Body(..., embed=True),
    simulation_goal: Optional[str] = Body(None, embed=True),
    db=Depends(get_db)
):
    """开始约会模拟"""
    simulation = date_simulation_service.start_simulation(
        user_id=user_id,
        avatar_id=avatar_id,
        scenario=scenario,
        simulation_goal=simulation_goal,
        db_session=db
    )
    return {"success": True, "simulation_id": simulation.id}


@router_simulation.post("/message")
async def add_simulation_message(
    simulation_id: str = Body(..., embed=True),
    role: str = Body(..., embed=True),
    content: str = Body(..., embed=True),
    db=Depends(get_db)
):
    """添加模拟对话消息"""
    success = date_simulation_service.add_message_to_simulation(
        simulation_id=simulation_id,
        role=role,
        content=content,
        db_session=db
    )
    return {"success": success}


@router_simulation.post("/complete")
async def complete_simulation(
    simulation_id: str = Body(..., embed=True),
    self_rating: Optional[int] = Body(None, embed=True),
    db=Depends(get_db)
):
    """完成模拟"""
    simulation = date_simulation_service.complete_simulation(
        simulation_id=simulation_id,
        self_rating=self_rating,
        db_session=db
    )
    return {"success": True, "simulation": {"id": simulation.id, "status": simulation.status}}


@router_simulation.post("/feedback")
async def generate_simulation_feedback(
    simulation_id: str = Body(..., embed=True),
    db=Depends(get_db)
):
    """生成模拟反馈"""
    feedback = date_simulation_service.generate_feedback(
        simulation_id=simulation_id,
        db_session=db
    )
    return {"success": True, "feedback": {"overall_score": feedback.overall_score}}


# ==================== 约会辅助 API ====================

router_outfit = APIRouter(prefix="/api/p14/outfit", tags=["P14-穿搭推荐"])
router_venue = APIRouter(prefix="/api/p14/venue", tags=["P14-场所策略"])
router_topics = APIRouter(prefix="/api/p14/topics", tags=["P14-话题锦囊"])


@router_outfit.post("/recommend")
async def recommend_outfit(
    user_id: str = Body(..., embed=True),
    venue: str = Body(..., embed=True),
    venue_type: str = Body(..., embed=True),
    weather_condition: str = Body(..., embed=True),
    temperature: float = Body(..., embed=True),
    date_date: str = Body(..., embed=True),
    db=Depends(get_db)
):
    """生成穿搭推荐"""
    recommendation = outfit_recommendation_service.generate_outfit_recommendation(
        user_id=user_id,
        venue=venue,
        venue_type=venue_type,
        weather_condition=weather_condition,
        temperature=temperature,
        date_date=datetime.fromisoformat(date_date),
        db_session=db
    )
    return {"success": True, "outfit": recommendation.outfit_recommendation}


@router_venue.get("/strategies")
async def get_venue_strategies(
    venue_type: Optional[str] = Query(None),
    relationship_stage: Optional[str] = Query(None),
    db=Depends(get_db)
):
    """获取场所策略"""
    strategies = venue_strategy_service.search_venue_strategies(
        venue_type=venue_type,
        relationship_stage=relationship_stage,
        db_session=db
    )
    return {"success": True, "count": len(strategies)}


@router_venue.get("/recommendations")
async def get_venue_recommendations(
    relationship_stage: str = Query(...),
    min_budget: Optional[float] = Query(None),
    max_budget: Optional[float] = Query(None),
    db=Depends(get_db)
):
    """根据关系阶段推荐场所"""
    budget_range = (min_budget, max_budget) if min_budget or max_budget else None
    recommendations = venue_strategy_service.get_venue_recommendations(
        relationship_stage=relationship_stage,
        budget_range=budget_range,
        db_session=db
    )
    return {"success": True, "recommendations": recommendations}


@router_topics.post("/generate")
async def generate_topic_kit(
    user_id: str = Body(..., embed=True),
    common_interests: Optional[List[str]] = Body(None, embed=True),
    db=Depends(get_db)
):
    """生成话题锦囊"""
    kit = topic_kit_service.generate_topic_kit(
        user_id=user_id,
        common_interests=common_interests,
        db_session=db
    )
    return {"success": True, "kit_id": kit.id}


# 继续添加更多 API...
