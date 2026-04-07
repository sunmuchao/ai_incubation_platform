"""
任务Repository，封装任务相关的数据库操作。
"""
from typing import List, Optional

from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models.db_models import TaskDB
from models.task import InteractionType, TaskPriority, TaskStatus
from repositories.base_repository import BaseRepository


class TaskRepository(BaseRepository[TaskDB]):
    """任务数据库操作类。"""

    def __init__(self, db: AsyncSession):
        super().__init__(TaskDB, db)

    async def get(self, task_id: str) -> Optional[TaskDB]:
        """根据 ID 获取任务。"""
        return await self.get_by_id(task_id)

    async def list_by_status(
        self,
        status: Optional[TaskStatus] = None,
        interaction_type: Optional[InteractionType] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[TaskDB]:
        """按状态和交互类型筛选任务。"""
        query = select(self.model)

        if status:
            query = query.where(self.model.status == status.value)
        if interaction_type:
            query = query.where(self.model.interaction_type == interaction_type.value)

        query = query.order_by(self.model.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def search_tasks(
        self,
        skill: Optional[str] = None,
        min_reward: float = 0,
        max_reward: Optional[float] = None,
        interaction_type: Optional[InteractionType] = None,
        location: Optional[str] = None,
        priority: Optional[TaskPriority] = None,
        keyword: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        skip: int = 0,
        limit: int = 100
    ) -> List[TaskDB]:
        """
        多维度搜索任务。
        """
        query = select(self.model).where(self.model.status == TaskStatus.PUBLISHED.value)

        # 交互类型筛选
        if interaction_type:
            query = query.where(self.model.interaction_type == interaction_type.value)

        # 优先级筛选
        if priority:
            query = query.where(self.model.priority == priority.value)

        # 地点模糊筛选
        if location:
            query = query.where(self.model.location_hint.ilike(f"%{location}%"))

        # 技能匹配
        if skill:
            skill_lower = skill.lower()
            query = query.where(
                or_(
                    # 匹配required_skills的key或value
                    func.jsonb_exists(self.model.required_skills, skill_lower),
                    func.jsonb_each_text(self.model.required_skills).value.ilike(f"%{skill_lower}%"),
                    # 匹配文本字段
                    self.model.title.ilike(f"%{skill_lower}%"),
                    self.model.description.ilike(f"%{skill_lower}%"),
                    func.array_to_string(self.model.requirements, ' ').ilike(f"%{skill_lower}%")
                )
            )

        # 关键词全文搜索
        if keyword:
            kw_lower = keyword.lower()
            query = query.where(
                or_(
                    self.model.title.ilike(f"%{kw_lower}%"),
                    self.model.description.ilike(f"%{kw_lower}%"),
                    func.array_to_string(self.model.requirements, ' ').ilike(f"%{kw_lower}%"),
                    self.model.capability_gap.ilike(f"%{kw_lower}%"),
                    self.model.location_hint.ilike(f"%{kw_lower}%")
                )
            )

        # 报酬范围筛选
        query = query.where(self.model.reward_amount >= min_reward)
        if max_reward is not None:
            query = query.where(self.model.reward_amount <= max_reward)

        # 排序
        sort_column_map = {
            "created_at": self.model.created_at,
            "reward": self.model.reward_amount,
            "priority": self.model.priority,
            "deadline": self.model.deadline,
        }
        sort_column = sort_column_map.get(sort_by, self.model.created_at)
        if sort_order.lower() == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        # 分页
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_worker_id(self, worker_id: str, status: Optional[TaskStatus] = None) -> List[TaskDB]:
        """获取工人承接的任务。"""
        query = select(self.model).where(self.model.worker_id == worker_id)
        if status:
            query = query.where(self.model.status == status.value)
        query = query.order_by(self.model.updated_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_employer_id(self, employer_id: str, status: Optional[TaskStatus] = None) -> List[TaskDB]:
        """获取雇主发布的任务。"""
        query = select(self.model).where(self.model.ai_employer_id == employer_id)
        if status:
            query = query.where(self.model.status == status.value)
        query = query.order_by(self.model.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())
