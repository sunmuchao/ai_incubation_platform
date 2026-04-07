"""
工具 API - 工具注册表接口
"""
import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from tools.registry import TOOLS_REGISTRY, get_tool, list_tools

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/tools", tags=["tools"])


class ToolExecuteRequest(BaseModel):
    """工具执行请求"""
    tool_name: str = Field(..., description="工具名称")
    parameters: Dict[str, Any] = Field(..., description="工具参数")


@router.get("")
async def list_all_tools() -> Dict[str, Any]:
    """获取所有可用工具"""
    tools = list_tools()
    return {"count": len(tools), "tools": tools}


@router.get("/{tool_name}")
async def get_tool_info(tool_name: str) -> Dict[str, Any]:
    """获取工具详细信息"""
    try:
        tool = get_tool(tool_name)
        return tool
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/execute")
async def execute_tool(request: ToolExecuteRequest) -> Dict[str, Any]:
    """
    执行指定工具

    可用工具：
    - identify_intent: 识别用户意图
    - route_to_project: 路由到子项目
    - aggregate_results: 聚合结果
    - cross_project_workflow: 跨项目工作流
    """
    logger.info(f"Executing tool: {request.tool_name}")

    if request.tool_name not in TOOLS_REGISTRY:
        raise HTTPException(
            status_code=404,
            detail=f"Tool '{request.tool_name}' not found. Available: {list(TOOLS_REGISTRY.keys())}",
        )

    try:
        tool = TOOLS_REGISTRY[request.tool_name]
        handler = tool["handler"]
        result = await handler(**request.parameters)
        return {
            "tool_name": request.tool_name,
            "success": True,
            "result": result,
        }
    except Exception as e:
        logger.error(f"Tool execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/registry/schema")
async def get_tools_schema() -> Dict[str, Any]:
    """
    获取所有工具的完整 Schema

    用于 AI Agent 进行工具选择和参数验证。
    """
    return {
        "tools": {
            name: {
                "name": info["name"],
                "description": info["description"],
                "input_schema": info["input_schema"],
            }
            for name, info in TOOLS_REGISTRY.items()
        }
    }
