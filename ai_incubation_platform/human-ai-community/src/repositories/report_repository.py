"""
举报 Repository
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from repositories.base import BaseRepository
from db.models import DBReport
from models.member import ReportStatus


class ReportRepository(BaseRepository[DBReport]):
    """举报 Repository"""

    def __init__(self, db: AsyncSession):
        super().__init__(DBReport, db)

    async def list_pending_reports(self, limit: int = 100) -> List[DBReport]:
        """获取待处理的举报列表"""
        result = await self.db.execute(
            select(self.model)
            .where(self.model.status == ReportStatus.PENDING)
            .order_by(self.model.created_at)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_by_reporter(self, reporter_id: str, limit: int = 50) -> List[DBReport]:
        """根据举报人 ID 获取举报列表"""
        result = await self.db.execute(
            select(self.model)
            .where(self.model.reporter_id == reporter_id)
            .order_by(desc(self.model.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_by_handler(self, handler_id: str, limit: int = 50) -> List[DBReport]:
        """根据处理人 ID 获取举报列表"""
        result = await self.db.execute(
            select(self.model)
            .where(self.model.handler_id == handler_id)
            .order_by(desc(self.model.updated_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_by_status(self, status: ReportStatus, limit: int = 100) -> List[DBReport]:
        """根据状态获取举报列表"""
        result = await self.db.execute(
            select(self.model)
            .where(self.model.status == status)
            .order_by(desc(self.model.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())
