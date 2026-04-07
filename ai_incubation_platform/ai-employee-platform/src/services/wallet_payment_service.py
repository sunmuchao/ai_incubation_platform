"""
钱包与支付服务
负责租户钱包管理和支付处理
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
import uuid

from models.db_models import (
    WalletDB, PaymentTransactionDB, PaymentMethodEnum, PaymentStatusEnum,
    InvoiceDB, InvoiceStatusEnum, TenantDB
)
from services.base_service import BaseService


class WalletService(BaseService):
    """钱包服务"""

    def get_wallet(self, tenant_id: str) -> Optional[WalletDB]:
        """获取租户钱包"""
        return self.db.query(WalletDB).filter(WalletDB.tenant_id == tenant_id).first()

    def create_wallet(self, tenant_id: str) -> WalletDB:
        """创建租户钱包"""
        try:
            wallet = WalletDB(tenant_id=tenant_id)
            self.db.add(wallet)
            self.db.commit()
            self.db.refresh(wallet)
            self.logger.info(f"Created wallet for tenant: {tenant_id}")
            return wallet
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to create wallet: {str(e)}")
            raise

    def recharge_wallet(self, tenant_id: str, amount: float) -> bool:
        """钱包充值"""
        wallet = self.get_wallet(tenant_id)
        if not wallet or amount <= 0:
            return False

        try:
            wallet.balance += amount
            wallet.total_recharge += amount
            wallet.updated_at = datetime.now()
            self.db.commit()
            self.logger.info(f"Recharged wallet for tenant {tenant_id}: {amount}")
            return True
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to recharge wallet: {str(e)}")
            raise

    def deduct_wallet(self, tenant_id: str, amount: float) -> bool:
        """钱包扣款"""
        wallet = self.get_wallet(tenant_id)
        if not wallet or wallet.balance < amount:
            return False

        try:
            wallet.balance -= amount
            wallet.total_consumption += amount
            wallet.updated_at = datetime.now()
            self.db.commit()
            self.logger.info(f"Deducted wallet for tenant {tenant_id}: {amount}")
            return True
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to deduct wallet: {str(e)}")
            raise

    def freeze_wallet(self, tenant_id: str, amount: float) -> bool:
        """冻结钱包金额"""
        wallet = self.get_wallet(tenant_id)
        if not wallet or wallet.balance < amount:
            return False

        try:
            wallet.balance -= amount
            wallet.frozen_balance += amount
            wallet.updated_at = datetime.now()
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to freeze wallet: {str(e)}")
            raise

    def unfreeze_wallet(self, tenant_id: str, amount: float) -> bool:
        """解冻钱包金额"""
        wallet = self.get_wallet(tenant_id)
        if not wallet or wallet.frozen_balance < amount:
            return False

        try:
            wallet.frozen_balance -= amount
            wallet.balance += amount
            wallet.updated_at = datetime.now()
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to unfreeze wallet: {str(e)}")
            raise


class PaymentService(BaseService):
    """支付服务"""

    def create_payment(
        self,
        tenant_id: str,
        user_id: str,
        amount: float,
        payment_method: str,
        order_id: Optional[str] = None,
        invoice_id: Optional[str] = None
    ) -> Optional[PaymentTransactionDB]:
        """创建支付交易"""
        try:
            # 验证租户
            tenant = self.db.query(TenantDB).filter(TenantDB.id == tenant_id).first()
            if not tenant:
                self.logger.warning(f"Tenant not found: {tenant_id}")
                return None

            # 如果是余额支付，检查余额
            if payment_method == "balance":
                wallet_service = WalletService(self.db)
                wallet = wallet_service.get_wallet(tenant_id)
                if not wallet or wallet.balance < amount:
                    self.logger.warning(f"Insufficient balance for tenant {tenant_id}")
                    return None

            payment = PaymentTransactionDB(
                tenant_id=tenant_id,
                user_id=user_id,
                order_id=order_id,
                invoice_id=invoice_id,
                amount=amount,
                payment_method=PaymentMethodEnum(payment_method)
            )

            # 如果是余额支付，直接处理
            if payment_method == "balance":
                wallet_service = WalletService(self.db)
                if wallet_service.deduct_wallet(tenant_id, amount):
                    payment.status = PaymentStatusEnum.SUCCESS
                    payment = self._handle_payment_success(payment, order_id, invoice_id)
                else:
                    payment.status = PaymentStatusEnum.FAILED
                    payment.error_message = "Insufficient balance"
            else:
                # 第三方支付标记为处理中
                payment.status = PaymentStatusEnum.PROCESSING

            self.db.add(payment)
            self.db.commit()
            self.db.refresh(payment)
            self.logger.info(f"Created payment: {payment.id}")
            return payment
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to create payment: {str(e)}")
            raise

    def _handle_payment_success(
        self,
        payment: PaymentTransactionDB,
        order_id: Optional[str],
        invoice_id: Optional[str]
    ) -> PaymentTransactionDB:
        """处理支付成功"""
        payment.status = PaymentStatusEnum.SUCCESS
        payment.third_party_transaction_id = f"mock_{str(uuid.uuid4())}"

        # 如果是支付订单，更新订单状态
        if order_id:
            from models.db_models import OrderDB, OrderStatusEnum
            order = self.db.query(OrderDB).filter(OrderDB.id == order_id).first()
            if order and order.status == OrderStatusEnum.PENDING:
                order.status = OrderStatusEnum.CONFIRMED
                order.confirmed_at = datetime.now()

        # 如果是支付发票，更新发票状态
        if invoice_id:
            invoice = self.db.query(InvoiceDB).filter(InvoiceDB.id == invoice_id).first()
            if invoice and invoice.status == InvoiceStatusEnum.ISSUED:
                invoice.paid_amount = invoice.total_amount
                invoice.payment_status = PaymentStatusEnum.SUCCESS
                invoice.status = InvoiceStatusEnum.PAID
                invoice.paid_at = datetime.now()

        return payment

    def get_payment(self, payment_id: str) -> Optional[PaymentTransactionDB]:
        """获取支付交易"""
        return self.db.query(PaymentTransactionDB).filter(PaymentTransactionDB.id == payment_id).first()

    def list_payments(
        self,
        tenant_id: str,
        status: Optional[PaymentStatusEnum] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[PaymentTransactionDB]:
        """获取支付列表"""
        query = self.db.query(PaymentTransactionDB).filter(PaymentTransactionDB.tenant_id == tenant_id)
        if status:
            query = query.filter(PaymentTransactionDB.status == status)
        return query.offset(offset).limit(limit).all()

    def process_third_party_payment(
        self,
        payment_id: str,
        success: bool,
        transaction_id: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """处理第三方支付结果"""
        payment = self.get_payment(payment_id)
        if not payment or payment.status != PaymentStatusEnum.PROCESSING:
            return False

        try:
            if success:
                payment.status = PaymentStatusEnum.SUCCESS
                payment.third_party_transaction_id = transaction_id or f"mock_{str(uuid.uuid4())}"
                payment = self._handle_payment_success(payment, payment.order_id, payment.invoice_id)
            else:
                payment.status = PaymentStatusEnum.FAILED
                payment.error_message = error_message or "Third party payment failed"

            self.db.commit()
            self.logger.info(f"Processed third party payment: {payment_id}, success={success}")
            return True
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to process third party payment: {str(e)}")
            raise
