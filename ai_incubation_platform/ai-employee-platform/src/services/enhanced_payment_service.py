"""
增强支付服务
整合第三方支付网关，提供统一的支付接口
"""
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import uuid
import json

from models.db_models import (
    PaymentTransactionDB, PaymentMethodEnum, PaymentStatusEnum,
    InvoiceDB, OrderDB, WalletDB, TenantDB
)
from services.wallet_payment_service import WalletService, PaymentService
from services.payment_gateway import (
    PaymentChannel, PaymentGatewayFactory,
    AlipayGateway, WechatPayGateway, StripeGateway
)
from config.settings import settings
from config.logging_config import get_logger

logger = get_logger(__name__)


class EnhancedPaymentService:
    """
    增强支付服务

    支持多种支付渠道:
    - 支付宝 (WAP/扫码/APP)
    - 微信支付 (JSAPI/扫码/H5)
    - Stripe (信用卡/支付宝国际)
    - 钱包余额
    """

    def __init__(self, db: Session, sandbox: bool = True):
        """
        初始化支付服务

        Args:
            db: 数据库会话
            sandbox: 是否使用沙箱环境
        """
        self.db = db
        self.sandbox = sandbox
        self.wallet_service = WalletService(db)
        self.base_payment_service = PaymentService(db)

    def create_payment_order(
        self,
        tenant_id: str,
        user_id: str,
        amount: float,
        channel: str,
        method: str,
        subject: str,
        order_id: Optional[str] = None,
        invoice_id: Optional[str] = None,
        extra_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        创建支付订单

        Args:
            tenant_id: 租户 ID
            user_id: 用户 ID
            amount: 金额
            channel: 支付渠道 (alipay/wechat_pay/stripe)
            method: 支付方式 (alipay_wap/alipay_qr/wechat_jsapi/wechat_native/stripe_card)
            subject: 订单标题
            order_id: 关联订单 ID (可选)
            invoice_id: 关联发票 ID (可选)
            extra_params: 额外参数

        Returns:
            {
                "success": True,
                "payment_id": "支付交易 ID",
                "payment_url": "支付链接",
                "qr_code": "二维码链接 (扫码支付)",
                "client_secret": "Stripe client_secret",
            }
        """
        try:
            # 1. 创建支付交易记录
            payment = PaymentTransactionDB(
                tenant_id=tenant_id,
                user_id=user_id,
                order_id=order_id,
                invoice_id=invoice_id,
                amount=amount,
                payment_method=PaymentMethodEnum(method),
                status=PaymentStatusEnum.PENDING,
                payment_data={
                    "channel": channel,
                    "method": method,
                    "subject": subject,
                }
            )
            self.db.add(payment)
            self.db.commit()
            self.db.refresh(payment)

            # 2. 根据渠道调用对应网关
            if channel == "alipay":
                result = self._create_alipay_payment(payment, amount, subject, method, extra_params or {})
            elif channel == "wechat_pay":
                result = self._create_wechat_payment(payment, amount, subject, method, extra_params or {})
            elif channel == "stripe":
                result = self._create_stripe_payment(payment, amount, subject, extra_params or {})
            elif channel == "balance":
                result = self._create_balance_payment(payment, amount)
            else:
                raise ValueError(f"Unsupported payment channel: {channel}")

            # 3. 更新支付交易记录
            if result.get("success"):
                payment.payment_data.update({
                    k: v for k, v in result.items()
                    if k not in ["success", "payment_url", "qr_code", "client_secret"]
                })
                payment.status = PaymentStatusEnum.PROCESSING
                self.db.commit()

                logger.info(f"Created payment order: {payment.id}, channel={channel}, amount={amount}")
            else:
                payment.status = PaymentStatusEnum.FAILED
                payment.error_message = result.get("error", "Unknown error")
                self.db.commit()

            return {
                "success": result.get("success", False),
                "payment_id": payment.id,
                **result
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create payment order: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    def _create_alipay_payment(
        self,
        payment: PaymentTransactionDB,
        amount: float,
        subject: str,
        method: str,
        extra_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """创建支付宝支付"""
        gateway = AlipayGateway(sandbox=self.sandbox)

        # 映射支付方式
        method_map = {
            "alipay_wap": "alipay.trade.wap.pay",
            "alipay_qr": "alipay.trade.precreate",
            "alipay_app": "alipay.trade.app.pay",
        }
        api_method = method_map.get(method, "alipay.trade.wap.pay")

        result = gateway.create_payment(
            order_id=payment.id,
            amount=amount,
            subject=subject,
            method=api_method,
            return_url=extra_params.get("return_url", ""),
        )

        return result

    def _create_wechat_payment(
        self,
        payment: PaymentTransactionDB,
        amount: float,
        subject: str,
        method: str,
        extra_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """创建微信支付"""
        gateway = WechatPayGateway(sandbox=self.sandbox)

        # 映射支付方式
        method_map = {
            "wechat_native": "native",
            "wechat_jsapi": "jsapi",
            "wechat_app": "app",
            "wechat_h5": "h5",
        }
        api_method = method_map.get(method, "native")

        # 微信支付金额单位为分
        amount_cents = int(amount * 100)

        result = gateway.create_payment(
            order_id=payment.id,
            amount=amount_cents,
            subject=subject,
            method=api_method,
            **extra_params
        )

        return result

    def _create_stripe_payment(
        self,
        payment: PaymentTransactionDB,
        amount: float,
        subject: str,
        extra_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """创建 Stripe 支付"""
        gateway = StripeGateway(sandbox=self.sandbox)

        # Stripe 金额单位为分
        amount_cents = int(amount * 100)
        currency = extra_params.get("currency", "cny")

        result = gateway.create_payment(
            order_id=payment.id,
            amount=amount_cents,
            subject=subject,
            currency=currency,
            **extra_params
        )

        return result

    def _create_balance_payment(
        self,
        payment: PaymentTransactionDB,
        amount: float
    ) -> Dict[str, Any]:
        """余额支付"""
        tenant_id = payment.tenant_id

        # 检查余额
        wallet = self.wallet_service.get_wallet(tenant_id)
        if not wallet or wallet.balance < amount:
            return {
                "success": False,
                "error": "Insufficient balance"
            }

        # 扣款
        if self.wallet_service.deduct_wallet(tenant_id, amount):
            payment.status = PaymentStatusEnum.SUCCESS
            payment.third_party_transaction_id = f"balance_{uuid.uuid4()}"

            # 处理支付成功后逻辑
            self._handle_payment_success(payment)

            return {
                "success": True,
                "transaction_id": payment.third_party_transaction_id
            }
        else:
            return {
                "success": False,
                "error": "Failed to deduct balance"
            }

    def handle_payment_callback(
        self,
        channel: str,
        data: Dict[str, Any],
        signature: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        处理支付回调

        Args:
            channel: 支付渠道
            data: 回调数据
            signature: 签名

        Returns:
            (是否成功，响应消息)
        """
        try:
            # 1. 验证签名
            if channel == "alipay":
                gateway = AlipayGateway(sandbox=self.sandbox)
                success, message = gateway.verify_callback(data)
                order_id = data.get("out_trade_no")
            elif channel == "wechat_pay":
                gateway = WechatPayGateway(sandbox=self.sandbox)
                # 微信支付 v3 需要解析回调体
                success, message = gateway.verify_callback({
                    "signature": signature,
                    "body": json.dumps(data)
                })
                order_id = data.get("out_trade_no")
            elif channel == "stripe":
                gateway = StripeGateway(sandbox=self.sandbox)
                success, message = gateway.verify_callback(data, signature)
                order_id = data.get("data", {}).get("object", {}).get("metadata", {}).get("order_id")
            else:
                return False, f"Unsupported channel: {channel}"

            if not success:
                logger.warning(f"Payment callback verification failed: {channel}, {message}")
                return False, message

            # 2. 查找支付交易
            payment = self.base_payment_service.get_payment(order_id)
            if not payment:
                logger.warning(f"Payment not found: {order_id}")
                return False, "Payment not found"

            # 3. 更新支付状态
            if payment.status != PaymentStatusEnum.PROCESSING:
                logger.warning(f"Payment already processed: {order_id}, status={payment.status}")
                return True, "Already processed"

            # 4. 处理支付成功
            payment.status = PaymentStatusEnum.SUCCESS
            if channel == "alipay":
                payment.third_party_transaction_id = data.get("trade_no")
            elif channel == "wechat_pay":
                payment.third_party_transaction_id = data.get("transaction_id")
            elif channel == "stripe":
                payment.third_party_transaction_id = data.get("data", {}).get("object", {}).get("id")

            self._handle_payment_success(payment)

            logger.info(f"Payment callback processed successfully: {order_id}")
            return True, "success"

        except Exception as e:
            logger.error(f"Failed to process payment callback: {e}", exc_info=True)
            return False, str(e)

    def _handle_payment_success(self, payment: PaymentTransactionDB):
        """处理支付成功"""
        # 更新订单状态
        if payment.order_id:
            order = self.db.query(OrderDB).filter(OrderDB.id == payment.order_id).first()
            if order and order.status.value == "pending":
                order.status = OrderDB.status.property.columns[0].type.enum_class.CONFIRMED
                order.confirmed_at = datetime.now()

        # 更新发票状态
        if payment.invoice_id:
            invoice = self.db.query(InvoiceDB).filter(InvoiceDB.id == payment.invoice_id).first()
            if invoice:
                invoice.paid_amount = payment.amount
                invoice.payment_status = PaymentStatusEnum.SUCCESS
                invoice.status = InvoiceDB.status.property.columns[0].type.enum_class.PAID
                invoice.paid_at = datetime.now()

        self.db.commit()
        logger.info(f"Payment success handled: {payment.id}")

    def query_payment_status(self, payment_id: str) -> Dict[str, Any]:
        """查询支付状态"""
        payment = self.base_payment_service.get_payment(payment_id)
        if not payment:
            return {"success": False, "error": "Payment not found"}

        # 如果是第三方支付，查询第三方状态
        if payment.payment_method.value in ["alipay_wap", "alipay_qr", "alipay_app"]:
            gateway = AlipayGateway(sandbox=self.sandbox)
            result = gateway.query_payment(payment_id)
        elif payment.payment_method.value in ["wechat_native", "wechat_jsapi", "wechat_app", "wechat_h5"]:
            gateway = WechatPayGateway(sandbox=self.sandbox)
            result = gateway.query_payment(payment_id)
        elif payment.payment_method.value in ["stripe_card", "stripe_alipay"]:
            gateway = StripeGateway(sandbox=self.sandbox)
            result = gateway.query_payment(payment.third_party_transaction_id or payment_id)
        else:
            result = {"success": True, "status": payment.status.value}

        return {
            "payment_id": payment_id,
            "amount": payment.amount,
            "status": payment.status.value,
            "third_party_status": result.get("trade_status") or result.get("status"),
            **result
        }

    def refund_payment(
        self,
        payment_id: str,
        amount: Optional[float] = None,
        reason: str = ""
    ) -> Dict[str, Any]:
        """
        退款

        Args:
            payment_id: 支付交易 ID
            amount: 退款金额 (None 表示全额退款)
            reason: 退款原因

        Returns:
            {
                "success": True,
                "refund_id": "退款 ID",
                "refund_amount": 100.00
            }
        """
        payment = self.base_payment_service.get_payment(payment_id)
        if not payment:
            return {"success": False, "error": "Payment not found"}

        if payment.status != PaymentStatusEnum.SUCCESS:
            return {"success": False, "error": "Payment not successful"}

        # 默认全额退款
        refund_amount = amount or payment.amount

        # 调用对应网关退款
        if payment.payment_method.value in ["alipay_wap", "alipay_qr", "alipay_app"]:
            gateway = AlipayGateway(sandbox=self.sandbox)
            result = gateway.refund(
                transaction_id=payment.third_party_transaction_id or payment_id,
                amount=refund_amount,
                reason=reason
            )
        elif payment.payment_method.value in ["wechat_native", "wechat_jsapi", "wechat_app", "wechat_h5"]:
            gateway = WechatPayGateway(sandbox=self.sandbox)
            # 微信支付金额单位为分
            result = gateway.refund(
                transaction_id=payment.third_party_transaction_id or payment_id,
                amount=int(refund_amount * 100),
                reason=reason
            )
        elif payment.payment_method.value in ["stripe_card", "stripe_alipay"]:
            gateway = StripeGateway(sandbox=self.sandbox)
            result = gateway.refund(
                payment_intent_id=payment.third_party_transaction_id or payment_id,
                amount=int(refund_amount * 100) if amount else None,
                reason=reason
            )
        elif payment.payment_method.value == "balance":
            # 余额支付，直接退回
            if self.wallet_service.recharge_wallet(payment.tenant_id, refund_amount):
                result = {"success": True, "refund_amount": refund_amount}
            else:
                result = {"success": False, "error": "Failed to refund"}
        else:
            return {"success": False, "error": "Unsupported payment method"}

        if result.get("success"):
            # 更新支付状态
            if amount and amount < payment.amount:
                payment.status = PaymentStatusEnum.REFUNDED  # 部分退款
            else:
                payment.status = PaymentStatusEnum.REFUNDED  # 全额退款

            payment.payment_data["refund_info"] = {
                "refund_id": result.get("refund_id") or result.get("refund_trade_no"),
                "refund_amount": refund_amount,
                "refund_reason": reason,
                "refunded_at": datetime.now().isoformat()
            }
            self.db.commit()

        return result

    def list_payments(
        self,
        tenant_id: str,
        status: Optional[PaymentStatusEnum] = None,
        channel: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[PaymentTransactionDB], int]:
        """列出支付记录"""
        query = self.db.query(PaymentTransactionDB).filter(
            PaymentTransactionDB.tenant_id == tenant_id
        )

        if status:
            query = query.filter(PaymentTransactionDB.status == status)

        if start_date:
            query = query.filter(PaymentTransactionDB.created_at >= start_date)

        if end_date:
            query = query.filter(PaymentTransactionDB.created_at <= end_date)

        total = query.count()
        payments = query.order_by(PaymentTransactionDB.created_at.desc()).offset(offset).limit(limit).all()

        return payments, total
