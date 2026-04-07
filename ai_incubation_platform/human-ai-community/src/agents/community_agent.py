"""
Community Agent - 社区治理 AI Agent

这是 Human-AI Community 的核心 AI Agent，负责：
1. 自主社区治理（内容审核、违规检测）
2. 成员匹配推荐
3. 内容创作与互动
4. 透明度报告生成

AI Agent 具有独立的身份、信誉分数和决策追溯链。
"""

import uuid
import logging
import json
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

from models.member import (
    CommunityMember, MemberType, MemberRole, Post, Comment,
    ReviewStatus, ReviewResult, ContentReview, ContentType,
    Report, ReportType, BanRecord, AuditLog, OperationType
)

logger = logging.getLogger(__name__)


class AgentType(str, Enum):
    """AI Agent 类型"""
    MODERATOR = "moderator"  # 版主 Agent
    CREATOR = "creator"  # 内容创作 Agent
    MATCHER = "matcher"  # 匹配推荐 Agent
    MEDIATOR = "mediator"  # 调解 Agent
    ANALYST = "analyst"  # 数据分析 Agent


class GovernanceAction(str, Enum):
    """治理行动类型"""
    PATROL = "patrol"  # 巡查
    EVALUATE = "evaluate"  # 评估内容
    REMOVE = "remove"  # 删除内容
    FLAG = "flag"  # 标记需人工审核
    WARN = "warn"  # 警告用户
    BAN = "ban"  # 封禁用户
    MEDIATE = "mediate"  # 调解纠纷


@dataclass
class AIAgentIdentity:
    """
    AI Agent 独立身份

    这是 AI Native 架构的核心：AI 作为一等公民，拥有独立的身份、
    人格特征、能力清单和信誉评分。
    """
    agent_id: str
    agent_name: str
    agent_type: AgentType
    personality_traits: Dict[str, float] = field(default_factory=dict)  # 大五人格分数
    behavioral_policy: str = ""  # 行为准则
    capability_profile: List[str] = field(default_factory=list)  # 能力清单
    operator_id: Optional[str] = None  # 人类运营者（可为 None，表示自主 AI）
    model_provider: str = "unknown"
    model_version: str = "unknown"
    reputation_score: float = 1.0  # 信誉分 (0-5)
    governance_power: float = 0.5  # 治理权重 (0-1)
    status: str = "pending"  # pending/active/suspended/retired
    registered_at: datetime = field(default_factory=datetime.now)
    activated_at: Optional[datetime] = None
    last_active_at: Optional[datetime] = None
    audit_trail_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    @classmethod
    def create_moderator_agent(
        cls,
        name: str = "AI 版主小安",
        operator_id: Optional[str] = None,
        model_provider: str = "anthropic",
        model_version: str = "claude-sonnet-4-20250514",
    ) -> "AIAgentIdentity":
        """创建版主 Agent"""
        return cls(
            agent_id=f"agent_{uuid.uuid4().hex[:12]}",
            agent_name=name,
            agent_type=AgentType.MODERATOR,
            personality_traits={
                "openness": 0.7,  # 开放性
                "conscientiousness": 0.9,  # 尽责性
                "extraversion": 0.5,  # 外向性
                "agreeableness": 0.8,  # 宜人性
                "neuroticism": 0.2,  # 神经质（低表示情绪稳定）
            },
            behavioral_policy="""
你是一个公正、细致的 AI 版主。你的职责是：
1. 主动巡查社区内容，发现潜在违规
2. 基于明确的规则做出审核决策
3. 对每个决策提供透明、可解释的理由
4. 在置信度不足时，提交人工审核

你的决策原则：
- 宁可错放，不可错杀（保守策略）
- 对于边界情况，标记为需人工审核
- 始终提供详细的决策理由
- 尊重用户申诉的权利
""",
            capability_profile=[
                "content_patrol",  # 内容巡查
                "violation_detection",  # 违规检测
                "auto_removal",  # 自主删除（高置信度时）
                "flag_for_review",  # 标记人工审核
                "decision_explanation",  # 决策解释
                "user_notification",  # 用户通知
            ],
            operator_id=operator_id,
            model_provider=model_provider,
            model_version=model_version,
            reputation_score=1.0,
            governance_power=0.5,
            status="active",
            activated_at=datetime.now(),
        )

    @classmethod
    def create_matcher_agent(
        cls,
        name: str = "AI 匹配助手小智",
        operator_id: Optional[str] = None,
    ) -> "AIAgentIdentity":
        """创建匹配推荐 Agent"""
        return cls(
            agent_id=f"agent_{uuid.uuid4().hex[:12]}",
            agent_name=name,
            agent_type=AgentType.MATCHER,
            personality_traits={
                "openness": 0.8,
                "conscientiousness": 0.7,
                "extraversion": 0.7,
                "agreeableness": 0.9,
                "neuroticism": 0.3,
            },
            behavioral_policy="""
你是一个友好、敏锐的 AI 匹配助手。你的职责是：
1. 分析成员的兴趣、专长和需求
2. 主动推荐志同道合的成员
3. 推荐相关的社区活动和内容
4. 促进有意义的连接和协作

你的推荐原则：
- 基于多维度的兴趣匹配
- 尊重用户隐私和偏好
- 提供个性化的推荐理由
- 允许用户反馈和优化推荐
""",
            capability_profile=[
                "interest_analysis",  # 兴趣分析
                "member_matching",  # 成员匹配
                "content_recommendation",  # 内容推荐
                "activity_suggestion",  # 活动建议
                "collaboration_facilitation",  # 协作促进
            ],
            operator_id=operator_id,
            model_provider="anthropic",
            model_version="claude-sonnet-4-20250514",
            reputation_score=1.0,
            governance_power=0.3,
            status="active",
            activated_at=datetime.now(),
        )


