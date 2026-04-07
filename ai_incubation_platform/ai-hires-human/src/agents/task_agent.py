"""
Task Agent - AI 任务代理，负责任务发布、匹配和验收的自主决策
"""
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from .deerflow_client import DeerFlowClient, local_runner

logger = logging.getLogger(__name__)


class TaskAgent:
    """
    任务代理 - AI Native 核心引擎

    职责：
    1. 解析用户自然语言意图
    2. 自主决策任务发布参数
    3. 调用工具执行任务操作
    4.  orchestrate 多步工作流
    """

    def __init__(self, deerflow_api_key: Optional[str] = None):
        """
        初始化任务代理

        Args:
            deerflow_api_key: DeerFlow API 密钥
        """
        self.df_client = DeerFlowClient(api_key=deerflow_api_key)
        self.fallback_enabled = True
        self._context: Dict[str, Any] = {}

    async def run_workflow(self, name: str, **input_data) -> Dict[str, Any]:
        """
        运行工作流，支持 DeerFlow 和本地降级

        Args:
            name: 工作流名称
            **input_data: 输入参数

        Returns:
            工作流执行结果
        """
        try:
            if self.df_client.is_available():
                logger.info(f"Running workflow '{name}' via DeerFlow")
                return await self.df_client.run_workflow(name, **input_data)
            elif self.fallback_enabled:
                logger.info(f"Running workflow '{name}' locally (DeerFlow fallback)")
                return await local_runner.run(name, **input_data)
            else:
                raise RuntimeError("DeerFlow unavailable and fallback disabled")
        except Exception as e:
            logger.error(f"Failed to run workflow {name}: {e}")
            raise

    async def run_tool(self, name: str, **input_data) -> Dict[str, Any]:
        """
        运行工具

        Args:
            name: 工具名称
            **input_data: 输入参数

        Returns:
            工具执行结果
        """
        try:
            if self.df_client.is_available():
                logger.info(f"Running tool '{name}' via DeerFlow")
                return await self.df_client.run_tool(name, **input_data)
            elif self.fallback_enabled:
                from tools import TOOLS_REGISTRY
                if name not in TOOLS_REGISTRY:
                    raise ValueError(f"Tool '{name}' not found")
                tool = TOOLS_REGISTRY[name]
                return await tool["handler"](**input_data)
            else:
                raise RuntimeError("DeerFlow unavailable and fallback disabled")
        except Exception as e:
            logger.error(f"Failed to run tool {name}: {e}")
            raise

    async def parse_intent(self, natural_language: str) -> Dict[str, Any]:
        """
        解析用户自然语言意图

        Args:
            natural_language: 用户自然语言输入

        Returns:
            结构化的意图参数
        """
        logger.info(f"Parsing intent: {natural_language}")

        # 使用 DeerFlow 进行意图解析
        if self.df_client.is_available():
            try:
                response = await self.df_client.chat(
                    message=f"请分析以下用户意图，提取任务发布参数：{natural_language}",
                    context={"action": "parse_task_intent"}
                )
                return response.get("parameters", {})
            except Exception as e:
                logger.warning(f"DeerFlow intent parsing failed: {e}, using local fallback")

        # 本地降级：使用简单的规则解析
        return self._local_intent_parse(natural_language)

    def _local_intent_parse(self, text: str) -> Dict[str, Any]:
        """
        本地意图解析（降级方案）

        从自然语言中提取任务参数
        """
        text_lower = text.lower()

        # 提取技能需求
        skills = {}
        skill_keywords = {
            "线下采集": ["线下", "实地", "现场", "拍照", "采集"],
            "数据标注": ["标注", "标记", "分类"],
            "文案写作": ["写作", "文案", "文章"],
            "翻译": ["翻译", "语种"],
            "客服": ["客服", "接待", "回复"],
        }
        for skill, keywords in skill_keywords.items():
            for kw in keywords:
                if kw in text_lower:
                    skills[skill] = "基础"
                    break

        # 提取交互类型
        interaction_type = "digital"
        if any(kw in text_lower for kw in ["线下", "实地", "现场", "物理"]):
            interaction_type = "physical"
        elif any(kw in text_lower for kw in ["混合", "线上线下"]):
            interaction_type = "hybrid"

        # 提取优先级
        priority = "medium"
        if any(kw in text_lower for kw in ["急", "尽快", "马上", "urgent"]):
            priority = "urgent"
        elif any(kw in text_lower for kw in ["高优先级", "重要", "high"]):
            priority = "high"
        elif any(kw in text_lower for kw in ["低优先级", "不急", "low"]):
            priority = "low"

        # 提取地点
        location = None
        location_keywords = ["北京", "上海", "广州", "深圳", "杭州", "地点", "城市"]
        for kw in location_keywords:
            if kw in text:
                location = kw
                break

        # 提取报酬（简单的数字提取）
        import re
        reward_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:元 | 块|CNY|USD)?', text)
        reward_amount = float(reward_match.group(1)) if reward_match else 100.0

        return {
            "title": text[:50] if len(text) > 50 else text,
            "description": text,
            "required_skills": skills,
            "interaction_type": interaction_type,
            "priority": priority,
            "location_hint": location,
            "reward_amount": reward_amount,
        }

    async def post_task_from_natural_language(
        self,
        user_id: str,
        natural_language: str,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        从自然语言发布任务

        Args:
            user_id: 用户 ID
            natural_language: 自然语言描述
            context: 上下文信息

        Returns:
            任务发布结果
        """
        logger.info(f"Posting task from natural language for user {user_id}")

        # 1. 解析意图
        params = await self.parse_intent(natural_language)

        # 2. 合并用户提供的参数
        params["ai_employer_id"] = user_id
        params["capability_gap"] = params.get("capability_gap", "AI 无法完成此类任务，需要真人协助")

        # 3. 调用工具发布任务
        result = await self.run_tool("post_task", **params)

        # 4. 记录审计日志
        await self._log_audit(
            actor=user_id,
            action="post_task",
            resource=result.get("task_id"),
            request={"natural_language": natural_language, "params": params},
            response=result,
            status="success"
        )

        return result

    async def match_workers_for_task(
        self,
        task_id: str,
        auto_assign: bool = False
    ) -> Dict[str, Any]:
        """
        为任务匹配工人

        Args:
            task_id: 任务 ID
            auto_assign: 是否自动分配（高置信度时）

        Returns:
            匹配结果
        """
        logger.info(f"Matching workers for task {task_id}")

        result = await self.run_tool(
            "match_workers",
            task_id=task_id,
            limit=10
        )

        # 如果启用自动分配且有高置信度匹配
        if auto_assign and result.get("matches"):
            best_match = result["matches"][0]
            if best_match.get("confidence", 0) >= 0.8:
                await self.run_tool(
                    "assign_worker",
                    task_id=task_id,
                    worker_id=best_match["worker_id"]
                )
                result["auto_assigned"] = True

        return result

    async def verify_delivery(
        self,
        task_id: str,
        delivery_content: str,
        auto_approve_threshold: float = 0.9
    ) -> Dict[str, Any]:
        """
        验证交付物

        Args:
            task_id: 任务 ID
            delivery_content: 交付内容
            auto_approve_threshold: 自动通过阈值

        Returns:
            验证结果
        """
        logger.info(f"Verifying delivery for task {task_id}")

        result = await self.run_tool(
            "verify_delivery",
            task_id=task_id,
            content=delivery_content
        )

        # 高置信度时自动通过
        if result.get("confidence", 0) >= auto_approve_threshold:
            await self.run_tool(
                "approve_task",
                task_id=task_id,
                reason=f"AI 验收通过（置信度：{result['confidence']:.2f}）"
            )
            result["auto_approved"] = True

        return result

    async def _log_audit(
        self,
        actor: str,
        action: str,
        resource: Optional[str],
        request: Dict,
        response: Dict,
        status: str
    ) -> None:
        """记录审计日志"""
        try:
            from database import AsyncSessionLocal
            from models.audit_log import AuditLog

            async with AsyncSessionLocal() as db:
                audit_log = AuditLog(
                    id=str(uuid.uuid4()),
                    actor=actor,
                    action=action,
                    resource=resource,
                    request=str(request)[:1000],  # 限制长度
                    response=str(response)[:1000],
                    status=status,
                    trace_id=str(uuid.uuid4())
                )
                db.add(audit_log)
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to log audit: {e}")

    def set_context(self, key: str, value: Any) -> None:
        """设置上下文"""
        self._context[key] = value

    def get_context(self, key: str, default: Any = None) -> Any:
        """获取上下文"""
        return self._context.get(key, default)

    def clear_context(self) -> None:
        """清除上下文"""
        self._context.clear()


# 全局任务代理实例
task_agent = TaskAgent()
