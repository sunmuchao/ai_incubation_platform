"""
AI Traffic Booster 与 ai-runtime-optimizer 集成模块

提供与运行态优化项目的统一埋点模型对齐，
支持跨项目 Agent 联合决策输入。
"""
from .burial_point_adapter import (
    # 数据模型
    TrafficMetricsSnapshot,
    RouteTrafficStat,
    TrafficUsageSummary,
    JointDecisionInput,
    JointSuggestion,
    # 适配器
    TrafficToRuntimeAdapter,
    JointDecisionAnalyzer,
    # 工具函数
    create_joint_decision_input
)

__all__ = [
    "TrafficMetricsSnapshot",
    "RouteTrafficStat",
    "TrafficUsageSummary",
    "JointDecisionInput",
    "JointSuggestion",
    "TrafficToRuntimeAdapter",
    "JointDecisionAnalyzer",
    "create_joint_decision_input"
]
