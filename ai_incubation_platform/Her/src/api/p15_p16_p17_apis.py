"""
P15-P17 API 层

P15 虚实结合 - 全自动关系管家
P16 圈子融合 - 生活圈的介绍人
P17 终极共振 - 人生合伙人
"""
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from typing import Optional, List, Dict, Any
from datetime import datetime

from db.database import get_db
from services.p15_services import autonomous_date_service, relationship_album_service
from services.p16_services import (
    tribe_matching_service,
    digital_home_service,
    family_meeting_simulation_service
)
from services.p17_services import stress_test_service, growth_plan_service, trust_service


# ==================== P15 虚实结合 API ====================

router_date_plan = APIRouter(prefix="/api/p15/date-plan", tags=["P15-自主约会策划"])
router_album = APIRouter(prefix="/api/p15/album", tags=["P15-情感纪念册"])


@router_date_plan.post("/create")
async def create_date_plan(
    user_a_id: str = Body(..., embed=True),
    user_b_id: str = Body(..., embed=True),
    user_a_lat: float = Body(..., embed=True),
    user_a_lon: float = Body(..., embed=True),
    user_b_lat: float = Body(..., embed=True),
    user_b_lon: float = Body(..., embed=True),
    preferences: Dict[str, Any] = Body(..., embed=True),
    db=Depends(get_db)
):
    """创建自主约会计划"""
    plan = autonomous_date_service.create_date_plan(
        user_a_id=user_a_id,
        user_b_id=user_b_id,
        user_a_location=(user_a_lat, user_a_lon),
        user_b_location=(user_b_lat, user_b_lon),
        preferences=preferences,
        db_session=db
    )
    return {"success": True, "plan_id": plan.id}


@router_album.post("/create")
async def create_album(
    user_a_id: str = Body(..., embed=True),
    user_b_id: str = Body(..., embed=True),
    title: str = Body(..., embed=True),
    album_type: str = Body(default="moment", embed=True),
    db=Depends(get_db)
):
    """创建情感纪念册"""
    album = relationship_album_service.create_album(
        user_a_id=user_a_id,
        user_b_id=user_b_id,
        title=title,
        album_type=album_type,
        db_session=db
    )
    return {"success": True, "album_id": album.id}


# ==================== P16 圈子融合 API ====================

router_tribe = APIRouter(prefix="/api/p16/tribe", tags=["P16-部落匹配"])
router_digital_home = APIRouter(prefix="/api/p16/digital-home", tags=["P16-数字小家"])
router_family_sim = APIRouter(prefix="/api/p16/family-sim", tags=["P16-见家长模拟"])


@router_tribe.post("/compatibility")
async def check_tribe_compatibility(
    user_a_id: str = Body(..., embed=True),
    user_b_id: str = Body(..., embed=True),
    db=Depends(get_db)
):
    """检查部落兼容性"""
    compatibility = tribe_matching_service.calculate_tribe_compatibility(
        user_a_id=user_a_id,
        user_b_id=user_b_id,
        db_session=db
    )
    return {"success": True, "compatibility": compatibility}


@router_digital_home.post("/create")
async def create_digital_home(
    user_a_id: str = Body(..., embed=True),
    user_b_id: str = Body(..., embed=True),
    home_name: str = Body(..., embed=True),
    theme: Optional[str] = Body(None, embed=True),
    db=Depends(get_db)
):
    """创建数字小家"""
    home = digital_home_service.create_digital_home(
        user_a_id=user_a_id,
        user_b_id=user_b_id,
        home_name=home_name,
        theme=theme,
        db_session=db
    )
    return {"success": True, "home_id": home.id}


