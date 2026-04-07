"""
运营后台服务 - 提供平台运营所需的只读数据与报表功能。
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from models.task import Task, TaskStatus, TaskPriority, InteractionType
from services.task_service import task_service
from services.payment_service import payment_service


class AdminService:
    """
    运营后台服务（内存存储实现）。
    提供平台数据统计、任务管理、用户管理等功能。
    """

    def __init__(self) -> None:
        pass

    def get_platform_stats(self) -> Dict[str, Any]:
        """
        获取平台整体统计数据。
        """
        tasks = list(task_service._tasks.values())
        wallets = payment_service._wallets
        transactions = list(payment_service._transactions.values())

        # 任务统计
        task_stats = {
            'total': len(tasks),
            'by_status': {},
            'by_interaction_type': {},
            'by_priority': {},
        }
        for task in tasks:
            # 按状态统计
            status = task.status.value
            task_stats['by_status'][status] = task_stats['by_status'].get(status, 0) + 1
            # 按交互类型统计
            interaction = task.interaction_type.value
            task_stats['by_interaction_type'][interaction] = task_stats['by_interaction_type'].get(interaction, 0) + 1
            # 按优先级统计
            priority = task.priority.value
            task_stats['by_priority'][priority] = task_stats['by_priority'].get(priority, 0) + 1

        # 支付统计
        total_volume = sum(tx.amount for tx in transactions if tx.status.value == 'success')
        total_fees = sum(tx.fee_amount for tx in transactions if tx.status.value == 'success')

        # 用户统计
        user_stats = {
            'total_workers': len(set(t.worker_id for t in tasks if t.worker_id)),
            'total_employers': len(set(t.ai_employer_id for t in tasks)),
            'total_wallets': len(wallets),
        }

        # 时间统计
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=7)

        today_tasks = [t for t in tasks if t.created_at >= today_start]
        week_tasks = [t for t in tasks if t.created_at >= week_start]

        time_stats = {
            'today_new_tasks': len(today_tasks),
            'week_new_tasks': len(week_tasks),
            'today_completed': len([t for t in today_tasks if t.status == TaskStatus.COMPLETED]),
            'week_completed': len([t for t in week_tasks if t.status == TaskStatus.COMPLETED]),
        }

        return {
            'task_stats': task_stats,
            'payment_stats': {
                'total_volume': total_volume,
                'total_fees': total_fees,
            },
            'user_stats': user_stats,
            'time_stats': time_stats,
        }

    def get_task_list(
        self,
        status: Optional[TaskStatus] = None,
        interaction_type: Optional[InteractionType] = None,
        priority: Optional[TaskPriority] = None,
        keyword: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Task]:
        """
        获取任务列表（管理视角，支持更多筛选）。
        """
        tasks = list(task_service._tasks.values())
        results = []

        for task in tasks:
            # 状态筛选
            if status is not None and task.status != status:
                continue
            # 交互类型筛选
            if interaction_type is not None and task.interaction_type != interaction_type:
                continue
            # 优先级筛选
            if priority is not None and task.priority != priority:
                continue
            # 关键词搜索
            if keyword:
                kw = keyword.lower()
                full_text = " ".join([
                    task.title,
                    task.description,
                    task.capability_gap,
                    task.location_hint or "",
                    str(task.required_skills),
                ]).lower()
                if kw not in full_text:
                    continue
            results.append(task)

        # 排序：按创建时间倒序
        results.sort(key=lambda t: t.created_at, reverse=True)

        # 分页
        return results[skip:skip + limit]

    def get_task_detail(self, task_id: str) -> Optional[Task]:
        """获取任务详情（管理视角）。"""
        return task_service.get_task(task_id)

    def get_user_list(
        self,
        user_type: str = "all",  # all, worker, employer
        skip: int = 0,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        获取用户列表。
        """
        tasks = list(task_service._tasks.values())
        wallets = payment_service._wallets

        workers = set(t.worker_id for t in tasks if t.worker_id)
        employers = set(t.ai_employer_id for t in tasks)

        users = {}

        if user_type in ("all", "worker"):
            for worker_id in workers:
                users[worker_id] = {
                    'user_id': worker_id,
                    'type': 'worker',
                    'completed_tasks': len([t for t in tasks if t.worker_id == worker_id and t.status == TaskStatus.COMPLETED]),
                    'total_earnings': sum(t.reward_amount for t in tasks if t.worker_id == worker_id and t.status == TaskStatus.COMPLETED),
                }

        if user_type in ("all", "employer"):
            for employer_id in employers:
                users[employer_id] = {
                    'user_id': employer_id,
                    'type': 'employer',
                    'published_tasks': len([t for t in tasks if t.ai_employer_id == employer_id]),
                    'completed_tasks': len([t for t in tasks if t.ai_employer_id == employer_id and t.status == TaskStatus.COMPLETED]),
                    'total_spent': sum(t.reward_amount for t in tasks if t.ai_employer_id == employer_id and t.status == TaskStatus.COMPLETED),
                }

        # 合并同一用户的数据
        for user_id, user_data in users.items():
            if user_id in wallets:
                user_data['wallet_balance'] = wallets[user_id].balance
            else:
                user_data['wallet_balance'] = 0.0

        # 转换列表并分页
        user_list = list(users.values())
        user_list.sort(key=lambda u: u.get('wallet_balance', 0), reverse=True)

        return user_list[skip:skip + limit]

    def get_transaction_list(
        self,
        transaction_type: Optional[str] = None,
        user_id: Optional[str] = None,
        task_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        获取交易记录列表。
        """
        transactions = list(payment_service._transactions.values())
        results = []

        for tx in transactions:
            # 类型筛选
            if transaction_type and tx.transaction_type.value != transaction_type:
                continue
            # 用户筛选
            if user_id and tx.payer_id != user_id and tx.payee_id != user_id:
                continue
            # 任务筛选
            if task_id and tx.task_id != task_id:
                continue
            results.append(tx)

        # 排序：按创建时间倒序
        results.sort(key=lambda t: t.created_at, reverse=True)

        # 分页
        return results[skip:skip + limit]

    def get_cheating_reports(self) -> List[Dict[str, Any]]:
        """
        获取作弊报告列表。
        """
        tasks = list(task_service._tasks.values())
        cheating_tasks = [t for t in tasks if t.cheating_flag]

        reports = []
        for task in cheating_tasks:
            reports.append({
                'task_id': task.id,
                'worker_id': task.worker_id,
                'ai_employer_id': task.ai_employer_id,
                'reason': task.cheating_reason,
                'title': task.title,
                'status': task.status.value,
                'created_at': task.created_at.isoformat(),
                'marked_at': task.updated_at.isoformat() if task.updated_at else None,
            })

        return reports


admin_service = AdminService()
