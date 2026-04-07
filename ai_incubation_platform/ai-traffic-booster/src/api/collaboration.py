"""
跨 Agent 协同 API

提供跨 Agent 工作流触发、状态查询、健康检查等接口
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from datetime import datetime

from schemas.collaboration import (
    WorkflowTriggerRequest,
    WorkflowListResponse,
    WorkflowDetailResponse,
    AgentHealthCheckResponse,
    TrafficAnomalyEvent,
    CrossAgentDiagnosisReport,
)
from services.collaboration_service import collaboration_service

router = APIRouter(prefix="/collaboration", tags=["collaboration"])


class WorkflowStatusResponse(BaseModel):
    """工作流状态响应"""
    workflow_id: str
    workflow_name: str
    status: str
    trigger_type: str
    steps: List[Dict[str, Any]]
    final_result: Optional[Dict[str, Any]]
    error_message: Optional[str]
    created_at: str
    updated_at: str
    completed_at: Optional[str]


@router.get("/health", summary="Agent 健康检查", description="检查所有 Agent 的健康状态")
async def check_agent_health() -> Dict[str, Any]:
    """
    检查所有 Agent 的健康状态

    返回：
    - agents: 各 Agent 的状态
    - overall_status: 整体状态 (healthy/degraded/unhealthy)
    """
    return await collaboration_service.check_agent_health()


@router.post("/workflow/trigger", summary="触发工作流", description="手动触发跨 Agent 工作流")
async def trigger_workflow(request: WorkflowTriggerRequest) -> Dict[str, Any]:
    """
    触发跨 Agent 工作流

    支持的工作流：
    - traffic_anomaly_diagnosis: 流量异常诊断工作流

    触发事件格式 (traffic_anomaly_diagnosis):
    ```json
    {
        "anomaly_id": "anomaly_xxx",
        "metric_name": "visitors",
        "current_value": 100,
        "expected_value": 500,
        "deviation": -0.6,
        "z_score": -3.5,
        "severity": "critical",
        "description": "流量严重下跌",
        "detected_at": "2026-04-04T10:00:00"
    }
    ```
    """
    try:
        workflow = await collaboration_service.trigger_workflow(
            workflow_name=request.workflow_name,
            trigger_event=request.trigger_event,
            trigger_type=request.trigger_type
        )

        return {
            "status": "success",
            "message": f"工作流 {request.workflow_name} 已触发",
            "workflow_id": workflow.workflow_id,
            "workflow_name": workflow.workflow_name,
            "status": workflow.status.value,
            "steps_count": len(workflow.steps),
            "created_at": workflow.created_at.isoformat()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"工作流执行失败：{str(e)}")


@router.get("/workflow/list", summary="获取工作流列表", description="获取历史工作流列表")
async def list_workflows(
    status: Optional[str] = None,
    limit: int = 20
) -> Dict[str, Any]:
    """
    获取工作流列表

    参数：
    - status: 状态过滤 (pending/running/completed/failed/timeout)
    - limit: 返回数量限制
    """
    from schemas.collaboration import WorkflowStatus

    status_filter = None
    if status:
        try:
            status_filter = WorkflowStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的状态值：{status}")

    workflows = collaboration_service.list_workflows(status_filter=status_filter, limit=limit)

    return {
        "workflows": [
            {
                "workflow_id": w.workflow_id,
                "workflow_name": w.workflow_name,
                "status": w.status.value,
                "trigger_type": w.trigger_type,
                "steps_count": len(w.steps),
                "created_at": w.created_at.isoformat(),
                "completed_at": w.completed_at.isoformat() if w.completed_at else None
            }
            for w in workflows
        ],
        "total": len(workflows),
        "filters": {"status": status, "limit": limit}
    }


@router.get("/workflow/{workflow_id}", summary="获取工作流详情", description="获取指定工作流的完整执行详情")
async def get_workflow(workflow_id: str) -> Dict[str, Any]:
    """
    获取工作流完整详情

    包括：
    - 所有步骤的执行状态
    - 每个步骤的输入输出
    - 最终诊断报告
    """
    workflow = collaboration_service.get_workflow_status(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail=f"工作流不存在：{workflow_id}")

    return {
        "workflow": {
            "workflow_id": workflow.workflow_id,
            "workflow_name": workflow.workflow_name,
            "status": workflow.status.value,
            "trigger_type": workflow.trigger_type,
            "trigger_event": workflow.trigger_event,
            "steps": [
                {
                    "step_id": s.step_id,
                    "step_name": s.step_name,
                    "agent_type": s.agent_type.value,
                    "endpoint": s.endpoint,
                    "input_data": s.input_data,
                    "output_data": s.output_data,
                    "status": s.status.value,
                    "error_message": s.error_message,
                    "started_at": s.started_at.isoformat() if s.started_at else None,
                    "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                    "duration_ms": s.duration_ms
                }
                for s in workflow.steps
            ],
            "final_result": workflow.final_result,
            "error_message": workflow.error_message,
            "created_at": workflow.created_at.isoformat(),
            "updated_at": workflow.updated_at.isoformat(),
            "completed_at": workflow.completed_at.isoformat() if workflow.completed_at else None,
            "total_duration_ms": workflow.total_duration_ms
        }
    }


@router.post("/workflow/{workflow_id}/cancel", summary="取消工作流", description="取消正在执行的工作流")
async def cancel_workflow(workflow_id: str) -> Dict[str, Any]:
    """
    取消正在执行的工作流

    注意：只能取消状态为 running 的工作流
    """
    workflow = collaboration_service.get_workflow_status(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail=f"工作流不存在：{workflow_id}")

    if workflow.status.value != "running":
        raise HTTPException(
            status_code=400,
            detail=f"无法取消状态为 {workflow.status.value} 的工作流"
        )

    # 标记为已取消
    workflow.status = "cancelled"
    workflow.error_message = "用户取消"

    return {
        "status": "success",
        "message": f"工作流 {workflow_id} 已取消",
        "workflow_id": workflow_id,
        "final_status": "cancelled"
    }


@router.get("/report/{workflow_id}", summary="获取诊断报告", description="获取跨 Agent 诊断报告")
async def get_diagnosis_report(workflow_id: str) -> Dict[str, Any]:
    """
    获取跨 Agent 诊断报告

    报告包含：
    - 异常摘要
    - 运行态诊断结果
    - 代码分析结果
    - 最终建议
    - 行动计划
    """
    workflow = collaboration_service.get_workflow_status(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail=f"工作流不存在：{workflow_id}")

    if workflow.status.value != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"工作流尚未完成，当前状态：{workflow.status.value}"
        )

    if not workflow.final_result:
        raise HTTPException(status_code=404, detail="未找到诊断报告")

    return {
        "report": workflow.final_result,
        "workflow_id": workflow_id,
        "workflow_name": workflow.workflow_name,
        "completed_at": workflow.completed_at.isoformat() if workflow.completed_at else None
    }


@router.post("/parse_anomaly", summary="解析异常事件", description="解析流量异常事件数据")
async def parse_anomaly_event(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    解析流量异常事件

    将原始异常数据转换为标准格式
    """
    anomaly_event = TrafficAnomalyEvent(
        anomaly_id=data.get("anomaly_id", "unknown"),
        metric_name=data.get("metric_name", "unknown"),
        current_value=data.get("current_value", 0),
        expected_value=data.get("expected_value", 0),
        deviation=data.get("deviation", 0),
        z_score=data.get("z_score", 0),
        severity=data.get("severity", "info"),
        description=data.get("description", ""),
        detected_at=datetime.fromisoformat(data.get("detected_at", datetime.now().isoformat()))
    )

    return {
        "status": "success",
        "anomaly_event": anomaly_event.model_dump(),
        "parsed_at": datetime.now().isoformat()
    }