@dataclass
class GovernanceTrace:
    """
    AI 治理追溯记录

    区块链式的不可篡改追溯链，记录 AI 的每个决策过程。
    这是 AI Native 架构中透明度和问责制的核心。
    """
    trace_id: str
    agent_id: str
    action_type: GovernanceAction
    target_content_type: Optional[ContentType] = None
    target_content_id: Optional[str] = None
    decision_input: Dict[str, Any] = field(default_factory=dict)
    decision_process: List[Dict[str, Any]] = field(default_factory=list)
    decision_output: Dict[str, Any] = field(default_factory=dict)
    confidence_score: float = 0.0
    reasoning: str = ""
    previous_trace_hash: Optional[str] = None
    signature: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def create(
        cls,
        agent_id: str,
        action_type: GovernanceAction,
        **kwargs,
    ) -> "GovernanceTrace":
        """创建追溯记录"""
        return cls(
            trace_id=f"trace_{uuid.uuid4().hex[:12]}",
            agent_id=agent_id,
            action_type=action_type,
            **kwargs,
        )

    def add_step(self, step_name: str, result: Any, confidence: float, reasoning: str):
        """添加决策步骤"""
        self.decision_process.append({
            "step": step_name,
            "result": result,
            "confidence": confidence,
            "reasoning": reasoning,
            "timestamp": datetime.now().isoformat(),
        })

    def finalize(self, output: Dict[str, Any], confidence: float, reasoning: str):
        """完成追溯记录"""
        self.decision_output = output
        self.confidence_score = confidence
        self.reasoning = reasoning
        # 简单签名（实际实现应使用加密签名）
        self.signature = f"sig_{uuid.uuid4().hex[:16]}"


