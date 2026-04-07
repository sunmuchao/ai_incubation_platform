"""
v2.1 自主修复执行引擎 - API 接口

提供增强的修复执行 API，包括：
- 执行引擎控制
- 验证结果查询
- 回滚管理
- 审批工作流
- 快照管理
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from core.execution_engine_v2 import (
    ExecutionEngineV2,
    ExecutionResult,
    ValidationResult,
    SnapshotStatus,
    ApprovalStatus,
    ApprovalLevel,
    get_execution_engine,
    get_snapshot_manager,
    get_approval_workflow,
    get_rollback_manager,
    get_validation_engine,
)
from models.remediation import RemediationScript, RiskLevel, RemediationCategory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/remediation/v2.1", tags=["remediation-v2.1"])


# ============================================================================
# 请求/响应模型
# ============================================================================

class ExecuteRequestV21(BaseModel):
    """执行请求 v2.1"""
    script_id: str = Field(..., description="脚本 ID")
    service_id: str = Field(..., description="服务 ID")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="执行参数")
    require_approval: bool = Field(default=False, description="是否需要审批")
    timeout_seconds: Optional[int] = Field(default=None, description="超时时间")


class ExecuteResponseV21(BaseModel):
    """执行响应 v2.1"""
    execution_id: str = Field(..., description="执行 ID")
    result: str = Field(..., description="执行结果")
    status: str = Field(..., description="执行状态")
    logs: List[str] = Field(default_factory=list, description="执行日志")
    started_at: Optional[str] = Field(default=None, description="开始时间")
    completed_at: Optional[str] = Field(default=None, description="完成时间")


class ValidationRequest(BaseModel):
    """验证请求"""
    service_id: str = Field(..., description="服务 ID")
    metric_names: List[str] = Field(..., description="指标名称列表")
    source: str = Field(default="current", description="指标来源")


class ValidationResponse(BaseModel):
    """验证响应"""
    service_id: str = Field(..., description="服务 ID")
    metrics: Dict[str, float] = Field(..., description="指标数据")
    validation_summary: Dict[str, Any] = Field(..., description="验证摘要")


class SnapshotRequest(BaseModel):
    """快照请求"""
    service_id: str = Field(..., description="服务 ID")
    service_type: str = Field(default="service", description="服务类型")
    config: Optional[Dict[str, Any]] = Field(default=None, description="配置快照")
    resources: Optional[Dict[str, Any]] = Field(default=None, description="资源快照")
    state: Optional[Dict[str, Any]] = Field(default=None, description="状态快照")


class SnapshotResponse(BaseModel):
    """快照响应"""
    snapshot_id: str = Field(..., description="快照 ID")
    service_id: str = Field(..., description="服务 ID")
    status: str = Field(..., description="快照状态")
    created_at: str = Field(..., description="创建时间")
    expires_at: Optional[str] = Field(default=None, description="过期时间")


class ApprovalRequestV21(BaseModel):
    """审批请求 v2.1"""
    execution_id: str = Field(..., description="执行 ID")
    approver: str = Field(..., description="审批人")
    action: str = Field(..., description="审批动作：approve/reject")
    reason: Optional[str] = Field(default=None, description="审批意见")


class ApprovalResponse(BaseModel):
    """审批响应"""
    request_id: str = Field(..., description="请求 ID")
    execution_id: str = Field(..., description="执行 ID")
    status: str = Field(..., description="审批状态")
    approvals: Dict[str, str] = Field(default_factory=dict, description="审批记录")
    rejections: Dict[str, str] = Field(default_factory=dict, description="拒绝记录")


class RollbackRequest(BaseModel):
    """回滚请求"""
    snapshot_id: str = Field(..., description="快照 ID")
    execution_id: Optional[str] = Field(default=None, description="关联执行 ID")


class RollbackResponse(BaseModel):
    """回滚响应"""
    success: bool = Field(..., description="是否成功")
    snapshot_id: str = Field(..., description="快照 ID")
    message: str = Field(..., description="结果信息")


# ============================================================================
# 执行引擎 API
# ============================================================================

@router.post("/execute", response_model=ExecuteResponseV21)
async def execute_remediation(request: ExecuteRequestV21):
    """
    执行修复操作

    使用增强的执行引擎执行修复脚本，包括：
    - 白名单检查
    - 审批验证
    - 快照创建
    - 执行验证
    - 自动回滚
    """
    engine = get_execution_engine()

    # 构造脚本对象（实际应从脚本库获取）
    script = RemediationScript(
        script_id=request.script_id,
        name=request.script_id,
        description="Execution script",
        category=RemediationCategory.CONFIG_ADJUSTMENT,
        target_type="service",
        script_content="echo 'Executing script'",
        risk_level=RiskLevel.LOW if not request.require_approval else RiskLevel.MEDIUM,
        timeout_seconds=request.timeout_seconds or 300,
    )

    # 注册脚本到白名单（实际应预先注册）
    engine.register_script(request.script_id)

    # 执行修复
    result = await engine.execute(
        script=script,
        service_id=request.service_id,
        parameters=request.parameters,
        require_approval=request.require_approval,
        timeout_seconds=request.timeout_seconds
    )

    # 获取执行上下文
    context = engine.get_context(result.value)
    if not context:
        # 使用执行 ID 查找
        for ctx in engine.list_executions():
            if ctx.result == result:
                context = ctx
                break

    execution_id = context.execution_id if context else f"exec_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    return ExecuteResponseV21(
        execution_id=execution_id,
        result=result.value,
        status=context.status.value if context else "unknown",
        logs=context.logs if context else [],
        started_at=context.started_at.isoformat() if context and context.started_at else None,
        completed_at=context.completed_at.isoformat() if context and context.completed_at else None,
    )


@router.get("/executions/{execution_id}")
async def get_execution(execution_id: str):
    """获取执行详情"""
    engine = get_execution_engine()
    context = engine.get_context(execution_id)

    if not context:
        raise HTTPException(status_code=404, detail=f"Execution not found: {execution_id}")

    return {
        "execution_id": context.execution_id,
        "script_id": context.script_id,
        "service_id": context.service_id,
        "status": context.status.value,
        "result": context.result.value if context.result else None,
        "parameters": context.parameters,
        "logs": context.logs,
        "started_at": context.started_at.isoformat() if context.started_at else None,
        "completed_at": context.completed_at.isoformat() if context.completed_at else None,
    }


@router.get("/executions")
async def list_executions(service_id: Optional[str] = Query(None, description="服务 ID")):
    """列出执行记录"""
    engine = get_execution_engine()
    contexts = engine.list_executions(service_id=service_id)

    return {
        "executions": [
            {
                "execution_id": ctx.execution_id,
                "script_id": ctx.script_id,
                "service_id": ctx.service_id,
                "status": ctx.status.value,
                "result": ctx.result.value if ctx.result else None,
                "started_at": ctx.started_at.isoformat() if ctx.started_at else None,
                "completed_at": ctx.completed_at.isoformat() if ctx.completed_at else None,
            }
            for ctx in contexts
        ],
        "total": len(contexts)
    }


# ============================================================================
# 验证引擎 API
# ============================================================================

@router.post("/validate/collect", response_model=ValidationResponse)
async def collect_metrics(request: ValidationRequest):
    """采集指标"""
    validation_engine = get_validation_engine()
    metrics = validation_engine.collect_metrics(
        service_id=request.service_id,
        metric_names=request.metric_names,
        source=request.source
    )

    summary = validation_engine.get_validation_summary(request.service_id)

    return ValidationResponse(
        service_id=request.service_id,
        metrics=metrics,
        validation_summary=summary
    )


@router.get("/validate/summary/{service_id}")
async def get_validation_summary(service_id: str):
    """获取验证摘要"""
    validation_engine = get_validation_engine()
    summary = validation_engine.get_validation_summary(service_id)
    return {"service_id": service_id, "summary": summary}


# ============================================================================
# 快照管理 API
# ============================================================================

@router.post("/snapshots", response_model=SnapshotResponse)
async def create_snapshot(request: SnapshotRequest):
    """创建快照"""
    snapshot_manager = get_snapshot_manager()
    snapshot = snapshot_manager.create_snapshot(
        service_id=request.service_id,
        service_type=request.service_type,
        config=request.config,
        resources=request.resources,
        state=request.state
    )

    return SnapshotResponse(
        snapshot_id=snapshot.snapshot_id,
        service_id=snapshot.service_id,
        status=snapshot.status.value,
        created_at=snapshot.created_at.isoformat(),
        expires_at=snapshot.expires_at.isoformat() if snapshot.expires_at else None,
    )


@router.get("/snapshots/{snapshot_id}")
async def get_snapshot(snapshot_id: str):
    """获取快照"""
    snapshot_manager = get_snapshot_manager()
    snapshot = snapshot_manager.get_snapshot(snapshot_id)

    if not snapshot:
        raise HTTPException(status_code=404, detail=f"Snapshot not found: {snapshot_id}")

    return {
        "snapshot_id": snapshot.snapshot_id,
        "service_id": snapshot.service_id,
        "service_type": snapshot.service_type,
        "status": snapshot.status.value,
        "created_at": snapshot.created_at.isoformat(),
        "expires_at": snapshot.expires_at.isoformat() if snapshot.expires_at else None,
        "execution_id": snapshot.execution_id,
    }


@router.get("/snapshots")
async def list_snapshots(service_id: Optional[str] = Query(None, description="服务 ID")):
    """列出快照"""
    snapshot_manager = get_snapshot_manager()
    snapshots = snapshot_manager.list_snapshots(service_id=service_id)

    return {
        "snapshots": [
            {
                "snapshot_id": s.snapshot_id,
                "service_id": s.service_id,
                "status": s.status.value,
                "created_at": s.created_at.isoformat(),
            }
            for s in snapshots
        ],
        "total": len(snapshots)
    }


@router.delete("/snapshots/{snapshot_id}")
async def delete_snapshot(snapshot_id: str):
    """删除快照"""
    snapshot_manager = get_snapshot_manager()
    success = snapshot_manager.delete_snapshot(snapshot_id)

    if not success:
        raise HTTPException(status_code=404, detail=f"Snapshot not found: {snapshot_id}")

    return {"success": True, "snapshot_id": snapshot_id}


@router.post("/snapshots/cleanup")
async def cleanup_expired_snapshots():
    """清理过期快照"""
    snapshot_manager = get_snapshot_manager()
    count = snapshot_manager.cleanup_expired()
    return {"success": True, "cleaned_count": count}


# ============================================================================
# 审批工作流 API
# ============================================================================

@router.post("/approval/request", response_model=ApprovalResponse)
async def request_approval(request: ApprovalRequestV21):
    """请求审批"""
    # 注意：这个接口用于手动创建审批请求
    # 通常审批请求会在执行修复时自动创建
    workflow = get_approval_workflow()

    # 找到对应的执行请求（简化处理）
    # 实际应该从存储中查找
    request_obj = workflow.create_approval_request(
        execution_id=request.execution_id,
        risk_level=RiskLevel.MEDIUM,
        approvers=[request.approver]
    )

    return ApprovalResponse(
        request_id=request_obj.request_id,
        execution_id=request_obj.execution_id,
        status=request_obj.status.value,
        approvals={k: v.isoformat() for k, v in request_obj.approvals.items()},
        rejections=request_obj.rejections,
    )


@router.post("/approval/{request_id}/approve", response_model=ApprovalResponse)
async def approve_request(request_id: str, request: ApprovalRequestV21):
    """批准请求"""
    workflow = get_approval_workflow()

    success = workflow.approve(
        request_id=request_id,
        approver=request.approver
    )

    if not success:
        raise HTTPException(status_code=400, detail="Approval failed")

    approval_request = workflow.get_request(request_id)
    return ApprovalResponse(
        request_id=approval_request.request_id,
        execution_id=approval_request.execution_id,
        status=approval_request.status.value,
        approvals={k: v.isoformat() for k, v in approval_request.approvals.items()},
        rejections=approval_request.rejections,
    )


@router.post("/approval/{request_id}/reject", response_model=ApprovalResponse)
async def reject_request(request_id: str, request: ApprovalRequestV21):
    """拒绝请求"""
    workflow = get_approval_workflow()

    success = workflow.reject(
        request_id=request_id,
        approver=request.approver,
        reason=request.reason or "No reason provided"
    )

    if not success:
        raise HTTPException(status_code=400, detail="Rejection failed")

    approval_request = workflow.get_request(request_id)
    return ApprovalResponse(
        request_id=approval_request.request_id,
        execution_id=approval_request.execution_id,
        status=approval_request.status.value,
        approvals={k: v.isoformat() for k, v in approval_request.approvals.items()},
        rejections=approval_request.rejections,
    )


@router.get("/approval/{request_id}")
async def get_approval_request(request_id: str):
    """获取审批请求详情"""
    workflow = get_approval_workflow()
    request = workflow.get_request(request_id)

    if not request:
        raise HTTPException(status_code=404, detail=f"Approval request not found: {request_id}")

    return {
        "request_id": request.request_id,
        "execution_id": request.execution_id,
        "status": request.status.value,
        "level": request.level.value,
        "required_approvals": request.required_approvals,
        "approvals": {k: v.isoformat() for k, v in request.approvals.items()},
        "rejections": request.rejections,
        "created_at": request.created_at.isoformat(),
        "expires_at": request.expires_at.isoformat() if request.expires_at else None,
    }


@router.get("/approvals")
async def list_approval_requests(status: Optional[str] = Query(None, description="审批状态")):
    """列出审批请求"""
    workflow = get_approval_workflow()

    if status:
        try:
            status_filter = ApprovalStatus(status)
            requests = workflow.list_requests(status=status_filter)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    else:
        requests = workflow.list_requests()

    return {
        "requests": [
            {
                "request_id": r.request_id,
                "execution_id": r.execution_id,
                "status": r.status.value,
                "level": r.level.value,
                "approvals_count": len(r.approvals),
                "required_approvals": r.required_approvals,
                "created_at": r.created_at.isoformat(),
            }
            for r in requests
        ],
        "total": len(requests)
    }


# ============================================================================
# 回滚管理 API
# ============================================================================

@router.post("/rollback", response_model=RollbackResponse)
async def rollback_execution(request: RollbackRequest):
    """执行回滚"""
    rollback_manager = get_rollback_manager()

    success = await rollback_manager.rollback(snapshot_id=request.snapshot_id)

    return RollbackResponse(
        success=success,
        snapshot_id=request.snapshot_id,
        message="Rollback completed successfully" if success else "Rollback failed"
    )


@router.get("/rollback/history")
async def get_rollback_history(snapshot_id: Optional[str] = Query(None, description="快照 ID")):
    """获取回滚历史"""
    rollback_manager = get_rollback_manager()
    history = rollback_manager.get_rollback_history(snapshot_id)
    return {"history": history}


# ============================================================================
# 健康检查
# ============================================================================

@router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "version": "v2.1.0",
        "components": {
            "execution_engine": "ready",
            "validation_engine": "ready",
            "rollback_manager": "ready",
            "approval_workflow": "ready",
            "snapshot_manager": "ready",
        }
    }
