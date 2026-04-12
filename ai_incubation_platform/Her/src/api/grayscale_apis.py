"""
灰度配置 API - A/B 测试与功能开关管理

核心功能：
- 功能开关查询与配置
- A/B 实验管理
- 用户分组查询
- 实验指标统计
"""
from fastapi import APIRouter, HTTPException, Depends, Body
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

from services.grayscale_config_service import (
    get_grayscale_config_service,
    GrayscaleConfigService,
    init_default_feature_flags,
    init_default_ab_experiments,
)
from auth.jwt import get_current_user_optional
from utils.logger import logger


router = APIRouter(prefix="/api/grayscale", tags=["grayscale"])


# ==================== 请求模型 ====================

class FeatureFlagRequest(BaseModel):
    """功能开关请求"""
    flag_key: str = Field(..., description="功能开关标识")
    user_id: str = Field(..., description="用户ID")
    user_context: Optional[Dict[str, Any]] = Field(None, description="用户上下文")


class ExperimentVariantRequest(BaseModel):
    """实验分组请求"""
    experiment_key: str = Field(..., description="实验标识")
    user_id: str = Field(..., description="用户ID")


class CreateFeatureFlagRequest(BaseModel):
    """创建功能开关请求"""
    flag_key: str
    name: str
    description: Optional[str] = None
    is_enabled: bool = True
    rollout_percentage: int = Field(0, ge=0, le=100)
    target_user_groups: List[str] = []
    target_cities: List[str] = []
    config_data: Dict[str, Any] = {}


class CreateExperimentRequest(BaseModel):
    """创建实验请求"""
    experiment_key: str
    name: str
    description: Optional[str] = None
    variants: List[Dict[str, Any]] = Field(..., description="变体配置列表")
    primary_metric: Optional[str] = None
    traffic_allocation: int = Field(100, ge=0, le=100)


# ==================== API 端点 ====================

@router.post("/feature/check")
async def check_feature_enabled(
    request: FeatureFlagRequest
) -> Dict:
    """
    检查功能是否对用户启用

    返回：
    - is_enabled: 功能是否启用
    - config: 功能配置（如果启用）
    """
    logger.info(f"[GRAYSCALE] Check feature: {request.flag_key} for user={request.user_id}")

    try:
        service = get_grayscale_config_service()

        is_enabled = service.is_feature_enabled(
            flag_key=request.flag_key,
            user_id=request.user_id,
            user_context=request.user_context or {}
        )

        config = service.get_feature_config(
            flag_key=request.flag_key,
            user_id=request.user_id,
            user_context=request.user_context or {}
        )

        return {
            "success": True,
            "data": {
                "flag_key": request.flag_key,
                "is_enabled": is_enabled,
                "config": config
            }
        }

    except Exception as e:
        logger.error(f"[GRAYSCALE] Check feature failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/experiment/variant")
async def get_experiment_variant(
    request: ExperimentVariantRequest
) -> Dict:
    """
    获取用户在实验中的分组

    返回：
    - experiment_key: 实验标识
    - variant_name: 分组名称
    - config: 变体配置
    - is_new_assignment: 是否新分配
    """
    logger.info(f"[GRAYSCALE] Get variant: {request.experiment_key} for user={request.user_id}")

    try:
        service = get_grayscale_config_service()

        result = service.get_experiment_variant(
            experiment_key=request.experiment_key,
            user_id=request.user_id
        )

        return {
            "success": True,
            "data": {
                "experiment_key": result.experiment_key,
                "variant_name": result.variant_name,
                "config": result.config,
                "is_new_assignment": result.is_new_assignment
            }
        }

    except Exception as e:
        logger.error(f"[GRAYSCALE] Get variant failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quick-start/{user_id}/enabled")
async def check_quick_start_enabled(
    user_id: str,
    user_group: str = "new_user",
    city: str = ""
) -> Dict:
    """
    检查快速入门功能是否对用户启用

    用于前端决定走哪个流程：
    - quick_start: 新的30秒快速入门流程
    - profile_collection: 原有完整问答流程
    """
    logger.info(f"[GRAYSCALE] Check quick-start for user={user_id}")

    try:
        service = get_grayscale_config_service()

        user_context = {
            "user_group": user_group,
            "city": city
        }

        is_enabled = service.is_quick_start_enabled(user_id, user_context)
        variant = service.get_quick_start_variant(user_id)

        return {
            "success": True,
            "data": {
                "user_id": user_id,
                "quick_start_enabled": is_enabled,
                "variant": variant,
                "recommended_flow": "quick_start" if is_enabled else "profile_collection"
            }
        }

    except Exception as e:
        logger.error(f"[GRAYSCALE] Check quick-start failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/flags")
