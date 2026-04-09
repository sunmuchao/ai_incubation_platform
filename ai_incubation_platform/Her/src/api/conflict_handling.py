"""
P1: 冲突处理 API

从"静态标签匹配"转向"动态共鸣演算法"的核心 API。

功能包括：
- 冲突处理风格评估
- 冲突兼容性查询
- 冲突记录与解决
- 沟通模式分析
- 冲突化解建议
"""
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from db.database import get_db
from services.conflict_handling_service import (
    ConflictHandlingService,
    get_style_name,
    STYLE_NAMES,
)
from models.p1_conflict_models import (
    ConflictStyleDB,
    ConflictHistoryDB,
    ConflictCompatibilityDB,
    ConflictResolutionTipDB,
    CommunicationPatternDB,
)


router = APIRouter(prefix="/api/conflict", tags=["P1-冲突处理"])


# ============= 请求/响应模型 =============

class ConflictStyleAssessmentRequest(BaseModel):
    """冲突风格评估请求"""
    avoiding_score: int = Field(0, ge=0, le=100, description="回避型得分")
    competing_score: int = Field(0, ge=0, le=100, description="对抗型得分")
    accommodating_score: int = Field(0, ge=0, le=100, description="迁就型得分")
    compromising_score: int = Field(0, ge=0, le=100, description="妥协型得分")
    collaborating_score: int = Field(0, ge=0, le=100, description="协商型得分")
    conflict_triggers: Optional[List[str]] = Field(None, description="冲突触发点列表")
    assessment_method: str = Field("questionnaire", description="评估方式")


class ConflictStyleResponse(BaseModel):
    """冲突风格响应"""
    id: str
    user_id: str
    primary_style: str
    primary_style_name: str
    avoiding_score: int
    competing_score: int
    accommodating_score: int
    compromising_score: int
    collaborating_score: int
    style_description: str
    conflict_triggers: List[str]
    assessment_method: str
    last_assessed_at: Optional[str] = None

    class Config:
        from_attributes = True


class ConflictCompatibilityResponse(BaseModel):
    """冲突兼容性响应"""
    id: str
    compatibility_score: float
    style_compatibility: float
    trigger_compatibility: float
    resolution_compatibility: float
    style_a_name: str
    style_b_name: str
    risk_factors: List[Dict[str, Any]]
    suggestions: List[Dict[str, Any]]
    compatibility_details: Dict[str, Any]

    class Config:
        from_attributes = True


class ConflictRecordRequest(BaseModel):
    """冲突记录请求"""
    conflict_type: str = Field(..., description="冲突类型")
    conflict_topic: Optional[str] = Field(None, description="冲突主题")
    conflict_description: Optional[str] = Field(None, description="冲突描述")
    partner_user_id: Optional[str] = Field(None, description="对方用户 ID")
    handling_style: Optional[str] = Field(None, description="处理方式")


class ConflictRecordResponse(BaseModel):
    """冲突记录响应"""
    id: str
    user_id: str
    partner_user_id: Optional[str]
    conflict_type: str
    conflict_topic: Optional[str]
    conflict_description: Optional[str]
    handling_style: Optional[str]
    resolution_status: str
    created_at: str

    class Config:
        from_attributes = True


class ConflictResolveRequest(BaseModel):
    """冲突解决请求"""
    resolution_description: str = Field(..., description="解决结果描述")
    handling_effectiveness: int = Field(1, ge=1, le=10, description="处理效果评分")
    relationship_impact: int = Field(0, ge=-10, le=10, description="对关系的影响")
    lessons_learned: Optional[str] = Field(None, description="经验教训")


class CommunicationPatternRequest(BaseModel):
    """沟通模式评估请求"""
    communication_style: Optional[str] = Field(None, description="沟通风格")
    preferred_frequency: Optional[str] = Field(None, description="沟通频率偏好")
    preferred_channels: Optional[List[str]] = Field(None, description="沟通渠道偏好")
    preferred_time: Optional[str] = Field(None, description="沟通时间偏好")
    response_pattern: Optional[str] = Field(None, description="响应模式")
    depth_preference: Optional[str] = Field(None, description="沟通深度偏好")


