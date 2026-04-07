"""
提案/投标服务
负责职位发布和提案的 CRUD 操作及状态流转
"""
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from models.db_models import (
    OrderDB, OrderStatusEnum, AIEmployeeDB, EmployeeStatusEnum
)
from models.p4_models import (
    JobPostingDB, ProposalDB, ProposalStatusEnum, ProposalTypeEnum
)
from services.base_service import BaseService


class JobPostingService(BaseService):
    """职位发布服务"""

    def create_job_posting(
        self,
        tenant_id: str,
        hirer_id: str,
        title: str,
        description: str,
        job_type: ProposalTypeEnum = ProposalTypeEnum.HOURLY,
        budget_min: Optional[float] = None,
        budget_max: Optional[float] = None,
        hourly_rate_min: Optional[float] = None,
        hourly_rate_max: Optional[float] = None,
        duration_hours: Optional[int] = None,
        required_skills: Optional[List[str]] = None,
        required_experience: Optional[str] = None,
        deadline: Optional[datetime] = None
    ) -> Optional[JobPostingDB]:
        """创建职位发布"""
        try:
            job_posting = JobPostingDB(
                tenant_id=tenant_id,
                hirer_id=hirer_id,
                title=title,
                description=description,
                job_type=job_type,
                budget_min=budget_min,
                budget_max=budget_max,
                hourly_rate_min=hourly_rate_min,
                hourly_rate_max=hourly_rate_max,
                duration_hours=duration_hours,
                required_skills=required_skills or [],
                required_experience=required_experience,
                deadline=deadline
            )
            self.db.add(job_posting)
            self.db.commit()
            self.db.refresh(job_posting)
            self.logger.info(f"Created job posting: {job_posting.id}")
            return job_posting
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to create job posting: {str(e)}")
            raise

    def get_job_posting(self, job_posting_id: str) -> Optional[JobPostingDB]:
        """获取职位发布"""
        job_posting = self.db.query(JobPostingDB).filter(JobPostingDB.id == job_posting_id).first()
        if job_posting:
            # 增加浏览次数
            job_posting.views += 1
            self.db.commit()
        return job_posting

    def list_job_postings(
        self,
        tenant_id: Optional[str] = None,
        hirer_id: Optional[str] = None,
        status: Optional[str] = None,
        skills: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[JobPostingDB]:
        """获取职位发布列表"""
        query = self.db.query(JobPostingDB)

        if tenant_id:
            query = query.filter(JobPostingDB.tenant_id == tenant_id)
        if hirer_id:
            query = query.filter(JobPostingDB.hirer_id == hirer_id)
        if status:
            query = query.filter(JobPostingDB.status == status)

        # 按技能过滤
        if skills:
            query = query.filter(JobPostingDB.required_skills.overlap(skills))

        # 只显示开放的职位
        query = query.filter(JobPostingDB.status == "open")

        return query.order_by(JobPostingDB.created_at.desc()).offset(offset).limit(limit).all()

    def close_job_posting(self, job_posting_id: str) -> bool:
        """关闭职位发布"""
        job_posting = self.get_job_posting(job_posting_id)
        if not job_posting or job_posting.status != "open":
            return False

        try:
            job_posting.status = "closed"
            job_posting.closed_at = datetime.now()
            self.db.commit()
            self.logger.info(f"Closed job posting: {job_posting_id}")
            return True
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to close job posting: {str(e)}")
            raise

    def fill_job_posting(self, job_posting_id: str, proposal_id: str) -> bool:
        """标记职位已招满（提案被接受）"""
        job_posting = self.db.query(JobPostingDB).filter(JobPostingDB.id == job_posting_id).first()
        if not job_posting or job_posting.status != "open":
            return False

        try:
            job_posting.status = "filled"
            job_posting.filled_at = datetime.now()
            self.db.commit()
            self.logger.info(f"Filled job posting: {job_posting_id} with proposal: {proposal_id}")
            return True
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to fill job posting: {str(e)}")
            raise


class ProposalService(BaseService):
    """提案服务"""

    def create_proposal(
        self,
        tenant_id: str,
        job_posting_id: str,
        employee_id: str,
        owner_id: str,
        cover_letter: str,
        proposed_rate: float,
        proposed_duration_hours: Optional[int] = None,
        proposal_type: ProposalTypeEnum = ProposalTypeEnum.FIXED_PRICE,
        delivery_date: Optional[datetime] = None,
        attachments: Optional[List[str]] = None
    ) -> Optional[ProposalDB]:
        """创建提案"""
        try:
            # 获取职位发布信息
            job_posting = self.db.query(JobPostingDB).filter(JobPostingDB.id == job_posting_id).first()
            if not job_posting or job_posting.status != "open":
                self.logger.warning(f"Job posting not available: {job_posting_id}")
                return None

            # 获取员工信息
            employee = self.db.query(AIEmployeeDB).filter(AIEmployeeDB.id == employee_id).first()
            if not employee:
                self.logger.warning(f"Employee not found: {employee_id}")
                return None

            # 租户隔离校验
            if employee.tenant_id != tenant_id:
                self.logger.warning(f"Cross-tenant proposal: employee tenant={employee.tenant_id}, job tenant={job_posting.tenant_id}")
                return None

            # 计算过期时间（7 天后）
            expires_at = datetime.now() + timedelta(days=7)

            proposal = ProposalDB(
                tenant_id=tenant_id,
                job_posting_id=job_posting_id,
                employee_id=employee_id,
                owner_id=owner_id,
                cover_letter=cover_letter,
                proposed_rate=proposed_rate,
                proposed_duration_hours=proposed_duration_hours,
                proposal_type=proposal_type,
                delivery_date=delivery_date,
                attachments=attachments or [],
                expires_at=expires_at
            )
            self.db.add(proposal)

            # 更新职位发布的提案数量
            job_posting.proposal_count += 1

            self.db.commit()
            self.db.refresh(proposal)
            self.logger.info(f"Created proposal: {proposal.id}")
            return proposal
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to create proposal: {str(e)}")
            raise

    def get_proposal(self, proposal_id: str) -> Optional[ProposalDB]:
        """获取提案"""
        return self.db.query(ProposalDB).filter(ProposalDB.id == proposal_id).first()

    def list_proposals(
        self,
        tenant_id: Optional[str] = None,
        job_posting_id: Optional[str] = None,
        employee_id: Optional[str] = None,
        owner_id: Optional[str] = None,
        status: Optional[ProposalStatusEnum] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[ProposalDB]:
        """获取提案列表"""
        query = self.db.query(ProposalDB)

        if tenant_id:
            query = query.filter(ProposalDB.tenant_id == tenant_id)
        if job_posting_id:
            query = query.filter(ProposalDB.job_posting_id == job_posting_id)
        if employee_id:
            query = query.filter(ProposalDB.employee_id == employee_id)
        if owner_id:
            query = query.filter(ProposalDB.owner_id == owner_id)
        if status:
            query = query.filter(ProposalDB.status == status)

        return query.order_by(ProposalDB.created_at.desc()).offset(offset).limit(limit).all()

    def accept_proposal(
        self,
        proposal_id: str,
        hirer_id: str,
        hirer_message: Optional[str] = None
    ) -> bool:
        """接受提案"""
        proposal = self.get_proposal(proposal_id)
        if not proposal or proposal.status != ProposalStatusEnum.PENDING:
            return False

        try:
            proposal.status = ProposalStatusEnum.ACCEPTED
            proposal.hirer_message = hirer_message
            proposal.responded_at = datetime.now()

            # 更新职位发布状态
            job_posting = self.db.query(JobPostingDB).filter(JobPostingDB.id == proposal.job_posting_id).first()
            if job_posting:
                job_posting.status = "filled"
                job_posting.filled_at = datetime.now()

            # 创建订单
            order = OrderDB(
                tenant_id=proposal.tenant_id,
                employee_id=proposal.employee_id,
                hirer_id=hirer_id,
                owner_id=proposal.owner_id,
                duration_hours=proposal.proposed_duration_hours or 10,
                task_description=job_posting.description if job_posting else proposal.cover_letter,
                hourly_rate=proposal.proposed_rate,
                total_amount=proposal.proposed_rate * (proposal.proposed_duration_hours or 10),
                platform_fee_rate=0.1,
                platform_fee=proposal.proposed_rate * (proposal.proposed_duration_hours or 10) * 0.1,
                owner_earning=proposal.proposed_rate * (proposal.proposed_duration_hours or 10) * 0.9,
                status=OrderStatusEnum.CONFIRMED,
                confirmed_at=datetime.now()
            )
            self.db.add(order)

            # 关联提案和订单
            proposal.order_id = order.id

            # 更新员工状态
            employee = self.db.query(AIEmployeeDB).filter(AIEmployeeDB.id == proposal.employee_id).first()
            if employee:
                employee.status = EmployeeStatusEnum.HIRED

            self.db.commit()
            self.logger.info(f"Accepted proposal: {proposal_id}, created order: {order.id}")
            return True
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to accept proposal: {str(e)}")
            raise

    def reject_proposal(
        self,
        proposal_id: str,
        hirer_id: str,
        hirer_message: Optional[str] = None
    ) -> bool:
        """拒绝提案"""
        proposal = self.get_proposal(proposal_id)
        if not proposal or proposal.status != ProposalStatusEnum.PENDING:
            return False

        try:
            proposal.status = ProposalStatusEnum.REJECTED
            proposal.hirer_message = hirer_message
            proposal.responded_at = datetime.now()
            self.db.commit()
            self.logger.info(f"Rejected proposal: {proposal_id}")
            return True
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to reject proposal: {str(e)}")
            raise

    def cancel_proposal(self, proposal_id: str, owner_id: str) -> bool:
        """取消提案"""
        proposal = self.get_proposal(proposal_id)
        if not proposal or proposal.owner_id != owner_id or proposal.status != ProposalStatusEnum.PENDING:
            return False

        try:
            proposal.status = ProposalStatusEnum.CANCELLED
            self.db.commit()
            self.logger.info(f"Cancelled proposal: {proposal_id}")
            return True
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to cancel proposal: {str(e)}")
            raise

    def expire_proposals(self) -> int:
        """过期超时提案"""
        try:
            expired_count = self.db.query(ProposalDB).filter(
                ProposalDB.status == ProposalStatusEnum.PENDING,
                ProposalDB.expires_at < datetime.now()
            ).update({"status": ProposalStatusEnum.EXPIRED})
            self.db.commit()
            self.logger.info(f"Expired {expired_count} proposals")
            return expired_count
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to expire proposals: {str(e)}")
            raise
