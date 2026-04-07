"""
P7 训练效果评估 API

提供：
- 任务完成率统计
- 准确率评估
- 用户反馈整合
- AI 能力评分模型
"""
from fastapi import APIRouter, HTTPException, Query, Body
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import uuid

router = APIRouter(prefix="/api/training-effectiveness", tags=["P7-训练效果评估"])

# 导入服务
from services.training_effectiveness_service import (
    training_effectiveness_service, TaskStatus, FeedbackType
)


# ==================== 请求/响应模型 ====================

class TaskRecordCreate(BaseModel):
    """创建任务记录"""
    employee_id: str
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    task_type: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = "pending"
    metrics: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class TaskStatusUpdate(BaseModel):
    """更新任务状态"""
    status: str  # pending, in_progress, completed, failed, cancelled
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class FeedbackCreate(BaseModel):
    """创建用户反馈"""
    employee_id: str
    user_id: str
    tenant_id: Optional[str] = None
    task_id: Optional[str] = None
    feedback_type: str  # rating, comment, bug_report, feature_request
    rating: Optional[int] = Field(None, ge=1, le=5)
    comment: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None


class CapabilityScoreResponse(BaseModel):
    """能力评分响应"""
    capability_name: str
    score: float
    confidence: float
    sample_size: int
    trend: str


class EvaluationResponse(BaseModel):
    """训练效果评估响应"""
    employee_id: str
    evaluation_period: str
    summary: Dict[str, Any]
    capability_breakdown: List[Dict[str, Any]]
    insights: Dict[str, Any]


# ==================== 任务记录管理端点 ====================

@router.post("/tasks", response_model=Dict[str, Any])
async def create_task_record(task: TaskRecordCreate):
    """
    创建任务记录

    用于追踪 AI 员工的任务执行情况
    """
    data = task.model_dump()
    task_record = training_effectiveness_service.record_task(data)

    return {
        "message": "任务记录创建成功",
        "task_id": task_record.id,
        "status": task_record.status.value
    }


@router.put("/tasks/{task_id}/status")
async def update_task_status(task_id: str, update: TaskStatusUpdate):
    """
    更新任务状态

    当任务状态变化时调用此接口
    """
    try:
        status = TaskStatus(update.status)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的状态值")

    training_effectiveness_service.update_task_status(
        task_id, status, update.result, update.error_message
    )

    return {
        "message": "任务状态更新成功",
        "task_id": task_id,
        "new_status": update.status
    }


@router.get("/employees/{employee_id}/tasks")
async def get_employee_tasks(
    employee_id: str,
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    status: Optional[str] = Query(None, description="任务状态过滤")
):
    """
    获取员工的任务记录列表
    """
    # 解析日期
    start_dt = None
    end_dt = None

    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="日期格式错误，应为 YYYY-MM-DD")

    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="日期格式错误，应为 YYYY-MM-DD")

    tasks = training_effectiveness_service.get_employee_tasks(employee_id, start_dt, end_dt)

    # 状态过滤
    if status:
        try:
            status_enum = TaskStatus(status)
            tasks = [t for t in tasks if t.status == status_enum]
        except ValueError:
            pass

    return {
        "employee_id": employee_id,
        "total": len(tasks),
        "tasks": [
            {
                "id": t.id,
                "task_type": t.task_type,
                "description": t.description[:100] if t.description else "",
                "status": t.status.value,
                "created_at": t.created_at.isoformat(),
                "completed_at": t.completed_at.isoformat() if t.completed_at else None,
                "metrics": t.metrics
            }
            for t in tasks
        ]
    }


# ==================== 用户反馈管理端点 ====================

@router.post("/feedback", response_model=Dict[str, Any])
async def submit_feedback(feedback: FeedbackCreate):
    """
    提交用户反馈

    用户可以对 AI 员工的表现进行评价和反馈
    """
    data = feedback.model_dump()
    feedback_record = training_effectiveness_service.submit_feedback(data)

    return {
        "message": "反馈提交成功",
        "feedback_id": feedback_record.id,
        "rating": feedback_record.rating
    }


