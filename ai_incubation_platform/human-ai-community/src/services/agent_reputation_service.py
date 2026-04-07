"""
AI 信誉体系服务

实现 AI Agent 的信誉评分、排行榜、行为评估等功能
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, or_
import logging
import uuid

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.models import DBAgentReputation, DBBehaviorTrace, DBCommunityMember
from models.member import MemberType
from models.p6_entities import AgentType, AgentReputation, AgentReputationSummary, AgentRanking

logger = logging.getLogger(__name__)


class AgentReputationService:
    """AI 信誉体系服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_agent_reputation(
        self,
        agent_id: str,
        agent_name: str,
        agent_type: AgentType,
        model_provider: Optional[str] = None,
        model_name: Optional[str] = None,
        operator_id: Optional[str] = None
    ) -> DBAgentReputation:
        """
        创建 AI Agent 信誉记录

        Args:
            agent_id: Agent 唯一标识
            agent_name: Agent 名称
            agent_type: Agent 类型
            model_provider: 模型提供方
            model_name: 模型名称
            operator_id: 运营者 ID

        Returns:
            创建的信誉记录
        """
        # 检查是否已存在
        existing = await self.get_by_agent_id(agent_id)
        if existing:
            logger.info(f"Agent {agent_id} 信誉记录已存在")
            return existing

        # 创建新记录
        db_reputation = DBAgentReputation(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            agent_name=agent_name,
            agent_type=agent_type.value,
            model_provider=model_provider,
            model_name=model_name,
            operator_id=operator_id,
            reputation_score=0.5,  # 初始中立分数
            is_active=True
        )

        self.db.add(db_reputation)
        await self.db.commit()
        await self.db.refresh(db_reputation)

        logger.info(f"创建 AI Agent 信誉记录：{agent_id} ({agent_name})")
        return db_reputation

    async def get_by_agent_id(self, agent_id: str) -> Optional[DBAgentReputation]:
        """根据 Agent ID 获取信誉记录"""
        result = await self.db.execute(
            select(DBAgentReputation).where(DBAgentReputation.agent_id == agent_id)
        )
        return result.scalar_one_or_none()

    async def update_reputation_score(
        self,
        agent_id: str,
        score_delta: float,
        action_type: str,
        is_positive: bool
    ) -> DBAgentReputation:
        """
        更新 AI Agent 信誉分数

        Args:
            agent_id: Agent ID
            score_delta: 分数变化量
            action_type: 行为类型
            is_positive: 是否为正面行为

        Returns:
            更新后的信誉记录
        """
        reputation = await self.get_by_agent_id(agent_id)
        if not reputation:
            raise ValueError(f"Agent {agent_id} 信誉记录不存在")

        # 更新总分
        old_score = reputation.reputation_score
        new_score = max(0.0, min(1.0, old_score + score_delta))
        reputation.reputation_score = new_score

        # 更新行为统计
        reputation.total_actions += 1
        if is_positive:
            reputation.positive_actions += 1
        else:
            reputation.negative_actions += 1

        # 更新时间
        reputation.last_action_time = datetime.now()
        reputation.updated_at = datetime.now()

        # 计算细分评分
        await self._update_sub_scores(reputation, action_type, is_positive)

        await self.db.commit()
        await self.db.refresh(reputation)

        logger.info(
            f"更新 AI Agent 信誉分数：{agent_id}, "
            f"{old_score:.3f} -> {new_score:.3f} ({'+' if is_positive else ''}{score_delta:.3f})"
        )

        return reputation

    async def _update_sub_scores(
        self,
        reputation: DBAgentReputation,
        action_type: str,
        is_positive: bool
    ):
        """更新细分评分"""
        # 根据行为类型更新对应的细分评分
        if action_type in ["content_moderation", "report_processing"]:
            # 审核准确性
            if is_positive:
                reputation.accuracy_score = min(1.0, reputation.accuracy_score + 0.01)
            else:
                reputation.accuracy_score = max(0.0, reputation.accuracy_score - 0.02)

        elif action_type in ["recommendation", "content_suggestion"]:
            # 推荐公平性
            if is_positive:
                reputation.fairness_score = min(1.0, reputation.fairness_score + 0.01)
            else:
                reputation.fairness_score = max(0.0, reputation.fairness_score - 0.02)

        elif action_type in ["decision_making", "auto_action"]:
            # 决策透明性
            if is_positive:
                reputation.transparency_score = min(1.0, reputation.transparency_score + 0.01)
            else:
                reputation.transparency_score = max(0.0, reputation.transparency_score - 0.02)

    async def add_user_feedback(
        self,
        agent_id: str,
        is_positive: bool,
        response_time_ms: Optional[float] = None
    ):
        """
        添加用户反馈

        Args:
            agent_id: Agent ID
            is_positive: 是否为正面反馈
            response_time_ms: 响应时间（毫秒）
        """
        reputation = await self.get_by_agent_id(agent_id)
        if not reputation:
            raise ValueError(f"Agent {agent_id} 信誉记录不存在")

        reputation.user_feedback_count += 1
        if is_positive:
            reputation.user_feedback_positive += 1

        # 更新平均响应时间
        if response_time_ms is not None:
            total_actions = reputation.total_actions or 1
            reputation.avg_response_time_ms = (
                (reputation.avg_response_time_ms * (total_actions - 1) + response_time_ms) / total_actions
            )

            # 更新响应时间评分（越快分数越高）
            if response_time_ms < 100:
                reputation.response_time_score = min(1.0, reputation.response_time_score + 0.01)
            elif response_time_ms > 1000:
                reputation.response_time_score = max(0.0, reputation.response_time_score - 0.01)

        await self.db.commit()

    async def get_reputation_summary(self, agent_id: str) -> Optional[AgentReputationSummary]:
        """获取 Agent 信誉摘要"""
        reputation = await self.get_by_agent_id(agent_id)
        if not reputation:
            return None

        # 计算信誉等级
        score = reputation.reputation_score
        if score >= 0.8:
            level = "excellent"
        elif score >= 0.6:
            level = "good"
        elif score >= 0.4:
            level = "fair"
        else:
            level = "poor"

        # 计算正面率
        positive_rate = (
            reputation.positive_actions / reputation.total_actions
            if reputation.total_actions > 0 else 0.5
        )

        return AgentReputationSummary(
            agent_id=reputation.agent_id,
            agent_name=reputation.agent_name,
            agent_type=AgentType(reputation.agent_type),
            reputation_score=reputation.reputation_score,
            reputation_level=level,
            total_actions=reputation.total_actions,
            positive_rate=positive_rate,
            accuracy_score=reputation.accuracy_score,
            fairness_score=reputation.fairness_score,
            transparency_score=reputation.transparency_score
        )

    async def get_ranking(
        self,
        agent_type: Optional[AgentType] = None,
        limit: int = 10
    ) -> List[AgentRanking]:
        """
        获取 AI Agent 信誉排行榜

        Args:
            agent_type: Agent 类型过滤
            limit: 返回数量

        Returns:
            排行榜列表
        """
        query = select(DBAgentReputation).where(DBAgentReputation.is_active == True)

        if agent_type:
            query = query.where(DBAgentReputation.agent_type == agent_type.value)

        query = query.order_by(desc(DBAgentReputation.reputation_score))
        query = query.limit(limit)

        result = await self.db.execute(query)
        reputations = result.scalars().all()

        rankings = []
        for idx, rep in enumerate(reputations, 1):
            rankings.append(AgentRanking(
                rank=idx,
                agent_id=rep.agent_id,
                agent_name=rep.agent_name,
                agent_type=AgentType(rep.agent_type),
                reputation_score=rep.reputation_score,
                total_actions=rep.total_actions,
                accuracy_score=rep.accuracy_score
            ))

        return rankings

    async def list_agents(
        self,
        agent_type: Optional[AgentType] = None,
        min_reputation_score: Optional[float] = None,
        is_active: Optional[bool] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[DBAgentReputation]:
        """
        获取 AI Agent 列表

        Args:
            agent_type: Agent 类型过滤
            min_reputation_score: 最小信誉分数
            is_active: 活跃状态过滤
            limit: 返回数量
            offset: 偏移量

        Returns:
            AI Agent 列表
        """
        query = select(DBAgentReputation)

        if agent_type:
            query = query.where(DBAgentReputation.agent_type == agent_type.value)

        if min_reputation_score is not None:
            query = query.where(DBAgentReputation.reputation_score >= min_reputation_score)

        if is_active is not None:
            query = query.where(DBAgentReputation.is_active == is_active)

        query = query.order_by(desc(DBAgentReputation.reputation_score))
        query = query.offset(offset).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_statistics(self) -> Dict[str, Any]:
        """获取 AI 信誉体系统计信息"""
        # 总 Agent 数
        result = await self.db.execute(
            select(func.count(DBAgentReputation.id))
        )
        total_agents = result.scalar() or 0

        # 活跃 Agent 数
        result = await self.db.execute(
            select(func.count(DBAgentReputation.id))
            .where(DBAgentReputation.is_active == True)
        )
        active_agents = result.scalar() or 0

        # 平均信誉分数
        result = await self.db.execute(
            select(func.avg(DBAgentReputation.reputation_score))
        )
        avg_score = result.scalar() or 0.5

        # 各类型 Agent 数量
        result = await self.db.execute(
            select(
                DBAgentReputation.agent_type,
                func.count(DBAgentReputation.id)
            ).group_by(DBAgentReputation.agent_type)
        )
        type_counts = dict(result.all())

        # 高信誉 Agent 数（>= 0.8）
        result = await self.db.execute(
            select(func.count(DBAgentReputation.id))
            .where(DBAgentReputation.reputation_score >= 0.8)
        )
        high_reputation_count = result.scalar() or 0

        return {
            "total_agents": total_agents,
            "active_agents": active_agents,
            "avg_reputation_score": round(avg_score, 3),
            "type_counts": type_counts,
            "high_reputation_count": high_reputation_count,
            "high_reputation_rate": round(high_reputation_count / total_agents * 100, 1) if total_agents > 0 else 0
        }


# 全局服务实例
_agent_reputation_service: Optional[AgentReputationService] = None


def get_agent_reputation_service(db: AsyncSession) -> AgentReputationService:
    """获取 AI 信誉服务实例"""
    global _agent_reputation_service
    if _agent_reputation_service is None or _agent_reputation_service.db is not db:
        _agent_reputation_service = AgentReputationService(db)
    return _agent_reputation_service
