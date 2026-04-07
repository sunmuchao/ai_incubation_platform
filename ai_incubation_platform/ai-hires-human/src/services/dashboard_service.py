"""
实时数据仪表板 - 数据聚合服务。

负责聚合各业务模块数据，提供实时指标计算。
"""
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from sqlalchemy import func, select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from models.db_models import (
    TaskDB, PaymentTransactionDB, WalletDB,
    WorkerProfileDB, EscrowTransactionDB,
    WorkerSubmissionDB, BehavioralEventDB
)
from models.dashboard import DashboardSnapshotDB


class DashboardService:
    """仪表板数据服务。"""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    # ==================== 总览数据 ====================

    async def get_overview_metrics(
        self,
        time_range: str = "realtime",
        organization_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取总览指标数据。

        Args:
            time_range: 时间范围 (realtime/hourly/daily/weekly/monthly)
            organization_id: 组织 ID（用于团队权限过滤）

        Returns:
            总览指标字典
        """
        # 计算时间范围
        start_time, end_time = self._get_time_range(time_range)

        # 并行获取各类指标
        task_metrics = await self._get_task_overview(start_time, end_time, organization_id)
        worker_metrics = await self._get_worker_overview(start_time, end_time, organization_id)
        quality_metrics = await self._get_quality_overview(start_time, end_time, organization_id)
        financial_metrics = await self._get_financial_overview(start_time, end_time, organization_id)

        return {
            "time_range": time_range,
            "start_time": start_time.isoformat() if start_time else None,
            "end_time": end_time.isoformat(),
            "generated_at": datetime.now().isoformat(),
            **task_metrics,
            **worker_metrics,
            **quality_metrics,
            **financial_metrics,
        }

    async def _get_task_overview(
        self,
        start_time: Optional[datetime],
        end_time: datetime,
        organization_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取任务相关指标。"""
        # 基础查询条件
        base_query = select(TaskDB)
        if start_time:
            base_query = base_query.where(TaskDB.submitted_at >= start_time)

        # 任务总数
        total_count_query = select(func.count(TaskDB.id))
        if start_time:
            total_count_query = total_count_query.where(TaskDB.submitted_at >= start_time)
        total_result = await self.db.execute(total_count_query)
        total_tasks = total_result.scalar() or 0

        # 各状态任务数
        status_query = select(
            TaskDB.status,
            func.count(TaskDB.id).label('count')
        ).group_by(TaskDB.status)
        if start_time:
            status_query = status_query.where(TaskDB.submitted_at >= start_time)
        status_result = await self.db.execute(status_query)
        status_counts = {row.status: row.count for row in status_result.fetchall()}

        # 任务完成率
        completed_count = status_counts.get('completed', 0)
        completion_rate = (completed_count / total_tasks * 100) if total_tasks > 0 else 0.0

        # 平均完成时间（小时）
        avg_completion_time_query = select(
            func.avg(
                func.extract('epoch', TaskDB.submitted_at) -
                func.extract('epoch', TaskDB.created_at)
            ) / 3600  # 转换为小时
        ).where(
            TaskDB.status == 'completed',
            TaskDB.submitted_at.isnot(None)
        )
        if start_time:
            avg_completion_time_query = avg_completion_time_query.where(TaskDB.submitted_at >= start_time)
        avg_time_result = await self.db.execute(avg_completion_time_query)
        avg_completion_hours = avg_time_result.scalar() or 0.0

        return {
            "total_tasks": total_tasks,
            "tasks_by_status": status_counts,
            "task_completion_rate": round(completion_rate, 2),
            "avg_completion_time_hours": round(avg_completion_hours, 2),
        }

    async def _get_worker_overview(
        self,
        start_time: Optional[datetime],
        end_time: datetime,
        organization_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取工人相关指标。"""
        # 活跃工人数（最近有提交记录的）
        active_workers_query = select(
            func.count(func.distinct(WorkerSubmissionDB.worker_id))
        ).where(
            WorkerSubmissionDB.submitted_at >= start_time
        ) if start_time else select(func.count(func.distinct(WorkerSubmissionDB.worker_id)))

        active_result = await self.db.execute(active_workers_query)
        active_workers = active_result.scalar() or 0

        # 总工人数
        total_workers_query = select(func.count(WorkerProfileDB.worker_id))
        total_result = await self.db.execute(total_workers_query)
        total_workers = total_result.scalar() or 0

        # 工人平均完成任务数
        avg_tasks_query = select(
            func.avg(WorkerProfileDB.completed_tasks)
        )
        avg_result = await self.db.execute(avg_tasks_query)
        avg_tasks_per_worker = avg_result.scalar() or 0.0

        # 工人平均评分
        avg_rating_query = select(
            func.avg(WorkerProfileDB.average_rating)
        )
        rating_result = await self.db.execute(avg_rating_query)
        avg_worker_rating = rating_result.scalar() or 0.0

        return {
            "active_workers": active_workers,
            "total_workers": total_workers,
            "avg_tasks_per_worker": round(avg_tasks_per_worker, 2),
            "avg_worker_rating": round(avg_worker_rating, 2),
        }

    async def _get_quality_overview(
        self,
        start_time: Optional[datetime],
        end_time: datetime,
        organization_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取质量相关指标。"""
        # 验收通过率
        total_submitted_query = select(func.count(TaskDB.id)).where(
            TaskDB.status.in_(['completed', 'rejected', 'manual_review'])
        )
        if start_time:
            total_submitted_query = total_submitted_query.where(TaskDB.submitted_at >= start_time)
        total_result = await self.db.execute(total_submitted_query)
        total_submitted = total_result.scalar() or 0

        approved_query = select(func.count(TaskDB.id)).where(
            TaskDB.status == 'completed'
        )
        if start_time:
            approved_query = approved_query.where(TaskDB.submitted_at >= start_time)
        approved_result = await self.db.execute(approved_query)
        approved_count = approved_result.scalar() or 0

        approval_rate = (approved_count / total_submitted * 100) if total_submitted > 0 else 0.0

        # 争议率
        disputed_query = select(func.count(TaskDB.id)).where(
            TaskDB.is_disputed == True
        )
        if start_time:
            disputed_query = disputed_query.where(TaskDB.submitted_at >= start_time)
        disputed_result = await self.db.execute(disputed_query)
        disputed_count = disputed_result.scalar() or 0

        dispute_rate = (disputed_count / total_submitted * 100) if total_submitted > 0 else 0.0

        # 作弊检测率
        cheating_query = select(func.count(TaskDB.id)).where(
            TaskDB.cheating_flag == True
        )
        if start_time:
            cheating_query = cheating_query.where(TaskDB.submitted_at >= start_time)
        cheating_result = await self.db.execute(cheating_query)
        cheating_count = cheating_result.scalar() or 0

        cheating_rate = (cheating_count / total_submitted * 100) if total_submitted > 0 else 0.0

        # 需要人工审核的任务数
        manual_review_query = select(func.count(TaskDB.id)).where(
            TaskDB.status == 'manual_review'
        )
        manual_result = await self.db.execute(manual_review_query)
        manual_review_count = manual_result.scalar() or 0

        return {
            "approval_rate": round(approval_rate, 2),
            "dispute_rate": round(dispute_rate, 2),
            "cheating_rate": round(cheating_rate, 2),
            "pending_manual_review": manual_review_count,
        }

    async def _get_financial_overview(
        self,
        start_time: Optional[datetime],
        end_time: datetime,
        organization_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取财务相关指标。"""
        # GMV（已完成交易的总额）
        gmv_query = select(func.sum(PaymentTransactionDB.amount)).where(
            PaymentTransactionDB.status == 'completed',
            PaymentTransactionDB.transaction_type == 'task_payment'
        )
        if start_time:
            gmv_query = gmv_query.where(PaymentTransactionDB.completed_at >= start_time)
        gmv_result = await self.db.execute(gmv_query)
        total_gmv = gmv_result.scalar() or 0.0

        # 平台服务费收入
        fee_query = select(func.sum(PaymentTransactionDB.fee_amount)).where(
            PaymentTransactionDB.status == 'completed'
        )
        if start_time:
            fee_query = fee_query.where(PaymentTransactionDB.completed_at >= start_time)
        fee_result = await self.db.execute(fee_query)
        total_fees = fee_result.scalar() or 0.0

        # 待结算金额（Escrow 中 frozen 的金额）
        escrow_frozen_query = select(func.sum(EscrowTransactionDB.total_amount)).where(
            EscrowTransactionDB.status == 'funded'
        )
        escrow_result = await self.db.execute(escrow_frozen_query)
        pending_settlement = escrow_result.scalar() or 0.0

        # 钱包总余额
        wallet_query = select(func.sum(WalletDB.balance))
        wallet_result = await self.db.execute(wallet_query)
        total_wallet_balance = wallet_result.scalar() or 0.0

        return {
            "total_gmv": round(total_gmv, 2),
            "platform_fees": round(total_fees, 2),
            "pending_settlement": round(pending_settlement, 2),
            "total_wallet_balance": round(total_wallet_balance, 2),
        }

    # ==================== 趋势数据 ====================

    async def get_task_trend(
        self,
        days: int = 7,
        organization_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取任务趋势数据（最近 N 天）。"""
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)

        trend_data = []
        current_date = start_time.date()

        while current_date <= end_time.date():
            day_start = datetime.combine(current_date, datetime.min.time())
            day_end = datetime.combine(current_date, datetime.max.time())

            # 当天创建的任务数
            created_query = select(func.count(TaskDB.id)).where(
                TaskDB.created_at >= day_start,
                TaskDB.created_at <= day_end
            )
            created_result = await self.db.execute(created_query)
            created_count = created_result.scalar() or 0

            # 当天完成的任务数
            completed_query = select(func.count(TaskDB.id)).where(
                TaskDB.status == 'completed',
                TaskDB.submitted_at >= day_start,
                TaskDB.submitted_at <= day_end
            )
            completed_result = await self.db.execute(completed_query)
            completed_count = completed_result.scalar() or 0

            trend_data.append({
                "date": current_date.isoformat(),
                "created": created_count,
                "completed": completed_count,
            })

            # 移动到下一天
            current_date += timedelta(days=1)

        return {
            "trend_type": "task_daily",
            "days": days,
            "data": trend_data,
        }

    async def get_worker_trend(
        self,
        days: int = 7,
        organization_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取工人活跃趋势数据。"""
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)

        trend_data = []
        current_date = start_time.date()

        while current_date <= end_time.date():
            day_start = datetime.combine(current_date, datetime.min.time())
            day_end = datetime.combine(current_date, datetime.max.time())

            # 当天活跃工人数
            active_query = select(
                func.count(func.distinct(WorkerSubmissionDB.worker_id))
            ).where(
                WorkerSubmissionDB.submitted_at >= day_start,
                WorkerSubmissionDB.submitted_at <= day_end
            )
            active_result = await self.db.execute(active_query)
            active_count = active_result.scalar() or 0

            trend_data.append({
                "date": current_date.isoformat(),
                "active_workers": active_count,
            })

            current_date += timedelta(days=1)

        return {
            "trend_type": "worker_daily",
            "days": days,
            "data": trend_data,
        }

    async def get_financial_trend(
        self,
        days: int = 7,
        organization_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取财务趋势数据。"""
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)

        trend_data = []
        current_date = start_time.date()

        while current_date <= end_time.date():
            day_start = datetime.combine(current_date, datetime.min.time())
            day_end = datetime.combine(current_date, datetime.max.time())

            # 当天 GMV
            gmv_query = select(func.sum(PaymentTransactionDB.amount)).where(
                PaymentTransactionDB.status == 'completed',
                PaymentTransactionDB.transaction_type == 'task_payment',
                PaymentTransactionDB.completed_at >= day_start,
                PaymentTransactionDB.completed_at <= day_end
            )
            gmv_result = await self.db.execute(gmv_query)
            daily_gmv = gmv_result.scalar() or 0.0

            trend_data.append({
                "date": current_date.isoformat(),
                "gmv": round(daily_gmv, 2),
            })

            current_date += timedelta(days=1)

        return {
            "trend_type": "financial_daily",
            "days": days,
            "data": trend_data,
        }

    # ==================== 工具方法 ====================

    def _get_time_range(self, time_range: str) -> tuple:
        """
        根据时间范围字符串计算起止时间。

        Returns:
            (start_time, end_time) 元组
        """
        end_time = datetime.now()

        if time_range == "realtime":
            start_time = end_time - timedelta(hours=1)
        elif time_range == "hourly":
            start_time = end_time - timedelta(hours=1)
        elif time_range == "daily":
            start_time = end_time - timedelta(days=1)
        elif time_range == "weekly":
            start_time = end_time - timedelta(weeks=1)
        elif time_range == "monthly":
            start_time = end_time - timedelta(days=30)
        elif time_range == "all":
            start_time = None
        else:
            start_time = end_time - timedelta(hours=1)

        return start_time, end_time

    async def save_snapshot(
        self,
        snapshot_type: str,
        metrics: Dict[str, Any],
        time_range: str = "realtime"
    ) -> str:
        """保存仪表板快照。"""
        snapshot_id = str(uuid.uuid4())
        snapshot = DashboardSnapshotDB(
            snapshot_id=snapshot_id,
            snapshot_type=snapshot_type,
            time_range=time_range,
            metrics=metrics,
        )
        self.db.add(snapshot)
        await self.db.commit()
        return snapshot_id
