"""
P9-002: 自动化工作流引擎服务

功能:
1. 工作流定义与验证
2. 工作流执行引擎
3. 节点调度与执行
4. 异常处理与重试
5. 执行历史记录
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
import uuid

from models.p9_models import (
    Workflow,
    WorkflowNode,
    WorkflowEdge,
    WorkflowStatus,
    WorkflowExecution,
    NodeExecution,
    ExecutionStatus,
    RetryPolicy,
    RetryPolicyType,
    ExecuteWorkflowRequest,
)

logger = logging.getLogger(__name__)


class WorkflowEngine:
    """
    工作流引擎

    基于 DAG (有向无环图) 的工作流执行引擎
    """

    def __init__(self):
        # 内存存储工作流定义
        self._workflows: Dict[str, Workflow] = {}
        # 内存存储执行记录
        self._executions: Dict[str, WorkflowExecution] = {}
        # 节点执行器映射
        self._node_executors: Dict[str, Callable] = {}
        # 注册默认执行器
        self._register_default_executors()

    def _register_default_executors(self):
        """注册默认节点执行器"""
        # 实际应对接 AI 员工执行服务
        self._node_executors["ai_task"] = self._execute_ai_task

    async def _execute_ai_task(self, node: WorkflowNode, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行 AI 任务节点

        实际应调用 AI 员工服务执行任务
        """
        # 模拟执行
        await asyncio.sleep(0.1)  # 模拟耗时

        return {
            "status": "completed",
            "result": f"Task '{node.name}' executed with input: {input_data}",
            "ai_employee_id": node.ai_employee_id,
        }

    def register_executor(self, node_type: str, executor: Callable):
        """
        注册节点执行器

        Args:
            node_type: 节点类型
            executor: 执行函数
        """
        self._node_executors[node_type] = executor
        logger.info(f"Registered executor for node type: {node_type}")

    def validate_workflow(self, workflow: Workflow) -> tuple[bool, List[str]]:
        """
        验证工作流定义

        Args:
            workflow: 工作流定义

        Returns:
            (是否有效，错误列表)
        """
        errors = []

        # 检查节点 ID 唯一性
        node_ids = [node.id for node in workflow.nodes]
        if len(node_ids) != len(set(node_ids)):
            errors.append("节点 ID 必须唯一")

        # 检查依赖关系
        node_id_set = set(node_ids)
        for node in workflow.nodes:
            for dep in node.dependencies:
                if dep not in node_id_set:
                    errors.append(f"节点 {node.id} 依赖不存在的节点：{dep}")

        # 检查循环依赖 (拓扑排序)
        if not self._topological_sort(workflow.nodes):
            errors.append("工作流存在循环依赖")

        # 检查边
        for edge in workflow.edges:
            if edge.source_id not in node_id_set:
                errors.append(f"边的源节点不存在：{edge.source_id}")
            if edge.target_id not in node_id_set:
                errors.append(f"边的目标节点不存在：{edge.target_id}")

        return len(errors) == 0, errors

    def _topological_sort(self, nodes: List[WorkflowNode]) -> bool:
        """
        拓扑排序检测循环依赖

        Returns:
            是否无环
        """
        # 构建邻接表
        graph = {node.id: [] for node in nodes}
        in_degree = {node.id: 0 for node in nodes}

        for node in nodes:
            for dep in node.dependencies:
                if dep in graph:
                    graph[dep].append(node.id)
                    in_degree[node.id] += 1

        # Kahn 算法
        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        visited = 0

        while queue:
            node_id = queue.pop(0)
            visited += 1
            for neighbor in graph[node_id]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return visited == len(nodes)

    def get_execution_order(self, workflow: Workflow) -> List[str]:
        """
        获取执行顺序（拓扑排序）

        Args:
            workflow: 工作流定义

        Returns:
            节点 ID 列表（按执行顺序）
        """
        nodes = workflow.nodes
        graph = {node.id: [] for node in nodes}
        in_degree = {node.id: 0 for node in nodes}

        for node in nodes:
            for dep in node.dependencies:
                if dep in graph:
                    graph[dep].append(node.id)
                    in_degree[node.id] += 1

        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        result = []

        while queue:
            # 按节点名称排序以保证确定性
            queue.sort()
            node_id = queue.pop(0)
            result.append(node_id)
            for neighbor in graph[node_id]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return result

    async def execute_workflow(
        self,
        workflow_id: str,
        request: ExecuteWorkflowRequest,
        tenant_id: str,
        triggered_by: str
    ) -> WorkflowExecution:
        """
        执行工作流

        Args:
            workflow_id: 工作流 ID
            request: 执行请求
            tenant_id: 租户 ID
            triggered_by: 触发者 ID

        Returns:
            WorkflowExecution: 执行记录
        """
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"工作流不存在：{workflow_id}")

        if workflow.status != WorkflowStatus.ACTIVE:
            raise ValueError(f"工作流未激活：{workflow.status}")

        # 创建执行记录
        execution_id = str(uuid.uuid4())
        execution = WorkflowExecution(
            id=execution_id,
            workflow_id=workflow_id,
            workflow_version=workflow.version,
            tenant_id=tenant_id,
            triggered_by=triggered_by,
            trigger_type=request.trigger_type,
            status=ExecutionStatus.RUNNING,
            input_data=request.input_data,
            node_executions=[],
            started_at=datetime.now()
        )

        self._executions[execution_id] = execution
        logger.info(f"Starting workflow execution: {execution_id}, workflow: {workflow_id}")

        # 获取执行顺序
        execution_order = self.get_execution_order(workflow)
        node_map = {node.id: node for node in workflow.nodes}

        # 执行节点
        node_results: Dict[str, Dict[str, Any]] = {}

        try:
            for node_id in execution_order:
                node = node_map[node_id]

                # 检查依赖是否完成
                if not self._check_dependencies_satisfied(node, node_results):
                    if workflow.error_handling == "fail_fast":
                        raise RuntimeError(f"节点 {node_id} 的依赖未满足")
                    continue

                # 准备输入数据
                node_input = self._prepare_node_input(node, request.input_data, node_results)

                # 执行节点
                node_execution = await self._execute_node_with_retry(node, node_input)
                execution.node_executions.append(node_execution)

                if node_execution.status == ExecutionStatus.FAILED:
                    if workflow.error_handling == "fail_fast":
                        raise RuntimeError(f"节点 {node_id} 执行失败：{node_execution.error_message}")
                    elif workflow.error_handling == "continue":
                        continue

                # 保存结果
                if node_execution.output_data:
                    node_results[node_id] = node_execution.output_data

            # 所有节点执行完成
            execution.status = ExecutionStatus.COMPLETED
            execution.output_data = node_results
            execution.completed_at = datetime.now()
            execution.execution_time = (execution.completed_at - execution.started_at).total_seconds()

            logger.info(f"Workflow execution completed: {execution_id}")

        except Exception as e:
            execution.status = ExecutionStatus.FAILED
            execution.error_message = str(e)
            execution.completed_at = datetime.now()
            execution.execution_time = (execution.completed_at - execution.started_at).total_seconds()

            logger.error(f"Workflow execution failed: {execution_id}, error: {e}")

        return execution

    def _check_dependencies_satisfied(
        self,
        node: WorkflowNode,
        node_results: Dict[str, Dict[str, Any]]
    ) -> bool:
        """检查依赖是否满足"""
        for dep_id in node.dependencies:
            if dep_id not in node_results:
                return False
        return True

    def _prepare_node_input(
        self,
        node: WorkflowNode,
        global_input: Dict[str, Any],
        node_results: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        准备节点输入数据

        根据 input_mapping 将全局输入和上游输出映射到节点输入
        """
        node_input = {}

        # 映射全局输入
        for target_key, source_key in node.input_mapping.items():
            if source_key.startswith("input."):
                # 来自全局输入
                global_key = source_key[6:]  # 去掉 "input." 前缀
                if global_key in global_input:
                    node_input[target_key] = global_input[global_key]
            elif source_key.startswith("node."):
                # 来自上游节点输出
                parts = source_key[5:].split(".")  # 去掉 "node." 前缀
                if len(parts) == 2:
                    upstream_node_id, output_key = parts
                    if upstream_node_id in node_results and output_key in node_results[upstream_node_id]:
                        node_input[target_key] = node_results[upstream_node_id][output_key]

        return node_input

    async def _execute_node_with_retry(
        self,
        node: WorkflowNode,
        input_data: Dict[str, Any]
    ) -> NodeExecution:
        """
        执行节点（带重试）

        Args:
            node: 节点定义
            input_data: 输入数据

        Returns:
            NodeExecution: 节点执行记录
        """
        node_execution = NodeExecution(
            node_id=node.id,
            node_name=node.name,
            status=ExecutionStatus.RUNNING,
            input_data=input_data,
            ai_employee_id=node.ai_employee_id,
            started_at=datetime.now()
        )

        retry_policy = node.retry_policy
        max_attempts = 1 + retry_policy.max_retries

        for attempt in range(max_attempts):
            try:
                # 获取执行器
                executor = self._node_executors.get(node.node_type.value)
                if not executor:
                    raise ValueError(f"未知的节点类型：{node.node_type}")

                # 执行
                if asyncio.iscoroutinefunction(executor):
                    output_data = await executor(node, input_data)
                else:
                    output_data = executor(node, input_data)

                # 执行成功
                node_execution.status = ExecutionStatus.COMPLETED
                node_execution.output_data = output_data
                node_execution.completed_at = datetime.now()
                node_execution.execution_time = (node_execution.completed_at - node_execution.started_at).total_seconds()

                logger.info(f"Node execution completed: {node.name}")
                return node_execution

            except Exception as e:
                node_execution.retry_count = attempt
                node_execution.error_message = str(e)

                if attempt < max_attempts - 1:
                    # 等待重试
                    wait_time = self._calculate_retry_wait(retry_policy, attempt)
                    logger.warning(f"Node {node.name} failed, retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    # 最终失败
                    node_execution.status = ExecutionStatus.FAILED
                    node_execution.completed_at = datetime.now()
                    node_execution.execution_time = (node_execution.completed_at - node_execution.started_at).total_seconds()

                    logger.error(f"Node execution failed after {max_attempts} attempts: {node.name}")
                    return node_execution

        return node_execution

    def _calculate_retry_wait(self, policy: RetryPolicy, attempt: int) -> int:
        """计算重试等待时间"""
        if policy.policy_type == RetryPolicyType.FIXED:
            return policy.fixed_interval_seconds
        elif policy.policy_type == RetryPolicyType.EXPONENTIAL:
            wait = policy.exponential_base ** attempt
            return min(int(wait), policy.exponential_max_seconds)
        else:
            return 0

    def save_workflow(self, workflow: Workflow) -> tuple[bool, str]:
        """
        保存工作流

        Args:
            workflow: 工作流定义

        Returns:
            (成功，消息)
        """
        # 验证
        is_valid, errors = self.validate_workflow(workflow)
        if not is_valid:
            return False, f"工作流验证失败：{', '.join(errors)}"

        # 保存
        self._workflows[workflow.id] = workflow
        logger.info(f"Workflow saved: {workflow.id}")

        return True, f"工作流 {workflow.id} 保存成功"

    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """获取工作流定义"""
        return self._workflows.get(workflow_id)

    def list_workflows(
        self,
        tenant_id: str,
        status: Optional[WorkflowStatus] = None
    ) -> List[Workflow]:
        """
        获取工作流列表

        Args:
            tenant_id: 租户 ID
            status: 可选，状态筛选

        Returns:
            工作流列表
        """
        workflows = [w for w in self._workflows.values() if w.tenant_id == tenant_id]

        if status:
            workflows = [w for w in workflows if w.status == status]

        return workflows

    def activate_workflow(self, workflow_id: str) -> tuple[bool, str]:
        """激活工作流"""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return False, f"工作流不存在：{workflow_id}"

        workflow.status = WorkflowStatus.ACTIVE
        workflow.updated_at = datetime.now()

        return True, f"工作流 {workflow_id} 已激活"

    def archive_workflow(self, workflow_id: str) -> tuple[bool, str]:
        """归档工作流"""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return False, f"工作流不存在：{workflow_id}"

        workflow.status = WorkflowStatus.ARCHIVED
        workflow.updated_at = datetime.now()

        return True, f"工作流 {workflow_id} 已归档"

    def get_execution(self, execution_id: str) -> Optional[WorkflowExecution]:
        """获取执行记录"""
        return self._executions.get(execution_id)

    def list_executions(
        self,
        workflow_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        status: Optional[ExecutionStatus] = None
    ) -> List[WorkflowExecution]:
        """
        获取执行记录列表

        Args:
            workflow_id: 可选，工作流 ID 筛选
            tenant_id: 可选，租户 ID 筛选
            status: 可选，状态筛选

        Returns:
            执行记录列表
        """
        executions = list(self._executions.values())

        if workflow_id:
            executions = [e for e in executions if e.workflow_id == workflow_id]
        if tenant_id:
            executions = [e for e in executions if e.tenant_id == tenant_id]
        if status:
            executions = [e for e in executions if e.status == status]

        # 按创建时间倒序
        executions.sort(key=lambda x: x.created_at, reverse=True)

        return executions


# 单例
workflow_engine = WorkflowEngine()
