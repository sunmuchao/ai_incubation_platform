"""
真实支付渠道 API。

支持 Stripe、支付宝、微信支付等多种支付渠道。
"""
import logging
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Header, Query, Body
from pydantic import BaseModel, Field

from models.payment import PaymentRequest, PayoutRequest
from services.real_payment_service import (
    PaymentChannel,
    real_payment_service,
)
from services.payment_service import payment_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/payment/real", tags=["真实支付渠道"])


# ============ 请求模型 ============

class CreatePaymentRequest(BaseModel):
    """创建支付订单请求。"""
    user_id: str
    amount: float = Field(..., gt=0, description="支付金额")
    currency: str = Field(default="CNY", description="货币代码")
    channel: str = Field(default="platform_wallet", description="支付渠道")
    description: Optional[str] = Field(None, description="支付描述")
    payment_method: Optional[str] = Field(None, description="支付方式")


class CreatePayoutRequest(BaseModel):
    """创建提现请求。"""
    worker_id: str
    amount: float = Field(..., gt=0, description="提现金额")
    payout_method: str = Field(default="bank_transfer", description="提现方式")
    bank_account: Optional[str] = Field(None, description="银行账户")
    alipay_account: Optional[str] = Field(None, description="支付宝账号")
    wechat_account: Optional[str] = Field(None, description="微信账号")


class RefundRequest(BaseModel):
    """退款请求。"""
    transaction_id: str
    amount: Optional[float] = Field(None, gt=0, description="退款金额（默认全额）")
    reason: Optional[str] = Field(None, description="退款原因")


class PaymentIntentConfirmRequest(BaseModel):
    """支付确认请求（用于 Stripe 等）。"""
    payment_intent_id: str
    payment_method_id: str


# ============ 响应模型 ============

class PaymentResponse(BaseModel):
    """支付响应。"""
    transaction_id: str
    status: str
    amount: float
    channel: str
    payment_url: Optional[str] = None
    client_secret: Optional[str] = None  # Stripe client_secret
    qr_code: Optional[str] = None  # 支付宝/微信二维码
    message: str = ""


class PayoutResponse(BaseModel):
    """提现响应。"""
    transaction_id: str
    status: str
    amount: float
    payout_method: str
    estimated_arrival: str
    message: str = ""


class RefundResponse(BaseModel):
    """退款响应。"""
    refund_id: str
    status: str
    amount: float
    message: str = ""


class WalletBalanceResponse(BaseModel):
    """钱包余额响应。"""
    user_id: str
    balance: float
    frozen_balance: float
    currency: str


# ============ API 端点 ============

@router.post("/create", response_model=PaymentResponse)
async def create_payment(request: CreatePaymentRequest):
    """
    创建支付订单。

    支持的支付渠道：
    - platform_wallet: 平台钱包（内部结算，即时到账）
    - stripe: Stripe 信用卡支付
    - alipay: 支付宝扫码支付
    - wechat_pay: 微信扫码支付

    返回支付 URL 或二维码，用户完成支付后平台会收到回调。
    """
    try:
        # 解析支付渠道
        channel_map = {
            "platform_wallet": PaymentChannel.PLATFORM_WALLET,
            "stripe": PaymentChannel.STRIPE,
            "alipay": PaymentChannel.ALIPAY,
            "wechat_pay": PaymentChannel.WECHAT_PAY,
        }
        channel = channel_map.get(request.channel.lower(), PaymentChannel.PLATFORM_WALLET)

        # 创建支付请求
        payment_request = PaymentRequest(
            user_id=request.user_id,
            amount=request.amount,
            currency=request.currency,
            payment_method=request.payment_method or channel.value,
            description=request.description,
        )

        # 调用支付服务
        tx = await real_payment_service.create_payment(payment_request, channel)

        # 构建响应
        response = PaymentResponse(
            transaction_id=tx.id,
            status=tx.status.value,
            amount=tx.amount,
            channel=channel.value,
            message="支付成功" if tx.status.value == "success" else "等待支付",
        )

        # 根据渠道返回额外信息
        if channel == PaymentChannel.STRIPE:
            # Stripe 返回 client_secret 供前端使用 Elements 确认支付
            response.client_secret = tx.external_transaction_id
            response.message = "请在前端使用 Stripe Elements 完成支付"

        elif channel == PaymentChannel.ALIPAY:
            # 支付宝返回二维码
            response.qr_code = f"alipay://alipayclient/?{tx.id}"
            response.payment_url = f"/api/payment/real/alipay/qr?tx={tx.id}"
            response.message = "请扫描二维码完成支付"

        elif channel == PaymentChannel.WECHAT_PAY:
            # 微信返回二维码 URL
            response.qr_code = f"weixin://wxpay/bizpayurl?pr={tx.id}"
            response.message = "请使用微信扫码支付"

        return response

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Payment creation failed")
        raise HTTPException(status_code=500, detail=f"支付创建失败：{str(e)}")