@router.get("/employees/{employee_id}/feedback")
async def get_employee_feedback(
    employee_id: str,
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)")
):
    """
    获取员工的用户反馈列表
    """
    start_dt = None
    end_dt = None

    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="日期格式错误")

    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="日期格式错误")

    feedbacks = training_effectiveness_service.get_employee_feedback(employee_id, start_dt, end_dt)

    return {
        "employee_id": employee_id,
        "total": len(feedbacks),
        "feedbacks": [
            {
                "id": f.id,
                "feedback_type": f.feedback_type.value,
                "rating": f.rating,
                "comment": f.comment,
                "tags": f.tags,
                "created_at": f.created_at.isoformat()
            }
            for f in feedbacks
        ]
    }


# ==================== 统计分析端点 ====================

@router.get("/employees/{employee_id}/completion-rate")
async def get_completion_rate(
    employee_id: str,
    period: Optional[str] = Query("last_30_days", description="统计周期")
):
    """
    获取任务完成率统计

    周期选项：last_7_days, last_30_days, last_90_days, all_time
    """
    end_date = datetime.now()
    if period == "last_7_days":
        start_date = end_date - timedelta(days=7)
    elif period == "last_30_days":
        start_date = end_date - timedelta(days=30)
    elif period == "last_90_days":
        start_date = end_date - timedelta(days=90)
    else:
        start_date = None

    stats = training_effectiveness_service.calculate_completion_rate(
        employee_id, start_date, end_date
    )

    return {
        "employee_id": employee_id,
        "period": period,
        "statistics": stats
    }


@router.get("/employees/{employee_id}/accuracy-rate")
async def get_accuracy_rate(
    employee_id: str,
    period: Optional[str] = Query("last_30_days", description="统计周期")
):
    """
    获取准确率统计

    基于任务执行结果的质量评估
    """
    end_date = datetime.now()
    if period == "last_7_days":
        start_date = end_date - timedelta(days=7)
    elif period == "last_30_days":
        start_date = end_date - timedelta(days=30)
    elif period == "last_90_days":
        start_date = end_date - timedelta(days=90)
    else:
        start_date = None

    stats = training_effectiveness_service.calculate_accuracy_rate(
        employee_id, start_date, end_date
    )

    return {
        "employee_id": employee_id,
        "period": period,
        "statistics": stats
    }


@router.get("/employees/{employee_id}/feedback-analysis")
async def get_feedback_analysis(
    employee_id: str,
    period: Optional[str] = Query("last_30_days", description="统计周期")
):
    """
    获取用户反馈分析

    包括平均评分、情感分析、常见标签等
    """
    end_date = datetime.now()
    if period == "last_7_days":
        start_date = end_date - timedelta(days=7)
    elif period == "last_30_days":
        start_date = end_date - timedelta(days=30)
    elif period == "last_90_days":
        start_date = end_date - timedelta(days=90)
    else:
        start_date = None

    analysis = training_effectiveness_service.analyze_feedback(
        employee_id, start_date, end_date
    )

    return {
        "employee_id": employee_id,
        "period": period,
        "analysis": analysis
    }


# ==================== 能力评估端点 ====================

@router.get("/employees/{employee_id}/capability-scores")
async def get_capability_scores(employee_id: str):
    """
    获取能力评分

    返回各维度的能力评分、置信度和趋势
    """
    scores = training_effectiveness_service.calculate_capability_scores(employee_id)

    return {
        "employee_id": employee_id,
        "capability_scores": [
            {
                "capability_name": cs.capability_name,
                "score": cs.score,
                "confidence": cs.confidence,
                "sample_size": cs.sample_size,
                "trend": cs.trend,
                "last_updated": cs.last_updated.isoformat()
            }
            for cs in scores
        ]
    }


