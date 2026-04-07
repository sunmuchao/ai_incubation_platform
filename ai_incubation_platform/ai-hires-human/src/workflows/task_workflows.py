"""
任务工作流 - AI Agent 多步工作流编排

支持两种模式：
1. DeerFlow 模式：当 DeerFlow 服务可用时，使用 @workflow 和 @step 装饰器
2. 本地降级模式：当 DeerFlow 不可用时，使用本地 execute 方法
"""
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# 尝试导入 DeerFlow，如果不可用则使用本地模式
try:
    from deerflow import workflow, step
    DEERFLOW_AVAILABLE = True
except ImportError:
    DEERFLOW_AVAILABLE = False
    # 定义本地装饰器占位符
    def workflow(name=None):
        def decorator(cls):
            return cls
        return decorator

    def step(func):
        return func


class AutoPostAndMatchWorkflow:
    """
    自主发布和匹配工作流

    流程：
    1. 解析用户自然语言意图
    2. 创建并发布任务
    3. 智能匹配工人
    4. 自动分配（高置信度时）
    5. 记录审计日志
    """

    def __init__(self):
        self._context: Dict[str, Any] = {}

    async def parse_intent(self, input_data: Dict) -> Dict:
        """Step 1: 解析用户自然语言意图"""
        natural_language = input_data.get("natural_language", "")
        user_id = input_data.get("user_id", "anonymous")

        logger.info(f"Parsing intent from user {user_id}: {natural_language[:100]}...")

        # 调用 Agent 进行意图解析
        from agents.task_agent import task_agent
        params = await task_agent.parse_intent(natural_language)

        # 合并用户 ID
        params["ai_employer_id"] = user_id

        self._context["intent_params"] = params

        return {
            "parsed_params": params,
            "user_id": user_id
        }

    async def create_task(self, step1_result: Dict) -> Dict:
        """Step 2: 创建并发布任务"""
        params = step1_result.get("parsed_params", {})
        user_id = step1_result.get("user_id", "anonymous")

        logger.info(f"Creating task for user {user_id}")

        # 确保必填字段
        if "title" not in params:
            params["title"] = params.get("description", "未命名任务")[:50]
        if "description" not in params:
            params["description"] = params.get("title", "无描述")

        # 调用任务工具
        from tools.task_tools import post_task
        result = await post_task(**params)

        if result.get("status") == "error":
            raise ValueError(f"Failed to create task: {result.get('message')}")

        task_id = result.get("task_id")
        self._context["task_id"] = task_id

        return {
            "task_id": task_id,
            "task_status": result.get("status"),
            "message": result.get("message")
        }

    async def match_workers(self, step2_result: Dict) -> Dict:
        """Step 3: 智能匹配工人"""
        task_id = step2_result.get("task_id")

        if not task_id:
            raise ValueError("Task ID not found in context")

        logger.info(f"Matching workers for task {task_id}")

        from tools.worker_tools import match_workers
        result = await match_workers(task_id=task_id, limit=10)

        matches = result.get("matches", [])

        return {
            "task_id": task_id,
            "matches": matches,
            "total_candidates": result.get("total_candidates", 0)
        }

    async def auto_assign(self, step3_result: Dict) -> Dict:
        """Step 4: 自动分配（高置信度时）"""
        matches = step3_result.get("matches", [])
        task_id = step3_result.get("task_id")

        if not matches:
            return {
                "task_id": task_id,
                "auto_assigned": False,
                "reason": "No matching workers found"
            }

        # 检查最高置信度
        best_match = matches[0]
        confidence = best_match.get("confidence", 0)

        logger.info(f"Best match confidence: {confidence}")

        if confidence >= 0.8:
            # 自动分配
            from tools.worker_tools import assign_worker
            assign_result = await assign_worker(
                task_id=task_id,
                worker_id=best_match["worker_id"],
                auto_assigned=True
            )

            return {
                "task_id": task_id,
                "auto_assigned": True,
                "worker_id": best_match["worker_id"],
                "confidence": confidence,
                "assignment_result": assign_result
            }
        else:
            return {
                "task_id": task_id,
                "auto_assigned": False,
                "reason": f"Confidence {confidence} below threshold 0.8",
                "top_matches": matches[:3]
            }

    async def log_audit(self, step4_result: Dict) -> Dict:
        """Step 5: 记录审计日志"""
        from agents.task_agent import task_agent

        task_id = step4_result.get("task_id")
        action = "auto_post_and_match"

        await task_agent._log_audit(
            actor=self._context.get("user_id", "system"),
            action=action,
            resource=task_id,
            request={"input": self._context.get("intent_params", {})},
            response=step4_result,
            status="success"
        )

        return {
            "workflow_completed": True,
            "task_id": task_id,
            "result": step4_result
        }

    async def execute(self, **input_data) -> Dict[str, Any]:
        """执行工作流（本地模式）"""
        try:
            result1 = await self.parse_intent(input_data)
            result2 = await self.create_task(result1)
            result3 = await self.match_workers(result2)
            result4 = await self.auto_assign(result3)
            final_result = await self.log_audit(result4)

            return final_result
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            return {
                "workflow_completed": False,
                "error": str(e)
            }


