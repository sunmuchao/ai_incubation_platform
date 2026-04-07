"""
AI 任务分解 API。

提供任务智能分解、子任务管理、结果聚合等功能。
"""
from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from models.task_decomposition import (
    DecompositionRequest,
    DecompositionResponse,
    DecompositionStrategy,
    SubTask,
    SubTaskAcceptBody,
    SubTaskCompleteBody,
    SubTaskStatus,
    SubTaskSubmitBody,
    TaskDecomposition,
)
from services.task_decomposition_service import task_decomposition_service
from services.task_service import task_service
from database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/task-decomposition", tags=["task_decomposition"])


@router.post("/decompose", response_model=DecompositionResponse)
async def decompose_task(request: DecompositionRequest):
    """
    将复杂任务智能分解为多个子任务。

    支持以下分解策略：
    - sequential: 顺序分解，子任务按顺序执行
    - parallel: 并行分解，子任务可并行执行
    - dependency_based: 基于依赖关系的分解
    - hierarchical: 分层分解，多级子任务

    系统会自动分析任务特征，匹配合适的分解模板（如调研、拍照、文档审核等）。
    """
    # 获取原始任务信息（使用内存服务）
    task = task_service.get_task(request.task_id)

    if not task:
        raise HTTPException(status_code=404, detail=f"Task not found: {request.task_id}")

    # 执行任务分解
    response = task_decomposition_service.decompose_task(
        request=request,
        task_title=task.title,
        task_description=task.description,
        acceptance_criteria=task.acceptance_criteria,
    )

    if not response.success:
        raise HTTPException(status_code=400, detail=response.message)

    return response


@router.get("/decomposition/{decomposition_id}", response_model=TaskDecomposition)
async def get_decomposition(decomposition_id: str):
    """获取任务分解记录详情。"""
    decomposition = task_decomposition_service.get_decomposition(decomposition_id)
    if not decomposition:
        raise HTTPException(status_code=404, detail="Decomposition not found")
    return decomposition


@router.get("/task/{task_id}/decomposition")
async def get_decomposition_by_task(task_id: str):
    """通过任务 ID 获取分解记录。"""
    decomposition = task_decomposition_service.get_decomposition_by_task_id(task_id)
    if not decomposition:
        raise HTTPException(status_code=404, detail="No decomposition found for this task")
    return decomposition


@router.get("/subtask/{sub_task_id}", response_model=SubTask)
async def get_sub_task(sub_task_id: str):
    """获取子任务详情。"""
    sub_task = task_decomposition_service.get_sub_task(sub_task_id)
    if not sub_task:
        raise HTTPException(status_code=404, detail="SubTask not found")
    return sub_task


@router.get("/task/{task_id}/subtasks", response_model=List[SubTask])
async def get_sub_tasks_by_task(task_id: str):
    """获取任务下的所有子任务。"""
    sub_tasks = task_decomposition_service.get_sub_tasks_by_parent_id(task_id)
    return sub_tasks


@router.post("/subtask/{sub_task_id}/accept")
async def accept_sub_task(sub_task_id: str, body: SubTaskAcceptBody):
    """工人接单子任务。"""
    sub_task = task_decomposition_service.get_sub_task(sub_task_id)
    if not sub_task:
        raise HTTPException(status_code=404, detail="SubTask not found")

    if sub_task.status != SubTaskStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"SubTask is not available for acceptance. Current status: {sub_task.status}"
        )

    success = task_decomposition_service.accept_sub_task(sub_task_id, body.worker_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to accept subtask")

    return {"message": "SubTask accepted", "sub_task_id": sub_task_id, "worker_id": body.worker_id}


@router.post("/subtask/{sub_task_id}/submit")
async def submit_sub_task(sub_task_id: str, body: SubTaskSubmitBody):
    """提交子任务交付物。"""
    sub_task = task_decomposition_service.get_sub_task(sub_task_id)
    if not sub_task:
        raise HTTPException(status_code=404, detail="SubTask not found")

    success = task_decomposition_service.submit_sub_task(
        sub_task_id,
        body.worker_id,
        body.content,
        body.attachments,
    )
    if not success:
        raise HTTPException(status_code=400, detail="Failed to submit subtask")

    return {"message": "SubTask submitted", "sub_task_id": sub_task_id}


@router.post("/subtask/{sub_task_id}/complete")
async def complete_sub_task(sub_task_id: str, body: SubTaskCompleteBody):
    """验收子任务。"""
    sub_task = task_decomposition_service.get_sub_task(sub_task_id)
    if not sub_task:
        raise HTTPException(status_code=404, detail="SubTask not found")

    success = task_decomposition_service.complete_sub_task(sub_task_id, body.approved)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to complete subtask")

    status = "completed" if body.approved else "returned"
    return {
        "message": "SubTask completed",
        "sub_task_id": sub_task_id,
        "status": status,
        "reason": body.reason or "",
    }


@router.post("/decomposition/{decomposition_id}/aggregate")
async def aggregate_results(decomposition_id: str):
    """
    聚合子任务结果生成最终交付物。

    当所有子任务完成后，调用此接口聚合结果。
    """
    decomposition = task_decomposition_service.get_decomposition(decomposition_id)
    if not decomposition:
        raise HTTPException(status_code=404, detail="Decomposition not found")

    aggregated = task_decomposition_service.aggregate_results(decomposition_id)
    if not aggregated:
        raise HTTPException(
            status_code=400,
            detail="No results to aggregate. Ensure all subtasks are completed."
        )

    return {
        "decomposition_id": decomposition_id,
        "aggregated_result": aggregated,
        "completed_count": decomposition.completed_count,
        "total_count": decomposition.total_sub_tasks,
    }


@router.get("/analysis")
async def analyze_task_prospective(task_title: str, task_description: str):
    """
    预分析任务特征（不执行实际分解）。

    用于评估任务是否适合分解，以及建议使用哪种分解策略。
    """
    analysis = task_decomposition_service.analyze_task(task_title, task_description)
    return {
        "matched_template": analysis["matched_template"],
        "confidence": analysis["confidence"],
        "suggested_strategy": analysis["suggested_strategy"].value,
        "estimated_complexity": analysis["estimated_complexity"],
        "is_suitable_for_decomposition": analysis["confidence"] >= 0.5,
    }


@router.get("/strategies")
async def list_decomposition_strategies():
    """获取所有可用的分解策略。"""
    return {
        "strategies": [
            {
                "name": strategy.value,
                "description": _get_strategy_description(strategy),
            }
            for strategy in DecompositionStrategy
        ]
    }


def _get_strategy_description(strategy: DecompositionStrategy) -> str:
    """获取策略描述。"""
    descriptions = {
        DecompositionStrategy.SEQUENTIAL: "顺序分解，子任务按顺序依次执行，前一个任务完成后一个才能开始",
        DecompositionStrategy.PARALLEL: "并行分解，子任务可以并行执行，无依赖关系",
        DecompositionStrategy.DEPENDENCY_BASED: "基于依赖关系的分解，子任务之间存在复杂的依赖关系网络",
        DecompositionStrategy.HIERARCHICAL: "分层分解，支持多级子任务嵌套，适合超复杂任务",
    }
    return descriptions.get(strategy, "未知策略")
