"""
本服务内所有需 Agent 编排的能力，统一通过 DeerFlow 2.0 提供。

安装：`pip install -e ../../deerflow-integration`（在子项目目录执行 requirements 时）
       并单独按官方文档安装上游 `deer-flow` 包。
"""
from deerflow_integration import (
    DEERFLOW_VERSION,
    get_deerflow_client,
    is_deerflow_available,
)

__all__ = [
    "DEERFLOW_VERSION",
    "get_deerflow_client",
    "is_deerflow_available",
]
