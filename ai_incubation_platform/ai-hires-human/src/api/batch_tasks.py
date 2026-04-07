"""
批量任务管理 API — CSV 导入、批量分发、批量验收。
"""
from __future__ import annotations

import csv
import io
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.task import InteractionType, Task, TaskCreate, TaskPriority, TaskStatus
from services.batch_task_service import batch_task_service

router = APIRouter(prefix="/api/batch-tasks", tags=["batch-tasks"])


class BatchTaskCreateResponse(BaseModel):
    """批量创建任务响应。"""
    total: int
    success_count: int
    failed_count: int
    task_ids: List[str]
    errors: List[Dict[str, Any]] = Field(default_factory=list)


class BatchTaskStatus(BaseModel):
    """批量任务状态。"""
    batch_id: str
    total_tasks: int
    status_counts: Dict[str, int]
    created_at: datetime
    completed_at: Optional[datetime] = None


class BatchAcceptRequest(BaseModel):
    """批量接单请求。"""
    worker_id: str
    task_ids: List[str]


class BatchAcceptResponse(BaseModel):
    """批量接单响应。"""
    success_count: int
    failed_count: int
    results: List[Dict[str, Any]]


class BatchCompleteRequest(BaseModel):
    """批量验收请求。"""
    ai_employer_id: str
    task_ids: List[str]
    approved: bool


class BatchCompleteResponse(BaseModel):
    """批量验收响应。"""
    success_count: int
    failed_count: int
    results: List[Dict[str, Any]]