# ============= 快速触发接口 =============

class QuickDiagnoseRequest(BaseModel):
    """快速诊断请求"""
    anomaly_id: str = Field(..., description="异常 ID")
    metric_name: str = Field(..., description="指标名称")
    severity: str = Field("warning", description="严重度")


@router.post("/quick-diagnose", summary="快速诊断", description="快速触发流量异常诊断工作流")
async def quick_diagnose(request: QuickDiagnoseRequest) -> Dict[str, Any]:
    """
    快速触发诊断工作流

    简化的接口，仅需提供关键参数即可触发完整诊断流程
    """
    trigger_event = {
        "anomaly_id": request.anomaly_id,
        "metric_name": request.metric_name,
        "current_value": 0,  # 需要从数据库获取
        "expected_value": 0,
        "deviation": 0,
        "z_score": 0,
        "severity": request.severity,
        "description": f"{request.metric_name} 发生 {request.severity} 级别异常",
        "detected_at": datetime.now().isoformat()
    }

    try:
        workflow = await collaboration_service.trigger_workflow(
            workflow_name="traffic_anomaly_diagnosis",
            trigger_event=trigger_event,
            trigger_type="manual"
        )

        return {
            "status": "success",
            "message": "诊断工作流已触发",
            "workflow_id": workflow.workflow_id,
            "poll_url": f"/api/collaboration/workflow/{workflow.workflow_id}",
            "report_url": f"/api/collaboration/report/{workflow.workflow_id}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflows/summary", summary="工作流统计", description="获取工作流执行统计")
async def get_workflows_summary() -> Dict[str, Any]:
    """
    获取工作流执行统计

    包括：
    - 总执行次数
    - 各状态分布
    - 平均执行时长
    """
    workflows = collaboration_service.list_workflows(limit=1000)

    status_counts = {}
    total_duration = 0
    completed_count = 0

    for w in workflows:
        status = w.status.value
        status_counts[status] = status_counts.get(status, 0) + 1

        if w.completed_at and w.created_at:
            duration = (w.completed_at - w.created_at).total_seconds() * 1000
            total_duration += duration
            completed_count += 1

    return {
        "total_workflows": len(workflows),
        "status_distribution": status_counts,
        "success_rate": round(status_counts.get("completed", 0) / len(workflows) * 100, 2) if workflows else 0,
        "avg_duration_ms": round(total_duration / completed_count) if completed_count > 0 else 0,
        "calculated_at": datetime.now().isoformat()
    }


@router.get("/stats", summary="服务统计", description="获取服务完整统计信息，包括熔断器状态")
async def get_service_stats() -> Dict[str, Any]:
    """
    获取服务完整统计信息

    包括：
    - 工作流统计（总数、成功、失败、降级）
    - 熔断器状态（每个 Agent 的熔断器）
    - 内存中的工作流数量
    """
    return collaboration_service.get_stats()


@router.post("/stats/reset", summary="重置统计", description="重置服务统计信息（仅开发环境）")
async def reset_service_stats() -> Dict[str, Any]:
    """
    重置服务统计信息

    注意：仅建议在开发环境下使用
    """
    collaboration_service.reset_stats()
    return {
        "status": "success",
        "message": "统计信息已重置"
    }
