"""
DeerFlow 客户端封装

提供统一的 DeerFlow 2.0 客户端，包括：
- 统一 API 密钥管理
- 自动重试机制
- 降级模式切换
- 审计日志集成
"""

import asyncio
import logging
from typing import Any, Dict, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum
import time

logger = logging.getLogger(__name__)


class ClientStatus(Enum):
    """客户端状态枚举"""
    INITIALIZED = "initialized"
    CONNECTED = "connected"
    DEGRADED = "degraded"
    DISCONNECTED = "disconnected"


@dataclass
class RetryConfig:
    """重试配置"""
    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    jitter: bool = True


@dataclass
class DeerFlowResponse:
    """DeerFlow 响应数据模型"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    trace_id: Optional[str] = None
    latency_ms: float = 0.0
    is_fallback: bool = False


class DeerFlowClient:
    """
    DeerFlow 2.0 客户端封装

    功能:
    - 统一 API 密钥管理
    - 自动重试机制
    - 降级模式切换
    - 审计日志集成
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        fallback_enabled: bool = True,
        retry_config: Optional[RetryConfig] = None,
        audit_logger: Optional[Any] = None,
        timeout: float = 30.0
    ):
        """
        初始化 DeerFlow 客户端

        Args:
            api_key: DeerFlow API 密钥
            fallback_enabled: 是否启用降级模式
            retry_config: 重试配置
            audit_logger: 审计日志记录器
            timeout: 请求超时时间（秒）
        """
        self.api_key = api_key
        self.fallback_enabled = fallback_enabled
        self.retry_config = retry_config or RetryConfig()
        self.audit_logger = audit_logger
        self.timeout = timeout
        self._client = None
        self._status = ClientStatus.INITIALIZED
        self._tools_registry: Dict[str, Callable] = {}

        # 初始化客户端
        self._init_client()

    def _init_client(self) -> None:
        """初始化 DeerFlow 客户端"""
        if self.api_key:
            try:
                from deerflow import Client
                self._client = Client(api_key=self.api_key, timeout=self.timeout)
                self._status = ClientStatus.CONNECTED
                logger.info("DeerFlow client initialized successfully")
            except ImportError:
                logger.warning("DeerFlow package not found, falling back to local mode")
                self._status = ClientStatus.DEGRADED
                if not self.fallback_enabled:
                    raise RuntimeError("DeerFlow not available and fallback is disabled")
            except Exception as e:
                logger.warning(f"Failed to initialize DeerFlow client: {e}")
                self._status = ClientStatus.DEGRADED
                if not self.fallback_enabled:
                    raise
        else:
            logger.info("No API key provided, running in local mode")
            self._status = ClientStatus.DEGRADED

    @property
    def status(self) -> ClientStatus:
        """获取客户端状态"""
        return self._status

    @property
    def is_connected(self) -> bool:
        """检查是否已连接到 DeerFlow"""
        return self._status == ClientStatus.CONNECTED

    @property
    def is_degraded(self) -> bool:
        """检查是否处于降级模式"""
        return self._status in (ClientStatus.DEGRADED, ClientStatus.DISCONNECTED)

    async def _execute_with_retry(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """带重试执行函数"""
        last_exception = None
        delay = self.retry_config.initial_delay

        for attempt in range(self.retry_config.max_retries + 1):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                logger.warning(f"Attempt {attempt + 1} failed: {e}")

                if attempt < self.retry_config.max_retries:
                    if self.retry_config.jitter:
                        import random
                        jitter = random.uniform(0, delay * 0.1)
                        actual_delay = delay + jitter
                    else:
                        actual_delay = delay

                    await asyncio.sleep(actual_delay)
                    delay = min(delay * self.retry_config.exponential_base,
                               self.retry_config.max_delay)

        raise last_exception

    async def run_workflow(
        self,
        name: str,
        **kwargs
    ) -> DeerFlowResponse:
        """
        运行工作流

        Args:
            name: 工作流名称
            **kwargs: 工作流参数

        Returns:
            DeerFlowResponse: 执行结果
        """
        trace_id = f"wf_{name}_{int(time.time() * 1000)}"
        start_time = time.time()

        try:
            if self._client:
                result = await self._execute_with_retry(
                    self._client.run_workflow,
                    name,
                    **kwargs
                )
                latency = (time.time() - start_time) * 1000

                response = DeerFlowResponse(
                    success=True,
                    data=result,
                    trace_id=trace_id,
                    latency_ms=latency,
                    is_fallback=False
                )
            else:
                # 降级模式：执行本地工作流
                result = await self._run_local_workflow(name, **kwargs)
                latency = (time.time() - start_time) * 1000

                response = DeerFlowResponse(
                    success=True,
                    data=result,
                    trace_id=trace_id,
                    latency_ms=latency,
                    is_fallback=True
                )

            # 记录审计日志
            await self._log_audit(
                actor="system",
                action="run_workflow",
                resource=name,
                request=kwargs,
                response={"success": response.success, "data": str(response.data)},
                status="success" if response.success else "failed",
                trace_id=trace_id
            )

            return response

        except Exception as e:
            latency = (time.time() - start_time) * 1000
            logger.error(f"Workflow execution failed: {e}")

            response = DeerFlowResponse(
                success=False,
                error=str(e),
                trace_id=trace_id,
                latency_ms=latency,
                is_fallback=self.is_degraded
            )

            await self._log_audit(
                actor="system",
                action="run_workflow",
                resource=name,
                request=kwargs,
                response={"error": str(e)},
                status="failed",
                trace_id=trace_id
            )

            return response

    async def _run_local_workflow(
        self,
        name: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        本地工作流执行（降级模式）

        Args:
            name: 工作流名称
            **kwargs: 工作流参数

        Returns:
            执行结果
        """
        logger.info(f"Running local workflow: {name}")

        # 检查是否有本地注册的工作流处理器
        if name in self._tools_registry:
            handler = self._tools_registry[name]
            if asyncio.iscoroutinefunction(handler):
                return await handler(**kwargs)
            else:
                return handler(**kwargs)

        # 默认返回空结果
        return {"status": "executed_locally", "workflow": name, "params": kwargs}

    def register_tool(
        self,
        name: str,
        handler: Callable,
        description: str = "",
        input_schema: Optional[Dict] = None
    ) -> None:
        """
        注册工具供 DeerFlow 调用

        Args:
            name: 工具名称
            handler: 处理函数
            description: 工具描述
            input_schema: 输入 schema
        """
        self._tools_registry[name] = handler
        logger.info(f"Registered tool: {name}")

    def unregister_tool(self, name: str) -> None:
        """注销工具"""
        if name in self._tools_registry:
            del self._tools_registry[name]
            logger.info(f"Unregistered tool: {name}")

    def list_tools(self) -> List[Dict[str, str]]:
        """列出所有已注册的工具"""
        return [
            {"name": name, "description": getattr(handler, "__doc__", "")}
            for name, handler in self._tools_registry.items()
        ]

    async def execute_tool(
        self,
        name: str,
        **kwargs
    ) -> DeerFlowResponse:
        """
        执行注册的工具

        Args:
            name: 工具名称
            **kwargs: 工具参数

        Returns:
            DeerFlowResponse: 执行结果
        """
        trace_id = f"tool_{name}_{int(time.time() * 1000)}"
        start_time = time.time()

        try:
            if name not in self._tools_registry:
                raise ValueError(f"Tool not found: {name}")

            handler = self._tools_registry[name]
            if asyncio.iscoroutinefunction(handler):
                result = await handler(**kwargs)
            else:
                result = handler(**kwargs)

            latency = (time.time() - start_time) * 1000

            response = DeerFlowResponse(
                success=True,
                data=result,
                trace_id=trace_id,
                latency_ms=latency,
                is_fallback=self.is_degraded
            )

            await self._log_audit(
                actor="system",
                action="execute_tool",
                resource=name,
                request=kwargs,
                response={"success": True},
                status="success",
                trace_id=trace_id
            )

            return response

        except Exception as e:
            latency = (time.time() - start_time) * 1000
            logger.error(f"Tool execution failed: {e}")

            response = DeerFlowResponse(
                success=False,
                error=str(e),
                trace_id=trace_id,
                latency_ms=latency
            )

            await self._log_audit(
                actor="system",
                action="execute_tool",
                resource=name,
                request=kwargs,
                response={"error": str(e)},
                status="failed",
                trace_id=trace_id
            )

            return response

    async def _log_audit(
        self,
        actor: str,
        action: str,
        resource: str,
        request: Dict,
        response: Dict,
        status: str,
        trace_id: Optional[str] = None
    ) -> None:
        """记录审计日志"""
        if self.audit_logger:
            try:
                await self.audit_logger.log(
                    actor=actor,
                    action=action,
                    resource=resource,
                    request=request,
                    response=response,
                    status=status,
                    trace_id=trace_id
                )
            except Exception as e:
                logger.error(f"Failed to log audit: {e}")

    async def connect(self) -> bool:
        """
        尝试重新连接 DeerFlow

        Returns:
            是否连接成功
        """
        if self.api_key:
            try:
                from deerflow import Client
                self._client = Client(api_key=self.api_key, timeout=self.timeout)
                self._status = ClientStatus.CONNECTED
                logger.info("DeerFlow client connected successfully")
                return True
            except Exception as e:
                logger.warning(f"Failed to connect: {e}")
                self._status = ClientStatus.DEGRADED
                return False
        return False

    async def disconnect(self) -> None:
        """断开连接"""
        self._client = None
        self._status = ClientStatus.DISCONNECTED
        logger.info("DeerFlow client disconnected")

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.disconnect()
