"""
社区团购工具层 - 标准化工具定义

遵循孵化器 Agent 标准，将业务动作封装为 DeerFlow 2.0 可调用的工具。
所有工具统一输入输出规范，支持工具注册和发现。
"""

from tools.base import BaseTool, tool_registry, register_tool, get_tool
from tools.product_selection import ProductSelectionTool
from tools.dynamic_pricing import DynamicPricingTool
from tools.stock_alert import StockAlertTool
from tools.registry import init_tools, get_available_tools, get_tool_registry

# AI Native 新增工具
from tools.groupbuy_tools import (
    CreateGroupTool,
    InviteMembersTool,
    PredictGroupSuccessTool,
    GetGroupStatusTool,
    init_groupbuy_tools
)
from tools.conversation_tools import (
    IntentRecognitionTool,
    EntityExtractionTool,
    ResponseGenerationTool,
    init_conversation_tools
)
from tools.product_tools import (
    SearchProductsTool,
    CompareProductsTool,
    GetProductDetailTool,
    init_product_tools
)

__all__ = [
    # 基类
    "BaseTool",
    "tool_registry",
    "register_tool",
    "get_tool",
    # 原有工具实现
    "ProductSelectionTool",
    "DynamicPricingTool",
    "StockAlertTool",
    # AI Native 新增工具 - 团购
    "CreateGroupTool",
    "InviteMembersTool",
    "PredictGroupSuccessTool",
    "GetGroupStatusTool",
    # AI Native 新增工具 - 对话
    "IntentRecognitionTool",
    "EntityExtractionTool",
    "ResponseGenerationTool",
    # AI Native 新增工具 - 商品
    "SearchProductsTool",
    "CompareProductsTool",
    "GetProductDetailTool",
    # 注册和初始化
    "init_tools",
    "init_groupbuy_tools",
    "init_conversation_tools",
    "init_product_tools",
    "get_available_tools",
    "get_tool_registry",
]
