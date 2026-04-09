"""
LLM 集成模块类型定义
"""
from typing import Optional, List, Dict, Any
from typing_extensions import TypedDict


class UserInfo(TypedDict, total=False):
    """用户信息"""
    user_id: str
    name: str
    age: int
    gender: str
    location: str
    interests: List[str]
    bio: str
    occupation: Optional[str]
    education: Optional[str]


class MatchContext(TypedDict, total=False):
    """匹配上下文"""
    user_info: UserInfo
    matched_user_info: UserInfo
    common_interests: List[str]
    compatibility_score: float
    match_reasoning: str


class IcebreakerGenerationContext(TypedDict, total=False):
    """破冰话题生成上下文"""
    user_info: UserInfo
    matched_user_info: UserInfo
    common_interests: List[str]
    compatibility_score: float
    match_reasoning: str
    conversation_stage: str


class MessageSuggestion(TypedDict):
    """消息建议"""
    content: str
    style: str
    confidence: float
    explanation: str


class LLMResponse(TypedDict, total=False):
    """LLM 响应"""
    success: bool
    content: str
    model: str
    usage: Dict[str, int]
    error: Optional[str]
