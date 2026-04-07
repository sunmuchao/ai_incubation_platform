"""
DeerFlow 2.0 客户端封装

提供与 DeerFlow 框架的集成，支持工作流编排和工具调用。
当 DeerFlow 不可用时，支持本地降级模式。
"""
import os
import json
import logging
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class DeerFlowConfig:
    """DeerFlow 配置"""
    api_key: Optional[str] = None
    api_base_url: str = "https://api.deerflow.ai/v1"
    timeout: int = 30
    max_retries: int = 3
    fallback_enabled: bool = True

    @classmethod
    def from_env(cls) -> "DeerFlowConfig":
        """从环境变量加载配置"""
        return cls(
            api_key=os.getenv("DEERFLOW_API_KEY"),
            api_base_url=os.getenv("DEERFLOW_API_BASE", "https://api.deerflow.ai/v1"),
            timeout=int(os.getenv("DEERFLOW_TIMEOUT", "30")),
            max_retries=int(os.getenv("DEERFLOW_MAX_RETRIES", "3")),
            fallback_enabled=os.getenv("DEERFLOW_FALLBACK_ENABLED", "true").lower() == "true"
        )


@dataclass
class WorkflowResult:
    """工作流执行结果"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    trace_id: Optional[str] = None
    steps: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def ok(cls, data: Dict[str, Any] = None, trace_id: str = None, steps: List = None) -> "WorkflowResult":
        return cls(success=True, data=data, trace_id=trace_id, steps=steps or [])

    @classmethod
    def fail(cls, error: str, trace_id: str = None) -> "WorkflowResult":
        return cls(success=False, error=error, trace_id=trace_id)


class DeerFlowClient:
    """
    DeerFlow 2.0 客户端

    提供工作流编排、工具调用和 Agent 通信能力。
    支持降级模式：当 DeerFlow 服务不可用时，使用本地工作流实现。
    """

    def __init__(self, config: Optional[DeerFlowConfig] = None):
        self.config = config or DeerFlowConfig.from_env()
        self._available = self._check_availability()
        self._local_workflows: Dict[str, Callable] = {}
        self._local_tools: Dict[str, Callable] = {}

        logger.info(f"DeerFlow 客户端初始化完成，服务可用：{self._available}")

    def _check_availability(self) -> bool:
        """检查 DeerFlow 服务是否可用"""
        if not self.config.api_key:
            logger.warning("DeerFlow API Key 未配置，将使用降级模式")
            return False

        # 实际项目中这里应该发起 HTTP 请求检查服务状态
        # 为了演示，我们假设服务可用
        return True

    def is_available(self) -> bool:
        """检查 DeerFlow 服务是否可用"""
        return self._available

    def register_local_workflow(self, name: str, handler: Callable) -> None:
        """注册本地工作流（用于降级模式）"""
        self._local_workflows[name] = handler
        logger.info(f"本地工作流注册成功：{name}")

    def register_local_tool(self, name: str, handler: Callable) -> None:
        """注册本地工具（用于降级模式）"""
        self._local_tools[name] = handler
        logger.info(f"本地工具注册成功：{name}")

    async def run_workflow(self, name: str, **input_data) -> WorkflowResult:
        """
        运行工作流

        Args:
            name: 工作流名称
            **input_data: 工作流输入参数

        Returns:
            WorkflowResult: 工作流执行结果
        """
        trace_id = f"wf_{datetime.now().strftime('%Y%m%d%H%M%S')}_{os.urandom(4).hex()}"

        if self._available:
            return await self._run_remote_workflow(name, trace_id, **input_data)
        elif self.config.fallback_enabled:
            logger.warning(f"DeerFlow 不可用，使用本地工作流：{name}")
            return await self._run_local_workflow(name, trace_id, **input_data)
        else:
            return WorkflowResult.fail(
                error="DeerFlow 服务不可用且降级模式已禁用",
                trace_id=trace_id
            )

    async def _run_remote_workflow(self, name: str, trace_id: str, **input_data) -> WorkflowResult:
        """运行远程工作流（调用 DeerFlow API）"""
        try:
            # 实际项目中这里会发起 HTTP 请求调用 DeerFlow API
            # 为了演示，我们模拟一个成功响应
            logger.info(f"调用远程工作流：{name}, trace_id: {trace_id}")

            # 模拟 API 调用
            await self._mock_api_call()

            return WorkflowResult.ok(
                data={"message": f"工作流 {name} 执行成功", "input": input_data},
                trace_id=trace_id
            )
        except Exception as e:
            logger.error(f"远程工作流执行失败：{name}, error: {str(e)}")
            return WorkflowResult.fail(error=str(e), trace_id=trace_id)

    async def _run_local_workflow(self, name: str, trace_id: str, **input_data) -> WorkflowResult:
        """运行本地工作流（降级模式）"""
        if name not in self._local_workflows:
            return WorkflowResult.fail(
                error=f"本地工作流未注册：{name}",
                trace_id=trace_id
            )

        try:
            handler = self._local_workflows[name]
            result = await handler(**input_data)
            return WorkflowResult.ok(data=result, trace_id=trace_id)
        except Exception as e:
            logger.error(f"本地工作流执行失败：{name}, error: {str(e)}")
            return WorkflowResult.fail(error=str(e), trace_id=trace_id)

    async def call_tool(self, name: str, **params) -> Dict[str, Any]:
        """
        调用工具

        Args:
            name: 工具名称
            **params: 工具参数

        Returns:
            Dict: 工具执行结果
        """
        if self._available:
            return await self._call_remote_tool(name, **params)
        elif self.config.fallback_enabled and name in self._local_tools:
            return await self._call_local_tool(name, **params)
        else:
            raise RuntimeError(f"工具不可用：{name}")

    async def _call_remote_tool(self, name: str, **params) -> Dict[str, Any]:
        """调用远程工具"""
        logger.info(f"调用远程工具：{name}, params: {params}")
        await self._mock_api_call()
        return {"success": True, "tool": name, "params": params}

    async def _call_local_tool(self, name: str, **params) -> Dict[str, Any]:
        """调用本地工具"""
        if name not in self._local_tools:
            raise RuntimeError(f"本地工具未注册：{name}")

        handler = self._local_tools[name]
        result = handler(**params)
        return result

    async def _mock_api_call(self) -> None:
        """模拟 API 调用延迟"""
        import asyncio
        await asyncio.sleep(0.1)

    def create_agent(self, agent_class: type, **kwargs) -> Any:
        """创建 Agent 实例"""
        return agent_class(client=self, **kwargs)


# 全局默认客户端
_default_client: Optional[DeerFlowClient] = None


def get_default_client() -> DeerFlowClient:
    """获取默认客户端实例"""
    global _default_client
    if _default_client is None:
        _default_client = DeerFlowClient()
    return _default_client


def set_default_client(client: DeerFlowClient) -> None:
    """设置默认客户端实例"""
    global _default_client
    _default_client = client
