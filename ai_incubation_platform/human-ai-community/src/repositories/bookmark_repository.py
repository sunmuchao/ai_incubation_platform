"""
收藏 Repository
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from repositories.base import BaseRepository
from db.models import DBBookmark
from models.member import ContentType


class BookmarkRepository(BaseRepository[DBBookmark]):
    """收藏 Repository"""

    def __init__(self, db: AsyncSession):
        super().__init__(DBBookmark, db)

    async def get_by_user_and_content(
        self,
        user_id: str,
        content_id: str,
        content_type: ContentType
    ) -> Optional[DBBookmark]:
        """检查用户是否已收藏某内容"""
        result = await self.db.execute(
            select(self.model)
            .where(self.model.user_id == user_id)
            .where(self.model.content_id == content_id)
            .where(self.model.content_type == content_type)
        )
        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        user_id: str,
        folder: Optional[str] = None,
        limit: int = 50
    ) -> List[DBBookmark]:
        """获取用户的收藏列表"""
        stmt = select(self.model).where(self.model.user_id == user_id)
        if folder:
            stmt = stmt.where(self.model.folder == folder)
        stmt = stmt.order_by(desc(self.model.created_at)).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_by_content(
        self,
        content_id: str,
        content_type: ContentType,
        limit: int = 100
    ) -> List[DBBookmark]:
        """获取某内容的收藏列表"""
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
        """统计某内容的收藏数"""
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
        """取消收藏"""
        bookmark = await self.get_by_user_and_content(user_id, content_id, content_type)
        if bookmark:
            await self.delete(bookmark.id)
            return True
        return False

    async def list_folders(self, user_id: str) -> List[str]:
        """获取用户的所有收藏夹名称"""
        result = await self.db.execute(
            select(func.distinct(self.model.folder))
            .where(self.model.user_id == user_id)
        )
        return [row[0] for row in result.all()]
