"""
工具注册和初始化

初始化并注册所有可用的工具。
"""
from typing import Optional
from sqlalchemy.orm import Session

from tools.base import tool_registry, BaseTool
from tools.product_selection import ProductSelectionTool
from tools.dynamic_pricing import DynamicPricingTool
from tools.stock_alert import StockAlertTool


def init_tools(db_session: Optional[Session] = None) -> None:
    """
    初始化并注册所有工具

    Args:
        db_session: 可选的数据库会话，用于支持数据库操作的工具
    """
    # 注册选品工具
    product_selection_tool = ProductSelectionTool(db_session)
    tool_registry.register(product_selection_tool)

    # 注册动态定价工具
    dynamic_pricing_tool = DynamicPricingTool(db_session)
    tool_registry.register(dynamic_pricing_tool)

    # 注册库存预警工具
    stock_alert_tool = StockAlertTool(db_session)
    tool_registry.register(stock_alert_tool)


def get_available_tools() -> list:
    """获取所有可用工具的元数据"""
    return tool_registry.list_tools()


def get_tool(name: str) -> Optional[BaseTool]:
    """获取指定工具"""
    return tool_registry.get(name)


def get_tool_registry():
    """获取工具注册中心"""
    return tool_registry
