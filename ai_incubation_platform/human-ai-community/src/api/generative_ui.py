"""
Generative UI API - 动态界面生成接口

根据用户兴趣、上下文和 AI 决策，动态生成个性化界面。
支持人机身份视觉区分、决策过程可视化、透明度仪表盘等。
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2", tags=["Generative UI"])


# ==================== 响应模型 ====================

class AuthorType(str, Enum):
    """作者类型"""
    HUMAN = "human"
    AI = "ai"
    HYBRID = "hybrid"  # 人机协作


class ContentType(str, Enum):
    """内容类型"""
    POST = "post"
    COMMENT = "comment"
    DISCUSSION = "discussion"


class UIComponentType(str, Enum):
    """UI 组件类型"""
    CARD = "card"
    BADGE = "badge"
    TIMELINE = "timeline"
    CHART = "chart"
    TABLE = "table"


class AuthorBadge(BaseModel):
    """作者标识徽章"""
    type: AuthorType
    icon: str  # emoji 或图标名称
    label: str
    color: str  # 边框颜色
    tooltip: str
    ai_model_info: Optional[str] = None  # AI 模型信息（仅 AI 类型）


class ContentCard(BaseModel):
    """内容卡片"""
    id: str
    type: ContentType
    title: str
    content: str
    author_badge: AuthorBadge
    created_at: datetime
    tags: List[str] = Field(default_factory=list)
    ai_contribution_ratio: Optional[float] = None  # AI 贡献度（0-1，仅混合类型）
    moderation_status: Optional[str] = None  # 审核状态
    decision_trace_id: Optional[str] = None  # 决策追溯 ID（如有）


class DecisionStep(BaseModel):
    """决策步骤"""
    step_name: str
    result: str
    confidence: float
    reasoning: str
    timestamp: str


class DecisionVisualization(BaseModel):
    """决策过程可视化"""
    trace_id: str
    agent_id: str
    agent_name: str
    action_type: str
    decision_steps: List[DecisionStep]
    final_decision: str
    confidence_score: float
    reasoning: str
    appeal_url: str


class TransparencyStats(BaseModel):
    """透明度统计"""
    ai_content_ratio: float
    total_ai_decisions: int
    decision_distribution: Dict[str, int]
    average_confidence: float
    appeal_count: int
    appeal_success_rate: float


class DashboardWidget(BaseModel):
    """仪表盘组件"""
    widget_id: str
    widget_type: str
    title: str
    data: Dict[str, Any]
    config: Dict[str, Any] = Field(default_factory=dict)


class GenerativeUIResponse(BaseModel):
    """Generative UI 响应"""
    components: List[Dict[str, Any]]
    layout: Dict[str, Any]
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ==================== API 端点 ====================

@router.get("/ui/content-feed", response_model=GenerativeUIResponse)
async def get_content_feed(
    limit: int = Query(20, description="返回内容数量"),
    author_type: Optional[AuthorType] = Query(None, description="按作者类型过滤"),
):
    """
    获取内容流（带人机身份标识）

    根据内容作者类型（人类/AI/混合）动态生成不同的视觉标识。
    """
    # 占位实现（实际应从数据库查询）
    cards = []

    # 示例：人类内容
    cards.append(ContentCard(
        id="post_001",
        type=ContentType.POST,
        title="大家对 AI 参与社区建设有什么看法？",
        content="最近社区里 AI 成员越来越多了，大家觉得这对社区生态有什么影响？...",
        author_badge=AuthorBadge(
            type=AuthorType.HUMAN,
            icon="👤",
            label="张三",
            color="#3B82F6",  # 蓝色
            tooltip="人类成员",
        ),
        created_at=datetime.now(),
        tags=["讨论", "AI"],
    ))

    # 示例：AI 内容
    cards.append(ContentCard(
        id="post_002",
        type=ContentType.POST,
        title="本周社区治理报告：处理 156 条举报，准确率 94%",
        content="大家好，我是 AI 版主小安。以下是本周的治理报告...",
        author_badge=AuthorBadge(
            type=AuthorType.AI,
            icon="🤖",
            label="AI 版主小安",
            color="#8B5CF6",  # 紫色
            tooltip="AI 版主 · Anthropic Claude",
            ai_model_info="Anthropic Claude",
        ),
        created_at=datetime.now(),
        tags=["治理报告", "AI 自主发布"],
        decision_trace_id="trace_abc123",
    ))

    # 示例：混合内容
    cards.append(ContentCard(
        id="post_003",
        type=ContentType.POST,
        title="Python 异步编程最佳实践（AI 辅助创作）",
        content="本文结合了作者的实战经验和 AI 的整理能力...",
        author_badge=AuthorBadge(
            type=AuthorType.HYBRID,
            icon="👤🤖",
            label="李四 + AI 润色",
            color="linear-gradient(#3B82F6, #8B5CF6)",  # 渐变
            tooltip="人机协作 · AI 贡献度 35%",
        ),
        created_at=datetime.now(),
        tags=["教程", "Python"],
        ai_contribution_ratio=0.35,
    ))

    # 按作者类型过滤
    if author_type:
        if author_type == AuthorType.HUMAN:
            cards = [c for c in cards if c.author_badge.type == AuthorType.HUMAN]
        elif author_type == AuthorType.AI:
            cards = [c for c in cards if c.author_badge.type == AuthorType.AI]
        elif author_type == AuthorType.HYBRID:
            cards = [c for c in cards if c.author_badge.type == AuthorType.HYBRID]

    return GenerativeUIResponse(
        components=[{"type": "content_card", "data": card.model_dump()} for card in cards[:limit]],
        layout={
            "type": "grid",
            "columns": 1,
            "gap": "1rem",
        },
        metadata={
            "total_count": len(cards),
            "ai_content_count": len([c for c in cards if c.author_badge.type == AuthorType.AI]),
            "hybrid_content_count": len([c for c in cards if c.author_badge.type == AuthorType.HYBRID]),
        },
    )


@router.get("/ui/decision/{trace_id}", response_model=DecisionVisualization)
async def get_decision_visualization(trace_id: str):
    """
    获取决策过程可视化

    展示 AI 决策的完整时间线，包括每个步骤的分析结果和置信度。
    用于透明度展示和用户申诉。
    """
    # 占位实现（实际应从追溯链查询）
    return DecisionVisualization(
        trace_id=trace_id,
        agent_id="agent_001",
        agent_name="AI 版主小安",
        action_type="content_removal",
        decision_steps=[
            DecisionStep(
                step_name="关键词检测",
                result="匹配 3 个垃圾广告关键词",
                confidence=0.85,
                reasoning="检测到'加微信'、'转账'、'点击链接'等关键词",
                timestamp="2026-04-06T14:32:11.234Z",
            ),
            DecisionStep(
                step_name="内容特征分析",
                result="包含 5 个外部链接",
                confidence=0.6,
                reasoning="内容长度异常短（<20 字）且包含过多链接",
                timestamp="2026-04-06T14:32:12.567Z",
            ),
            DecisionStep(
                step_name="用户历史考量",
                result="过去 24 小时发布 15 条内容",
                confidence=0.7,
                reasoning="用户发布频率异常，3 条已被标记为垃圾内容",
                timestamp="2026-04-06T14:32:13.890Z",
            ),
        ],
        final_decision="removed",
        confidence_score=0.78,
        reasoning="综合风险分数 0.78，超过阈值 0.7，判定为垃圾内容",
        appeal_url=f"/appeal/{trace_id}",
    )


@router.get("/ui/transparency-dashboard", response_model=GenerativeUIResponse)
async def get_transparency_dashboard(
    period: str = Query("current_month", description="报告周期"),
):
    """
    获取透明度仪表盘

    展示 AI 治理的实时统计，包括决策分布、准确率趋势、申诉率等。
    """
    # 占位实现
    stats = TransparencyStats(
        ai_content_ratio=0.42,
        total_ai_decisions=156,
        decision_distribution={
            "approved": 98,
            "flagged": 42,
            "removed": 16,
        },
        average_confidence=0.82,
        appeal_count=5,
        appeal_success_rate=0.2,
    )

    widgets = [
        DashboardWidget(
            widget_id="ratio_card",
            widget_type="stat_card",
            title="AI 内容占比",
            data={"value": 42, "unit": "%", "trend": "+5%"},
            config={"color": "blue"},
        ),
        DashboardWidget(
            widget_id="decisions_card",
            widget_type="stat_card",
            title="自动处理率",
            data={"value": 78, "unit": "%", "trend": "+3%"},
            config={"color": "green"},
        ),
        DashboardWidget(
            widget_id="appeal_card",
            widget_type="stat_card",
            title="申诉成功率",
            data={"value": 12, "unit": "%", "trend": "-2%"},
            config={"color": "yellow"},
        ),
        DashboardWidget(
            widget_id="distribution_chart",
            widget_type="bar_chart",
            title="决策类型分布",
            data=stats.decision_distribution,
            config={"labels": ["通过", "标记", "删除"]},
        ),
    ]

    return GenerativeUIResponse(
        components=[{"type": "widget", "data": w.model_dump()} for w in widgets],
        layout={
            "type": "dashboard",
            "rows": [
                ["ratio_card", "decisions_card", "appeal_card"],
                ["distribution_chart"],
            ],
        },
        metadata={
            "period": period,
            "generated_at": datetime.now().isoformat(),
            "stats": stats.model_dump(),
        },
    )


@router.get("/ui/agent-status")
async def get_agent_status():
    """
    获取 AI Agent 状态卡片

    展示 AI 版主的活动状态、信誉分数、处理统计等。
    """
    # 占位实现
    return {
        "agents": [
            {
                "agent_id": "agent_001",
                "agent_name": "AI 版主小安",
                "agent_type": "moderator",
                "status": "active",
                "reputation_score": 4.8,
                "governance_power": 0.5,
                "stats": {
                    "total_decisions": 1234,
                    "accuracy_rate": 0.94,
                    "avg_response_time": "0.3s",
                },
                "last_active_at": datetime.now().isoformat(),
            },
            {
                "agent_id": "agent_002",
                "agent_name": "AI 匹配助手小智",
                "agent_type": "matcher",
                "status": "active",
                "reputation_score": 4.5,
                "governance_power": 0.3,
                "stats": {
                    "total_matches": 987,
                    "success_rate": 0.85,
                },
                "last_active_at": datetime.now().isoformat(),
            },
        ],
    }


@router.get("/ui/recommendation-widgets")
async def get_recommendation_widgets(user_id: str):
    """
    获取个性化推荐组件

    根据用户兴趣动态生成推荐内容、匹配成员等组件。
    """
    # 占位实现
    return {
        "widgets": [
            {
                "widget_id": "recommended_members",
                "widget_type": "member_list",
                "title": "您可能感兴趣的成员",
                "items": [
                    {
                        "member_id": "member_001",
                        "name": "王五",
                        "common_interests": ["人工智能", "Python"],
                        "match_score": 0.92,
                    },
                    {
                        "member_id": "member_002",
                        "name": "赵六",
                        "common_interests": ["数据科学", "机器学习"],
                        "match_score": 0.88,
                    },
                ],
            },
            {
                "widget_id": "recommended_content",
                "widget_type": "content_list",
                "title": "为您推荐",
                "items": [
                    {
                        "content_id": "post_101",
                        "title": "深度学习入门教程",
                        "relevance_score": 0.95,
                        "reason": "与您感兴趣的 机器学习 相关",
                    },
                ],
            },
        ],
        "layout": {
            "type": "sidebar",
            "position": "right",
            "width": "300px",
        },
    }
