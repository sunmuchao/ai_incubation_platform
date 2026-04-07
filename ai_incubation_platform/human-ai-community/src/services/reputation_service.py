"""
声誉系统服务

实现人类与 AI 共享的声誉评分系统，包括：
- 多维度声誉评分
- 声誉等级与权益
- 行为追踪（正面/负面）
- 声誉恢复机制
- 声誉排行榜
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

from db.models import DBMemberReputation, DBReputationBehaviorLog, DBReputationRestoration
from models.p14_reputation import (
    MemberReputation, ReputationLevel, ReputationDimension,
    BehaviorType, ReputationBehaviorLog, ReputationRestoration,
    ReputationRankingEntry, ReputationRankingType,
    REPUTATION_PRIVILEGES, BEHAVIOR_SCORE_CONFIG
)

logger = logging.getLogger(__name__)


class ReputationService:
    """声誉系统服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ==================== 声誉记录管理 ====================

    async def get_or_create_reputation(
        self,
        member_id: str,
        member_type: str
    ) -> DBMemberReputation:
        """获取或创建声誉记录"""
        reputation = await self.get_by_member_id(member_id)

        if reputation is None:
            reputation = DBMemberReputation(
                id=str(uuid.uuid4()),
                member_id=member_id,
                member_type=member_type,
                total_score=100,
                level=ReputationLevel.NEWCOMER.value
            )
            self.db.add(reputation)
            await self.db.commit()
            await self.db.refresh(reputation)
            logger.info(f"创建声誉记录：{member_id} ({member_type})")

        return reputation

    async def get_by_member_id(self, member_id: str) -> Optional[DBMemberReputation]:
        """根据成员 ID 获取声誉记录"""
        result = await self.db.execute(
            select(DBMemberReputation).where(DBMemberReputation.member_id == member_id)
        )
        return result.scalar_one_or_none()

    async def update_reputation_score(
        self,
        member_id: str,
        behavior_type: BehaviorType,
        content_id: Optional[str] = None,
        content_type: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        更新声誉分数

        Args:
            member_id: 成员 ID
            behavior_type: 行为类型
            content_id: 关联内容 ID
            content_type: 关联内容类型
            ip_address: IP 地址

        Returns:
            更新结果
        """
        reputation = await self.get_or_create_reputation(member_id, "human")

        # 获取行为配置
        config = BEHAVIOR_SCORE_CONFIG.get(behavior_type)
        if config is None:
            logger.warning(f"未知的行为类型：{behavior_type}")
            return {"success": False, "error": "Unknown behavior type"}

        score_delta = config["score_delta"]
        dimension = config["dimension"]
        is_positive = config["is_positive"]

        # 更新总分
        old_score = reputation.total_score
        new_score = max(0, min(1000, old_score + score_delta))
        reputation.total_score = new_score

        # 更新等级
        new_level = self._calculate_level(new_score)
        old_level = reputation.level
        reputation.level = new_level.value

        # 更新维度分数
        await self._update_dimension_score(reputation, dimension, score_delta)

        # 更新行为统计
        reputation.last_action_at = datetime.now()

        if behavior_type == BehaviorType.POST_CREATE:
            reputation.total_posts += 1
        elif behavior_type == BehaviorType.COMMENT_CREATE:
            reputation.total_comments += 1
        elif behavior_type in [BehaviorType.POST_UPVOTED, BehaviorType.COMMENT_UPVOTED]:
            reputation.total_upvotes_received += 1
        elif behavior_type in [BehaviorType.POST_DOWNVOTED, BehaviorType.COMMENT_DOWNVOTED]:
            reputation.total_downvotes_received += 1
        elif behavior_type == BehaviorType.HELP_OTHERS:
            reputation.helpful_actions += 1
        elif behavior_type in [BehaviorType.VIOLATION_DETECTED, BehaviorType.SPAM_DETECTED]:
            reputation.violation_actions += 1

        if is_positive:
            reputation.positive_actions += 1
        else:
            reputation.negative_actions += 1

        # 检查是否需要进入观察模式
        if new_score < 200 and not reputation.probation_mode:
            reputation.probation_mode = True
            reputation.probation_end_date = datetime.now() + timedelta(days=30)
            logger.info(f"用户 {member_id} 进入观察模式，结束日期：{reputation.probation_end_date}")

        # 记录行为日志
        await self._log_behavior(
            member_id=member_id,
            member_type=reputation.member_type,
            behavior_type=behavior_type,
            is_positive=is_positive,
            score_delta=score_delta,
            dimension=dimension,
            content_id=content_id,
            content_type=content_type,
            ip_address=ip_address
        )

        await self.db.commit()
        await self.db.refresh(reputation)

        logger.info(
            f"更新声誉分数：{member_id}, {old_score} -> {new_score} "
            f"({ '+' if score_delta > 0 else '' }{score_delta}), 等级：{old_level} -> {new_level}"
        )

        return {
            "success": True,
            "old_score": old_score,
            "new_score": new_score,
            "old_level": old_level,
            "new_level": new_level,
            "score_delta": score_delta
        }

    async def _update_dimension_score(
        self,
        reputation: DBMemberReputation,
        dimension: ReputationDimension,
        delta: int
    ):
        """更新维度分数"""
        # 将分数变化映射到 0-100 的维度分数（delta 通常为 -20 到 +5）
        dimension_delta = delta * 0.5  # 缩放因子

        if dimension == ReputationDimension.CONTENT_QUALITY:
            reputation.content_quality_score = max(0, min(100, reputation.content_quality_score + dimension_delta))
        elif dimension == ReputationDimension.COMMUNITY_CONTRIBUTION:
            reputation.community_contribution_score = max(0, min(100, reputation.community_contribution_score + dimension_delta))
        elif dimension == ReputationDimension.COLLABORATION:
            reputation.collaboration_score = max(0, min(100, reputation.collaboration_score + dimension_delta))
        elif dimension == ReputationDimension.TRUSTWORTHINESS:
            reputation.trustworthiness_score = max(0, min(100, reputation.trustworthiness_score + dimension_delta))

    async def _log_behavior(
        self,
        member_id: str,
        member_type: str,
        behavior_type: BehaviorType,
        is_positive: bool,
        score_delta: int,
        dimension: ReputationDimension,
        content_id: Optional[str] = None,
        content_type: Optional[str] = None,
        ip_address: Optional[str] = None
    ):
        """记录行为日志"""
        config = BEHAVIOR_SCORE_CONFIG.get(behavior_type, {})

        log = DBReputationBehaviorLog(
            id=str(uuid.uuid4()),
            member_id=member_id,
            member_type=member_type,
            behavior_type=behavior_type.value,
            is_positive=is_positive,
            description=config.get("description", behavior_type.value),
            content_id=content_id,
            content_type=content_type,
            score_delta=score_delta,
            dimension_affected=dimension.value if dimension else None,
            context={},
            ip_address=ip_address,
            created_at=datetime.now()
        )
        self.db.add(log)

    def _calculate_level(self, score: int) -> ReputationLevel:
        """计算声誉等级"""
        if score <= 100:
            return ReputationLevel.NEWCOMER
        elif score <= 300:
            return ReputationLevel.BASIC
        elif score <= 500:
            return ReputationLevel.REGULAR
        elif score <= 700:
            return ReputationLevel.ACTIVE
        elif score <= 850:
            return ReputationLevel.CONTRIBUTOR
        elif score <= 950:
            return ReputationLevel.LEADER
        else:
            return ReputationLevel.LEGEND

    # ==================== 声誉排行榜 ====================

    async def get_ranking(
        self,
        ranking_type: ReputationRankingType = ReputationRankingType.OVERALL,
        member_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[ReputationRankingEntry]:
        """获取声誉排行榜"""
        query = select(DBMemberReputation)

        if member_type:
            query = query.where(DBMemberReputation.member_type == member_type)

        # 根据排行榜类型排序
        if ranking_type == ReputationRankingType.CONTENT_QUALITY:
            query = query.order_by(desc(DBMemberReputation.content_quality_score))
        elif ranking_type == ReputationRankingType.COMMUNITY_CONTRIBUTION:
            query = query.order_by(desc(DBMemberReputation.community_contribution_score))
        elif ranking_type == ReputationRankingType.COLLABORATION:
            query = query.order_by(desc(DBMemberReputation.collaboration_score))
        elif ranking_type == ReputationRankingType.TRUSTWORTHINESS:
            query = query.order_by(desc(DBMemberReputation.trustworthiness_score))
        elif ranking_type == ReputationRankingType.AI_AGENT:
            query = query.where(DBMemberReputation.member_type == "ai").order_by(desc(DBMemberReputation.total_score))
        elif ranking_type == ReputationRankingType.HUMAN:
            query = query.where(DBMemberReputation.member_type == "human").order_by(desc(DBMemberReputation.total_score))
        else:  # OVERALL
            query = query.order_by(desc(DBMemberReputation.total_score))

        query = query.offset(offset).limit(limit)

        result = await self.db.execute(query)
        reputations = result.scalars().all()

        rankings = []
        for idx, rep in enumerate(reputations, 1):
            positive_rate = (
                rep.positive_actions / (rep.positive_actions + rep.negative_actions)
                if (rep.positive_actions + rep.negative_actions) > 0 else 0.5
            )

            rankings.append(ReputationRankingEntry(
                rank=offset + idx,
                member_id=rep.member_id,
                member_name=f"User_{rep.member_id[:8]}",  # 实际应用中应该关联成员表获取名称
                member_type=rep.member_type,
                total_score=rep.total_score,
                level=ReputationLevel(rep.level),
                content_quality_score=rep.content_quality_score,
                community_contribution_score=rep.community_contribution_score,
                collaboration_score=rep.collaboration_score,
                trustworthiness_score=rep.trustworthiness_score,
                total_posts=rep.total_posts,
                total_upvotes_received=rep.total_upvotes_received,
                positive_rate=positive_rate
            ))

        return rankings

    # ==================== 声誉恢复机制 ====================

    async def create_restoration_request(
        self,
        member_id: str,
        reason: str,
        commitment_actions: List[str]
    ) -> DBReputationRestoration:
        """创建声誉恢复申请"""
        reputation = await self.get_by_member_id(member_id)
        if reputation is None:
            raise ValueError(f"声誉记录不存在：{member_id}")

        restoration = DBReputationRestoration(
            id=str(uuid.uuid4()),
            member_id=member_id,
            member_type=reputation.member_type,
            previous_score=reputation.total_score,
            previous_level=reputation.level,
            reason=reason,
            reason_type="appeal",
            restoration_actions=commitment_actions,
            completed_actions=[],
            progress=0.0,
            target_score=min(500, reputation.total_score + 200),  # 目标分数最多恢复 200 分
            status="in_progress"
        )

        self.db.add(restoration)
        await self.db.commit()
        await self.db.refresh(restoration)

        logger.info(f"创建声誉恢复申请：{member_id}, 目标分数：{restoration.target_score}")
        return restoration

    async def complete_restoration_action(
        self,
        restoration_id: str,
        action: str
    ) -> DBReputationRestoration:
        """完成恢复动作"""
        result = await self.db.execute(
            select(DBReputationRestoration).where(DBReputationRestoration.id == restoration_id)
        )
        restoration = result.scalar_one_or_none()

        if restoration is None:
            raise ValueError(f"恢复记录不存在：{restoration_id}")

        if action not in restoration.restoration_actions:
            raise ValueError(f"动作不在恢复计划中：{action}")

        if action in restoration.completed_actions:
            raise ValueError(f"动作已完成：{action}")

        # 添加已完成的动作
        restoration.completed_actions.append(action)

        # 更新进度
        total_actions = len(restoration.restoration_actions)
        completed_actions = len(restoration.completed_actions)
        restoration.progress = completed_actions / total_actions

        # 如果全部完成，更新声誉分数
        if restoration.progress >= 1.0:
            restoration.status = "completed"
            restoration.completed_at = datetime.now()

            # 更新声誉记录
            reputation = await self.get_by_member_id(restoration.member_id)
            if reputation:
                score_increase = restoration.target_score - reputation.total_score
                reputation.total_score = restoration.target_score
                reputation.level = self._calculate_level(restoration.target_score).value
                reputation.probation_mode = False
                reputation.probation_end_date = None
                reputation.restoration_progress = 1.0

                await self.db.commit()
                await self.db.refresh(reputation)

        await self.db.commit()
        await self.db.refresh(restoration)

        logger.info(f"完成恢复动作：{restoration_id}, {action}, 进度：{restoration.progress:.1%}")
        return restoration

    # ==================== 权益查询 ====================

    async def get_privileges(self, member_id: str) -> Dict[str, Any]:
        """获取成员权益"""
        reputation = await self.get_by_member_id(member_id)

        if reputation is None:
            # 默认新人权益
            level = ReputationLevel.NEWCOMER
        else:
            level = ReputationLevel(reputation.level)

        privilege = REPUTATION_PRIVILEGES.get(level)

        return {
            "member_id": member_id,
            "level": level.value,
            "score": reputation.total_score if reputation else 0,
            "privileges": privilege.privileges if privilege else [],
            "description": privilege.description if privilege else "",
            "next_level": self._get_next_level(level).value if level != ReputationLevel.LEGEND else None,
            "points_to_next_level": self._get_points_to_next_level(level, reputation.total_score if reputation else 0)
        }

    def _get_next_level(self, current: ReputationLevel) -> Optional[ReputationLevel]:
        """获取下一个等级"""
        levels = list(ReputationLevel)
        current_idx = levels.index(current)
        if current_idx < len(levels) - 1:
            return levels[current_idx + 1]
        return None

    def _get_points_to_next_level(self, current: ReputationLevel, current_score: int) -> int:
        """获取到下一个等级还需要的分数"""
        privilege = REPUTATION_PRIVILEGES.get(current)
        if privilege is None or current == ReputationLevel.LEGEND:
            return 0
        return privilege.max_score + 1 - current_score

    # ==================== 统计信息 ====================

    async def get_statistics(self) -> Dict[str, Any]:
        """获取声誉系统统计信息"""
        # 总成员数
        result = await self.db.execute(select(func.count(DBMemberReputation.id)))
        total_members = result.scalar() or 0

        # 各等级人数分布
        result = await self.db.execute(
            select(DBMemberReputation.level, func.count(DBMemberReputation.id))
            .group_by(DBMemberReputation.level)
        )
        level_distribution = dict(result.all())

        # 平均分数
        result = await self.db.execute(select(func.avg(DBMemberReputation.total_score)))
        avg_score = result.scalar() or 0

        # 观察模式中的成员数
        result = await self.db.execute(
            select(func.count(DBMemberReputation.id))
            .where(DBMemberReputation.probation_mode == True)
        )
        probation_count = result.scalar() or 0

        # 进行中的恢复申请数
        result = await self.db.execute(
            select(func.count(DBReputationRestoration.id))
            .where(DBReputationRestoration.status == "in_progress")
        )
        active_restorations = result.scalar() or 0

        return {
            "total_members": total_members,
            "level_distribution": level_distribution,
            "avg_score": round(avg_score, 1),
            "probation_count": probation_count,
            "active_restorations": active_restorations
        }

    async def list_members(
        self,
        level: Optional[ReputationLevel] = None,
        min_score: Optional[int] = None,
        max_score: Optional[int] = None,
        member_type: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[DBMemberReputation]:
        """获取成员声誉列表"""
        query = select(DBMemberReputation)

        if level:
            query = query.where(DBMemberReputation.level == level.value)
        if min_score is not None:
            query = query.where(DBMemberReputation.total_score >= min_score)
        if max_score is not None:
            query = query.where(DBMemberReputation.total_score <= max_score)
        if member_type:
            query = query.where(DBMemberReputation.member_type == member_type)

        query = query.order_by(desc(DBMemberReputation.total_score))
        query = query.offset(offset).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()


# 全局服务实例
_reputation_service: Optional[ReputationService] = None


def get_reputation_service(db: AsyncSession) -> ReputationService:
    """获取声誉服务实例"""
    global _reputation_service
    if _reputation_service is None or _reputation_service.db is not db:
        _reputation_service = ReputationService(db)
    return _reputation_service
