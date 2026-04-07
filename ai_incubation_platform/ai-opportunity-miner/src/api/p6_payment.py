"""
P6 - 支付与订单管理 API

提供支付、订单、发票、试用相关的 API 端点
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from config.database import get_db
from services.payment_service import PaymentService, get_payment_service
from services.invoice_service import InvoiceService, get_invoice_service
from services.trial_service import TrialService, get_trial_service
from services.payment_gateway import initialize_payment_gateways

router = APIRouter(prefix="/api/p6", tags=["P6 商用功能"])

# 初始化支付网关
initialize_payment_gateways({"mock": {}})


# ==================== Pydantic 模型 ====================


class CreateOrderRequest(BaseModel):
    """创建订单请求"""
    product_type: str = Field(..., description="产品类型 (subscription/topup)")
    subscription_tier: Optional[str] = Field(None, description="订阅等级 (free/pro/enterprise)")
    billing_cycle: Optional[str] = Field("monthly", description="计费周期 (monthly/yearly)")
    invoice_required: Optional[bool] = Field(False, description="是否需要发票")
    invoice_title: Optional[str] = Field(None, description="发票抬头")
    invoice_tax_id: Optional[str] = Field(None, description="税号")
    notes: Optional[str] = Field(None, description="备注")


class InitiatePaymentRequest(BaseModel):
    """发起支付请求"""
    payment_method: Optional[str] = Field("mock", description="支付方式 (mock/alipay/wechat/stripe)")


class RefundRequest(BaseModel):
    """退款请求"""
    reason: str = Field(..., description="退款原因")


class CompanyInvoiceInfoRequest(BaseModel):
    """企业发票信息请求"""
    company_name: str = Field(..., description="公司名称")
    tax_id: str = Field(..., description="纳税人识别号")
    company_address: Optional[str] = Field(None, description="公司地址")
    company_phone: Optional[str] = Field(None, description="公司电话")
    bank_name: Optional[str] = Field(None, description="开户行名称")
    bank_account: Optional[str] = Field(None, description="银行账号")
    receiver_email: Optional[str] = Field(None, description="电子发票接收邮箱")
    receiver_address: Optional[str] = Field(None, description="纸质发票收件地址")
    receiver_phone: Optional[str] = Field(None, description="收件人电话")
    invoice_type_preference: Optional[str] = Field("electronic", description="发票类型偏好")


class RequestInvoiceRequest(BaseModel):
    """申请发票请求"""
    invoice_type: Optional[str] = Field("electronic", description="发票类型 (electronic/paper)")
    invoice_title: Optional[str] = Field(None, description="发票抬头")
    tax_id: Optional[str] = Field(None, description="税号")
    receiver_name: Optional[str] = Field(None, description="收件人姓名")
    receiver_phone: Optional[str] = Field(None, description="收件人电话")
    receiver_address: Optional[str] = Field(None, description="收件地址")
    receiver_email: Optional[str] = Field(None, description="电子发票邮箱")
    notes: Optional[str] = Field(None, description="备注")


class StartTrialRequest(BaseModel):
    """开始试用请求"""
    trial_tier: Optional[str] = Field("pro", description="试用等级 (pro/enterprise)")


class ConvertTrialRequest(BaseModel):
    """试用转订阅请求"""
    new_tier: str = Field(..., description="新订阅等级")


class CancelTrialRequest(BaseModel):
    """取消试用请求"""
    reason: Optional[str] = Field(None, description="取消原因")


# ==================== 订单管理 API ====================


@router.post("/payment/create-order", summary="创建订单")
async def create_order(
    request: CreateOrderRequest,
    user_id: str = Query(..., description="用户 ID"),
    db: Session = Depends(get_db),
):
    """
    创建新的订单

    - **product_type**: 产品类型 (subscription-订阅/topup-充值)
    - **subscription_tier**: 订阅等级 (free/pro/enterprise)
    - **billing_cycle**: 计费周期 (monthly-月付/yearly-年付)
    - **invoice_required**: 是否需要发票
    """
    try:
        payment_service = get_payment_service(db)
        order = payment_service.create_order(
            user_id=user_id,
            product_type=request.product_type,
            subscription_tier=request.subscription_tier,
            billing_cycle=request.billing_cycle,
            invoice_required=request.invoice_required,
            invoice_title=request.invoice_title,
            invoice_tax_id=request.invoice_tax_id,
            notes=request.notes,
        )
        return {
            "success": True,
            "data": order.to_dict(),
            "message": "订单创建成功",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/payment/orders/{order_id}", summary="获取订单详情")
async def get_order(
    order_id: str,
    db: Session = Depends(get_db),
):
    """获取订单详细信息"""
    payment_service = get_payment_service(db)
    order = payment_service.get_order(order_id)

    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    return {
        "success": True,
        "data": order.to_dict(),
    }


@router.get("/payment/orders", summary="获取用户订单列表")
async def get_user_orders(
    user_id: str = Query(..., description="用户 ID"),
    status: Optional[str] = Query(None, description="订单状态"),
    limit: int = Query(50, description="返回数量限制"),
    db: Session = Depends(get_db),
):
    """获取用户的订单列表"""
    payment_service = get_payment_service(db)
    orders = payment_service.get_user_orders(user_id=user_id, status=status, limit=limit)

    return {
        "success": True,
        "data": [order.to_dict() for order in orders],
        "count": len(orders),
    }


@router.post("/payment/pay/{order_id}", summary="发起支付")
async def initiate_payment(
    order_id: str,
    request: InitiatePaymentRequest,
    db: Session = Depends(get_db),
):
    """
    发起支付

    支持的支付方式：
    - **mock**: 模拟支付（测试用）
    - **alipay**: 支付宝（待实现）
    - **wechat**: 微信支付（待实现）
    - **stripe**: Stripe 国际支付（待实现）
    """
    try:
        payment_service = get_payment_service(db)
        result = payment_service.initiate_payment(
            order_id=order_id,
            payment_method=request.payment_method,
        )
        return {
            "success": True,
            "data": result,
            "message": "支付已发起",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/payment/callback/{payment_method}", summary="支付回调")
async def payment_callback(
    payment_method: str,
    callback_data: Dict[str, Any] = Body(..., description="回调数据"),
    db: Session = Depends(get_db),
):
    """
    处理支付回调

    支付平台（支付宝/微信/Stripe）会在支付完成后回调此接口
    """
    payment_service = get_payment_service(db)
    result = payment_service.process_callback(
        payment_method=payment_method,
        callback_data=callback_data,
    )

    if result.get("success"):
        return {"success": True, "message": "回调处理成功", "data": result}
    else:
        raise HTTPException(status_code=400, detail=result.get("message"))


@router.post("/payment/refund/{order_id}", summary="申请退款")
async def request_refund(
    order_id: str,
    request: RefundRequest,
    user_id: str = Query(..., description="用户 ID"),
    db: Session = Depends(get_db),
):
    """
    申请退款

    - 7 天内自动退款
    - 超过 7 天需要人工审核
    """
    try:
        payment_service = get_payment_service(db)

        # 验证订单属于该用户
        order = payment_service.get_order(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="订单不存在")
        if order.user_id != user_id:
            raise HTTPException(status_code=403, detail="无权操作此订单")

        result = payment_service.request_refund(
            order_id=order_id,
            reason=request.reason,
        )
        return {
            "success": True,
            "data": result,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 发票管理 API ====================


@router.post("/invoice/company-info", summary="保存企业发票信息")
async def save_company_info(
    request: CompanyInvoiceInfoRequest,
    user_id: str = Query(..., description="用户 ID"),
    db: Session = Depends(get_db),
):
    """保存或更新企业发票信息"""
    try:
        invoice_service = get_invoice_service(db)
        info = invoice_service.save_company_info(
            user_id=user_id,
            company_name=request.company_name,
            tax_id=request.tax_id,
            company_address=request.company_address,
            company_phone=request.company_phone,
            bank_name=request.bank_name,
            bank_account=request.bank_account,
            receiver_email=request.receiver_email,
            receiver_address=request.receiver_address,
            receiver_phone=request.receiver_phone,
            invoice_type_preference=request.invoice_type_preference,
        )
        return {
            "success": True,
            "data": info.to_dict(),
            "message": "企业发票信息已保存",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/invoice/company-info", summary="获取企业发票信息")
async def get_company_info(
    user_id: str = Query(..., description="用户 ID"),
    db: Session = Depends(get_db),
):
    """获取用户保存的企业发票信息"""
    invoice_service = get_invoice_service(db)
    info = invoice_service.get_company_info(user_id)

    if not info:
        return {
            "success": True,
            "data": None,
            "message": "尚未保存企业发票信息",
        }

    return {
        "success": True,
        "data": info.to_dict(),
    }


@router.post("/invoice/request", summary="申请发票")
async def request_invoice(
    request: RequestInvoiceRequest,
    order_id: str = Query(..., description="订单 ID"),
    user_id: str = Query(..., description="用户 ID"),
    db: Session = Depends(get_db),
):
    """为已支付的订单申请发票"""
    try:
        invoice_service = get_invoice_service(db)

        # 验证订单属于该用户
        payment_service = get_payment_service(db)
        order = payment_service.get_order(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="订单不存在")
        if order.user_id != user_id:
            raise HTTPException(status_code=403, detail="无权操作此订单")

        invoice = invoice_service.request_invoice(
            user_id=user_id,
            order_id=order_id,
            invoice_type=request.invoice_type,
            invoice_title=request.invoice_title,
            tax_id=request.tax_id,
            receiver_name=request.receiver_name,
            receiver_phone=request.receiver_phone,
            receiver_address=request.receiver_address,
            receiver_email=request.receiver_email,
            notes=request.notes,
        )
        return {
            "success": True,
            "data": invoice.to_dict(),
            "message": "发票申请已提交",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/invoice/history", summary="获取发票历史")
async def get_invoice_history(
    user_id: str = Query(..., description="用户 ID"),
    status: Optional[str] = Query(None, description="发票状态"),
    limit: int = Query(50, description="返回数量限制"),
    db: Session = Depends(get_db),
):
    """获取用户的发票历史记录"""
    invoice_service = get_invoice_service(db)
    invoices = invoice_service.get_user_invoices(user_id=user_id, status=status, limit=limit)

    return {
        "success": True,
        "data": [invoice.to_dict() for invoice in invoices],
        "count": len(invoices),
    }


@router.get("/invoice/{invoice_id}", summary="获取发票详情")
async def get_invoice(
    invoice_id: str,
    db: Session = Depends(get_db),
):
    """获取发票详细信息"""
    invoice_service = get_invoice_service(db)
    invoice = invoice_service.get_invoice(invoice_id)

    if not invoice:
        raise HTTPException(status_code=404, detail="发票不存在")

    return {
        "success": True,
        "data": invoice.to_dict(),
    }


@router.post("/invoice/{invoice_id}/deliver", summary="交付发票")
async def deliver_invoice(
    invoice_id: str,
    db: Session = Depends(get_db),
):
    """交付发票（管理员操作）"""
    try:
        invoice_service = get_invoice_service(db)
        invoice = invoice_service.deliver_invoice(invoice_id)
        return {
            "success": True,
            "data": invoice.to_dict(),
            "message": "发票已交付",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 试用管理 API ====================


@router.post("/subscription/start-trial", summary="开始试用")
async def start_trial(
    request: StartTrialRequest,
    user_id: str = Query(..., description="用户 ID"),
    db: Session = Depends(get_db),
):
    """
    开始免费试用

    - 专业版：7 天免费试用
    - 企业版：14 天免费试用
    """
    try:
        trial_service = get_trial_service(db)
        result = trial_service.start_trial(
            user_id=user_id,
            trial_tier=request.trial_tier,
        )
        return {
            "success": True,
            "data": result,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/subscription/trial-status", summary="获取试用状态")
async def get_trial_status(
    user_id: str = Query(..., description="用户 ID"),
    db: Session = Depends(get_db),
):
    """获取用户的试用状态"""
    trial_service = get_trial_service(db)
    status = trial_service.get_trial_status(user_id)

    if not status:
        return {
            "success": True,
            "data": None,
            "message": "用户没有试用记录",
        }

    return {
        "success": True,
        "data": status,
    }


@router.post("/subscription/cancel-trial", summary="取消试用")
async def cancel_trial(
    request: CancelTrialRequest,
    user_id: str = Query(..., description="用户 ID"),
    db: Session = Depends(get_db),
):
    """取消正在进行试用"""
    try:
        trial_service = get_trial_service(db)
        result = trial_service.cancel_trial(
            user_id=user_id,
            reason=request.reason,
        )
        return {
            "success": True,
            "data": result,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/subscription/convert-trial", summary="试用转订阅")
async def convert_trial(
    request: ConvertTrialRequest,
    user_id: str = Query(..., description="用户 ID"),
    db: Session = Depends(get_db),
):
    """将试用转为正式订阅"""
    try:
        trial_service = get_trial_service(db)
        result = trial_service.convert_trial(
            user_id=user_id,
            new_tier=request.new_tier,
        )
        return {
            "success": True,
            "data": result,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 支付网关管理 API ====================


@router.get("/payment/methods", summary="获取支持的支付方式")
async def get_payment_methods():
    """获取所有支持的支付方式"""
    from services.payment_gateway import PaymentGatewayFactory
    return {
        "success": True,
        "data": {
            "supported_methods": PaymentGatewayFactory.get_supported_methods(),
            "descriptions": {
                "mock": "模拟支付（测试用）",
                "alipay": "支付宝",
                "wechat": "微信支付",
                "stripe": "Stripe 国际支付",
            },
        },
    }


@router.post("/payment/mock/complete", summary="完成模拟支付")
async def complete_mock_payment(
    transaction_id: str = Query(..., description="交易 ID"),
    db: Session = Depends(get_db),
):
    """
    完成模拟支付（仅测试用）

    在测试环境中，调用此接口模拟支付成功回调
    """
    from services.payment_gateway import get_payment_manager

    payment_manager = get_payment_manager()
    gateway = payment_manager.get_gateway("mock")

    try:
        callback_result = gateway.simulate_payment_callback(transaction_id)
        # 处理回调
        payment_service = get_payment_service(db)
        result = payment_service.process_callback(
            payment_method="mock",
            callback_data=callback_result,
        )
        return {
            "success": True,
            "data": result,
            "message": "模拟支付已完成",
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 统计 API ====================


@router.get("/trial/statistics", summary="获取试用统计")
async def get_trial_statistics(
    db: Session = Depends(get_db),
):
    """获取试用统计数据（管理员用）"""
    trial_service = get_trial_service(db)
    stats = trial_service.get_trial_statistics()

    return {
        "success": True,
        "data": stats,
    }
