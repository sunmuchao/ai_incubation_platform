"""
投票服务层
支持投票创建、投票管理、投票统计等功能
"""
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.activity_models import (
    DBVote, DBVoteOption, DBVoteRecord, DBActivity,
    VoteTypeEnum, VoteStatusEnum, ActivityStatusEnum
)
from core.logging_config import get_logger

logger = get_logger(__name__)


class VoteService:
    """投票服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ==================== 投票管理 ====================

    async def create_vote(
        self,
        activity_id: str,
        title: str,
        vote_type: VoteTypeEnum,
        start_time: datetime,
        end_time: datetime,
        description: Optional[str] = None,
        min_choices: int = 1,
        max_choices: int = 1,
        is_anonymous: bool = False,
        show_results_before_vote: bool = False,
    ) -> Tuple[bool, Optional[DBVote], str]:
        """创建投票"""
        # 检查活动是否存在
        result = await self.db.execute(
            select(DBActivity).where(DBActivity.id == activity_id)
        )
        activity = result.scalar_one_or_none()
        if not activity:
            return False, None, "关联活动不存在"

        # 验证投票类型
        if vote_type == VoteTypeEnum.MULTIPLE_CHOICE and max_choices < 1:
            return False, None, "多选题最多选择数必须大于 0"
        if vote_type == VoteTypeEnum.SINGLE_CHOICE:
            max_choices = 1
            min_choices = 1

        # 确定投票状态
        now = datetime.now(start_time.tzinfo) if start_time.tzinfo else datetime.now()
        if start_time > now:
            status = VoteStatusEnum.DRAFT
        elif end_time <= now:
            status = VoteStatusEnum.ENDED
        else:
            status = VoteStatusEnum.ACTIVE

        vote_id = str(uuid.uuid4())
        vote = DBVote(
            id=vote_id,
            activity_id=activity_id,
            title=title,
            description=description,
            vote_type=vote_type,
            status=status,
            start_time=start_time,
            end_time=end_time,
            min_choices=min_choices,
            max_choices=max_choices,
            is_anonymous=is_anonymous,
            show_results_before_vote=show_results_before_vote,
        )

        self.db.add(vote)
        await self.db.commit()
        await self.db.refresh(vote)

        logger.info(f"投票已创建：{vote_id}, 标题：{title}")
        return True, vote, "投票创建成功"

    async def get_vote(self, vote_id: str) -> Optional[DBVote]:
        """获取投票详情"""
        result = await self.db.execute(
            select(DBVote).where(DBVote.id == vote_id)
        )
        return result.scalar_one_or_none()

    async def update_vote(
        self,
        vote_id: str,
        **kwargs
    ) -> Optional[DBVote]:
        """更新投票"""
        vote = await self.get_vote(vote_id)
        if not vote:
            return None

        # 已结束的投票不能修改
        if vote.status == VoteStatusEnum.ENDED:
            raise ValueError("已结束的投票不能修改")

        allowed_fields = [
            "title", "description", "vote_type", "status", "start_time", "end_time",
            "min_choices", "max_choices", "is_anonymous", "show_results_before_vote"
        ]

        for field in allowed_fields:
            if field in kwargs:
                setattr(vote, field, kwargs[field])

        await self.db.commit()
        await self.db.refresh(vote)

        logger.info(f"投票已更新：{vote_id}")
        return vote

    async def delete_vote(self, vote_id: str) -> bool:
        """删除投票"""
        vote = await self.get_vote(vote_id)
        if not vote:
            return False

        # 已有投票记录的投票不能删除
        if vote.total_voters > 0:
            raise ValueError("已有投票记录的投票不能删除")

        await self.db.delete(vote)
        await self.db.commit()

        logger.info(f"投票已删除：{vote_id}")
        return True

    async def get_votes_by_activity(self, activity_id: str) -> List[DBVote]:
        """获取活动的所有投票"""
        result = await self.db.execute(
            select(DBVote)
            .where(DBVote.activity_id == activity_id)
            .order_by(DBVote.created_at)
        )
        return list(result.scalars().all())

    async def get_active_votes(self, limit: int = 50) -> List[DBVote]:
        """获取进行中的投票"""
        now = datetime.now()
        result = await self.db.execute(
            select(DBVote)
            .where(DBVote.status == VoteStatusEnum.ACTIVE)
            .where(DBVote.start_time <= now)
            .where(DBVote.end_time > now)
            .order_by(desc(DBVote.total_voters))
            .limit(limit)
        )
        return list(result.scalars().all())

    # ==================== 投票选项管理 ====================

    async def add_vote_option(
        self,
        vote_id: str,
        title: str,
        description: Optional[str] = None,
        image_url: Optional[str] = None,
        order_index: Optional[int] = None,
    ) -> Tuple[bool, Optional[DBVoteOption], str]:
        """添加投票选项"""
        vote = await self.get_vote(vote_id)
        if not vote:
            return False, None, "投票不存在"

        # 已有投票记录的投票不能添加选项
        if vote.total_voters > 0:
            return False, None, "已有投票记录的投票不能添加选项"

        # 获取当前最大 order_index
        if order_index is None:
            result = await self.db.execute(
                select(func.max(DBVoteOption.order_index))
                .where(DBVoteOption.vote_id == vote_id)
            )
            max_order = result.scalar_one_or_none()
            order_index = (max_order or 0) + 1

        option = DBVoteOption(
            id=str(uuid.uuid4()),
            vote_id=vote_id,
            title=title,
            description=description,
            image_url=image_url,
            order_index=order_index,
        )

        self.db.add(option)
        await self.db.commit()
        await self.db.refresh(option)

        logger.info(f"投票选项已添加：{option.id}, 标题：{title}")
        return True, option, "选项添加成功"

    async def get_vote_options(self, vote_id: str) -> List[DBVoteOption]:
        """获取投票选项列表"""
        result = await self.db.execute(
            select(DBVoteOption)
            .where(DBVoteOption.vote_id == vote_id)
            .order_by(DBVoteOption.order_index)
        )
        return list(result.scalars().all())

    async def update_vote_option(
        self,
        option_id: str,
        **kwargs
    ) -> Optional[DBVoteOption]:
        """更新投票选项"""
        result = await self.db.execute(
            select(DBVoteOption).where(DBVoteOption.id == option_id)
        )
        option = result.scalar_one_or_none()
        if not option:
            return None

        vote = await self.get_vote(option.vote_id)
        if vote and vote.total_voters > 0:
            raise ValueError("已有投票记录的投票不能修改选项")

        allowed_fields = ["title", "description", "image_url", "order_index"]
        for field in allowed_fields:
            if field in kwargs:
                setattr(option, field, kwargs[field])

        await self.db.commit()
        await self.db.refresh(option)

        return option

    async def delete_vote_option(self, option_id: str) -> bool:
        """删除投票选项"""
        result = await self.db.execute(
            select(DBVoteOption).where(DBVoteOption.id == option_id)
        )
        option = result.scalar_one_or_none()
        if not option:
            return False

        vote = await self.get_vote(option.vote_id)
        if vote and vote.total_voters > 0:
            raise ValueError("已有投票记录的投票不能删除选项")

        await self.db.delete(option)
        await self.db.commit()

        logger.info(f"投票选项已删除：{option_id}")
        return True

    # ==================== 投票参与 ====================

    async def cast_vote(
        self,
        vote_id: str,
        user_id: str,
        selected_options: List[str],
    ) -> Tuple[bool, Optional[DBVoteRecord], str]:
        """投票"""
        vote = await self.get_vote(vote_id)
        if not vote:
            return False, None, "投票不存在"

        # 检查投票状态
        if vote.status != VoteStatusEnum.ACTIVE:
            return False, None, "投票未在进行中"

        # 检查是否已投票
        existing = await self.get_vote_record(vote_id, user_id)
        if existing:
            return False, None, "您已参与投票"

        # 验证选项数量
        option_count = len(selected_options)
        if option_count < vote.min_choices:
            return False, None, f"至少选择 {vote.min_choices} 个选项"
        if option_count > vote.max_choices:
            return False, None, f"最多选择 {vote.max_choices} 个选项"

        # 验证选项是否存在
        options = await self.get_vote_options(vote_id)
        valid_option_ids = {opt.id for opt in options}
        for option_id in selected_options:
            if option_id not in valid_option_ids:
                return False, None, "无效的选项 ID"

        # 创建投票记录
        record = DBVoteRecord(
            id=str(uuid.uuid4()),
            vote_id=vote_id,
            user_id=user_id,
            selected_options=selected_options,
        )

        self.db.add(record)

        # 更新选项得票数
        for option_id in selected_options:
            for option in options:
                if option.id == option_id:
                    option.vote_count += 1

        # 更新投票统计
        vote.total_voters += 1
        vote.total_votes += len(selected_options)

        # 更新得票百分比
        await self._update_vote_percentages(vote_id)

        # 检查是否需要结束投票
        await self._check_vote_status(vote)

        await self.db.commit()
        await self.db.refresh(record)

        logger.info(f"用户 {user_id} 已参与投票 {vote_id}")
        return True, record, "投票成功"

    async def _update_vote_percentages(self, vote_id: str):
        """更新投票百分比"""
        vote = await self.get_vote(vote_id)
        if not vote or vote.total_votes == 0:
            return

        options = await self.get_vote_options(vote_id)
        for option in options:
            if vote.total_votes > 0:
                option.vote_percentage = round(option.vote_count / vote.total_votes * 100, 2)
            else:
                option.vote_percentage = 0.0

    async def _check_vote_status(self, vote: DBVote):
        """检查投票状态"""
        now = datetime.now()
        if vote.end_time <= now and vote.status != VoteStatusEnum.ENDED:
            vote.status = VoteStatusEnum.ENDED

    async def get_vote_record(self, vote_id: str, user_id: str) -> Optional[DBVoteRecord]:
        """获取用户投票记录"""
        result = await self.db.execute(
            select(DBVoteRecord)
            .where(DBVoteRecord.vote_id == vote_id)
            .where(DBVoteRecord.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_vote_results(self, vote_id: str) -> Dict[str, Any]:
        """获取投票结果"""
        vote = await self.get_vote(vote_id)
        if not vote:
            return {}

        options = await self.get_vote_options(vote_id)

        return {
            "vote_id": vote.id,
            "title": vote.title,
            "vote_type": vote.vote_type.value,
            "status": vote.status.value,
            "total_voters": vote.total_voters,
            "total_votes": vote.total_votes,
            "is_anonymous": vote.is_anonymous,
            "options": [
                {
                    "id": opt.id,
                    "title": opt.title,
                    "description": opt.description,
                    "vote_count": opt.vote_count,
                    "vote_percentage": opt.vote_percentage,
                    "image_url": opt.image_url,
                }
                for opt in options
            ],
        }

    async def end_vote(self, vote_id: str) -> Tuple[bool, Optional[DBVote], str]:
        """手动结束投票"""
        vote = await self.get_vote(vote_id)
        if not vote:
            return False, None, "投票不存在"

        if vote.status == VoteStatusEnum.ENDED:
            return False, None, "投票已结束"

        vote.status = VoteStatusEnum.ENDED
        await self.db.commit()
        await self.db.refresh(vote)

        logger.info(f"投票已手动结束：{vote_id}")
        return True, vote, "投票已结束"


def get_vote_service(db: AsyncSession) -> VoteService:
    """获取投票服务实例"""
    return VoteService(db)
