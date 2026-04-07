"""
Repository 基类
"""
from typing import TypeVar, Generic, Type, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime

from db.base import Base

T = TypeVar('T', bound=Base)


class BaseRepository(Generic[T]):
    """基础 Repository 类"""

    def __init__(self, model: Type[T], db: AsyncSession):
        self.model = model
        self.db = db

    async def get(self, id: str) -> Optional[T]:
        """根据 ID 获取记录"""
        result = await self.db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_by_ids(self, ids: List[str]) -> List[T]:
        """根据 ID 列表获取记录"""
        result = await self.db.execute(select(self.model).where(self.model.id.in_(ids)))
        return list(result.scalars().all())

    async def list(self, limit: int = 100, offset: int = 0) -> List[T]:
        """获取记录列表"""
        result = await self.db.execute(
            select(self.model)
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def count(self) -> int:
        """获取记录总数"""
        result = await self.db.execute(select(func.count()).select_from(self.model))
        return result.scalar()

    async def create(self, data: dict) -> T:
        """创建记录"""
        instance = self.model(**data)
        self.db.add(instance)
        await self.db.flush()
        await self.db.refresh(instance)
        return instance

    async def update(self, id: str, data: dict) -> Optional[T]:
        """更新记录"""
        instance = await self.get(id)
        if not instance:
            return None
        for key, value in data.items():
            setattr(instance, key, value)
        instance.updated_at = datetime.now()
        await self.db.flush()
        await self.db.refresh(instance)
        return instance

    async def delete(self, id: str) -> bool:
        """删除记录"""
        instance = await self.get(id)
        if not instance:
            return False
        await self.db.delete(instance)
        return True

    async def list_by_filter(self, filters: dict, limit: int = 100) -> List[T]:
        """根据过滤条件获取记录列表"""
        query = select(self.model)
        for key, value in filters.items():
            if value is not None:
                column = getattr(self.model, key, None)
                if column:
                    query = query.where(column == value)
        query = query.limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_field(self, field: str, value: any) -> Optional[T]:
        """根据字段值获取单条记录"""
        column = getattr(self.model, field, None)
        if not column:
            return None
        result = await self.db.execute(select(self.model).where(column == value))
        return result.scalar_one_or_none()
