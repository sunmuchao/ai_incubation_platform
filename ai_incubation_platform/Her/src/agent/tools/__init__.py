"""
红娘 Agent 工具集

所有工具按功能分类，每个工具实现：
- name: 工具名称
- description: 工具描述
- input_schema: JSONSchema 输入定义
- handler: 处理函数

注：MatchTool 已废弃，匹配功能使用 DeerFlow her_find_matches_tool。
注：ConversationMatchmakerTool 已废弃，使用 ConversationMatchService。
"""
from agent.tools.registry import ToolRegistry
from agent.tools.profile_tool import ProfileTool
from agent.tools.reasoning_tool import ReasoningTool
from agent.tools.logging_tool import LoggingTool
from agent.tools.autonomous_tools import (
    CompatibilityAnalysisTool,
    TopicSuggestionTool,
    RelationshipTrackingTool,
    register_autonomous_tools
)
from agent.tools.skill_tool import (
    SkillTool,
    EmotionAnalysisTool,
    SafetyGuardianTool,
    SilenceBreakerTool,
    EmotionMediatorTool,
    LoveLanguageTranslatorTool,
    RelationshipProphetTool,
    DateCoachTool,
    DateAssistantTool,
    RelationshipCuratorTool,
    RiskControlTool,
    ShareGrowthTool,
    PerformanceCoachTool,
    ActivityDirectorTool,
    VideoDateCoachTool,
    # 注：ConversationMatchmakerTool 已废弃
    register_skill_tools
)

__all__ = [
    "ToolRegistry",
    "ProfileTool",
    "ReasoningTool",
    "LoggingTool",
    "CompatibilityAnalysisTool",
    "TopicSuggestionTool",
    "RelationshipTrackingTool",
    "register_autonomous_tools",
    # Skill 工具
    "SkillTool",
    "EmotionAnalysisTool",
    "SafetyGuardianTool",
    "SilenceBreakerTool",
    "EmotionMediatorTool",
    "LoveLanguageTranslatorTool",
    "RelationshipProphetTool",
    "DateCoachTool",
    "DateAssistantTool",
    "RelationshipCuratorTool",
    "RiskControlTool",
    "ShareGrowthTool",
    "PerformanceCoachTool",
    "ActivityDirectorTool",
    "VideoDateCoachTool",
    # 注：ConversationMatchmakerTool 已废弃
    "register_skill_tools",
]

