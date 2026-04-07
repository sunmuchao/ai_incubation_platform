"""
支付 API 端点
提供支付宝、微信支付、Stripe 等支付渠道的接口
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Query, Body
from fastapi.responses import JSONResponse, HTMLResponse
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field

from config.database import get_db
from config.settings import settings
from middleware.auth import require_auth, get_current_user
from services.enhanced_payment_service import EnhancedPaymentService
from models.db_models import PaymentStatusEnum
from config.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/payment", tags=["支付"])


# ==================== 请求/响应模型 ====================

class PaymentCreateRequest(BaseModel):
    """创建支付请求"""
    amount: float = Field(..., gt=0, description="支付金额")
    channel: str = Field(..., description="支付渠道：alipay/wechat_pay/stripe/balance")
    method: str = Field(..., description="支付方式：alipay_wap/alipay_qr/wechat_native/wechat_jsapi/stripe_card")
    subject: str = Field(..., max_length=256, description="订单标题")
    order_id: Optional[str] = Field(None, description="关联订单 ID")
    invoice_id: Optional[str] = Field(None, description="关联发票 ID")
    return_url: Optional[str] = Field(None, description="支付成功返回 URL")
    extra_params: Optional[Dict[str, Any]] = Field(default_factory=dict, description="额外参数")


class PaymentCreateResponse(BaseModel):
    """创建支付响应"""
    success: bool
    payment_id: str
    payment_url: Optional[str] = None
    qr_code: Optional[str] = None
    form_html: Optional[str] = None
    client_secret: Optional[str] = None
    error: Optional[str] = None


class PaymentQueryResponse(BaseModel):
    """支付查询响应"""
    payment_id: str
    amount: float
    status: str
    channel: str
    third_party_status: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]


class RefundRequest(BaseModel):
    """退款请求"""
    amount: Optional[float] = Field(None, gt=0, description="退款金额 (None 表示全额退款)")
    reason: str = Field(default="", max_length=500, description="退款原因")


# ==================== 支付创建 ====================

@router.post("/create", response_model=PaymentCreateResponse)
async def create_payment(
    request: PaymentCreateRequest,
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(require_auth)
):
    """
    创建支付订单

    支持以下支付渠道:
    - **支付宝**: WAP 支付、扫码支付、APP 支付
    - **微信支付**: 扫码支付、JSAPI 支付、H5 支付
    - **Stripe**: 信用卡支付 (国际)
    - **余额支付**: 使用钱包余额

    返回结果说明:
    - `payment_url`: 支付宝 WAP/Stripe 支付链接
    - `qr_code`: 支付宝/微信扫码支付二维码链接
    - `form_html`: 支付宝表单 HTML (自动提交)
    - `client_secret`: Stripe PaymentIntent 密钥
    """
    service = EnhancedPaymentService(db, sandbox=not settings.is_production())

    # 准备额外参数
    extra_params = request.extra_params or {}
    if request.return_url:
        extra_params["return_url"] = request.return_url

    # 创建支付
    result = service.create_payment_order(
        tenant_id=user["tenant_id"],
        user_id=user["user_id"],
        amount=request.amount,
        channel=request.channel,
        method=request.method,
        subject=request.subject,
        order_id=request.order_id,
        invoice_id=request.invoice_id,
        extra_params=extra_params
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to create payment")
        )

    return PaymentCreateResponse(**result)


@router.post("/create-alipay-wap")
async def create_alipay_wap(
    amount: float = Query(..., gt=0, description="金额"),
    subject: str = Query(..., description="标题"),
    order_id: Optional[str] = Query(None, description="订单 ID"),
    return_url: Optional[str] = Query(None, description="返回 URL"),
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(require_auth)
):
    """创建支付宝 WAP 支付 (快捷返回 HTML 表单)"""
    service = EnhancedPaymentService(db, sandbox=not settings.is_production())

    result = service.create_payment_order(
        tenant_id=user["tenant_id"],
        user_id=user["user_id"],
        amount=amount,
        channel="alipay",
        method="alipay_wap",
        subject=subject,
        order_id=order_id,
        extra_params={"return_url": return_url}
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to create payment")
        )

    # 返回 HTML 表单
    return HTMLResponse(content=result.get("form_html", ""))


@router.post("/create-wechat-native")
async def create_wechat_native(
    amount: float = Query(..., gt=0, description="金额"),
    subject: str = Query(..., description="标题"),
    order_id: Optional[str] = Query(None, description="订单 ID"),
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(require_auth)
):
    """创建微信扫码支付"""
    service = EnhancedPaymentService(db, sandbox=not settings.is_production())

    result = service.create_payment_order(
        tenant_id=user["tenant_id"],
        user_id=user["user_id"],
        amount=amount,
        channel="wechat_pay",
        method="wechat_native",
        subject=subject,
        order_id=order_id
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to create payment")
        )

    return {
        "success": True,
        "payment_id": result["payment_id"],
        "code_url": result.get("qr_code"),
    }


# ==================== 支付查询 ====================

@router.get("/{payment_id}", response_model=PaymentQueryResponse)
async def query_payment(
    payment_id: str,
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(require_auth)
):
    """查询支付状态"""
    from models.db_models import PaymentTransactionDB

    payment = db.query(PaymentTransactionDB).filter(
        PaymentTransactionDB.id == payment_id,
        PaymentTransactionDB.tenant_id == user["tenant_id"]
    ).first()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )

    # 如果是处理中，查询第三方支付状态
    service = EnhancedPaymentService(db, sandbox=not settings.is_production())
    if payment.status == PaymentStatusEnum.PROCESSING:
        third_party_result = service.query_payment_status(payment_id)
        third_party_status = third_party_result.get("third_party_status") or third_party_result.get("status")
    else:
        third_party_status = None

    return PaymentQueryResponse(
        payment_id=payment.id,
        amount=payment.amount,
        status=payment.status.value,
        channel=payment.payment_data.get("channel", "unknown"),
        third_party_status=third_party_status,
        created_at=payment.created_at,
        updated_at=payment.updated_at
    )


@router.get("/{payment_id}/qr")
async def get_payment_qr(
    payment_id: str,
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(require_auth)
):
    """获取支付二维码 (用于扫码支付)"""
    from models.db_models import PaymentTransactionDB
    import qrcode
    import io
    import base64
    from fastapi.responses import PNGResponse

    payment = db.query(PaymentTransactionDB).filter(
        PaymentTransactionDB.id == payment_id,
        PaymentTransactionDB.tenant_id == user["tenant_id"]
    ).first()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )

    qr_code_data = payment.payment_data.get("qr_code")
    if not qr_code_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This payment does not have a QR code"
        )

    # 生成二维码图片
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(qr_code_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    # 转换为 PNG 格式
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    return PNGResponse(img_bytes.getvalue())


# ==================== 支付回调 ====================

@router.post("/callback/alipay")
async def alipay_callback(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    支付宝异步通知回调

    支付宝会 POST form-data 格式的数据到此接口
    """
    form_data = await request.form()
    data = dict(form_data)

    service = EnhancedPaymentService(db, sandbox=not settings.is_production())
    success, message = service.handle_payment_callback("alipay", data)

    if success:
        return Response(content="success", media_type="text/plain")
    else:
        return Response(content=message, media_type="text/plain", status_code=400)


