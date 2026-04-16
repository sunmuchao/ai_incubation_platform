"""
Her Tools - Schemas Module

Input/Output schemas for all Her tools.
"""
from typing import Dict, Any, List, Type
from pydantic import BaseModel, Field


# ==================== Output Schemas ====================

class MatchResult(BaseModel):
    """单个匹配结果"""
    user_id: str = Field(description="用户 ID")
    name: str = Field(description="姓名")
    age: int = Field(default=0, description="年龄")
    location: str = Field(default="", description="所在地")
    gender: str = Field(default="", description="性别")
    interests: List[str] = Field(default_factory=list, description="兴趣爱好")
    bio: str = Field(default="", description="简介")


class ToolResult(BaseModel):
    """工具统一返回格式"""
    success: bool = Field(description="是否成功")
    data: Dict[str, Any] = Field(default_factory=dict, description="结构化数据")
    summary: str = Field(default="", description="一句话总结，用于 Agent 理解")
    error: str = Field(default="", description="错误信息")


# ==================== Input Schemas ====================

class HerFindMatchesInput(BaseModel):
    """查找匹配对象的输入参数"""
    user_id: str = Field(description="用户 ID")
    intent: str = Field(default="", description="用户意图描述")
    limit: int = Field(default=5, description="返回数量")


class HerDailyRecommendInput(BaseModel):
    """每日推荐的输入参数"""
    user_id: str = Field(description="用户 ID")


class HerAnalyzeCompatibilityInput(BaseModel):
    """兼容性分析的输入参数"""
    user_id: str = Field(description="用户 ID")
    target_user_id: str = Field(description="目标用户 ID")


class HerAnalyzeRelationshipInput(BaseModel):
    """关系分析的输入参数"""
    user_id: str = Field(description="用户 ID")
    match_id: str = Field(description="匹配记录 ID")


class HerSuggestTopicsInput(BaseModel):
    """话题推荐的输入参数"""
    user_id: str = Field(description="用户 ID")
    match_id: str = Field(default="", description="匹配记录 ID")
    context: str = Field(default="", description="对话上下文")


class HerGetIcebreakerInput(BaseModel):
    """破冰建议的输入参数"""
    user_id: str = Field(description="用户 ID")
    match_id: str = Field(default="", description="匹配记录 ID")
    target_name: str = Field(default="TA", description="目标用户姓名")


class HerPlanDateInput(BaseModel):
    """约会策划的输入参数"""
    user_id: str = Field(description="用户 ID")
    match_id: str = Field(default="", description="匹配记录 ID")
    target_name: str = Field(default="TA", description="约会对象姓名")
    location: str = Field(default="", description="约会地点")
    preferences: str = Field(default="", description="偏好设置")


class HerCollectProfileInput(BaseModel):
    """信息收集的输入参数"""
    user_id: str = Field(description="用户 ID")
    trigger_reason: str = Field(default="user_intent", description="触发原因")


class HerUpdatePreferenceInput(BaseModel):
    """更新用户偏好的输入参数"""
    user_id: str = Field(description="用户 ID")
    dimension: str = Field(description="偏好维度，如: accept_remote, relationship_goal, preferred_age_min, preferred_age_max, preferred_location")
    value: str = Field(description="偏好值")


class HerGetUserInput(BaseModel):
    """获取用户画像的输入参数"""
    user_id: str = Field(description="用户 ID")


class HerGetTargetUserInput(BaseModel):
    """获取目标用户画像的输入参数"""
    target_user_id: str = Field(description="目标用户 ID")


class HerGetConversationHistoryInput(BaseModel):
    """获取对话历史的输入参数"""
    user_id: str = Field(description="用户 ID")
    match_id: str = Field(description="匹配对象 ID")
    limit: int = Field(default=20, description="返回消息数量")


class HerInitiateChatInput(BaseModel):
    """发起聊天的输入参数"""
    target_user_id: str = Field(description="目标用户 ID")
    context: str = Field(default="", description="上下文信息，如 '你们刚完成了92%匹配度分析'")
    compatibility_score: int = Field(default=0, description="匹配度分数")


class HerSafeQueryInput(BaseModel):
    """安全 SQL 查询的输入参数"""
    sql: str = Field(description="SQL 查询语句（必须是 SELECT，只允许查询白名单表）")


class HerFindUserByNameInput(BaseModel):
    """按名字查找用户的输入参数"""
    name: str = Field(description="用户名字（支持模糊匹配）")
    location: str = Field(default="", description="城市（可选，用于缩小范围）")
    limit: int = Field(default=5, description="返回数量")


# ==================== Exports ====================

__all__ = [
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
]