async def create_feature_flag(
    request: CreateFeatureFlagRequest
) -> Dict:
    """
    创建新的功能开关

    用于后台管理配置
    """
    logger.info(f"[GRAYSCALE] Create feature flag: {request.flag_key}")

    try:
        import uuid
        from services.grayscale_config_service import FeatureFlagDB
        from utils.db_session_manager import db_session

        with db_session() as db:
            # 检查是否已存在
            existing = db.query(FeatureFlagDB).filter(
                FeatureFlagDB.flag_key == request.flag_key
            ).first()

            if existing:
                raise HTTPException(status_code=400, detail="Flag already exists")

            flag = FeatureFlagDB(
                id=str(uuid.uuid4()),
                flag_key=request.flag_key,
                name=request.name,
                description=request.description,
                is_enabled=request.is_enabled,
                rollout_percentage=request.rollout_percentage,
                target_user_groups=request.target_user_groups,
                target_cities=request.target_cities,
                config_data=request.config_data
            )
            db.add(flag)
            db.commit()

        return {
            "success": True,
            "message": "Feature flag created",
            "data": {"flag_key": request.flag_key}
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[GRAYSCALE] Create flag failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/flags")
async def list_feature_flags() -> Dict:
    """
    获取所有功能开关列表

    用于后台管理查看
    """
    logger.info("[GRAYSCALE] List feature flags")

    try:
        from services.grayscale_config_service import FeatureFlagDB
        from utils.db_session_manager import db_session

        with db_session() as db:
            flags = db.query(FeatureFlagDB).all()

            return {
                "success": True,
                "data": {
                    "flags": [
                        {
                            "flag_key": f.flag_key,
                            "name": f.name,
                            "is_enabled": f.is_enabled,
                            "rollout_percentage": f.rollout_percentage,
                            "target_user_groups": f.target_user_groups or [],
                            "target_cities": f.target_cities or []
                        }
                        for f in flags
                    ],
                    "total_count": len(flags)
                }
            }

    except Exception as e:
        logger.error(f"[GRAYSCALE] List flags failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/experiments")
async def create_experiment(
    request: CreateExperimentRequest
) -> Dict:
    """
    创建新的 A/B 实验
    """
    logger.info(f"[GRAYSCALE] Create experiment: {request.experiment_key}")

    try:
        import uuid
        from services.grayscale_config_service import ABExperimentDB
        from utils.db_session_manager import db_session

        with db_session() as db:
            existing = db.query(ABExperimentDB).filter(
                ABExperimentDB.experiment_key == request.experiment_key
            ).first()

            if existing:
                raise HTTPException(status_code=400, detail="Experiment already exists")

            experiment = ABExperimentDB(
                id=str(uuid.uuid4()),
                experiment_key=request.experiment_key,
                name=request.name,
                description=request.description,
                status="draft",
                variants=request.variants,
                primary_metric=request.primary_metric,
                traffic_allocation=request.traffic_allocation
            )
            db.add(experiment)
            db.commit()

        return {
            "success": True,
            "message": "Experiment created",
            "data": {"experiment_key": request.experiment_key}
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[GRAYSCALE] Create experiment failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/init-defaults")
async def initialize_default_configs() -> Dict:
    """
    初始化默认配置

    包括功能开关和 A/B 实验的默认配置
    """
    logger.info("[GRAYSCALE] Initialize default configs")

    try:
        await init_default_feature_flags()
        await init_default_ab_experiments()

        return {
            "success": True,
            "message": "Default configs initialized",
            "data": {
                "feature_flags_count": len(DEFAULT_FEATURE_FLAGS),
                "experiments_count": len(DEFAULT_EXPERIMENTS)
            }
        }

    except Exception as e:
        logger.error(f"[GRAYSCALE] Init defaults failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check() -> Dict:
    """健康检查"""
    return {
        "success": True,
        "service": "grayscale-config",
        "status": "healthy"
    }


# 导入默认配置常量
from services.grayscale_config_service import DEFAULT_FEATURE_FLAGS, DEFAULT_AB_EXPERIMENTS as DEFAULT_EXPERIMENTS