"""
P6 - 发票服务

功能：
1. 企业发票信息管理
2. 发票申请与开具
3. 发票历史记录
4. 电子发票交付
"""
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from models.db_models import (
    CompanyInvoiceInfoDB, InvoiceDB, OrderDB, InvoiceStatus, UserDB
)
import logging

logger = logging.getLogger(__name__)


class InvoiceService:
    """发票服务"""

    # 发票税率（增值税专用发票 6%）
    TAX_RATE = 0.06

    def __init__(self, db: Session):
        self.db = db

    # ==================== 企业发票信息管理 ====================

    def save_company_info(
        self,
        user_id: str,
        company_name: str,
        tax_id: str,
        company_address: str = None,
        company_phone: str = None,
        bank_name: str = None,
        bank_account: str = None,
        receiver_email: str = None,
        receiver_address: str = None,
        receiver_phone: str = None,
        invoice_type_preference: str = "electronic",
    ) -> CompanyInvoiceInfoDB:
        """
        保存/更新企业发票信息

        Args:
            user_id: 用户 ID
            company_name: 公司名称
            tax_id: 纳税人识别号
            company_address: 公司地址
            company_phone: 公司电话
            bank_name: 开户行名称
            bank_account: 银行账号
            receiver_email: 电子发票接收邮箱
            receiver_address: 纸质发票收件地址
            receiver_phone: 收件人电话
            invoice_type_preference: 发票类型偏好 (electronic/paper)

        Returns:
            CompanyInvoiceInfoDB: 企业发票信息对象
        """
        # 检查是否已存在
        info = self.db.query(CompanyInvoiceInfoDB).filter(
            CompanyInvoiceInfoDB.user_id == user_id
        ).first()

        if info:
            # 更新现有信息
            info.company_name = company_name
            info.tax_id = tax_id
            info.company_address = company_address
            info.company_phone = company_phone
            info.bank_name = bank_name
            info.bank_account = bank_account
            info.receiver_email = receiver_email
            info.receiver_address = receiver_address
            info.receiver_phone = receiver_phone
            info.invoice_type_preference = invoice_type_preference
            info.updated_at = datetime.now()
        else:
            # 创建新记录
            info = CompanyInvoiceInfoDB(
                id=str(uuid.uuid4()),
                user_id=user_id,
                company_name=company_name,
                tax_id=tax_id,
                company_address=company_address,
                company_phone=company_phone,
                bank_name=bank_name,
                bank_account=bank_account,
                receiver_email=receiver_email,
                receiver_address=receiver_address,
                receiver_phone=receiver_phone,
                invoice_type_preference=invoice_type_preference,
            )
            self.db.add(info)

        self.db.commit()
        self.db.refresh(info)

        logger.info(f"保存企业发票信息：user_id={user_id}, company_name={company_name}")

        return info

    def get_company_info(self, user_id: str) -> Optional[CompanyInvoiceInfoDB]:
        """获取企业发票信息"""
        return self.db.query(CompanyInvoiceInfoDB).filter(
            CompanyInvoiceInfoDB.user_id == user_id
        ).first()

    # ==================== 发票申请与开具 ====================

    def request_invoice(
        self,
        user_id: str,
        order_id: str,
        invoice_type: str = "electronic",
        invoice_title: str = None,
        tax_id: str = None,
        receiver_name: str = None,
        receiver_phone: str = None,
        receiver_address: str = None,
        receiver_email: str = None,
        notes: str = None,
    ) -> InvoiceDB:
        """
        申请发票

        Args:
            user_id: 用户 ID
            order_id: 订单 ID
            invoice_type: 发票类型 (electronic/paper)
            invoice_title: 发票抬头
            tax_id: 税号
            receiver_name: 收件人姓名
            receiver_phone: 收件人电话
            receiver_address: 收件地址
            receiver_email: 电子发票邮箱
            notes: 备注

        Returns:
            InvoiceDB: 发票对象
        """
        # 检查订单是否存在且已支付
        order = self.db.query(OrderDB).filter(OrderDB.id == order_id).first()
        if not order:
            raise ValueError(f"订单不存在：{order_id}")

        if order.status.value != "paid":
            raise ValueError(f"订单未支付，无法申请发票")

        # 检查是否已开具发票
        existing = self.db.query(InvoiceDB).filter(
            InvoiceDB.order_id == order_id
        ).first()
        if existing:
            raise ValueError(f"该订单已开具发票")

        # 如果没有提供发票抬头，使用订单中的信息
        if not invoice_title:
            invoice_title = order.invoice_title or "个人"
        if not tax_id:
            tax_id = order.invoice_tax_id or ""

        # 获取企业发票信息（如果有）
        company_info = self.get_company_info(user_id)
        if company_info and not receiver_email:
            receiver_email = company_info.receiver_email
        if company_info and not receiver_address and invoice_type == "paper":
            receiver_address = company_info.receiver_address

        # 生成发票号码
        invoice_no = self._generate_invoice_no()

        # 计算税额
        amount = order.paid_amount
        tax_amount = amount * self.TAX_RATE
        total_amount = amount + tax_amount

        # 创建发票记录
        invoice = InvoiceDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            order_id=order_id,
            invoice_no=invoice_no,
            invoice_type=invoice_type,
            invoice_title=invoice_title,
            tax_id=tax_id,
            amount=amount,
            tax_amount=tax_amount,
            total_amount=total_amount,
            receiver_name=receiver_name,
            receiver_phone=receiver_phone,
            receiver_address=receiver_address,
            receiver_email=receiver_email,
            status=InvoiceStatus.PENDING,
            notes=notes,
        )

        self.db.add(invoice)
        self.db.commit()
        self.db.refresh(invoice)

        logger.info(f"申请发票：invoice_no={invoice_no}, user_id={user_id}, type={invoice_type}")

        return invoice

    def issue_invoice(self, invoice_id: str, invoice_url: str = None) -> InvoiceDB:
        """
        开具发票

        Args:
            invoice_id: 发票 ID
            invoice_url: 电子发票文件 URL（可选）

        Returns:
            InvoiceDB: 发票对象
        """
        invoice = self.db.query(InvoiceDB).filter(InvoiceDB.id == invoice_id).first()
        if not invoice:
            raise ValueError(f"发票不存在：{invoice_id}")

        if invoice.status != InvoiceStatus.PENDING:
            raise ValueError(f"发票状态不允许开具：{invoice.status.value}")

        invoice.status = InvoiceStatus.ISSUED
        invoice.issued_at = datetime.now()
        if invoice_url:
            invoice.invoice_url = invoice_url

        self.db.commit()
        self.db.refresh(invoice)

        logger.info(f"发票已开具：invoice_no={invoice.invoice_no}")

        return invoice

    def deliver_invoice(self, invoice_id: str) -> InvoiceDB:
        """
        交付发票

        Args:
            invoice_id: 发票 ID

        Returns:
            InvoiceDB: 发票对象
        """
        invoice = self.db.query(InvoiceDB).filter(InvoiceDB.id == invoice_id).first()
        if not invoice:
            raise ValueError(f"发票不存在：{invoice_id}")

        if invoice.status != InvoiceStatus.ISSUED:
            raise ValueError(f"发票未开具，无法交付")

        # 模拟交付（实际应发送邮件或短信）
        if invoice.invoice_type == "electronic" and invoice.receiver_email:
            # 发送电子发票邮件
            logger.info(f"发送电子发票到：{invoice.receiver_email}")
            invoice.delivery_status = "sent"
        elif invoice.invoice_type == "paper" and invoice.receiver_address:
            # 安排纸质发票邮寄
            logger.info(f"安排纸质发票邮寄到：{invoice.receiver_address}")
            invoice.delivery_status = "sent"

        invoice.status = InvoiceStatus.DELIVERED
        invoice.delivered_at = datetime.now()

        self.db.commit()
        self.db.refresh(invoice)

        logger.info(f"发票已交付：invoice_no={invoice.invoice_no}")

        return invoice

    def cancel_invoice(self, invoice_id: str, reason: str) -> InvoiceDB:
        """
        取消发票

        Args:
            invoice_id: 发票 ID
            reason: 取消原因

        Returns:
            InvoiceDB: 发票对象
        """
        invoice = self.db.query(InvoiceDB).filter(InvoiceDB.id == invoice_id).first()
        if not invoice:
            raise ValueError(f"发票不存在：{invoice_id}")

        if invoice.status == InvoiceStatus.DELIVERED:
            raise ValueError(f"发票已交付，无法取消")

        invoice.status = InvoiceStatus.CANCELLED
        invoice.notes = f"{invoice.notes or ''} [取消原因：{reason}]"

        self.db.commit()
        self.db.refresh(invoice)

        logger.info(f"发票已取消：invoice_no={invoice.invoice_no}, reason={reason}")

        return invoice

    # ==================== 发票查询 ====================

    def get_invoice(self, invoice_id: str) -> Optional[InvoiceDB]:
        """获取发票详情"""
        return self.db.query(InvoiceDB).filter(InvoiceDB.id == invoice_id).first()

    def get_invoice_by_no(self, invoice_no: str) -> Optional[InvoiceDB]:
        """通过发票号码获取发票"""
        return self.db.query(InvoiceDB).filter(InvoiceDB.invoice_no == invoice_no).first()

    def get_user_invoices(
        self,
        user_id: str,
        status: str = None,
        limit: int = 50,
    ) -> List[InvoiceDB]:
        """获取用户发票列表"""
        query = self.db.query(InvoiceDB).filter(InvoiceDB.user_id == user_id)

        if status:
            query = query.filter(InvoiceDB.status == InvoiceStatus(status))

        return query.order_by(InvoiceDB.created_at.desc()).limit(limit).all()

    def get_order_invoice(self, order_id: str) -> Optional[InvoiceDB]:
        """获取订单的发票"""
        return self.db.query(InvoiceDB).filter(
            InvoiceDB.order_id == order_id
        ).first()

    # ==================== 工具方法 ====================

    def _generate_invoice_no(self) -> str:
        """生成发票号码"""
        timestamp = datetime.now().strftime("%Y%m%d")
        unique_id = uuid.uuid4().hex[:6]
        return f"INV{timestamp}{unique_id}"


# 全局单例
def get_invoice_service(db: Session) -> InvoiceService:
    """获取发票服务实例"""
    return InvoiceService(db)
