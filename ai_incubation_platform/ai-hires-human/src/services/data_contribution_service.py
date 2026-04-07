"""
用户贡献数据服务。
"""
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from models.data_contribution import (
    DataContributionDB,
    ContributionVoteDB,
    TaskTemplateContributionDB,
    GoldenStandardContributionDB,
    ContributorAchievementDB,
    ContributionRewardDB,
)


class DataContributionService:
    """数据贡献管理服务。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_contribution(
        self,
        contributor_id: str,
        contribution_type: str,
        title: str,
        description: str,
        content: Dict,
        contributor_type: str = "worker",
        related_task_id: Optional[str] = None,
        related_batch_id: Optional[str] = None,
    ) -> DataContributionDB:
        """创建新的数据贡献。"""
        contribution = DataContributionDB(
            contribution_id=str(uuid.uuid4()),
            contributor_id=contributor_id,
            contributor_type=contributor_type,
            contribution_type=contribution_type,
            title=title,
            description=description,
            content=content,
            related_task_id=related_task_id,
            related_batch_id=related_batch_id,
        )
        self.db.add(contribution)
        await self.db.commit()
        await self.db.refresh(contribution)
        return contribution

    async def get_contribution(self, contribution_id: str) -> Optional[DataContributionDB]:
        """获取贡献详情。"""
        result = await self.db.execute(
            select(DataContributionDB).where(DataContributionDB.contribution_id == contribution_id)
        )
        return result.scalar_one_or_none()

    async def list_contributions(
        self,
        contributor_id: Optional[str] = None,
        contribution_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[DataContributionDB]:
        """列出贡献记录。"""
        query = select(DataContributionDB)

        if contributor_id:
            query = query.where(DataContributionDB.contributor_id == contributor_id)
        if contribution_type:
            query = query.where(DataContributionDB.contribution_type == contribution_type)
        if status:
            query = query.where(DataContributionDB.status == status)

        query = query.order_by(DataContributionDB.created_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_contribution_status(
        self,
        contribution_id: str,
        status: str,
        review_notes: Optional[str] = None,
        reviewer_id: Optional[str] = None,
        quality_score: Optional[float] = None,
    ) -> bool:
        """更新贡献审核状态。"""
        contribution = await self.get_contribution(contribution_id)
        if not contribution:
            return False

        contribution.status = status
        if review_notes:
            contribution.review_notes = review_notes
        if reviewer_id:
            contribution.reviewed_by = reviewer_id
        if quality_score is not None:
            contribution.quality_score = quality_score
        contribution.reviewed_at = datetime.now()

        await self.db.commit()
        return True

    async def add_vote(
        self,
        contribution_id: str,
        voter_id: str,
        vote_type: str,  # "upvote" or "downvote"
    ) -> bool:
        """添加投票。"""
        # 检查是否已投票
        existing_vote = await self.db.execute(
            select(ContributionVoteDB).where(
                and_(
                    ContributionVoteDB.contribution_id == contribution_id,
                    ContributionVoteDB.voter_id == voter_id,
                )
            )
        )
        if existing_vote.scalar_one_or_none():
            return False  # 已经投过票

        # 创建投票
        vote = ContributionVoteDB(
            vote_id=str(uuid.uuid4()),
            contribution_id=contribution_id,
            voter_id=voter_id,
            vote_type=vote_type,
        )
        self.db.add(vote)

        # 更新贡献的投票计数
        contribution = await self.get_contribution(contribution_id)
        if contribution:
            if vote_type == "upvote":
                contribution.upvotes += 1
            else:
                contribution.downvotes += 1
            contribution.usefulness_score = (
                (contribution.upvotes / (contribution.upvotes + contribution.downvotes) * 100)
                if (contribution.upvotes + contribution.downvotes) > 0
                else 50.0
            )

        await self.db.commit()
        return True

    async def increment_usage(self, contribution_id: str) -> bool:
        """增加使用计数。"""
        contribution = await self.get_contribution(contribution_id)
        if contribution:
            contribution.usage_count += 1
            await self.db.commit()
            return True
        return False

    async def get_contributor_stats(self, contributor_id: str) -> Dict:
        """获取贡献者统计信息。"""
        # 总贡献数
        total_result = await self.db.execute(
            select(func.count(DataContributionDB.contribution_id)).where(
                DataContributionDB.contributor_id == contributor_id
            )
        )
        total_contributions = total_result.scalar() or 0

        # 已通过的贡献数
        approved_result = await self.db.execute(
            select(func.count(DataContributionDB.contribution_id)).where(
                and_(
                    DataContributionDB.contributor_id == contributor_id,
                    DataContributionDB.status == "approved",
                )
            )
        )
        approved_contributions = approved_result.scalar() or 0

        # 总奖励
        reward_result = await self.db.execute(
            select(func.sum(DataContributionDB.reward_amount)).where(
                and_(
                    DataContributionDB.contributor_id == contributor_id,
                    DataContributionDB.reward_status == "paid",
                )
            )
        )
        total_rewards = reward_result.scalar() or 0.0

        # 总点赞
        votes_result = await self.db.execute(
            select(func.sum(DataContributionDB.upvotes)).where(
                DataContributionDB.contributor_id == contributor_id
            )
        )
        total_upvotes = votes_result.scalar() or 0

        return {
            "total_contributions": total_contributions,
            "approved_contributions": approved_contributions,
            "approval_rate": (approved_contributions / total_contributions * 100) if total_contributions > 0 else 0,
            "total_rewards": total_rewards,
            "total_upvotes": total_upvotes,
        }


class TaskTemplateService:
    """任务模板贡献服务。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_template(
        self,
        contribution_id: str,
        template_name: str,
        category: str,
        title_template: str,
        description_template: str,
        acceptance_criteria_template: List,
        requirements_template: List,
        required_skills_template: Dict,
    ) -> TaskTemplateContributionDB:
        """创建任务模板。"""
        template = TaskTemplateContributionDB(
            template_id=str(uuid.uuid4()),
            contribution_id=contribution_id,
            template_name=template_name,
            category=category,
            title_template=title_template,
            description_template=description_template,
            acceptance_criteria_template=acceptance_criteria_template,
            requirements_template=requirements_template,
            required_skills_template=required_skills_template,
        )
        self.db.add(template)
        await self.db.commit()
        await self.db.refresh(template)
        return template

    async def get_template(self, template_id: str) -> Optional[TaskTemplateContributionDB]:
        """获取模板详情。"""
        result = await self.db.execute(
            select(TaskTemplateContributionDB).where(TaskTemplateContributionDB.template_id == template_id)
        )
        return result.scalar_one_or_none()

    async def get_template_by_name(self, template_name: str) -> Optional[TaskTemplateContributionDB]:
        """通过名称获取模板。"""
        result = await self.db.execute(
            select(TaskTemplateContributionDB).where(TaskTemplateContributionDB.template_name == template_name)
        )
        return result.scalar_one_or_none()

    async def list_templates(
        self,
        category: Optional[str] = None,
        limit: int = 20,
    ) -> List[TaskTemplateContributionDB]:
        """列出模板。"""
        query = select(TaskTemplateContributionDB)
        if category:
            query = query.where(TaskTemplateContributionDB.category == category)
        query = query.order_by(TaskTemplateContributionDB.usage_count.desc()).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def increment_template_usage(self, template_id: str) -> bool:
        """增加模板使用计数。"""
        template = await self.get_template(template_id)
        if template:
            template.usage_count += 1
            await self.db.commit()
            return True
        return False


class GoldenStandardTemplateService:
    """黄金标准测试模板服务。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_template(
        self,
        contribution_id: str,
        test_name: str,
        category: str,
        questions_template: List,
        passing_score_template: float = 80.0,
    ) -> GoldenStandardContributionDB:
        """创建黄金标准测试模板。"""
        template = GoldenStandardContributionDB(
            gs_template_id=str(uuid.uuid4()),
            contribution_id=contribution_id,
            test_name=test_name,
            category=category,
            questions_template=questions_template,
            passing_score_template=passing_score_template,
        )
        self.db.add(template)
        await self.db.commit()
        await self.db.refresh(template)
        return template

    async def get_template(self, template_id: str) -> Optional[GoldenStandardContributionDB]:
        """获取模板详情。"""
        result = await self.db.execute(
            select(GoldenStandardContributionDB).where(
                GoldenStandardContributionDB.gs_template_id == template_id
            )
        )
        return result.scalar_one_or_none()

    async def list_templates(
        self,
        category: Optional[str] = None,
        limit: int = 20,
    ) -> List[GoldenStandardContributionDB]:
        """列出模板。"""
        query = select(GoldenStandardContributionDB)
        if category:
            query = query.where(GoldenStandardContributionDB.category == category)
        query = query.order_by(GoldenStandardContributionDB.usage_count.desc()).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())


class ContributorAchievementService:
    """贡献者成就服务。"""

    ACHIEVEMENTS = {
        "first_contribution": {
            "name": "初次贡献",
            "description": "提交第一个数据贡献",
            "target": 1,
        },
        "dedicated_contributor": {
            "name": "积极贡献者",
            "description": "累计提交 10 个数据贡献",
            "target": 10,
        },
        "template_master": {
            "name": "模板大师",
            "description": "创建的模板被使用 100 次",
            "target": 100,
        },
        "quality_expert": {
            "name": "质量专家",
            "description": "获得 50 个点赞",
            "target": 50,
        },
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_and_award_achievements(self, contributor_id: str) -> List[str]:
        """检查并授予成就。"""
        unlocked_achievements = []

        # 获取贡献者统计
        from models.data_contribution import DataContributionDB
        from sqlalchemy import func, select

        total_result = await self.db.execute(
            select(func.count(DataContributionDB.contribution_id)).where(
                DataContributionDB.contributor_id == contributor_id
            )
        )
        total_contributions = total_result.scalar() or 0

        # 检查成就
        for achievement_type, achievement_info in self.ACHIEVEMENTS.items():
            # 检查是否已解锁
            existing = await self.db.execute(
                select(ContributorAchievementDB).where(
                    and_(
                        ContributorAchievementDB.contributor_id == contributor_id,
                        ContributorAchievementDB.achievement_type == achievement_type,
                    )
                )
            )
            if existing.scalar_one_or_none():
                continue  # 已经解锁

            # 创建成就记录
            achievement = ContributorAchievementDB(
                achievement_id=str(uuid.uuid4()),
                contributor_id=contributor_id,
                achievement_type=achievement_type,
                achievement_name=achievement_info["name"],
                achievement_description=achievement_info["description"],
                progress=min(total_contributions, achievement_info["target"]),
                target=achievement_info["target"],
                is_unlocked=total_contributions >= achievement_info["target"],
            )
            if achievement.is_unlocked:
                achievement.unlocked_at = datetime.now()
                unlocked_achievements.append(achievement_type)

            self.db.add(achievement)

        await self.db.commit()
        return unlocked_achievements

    async def get_contributor_achievements(self, contributor_id: str) -> List[ContributorAchievementDB]:
        """获取贡献者的所有成就。"""
        result = await self.db.execute(
            select(ContributorAchievementDB).where(
                ContributorAchievementDB.contributor_id == contributor_id
            )
        )
        return list(result.scalars().all())


class ContributionRewardService:
    """贡献奖励服务。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_reward(
        self,
        contribution_id: str,
        contributor_id: str,
        reward_type: str,
        reward_amount: float = 0.0,
        reward_points: int = 0,
        reward_reason: str = "",
    ) -> ContributionRewardDB:
        """创建奖励记录。"""
        reward = ContributionRewardDB(
            reward_id=str(uuid.uuid4()),
            contribution_id=contribution_id,
            contributor_id=contributor_id,
            reward_type=reward_type,
            reward_amount=reward_amount,
            reward_currency="CNY",
            reward_points=reward_points,
            reward_reason=reward_reason,
        )
        self.db.add(reward)
        await self.db.commit()
        await self.db.refresh(reward)
        return reward

    async def mark_reward_paid(self, reward_id: str) -> bool:
        """标记奖励已支付。"""
        result = await self.db.execute(
            select(ContributionRewardDB).where(ContributionRewardDB.reward_id == reward_id)
        )
        reward = result.scalar_one_or_none()
        if not reward:
            return False

        reward.status = "paid"
        reward.paid_at = datetime.now()
        await self.db.commit()
        return True

    async def get_contributor_rewards(self, contributor_id: str) -> List[ContributionRewardDB]:
        """获取贡献者的所有奖励。"""
        result = await self.db.execute(
            select(ContributionRewardDB).where(
                ContributorAchievementDB.contributor_id == contributor_id
            )
        )
        return list(result.scalars().all())