class CommunicationPatternResponse(BaseModel):
    """沟通模式响应"""
    id: str
    user_id: str
    communication_style: Optional[str]
    preferred_frequency: Optional[str]
    preferred_channels: List[str]
    preferred_time: Optional[str]
    response_pattern: Optional[str]
    depth_preference: Optional[str]

    class Config:
        from_attributes = True


class CompatibilitySuggestionResponse(BaseModel):
    """兼容性建议响应"""
    conflict_compatibility: Optional[Dict[str, Any]]
    communication_compatibility: Optional[Dict[str, Any]]
    overall_suggestions: List[str]


class ResolutionTipResponse(BaseModel):
    """冲突化解建议响应"""
    id: str
    conflict_type: str
    style_combination: Optional[str]
    tip_title: str
    tip_content: str
    tip_type: str
    psychological_basis: Optional[str]
    effectiveness_rating: float
    applicable_scenarios: List[str]

    class Config:
        from_attributes = True


# ============= 依赖注入 =============

def get_conflict_service(db: Session = Depends(get_db)) -> ConflictHandlingService:
    """获取冲突处理服务"""
    return ConflictHandlingService(db)


# ============= 冲突处理风格 API =============

@router.post("/style/assess", response_model=ConflictStyleResponse)
async def assess_conflict_style(
    request: ConflictStyleAssessmentRequest,
    user_id: str = Query(..., description="用户 ID"),
    service: ConflictHandlingService = Depends(get_conflict_service),
):
    """
    评估用户冲突处理风格

    通过问卷或行为分析评估用户的冲突处理风格，
    包括回避型、对抗型、迁就型、妥协型、协商型五种。
    """
    style = service.assess_conflict_style(
        user_id=user_id,
        avoiding_score=request.avoiding_score,
        competing_score=request.competing_score,
        accommodating_score=request.accommodating_score,
        compromising_score=request.compromising_score,
        collaborating_score=request.collaborating_score,
        conflict_triggers=request.conflict_triggers,
        assessment_method=request.assessment_method,
    )

    return ConflictStyleResponse(
        id=style.id,
        user_id=style.user_id,
        primary_style=style.primary_style,
        primary_style_name=get_style_name(style.primary_style),
        avoiding_score=style.avoiding_score,
        competing_score=style.competing_score,
        accommodating_score=style.accommodating_score,
        compromising_score=style.compromising_score,
        collaborating_score=style.collaborating_score,
        style_description=style.style_description,
        conflict_triggers=json.loads(style.conflict_triggers or "[]"),
        assessment_method=style.assessment_method,
        last_assessed_at=style.last_assessed_at.isoformat() if style.last_assessed_at else None,
    )


@router.get("/style/{user_id}", response_model=Optional[ConflictStyleResponse])
async def get_user_conflict_style(
    user_id: str,
    service: ConflictHandlingService = Depends(get_conflict_service),
):
    """获取用户冲突处理风格"""
    style = service.get_user_conflict_style(user_id)
    if not style:
        raise HTTPException(status_code=404, detail="用户未进行冲突风格评估")

    return ConflictStyleResponse(
        id=style.id,
        user_id=style.user_id,
        primary_style=style.primary_style,
        primary_style_name=get_style_name(style.primary_style),
        avoiding_score=style.avoiding_score,
        competing_score=style.competing_score,
        accommodating_score=style.accommodating_score,
        compromising_score=style.compromising_score,
        collaborating_score=style.collaborating_score,
        style_description=style.style_description,
        conflict_triggers=json.loads(style.conflict_triggers or "[]"),
        assessment_method=style.assessment_method,
        last_assessed_at=style.last_assessed_at.isoformat() if style.last_assessed_at else None,
    )


# ============= 冲突兼容性 API =============

