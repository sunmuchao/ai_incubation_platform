"""
DeerFlow 客户端封装 - 与 DeerFlow 2.0 网关交互

支持降级模式：当 DeerFlow 不可用时，使用本地工作流执行
"""
import asyncio
import json
import os
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class DeerFlowClient:
    """DeerFlow 2.0 客户端封装"""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """
        初始化 DeerFlow 客户端

        Args:
            api_key: DeerFlow API 密钥，从环境变量 DEERFLOW_API_KEY 读取
            base_url: DeerFlow 网关基础 URL
        """
        self.api_key = api_key or os.getenv("DEERFLOW_API_KEY")
        self.base_url = base_url or os.getenv("DEERFLOW_BASE_URL", "http://localhost:8000")
        self._available: Optional[bool] = None

    def is_available(self) -> bool:
        """检查 DeerFlow 服务是否可用"""
        if self._available is not None:
            return self._available

        if not self.api_key:
            logger.warning("DeerFlow API key not configured, using local fallback")
            self._available = False
            return False

        try:
            # 简单的连通性检查
            import httpx
            response = httpx.get(
                f"{self.base_url}/health",
                timeout=2.0
            )
            self._available = response.status_code == 200
            return self._available
        except Exception as e:
            logger.warning(f"DeerFlow unavailable: {e}, using local fallback")
            self._available = False
            return False

    async def run_workflow(self, workflow_name: str, **input_data) -> Dict[str, Any]:
        """
        运行 DeerFlow 工作流

        Args:
            workflow_name: 工作流名称
            **input_data: 工作流输入参数

        Returns:
            工作流执行结果
        """
        if not self.is_available():
            raise RuntimeError("DeerFlow service unavailable")

        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/workflows/{workflow_name}/run",
                    json={"input": input_data},
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    timeout=60.0
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to run workflow {workflow_name}: {e}")
            raise

    async def run_tool(self, tool_name: str, **input_data) -> Dict[str, Any]:
        """
        运行 DeerFlow 工具

        Args:
            tool_name: 工具名称
            **input_data: 工具输入参数

        Returns:
            工具执行结果
        """
        if not self.is_available():
            raise RuntimeError("DeerFlow service unavailable")

        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/tools/{tool_name}/run",
                    json={"input": input_data},
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to run tool {tool_name}: {e}")
            raise

    async def chat(self, message: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        发送对话消息到 DeerFlow

        Args:
            message: 用户消息
            context: 对话上下文

        Returns:
            AI 响应
        """
        if not self.is_available():
            raise RuntimeError("DeerFlow service unavailable")

        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "message": message,
                        "context": context or {}
                    },
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    timeout=60.0
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to chat: {e}")
            raise


class LocalWorkflowRunner:
    """本地工作流运行器 - DeerFlow 不可用时的降级方案"""

    def __init__(self):
        self._workflows = {}

    def register_workflow(self, name: str, workflow_class):
        """注册本地工作流"""
        self._workflows[name] = workflow_class

    async def run(self, workflow_name: str, **input_data) -> Dict[str, Any]:
        """运行本地工作流"""
        if workflow_name not in self._workflows:
            raise ValueError(f"Workflow {workflow_name} not registered")

        workflow_class = self._workflows[workflow_name]
        workflow = workflow_class()
        return await workflow.execute(**input_data)


# 全局本地工作流运行器
local_runner = LocalWorkflowRunner()
