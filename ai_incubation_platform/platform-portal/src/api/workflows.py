"""
工作流 API - 跨项目工作流接口
"""
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from workflows.cross_project_workflows import (
    startup_journey_workflow,
    talent_pipeline_workflow,
    full_stack_analysis_workflow,
    community_growth_workflow,
    WORKFLOW_REGISTRY,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/workflows", tags=["workflows"])


class WorkflowExecuteRequest(BaseModel):
    """工作流执行请求"""
    user_id: str = Field(..., description="用户 ID")
    input_data: Optional[Dict[str, Any]] = Field(None, description="输入数据")


@router.get("")
async def list_workflows() -> Dict[str, Any]:
    """获取所有可用工作流"""
    workflows = [
        {
            "name": name,
            "description": func.__doc__.split("\n")[2] if func.__doc__ else "",
        }
        for name, func in WORKFLOW_REGISTRY.items()
    ]
    return {"count": len(workflows), "workflows": workflows}


@router.post("/{workflow_name}/execute")
async def execute_workflow(
    workflow_name: str,
    request: WorkflowExecuteRequest,
) -> Dict[str, Any]:
    """
    执行指定的跨项目工作流

    可用工作流：
    - startup_journey: 创业旅程
    - talent_pipeline: 人才管道
    - full_stack_analysis: 全栈分析
    - community_growth: 社区增长
    """
    logger.info(f"Executing workflow: {workflow_name} for user {request.user_id}")

    if workflow_name not in WORKFLOW_REGISTRY:
        raise HTTPException(
            status_code=404,
            detail=f"Workflow '{workflow_name}' not found. Available: {list(WORKFLOW_REGISTRY.keys())}",
        )

    try:
        workflow_func = WORKFLOW_REGISTRY[workflow_name]
        result = await workflow_func(
            user_id=request.user_id,
            input_data=request.input_data or {},
        )
        return result
    except Exception as e:
        logger.error(f"Workflow execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{workflow_name}")
async def get_workflow_info(workflow_name: str) -> Dict[str, Any]:
    """获取工作流详细信息"""
    if workflow_name not in WORKFLOW_REGISTRY:
        raise HTTPException(
            status_code=404,
            detail=f"Workflow '{workflow_name}' not found",
        )

    from agents.portal_agent import WORKFLOW_TEMPLATES

    template = WORKFLOW_TEMPLATES.get(workflow_name, {})

    return {
        "name": workflow_name,
        "description": template.get("description", ""),
        "projects": template.get("projects", []),
        "workflow": template.get("workflow", []),
    }
