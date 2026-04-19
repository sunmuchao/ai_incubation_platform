"""
Her Tools - Schemas Module (精简版)

只保留 4 个核心工具的 Input Schema。

【Agent Native 设计原则】
- ToolResult 只返回 success/error/data 三个字段
- 工具只做数据查询，不做业务逻辑判断
- Agent 自行解读数据并生成回复

版本历史：
- v4.0: 精简为 4 个核心工具
"""
from typing import Dict, Any, List, Optional
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
    confidence_level: str = Field(default="medium", description="置信度等级")
    confidence_score: int = Field(default=40, description="置信度分数")


class ToolResult(BaseModel):
    """
    工具统一返回格式（Agent Native 设计）

    只返回原始数据，Agent 自行解读并生成回复。

    【设计原则】
    - success/error: 执行状态，Agent 据此决定回复内容
    - data: 原始数据，包含 component_type 供前端渲染 UI
    - 不包含 instruction/output_hint/summary: Agent 自主决定输出内容

    重要：Agent 必须基于 data 内容自主生成回复，不能直接输出原始 JSON！
    """
    success: bool = Field(description="是否成功")
    error: str = Field(default="", description="错误信息")
    data: Dict[str, Any] = Field(
        default_factory=dict,
        description="原始数据，包含 component_type 供前端渲染 UI，Agent 用于决策和生成回复"
    )


# ==================== Input Schemas（精简为 4 个）====================

class HerGetProfileInput(BaseModel):
    """
    获取用户画像的输入参数

    user_id 可选，支持：
    - 不传或传 "me"/"current" → 返回当前用户
    - 传具体 ID → 返回该用户画像
    """
    user_id: str = Field(
        default="me",
        description="用户 ID，可选。不传或传 'me' 返回当前用户，传具体 ID 返回该用户画像"
    )


class HerFindCandidatesInput(BaseModel):
    """
    查找匹配对象的输入参数

    只做硬约束过滤（性别、封禁用户），软约束由 Agent 自行判断。
    """
    user_id: str = Field(
        default="me",
        description="用户 ID，可选。不传或传 'me' 使用当前用户"
    )


class HerGetConversationHistoryInput(BaseModel):
    """
    获取对话历史的输入参数
    """
    user_id: str = Field(
        default="me",
        description="用户 ID，可选。不传或传 'me' 使用当前用户"
    )
    target_id: str = Field(
        description="对话对象 ID"
    )
    limit: int = Field(
        default=20,
        description="返回消息数量，默认 20"
    )


class HerUpdatePreferenceInput(BaseModel):
    """
    更新用户偏好的输入参数

    支持更新的维度：
    - accept_remote: 异地接受度（"接受异地"/"同城优先"/"只找同城"）
    - relationship_goal: 关系目标（"serious"/"casual"/"friendship"）
    - preferred_age_min: 年龄下限
    - preferred_age_max: 年龄上限
    - preferred_location: 偏好地点
    """
    user_id: str = Field(
        default="me",
        description="用户 ID，可选。不传或传 'me' 使用当前用户"
    )
    dimension: str = Field(
        description="偏好维度：accept_remote, relationship_goal, preferred_age_min, preferred_age_max, preferred_location"
    )
    value: str = Field(
        description="偏好值"
    )


class HerCreateProfileInput(BaseModel):
    """
    创建用户画像的输入参数

    当用户不存在时，Agent 调用此工具创建用户档案。
    """
    name: str = Field(
        description="用户姓名"
    )
    age: int = Field(
        ge=18, le=150,
        description="用户年龄，必须在 18-150 之间"
    )
    gender: str = Field(
        description="用户性别：male 或 female"
    )
    location: str = Field(
        default="",
        description="用户所在地，可选"
    )
    occupation: str = Field(
        default="",
        description="用户职业，可选"
    )
    interests: List[str] = Field(
        default_factory=list,
        description="兴趣爱好列表，可选"
    )
    relationship_goal: str = Field(
        default="",
        description="关系目标：serious/marriage/dating/casual，可选"
    )
    bio: str = Field(
        default="",
        description="个人简介，可选"
    )
    accept_remote: str = Field(
        default="",
        description="异地接受度：yes/no/conditional，可选"
    )
    preferred_age_min: int = Field(
        default=0,
        description="偏好年龄下限，可选"
    )
    preferred_age_max: int = Field(
        default=0,
        description="偏好年龄上限，可选"
    )


class HerRecordFeedbackInput(BaseModel):
    """
    记录用户对候选人的反馈

    建立反馈闭环，用于优化后续推荐。
    """
    user_id: str = Field(
        default="me",
        description="用户 ID，可选。不传或传 'me' 使用当前用户"
    )
    candidate_id: str = Field(
        description="候选人 ID（display_id 或 user_id）"
    )
    feedback_type: str = Field(
        description="反馈类型：like（喜欢）/ dislike（不喜欢）/ neutral（中性）/ skip（跳过）"
    )
    reason: str = Field(
        default="",
        description="不喜欢原因（仅 feedback_type=dislike 时需要）"
    )
    detail: str = Field(
        default="",
        description="用户自定义原因（可选，自由文本）"
    )


class HerGetFeedbackHistoryInput(BaseModel):
    """
    获取用户的反馈历史

    用于分析用户偏好模式。
    """
    user_id: str = Field(
        default="me",
        description="用户 ID，可选。不传或传 'me' 使用当前用户"
    )
    feedback_type: str = Field(
        default="",
        description="筛选类型：like / dislike / neutral / skip（可选，不传返回全部）"
    )
    limit: int = Field(
        default=20,
        description="返回数量限制，默认 20"
    )


# ==================== Exports ====================

__all__ = [
    # Output
    "MatchResult",
    "ToolResult",
    # Input（精简为 7 个）
    "HerGetProfileInput",
    "HerFindCandidatesInput",
    "HerGetConversationHistoryInput",
    "HerUpdatePreferenceInput",
    "HerCreateProfileInput",
    "HerRecordFeedbackInput",
    "HerGetFeedbackHistoryInput",
]