@router.get("/employees/{employee_id}/evaluation")
async def evaluate_training_effectiveness(
    employee_id: str,
    period: Optional[str] = Query("last_30_days", description="评估周期")
):
    """
    综合训练效果评估

    生成包含任务完成率、准确率、用户反馈和能力评分的综合评估报告
    """
    evaluation = training_effectiveness_service.evaluate_training_effectiveness(
        employee_id, period
    )

    return {
        "employee_id": employee_id,
        "period": period,
        "evaluation": {
            "summary": {
                "overall_score": evaluation.overall_score,
                "overall_level": evaluation.overall_level,
                "total_tasks": evaluation.total_tasks,
                "completed_tasks": evaluation.completed_tasks,
                "completion_rate": evaluation.completion_rate,
                "accuracy_rate": evaluation.accuracy_rate,
                "average_rating": evaluation.average_rating,
                "positive_feedback_rate": evaluation.positive_feedback_rate
            },
            "capability_scores": [
                {
                    "capability_name": cs.capability_name,
                    "score": cs.score,
                    "trend": cs.trend
                }
                for cs in evaluation.capability_scores
            ],
            "insights": {
                "strengths": evaluation.strengths,
                "areas_for_improvement": evaluation.areas_for_improvement,
                "recommended_training": evaluation.recommended_training
            }
        }
    }


@router.get("/employees/{employee_id}/report")
async def generate_report(
    employee_id: str,
    period: Optional[str] = Query("last_30_days", description="报告周期")
):
    """
    生成训练效果评估报告

    完整的评估报告，可用于导出和分享
    """
    report = training_effectiveness_service.generate_report(employee_id, period)

    return {
        "report": report
    }


# ==================== 批量统计端点 ====================

@router.get("/tenants/{tenant_id}/overview")
async def get_tenant_overview(
    tenant_id: str,
    period: Optional[str] = Query("last_30_days", description="统计周期")
):
    """
    获取租户下所有员工的训练效果概览
    """
    end_date = datetime.now()
    if period == "last_7_days":
        start_date = end_date - timedelta(days=7)
    elif period == "last_30_days":
        start_date = end_date - timedelta(days=30)
    elif period == "last_90_days":
        start_date = end_date - timedelta(days=90)
    else:
        start_date = None

    # 获取租户下所有任务
    all_tasks = list(training_effectiveness_service._tasks.values())
    tenant_tasks = [t for t in all_tasks if t.tenant_id == tenant_id]

    if start_date:
        tenant_tasks = [t for t in tenant_tasks if t.created_at >= start_date]
    if end_date:
        tenant_tasks = [t for t in tenant_tasks if t.created_at <= end_date]

    # 按员工分组统计
    employee_stats = {}
    for task in tenant_tasks:
        if task.employee_id not in employee_stats:
            employee_stats[task.employee_id] = {
                "total": 0,
                "completed": 0,
                "failed": 0
            }
        employee_stats[task.employee_id]["total"] += 1
        if task.status == TaskStatus.COMPLETED:
            employee_stats[task.employee_id]["completed"] += 1
        elif task.status == TaskStatus.FAILED:
            employee_stats[task.employee_id]["failed"] += 1

    # 计算整体统计
    total_tasks = len(tenant_tasks)
    completed_tasks = sum(1 for t in tenant_tasks if t.status == TaskStatus.COMPLETED)
    failed_tasks = sum(1 for t in tenant_tasks if t.status == TaskStatus.FAILED)

    return {
        "tenant_id": tenant_id,
        "period": period,
        "overview": {
            "total_employees": len(employee_stats),
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "overall_completion_rate": round(completed_tasks / total_tasks * 100, 2) if total_tasks > 0 else 0
        },
        "employee_summary": [
            {
                "employee_id": emp_id,
                "total_tasks": stats["total"],
                "completion_rate": round(stats["completed"] / stats["total"] * 100, 2) if stats["total"] > 0 else 0
            }
            for emp_id, stats in employee_stats.items()
        ]
    }


# ==================== 健康检查 ====================

@router.get("/health")
async def health_check():
    """
    训练效果评估服务健康检查
    """
    return {
        "status": "healthy",
        "service": "training_effectiveness_service",
        "version": "v1.0",
        "total_tasks": len(training_effectiveness_service._tasks),
        "total_feedbacks": len(training_effectiveness_service._feedbacks),
        "total_evaluations": len(training_effectiveness_service._evaluations)
    }