@router_digital_home.post("/goal/create")
async def create_couple_goal(
    home_id: str = Body(..., embed=True),
    user_a_id: str = Body(..., embed=True),
    user_b_id: str = Body(..., embed=True),
    goal_title: str = Body(..., embed=True),
    goal_type: str = Body(..., embed=True),
    target_value: float = Body(..., embed=True),
    target_date: str = Body(..., embed=True),
    db=Depends(get_db)
):
    """创建共同目标"""
    goal = digital_home_service.create_couple_goal(
        home_id=home_id,
        user_a_id=user_a_id,
        user_b_id=user_b_id,
        goal_title=goal_title,
        goal_type=goal_type,
        target_value=target_value,
        target_date=datetime.fromisoformat(target_date),
        db_session=db
    )
    return {"success": True, "goal_id": goal.id}


@router_family_sim.post("/role/create")
async def create_virtual_role(
    user_id: str = Body(..., embed=True),
    role_name: str = Body(..., embed=True),
    role_type: str = Body(..., embed=True),
    personality: str = Body(..., embed=True),
    db=Depends(get_db)
):
    """创建虚拟角色"""
    role = family_meeting_simulation_service.create_virtual_role(
        user_id=user_id,
        role_name=role_name,
        role_type=role_type,
        personality=personality,
        db_session=db
    )
    return {"success": True, "role_id": role.id}


# ==================== P17 终极共振 API ====================

router_stress_test = APIRouter(prefix="/api/p17/stress-test", tags=["P17-压力测试"])
router_growth = APIRouter(prefix="/api/p17/growth", tags=["P17-成长计划"])
router_trust = APIRouter(prefix="/api/p17/trust", tags=["P17-信任背书"])


@router_stress_test.post("/start")
async def start_stress_test(
    user_a_id: str = Body(..., embed=True),
    user_b_id: str = Body(..., embed=True),
    scenario_id: str = Body(..., embed=True),
    test_mode: str = Body(default="separate", embed=True),
    db=Depends(get_db)
):
    """开始压力测试"""
    test = stress_test_service.start_stress_test(
        user_a_id=user_a_id,
        user_b_id=user_b_id,
        scenario_id=scenario_id,
        test_mode=test_mode,
        db_session=db
    )
    return {"success": True, "test_id": test.id}


@router_stress_test.post("/{test_id}/complete")
async def complete_stress_test(
    test_id: str,
    db=Depends(get_db)
):
    """完成压力测试"""
    test = stress_test_service.complete_stress_test(
        test_id=test_id,
        db_session=db
    )
    return {
        "success": True,
        "result": test.test_result,
        "analysis": test.ai_analysis
    }


@router_growth.post("/plan/create")
async def create_growth_plan(
    user_a_id: str = Body(..., embed=True),
    user_b_id: str = Body(..., embed=True),
    plan_name: str = Body(..., embed=True),
    growth_goals: List[Dict] = Body(..., embed=True),
    db=Depends(get_db)
):
    """创建成长计划"""
    plan = growth_plan_service.create_growth_plan(
        user_a_id=user_a_id,
        user_b_id=user_b_id,
        plan_name=plan_name,
        growth_goals=growth_goals,
        db_session=db
    )
    return {"success": True, "plan_id": plan.id}


@router_trust.post("/score/calculate")
async def calculate_trust_score(
    user_id: str = Body(..., embed=True),
    db=Depends(get_db)
):
    """计算信任分"""
    score = trust_service.calculate_trust_score(
        user_id=user_id,
        db_session=db
    )
    return {
        "success": True,
        "trust_score": score.overall_trust_score,
        "trust_level": score.trust_level
    }


@router_trust.post("/endorse")
async def add_endorsement(
    endorsed_user_id: str = Body(..., embed=True),
    endorser_user_id: str = Body(..., embed=True),
    endorsement_type: str = Body(..., embed=True),
    endorsement_text: str = Body(..., embed=True),
    relationship_context: str = Body(..., embed=True),
    db=Depends(get_db)
):
    """添加信任背书"""
    endorsement = trust_service.add_endorsement(
        endorsed_user_id=endorsed_user_id,
        endorser_user_id=endorser_user_id,
        endorsement_type=endorsement_type,
        endorsement_text=endorsement_text,
        relationship_context=relationship_context,
        db_session=db
    )
    return {"success": True, "endorsement_id": endorsement.id}
