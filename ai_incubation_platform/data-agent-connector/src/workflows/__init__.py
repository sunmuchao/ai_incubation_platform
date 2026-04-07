"""
Workflows 层 - 数据连接器领域工作流

提供 DeerFlow 2.0 风格的工作流编排，支持：
1. 多步任务自动编排
2. 声明式流程定义
3. 本地降级执行
"""
from .connector_workflows import (
    # 工作流类
    ConnectDatasourceWorkflow,
    DisconnectDatasourceWorkflow,
    QueryDataWorkflow,
    SchemaDiscoveryWorkflow,
    LineageAnalysisWorkflow,
    AutoDataPipelineWorkflow,
    # 工具函数
    connect_datasource,
    disconnect_datasource,
    query_data,
    discover_schema,
    analyze_lineage,
    build_data_pipeline,
)

__all__ = [
    # 工作流类
    "ConnectDatasourceWorkflow",
    "DisconnectDatasourceWorkflow",
    "QueryDataWorkflow",
    "SchemaDiscoveryWorkflow",
    "LineageAnalysisWorkflow",
    "AutoDataPipelineWorkflow",
    # 工具函数
    "connect_datasource",
    "disconnect_datasource",
    "query_data",
    "discover_schema",
    "analyze_lineage",
    "build_data_pipeline",
]
