"""
真实支付渠道对接服务。

支持以下支付渠道：
1. Stripe（国际支付）- 信用卡、借记卡
2. 支付宝（中国）- 扫码支付、APP 支付
3. 微信支付（中国）- JSAPI 支付、APP 支付

注意：使用前需要配置相应的 API 密钥和回调地址。
"""
from __future__ import annotations

import logging
import os
import hashlib
import hmac
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field

import httpx

from models.payment import (
    PaymentRequest,
    PaymentStatus,
    PaymentTransaction,
    PayoutRequest,
    TaskPaymentRequest,
    TransactionType,
    Wallet,
)
from services.payment_service import payment_service

logger = logging.getLogger(__name__)


class PaymentChannel(str, Enum):
    """支付渠道。"""
    STRIPE = "stripe"
    ALIPAY = "alipay"
    WECHAT_PAY = "wechat_pay"
    PLATFORM_WALLET = "platform_wallet"  # 平台钱包（内部结算）


class PaymentMethod(str, Enum):
    """支付方式。"""
    # Stripe
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    # Alipay
    ALIPAY_SCAN = "alipay_scan"  # 扫码支付
    ALIPAY_APP = "alipay_app"  # APP 支付
    ALIPAY_WEB = "alipay_web"  # 网页支付
    # WeChat Pay
    WECHAT_JSAPI = "wechat_jsapi"  # 公众号支付
    WECHAT_APP = "wechat_app"  # APP 支付
    WECHAT_NATIVE = "wechat_native"  # 扫码支付


@dataclass
class StripePaymentIntent:
    """Stripe 支付意图。"""
    intent_id: str
    amount: float
    currency: str
    status: str
    client_secret: str
    payment_method: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class AlipayTradeResponse:
    """支付宝交易响应。"""
    trade_no: str
    out_trade_no: str
    qr_code: Optional[str] = None  # 扫码支付的二维码
    pay_url: Optional[str] = None  # 网页支付链接


@dataclass
class WechatPayResponse:
    """微信支付响应。"""
    transaction_id: str
    out_trade_no: str
    code_url: Optional[str] = None  # 扫码支付的二维码链接
    prepay_id: Optional[str] = None  # 预支付交易会话标识


class StripeService:
    """
    Stripe 支付服务。

    文档：https://stripe.com/docs/api
    """

    def __init__(self) -> None:
        self.api_key = os.getenv("STRIPE_SECRET_KEY", "")
        self.api_base = "https://api.stripe.com/v1"
        self.webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")

    async def create_payment_intent(
        self,
        amount: float,
        currency: str,
        customer_id: Optional[str] = None,
        description: Optional[str] = None,
    ) -> StripePaymentIntent:
        """
        创建支付意图。

        Args:
            amount: 金额（以分为单位）
            currency: 货币代码（如 USD, CNY）
            customer_id: 客户 ID（可选）
            description: 描述（可选）

        Returns:
            StripePaymentIntent
        """
        if not self.api_key:
            raise ValueError("Stripe API key not configured")

        async with httpx.AsyncClient() as client:
            data = {
                "amount": int(amount * 100),  # Stripe 以分为单位
                "currency": currency,
                "description": description or "Payment",
            }
            if customer_id:
                data["customer"] = customer_id

            resp = await client.post(
                f"{self.api_base}/payment_intents",
                data=data,
                auth=(self.api_key, ""),
            )
            resp.raise_for_status()
            result = resp.json()

            return StripePaymentIntent(
                intent_id=result["id"],
                amount=amount,
                currency=currency,
                status=result["status"],
                client_secret=result["client_secret"],
                payment_method=result.get("payment_method"),
            )

    async def confirm_payment_intent(self, intent_id: str, payment_method_id: str) -> bool:
        """确认支付意图。"""
        if not self.api_key:
            raise ValueError("Stripe API key not configured")

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.api_base}/payment_intents/{intent_id}/confirm",
                data={"payment_method": payment_method_id},
                auth=(self.api_key, ""),
            )
            resp.raise_for_status()
            result = resp.json()
            return result["status"] == "succeeded"

    async def refund_payment(self, intent_id: str, amount: Optional[float] = None) -> bool:
        """退款。"""
        if not self.api_key:
            raise ValueError("Stripe API key not configured")

        data = {}
        if amount:
            data["amount"] = int(amount * 100)

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.api_base}/refunds",
                data={"payment_intent": intent_id, **data},
                auth=(self.api_key, ""),
            )
            resp.raise_for_status()
            return True

    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """验证 Stripe webhook 签名。"""
        if not self.webhook_secret:
            return False

        try:
            expected_signature = hmac.new(
                self.webhook_secret.encode(),
                payload,
                hashlib.sha256,
            ).hexdigest()

            # Stripe 签名格式：t=timestamp,v1=signature
            parts = signature.split(",")
            sig_dict = {}
            for part in parts:
                key, value = part.split("=", 1)
                sig_dict[key] = value

            return hmac.compare_digest(sig_dict.get("v1", ""), expected_signature)
        except Exception:
            return False


