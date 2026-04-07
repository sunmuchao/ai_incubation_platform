"""
v1.6 - 配额与计费管理 API

提供配额管理、计费管理、套餐包相关的 API 端点
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from config.database import get_db
from services.quota_service import QuotaService, get_quota_service
from services.billing_service import BillingService, get_billing_service
from services.tenant_service import TenantService, get_tenant_service
from models.db_models import BillingMode, QuotaType, TenantType

router = APIRouter(prefix="/api/v1.6", tags=["v1.6 配额与计费"])


# ==================== Pydantic 模型 ====================


class RecordUsageRequest(BaseModel):
    """记录使用量请求"""
    feature_name: str = Field(..., description="功能名称")
    count: int = Field(1, description="使用数量")
    tenant_id: Optional[str] = Field(None, description="租户 ID")


class CheckQuotaRequest(BaseModel):
    """检查配额请求"""
    user_id: str = Field(..., description="用户 ID")
    feature_name: str = Field(..., description="功能名称")
    count: int = Field(1, description="请求数量")


class UpdateQuotaConfigRequest(BaseModel):
    """更新配额配置请求"""
    limit_value: Optional[int] = Field(None, description="限制值")
    overage_policy: Optional[str] = Field(None, description="超额处理策略")
    overage_price: Optional[float] = Field(None, description="超额单价")


class CreateBillingItemRequest(BaseModel):
    """创建计费项目请求"""
    item_name: str = Field(..., description="项目名称")
    item_type: str = Field(..., description="项目类型")
    quantity: float = Field(..., description="数量")
    tenant_id: Optional[str] = Field(None, description="租户 ID")
    related_order_id: Optional[str] = Field(None, description="关联订单 ID")
    related_resource_id: Optional[str] = Field(None, description="关联资源 ID")


class PurchasePackageRequest(BaseModel):
    """购买套餐包请求"""
    package_code: str = Field(..., description="套餐包代码")
    order_id: Optional[str] = Field(None, description="关联订单 ID")


class ConsumePackageCreditRequest(BaseModel):
    """消耗套餐包额度请求"""
    credit_type: str = Field(..., description="额度类型 (credits/storage_gb/exports)")
    count: int = Field(1, description="消耗数量")


class CreateTenantRequest(BaseModel):
    """创建租户请求"""
    name: str = Field(..., description="租户名称")
    tenant_type: str = Field("individual", description="租户类型 (individual/team/enterprise)")
    creator_user_id: Optional[str] = Field(None, description="创建者用户 ID")


class UpdateTenantRequest(BaseModel):
    """更新租户请求"""
    name: Optional[str] = Field(None, description="租户名称")
    custom_branding: Optional[Dict] = Field(None, description="自定义品牌配置")
    custom_domain: Optional[str] = Field(None, description="自定义域名")


class AddTenantUserRequest(BaseModel):
    """添加租户用户请求"""
    user_id: str = Field(..., description="用户 ID")
    role: Optional[str] = Field("member", description="用户角色")
    permissions: Optional[List[str]] = Field(None, description="自定义权限列表")


class ConfigureSSORequest(BaseModel):
    """配置 SSO 请求"""
    provider: str = Field(..., description="SSO 提供商 (okta/azure_ad/google_workspace)")
    config: Dict[str, Any] = Field(..., description="SSO 配置详情")


class ConfigureBrandingRequest(BaseModel):
    """配置品牌请求"""
    logo_url: Optional[str] = Field(None, description="Logo URL")
    primary_color: Optional[str] = Field(None, description="主色调")
    secondary_color: Optional[str] = Field(None, description="辅助色")
    company_name: Optional[str] = Field(None, description="公司名称")


# ==================== 配额管理 API ====================


@router.post("/quota/record-usage", summary="记录配额使用")
async def record_usage(
    request: RecordUsageRequest,
    user_id: str = Query(..., description="用户 ID"),
    db: Session = Depends(get_db),
):
    """
    记录配额使用

    - 自动根据用户订阅等级检查配额限制
    - 支持超额处理（阻止/按量计费/通知）
    """
    quota_service = get_quota_service(db)

    try:
        result = quota_service.record_usage(
            user_id=user_id,
            feature_name=request.feature_name,
            count=request.count,
            tenant_id=request.tenant_id,
        )

        if not result["allowed"]:
            raise HTTPException(
                status_code=429,
                detail={
                    "code": "QUOTA_EXCEEDED",
                    "feature": request.feature_name,
                    "limit": result["limit"],
                    "used": result["used_count"],
                    "policy": result["policy"],
                }
            )

        return {
            "success": True,
            "data": result,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/quota/check", summary="检查配额")
async def check_quota(
    request: CheckQuotaRequest,
    db: Session = Depends(get_db),
):
    """检查配额是否充足（不记录使用）"""
    quota_service = get_quota_service(db)

    result = quota_service.check_quota(
        user_id=request.user_id,
        feature_name=request.feature_name,
        count=request.count,
    )

    return {
        "success": True,
        "data": result,
    }


@router.get("/quota/configs", summary="获取配额配置")
async def get_quota_configs(
    subscription_tier: str = Query("free", description="订阅等级"),
    db: Session = Depends(get_db),
):
    """获取某订阅等级的所有配额配置"""
    quota_service = get_quota_service(db)
    configs = quota_service.get_all_quota_configs(subscription_tier)

    return {
        "success": True,
        "data": [config.to_dict() for config in configs],
    }


@router.get("/quota/stats", summary="获取配额使用统计")
async def get_quota_stats(
    user_id: str = Query(..., description="用户 ID"),
    feature_name: Optional[str] = Query(None, description="功能名称"),
    db: Session = Depends(get_db),
):
    """获取配额使用统计"""
    quota_service = get_quota_service(db)
    stats = quota_service.get_usage_stats(
        user_id=user_id,
        feature_name=feature_name,
    )

    return {
        "success": True,
        "data": stats,
    }


@router.put("/quota/config", summary="更新配额配置")
async def update_quota_config(
    request: UpdateQuotaConfigRequest,
    subscription_tier: str = Query(..., description="订阅等级"),
    feature_name: str = Query(..., description="功能名称"),
    db: Session = Depends(get_db),
):
    """更新配额配置（管理员操作）"""
    quota_service = get_quota_service(db)

    try:
        config = quota_service.update_quota_config(
            subscription_tier=subscription_tier,
            feature_name=feature_name,
            limit_value=request.limit_value,
            overage_policy=request.overage_policy,
            overage_price=request.overage_price,
        )

        return {
            "success": True,
            "data": config.to_dict(),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 计费管理 API ====================


@router.get("/billing/account", summary="获取计费账户信息")
async def get_billing_account(
    user_id: str = Query(..., description="用户 ID"),
    db: Session = Depends(get_db),
):
    """获取计费账户信息"""
    billing_service = get_billing_service(db)

    account = billing_service.get_billing_account(user_id)
    if not account:
        # 自动创建
        account = billing_service.create_billing_account(user_id)

    return {
        "success": True,
        "data": billing_service.get_account_balance(user_id),
    }


@router.post("/billing/mode", summary="更新计费模式")
async def update_billing_mode(
    new_mode: str = Query(..., description="计费模式 (subscription/pay_as_you_go/prepaid)"),
    user_id: str = Query(..., description="用户 ID"),
    db: Session = Depends(get_db),
):
    """更新计费模式"""
    billing_service = get_billing_service(db)

    try:
        mode = BillingMode(new_mode)
        account = billing_service.update_billing_mode(user_id, mode)

        return {
            "success": True,
            "data": {
                "user_id": user_id,
                "billing_mode": mode.value,
            },
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/billing/item", summary="创建计费项目")
async def create_billing_item(
    request: CreateBillingItemRequest,
    user_id: str = Query(..., description="用户 ID"),
    db: Session = Depends(get_db),
):
    """创建计费项目（按量计费）"""
    billing_service = get_billing_service(db)

    try:
        item = billing_service.create_billing_item(
            user_id=user_id,
            item_name=request.item_name,
            item_type=request.item_type,
            quantity=request.quantity,
            tenant_id=request.tenant_id,
            related_order_id=request.related_order_id,
            related_resource_id=request.related_resource_id,
        )

        return {
            "success": True,
            "data": item.to_dict(),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/billing/charge/{item_id}", summary="扣除计费项目费用")
async def charge_billing_item(
    item_id: str,
    user_id: str = Query(..., description="用户 ID"),
    db: Session = Depends(get_db),
):
    """从账户扣除计费项目费用"""
    billing_service = get_billing_service(db)

    try:
        result = billing_service.charge_billing_item(user_id, item_id)

        return {
            "success": True,
            "data": result,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 套餐包管理 API ====================


@router.get("/packages", summary="获取套餐包列表")
async def get_packages(
    db: Session = Depends(get_db),
):
    """获取所有可用的套餐包"""
    billing_service = get_billing_service(db)
    packages = billing_service.get_packages()

    return {
        "success": True,
        "data": [pkg.to_dict() for pkg in packages],
    }


@router.post("/packages/purchase", summary="购买套餐包")
async def purchase_package(
    request: PurchasePackageRequest,
    user_id: str = Query(..., description="用户 ID"),
    db: Session = Depends(get_db),
):
    """购买套餐包"""
    billing_service = get_billing_service(db)

    try:
        user_package = billing_service.purchase_package(
            user_id=user_id,
            package_code=request.package_code,
            order_id=request.order_id,
        )

        return {
            "success": True,
            "data": user_package.to_dict(),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/packages/my", summary="获取我的套餐包")
async def get_user_packages(
    user_id: str = Query(..., description="用户 ID"),
    status: Optional[str] = Query("active", description="状态"),
    db: Session = Depends(get_db),
):
    """获取用户购买的套餐包"""
    billing_service = get_billing_service(db)
    packages = billing_service.get_user_packages(user_id, status)

    return {
        "success": True,
        "data": [pkg.to_dict() for pkg in packages],
    }


@router.get("/packages/summary", summary="获取套餐包汇总")
async def get_package_summary(
    user_id: str = Query(..., description="用户 ID"),
    db: Session = Depends(get_db),
):
    """获取用户套餐包汇总信息"""
    billing_service = get_billing_service(db)
    summary = billing_service.get_package_summary(user_id)

    return {
        "success": True,
        "data": summary,
    }


@router.post("/packages/consume", summary="消耗套餐包额度")
async def consume_package_credit(
    request: ConsumePackageCreditRequest,
    user_id: str = Query(..., description="用户 ID"),
    db: Session = Depends(get_db),
):
    """消耗套餐包额度"""
    billing_service = get_billing_service(db)

    try:
        result = billing_service.consume_package_credit(
            user_id=user_id,
            credit_type=request.credit_type,
            count=request.count,
        )

        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["message"])

        return {
            "success": True,
            "data": result,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 充值管理 API ====================


@router.get("/billing/recharge-history", summary="获取充值历史")
async def get_recharge_history(
    user_id: str = Query(..., description="用户 ID"),
    limit: int = Query(50, description="返回数量限制"),
    db: Session = Depends(get_db),
):
    """获取用户充值历史记录"""
    billing_service = get_billing_service(db)
    records = billing_service.get_recharge_history(user_id, limit)

    return {
        "success": True,
        "data": [record.to_dict() for record in records],
    }


# ==================== 租户管理 API ====================


@router.post("/tenants", summary="创建租户")
async def create_tenant(
    request: CreateTenantRequest,
    db: Session = Depends(get_db),
):
    """创建新租户"""
    tenant_service = get_tenant_service(db)

    try:
        tenant_type = TenantType(request.tenant_type)
        tenant = tenant_service.create_tenant(
            name=request.name,
            tenant_type=tenant_type,
            creator_user_id=request.creator_user_id,
        )

        return {
            "success": True,
            "data": tenant.to_dict(),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/tenants/{tenant_id}", summary="获取租户信息")
async def get_tenant(
    tenant_id: str,
    db: Session = Depends(get_db),
):
    """获取租户详细信息"""
    tenant_service = get_tenant_service(db)
    tenant = tenant_service.get_tenant(tenant_id)

    if not tenant:
        raise HTTPException(status_code=404, detail="租户不存在")

    return {
        "success": True,
        "data": tenant.to_dict(),
    }


@router.put("/tenants/{tenant_id}", summary="更新租户信息")
async def update_tenant(
    tenant_id: str,
    request: UpdateTenantRequest,
    db: Session = Depends(get_db),
):
    """更新租户信息"""
    tenant_service = get_tenant_service(db)

    try:
        tenant = tenant_service.update_tenant(
            tenant_id=tenant_id,
            name=request.name,
            custom_branding=request.custom_branding,
            custom_domain=request.custom_domain,
        )

        return {
            "success": True,
            "data": tenant.to_dict(),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/tenants/{tenant_id}/users", summary="获取租户用户列表")
async def get_tenant_users(
    tenant_id: str,
    db: Session = Depends(get_db),
):
    """获取租户下的所有用户"""
    tenant_service = get_tenant_service(db)
    users = tenant_service.get_tenant_users(tenant_id)

    return {
        "success": True,
        "data": users,
    }


@router.post("/tenants/{tenant_id}/users", summary="添加租户用户")
async def add_tenant_user(
    tenant_id: str,
    request: AddTenantUserRequest,
    db: Session = Depends(get_db),
):
    """添加用户到租户"""
    tenant_service = get_tenant_service(db)

    try:
        tenant_user = tenant_service.add_tenant_user(
            tenant_id=tenant_id,
            user_id=request.user_id,
            role=request.role,
            permissions=request.permissions,
        )

        return {
            "success": True,
            "data": {
                "tenant_user_id": tenant_user.id,
                "user_id": tenant_user.user_id,
                "role": tenant_user.role,
                "permissions": tenant_user.permissions,
            },
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/tenants/{tenant_id}/users/{user_id}", summary="移除租户用户")
async def remove_tenant_user(
    tenant_id: str,
    user_id: str,
    db: Session = Depends(get_db),
):
    """从租户移除用户"""
    tenant_service = get_tenant_service(db)

    try:
        tenant_service.remove_tenant_user(tenant_id, user_id)

        return {
            "success": True,
            "message": "用户已移除",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/tenants/{tenant_id}/sso", summary="配置 SSO")
async def configure_sso(
    tenant_id: str,
    request: ConfigureSSORequest,
    db: Session = Depends(get_db),
):
    """配置 SSO 单点登录"""
    tenant_service = get_tenant_service(db)

    try:
        tenant = tenant_service.configure_sso(
            tenant_id=tenant_id,
            provider=request.provider,
            config=request.config,
        )

        return {
            "success": True,
            "data": {
                "sso_enabled": tenant.sso_enabled,
                "sso_provider": tenant.sso_provider,
            },
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/tenants/{tenant_id}/sso", summary="禁用 SSO")
async def disable_sso(
    tenant_id: str,
    db: Session = Depends(get_db),
):
    """禁用 SSO"""
    tenant_service = get_tenant_service(db)

    try:
        tenant = tenant_service.disable_sso(tenant_id)

        return {
            "success": True,
            "data": {
                "sso_enabled": tenant.sso_enabled,
            },
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/tenants/{tenant_id}/sso", summary="获取 SSO 配置")
async def get_sso_config(
    tenant_id: str,
    db: Session = Depends(get_db),
):
    """获取 SSO 配置"""
    tenant_service = get_tenant_service(db)
    config = tenant_service.get_sso_config(tenant_id)

    return {
        "success": True,
        "data": config,
    }


@router.post("/tenants/{tenant_id}/branding", summary="配置品牌")
async def configure_branding(
    tenant_id: str,
    request: ConfigureBrandingRequest,
    db: Session = Depends(get_db),
):
    """配置自定义品牌"""
    tenant_service = get_tenant_service(db)

    branding = {
        "logo_url": request.logo_url,
        "primary_color": request.primary_color,
        "secondary_color": request.secondary_color,
        "company_name": request.company_name,
    }

    try:
        tenant = tenant_service.configure_branding(
            tenant_id=tenant_id,
            branding=branding,
        )

        return {
            "success": True,
            "data": tenant.custom_branding,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/tenants/{tenant_id}/branding", summary="获取品牌配置")
async def get_branding(
    tenant_id: str,
    db: Session = Depends(get_db),
):
    """获取品牌配置"""
    tenant_service = get_tenant_service(db)
    branding = tenant_service.get_branding(tenant_id)

    return {
        "success": True,
        "data": branding,
    }


@router.get("/tenants/{tenant_id}/stats", summary="获取租户统计")
async def get_tenant_stats(
    tenant_id: str,
    db: Session = Depends(get_db),
):
    """获取租户统计信息"""
    tenant_service = get_tenant_service(db)
    stats = tenant_service.get_tenant_stats(tenant_id)

    return {
        "success": True,
        "data": stats,
    }


@router.get("/users/{user_id}/tenants", summary="获取用户所属租户")
async def get_user_tenants(
    user_id: str,
    db: Session = Depends(get_db),
):
    """获取用户所属的所有租户"""
    tenant_service = get_tenant_service(db)
    tenants = tenant_service.get_user_tenants(user_id)

    return {
        "success": True,
        "data": [tenant.to_dict() for tenant in tenants],
    }


# ==================== 初始化端点 ====================


@router.post("/init/quota-configs", summary="初始化配额配置")
async def init_quota_configs(
    db: Session = Depends(get_db),
):
    """初始化配额配置（管理员操作）"""
    quota_service = get_quota_service(db)
    quota_service.initialize_quota_configs()

    return {
        "success": True,
        "message": "配额配置初始化完成",
    }


@router.post("/init/packages", summary="初始化套餐包")
async def init_packages(
    db: Session = Depends(get_db),
):
    """初始化默认套餐包（管理员操作）"""
    billing_service = get_billing_service(db)
    billing_service.initialize_packages()

    return {
        "success": True,
        "message": "套餐包初始化完成",
    }