class AutoVerifyDeliveryWorkflow:
    """
    自主验收工作流

    流程：
    1. 获取任务和交付内容
    2. 验证交付物质量
    3. 执行反作弊检查
    4. 自动决策（通过/拒绝/人工复核）
    5. 记录审计日志
    """

    def __init__(self):
        self._context: Dict[str, Any] = {}

    async def get_delivery(self, input_data: Dict) -> Dict:
        """Step 1: 获取任务和交付内容"""
        task_id = input_data.get("task_id")
        content = input_data.get("content")

        if not task_id:
            raise ValueError("task_id is required")

        from tools.task_tools import get_task
        task_result = await get_task(task_id)

        return {
            "task_id": task_id,
            "content": content,
            "task_info": task_result
        }

    async def verify_quality(self, step1_result: Dict) -> Dict:
        """Step 2: 验证交付物质量"""
        task_id = step1_result.get("task_id")
        content = step1_result.get("content")

        from tools.verification_tools import verify_delivery
        quality_result = await verify_delivery(
            task_id=task_id,
            content=content
        )

        self._context["quality_result"] = quality_result

        return {
            "task_id": task_id,
            "quality_check": quality_result
        }

    async def check_anti_cheat(self, step2_result: Dict) -> Dict:
        """Step 3: 执行反作弊检查"""
        task_id = step2_result.get("task_id")

        # 获取任务以获取 worker_id
        from tools.task_tools import get_task
        task_result = await get_task(task_id)
        worker_id = task_result.get("task", {}).get("worker_id", "unknown")
        content = self._context.get("quality_result", {}).get("task_id")

        from tools.verification_tools import check_anti_cheat
        anti_cheat_result = await check_anti_cheat(
            task_id=task_id,
            worker_id=worker_id,
            content=content or ""
        )

        self._context["anti_cheat_result"] = anti_cheat_result

        return {
            "task_id": task_id,
            "anti_cheat_check": anti_cheat_result
        }

    async def make_decision(self, step3_result: Dict) -> Dict:
        """Step 4: 自动决策"""
        quality_result = self._context.get("quality_result", {})
        anti_cheat_result = self._context.get("anti_cheat_result", {})

        task_id = step3_result.get("task_id")

        # 检查作弊
        if anti_cheat_result.get("cheat_detected", False):
            decision = "reject"
            reason = f"作弊检测：{anti_cheat_result.get('checks', {})}"
        elif quality_result.get("confidence", 0) >= 0.9:
            decision = "approve"
            reason = f"高质量交付（置信度：{quality_result.get('confidence')}）"
        elif quality_result.get("confidence", 0) >= 0.6:
            decision = "approve"
            reason = f"合格交付（置信度：{quality_result.get('confidence')}）"
        else:
            decision = "manual_review"
            reason = f"需要人工复核（置信度：{quality_result.get('confidence')}）"

        # 执行决策
        if decision == "approve":
            from tools.verification_tools import approve_task
            action_result = await approve_task(task_id=task_id, reason=reason)
        elif decision == "reject":
            from tools.verification_tools import reject_task
            action_result = await reject_task(task_id=task_id, reason=reason)
        else:
            from tools.verification_tools import request_manual_review
            action_result = await request_manual_review(
                task_id=task_id,
                reason=reason
            )

        return {
            "task_id": task_id,
            "decision": decision,
            "reason": reason,
            "action_result": action_result,
            "quality_confidence": quality_result.get("confidence"),
            "cheat_detected": anti_cheat_result.get("cheat_detected", False)
        }

    async def log_audit(self, step4_result: Dict) -> Dict:
        """Step 5: 记录审计日志"""
        from agents.task_agent import task_agent

        await task_agent._log_audit(
            actor="system",
            action="auto_verify_delivery",
            resource=step4_result.get("task_id"),
            request={"task_id": step4_result.get("task_id")},
            response=step4_result,
            status="success"
        )

        return {
            "workflow_completed": True,
            "result": step4_result
        }

    async def execute(self, **input_data) -> Dict[str, Any]:
        """执行工作流（本地模式）"""
        try:
            result1 = await self.get_delivery(input_data)
            result2 = await self.verify_quality(result1)
            result3 = await self.check_anti_cheat(result2)
            result4 = await self.make_decision(result3)
            final_result = await self.log_audit(result4)

            return final_result
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            return {
                "workflow_completed": False,
                "error": str(e)
            }