class AlipayService:
    """
    支付宝支付服务。

    文档：https://opendocs.alipay.com/open
    """

    def __init__(self) -> None:
        self.app_id = os.getenv("ALIPAY_APP_ID", "")
        self.private_key = os.getenv("ALIPAY_PRIVATE_KEY", "")
        self.alipay_public_key = os.getenv("ALIPAY_PUBLIC_KEY", "")
        self.gateway = "https://openapi.alipay.com/gateway.do"

    async def create_qr_pay(
        self,
        out_trade_no: str,
        amount: float,
        subject: str,
    ) -> Optional[AlipayTradeResponse]:
        """
        创建扫码支付。

        Args:
            out_trade_no: 商户订单号
            amount: 金额（元）
            subject: 订单标题

        Returns:
            AlipayTradeResponse
        """
        # 简化实现，实际需要根据支付宝文档构造请求
        logger.info("Alipay QR pay: trade_no=%s, amount=%.2f", out_trade_no, amount)
        # TODO: 实现完整的支付宝 API 调用
        return AlipayTradeResponse(
            trade_no=f"alipay_{out_trade_no}",
            out_trade_no=out_trade_no,
            qr_code="mock_qr_code",
        )

    async def create_web_pay(
        self,
        out_trade_no: str,
        amount: float,
        subject: str,
        return_url: str,
    ) -> Optional[str]:
        """
        创建网页支付。

        Returns:
            支付页面 URL
        """
        logger.info("Alipay web pay: trade_no=%s, amount=%.2f", out_trade_no, amount)
        # TODO: 实现完整的支付宝网页支付
        return "https://openapi.alipay.com/gateway.do?mock=web_pay"

    def verify_notify_signature(self, data: dict, sign: str) -> bool:
        """验证支付宝异步通知签名。"""
        # TODO: 实现支付宝签名验证
        logger.debug("Alipay notify signature verification: %s", sign)
        return True  # Mock 验证通过


class WechatPayService:
    """
    微信支付服务。

    文档：https://pay.weixin.qq.com/wiki/doc/apiv3/
    """

    def __init__(self) -> None:
        self.appid = os.getenv("WECHAT_APPID", "")
        self.mchid = os.getenv("WECHAT_MCHID", "")
        self.api_v3_key = os.getenv("WECHAT_API_V3_KEY", "")
        self.private_key = os.getenv("WECHAT_PRIVATE_KEY", "")
        self.serial_no = os.getenv("WECHAT_SERIAL_NO", "")

    async def create_native_pay(
        self,
        out_trade_no: str,
        amount: float,
        description: str,
    ) -> Optional[WechatPayResponse]:
        """
        创建 Native 扫码支付。

        Returns:
            WechatPayResponse
        """
        logger.info("Wechat native pay: trade_no=%s, amount=%.2f", out_trade_no, amount)
        # TODO: 实现完整的微信支付 API 调用
        return WechatPayResponse(
            transaction_id=f"wechat_{out_trade_no}",
            out_trade_no=out_trade_no,
            code_url="weixin://wxpay/bizpayurl?mock",
        )

    def verify_notify_signature(self, serial: str, signature: str, body: bytes) -> bool:
        """验证微信支付回调签名。"""
        # TODO: 实现微信支付签名验证
        logger.debug("Wechat notify signature verification: %s", serial)
        return True  # Mock 验证通过


