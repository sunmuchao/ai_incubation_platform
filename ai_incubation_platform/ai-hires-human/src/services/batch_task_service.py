"""
批量任务管理服务。
"""
from __future__ import annotations

import csv
import io
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from fastapi import BackgroundTasks

from models.task import InteractionType, Task, TaskCreate, TaskPriority, TaskStatus
from services.task_service import task_service
from services.callback_service import notify_task_completed_by_id

logger = logging.getLogger(__name__)


class BatchTaskService:
    """
    批量任务管理服务，提供以下功能：
    1. CSV 批量导入任务
    2. 批量创建任务（支持模板）
    3. 批量接单
    4. 批量提交工作
    5. 批量验收任务
    6. 任务模板管理
    """

    def __init__(self) -> None:
        # 批量任务追踪：batch_id -> {task_ids, created_at, ...}
        self._batches: Dict[str, Dict[str, Any]] = {}
        # 任务模板：template_name -> template_data
        self._templates: Dict[str, Dict[str, Any]] = {}

    def import_tasks_from_csv(
        self,
        csv_content: str,
        ai_employer_id: str,
        default_interaction_type: InteractionType = InteractionType.DIGITAL,
        default_priority: TaskPriority = TaskPriority.MEDIUM,
    ) -> Dict[str, Any]:
        """
        从 CSV 内容批量导入任务。

        返回：
        {
            "total": int,
            "success_count": int,
            "failed_count": int,
            "task_ids": List[str],
            "errors": List[Dict]
        }
        """
        task_ids = []
        errors = []
        success_count = 0

        reader = csv.DictReader(io.StringIO(csv_content))

        for row_num, row in enumerate(reader, start=2):  # 从 2 开始，第 1 行是 header
            try:
                # 必填字段检查
                title = (row.get('title') or '').strip()
                description = (row.get('description') or '').strip()
                capability_gap = (row.get('capability_gap') or '').strip()

                if not title or not description or not capability_gap:
                    errors.append({
                        "row": row_num,
                        "error": "Missing required fields: title, description, capability_gap"
                    })
                    continue

                # 解析验收标准（支持 JSON 数组或分号分隔）
                acceptance_criteria_str = row.get('acceptance_criteria') or '[]'
                if acceptance_criteria_str.startswith('['):
                    acceptance_criteria = json.loads(acceptance_criteria_str)
                else:
                    acceptance_criteria = [s.strip() for s in acceptance_criteria_str.split(';') if s.strip()]

                # 解析任务要求
                requirements_str = row.get('requirements') or '[]'
                if requirements_str.startswith('['):
                    requirements = json.loads(requirements_str)
                else:
                    requirements = [s.strip() for s in requirements_str.split(';') if s.strip()]

                # 解析所需技能（支持 JSON 对象或 key=value 格式）
                required_skills_str = row.get('required_skills') or '{}'
                if required_skills_str.startswith('{'):
                    required_skills = json.loads(required_skills_str)
                else:
                    required_skills = {}
                    for item in required_skills_str.split(';'):
                        if '=' in item:
                            key, value = item.split('=', 1)
                            required_skills[key.strip()] = value.strip()

                # 解析截止时间
                deadline_str = (row.get('deadline') or '').strip()
                deadline = None
                if deadline_str:
                    try:
                        deadline = datetime.fromisoformat(deadline_str.replace('Z', '+00:00'))
                    except ValueError:
                        logger.warning("Invalid deadline format at row %d: %s", row_num, deadline_str)

                # 解析报酬
                reward_amount = 0.0
                reward_str = (row.get('reward_amount') or '0').strip()
                if reward_str:
                    try:
                        reward_amount = float(reward_str)
                    except ValueError:
                        logger.warning("Invalid reward_amount at row %d: %s", row_num, reward_str)

                # 创建任务
                task_create = TaskCreate(
                    ai_employer_id=ai_employer_id,
                    title=title,
                    description=description,
                    capability_gap=capability_gap,
                    acceptance_criteria=acceptance_criteria,
                    requirements=requirements,
                    required_skills=required_skills,
                    location_hint=(row.get('location_hint') or '').strip() or None,
                    interaction_type=InteractionType(row.get('interaction_type', default_interaction_type.value)),
                    priority=TaskPriority(row.get('priority', default_priority.value)),
                    reward_amount=reward_amount,
                    deadline=deadline,
                    callback_url=(row.get('callback_url') or '').strip() or None,
                    publish_immediately=True,
                )

                task = task_service.create_task(task_create)
                task_ids.append(task.id)
                success_count += 1

            except Exception as e:
                errors.append({
                    "row": row_num,
                    "error": str(e),
                    "data": row
                })
                logger.exception("Failed to import task at row %d", row_num)

        # 创建批量记录
        batch_id = str(uuid.uuid4())
        self._batches[batch_id] = {
            "batch_id": batch_id,
            "task_ids": task_ids,
            "total": len(list(reader)) + success_count + len(errors),
            "success_count": success_count,
            "failed_count": len(errors),
            "created_at": datetime.now(),
            "errors": errors,
        }

        return {
            "total": success_count + len(errors),
            "success_count": success_count,
            "failed_count": len(errors),
            "task_ids": task_ids,
            "errors": errors,
            "batch_id": batch_id,
        }

    def create_task_batch(
        self,
        tasks: List[TaskCreate],
        template_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """批量创建任务。"""
        task_ids = []
        errors = []

        for i, task_create in enumerate(tasks):
            try:
                task = task_service.create_task(task_create)
                task_ids.append(task.id)
            except Exception as e:
                errors.append({
                    "index": i,
                    "error": str(e),
                    "task_title": task_create.title,
                })
                logger.exception("Failed to create task at index %d", i)

        # 创建批量记录
        batch_id = str(uuid.uuid4())
        self._batches[batch_id] = {
            "batch_id": batch_id,
            "task_ids": task_ids,
            "total": len(tasks),
            "success_count": len(task_ids),
            "failed_count": len(errors),
            "template_name": template_name,
            "created_at": datetime.now(),
            "errors": errors,
        }

        return {
            "total": len(tasks),
            "success_count": len(task_ids),
            "failed_count": len(errors),
            "task_ids": task_ids,
            "errors": errors,
            "batch_id": batch_id,
        }

    def get_batch_status(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """获取批量任务状态。"""
        batch = self._batches.get(batch_id)
        if not batch:
            return None

        # 统计各状态的任务数量
        status_counts: Dict[str, int] = {}
        completed_at = None

        for task_id in batch["task_ids"]:
            task = task_service.get_task(task_id)
            if task:
                status = task.status.value
                status_counts[status] = status_counts.get(status, 0) + 1
                if task.status == TaskStatus.COMPLETED:
                    completed_at = task.updated_at

        return {
            "batch_id": batch_id,
            "total_tasks": batch["total"],
            "status_counts": status_counts,
            "created_at": batch["created_at"],
            "completed_at": completed_at,
        }

    def batch_accept_tasks(
        self,
        worker_id: str,
        task_ids: List[str],
    ) -> List[Dict[str, Any]]:
        """批量接单。"""
        results = []
        for task_id in task_ids:
            try:
                ok = task_service.accept_task(task_id, worker_id)
                results.append({
                    "task_id": task_id,
                    "success": ok,
                    "message": "Task accepted" if ok else "Failed to accept",
                })
            except Exception as e:
                results.append({
                    "task_id": task_id,
                    "success": False,
                    "error": str(e),
                })
        return results

    def submit_work(
        self,
        task_id: str,
        worker_id: str,
        content: str,
        attachments: List[str],
    ) -> bool:
        """提交工作（代理到 task_service）。"""
        from services.anti_cheat_service import anti_cheat_service

        # 反作弊检测
        freq_ok, freq_reason = anti_cheat_service.check_submission_frequency(worker_id)
        if not freq_ok:
            raise Exception(f"Submission rejected: {freq_reason}")

        dup_ok, dup_reason = anti_cheat_service.check_duplicate_delivery(
            task_id, content, attachments, worker_id
        )
        if not dup_ok:
            raise Exception(f"Submission rejected: {dup_reason}")

        ok = task_service.submit_work(task_id, worker_id, content, attachments)
        if ok:
            task = task_service.get_task(task_id)
            if task:
                content_hash = anti_cheat_service.record_submission(
                    task_id, worker_id, content, attachments
                )
                task.delivery_content_hash = content_hash
                task.submission_count += 1
                task.last_submitted_at = task.submitted_at
                task.updated_at = datetime.now()
        return ok

    def batch_complete_tasks(
        self,
        ai_employer_id: str,
        task_ids: List[str],
        approved: bool,
        background_tasks: BackgroundTasks,
    ) -> List[Dict[str, Any]]:
        """批量验收任务。"""
        results = []
        for task_id in task_ids:
            try:
                task = task_service.get_task(task_id)
                if not task or task.ai_employer_id != ai_employer_id:
                    results.append({
                        "task_id": task_id,
                        "success": False,
                        "error": "Task not found or no permission",
                    })
                    continue

                if task.status != TaskStatus.REVIEW:
                    results.append({
                        "task_id": task_id,
                        "success": False,
                        "error": f"Task not awaiting review (status: {task.status.value})",
                    })
                    continue

                task_service.complete_task(task_id, approved)

                # 如果验收通过且有回调 URL，触发回调
                if approved:
                    task = task_service.get_task(task_id)
                    if task and task.callback_url:
                        background_tasks.add_task(notify_task_completed_by_id, task_id)

                results.append({
                    "task_id": task_id,
                    "success": True,
                    "approved": approved,
                })
            except Exception as e:
                results.append({
                    "task_id": task_id,
                    "success": False,
                    "error": str(e),
                })
                logger.exception("Failed to complete task %s", task_id)

        return results

    def list_task_templates(self) -> List[Dict[str, Any]]:
        """获取任务模板列表。"""
        return [
            {
                "name": name,
                "title_template": data["title_template"],
                "description_template": data["description_template"],
                "capability_gap": data["capability_gap"],
                "interaction_type": data["interaction_type"],
                "priority": data["priority"],
                "reward_amount": data["reward_amount"],
                "created_at": data.get("created_at"),
            }
            for name, data in self._templates.items()
        ]

    def create_task_template(
        self,
        name: str,
        title_template: str,
        description_template: str,
        capability_gap: str,
        interaction_type: InteractionType,
        priority: TaskPriority,
        reward_amount: float,
        acceptance_criteria: List[str],
        requirements: List[str],
        required_skills: Dict[str, Any],
    ) -> Dict[str, Any]:
        """创建任务模板。"""
        template_data = {
            "name": name,
            "title_template": title_template,
            "description_template": description_template,
            "capability_gap": capability_gap,
            "interaction_type": interaction_type.value,
            "priority": priority.value,
            "reward_amount": reward_amount,
            "acceptance_criteria": acceptance_criteria,
            "requirements": requirements,
            "required_skills": required_skills,
            "created_at": datetime.now(),
        }
        self._templates[name] = template_data

        return {"message": "Template created", "name": name}

    def delete_task_template(self, template_name: str) -> bool:
        """删除任务模板。"""
        if template_name in self._templates:
            del self._templates[template_name]
            return True
        return False

    def create_tasks_from_template(
        self,
        template_name: str,
        ai_employer_id: str,
        variables_list: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        从模板批量创建任务。

        variables_list 是变量字典列表，每个字典的键值将替换模板中的 {{key}} 占位符。
        """
        template = self._templates.get(template_name)
        if not template:
            raise ValueError(f"Template '{template_name}' not found")

        tasks = []
        for variables in variables_list:
            # 变量替换
            title = self._replace_variables(template["title_template"], variables)
            description = self._replace_variables(template["description_template"], variables)
            capability_gap = self._replace_variables(template["capability_gap"], variables)

            task_create = TaskCreate(
                ai_employer_id=ai_employer_id,
                title=title,
                description=description,
                capability_gap=capability_gap,
                acceptance_criteria=template["acceptance_criteria"],
                requirements=template["requirements"],
                required_skills=template["required_skills"],
                interaction_type=InteractionType(template["interaction_type"]),
                priority=TaskPriority(template["priority"]),
                reward_amount=template["reward_amount"],
                publish_immediately=True,
            )
            tasks.append(task_create)

        return self.create_task_batch(tasks, template_name=template_name)

    def _replace_variables(self, template: str, variables: Dict[str, Any]) -> str:
        """替换模板中的变量。"""
        result = template
        for key, value in variables.items():
            result = result.replace(f"{{{{{key}}}}}", str(value))
        return result


batch_task_service = BatchTaskService()
