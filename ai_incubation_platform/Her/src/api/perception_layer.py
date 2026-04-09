"""
P1: 感知层 API - 用户向量表示和数字潜意识引擎

功能包括：
- 用户向量查询和更新
- 向量相似度计算
- 数字潜意识画像分析
- 向量偏移历史查询
"""
import json
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from db.database import get_db
from services.perception_layer_service import (
    PerceptionLayerService,
    get_vector_dimension_name,
    get_subconscious_trait_description,
    get_attachment_style_description,
)
from models.p1_perception_models import (
    DigitalSubconsciousProfileDB,
    VECTOR_DIMENSIONS,
    SUBCONSCIOUS_TRAITS_LIBRARY,
    ATTACHMENT_STYLE_DESCRIPTIONS,
)


router = APIRouter(prefix="/api/perception", tags=["P1-感知层"])


# ============= 请求/响应模型 =============

class UserVectorResponse(BaseModel):
    """用户向量响应"""
    success: bool
    data: Dict[str, Any]
    message: Optional[str] = None


class VectorSimilarityRequest(BaseModel):
    """向量相似度请求"""
    user_a_id: str = Field(..., description="用户 A ID")
    user_b_id: str = Field(..., description="用户 B ID")
    vector_type: str = Field(..., description="向量类型")


class VectorSimilarityResponse(BaseModel):
    """向量相似度响应"""
    success: bool
    data: Dict[str, Any]
    message: Optional[str] = None


class CompatibilityRequest(BaseModel):
    """兼容性请求"""
    user_a_id: str = Field(..., description="用户 A ID")
    user_b_id: str = Field(..., description="用户 B ID")
    weights: Optional[Dict[str, float]] = Field(None, description="各维度权重")


class CompatibilityResponse(BaseModel):
    """兼容性响应"""
    success: bool
    data: Dict[str, Any]
    message: Optional[str] = None


class SubconsciousProfileResponse(BaseModel):
    """潜意识画像响应"""
    id: str
    user_id: str
    subconscious_traits: List[Dict[str, str]]
    hidden_needs: List[Dict[str, Any]]
    emotional_tendency: str
    attachment_style: str
    attachment_style_description: str
    relationship_patterns: List[Dict[str, str]]
    growth_suggestions: List[Dict[str, str]]
    confidence_score: float
    last_analyzed_at: Optional[str] = None

    class Config:
        from_attributes = True


class VectorUpdateHistoryResponse(BaseModel):
    """向量更新历史响应"""
    id: str
    user_id: str
    vector_type: str
    previous_vector: Optional[List[float]]
    new_vector: List[float]
    vector_drift: float
    update_reason: str
    created_at: str

    class Config:
        from_attributes = True


# ============= 依赖注入 =============

def get_perception_service(db: Session = Depends(get_db)) -> PerceptionLayerService:
    """获取感知层服务"""
    return PerceptionLayerService(db)


# ============= 用户向量 API =============

@router.get("/vector/{user_id}", response_model=UserVectorResponse)
async def get_user_vector(
    user_id: str,
    vector_type: Optional[str] = Query(None, description="向量类型"),
    service: PerceptionLayerService = Depends(get_perception_service),
):
    """
    获取用户向量

    返回用户的向量表示，包括价值观、兴趣偏好、沟通风格和行为模式向量。
    """
    vector_data = service.get_user_vector(user_id, vector_type)

    return UserVectorResponse(
        success=True,
        data=vector_data,
        message="获取成功",
    )


@router.post("/vector/{user_id}/initialize")
async def initialize_user_vector(
    user_id: str,
    service: PerceptionLayerService = Depends(get_perception_service),
):
    """
    初始化用户向量

    为用户创建默认的向量表示。
    """
    vector = service.get_or_create_user_vector(user_id)

    return {
        "success": True,
        "data": {
            "user_id": user_id,
            "vector_version": vector.vector_version,
            "created_at": vector.created_at.isoformat(),
        },
        "message": "用户向量初始化完成",
    }


