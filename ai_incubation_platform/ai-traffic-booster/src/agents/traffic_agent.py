"""
Traffic Agent - 流量优化 Agent

基于 DeerFlow 2.0 的自主流量优化 Agent，实现：
- 主动流量监控和异常检测
- 自主优化策略制定
- 对话式交互
"""
import os
import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass, field

from .deerflow_client import DeerFlowClient, get_deerflow_client, ToolDefinition

logger = logging.getLogger(__name__)


@dataclass
class AgentContext:
    """Agent 上下文"""
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    trace_id: Optional[str] = None
    preferences: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResponse:
    """Agent 响应"""
    message: str
    action_taken: Optional[str] = None
    confidence: float = 0.0
    requires_approval: bool = False
    data: Dict[str, Any] = field(default_factory=dict)
    suggestions: List[str] = field(default_factory=list)


class TrafficAgent:
    """
    流量优化 Agent

    核心能力：
    1. 主动监控 - 持续监控流量指标，自动发现异常
    2. 自主决策 - 基于置信度阈值自主执行优化
    3. 对话交互 - 自然语言对话替代手动配置
    """

    def __init__(self, deerflow_client: Optional[DeerFlowClient] = None):
        """
        初始化 Traffic Agent

        Args:
            deerflow_client: DeerFlow 客户端
        """
        self.df_client = deerflow_client or get_deerflow_client()
        self.context: Optional[AgentContext] = None
        self.auto_execute_threshold = float(os.getenv("AGENT_AUTO_EXECUTE_THRESHOLD", "0.9"))
        self.request_approval_threshold = float(os.getenv("AGENT_REQUEST_APPROVAL_THRESHOLD", "0.7"))

        # 注册工具
        self._register_default_tools()

    def _register_default_tools(self):
        """注册默认工具"""
        # 工具将在外部注册，此处保留扩展接口
        pass

    def set_context(self, context: AgentContext):
        """设置 Agent 上下文"""
        self.context = context

    async def analyze_traffic(self, query: str) -> AgentResponse:
        """
        分析流量查询

        Args:
            query: 自然语言查询，如"上周流量为什么下跌"

        Returns:
            Agent 响应
        """
        trace_id = self.context.trace_id if self.context else f"trace_{datetime.now().timestamp()}"
        logger.info(f"[{trace_id}] Analyzing traffic query: {query}")

        # TODO: 调用 LLM 进行深度分析
        # 当前使用规则引擎降级
        return AgentResponse(
            message=f"正在分析：{query}",
            action_taken="analysis_started",
            confidence=0.5,
            requires_approval=False,
            data={"query": query, "trace_id": trace_id}
        )

    async def discover_opportunities(self) -> AgentResponse:
        """
        主动发现增长机会

        Returns:
            Agent 响应，包含发现的机会列表
        """
        trace_id = self.context.trace_id if self.context else f"trace_{datetime.now().timestamp()}"
        logger.info(f"[{trace_id}] Discovering growth opportunities")

        # TODO: 调用机会发现服务
        return AgentResponse(
            message="正在分析增长机会...",
            action_taken="opportunity_scan_started",
            confidence=0.6,
            requires_approval=False,
            data={"trace_id": trace_id}
        )

    async def execute_optimization(self, strategy_id: str) -> AgentResponse:
        """
        执行优化策略

        Args:
            strategy_id: 策略 ID

        Returns:
            Agent 响应
        """
        trace_id = self.context.trace_id if self.context else f"trace_{datetime.now().timestamp()}"
        logger.info(f"[{trace_id}] Executing optimization strategy: {strategy_id}")

        # 检查置信度
        confidence = 0.85  # TODO: 从策略获取

        if confidence >= self.auto_execute_threshold:
            # 自主执行
            return await self._auto_execute(strategy_id)
        elif confidence >= self.request_approval_threshold:
            # 请求批准
            return AgentResponse(
                message=f"建议执行优化策略 {strategy_id}，预计提升流量 15%",
                action_taken="approval_requested",
                confidence=confidence,
                requires_approval=True,
                data={"strategy_id": strategy_id, "trace_id": trace_id}
            )
        else:
            # 仅建议
            return AgentResponse(
                message=f"发现优化机会 {strategy_id}，建议人工审核",
                action_taken="suggestion_only",
                confidence=confidence,
                requires_approval=True,
                data={"strategy_id": strategy_id, "trace_id": trace_id}
            )

    async def _auto_execute(self, strategy_id: str) -> AgentResponse:
        """自主执行优化策略"""
        logger.info(f"Auto-executing strategy: {strategy_id}")

        # TODO: 调用执行服务
        # 记录审计日志
        self._log_audit("auto_execute", strategy_id)

        return AgentResponse(
            message=f"已自主执行优化策略 {strategy_id}",
            action_taken="auto_executed",
            confidence=0.9,
            requires_approval=False,
            data={"strategy_id": strategy_id},
            suggestions=["3 天后可查看效果报告"]
        )

    def _log_audit(self, action: str, resource: str, request: Optional[Dict] = None,
                   response: Optional[Dict] = None, status: str = "success"):
        """记录审计日志"""
        # TODO: 写入审计日志表
        logger.info(f"Audit: {action} on {resource} - {status}")

    async def chat(self, message: str) -> AgentResponse:
        """
        对话式交互入口

        Args:
            message: 用户消息

        Returns:
            Agent 响应
        """
        trace_id = self.context.trace_id if self.context else f"trace_{datetime.now().timestamp()}"
        logger.info(f"[{trace_id}] Chat message: {message}")

        # 意图识别
        intent = self._classify_intent(message)

        if intent == "analyze":
            return await self.analyze_traffic(message)
        elif intent == "optimize":
            return await self.discover_opportunities()
        elif intent == "execute":
            # 提取策略 ID
            strategy_id = self._extract_strategy_id(message)
            return await self.execute_optimization(strategy_id or "unknown")
        else:
            return AgentResponse(
                message=f"收到：{message}。我是您的流量优化助手，可以帮您分析流量、发现机会、执行优化。",
                action_taken="greeting",
                confidence=1.0,
                requires_approval=False,
                suggestions=[
                    "分析上周流量下跌原因",
                    "发现增长机会",
                    "执行 SEO 优化策略"
                ]
            )

    def _classify_intent(self, message: str) -> str:
        """分类用户意图"""
        message_lower = message.lower()

        # 执行类意图（优先检查，因为更具体）
        if any(kw in message_lower for kw in ["执行", "运行", "开始", "execute", "run", "start"]):
            return "execute"

        # 分析类意图
        if any(kw in message_lower for kw in ["为什么", "分析", "原因", "trend", "why", "analyze"]):
            return "analyze"

        # 优化类意图
        if any(kw in message_lower for kw in ["优化", "机会", "提升", "增长", "optimize", "optimization", "opportunity", "find"]):
            return "optimize"

        return "general"

    def _extract_strategy_id(self, message: str) -> Optional[str]:
        """从消息中提取策略 ID"""
        # TODO: 使用 NLP 提取
        import re
        match = re.search(r'策略[_\s]?(\w+)|strategy[_\s]?(\w+)', message, re.IGNORECASE)
        if match:
            return match.group(1) or match.group(2)
        return None


# 全局 Agent 实例
_traffic_agent: Optional[TrafficAgent] = None


def get_traffic_agent() -> TrafficAgent:
    """获取全局 Traffic Agent 实例"""
    global _traffic_agent
    if _traffic_agent is None:
        _traffic_agent = TrafficAgent()
    return _traffic_agent


def init_traffic_agent(deerflow_client: Optional[DeerFlowClient] = None) -> TrafficAgent:
    """初始化全局 Traffic Agent"""
    global _traffic_agent
    _traffic_agent = TrafficAgent(deerflow_client=deerflow_client)
    return _traffic_agent
