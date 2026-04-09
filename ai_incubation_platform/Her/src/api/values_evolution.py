"""
P1: 价值观演化追踪 API

从"静态标签匹配"转向"动态共鸣演算法"的核心 API。

功能包括：
- 价值观声明管理
- 价值观推断
- 价值观偏移检测
- 匹配权重调整
- 演化历史查询
"""
import json
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from db.database import get_db
from services.values_evolution_service import (
    ValuesEvolutionService,
    get_dimension_name,
    get_value_name,
    VALUES_DIMENSIONS,
    VALUES_OPTIONS,
)
from models.p1_values_models import (
    DeclaredValuesDB,
    InferredValuesDB,
    ValuesDriftDB,
    ValuesEvolutionHistoryDB,
)


router = APIRouter(prefix="/api/values", tags=["P1-价值观演化"])


# ============= 请求/响应模型 =============

class DeclaredValuesRequest(BaseModel):
    """价值观声明请求"""
    values_data: Dict[str, str] = Field(..., description="价值观数据")
    source: str = Field(default="questionnaire", description="来源：questionnaire/interview/ai_inferred")


class ValuesResponse(BaseModel):
    """价值观响应"""
    success: bool
    data: Dict[str, str]
    confidence_score: Optional[float] = None
    last_updated: Optional[str] = None
    message: Optional[str] = None


class DimensionDriftResponse(BaseModel):
    """单维度偏移响应"""
    dimension: str
    dimension_name: str
    original_value: str
    original_value_name: str
    current_value: str
    current_value_name: str
    drift_score: float
    drift_direction: str
    drift_severity: str
    drift_description: str
    suggested_action: str


class DriftTrackResponse(BaseModel):
    """价值观偏移追踪响应"""
    success: bool
    data: Dict[str, Any]
    message: Optional[str] = None


class EvolutionHistoryResponse(BaseModel):
    """演化历史响应"""
    id: str
    user_id: str
    evolution_type: str
    before_state: Dict[str, Any]
    after_state: Dict[str, Any]
    evolution_reason: str
    created_at: str

    class Config:
        from_attributes = True


class MatchingWeightsResponse(BaseModel):
    """匹配权重响应"""
    success: bool
    data: Dict[str, float]
    message: Optional[str] = None


# ============= 依赖注入 =============

def get_values_service(db: Session = Depends(get_db)) -> ValuesEvolutionService:
    """获取价值观演化服务"""
    return ValuesEvolutionService(db)


# ============= 价值观声明 API =============

