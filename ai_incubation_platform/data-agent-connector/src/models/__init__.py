"""
模型统一注册模块

将所有模型注册到同一个 Base，确保数据库表创建时包含所有模型
"""
from models.lineage_db import (
    Base,
    LineageNodeModel,
    LineageEdgeModel,
    LineageQueryHistoryModel,
    LineageSnapshotModel
)

# 导入所有模型以确保它们注册到 Base
from models.rbac import (
    RoleModel,
    UserModel,
    UserRoleModel,
    DataSourcePermissionModel,
    ColumnMaskModel,
    PermissionAuditModel
)

from models.tenant import (
    TenantModel,
    TenantMemberModel,
    TenantDatasourceModel,
    TenantQuotaUsageModel
)

from models.monitoring import (
    MetricModel,
    AlertRuleModel,
    AlertModel,
    SystemHealthModel
)

# P5 数据智能模型
from models.vector_index import VectorIndexModel, VectorCollectionModel, VectorSearchHistoryModel, VectorSchemaInfoModel
from models.data_quality import QualityRuleModel, QualityResultModel, AnomalyModel, QualityDashboardModel
from models.schema_recommendation import RecommendationRuleModel, RecommendationModel, QueryPatternModel, IndexUsageModel

# 导出所有模型
__all__ = [
    # Base 必须首先导出
    "Base",
    # Lineage 模型
    "LineageNodeModel",
    "LineageEdgeModel",
    "LineageQueryHistoryModel",
    "LineageSnapshotModel",
    # RBAC 模型
    "RoleModel",
    "UserModel",
    "UserRoleModel",
    "DataSourcePermissionModel",
    "ColumnMaskModel",
    "PermissionAuditModel",
    # Tenant 模型
    "TenantModel",
    "TenantMemberModel",
    "TenantDatasourceModel",
    "TenantQuotaUsageModel",
    # Monitoring 模型
    "MetricModel",
    "AlertRuleModel",
    "AlertModel",
    "SystemHealthModel",
    # P5 数据智能模型
    "VectorIndexModel",
    "VectorCollectionModel",
    "VectorSearchHistoryModel",
    "VectorSchemaInfoModel",
    "QualityRuleModel",
    "QualityResultModel",
    "AnomalyModel",
    "QualityDashboardModel",
    "RecommendationRuleModel",
    "RecommendationModel",
    "QueryPatternModel",
    "IndexUsageModel",
]