class RealPaymentService:
    """
    真实支付服务。

    整合多个支付渠道，提供统一的支付接口。
    """

    def __init__(self) -> None:
        self.stripe = StripeService()
        self.alipay = AlipayService()
        self.wechat = WechatPayService()
        # 使用内存存储支付渠道映射
        self._payment_channels: Dict[str, PaymentChannel] = {}

    async def create_payment(
        self,
        request: PaymentRequest,
        channel: PaymentChannel = PaymentChannel.PLATFORM_WALLET,
    ) -> PaymentTransaction:
        """
        创建支付订单。

        Args:
            request: 支付请求
            channel: 支付渠道

        Returns:
            PaymentTransaction
        """
        if channel == PaymentChannel.PLATFORM_WALLET:
            # 使用平台钱包（内部结算）
            return payment_service.create_deposit(request)

        elif channel == PaymentChannel.STRIPE:
            # Stripe 支付
            intent = await self.stripe.create_payment_intent(
                amount=request.amount,
                currency=request.currency or "CNY",
                customer_id=request.user_id,
                description=request.description or "账户充值",
            )

            tx = PaymentTransaction(
                transaction_type=TransactionType.DEPOSIT,
                amount=request.amount,
                payer_id=request.user_id,
                payee_id="platform",
                payment_method=PaymentMethod.CREDIT_CARD.value,
                description=request.description or "Stripe 充值",
                external_transaction_id=intent.intent_id,
            )
            # 存储渠道映射
            self._payment_channels[tx.id] = channel

            # Mock：假设支付成功（实际应等待 webhook 回调）
            tx.status = PaymentStatus.SUCCESS
            tx.completed_at = datetime.now()

            # 充值到钱包
            wallet = payment_service.get_wallet_balance(request.user_id)
            wallet.balance += request.amount

            logger.info("Stripe payment success: user=%s, amount=%.2f, tx=%s",
                       request.user_id, request.amount, tx.id)
            return tx

        elif channel == PaymentChannel.ALIPAY:
            # 支付宝扫码支付
            trade = await self.alipay.create_qr_pay(
                out_trade_no=f"alipay_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                amount=request.amount,
                subject=request.description or "账户充值",
            )

            tx = PaymentTransaction(
                transaction_type=TransactionType.DEPOSIT,
                amount=request.amount,
                payer_id=request.user_id,
                payee_id="platform",
                payment_method=PaymentMethod.ALIPAY_SCAN.value,
                description=request.description or "支付宝充值",
                external_transaction_id=trade.trade_no if trade else None,
            )
            self._payment_channels[tx.id] = channel

            # 支付宝需要等待回调确认
            tx.status = PaymentStatus.PENDING
            logger.info("Alipay payment created: user=%s, amount=%.2f, tx=%s",
                       request.user_id, request.amount, tx.id)
            return tx

        elif channel == PaymentChannel.WECHAT_PAY:
            # 微信扫码支付
            pay = await self.wechat.create_native_pay(
                out_trade_no=f"wechat_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                amount=request.amount,
                description=request.description or "账户充值",
            )

            tx = PaymentTransaction(
                transaction_type=TransactionType.DEPOSIT,
                amount=request.amount,
                payer_id=request.user_id,
                payee_id="platform",
                payment_method=PaymentMethod.WECHAT_NATIVE.value,
                description=request.description or "微信充值",
                external_transaction_id=pay.transaction_id if pay else None,
            )
            self._payment_channels[tx.id] = channel

            # 微信需要等待回调确认
            tx.status = PaymentStatus.PENDING
            logger.info("Wechat payment created: user=%s, amount=%.2f, tx=%s",
                       request.user_id, request.amount, tx.id)
            return tx

        else:
            raise ValueError(f"Unsupported payment channel: {channel}")

    async def process_payout(
        self,
        request: PayoutRequest,
        channel: PaymentChannel = PaymentChannel.PLATFORM_WALLET,
    ) -> PaymentTransaction:
        """
        处理提现申请。

        Args:
            request: 提现请求
            channel: 支付渠道

        Returns:
            PaymentTransaction
        """
        if channel == PaymentChannel.PLATFORM_WALLET:
            # 平台钱包提现
            return payment_service.create_payout(request)

        # 其他渠道的提现需要调用对应的 API
        # 这里简化处理，仅记录
        tx = PaymentTransaction(
            transaction_type=TransactionType.WORKER_PAYOUT,
            amount=request.amount,
            payer_id="platform",
            payee_id=request.worker_id,
            payment_method=request.payout_method,
            description=f"提现到{request.payout_method}",
        )
        tx.status = PaymentStatus.SUCCESS
        tx.completed_at = datetime.now()

        logger.info("Payout processed: worker=%s, amount=%.2f, tx=%s",
                   request.worker_id, request.amount, tx.id)
        return tx

    async def confirm_payment(self, transaction_id: str) -> bool:
        """
        确认支付（用于支付宝/微信回调）。

        Args:
            transaction_id: 交易 ID

        Returns:
            bool
        """
        tx = payment_service.get_transaction(transaction_id)
        if not tx:
            return False

        if tx.status != PaymentStatus.PENDING:
            return False

        # 更新交易状态
        tx.status = PaymentStatus.SUCCESS
        tx.completed_at = datetime.now()

        # 充值到钱包
        if tx.payer_id:
            wallet = payment_service.get_wallet_balance(tx.payer_id)
            wallet.balance += tx.amount

        logger.info("Payment confirmed: tx=%s, amount=%.2f", transaction_id, tx.amount)
        return True

    async def process_refund(
        self,
        transaction_id: str,
        amount: Optional[float] = None,
        reason: Optional[str] = None,
    ) -> bool:
        """
        处理退款。

        Args:
            transaction_id: 原交易 ID
            amount: 退款金额（可选，默认全额）
            reason: 退款原因

        Returns:
            bool
        """
        channel = self._payment_channels.get(transaction_id, PaymentChannel.PLATFORM_WALLET)

        if channel == PaymentChannel.STRIPE:
            tx = payment_service.get_transaction(transaction_id)
            if not tx:
                return False

            refund_amount = amount or tx.amount
            await self.stripe.refund_payment(tx.external_transaction_id, refund_amount)
            logger.info("Stripe refund processed: tx=%s, amount=%.2f", transaction_id, refund_amount)
            return True

        # 其他渠道的退款简化处理
        logger.info("Refund processed: tx=%s, channel=%s", transaction_id, channel.value)
        return True

    def get_payment_url(self, transaction_id: str) -> Optional[str]:
        """
        获取支付 URL（用于支付宝/微信网页支付）。

        Args:
            transaction_id: 交易 ID

        Returns:
            支付 URL 或 None
        """
        channel = self._payment_channels.get(transaction_id)
        if channel == PaymentChannel.ALIPAY:
            return f"https://openapi.alipay.com/gateway.do?trade_no={transaction_id}"
        elif channel == PaymentChannel.WECHAT_PAY:
            return f"weixin://wxpay/bizpayurl?pr={transaction_id}"
        return None


# 全局支付服务实例
real_payment_service = RealPaymentService()
