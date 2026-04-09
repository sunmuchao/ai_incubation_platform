"""
数字分身预聊 API

P2 功能：数字分身模拟相亲、复盘报告
"""
from fastapi import APIRouter, Depends, HTTPException, Body, Query
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import asyncio

from db.database import get_db, SessionLocal
from services.digital_twin_service import digital_twin_service, DigitalTwinService
from utils.logger import logger
from auth.jwt import get_current_user

router = APIRouter(prefix="/api/digital-twin", tags=["P2-数字分身预聊"])


# ============= 请求/响应模型 =============

class TwinProfileCreateRequest(BaseModel):
    """分身配置创建请求"""
    display_name: str = Field(..., description="显示名称")
    personality_traits: Dict[str, Any] = Field(default_factory=dict, description="性格特征")
    communication_style: str = Field(default="medium", description="沟通风格")
    core_values: List[str] = Field(default_factory=list, description="核心价值观")
    interests: List[str] = Field(default_factory=list, description="兴趣爱好")
    deal_breakers: List[str] = Field(default_factory=list, description="不可接受的行为")
    response_patterns: List[str] = Field(default_factory=list, description="常见回复模式")
    topic_preferences: List[str] = Field(default_factory=list, description="喜欢的话题")
    conversation_starters: List[str] = Field(default_factory=list, description="开场白偏好")
    simulation_temperature: float = Field(default=0.7, ge=0, le=1, description="AI 创造性")
    response_length_preference: str = Field(default="medium", description="回复长度偏好")


class TwinProfileResponse(BaseModel):
    """分身配置响应"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None


class SimulationStartRequest(BaseModel):
    """模拟启动请求"""
    partner_user_id: str = Field(..., description="对方用户 ID")
    total_rounds: int = Field(default=10, ge=5, le=20, description="模拟轮数")
    simulation_config: Dict[str, Any] = Field(default_factory=dict, description="模拟配置")


class SimulationResponse(BaseModel):
    """模拟响应"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None


