"""
Agent 工具 API
提供 DeerFlow 2.0 Agent 工具注册和调用接口
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import asyncio

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.deerflow_agent import opportunity_agent

router = APIRouter(prefix="/api/agent", tags=["agent"])


class ToolInvokeRequest(BaseModel):
    """工具调用请求"""
    tool_name: str
    parameters: Dict[str, Any] = {}


class WorkflowRequest(BaseModel):
    """工作流请求"""
    keywords: Optional[List[str]] = None
    industry: Optional[str] = None
    format: Optional[str] = "markdown"


@router.get("/tools")
async def list_tools():
    """获取所有可用工具的 schema"""
    return {
        "tools": opportunity_agent.get_tools_schema(),
        "count": len(opportunity_agent.tools_registry),
    }


@router.get("/tools/{tool_name}")
async def get_tool(tool_name: str):
    """获取单个工具详情"""
    tool = opportunity_agent.tools_registry.get(tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
    return {
        "name": tool["name"],
        "description": tool["description"],
        "input_schema": tool["input_schema"],
        "audit_log": tool.get("audit_log", False),
    }


@router.post("/tools/invoke")
async def invoke_tool(request: ToolInvokeRequest):
    """调用单个工具"""
    result = await opportunity_agent.execute_tool(request.tool_name, **request.parameters)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Tool execution failed"))
    return result


@router.post("/workflow/discover")
async def discover_workflow(request: WorkflowRequest):
    """运行商机发现工作流"""
    if not request.keywords and not request.industry:
        raise HTTPException(status_code=400, detail="Must provide either keywords or industry")

    result = await opportunity_agent.discover_opportunities_workflow(
        keywords=request.keywords or [],
        industry=request.industry,
    )
    return result


@router.post("/workflow/analyze")
async def analyze_workflow(request: WorkflowRequest):
    """运行行业分析工作流"""
    if not request.industry:
        raise HTTPException(status_code=400, detail="Must provide industry")

    result = await opportunity_agent.analyze_industry_workflow(industry=request.industry)
    return result


@router.post("/workflow/export/{opp_id}")
async def export_workflow(opp_id: str, format: str = "markdown"):
    """运行报告导出工作流"""
    result = await opportunity_agent.export_report_workflow(opp_id, format)
    if result.get("status") == "failed":
        raise HTTPException(status_code=400, detail=result.get("error", "Export failed"))
    return result


@router.get("/audit-logs")
async def get_audit_logs(tool_name: Optional[str] = None):
    """获取审计日志"""
    logs = opportunity_agent.get_audit_logs(tool_name)
    return {
        "count": len(logs),
        "logs": logs,
    }
