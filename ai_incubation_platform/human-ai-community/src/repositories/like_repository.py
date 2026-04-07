"""
点赞 Repository
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from repositories.base import BaseRepository
from db.models import DBLike
from models.member import ContentType


class LikeRepository(BaseRepository[DBLike]):
    """点赞 Repository"""

    def __init__(self, db: AsyncSession):
        super().__init__(DBLike, db)

    async def get_by_user_and_content(
        self,
        user_id: str,
        content_id: str,
        content_type: ContentType
    ) -> Optional[DBLike]:
        """检查用户是否已点赞某内容"""
        result = await self.db.execute(
            select(self.model)
            .where(self.model.user_id == user_id)
            .where(self.model.content_id == content_id)
            .where(self.model.content_type == content_type)
        )
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: str, limit: int = 50) -> List[DBLike]:
        """获取用户的点赞列表"""
        result = await self.db.execute(
            select(self.model)
            .where(self.model.user_id == user_id)
            .order_by(desc(self.model.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_by_content(
        self,
        content_id: str,
        content_type: ContentType,
        limit: int = 100
    ) -> List[DBLike]:
        """获取某内容的点赞列表"""
        result = await self.db.execute(
            select(self.model)
            .where(self.model.content_id == content_id)
            .where(self.model.content_type == content_type)
            .order_by(desc(self.model.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_by_content(
        self,
        content_id: str,
        content_type: ContentType
    ) -> int:
        """统计某内容的点赞数"""
        result = await self.db.execute(
            select(func.count())
            .select_from(self.model)
            .where(self.model.content_id == content_id)
            .where(self.model.content_type == content_type)
        )
        return result.scalar() or 0

    async def delete_by_user_and_content(
        self,
        user_id: str,
        content_id: str,
        content_type: ContentType
    ) -> bool:
        """取消点赞"""
        like = await self.get_by_user_and_content(user_id, content_id, content_type)
        if like:
            await self.delete(like.id)
            return True
        return False