class ReportResponse(BaseModel):
    """报告响应"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None


# ============= 辅助函数 =============

def get_twin_service(db: Session = Depends(get_db)) -> DigitalTwinService:
    """获取数字分身服务实例"""
    return digital_twin_service


# ============= 数字分身配置 API =============

@router.get("/profile", response_model=TwinProfileResponse)
async def get_my_twin_profile(
    current_user: dict = Depends(get_current_user),
    service: DigitalTwinService = Depends(get_twin_service)
):
    """
    获取我的数字分身配置

    返回当前用户的数字分身配置信息
    """
    user_id = current_user.get("user_id")
    profile = service.get_twin_profile(user_id)

    if not profile:
        return TwinProfileResponse(
            success=True,
            data=None,
            message="尚未配置数字分身"
        )

    return TwinProfileResponse(
        success=True,
        data=profile.to_dict(),
        message="数字分身配置获取成功"
    )


@router.post("/profile/create", response_model=TwinProfileResponse)
async def create_twin_profile(
    request: TwinProfileCreateRequest,
    current_user: dict = Depends(get_current_user),
    service: DigitalTwinService = Depends(get_twin_service)
):
    """
    创建/更新数字分身配置

    需要提供：
    - 显示名称
    - 性格特征（大五人格等）
    - 沟通风格
    - 核心价值观
    - 兴趣爱好
    - 不可接受的行为
    - 常见回复模式
    - 喜欢的话题
    - 开场白偏好
    """
    user_id = current_user.get("user_id")

    success, message, profile = service.create_twin_profile(
        user_id=user_id,
        display_name=request.display_name,
        personality_traits=request.personality_traits,
        communication_style=request.communication_style,
        core_values=request.core_values,
        interests=request.interests,
        deal_breakers=request.deal_breakers,
        response_patterns=request.response_patterns,
        topic_preferences=request.topic_preferences,
        conversation_starters=request.conversation_starters,
        simulation_temperature=request.simulation_temperature,
        response_length_preference=request.response_length_preference,
    )

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return TwinProfileResponse(
        success=True,
        data=profile.to_dict(),
        message=message
    )


@router.put("/profile/update", response_model=TwinProfileResponse)
async def update_twin_profile(
    updates: Dict[str, Any] = Body(..., description="配置更新项"),
    current_user: dict = Depends(get_current_user),
    service: DigitalTwinService = Depends(get_twin_service)
):
    """
    更新数字分身配置

    可更新的字段：
    - display_name
    - personality_traits
    - communication_style
    - core_values
    - interests
    - deal_breakers
    - response_patterns
    - topic_preferences
    - conversation_starters
    - simulation_temperature
    - response_length_preference
    """
    user_id = current_user.get("user_id")
    success, message = service.update_twin_profile(user_id, updates)

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return TwinProfileResponse(
        success=True,
        message=message
    )


# ============= 模拟会话 API =============

@router.post("/simulation/start", response_model=SimulationResponse)
async def start_simulation(
    request: SimulationStartRequest,
    current_user: dict = Depends(get_current_user),
    service: DigitalTwinService = Depends(get_twin_service)
):
    """
    启动数字分身模拟

    基于双方用户的分身配置，进行模拟对话
    """
    user_id = current_user.get("user_id")

    success, message, simulation = service.start_simulation(
        user_a_id=user_id,
        user_b_id=request.partner_user_id,
        total_rounds=request.total_rounds,
        simulation_config=request.simulation_config,
    )

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return SimulationResponse(
        success=True,
        data={
            "simulation_id": simulation.id,
            "status": simulation.status,
            "total_rounds": simulation.total_rounds,
        },
        message=message
    )


@router.post("/simulation/{simulation_id}/run", response_model=SimulationResponse)
async def run_simulation(
    simulation_id: int,
    current_user: dict = Depends(get_current_user),
    service: DigitalTwinService = Depends(get_twin_service)
):
    """
    运行数字分身模拟

    异步执行模拟对话，完成后生成分析报告
    """
    # 异步运行模拟
    async def progress_callback(round_num: int, response: Dict):
        logger.info(f"Simulation round {round_num} completed")

    success, message = await service.run_simulation(simulation_id, progress_callback)

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return SimulationResponse(
        success=True,
        message=message
    )


@router.get("/simulation/{simulation_id}", response_model=SimulationResponse)
async def get_simulation_status(
    simulation_id: int,
    current_user: dict = Depends(get_current_user),
    service: DigitalTwinService = Depends(get_twin_service)
):
    """
    获取模拟状态

    返回模拟的当前状态和进度
    """
    db = SessionLocal()
    from models.p2_digital_twin_models import DigitalTwinSimulation

    simulation = db.query(DigitalTwinSimulation).filter(
        DigitalTwinSimulation.id == simulation_id
    ).first()

    if not simulation:
        raise HTTPException(status_code=404, detail="模拟未找到")

    return SimulationResponse(
        success=True,
        data={
            "id": simulation.id,
            "user_a_id": simulation.user_a_id,
            "user_b_id": simulation.user_b_id,
            "status": simulation.status,
            "total_rounds": simulation.total_rounds,
            "completed_rounds": simulation.completed_rounds,
            "compatibility_score": simulation.compatibility_score,
            "chemistry_score": simulation.chemistry_score,
            "communication_match": simulation.communication_match,
            "values_alignment": simulation.values_alignment,
            "started_at": simulation.started_at.isoformat() if simulation.started_at else None,
            "completed_at": simulation.completed_at.isoformat() if simulation.completed_at else None,
        },
        message="模拟状态获取成功"
    )


# ============= 复盘报告 API =============

@router.post("/report/generate", response_model=ReportResponse)
async def generate_report(
    simulation_id: int = Body(..., embed=True, description="模拟 ID"),
    current_user: dict = Depends(get_current_user),
    service: DigitalTwinService = Depends(get_twin_service)
):
    """
    生成复盘报告

    基于模拟对话生成详细的复盘报告
    """
    user_id = current_user.get("user_id")

    success, message, report = service.generate_report(simulation_id, user_id)

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return ReportResponse(
        success=True,
        data=report.to_dict(),
        message=message
    )


@router.get("/report/{simulation_id}", response_model=ReportResponse)
async def get_report(
    simulation_id: int,
    current_user: dict = Depends(get_current_user),
    service: DigitalTwinService = Depends(get_twin_service)
):
    """
    获取复盘报告

    返回已生成的复盘报告
    """
    user_id = current_user.get("user_id")
    report = service.get_report(user_id, simulation_id)

    if not report:
        return ReportResponse(
            success=True,
            data=None,
            message="报告尚未生成"
        )

    # 标记为已查看
    service.mark_report_viewed(report.id)

    return ReportResponse(
        success=True,
        data=report.to_dict(),
        message="报告获取成功"
    )


# ============= 辅助端点 =============

@router.get("/simulations/my")
async def get_my_simulations(
    limit: int = Query(default=10, ge=1, le=50, description="返回数量"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
    current_user: dict = Depends(get_current_user),
    service: DigitalTwinService = Depends(get_twin_service)
):
    """
    获取我的模拟历史

    返回当前用户参与的所有模拟会话
    """
    user_id = current_user.get("user_id")
    db = SessionLocal()

    from models.p2_digital_twin_models import DigitalTwinSimulation

    simulations = db.query(DigitalTwinSimulation).filter(
        (DigitalTwinSimulation.user_a_id == user_id) |
        (DigitalTwinSimulation.user_b_id == user_id)
    ).order_by(
        DigitalTwinSimulation.created_at.desc()
    ).offset(offset).limit(limit).all()

    return {
        "success": True,
        "data": [sim.to_dict() for sim in simulations],
        "total": len(simulations),
    }


@router.get("/reference/personality-traits")
async def get_personality_traits_reference():
    """
    获取性格特征参考

    提供大五人格等性格特征的选项参考
    """
    return {
        "success": True,
        "data": {
            "big_five": {
                "openness": {"name": "开放性", "description": "对新体验的开放程度", "range": [1, 5]},
                "conscientiousness": {"name": "尽责性", "description": "自律和组织能力", "range": [1, 5]},
                "extraversion": {"name": "外向性", "description": "社交活跃度", "range": [1, 5]},
                "agreeableness": {"name": "宜人性", "description": "合作和同理心", "range": [1, 5]},
                "neuroticism": {"name": "神经质", "description": "情绪稳定性", "range": [1, 5]},
            },
            "communication_styles": {
                "direct": "直接型 - 直言不讳，喜欢清晰明确的沟通",
                "indirect": "间接型 - 委婉含蓄，注重语气和上下文",
                "warm": "温暖型 - 热情友好，注重情感连接",
                "reserved": " reserved 型 - 内敛谨慎，保持适当距离",
            },
            "response_lengths": {
                "short": "简短 - 1-2 句话",
                "medium": "中等 - 3-5 句话",
                "long": "详细 - 多段文字",
            },
        }
    }
