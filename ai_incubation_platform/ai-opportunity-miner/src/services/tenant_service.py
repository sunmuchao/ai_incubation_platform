"""
v1.6 - 企业功能服务

功能：
1. 多租户管理
2. 租户用户管理
3. SSO 单点登录配置
4. 自定义品牌配置
5. 企业级权限管理
"""
import uuid
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import and_

from models.db_models import (
    TenantDB, TenantUserDB, UserDB, TenantType
)
import logging

logger = logging.getLogger(__name__)


class TenantService:
    """企业功能服务"""

    # 租户类型配置
    TENANT_CONFIGS = {
        TenantType.INDIVIDUAL: {
            "max_users": 1,
            "max_storage_gb": 10,
            "sso_enabled": False,
            "custom_branding": False,
            "custom_domain": False,
        },
        TenantType.TEAM: {
            "max_users": 10,
            "max_storage_gb": 100,
            "sso_enabled": False,
            "custom_branding": True,
            "custom_domain": False,
        },
        TenantType.ENTERPRISE: {
            "max_users": -1,  # 无限制
            "max_storage_gb": 1000,
            "sso_enabled": True,
            "custom_branding": True,
            "custom_domain": True,
        },
    }

    # 租户角色权限
    ROLE_PERMISSIONS = {
        "owner": [
            "tenant.manage",
            "user.manage",
            "billing.manage",
            "sso.manage",
            "branding.manage",
            "data.export",
            "data.delete",
            "reports.view",
            "reports.create",
        ],
        "admin": [
            "user.manage",
            "data.export",
            "reports.view",
            "reports.create",
        ],
        "member": [
            "data.export",
            "reports.view",
            "reports.create",
        ],
        "viewer": [
            "reports.view",
        ],
    }

    def __init__(self, db: Session):
        self.db = db

    # ==================== 租户管理 ====================

    def create_tenant(
        self,
        name: str,
        tenant_type: TenantType = TenantType.INDIVIDUAL,
        creator_user_id: str = None,
    ) -> TenantDB:
        """创建租户"""
        config = self.TENANT_CONFIGS.get(tenant_type, self.TENANT_CONFIGS[TenantType.INDIVIDUAL])

        tenant = TenantDB(
            id=str(uuid.uuid4()),
            name=name,
            type=tenant_type,
            max_users=config["max_users"],
            max_storage_gb=config["max_storage_gb"],
        )

        self.db.add(tenant)
        self.db.commit()
        self.db.refresh(tenant)

        # 创建者自动成为租户所有者
        if creator_user_id:
            self.add_tenant_user(tenant.id, creator_user_id, "owner")

        logger.info(f"创建租户：id={tenant.id}, name={name}, type={tenant_type.value}")
        return tenant

    def get_tenant(self, tenant_id: str) -> Optional[TenantDB]:
        """获取租户信息"""
        return self.db.query(TenantDB).filter(TenantDB.id == tenant_id).first()

    def update_tenant(
        self,
        tenant_id: str,
        name: str = None,
        custom_branding: Dict = None,
        custom_domain: str = None,
    ) -> TenantDB:
        """更新租户信息"""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            raise ValueError(f"租户不存在：{tenant_id}")

        if name:
            tenant.name = name
        if custom_branding is not None:
            tenant.custom_branding = custom_branding
        if custom_domain is not None:
            if tenant.type != TenantType.ENTERPRISE:
                raise ValueError("只有企业版租户可以设置自定义域名")
            tenant.custom_domain = custom_domain

        self.db.commit()
        self.db.refresh(tenant)

        logger.info(f"更新租户：id={tenant_id}")
        return tenant

    def delete_tenant(self, tenant_id: str):
        """删除租户"""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            raise ValueError(f"租户不存在：{tenant_id}")

        # 检查租户下是否有用户
        user_count = self.db.query(TenantUserDB).filter(
            TenantUserDB.tenant_id == tenant_id
        ).count()

        if user_count > 0:
            raise ValueError(f"租户下还有 {user_count} 个用户，无法删除")

        self.db.delete(tenant)
        self.db.commit()

        logger.info(f"删除租户：id={tenant_id}")

    def get_tenant_by_name(self, name: str) -> Optional[TenantDB]:
        """通过名称获取租户"""
        return self.db.query(TenantDB).filter(TenantDB.name == name).first()

    # ==================== SSO 配置 ====================

    def configure_sso(
        self,
        tenant_id: str,
        provider: str,
        config: Dict[str, Any],
    ) -> TenantDB:
        """配置 SSO 单点登录"""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            raise ValueError(f"租户不存在：{tenant_id}")

        if tenant.type != TenantType.ENTERPRISE:
            raise ValueError("只有企业版租户可以配置 SSO")

        tenant.sso_enabled = True
        tenant.sso_provider = provider
        tenant.sso_config = config

        self.db.commit()
        self.db.refresh(tenant)

        logger.info(f"配置 SSO: tenant={tenant_id}, provider={provider}")
        return tenant

    def disable_sso(self, tenant_id: str) -> TenantDB:
        """禁用 SSO"""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            raise ValueError(f"租户不存在：{tenant_id}")

        tenant.sso_enabled = False
        tenant.sso_provider = None
        tenant.sso_config = None

        self.db.commit()
        self.db.refresh(tenant)

        logger.info(f"禁用 SSO: tenant={tenant_id}")
        return tenant

    def get_sso_config(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """获取 SSO 配置"""
        tenant = self.get_tenant(tenant_id)
        if not tenant or not tenant.sso_enabled:
            return None

        return {
            "provider": tenant.sso_provider,
            "config": tenant.sso_config,
        }

    # ==================== 自定义品牌 ====================

    def configure_branding(
        self,
        tenant_id: str,
        branding: Dict[str, Any],
    ) -> TenantDB:
        """
        配置自定义品牌

        Args:
            tenant_id: 租户 ID
            branding: 品牌配置
                - logo_url: Logo URL
                - primary_color: 主色调
                - secondary_color: 辅助色
                - company_name: 公司名称
        """
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            raise ValueError(f"租户不存在：{tenant_id}")

        config = self.TENANT_CONFIGS.get(tenant.type)
        if not config or not config.get("custom_branding"):
            raise ValueError("该租户类型不支持自定义品牌")

        tenant.custom_branding = branding

        self.db.commit()
        self.db.refresh(tenant)

        logger.info(f"配置品牌：tenant={tenant_id}")
        return tenant

    def get_branding(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """获取品牌配置"""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return None

        return tenant.custom_branding

    # ==================== 租户用户管理 ====================

    def add_tenant_user(
        self,
        tenant_id: str,
        user_id: str,
        role: str = "member",
        permissions: List[str] = None,
    ) -> TenantUserDB:
        """添加租户用户"""
        # 检查租户是否存在
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            raise ValueError(f"租户不存在：{tenant_id}")

        # 检查用户是否存在
        user = self.db.query(UserDB).filter(UserDB.id == user_id).first()
        if not user:
            raise ValueError(f"用户不存在：{user_id}")

        # 检查租户用户数限制
        if tenant.max_users != -1:
            current_count = self.db.query(TenantUserDB).filter(
                TenantUserDB.tenant_id == tenant_id
            ).count()

            # 检查用户是否已经在租户中
            existing = self.db.query(TenantUserDB).filter(
                and_(
                    TenantUserDB.tenant_id == tenant_id,
                    TenantUserDB.user_id == user_id
                )
            ).first()

            if not existing and current_count >= tenant.max_users:
                raise ValueError(f"租户用户数已达上限：{tenant.max_users}")

        # 检查用户是否已在租户中
        existing = self.db.query(TenantUserDB).filter(
            and_(
                TenantUserDB.tenant_id == tenant_id,
                TenantUserDB.user_id == user_id
            )
        ).first()

        if existing:
            existing.role = role
            if permissions:
                existing.permissions = permissions
            self.db.commit()
            self.db.refresh(existing)
            logger.info(f"更新租户用户角色：tenant={tenant_id}, user={user_id}, role={role}")
            return existing

        # 添加新用户
        tenant_user = TenantUserDB(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            user_id=user_id,
            role=role,
            permissions=permissions or self.ROLE_PERMISSIONS.get(role, []),
        )

        self.db.add(tenant_user)
        self.db.commit()
        self.db.refresh(tenant_user)

        logger.info(f"添加租户用户：tenant={tenant_id}, user={user_id}, role={role}")
        return tenant_user

    def remove_tenant_user(self, tenant_id: str, user_id: str):
        """移除租户用户"""
        tenant_user = self.db.query(TenantUserDB).filter(
            and_(
                TenantUserDB.tenant_id == tenant_id,
                TenantUserDB.user_id == user_id
            )
        ).first()

        if not tenant_user:
            raise ValueError(f"用户不在租户中：tenant={tenant_id}, user={user_id}")

        # 不允许移除所有者
        if tenant_user.role == "owner":
            raise ValueError("不能移除租户所有者")

        self.db.delete(tenant_user)
        self.db.commit()

        logger.info(f"移除租户用户：tenant={tenant_id}, user={user_id}")

    def get_tenant_users(self, tenant_id: str) -> List[Dict[str, Any]]:
        """获取租户用户列表"""
        tenant_users = self.db.query(TenantUserDB).filter(
            TenantUserDB.tenant_id == tenant_id
        ).all()

        result = []
        for tu in tenant_users:
            user = self.db.query(UserDB).filter(UserDB.id == tu.user_id).first()
            result.append({
                "tenant_user_id": tu.id,
                "user_id": tu.user_id,
                "username": user.username if user else None,
                "email": user.email if user else None,
                "role": tu.role,
                "permissions": tu.permissions,
                "created_at": tu.created_at.isoformat(),
            })

        return result

    def get_user_tenants(self, user_id: str) -> List[TenantDB]:
        """获取用户所属的所有租户"""
        tenant_users = self.db.query(TenantUserDB).filter(
            TenantUserDB.user_id == user_id
        ).all()

        tenant_ids = [tu.tenant_id for tu in tenant_users]
        return self.db.query(TenantDB).filter(TenantDB.id.in_(tenant_ids)).all()

    def get_tenant_user(self, tenant_id: str, user_id: str) -> Optional[TenantUserDB]:
        """获取租户用户详情"""
        return self.db.query(TenantUserDB).filter(
            and_(
                TenantUserDB.tenant_id == tenant_id,
                TenantUserDB.user_id == user_id
            )
        ).first()

    def update_user_role(
        self,
        tenant_id: str,
        user_id: str,
        new_role: str,
    ) -> TenantUserDB:
        """更新用户角色"""
        tenant_user = self.get_tenant_user(tenant_id, user_id)
        if not tenant_user:
            raise ValueError(f"用户不在租户中：tenant={tenant_id}, user={user_id}")

        tenant_user.role = new_role
        tenant_user.permissions = self.ROLE_PERMISSIONS.get(new_role, [])

        self.db.commit()
        self.db.refresh(tenant_user)

        logger.info(f"更新用户角色：tenant={tenant_id}, user={user_id}, new_role={new_role}")
        return tenant_user

    def check_user_permission(self, tenant_id: str, user_id: str, permission: str) -> bool:
        """检查用户是否有指定权限"""
        tenant_user = self.get_tenant_user(tenant_id, user_id)
        if not tenant_user:
            return False

        # 所有者拥有所有权限
        if tenant_user.role == "owner":
            return True

        # 检查权限列表
        permissions = tenant_user.permissions or []
        return permission in permissions

    # ==================== 租户统计 ====================

    def get_tenant_stats(self, tenant_id: str) -> Dict[str, Any]:
        """获取租户统计信息"""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return {}

        # 用户统计
        user_count = self.db.query(TenantUserDB).filter(
            TenantUserDB.tenant_id == tenant_id
        ).count()

        # 角色统计
        role_stats = {}
        for role in ["owner", "admin", "member", "viewer"]:
            count = self.db.query(TenantUserDB).filter(
                and_(
                    TenantUserDB.tenant_id == tenant_id,
                    TenantUserDB.role == role
                )
            ).count()
            role_stats[role] = count

        return {
            "tenant_id": tenant_id,
            "tenant_name": tenant.name,
            "tenant_type": tenant.type.value if tenant.type else None,
            "user_count": user_count,
            "max_users": tenant.max_users,
            "max_storage_gb": tenant.max_storage_gb,
            "sso_enabled": tenant.sso_enabled,
            "custom_domain": tenant.custom_domain,
            "role_stats": role_stats,
        }


# 全局单例
def get_tenant_service(db: Session) -> TenantService:
    """获取租户服务实例"""
    return TenantService(db)
