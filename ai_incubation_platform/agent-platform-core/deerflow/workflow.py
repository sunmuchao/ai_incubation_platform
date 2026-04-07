"""
工作流编排引擎

提供工作流的定义、编排和执行能力
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import time
import uuid

logger = logging.getLogger(__name__)


class WorkflowStatus(Enum):
    """工作流状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class NodeStatus(Enum):
    """节点状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class WorkflowNode:
    """工作流节点"""
    id: str
    name: str
    handler: Optional[Callable] = None
    dependencies: List[str] = field(default_factory=list)
    condition: Optional[Callable[[Dict], bool]] = None
    retry_count: int = 0
    max_retries: int = 3
    timeout: float = 30.0
    status: NodeStatus = NodeStatus.PENDING
    result: Any = None
    error: Optional[str] = None

    def reset(self):
        """重置节点状态"""
        self.status = NodeStatus.PENDING
        self.result = None
        self.error = None


@dataclass
class WorkflowDefinition:
    """工作流定义"""
    id: str
    name: str
    description: str = ""
    nodes: List[WorkflowNode] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_node(
        self,
        name: str,
        handler: Optional[Callable] = None,
        dependencies: Optional[List[str]] = None,
        condition: Optional[Callable[[Dict], bool]] = None,
        retry_count: int = 3,
        timeout: float = 30.0
    ) -> str:
        """添加节点"""
        node_id = str(uuid.uuid4())
        node = WorkflowNode(
            id=node_id,
            name=name,
            handler=handler,
            dependencies=dependencies or [],
            condition=condition,
            retry_count=0,
            max_retries=retry_count,
            timeout=timeout
        )
        self.nodes.append(node)
        return node_id

    def get_node(self, node_id: str) -> Optional[WorkflowNode]:
        """获取节点"""
        for node in self.nodes:
            if node.id == node_id or node.name == node_id:
                return node
        return None

    def reset(self):
        """重置所有节点状态"""
        for node in self.nodes:
            node.reset()


@dataclass
class WorkflowExecution:
    """工作流执行实例"""
    id: str
    workflow: WorkflowDefinition
    status: WorkflowStatus = WorkflowStatus.PENDING
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    context: Dict[str, Any] = field(default_factory=dict)
    results: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    @property
    def duration(self) -> float:
        """执行耗时（毫秒）"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time) * 1000
        return 0.0


