"""
用户模型

安全增强：
- Email 必须使用 EmailStr 类型，拒绝空值和无效格式
- Age 必须在 18-150 范围内
- Name 必须非空且长度限制
- Location 必须非空且长度限制
"""
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List, Dict
from datetime import datetime
import uuid
from enum import Enum
import re


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class SexualOrientation(str, Enum):
    """性取向偏好"""
    HETEROSEXUAL = "heterosexual"  # 异性
    HOMOSEXUAL = "homosexual"  # 同性
    BISEXUAL = "bisexual"  # 双性


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
    # 性取向偏好
    sexual_orientation: SexualOrientation = SexualOrientation.HETEROSEXUAL

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
    """创建用户请求

    安全验证规则：
    - name: 必填，长度 1-50 字符，禁止纯空格
    - email: 必填，EmailStr 类型验证
    - age: 必填，范围 18-150
    - gender: 必填，枚举值验证
    - location: 必填，长度 1-200 字符
    """
    name: str = Field(..., min_length=1, max_length=50, description="用户姓名")
    email: EmailStr = Field(..., description="用户邮箱")
    age: int = Field(..., ge=18, le=150, description="用户年龄（18-150）")
    gender: Gender = Field(..., description="用户性别")
    location: str = Field(..., min_length=1, max_length=200, description="用户位置")
    # 开发/测试环境允许不传 password，由服务端使用默认测试密码落库。
    # 生产环境应要求显式传入 password（由路由层校验）。
    password: Optional[str] = None
    bio: Optional[str] = Field(None, max_length=5000, description="用户简介")
    preferred_age_min: int = Field(default=18, ge=18, le=150, description="偏好最小年龄")
    preferred_age_max: int = Field(default=60, ge=18, le=150, description="偏好最大年龄")
    preferred_gender: Optional[Gender] = None
    interests: List[str] = Field(default_factory=list, max_length=20, description="兴趣列表（最多20项）")
    values: Dict[str, float] = Field(default_factory=dict, description="价值观评分")
    goal: RelationshipGoal = Field(default=RelationshipGoal.SERIOUS, description="关系目标")
    sexual_orientation: SexualOrientation = Field(default=SexualOrientation.HETEROSEXUAL, description="性取向")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """验证姓名：禁止纯空格"""
        if v is None or v.strip() == '':
            raise ValueError('name cannot be empty or whitespace only')
        return v.strip()

    @field_validator('location')
    @classmethod
    def validate_location(cls, v: str) -> str:
        """验证地址：禁止纯空格"""
        if v is None or v.strip() == '':
            raise ValueError('location cannot be empty or whitespace only')
        return v.strip()

    @field_validator('values')
    @classmethod
    def validate_values(cls, v: Dict[str, float]) -> Dict[str, float]:
        """验证价值观评分：值必须在 0-1 范围"""
        for key, value in v.items():
            if not (0 <= value <= 1):
                raise ValueError(f'value for {key} must be between 0 and 1')
        return v

    @field_validator('preferred_age_min', 'preferred_age_max')
    @classmethod
    def validate_age_range(cls, v: int, info) -> int:
        """验证年龄范围：min <= max"""
        return v

    def model_post_init(self, __context) -> None:
        """后置验证：检查年龄范围"""
        if self.preferred_age_min > self.preferred_age_max:
            raise ValueError('preferred_age_min must be less than or equal to preferred_age_max')


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
    sexual_orientation: Optional[SexualOrientation] = None
