"""
Community Workflows - 社区核心工作流

定义 AI Agent 执行的多步工作流程，包括：
1. 内容审核工作流 - 自主巡查、评估、决策
2. 成员匹配工作流 - 兴趣分析、匹配推荐
3. 内容推荐工作流 - 个性化内容推荐
4. 透明度报告工作流 - 定期生成治理报告

每个工作流由多个步骤组成，支持降级执行。
"""

import logging
import json
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class WorkflowStatus(str, Enum):
    """工作流状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorkflowExecution:
    """工作流执行记录"""
    execution_id: str
    workflow_name: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Optional[Dict[str, Any]] = None
    steps_executed: List[Dict[str, Any]] = field(default_factory=list)
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class StepResult:
    """步骤执行结果"""

    def __init__(self, success: bool, data: Any = None, error: str = None):
        self.success = success
        self.data = data
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
        }


class CommunityWorkflows:
    """
    社区工作流执行器

    提供工作流注册、执行和状态跟踪功能。
    支持 DeerFlow 远程执行和本地降级执行。
    """

    def __init__(self, tools_registry: Dict[str, Any] = None):
        self.tools_registry = tools_registry or {}
        self._workflows: Dict[str, Callable] = {}
        self._executions: Dict[str, WorkflowExecution] = {}
        self._register_default_workflows()

    def _register_default_workflows(self):
        """注册默认工作流"""
        self.register_workflow("moderation", self._execute_moderation_workflow)
        self.register_workflow("matching", self._execute_matching_workflow)
        self.register_workflow("recommendation", self._execute_recommendation_workflow)
        self.register_workflow("transparency_report", self._execute_transparency_report_workflow)

    def register_workflow(self, name: str, handler: Callable):
        """注册工作流"""
        self._workflows[name] = handler
        logger.info(f"Workflow registered: {name}")

    async def execute(self, workflow_name: str, **input_data) -> Dict[str, Any]:
        """执行工作流"""
        if workflow_name not in self._workflows:
            return {"error": f"Workflow not found: {workflow_name}"}

        execution_id = f"exec_{uuid.uuid4().hex[:12]}"
        execution = WorkflowExecution(
            execution_id=execution_id,
            workflow_name=workflow_name,
            input_data=input_data,
            started_at=datetime.now(),
        )
        self._executions[execution_id] = execution

        try:
            execution.status = WorkflowStatus.RUNNING
            handler = self._workflows[workflow_name]
            result = await handler(input_data, execution)
            execution.status = WorkflowStatus.COMPLETED
            execution.output_data = result
            execution.completed_at = datetime.now()
            return result
        except Exception as e:
            execution.status = WorkflowStatus.FAILED
            execution.error_message = str(e)
            execution.completed_at = datetime.now()
            logger.error(f"Workflow execution failed: {workflow_name}: {e}")
            return {"error": str(e)}

    def get_execution(self, execution_id: str) -> Optional[WorkflowExecution]:
        """获取执行记录"""
        return self._executions.get(execution_id)

    def list_workflows(self) -> List[str]:
        """列出所有工作流"""
        return list(self._workflows.keys())

    # ==================== 内容审核工作流 ====================

    async def _execute_moderation_workflow(
        self,
        input_data: Dict[str, Any],
        execution: WorkflowExecution,
    ) -> Dict[str, Any]:
        """
        内容审核工作流

        流程：
        1. 内容获取与预处理
        2. 内容风险分析
        3. 社区规则检查
        4. 用户历史考量
        5. 综合决策
        6. 执行行动（删除/标记/通过）
        7. 通知用户
        8. 记录追溯
        """
        result = {
            "workflow": "moderation",
            "content_id": input_data.get("content_id"),
            "steps": [],
            "final_decision": None,
        }

        # Step 1: 内容分析
        content = input_data.get("content", "")
        if content:
            analysis_result = await self._call_tool("analyze_content", {
                "content": content,
                "content_type": input_data.get("content_type", "post"),
            })
            execution.steps_executed.append({"step": "analyze_content", "result": analysis_result})
            result["steps"].append({"name": "内容分析", "result": analysis_result})

        # Step 2: 规则检查
        if content:
            rule_result = await self._call_tool("check_community_rules", {
                "content": content,
                "rule_category": "all",
            })
            execution.steps_executed.append({"step": "check_rules", "result": rule_result})
            result["steps"].append({"name": "规则检查", "result": rule_result})

        # Step 3: 用户历史
        user_id = input_data.get("user_id")
        if user_id:
            user_history = await self._call_tool("get_user_history", {
                "user_id": user_id,
                "history_type": "all",
            })
            execution.steps_executed.append({"step": "get_user_history", "result": user_history})
            result["steps"].append({"name": "用户历史考量", "result": user_history})

        # Step 4: 综合决策
        decision_result = await self._call_tool("make_moderation_decision", {
            "content_id": input_data.get("content_id"),
            "analysis_result": result["steps"][0]["result"] if len(result["steps"]) > 0 else {},
            "rule_check_result": result["steps"][1]["result"] if len(result["steps"]) > 1 else {},
            "user_history": result["steps"][2]["result"] if len(result["steps"]) > 2 else {},
        })
        execution.steps_executed.append({"step": "make_decision", "result": decision_result})
        result["final_decision"] = decision_result

        # Step 5: 执行行动
        action = decision_result.get("action")
        if action == "remove":
            result["action_taken"] = "content_removed"
        elif action == "flag":
            result["action_taken"] = "flagged_for_review"
        else:
            result["action_taken"] = "approved"

        # Step 6: 通知用户
        if action in ["remove", "flag"] and user_id:
            await self._call_tool("send_notification", {
                "user_id": user_id,
                "notification_type": "content_removed" if action == "remove" else "content_flagged",
                "title": "内容处理通知",
                "message": f"您的内容已被{action == 'remove' and '删除' or '标记审核'}",
            })
            result["notification_sent"] = True

        return result

    # ==================== 成员匹配工作流 ====================

    async def _execute_matching_workflow(
        self,
        input_data: Dict[str, Any],
        execution: WorkflowExecution,
    ) -> Dict[str, Any]:
        """
        成员匹配工作流

        流程：
        1. 分析请求成员的兴趣
        2. 查找匹配的成员
        3. 生成推荐理由
        4. 返回匹配结果
        """
        result = {
            "workflow": "matching",
            "member_id": input_data.get("member_id"),
            "matches": [],
        }

        # Step 1: 兴趣分析
        member_id = input_data.get("member_id")
        if member_id:
            interests = await self._call_tool("analyze_member_interests", {
                "member_id": member_id,
            })
            execution.steps_executed.append({"step": "analyze_interests", "result": interests})
            result["member_interests"] = interests

        # Step 2: 查找匹配
        matches = await self._call_tool("find_matching_members", {
            "member_id": member_id,
            "limit": input_data.get("limit", 10),
        })
        execution.steps_executed.append({"step": "find_matches", "result": matches})
        result["matches"] = matches.get("matches", [])

        return result

    # ==================== 内容推荐工作流 ====================

    async def _execute_recommendation_workflow(
        self,
        input_data: Dict[str, Any],
        execution: WorkflowExecution,
    ) -> Dict[str, Any]:
        """
        内容推荐工作流

        流程：
        1. 分析用户兴趣
        2. 获取推荐内容
        3. 排序和过滤
        4. 返回推荐结果
        """
        result = {
            "workflow": "recommendation",
            "member_id": input_data.get("member_id"),
            "recommendations": [],
        }

        member_id = input_data.get("member_id")
        if member_id:
            # 获取推荐
            recommendations = await self._call_tool("get_content_recommendations", {
                "member_id": member_id,
                "recommendation_type": input_data.get("recommendation_type", "all"),
                "limit": input_data.get("limit", 10),
            })
            execution.steps_executed.append({"step": "get_recommendations", "result": recommendations})
            result["recommendations"] = recommendations.get("recommendations", [])

        return result

    # ==================== 透明度报告工作流 ====================

    async def _execute_transparency_report_workflow(
        self,
        input_data: Dict[str, Any],
        execution: WorkflowExecution,
    ) -> Dict[str, Any]:
        """
        透明度报告工作流

        流程：
        1. 收集决策数据
        2. 统计分析
        3. 生成报告
        """
        period_start = input_data.get("period_start")
        period_end = input_data.get("period_end")

        # 生成报告
        report = await self._call_tool("generate_transparency_report", {
            "period_start": period_start,
            "period_end": period_end,
        })
        execution.steps_executed.append({"step": "generate_report", "result": report})

        return report

    async def _call_tool(self, tool_name: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """调用工具"""
        if tool_name in self.tools_registry:
            tool = self.tools_registry[tool_name]
            if hasattr(tool, "handler"):
                try:
                    return await tool["handler"](input_data)
                except Exception as e:
                    logger.error(f"Tool call failed: {tool_name}: {e}")
                    return {"error": str(e)}

        # 如果工具未注册，返回空结果
        logger.warning(f"Tool not found: {tool_name}")
        return {}


# ==================== 简化的工作流装饰器实现 ====================

class workflow:
    """工作流装饰器（简化实现）"""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.steps = []

    def __call__(self, cls):
        cls.workflow_name = self.name
        cls.workflow_description = self.description
        return cls


class step:
    """步骤装饰器（简化实现）"""

    def __init__(self, func):
        self.func = func
        self.step_name = func.__name__

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self

        async def wrapper(*args, **kwargs):
            return await self.func(obj, *args, **kwargs)

        wrapper.step_name = self.step_name
        return wrapper


# ==================== 具体工作流类定义 ====================

@workflow(name="content_moderation", description="内容审核工作流")
class ModerationWorkflow:
    """
    内容审核工作流

    流程：
    1. 内容获取与预处理
    2. 内容风险分析
    3. 社区规则检查
    4. 用户历史考量
    5. 综合决策
    6. 执行行动
    7. 通知用户
    8. 记录追溯
    """

    def __init__(self, tools_registry: Dict[str, Any] = None):
        self.tools_registry = tools_registry or {}

    @step
    async def fetch_content(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Step 1: 获取内容"""
        return {
            "content_id": input_data.get("content_id"),
            "content": input_data.get("content", ""),
            "content_type": input_data.get("content_type", "post"),
        }

    @step
    async def analyze_content(self, content_data: Dict[str, Any]) -> Dict[str, Any]:
        """Step 2: 内容分析"""
        # 调用分析工具
        return {"risk_score": 0.5, "indicators": []}

    @step
    async def check_rules(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """Step 3: 规则检查"""
        return {"violated": False, "rules": []}

    @step
    async def evaluate_user_history(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Step 4: 用户历史评估"""
        return {"reputation": 1.0, "violations": 0}

    @step
    async def make_decision(
        self,
        analysis: Dict[str, Any],
        rules: Dict[str, Any],
        user_history: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Step 5: 综合决策"""
        return {"action": "approve", "confidence": 0.9}

    @step
    async def execute_action(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """Step 6: 执行行动"""
        return {"executed": True, "action": decision.get("action")}

    @step
    async def notify_user(self, execution_result: Dict[str, Any]) -> Dict[str, Any]:
        """Step 7: 通知用户"""
        return {"notified": True}

    @step
    async def log_trace(self, all_results: Dict[str, Any]) -> Dict[str, Any]:
        """Step 8: 记录追溯"""
        return {"trace_id": str(uuid.uuid4())}


@workflow(name="member_matching", description="成员匹配工作流")
class MatchingWorkflow:
    """
    成员匹配工作流

    流程：
    1. 分析成员兴趣
    2. 查找匹配成员
    3. 生成推荐理由
    4. 返回结果
    """

    @step
    async def analyze_interests(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析兴趣"""
        return {"interests": []}

    @step
    async def find_matches(self, interests: Dict[str, Any]) -> Dict[str, Any]:
        """查找匹配"""
        return {"matches": []}

    @step
    async def generate_reasons(self, matches: Dict[str, Any]) -> Dict[str, Any]:
        """生成推荐理由"""
        return {"reasons": []}


@workflow(name="content_recommendation", description="内容推荐工作流")
class RecommendationWorkflow:
    """
    内容推荐工作流

    流程：
    1. 分析用户兴趣
    2. 获取候选内容
    3. 排序和过滤
    4. 返回推荐
    """

    @step
    async def analyze_user_interests(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析用户兴趣"""
        return {"interests": []}

    @step
    async def get_candidate_content(self, interests: Dict[str, Any]) -> Dict[str, Any]:
        """获取候选内容"""
        return {"candidates": []}

    @step
    async def rank_and_filter(self, candidates: Dict[str, Any]) -> Dict[str, Any]:
        """排序和过滤"""
        return {"ranked": []}


# ==================== 全局工作流实例 ====================

_default_workflow_runner: Optional[CommunityWorkflows] = None


def get_workflow_runner(tools_registry: Dict[str, Any] = None) -> CommunityWorkflows:
    """获取工作流执行器单例"""
    global _default_workflow_runner
    if _default_workflow_runner is None:
        _default_workflow_runner = CommunityWorkflows(tools_registry)
    return _default_workflow_runner


def get_workflow(name: str) -> Optional[Callable]:
    """获取工作流处理器"""
    runner = get_workflow_runner()
    return runner._workflows.get(name)


def list_workflows() -> List[str]:
    """列出所有工作流"""
    runner = get_workflow_runner()
    return runner.list_workflows()
