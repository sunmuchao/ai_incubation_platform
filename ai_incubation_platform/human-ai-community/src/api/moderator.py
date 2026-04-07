"""
版主工具 API 路由

提供 Reddit 风格的版主治理接口：
- 用户注释系统
- 内容相似度检测
- 动态速率限制
- 批量举报处理
"""
from fastapi import APIRouter, HTTPException, Query, Body
from typing import List, Optional
from pydantic import BaseModel, Field

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.member import ReportStatus
from services.moderator_tools import create_moderator_tools
from services.community_service import community_service

router = APIRouter(prefix="/api/moderator", tags=["moderator"])

# 创建版主工具实例
moderator_tools = create_moderator_tools(community_service)


# ==================== 请求模型 ====================

class AddAnnotationRequest(BaseModel):
    """添加用户注释请求"""
    note: str = Field(..., description="注释内容")
    annotation_type: str = Field(default="warning", description="注释类型：warning, ban, spam, abuse, other")
    is_private: bool = Field(default=True, description="是否私有（仅版主可见）")


class UpdateReputationRequest(BaseModel):
    """更新用户信誉请求"""
    action: str = Field(..., description="操作类型：reward_good_post, reward_helpful_comment, penalize_spam, penalize_abuse")


class BatchProcessReportsRequest(BaseModel):
    """批量处理举报请求"""
    report_ids: List[str] = Field(..., description="举报 ID 列表")
    status: str = Field(..., description="处理状态：resolved, dismissed")
    handler_note: str = Field(default="", description="处理备注")


class CheckSimilarityRequest(BaseModel):
    """检查内容相似度请求"""
    content: str = Field(..., description="待检查内容")
    threshold: float = Field(default=0.8, ge=0, le=1, description="相似度阈值")


# ==================== 用户注释系统 ====================

@router.post("/users/{user_id}/annotations")
async def add_user_annotation(
    user_id: str,
    moderator_id: str = Query(..., description="版主 ID"),
    request: AddAnnotationRequest = Body(...)
):
    """
    添加用户注释

    版主可以对用户添加私有注释，用于追踪问题用户行为
    """
    result = moderator_tools.add_user_annotation(
        user_id=user_id,
        moderator_id=moderator_id,
        note=request.note,
        annotation_type=request.annotation_type,
        is_private=request.is_private
    )

    if not result.get("success"):
        raise HTTPException(status_code=403, detail=result.get("error", "操作失败"))

    return result


@router.get("/users/{user_id}/annotations")
async def get_user_annotations(
    user_id: str,
    moderator_id: str = Query(..., description="版主 ID")
):
    """
    获取用户注释列表

    返回用户的所有注释记录及摘要统计
    """
    result = moderator_tools.get_user_annotations(
        user_id=user_id,
        moderator_id=moderator_id
    )

    if not result.get("success"):
        raise HTTPException(status_code=403, detail=result.get("error", "操作失败"))

    return result


# ==================== 内容相似度检测 ====================

@router.post("/content/check-similarity")
async def check_content_similarity(request: CheckSimilarityRequest):
    """
    检查内容相似度

    检测待发布内容是否与已有内容高度相似，防止重复发帖/刷屏
    """
    return moderator_tools.check_content_similarity(
        content=request.content,
        threshold=request.threshold
    )


@router.post("/content/register-similarity")
async def register_content_similarity(
    content: str = Body(...),
    content_id: str = Body(...),
    content_type: str = Body(default="post", description="内容类型：post, comment")
):
    """
    注册内容到相似度检测缓存

    当新内容发布时，调用此接口将其注册到检测缓存中
    """
    from models.member import ContentType

    try:
        ct = ContentType(content_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的内容类型")

    moderator_tools.similarity_checker.register_content(
        content=content,
        content_id=content_id,
        content_type=ct
    )

    return {"success": True, "message": "内容已注册"}


# ==================== 动态速率限制 ====================

@router.get("/rate-limits/{resource}/{user_id}")
async def get_rate_limit_status(resource: str, user_id: str):
    """
    获取用户速率限制状态

    返回基于用户信誉的动态限制信息
    """
    return moderator_tools.get_rate_limit_status(resource, user_id)


@router.post("/users/{user_id}/reputation")
async def update_user_reputation(
    user_id: str,
    moderator_id: str = Query(..., description="版主 ID"),
    request: UpdateReputationRequest = Body(...)
):
    """
    更新用户信誉分数

    版主可以手动调整用户信誉分数，影响其速率限制：
    - reward_good_post: 奖励优质帖子
    - reward_helpful_comment: 奖励有帮助的评论
    - penalize_spam: 惩罚 spam 行为
    - penalize_abuse: 惩罚滥用行为
    """
    result = moderator_tools.update_user_reputation(
        user_id=user_id,
        action=request.action,
        moderator_id=moderator_id
    )

    if not result.get("success"):
        raise HTTPException(status_code=403, detail=result.get("error", "操作失败"))

    return result


@router.get("/reputation/{user_id}")
async def get_user_reputation(user_id: str):
    """获取用户信誉分数"""
    return {
        "user_id": user_id,
        "reputation": moderator_tools.rate_limiter.get_reputation(user_id)
    }


# ==================== 批量举报处理 ====================

@router.get("/reports/high-priority")
async def get_high_priority_reports(limit: int = Query(default=50, ge=1, le=200)):
    """
    获取高优先级举报

    根据举报类型、举报人信誉等因素自动排序优先级
    """
    return moderator_tools.get_high_priority_reports(limit=limit)


@router.post("/reports/batch-process")
async def batch_process_reports(
    handler_id: str = Query(..., description="处理人 ID"),
    request: BatchProcessReportsRequest = Body(...)
):
    """
    批量处理举报

    支持一次性处理多个举报，提高版主效率
    """
    result = moderator_tools.batch_process_reports(
        report_ids=request.report_ids,
        handler_id=handler_id,
        status=request.status,
        handler_note=request.handler_note
    )

    return result


# ==================== 版主仪表盘 ====================

@router.get("/dashboard")
async def get_moderator_dashboard(moderator_id: str = Query(...)):
    """
    获取版主仪表盘数据

    提供版主所需的概览数据：
    - 待处理举报数量
    - 高优先级举报数量
    - 今日审核队列统计
    """
    moderator = community_service.get_member(moderator_id)
    if not moderator or moderator.role not in ["moderator", "admin"]:
        raise HTTPException(status_code=403, detail="权限不足")

    # 获取举报统计
    reports = list(community_service._reports.values())
    pending_reports = [r for r in reports if r.status.value == "pending"]

    # 获取高优先级举报
    high_priority = moderator_tools.get_high_priority_reports(limit=100)

    # 获取审核队列
    review_queue = community_service.get_review_queue()

    return {
        "moderator_id": moderator_id,
        "pending_reports": len(pending_reports),
        "high_priority_reports": len(high_priority.get("reports", [])),
        "review_queue": {
            "pending": review_queue.get("pending_total", 0),
            "flagged": review_queue.get("flagged_total", 0)
        },
        "top_priority_items": high_priority.get("reports", [])[:5]
    }