@router.get("/compatibility/{user_a_id}/{user_b_id}", response_model=ConflictCompatibilityResponse)
async def get_conflict_compatibility(
    user_a_id: str,
    user_b_id: str,
    service: ConflictHandlingService = Depends(get_conflict_service),
):
    """
    获取双方冲突兼容性

    基于双方冲突处理风格、触发点兼容性、解决方式兼容性
    计算综合兼容性评分，并提供风险提示和建议。
    """
    # 获取兼容性
    compatibility = service.get_conflict_compatibility(user_a_id, user_b_id)

    if not compatibility:
        # 如果没有记录，先计算
        compatibility = service.calculate_conflict_compatibility(user_a_id, user_b_id)

    # 获取双方风格
    style_a = service.get_user_conflict_style(user_a_id)
    style_b = service.get_user_conflict_style(user_b_id)

    return ConflictCompatibilityResponse(
        id=compatibility.id,
        compatibility_score=compatibility.compatibility_score,
        style_compatibility=compatibility.style_compatibility,
        trigger_compatibility=compatibility.trigger_compatibility,
        resolution_compatibility=compatibility.resolution_compatibility,
        style_a_name=get_style_name(style_a.primary_style) if style_a else "未知",
        style_b_name=get_style_name(style_b.primary_style) if style_b else "未知",
        risk_factors=json.loads(compatibility.risk_factors or "[]"),
        suggestions=json.loads(compatibility.suggestions or "[]"),
        compatibility_details=json.loads(compatibility.compatibility_details or "{}"),
    )


@router.post("/compatibility/{user_a_id}/{user_b_id}/calculate")
async def calculate_conflict_compatibility(
    user_a_id: str,
    user_b_id: str,
    service: ConflictHandlingService = Depends(get_conflict_service),
):
    """
    重新计算双方冲突兼容性

    当双方冲突风格有更新时，可调用此接口重新计算兼容性。
    """
    compatibility = service.calculate_conflict_compatibility(user_a_id, user_b_id)

    return {
        "message": "兼容性计算完成",
        "compatibility_score": compatibility.compatibility_score,
        "style_compatibility": compatibility.style_compatibility,
        "trigger_compatibility": compatibility.trigger_compatibility,
        "resolution_compatibility": compatibility.resolution_compatibility,
    }


# ============= 冲突历史 API =============

@router.post("/history/record", response_model=ConflictRecordResponse)
async def record_conflict(
    request: ConflictRecordRequest,
    user_id: str = Query(..., description="用户 ID"),
    service: ConflictHandlingService = Depends(get_conflict_service),
):
    """记录冲突事件"""
    conflict = service.record_conflict(
        user_id=user_id,
        conflict_type=request.conflict_type,
        conflict_topic=request.conflict_topic,
        conflict_description=request.conflict_description,
        partner_user_id=request.partner_user_id,
        handling_style=request.handling_style,
    )

    return ConflictRecordResponse(
        id=conflict.id,
        user_id=conflict.user_id,
        partner_user_id=conflict.partner_user_id,
        conflict_type=conflict.conflict_type,
        conflict_topic=conflict.conflict_topic,
        conflict_description=conflict.conflict_description,
        handling_style=conflict.handling_style,
        resolution_status=conflict.resolution_status,
        created_at=conflict.created_at.isoformat(),
    )


@router.post("/history/{conflict_id}/resolve", response_model=ConflictRecordResponse)
async def resolve_conflict(
    conflict_id: str,
    request: ConflictResolveRequest,
    service: ConflictHandlingService = Depends(get_conflict_service),
):
    """标记冲突为已解决"""
    conflict = service.resolve_conflict(
        conflict_id=conflict_id,
        resolution_description=request.resolution_description,
        handling_effectiveness=request.handling_effectiveness,
        relationship_impact=request.relationship_impact,
        lessons_learned=request.lessons_learned,
    )

    return ConflictRecordResponse(
        id=conflict.id,
        user_id=conflict.user_id,
        partner_user_id=conflict.partner_user_id,
        conflict_type=conflict.conflict_type,
        conflict_topic=conflict.conflict_topic,
        conflict_description=conflict.conflict_description,
        handling_style=conflict.handling_style,
        resolution_status=conflict.resolution_status,
        created_at=conflict.created_at.isoformat(),
    )


