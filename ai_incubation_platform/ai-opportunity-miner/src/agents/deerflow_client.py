"""
DeerFlow 2.0 客户端封装

提供与 DeerFlow 框架的集成，支持：
- 工作流注册和执行
- 工具注册和调用
- 降级模式（DeerFlow 不可用时使用本地实现）
"""
import os
import logging
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime

logger = logging.getLogger(__name__)


class DeerFlowClient:
    """
    DeerFlow 2.0 客户端

    封装与 DeerFlow 框架的交互，提供统一的 API 接口。
    当 DeerFlow 服务不可用时，自动降级到本地执行模式。
    """

    def __init__(self, api_key: Optional[str] = None, api_url: Optional[str] = None):
        """
        初始化 DeerFlow 客户端

        Args:
            api_key: DeerFlow API 密钥（可选）
            api_url: DeerFlow API 地址（可选）
        """
        self.api_key = api_key or os.getenv("DEERFLOW_API_KEY")
        self.api_url = api_url or os.getenv("DEERFLOW_API_URL", "http://localhost:8000")
        self._available = False
        self._workflows = {}
        self._tools = {}

        self._check_availability()

    def _check_availability(self):
        """检查 DeerFlow 服务是否可用"""
        if not self.api_key:
            logger.info("DeerFlow API key not configured, running in local mode")
            self._available = False
            return

        try:
            import requests
            response = requests.get(f"{self.api_url}/health", timeout=5)
            if response.status_code == 200:
                self._available = True
                logger.info(f"Connected to DeerFlow at {self.api_url}")
            else:
                self._available = False
                logger.warning(f"DeerFlow health check failed: {response.status_code}")
        except Exception as e:
            self._available = False
            logger.warning(f"DeerFlow not available: {e}, running in local mode")

    @property
    def is_available(self) -> bool:
        """检查 DeerFlow 是否可用"""
        return self._available

    def register_workflow(self, name: str, workflow_class: type):
        """
        注册工作流

        Args:
            name: 工作流名称
            workflow_class: 工作流类
        """
        self._workflows[name] = workflow_class
        logger.info(f"Registered workflow: {name}")

    def register_tool(self, name: str, handler: Callable, description: str = "", input_schema: Dict = None):
        """
        注册工具

        Args:
            name: 工具名称
            handler: 处理函数
            description: 工具描述
            input_schema: 输入参数 schema
        """
        self._tools[name] = {
            "handler": handler,
            "description": description,
            "input_schema": input_schema or {}
        }
        logger.info(f"Registered tool: {name}")

    async def run_workflow(self, workflow_name: str, **input_data) -> Dict[str, Any]:
        """
        运行工作流

        Args:
            workflow_name: 工作流名称
            **input_data: 输入数据

        Returns:
            工作流执行结果
        """
        workflow_class = self._workflows.get(workflow_name)
        if not workflow_class:
            return {
                "success": False,
                "error": f"Workflow '{workflow_name}' not found"
            }

        try:
            workflow = workflow_class()
            result = await workflow.run(**input_data)
            return {
                "success": True,
                "workflow_name": workflow_name,
                "result": result
            }
        except Exception as e:
            logger.error(f"Workflow execution failed: {workflow_name}, error: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def call_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """
        调用工具

        Args:
            tool_name: 工具名称
            **kwargs: 工具参数

        Returns:
            工具执行结果
        """
        tool = self._tools.get(tool_name)
        if not tool:
            return {
                "success": False,
                "error": f"Tool '{tool_name}' not found"
            }

        try:
            handler = tool["handler"]
            import inspect
            if inspect.iscoroutinefunction(handler):
                result = await handler(**kwargs)
            else:
                result = handler(**kwargs)
            return result
        except Exception as e:
            logger.error(f"Tool execution failed: {tool_name}, error: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_workflows(self) -> List[str]:
        """获取所有已注册的工作流"""
        return list(self._workflows.keys())

    def get_tools(self) -> List[str]:
        """获取所有已注册的工具"""
        return list(self._tools.keys())


# 全局客户端实例
_deerflow_client = None


def get_deerflow_client() -> DeerFlowClient:
    """获取全局 DeerFlow 客户端实例"""
    global _deerflow_client
    if _deerflow_client is None:
        _deerflow_client = DeerFlowClient()
    return _deerflow_client


def is_deerflow_available() -> bool:
    """检查 DeerFlow 是否可用"""
    client = get_deerflow_client()
    return client.is_available
