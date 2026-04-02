"""
任务服务 — AI 发布、真人接单、交付与验收闭环。
"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from models.task import (
    InteractionType,
    Task,
    TaskCreate,
    TaskStatus,
)


class TaskService:
    """内存存储；生产环境可换为 PostgreSQL + 队列。"""

    def __init__(self) -> None:
        self._tasks: Dict[str, Task] = {}

    def create_task(self, data: TaskCreate) -> Task:
        """AI / Agent 因能力缺口发布任务。"""
        payload = data.model_dump(exclude={"publish_immediately"})
        status = TaskStatus.PUBLISHED if data.publish_immediately else TaskStatus.PENDING
        task = Task(**payload, status=status)
        self._tasks[task.id] = task
        return task

    def publish_task(self, task_id: str) -> bool:
        """将 pending 任务发布到市场。"""
        task = self._tasks.get(task_id)
        if not task or task.status != TaskStatus.PENDING:
            return False
        task.status = TaskStatus.PUBLISHED
        task.updated_at = datetime.now()
        return True

    def get_task(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)

    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        interaction_type: Optional[InteractionType] = None,
    ) -> List[Task]:
        rows = list(self._tasks.values())
        if status is not None:
            rows = [t for t in rows if t.status == status]
        if interaction_type is not None:
            rows = [t for t in rows if t.interaction_type == interaction_type]
        return rows

    def accept_task(self, task_id: str, worker_id: str) -> bool:
        """真人接单：仅 published 可接。"""
        task = self._tasks.get(task_id)
        if not task or task.status != TaskStatus.PUBLISHED:
            return False
        task.status = TaskStatus.IN_PROGRESS
        task.worker_id = worker_id
        task.updated_at = datetime.now()
        return True

    def submit_work(
        self,
        task_id: str,
        worker_id: str,
        content: str,
        attachments: Optional[List[str]] = None,
    ) -> bool:
        """提交交付物；须由当前接单人提交，且任务处于进行中。"""
        task = self._tasks.get(task_id)
        if not task:
            return False
        if task.status != TaskStatus.IN_PROGRESS or task.worker_id != worker_id:
            return False
        task.delivery_content = content
        task.delivery_attachments = list(attachments or [])
        task.status = TaskStatus.REVIEW
        task.submitted_at = datetime.now()
        task.updated_at = datetime.now()
        return True

    def complete_task(self, task_id: str, approved: bool) -> bool:
        """AI 雇主验收。"""
        task = self._tasks.get(task_id)
        if not task:
            return False
        if approved:
            task.status = TaskStatus.COMPLETED
        else:
            task.status = TaskStatus.IN_PROGRESS
        task.updated_at = datetime.now()
        return True

    def cancel_task(self, task_id: str, operator_id: str, reason: Optional[str] = None) -> bool:
        """取消任务。可由AI雇主或平台操作，已完成的任务不可取消。"""
        task = self._tasks.get(task_id)
        if not task or task.status in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]:
            return False
        task.status = TaskStatus.CANCELLED
        task.review_reason = reason
        task.reviewer_id = operator_id
        task.updated_at = datetime.now()
        return True

    def start_manual_review(self, task_id: str, reviewer_id: str) -> bool:
        """将任务从REVIEW状态转入人工复核。"""
        task = self._tasks.get(task_id)
        if not task or task.status != TaskStatus.REVIEW:
            return False
        task.status = TaskStatus.MANUAL_REVIEW
        task.reviewer_id = reviewer_id
        task.updated_at = datetime.now()
        return True

    def manual_review_task(self, task_id: str, reviewer_id: str, approved: bool, reason: str, override_ai: bool = False) -> bool:
        """人工复核任务。"""
        task = self._tasks.get(task_id)
        if not task or task.status != TaskStatus.MANUAL_REVIEW:
            return False
        if approved:
            task.status = TaskStatus.COMPLETED
        else:
            task.status = TaskStatus.IN_PROGRESS
        task.review_reason = reason
        task.reviewer_id = reviewer_id
        task.updated_at = datetime.now()
        return True

    def appeal_task(self, task_id: str, appealer_id: str, appeal_reason: str, evidence: Optional[List[str]] = None) -> bool:
        """对验收结果提出申诉，进入争议仲裁状态。"""
        task = self._tasks.get(task_id)
        if not task or task.status != TaskStatus.COMPLETED or task.appeal_count >= 1:
            return False
        task.status = TaskStatus.DISPUTE
        task.is_disputed = True
        task.appeal_count += 1
        task.review_reason = appeal_reason
        task.updated_at = datetime.now()
        return True

    def resolve_dispute(self, task_id: str, reviewer_id: str, approved: bool, reason: str) -> bool:
        """平台仲裁争议。"""
        task = self._tasks.get(task_id)
        if not task or task.status != TaskStatus.DISPUTE:
            return False
        if approved:
            task.status = TaskStatus.COMPLETED
        else:
            task.status = TaskStatus.CANCELLED
        task.review_reason = reason
        task.reviewer_id = reviewer_id
        task.is_disputed = False
        task.updated_at = datetime.now()
        return True

    def search_tasks(
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
    ) -> List[Task]:
        """真人侧浏览可接任务，支持多维度筛选与排序。"""
        results: List[Task] = []
        for task in self._tasks.values():
            if task.status != TaskStatus.PUBLISHED:
                continue

            # 交互类型筛选
            if interaction_type is not None and task.interaction_type != interaction_type:
                continue

            # 优先级筛选
            if priority is not None and task.priority != priority:
                continue

            # 地点筛选（模糊匹配）
            if location and task.location_hint:
                if location.lower() not in task.location_hint.lower():
                    continue

            # 技能匹配
            if skill:
                sk = skill.lower()
                skills_flat = [
                    *(str(v).lower() for v in task.required_skills.values()),
                    *(str(k).lower() for k in task.required_skills.keys()),
                ]
                text_haystack = " ".join(
                    [task.title, task.description, *task.requirements]
                ).lower()
                skill_ok = any(sk in s or s in sk for s in skills_flat) if skills_flat else False
                if not skill_ok and sk not in text_haystack:
                    continue

            # 关键词搜索（标题、描述、需求全文匹配）
            if keyword:
                kw = keyword.lower()
                full_text = " ".join([
                    task.title,
                    task.description,
                    *task.requirements,
                    task.capability_gap,
                    task.location_hint or ""
                ]).lower()
                if kw not in full_text:
                    continue

            # 报酬范围筛选
            if task.reward_amount < min_reward:
                continue
            if max_reward is not None and task.reward_amount > max_reward:
                continue

            results.append(task)

        # 排序
        sort_key_map = {
            "created_at": lambda t: t.created_at,
            "reward": lambda t: t.reward_amount,
            "priority": lambda t: t.priority,
            "deadline": lambda t: t.deadline or datetime.max,
        }
        key_func = sort_key_map.get(sort_by, lambda t: t.created_at)
        reverse = sort_order.lower() == "desc"
        results.sort(key=key_func, reverse=reverse)

        return results


task_service = TaskService()
