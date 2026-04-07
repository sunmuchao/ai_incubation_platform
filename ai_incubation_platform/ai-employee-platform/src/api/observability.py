"""
P5 AI 可观测性 API

提供:
- Agent 执行记录查询
- 执行日志查看
- 性能指标统计
- 工作日志管理
- 可视化面板数据
"""

from typing import Optional, List
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session

from config.database import get_db
from middleware.auth import get_current_user_id, get_current_tenant_id
from services.observability_service import ObservabilityService
from models.observability_models import AgentExecutionStatus, LogLevel, AgentWorkLogDB, StreamEventType

router = APIRouter(prefix="/api/observability", tags=["Observability"])


def get_observability_service(db: Session) -> ObservabilityService:
    """获取可观测性服务实例"""
    return ObservabilityService(db)


# ============== Agent 执行追踪 ==============

@router.post("/executions", summary="创建执行记录", response_model=dict)
async def create_execution(
    employee_id: str = Body(..., description="AI 员工 ID"),
    task_description: str = Body(..., description="任务描述"),
    order_id: Optional[str] = Body(None, description="关联订单 ID"),
    deerflow_task_id: Optional[str] = Body(None, description="DeerFlow 任务 ID"),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """创建 Agent 执行记录"""
    observability_service = get_observability_service(db)
    execution = observability_service.create_execution(
        employee_id=employee_id,
        task_description=task_description,
        tenant_id=tenant_id,
        user_id=user_id,
        order_id=order_id,
        deerflow_task_id=deerflow_task_id
    )
    return {"execution": execution.to_dict()}


@router.post("/executions/{execution_id}/start", summary="标记执行开始", response_model=dict)
async def start_execution(
    execution_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """标记 Agent 执行开始"""
    observability_service = get_observability_service(db)
    execution = observability_service.get_execution(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    if execution.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="无权访问该执行记录")

    execution = observability_service.start_execution(execution_id)
    return {"execution": execution.to_dict()}


@router.post("/executions/{execution_id}/complete", summary="标记执行完成", response_model=dict)
async def complete_execution(
    execution_id: str,
    result_summary: Optional[str] = Body(None, description="执行结果摘要"),
    prompt_tokens: int = Body(0, description="输入 Token 数"),
    completion_tokens: int = Body(0, description="输出 Token 数"),
    api_call_count: int = Body(0, description="API 调用次数"),
    external_api_calls: Optional[List[dict]] = Body(None, description="外部 API 调用详情"),
    decision_tree: Optional[List[dict]] = Body(None, description="决策树"),
    tool_calls: Optional[List[dict]] = Body(None, description="工具调用记录"),
    token_details: Optional[List[dict]] = Body(None, description="Token 使用明细"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """标记 Agent 执行完成"""
    observability_service = get_observability_service(db)
    execution = observability_service.get_execution(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    if execution.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="无权访问该执行记录")

    execution = observability_service.complete_execution(
        execution_id=execution_id,
        result_summary=result_summary,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        api_call_count=api_call_count,
        external_api_calls=external_api_calls,
        decision_tree=decision_tree,
        tool_calls=tool_calls,
        token_details=token_details
    )
    return {"execution": execution.to_dict()}


@router.post("/executions/{execution_id}/fail", summary="标记执行失败", response_model=dict)
async def fail_execution(
    execution_id: str,
    error_message: str = Body(..., description="错误信息"),
    error_stack: Optional[str] = Body(None, description="错误堆栈"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """标记 Agent 执行失败"""
    observability_service = get_observability_service(db)
    execution = observability_service.get_execution(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    if execution.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="无权访问该执行记录")

    execution = observability_service.fail_execution(
        execution_id=execution_id,
        error_message=error_message,
        error_stack=error_stack
    )
    return {"execution": execution.to_dict()}


@router.get("/executions/{execution_id}", summary="获取执行记录详情", response_model=dict)
async def get_execution(
    execution_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """获取 Agent 执行记录详情"""
    observability_service = get_observability_service(db)
    execution = observability_service.get_execution(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    if execution.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="无权访问该执行记录")

    # 获取关联日志
    logs = observability_service.get_execution_logs(execution_id)

    return {
        "execution": execution.to_dict(),
        "logs": [log.to_dict() for log in logs[-50:]]  # 最近 50 条日志
    }


@router.get("/executions", summary="列出执行记录", response_model=dict)
async def list_executions(
    employee_id: Optional[str] = Query(None, description="AI 员工 ID"),
    order_id: Optional[str] = Query(None, description="关联订单 ID"),
    status: Optional[AgentExecutionStatus] = Query(None, description="执行状态"),
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
    limit: int = Query(50, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """列出 Agent 执行记录"""
    observability_service = get_observability_service(db)
    executions = observability_service.list_executions(
        tenant_id=tenant_id,
        employee_id=employee_id,
        order_id=order_id,
        status=status,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset
    )

    return {
        "executions": [e.to_dict() for e in executions],
        "total": len(executions),
        "limit": limit,
        "offset": offset
    }


@router.get("/executions/{execution_id}/logs", summary="获取执行日志", response_model=dict)
async def get_execution_logs(
    execution_id: str,
    level: Optional[LogLevel] = Query(None, description="日志级别"),
    category: Optional[str] = Query(None, description="日志分类"),
    limit: int = Query(100, ge=1, le=500, description="返回数量限制"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """获取 Agent 执行日志"""
    observability_service = get_observability_service(db)
    execution = observability_service.get_execution(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    if execution.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="无权访问该执行记录")

    logs = observability_service.get_execution_logs(
        execution_id=execution_id,
        level=level,
        category=category,
        limit=limit
    )

    return {
        "logs": [log.to_dict() for log in logs],
        "total": len(logs)
    }


# ============== 流式事件追踪 (v1.1 新增) ==============

@router.post("/executions/{execution_id}/start-streaming", summary="启动流式追踪", response_model=dict)
async def start_execution_streaming(
    execution_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """启动执行并开始流式追踪"""
    observability_service = get_observability_service(db)
    execution = observability_service.get_execution(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    if execution.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="无权访问该执行记录")

    execution = observability_service.start_execution_streaming(execution_id)
    return {"execution": execution.to_dict()}


@router.post("/executions/{execution_id}/stream-event", summary="记录流式事件", response_model=dict)
async def record_stream_event(
    execution_id: str,
    event_type: StreamEventType = Body(..., description="事件类型"),
    event_data: Optional[dict] = Body(None, description="事件数据"),
    token_delta: int = Body(0, description="Token 增量"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """记录流式事件"""
    observability_service = get_observability_service(db)
    execution = observability_service.get_execution(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    if execution.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="无权访问该执行记录")

    # 获取累计 Token 数
    cumulative_tokens = (execution.total_tokens or 0) + token_delta

    event = observability_service.record_stream_event(
        execution_id=execution_id,
        tenant_id=tenant_id,
        event_type=event_type,
        event_data=event_data,
        token_delta=token_delta,
        cumulative_tokens=cumulative_tokens
    )
    return {"stream_event": event.to_dict()}


@router.post("/executions/{execution_id}/progress", summary="更新执行进度", response_model=dict)
async def update_execution_progress(
    execution_id: str,
    progress_percent: int = Body(..., ge=0, le=100, description="进度百分比"),
    progress_message: Optional[str] = Body(None, description="进度消息"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """更新执行进度"""
    observability_service = get_observability_service(db)
    execution = observability_service.get_execution(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    if execution.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="无权访问该执行记录")

    execution = observability_service.update_execution_progress(
        execution_id=execution_id,
        progress_percent=progress_percent,
        progress_message=progress_message
    )
    return {"execution": execution.to_dict()}


@router.post("/executions/{execution_id}/token-usage", summary="记录 Token 使用", response_model=dict)
async def record_token_usage(
    execution_id: str,
    step_name: str = Body(..., description="步骤名称"),
    prompt_tokens: int = Body(0, description="输入 Token 数"),
    completion_tokens: int = Body(0, description="输出 Token 数"),
    model: Optional[str] = Body(None, description="模型名称"),
    cost: float = Body(0.0, description="成本"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """记录 Token 使用明细"""
    observability_service = get_observability_service(db)
    execution = observability_service.get_execution(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    if execution.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="无权访问该执行记录")

    token_detail = observability_service.record_token_usage(
        execution_id=execution_id,
        tenant_id=tenant_id,
        step_name=step_name,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        model=model,
        cost=cost
    )
    return {"token_detail": token_detail, "execution": execution.to_dict()}


@router.get("/executions/{execution_id}/stream-events", summary="获取流式事件", response_model=dict)
async def get_stream_events(
    execution_id: str,
    limit: int = Query(100, ge=1, le=500, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """获取流式事件列表"""
    observability_service = get_observability_service(db)
    execution = observability_service.get_execution(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    if execution.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="无权访问该执行记录")

    events = observability_service.get_stream_events(
        execution_id=execution_id,
        limit=limit,
        offset=offset
    )

    return {
        "stream_events": [event.to_dict() for event in events],
        "total": len(events)
    }


# ============== 统计面板 ==============

@router.get("/employees/{employee_id}/stats", summary="获取员工统计", response_model=dict)
async def get_employee_stats(
    employee_id: str,
    days: int = Query(30, ge=1, le=90, description="统计天数"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """获取 AI 员工统计数据"""
    observability_service = get_observability_service(db)
    stats = observability_service.get_employee_stats(
        employee_id=employee_id,
        tenant_id=tenant_id,
        days=days
    )
    return {"stats": stats}


@router.get("/dashboard", summary="获取可观测性面板数据", response_model=dict)
async def get_observability_dashboard(
    days: int = Query(30, ge=1, le=90, description="统计天数"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """获取租户可观测性面板数据"""
    observability_service = get_observability_service(db)
    dashboard = observability_service.get_tenant_observability_dashboard(
        tenant_id=tenant_id,
        days=days
    )
    return {"dashboard": dashboard}


# ============== 工作日志 ==============

@router.get("/work-logs", summary="列出工作日志", response_model=dict)
async def list_work_logs(
    employee_id: Optional[str] = Query(None, description="AI 员工 ID"),
    order_id: Optional[str] = Query(None, description="关联订单 ID"),
    is_submitted: Optional[bool] = Query(None, description="是否已提交"),
    review_status: Optional[str] = Query(None, description="审核状态"),
    limit: int = Query(50, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
    user_id: str = Depends(get_current_user_id)
):
    """列出工作日志"""
    observability_service = get_observability_service(db)
    logs = observability_service.list_work_logs(
        tenant_id=tenant_id,
        employee_id=employee_id,
        order_id=order_id,
        is_submitted=is_submitted,
        review_status=review_status,
        limit=limit,
        offset=offset
    )

    return {
        "work_logs": [log.to_dict() for log in logs],
        "total": len(logs),
        "limit": limit,
        "offset": offset
    }


@router.get("/work-logs/{log_id}", summary="获取工作日志详情", response_model=dict)
async def get_work_log(
    log_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """获取工作日志详情"""
    observability_service = get_observability_service(db)
    work_log = observability_service.db.query(AgentWorkLogDB).filter(
        AgentWorkLogDB.id == log_id,
        AgentWorkLogDB.tenant_id == tenant_id
    ).first()

    if not work_log:
        raise HTTPException(status_code=404, detail="工作日志不存在")

    return {"work_log": work_log.to_dict()}


@router.post("/work-logs/{log_id}/submit", summary="提交工作日志", response_model=dict)
async def submit_work_log(
    log_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """提交工作日志"""
    observability_service = get_observability_service(db)
    work_log = observability_service.db.query(AgentWorkLogDB).filter(
        AgentWorkLogDB.id == log_id,
        AgentWorkLogDB.tenant_id == tenant_id
    ).first()

    if not work_log:
        raise HTTPException(status_code=404, detail="工作日志不存在")

    work_log = observability_service.submit_work_log(log_id, user_id)
    return {"work_log": work_log.to_dict()}


@router.post("/work-logs/{log_id}/review", summary="审核工作日志", response_model=dict)
async def review_work_log(
    log_id: str,
    approved: bool = Body(..., description="是否通过"),
    comments: Optional[str] = Body(None, description="审核意见"),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """审核工作日志"""
    observability_service = get_observability_service(db)
    work_log = observability_service.db.query(AgentWorkLogDB).filter(
        AgentWorkLogDB.id == log_id,
        AgentWorkLogDB.tenant_id == tenant_id
    ).first()

    if not work_log:
        raise HTTPException(status_code=404, detail="工作日志不存在")

    work_log = observability_service.review_work_log(log_id, user_id, approved, comments)
    return {"work_log": work_log.to_dict()}
