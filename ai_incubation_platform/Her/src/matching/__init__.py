"""
匹配引擎模块

双引擎架构（规划中）：
- RuleMatchEngine: 常规模式（免费，系统主导）
- AgenticMatchEngine: 许愿模式（付费，用户主导）
- EngineSwitch: 引擎切换器

当前状态：使用 matcher.py 中的匹配器
"""

# 注意：以下模块尚未实现，暂时注释
# from matching.engine_base import (
#     MatchEngine,
#     MatchRequest,
#     MatchResult,
#     EngineMetrics,
# )
# from matching.rule_engine import RuleMatchEngine
# from matching.agentic_engine import AgenticMatchEngine
# from matching.engine_switch import EngineSwitch, get_engine_switch

# 当前可用的匹配器
from matching.matcher import matchmaker

__all__ = [
    "matchmaker",
    # "MatchEngine",
    # "MatchRequest",
    # "MatchResult",
    # "EngineMetrics",
    # "RuleMatchEngine",
    # "AgenticMatchEngine",
    # "EngineSwitch",
    # "get_engine_switch",
]