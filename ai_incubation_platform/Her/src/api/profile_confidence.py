"""
用户画像置信度 API 端点

功能：
- 获取用户置信度详情
- 刷新置信度评估
- 获取置信度摘要（用于匹配卡片展示）
- 获取验证建议
- 批量评估（管理员接口）

端点：
- GET /api/profile/confidence - 获取完整置信度详情
- GET /api/profile/confidence/summary - 获取置信度摘要
- POST /api/profile/confidence/refresh - 手动刷新评估
- GET /api/profile/confidence/recommendations - 获取验证建议
- POST /api/profile/confidence/batch - 批量评估（管理员）
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from typing import List, Optional
from pydantic import BaseModel

from auth.jwt import get_current_user, get_admin_user
from services.profile_confidence_service import profile_confidence_service
from utils.logger import logger


router = APIRouter(prefix="/api/profile/confidence", tags=["profile_confidence"])


# ============================================
# Pydantic 模型
# ============================================

class ConfidenceDetailResponse(BaseModel):
    """置信度详情响应"""
    success: bool
    user_id: str
    overall_confidence: float
    confidence_level: str
    confidence_level_name: str
    dimensions: dict
    cross_validation_flags: dict
    recommendations: list
    last_evaluated_at: Optional[str] = None


class ConfidenceSummaryResponse(BaseModel):
    """置信度摘要响应"""
    confidence: float
    level: str
    level_name: str
    verified: bool
    flags_count: int


class RefreshRequest(BaseModel):
    """刷新评估请求"""
    force: bool = False


class BatchEvaluateRequest(BaseModel):
    """批量评估请求"""
    user_ids: List[str]


class BatchEvaluateResponse(BaseModel):
    """批量评估响应"""
    success_count: int
    failed_count: int
    details: dict


# ============================================
# API 端点
# ============================================

@router.get("", response_model=ConfidenceDetailResponse)
async def get_confidence_detail(
    current_user_id: str = Depends(get_current_user)
):
    """
    获取用户置信度详情

    返回：
    - overall_confidence: 总置信度 (0-1)
    - confidence_level: 置信度等级 (low/medium/high/very_high)
    - dimensions: 各维度置信度
    - cross_validation_flags: 交叉验证异常标记
    - recommendations: 验证建议
    """
    logger.info(f"Getting confidence detail for user: {current_user_id}")

    result = profile_confidence_service.get_confidence_detail(current_user_id)

    if not result.get("success"):
        raise HTTPException(status_code=500, detail="Confidence evaluation failed")

    return ConfidenceDetailResponse(**result)


@router.get("/summary", response_model=ConfidenceSummaryResponse)
async def get_confidence_summary(
    current_user_id: str = Depends(get_current_user)
):
    """
    获取置信度摘要

    用于展示在匹配卡片、用户资料卡片等场景
    """
    result = profile_confidence_service.get_confidence_summary(current_user_id)
    return ConfidenceSummaryResponse(**result)


@router.get("/user/{user_id}/summary", response_model=ConfidenceSummaryResponse)
async def get_other_user_confidence_summary(
    user_id: str,
    current_user_id: str = Depends(get_current_user)
):
    """
    获取其他用户的置信度摘要

    用于查看匹配对象的可信度
    """
    logger.info(f"User {current_user_id} viewing confidence summary of user {user_id}")

    result = profile_confidence_service.get_confidence_summary(user_id)
    return ConfidenceSummaryResponse(**result)


@router.post("/refresh")
async def refresh_confidence(
    request: RefreshRequest,
    current_user_id: str = Depends(get_current_user)
):
    """
    手动刷新置信度评估

    触发重新计算各维度置信度
    """
    logger.info(f"Refreshing confidence for user: {current_user_id}, force={request.force}")

    result = profile_confidence_service.evaluate_user_confidence(
        user_id=current_user_id,
        trigger_source="manual",
        force_refresh=request.force
    )

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Refresh failed"))

    return {
        "success": True,
        "message": "置信度已更新",
        "confidence": result["overall_confidence"],
        "level": result["confidence_level"],
        "change": result.get("confidence_change", 0),
    }


@router.get("/recommendations")
async def get_verification_recommendations(
    current_user_id: str = Depends(get_current_user)
):
    """
    获取验证建议

    返回提升置信度建议完成的验证项
    """
    detail = profile_confidence_service.get_confidence_detail(current_user_id)

    recommendations = detail.get("recommendations", [])

    return {
        "success": True,
        "recommendations": recommendations,
        "total_count": len(recommendations),
        "high_priority_count": sum(1 for r in recommendations if r.get("priority") == "high"),
    }


@router.post("/batch", response_model=BatchEvaluateResponse)
async def batch_evaluate_users(
    request: BatchEvaluateRequest,
    admin_user_id: str = Depends(get_admin_user)
):
    """
    批量评估用户置信度

    管理员接口，用于批量触发评估
    """
    logger.info(f"Admin {admin_user_id} triggering batch evaluation for {len(request.user_ids)} users")

    if len(request.user_ids) > 100:
        raise HTTPException(status_code=400, detail="最多批量评估 100 个用户")

    result = profile_confidence_service.batch_evaluate_users(
        user_ids=request.user_ids,
        trigger_source="admin_batch"
    )

    return BatchEvaluateResponse(**result)


@router.get("/explain")
async def explain_confidence_system(
    current_user_id: str = Depends(get_current_user)
):
    """
    解释置信度系统

    向用户展示置信度是如何计算的
    """
    return {
        "success": True,
        "explanation": {
            "title": "用户可信度评估系统",
            "description": "我们通过多维度的智能分析来评估用户信息的可信度，帮助您更安全地进行匹配。",
            "dimensions": [
                {
                    "name": "身份验证",
                    "weight": "25%",
                    "description": "实名认证、人脸核身、手机验证等官方认证",
                    "how_to_improve": "完成实名认证可大幅提升此维度分数",
                },
                {
                    "name": "信息一致性",
                    "weight": "20%",
                    "description": "年龄与学历、职业与收入等信息的逻辑一致性校验",
                    "how_to_improve": "确保填写的信息之间逻辑一致，或完成相关认证",
                },
                {
                    "name": "行为一致性",
                    "weight": "15%",
                    "description": "您声称的兴趣爱好与实际浏览行为的一致程度",
                    "how_to_improve": "多浏览和互动您感兴趣的内容类型",
                },
                {
                    "name": "社交背书",
                    "weight": "10%",
                    "description": "邀请来源、好评率等社交信号",
                    "how_to_improve": "邀请朋友加入、获得其他用户的好评",
                },
                {
                    "name": "时间积累",
                    "weight": "基础分",
                    "description": "注册时长、活跃天数、画像完善度",
                    "how_to_improve": "保持活跃、完善个人资料",
                },
            ],
            "levels": [
                {"name": "极可信", "range": "80-100%", "color": "gold"},
                {"name": "较可信", "range": "60-80%", "color": "green"},
                {"name": "普通用户", "range": "40-60%", "color": "blue"},
                {"name": "需谨慎", "range": "0-40%", "color": "orange"},
            ],
            "privacy_note": "置信度评估仅用于帮助用户判断对方信息的可信程度，不会公开您的具体信息。",
        },
    }


# ============================================
# 注册时自动评估的钩子
# ============================================

async def evaluate_on_register(user_id: str):
    """用户注册后自动评估置信度"""
    logger.info(f"Auto-evaluating confidence for newly registered user: {user_id}")

    try:
        result = profile_confidence_service.evaluate_user_confidence(
            user_id=user_id,
            trigger_source="register"
        )
        logger.info(f"Auto-evaluation result: confidence={result.get('overall_confidence', 0.3):.2f}")
        return result
    except Exception as e:
        logger.error(f"Auto-evaluation failed for user {user_id}: {e}")
        return {"success": False, "error": str(e)}


async def evaluate_on_profile_update(user_id: str):
    """用户画像更新后自动重新评估"""
    logger.info(f"Re-evaluating confidence after profile update for user: {user_id}")

    try:
        result = profile_confidence_service.evaluate_user_confidence(
            user_id=user_id,
            trigger_source="profile_update"
        )
        return result
    except Exception as e:
        logger.error(f"Re-evaluation failed for user {user_id}: {e}")
        return {"success": False, "error": str(e)}