"""
用户反馈 API 路由 - v1.22 用户体验优化

提供用户反馈功能的 API 端点
"""
from fastapi import APIRouter, HTTPException, Query, Body, Depends, Header, UploadFile, File, Form
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import AsyncSessionLocal
from sqlalchemy.ext.asyncio import AsyncSession
from services.feedback_service import get_feedback_service

router = APIRouter(prefix="/api/ux/feedback", tags=["ux-feedback"])


# ==================== 依赖注入 ====================

async def get_db() -> AsyncSession:
    """获取数据库会话"""
    async with AsyncSessionLocal() as session:
        yield session


async def get_current_user_id(x_user_id: str = Header(..., description="用户 ID")) -> str:
    """获取当前用户 ID（从请求头）"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="未授权")
    return x_user_id


# ==================== 请求/响应模型 ====================

class FeedbackCreateRequest(BaseModel):
    """反馈创建请求"""
    feedback_type: str = Field(..., description="反馈类型：bug/feature/complaint/compliment/other")
    category: Optional[str] = Field(None, description="反馈分类")
    title: str = Field(..., description="反馈标题")
    description: str = Field(..., description="反馈详细描述")
    contact_info: Optional[str] = Field(None, description="联系方式（可选）")


class FeedbackUpdateRequest(BaseModel):
    """反馈更新请求"""
    title: Optional[str] = Field(None, description="反馈标题")
    description: Optional[str] = Field(None, description="反馈详细描述")
    contact_info: Optional[str] = Field(None, description="联系方式")


class FeedbackResponse(BaseModel):
    """反馈响应"""
    success: bool
    feedback: Dict[str, Any]
    message: str = ""


class FeedbackListResponse(BaseModel):
    """反馈列表响应"""
    success: bool
    feedbacks: List[Dict[str, Any]]
    total: int


class FeedbackCategoriesResponse(BaseModel):
    """反馈分类响应"""
    success: bool
    categories: List[Dict[str, Any]]


class SatisfactionRatingRequest(BaseModel):
    """满意度评分请求"""
    rating: int = Field(..., ge=1, le=5, description="满意度评分 1-5")
    comment: Optional[str] = Field(None, description="满意度评价")


# ==================== API 端点 ====================

@router.post("", response_model=FeedbackResponse)
async def create_feedback(
    request: FeedbackCreateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    提交用户反馈

    允许用户提交 bug 报告、功能建议、投诉或表扬。
    支持截图上传（通过 multipart/form-data）。
    """
    service = get_feedback_service(db)

    try:
        feedback = await service.create_feedback(
            user_id=user_id,
            feedback_type=request.feedback_type,
            title=request.title,
            description=request.description,
            category=request.category,
            contact_info=request.contact_info,
        )

        return {
            "success": True,
            "feedback": feedback.to_dict(),
            "message": "反馈提交成功，我们将尽快处理"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=FeedbackListResponse)
async def get_user_feedback(
    status_filter: Optional[str] = Query(None, description="状态过滤：pending/investigated/resolved/rejected"),
    type_filter: Optional[str] = Query(None, description="类型过滤：bug/feature/complaint/compliment/other"),
    limit: int = Query(50, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    获取我的反馈列表

    返回当前用户提交的所有反馈，支持状态和类型过滤。
    """
    service = get_feedback_service(db)

    feedbacks = await service.get_user_feedback(
        user_id=user_id,
        status_filter=status_filter,
        type_filter=type_filter,
        limit=limit,
        offset=offset
    )

    return {
        "success": True,
        "feedbacks": [f.to_dict() for f in feedbacks],
        "total": len(feedbacks)
    }


@router.get("/{feedback_id}", response_model=FeedbackResponse)
async def get_feedback_details(
    feedback_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    获取反馈详情

    返回指定反馈的详细信息，包括处理状态和官方回复。
    """
    service = get_feedback_service(db)

    feedback = await service.get_feedback_details(feedback_id)

    if not feedback:
        raise HTTPException(status_code=404, detail="反馈不存在")

    if feedback.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权查看此反馈")

    return {
        "success": True,
        "feedback": feedback.to_dict(),
        "message": "获取反馈详情成功"
    }


@router.put("/{feedback_id}", response_model=FeedbackResponse)
async def update_feedback(
    feedback_id: str,
    request: FeedbackUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    更新反馈

    允许用户更新自己提交的反馈（补充信息）。
    仅限反馈提交者本人操作。
    """
    service = get_feedback_service(db)

    try:
        update_data = {k: v for k, v in request.model_dump().items() if v is not None}

        if not update_data:
            raise HTTPException(status_code=400, detail="至少需要提供一个更新字段")

        feedback = await service.update_feedback(
            feedback_id=feedback_id,
            user_id=user_id,
            **update_data
        )

        return {
            "success": True,
            "feedback": feedback.to_dict(),
            "message": "反馈更新成功"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/categories", response_model=FeedbackCategoriesResponse)
async def get_feedback_categories(
    db: AsyncSession = Depends(get_db)
):
    """
    获取反馈分类选项

    返回平台预定义的反馈分类列表，用于前端展示选择选项。
    """
    service = get_feedback_service(db)

    categories = await service.get_feedback_categories()

    return {
        "success": True,
        "categories": [c.to_dict() for c in categories]
    }


@router.post("/{feedback_id}/rating", response_model=FeedbackResponse)
async def submit_satisfaction_rating(
    feedback_id: str,
    request: SatisfactionRatingRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    提交满意度评分

    对已解决的反馈进行满意度评价（1-5 星）。
    仅限反馈提交者本人评价。
    """
    service = get_feedback_service(db)

    try:
        feedback = await service.submit_satisfaction_rating(
            feedback_id=feedback_id,
            user_id=user_id,
            rating=request.rating,
            comment=request.comment
        )

        return {
            "success": True,
            "feedback": feedback.to_dict(),
            "message": "感谢您的评价！"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/stats/summary")
async def get_feedback_stats_summary(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    获取用户反馈统计摘要

    返回当前用户反馈的统计信息，包括总数、各状态数量等。
    """
    service = get_feedback_service(db)

    # 获取用户反馈列表
    all_feedbacks = await service.get_user_feedback(user_id=user_id, limit=1000)

    stats = {
        "total": len(all_feedbacks),
        "pending": sum(1 for f in all_feedbacks if f.status == 'pending'),
        "investigated": sum(1 for f in all_feedbacks if f.status == 'investigated'),
        "resolved": sum(1 for f in all_feedbacks if f.status == 'resolved'),
        "rejected": sum(1 for f in all_feedbacks if f.status == 'rejected'),
    }

    return {
        "success": True,
        "stats": stats
    }
