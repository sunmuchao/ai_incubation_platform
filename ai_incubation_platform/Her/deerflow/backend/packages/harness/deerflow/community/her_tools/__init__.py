"""
Her Tools - DeerFlow Tools for Her Project

【Agent Native 架构】
DeerFlow Agent 是唯一的决策大脑，负责意图理解、数据解读、建议生成。
her_tools 只做数据查询，不包含任何业务逻辑或模板！

正确的执行循环：
```
用户消息 → Agent 思考(Thinking) → 选择工具 → 执行工具(纯数据查询) → 返回原始数据
                                                                      ↓
                                    Agent 解读数据(Thinking) → 生成个性化建议
                                                                      ↓
                                    输出回复 → 完成
```

工具列表（全部为纯数据查询）：
- her_find_matches: 查询数据库匹配对象（返回候选人列表）
- her_daily_recommend: 查询今日推荐（返回活跃用户列表）
- her_analyze_compatibility: 查询用户画像对比（返回双方原始数据）
- her_analyze_relationship: 查询关系数据（返回匹配记录和互动数据）
- her_suggest_topics: 查询用户画像和对话历史（让 Agent 自己生成话题）
- her_get_icebreaker: 查询双方画像（让 Agent 自己生成开场白）
- her_plan_date: 查询双方画像和活动选项（让 Agent 自己生成约会方案）
- her_collect_profile: 查询用户信息缺失字段
- her_update_preference: 更新用户偏好到数据库
- her_get_user: 获取用户画像
- her_get_target_user: 获取目标用户画像
- her_get_conversation_history: 获取对话历史
- her_safe_query: 安全 SQL 查询（Agent 可以自己生成查询，补齐缺失信息）【新增】
- her_find_user_by_name: 按名字查找用户（便捷封装）【新增】
- her_get_product_capabilities: 查询产品能力开关（通知/提醒等）【新增】

设计原则（Agent Native）：
- 所有工具只返回原始数据（JSON）
- 工具内部不包含业务判断、不生成建议、不返回模板
- Agent 根据返回的数据自主思考、解读、生成个性化建议
- 模板和硬编码逻辑已全部移除，Agent 应根据具体情况创造建议

【v3.1 新增】自主信息获取能力：
- Agent 不再只能调用预定义工具
- Agent 可以通过 her_safe_query 自己生成 SQL 查询
- 用于补齐缺失的信息（如根据名字查询 user_id）
- 但必须在安全边界内：只允许 SELECT，只允许白名单表

版本历史：
- v1.0: 硬编码模板（如 interest_topics 字典）
- v2.0: Agent Native 重构，工具只返回数据，Agent 自己生成建议
- v3.0: 模块化拆分，单一职责，便于维护
- v3.1: 新增安全 SQL 查询工具，Agent 可自主补齐信息

模块化结构：
- schemas.py: 输入/输出数据模型
- helpers.py: 辅助函数（路径解析、用户ID提取、数据库访问）
- match_tools.py: 匹配相关工具
- analysis_tools.py: 分析相关工具
- conversation_tools.py: 对话相关工具
- profile_tools.py: 资料相关工具
- user_tools.py: 用户数据相关工具
- query_tools.py: 安全查询工具【新增】
- capabilities_tools.py: 产品能力开关【新增】
"""

# ==================== 从模块导入 ====================

from .schemas import (
    MatchResult,
    ToolResult,
    HerFindMatchesInput,
    HerDailyRecommendInput,
    HerAnalyzeCompatibilityInput,
    HerAnalyzeRelationshipInput,
    HerSuggestTopicsInput,
    HerGetIcebreakerInput,
    HerPlanDateInput,
    HerCollectProfileInput,
    HerUpdatePreferenceInput,
    HerGetUserInput,
    HerGetTargetUserInput,
    HerGetConversationHistoryInput,
    HerInitiateChatInput,
    HerSafeQueryInput,
    HerFindUserByNameInput,
    HerGetProductCapabilitiesInput,
)

from .helpers import (
    get_her_root,
    ensure_her_in_path,
    get_current_user_id,
    run_async,
    get_db_user,
    get_user_confidence,
)

from .match_tools import (
    HerFindMatchesTool,
    HerDailyRecommendTool,
    her_find_matches_tool,
    her_daily_recommend_tool,
)

