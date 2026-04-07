"""
审计日志 Repository
"""
from typing import Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from repositories.base import BaseRepository
from db.models import DBAuditLog
from models.member import OperationType


class AuditLogRepository(BaseRepository[DBAuditLog]):
    """审计日志 Repository"""

    def __init__(self, db: AsyncSession):
        super().__init__(DBAuditLog, db)

    async def list_by_operator(
        self, operator_id: str, limit: int = 100
    ) -> List[DBAuditLog]:
        """根据操作人 ID 获取审计日志"""
        result = await self.db.execute(
            select(self.model)
            .where(self.model.operator_id == operator_id)
            .order_by(desc(self.model.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_by_operation_type(
        self, operation_type: OperationType, limit: int = 100
    ) -> List[DBAuditLog]:
        """根据操作类型获取审计日志"""
        result = await self.db.execute(
            select(self.model)
            .where(self.model.operation_type == operation_type)
            .order_by(desc(self.model.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_by_time_range(
        self,
        start_time: datetime,
        end_time: datetime,
        limit: int = 10000,
    ) -> List[DBAuditLog]:
        """根据时间范围获取审计日志"""
        result = await self.db.execute(
            select(self.model)
            .where(self.model.created_at >= start_time)
            .where(self.model.created_at <= end_time)
            .order_by(desc(self.model.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_by_filters(
        self,
        operator_id: Optional[str] = None,
        operation_type: Optional[OperationType] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[DBAuditLog]:
        """根据多条件过滤获取审计日志"""
        query = select(self.model)

        if operator_id:
            query = query.where(self.model.operator_id == operator_id)
        if operation_type:
            query = query.where(self.model.operation_type == operation_type)
        if start_time:
            query = query.where(self.model.created_at >= start_time)
        if end_time:
            query = query.where(self.model.created_at <= end_time)

        query = query.order_by(desc(self.model.created_at)).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())
