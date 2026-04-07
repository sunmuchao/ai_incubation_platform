"""
员工 API 路由 - 数据库持久化版本
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.database import get_db
from models.db_models import (
    AIEmployeeDB, EmployeeStatusEnum, OrderStatusEnum,
    TenantStatusEnum, UserRoleEnum, InvoiceStatusEnum,
    PaymentStatusEnum, PaymentMethodEnum
)
from services.service_manager import ServiceManager, get_service_manager
from middleware.auth import require_auth, get_current_user_id, get_current_tenant_id

router = APIRouter(tags=["employees"])


# ==================== 员工管理 ====================

@router.get("/employees", response_model=List[dict])
async def list_employees(
    status: Optional[str] = None,
    tenant_id: Optional[str] = None,
    db: Session = Depends(get_db),
    services: ServiceManager = Depends(get_service_manager)
):
    """获取 AI 员工列表"""
    status_enum = EmployeeStatusEnum(status) if status else None
    employees = services.employees.list_employees(
        tenant_id=tenant_id,
        status=status_enum
    )
    return [emp_to_dict(emp) for emp in employees]


@router.post("/employees", response_model=dict)
async def create_employee(
    name: str,
    description: str,
    hourly_rate: float = 10.0,
    skills: dict = None,
    owner_id: Optional[str] = None,
    db: Session = Depends(get_db),
    services: ServiceManager = Depends(get_service_manager),
    current_user: dict = Depends(require_auth)
):
    """创建 AI 员工"""
    tenant_id = current_user.get("tenant_id")
    user_id = current_user.get("user_id")

    employee = services.employees.create_employee(
        tenant_id=tenant_id,
        owner_id=owner_id or user_id,
        name=name,
        description=description,
        skills=skills or {},
        hourly_rate=hourly_rate
    )
    return emp_to_dict(employee)


@router.get("/employees/{employee_id}", response_model=dict)
async def get_employee(
    employee_id: str,
    db: Session = Depends(get_db),
    services: ServiceManager = Depends(get_service_manager)
):
    """获取 AI 员工详情"""
    employee = services.employees.get_employee(employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return emp_to_dict(employee)


@router.post("/employees/{employee_id}/publish", response_model=dict)
async def publish_employee(
    employee_id: str,
    db: Session = Depends(get_db),
    services: ServiceManager = Depends(get_service_manager)
):
    """上架 AI 员工"""
    success = services.employees.update_status(employee_id, EmployeeStatusEnum.AVAILABLE)
    if not success:
        raise HTTPException(status_code=404, detail="Employee not found")
    employee = services.employees.get_employee(employee_id)
    return emp_to_dict(employee)


@router.post("/employees/{employee_id}/offline", response_model=dict)
async def offline_employee(
    employee_id: str,
    db: Session = Depends(get_db),
    services: ServiceManager = Depends(get_service_manager)
):
    """下线 AI 员工"""
    success = services.employees.update_status(employee_id, EmployeeStatusEnum.OFFLINE)
    if not success:
        raise HTTPException(status_code=404, detail="Employee not found")
    employee = services.employees.get_employee(employee_id)
    return emp_to_dict(employee)


@router.get("/employees/search/{skill}", response_model=List[dict])
async def search_employees(
    skill: str,
    min_rating: float = Query(0, ge=0, le=5),
    db: Session = Depends(get_db),
    services: ServiceManager = Depends(get_service_manager),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """搜索 AI 员工"""
    results = services.employees.search_employees(
        skill=skill,
        min_rating=min_rating,
        tenant_id=tenant_id
    )
    return [emp_to_dict(emp) for emp in results]


# ==================== 订单管理 ====================

@router.post("/employees/{employee_id}/order", response_model=dict)
async def create_order(
    employee_id: str,
    hirer_id: str,
    duration_hours: int,
    task_description: str,
    db: Session = Depends(get_db),
    services: ServiceManager = Depends(get_service_manager),
    current_user: dict = Depends(require_auth)
):
    """创建租赁订单"""
    tenant_id = current_user.get("tenant_id")

    order = services.orders.create_order(
        tenant_id=tenant_id,
        employee_id=employee_id,
        hirer_id=hirer_id,
        owner_id="",  # 会从员工信息中获取
        duration_hours=duration_hours,
        task_description=task_description
    )
    if not order:
        raise HTTPException(status_code=400, detail="Failed to create order. Employee not available.")
    return order_to_dict(order)


@router.get("/orders/{order_id}", response_model=dict)
async def get_order(
    order_id: str,
    db: Session = Depends(get_db),
    services: ServiceManager = Depends(get_service_manager)
):
    """获取订单详情"""
    order = services.orders.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order_to_dict(order)


@router.get("/employees/{employee_id}/orders", response_model=List[dict])
async def get_employee_orders(
    employee_id: str,
    db: Session = Depends(get_db),
    services: ServiceManager = Depends(get_service_manager)
):
    """获取员工的所有订单"""
    orders = services.orders.list_orders(employee_id=employee_id)
    return [order_to_dict(order) for order in orders]


@router.get("/orders/owners/{owner_id}", response_model=List[dict])
async def get_owner_orders(
    owner_id: str,
    db: Session = Depends(get_db),
    services: ServiceManager = Depends(get_service_manager)
):
    """获取所有者的所有订单"""
    orders = services.orders.list_orders(owner_id=owner_id)
    return [order_to_dict(order) for order in orders]


@router.get("/orders/hirers/{hirer_id}", response_model=List[dict])
async def get_hirer_orders(
    hirer_id: str,
    db: Session = Depends(get_db),
    services: ServiceManager = Depends(get_service_manager)
):
    """获取租赁者的所有订单"""
    orders = services.orders.list_orders(hirer_id=hirer_id)
    return [order_to_dict(order) for order in orders]


@router.post("/orders/{order_id}/confirm")
async def confirm_order(
    order_id: str,
    db: Session = Depends(get_db),
    services: ServiceManager = Depends(get_service_manager)
):
    """确认订单"""
    if not services.orders.confirm_order(order_id):
        raise HTTPException(status_code=400, detail="Failed to confirm order")
    return {"message": "Order confirmed successfully"}


@router.post("/orders/{order_id}/start")
async def start_order(
    order_id: str,
    db: Session = Depends(get_db),
    services: ServiceManager = Depends(get_service_manager)
):
    """开始执行订单"""
    if not services.orders.start_order(order_id):
        raise HTTPException(status_code=400, detail="Failed to start order")
    return {"message": "Order started successfully"}


@router.post("/orders/{order_id}/complete")
async def complete_order(
    order_id: str,
    rating: Optional[float] = None,
    review: Optional[str] = None,
    review_tags: Optional[List[str]] = None,
    db: Session = Depends(get_db),
    services: ServiceManager = Depends(get_service_manager)
):
    """完成订单"""
    if not services.orders.complete_order(order_id, rating, review, review_tags):
        raise HTTPException(status_code=400, detail="Failed to complete order")
    return {"message": "Order completed successfully"}


@router.post("/orders/{order_id}/cancel")
async def cancel_order(
    order_id: str,
    db: Session = Depends(get_db),
    services: ServiceManager = Depends(get_service_manager)
):
    """取消订单"""
    if not services.orders.cancel_order(order_id):
        raise HTTPException(status_code=400, detail="Failed to cancel order")
    return {"message": "Order cancelled successfully"}


# ==================== 租户管理 ====================

@router.post("/tenants", response_model=dict)
async def create_tenant(
    name: str,
    contact_name: str,
    contact_email: str,
    contact_phone: Optional[str] = None,
    billing_cycle: str = "monthly",
    db: Session = Depends(get_db),
    services: ServiceManager = Depends(get_service_manager)
):
    """创建租户"""
    tenant = services.tenants.create_tenant(
        name=name,
        contact_name=contact_name,
        contact_email=contact_email,
        contact_phone=contact_phone,
        billing_cycle=billing_cycle
    )
    # 自动创建钱包
    services.wallet.create_wallet(tenant.id)
    return tenant_to_dict(tenant)


@router.get("/tenants", response_model=List[dict])
async def list_tenants(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    services: ServiceManager = Depends(get_service_manager)
):
    """获取租户列表"""
    status_enum = TenantStatusEnum(status) if status else None
    tenants = services.tenants.list_tenants(status=status_enum)
    return [tenant_to_dict(t) for t in tenants]


@router.get("/tenants/{tenant_id}", response_model=dict)
async def get_tenant(
    tenant_id: str,
    db: Session = Depends(get_db),
    services: ServiceManager = Depends(get_service_manager)
):
    """获取租户详情"""
    tenant = services.tenants.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant_to_dict(tenant)


# ==================== 用户与认证 ====================

@router.post("/auth/register", response_model=dict)
async def register_user(
    username: str,
    email: str,
    password: str,
    full_name: Optional[str] = None,
    role: str = "hirer",
    tenant_id: Optional[str] = None,
    db: Session = Depends(get_db),
    services: ServiceManager = Depends(get_service_manager),
    current_user: dict = Depends(require_auth)
):
    """创建用户"""
    target_tenant_id = tenant_id or current_user.get("tenant_id")
    user = services.users.create_user(
        tenant_id=target_tenant_id,
        username=username,
        email=email,
        password=password,
        full_name=full_name,
        role=role
    )
    if not user:
        raise HTTPException(status_code=400, detail="Failed to create user")
    return user_to_dict(user)


@router.post("/auth/login", response_model=dict)
async def login(
    username: str,
    password: str,
    db: Session = Depends(get_db),
    services: ServiceManager = Depends(get_service_manager)
):
    """用户登录"""
    result = services.users.login(username, password)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return result


@router.get("/users/me", response_model=dict)
async def get_current_user_info(
    current_user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
    services: ServiceManager = Depends(get_service_manager)
):
    """获取当前用户信息"""
    user = services.users.get_user(current_user.get("user_id"))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user_to_dict(user)


# ==================== 钱包与支付 ====================

@router.get("/tenants/{tenant_id}/wallet", response_model=dict)
async def get_wallet(
    tenant_id: str,
    db: Session = Depends(get_db),
    services: ServiceManager = Depends(get_service_manager),
    current_user: dict = Depends(require_auth)
):
    """获取租户钱包信息"""
    if current_user.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    wallet = services.wallet.get_wallet(tenant_id)
    if not wallet:
        # 自动创建钱包
        wallet = services.wallet.create_wallet(tenant_id)
    return wallet_to_dict(wallet)


@router.post("/tenants/{tenant_id}/wallet/recharge")
async def recharge_wallet(
    tenant_id: str,
    amount: float,
    db: Session = Depends(get_db),
    services: ServiceManager = Depends(get_service_manager),
    current_user: dict = Depends(require_auth)
):
    """钱包充值"""
    if current_user.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    if not services.wallet.recharge_wallet(tenant_id, amount):
        raise HTTPException(status_code=400, detail="Failed to recharge wallet")
    return {"message": "Wallet recharged successfully", "amount": amount}


@router.post("/tenants/{tenant_id}/payments", response_model=dict)
async def create_payment(
    tenant_id: str,
    amount: float,
    payment_method: str,
    order_id: Optional[str] = None,
    invoice_id: Optional[str] = None,
    db: Session = Depends(get_db),
    services: ServiceManager = Depends(get_service_manager),
    current_user: dict = Depends(require_auth)
):
    """创建支付请求"""
    if current_user.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    payment = services.payments.create_payment(
        tenant_id=tenant_id,
        user_id=current_user.get("user_id"),
        amount=amount,
        payment_method=payment_method,
        order_id=order_id,
        invoice_id=invoice_id
    )
    if not payment:
        raise HTTPException(status_code=400, detail="Failed to create payment")
    return payment_to_dict(payment)


# ==================== 账单管理 ====================

@router.post("/tenants/{tenant_id}/invoices/generate", response_model=dict)
async def generate_invoice(
    tenant_id: str,
    period_start: datetime,
    period_end: datetime,
    db: Session = Depends(get_db),
    services: ServiceManager = Depends(get_service_manager),
    current_user: dict = Depends(require_auth)
):
    """生成账单"""
    if current_user.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    invoice = services.invoices.generate_invoice(tenant_id, period_start, period_end)
    if not invoice:
        raise HTTPException(status_code=400, detail="Failed to generate invoice")
    return invoice_to_dict(invoice)


@router.get("/tenants/{tenant_id}/invoices", response_model=List[dict])
async def list_invoices(
    tenant_id: str,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    services: ServiceManager = Depends(get_service_manager),
    current_user: dict = Depends(require_auth)
):
    """获取租户账单列表"""
    if current_user.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    status_enum = InvoiceStatusEnum(status) if status else None
    invoices = services.invoices.get_invoices(tenant_id, status=status_enum)
    return [invoice_to_dict(inv) for inv in invoices]


# ==================== 工具函数 ====================

def tenant_to_dict(tenant) -> dict:
    return {
        "id": tenant.id,
        "name": tenant.name,
        "contact_name": tenant.contact_name,
        "contact_email": tenant.contact_email,
        "contact_phone": tenant.contact_phone,
        "status": tenant.status.value,
        "billing_cycle": tenant.billing_cycle.value,
        "max_employees": tenant.max_employees,
        "max_concurrent_jobs": tenant.max_concurrent_jobs,
        "storage_quota_gb": tenant.storage_quota_gb,
        "used_storage_gb": tenant.used_storage_gb,
        "trial_end_at": tenant.trial_end_at.isoformat() if tenant.trial_end_at else None,
        "created_at": tenant.created_at.isoformat() if tenant.created_at else None,
        "updated_at": tenant.updated_at.isoformat() if tenant.updated_at else None
    }


def user_to_dict(user) -> dict:
    return {
        "id": user.id,
        "tenant_id": user.tenant_id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.value,
        "is_active": user.is_active,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None
    }


def emp_to_dict(employee) -> dict:
    return {
        "id": employee.id,
        "tenant_id": employee.tenant_id,
        "name": employee.name,
        "owner_id": employee.owner_id,
        "avatar": employee.avatar,
        "description": employee.description,
        "skills": employee.skills,
        "status": employee.status.value,
        "hourly_rate": employee.hourly_rate,
        "total_jobs": employee.total_jobs,
        "total_earnings": employee.total_earnings,
        "rating": employee.rating,
        "review_count": employee.review_count,
        "current_training_version": employee.current_training_version,
        "training_versions": employee.training_versions,
        "agent_config": employee.agent_config,
        "deerflow_agent_id": employee.deerflow_agent_id,
        "risk_level": employee.risk_level.value,
        "risk_score": employee.risk_score,
        "violation_count": employee.violation_count,
        "is_verified": employee.is_verified,
        "created_at": employee.created_at.isoformat() if employee.created_at else None,
        "updated_at": employee.updated_at.isoformat() if employee.updated_at else None
    }


def order_to_dict(order) -> dict:
    return {
        "id": order.id,
        "tenant_id": order.tenant_id,
        "employee_id": order.employee_id,
        "owner_id": order.owner_id,
        "hirer_id": order.hirer_id,
        "duration_hours": order.duration_hours,
        "task_description": order.task_description,
        "hourly_rate": order.hourly_rate,
        "total_amount": order.total_amount,
        "platform_fee_rate": order.platform_fee_rate,
        "platform_fee": order.platform_fee,
        "owner_earning": order.owner_earning,
        "status": order.status.value,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "confirmed_at": order.confirmed_at.isoformat() if order.confirmed_at else None,
        "started_at": order.started_at.isoformat() if order.started_at else None,
        "completed_at": order.completed_at.isoformat() if order.completed_at else None,
        "cancelled_at": order.cancelled_at.isoformat() if order.cancelled_at else None,
        "rating": order.rating,
        "review": order.review,
        "review_tags": order.review_tags,
        "review_likes": order.review_likes,
        "is_review_hidden": order.is_review_hidden,
        "risk_check_passed": order.risk_check_passed,
        "risk_factors": order.risk_factors
    }


def wallet_to_dict(wallet) -> dict:
    return {
        "id": wallet.id,
        "tenant_id": wallet.tenant_id,
        "balance": wallet.balance,
        "frozen_balance": wallet.frozen_balance,
        "total_recharge": wallet.total_recharge,
        "total_consumption": wallet.total_consumption,
        "currency": wallet.currency,
        "created_at": wallet.created_at.isoformat() if wallet.created_at else None,
        "updated_at": wallet.updated_at.isoformat() if wallet.updated_at else None
    }


def payment_to_dict(payment) -> dict:
    return {
        "id": payment.id,
        "tenant_id": payment.tenant_id,
        "user_id": payment.user_id,
        "invoice_id": payment.invoice_id,
        "order_id": payment.order_id,
        "amount": payment.amount,
        "currency": payment.currency,
        "payment_method": payment.payment_method.value,
        "status": payment.status.value,
        "third_party_transaction_id": payment.third_party_transaction_id,
        "payment_data": payment.payment_data,
        "error_message": payment.error_message,
        "created_at": payment.created_at.isoformat() if payment.created_at else None,
        "updated_at": payment.updated_at.isoformat() if payment.updated_at else None
    }


def invoice_to_dict(invoice) -> dict:
    return {
        "id": invoice.id,
        "tenant_id": invoice.tenant_id,
        "invoice_number": invoice.invoice_number,
        "period_start": invoice.period_start.isoformat() if invoice.period_start else None,
        "period_end": invoice.period_end.isoformat() if invoice.period_end else None,
        "total_amount": invoice.total_amount,
        "paid_amount": invoice.paid_amount,
        "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
        "status": invoice.status.value,
        "items": invoice.items,
        "payment_status": invoice.payment_status.value,
        "issued_at": invoice.issued_at.isoformat() if invoice.issued_at else None,
        "paid_at": invoice.paid_at.isoformat() if invoice.paid_at else None,
        "created_at": invoice.created_at.isoformat() if invoice.created_at else None,
        "updated_at": invoice.updated_at.isoformat() if invoice.updated_at else None
    }
