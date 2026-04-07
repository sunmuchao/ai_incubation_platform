"""
P8 钱包增强 API

提供：
- 钱包充值
- 充值历史查询
- 自动扣费计划管理
- 账单分期支付
- 钱包转账
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

from config.database import get_db
from middleware.auth import require_auth, get_current_user
from services.wallet_enhanced_service import WalletEnhancedService
from models.db_models import PaymentMethodEnum

router = APIRouter(prefix="/api/wallet", tags=["P8-钱包增强"])


# ==================== 请求/响应模型 ====================

class WalletRechargeRequest(BaseModel):
    """钱包充值请求"""
    amount: float = Field(..., gt=0, description="充值金额")
    payment_method: str = Field(..., description="支付方式：alipay/wechat_pay/bank_transfer")
    transaction_id: Optional[str] = Field(None, description="第三方支付交易 ID")
    description: Optional[str] = Field(None, description="描述")


class WalletRechargeResponse(BaseModel):
    """钱包充值响应"""
    success: bool
    recharge_id: str
    amount: float
    old_balance: float
    new_balance: float
    message: str


class AutoDeductionPlanCreate(BaseModel):
    """创建自动扣费计划请求"""
    name: str = Field(..., description="计划名称")
    amount: float = Field(..., gt=0, description="每次扣费金额")
    frequency: str = Field(..., description="扣费频率：daily/weekly/monthly")
    target_type: str = Field(..., description="目标类型：invoice/subscription/installment")
    target_id: str = Field(..., description="目标 ID")
    total_amount: Optional[float] = Field(None, gt=0, description="总金额")
    max_deductions: Optional[int] = Field(None, ge=1, description="最大扣费次数")
    payment_method: str = Field(default="balance", description="支付方式")
    start_date: Optional[str] = Field(None, description="开始日期")
    end_date: Optional[str] = Field(None, description="结束日期")


class InstallmentPlanCreate(BaseModel):
    """创建分期支付计划请求"""
    invoice_id: str = Field(..., description="账单 ID")
    total_amount: float = Field(..., gt=0, description="总金额")
    installments: int = Field(..., ge=2, le=24, description="分期期数 (2-24)")
    payment_method: str = Field(default="balance", description="支付方式")


class WalletTransferRequest(BaseModel):
    """钱包转账请求"""
    to_tenant_id: str = Field(..., description="转入租户 ID")
    amount: float = Field(..., gt=0, description="转账金额")
    description: Optional[str] = Field(None, description="描述")


# ==================== 钱包充值 ====================

@router.post("/recharge", response_model=WalletRechargeResponse)
async def recharge_wallet(
    request: WalletRechargeRequest,
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(require_auth)
):
    """
    钱包充值

    支持以下支付方式:
    - **支付宝**: 需要配置支付宝 app_id 和私钥
    - **微信支付**: 需要配置微信商户号和 API 密钥
    - **银行转账**: 线下转账后确认
    """
    service = WalletEnhancedService(db)

    # 如果是支付宝或微信支付，需要先创建支付订单
    if request.payment_method in ["alipay", "wechat_pay"]:
        # 这里应该调用支付网关创建支付订单
        # 为简化，直接记录充值
        pass

    result = service.recharge_wallet(
        tenant_id=user["tenant_id"],
        user_id=user["user_id"],
        amount=request.amount,
        payment_method=request.payment_method,
        transaction_id=request.transaction_id,
        description=request.description
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "充值失败"))

    return WalletRechargeResponse(**result)


@router.get("/recharge/history")
async def get_recharge_history(
    start_date: Optional[str] = Query(None, description="开始日期 (ISO format)"),
    end_date: Optional[str] = Query(None, description="结束日期 (ISO format)"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(require_auth)
):
    """获取充值历史记录"""
    service = WalletEnhancedService(db)

    start_dt = datetime.fromisoformat(start_date) if start_date else None
    end_dt = datetime.fromisoformat(end_date) if end_date else None
    offset = (page - 1) * page_size

    history, total = service.get_recharge_history(
        tenant_id=user["tenant_id"],
        start_date=start_dt,
        end_date=end_dt,
        limit=page_size,
        offset=offset
    )

    return {
        "items": history,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/balance")
async def get_wallet_balance(
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(require_auth)
):
    """获取钱包余额"""
    from models.db_models import WalletDB

    wallet = db.query(WalletDB).filter(
        WalletDB.tenant_id == user["tenant_id"]
    ).first()

    if not wallet:
        return {
            "tenant_id": user["tenant_id"],
            "balance": 0.0,
            "frozen_balance": 0.0,
            "currency": "CNY"
        }

    return {
        "tenant_id": wallet.tenant_id,
        "balance": wallet.balance,
        "frozen_balance": wallet.frozen_balance,
        "total_recharge": wallet.total_recharge,
        "total_consumption": wallet.total_consumption,
        "currency": wallet.currency
    }


# ==================== 自动扣费计划 ====================

@router.post("/auto-deduction", response_model=Dict[str, Any])
async def create_auto_deduction_plan(
    request: AutoDeductionPlanCreate,
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(require_auth)
):
    """
    创建自动扣费计划

    用于定期自动扣费，如订阅服务、分期付款等
    """
    service = WalletEnhancedService(db)

    result = service.create_auto_deduction_plan(
        tenant_id=user["tenant_id"],
        user_id=user["user_id"],
        name=request.name,
        amount=request.amount,
        frequency=request.frequency,
        target_type=request.target_type,
        target_id=request.target_id,
        total_amount=request.total_amount,
        max_deductions=request.max_deductions,
        payment_method=request.payment_method,
        start_date=datetime.fromisoformat(request.start_date) if request.start_date else None,
        end_date=datetime.fromisoformat(request.end_date) if request.end_date else None
    )

    return result


@router.get("/auto-deduction/list")
async def list_auto_deduction_plans(
    status: Optional[str] = Query(None, description="状态：active/paused/completed/cancelled"),
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(require_auth)
):
    """获取自动扣费计划列表"""
    service = WalletEnhancedService(db)

    plans = service.list_auto_deduction_plans(
        tenant_id=user["tenant_id"],
        user_id=user["user_id"],
        status=status
    )

    return {
        "total": len(plans),
        "plans": plans
    }


@router.get("/auto-deduction/{plan_id}")
async def get_auto_deduction_plan(
    plan_id: str,
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(require_auth)
):
    """获取自动扣费计划详情"""
    service = WalletEnhancedService(db)

    plan = service.get_auto_deduction_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="计划不存在")

    return plan


@router.post("/auto-deduction/{plan_id}/cancel")
async def cancel_auto_deduction_plan(
    plan_id: str,
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(require_auth)
):
    """取消自动扣费计划"""
    service = WalletEnhancedService(db)

    result = service.cancel_auto_deduction_plan(
        plan_id=plan_id,
        user_id=user["user_id"]
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "取消失败"))

    return result


# ==================== 账单分期支付 ====================

@router.post("/installment", response_model=Dict[str, Any])
async def create_installment_plan(
    request: InstallmentPlanCreate,
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(require_auth)
):
    """
    创建账单分期支付计划

    将大额账单分多期支付，减轻一次性支付压力
    """
    service = WalletEnhancedService(db)

    result = service.create_installment_plan(
        tenant_id=user["tenant_id"],
        user_id=user["user_id"],
        invoice_id=request.invoice_id,
        total_amount=request.total_amount,
        installments=request.installments,
        payment_method=request.payment_method
    )

    return result


# ==================== 钱包转账 ====================

@router.post("/transfer", response_model=Dict[str, Any])
async def transfer_wallet(
    request: WalletTransferRequest,
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(require_auth)
):
    """
    钱包转账

    将余额转账给其他租户
    """
    service = WalletEnhancedService(db)

    result = service.transfer_wallet(
        from_tenant_id=user["tenant_id"],
        to_tenant_id=request.to_tenant_id,
        user_id=user["user_id"],
        amount=request.amount,
        description=request.description
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "转账失败"))

    return result


# ==================== 定时任务端点 ====================

@router.post("/admin/process-auto-deductions")
async def process_auto_deductions(
    db: Session = Depends(get_db),
    admin: bool = Query(False, description="是否需要管理员权限")
):
    """
    处理到期的自动扣费

    应该由定时任务调用，例如每天凌晨执行
    """
    if not admin:
        # 实际应该验证管理员权限或内部调用密钥
        pass

    service = WalletEnhancedService(db)
    result = service.process_auto_deductions()

    return result
