"""
新手引导 API 路由 - v1.22 用户体验优化

提供新手引导流程的 API 端点
"""
from fastapi import APIRouter, HTTPException, Query, Body, Depends, Header
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import AsyncSessionLocal
from sqlalchemy.ext.asyncio import AsyncSession
from services.onboarding_service import get_onboarding_service, get_nudge_service

router = APIRouter(prefix="/api/ux/onboarding", tags=["ux-onboarding"])


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

class StepProgressRequest(BaseModel):
    """步骤进度更新请求"""
    step_name: str = Field(..., description="步骤名称（不含 step_前缀）")
    completed: bool = Field(..., description="是否完成")


class NudgeDismissRequest(BaseModel):
    """引导关闭请求"""
    nudge_id: str = Field(..., description="引导 ID")


class NudgeCompleteRequest(BaseModel):
    """引导完成请求"""
    nudge_id: str = Field(..., description="引导 ID")


class OnboardingProgressResponse(BaseModel):
    """新手引导进度响应"""
    success: bool
    progress: Dict[str, Any]
    message: str = ""


class OnboardingChecklistResponse(BaseModel):
    """新手任务清单响应"""
    success: bool
    checklist: Dict[str, Any]


class NudgeListResponse(BaseModel):
    """用户引导列表响应"""
    success: bool
    nudges: List[Dict[str, Any]]


class NudgeActionResponse(BaseModel):
    """引导动作响应"""
    success: bool
    message: str = ""


# ==================== API 端点 ====================

@router.get("", response_model=OnboardingProgressResponse)
async def get_onboarding_progress(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    获取新手引导进度

    返回当前用户的新手引导进度，包括整体进度百分比、各步骤完成状态等。
    如果用户尚未开始引导，将返回初始状态。
    """
    service = get_onboarding_service(db)

    progress = await service.get_or_create_progress(user_id)

    return {
        "success": True,
        "progress": progress.to_dict(),
        "message": "获取新手引导进度成功"
    }


@router.post("/start", response_model=OnboardingProgressResponse)
async def start_onboarding(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    开始新手引导

    初始化新手引导流程，将状态设置为"in_progress"。
    """
    service = get_onboarding_service(db)

    progress = await service.start_onboarding(user_id)

    return {
        "success": True,
        "progress": progress.to_dict(),
        "message": "新手引导已开始"
    }


@router.post("/step", response_model=OnboardingProgressResponse)
async def update_step_progress(
    request: StepProgressRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    更新引导步骤进度

    更新特定步骤的完成状态。
    步骤名称不需要"step_"前缀，例如传入"profile_complete"。
    """
    service = get_onboarding_service(db)

    progress = await service.update_step_progress(
        user_id=user_id,
        step_name=request.step_name,
        completed=request.completed
    )

    return {
        "success": True,
        "progress": progress.to_dict(),
        "message": f"步骤 {request.step_name} 已标记为{'完成' if request.completed else '未完成'}"
    }


@router.post("/complete", response_model=OnboardingProgressResponse)
async def complete_onboarding(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    完成新手引导

    将新手引导状态标记为"completed"，设置整体进度为 100%。
    """
    service = get_onboarding_service(db)

    progress = await service.complete_onboarding(user_id)

    return {
        "success": True,
        "progress": progress.to_dict(),
        "message": "恭喜！新手引导已完成"
    }


@router.post("/skip", response_model=OnboardingProgressResponse)
async def skip_onboarding(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    跳过新手引导

    允许用户跳过新手引导流程。
    跳过后的用户仍可在后续通过任务清单完成引导步骤。
    """
    service = get_onboarding_service(db)

    progress = await service.skip_onboarding(user_id)

    return {
        "success": True,
        "progress": progress.to_dict(),
        "message": "新手引导已跳过，您仍可在设置中查看任务清单"
    }


@router.get("/checklist", response_model=OnboardingChecklistResponse)
async def get_onboarding_checklist(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    获取新手任务清单

    返回完整的新手任务清单，包括各步骤的详细说明、教程链接、奖励等。
    用于前端展示新手引导界面。
    """
    service = get_onboarding_service(db)

    checklist = await service.get_onboarding_checklist(user_id)

    return {
        "success": True,
        "checklist": checklist
    }


@router.get("/tips/{step_key}")
async def get_step_tips(
    step_key: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    获取步骤提示信息

    返回特定步骤的详细引导内容，包括教程文本、视频教程链接等。
    """
    service = get_onboarding_service(db)

    tips = await service.get_step_tips(user_id, step_key)

    if not tips:
        raise HTTPException(status_code=404, detail="步骤不存在或未激活")

    return {
        "success": True,
        "tips": tips
    }


# ==================== 用户引导 API ====================

@router.get("/nudges", response_model=NudgeListResponse)
async def get_active_nudges(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    获取活跃的用户引导

    返回当前用户待展示的所有引导消息。
    引导用于在合适的时机向用户推荐功能或提示操作。
    """
    service = get_nudge_service(db)

    nudges = await service.get_active_nudges(user_id)

    return {
        "success": True,
        "nudges": [n.to_dict() for n in nudges]
    }


@router.post("/nudges/dismiss", response_model=NudgeActionResponse)
async def dismiss_nudge(
    request: NudgeDismissRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    关闭用户引导

    用户手动关闭引导消息，后续不再展示。
    """
    service = get_nudge_service(db)

    success = await service.dismiss_nudge(request.nudge_id)

    if not success:
        raise HTTPException(status_code=404, detail="引导不存在")

    return {
        "success": True,
        "message": "引导已关闭"
    }


@router.post("/nudges/complete", response_model=NudgeActionResponse)
async def complete_nudge(
    request: NudgeCompleteRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    完成用户引导

    用户完成了引导推荐的操作，标记引导为已完成。
    """
    service = get_nudge_service(db)

    success = await service.complete_nudge(request.nudge_id)

    if not success:
        raise HTTPException(status_code=404, detail="引导不存在")

    return {
        "success": True,
        "message": "引导已完成"
    }


@router.get("/nudges/check/{nudge_type}")
async def check_nudge_availability(
    nudge_type: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    检查引导是否可展示

    判断是否应该向用户展示指定类型的引导。
    """
    service = get_nudge_service(db)

    should_show = await service.should_show_nudge(user_id, nudge_type)

    return {
        "success": True,
        "should_show": should_show,
        "nudge_type": nudge_type
    }
