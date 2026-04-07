"""
账单服务
负责用量记录和账单发票管理
"""
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import uuid

from models.db_models import (
    UsageRecordDB, InvoiceDB, InvoiceStatusEnum, TenantDB
)
from services.base_service import BaseService
from config.settings import settings


class UsageService(BaseService):
    """用量记录服务"""

    def create_usage_record(
        self,
        tenant_id: str,
        user_id: str,
        resource_type: str,
        quantity: float,
        unit: str,
        unit_price: float,
        total_amount: float,
        description: str,
        resource_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> UsageRecordDB:
        """创建用量记录"""
        try:
            usage = UsageRecordDB(
                tenant_id=tenant_id,
                user_id=user_id,
                resource_type=resource_type,
                resource_id=resource_id,
                quantity=quantity,
                unit=unit,
                unit_price=unit_price,
                total_amount=total_amount,
                description=description,
                start_time=start_time or datetime.now(),
                end_time=end_time
            )
            self.db.add(usage)
            self.db.commit()
            self.db.refresh(usage)
            self.logger.info(f"Created usage record: {usage.id}")
            return usage
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to create usage record: {str(e)}")
            raise

    def get_usage_records(
        self,
        tenant_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        resource_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[UsageRecordDB]:
        """获取用量记录列表"""
        query = self.db.query(UsageRecordDB).filter(UsageRecordDB.tenant_id == tenant_id)
        if start_time:
            query = query.filter(UsageRecordDB.created_at >= start_time)
        if end_time:
            query = query.filter(UsageRecordDB.created_at <= end_time)
        if resource_type:
            query = query.filter(UsageRecordDB.resource_type == resource_type)
        return query.order_by(UsageRecordDB.created_at.desc()).offset(offset).limit(limit).all()


class InvoiceService(BaseService):
    """账单发票服务"""

    def generate_invoice(
        self,
        tenant_id: str,
        period_start: datetime,
        period_end: datetime
    ) -> Optional[InvoiceDB]:
        """生成账单"""
        try:
            # 验证租户
            tenant = self.db.query(TenantDB).filter(TenantDB.id == tenant_id).first()
            if not tenant:
                self.logger.warning(f"Tenant not found: {tenant_id}")
                return None

            # 获取该周期内的用量记录
            usage_records = self.db.query(UsageRecordDB).filter(
                UsageRecordDB.tenant_id == tenant_id,
                UsageRecordDB.created_at >= period_start,
                UsageRecordDB.created_at <= period_end
            ).all()

            if not usage_records:
                self.logger.warning(f"No usage records for tenant {tenant_id} in period")
                return None

            # 计算总金额
            total_amount = sum(r.total_amount for r in usage_records)

            # 生成发票编号
            invoice_number = f"INV-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"

            # 计算到期日
            due_date = datetime.now() + timedelta(days=settings.invoice_due_days)

            invoice = InvoiceDB(
                tenant_id=tenant_id,
                invoice_number=invoice_number,
                period_start=period_start,
                period_end=period_end,
                total_amount=total_amount,
                due_date=due_date,
                items=[{
                    "usage_id": r.id,
                    "resource_type": r.resource_type,
                    "description": r.description,
                    "quantity": r.quantity,
                    "unit": r.unit,
                    "unit_price": r.unit_price,
                    "amount": r.total_amount
                } for r in usage_records]
            )

            self.db.add(invoice)
            self.db.commit()
            self.db.refresh(invoice)
            self.logger.info(f"Generated invoice: {invoice.invoice_number} for tenant {tenant_id}")
            return invoice
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to generate invoice: {str(e)}")
            raise

    def get_invoice(self, invoice_id: str) -> Optional[InvoiceDB]:
        """获取账单"""
        return self.db.query(InvoiceDB).filter(InvoiceDB.id == invoice_id).first()

    def get_invoices(
        self,
        tenant_id: str,
        status: Optional[InvoiceStatusEnum] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[InvoiceDB]:
        """获取账单列表"""
        query = self.db.query(InvoiceDB).filter(InvoiceDB.tenant_id == tenant_id)
        if status:
            query = query.filter(InvoiceDB.status == status)
        return query.order_by(InvoiceDB.created_at.desc()).offset(offset).limit(limit).all()

    def issue_invoice(self, invoice_id: str) -> bool:
        """开具发票"""
        invoice = self.get_invoice(invoice_id)
        if not invoice or invoice.status != InvoiceStatusEnum.DRAFT:
            return False

        try:
            invoice.status = InvoiceStatusEnum.ISSUED
            invoice.issued_at = datetime.now()
            self.db.commit()
            self.logger.info(f"Issued invoice: {invoice_id}")
            return True
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to issue invoice: {str(e)}")
            raise

    def mark_invoice_paid(self, invoice_id: str) -> bool:
        """标记发票已支付"""
        invoice = self.get_invoice(invoice_id)
        if not invoice or invoice.status != InvoiceStatusEnum.ISSUED:
            return False

        try:
            invoice.status = InvoiceStatusEnum.PAID
            invoice.paid_amount = invoice.total_amount
            invoice.payment_status = InvoiceStatusEnum.PAID
            invoice.paid_at = datetime.now()
            self.db.commit()
            self.logger.info(f"Marked invoice as paid: {invoice_id}")
            return True
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to mark invoice as paid: {str(e)}")
            raise
