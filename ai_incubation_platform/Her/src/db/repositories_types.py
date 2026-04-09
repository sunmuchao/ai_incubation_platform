"""
Repositories 模块类型定义

用于替代 Dict[str, Any]，提供更精确的类型注解
"""
from typing import Optional, List, Dict, Any, Union
from typing_extensions import TypedDict


class UserCreateData(TypedDict, total=False):
    """用户创建数据"""
    id: str
    name: str
    email: str
    password_hash: str
    age: int
    gender: str
    location: str
    interests: Union[List[str], str]  # 支持列表或 JSON 字符串
    values: Union[Dict[str, Any], List, str]  # 支持 dict、list 或 JSON 字符串
    bio: str
    avatar_url: Optional[str]
    preferred_age_min: int
    preferred_age_max: int
    preferred_location: Optional[str]
    preferred_gender: Optional[str]
    sexual_orientation: str


class UserUpdateData(TypedDict, total=False):
    """用户更新数据"""
    name: str
    email: str
    age: int
    gender: str
    location: str
    interests: Union[List[str], str]
    values: Union[Dict[str, Any], List, str]
    bio: str
    avatar_url: Optional[str]
    preferred_age_min: int
    preferred_age_max: int
    preferred_location: Optional[str]
    preferred_gender: Optional[str]
    is_active: bool


class MatchCreateData(TypedDict, total=False):
    """匹配记录创建数据"""
    id: str
    user_a_id: str
    user_b_id: str
    match_score: float
    match_reason: str
    status: str
    matched_by: str


class MessageCreateData(TypedDict, total=False):
    """消息创建数据"""
    id: str
    conversation_id: str
    sender_id: str
    content: str
    message_type: str
    metadata: Optional[Dict[str, Any]]


class LLMSkillContext(TypedDict, total=False):
    """LLM Skill 执行上下文"""
    skill_name: str
    user_id: str
    target_user_id: Optional[str]
    conversation_id: Optional[str]
    previous_results: Optional[List[Dict[str, Any]]]


class PortalUserInfo(TypedDict, total=False):
    """门户用户信息"""
    portal_user_id: str
    username: str
    email: str
    phone: Optional[str]
    real_name: Optional[str]
    is_verified: bool


class CacheEntry(TypedDict, total=False):
    """缓存条目"""
    key: str
    value: Any
    expire_at: Optional[float]
    created_at: float
