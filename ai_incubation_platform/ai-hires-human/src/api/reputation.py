"""
信誉体系 API。

提供工人和雇主的信誉查询、评分记录、排行榜等功能。
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from services.reputation_service import (
    ReputationLevel,
    reputation_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reputation", tags=["信誉体系"])


# ============ 请求/响应模型 ============

class ReputationSummaryResponse(BaseModel):
    """信誉摘要响应。"""
    user_id: str
    user_type: str
    score: float
    level: str
    total_tasks: int
    completed_tasks: int
    completion_rate: float
    on_time_delivery_rate: float
    average_rating: float
    can_accept_tasks: bool
    recent_events: list = Field(default_factory=list)


class ReputationEventRequest(BaseModel):
    """添加信誉事件请求。"""
    event_type: str = Field(..., description="事件类型")
    task_id: Optional[str] = Field(None, description="相关任务 ID")
    description: Optional[str] = Field(None, description="事件描述")


class TaskCompletionRequest(BaseModel):
    """任务完成事件请求。"""
    user_id: str
    user_type: str
    task_id: str
    rating: Optional[float] = Field(None, ge=1.0, le=5.0, description="评分")
    on_time: bool = True


class TaskCancelRequest(BaseModel):
    """任务取消事件请求。"""
    user_id: str
    user_type: str
    task_id: str
    reason: Optional[str] = None


class DisputeResultRequest(BaseModel):
    """争议结果请求。"""
    user_id: str
    user_type: str
    task_id: str
    won: bool


class CheatingReportRequest(BaseModel):
    """作弊举报请求。"""
    user_id: str
    user_type: str
    task_id: str
    reason: str


class LeaderboardItem(BaseModel):
    """排行榜项。"""
    rank: int
    user_id: str
    score: float
    level: str
    completed_tasks: int


class LeaderboardResponse(BaseModel):
    """排行榜响应。"""
    items: list = Field(default_factory=list)
    total: int


class ComprehensiveScoreResponse(BaseModel):
    """综合信誉分数响应。"""
    user_id: str
    comprehensive_score: float
    level: str
    breakdown: dict
    weights: dict


class DepositCalculationRequest(BaseModel):
    """保证金计算请求。"""
    user_id: str
    base_amount: float


class DepositCalculationResponse(BaseModel):
    """保证金计算响应。"""
    user_id: str
    base_amount: float
    required_deposit: float
    deposit_rate: float
    reputation_level: str


# ============ API 端点 ============

@router.get("/{user_id}", response_model=ReputationSummaryResponse)
async def get_reputation(
    user_id: str,
):
    """
    获取用户信誉摘要。

    返回用户的信誉分数、等级、任务统计和最近事件。
    """
    summary = reputation_service.get_reputation_summary(user_id)
    if not summary:
        # 返回默认的空记录
        return ReputationSummaryResponse(
            user_id=user_id,
            user_type="unknown",
            score=50.0,
            level="silver",
            total_tasks=0,
            completed_tasks=0,
            completion_rate=0.0,
            on_time_delivery_rate=100.0,
            average_rating=5.0,
            can_accept_tasks=True,
            recent_events=[],
        )
    return ReputationSummaryResponse(**summary)


@router.get("/{user_id}/comprehensive", response_model=ComprehensiveScoreResponse)
async def get_comprehensive_score(user_id: str):
    """
    获取用户综合信誉分数。

    综合考虑基础分数、完成率、准时交付率、评分和争议率等多个维度。
    """
    result = reputation_service.calculate_comprehensive_score(user_id)
    if not result:
        raise HTTPException(status_code=404, detail="用户信誉记录不存在")
    return ComprehensiveScoreResponse(**result)


@router.post("/event")
async def add_reputation_event(request: ReputationEventRequest):
    """
    手动添加信誉事件。

    事件类型包括：
    - TASK_COMPLETED: 完成任务 (+5)
    - TASK_CANCELLED: 取消任务 (-3)
    - TASK_DISPUTE_LOST: 争议败诉 (-10)
    - TASK_DISPUTE_WON: 争议胜诉 (+3)
    - LATE_DELIVERY: 逾期交付 (-5)
    - EARLY_DELIVERY: 提前交付 (+2)
    - HIGH_RATING: 获得好评 (+3)
    - LOW_RATING: 获得差评 (-5)
    - CHEATING_DETECTED: 作弊 detected (-20)
    - FIRST_TASK: 首次完成任务 (+5)
    """
    # 需要 user_id 参数
    raise HTTPException(
        status_code=400,
        detail="请使用具体的用户端点，如 POST /api/reputation/{user_id}/event"
    )


@router.post("/{user_id}/event")
async def add_user_reputation_event(
    user_id: str,
    request: ReputationEventRequest,
):
    """为特定用户添加信誉事件。"""
    record = reputation_service.add_event(
        user_id=user_id,
        event_type=request.event_type,
        task_id=request.task_id,
        description=request.description,
    )
    if not record:
        raise HTTPException(status_code=404, detail="用户信誉记录不存在")

    return {
        "message": "信誉事件已记录",
        "user_id": user_id,
        "event_type": request.event_type,
        "score_delta": reputation_service._event_types.get(request.event_type, {}).get("score_delta", 0),
        "new_score": record.score,
        "new_level": record.level.value,
    }


@router.post("/task/completed")
async def record_task_completed(request: TaskCompletionRequest):
    """
    记录任务完成事件。

    自动更新：
    - 完成任务数 +1
    - 基础信誉分 +5
    - 首次完成额外 +5
    - 根据准时情况 +/- 分
    - 根据评分 +/- 分
    """
    record = reputation_service.record_task_completed(
        user_id=request.user_id,
        user_type=request.user_type,
        task_id=request.task_id,
        rating=request.rating,
        on_time=request.on_time,
    )
    if not record:
        raise HTTPException(status_code=500, detail="记录任务完成失败")

    return {
        "message": "任务完成已记录",
        "user_id": request.user_id,
        "new_score": record.score,
        "new_level": record.level.value,
        "completed_tasks": record.completed_tasks,
    }


@router.post("/task/cancelled")
async def record_task_cancelled(request: TaskCancelRequest):
    """记录任务取消事件。"""
    record = reputation_service.record_task_cancelled(
        user_id=request.user_id,
        user_type=request.user_type,
        task_id=request.task_id,
        reason=request.reason,
    )
    if not record:
        raise HTTPException(status_code=500, detail="记录任务取消失败")

    return {
        "message": "任务取消已记录",
        "user_id": request.user_id,
        "new_score": record.score,
        "cancelled_tasks": record.cancelled_tasks,
    }


@router.post("/dispute/result")
async def record_dispute_result(request: DisputeResultRequest):
    """记录争议结果。"""
    record = reputation_service.record_dispute_result(
        user_id=request.user_id,
        user_type=request.user_type,
        task_id=request.task_id,
        won=request.won,
    )
    if not record:
        raise HTTPException(status_code=500, detail="记录争议结果失败")

    return {
        "message": "争议结果已记录",
        "user_id": request.user_id,
        "new_score": record.score,
        "disputed_tasks": record.disputed_tasks,
    }


@router.post("/cheating/report")
async def report_cheating(request: CheatingReportRequest):
    """
    举报作弊行为。

    作弊将导致信誉分大幅降低（-20 分）。
    """
    record = reputation_service.record_cheating(
        user_id=request.user_id,
        user_type=request.user_type,
        task_id=request.task_id,
        reason=request.reason,
    )
    if not record:
        raise HTTPException(status_code=500, detail="记录作弊行为失败")

    return {
        "message": "作弊行为已记录",
        "user_id": request.user_id,
        "new_score": record.score,
        "new_level": record.level.value,
    }


@router.get("/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard(
    user_type: Optional[str] = Query(None, description="用户类型：worker 或 employer"),
    limit: int = Query(10, ge=1, le=100, description="返回数量限制"),
):
    """
    获取信誉排行榜。

    可按用户类型筛选，默认返回前 10 名。
    """
    items = reputation_service.get_leaderboard(user_type=user_type, limit=limit)
    return LeaderboardResponse(
        items=items,
        total=len(items),
    )


@router.post("/deposit/calculate", response_model=DepositCalculationResponse)
async def calculate_deposit(request: DepositCalculationRequest):
    """
    计算需要缴纳的保证金。

    根据用户信誉等级确定保证金比例：
    - 钻石：0% (免保证金)
    - 白金：5%
    - 黄金：10%
    - 白银：20%
    - 青铜：30%
    """
    record = reputation_service.get_or_create_record(request.user_id, "worker")
    required_deposit = record.get_required_deposit(request.base_amount)
    deposit_rate = required_deposit / request.base_amount if request.base_amount > 0 else 0

    return DepositCalculationResponse(
        user_id=request.user_id,
        base_amount=request.base_amount,
        required_deposit=required_deposit,
        deposit_rate=deposit_rate,
        reputation_level=record.level.value,
    )


@router.get("/{user_id}/can-access")
async def check_access(
    user_id: str,
    min_reputation: float = Query(0, ge=0, le=100, description="最低信誉要求"),
):
    """
    检查用户是否可以接受任务。

    用于任务准入门槛控制。
    """
    record = reputation_service.get_or_create_record(user_id, "worker")
    can_access = record.can_accept_task(min_reputation)

    return {
        "user_id": user_id,
        "can_access": can_access,
        "current_score": record.score,
        "required_score": min_reputation,
        "level": record.level.value,
    }


@router.get("/{user_id}/events")
async def get_user_events(
    user_id: str,
    limit: int = Query(20, ge=1, le=100, description="返回事件数量限制"),
):
    """获取用户的信誉事件历史。"""
    record = reputation_service._records.get(user_id)
    if not record:
        return {"user_id": user_id, "events": [], "total": 0}

    events = record.events[-limit:]
    return {
        "user_id": user_id,
        "events": events,
        "total": len(record.events),
    }