@router.post("/callback/wechat/{payment_id}")
async def wechat_callback(
    payment_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    微信支付异步通知回调

    微信支付 v3 使用 JSON 格式
    """
    try:
        data = await request.json()
        signature = request.headers.get("Wechatpay-Signature", "")
        nonce = request.headers.get("Wechatpay-Nonce", "")
        timestamp = request.headers.get("Wechatpay-Timestamp", "")

        service = EnhancedPaymentService(db, sandbox=not settings.is_production())

        # 验证签名
        from services.payment_gateway import WechatPayGateway
        gateway = WechatPayGateway(sandbox=not settings.is_production())

        # 构建签名字符串
        sign_message = f"{timestamp}\n{nonce}\n{json.dumps(data)}\n"
        # 验证逻辑在 service 中处理
        success, message = service.handle_payment_callback("wechat_pay", data, signature)

        if success:
            return JSONResponse({"code": "SUCCESS", "message": "OK"})
        else:
            return JSONResponse({"code": "FAIL", "message": message}, status_code=400)

    except Exception as e:
        logger.error(f"Wechat callback error: {e}", exc_info=True)
        return JSONResponse({"code": "FAIL", "message": str(e)}, status_code=500)


@router.post("/callback/stripe")
async def stripe_callback(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Stripe Webhook 回调
    """
    body = await request.body()
    sig_header = request.headers.get("Stripe-Signature", "")

    service = EnhancedPaymentService(db, sandbox=not settings.is_production())
    success, message = service.handle_payment_callback("stripe", body, sig_header)

    if success:
        return JSONResponse({"status": "success"})
    else:
        return JSONResponse({"status": "failed", "error": message}, status_code=400)


# ==================== 退款 ====================

@router.post("/{payment_id}/refund")
async def refund_payment(
    payment_id: str,
    refund_request: RefundRequest,
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(require_auth)
):
    """
    退款

    - 支持全额退款和部分退款
    - 余额支付即时到账
    - 第三方支付 1-3 个工作日到账
    """
    from models.db_models import PaymentTransactionDB

    # 验证支付归属
    payment = db.query(PaymentTransactionDB).filter(
        PaymentTransactionDB.id == payment_id,
        PaymentTransactionDB.tenant_id == user["tenant_id"]
    ).first()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )

    service = EnhancedPaymentService(db, sandbox=not settings.is_production())
    result = service.refund_payment(
        payment_id=payment_id,
        amount=refund_request.amount,
        reason=refund_request.reason
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Refund failed")
        )

    return result


# ==================== 支付记录列表 ====================

@router.get("/list")
async def list_payments(
    status: Optional[str] = Query(None, description="支付状态"),
    channel: Optional[str] = Query(None, description="支付渠道"),
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(require_auth)
):
    """获取支付记录列表"""
    offset = (page - 1) * page_size

    status_enum = PaymentStatusEnum(status) if status else None

    service = EnhancedPaymentService(db, sandbox=not settings.is_production())
    payments, total = service.list_payments(
        tenant_id=user["tenant_id"],
        status=status_enum,
        channel=channel,
        start_date=start_date,
        end_date=end_date,
        limit=page_size,
        offset=offset
    )

    return {
        "items": [
            {
                "payment_id": p.id,
                "amount": p.amount,
                "status": p.status.value,
                "channel": p.payment_data.get("channel", "unknown"),
                "method": p.payment_method.value,
                "created_at": p.created_at,
            }
            for p in payments
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
