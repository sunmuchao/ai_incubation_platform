"""
通知 Repository
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, update
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from repositories.base import BaseRepository
from db.models import DBNotification


class NotificationRepository(BaseRepository[DBNotification]):
    """通知 Repository"""

    def __init__(self, db: AsyncSession):
        super().__init__(DBNotification, db)

    async def list_by_recipient(
        self,
        recipient_id: str,
        is_read: Optional[bool] = None,
        limit: int = 100
    ) -> List[DBNotification]:
        """获取用户的通知列表"""
        stmt = select(self.model).where(self.model.recipient_id == recipient_id)
        if is_read is not None:
            stmt = stmt.where(self.model.is_read == is_read)
        stmt = stmt.order_by(desc(self.model.created_at)).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_unread(self, recipient_id: str) -> int:
        """统计用户未读通知数"""
        result = await self.db.execute(
            select(func.count())
            .select_from(self.model)
            .where(self.model.recipient_id == recipient_id)
            .where(self.model.is_read == False)
        )
        return result.scalar() or 0

    async def mark_as_read(self, notification_id: str) -> bool:
        """标记通知为已读"""
        notification = await self.get(notification_id)
        if notification:
            notification.is_read = True
            notification.read_at = datetime.now()
            await self.db.commit()
            return True
        return False

    async def mark_all_as_read(self, recipient_id: str) -> int:
        """标记用户所有通知为已读"""
        stmt = (
            update(self.model)
            .where(self.model.recipient_id == recipient_id)
            .where(self.model.is_read == False)
            .values(is_read=True, read_at=datetime.now())
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount

    async def list_unread_by_recipient(
        self,
        recipient_id: str,
        limit: int = 100
    ) -> List[DBNotification]:
        """获取用户的未读通知列表"""
        result = await self.db.execute(
            select(self.model)
            .where(self.model.recipient_id == recipient_id)
            .where(self.model.is_read == False)
            .order_by(desc(self.model.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())
