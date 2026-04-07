"""
代码理解 AI Agent

基于 DeerFlow 2.0 的代码理解代理，支持：
1. 代码解释与分析
2. 架构理解与可视化
3. 问题诊断与建议
"""
import os
import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.deerflow_client import get_deerflow_client, is_deerflow_available
from services.understanding_service import understanding_service

logger = logging.getLogger(__name__)


class CodeUnderstandingAgent:
    """
    代码理解 AI Agent

    作为 DeerFlow 2.0 框架中的核心 Agent，负责：
    1. 理解用户自然语言请求
    2. 自主规划代码分析任务
    3. 调用工具执行分析
    4. 生成解释与可视化
    """

    def __init__(self, project_name: Optional[str] = None):
        """
        初始化 Agent

        Args:
            project_name: 默认项目名称
        """
        self.default_project = project_name or "default"
        self.df_client = get_deerflow_client()
        self.fallback_enabled = True

    async def run(self, message: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        运行 Agent，处理用户请求

        Args:
            message: 用户自然语言消息
            context: 上下文信息（当前文件、选中代码等）

        Returns:
            Agent 响应（包含思考过程、结果、建议等）
        """
        # 尝试使用 DeerFlow 云端 Agent
        if self.df_client.is_available():
            try:
                return await self._run_via_deerflow(message, context)
            except Exception as e:
                logger.warning(f"DeerFlow 调用失败，降级到本地模式：{e}")

        # 降级到本地执行
        if self.fallback_enabled:
            return await self._run_local(message, context)
        else:
            raise RuntimeError("DeerFlow 不可用且本地降级被禁用")

    async def _run_via_deerflow(self, message: str, context: Optional[Dict]) -> Dict[str, Any]:
        """通过 DeerFlow 云端 Agent 执行"""
        # 构建完整的上下文
        full_context = {
            "project": self.default_project,
            **(context or {}),
        }

        # 调用 DeerFlow Agent API
        response = await self.df_client.call_agent(
            agent_name="code_understanding",
            message=message,
            context=full_context
        )

        return self._format_response(response)

    async def _run_local(self, message: str, context: Optional[Dict]) -> Dict[str, Any]:
        """本地降级模式执行"""
        # 简单的意图识别和执行
        intent = self._detect_intent(message)

        thinking_steps = []
        result = {}

        if intent == "explain_code":
            code = context.get("selected_code") if context else None
            if code:
                thinking_steps.append("正在分析代码结构...")
                result = understanding_service.explain(
                    code=code,
                    language=context.get("language", "python"),
                    context=context.get("context")
                )
                thinking_steps.append("已生成代码解释")
            else:
                return {"error": "需要提供代码片段"}

        elif intent == "analyze_module":
            module_path = context.get("file_path") if context else None
            if module_path:
                thinking_steps.append(f"正在分析模块：{module_path}")
                result = understanding_service.summarize_module(module_name=module_path)
                thinking_steps.append("已生成模块摘要")
            else:
                return {"error": "需要提供模块路径"}

        elif intent == "answer_question":
            thinking_steps.append("正在搜索代码库...")
            result = understanding_service.ask(question=message)
            thinking_steps.append(f"找到 {len(result.get('citations', []))} 个相关引用")

        elif intent == "explore_project":
            thinking_steps.append("正在生成项目全局地图...")
            result = understanding_service.global_map(
                project_name=self.default_project,
                repo_hint=context.get("repo_path", ".") if context else "."
            )
            thinking_steps.append("已生成项目架构视图")

        else:
            # 默认当作问答处理
            thinking_steps.append("正在理解您的问题...")
            result = understanding_service.ask(question=message)
            thinking_steps.append("已生成回答")

        return {
            "type": "agent_response",
            "thinking": thinking_steps,
            "content": result,
            "intent": intent,
            "confidence": 0.85,
            "suggestions": self._generate_suggestions(intent, result),
        }

    def _detect_intent(self, message: str) -> str:
        """简单的意图识别"""
        message_lower = message.lower()

        if any(kw in message_lower for kw in ["解释", "explain", "这段代码", "什么意思"]):
            return "explain_code"
        elif any(kw in message_lower for kw in ["模块", "module", "架构", "architecture", "结构"]):
            return "analyze_module"
        elif any(kw in message_lower for kw in ["问题", "question", "如何", "怎么", "where", "what"]):
            return "answer_question"
        elif any(kw in message_lower for kw in ["探索", "explore", "全局", "overview", "地图"]):
            return "explore_project"
        else:
            return "general"

    def _format_response(self, response: Dict) -> Dict[str, Any]:
        """格式化 DeerFlow 响应"""
        return {
            "type": "agent_response",
            "thinking": response.get("thinking", []),
            "content": response.get("answer", {}),
            "intent": response.get("intent", "general"),
            "confidence": response.get("confidence", 0.8),
            "suggestions": response.get("suggestions", []),
        }

    def _generate_suggestions(self, intent: str, result: Dict) -> List[str]:
        """生成下一步建议"""
        suggestions = []

        if intent == "explain_code":
            suggestions = [
                "查看相关函数的定义",
                "分析这个模块的整体结构",
                "搜索类似的实现模式"
            ]
        elif intent == "analyze_module":
            suggestions = [
                "查看模块间的依赖关系",
                "分析调用链",
                "生成模块文档"
            ]
        elif intent == "answer_question":
            suggestions = [
                "查看更多相关代码",
                "深入了解某个引用",
                "询问相关问题"
            ]
        elif intent == "explore_project":
            suggestions = [
                "深入探索特定模块",
                "查看核心入口点",
                "分析技术栈"
            ]

        return suggestions


# 全局 Agent 实例
_code_agent: Optional[CodeUnderstandingAgent] = None


def get_code_agent(project_name: Optional[str] = None) -> CodeUnderstandingAgent:
    """获取代码理解 Agent 单例"""
    global _code_agent
    if _code_agent is None:
        _code_agent = CodeUnderstandingAgent(project_name=project_name)
    return _code_agent