class CommunityAgent:
    """
    社区治理 AI Agent

    这是 Human-AI Community 的核心 AI Agent 实现，
    支持自主治理、成员匹配、内容推荐等功能。
    """

    def __init__(
        self,
        identity: AIAgentIdentity,
        community_service=None,
    ):
        self.identity = identity
        self.community_service = community_service
        self._trace_chain: List[GovernanceTrace] = []
        self._last_patrol_time: Optional[datetime] = None
        self._decisions_made: int = 0
        self._accuracy_rate: float = 1.0

        # 置信度阈值配置
        self._auto_action_threshold = 0.9  # 自主行动阈值
        self._flag_threshold = 0.6  # 标记人工审核阈值

    async def patrol_channels(
        self,
        time_window: timedelta = timedelta(hours=24),
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        主动巡查频道内容

        AI 版主不是被动等待举报，而是主动扫描新内容，
        发现潜在违规行为。
        """
        logger.info(f"Starting patrol for agent: {self.identity.agent_name}")

        if self.community_service is None:
            logger.warning("Community service not available")
            return []

        # 获取最近的内容
        posts = self.community_service.list_posts(limit=limit)
        cutoff_time = datetime.now() - time_window
        recent_posts = [p for p in posts if p.created_at >= cutoff_time]

        findings = []
        for post in recent_posts:
            trace = GovernanceTrace.create(
                agent_id=self.identity.agent_id,
                action_type=GovernanceAction.PATROL,
                target_content_type=ContentType.POST,
                target_content_id=post.id,
                decision_input={"post_id": post.id, "title": post.title},
            )
            trace.add_step(
                step_name="content_fetch",
                result={"post_id": post.id, "title_length": len(post.title)},
                confidence=1.0,
                reasoning=f"获取帖子内容：{post.title[:50]}...",
            )

            # 初步内容分析
            analysis = await self._analyze_content(post.title + " " + post.content)
            trace.add_step(
                step_name="content_analysis",
                result=analysis,
                confidence=analysis.get("risk_score", 0),
                reasoning=analysis.get("summary", ""),
            )

            # 如果风险分数超过阈值，进一步评估
            if analysis.get("risk_score", 0) >= 0.3:
                await self._evaluate_and_act(post.id, ContentType.POST, analysis, trace)
                findings.append({
                    "content_id": post.id,
                    "content_type": "post",
                    "risk_score": analysis.get("risk_score", 0),
                    "action_taken": trace.decision_output.get("action", "none"),
                })

            self._trace_chain.append(trace)

        self._last_patrol_time = datetime.now()
        self.identity.last_active_at = datetime.now()

        logger.info(f"Patrol completed: {len(findings)} findings")
        return findings

    async def _analyze_content(self, content: str) -> Dict[str, Any]:
        """分析内容风险"""
        # 简化的内容分析（实际实现应调用 LLM）
        risk_indicators = []
        risk_score = 0.0

        # 关键词检测（占位实现）
        spam_keywords = ["加微信", "转账", "点击链接", "免费", "赚钱"]
        for keyword in spam_keywords:
            if keyword in content:
                risk_indicators.append(f"包含敏感词：{keyword}")
                risk_score += 0.15

        # 链接检测
        link_count = content.count("http://") + content.count("https://")
        if link_count > 3:
            risk_indicators.append(f"包含过多链接：{link_count}个")
            risk_score += 0.2

        # 内容长度异常检测
        if len(content) < 10:
            risk_indicators.append("内容过短")
            risk_score += 0.1

        return {
            "risk_score": min(1.0, risk_score),
            "indicators": risk_indicators,
            "summary": f"检测到 {len(risk_indicators)} 个风险指标" if risk_indicators else "内容无明显风险",
        }

    async def _evaluate_and_act(
        self,
        content_id: str,
        content_type: ContentType,
        analysis: Dict[str, Any],
        trace: GovernanceTrace,
    ):
        """评估内容并采取行动"""
        risk_score = analysis.get("risk_score", 0)

        # 根据置信度自主决策
        if risk_score >= self._auto_action_threshold:
            # 高风险：自主删除
            trace.add_step(
                step_name="decision",
                result="auto_remove",
                confidence=risk_score,
                reasoning=f"风险分数 {risk_score:.2f} >= {self._auto_action_threshold}，自主删除",
            )
            await self._remove_content(content_id, content_type, trace)
        elif risk_score >= self._flag_threshold:
            # 中风险：标记人工审核
            trace.add_step(
                step_name="decision",
                result="flag_for_review",
                confidence=risk_score,
                reasoning=f"风险分数 {risk_score:.2f} >= {self._flag_threshold}，标记人工审核",
            )
            await self._flag_content(content_id, content_type, trace)
        else:
            # 低风险：记录并继续
            trace.add_step(
                step_name="decision",
                result="log_and_continue",
                confidence=risk_score,
                reasoning=f"风险分数 {risk_score:.2f} < {self._flag_threshold}，无需处理",
            )

    async def _remove_content(
        self,
        content_id: str,
        content_type: ContentType,
        trace: GovernanceTrace,
    ):
        """删除违规内容"""
        # 这里应该调用实际的删除 API
        trace.finalize(
            output={"action": "removed", "content_id": content_id},
            confidence=trace.confidence_score,
            reasoning=trace.reasoning,
        )
        self._decisions_made += 1
        logger.info(f"Content removed: {content_id}")

    async def _flag_content(
        self,
        content_id: str,
        content_type: ContentType,
        trace: GovernanceTrace,
    ):
        """标记内容需人工审核"""
        # 这里应该调用实际的标记 API
        trace.finalize(
            output={"action": "flagged", "content_id": content_id},
            confidence=trace.confidence_score,
            reasoning=trace.reasoning,
        )
        self._decisions_made += 1
        logger.info(f"Content flagged: {content_id}")

    async def explain_decision(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """
        解释决策过程

        透明度要求：用户有权了解 AI 决策的完整过程。
        """
        trace = next((t for t in self._trace_chain if t.trace_id == trace_id), None)
        if not trace:
            return None

        return {
            "trace_id": trace.trace_id,
            "agent_id": trace.agent_id,
            "agent_name": self.identity.agent_name,
            "action_type": trace.action_type.value,
            "decision_process": trace.decision_process,
            "final_decision": trace.decision_output,
            "confidence_score": trace.confidence_score,
            "reasoning": trace.reasoning,
            "timestamp": trace.created_at.isoformat(),
        }

    async def get_transparency_report(
        self,
        period_start: datetime,
        period_end: datetime,
    ) -> Dict[str, Any]:
        """
        生成透明度报告

        定期生成 AI 治理报告，包括决策统计、准确率、申诉率等。
        """
        filtered_traces = [
            t for t in self._trace_chain
            if period_start <= t.created_at <= period_end
        ]

        # 统计决策分布
        action_counts = {}
        for trace in filtered_traces:
            action = trace.decision_output.get("action", "unknown")
            action_counts[action] = action_counts.get(action, 0) + 1

        return {
            "report_id": f"report_{uuid.uuid4().hex[:8]}",
            "agent_id": self.identity.agent_id,
            "agent_name": self.identity.agent_name,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "total_decisions": len(filtered_traces),
            "action_distribution": action_counts,
            "average_confidence": sum(t.confidence_score for t in filtered_traces) / len(filtered_traces) if filtered_traces else 0,
            "accuracy_rate": self._accuracy_rate,
            "reputation_score": self.identity.reputation_score,
            "generated_at": datetime.now().isoformat(),
        }

    def get_status(self) -> Dict[str, Any]:
        """获取 Agent 状态"""
        return {
            "agent_id": self.identity.agent_id,
            "agent_name": self.identity.agent_name,
            "agent_type": self.identity.agent_type.value,
            "status": self.identity.status,
            "reputation_score": self.identity.reputation_score,
            "governance_power": self.identity.governance_power,
            "decisions_made": self._decisions_made,
            "accuracy_rate": self._accuracy_rate,
            "last_patrol_time": self._last_patrol_time.isoformat() if self._last_patrol_time else None,
            "last_active_at": self.identity.last_active_at.isoformat() if self.identity.last_active_at else None,
        }


# 全局 Agent 实例注册表
_agent_registry: Dict[str, CommunityAgent] = {}


def get_community_agent(agent_id: Optional[str] = None) -> Optional[CommunityAgent]:
    """获取已注册的 Agent 实例"""
    if agent_id:
        return _agent_registry.get(agent_id)
    # 返回第一个可用的版主 Agent
    for agent in _agent_registry.values():
        if agent.identity.agent_type == AgentType.MODERATOR:
            return agent
    return None


def register_agent(agent: CommunityAgent) -> None:
    """注册 AI Agent"""
    _agent_registry[agent.identity.agent_id] = agent
    logger.info(f"Agent registered: {agent.identity.agent_name}")


def create_default_moderator_agent(
    community_service=None,
    operator_id: Optional[str] = None,
) -> CommunityAgent:
    """创建默认的版主 Agent"""
    identity = AIAgentIdentity.create_moderator_agent(operator_id=operator_id)
    agent = CommunityAgent(identity=identity, community_service=community_service)
    register_agent(agent)
    return agent


def create_default_matcher_agent(
    community_service=None,
    operator_id: Optional[str] = None,
) -> CommunityAgent:
    """创建默认的匹配推荐 Agent"""
    identity = AIAgentIdentity.create_matcher_agent(operator_id=operator_id)
    agent = CommunityAgent(identity=identity, community_service=community_service)
    register_agent(agent)
    return agent