@router.post("/declare", response_model=ValuesResponse)
async def declare_values(
    request: DeclaredValuesRequest,
    user_id: str = Query(..., description="用户 ID"),
    service: ValuesEvolutionService = Depends(get_values_service),
):
    """
    声明用户价值观

    用户通过问卷或访谈等方式声明自己的价值观，
    系统将以此作为基准与实际行为进行对比。
    """
    try:
        record = service.set_declared_values(
            user_id=user_id,
            values_data=request.values_data,
            source=request.source,
        )

        return ValuesResponse(
            success=True,
            data=json.loads(record.values_data),
            confidence_score=record.confidence_score,
            last_updated=record.updated_at.isoformat() if record.updated_at else None,
            message="价值观声明成功",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/declared/{user_id}", response_model=ValuesResponse)
async def get_declared_values(
    user_id: str,
    service: ValuesEvolutionService = Depends(get_values_service),
):
    """获取用户声明的价值观"""
    values = service.get_declared_values(user_id)

    if not values:
        raise HTTPException(status_code=404, detail="用户未声明价值观")

    return ValuesResponse(
        success=True,
        data=values,
        message="获取成功",
    )


# ============= 价值观推断 API =============

@router.post("/infer/{user_id}")
async def infer_values(
    user_id: str,
    days: int = Query(default=30, ge=1, le=90, description="分析周期（天数）"),
    service: ValuesEvolutionService = Depends(get_values_service),
):
    """
    从行为推断用户价值观

    分析用户过去 N 天的行为数据，
    推断其实际价值观倾向。
    """
    record = service.infer_values_from_behavior(user_id, days=days)

    return {
        "success": True,
        "data": json.loads(record.values_data),
        "confidence_score": record.confidence_score,
        "behavior_evidence": json.loads(record.behavior_evidence),
        "analysis_period": {
            "start": record.analysis_start_date.isoformat(),
            "end": record.analysis_end_date.isoformat(),
        },
    }


@router.get("/inferred/{user_id}", response_model=ValuesResponse)
async def get_inferred_values(
    user_id: str,
    service: ValuesEvolutionService = Depends(get_values_service),
):
    """获取用户推断的价值观"""
    values = service.get_inferred_values(user_id)

    if not values:
        raise HTTPException(status_code=404, detail="无推断的价值观数据")

    return ValuesResponse(
        success=True,
        data=values,
        message="获取成功",
    )


# ============= 价值观偏移检测 API =============

@router.post("/drift/calculate/{user_id}")
async def calculate_values_drift(
    user_id: str,
    service: ValuesEvolutionService = Depends(get_values_service),
):
    """
    计算用户价值观偏移

    对比声明价值观与推断价值观，
    检测各维度的偏移程度。
    """
    drift_records = service.calculate_values_drift(user_id)

    return {
        "success": True,
        "data": [
            {
                "dimension": d.drift_dimension,
                "dimension_name": get_dimension_name(d.drift_dimension),
                "original_value": d.original_value,
                "current_value": d.current_value,
                "drift_score": d.drift_score,
                "drift_severity": d.drift_severity,
                "suggested_action": d.suggested_action,
            }
            for d in drift_records
        ],
        "message": f"检测到 {len(drift_records)} 个维度偏移",
    }


@router.get("/drift/{user_id}", response_model=List[DimensionDriftResponse])
async def get_user_drifts(
    user_id: str,
    min_severity: str = Query(default="slight", description="最小严重程度"),
    service: ValuesEvolutionService = Depends(get_values_service),
):
    """获取用户的价值观偏移记录"""
    drift_records = service.get_user_drifts(user_id)

    severity_order = ["slight", "moderate", "significant", "severe"]
    min_idx = severity_order.index(min_severity) if min_severity in severity_order else 0

    filtered = [
        d for d in drift_records
        if severity_order.index(d.drift_severity) >= min_idx
    ]

    return [
        DimensionDriftResponse(
            dimension=d.drift_dimension,
            dimension_name=get_dimension_name(d.drift_dimension),
            original_value=d.original_value,
            original_value_name=get_value_name(d.original_value),
            current_value=d.current_value,
            current_value_name=get_value_name(d.current_value),
            drift_score=d.drift_score,
            drift_direction=d.drift_direction,
            drift_severity=d.drift_severity,
            drift_description=d.drift_description,
            suggested_action=d.suggested_action,
        )
        for d in filtered
    ]


# ============= 综合追踪 API =============

@router.post("/track/{user_id}", response_model=DriftTrackResponse)
async def track_values_evolution(
    user_id: str,
    service: ValuesEvolutionService = Depends(get_values_service),
):
    """
    执行完整的价值观演化追踪

    包括：行为推断、偏移计算、权重调整、通知生成
    """
    result = service.track_values_evolution(user_id)

    # 格式化偏移记录
    formatted_drifts = []
    for drift in result["drift_records"]:
        formatted_drifts.append({
            "dimension": drift["dimension"],
            "dimension_name": get_dimension_name(drift["dimension"]),
            "drift_score": drift["drift_score"],
            "drift_severity": drift["drift_severity"],
            "suggested_action": drift["suggested_action"],
        })

    return DriftTrackResponse(
        success=True,
        data={
            "inferred_values": result["inferred_values"],
            "drift_records": formatted_drifts,
            "weight_adjustment": result["weight_adjustment"],
            "notifications": result["notifications"],
        },
        message=f"完成价值观演化追踪，检测到 {len(formatted_drifts)} 个维度偏移",
    )


# ============= 匹配权重 API =============

@router.get("/weights/{user_id}", response_model=MatchingWeightsResponse)
async def get_matching_weights(
    user_id: str,
    service: ValuesEvolutionService = Depends(get_values_service),
):
    """获取用户当前的匹配权重"""
    weights = service.get_current_matching_weights(user_id)

    return MatchingWeightsResponse(
        success=True,
        data=weights,
        message="获取成功",
    )


# ============= 演化历史 API =============

@router.get("/history/{user_id}", response_model=List[EvolutionHistoryResponse])
async def get_evolution_history(
    user_id: str,
    limit: int = Query(default=20, ge=1, le=100, description="返回数量限制"),
    service: ValuesEvolutionService = Depends(get_values_service),
):
    """获取用户价值观演化历史"""
    history = service.get_evolution_history(user_id, limit)

    return [
        EvolutionHistoryResponse(
            id=h.id,
            user_id=h.user_id,
            evolution_type=h.evolution_type,
            before_state=json.loads(h.before_state),
            after_state=json.loads(h.after_state),
            evolution_reason=h.evolution_reason,
            created_at=h.created_at.isoformat(),
        )
        for h in history
    ]


# ============= 参考数据 API =============

@router.get("/dimensions/reference")
async def get_values_dimensions_reference():
    """
    获取价值观维度参考数据

    返回所有维度的中英文名称和可选值，
    用于前端展示和问卷设计。
    """
    dimension_info = {
        "family_view": {
            "name": "家庭观念",
            "description": "对家庭角色、责任分工、育儿理念的理解",
            "options": {
                "traditional": "传统型（男主外女主内，重视传统家庭角色）",
                "balanced": "平衡型（灵活分工，兼顾传统与现代）",
                "liberal": "开放型（完全平等，不受传统束缚）",
            },
        },
        "career_view": {
            "name": "事业观念",
            "description": "对事业发展与家庭平衡的态度",
            "options": {
                "career_focused": "事业优先（职业发展放在首位）",
                "family_focused": "家庭优先（家庭生活放在首位）",
                "balanced": "平衡型（事业与家庭并重）",
            },
        },
        "consumption_view": {
            "name": "消费观念",
            "description": "对金钱使用和消费习惯的态度",
            "options": {
                "frugal": "节俭型（量入为出，避免浪费）",
                "moderate": "适度型（理性消费，平衡收支）",
                "generous": "享受型（注重生活品质，愿意为体验买单）",
            },
        },
        "social_view": {
            "name": "社交观念",
            "description": "对社交活动和人际交往的偏好",
            "options": {
                "introverted": "内向型（偏好独处或小圈子）",
                "extroverted": "外向型（偏好社交活动和认识新人）",
                "ambivert": "中间型（介于两者之间）",
            },
        },
        "life_pace": {
            "name": "生活节奏",
            "description": "对生活节奏和日常安排的偏好",
            "options": {
                "slow": "慢节奏（从容不迫，注重生活品质）",
                "balanced": "平衡型（张弛有度）",
                "fast": "快节奏（高效忙碌，追求成就感）",
            },
        },
        "risk_preference": {
            "name": "风险偏好",
            "description": "对不确定性和风险的态度",
            "options": {
                "risk_averse": "风险规避（偏好稳定，避免冒险）",
                "moderate": "适度型（谨慎评估后决策）",
                "risk_seeking": "风险偏好（愿意尝试新事物）",
            },
        },
    }

    return {
        "dimensions": [
            {
                "key": dim,
                "info": info,
            }
            for dim, info in dimension_info.items()
        ]
    }


