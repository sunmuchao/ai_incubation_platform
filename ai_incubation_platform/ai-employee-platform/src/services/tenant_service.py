"""
租户管理服务
负责租户的 CRUD 操作
"""
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select

from models.db_models import TenantDB, TenantStatusEnum, BillingCycleEnum
from services.base_service import BaseService
from config.settings import settings


class TenantService(BaseService):
    """租户服务"""

    def create_tenant(
        self,
        name: str,
        contact_name: str,
        contact_email: str,
        contact_phone: Optional[str] = None,
        billing_cycle: str = "monthly"
    ) -> TenantDB:
        """创建租户"""
        try:
            tenant = TenantDB(
                name=name,
                contact_name=contact_name,
                contact_email=contact_email,
                contact_phone=contact_phone,
                status=TenantStatusEnum.TRIAL,
                billing_cycle=BillingCycleEnum(billing_cycle),
                max_employees=settings.default_max_employees,
                max_concurrent_jobs=settings.default_max_concurrent_jobs,
                storage_quota_gb=settings.default_storage_quota_gb,
                trial_end_at=datetime.now() + timedelta(days=settings.default_trial_days)
            )
            self.db.add(tenant)
            self.db.commit()
            self.db.refresh(tenant)
            self.logger.info(f"Created tenant: {tenant.id}, name: {name}")
            return tenant
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to create tenant: {str(e)}")
            raise

    def get_tenant(self, tenant_id: str) -> Optional[TenantDB]:
        """获取租户"""
        return self.db.query(TenantDB).filter(TenantDB.id == tenant_id).first()

    def list_tenants(
        self,
        status: Optional[TenantStatusEnum] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[TenantDB]:
        """获取租户列表"""
        query = self.db.query(TenantDB)
        if status:
            query = query.filter(TenantDB.status == status)
        return query.offset(offset).limit(limit).all()

    def update_tenant_status(
        self,
        tenant_id: str,
        status: TenantStatusEnum
    ) -> bool:
        """更新租户状态"""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return False

        try:
            tenant.status = status
            tenant.updated_at = datetime.now()
            self.db.commit()
            self.logger.info(f"Updated tenant {tenant_id} status to {status.value}")
            return True
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to update tenant status: {str(e)}")
            raise

    def delete_tenant(self, tenant_id: str) -> bool:
        """删除租户（软删除，设置为 cancelled）"""
        return self.update_tenant_status(tenant_id, TenantStatusEnum.CANCELLED)