@router.get("/history/{user_id}", response_model=List[ConflictRecordResponse])
async def get_user_conflict_history(
    user_id: str,
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
    service: ConflictHandlingService = Depends(get_conflict_service),
):
    """获取用户冲突历史"""
    history = service.get_user_conflict_history(user_id, limit)

    return [
        ConflictRecordResponse(
            id=h.id,
            user_id=h.user_id,
            partner_user_id=h.partner_user_id,
            conflict_type=h.conflict_type,
            conflict_topic=h.conflict_topic,
            conflict_description=h.conflict_description,
            handling_style=h.handling_style,
            resolution_status=h.resolution_status,
            created_at=h.created_at.isoformat(),
        )
        for h in history
    ]


# ============= 沟通模式 API =============

@router.post("/communication/assess", response_model=CommunicationPatternResponse)
async def assess_communication_pattern(
    request: CommunicationPatternRequest,
    user_id: str = Query(..., description="用户 ID"),
    service: ConflictHandlingService = Depends(get_conflict_service),
):
    """评估用户沟通模式"""
    pattern = service.assess_communication_pattern(
        user_id=user_id,
        communication_style=request.communication_style,
        preferred_frequency=request.preferred_frequency,
        preferred_channels=request.preferred_channels,
        preferred_time=request.preferred_time,
        response_pattern=request.response_pattern,
        depth_preference=request.depth_preference,
    )

    return CommunicationPatternResponse(
        id=pattern.id,
        user_id=pattern.user_id,
        communication_style=pattern.communication_style,
        preferred_frequency=pattern.preferred_frequency,
        preferred_channels=json.loads(pattern.preferred_channels or "[]"),
        preferred_time=pattern.preferred_time,
        response_pattern=pattern.response_pattern,
        depth_preference=pattern.depth_preference,
    )


@router.get("/communication/{user_id}", response_model=Optional[CommunicationPatternResponse])
async def get_user_communication_pattern(
    user_id: str,
    service: ConflictHandlingService = Depends(get_conflict_service),
):
    """获取用户沟通模式"""
    pattern = service.get_user_communication_pattern(user_id)
    if not pattern:
        raise HTTPException(status_code=404, detail="用户未进行沟通模式评估")

    return CommunicationPatternResponse(
        id=pattern.id,
        user_id=pattern.user_id,
        communication_style=pattern.communication_style,
        preferred_frequency=pattern.preferred_frequency,
        preferred_channels=json.loads(pattern.preferred_channels or "[]"),
        preferred_time=pattern.preferred_time,
        response_pattern=pattern.response_pattern,
        depth_preference=pattern.depth_preference,
    )


# ============= 兼容性建议 API =============

@router.get("/suggestions/{user_a_id}/{user_b_id}", response_model=CompatibilitySuggestionResponse)
async def get_compatibility_suggestions(
    user_a_id: str,
    user_b_id: str,
    service: ConflictHandlingService = Depends(get_conflict_service),
):
    """
    获取双方兼容性综合建议

    综合冲突风格和沟通模式的兼容性分析，
    提供整体的关系建议。
    """
    suggestions = service.get_compatibility_suggestions(user_a_id, user_b_id)

    return CompatibilitySuggestionResponse(
        conflict_compatibility=suggestions.get("conflict_compatibility"),
        communication_compatibility=suggestions.get("communication_compatibility"),
        overall_suggestions=suggestions.get("overall_suggestions", []),
    )


# ============= 冲突化解建议 API =============

@router.get("/tips", response_model=List[ResolutionTipResponse])
async def get_resolution_tips(
    conflict_type: str = Query(..., description="冲突类型"),
    style_a: Optional[str] = Query(None, description="用户 A 的风格"),
    style_b: Optional[str] = Query(None, description="用户 B 的风格"),
    tip_type: Optional[str] = Query(None, description="建议类型"),
    service: ConflictHandlingService = Depends(get_conflict_service),
):
    """获取冲突化解建议"""
    tips = service.get_resolution_tips(
        conflict_type=conflict_type,
        style_a=style_a,
        style_b=style_b,
        tip_type=tip_type,
    )

    return [
        ResolutionTipResponse(
            id=tip.id,
            conflict_type=tip.conflict_type,
            style_combination=tip.style_combination,
            tip_title=tip.tip_title,
            tip_content=tip.tip_content,
            tip_type=tip.tip_type,
            psychological_basis=tip.psychological_basis,
            effectiveness_rating=tip.effectiveness_rating,
            applicable_scenarios=json.loads(tip.applicable_scenarios or "[]"),
        )
        for tip in tips
    ]


