"""
工具 API 路由 - 暴露标准化工具功能

提供 HTTP 接口供 DeerFlow Agent 或其他调用方使用工具。
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
import uuid

from config.database import get_db
from tools.registry import init_tools, get_available_tools, get_tool

router = APIRouter(prefix="/api/tools", tags=["tools"])


@router.get("/list", summary="获取可用工具列表")
async def list_tools():
    """获取所有已注册工具的元数据"""
    tools = get_available_tools()
    return {
        "success": True,
        "tools": [
            {
                "name": tool.name,
                "description": tool.description,
                "version": tool.version,
                "tags": tool.tags
            }
            for tool in tools
        ],
        "total": len(tools)
    }


@router.get("/{tool_name}/schema", summary="获取工具输入 Schema")
async def get_tool_schema(tool_name: str):
    """获取指定工具的输入参数 JSON Schema"""
    tool = get_tool(tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"工具 {tool_name} 不存在")

    return {
        "success": True,
        "tool_name": tool_name,
        "metadata": {
            "name": tool.get_metadata().name,
            "description": tool.get_metadata().description,
            "version": tool.get_metadata().version,
            "tags": tool.get_metadata().tags
        },
        "input_schema": tool.get_input_schema()
    }


@router.post("/{tool_name}/execute", summary="执行工具")
async def execute_tool(
    tool_name: str,
    params: Dict[str, Any] = Body(..., description="工具输入参数"),
    context: Optional[Dict[str, Any]] = Body(None, description="调用上下文"),
    db: Session = Depends(get_db)
):
    """
    执行指定的工具

    请求体:
    - params: 工具输入参数，应符合该工具的 input_schema
    - context: 可选的调用上下文，如 request_id 等
    """
    # 初始化工具（如果尚未初始化）
    init_tools(db)

    tool = get_tool(tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"工具 {tool_name} 不存在")

    # 生成 request_id 用于追踪
    request_id = str(uuid.uuid4())
    if context is None:
        context = {}
    context["request_id"] = request_id

    # 执行工具
    try:
        result = tool(params, context)
        return {
            "success": result.success,
            "request_id": request_id,
            "tool_name": tool_name,
            "data": result.data,
            "error": result.error
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"工具执行失败：{str(e)}")


# ========== 快捷工具接口 ==========
# 为常用工具提供简化的调用接口

@router.post("/product-selection", summary="获取商品推荐")
async def product_selection(
    community_id: str = Query(..., description="社区 ID"),
    limit: int = Query(10, description="返回数量"),
    category: Optional[str] = Query(None, description="商品类别"),
    db: Session = Depends(get_db)
):
    """获取社区推荐商品"""
    init_tools(db)

    tool = get_tool("product_selection")
    if not tool:
        raise HTTPException(status_code=404, detail="选品工具不可用")

    params = {
        "community_id": community_id,
        "limit": limit,
        "category": category,
        "seasonal": True
    }

    result = tool(params)
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    return result.data


@router.post("/dynamic-price", summary="计算动态价格")
async def dynamic_price(
    product_id: str = Query(..., description="商品 ID"),
    current_participants: int = Query(1, description="当前参与人数"),
    target_size: int = Query(2, description="目标成团人数"),
    base_price: float = Query(..., description="基础价格"),
    db: Session = Depends(get_db)
):
    """计算商品动态价格"""
    init_tools(db)

    tool = get_tool("dynamic_pricing")
    if not tool:
        raise HTTPException(status_code=404, detail="定价工具不可用")

    params = {
        "product_id": product_id,
        "current_participants": current_participants,
        "target_size": target_size,
        "base_price": base_price
    }

    result = tool(params)
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    return result.data


@router.get("/stock-alert", summary="检查库存预警")
async def stock_alert(
    alert_threshold: int = Query(10, description="预警阈值"),
    product_ids: Optional[List[str]] = Query(None, description="商品 ID 列表"),
    db: Session = Depends(get_db)
):
    """检查商品库存预警"""
    init_tools(db)

    tool = get_tool("stock_alert")
    if not tool:
        raise HTTPException(status_code=404, detail="库存预警工具不可用")

    params = {
        "product_ids": product_ids or [],
        "alert_threshold": alert_threshold
    }

    result = tool(params)
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    return result.data
