"""
报表服务 - 提供平台各类报表数据生成。
"""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from models.task import Task, TaskStatus, TaskPriority, InteractionType
from services.task_service import task_service
from services.payment_service import payment_service


class ReportService:
    """
    报表服务（内存存储实现）。
    提供任务完成情况、工人绩效、支付流水等报表功能。
    """

    def __init__(self) -> None:
        pass

    def get_task_completion_report(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        group_by: str = "day",  # day, week, month, status, priority, interaction_type
    ) -> List[Dict[str, Any]]:
        """
        任务完成情况报表。

        支持按时间（日/周/月）、状态、优先级、交互类型分组。
        """
        tasks = list(task_service._tasks.values())

        # 时间筛选
        if start_date:
            tasks = [t for t in tasks if t.created_at >= start_date]
        if end_date:
            tasks = [t for t in tasks if t.created_at <= end_date]

        reports = []

        if group_by == "day":
            # 按天分组
            grouped = {}
            for task in tasks:
                date_key = task.created_at.strftime("%Y-%m-%d")
                if date_key not in grouped:
                    grouped[date_key] = []
                grouped[date_key].append(task)

            for date_key, day_tasks in sorted(grouped.items()):
                reports.append({
                    'period': date_key,
                    'total': len(day_tasks),
                    'completed': len([t for t in day_tasks if t.status == TaskStatus.COMPLETED]),
                    'in_progress': len([t for t in day_tasks if t.status == TaskStatus.IN_PROGRESS]),
                    'cancelled': len([t for t in day_tasks if t.status == TaskStatus.CANCELLED]),
                    'pending_review': len([t for t in day_tasks if t.status == TaskStatus.REVIEW]),
                    'total_reward': sum(t.reward_amount for t in day_tasks),
                })

        elif group_by == "week":
            # 按周分组
            grouped = {}
            for task in tasks:
                # ISO 周：YYYY-Www
                week_key = task.created_at.strftime("%Y-W%W")
                if week_key not in grouped:
                    grouped[week_key] = []
                grouped[week_key].append(task)

            for week_key, week_tasks in sorted(grouped.items()):
                reports.append({
                    'period': week_key,
                    'total': len(week_tasks),
                    'completed': len([t for t in week_tasks if t.status == TaskStatus.COMPLETED]),
                    'in_progress': len([t for t in week_tasks if t.status == TaskStatus.IN_PROGRESS]),
                    'cancelled': len([t for t in week_tasks if t.status == TaskStatus.CANCELLED]),
                    'total_reward': sum(t.reward_amount for t in week_tasks),
                })

        elif group_by == "month":
            # 按月分组
            grouped = {}
            for task in tasks:
                month_key = task.created_at.strftime("%Y-%m")
                if month_key not in grouped:
                    grouped[month_key] = []
                grouped[month_key].append(task)

            for month_key, month_tasks in sorted(grouped.items()):
                reports.append({
                    'period': month_key,
                    'total': len(month_tasks),
                    'completed': len([t for t in month_tasks if t.status == TaskStatus.COMPLETED]),
                    'in_progress': len([t for t in month_tasks if t.status == TaskStatus.IN_PROGRESS]),
                    'cancelled': len([t for t in month_tasks if t.status == TaskStatus.CANCELLED]),
                    'total_reward': sum(t.reward_amount for t in month_tasks),
                })

        elif group_by == "status":
            # 按状态分组
            grouped = {}
            for task in tasks:
                status = task.status.value
                if status not in grouped:
                    grouped[status] = []
                grouped[status].append(task)

            for status, status_tasks in sorted(grouped.items()):
                reports.append({
                    'status': status,
                    'count': len(status_tasks),
                    'total_reward': sum(t.reward_amount for t in status_tasks),
                    'interaction_types': {
                        it.value: len([t for t in status_tasks if t.interaction_type == it])
                        for it in InteractionType
                    },
                })

        elif group_by == "priority":
            # 按优先级分组
            grouped = {}
            for task in tasks:
                priority = task.priority.value
                if priority not in grouped:
                    grouped[priority] = []
                grouped[priority].append(task)

            for priority, priority_tasks in sorted(grouped.items()):
                reports.append({
                    'priority': priority,
                    'count': len(priority_tasks),
                    'completed': len([t for t in priority_tasks if t.status == TaskStatus.COMPLETED]),
                    'completion_rate': len([t for t in priority_tasks if t.status == TaskStatus.COMPLETED]) / len(priority_tasks) if priority_tasks else 0,
                    'avg_reward': sum(t.reward_amount for t in priority_tasks) / len(priority_tasks) if priority_tasks else 0,
                })

        elif group_by == "interaction_type":
            # 按交互类型分组
            grouped = {}
            for task in tasks:
                itype = task.interaction_type.value
                if itype not in grouped:
                    grouped[itype] = []
                grouped[itype].append(task)

            for itype, itype_tasks in sorted(grouped.items()):
                reports.append({
                    'interaction_type': itype,
                    'count': len(itype_tasks),
                    'completed': len([t for t in itype_tasks if t.status == TaskStatus.COMPLETED]),
                    'completion_rate': len([t for t in itype_tasks if t.status == TaskStatus.COMPLETED]) / len(itype_tasks) if itype_tasks else 0,
                    'avg_reward': sum(t.reward_amount for t in itype_tasks) / len(itype_tasks) if itype_tasks else 0,
                })

        return reports

    def get_worker_performance_report(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        min_tasks: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        工人绩效报表。

        包含每个工人的任务完成情况、收入、评分等。
        """
        tasks = list(task_service._tasks.values())

        # 时间筛选
        if start_date:
            tasks = [t for t in tasks if t.created_at >= start_date]
        if end_date:
            tasks = [t for t in tasks if t.created_at <= end_date]

        # 按工人分组
        worker_stats = {}
        for task in tasks:
            if not task.worker_id:
                continue

            worker_id = task.worker_id
            if worker_id not in worker_stats:
                worker_stats[worker_id] = {
                    'worker_id': worker_id,
                    'total_tasks': 0,
                    'completed_tasks': 0,
                    'cancelled_tasks': 0,
                    'total_earnings': 0.0,
                    'avg_rating': 0.0,
                    'ratings_count': 0,
                }

            stats = worker_stats[worker_id]
            stats['total_tasks'] += 1

            if task.status == TaskStatus.COMPLETED:
                stats['completed_tasks'] += 1
                stats['total_earnings'] += task.reward_amount
            elif task.status == TaskStatus.CANCELLED:
                stats['cancelled_tasks'] += 1

        # 过滤并计算成功率
        results = []
        for worker_id, stats in worker_stats.items():
            if stats['total_tasks'] < min_tasks:
                continue

            stats['success_rate'] = (
                stats['completed_tasks'] / stats['total_tasks']
                if stats['total_tasks'] > 0 else 0.0
            )
            results.append(stats)

        # 按成功率和完成任务数排序
        results.sort(key=lambda x: (x['success_rate'], x['completed_tasks']), reverse=True)

        return results

    def get_payment_flow_report(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        transaction_type: Optional[str] = None,
        group_by: str = "day",
    ) -> List[Dict[str, Any]]:
        """
        支付流水报表。
        """
        transactions = list(payment_service._transactions.values())

        # 时间筛选
        if start_date:
            transactions = [tx for tx in transactions if tx.created_at >= start_date]
        if end_date:
            transactions = [tx for tx in transactions if tx.created_at <= end_date]

        # 类型筛选
        if transaction_type:
            transactions = [tx for tx in transactions if tx.transaction_type.value == transaction_type]

        # 按时间分组
        reports = []

        if group_by == "day":
            grouped = {}
            for tx in transactions:
                date_key = tx.created_at.strftime("%Y-%m-%d")
                if date_key not in grouped:
                    grouped[date_key] = []
                grouped[date_key].append(tx)

            for date_key, day_txs in sorted(grouped.items()):
                reports.append({
                    'period': date_key,
                    'total_transactions': len(day_txs),
                    'total_amount': sum(tx.amount for tx in day_txs),
                    'total_fees': sum(tx.fee_amount for tx in day_txs),
                    'by_type': {
                        tt.value: sum(tx.amount for tx in day_txs if tx.transaction_type.value == tt)
                        for tt in set(tx.transaction_type for tx in day_txs)
                    },
                })

        elif group_by == "type":
            # 按交易类型分组
            grouped = {}
            for tx in transactions:
                tt = tx.transaction_type.value
                if tt not in grouped:
                    grouped[tt] = []
                grouped[tt].append(tx)

            for tt, tt_txs in sorted(grouped.items()):
                reports.append({
                    'transaction_type': tt,
                    'count': len(tt_txs),
                    'total_amount': sum(tx.amount for tx in tt_txs),
                    'total_fees': sum(tx.fee_amount for tx in tt_txs),
                    'success_count': len([tx for tx in tt_txs if tx.status.value == 'success']),
                })

        return reports

    def export_to_csv(self, data: List[Dict[str, Any]]) -> str:
        """
        将数据导出为 CSV 格式字符串。
        """
        if not data:
            return ""

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)

        return output.getvalue()

    def export_to_json(self, data: List[Dict[str, Any]], pretty: bool = True) -> str:
        """
        将数据导出为 JSON 格式字符串。
        """
        if pretty:
            return json.dumps(data, indent=2, ensure_ascii=False, default=str)
        return json.dumps(data, ensure_ascii=False, default=str)


report_service = ReportService()
