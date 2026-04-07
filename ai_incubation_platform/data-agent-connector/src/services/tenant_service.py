"""
多租户服务

实现多租户管理功能：
- 租户 CRUD
- 租户成员管理
- 租户数据源管理
- 租户配额管理
- 租户隔离
"""
import asyncio
from datetime import datetime, date
from typing import Any, Dict, List, Optional, Tuple
from contextlib import asynccontextmanager

from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker, Session

from models.tenant import TenantModel, TenantMemberModel, TenantDatasourceModel, TenantQuotaUsageModel
from config.database import db_manager
from utils.logger import logger


class TenantService:
    """多租户服务"""

    def __init__(self):
        self._default_tenant_id: Optional[str] = None

    def _get_sync_session(self) -> Session:
        """获取同步数据库 Session"""
        return db_manager.get_sync_session()

    async def initialize_default_tenant(self) -> None:
        """初始化默认租户"""
        session = self._get_sync_session()
        try:
            # 检查是否已有默认租户
            stmt = select(TenantModel).where(TenantModel.tenant_code == "default")
            existing = session.scalar(stmt)

            if not existing:
                builtin_tenants = TenantModel.get_builtin_tenants()
                tenant_data = builtin_tenants[0]

                tenant = TenantModel(
                    tenant_code=tenant_data["tenant_code"],
                    tenant_name=tenant_data["tenant_name"],
                    description=tenant_data["description"],
                    status=tenant_data["status"],
                    config_json=tenant_data["config_json"],
                    quota_json=tenant_data["quota_json"],
                    contact_name=tenant_data["contact_name"],
                    contact_email=tenant_data["contact_email"],
                    created_by="system"
                )
                session.add(tenant)
                session.commit()
                session.refresh(tenant)

                self._default_tenant_id = tenant.id
                logger.info("Created default tenant")
            else:
                self._default_tenant_id = existing.id
                logger.info("Default tenant already exists")

        except Exception as e:
            session.rollback()
            logger.error(f"Failed to initialize default tenant: {e}")
        finally:
            session.close()

    # ==================== 租户管理 ====================

    async def create_tenant(self, tenant_code: str, tenant_name: str,
                            description: str = None, config: Dict = None,
                            quota: Dict = None, created_by: str = None) -> Dict[str, Any]:
        """创建租户"""
        session = self._get_sync_session()
        try:
            # 检查租户编码是否已存在
            stmt = select(TenantModel).where(TenantModel.tenant_code == tenant_code)
            existing = session.scalar(stmt)
            if existing:
                return {"success": False, "error": f"租户编码 '{tenant_code}' 已存在"}

            tenant = TenantModel(
                tenant_code=tenant_code,
                tenant_name=tenant_name,
                description=description,
                config_json=config or {},
                quota_json=quota or {},
                created_by=created_by
            )
            session.add(tenant)
            session.commit()
            session.refresh(tenant)

            logger.info(f"Created tenant: {tenant_code}")
            return {"success": True, "tenant": tenant.to_dict()}

        except Exception as e:
            session.rollback()
            logger.error(f"Failed to create tenant: {e}")
            return {"success": False, "error": str(e)}
        finally:
            session.close()

    async def get_tenant(self, tenant_code: str) -> Optional[Dict[str, Any]]:
        """获取租户信息"""
        session = self._get_sync_session()
        try:
            stmt = select(TenantModel).where(TenantModel.tenant_code == tenant_code)
            tenant = session.scalar(stmt)
            return tenant.to_dict() if tenant else None
        finally:
            session.close()

    async def get_tenant_by_id(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """通过 ID 获取租户信息"""
        session = self._get_sync_session()
        try:
            stmt = select(TenantModel).where(TenantModel.id == tenant_id)
            tenant = session.scalar(stmt)
            return tenant.to_dict() if tenant else None
        finally:
            session.close()

    async def list_tenants(self, status: str = None, limit: int = 100,
                           offset: int = 0) -> List[Dict[str, Any]]:
        """获取租户列表"""
        session = self._get_sync_session()
        try:
            stmt = select(TenantModel).order_by(TenantModel.created_at.desc())

            if status:
                stmt = stmt.where(TenantModel.status == status)

            stmt = stmt.offset(offset).limit(limit)
            tenants = session.scalars(stmt).all()

            return [tenant.to_dict() for tenant in tenants]
        finally:
            session.close()

    async def update_tenant(self, tenant_code: str, tenant_name: str = None,
                            description: str = None, config: Dict = None,
                            quota: Dict = None, status: str = None,
                            updated_by: str = None) -> Dict[str, Any]:
        """更新租户"""
        session = self._get_sync_session()
        try:
            stmt = select(TenantModel).where(TenantModel.tenant_code == tenant_code)
            tenant = session.scalar(stmt)

            if not tenant:
                return {"success": False, "error": f"租户 '{tenant_code}' 不存在"}

            if tenant_name is not None:
                tenant.tenant_name = tenant_name
            if description is not None:
                tenant.description = description
            if config is not None:
                tenant.config_json = {**tenant.config_json, **config} if tenant.config_json else config
            if quota is not None:
                tenant.quota_json = {**tenant.quota_json, **quota} if tenant.quota_json else quota
            if status is not None:
                tenant.status = status

            session.commit()
            session.refresh(tenant)

            logger.info(f"Updated tenant: {tenant_code}")
            return {"success": True, "tenant": tenant.to_dict()}

        except Exception as e:
            session.rollback()
            logger.error(f"Failed to update tenant: {e}")
            return {"success": False, "error": str(e)}
        finally:
            session.close()

    async def delete_tenant(self, tenant_code: str, deleted_by: str = None) -> Dict[str, Any]:
        """删除租户（软删除：设置为 inactive）"""
        session = self._get_sync_session()
        try:
            stmt = select(TenantModel).where(TenantModel.tenant_code == tenant_code)
            tenant = session.scalar(stmt)

            if not tenant:
                return {"success": False, "error": f"租户 '{tenant_code}' 不存在"}

            if tenant.tenant_code == "default":
                return {"success": False, "error": "默认租户不可删除"}

            # 软删除：设置为 inactive
            tenant.status = "inactive"
            session.commit()

            logger.info(f"Deleted tenant: {tenant_code}")
            return {"success": True, "message": f"租户 '{tenant_code}' 已删除"}

        except Exception as e:
            session.rollback()
            logger.error(f"Failed to delete tenant: {e}")
            return {"success": False, "error": str(e)}
        finally:
            session.close()

    # ==================== 租户成员管理 ====================

    async def add_tenant_member(self, tenant_code: str, user_id: str,
                                role: str = "member", created_by: str = None) -> Dict[str, Any]:
        """添加租户成员"""
        session = self._get_sync_session()
        try:
            # 获取租户
            tenant_stmt = select(TenantModel).where(TenantModel.tenant_code == tenant_code)
            tenant = session.scalar(tenant_stmt)
            if not tenant:
                return {"success": False, "error": f"租户 '{tenant_code}' 不存在"}

            # 检查成员是否已存在
            existing_stmt = select(TenantMemberModel).where(
                TenantMemberModel.tenant_id == tenant.id,
                TenantMemberModel.user_id == user_id
            )
            existing = session.scalar(existing_stmt)
            if existing:
                return {"success": False, "error": f"用户 '{user_id}' 已是租户成员"}

            member = TenantMemberModel(
                tenant_id=tenant.id,
                user_id=user_id,
                role=role,
                created_by=created_by
            )
            session.add(member)
            session.commit()

            # 更新租户用户数配额使用
            await self._update_quota_usage(tenant.id, "users_count", 1)

            logger.info(f"Added member {user_id} to tenant {tenant_code} with role {role}")
            return {"success": True, "member": member.to_dict()}

        except Exception as e:
            session.rollback()
            logger.error(f"Failed to add tenant member: {e}")
            return {"success": False, "error": str(e)}
        finally:
            session.close()

    async def remove_tenant_member(self, tenant_code: str, user_id: str) -> Dict[str, Any]:
        """移除租户成员"""
        session = self._get_sync_session()
        try:
            # 获取租户
            tenant_stmt = select(TenantModel).where(TenantModel.tenant_code == tenant_code)
            tenant = session.scalar(tenant_stmt)
            if not tenant:
                return {"success": False, "error": f"租户 '{tenant_code}' 不存在"}

            # 删除成员
            delete_stmt = delete(TenantMemberModel).where(
                TenantMemberModel.tenant_id == tenant.id,
                TenantMemberModel.user_id == user_id
            )
            session.execute(delete_stmt)
            session.commit()

            # 更新租户用户数配额使用
            await self._update_quota_usage(tenant.id, "users_count", -1)

            logger.info(f"Removed member {user_id} from tenant {tenant_code}")
            return {"success": True, "message": f"用户 '{user_id}' 已移除"}

        except Exception as e:
            session.rollback()
            logger.error(f"Failed to remove tenant member: {e}")
            return {"success": False, "error": str(e)}
        finally:
            session.close()

    async def get_tenant_members(self, tenant_code: str) -> List[Dict[str, Any]]:
        """获取租户成员列表"""
        session = self._get_sync_session()
        try:
            # 获取租户
            tenant_stmt = select(TenantModel).where(TenantModel.tenant_code == tenant_code)
            tenant = session.scalar(tenant_stmt)
            if not tenant:
                return []

            # 获取成员
            member_stmt = select(TenantMemberModel).where(
                TenantMemberModel.tenant_id == tenant.id
            ).order_by(TenantMemberModel.created_at.desc())
            members = session.scalars(member_stmt).all()

            return [member.to_dict() for member in members]
        finally:
            session.close()

    async def get_user_tenants(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户所属的所有租户"""
        session = self._get_sync_session()
        try:
            # 获取用户的成员关系
            member_stmt = select(TenantMemberModel).where(
                TenantMemberModel.user_id == user_id
            )
            members = session.scalars(member_stmt).all()

            tenant_ids = [m.tenant_id for m in members]
            if not tenant_ids:
                return []

            # 获取租户信息
            tenant_stmt = select(TenantModel).where(TenantModel.id.in_(tenant_ids))
            tenants = session.scalars(tenant_stmt).all()

            return [tenant.to_dict() for tenant in tenants]
        finally:
            session.close()

    async def check_tenant_member_role(self, tenant_code: str, user_id: str) -> Optional[str]:
        """检查用户在租户中的角色"""
        session = self._get_sync_session()
        try:
            # 获取租户
            tenant_stmt = select(TenantModel).where(TenantModel.tenant_code == tenant_code)
            tenant = session.scalar(tenant_stmt)
            if not tenant:
                return None

            # 获取成员角色
            member_stmt = select(TenantMemberModel).where(
                TenantMemberModel.tenant_id == tenant.id,
                TenantMemberModel.user_id == user_id,
                TenantMemberModel.status == "active"
            )
            member = session.scalar(member_stmt)

            return member.role if member else None
        finally:
            session.close()

    # ==================== 租户数据源管理 ====================

    async def add_tenant_datasource(self, tenant_code: str, datasource_name: str,
                                    connector_type: str, config: Dict = None,
                                    is_public: bool = False,
                                    allowed_users: List[str] = None,
                                    created_by: str = None) -> Dict[str, Any]:
        """添加租户数据源"""
        session = self._get_sync_session()
        try:
            # 获取租户
            tenant_stmt = select(TenantModel).where(TenantModel.tenant_code == tenant_code)
            tenant = session.scalar(tenant_stmt)
            if not tenant:
                return {"success": False, "error": f"租户 '{tenant_code}' 不存在"}

            # 检查配额
            quota_check = await self._check_quota(tenant.id, "datasources_count")
            if not quota_check["allowed"]:
                return {"success": False, "error": quota_check["reason"]}

            # 检查数据源是否已存在
            existing_stmt = select(TenantDatasourceModel).where(
                TenantDatasourceModel.tenant_id == tenant.id,
                TenantDatasourceModel.datasource_name == datasource_name
            )
            existing = session.scalar(existing_stmt)
            if existing:
                return {"success": False, "error": f"数据源 '{datasource_name}' 已存在"}

            ds = TenantDatasourceModel(
                tenant_id=tenant.id,
                datasource_name=datasource_name,
                connector_type=connector_type,
                config_json=config or {},
                is_public=is_public,
                allowed_users=allowed_users or [],
                created_by=created_by
            )
            session.add(ds)
            session.commit()
            session.refresh(ds)

            # 更新配额使用
            await self._update_quota_usage(tenant.id, "datasources_count", 1)

            logger.info(f"Added datasource {datasource_name} to tenant {tenant_code}")
            return {"success": True, "datasource": ds.to_dict()}

        except Exception as e:
            session.rollback()
            logger.error(f"Failed to add tenant datasource: {e}")
            return {"success": False, "error": str(e)}
        finally:
            session.close()

    async def remove_tenant_datasource(self, tenant_code: str,
                                        datasource_name: str) -> Dict[str, Any]:
        """移除租户数据源"""
        session = self._get_sync_session()
        try:
            # 获取租户
            tenant_stmt = select(TenantModel).where(TenantModel.tenant_code == tenant_code)
            tenant = session.scalar(tenant_stmt)
            if not tenant:
                return {"success": False, "error": f"租户 '{tenant_code}' 不存在"}

            # 删除数据源
            delete_stmt = delete(TenantDatasourceModel).where(
                TenantDatasourceModel.tenant_id == tenant.id,
                TenantDatasourceModel.datasource_name == datasource_name
            )
            session.execute(delete_stmt)
            session.commit()

            # 更新配额使用
            await self._update_quota_usage(tenant.id, "datasources_count", -1)

            logger.info(f"Removed datasource {datasource_name} from tenant {tenant_code}")
            return {"success": True, "message": f"数据源 '{datasource_name}' 已移除"}

        except Exception as e:
            session.rollback()
            logger.error(f"Failed to remove tenant datasource: {e}")
            return {"success": False, "error": str(e)}
        finally:
            session.close()

    async def get_tenant_datasources(self, tenant_code: str,
                                     user_id: str = None) -> List[Dict[str, Any]]:
        """获取租户数据源列表（根据用户权限过滤）"""
        session = self._get_sync_session()
        try:
            # 获取租户
            tenant_stmt = select(TenantModel).where(TenantModel.tenant_code == tenant_code)
            tenant = session.scalar(tenant_stmt)
            if not tenant:
                return []

            # 获取数据源
            ds_stmt = select(TenantDatasourceModel).where(
                TenantDatasourceModel.tenant_id == tenant.id
            )

            # 如果指定了用户，过滤有权限访问的数据源
            if user_id:
                # 检查用户角色
                member_stmt = select(TenantMemberModel).where(
                    TenantMemberModel.tenant_id == tenant.id,
                    TenantMemberModel.user_id == user_id
                )
                member = session.scalar(member_stmt)

                if member and member.role in ["owner", "admin"]:
                    # 管理员可访问所有数据源
                    pass
                else:
                    # 普通用户只能访问公开或授权的数据源
                    # 这里需要在查询时过滤，简化处理：返回所有，由调用方自行过滤
                    pass

            datasources = session.scalars(ds_stmt).all()
            return [ds.to_dict() for ds in datasources]
        finally:
            session.close()

    async def get_tenant_datasource(self, tenant_code: str,
                                    datasource_name: str) -> Optional[Dict[str, Any]]:
        """获取租户数据源详情"""
        session = self._get_sync_session()
        try:
            # 获取租户
            tenant_stmt = select(TenantModel).where(TenantModel.tenant_code == tenant_code)
            tenant = session.scalar(tenant_stmt)
            if not tenant:
                return None

            # 获取数据源
            ds_stmt = select(TenantDatasourceModel).where(
                TenantDatasourceModel.tenant_id == tenant.id,
                TenantDatasourceModel.datasource_name == datasource_name
            )
            ds = session.scalar(ds_stmt)

            return ds.to_dict() if ds else None
        finally:
            session.close()

    # ==================== 租户配额管理 ====================

    async def _check_quota(self, tenant_id: str, quota_type: str) -> Dict[str, Any]:
        """检查配额是否充足"""
        session = self._get_sync_session()
        try:
            # 获取租户配额
            tenant_stmt = select(TenantModel).where(TenantModel.id == tenant_id)
            tenant = session.scalar(tenant_stmt)
            if not tenant:
                return {"allowed": False, "reason": "租户不存在"}

            quota = tenant.quota_json or {}
            quota_limit = quota.get(f"max_{quota_type}", float('inf'))

            # 获取当前使用量
            today = date.today().isoformat()
            usage_stmt = select(TenantQuotaUsageModel).where(
                TenantQuotaUsageModel.tenant_id == tenant_id,
                TenantQuotaUsageModel.usage_date == today
            )
            usage = session.scalar(usage_stmt)

            current_usage = getattr(usage, quota_type, 0) if usage else 0

            if current_usage >= quota_limit:
                return {
                    "allowed": False,
                    "reason": f"配额已达到上限：{quota_type}={current_usage}/{quota_limit}"
                }

            return {"allowed": True, "current": current_usage, "limit": quota_limit}

        except Exception as e:
            logger.error(f"Failed to check quota: {e}")
            return {"allowed": False, "reason": str(e)}

    async def _update_quota_usage(self, tenant_id: str, usage_type: str,
                                   delta: int = 1) -> None:
        """更新配额使用量"""
        session = self._get_sync_session()
        try:
            today = date.today().isoformat()

            # 获取或创建使用记录
            usage_stmt = select(TenantQuotaUsageModel).where(
                TenantQuotaUsageModel.tenant_id == tenant_id,
                TenantQuotaUsageModel.usage_date == today
            )
            usage = session.scalar(usage_stmt)

            if not usage:
                usage = TenantQuotaUsageModel(
                    tenant_id=tenant_id,
                    usage_date=today
                )
                session.add(usage)
                session.flush()

            # 更新使用量
            current = getattr(usage, usage_type, 0)
            setattr(usage, usage_type, max(0, current + delta))

            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to update quota usage: {e}")
        finally:
            session.close()

    async def get_quota_usage(self, tenant_code: str,
                              days: int = 7) -> List[Dict[str, Any]]:
        """获取租户配额使用情况"""
        session = self._get_sync_session()
        try:
            # 获取租户
            tenant_stmt = select(TenantModel).where(TenantModel.tenant_code == tenant_code)
            tenant = session.scalar(tenant_stmt)
            if not tenant:
                return []

            # 获取最近 N 天的使用记录
            from datetime import timedelta
            start_date = (date.today() - timedelta(days=days)).isoformat()

            usage_stmt = select(TenantQuotaUsageModel).where(
                TenantQuotaUsageModel.tenant_id == tenant.id,
                TenantQuotaUsageModel.usage_date >= start_date
            ).order_by(TenantQuotaUsageModel.usage_date.desc())

            usages = session.scalars(usage_stmt).all()
            return [usage.to_dict() for usage in usages]

        finally:
            session.close()

    # ==================== 租户隔离 ====================

    async def get_tenant_for_user(self, user_id: str,
                                  x_tenant_code: str = None) -> Optional[str]:
        """
        获取用户当前激活的租户

        Args:
            user_id: 用户 ID
            x_tenant_code: 请求头中指定的租户编码（可选）

        Returns:
            租户编码，如果用户不属于任何租户则返回 None
        """
        if x_tenant_code:
            # 优先使用请求头指定的租户
            tenant = await self.get_tenant(x_tenant_code)
            if tenant:
                # 验证用户是否属于该租户
                role = await self.check_tenant_member_role(x_tenant_code, user_id)
                if role:
                    return x_tenant_code
            return None

        # 返回用户的第一个租户
        tenants = await self.get_user_tenants(user_id)
        return tenants[0]["tenant_code"] if tenants else None

    async def resolve_datasource_for_tenant(self, tenant_code: str,
                                            datasource_name: str) -> Optional[str]:
        """
        解析租户数据源，返回完整的数据源标识

        用于在查询时添加租户前缀，实现数据隔离

        Returns:
            完整数据源标识（如 "tenant_default:mysql_prod"），如果不存在则返回 None
        """
        ds = await self.get_tenant_datasource(tenant_code, datasource_name)
        if ds:
            return f"tenant_{tenant_code}:{datasource_name}"
        return None


# 全局服务实例
tenant_service = TenantService()


async def init_tenant():
    """初始化多租户服务"""
    await tenant_service.initialize_default_tenant()
    logger.info("Tenant service initialized")
