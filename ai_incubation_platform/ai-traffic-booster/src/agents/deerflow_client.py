"""
DeerFlow 2.0 客户端封装

提供与 DeerFlow 框架的集成，支持 Agent 编排和工作流执行
"""
import os
import json
import logging
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class DeerFlowStatus(Enum):
    """DeerFlow 客户端状态"""
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    FALLBACK = "fallback"


@dataclass
class ToolDefinition:
    """工具定义"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Callable


class DeerFlowClient:
    """
    DeerFlow 2.0 客户端

    提供与 DeerFlow 框架的集成，支持：
    - Agent 运行时调用
    - 工作流编排执行
    - 工具注册和调用
    - 降级模式支持
    """

    def __init__(self, api_key: Optional[str] = None, api_base: Optional[str] = None):
        """
        初始化 DeerFlow 客户端

        Args:
            api_key: DeerFlow API Key，来自环境变量 DEERFLOW_API_KEY
            api_base: DeerFlow API 基础 URL
        """
        self.api_key = api_key or os.getenv("DEERFLOW_API_KEY")
        self.api_base = api_base or os.getenv("DEERFLOW_API_BASE", "https://api.deerflow.ai/v1")
        self.status = DeerFlowStatus.UNAVAILABLE
        self.fallback_enabled = True
        self.tools: Dict[str, ToolDefinition] = {}
        self.workflows: Dict[str, Callable] = {}

        # 尝试连接 DeerFlow 服务
        self._initialize()

    def _initialize(self):
        """初始化客户端连接"""
        if self.api_key:
            try:
                # 尝试连接 DeerFlow 服务
                self._validate_connection()
                self.status = DeerFlowStatus.AVAILABLE
                logger.info("DeerFlow client initialized successfully")
            except Exception as e:
                logger.warning(f"DeerFlow connection failed: {e}, fallback enabled: {self.fallback_enabled}")
                if self.fallback_enabled:
                    self.status = DeerFlowStatus.FALLBACK
                else:
                    self.status = DeerFlowStatus.UNAVAILABLE
        else:
            logger.warning("DEERFLOW_API_KEY not set, using fallback mode")
            if self.fallback_enabled:
                self.status = DeerFlowStatus.FALLBACK

    def _validate_connection(self):
        """验证与 DeerFlow 服务的连接"""
        # TODO: 实现实际的连接验证逻辑
        pass

    def is_available(self) -> bool:
        """检查 DeerFlow 服务是否可用"""
        return self.status == DeerFlowStatus.AVAILABLE

    def is_fallback(self) -> bool:
        """检查是否处于降级模式"""
        return self.status == DeerFlowStatus.FALLBACK

    def register_tool(self, tool: ToolDefinition):
        """
        注册工具到 DeerFlow

        Args:
            tool: 工具定义
        """
        self.tools[tool.name] = tool
        logger.info(f"Tool registered: {tool.name}")

    def register_workflow(self, name: str, workflow: Callable):
        """
        注册工作流

        Args:
            name: 工作流名称
            workflow: 工作流处理函数
        """
        self.workflows[name] = workflow
        logger.info(f"Workflow registered: {name}")

    async def run_workflow(self, name: str, **input_data) -> Dict[str, Any]:
        """
        运行工作流

        Args:
            name: 工作流名称
            **input_data: 输入数据

        Returns:
            工作流执行结果
        """
        if self.is_available():
            return await self._run_remote_workflow(name, **input_data)
        elif self.is_fallback():
            return await self._run_local_workflow(name, **input_data)
        else:
            raise RuntimeError("DeerFlow unavailable and fallback disabled")

    async def _run_remote_workflow(self, name: str, **input_data) -> Dict[str, Any]:
        """运行远程 DeerFlow 工作流"""
        # TODO: 实现远程工作流调用
        logger.info(f"Running remote workflow: {name}")
        return {"status": "success", "workflow": name, "mode": "remote"}

    async def _run_local_workflow(self, name: str, **input_data) -> Dict[str, Any]:
        """运行本地降级工作流"""
        if name in self.workflows:
            logger.info(f"Running local fallback workflow: {name}")
            return await self.workflows[name](**input_data)
        else:
            raise RuntimeError(f"Local workflow not found: {name}")

    async def call_tool(self, tool_name: str, **kwargs) -> Any:
        """
        调用工具

        Args:
            tool_name: 工具名称
            **kwargs: 工具参数

        Returns:
            工具执行结果
        """
        if tool_name not in self.tools:
            raise ValueError(f"Tool not found: {tool_name}")

        tool = self.tools[tool_name]
        return await tool.handler(**kwargs)

    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """获取所有工具的 Schema，用于 Agent 调用"""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema
            }
            for tool in self.tools.values()
        ]


# 全局客户端实例
_deerflow_client: Optional[DeerFlowClient] = None


def get_deerflow_client() -> DeerFlowClient:
    """获取全局 DeerFlow 客户端实例"""
    global _deerflow_client
    if _deerflow_client is None:
        _deerflow_client = DeerFlowClient()
    return _deerflow_client


def init_deerflow_client(api_key: Optional[str] = None, api_base: Optional[str] = None) -> DeerFlowClient:
    """初始化全局 DeerFlow 客户端"""
    global _deerflow_client
    _deerflow_client = DeerFlowClient(api_key=api_key, api_base=api_base)
    return _deerflow_client
