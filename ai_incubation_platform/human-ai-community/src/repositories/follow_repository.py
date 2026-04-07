"""
关注关系 Repository
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from repositories.base import BaseRepository
from db.models import DBFollow


class FollowRepository(BaseRepository[DBFollow]):
    """关注关系 Repository"""

    def __init__(self, db: AsyncSession):
        super().__init__(DBFollow, db)

    async def get_follow_relationship(
        self,
        follower_id: str,
        following_id: str
    ) -> Optional[DBFollow]:
        """获取关注关系"""
        result = await self.db.execute(
            select(self.model)
            .where(self.model.follower_id == follower_id)
            .where(self.model.following_id == following_id)
        )
        return result.scalar_one_or_none()

    async def list_following(self, user_id: str, limit: int = 100) -> List[DBFollow]:
        """获取用户关注的列表"""
        result = await self.db.execute(
            select(self.model)
            .where(self.model.follower_id == user_id)
            .order_by(desc(self.model.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_followers(self, user_id: str, limit: int = 100) -> List[DBFollow]:
        """获取用户的粉丝列表"""
        result = await self.db.execute(
            select(self.model)
            .where(self.model.following_id == user_id)
            .order_by(desc(self.model.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_following(self, user_id: str) -> int:
        """统计用户关注数"""
        result = await self.db.execute(
            select(func.count())
            .select_from(self.model)
            .where(self.model.follower_id == user_id)
        )
        return result.scalar() or 0

    async def count_followers(self, user_id: str) -> int:
        """统计用户粉丝数"""
        result = await self.db.execute(
            select(func.count())
            .select_from(self.model)
            .where(self.model.following_id == user_id)
        )
        return result.scalar() or 0

    async def delete_follow_relationship(
        self,
        follower_id: str,
        following_id: str
    ) -> bool:
        """取消关注"""
        follow = await self.get_follow_relationship(follower_id, following_id)
        if follow:
            await self.delete(follow.id)
            return True
        return False

    async def is_following(self, follower_id: str, following_id: str) -> bool:
        """检查是否已关注"""
        follow = await self.get_follow_relationship(follower_id, following_id)
        return follow is not None