@router.post("/import", response_model=BatchTaskCreateResponse)
async def import_tasks_from_csv(
    file: UploadFile = File(..., description="CSV 文件"),
    ai_employer_id: str = Form(..., description="AI 雇主 ID"),
    default_interaction_type: InteractionType = Form(InteractionType.DIGITAL, description="默认交互类型"),
    default_priority: TaskPriority = Form(TaskPriority.MEDIUM, description="默认优先级"),
):
    """
    从 CSV 文件批量导入任务。

    CSV 格式要求：
    - title: 任务标题（必填）
    - description: 任务描述（必填）
    - capability_gap: AI 能力缺口说明（必填）
    - acceptance_criteria: 验收标准（JSON 数组或分号分隔）
    - requirements: 任务要求（JSON 数组或分号分隔）
    - required_skills: 所需技能（JSON 对象或 key=value 分号分隔）
    - location_hint: 地点提示（可选）
    - reward_amount: 报酬金额（可选，默认 0）
    - deadline: 截止时间（可选，ISO 8601 格式）
    - callback_url: 回调 URL（可选）
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing file")

    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be CSV format")

    try:
        content = await file.read()
        csv_content = content.decode('utf-8')
        return batch_task_service.import_tasks_from_csv(
            csv_content=csv_content,
            ai_employer_id=ai_employer_id,
            default_interaction_type=default_interaction_type,
            default_priority=default_priority,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.post("/create-batch", response_model=BatchTaskCreateResponse)
async def create_task_batch(
    tasks: List[TaskCreate],
    template_name: Optional[str] = Form(None, description="任务模板名称"),
):
    """
    批量创建任务（支持任务模板）。

    请求体为 TaskCreate 数组，可选指定模板名称用于后续追踪。
    """
    return batch_task_service.create_task_batch(
        tasks=tasks,
        template_name=template_name,
    )


@router.get("/batches/{batch_id}", response_model=BatchTaskStatus)
async def get_batch_status(batch_id: str):
    """获取批量任务的状态统计。"""
    status = batch_task_service.get_batch_status(batch_id)
    if not status:
        raise HTTPException(status_code=404, detail="Batch not found")
    return status


@router.post("/batch-accept", response_model=BatchAcceptResponse)
async def batch_accept_tasks(request: BatchAcceptRequest):
    """
    批量接单。

    工人一次性接收多个任务（需确保任务状态为 published）。
    """
    results = batch_task_service.batch_accept_tasks(
        worker_id=request.worker_id,
        task_ids=request.task_ids,
    )
    success_count = sum(1 for r in results if r.get('success', False))
    failed_count = len(results) - success_count
    return BatchAcceptResponse(
        success_count=success_count,
        failed_count=failed_count,
        results=results,
    )


@router.post("/batch-submit", response_model=BatchTaskCreateResponse)
async def batch_submit_work(
    worker_id: str = Form(...),
    task_ids: List[str] = Form(...),
    contents: List[str] = Form(...),
    attachments_list: List[str] = Form(default=[], description="JSON 数组的附件列表"),
):
    """
    批量提交工作。

    每个任务对应一个 content，attachments 为可选的 JSON 数组。
    """
    import json
    results = []
    errors = []

    if len(task_ids) != len(contents):
        raise HTTPException(status_code=400, detail="task_ids and contents must have same length")

    for i, task_id in enumerate(task_ids):
        try:
            content = contents[i]
            attachments = json.loads(attachments_list[i]) if i < len(attachments_list) and attachments_list[i] else []
            ok = batch_task_service.submit_work(task_id, worker_id, content, attachments)
            if ok:
                results.append({"task_id": task_id, "success": True})
            else:
                errors.append({"task_id": task_id, "error": "Submit failed"})
        except Exception as e:
            errors.append({"task_id": task_id, "error": str(e)})

    return BatchTaskCreateResponse(
        total=len(task_ids),
        success_count=len(results),
        failed_count=len(errors),
        task_ids=[r["task_id"] for r in results],
        errors=errors,
    )


@router.post("/batch-complete", response_model=BatchCompleteResponse)
async def batch_complete_tasks(
    request: BatchCompleteRequest,
    background_tasks: BackgroundTasks,
):
    """
    批量验收任务。

    AI 雇主一次性验收多个任务（通过或不通过）。
    """
    results = batch_task_service.batch_complete_tasks(
        ai_employer_id=request.ai_employer_id,
        task_ids=request.task_ids,
        approved=request.approved,
        background_tasks=background_tasks,
    )
    success_count = sum(1 for r in results if r.get('success', False))
    failed_count = len(results) - success_count
    return BatchCompleteResponse(
        success_count=success_count,
        failed_count=failed_count,
        results=results,
    )


@router.get("/templates", response_model=List[Dict[str, Any]])
async def list_task_templates():
    """获取任务模板列表。"""
    return batch_task_service.list_task_templates()


@router.post("/templates", response_model=Dict[str, Any])
async def create_task_template(
    name: str = Form(...),
    title_template: str = Form(...),
    description_template: str = Form(...),
    capability_gap: str = Form(...),
    interaction_type: InteractionType = Form(InteractionType.DIGITAL),
    priority: TaskPriority = Form(TaskPriority.MEDIUM),
    reward_amount: float = Form(0.0),
    acceptance_criteria: str = Form("[]", description="JSON 数组"),
    requirements: str = Form("[]", description="JSON 数组"),
    required_skills: str = Form("{}", description="JSON 对象"),
):
    """
    创建任务模板。

    模板支持变量替换，如 {{item_name}}, {{location}}, {{deadline}} 等。
    """
    import json
    return batch_task_service.create_task_template(
        name=name,
        title_template=title_template,
        description_template=description_template,
        capability_gap=capability_gap,
        interaction_type=interaction_type,
        priority=priority,
        reward_amount=reward_amount,
        acceptance_criteria=json.loads(acceptance_criteria),
        requirements=json.loads(requirements),
        required_skills=json.loads(required_skills),
    )


@router.delete("/templates/{template_name}")
async def delete_task_template(template_name: str):
    """删除任务模板。"""
    if not batch_task_service.delete_task_template(template_name):
        raise HTTPException(status_code=404, detail="Template not found")
    return {"message": "Template deleted", "name": template_name}
