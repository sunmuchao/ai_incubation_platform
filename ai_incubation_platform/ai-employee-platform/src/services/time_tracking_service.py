"""
时间追踪与工作验证服务
负责工作时间追踪、工作日志记录和验证
"""
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

from models.db_models import OrderDB, OrderStatusEnum, AIEmployeeDB
from models.p4_models import (
    WorkSessionDB, WorkLogDB, WorkLogStatusEnum, MilestoneDB, MilestoneStatusEnum,
    VerificationMethodEnum, EscrowDB, EscrowStatusEnum
)
from services.base_service import BaseService


class WorkSessionService(BaseService):
    """工作时间会话服务"""

    def start_session(
        self,
        tenant_id: str,
        order_id: str,
        employee_id: str,
        hirer_id: str,
        activity_description: Optional[str] = None,
        automatic: bool = False
    ) -> Optional[WorkSessionDB]:
        """开始工作会话"""
        try:
            # 验证订单状态
            order = self.db.query(OrderDB).filter(OrderDB.id == order_id).first()
            if not order or order.status not in [OrderStatusEnum.CONFIRMED, OrderStatusEnum.IN_PROGRESS]:
                self.logger.warning(f"Invalid order status for work session: {order_id}, status: {order.status}")
                return None

            # 租户隔离校验
            if order.tenant_id != tenant_id:
                self.logger.warning(f"Cross-tenant work session: order tenant={order.tenant_id}, session tenant={tenant_id}")
                return None

            session = WorkSessionDB(
                tenant_id=tenant_id,
                order_id=order_id,
                employee_id=employee_id,
                hirer_id=hirer_id,
                started_at=datetime.now(),
                activity_description=activity_description,
                automatic=automatic,
                status=WorkLogStatusEnum.ACTIVE
            )
            self.db.add(session)
            self.db.commit()
            self.db.refresh(session)
            self.logger.info(f"Started work session: {session.id}")
            return session
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to start work session: {str(e)}")
            raise

    def pause_session(self, session_id: str) -> bool:
        """暂停工作会话"""
        session = self.db.query(WorkSessionDB).filter(WorkSessionDB.id == session_id).first()
        if not session or session.status != WorkLogStatusEnum.ACTIVE:
            return False

        try:
            session.status = WorkLogStatusEnum.PAUSED
            session.ended_at = datetime.now()
            session.duration_seconds = int((session.ended_at - session.started_at).total_seconds())
            self.db.commit()
            self.logger.info(f"Paused work session: {session_id}")
            return True
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to pause work session: {str(e)}")
            raise

    def resume_session(self, session_id: str) -> bool:
        """恢复工作会话"""
        session = self.db.query(WorkSessionDB).filter(WorkSessionDB.id == session_id).first()
        if not session or session.status != WorkLogStatusEnum.PAUSED:
            return False

        try:
            # 保存之前的时长
            if session.ended_at:
                previous_duration = int((session.ended_at - session.started_at).total_seconds())
            else:
                previous_duration = session.duration_seconds

            session.status = WorkLogStatusEnum.ACTIVE
            session.started_at = datetime.now()
            session.ended_at = None
            session.duration_seconds = previous_duration
            self.db.commit()
            self.logger.info(f"Resumed work session: {session_id}")
            return True
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to resume work session: {str(e)}")
            raise

    def end_session(self, session_id: str) -> bool:
        """结束工作会话"""
        session = self.db.query(WorkSessionDB).filter(WorkSessionDB.id == session_id).first()
        if not session or session.status not in [WorkLogStatusEnum.ACTIVE, WorkLogStatusEnum.PAUSED]:
            return False

        try:
            session.status = WorkLogStatusEnum.COMPLETED
            session.ended_at = datetime.now()

            if session.duration_seconds == 0:
                session.duration_seconds = int((session.ended_at - session.started_at).total_seconds())

            session.billable_seconds = session.duration_seconds
            self.db.commit()
            self.logger.info(f"Ended work session: {session_id}")
            return True
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to end work session: {str(e)}")
            raise

    def get_session(self, session_id: str) -> Optional[WorkSessionDB]:
        """获取工作会话"""
        return self.db.query(WorkSessionDB).filter(WorkSessionDB.id == session_id).first()

    def list_sessions(
        self,
        tenant_id: Optional[str] = None,
        order_id: Optional[str] = None,
        employee_id: Optional[str] = None,
        status: Optional[WorkLogStatusEnum] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[WorkSessionDB]:
        """获取工作会话列表"""
        query = self.db.query(WorkSessionDB)

        if tenant_id:
            query = query.filter(WorkSessionDB.tenant_id == tenant_id)
        if order_id:
            query = query.filter(WorkSessionDB.order_id == order_id)
        if employee_id:
            query = query.filter(WorkSessionDB.employee_id == employee_id)
        if status:
            query = query.filter(WorkSessionDB.status == status)

        return query.order_by(WorkSessionDB.started_at.desc()).offset(offset).limit(limit).all()

    def get_active_session(self, order_id: str, employee_id: str) -> Optional[WorkSessionDB]:
        """获取正在进行的工作会话"""
        return self.db.query(WorkSessionDB).filter(
            WorkSessionDB.order_id == order_id,
            WorkSessionDB.employee_id == employee_id,
            WorkSessionDB.status == WorkLogStatusEnum.ACTIVE
        ).first()


class WorkLogService(BaseService):
    """工作日志服务"""

    def create_work_log(
        self,
        tenant_id: str,
        order_id: str,
        employee_id: str,
        description: str,
        duration_minutes: int,
        work_type: str = "development",
        verification_method: VerificationMethodEnum = VerificationMethodEnum.MANUAL,
        verification_data: Optional[dict] = None,
        session_id: Optional[str] = None
    ) -> Optional[WorkLogDB]:
        """创建工作日志"""
        try:
            # 获取订单信息
            order = self.db.query(OrderDB).filter(OrderDB.id == order_id).first()
            if not order:
                self.logger.warning(f"Order not found: {order_id}")
                return None

            # 计算金额
            amount = order.hourly_rate * (duration_minutes / 60)

            work_log = WorkLogDB(
                tenant_id=tenant_id,
                order_id=order_id,
                employee_id=employee_id,
                session_id=session_id,
                logged_at=datetime.now(),
                description=description,
                duration_minutes=duration_minutes,
                work_type=work_type,
                verification_method=verification_method,
                verification_data=verification_data or {},
                hourly_rate=order.hourly_rate,
                amount=amount
            )
            self.db.add(work_log)
            self.db.commit()
            self.db.refresh(work_log)
            self.logger.info(f"Created work log: {work_log.id}")
            return work_log
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to create work log: {str(e)}")
            raise

    def submit_work_log(self, log_id: str) -> bool:
        """提交工作日志审核"""
        work_log = self.db.query(WorkLogDB).filter(WorkLogDB.id == log_id).first()
        if not work_log or work_log.status not in [WorkLogStatusEnum.ACTIVE, WorkLogStatusEnum.PAUSED]:
            return False

        try:
            work_log.status = WorkLogStatusEnum.SUBMITTED
            self.db.commit()
            self.logger.info(f"Submitted work log: {log_id}")
            return True
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to submit work log: {str(e)}")
            raise

    def approve_work_log(self, log_id: str, approved_by: str) -> bool:
        """批准工作日志"""
        work_log = self.db.query(WorkLogDB).filter(WorkLogDB.id == log_id).first()
        if not work_log or work_log.status != WorkLogStatusEnum.SUBMITTED:
            return False

        try:
            work_log.status = WorkLogStatusEnum.APPROVED
            work_log.approved_by = approved_by
            work_log.approved_at = datetime.now()
            work_log.billable = True

            # 释放托管金额（如果有）
            self._release_escrow_for_work_log(work_log)

            self.db.commit()
            self.logger.info(f"Approved work log: {log_id}")
            return True
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to approve work log: {str(e)}")
            raise

    def reject_work_log(self, log_id: str, rejection_reason: str) -> bool:
        """拒绝工作日志"""
        work_log = self.db.query(WorkLogDB).filter(WorkLogDB.id == log_id).first()
        if not work_log or work_log.status != WorkLogStatusEnum.SUBMITTED:
            return False

        try:
            work_log.status = WorkLogStatusEnum.REJECTED
            work_log.rejection_reason = rejection_reason
            work_log.billable = False
            self.db.commit()
            self.logger.info(f"Rejected work log: {log_id}, reason: {rejection_reason}")
            return True
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to reject work log: {str(e)}")
            raise

    def get_work_log(self, log_id: str) -> Optional[WorkLogDB]:
        """获取工作日志"""
        return self.db.query(WorkLogDB).filter(WorkLogDB.id == log_id).first()

    def list_work_logs(
        self,
        tenant_id: Optional[str] = None,
        order_id: Optional[str] = None,
        employee_id: Optional[str] = None,
        session_id: Optional[str] = None,
        status: Optional[WorkLogStatusEnum] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[WorkLogDB]:
        """获取工作日志列表"""
        query = self.db.query(WorkLogDB)

        if tenant_id:
            query = query.filter(WorkLogDB.tenant_id == tenant_id)
        if order_id:
            query = query.filter(WorkLogDB.order_id == order_id)
        if employee_id:
            query = query.filter(WorkLogDB.employee_id == employee_id)
        if session_id:
            query = query.filter(WorkLogDB.session_id == session_id)
        if status:
            query = query.filter(WorkLogDB.status == status)

        return query.order_by(WorkLogDB.logged_at.desc()).offset(offset).limit(limit).all()

    def get_total_hours(self, order_id: str) -> dict:
        """获取订单的总工时统计"""
        result = self.db.query(
            func.sum(WorkLogDB.duration_minutes).label('total_minutes'),
            func.sum(WorkLogDB.amount).label('total_amount')
        ).filter(
            WorkLogDB.order_id == order_id,
            WorkLogDB.status == WorkLogStatusEnum.APPROVED
        ).first()

        return {
            'total_minutes': result.total_minutes or 0,
            'total_hours': (result.total_minutes or 0) / 60,
            'total_amount': result.total_amount or 0
        }

    def _release_escrow_for_work_log(self, work_log: WorkLogDB) -> None:
        """释放工作日志对应的托管金额"""
        # 获取订单的托管
        escrow = self.db.query(EscrowDB).filter(
            EscrowDB.order_id == work_log.order_id,
            EscrowDB.status == EscrowStatusEnum.FUNDED
        ).first()

        if escrow and escrow.released_amount + work_log.amount <= escrow.amount:
            escrow.released_amount += work_log.amount
            if escrow.released_amount >= escrow.amount:
                escrow.status = EscrowStatusEnum.RELEASED
                escrow.released_at = datetime.now()
            else:
                escrow.status = EscrowStatusEnum.PARTIALLY_RELEASED


class MilestoneService(BaseService):
    """里程碑服务"""

    def create_milestone(
        self,
        tenant_id: str,
        order_id: str,
        title: str,
        description: str,
        amount: float,
        deliverables: Optional[List[str]] = None,
        due_date: Optional[datetime] = None
    ) -> Optional[MilestoneDB]:
        """创建里程碑"""
        try:
            milestone = MilestoneDB(
                tenant_id=tenant_id,
                order_id=order_id,
                title=title,
                description=description,
                amount=amount,
                deliverables=deliverables or [],
                due_date=due_date
            )
            self.db.add(milestone)
            self.db.commit()
            self.db.refresh(milestone)
            self.logger.info(f"Created milestone: {milestone.id}")
            return milestone
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to create milestone: {str(e)}")
            raise

    def submit_milestone(self, milestone_id: str, deliverables: Optional[List[str]] = None) -> bool:
        """提交里程碑"""
        milestone = self.db.query(MilestoneDB).filter(MilestoneDB.id == milestone_id).first()
        if not milestone or milestone.status not in [MilestoneStatusEnum.PENDING, MilestoneStatusEnum.IN_PROGRESS]:
            return False

        try:
            milestone.status = MilestoneStatusEnum.SUBMITTED
            milestone.submitted_at = datetime.now()
            if deliverables:
                milestone.deliverables = deliverables
            self.db.commit()
            self.logger.info(f"Submitted milestone: {milestone_id}")
            return True
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to submit milestone: {str(e)}")
            raise

    def approve_milestone(self, milestone_id: str) -> bool:
        """批准里程碑"""
        milestone = self.db.query(MilestoneDB).filter(MilestoneDB.id == milestone_id).first()
        if not milestone or milestone.status != MilestoneStatusEnum.SUBMITTED:
            return False

        try:
            milestone.status = MilestoneStatusEnum.APPROVED
            milestone.approved_at = datetime.now()

            # 释放对应的托管金额
            escrow = self.db.query(EscrowDB).filter(
                EscrowDB.milestone_id == milestone_id,
                EscrowDB.status.in_([EscrowStatusEnum.FUNDED, EscrowStatusEnum.PARTIALLY_RELEASED])
            ).first()

            if escrow:
                escrow.released_amount += milestone.amount
                if escrow.released_amount >= escrow.amount:
                    escrow.status = EscrowStatusEnum.RELEASED
                    escrow.released_at = datetime.now()
                else:
                    escrow.status = EscrowStatusEnum.PARTIALLY_RELEASED

            self.db.commit()
            self.logger.info(f"Approved milestone: {milestone_id}")
            return True
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to approve milestone: {str(e)}")
            raise

    def reject_milestone(self, milestone_id: str, rejection_reason: str) -> bool:
        """拒绝里程碑"""
        milestone = self.db.query(MilestoneDB).filter(MilestoneDB.id == milestone_id).first()
        if not milestone or milestone.status != MilestoneStatusEnum.SUBMITTED:
            return False

        try:
            milestone.status = MilestoneStatusEnum.REJECTED
            milestone.rejected_at = datetime.now()
            milestone.rejection_reason = rejection_reason
            self.db.commit()
            self.logger.info(f"Rejected milestone: {milestone_id}, reason: {rejection_reason}")
            return True
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to reject milestone: {str(e)}")
            raise

    def get_milestone(self, milestone_id: str) -> Optional[MilestoneDB]:
        """获取里程碑"""
        return self.db.query(MilestoneDB).filter(MilestoneDB.id == milestone_id).first()

    def list_milestones(
        self,
        tenant_id: Optional[str] = None,
        order_id: Optional[str] = None,
        status: Optional[MilestoneStatusEnum] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[MilestoneDB]:
        """获取里程碑列表"""
        query = self.db.query(MilestoneDB)

        if tenant_id:
            query = query.filter(MilestoneDB.tenant_id == tenant_id)
        if order_id:
            query = query.filter(MilestoneDB.order_id == order_id)
        if status:
            query = query.filter(MilestoneDB.status == status)

        return query.order_by(MilestoneDB.created_at.asc()).offset(offset).limit(limit).all()
