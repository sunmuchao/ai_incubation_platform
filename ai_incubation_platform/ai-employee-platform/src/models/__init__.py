"""
数据模型模块

注意：SQLAlchemy 模型应该直接从 db_models、p4_models 等模块导入，
避免通过本模块导入导致 SQLAlchemy 注册表重复注册问题。
"""

# 只导出 Pydantic 模型，不导出 SQLAlchemy 模型
from models.employee import (
    AIEmployee,
    AIEmployeeCreate,
    EmployeeStatus,
    Order,
    OrderStatus,
    RentalRequest,
    TrainingDataVersion,
    TrainingDataUploadRequest,
    TrainingTask,
    TrainingStartRequest,
    ReviewSubmitRequest,
    Tenant,
    TenantStatus,
    User,
    UserRole,
    UsageRecord,
    Invoice,
    InvoiceStatus,
    PaymentTransaction,
    PaymentMethod,
    Wallet,
    TenantCreateRequest,
    UserCreateRequest,
    LoginRequest,
    LoginResponse,
    PaymentRequest,
)

# 导出枚举类型（这些不是 SQLAlchemy 模型，可以安全导出）
from models.db_models import (
    SkillLevelEnum,
    EmployeeStatusEnum,
    TrainingDataTypeEnum,
    TrainingStatusEnum,
    RiskLevelEnum,
    TenantStatusEnum,
    UserRoleEnum,
    BillingCycleEnum,
    InvoiceStatusEnum,
    PaymentStatusEnum,
    PaymentMethodEnum,
    OrderStatusEnum,
)

__all__ = [
    # Pydantic 模型
    "AIEmployee",
    "AIEmployeeCreate",
    "EmployeeStatus",
    "Order",
    "OrderStatus",
    "RentalRequest",
    "TrainingDataVersion",
    "TrainingDataUploadRequest",
    "TrainingTask",
    "TrainingStartRequest",
    "ReviewSubmitRequest",
    "Tenant",
    "TenantStatus",
    "User",
    "UserRole",
    "UsageRecord",
    "Invoice",
    "InvoiceStatus",
    "PaymentTransaction",
    "PaymentMethod",
    "Wallet",
    "TenantCreateRequest",
    "UserCreateRequest",
    "LoginRequest",
    "LoginResponse",
    "PaymentRequest",
    # 枚举
    "SkillLevelEnum",
    "EmployeeStatusEnum",
    "TrainingDataTypeEnum",
    "TrainingStatusEnum",
    "RiskLevelEnum",
    "TenantStatusEnum",
    "UserRoleEnum",
    "BillingCycleEnum",
    "InvoiceStatusEnum",
    "PaymentStatusEnum",
    "PaymentMethodEnum",
    "OrderStatusEnum",
]
