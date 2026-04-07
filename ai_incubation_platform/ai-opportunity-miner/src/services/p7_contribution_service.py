"""
P7 - 用户贡献数据服务

功能：
1. 用户提交商机/数据源/验证信息
2. 审核工作流（管理员审核）
3. 质量评分与积分奖励
4. 社区投票机制
"""
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from models.db_models import (
    UserContributionDB, UserPointsDB, PointsTransactionDB,
    CommunityVoteDB, UserDB, BusinessOpportunityDB
)


class ContributionService:
    """用户贡献服务"""

    # 贡献类型枚举
    CONTRIBUTION_TYPES = ["opportunity", "data_source", "verification", "correction"]

    # 审核状态枚举
    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"

    # 积分奖励配置
    POINTS_REWARDS = {
        "contribution_submitted": 0,      # 提交贡献：0 分（待审核）
        "contribution_approved": 10,      # 审核通过：10 分
        "contribution_adopted": 50,       # 被采纳：50 分
        "quality_bonus": 20,              # 高质量额外奖励：20 分
    }

    # 信誉等级配置
    REPUTATION_LEVELS = {
        "bronze": (0, 20),
        "silver": (20, 40),
        "gold": (40, 60),
        "platinum": (60, 80),
        "diamond": (80, 100),
    }

    def __init__(self, db: Session):
        self.db = db

    # ==================== 贡献管理 ====================

    def create_contribution(
        self,
        user_id: str,
        contribution_type: str,
        title: str,
        description: str,
        content: Dict = None,
        source_url: str = None,
        source_evidence: Dict = None,
    ) -> UserContributionDB:
        """创建用户贡献"""
        if contribution_type not in self.CONTRIBUTION_TYPES:
            raise ValueError(f"无效的贡献类型：{contribution_type}")

        contribution = UserContributionDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            contribution_type=contribution_type,
            title=title,
            description=description,
            content=content or {},
            source_url=source_url,
            source_evidence=source_evidence or {},
            status=self.STATUS_PENDING,
        )

        self.db.add(contribution)
        self.db.commit()
        self.db.refresh(contribution)

        # 更新用户贡献计数
        self._increment_user_contribution_count(user_id)

        return contribution

    def get_contribution(self, contribution_id: str) -> Optional[UserContributionDB]:
        """获取贡献详情"""
        return self.db.query(UserContributionDB).filter(
            UserContributionDB.id == contribution_id
        ).first()

    def list_contributions(
        self,
        user_id: str = None,
        status: str = None,
        contribution_type: str = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[UserContributionDB]:
        """获取贡献列表（支持筛选）"""
        query = self.db.query(UserContributionDB)

        if user_id:
            query = query.filter(UserContributionDB.user_id == user_id)
        if status:
            query = query.filter(UserContributionDB.status == status)
        if contribution_type:
            query = query.filter(UserContributionDB.contribution_type == contribution_type)

        return query.order_by(
            UserContributionDB.created_at.desc()
        ).offset(offset).limit(limit).all()

    # ==================== 审核管理 ====================

    def review_contribution(
        self,
        contribution_id: str,
        reviewer_id: str,
        status: str,
        review_notes: str = None,
        quality_score: float = None,
    ) -> UserContributionDB:
        """审核贡献"""
        contribution = self.get_contribution(contribution_id)
        if not contribution:
            raise ValueError(f"贡献 {contribution_id} 不存在")

        if status not in [self.STATUS_APPROVED, self.STATUS_REJECTED]:
            raise ValueError(f"无效的审核状态：{status}")

        # 更新审核信息
        contribution.status = status
        contribution.reviewed_by = reviewer_id
        contribution.reviewed_at = datetime.now()
        contribution.review_notes = review_notes
        contribution.quality_score = quality_score

        # 如果审核通过，奖励积分
        if status == self.STATUS_APPROVED:
            points = self.POINTS_REWARDS["contribution_approved"]
            self._award_points(contribution.user_id, "contribution_approved", points, contribution_id)
            self._increment_approved_count(contribution.user_id)

        self.db.commit()
        self.db.refresh(contribution)

        return contribution

    def adopt_contribution(
        self,
        contribution_id: str,
        opportunity_id: str,
    ) -> UserContributionDB:
        """采纳贡献（将用户提交的商机加入系统）"""
        contribution = self.get_contribution(contribution_id)
        if not contribution:
            raise ValueError(f"贡献 {contribution_id} 不存在")

        if contribution.status != self.STATUS_APPROVED:
            raise ValueError(f"只有审核通过的贡献才能被采纳")

        contribution.is_adopted = True
        contribution.adopted_opportunity_id = opportunity_id

        # 奖励采纳积分
        points = self.POINTS_REWARDS["contribution_adopted"]
        self._award_points(contribution.user_id, "contribution_adopted", points, contribution_id)
        self._increment_adopted_count(contribution.user_id)

        # 如果质量分数高，额外奖励
        if contribution.quality_score and contribution.quality_score >= 80:
            bonus_points = self.POINTS_REWARDS["quality_bonus"]
            self._award_points(contribution.user_id, "quality_bonus", bonus_points, contribution_id)

        self.db.commit()
        self.db.refresh(contribution)

        return contribution

    # ==================== 社区投票 ====================

    def vote_contribution(
        self,
        user_id: str,
        contribution_id: str,
        vote_type: str,
    ) -> CommunityVoteDB:
        """对贡献进行投票"""
        # 检查贡献是否存在
        contribution = self.get_contribution(contribution_id)
        if not contribution:
            raise ValueError(f"贡献 {contribution_id} 不存在")

        # 检查是否已投过票
        existing_vote = self.db.query(CommunityVoteDB).filter(
            CommunityVoteDB.user_id == user_id,
            CommunityVoteDB.target_type == "contribution",
            CommunityVoteDB.target_id == contribution_id,
        ).first()

        if existing_vote:
            # 更新现有投票
            existing_vote.vote_type = vote_type
            existing_vote.weight = self._get_vote_weight(user_id)
            self.db.commit()
            self.db.refresh(existing_vote)
            return existing_vote
        else:
            # 创建新投票
            vote = CommunityVoteDB(
                id=str(uuid.uuid4()),
                user_id=user_id,
                target_type="contribution",
                target_id=contribution_id,
                vote_type=vote_type,
                weight=self._get_vote_weight(user_id),
            )
            self.db.add(vote)
            self.db.commit()

            # 更新贡献的投票数
            self._update_contribution_votes(contribution_id)

            return vote

    def _update_contribution_votes(self, contribution_id: str):
        """更新贡献的投票统计"""
        upvotes = self.db.query(CommunityVoteDB).filter(
            CommunityVoteDB.target_type == "contribution",
            CommunityVoteDB.target_id == contribution_id,
            CommunityVoteDB.vote_type == "upvote",
        ).count()

        downvotes = self.db.query(CommunityVoteDB).filter(
            CommunityVoteDB.target_type == "contribution",
            CommunityVoteDB.target_id == contribution_id,
            CommunityVoteDB.vote_type == "downvote",
        ).count()

        contribution = self.get_contribution(contribution_id)
        if contribution:
            contribution.community_votes = upvotes - downvotes
            self.db.commit()

    def _get_vote_weight(self, user_id: str) -> float:
        """获取用户投票权重（基于信誉分数）"""
        points_account = self.db.query(UserPointsDB).filter(
            UserPointsDB.user_id == user_id
        ).first()

        if not points_account:
            return 1.0

        # 信誉分数越高，投票权重越大
        base_weight = 1.0
        reputation_bonus = points_account.reputation_score / 100.0
        return base_weight + reputation_bonus

    # ==================== 积分管理 ====================

    def _award_points(
        self,
        user_id: str,
        action: str,
        points: int,
        related_contribution_id: str = None,
    ):
        """奖励用户积分"""
        # 获取或创建积分账户
        points_account = self._get_or_create_points_account(user_id)

        # 更新积分
        points_account.total_points += points
        points_account.available_points += points

        # 创建交易记录
        transaction = PointsTransactionDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            transaction_type="earn",
            action=action,
            points_change=points,
            balance_after=points_account.available_points,
            related_contribution_id=related_contribution_id,
            description=f"获得积分：{action}",
            extra_data=None,
        )
        self.db.add(transaction)

        # 更新信誉等级
        self._update_reputation_level(points_account)

    def _get_or_create_points_account(self, user_id: str) -> UserPointsDB:
        """获取或创建用户积分账户"""
        account = self.db.query(UserPointsDB).filter(
            UserPointsDB.user_id == user_id
        ).first()

        if not account:
            account = UserPointsDB(
                id=str(uuid.uuid4()),
                user_id=user_id,
            )
            self.db.add(account)
            self.db.commit()
            self.db.refresh(account)

        return account

    def _update_reputation_level(self, points_account: UserPointsDB):
        """更新用户信誉等级"""
        # 计算信誉分数
        score = 0.0

        # 基于贡献数量
        score += min(points_account.contributions_count * 2, 30)  # 最多 30 分

        # 基于采纳率
        if points_account.contributions_count > 0:
            adoption_rate = points_account.adopted_contributions_count / points_account.contributions_count
            score += adoption_rate * 40  # 最多 40 分

        # 基于已用积分
        score += min(points_account.spent_points / 10, 30)  # 最多 30 分

        score = min(score, 100)  # 上限 100 分
        points_account.reputation_score = score

        # 更新等级
        for level, (min_score, max_score) in self.REPUTATION_LEVELS.items():
            if min_score <= score < max_score:
                points_account.reputation_level = level
                break
        else:
            points_account.reputation_level = "diamond"

    def _increment_user_contribution_count(self, user_id: str):
        """增加用户贡献计数"""
        account = self._get_or_create_points_account(user_id)
        account.contributions_count += 1
        self.db.commit()

    def _increment_approved_count(self, user_id: str):
        """增加审核通过计数"""
        account = self._get_or_create_points_account(user_id)
        account.approved_contributions_count += 1
        self.db.commit()

    def _increment_adopted_count(self, user_id: str):
        """增加采纳计数"""
        account = self._get_or_create_points_account(user_id)
        account.adopted_contributions_count += 1
        self.db.commit()

    def get_user_points(self, user_id: str) -> Optional[UserPointsDB]:
        """获取用户积分账户"""
        return self.db.query(UserPointsDB).filter(
            UserPointsDB.user_id == user_id
        ).first()

    def get_points_transactions(
        self,
        user_id: str,
        limit: int = 50,
    ) -> List[PointsTransactionDB]:
        """获取积分交易记录"""
        return self.db.query(PointsTransactionDB).filter(
            PointsTransactionDB.user_id == user_id
        ).order_by(
            PointsTransactionDB.created_at.desc()
        ).limit(limit).all()


# 全局单例
_contribution_service_instances = {}


def get_contribution_service(db: Session) -> ContributionService:
    """获取贡献服务实例"""
    return ContributionService(db)