@router.post("/tips", response_model=ResolutionTipResponse)
async def add_resolution_tip(
    request: Dict[str, Any],
    service: ConflictHandlingService = Depends(get_conflict_service),
):
    """添加冲突化解建议（管理员功能）"""
    tip = service.add_resolution_tip(
        conflict_type=request["conflict_type"],
        tip_title=request["tip_title"],
        tip_content=request["tip_content"],
        style_combination=request.get("style_combination"),
        tip_type=request.get("tip_type", "general"),
        psychological_basis=request.get("psychological_basis"),
    )

    return ResolutionTipResponse(
        id=tip.id,
        conflict_type=tip.conflict_type,
        style_combination=tip.style_combination,
        tip_title=tip.tip_title,
        tip_content=tip.tip_content,
        tip_type=tip.tip_type,
        psychological_basis=tip.psychological_basis,
        effectiveness_rating=tip.effectiveness_rating,
        applicable_scenarios=json.loads(tip.applicable_scenarios or "[]"),
    )


@router.post("/tips/{tip_id}/rate")
async def rate_tip_effectiveness(
    tip_id: str,
    rating: float = Query(..., ge=1, le=5, description="评分 (1-5)"),
    service: ConflictHandlingService = Depends(get_conflict_service),
):
    """评分建议有效性"""
    tip = service.rate_tip_effectiveness(tip_id, rating)

    return {
        "message": "评分成功",
        "tip_id": tip_id,
        "new_rating": tip.effectiveness_rating,
        "total_ratings": tip.effectiveness_count,
    }


# ============= 风格参考数据 API =============

@router.get("/styles/reference")
async def get_style_reference():
    """
    获取冲突处理风格参考数据

    返回所有风格的中文名称和详细描述，
    用于前端展示和问卷设计。
    """
    return {
        "styles": [
            {
                "key": style_key,
                "name": STYLE_NAMES[style_key],
                "description": desc,
            }
            for style_key, desc in [
                ("avoiding", "回避型：倾向于避免正面冲突，可能会压抑自己的想法和感受"),
                ("competing", "对抗型：倾向于坚持己见，视冲突为竞争，力求获胜"),
                ("accommodating", "迁就型：倾向于迁就对方，将对方需求置于自己之上"),
                ("compromising", "妥协型：倾向于寻找中间地带，双方各让一步"),
                ("collaborating", "协商型：倾向于深入探讨问题根源，寻求双赢解决方案"),
            ]
        ]
    }


@router.get("/conflict-types/reference")
async def get_conflict_types_reference():
    """
    获取冲突类型参考数据

    返回所有冲突类型的定义和示例，
    用于前端展示和问卷设计。
    """
    return {
        "conflict_types": [
            {
                "key": "values_mismatch",
                "name": "价值观分歧",
                "description": "对生活目标、消费观念、家庭责任等核心价值观的不同理解",
            },
            {
                "key": "communication_issue",
                "name": "沟通问题",
                "description": "表达方式、倾听能力、反馈频率等沟通方面的障碍",
            },
            {
                "key": "expectation_gap",
                "name": "期望落差",
                "description": "对关系发展速度、投入程度、未来规划等方面的期望不一致",
            },
            {
                "key": "boundary_violation",
                "name": "边界侵犯",
                "description": "个人空间、隐私、社交圈等边界被侵犯",
            },
            {
                "key": "resource_dispute",
                "name": "资源争议",
                "description": "时间、金钱、精力等资源分配的争议",
            },
            {
                "key": "personality_clash",
                "name": "性格冲突",
                "description": "生活习惯、兴趣爱好、社交方式等性格差异导致的冲突",
            },
        ]
    }


