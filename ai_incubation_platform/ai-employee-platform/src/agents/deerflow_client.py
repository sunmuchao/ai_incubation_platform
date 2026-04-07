"""
DeerFlow 2.0 客户端封装

提供与 DeerFlow 框架的核心集成能力:
- 工作流执行
- 工具注册
- Agent 运行时
- 降级模式支持
"""
import asyncio
import logging
import os
from typing import Any, Dict, List, Optional, Callable
from functools import wraps

logger = logging.getLogger(__name__)


class DeerFlowClient:
    """
    DeerFlow 2.0 客户端

    负责与 DeerFlow 框架交互，提供:
    - 工作流执行
    - 工具调用
    - Agent 协调

    支持降级模式：当 DeerFlow 不可用时自动切换到本地实现
    """

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """
        初始化 DeerFlow 客户端

        Args:
            api_key: DeerFlow API 密钥，从环境变量获取
            base_url: DeerFlow API 基础 URL
        """
        self.api_key = api_key or os.getenv("DEERFLOW_API_KEY")
        self.base_url = base_url or os.getenv("DEERFLOW_BASE_URL", "http://localhost:8080")
        self._available: Optional[bool] = None
        self._tools_registry: Dict[str, Dict[str, Any]] = {}
        self._workflows: Dict[str, Any] = {}

    def is_available(self) -> bool:
        """
        检查 DeerFlow 服务是否可用

        Returns:
            bool: DeerFlow 是否可用
        """
        if self._available is not None:
            return self._available

        # 检查是否有 API 密钥
        if not self.api_key:
            logger.info("DeerFlow: 无 API 密钥，降级到本地模式")
            self._available = False
            return False

        # 尝试连接 DeerFlow 服务
        try:
            import requests
            response = requests.get(
                f"{self.base_url}/health",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=2
            )
            self._available = response.status_code == 200
            logger.info(f"DeerFlow: 服务{'可用' if self._available else '不可用'}")
            return self._available
        except Exception as e:
            logger.warning(f"DeerFlow: 连接失败 - {e}, 降级到本地模式")
            self._available = False
            return False

    def register_tool(self, name: str, description: str, input_schema: Dict[str, Any], handler: Callable):
        """
        注册工具到 DeerFlow

        Args:
            name: 工具名称
            description: 工具描述（供 AI 理解）
            input_schema: JSON Schema 格式的输入定义
            handler: 工具处理函数
        """
        self._tools_registry[name] = {
            "name": name,
            "description": description,
            "input_schema": input_schema,
            "handler": handler
        }
        logger.info(f"DeerFlow: 工具已注册 - {name}")

    def get_tools_registry(self) -> Dict[str, Dict[str, Any]]:
        """获取已注册的工具列表"""
        return self._tools_registry.copy()

    def register_workflow(self, name: str, workflow_class: Any):
        """
        注册工作流

        Args:
            name: 工作流名称
            workflow_class: 工作流类定义
        """
        self._workflows[name] = workflow_class
        logger.info(f"DeerFlow: 工作流已注册 - {name}")

    async def run_workflow(self, name: str, **input_data) -> Dict[str, Any]:
        """
        运行工作流

        Args:
            name: 工作流名称
            **input_data: 工作流输入参数

        Returns:
            Dict: 工作流执行结果
        """
        if name not in self._workflows:
            raise ValueError(f"工作流未注册：{name}")

        workflow_class = self._workflows[name]

        if self.is_available():
            # 使用远程 DeerFlow 执行
            return await self._run_remote_workflow(name, workflow_class, **input_data)
        else:
            # 降级到本地执行
            logger.info(f"DeerFlow: 降级执行本地工作流 - {name}")
            return await self._run_local_workflow(workflow_class, **input_data)

    async def _run_remote_workflow(self, name: str, workflow_class: Any, **input_data) -> Dict[str, Any]:
        """远程执行工作流（通过 DeerFlow API）"""
        try:
            import requests

            response = requests.post(
                f"{self.base_url}/workflows/{name}/run",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json=input_data,
                timeout=60
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"DeerFlow 远程执行失败：{e}, 降级到本地")
            return await self._run_local_workflow(workflow_class, **input_data)

    async def _run_local_workflow(self, workflow_class: Any, **input_data) -> Dict[str, Any]:
        """
        本地执行工作流（降级模式）

        按顺序执行工作流的每个 step
        """
        workflow = workflow_class()
        result = input_data.copy()

        # 获取所有 @step 装饰的方法
        steps = []
        for attr_name in dir(workflow):
            attr = getattr(workflow, attr_name)
            if hasattr(attr, '_is_step'):
                steps.append((attr_name, attr))

        # 按定义顺序排序
        steps.sort(key=lambda x: getattr(x[1], '_step_order', 0))

        # 依次执行每个 step
        for step_name, step_func in steps:
            logger.info(f"执行工作流步骤：{step_name}")
            try:
                if asyncio.iscoroutinefunction(step_func):
                    step_result = await step_func(result)
                else:
                    step_result = step_func(result)
                result.update(step_result)
            except Exception as e:
                logger.error(f"工作流步骤 {step_name} 执行失败：{e}")
                result['error'] = f"Step {step_name} failed: {str(e)}"
                break

        return result

    async def call_tool(self, tool_name: str, **kwargs) -> Any:
        """
        调用已注册的工具

        Args:
            tool_name: 工具名称
            **kwargs: 工具参数

        Returns:
            Any: 工具执行结果
        """
        if tool_name not in self._tools_registry:
            raise ValueError(f"工具未注册：{tool_name}")

        tool_info = self._tools_registry[tool_name]
        handler = tool_info["handler"]

        try:
            if asyncio.iscoroutinefunction(handler):
                return await handler(**kwargs)
            else:
                return handler(**kwargs)
        except Exception as e:
            logger.error(f"工具调用失败 {tool_name}: {e}")
            raise

    def get_workflow_metadata(self, name: str) -> Optional[Dict[str, Any]]:
        """获取工作流元数据（文档、步骤等）"""
        if name not in self._workflows:
            return None

        workflow_class = self._workflows[name]
        metadata = {
            "name": name,
            "description": workflow_class.__doc__ or "",
            "steps": []
        }

        # 提取步骤信息
        for attr_name in dir(workflow_class):
            attr = getattr(workflow_class, attr_name)
            if hasattr(attr, '_is_step'):
                metadata["steps"].append({
                    "name": attr_name,
                    "description": attr.__doc__ or "",
                    "order": getattr(attr, '_step_order', 0)
                })

        return metadata


def is_deerflow_available() -> bool:
    """
    检查 DeerFlow 是否可用（模块级函数）

    Returns:
        bool: DeerFlow 是否可用
    """
    client = DeerFlowClient()
    return client.is_available()


def step(order: int = 0):
    """
    工作流步骤装饰器

    Args:
        order: 步骤执行顺序
    """
    def decorator(func):
        func._is_step = True
        func._step_order = order
        return func
    return decorator


def workflow(name: str):
    """
    工作流类装饰器

    Args:
        name: 工作流名称
    """
    def decorator(cls):
        cls._workflow_name = name
        return cls
    return decorator
