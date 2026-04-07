"""
员工 API 路由
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.employee import (
    AIEmployee, AIEmployeeCreate, EmployeeStatus, Order, OrderStatus, RentalRequest,
    TrainingDataVersion, TrainingDataUploadRequest, TrainingTask, TrainingStartRequest,
    ReviewSubmitRequest, Tenant, TenantStatus, User, UserRole, UsageRecord,
    Invoice, InvoiceStatus, PaymentTransaction, PaymentMethod, Wallet,
    TenantCreateRequest, UserCreateRequest, LoginRequest, LoginResponse, PaymentRequest
)
from services.employee_service import employee_service

router = APIRouter(prefix="/api/employees", tags=["employees"])


@router.get("/", response_model=List[AIEmployee])
async def list_employees(status: Optional[EmployeeStatus] = None):
    """获取 AI 员工列表"""
    return employee_service.list_employees(status=status)


@router.post("/", response_model=AIEmployee)
async def create_employee(employee_data: AIEmployeeCreate, owner_id: str):
    """创建 AI 员工"""
    return employee_service.create_employee(employee_data, owner_id)


@router.get("/{employee_id}", response_model=AIEmployee)
async def get_employee(employee_id: str):
    """获取 AI 员工详情"""
    employee = employee_service.get_employee(employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee


@router.post("/{employee_id}/publish", response_model=AIEmployee)
async def publish_employee(employee_id: str):
    """上架 AI 员工（设置为 available）"""
    if not employee_service.update_status(employee_id, EmployeeStatus.AVAILABLE):
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee_service.get_employee(employee_id)


@router.post("/{employee_id}/offline", response_model=AIEmployee)
async def offline_employee(employee_id: str):
    """下线 AI 员工（设置为 offline）"""
    if not employee_service.update_status(employee_id, EmployeeStatus.OFFLINE):
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee_service.get_employee(employee_id)


@router.post("/{employee_id}/hire", deprecated=True)
async def hire_employee(employee_id: str, hirer_id: str, duration_hours: int):
    """
    雇佣 AI 员工（已废弃，请使用 /api/employees/{employee_id}/order 创建订单）
    """
    rental_request = RentalRequest(
        employee_id=employee_id,
        hirer_id=hirer_id,
        duration_hours=duration_hours,
        task_description="Legacy hire request"
    )
    order = employee_service.create_order(
        employee_id=employee_id,
        hirer_id=hirer_id,
        duration_hours=duration_hours,
        task_description="Legacy hire request"
    )
    if not order:
        raise HTTPException(status_code=400, detail="Failed to hire employee")

    # 自动确认订单
    employee_service.confirm_order(order.id)
    return {"message": f"Hired {order.employee_id} for {duration_hours} hours", "order_id": order.id}


@router.get("/search/{skill}", response_model=List[AIEmployee])
async def search_employees(
    skill: str,
    min_rating: float = Query(0, ge=0, le=5),
):
    """搜索 AI 员工"""
    # P0: 搜索端点应与市场侧一致，只展示可上架（available）的员工
    results = employee_service.search_employees(skill, min_rating)
    return [e for e in results if e.status == EmployeeStatus.AVAILABLE]


# 订单相关接口
@router.post("/{employee_id}/order", response_model=Order)
async def create_order(employee_id: str, rental_request: RentalRequest):
    """创建租赁订单"""
    if rental_request.employee_id != employee_id:
        raise HTTPException(
            status_code=400,
            detail="employee_id mismatch between path and request body",
        )
    order = employee_service.create_order(
        employee_id=employee_id,
        hirer_id=rental_request.hirer_id,
        duration_hours=rental_request.duration_hours,
        task_description=rental_request.task_description
    )
    if not order:
        raise HTTPException(status_code=400, detail="Failed to create order. Employee not available.")
    return order


@router.get("/orders/{order_id}", response_model=Order)
async def get_order(order_id: str):
    """获取订单详情"""
    order = employee_service.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.get("/{employee_id}/orders", response_model=List[Order])
async def get_employee_orders(employee_id: str):
    """获取员工的所有订单"""
    return employee_service.list_orders_by_employee(employee_id)


@router.get("/owners/{owner_id}/orders", response_model=List[Order])
async def get_owner_orders(owner_id: str):
    """获取所有者的所有订单"""
    return employee_service.list_orders_by_owner(owner_id)


@router.get("/hirers/{hirer_id}/orders", response_model=List[Order])
async def get_hirer_orders(hirer_id: str):
    """获取租赁者的所有订单"""
    return employee_service.list_orders_by_hirer(hirer_id)


@router.post("/orders/{order_id}/confirm")
async def confirm_order(order_id: str):
    """确认订单"""
    if not employee_service.confirm_order(order_id):
        raise HTTPException(status_code=400, detail="Failed to confirm order")
    return {"message": "Order confirmed successfully"}


@router.post("/orders/{order_id}/start")
async def start_order(order_id: str):
    """开始执行订单"""
    if not employee_service.start_order(order_id):
        raise HTTPException(status_code=400, detail="Failed to start order")
    return {"message": "Order started successfully"}


@router.post("/orders/{order_id}/complete")
async def complete_order(order_id: str, review_data: Optional[ReviewSubmitRequest] = None):
    """完成订单，可同时提交评价"""
    if not employee_service.complete_order(order_id, review_data):
        raise HTTPException(status_code=400, detail="Failed to complete order")
    return {"message": "Order completed successfully"}


@router.post("/orders/{order_id}/cancel")
async def cancel_order(order_id: str):
    """取消订单"""
    if not employee_service.cancel_order(order_id):
        raise HTTPException(status_code=400, detail="Failed to cancel order")
    return {"message": "Order cancelled successfully"}


# 训练数据管理接口
@router.post("/{employee_id}/training-data", response_model=TrainingDataVersion)
async def upload_training_data(
    employee_id: str,
    data: TrainingDataUploadRequest,
    created_by: str
):
    """上传训练数据并创建新版本"""
    version = employee_service.upload_training_data(employee_id, data, created_by)
    if not version:
        raise HTTPException(status_code=404, detail="Employee not found")
    return version


@router.get("/{employee_id}/training-data", response_model=List[TrainingDataVersion])
async def list_training_versions(employee_id: str):
    """获取员工的所有训练数据版本"""
    employee = employee_service.get_employee(employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee_service.get_training_versions(employee_id)


@router.get("/training-data/{version_id}", response_model=TrainingDataVersion)
async def get_training_version(version_id: str):
    """获取指定训练数据版本详情"""
    version = employee_service.get_training_version(version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Training version not found")
    return version


# Agent 运行时接口
@router.post("/{employee_id}/agent/create")
async def create_deerflow_agent(employee_id: str):
    """在DeerFlow中创建Agent实例"""
    agent_id = employee_service.create_deerflow_agent(employee_id)
    if not agent_id:
        raise HTTPException(status_code=400, detail="Failed to create DeerFlow agent. Check if DeerFlow is available.")
    return {"agent_id": agent_id, "message": "Agent created successfully"}


@router.post("/{employee_id}/training/start", response_model=TrainingTask)
async def start_training(employee_id: str, request: TrainingStartRequest):
    """开始训练任务"""
    task = employee_service.start_training(employee_id, request.version_id, request.training_config)
    if not task:
        raise HTTPException(status_code=400, detail="Failed to start training. Check employee and version ID.")
    return task


@router.get("/training/tasks/{task_id}", response_model=TrainingTask)
async def get_training_task(task_id: str):
    """获取训练任务状态"""
    task = employee_service.get_training_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Training task not found")
    return task


# 评价与风控接口
@router.get("/{employee_id}/reviews", response_model=List[Order])
async def get_employee_reviews(employee_id: str, min_rating: float = 0):
    """获取员工的所有评价"""
    employee = employee_service.get_employee(employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee_service.get_employee_reviews(employee_id, min_rating)


@router.post("/orders/{order_id}/reviews/like")
async def like_review(order_id: str):
    """点赞评价"""
    if not employee_service.like_review(order_id):
        raise HTTPException(status_code=400, detail="Failed to like review")
    return {"message": "Review liked successfully"}


@router.get("/{employee_id}/risk-report")
async def get_risk_report(employee_id: str):
    """获取员工风险报告"""
    report = employee_service.get_risk_report(employee_id)
    if not report:
        raise HTTPException(status_code=404, detail="Employee not found")
    return report


# ======================================
# P2 新增接口：租户管理
# ======================================
@router.post("/tenants", response_model=Tenant)
async def create_tenant(tenant_data: TenantCreateRequest):
    """创建租户"""
    return employee_service.create_tenant(tenant_data)


@router.get("/tenants", response_model=List[Tenant])
async def list_tenants(status: Optional[TenantStatus] = None):
    """获取租户列表"""
    return employee_service.list_tenants(status)


@router.get("/tenants/{tenant_id}", response_model=Tenant)
async def get_tenant(tenant_id: str):
    """获取租户详情"""
    tenant = employee_service.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


@router.put("/tenants/{tenant_id}/status")
async def update_tenant_status(tenant_id: str, status: TenantStatus):
    """更新租户状态"""
    if not employee_service.update_tenant_status(tenant_id, status):
        raise HTTPException(status_code=400, detail="Failed to update tenant status")
    return {"message": "Tenant status updated successfully"}


@router.get("/tenants/{tenant_id}/employees", response_model=List[AIEmployee])
async def list_tenant_employees(tenant_id: str, status: Optional[EmployeeStatus] = None):
    """获取租户下的所有AI员工"""
    tenant = employee_service.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return employee_service.list_employees_by_tenant(tenant_id, status)


@router.get("/tenants/{tenant_id}/orders", response_model=List[Order])
async def list_tenant_orders(tenant_id: str, status: Optional[OrderStatus] = None):
    """获取租户下的所有订单"""
    tenant = employee_service.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return employee_service.list_orders_by_tenant(tenant_id, status)


# ======================================
# P2 新增接口：用户与认证
# ======================================
@router.post("/tenants/{tenant_id}/users", response_model=User)
async def create_user(tenant_id: str, user_data: UserCreateRequest):
    """创建租户用户"""
    user = employee_service.create_user(tenant_id, user_data)
    if not user:
        raise HTTPException(status_code=400, detail="Failed to create user. Tenant not found or username exists.")
    return user


@router.post("/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """用户登录"""
    result = employee_service.login(request)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return result


@router.get("/users/{user_id}", response_model=User)
async def get_user(user_id: str):
    """获取用户信息"""
    user = employee_service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# ======================================
# P2 新增接口：用量统计与账单
# ======================================
@router.get("/tenants/{tenant_id}/usage", response_model=List[UsageRecord])
async def get_usage_records(
    tenant_id: str,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None
):
    """获取租户用量记录"""
    tenant = employee_service.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return employee_service.get_usage_records(tenant_id, start_time, end_time)


@router.post("/tenants/{tenant_id}/invoices/generate", response_model=Invoice)
async def generate_invoice(
    tenant_id: str,
    period_start: datetime,
    period_end: datetime
):
    """生成指定周期的账单"""
    invoice = employee_service.generate_invoice(tenant_id, period_start, period_end)
    if not invoice:
        raise HTTPException(status_code=400, detail="Failed to generate invoice. No usage records found.")
    return invoice


@router.get("/tenants/{tenant_id}/invoices", response_model=List[Invoice])
async def list_invoices(tenant_id: str, status: Optional[InvoiceStatus] = None):
    """获取租户账单列表"""
    tenant = employee_service.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return employee_service.get_invoices(tenant_id, status)


@router.get("/invoices/{invoice_id}", response_model=Invoice)
async def get_invoice(invoice_id: str):
    """获取账单详情"""
    invoice = employee_service.get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.post("/invoices/{invoice_id}/issue")
async def issue_invoice(invoice_id: str):
    """开具发票"""
    if not employee_service.issue_invoice(invoice_id):
        raise HTTPException(status_code=400, detail="Failed to issue invoice")
    return {"message": "Invoice issued successfully"}


# ======================================
# P2 新增接口：支付与钱包
# ======================================
@router.get("/tenants/{tenant_id}/wallet", response_model=Wallet)
async def get_wallet(tenant_id: str):
    """获取租户钱包信息"""
    wallet = employee_service.get_wallet(tenant_id)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    return wallet


@router.post("/tenants/{tenant_id}/wallet/recharge")
async def recharge_wallet(tenant_id: str, amount: float):
    """钱包充值"""
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    if not employee_service.recharge_wallet(tenant_id, amount):
        raise HTTPException(status_code=400, detail="Failed to recharge wallet")
    return {"message": "Wallet recharged successfully", "amount": amount}


@router.post("/tenants/{tenant_id}/payments", response_model=PaymentTransaction)
async def create_payment(tenant_id: str, user_id: str, request: PaymentRequest):
    """创建支付请求"""
    payment = employee_service.create_payment(tenant_id, user_id, request)
    if not payment:
        raise HTTPException(status_code=400, detail="Failed to create payment. Insufficient balance or invalid parameters.")
    return payment


@router.get("/payments/{payment_id}", response_model=PaymentTransaction)
async def get_payment_status(payment_id: str):
    """查询支付状态"""
    payment = employee_service.get_payment_status(payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment
