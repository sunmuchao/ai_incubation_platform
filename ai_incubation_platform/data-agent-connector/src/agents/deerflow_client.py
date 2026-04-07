"""
DeerFlow 2.0 客户端封装

提供与 DeerFlow 平台的集成，支持：
- 工作流执行
- Agent 调用
- 工具注册
- 降级模式（DeerFlow 不可用时使用本地执行）
"""
import os
import sys
import json
import asyncio
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
import httpx

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import logger


@dataclass
class DeerFlowWorkflowResult:
    """DeerFlow 工作流执行结果"""
    success: bool
    workflow_name: str
    result: Any = None
    error: Optional[str] = None
    trace_id: Optional[str] = None
    steps: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "workflow_name": self.workflow_name,
            "result": self.result,
            "error": self.error,
            "trace_id": self.trace_id,
            "steps": self.steps
        }


class DeerFlowClient:
    """
    DeerFlow 2.0 客户端

    支持与 DeerFlow 平台的 API 交互，包括：
    - 工作流执行
    - Agent 调用
    - 工具管理

    降级模式：当 DeerFlow 不可用时，自动切换到本地执行
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        fallback_enabled: bool = True,
        timeout: int = 60
    ):
        """
        初始化 DeerFlow 客户端

        参数:
            api_key: DeerFlow API 密钥（从环境变量 DEERFLOW_API_KEY 加载）
            base_url: DeerFlow API 基础 URL（从环境变量 DEERFLOW_BASE_URL 加载）
            fallback_enabled: 是否启用降级模式（默认 True）
            timeout: 请求超时时间（秒）
        """
        self.api_key = api_key or os.getenv("DEERFLOW_API_KEY")
        self.base_url = base_url or os.getenv("DEERFLOW_BASE_URL", "https://api.deerflow.ai")
        self.fallback_enabled = fallback_enabled
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        self._available = None

    async def _get_client(self) -> httpx.AsyncClient:
        """获取或创建 HTTP 客户端"""
        if self._client is None or self._client.is_closed:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
                headers["X-API-Key"] = self.api_key

            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=httpx.Timeout(self.timeout)
            )
        return self._client

    async def close(self):
        """关闭客户端"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def is_available(self) -> bool:
        """
        检查 DeerFlow 服务是否可用

        返回:
            bool: True 表示服务可用，False 表示不可用
        """
        if self._available is not None:
            return self._available

        if not self.api_key:
            logger.info("DeerFlow API key not configured, fallback mode enabled")
            self._available = False
            return False

        if not self.base_url:
            logger.info("DeerFlow base URL not configured, fallback mode enabled")
            self._available = False
            return False

        self._available = True
        return True

    async def health_check(self) -> bool:
        """
        执行健康检查

        返回:
            bool: True 表示服务健康
        """
        try:
            client = await self._get_client()
            response = await client.get("/health")
            if response.status_code == 200:
                self._available = True
                return True
            self._available = False
            return False
        except Exception as e:
            logger.warning(f"DeerFlow health check failed: {e}")
            self._available = False
            return False

    async def run_workflow(
        self,
        workflow_name: str,
        **input_data
    ) -> DeerFlowWorkflowResult:
        """
        执行 DeerFlow 工作流

        参数:
            workflow_name: 工作流名称
            **input_data: 工作流输入参数

        返回:
            DeerFlowWorkflowResult: 工作流执行结果
        """
        if self.is_available():
            try:
                return await self._run_remote_workflow(workflow_name, **input_data)
            except Exception as e:
                logger.error(f"Remote workflow execution failed: {e}")
                if self.fallback_enabled:
                    logger.info("Falling back to local workflow execution")
                    return await self._run_local_workflow(workflow_name, **input_data)
                raise
        else:
            if self.fallback_enabled:
                logger.info("DeerFlow unavailable, using local workflow execution")
                return await self._run_local_workflow(workflow_name, **input_data)
            raise RuntimeError("DeerFlow unavailable and fallback disabled")

    async def _run_remote_workflow(
        self,
        workflow_name: str,
        **input_data
    ) -> DeerFlowWorkflowResult:
        """执行远程工作流"""
        client = await self._get_client()

        payload = {
            "workflow_name": workflow_name,
            "input": input_data
        }

        try:
            response = await client.post(
                "/api/v1/workflows/run",
                json=payload
            )
            response.raise_for_status()
            data = response.json()

            return DeerFlowWorkflowResult(
                success=data.get("success", True),
                workflow_name=workflow_name,
                result=data.get("result"),
                trace_id=data.get("trace_id"),
                steps=data.get("steps", [])
            )
        except httpx.HTTPStatusError as e:
            return DeerFlowWorkflowResult(
                success=False,
                workflow_name=workflow_name,
                error=f"HTTP error: {e.response.status_code} - {e.response.text}"
            )
        except Exception as e:
            return DeerFlowWorkflowResult(
                success=False,
                workflow_name=workflow_name,
                error=str(e)
            )

    async def _run_local_workflow(
        self,
        workflow_name: str,
        **input_data
    ) -> DeerFlowWorkflowResult:
        """
        执行本地工作流（降级模式）

        从本地 workflows 模块加载并执行工作流
        """
        try:
            # 动态导入本地工作流
            from src.workflows import connector_workflows

            # 查找对应的工作流类
            workflow_class_name = self._snake_to_pascal(workflow_name) + "Workflow"
            if hasattr(connector_workflows, workflow_class_name):
                workflow_class = getattr(connector_workflows, workflow_class_name)
                workflow_instance = workflow_class()

                # 执行工作流的 run 方法
                if hasattr(workflow_instance, "run"):
                    result = await workflow_instance.run(**input_data)
                    return DeerFlowWorkflowResult(
                        success=True,
                        workflow_name=workflow_name,
                        result=result
                    )

            # 尝试直接调用函数
            if hasattr(connector_workflows, workflow_name):
                workflow_func = getattr(connector_workflows, workflow_name)
                result = await workflow_func(**input_data)
                return DeerFlowWorkflowResult(
                    success=True,
                    workflow_name=workflow_name,
                    result=result
                )

            return DeerFlowWorkflowResult(
                success=False,
                workflow_name=workflow_name,
                error=f"Local workflow '{workflow_name}' not found"
            )
        except Exception as e:
            logger.error(f"Local workflow execution failed: {e}")
            return DeerFlowWorkflowResult(
                success=False,
                workflow_name=workflow_name,
                error=f"Local execution failed: {str(e)}"
            )

    def _snake_to_pascal(self, name: str) -> str:
        """将蛇形命名转换为帕斯卡命名"""
        return "".join(word.capitalize() for word in name.split("_"))

    async def call_agent(
        self,
        agent_name: str,
        task: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        调用 DeerFlow Agent

        参数:
            agent_name: Agent 名称
            task: 任务描述
            context: 上下文信息

        返回:
            Dict[str, Any]: Agent 响应
        """
        if self.is_available():
            try:
                return await self._call_remote_agent(agent_name, task, context)
            except Exception as e:
                logger.warning(f"Remote agent call failed: {e}, falling back to local")
                return await self._call_local_agent(agent_name, task, context)
        else:
            return await self._call_local_agent(agent_name, task, context)

    async def _call_remote_agent(
        self,
        agent_name: str,
        task: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """调用远程 Agent"""
        client = await self._get_client()

        payload = {
            "agent_name": agent_name,
            "task": task,
            "context": context or {}
        }

        response = await client.post(
            "/api/v1/agents/run",
            json=payload
        )
        response.raise_for_status()
        return response.json()

    async def _call_local_agent(
        self,
        agent_name: str,
        task: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """调用本地 Agent（降级模式）"""
        try:
            from src.agents import connector_agent

            agent_class_name = self._snake_to_pascal(agent_name) + "Agent"
            if hasattr(connector_agent, agent_class_name):
                agent_class = getattr(connector_agent, agent_class_name)
                agent_instance = agent_class()
                return await agent_instance.run(task, context or {})

            return {"success": False, "error": f"Local agent '{agent_name}' not found"}
        except Exception as e:
            return {"success": False, "error": f"Local agent failed: {str(e)}"}

    async def register_tools(self, tools_registry: Dict[str, Dict[str, Any]]) -> bool:
        """
        注册工具到 DeerFlow

        参数:
            tools_registry: 工具注册表

        返回:
            bool: 注册是否成功
        """
        if not self.is_available():
            logger.info("DeerFlow unavailable, skipping tool registration")
            return False

        try:
            client = await self._get_client()
            response = await client.post(
                "/api/v1/tools/register",
                json={"tools": tools_registry}
            )
            response.raise_for_status()
            logger.info(f"Registered {len(tools_registry)} tools to DeerFlow")
            return True
        except Exception as e:
            logger.error(f"Tool registration failed: {e}")
            return False