@router.post("/payout", response_model=PayoutResponse)
async def create_payout(request: CreatePayoutRequest):
    """
    创建提现申请。

    工人可以将钱包余额提现到：
    - 银行账户
    - 支付宝
    - 微信

    提现申请审核后会自动打款。
    """
    try:
        # 构建提现请求
        payout_request = PayoutRequest(
            worker_id=request.worker_id,
            amount=request.amount,
            payout_method=request.payout_method,
        )

        # 调用支付服务
        tx = await real_payment_service.process_payout(payout_request, PaymentChannel.PLATFORM_WALLET)

        # 估算到账时间
        estimated_arrival = "1-3 个工作日"

        return PayoutResponse(
            transaction_id=tx.id,
            status=tx.status.value,
            amount=tx.amount,
            payout_method=request.payout_method,
            estimated_arrival=estimated_arrival,
            message="提现申请已提交",
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Payout creation failed")
        raise HTTPException(status_code=500, detail=f"提现申请失败：{str(e)}")


@router.post("/refund", response_model=RefundResponse)
async def process_refund(request: RefundRequest):
    """
    处理退款。

    支持部分退款和全额退款。
    """
    try:
        success = await real_payment_service.process_refund(
            transaction_id=request.transaction_id,
            amount=request.amount,
            reason=request.reason,
        )

        if not success:
            raise HTTPException(status_code=400, detail="退款失败，交易不存在或状态异常")

        # 获取原交易信息
        tx = payment_service.get_transaction(request.transaction_id)
        refund_amount = request.amount or (tx.amount if tx else 0)

        return RefundResponse(
            refund_id=f"refund_{request.transaction_id}",
            status="success",
            amount=refund_amount,
            message="退款已成功处理",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Refund processing failed")
        raise HTTPException(status_code=500, detail=f"退款失败：{str(e)}")


@router.get("/wallet/{user_id}", response_model=WalletBalanceResponse)
async def get_wallet_balance(user_id: str):
    """获取用户钱包余额。"""
    wallet = payment_service.get_wallet_balance(user_id)
    return WalletBalanceResponse(
        user_id=user_id,
        balance=wallet.balance,
        frozen_balance=wallet.frozen_balance,
        currency=wallet.currency,
    )


@router.post("/stripe/webhook")
async def stripe_webhook(
    request: str,
    stripe_signature: str = Header(None, alias="Stripe-Signature"),
):
    """
    Stripe webhook 回调端点。

    处理以下事件：
    - payment_intent.succeeded: 支付成功
    - payment_intent.payment_failed: 支付失败
    - charge.refunded: 退款完成
    """
    # TODO: 实现 Stripe 签名验证
    # if not real_payment_service.stripe.verify_webhook_signature(
    #     request.encode(), stripe_signature
    # ):
    #     raise HTTPException(status_code=400, detail="Invalid signature")

    logger.info("Stripe webhook received: %s", request[:100])
    # TODO: 解析事件并更新交易状态

    return {"status": "received"}


@router.post("/alipay/notify")
async def alipay_notify(
    request: dict,
    sign: str = Query(..., description="签名"),
):
    """
    支付宝异步通知回调。

    支付宝会在用户支付成功后 POST 通知到此端点。
    """
    # 验证签名
    if not real_payment_service.alipay.verify_notify_signature(request, sign):
        logger.warning("Alipay notify signature verification failed")
        raise HTTPException(status_code=400, detail="Invalid signature")

    # 获取交易号
    trade_no = request.get("trade_no")
    out_trade_no = request.get("out_trade_no")
    trade_status = request.get("trade_status")

    logger.info(
        "Alipay notify: trade_no=%s, out_trade_no=%s, status=%s",
        trade_no, out_trade_no, trade_status
    )

    if trade_status == "TRADE_SUCCESS":
        # 找到对应的交易并确认
        # TODO: 根据 out_trade_no 查找交易
        await real_payment_service.confirm_payment(out_trade_no)

    return {"status": "success"}


@router.post("/wechat/notify")
async def wechat_notify(
    request: dict,
    wechatpay_signature: str = Header(None, alias="Wechatpay-Signature"),
    wechatpay_serial: str = Header(None, alias="Wechatpay-Serial"),
):
    """
    微信支付异步通知回调。
    """
    # 验证签名
    # if not real_payment_service.wechat.verify_notify_signature(
    #     wechatpay_serial, wechatpay_signature, str(request).encode()
    # ):
    #     logger.warning("Wechat notify signature verification failed")
    #     raise HTTPException(status_code=400, detail="Invalid signature")

    logger.info("Wechat notify received: %s", request)
    # TODO: 解析事件并更新交易状态

    return {"status": "success"}


@router.get("/alipay/qr/{transaction_id}")
async def get_alipay_qr(transaction_id: str):
    """获取支付宝支付二维码。"""
    tx = payment_service.get_transaction(transaction_id)
    if not tx:
        raise HTTPException(status_code=404, detail="交易不存在")

    # 返回二维码图片（这里简化为返回 URL）
    qr_url = f"alipay://alipayclient/?{transaction_id}"
    return {
        "transaction_id": transaction_id,
        "qr_url": qr_url,
        "amount": tx.amount,
    }


@router.get("/status/{transaction_id}")
async def get_payment_status(transaction_id: str):
    """获取支付状态。"""
    tx = payment_service.get_transaction(transaction_id)
    if not tx:
        raise HTTPException(status_code=404, detail="交易不存在")

    return {
        "transaction_id": tx.id,
        "status": tx.status.value,
        "amount": tx.amount,
        "currency": tx.currency,
        "payment_method": tx.payment_method,
        "created_at": tx.created_at.isoformat() if tx.created_at else None,
        "completed_at": tx.completed_at.isoformat() if tx.completed_at else None,
        "description": tx.description,
    }