class WorkflowEngine:
    """
    工作流编排引擎

    功能:
    - 工作流定义与注册
    - 节点依赖解析
    - 并行/串行执行
    - 条件分支控制
    - 超时与重试
    """

    def __init__(self, max_concurrent_nodes: int = 5):
        """
        初始化工作流引擎

        Args:
            max_concurrent_nodes: 最大并发节点数
        """
        self._workflows: Dict[str, WorkflowDefinition] = {}
        self._executions: Dict[str, WorkflowExecution] = {}
        self._max_concurrent_nodes = max_concurrent_nodes
        self._node_handlers: Dict[str, Callable] = {}

    def register_workflow(
        self,
        name: str,
        description: str = "",
        workflow_id: Optional[str] = None
    ) -> WorkflowDefinition:
        """
        注册工作流

        Args:
            name: 工作流名称
            description: 工作流描述
            workflow_id: 工作流 ID（可选）

        Returns:
            WorkflowDefinition: 工作流定义对象
        """
        wf_id = workflow_id or str(uuid.uuid4())
        workflow = WorkflowDefinition(
            id=wf_id,
            name=name,
            description=description
        )
        self._workflows[name] = workflow
        logger.info(f"Registered workflow: {name}")
        return workflow

    def get_workflow(self, name: str) -> Optional[WorkflowDefinition]:
        """获取工作流定义"""
        return self._workflows.get(name)

    def list_workflows(self) -> List[Dict[str, str]]:
        """列出所有工作流"""
        return [
            {
                "id": wf.id,
                "name": wf.name,
                "description": wf.description,
                "nodes_count": len(wf.nodes)
            }
            for wf in self._workflows.values()
        ]

    def unregister_workflow(self, name: str) -> bool:
        """注销工作流"""
        if name in self._workflows:
            del self._workflows[name]
            logger.info(f"Unregistered workflow: {name}")
            return True
        return False

    def register_node_handler(self, name: str, handler: Callable) -> None:
        """注册节点处理器"""
        self._node_handlers[name] = handler
        logger.info(f"Registered node handler: {name}")

    async def execute(
        self,
        workflow_name: str,
        initial_context: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None
    ) -> WorkflowExecution:
        """
        执行工作流

        Args:
            workflow_name: 工作流名称
            initial_context: 初始上下文
            timeout: 总超时时间（秒）

        Returns:
            WorkflowExecution: 执行结果
        """
        workflow = self._workflows.get(workflow_name)
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_name}")

        # 重置工作流状态
        workflow.reset()

        # 创建执行实例
        execution = WorkflowExecution(
            id=str(uuid.uuid4()),
            workflow=workflow,
            context=initial_context or {}
        )
        self._executions[execution.id] = execution

        execution.status = WorkflowStatus.RUNNING
        execution.start_time = time.time()

        try:
            # 执行工作流
            await self._execute_workflow(execution, timeout)
            execution.status = WorkflowStatus.COMPLETED
        except asyncio.TimeoutError:
            execution.status = WorkflowStatus.FAILED
            execution.error = f"Workflow timed out after {timeout} seconds"
            logger.error(execution.error)
        except Exception as e:
            execution.status = WorkflowStatus.FAILED
            execution.error = str(e)
            logger.error(f"Workflow execution failed: {e}")
        finally:
            execution.end_time = time.time()

        return execution

    async def _execute_workflow(
        self,
        execution: WorkflowExecution,
        timeout: Optional[float] = None
    ) -> None:
        """执行工作流"""
        workflow = execution.workflow
        completed_nodes = set()

        # 创建超时上下文
        if timeout:
            try:
                await asyncio.wait_for(
                    self._execute_nodes_loop(workflow, execution, completed_nodes),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                raise
        else:
            await self._execute_nodes_loop(workflow, execution, completed_nodes)

    async def _execute_nodes_loop(
        self,
        workflow: WorkflowDefinition,
        execution: WorkflowExecution,
        completed_nodes: set
    ) -> None:
        """循环执行节点"""
        while len(completed_nodes) < len(workflow.nodes):
            # 获取可执行的节点
            ready_nodes = self._get_ready_nodes(workflow, completed_nodes)

            if not ready_nodes:
                # 没有可执行的节点，检查是否有未完成的节点
                pending_nodes = [
                    n for n in workflow.nodes
                    if n.id not in completed_nodes and n.status != NodeStatus.SKIPPED
                ]
                if not pending_nodes:
                    break
                # 等待其他节点完成
                await asyncio.sleep(0.1)
                continue

            # 并发执行可执行的节点
            tasks = [
                self._execute_node(node, execution)
                for node in ready_nodes[:self._max_concurrent_nodes]
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for node, result in zip(ready_nodes, results):
                if isinstance(result, Exception):
                    node.status = NodeStatus.FAILED
                    node.error = str(result)
                else:
                    completed_nodes.add(node.id)
                    execution.results[node.name] = node.result

    def _get_ready_nodes(
        self,
        workflow: WorkflowDefinition,
        completed_nodes: set
    ) -> List[WorkflowNode]:
        """获取可执行的节点"""
        ready = []
        for node in workflow.nodes:
            if node.id in completed_nodes:
                continue
            if node.status in (NodeStatus.RUNNING, NodeStatus.FAILED):
                continue

            # 检查依赖
            deps_satisfied = True
            for dep_id in node.dependencies:
                dep_node = workflow.get_node(dep_id)
                if dep_node:
                    if dep_node.status != NodeStatus.COMPLETED:
                        deps_satisfied = False
                        break
                elif dep_id not in completed_nodes:
                    deps_satisfied = False
                    break

            if deps_satisfied:
                ready.append(node)

        return ready

    async def _execute_node(
        self,
        node: WorkflowNode,
        execution: WorkflowExecution
    ) -> Any:
        """执行单个节点"""
        node.status = NodeStatus.RUNNING

        # 检查条件
        if node.condition:
            if not node.condition(execution.context):
                node.status = NodeStatus.SKIPPED
                logger.info(f"Node {node.name} skipped due to condition")
                return None

        # 执行节点
        attempt = 0
        while attempt <= node.max_retries:
            try:
                result = await asyncio.wait_for(
                    self._call_node_handler(node, execution),
                    timeout=node.timeout
                )
                node.result = result
                node.status = NodeStatus.COMPLETED
                logger.info(f"Node {node.name} completed successfully")
                return result
            except asyncio.TimeoutError:
                node.error = f"Node timed out after {node.timeout} seconds"
                logger.warning(f"Node {node.name} timed out, attempt {attempt + 1}")
            except Exception as e:
                node.error = str(e)
                logger.warning(f"Node {node.name} failed: {e}, attempt {attempt + 1}")

            attempt += 1
            node.retry_count = attempt

            if attempt <= node.max_retries:
                await asyncio.sleep(0.1 * attempt)  # 指数退避

        node.status = NodeStatus.FAILED
        raise Exception(f"Node {node.name} failed after {attempt} attempts: {node.error}")

    async def _call_node_handler(
        self,
        node: WorkflowNode,
        execution: WorkflowExecution
    ) -> Any:
        """调用节点处理器"""
        handler = node.handler

        # 如果没有指定 handler，查找注册的处理器
        if not handler:
            handler = self._node_handlers.get(node.name)

        if not handler:
            # 返回当前上下文
            return execution.context

        # 调用 handler
        if asyncio.iscoroutinefunction(handler):
            return await handler(execution.context)
        else:
            return handler(execution.context)

    def get_execution(self, execution_id: str) -> Optional[WorkflowExecution]:
        """获取执行实例"""
        return self._executions.get(execution_id)

    def cancel_execution(self, execution_id: str) -> bool:
        """取消执行"""
        execution = self._executions.get(execution_id)
        if execution and execution.status == WorkflowStatus.RUNNING:
            execution.status = WorkflowStatus.CANCELLED
            execution.end_time = time.time()
            logger.info(f"Cancelled execution: {execution_id}")
            return True
        return False

    def create_chain(
        self,
        workflow_name: str,
        nodes: List[Dict[str, Any]]
    ) -> WorkflowDefinition:
        """
        创建链式工作流

        Args:
            workflow_name: 工作流名称
            nodes: 节点列表，每个节点包含 name, handler, timeout 等

        Returns:
            WorkflowDefinition: 工作流定义
        """
        workflow = self.register_workflow(workflow_name)

        prev_node_id = None
        for node_config in nodes:
            dependencies = [prev_node_id] if prev_node_id else []
            node_id = workflow.add_node(
                name=node_config.get("name", f"node_{len(workflow.nodes)}"),
                handler=node_config.get("handler"),
                dependencies=dependencies,
                timeout=node_config.get("timeout", 30.0)
            )
            prev_node_id = node_id

        return workflow

    def create_parallel(
        self,
        workflow_name: str,
        parallel_nodes: List[Dict[str, Any]],
        merge_handler: Optional[Callable] = None
    ) -> WorkflowDefinition:
        """
        创建并行工作流

        Args:
            workflow_name: 工作流名称
            parallel_nodes: 并行节点列表
            merge_handler: 合并结果的处理器

        Returns:
            WorkflowDefinition: 工作流定义
        """
        workflow = self.register_workflow(workflow_name)

        # 添加起始节点
        start_id = workflow.add_node(name="start")

        # 添加并行节点
        parallel_ids = []
        for node_config in parallel_nodes:
            node_id = workflow.add_node(
                name=node_config.get("name", f"parallel_{len(parallel_ids)}"),
                handler=node_config.get("handler"),
                dependencies=[start_id],
                timeout=node_config.get("timeout", 30.0)
            )
            parallel_ids.append(node_id)

        # 添加合并节点
        if merge_handler:
            workflow.add_node(
                name="merge",
                handler=merge_handler,
                dependencies=parallel_ids
            )

        return workflow