from .analysis_tools import (
    HerAnalyzeCompatibilityTool,
    HerAnalyzeRelationshipTool,
    her_analyze_compatibility_tool,
    her_analyze_relationship_tool,
)

from .conversation_tools import (
    HerSuggestTopicsTool,
    HerGetIcebreakerTool,
    HerPlanDateTool,
    her_suggest_topics_tool,
    her_get_icebreaker_tool,
    her_plan_date_tool,
)

from .profile_tools import (
    HerCollectProfileTool,
    HerUpdatePreferenceTool,
    her_collect_profile_tool,
    her_update_preference_tool,
)

from .user_tools import (
    HerGetUserTool,
    HerGetTargetUserTool,
    HerGetConversationHistoryTool,
    HerInitiateChatTool,
    her_get_user_tool,
    her_get_target_user_tool,
    her_get_conversation_history_tool,
    her_initiate_chat_tool,
)

from .query_tools import (
    HerSafeQueryTool,
    HerFindUserByNameTool,
    her_safe_query_tool,
    her_find_user_by_name_tool,
)

from .capabilities_tools import (
    HerGetProductCapabilitiesTool,
    her_get_product_capabilities_tool,
)


# ==================== 统一导出 ====================

__all__ = [
    # Schemas
    "MatchResult",
    "ToolResult",
    "HerFindMatchesInput",
    "HerDailyRecommendInput",
    "HerAnalyzeCompatibilityInput",
    "HerAnalyzeRelationshipInput",
    "HerSuggestTopicsInput",
    "HerGetIcebreakerInput",
    "HerPlanDateInput",
    "HerCollectProfileInput",
    "HerUpdatePreferenceInput",
    "HerGetUserInput",
    "HerGetTargetUserInput",
    "HerGetConversationHistoryInput",
    "HerInitiateChatInput",
    "HerSafeQueryInput",
    "HerFindUserByNameInput",
    "HerGetProductCapabilitiesInput",
    # Helpers
    "get_her_root",
    "ensure_her_in_path",
    "get_current_user_id",
    "run_async",
    "get_db_user",
    "get_user_confidence",
    # Match Tools
    "HerFindMatchesTool",
    "HerDailyRecommendTool",
    "her_find_matches_tool",
    "her_daily_recommend_tool",
    # Analysis Tools
    "HerAnalyzeCompatibilityTool",
    "HerAnalyzeRelationshipTool",
    "her_analyze_compatibility_tool",
    "her_analyze_relationship_tool",
    # Conversation Tools
    "HerSuggestTopicsTool",
    "HerGetIcebreakerTool",
    "HerPlanDateTool",
    "her_suggest_topics_tool",
    "her_get_icebreaker_tool",
    "her_plan_date_tool",
    # Profile Tools
    "HerCollectProfileTool",
    "HerUpdatePreferenceTool",
    "her_collect_profile_tool",
    "her_update_preference_tool",
    # User Tools
    "HerGetUserTool",
    "HerGetTargetUserTool",
    "HerGetConversationHistoryTool",
    "HerInitiateChatTool",
    "her_get_user_tool",
    "her_get_target_user_tool",
    "her_get_conversation_history_tool",
    "her_initiate_chat_tool",
    # Query Tools (新增)
    "HerSafeQueryTool",
    "HerFindUserByNameTool",
    "her_safe_query_tool",
    "her_find_user_by_name_tool",
    "HerGetProductCapabilitiesTool",
    "her_get_product_capabilities_tool",
]


# ==================== 工具列表（便于注册）====================

HER_TOOLS = [
    her_find_matches_tool,
    her_daily_recommend_tool,
    her_analyze_compatibility_tool,
    her_analyze_relationship_tool,
    her_suggest_topics_tool,
    her_get_icebreaker_tool,
    her_plan_date_tool,
    her_collect_profile_tool,
    her_update_preference_tool,
    her_get_user_tool,
    her_get_target_user_tool,
    her_get_conversation_history_tool,
    her_initiate_chat_tool,
    # 新增：安全查询工具
    her_safe_query_tool,
    her_find_user_by_name_tool,
    her_get_product_capabilities_tool,
]