"""
用户模型
"""
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict
from datetime import datetime
import uuid
from enum import Enum


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class RelationshipGoal(str, Enum):
    CASUAL = "casual"
    SERIOUS = "serious"
    MARRIAGE = "marriage"
    FRIENDSHIP = "friendship"


class User(BaseModel):
    """用户模型"""
    id: str = str(uuid.uuid4())
    name: str
    email: str
    age: int
    gender: Gender
    location: str
    avatar: Optional[str] = None
    bio: Optional[str] = None

    # 择偶偏好
    preferred_age_min: int = 18
    preferred_age_max: int = 60
    preferred_gender: Optional[Gender] = None
    preferred_locations: List[str] = []

    # 价值观和兴趣
    values: Dict[str, float] = {}  # 价值观维度评分 0-1
    interests: List[str] = []
    lifestyle: Dict[str, str] = {}

    # 关系目标
    goal: RelationshipGoal = RelationshipGoal.SERIOUS

    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()


class UserProfile(BaseModel):
    """用户完整画像"""
    user_id: str
    personality_scores: Dict[str, float]  # 性格维度评分
    compatibility_profile: Dict[str, float]  # 兼容性画像
    deal_breakers: List[str]  # 不可接受的条件


class UserCreate(BaseModel):
    """创建用户请求"""
    name: str
    email: str
    age: int
    gender: Gender
    location: str
    # 开发/测试环境允许不传 password，由服务端使用默认测试密码落库。
    # 生产环境应要求显式传入 password（由路由层校验）。
    password: Optional[str] = None
    bio: Optional[str] = None
    preferred_age_min: int = 18
    preferred_age_max: int = 60
    preferred_gender: Optional[Gender] = None
    interests: List[str] = []
    values: Dict[str, float] = {}
    goal: RelationshipGoal = RelationshipGoal.SERIOUS


class MatchResult(BaseModel):
    """匹配结果"""
    user_id: str
    matched_user_id: str
    compatibility_score: float
    score_breakdown: Dict[str, float]
    reasoning: str
    common_interests: List[str]
    potential_issues: List[str]


class UserUpdate(BaseModel):
    """更新用户请求"""
    name: Optional[str] = None
    bio: Optional[str] = None
    avatar: Optional[str] = None
    location: Optional[str] = None
    preferred_age_min: Optional[int] = None
    preferred_age_max: Optional[int] = None
    preferred_gender: Optional[Gender] = None
    interests: Optional[List[str]] = None
    values: Optional[Dict[str, float]] = None
    goal: Optional[RelationshipGoal] = None
