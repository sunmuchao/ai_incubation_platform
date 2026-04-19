"""
Her Tools - DeerFlow Tools for Her Project (精简版 v4.3)

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

工具列表（精简为 7 个核心工具）：
- her_get_profile: 获取用户画像（含缺失字段提示）
- her_find_candidates: 查询候选匹配对象池（硬约束过滤）
- her_get_conversation_history: 获取对话历史
- her_update_preference: 更新用户偏好
- her_create_profile: 创建用户档案（当用户不存在时调用）
- her_record_feedback: 记录用户对候选人的反馈（建立反馈闭环）
- her_get_feedback_history: 获取用户反馈历史（分析偏好模式）

设计原则（Agent Native）：
- 所有工具只返回原始数据（JSON）
- 工具内部不包含业务判断、不生成建议、不返回模板
- Agent 根据返回的数据自主思考、解读、生成个性化建议

版本历史：
- v1.0: 硬编码模板（如 interest_topics 字典）
- v2.0: Agent Native 重构，工具只返回数据，Agent 自己生成建议
- v3.0: 模块化拆分，单一职责，便于维护
- v3.1: 新增安全 SQL 查询工具，Agent 可自主补齐信息
- v4.0: 精简为 4 个核心工具，删除冗余工具
- v4.1: 新增 her_create_profile 工具，支持用户档案创建
- v4.2: 新增 her_record_feedback / her_get_feedback_history，建立反馈闭环
"""

# ==================== 从模块导入 ====================

from .schemas import (
    MatchResult,
    ToolResult,
    HerGetProfileInput,
    HerFindCandidatesInput,
    HerGetConversationHistoryInput,
    HerUpdatePreferenceInput,
    HerCreateProfileInput,
    HerRecordFeedbackInput,
    HerGetFeedbackHistoryInput,
)

from .helpers import (
    get_her_root,
    ensure_her_in_path,
    get_current_user_id,
    run_async,
    get_db_user,
    get_user_confidence,
    batch_get_user_confidence,
)

from .profile_tools import (
    HerGetProfileTool,
    HerUpdatePreferenceTool,
    HerCreateProfileTool,
    her_get_profile_tool,
    her_update_preference_tool,
    her_create_profile_tool,
)

from .match_tools import (
    HerFindCandidatesTool,
    her_find_candidates_tool,
)

from .user_tools import (
    HerGetConversationHistoryTool,
    her_get_conversation_history_tool,
)

from .feedback_tools import (
    HerRecordFeedbackTool,
    HerGetFeedbackHistoryTool,
    her_record_feedback_tool,
    her_get_feedback_history_tool,
    PRESET_DISLIKE_REASONS,
)


# ==================== 统一导出 ====================

__all__ = [
    # Schemas
    "MatchResult",
    "ToolResult",
    "HerGetProfileInput",
    "HerFindCandidatesInput",
    "HerGetConversationHistoryInput",
    "HerUpdatePreferenceInput",
    "HerCreateProfileInput",
    "HerRecordFeedbackInput",
    "HerGetFeedbackHistoryInput",
    # Helpers
    "get_her_root",
    "ensure_her_in_path",
    "get_current_user_id",
    "run_async",
    "get_db_user",
    "get_user_confidence",
    "batch_get_user_confidence",
    # Profile Tools
    "HerGetProfileTool",
    "HerUpdatePreferenceTool",
    "HerCreateProfileTool",
    "her_get_profile_tool",
    "her_update_preference_tool",
    "her_create_profile_tool",
    # Match Tools
    "HerFindCandidatesTool",
    "her_find_candidates_tool",
    # User Tools
    "HerGetConversationHistoryTool",
    "her_get_conversation_history_tool",
    # Feedback Tools
    "HerRecordFeedbackTool",
    "HerGetFeedbackHistoryTool",
    "her_record_feedback_tool",
    "her_get_feedback_history_tool",
    "PRESET_DISLIKE_REASONS",
]


# ==================== 工具列表（便于注册）====================

HER_TOOLS = [
    her_get_profile_tool,
    her_find_candidates_tool,
    her_get_conversation_history_tool,
    her_update_preference_tool,
    her_create_profile_tool,
    her_record_feedback_tool,
    her_get_feedback_history_tool,
]