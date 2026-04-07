"""
争议解决服务
负责争议的创建、处理、调解和解决
"""
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from models.db_models import OrderDB, OrderStatusEnum
from models.p4_models import (
    DisputeDB, DisputeStatusEnum, DisputeResolutionEnum,
    DisputeMessageDB, DisputeEvidenceDB, EscrowDB, EscrowStatusEnum
)
from services.base_service import BaseService


class DisputeService(BaseService):
    """争议解决服务"""

    def create_dispute(
        self,
        tenant_id: str,
        order_id: str,
        opened_by: str,
        opened_by_role: str,
        against_user_id: str,
        title: str,
        description: str,
        dispute_type: str,
        desired_resolution: Optional[str] = None,
        evidence: Optional[List[dict]] = None
    ) -> Optional[DisputeDB]:
        """创建争议"""
        try:
            # 验证订单
            order = self.db.query(OrderDB).filter(OrderDB.id == order_id).first()
            if not order:
                self.logger.warning(f"Order not found: {order_id}")
                return None

            # 租户隔离校验
            if order.tenant_id != tenant_id:
                self.logger.warning(f"Cross-tenant dispute: order tenant={order.tenant_id}, dispute tenant={tenant_id}")
                return None

            dispute = DisputeDB(
                tenant_id=tenant_id,
                order_id=order_id,
                opened_by=opened_by,
                opened_by_role=opened_by_role,
                against_user_id=against_user_id,
                title=title,
                description=description,
                dispute_type=dispute_type,
                desired_resolution=desired_resolution,
                evidence=evidence or [],
                priority="normal"
            )
            self.db.add(dispute)

            # 更新订单状态
            order.status = OrderStatusEnum.CANCELLED  # 争议期间订单暂停
            order.cancelled_at = datetime.now()

            # 更新托管状态
            escrow = self.db.query(EscrowDB).filter(EscrowDB.order_id == order_id).first()
            if escrow:
                escrow.status = EscrowStatusEnum.DISPUTED

            self.db.commit()
            self.db.refresh(dispute)
            self.logger.info(f"Created dispute: {dispute.id} for order: {order_id}")
            return dispute
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to create dispute: {str(e)}")
            raise

    def get_dispute(self, dispute_id: str) -> Optional[DisputeDB]:
        """获取争议"""
        return self.db.query(DisputeDB).filter(DisputeDB.id == dispute_id).first()

    def list_disputes(
        self,
        tenant_id: Optional[str] = None,
        order_id: Optional[str] = None,
        opened_by: Optional[str] = None,
        status: Optional[DisputeStatusEnum] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[DisputeDB]:
        """获取争议列表"""
        query = self.db.query(DisputeDB)

        if tenant_id:
            query = query.filter(DisputeDB.tenant_id == tenant_id)
        if order_id:
            query = query.filter(DisputeDB.order_id == order_id)
        if opened_by:
            query = query.filter(DisputeDB.opened_by == opened_by)
        if status:
            query = query.filter(DisputeDB.status == status)

        return query.order_by(DisputeDB.created_at.desc()).offset(offset).limit(limit).all()

    def assign_mediator(self, dispute_id: str, mediator_id: str) -> bool:
        """指派调解员"""
        dispute = self.get_dispute(dispute_id)
        if not dispute or dispute.status not in [DisputeStatusEnum.OPEN, DisputeStatusEnum.UNDER_REVIEW]:
            return False

        try:
            dispute.assigned_mediator_id = mediator_id
            dispute.status = DisputeStatusEnum.UNDER_REVIEW
            self.db.commit()
            self.logger.info(f"Assigned mediator {mediator_id} to dispute: {dispute_id}")
            return True
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to assign mediator: {str(e)}")
            raise

    def update_dispute_status(
        self,
        dispute_id: str,
        status: DisputeStatusEnum,
        updated_by: str
    ) -> bool:
        """更新争议状态"""
        dispute = self.get_dispute(dispute_id)
        if not dispute:
            return False

        try:
            dispute.status = status
            dispute.updated_at = datetime.now()
            self.db.commit()
            self.logger.info(f"Updated dispute {dispute_id} status to {status.value}")
            return True
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to update dispute status: {str(e)}")
            raise

    def add_dispute_message(
        self,
        tenant_id: str,
        dispute_id: str,
        sender_id: str,
        sender_role: str,
        content: str,
        attachments: Optional[List[str]] = None,
        is_internal: bool = False
    ) -> Optional[DisputeMessageDB]:
        """添加争议消息"""
        try:
            # 验证争议存在
            dispute = self.get_dispute(dispute_id)
            if not dispute:
                self.logger.warning(f"Dispute not found: {dispute_id}")
                return None

            # 租户隔离校验
            if dispute.tenant_id != tenant_id:
                self.logger.warning(f"Cross-tenant dispute message: dispute tenant={dispute.tenant_id}, message tenant={tenant_id}")
                return None

            message = DisputeMessageDB(
                tenant_id=tenant_id,
                dispute_id=dispute_id,
                sender_id=sender_id,
                sender_role=sender_role,
                content=content,
                attachments=attachments or [],
                is_internal=is_internal
            )
            self.db.add(message)
            self.db.commit()
            self.db.refresh(message)
            self.logger.info(f"Added message to dispute: {dispute_id}")
            return message
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to add dispute message: {str(e)}")
            raise

    def submit_evidence(
        self,
        tenant_id: str,
        dispute_id: str,
        submitted_by: str,
        submitted_by_role: str,
        evidence_type: str,
        file_url: str,
        file_name: str,
        file_size: Optional[int] = None,
        description: Optional[str] = None
    ) -> Optional[DisputeEvidenceDB]:
        """提交争议证据"""
        try:
            # 验证争议存在
            dispute = self.get_dispute(dispute_id)
            if not dispute:
                self.logger.warning(f"Dispute not found: {dispute_id}")
                return None

            # 租户隔离校验
            if dispute.tenant_id != tenant_id:
                self.logger.warning(f"Cross-tenant evidence: dispute tenant={dispute.tenant_id}, evidence tenant={tenant_id}")
                return None

            evidence = DisputeEvidenceDB(
                tenant_id=tenant_id,
                dispute_id=dispute_id,
                submitted_by=submitted_by,
                submitted_by_role=submitted_by_role,
                evidence_type=evidence_type,
                file_url=file_url,
                file_name=file_name,
                file_size=file_size,
                description=description
            )
            self.db.add(evidence)

            # 更新争议证据列表
            if dispute.evidence is None:
                dispute.evidence = []
            dispute.evidence.append({
                'id': evidence.id,
                'type': evidence_type,
                'name': file_name,
                'submitted_by': submitted_by,
                'submitted_at': datetime.now().isoformat()
            })

            self.db.commit()
            self.db.refresh(evidence)
            self.logger.info(f"Submitted evidence to dispute: {dispute_id}")
            return evidence
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to submit evidence: {str(e)}")
            raise

    def verify_evidence(self, evidence_id: str) -> bool:
        """验证证据"""
        evidence = self.db.query(DisputeEvidenceDB).filter(DisputeEvidenceDB.id == evidence_id).first()
        if not evidence or evidence.is_verified:
            return False

        try:
            evidence.is_verified = True
            evidence.verified_at = datetime.now()
            self.db.commit()
            self.logger.info(f"Verified evidence: {evidence_id}")
            return True
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to verify evidence: {str(e)}")
            raise

    def resolve_dispute(
        self,
        dispute_id: str,
        resolution: DisputeResolutionEnum,
        resolution_details: str,
        resolved_by: str,
        refund_amount: Optional[float] = None,
        release_amount: Optional[float] = None
    ) -> bool:
        """解决争议"""
        dispute = self.get_dispute(dispute_id)
        if not dispute or dispute.status not in [DisputeStatusEnum.UNDER_REVIEW, DisputeStatusEnum.MEDIATION]:
            self.logger.warning(f"Cannot resolve dispute {dispute_id}: invalid status {dispute.status if dispute else 'not found'}")
            return False

        try:
            dispute.resolution = resolution
            dispute.resolution_details = resolution_details
            dispute.refund_amount = refund_amount
            dispute.release_amount = release_amount
            dispute.status = DisputeStatusEnum.RESOLVED
            dispute.closed_at = datetime.now()
            dispute.closed_by = resolved_by

            # 执行解决结果
            self._execute_resolution(dispute)

            self.db.commit()
            self.logger.info(f"Resolved dispute: {dispute_id} with {resolution.value}")
            return True
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to resolve dispute: {str(e)}")
            raise

    def close_dispute(self, dispute_id: str, closed_by: str) -> bool:
        """关闭争议"""
        dispute = self.get_dispute(dispute_id)
        if not dispute or dispute.status not in [DisputeStatusEnum.RESOLVED]:
            return False

        try:
            dispute.status = DisputeStatusEnum.CLOSED
            dispute.closed_at = datetime.now()
            dispute.closed_by = closed_by
            self.db.commit()
            self.logger.info(f"Closed dispute: {dispute_id}")
            return True
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to close dispute: {str(e)}")
            raise

    def escalate_dispute(self, dispute_id: str, reason: str) -> bool:
        """升级争议"""
        dispute = self.get_dispute(dispute_id)
        if not dispute or dispute.status not in [DisputeStatusEnum.UNDER_REVIEW, DisputeStatusEnum.MEDIATION]:
            return False

        try:
            dispute.status = DisputeStatusEnum.ESCALATED
            dispute.priority = "urgent"
            dispute.updated_at = datetime.now()

            # 添加升级说明消息
            message = DisputeMessageDB(
                tenant_id=dispute.tenant_id,
                dispute_id=dispute_id,
                sender_id="system",
                sender_role="system",
                content=f"争议已升级：{reason}",
                is_internal=True
            )
            self.db.add(message)

            self.db.commit()
            self.logger.info(f"Escalated dispute: {dispute_id}")
            return True
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to escalate dispute: {str(e)}")
            raise

    def _execute_resolution(self, dispute: DisputeDB) -> None:
        """执行争议解决结果"""
        escrow = self.db.query(EscrowDB).filter(EscrowDB.order_id == dispute.order_id).first()
        if not escrow:
            return

        try:
            if dispute.resolution == DisputeResolutionEnum.REFUND:
                # 全额退款给租赁者
                escrow.status = EscrowStatusEnum.REFUNDED
                escrow.refunded_amount = escrow.amount
                escrow.refunded_at = datetime.now()

            elif dispute.resolution == DisputeResolutionEnum.PARTIAL_REFUND:
                # 部分退款
                if dispute.refund_amount:
                    escrow.refunded_amount = dispute.refund_amount
                if dispute.release_amount:
                    escrow.released_amount = dispute.release_amount
                escrow.status = EscrowStatusEnum.PARTIALLY_RELEASED
                escrow.updated_at = datetime.now()

            elif dispute.resolution == DisputeResolutionEnum.MUTUAL_AGREEMENT:
                # 按双方协议分配
                if dispute.refund_amount:
                    escrow.refunded_amount = dispute.refund_amount
                if dispute.release_amount:
                    escrow.released_amount = dispute.release_amount
                escrow.status = EscrowStatusEnum.PARTIALLY_RELEASED
                escrow.updated_at = datetime.now()

            elif dispute.resolution == DisputeResolutionEnum.PLATFORM_MEDIATION:
                # 按平台调解结果分配（通常释放给员工所有者）
                escrow.released_amount = dispute.release_amount or escrow.amount
                escrow.status = EscrowStatusEnum.RELEASED
                escrow.released_at = datetime.now()

            self.db.add(escrow)
            self.logger.info(f"Executed resolution for escrow: {escrow.id}")
        except Exception as e:
            self.logger.error(f"Failed to execute resolution: {str(e)}")
            raise

    def get_dispute_messages(self, dispute_id: str, include_internal: bool = False) -> List[DisputeMessageDB]:
        """获取争议消息列表"""
        query = self.db.query(DisputeMessageDB).filter(
            DisputeMessageDB.dispute_id == dispute_id
        )
        if not include_internal:
            query = query.filter(DisputeMessageDB.is_internal == False)
        return query.order_by(DisputeMessageDB.created_at.asc()).all()

    def get_dispute_evidence(self, dispute_id: str) -> List[DisputeEvidenceDB]:
        """获取争议证据列表"""
        return self.db.query(DisputeEvidenceDB).filter(
            DisputeEvidenceDB.dispute_id == dispute_id
        ).all()

    def get_dispute_stats(self, tenant_id: str) -> dict:
        """获取争议统计信息"""
        total = self.db.query(DisputeDB).filter(DisputeDB.tenant_id == tenant_id).count()
        open_count = self.db.query(DisputeDB).filter(
            DisputeDB.tenant_id == tenant_id,
            DisputeDB.status == DisputeStatusEnum.OPEN
        ).count()
        resolved_count = self.db.query(DisputeDB).filter(
            DisputeDB.tenant_id == tenant_id,
            DisputeDB.status == DisputeStatusEnum.RESOLVED
        ).count()

        return {
            'total': total,
            'open': open_count,
            'under_review': self.db.query(DisputeDB).filter(
                DisputeDB.tenant_id == tenant_id,
                DisputeDB.status == DisputeStatusEnum.UNDER_REVIEW
            ).count(),
            'resolved': resolved_count,
            'closed': self.db.query(DisputeDB).filter(
                DisputeDB.tenant_id == tenant_id,
                DisputeDB.status == DisputeStatusEnum.CLOSED
            ).count()
        }
