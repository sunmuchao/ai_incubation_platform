"""
工具注册表

提供工具的注册、发现、执行和生命周期管理
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Callable, Type, Union
from dataclasses import dataclass, field
import time
from collections import defaultdict

from .base import BaseTool, ToolContext, ToolResult, ToolStatus

logger = logging.getLogger(__name__)


@dataclass
class ToolRegistration:
    """工具注册信息"""
    name: str
    handler: Union[BaseTool, Callable]
    description: str
    input_schema: Dict[str, Any]
    requires_auth: bool = False
    requires_audit: bool = True
    rate_limit: Optional[int] = None
    rate_limit_window: int = 60  # 秒
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


@dataclass
class RateLimitState:
    """限流状态"""
    count: int = 0
    window_start: float = field(default_factory=time.time)


class ToolsRegistry:
    """
    统一工具注册表

    功能:
    - 工具注册与发现
    - 输入验证
    - 审计日志自动记录
    - 限流控制
    """

    def __init__(self, audit_logger: Optional[Any] = None):
        """
        初始化工具注册表

        Args:
            audit_logger: 审计日志记录器
        """
        self._tools: Dict[str, ToolRegistration] = {}
        self._rate_limits: Dict[str, RateLimitState] = defaultdict(RateLimitState)
        self._audit_logger = audit_logger
        self._execution_history: List[Dict[str, Any]] = []
        self._max_history_size = 1000

    def register(
        self,
        name: str,
        handler: Union[BaseTool, Callable],
        description: str,
        input_schema: Optional[Dict] = None,
        requires_auth: bool = False,
        requires_audit: bool = True,
        rate_limit: Optional[int] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict] = None
    ) -> None:
        """
        注册工具

        Args:
            name: 工具名称
            handler: 工具处理器（BaseTool 实例或函数）
            description: 工具描述
            input_schema: 输入 schema（JSON Schema 格式）
            requires_auth: 是否需要认证
            requires_audit: 是否需要审计日志
            rate_limit: 限流（每秒请求数）
            tags: 标签列表
            metadata: 额外元数据
        """
        if name in self._tools:
            logger.warning(f"Tool {name} already registered, overwriting")

        registration = ToolRegistration(
            name=name,
            handler=handler,
            description=description,
            input_schema=input_schema or {"type": "object", "properties": {}},
            requires_auth=requires_auth,
            requires_audit=requires_audit,
            rate_limit=rate_limit,
            tags=tags or [],
            metadata=metadata or {}
        )
        self._tools[name] = registration
        logger.info(f"Registered tool: {name}")

    def unregister(self, name: str) -> bool:
        """注销工具"""
        if name in self._tools:
            del self._tools[name]
            logger.info(f"Unregistered tool: {name}")
            return True
        return False

    def get(self, name: str) -> Optional[ToolRegistration]:
        """获取工具注册信息"""
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        """列出所有工具（供 AI 发现）"""
        return [
            {
                "name": reg.name,
                "description": reg.description,
                "input_schema": reg.input_schema,
                "requires_auth": reg.requires_auth,
                "rate_limit": reg.rate_limit,
                "tags": reg.tags
            }
            for reg in self._tools.values()
        ]

    def search_tools(self, query: str) -> List[Dict[str, Any]]:
        """搜索工具"""
        query_lower = query.lower()
        results = []
        for reg in self._tools.values():
            if (query_lower in reg.name.lower() or
                query_lower in reg.description.lower() or
                any(query_lower in tag.lower() for tag in reg.tags)):
                results.append({
                    "name": reg.name,
                    "description": reg.description,
                    "relevance": self._calculate_relevance(reg, query)
                })
        return sorted(results, key=lambda x: x["relevance"], reverse=True)

    def _calculate_relevance(self, reg: ToolRegistration, query: str) -> float:
        """计算相关性分数"""
        score = 0.0
        query_lower = query.lower()

        if query_lower == reg.name.lower():
            score += 10.0
        elif query_lower in reg.name.lower():
            score += 5.0

        if query_lower in reg.description.lower():
            score += 3.0

        for tag in reg.tags:
            if query_lower in tag.lower():
                score += 2.0

        return score

    async def execute(
        self,
        name: str,
        context: Optional[ToolContext] = None,
        **kwargs
    ) -> ToolResult:
        """
        执行工具

        Args:
            name: 工具名称
            context: 执行上下文
            **kwargs: 工具参数

        Returns:
            ToolResult: 执行结果
        """
        start_time = time.time()
        context = context or ToolContext()

        # 1. 验证工具存在
        reg = self.get(name)
        if not reg:
            return ToolResult.fail(
                error=f"Tool not found: {name}",
                status=ToolStatus.FAILED,
                request_id=context.request_id
            )

        # 2. 检查限流
        if reg.rate_limit:
            if not self._check_rate_limit(name, reg.rate_limit):
                return ToolResult.fail(
                    error=f"Rate limit exceeded for tool: {name}",
                    status=ToolStatus.FAILED,
                    request_id=context.request_id
                )

        # 3. 验证输入
        validation_result = self._validate_input(reg, kwargs)
        if not validation_result[0]:
            return ToolResult.fail(
                error=validation_result[1],
                status=ToolStatus.VALIDATION_ERROR,
                request_id=context.request_id
            )

        # 4. 记录审计日志（执行前）
        if reg.requires_audit and self._audit_logger:
            await self._log_audit(
                actor=context.user_id or "anonymous",
                action="execute_tool",
                resource=name,
                request=kwargs,
                status="started",
                trace_id=context.request_id
            )

        try:
            # 5. 执行工具
            result = await self._execute_handler(reg, context, **kwargs)

            # 6. 记录审计日志（执行后）
            if reg.requires_audit and self._audit_logger:
                await self._log_audit(
                    actor=context.user_id or "anonymous",
                    action="execute_tool",
                    resource=name,
                    request=kwargs,
                    response=result.to_dict(),
                    status="success" if result.success else "failed",
                    trace_id=context.request_id
                )

            # 7. 记录执行历史
            self._record_execution(name, result, time.time() - start_time)

            return result

        except Exception as e:
            logger.exception(f"Tool execution failed: {e}")

            # 记录失败审计日志
            if reg.requires_audit and self._audit_logger:
                await self._log_audit(
                    actor=context.user_id or "anonymous",
                    action="execute_tool",
                    resource=name,
                    request=kwargs,
                    response={"error": str(e)},
                    status="failed",
                    trace_id=context.request_id
                )

            return ToolResult.fail(
                error=str(e),
                status=ToolStatus.FAILED,
                request_id=context.request_id
            )

    def _check_rate_limit(self, name: str, limit: int) -> bool:
        """检查限流"""
        state = self._rate_limits[name]
        current_time = time.time()

        # 重置窗口
        if current_time - state.window_start >= 1.0:
            state.count = 0
            state.window_start = current_time

        state.count += 1
        return state.count <= limit

    def _validate_input(self, reg: ToolRegistration, kwargs: Dict) -> tuple[bool, Optional[str]]:
        """验证输入"""
        if isinstance(reg.handler, BaseTool):
            return reg.handler.validate_input(kwargs)

        # 简单验证必填参数
        required = reg.input_schema.get("required", [])
        for param in required:
            if param not in kwargs or kwargs[param] is None:
                return False, f"Missing required parameter: {param}"

        return True, None

    async def _execute_handler(
        self,
        reg: ToolRegistration,
        context: ToolContext,
        **kwargs
    ) -> ToolResult:
        """执行处理器"""
        if isinstance(reg.handler, BaseTool):
            return await reg.handler.run(context, **kwargs)
        elif asyncio.iscoroutinefunction(reg.handler):
            result = await reg.handler(**kwargs)
            return ToolResult.ok(data=result)
        else:
            result = reg.handler(**kwargs)
            return ToolResult.ok(data=result)

    async def _log_audit(self, **kwargs) -> None:
        """记录审计日志"""
        try:
            await self._audit_logger.log(**kwargs)
        except Exception as e:
            logger.error(f"Failed to log audit: {e}")

    def _record_execution(
        self,
        tool_name: str,
        result: ToolResult,
        duration: float
    ) -> None:
        """记录执行历史"""
        entry = {
            "tool_name": tool_name,
            "success": result.success,
            "duration_ms": duration * 1000,
            "timestamp": time.time()
        }
        self._execution_history.append(entry)

        # 限制历史记录大小
        if len(self._execution_history) > self._max_history_size:
            self._execution_history = self._execution_history[-self._max_history_size:]

    def get_stats(self, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """获取统计信息"""
        if tool_name:
            tool_entries = [
                e for e in self._execution_history
                if e["tool_name"] == tool_name
            ]
        else:
            tool_entries = self._execution_history

        if not tool_entries:
            return {"count": 0}

        success_count = sum(1 for e in tool_entries if e["success"])
        durations = [e["duration_ms"] for e in tool_entries]

        return {
            "count": len(tool_entries),
            "success_count": success_count,
            "failure_count": len(tool_entries) - success_count,
            "success_rate": success_count / len(tool_entries),
            "avg_duration_ms": sum(durations) / len(durations),
            "min_duration_ms": min(durations),
            "max_duration_ms": max(durations)
        }

    def clear_rate_limits(self) -> None:
        """清空限流状态"""
        self._rate_limits.clear()
        logger.info("Rate limits cleared")

    def batch_register(self, tools: List[Dict[str, Any]]) -> None:
        """批量注册工具"""
        for tool_config in tools:
            self.register(**tool_config)

    def import_tools(self, tools_module: Any) -> None:
        """从模块导入工具"""
        if hasattr(tools_module, 'tools'):
            for tool in tools_module.tools:
                if isinstance(tool, BaseTool):
                    self.register(
                        name=tool.name,
                        handler=tool,
                        description=tool.description,
                        input_schema=tool.input_schema,
                        requires_auth=tool.requires_auth,
                        tags=tool.tags
                    )