@router.post("/vector/{user_id}/update")
async def update_user_vector(
    user_id: str,
    vector_type: str = Query(..., description="向量类型"),
    vector_data: List[float] = Body(..., description="新向量数据"),
    update_reason: str = Body(default="manual", description="更新原因"),
    service: PerceptionLayerService = Depends(get_perception_service),
):
    """
    更新用户向量

    手动更新用户的向量表示。
    """
    try:
        vector = service.update_user_vectors(
            user_id=user_id,
            vector_type=vector_type,
            new_vector=vector_data,
            update_reason=update_reason,
        )

        return {
            "success": True,
            "data": {
                "user_id": user_id,
                "vector_type": vector_type,
                "vector_version": vector.vector_version,
                "updated_at": vector.updated_at.isoformat(),
            },
            "message": f"{get_vector_dimension_name(vector_type)}更新完成",
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============= 向量相似度 API =============

@router.get("/similarity/{user_a_id}/{user_b_id}/{vector_type}", response_model=VectorSimilarityResponse)
async def get_vector_similarity(
    user_a_id: str,
    user_b_id: str,
    vector_type: str,
    use_cache: bool = Query(default=True, description="是否使用缓存"),
    service: PerceptionLayerService = Depends(get_perception_service),
):
    """
    计算向量相似度

    计算两个用户在指定向量类型上的相似度。
    """
    if use_cache:
        similarity = service.get_or_compute_similarity_cache(
            user_a_id, user_b_id, vector_type
        )
    else:
        similarity = service.calculate_vector_similarity(
            user_a_id, user_b_id, vector_type
        )

    return VectorSimilarityResponse(
        success=True,
        data={
            "user_a_id": user_a_id,
            "user_b_id": user_b_id,
            "vector_type": vector_type,
            "similarity": similarity,
        },
        message=f"相似度计算完成",
    )


@router.post("/compatibility", response_model=CompatibilityResponse)
async def get_overall_compatibility(
    request: CompatibilityRequest,
    service: PerceptionLayerService = Depends(get_perception_service),
):
    """
    计算综合兼容性

    基于多个向量维度计算双方的综合兼容性。
    """
    compatibility = service.get_overall_compatibility(
        user_a_id=request.user_a_id,
        user_b_id=request.user_b_id,
        weights=request.weights,
    )

    return CompatibilityResponse(
        success=True,
        data={
            "user_a_id": request.user_a_id,
            "user_b_id": request.user_b_id,
            "overall_compatibility": compatibility,
            "weights_used": request.weights or "default",
        },
        message="兼容性计算完成",
    )


# ============= 数字潜意识画像 API =============

@router.post("/subconscious/{user_id}/analyze")
async def analyze_digital_subconscious(
    user_id: str,
    service: PerceptionLayerService = Depends(get_perception_service),
):
    """
    分析数字潜意识画像

    基于用户向量和行为数据分析其潜意识特征、依恋风格和成长建议。
    """
    profile = service.analyze_digital_subconscious(user_id)

    return {
        "success": True,
        "data": {
            "user_id": user_id,
            "subconscious_traits": json.loads(profile.subconscious_traits),
            "emotional_tendency": profile.emotional_tendency,
            "attachment_style": profile.attachment_style,
            "confidence_score": profile.confidence_score,
        },
        "message": "潜意识画像分析完成",
    }


@router.get("/subconscious/{user_id}", response_model=Optional[SubconsciousProfileResponse])
async def get_subconscious_profile(
    user_id: str,
    service: PerceptionLayerService = Depends(get_perception_service),
):
    """获取用户数字潜意识画像"""
    profile = service.get_digital_subconscious_profile(user_id)

    if not profile:
        # 如果没有画像，先分析
        profile = service.analyze_digital_subconscious(user_id)

    return SubconsciousProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        subconscious_traits=[
            {"trait": trait, "description": get_subconscious_trait_description(trait)}
            for trait in json.loads(profile.subconscious_traits or "[]")
        ],
        hidden_needs=json.loads(profile.hidden_needs or "[]"),
        emotional_tendency=profile.emotional_tendency,
        attachment_style=profile.attachment_style,
        attachment_style_description=get_attachment_style_description(profile.attachment_style),
        relationship_patterns=json.loads(profile.relationship_patterns or "[]"),
        growth_suggestions=json.loads(profile.growth_suggestions or "[]"),
        confidence_score=profile.confidence_score,
        last_analyzed_at=profile.last_analyzed_at.isoformat() if profile.last_analyzed_at else None,
    )


# ============= 向量更新历史 API =============

@router.get("/history/{user_id}", response_model=List[VectorUpdateHistoryResponse])
async def get_vector_update_history(
    user_id: str,
    vector_type: Optional[str] = Query(None, description="向量类型"),
    limit: int = Query(default=20, ge=1, le=100, description="返回数量限制"),
    service: PerceptionLayerService = Depends(get_perception_service),
):
    """获取向量更新历史"""
    from models.p1_perception_models import VectorUpdateHistoryDB
    from sqlalchemy import and_, desc

    query = service.db.query(VectorUpdateHistoryDB).filter(
        VectorUpdateHistoryDB.user_id == user_id
    )

    if vector_type:
        query = query.filter(VectorUpdateHistoryDB.vector_type == vector_type)

    history = query.order_by(desc(VectorUpdateHistoryDB.created_at)).limit(limit).all()

    return [
        VectorUpdateHistoryResponse(
            id=h.id,
            user_id=h.user_id,
            vector_type=h.vector_type,
            previous_vector=json.loads(h.previous_vector) if h.previous_vector else None,
            new_vector=json.loads(h.new_vector),
            vector_drift=h.vector_drift,
            update_reason=h.update_reason,
            created_at=h.created_at.isoformat(),
        )
        for h in history
    ]


# ============= 参考数据 API =============

@router.get("/dimensions/reference")
async def get_vector_dimensions_reference():
    """
    获取向量维度参考数据

    返回所有向量类型的维度配置和说明。
    """
    return {
        "dimensions": {
            vector_type: {
                "name": get_vector_dimension_name(vector_type),
                "dimension": dim,
            }
            for vector_type, dim in VECTOR_DIMENSIONS.items()
        }
    }


@router.get("/subconscious-traits/reference")
async def get_subconscious_traits_reference():
    """
    获取潜意识特征标签库

    返回所有潜意识特征标签及其描述。
    """
    return {
        "traits": [
            {"trait": trait, "description": desc}
            for trait, desc in SUBCONSCIOUS_TRAITS_LIBRARY.items()
        ]
    }


@router.get("/attachment-styles/reference")
async def get_attachment_styles_reference():
    """
    获取依恋风格参考数据

    返回所有依恋风格及其描述。
    """
    return {
        "styles": [
            {"style": style, "description": desc}
            for style, desc in ATTACHMENT_STYLE_DESCRIPTIONS.items()
        ]
    }

