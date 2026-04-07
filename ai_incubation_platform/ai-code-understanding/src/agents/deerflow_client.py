"""
DeerFlow 2.0 客户端封装

提供统一的 DeerFlow API 访问接口，支持降级模式
"""
import os
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

DEERFLOW_VERSION = "2.0"


class DeerFlowClient:
    """
    DeerFlow 2.0 客户端

    支持：
    1. 云端 DeerFlow API 调用
    2. 本地降级模式（当 DeerFlow 不可用时）
    3. 自动重试与超时控制
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化 DeerFlow 客户端

        Args:
            api_key: DeerFlow API Key，从环境变量 DEERFLOW_API_KEY 获取
        """
        self.api_key = api_key or os.environ.get("DEERFLOW_API_KEY")
        self.base_url = os.environ.get("DEERFLOW_BASE_URL", "https://api.deerflow.ai/v2")
        self._available = None

    def is_available(self) -> bool:
        """检查 DeerFlow 服务是否可用"""
        if self._available is not None:
            return self._available

        if not self.api_key:
            logger.warning("DeerFlow API Key 未配置，使用本地降级模式")
            self._available = False
            return False

        try:
            import requests
            response = requests.get(
                f"{self.base_url}/health",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=5
            )
            self._available = response.status_code == 200
            return self._available
        except Exception as e:
            logger.warning(f"DeerFlow 服务不可用：{e}，使用本地降级模式")
            self._available = False
            return False

    async def run_workflow(self, name: str, **input_data) -> Dict[str, Any]:
        """
        运行 DeerFlow 工作流

        Args:
            name: 工作流名称
            **input_data: 工作流输入参数

        Returns:
            工作流执行结果
        """
        if not self.is_available():
            raise RuntimeError("DeerFlow 服务不可用")

        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/workflows/{name}/run",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json=input_data
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(f"DeerFlow 工作流执行失败：{error_text}")
                return await response.json()

    async def call_agent(self, agent_name: str, message: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        调用 AI Agent

        Args:
            agent_name: Agent 名称
            message: 用户消息
            context: 上下文信息

        Returns:
            Agent 响应
        """
        if not self.is_available():
            raise RuntimeError("DeerFlow 服务不可用")

        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/agents/{agent_name}/chat",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={"message": message, "context": context or {}}
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(f"DeerFlow Agent 调用失败：{error_text}")
                return await response.json()


# 全局客户端实例
_deerflow_client: Optional[DeerFlowClient] = None


def get_deerflow_client(api_key: Optional[str] = None) -> DeerFlowClient:
    """获取 DeerFlow 客户端单例"""
    global _deerflow_client
    if _deerflow_client is None:
        _deerflow_client = DeerFlowClient(api_key=api_key)
    return _deerflow_client


def is_deerflow_available() -> bool:
    """检查 DeerFlow 服务是否可用"""
    return get_deerflow_client().is_available()
