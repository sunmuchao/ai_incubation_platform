"""
数据源模块
支持多数据源接入和降级策略
"""
from .real_api_adapter import (
    RealDataAdapter,
    DataSourceType,
    DataSourceStatus
)

__all__ = [
    "RealDataAdapter",
    "DataSourceType",
    "DataSourceStatus"
]
