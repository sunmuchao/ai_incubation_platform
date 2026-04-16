"""
用户模型

安全增强：
- Email 必须使用 EmailStr 类型，拒绝空值和无效格式（可选字段，如未提供则自动生成）
- Age 必须在 18-150 范围内
- Name 必须非空且长度限制
- Location 可选（新用户可能未填写）

修复说明：
- User 模型中的 email/location 改为 Optional，匹配数据库 nullable=True
- UserCreate 模型中的 username/email/location 改为 Optional，支持自动生成
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
    """用户模型（响应模型）"""
    id: str = str(uuid.uuid4())
    name: str
    email: Optional[str] = None  # 🔧 [修复] 改为可选，匹配数据库 nullable=True
    age: int
    gender: Gender
    location: Optional[str] = None  # 🔧 [修复] 改为可选，新用户可能未填写
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
    - username: 可选（如未提供，自动生成 UUID）
    - email: 可选（如未提供，自动生成临时邮箱）
    - password: 必填（生产环境），开发环境可选
    - name: 必填，长度 1-50 字符，显示昵称
    - age: 必填，范围 18-150
    - gender: 必填，枚举值验证
    - location: 可选（新用户可能未填写）
    - preferred_age_min/max: 可选（匹配偏好年龄范围）
    - accept_remote: 可选（是否接受异地）
    """
    username: Optional[str] = Field(None, min_length=3, max_length=20, description="用户名（如未提供则自动生成）")
    email: Optional[EmailStr] = Field(None, description="用户邮箱（如未提供则自动生成临时邮箱）")
    password: Optional[str] = Field(None, min_length=8, description="密码（生产环境必填）")
    name: str = Field(..., min_length=1, max_length=50, description="用户昵称/显示名称")
    age: int = Field(..., ge=18, le=150, description="用户年龄（18-150）")
    gender: Gender = Field(..., description="用户性别")
    location: Optional[str] = Field(None, max_length=200, description="用户位置（新用户可选）")
    bio: Optional[str] = Field(None, max_length=5000, description="用户简介")
    interests: List[str] = Field(default_factory=list, max_length=20, description="兴趣列表")
    values: Dict[str, float] = Field(default_factory=dict, description="价值观评分")
    sexual_orientation: SexualOrientation = Field(default=SexualOrientation.HETEROSEXUAL, description="性取向")

    # ===== 🔧 [新增] 偏好字段（支持带偏好注册） =====
    preferred_age_min: Optional[int] = Field(None, ge=18, le=150, description="偏好年龄下限")
    preferred_age_max: Optional[int] = Field(None, ge=18, le=150, description="偏好年龄上限")
    preferred_location: Optional[str] = Field(None, max_length=200, description="偏好城市")
    accept_remote: Optional[str] = Field(None, description="是否接受异地: yes/no/conditional/只找同城/接受异地")
    relationship_goal: Optional[str] = Field(None, description="关系目标: serious/marriage/dating/casual")

    @field_validator('username')
    @classmethod
    def validate_username(cls, v: Optional[str]) -> Optional[str]:
        """验证用户名：只允许字母、数字、下划线、中文（可选字段）"""
        if v is None:
            return v  # 允许为空，注册时会自动生成
        if not v:
            raise ValueError('username cannot be empty')
        if not re.match(r'^[a-zA-Z0-9_\u4e00-\u9fa5]+$', v):
            raise ValueError('username can only contain letters, numbers, underscore and Chinese')
        return v.strip()

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """验证姓名：禁止纯空格"""
        if v is None or v.strip() == '':
            raise ValueError('name cannot be empty or whitespace only')
        return v.strip()

    @field_validator('location')
    @classmethod
    def validate_location(cls, v: Optional[str]) -> Optional[str]:
        """验证地址：空字符串转为 None（可选字段）"""
        if v is None:
            return v  # 允许为空，新用户可能未填写
        if v.strip() == '':
            return None  # 空字符串或纯空格转为 None
        return v.strip()

    @field_validator('values')
    @classmethod
    def validate_values(cls, v: Dict[str, float]) -> Dict[str, float]:
        """验证价值观评分：值必须在 0-1 范围"""
        for key, value in v.items():
            if not (0 <= value <= 1):
                raise ValueError(f'value for {key} must be between 0 and 1')
        return v


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
