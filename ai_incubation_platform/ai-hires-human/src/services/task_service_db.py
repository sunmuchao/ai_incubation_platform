"""
任务服务 - 数据库持久化实现。

基于 PostgreSQL + SQLAlchemy 异步实现，支持：
1. 任务 CRUD 操作
2. 多维度搜索与筛选
3. 状态机流转
4. 回调触发
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import select, update, delete, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models.db_models import TaskDB
from models.task import (
    InteractionType,
    Task,
    TaskCreate,
    TaskPriority,
    TaskStatus,
)
from repositories.task_repository import TaskRepository

logger = logging.getLogger(__name__)


class DatabaseTaskService:
    """基于数据库的任务服务。"""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.repository = TaskRepository(db_session)

    async def create_task(self, data: TaskCreate) -> Task:
        """AI / Agent 因能力缺口发布任务。"""
        # 准备数据库模型数据
        task_db = TaskDB(
            ai_employer_id=data.ai_employer_id,
            title=data.title,
            description=data.description,
            requirements=data.requirements,
            interaction_type=data.interaction_type.value,
            capability_gap=data.capability_gap,
            acceptance_criteria=data.acceptance_criteria,
            location_hint=data.location_hint,
            required_skills=data.required_skills,
            priority=data.priority.value,
            status=TaskStatus.PUBLISHED.value if data.publish_immediately else TaskStatus.PENDING.value,
            reward_amount=data.reward_amount,
            reward_currency=data.reward_currency,
            deadline=data.deadline,
            callback_url=data.callback_url,
        )

        self.db.add(task_db)
        await self.db.commit()
        await self.db.refresh(task_db)

        # 转换为领域模型
        return self._to_domain_model(task_db)

    async def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务详情。"""
        task_db = await self.repository.get(task_id)
        if task_db:
            return self._to_domain_model(task_db)
        return None

    async def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        interaction_type: Optional[InteractionType] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Task]:
        """列出任务。"""
        task_dbs = await self.repository.list_by_status(
            status=status,
            interaction_type=interaction_type,
            skip=skip,
            limit=limit,
        )
        return [self._to_domain_model(t) for t in task_dbs]

    async def publish_task(self, task_id: str) -> bool:
        """将 pending 任务发布到市场。"""
        task_db = await self.repository.get(task_id)
        if not task_db or task_db.status != TaskStatus.PENDING.value:
            return False

        task_db.status = TaskStatus.PUBLISHED.value
        task_db.updated_at = datetime.now()
        await self.db.commit()
        await self.db.refresh(task_db)

        return True

    async def accept_task(self, task_id: str, worker_id: str) -> bool:
        """真人接单：仅 published 可接。"""
        task_db = await self.repository.get(task_id)
        if not task_db or task_db.status != TaskStatus.PUBLISHED.value:
            return False

        task_db.status = TaskStatus.IN_PROGRESS.value
        task_db.worker_id = worker_id
        task_db.updated_at = datetime.now()
        await self.db.commit()
        await self.db.refresh(task_db)

        return True

    async def submit_work(
        self,
        task_id: str,
        worker_id: str,
        content: str,
        attachments: Optional[List[str]] = None,
    ) -> bool:
        """提交交付物；须由当前接单人提交，且任务处于进行中。"""
        task_db = await self.repository.get(task_id)
        if not task_db:
            return False
        if task_db.status != TaskStatus.IN_PROGRESS.value or task_db.worker_id != worker_id:
            return False

        task_db.delivery_content = content
        task_db.delivery_attachments = list(attachments or [])
        task_db.status = TaskStatus.REVIEW.value
        task_db.submitted_at = datetime.now()
        task_db.updated_at = datetime.now()
        task_db.submission_count += 1
        task_db.last_submitted_at = datetime.now()
        await self.db.commit()
        await self.db.refresh(task_db)

        return True

    async def complete_task(self, task_id: str, approved: bool) -> bool:
        """AI 雇主验收。"""
        task_db = await self.repository.get(task_id)
        if not task_db:
            return False
        if approved:
            task_db.status = TaskStatus.COMPLETED.value
        else:
            task_db.status = TaskStatus.IN_PROGRESS.value
        task_db.updated_at = datetime.now()
        await self.db.commit()
        await self.db.refresh(task_db)

        return True

    async def cancel_task(self, task_id: str, operator_id: str, reason: Optional[str] = None) -> bool:
        """取消任务。可由 AI 雇主或平台操作，已完成的任务不可取消。"""
        task_db = await self.repository.get(task_id)
        if not task_db or task_db.status in [TaskStatus.COMPLETED.value, TaskStatus.CANCELLED.value]:
            return False

        task_db.status = TaskStatus.CANCELLED.value
        task_db.review_reason = reason
        task_db.reviewer_id = operator_id
        task_db.updated_at = datetime.now()
        await self.db.commit()
        await self.db.refresh(task_db)

        return True

    async def start_manual_review(self, task_id: str, reviewer_id: str) -> bool:
        """将任务从 REVIEW 状态转入人工复核。"""
        task_db = await self.repository.get(task_id)
        if not task_db or task_db.status != TaskStatus.REVIEW.value:
            return False

        task_db.status = TaskStatus.MANUAL_REVIEW.value
        task_db.reviewer_id = reviewer_id
        task_db.updated_at = datetime.now()
        await self.db.commit()
        await self.db.refresh(task_db)

        return True

    async def manual_review_task(
        self,
        task_id: str,
        reviewer_id: str,
        approved: bool,
        reason: str,
        override_ai: bool = False,
    ) -> bool:
        """人工复核任务。"""
        task_db = await self.repository.get(task_id)
        if not task_db or task_db.status != TaskStatus.MANUAL_REVIEW.value:
            return False

        if approved:
            task_db.status = TaskStatus.COMPLETED.value
        else:
            task_db.status = TaskStatus.IN_PROGRESS.value
        task_db.review_reason = reason
        task_db.reviewer_id = reviewer_id
        task_db.updated_at = datetime.now()
        await self.db.commit()
        await self.db.refresh(task_db)

        return True

    async def appeal_task(
        self,
        task_id: str,
        appealer_id: str,
        appeal_reason: str,
        evidence: Optional[List[str]] = None,
    ) -> bool:
        """对验收结果提出申诉，进入争议仲裁状态。"""
        task_db = await self.repository.get(task_id)
        if not task_db or task_db.status != TaskStatus.COMPLETED.value or task_db.appeal_count >= 1:
            return False

        task_db.status = TaskStatus.DISPUTE.value
        task_db.is_disputed = True
        task_db.appeal_count += 1
        task_db.review_reason = appeal_reason
        task_db.updated_at = datetime.now()
        await self.db.commit()
        await self.db.refresh(task_db)

        return True

    async def resolve_dispute(
        self,
        task_id: str,
        reviewer_id: str,
        approved: bool,
        reason: str,
    ) -> bool:
        """平台仲裁争议。"""
        task_db = await self.repository.get(task_id)
        if not task_db or task_db.status != TaskStatus.DISPUTE.value:
            return False

        if approved:
            task_db.status = TaskStatus.COMPLETED.value
        else:
            task_db.status = TaskStatus.CANCELLED.value
        task_db.review_reason = reason
        task_db.reviewer_id = reviewer_id
        task_db.is_disputed = False
        task_db.updated_at = datetime.now()
        await self.db.commit()
        await self.db.refresh(task_db)

        return True

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
        limit: int = 100,
    ) -> List[Task]:
        """真人侧浏览可接任务，支持多维度筛选与排序。"""
        task_dbs = await self.repository.search_tasks(
            skill=skill,
            min_reward=min_reward,
            max_reward=max_reward,
            interaction_type=interaction_type,
            location=location,
            priority=priority,
            keyword=keyword,
            sort_by=sort_by,
            sort_order=sort_order,
            skip=skip,
            limit=limit,
        )
        return [self._to_domain_model(t) for t in task_dbs]

    async def get_tasks_by_worker_id(
        self,
        worker_id: str,
        status: Optional[TaskStatus] = None,
    ) -> List[Task]:
        """获取工人承接的任务。"""
        task_dbs = await self.repository.get_by_worker_id(worker_id, status)
        return [self._to_domain_model(t) for t in task_dbs]

    async def get_tasks_by_employer_id(
        self,
        employer_id: str,
        status: Optional[TaskStatus] = None,
    ) -> List[Task]:
        """获取雇主发布的任务。"""
        task_dbs = await self.repository.get_by_employer_id(employer_id, status)
        return [self._to_domain_model(t) for t in task_dbs]

    def _to_domain_model(self, task_db: TaskDB) -> Task:
        """将数据库模型转换为领域模型。"""
        return Task(
            id=task_db.id,
            ai_employer_id=task_db.ai_employer_id,
            title=task_db.title,
            description=task_db.description,
            requirements=task_db.requirements,
            interaction_type=InteractionType(task_db.interaction_type),
            capability_gap=task_db.capability_gap,
            acceptance_criteria=task_db.acceptance_criteria,
            location_hint=task_db.location_hint,
            required_skills=task_db.required_skills,
            priority=TaskPriority(task_db.priority),
            status=TaskStatus(task_db.status),
            reward_amount=task_db.reward_amount,
            reward_currency=task_db.reward_currency,
            deadline=task_db.deadline,
            worker_id=task_db.worker_id,
            delivery_content=task_db.delivery_content,
            delivery_attachments=task_db.delivery_attachments,
            submitted_at=task_db.submitted_at,
            callback_url=task_db.callback_url,
            review_reason=task_db.review_reason,
            reviewer_id=task_db.reviewer_id,
            appeal_count=task_db.appeal_count,
            is_disputed=task_db.is_disputed,
            submission_count=task_db.submission_count,
            last_submitted_at=task_db.last_submitted_at,
            delivery_content_hash=task_db.delivery_content_hash,
            cheating_flag=task_db.cheating_flag,
            cheating_reason=task_db.cheating_reason,
            created_at=task_db.created_at,
            updated_at=task_db.updated_at,
        )


# 全局任务服务实例（内存实现，向后兼容）
# 生产环境应使用 DatabaseTaskService
_task_service_instance = None


async def get_database_task_service(db_session: AsyncSession) -> DatabaseTaskService:
    """获取数据库任务服务实例。"""
    return DatabaseTaskService(db_session)
