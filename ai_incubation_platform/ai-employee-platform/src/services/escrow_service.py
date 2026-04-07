"""
支付托管 (Escrow) 服务
负责托管账户的创建、充值、释放和退款
"""
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from models.db_models import OrderDB, OrderStatusEnum, AIEmployeeDB, TenantDB, WalletDB
from models.p4_models import (
    EscrowDB, EscrowStatusEnum, EscrowTransactionDB, MilestoneDB
)
from services.base_service import BaseService
from config.settings import settings


class EscrowService(BaseService):
    """支付托管服务"""

    def create_escrow(
        self,
        tenant_id: str,
        order_id: str,
        hirer_id: str,
        employee_id: str,
        owner_id: str,
        amount: float,
        currency: str = "CNY",
        milestone_id: Optional[str] = None,
        funding_deadline_hours: int = 24
    ) -> Optional[EscrowDB]:
        """创建托管"""
        try:
            # 验证订单
            order = self.db.query(OrderDB).filter(OrderDB.id == order_id).first()
            if not order:
                self.logger.warning(f"Order not found: {order_id}")
                return None

            # 租户隔离校验
            if order.tenant_id != tenant_id:
                self.logger.warning(f"Cross-tenant escrow: order tenant={order.tenant_id}, escrow tenant={tenant_id}")
                return None

            # 计算平台费用和所有者收益
            platform_fee = amount * settings.platform_fee_rate
            owner_earning = amount - platform_fee

            escrow = EscrowDB(
                tenant_id=tenant_id,
                order_id=order_id,
                milestone_id=milestone_id,
                hirer_id=hirer_id,
                employee_id=employee_id,
                owner_id=owner_id,
                amount=amount,
                currency=currency,
                status=EscrowStatusEnum.PENDING,
                funding_deadline=datetime.now() + timedelta(hours=funding_deadline_hours),
                platform_fee=platform_fee,
                owner_earning=owner_earning
            )
            self.db.add(escrow)
            self.db.commit()
            self.db.refresh(escrow)
            self.logger.info(f"Created escrow: {escrow.id} for order: {order_id}")
            return escrow
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to create escrow: {str(e)}")
            raise

    def fund_escrow(
        self,
        escrow_id: str,
        payment_method: str = "balance",
        transaction_id: Optional[str] = None
    ) -> bool:
        """充值托管"""
        escrow = self.db.query(EscrowDB).filter(EscrowDB.id == escrow_id).first()
        if not escrow or escrow.status != EscrowStatusEnum.PENDING:
            self.logger.warning(f"Cannot fund escrow {escrow_id}: invalid status {escrow.status if escrow else 'not found'}")
            return False

        try:
            # 检查充值截止时间
            if datetime.now() > escrow.funding_deadline:
                escrow.status = EscrowStatusEnum.REFUNDED
                escrow.refunded_at = datetime.now()
                self.db.commit()
                self.logger.warning(f"Escrow {escrow_id} expired")
                return False

            # 扣除租户钱包余额
            wallet = self.db.query(WalletDB).filter(WalletDB.tenant_id == escrow.tenant_id).first()
            if not wallet or wallet.balance < escrow.amount:
                self.logger.warning(f"Insufficient balance for escrow {escrow_id}")
                return False

            # 创建交易记录
            transaction = EscrowTransactionDB(
                tenant_id=escrow.tenant_id,
                escrow_id=escrow_id,
                transaction_type="fund",
                amount=escrow.amount,
                currency=escrow.currency,
                status="completed",
                payment_method=payment_method,
                third_party_id=transaction_id,
                description=f"充值托管：{escrow_id}",
                processed_at=datetime.now()
            )
            self.db.add(transaction)

            # 更新钱包余额
            wallet.balance -= escrow.amount
            wallet.frozen_balance += escrow.amount

            # 更新托管状态
            escrow.status = EscrowStatusEnum.FUNDED
            escrow.funded_at = datetime.now()
            escrow.payment_method = payment_method
            escrow.transaction_id = transaction_id

            # 更新订单状态为进行中
            order = self.db.query(OrderDB).filter(OrderDB.id == escrow.order_id).first()
            if order and order.status == OrderStatusEnum.CONFIRMED:
                order.status = OrderStatusEnum.IN_PROGRESS
                order.started_at = datetime.now()

            self.db.commit()
            self.logger.info(f"Funded escrow: {escrow_id}")
            return True
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to fund escrow: {str(e)}")
            raise

    def release_escrow(
        self,
        escrow_id: str,
        release_amount: Optional[float] = None,
        reason: Optional[str] = None
    ) -> bool:
        """释放托管金额"""
        escrow = self.db.query(EscrowDB).filter(EscrowDB.id == escrow_id).first()
        if not escrow or escrow.status not in [EscrowStatusEnum.FUNDED, EscrowStatusEnum.PARTIALLY_RELEASED]:
            self.logger.warning(f"Cannot release escrow {escrow_id}: invalid status {escrow.status if escrow else 'not found'}")
            return False

        try:
            release_amount = release_amount or escrow.amount

            # 检查可释放金额
            available = escrow.amount - escrow.released_amount
            if release_amount > available:
                self.logger.warning(f"Release amount {release_amount} exceeds available {available}")
                return False

            # 创建交易记录
            transaction = EscrowTransactionDB(
                tenant_id=escrow.tenant_id,
                escrow_id=escrow_id,
                transaction_type="release",
                amount=release_amount,
                currency=escrow.currency,
                status="completed",
                description=f"释放托管：{reason or '完成交付'}",
                processed_at=datetime.now()
            )
            self.db.add(transaction)

            # 更新托管状态
            escrow.released_amount += release_amount
            escrow.released_at = datetime.now()

            if escrow.released_amount >= escrow.amount:
                escrow.status = EscrowStatusEnum.RELEASED

                # 更新订单状态
                order = self.db.query(OrderDB).filter(OrderDB.id == escrow.order_id).first()
                if order:
                    order.status = OrderStatusEnum.COMPLETED
                    order.completed_at = datetime.now()
            else:
                escrow.status = EscrowStatusEnum.PARTIALLY_RELEASED

            # 更新钱包（将冻结金额转为所有者收益）
            # 实际打款给所有者的逻辑
            owner_wallet = self.db.query(WalletDB).join(TenantDB).filter(
                TenantDB.id == escrow.tenant_id
            ).first()  # 简化处理，实际应该按所有者租户

            # 更新员工收入统计
            employee = self.db.query(AIEmployeeDB).filter(AIEmployeeDB.id == escrow.employee_id).first()
            if employee:
                proportion = release_amount / escrow.amount
                employee.total_earnings += escrow.owner_earning * proportion

            self.db.commit()
            self.logger.info(f"Released {release_amount} from escrow: {escrow_id}")
            return True
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to release escrow: {str(e)}")
            raise

    def refund_escrow(
        self,
        escrow_id: str,
        refund_amount: Optional[float] = None,
        reason: Optional[str] = None
    ) -> bool:
        """退款托管金额"""
        escrow = self.db.query(EscrowDB).filter(EscrowDB.id == escrow_id).first()
        if not escrow or escrow.status not in [EscrowStatusEnum.FUNDED, EscrowStatusEnum.PARTIALLY_RELEASED]:
            self.logger.warning(f"Cannot refund escrow {escrow_id}: invalid status {escrow.status if escrow else 'not found'}")
            return False

        try:
            refund_amount = refund_amount or (escrow.amount - escrow.released_amount)

            # 创建交易记录
            transaction = EscrowTransactionDB(
                tenant_id=escrow.tenant_id,
                escrow_id=escrow_id,
                transaction_type="refund",
                amount=refund_amount,
                currency=escrow.currency,
                status="completed",
                description=f"退款托管：{reason or '订单取消'}",
                processed_at=datetime.now()
            )
            self.db.add(transaction)

            # 更新托管状态
            escrow.refunded_amount += refund_amount
            escrow.refunded_at = datetime.now()

            # 恢复钱包冻结金额
            wallet = self.db.query(WalletDB).filter(WalletDB.tenant_id == escrow.tenant_id).first()
            if wallet:
                wallet.frozen_balance -= refund_amount
                wallet.balance += refund_amount  # 退回余额

            if escrow.refunded_amount + escrow.released_amount >= escrow.amount:
                escrow.status = EscrowStatusEnum.REFUNDED
            else:
                escrow.status = EscrowStatusEnum.PARTIALLY_RELEASED

            self.db.commit()
            self.logger.info(f"Refunded {refund_amount} from escrow: {escrow_id}")
            return True
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to refund escrow: {str(e)}")
            raise

    def dispute_escrow(self, escrow_id: str) -> bool:
        """标记托管为争议状态"""
        escrow = self.db.query(EscrowDB).filter(EscrowDB.id == escrow_id).first()
        if not escrow or escrow.status not in [EscrowStatusEnum.FUNDED, EscrowStatusEnum.PARTIALLY_RELEASED]:
            return False

        try:
            escrow.status = EscrowStatusEnum.DISPUTED
            self.db.commit()
            self.logger.info(f"Escrow marked as disputed: {escrow_id}")
            return True
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to dispute escrow: {str(e)}")
            raise

    def get_escrow(self, escrow_id: str) -> Optional[EscrowDB]:
        """获取托管"""
        return self.db.query(EscrowDB).filter(EscrowDB.id == escrow_id).first()

    def list_escrows(
        self,
        tenant_id: Optional[str] = None,
        order_id: Optional[str] = None,
        hirer_id: Optional[str] = None,
        employee_id: Optional[str] = None,
        owner_id: Optional[str] = None,
        status: Optional[EscrowStatusEnum] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[EscrowDB]:
        """获取托管列表"""
        query = self.db.query(EscrowDB)

        if tenant_id:
            query = query.filter(EscrowDB.tenant_id == tenant_id)
        if order_id:
            query = query.filter(EscrowDB.order_id == order_id)
        if hirer_id:
            query = query.filter(EscrowDB.hirer_id == hirer_id)
        if employee_id:
            query = query.filter(EscrowDB.employee_id == employee_id)
        if owner_id:
            query = query.filter(EscrowDB.owner_id == owner_id)
        if status:
            query = query.filter(EscrowDB.status == status)

        return query.order_by(EscrowDB.created_at.desc()).offset(offset).limit(limit).all()

    def check_expired_escrows(self) -> int:
        """检查并处理过期的托管"""
        try:
            expired_escrows = self.db.query(EscrowDB).filter(
                EscrowDB.status == EscrowStatusEnum.PENDING,
                EscrowDB.funding_deadline < datetime.now()
            ).all()

            expired_count = 0
            for escrow in expired_escrows:
                escrow.status = EscrowStatusEnum.REFUNDED
                escrow.refunded_at = datetime.now()
                expired_count += 1

            self.db.commit()
            self.logger.info(f"Processed {expired_count} expired escrows")
            return expired_count
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to check expired escrows: {str(e)}")
            raise

    def get_escrow_stats(self, escrow_id: str) -> dict:
        """获取托管统计信息"""
        escrow = self.get_escrow(escrow_id)
        if not escrow:
            return {}

        transactions = self.db.query(EscrowTransactionDB).filter(
            EscrowTransactionDB.escrow_id == escrow_id
        ).all()

        return {
            'escrow_id': escrow_id,
            'total_amount': escrow.amount,
            'released_amount': escrow.released_amount,
            'refunded_amount': escrow.refunded_amount,
            'remaining_amount': escrow.amount - escrow.released_amount - escrow.refunded_amount,
            'platform_fee': escrow.platform_fee,
            'owner_earning': escrow.owner_earning,
            'status': escrow.status.value,
            'transaction_count': len(transactions)
        }
