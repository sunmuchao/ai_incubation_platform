"""
企业级功能服务

包含：
- 列级权限服务
- 行级策略服务
- 租户配额服务
- 租户使用统计服务
- 增强审计日志服务
- 合规报告服务
"""
import asyncio
import uuid
import json
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from collections import defaultdict
import re

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import text as sql_text

from models.enterprise import (
    ColumnPermissionModel, RowLevelPolicyModel,
    TenantQuotaModel, TenantUsageModel,
    AuditLogEnhancedModel, ComplianceReportModel
)
from models.rbac import RoleModel, UserModel, UserRoleModel
from models.tenant import TenantModel
from config.database import db_manager
from utils.logger import logger


class EnterpriseService:
    """企业级功能服务"""

    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._cache_ttl: int = 60  # 缓存 TTL（秒）

    def _get_sync_session(self) -> Session:
        """获取同步数据库 Session"""
        return db_manager.get_sync_session()

    # ==================== 列级权限服务 ====================

    async def create_column_permission(
        self,
        role_name: str,
        datasource_name: str,
        table_name: str,
        column_name: str,
        access_type: str = "deny",
        created_by: str = None
    ) -> Dict[str, Any]:
        """创建列权限"""
        session = self._get_sync_session()
        try:
            # 获取角色
            role_stmt = select(RoleModel).where(RoleModel.name == role_name)
            role = session.scalar(role_stmt)
            if not role:
                return {"success": False, "error": f"角色 '{role_name}' 不存在"}

            # 检查权限是否已存在
            existing_stmt = select(ColumnPermissionModel).where(
                ColumnPermissionModel.role_id == role.id,
                ColumnPermissionModel.datasource_name == datasource_name,
                ColumnPermissionModel.table_name == table_name,
                ColumnPermissionModel.column_name == column_name
            )
            existing = session.scalar(existing_stmt)
            if existing:
                return {"success": False, "error": "列权限已存在"}

            perm = ColumnPermissionModel(
                role_id=role.id,
                datasource_name=datasource_name,
                table_name=table_name,
                column_name=column_name,
                access_type=access_type,
                created_by=created_by
            )
            session.add(perm)
            session.commit()
            session.refresh(perm)

            logger.info(f"Created column permission: {role_name}.{datasource_name}.{table_name}.{column_name}={access_type}")

            return {"success": True, "permission": perm.to_dict()}
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to create column permission: {e}")
            return {"success": False, "error": str(e)}
        finally:
            session.close()

    async def get_column_permissions(
        self,
        role_name: str = None,
        datasource_name: str = None,
        table_name: str = None
    ) -> List[Dict[str, Any]]:
        """获取列权限列表"""
        session = self._get_sync_session()
        try:
            stmt = select(ColumnPermissionModel).order_by(ColumnPermissionModel.created_at.desc())

            if role_name:
                role_stmt = select(RoleModel).where(RoleModel.name == role_name)
                role = session.scalar(role_stmt)
                if role:
                    stmt = stmt.where(ColumnPermissionModel.role_id == role.id)

            if datasource_name:
                stmt = stmt.where(ColumnPermissionModel.datasource_name == datasource_name)

            if table_name:
                stmt = stmt.where(ColumnPermissionModel.table_name == table_name)

            permissions = session.scalars(stmt).all()
            return [perm.to_dict() for perm in permissions]
        finally:
            session.close()

    async def delete_column_permission(self, permission_id: str) -> Dict[str, Any]:
        """删除列权限"""
        session = self._get_sync_session()
        try:
            stmt = select(ColumnPermissionModel).where(ColumnPermissionModel.id == permission_id)
            perm = session.scalar(stmt)
            if not perm:
                return {"success": False, "error": "权限不存在"}

            session.delete(perm)
            session.commit()

            logger.info(f"Deleted column permission: {permission_id}")
            return {"success": True, "message": "权限已删除"}
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to delete column permission: {e}")
            return {"success": False, "error": str(e)}
        finally:
            session.close()

    async def get_user_column_permissions(
        self,
        user_id: str,
        datasource_name: str,
        table_name: str
    ) -> Dict[str, str]:
        """获取用户对指定表的列权限"""
        session = self._get_sync_session()
        try:
            # 获取用户角色
            user_stmt = select(UserModel).where(UserModel.user_id == user_id)
            user = session.scalar(user_stmt)
            if not user:
                return {}

            user_role_stmt = select(UserRoleModel).where(UserRoleModel.user_id == user.id)
            user_roles = session.scalars(user_role_stmt).all()

            role_ids = [ur.role_id for ur in user_roles]
            if not role_ids:
                return {}

            # 获取列权限
            perm_stmt = select(ColumnPermissionModel).where(
                ColumnPermissionModel.role_id.in_(role_ids),
                ColumnPermissionModel.datasource_name == datasource_name,
                ColumnPermissionModel.table_name == table_name
            )
            permissions = session.scalars(perm_stmt).all()

            # 合并权限（deny 优先）
            result = {}
            for perm in permissions:
                if perm.access_type == "deny":
                    result[perm.column_name] = "deny"
                elif perm.column_name not in result:
                    result[perm.column_name] = "allow"

            return result
        finally:
            session.close()

    # ==================== 行级策略服务 ====================

    async def create_row_level_policy(
        self,
        role_name: str,
        datasource_name: str,
        table_name: str,
        filter_condition: str,
        description: str = None,
        priority: int = 0,
        created_by: str = None
    ) -> Dict[str, Any]:
        """创建行级策略"""
        session = self._get_sync_session()
        try:
            # 获取角色
            role_stmt = select(RoleModel).where(RoleModel.name == role_name)
            role = session.scalar(role_stmt)
            if not role:
                return {"success": False, "error": f"角色 '{role_name}' 不存在"}

            policy = RowLevelPolicyModel(
                role_id=role.id,
                datasource_name=datasource_name,
                table_name=table_name,
                filter_condition=filter_condition,
                description=description,
                priority=priority,
                created_by=created_by
            )
            session.add(policy)
            session.commit()
            session.refresh(policy)

            logger.info(f"Created row level policy: {policy.id}")

            return {"success": True, "policy": policy.to_dict()}
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to create row level policy: {e}")
            return {"success": False, "error": str(e)}
        finally:
            session.close()

    async def get_row_level_policies(
        self,
        role_name: str = None,
        datasource_name: str = None,
        table_name: str = None,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """获取行级策略列表"""
        session = self._get_sync_session()
        try:
            stmt = select(RowLevelPolicyModel).order_by(
                RowLevelPolicyModel.priority.desc(),
                RowLevelPolicyModel.created_at.desc()
            )

            if role_name:
                role_stmt = select(RoleModel).where(RoleModel.name == role_name)
                role = session.scalar(role_stmt)
                if role:
                    stmt = stmt.where(RowLevelPolicyModel.role_id == role.id)

            if datasource_name:
                stmt = stmt.where(RowLevelPolicyModel.datasource_name == datasource_name)

            if table_name:
                stmt = stmt.where(RowLevelPolicyModel.table_name == table_name)

            if active_only:
                stmt = stmt.where(RowLevelPolicyModel.is_active == True)

            policies = session.scalars(stmt).all()
            return [policy.to_dict() for policy in policies]
        finally:
            session.close()

    async def update_row_level_policy(
        self,
        policy_id: str,
        filter_condition: str = None,
        description: str = None,
        priority: int = None,
        is_active: bool = None
    ) -> Dict[str, Any]:
        """更新行级策略"""
        session = self._get_sync_session()
        try:
            stmt = select(RowLevelPolicyModel).where(RowLevelPolicyModel.id == policy_id)
            policy = session.scalar(stmt)
            if not policy:
                return {"success": False, "error": "策略不存在"}

            if filter_condition is not None:
                policy.filter_condition = filter_condition
            if description is not None:
                policy.description = description
            if priority is not None:
                policy.priority = priority
            if is_active is not None:
                policy.is_active = is_active

            session.commit()
            session.refresh(policy)

            return {"success": True, "policy": policy.to_dict()}
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to update row level policy: {e}")
            return {"success": False, "error": str(e)}
        finally:
            session.close()

    async def delete_row_level_policy(self, policy_id: str) -> Dict[str, Any]:
        """删除行级策略"""
        session = self._get_sync_session()
        try:
            stmt = select(RowLevelPolicyModel).where(RowLevelPolicyModel.id == policy_id)
            policy = session.scalar(stmt)
            if not policy:
                return {"success": False, "error": "策略不存在"}

            session.delete(policy)
            session.commit()

            return {"success": True, "message": "策略已删除"}
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to delete row level policy: {e}")
            return {"success": False, "error": str(e)}
        finally:
            session.close()

    async def get_user_row_level_policies(
        self,
        user_id: str,
        datasource_name: str,
        table_name: str
    ) -> List[Dict[str, Any]]:
        """获取用户对指定表的行级策略"""
        session = self._get_sync_session()
        try:
            # 获取用户角色
            user_stmt = select(UserModel).where(UserModel.user_id == user_id)
            user = session.scalar(user_stmt)
            if not user:
                return []

            user_role_stmt = select(UserRoleModel).where(UserRoleModel.user_id == user.id)
            user_roles = session.scalars(user_role_stmt).all()

            role_ids = [ur.role_id for ur in user_roles]
            if not role_ids:
                return []

            # 获取行级策略
            policy_stmt = select(RowLevelPolicyModel).where(
                RowLevelPolicyModel.role_id.in_(role_ids),
                RowLevelPolicyModel.datasource_name == datasource_name,
                RowLevelPolicyModel.table_name == table_name,
                RowLevelPolicyModel.is_active == True
            ).order_by(RowLevelPolicyModel.priority.desc())

            policies = session.scalars(policy_stmt).all()
            return [policy.to_dict() for policy in policies]
        finally:
            session.close()

    async def build_row_level_filter(
        self,
        user_id: str,
        datasource_name: str,
        table_name: str
    ) -> Optional[str]:
        """构建行级过滤条件"""
        policies = await self.get_user_row_level_policies(user_id, datasource_name, table_name)

        if not policies:
            return None

        # 合并所有策略条件（使用 AND 连接）
        conditions = [p["filter_condition"] for p in policies if p.get("filter_condition")]
        if conditions:
            return " AND ".join(f"({c})" for c in conditions)

        return None

    # ==================== 租户配额服务 ====================

    async def set_tenant_quota(
        self,
        tenant_code: str,
        daily_query_limit: int = None,
        monthly_query_limit: int = None,
        max_concurrent_queries: int = None,
        max_storage_gb: float = None,
        max_datasources: int = None,
        reset_day: int = None,
        created_by: str = None
    ) -> Dict[str, Any]:
        """设置租户配额"""
        session = self._get_sync_session()
        try:
            # 获取租户
            tenant_stmt = select(TenantModel).where(TenantModel.code == tenant_code)
            tenant = session.scalar(tenant_stmt)
            if not tenant:
                return {"success": False, "error": f"租户 '{tenant_code}' 不存在"}

            # 获取或创建配额
            quota_stmt = select(TenantQuotaModel).where(TenantQuotaModel.tenant_id == tenant.id)
            quota = session.scalar(quota_stmt)

            if not quota:
                quota = TenantQuotaModel(tenant_id=tenant.id, created_by=created_by)
                session.add(quota)
                session.flush()

            # 更新配额
            if daily_query_limit is not None:
                quota.daily_query_limit = daily_query_limit
            if monthly_query_limit is not None:
                quota.monthly_query_limit = monthly_query_limit
            if max_concurrent_queries is not None:
                quota.max_concurrent_queries = max_concurrent_queries
            if max_storage_gb is not None:
                quota.max_storage_gb = max_storage_gb
            if max_datasources is not None:
                quota.max_datasources = max_datasources
            if reset_day is not None:
                quota.reset_day = reset_day

            session.commit()
            session.refresh(quota)

            return {"success": True, "quota": quota.to_dict()}
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to set tenant quota: {e}")
            return {"success": False, "error": str(e)}
        finally:
            session.close()

    async def get_tenant_quota(self, tenant_code: str) -> Optional[Dict[str, Any]]:
        """获取租户配额"""
        session = self._get_sync_session()
        try:
            tenant_stmt = select(TenantModel).where(TenantModel.code == tenant_code)
            tenant = session.scalar(tenant_stmt)
            if not tenant:
                return None

            quota_stmt = select(TenantQuotaModel).where(TenantQuotaModel.tenant_id == tenant.id)
            quota = session.scalar(quota_stmt)

            return quota.to_dict() if quota else None
        finally:
            session.close()

    async def check_quota_limit(
        self,
        tenant_code: str,
        query_count: int = None,
        concurrent_count: int = None
    ) -> Tuple[bool, Optional[str]]:
        """检查配额限制"""
        quota = await self.get_tenant_quota(tenant_code)
        if not quota:
            return True, None  # 没有限制配置

        today = date.today()

        # 检查日配额
        if query_count:
            # 获取今日已用配额
            usage = await self.get_tenant_usage(tenant_code, today)
            used_today = usage.get("query_count", 0) if usage else 0
            if used_today + query_count > quota["daily_query_limit"]:
                return False, f"超出日查询配额限制 ({used_today}/{quota['daily_query_limit']})"

        # 检查月配额
        month_start = today.replace(day=1)
        month_usage = await self.get_tenant_usage_range(tenant_code, month_start, today)
        month_used = sum(u.get("query_count", 0) for u in month_usage)
        if month_used > quota["monthly_query_limit"]:
            return False, f"超出月查询配额限制 ({month_used}/{quota['monthly_query_limit']})"

        # 检查并发限制
        if concurrent_count and concurrent_count > quota["max_concurrent_queries"]:
            return False, f"超出并发查询限制 ({concurrent_count}/{quota['max_concurrent_queries']})"

        return True, None

    # ==================== 租户使用统计服务 ====================

    async def record_tenant_usage(
        self,
        tenant_code: str,
        query_count: int = 1,
        failed_query_count: int = 0,
        query_duration_ms: float = 0,
        storage_used_gb: float = 0,
        concurrent_count: int = 0,
        active_datasources: int = 0,
        active_users: int = 0
    ) -> Dict[str, Any]:
        """记录租户使用统计"""
        session = self._get_sync_session()
        try:
            tenant_stmt = select(TenantModel).where(TenantModel.code == tenant_code)
            tenant = session.scalar(tenant_stmt)
            if not tenant:
                return {"success": False, "error": f"租户 '{tenant_code}' 不存在"}

            today = date.today()

            # 获取或创建统计
            usage_stmt = select(TenantUsageModel).where(
                TenantUsageModel.tenant_id == tenant.id,
                TenantUsageModel.stat_date == today
            )
            usage = session.scalar(usage_stmt)

            if not usage:
                usage = TenantUsageModel(
                    tenant_id=tenant.id,
                    stat_date=today
                )
                session.add(usage)
                session.flush()

            # 累加统计
            usage.query_count += query_count
            usage.failed_query_count += failed_query_count

            # 更新平均耗时
            total_queries = usage.query_count
            if total_queries > 0:
                usage.avg_query_duration_ms = (
                    (usage.avg_query_duration_ms * (total_queries - query_count) + query_duration_ms) / total_queries
                )

            # 更新峰值并发
            if concurrent_count > usage.peak_concurrent:
                usage.peak_concurrent = concurrent_count

            # 更新其他统计
            if storage_used_gb > 0:
                usage.storage_used_gb = storage_used_gb
            if active_datasources > 0:
                usage.active_datasources = active_datasources
            if active_users > 0:
                usage.active_users = active_users

            session.commit()

            return {"success": True, "usage": usage.to_dict()}
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to record tenant usage: {e}")
            return {"success": False, "error": str(e)}
        finally:
            session.close()

    async def get_tenant_usage(
        self,
        tenant_code: str,
        stat_date: date = None
    ) -> Optional[Dict[str, Any]]:
        """获取租户使用统计"""
        session = self._get_sync_session()
        try:
            tenant_stmt = select(TenantModel).where(TenantModel.code == tenant_code)
            tenant = session.scalar(tenant_stmt)
            if not tenant:
                return None

            stmt = select(TenantUsageModel).where(TenantUsageModel.tenant_id == tenant.id)
            if stat_date:
                stmt = stmt.where(TenantUsageModel.stat_date == stat_date)
            else:
                stmt = stmt.order_by(TenantUsageModel.stat_date.desc()).limit(1)

            usage = session.scalar(stmt)
            return usage.to_dict() if usage else None
        finally:
            session.close()

    async def get_tenant_usage_range(
        self,
        tenant_code: str,
        start_date: date,
        end_date: date
    ) -> List[Dict[str, Any]]:
        """获取租户使用统计范围"""
        session = self._get_sync_session()
        try:
            tenant_stmt = select(TenantModel).where(TenantModel.code == tenant_code)
            tenant = session.scalar(tenant_stmt)
            if not tenant:
                return []

            stmt = select(TenantUsageModel).where(
                TenantUsageModel.tenant_id == tenant.id,
                TenantUsageModel.stat_date >= start_date,
                TenantUsageModel.stat_date <= end_date
            ).order_by(TenantUsageModel.stat_date)

            usages = session.scalars(stmt).all()
            return [u.to_dict() for u in usages]
        finally:
            session.close()

    # ==================== 增强审计日志服务 ====================

    async def log_audit(
        self,
        trace_id: str,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: str = None,
        tenant_id: str = None,
        request_method: str = None,
        request_path: str = None,
        request_body: dict = None,
        response_status: int = None,
        response_body: dict = None,
        before_state: dict = None,
        after_state: dict = None,
        ip_address: str = None,
        user_agent: str = None,
        referer: str = None,
        duration_ms: int = None,
        db_query_count: int = 0,
        db_query_duration_ms: int = None,
        risk_score: float = 0.0,
        is_anomaly: bool = False,
        anomaly_reason: str = None,
        session_id: str = None,
        span_id: str = None
    ) -> Dict[str, Any]:
        """记录增强审计日志"""
        session = self._get_sync_session()
        try:
            audit = AuditLogEnhancedModel(
                trace_id=trace_id,
                session_id=session_id,
                span_id=span_id,
                user_id=user_id,
                tenant_id=tenant_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                request_method=request_method,
                request_path=request_path,
                request_body=request_body,
                response_status=response_status,
                response_body=response_body,
                before_state=before_state,
                after_state=after_state,
                ip_address=ip_address,
                user_agent=user_agent,
                referer=referer,
                duration_ms=duration_ms,
                db_query_count=db_query_count,
                db_query_duration_ms=db_query_duration_ms,
                risk_score=risk_score,
                is_anomaly=is_anomaly,
                anomaly_reason=anomaly_reason
            )
            session.add(audit)
            session.commit()

            return {"success": True, "audit_id": audit.id}
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to log audit: {e}")
            return {"success": False, "error": str(e)}
        finally:
            session.close()

    async def get_audit_logs(
        self,
        user_id: str = None,
        tenant_id: str = None,
        action: str = None,
        resource_type: str = None,
        resource_id: str = None,
        is_anomaly: bool = None,
        start_date: datetime = None,
        end_date: datetime = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """获取审计日志"""
        session = self._get_sync_session()
        try:
            stmt = select(AuditLogEnhancedModel).order_by(
                AuditLogEnhancedModel.created_at.desc()
            )

            if user_id:
                stmt = stmt.where(AuditLogEnhancedModel.user_id == user_id)
            if tenant_id:
                stmt = stmt.where(AuditLogEnhancedModel.tenant_id == tenant_id)
            if action:
                stmt = stmt.where(AuditLogEnhancedModel.action == action)
            if resource_type:
                stmt = stmt.where(AuditLogEnhancedModel.resource_type == resource_type)
            if resource_id:
                stmt = stmt.where(AuditLogEnhancedModel.resource_id == resource_id)
            if is_anomaly is not None:
                stmt = stmt.where(AuditLogEnhancedModel.is_anomaly == is_anomaly)
            if start_date:
                stmt = stmt.where(AuditLogEnhancedModel.created_at >= start_date)
            if end_date:
                stmt = stmt.where(AuditLogEnhancedModel.created_at <= end_date)

            stmt = stmt.offset(offset).limit(limit)
            audits = session.scalars(stmt).all()

            return [audit.to_dict() for audit in audits]
        finally:
            session.close()

    async def get_audit_statistics(
        self,
        tenant_id: str = None,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> Dict[str, Any]:
        """获取审计统计"""
        session = self._get_sync_session()
        try:
            stmt = select(AuditLogEnhancedModel)

            if tenant_id:
                stmt = stmt.where(AuditLogEnhancedModel.tenant_id == tenant_id)
            if start_date:
                stmt = stmt.where(AuditLogEnhancedModel.created_at >= start_date)
            if end_date:
                stmt = stmt.where(AuditLogEnhancedModel.created_at <= end_date)

            # 总日志数
            total_stmt = select(func.count()).select_from(stmt.subquery())
            total = session.scalar(total_stmt) or 0

            # 异常日志数
            anomaly_stmt = select(func.count()).where(AuditLogEnhancedModel.is_anomaly == True)
            if tenant_id:
                anomaly_stmt = anomaly_stmt.where(AuditLogEnhancedModel.tenant_id == tenant_id)
            if start_date:
                anomaly_stmt = anomaly_stmt.where(AuditLogEnhancedModel.created_at >= start_date)
            if end_date:
                anomaly_stmt = anomaly_stmt.where(AuditLogEnhancedModel.created_at <= end_date)

            anomaly = session.scalar(anomaly_stmt) or 0

            # 按操作类型分组
            action_stmt = select(
                AuditLogEnhancedModel.action,
                func.count().label('count')
            ).where(
                AuditLogEnhancedModel.created_at >= start_date if start_date else True
            )
            if tenant_id:
                action_stmt = action_stmt.where(AuditLogEnhancedModel.tenant_id == tenant_id)
            action_stmt = action_stmt.group_by(AuditLogEnhancedModel.action)

            by_action = {row.action: row.count for row in session.execute(action_stmt)}

            return {
                "total_logs": total,
                "anomaly_count": anomaly,
                "anomaly_rate": anomaly / total if total > 0 else 0,
                "by_action": by_action
            }
        finally:
            session.close()

    # ==================== 合规报告服务 ====================

    async def generate_compliance_report(
        self,
        tenant_code: str,
        report_type: str,
        start_date: date,
        end_date: date,
        created_by: str = None
    ) -> Dict[str, Any]:
        """生成合规报告"""
        session = self._get_sync_session()
        try:
            # 获取租户
            tenant_stmt = select(TenantModel).where(TenantModel.code == tenant_code)
            tenant = session.scalar(tenant_stmt)
            if not tenant:
                return {"success": False, "error": f"租户 '{tenant_code}' 不存在"}

            # 创建报告记录
            report = ComplianceReportModel(
                tenant_id=tenant.id,
                report_type=report_type,
                start_date=start_date,
                end_date=end_date,
                status="generating",
                created_by=created_by
            )
            session.add(report)
            session.commit()
            session.refresh(report)

            # 异步生成报告内容
            asyncio.create_task(self._generate_report_content(report.id))

            return {"success": True, "report_id": report.id, "status": "generating"}
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to generate compliance report: {e}")
            return {"success": False, "error": str(e)}
        finally:
            session.close()

    async def _generate_report_content(self, report_id: str) -> None:
        """异步生成报告内容"""
        session = self._get_sync_session()
        try:
            stmt = select(ComplianceReportModel).where(ComplianceReportModel.id == report_id)
            report = session.scalar(stmt)
            if not report:
                return

            # 获取审计日志
            start_datetime = datetime.combine(report.start_date, datetime.min.time())
            end_datetime = datetime.combine(report.end_date, datetime.max.time())

            audits = await self.get_audit_logs(
                tenant_id=report.tenant_id,
                start_date=start_datetime,
                end_date=end_datetime,
                limit=10000
            )

            # 生成报告数据
            report_data = self._compile_report_data(report.report_type, audits)

            # 更新报告
            report.report_data = report_data
            report.summary = self._generate_summary(report_data)
            report.status = "completed"
            report.completed_at = datetime.utcnow()

            session.commit()
            logger.info(f"Generated compliance report: {report_id}")

        except Exception as e:
            session.rollback()
            logger.error(f"Failed to generate report content: {e}")
            # 更新状态为失败
            try:
                stmt = select(ComplianceReportModel).where(ComplianceReportModel.id == report_id)
                report = session.scalar(stmt)
                if report:
                    report.status = "failed"
                    session.commit()
            except Exception as e2:
                session.rollback()
        finally:
            session.close()

    def _compile_report_data(self, report_type: str, audits: List[Dict]) -> Dict[str, Any]:
        """编译报告数据"""
        # 按报告类型组织数据
        return {
            "report_type": report_type,
            "total_audits": len(audits),
            "audits": audits,
            "generated_at": datetime.utcnow().isoformat()
        }

    def _generate_summary(self, report_data: Dict) -> Dict[str, Any]:
        """生成报告摘要"""
        return {
            "total_operations": report_data.get("total_audits", 0),
            "unique_users": len(set(a.get("user_id") for a in report_data.get("audits", []) if a.get("user_id"))),
            "anomaly_count": sum(1 for a in report_data.get("audits", []) if a.get("is_anomaly")),
        }

    async def get_compliance_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        """获取合规报告"""
        session = self._get_sync_session()
        try:
            stmt = select(ComplianceReportModel).where(ComplianceReportModel.id == report_id)
            report = session.scalar(stmt)
            return report.to_dict() if report else None
        finally:
            session.close()

    async def list_compliance_reports(
        self,
        tenant_code: str,
        report_type: str = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """获取合规报告列表"""
        session = self._get_sync_session()
        try:
            tenant_stmt = select(TenantModel).where(TenantModel.code == tenant_code)
            tenant = session.scalar(tenant_stmt)
            if not tenant:
                return []

            stmt = select(ComplianceReportModel).where(
                ComplianceReportModel.tenant_id == tenant.id
            ).order_by(ComplianceReportModel.created_at.desc())

            if report_type:
                stmt = stmt.where(ComplianceReportModel.report_type == report_type)

            stmt = stmt.offset(offset).limit(limit)
            reports = session.scalars(stmt).all()

            return [report.to_dict() for report in reports]
        finally:
            session.close()


# 全局服务实例
enterprise_service = EnterpriseService()
