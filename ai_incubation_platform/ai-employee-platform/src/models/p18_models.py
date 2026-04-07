"""
P18 阶段数据模型 - 组织文化构建 (Organizational Culture Building)

本模块定义了组织文化构建相关的数据模型，包括：
- 文化价值观定义与传播
- 员工认可与奖励
- 团队凝聚力建设
- 文化契合度评估
- 多样性与包容性
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional
import uuid


# ==================== 枚举定义 ====================

class CultureValueType(str, Enum):
    """文化价值观类型"""
    CORE = "core"  # 核心价值观
    BEHAVIORAL = "behavioral"  # 行为准则
    OPERATIONAL = "operational"  # 运营原则
    ASPIRATIONAL = "aspirational"  # 愿景价值观


class RecognitionType(str, Enum):
    """认可类型"""
    PEER = "peer"  # 同事认可
    MANAGER = "manager"  # 上级认可
    TEAM = "team"  # 团队认可
    COMPANY = "company"  # 公司认可
    AUTOMATED = "automated"  # 自动认可


class RecognitionCategory(str, Enum):
    """认可分类"""
    INNOVATION = "innovation"  # 创新
    COLLABORATION = "collaboration"  # 协作
    EXCELLENCE = "excellence"  # 卓越
    CULTURE_FIT = "culture_fit"  # 文化契合
    CUSTOMER_FOCUS = "customer_focus"  # 客户导向
    OWNERSHIP = "ownership"  # 主人翁精神
    DIVERSITY = "diversity"  # 多样性贡献
    MENTORSHIP = "mentorship"  # 导师精神
    KNOWLEDGE_SHARING = "knowledge_sharing"  # 知识分享
    OTHER = "other"  # 其他


class AwardTier(str, Enum):
    """奖励等级"""
    BRONZE = "bronze"  # 铜牌
    SILVER = "silver"  # 银牌
    GOLD = "gold"  # 金牌
    PLATINUM = "platinum"  # 白金
    DIAMOND = "diamond"  # 钻石


class TeamEventType(str, Enum):
    """团队活动类型"""
    TEAM_BUILDING = "team_building"  # 团建活动
    CULTURE_WORKSHOP = "culture_workshop"  # 文化工作坊
    HACKATHON = "hackathon"  # 黑客松
    SOCIAL = "social"  # 社交活动
    LEARNING = "learning"  # 学习活动
    CELEBRATION = "celebration"  # 庆祝活动
    VOLUNTEERING = "volunteering"  # 志愿活动


class InclusionInitiativeType(str, Enum):
    """包容性举措类型"""
    TRAINING = "training"  # 培训
    POLICY = "policy"  # 政策
    RESOURCE_GROUP = "resource_group"  # 资源小组
    MENTORSHIP = "mentorship"  # 导师计划
    RECRUITING = "recruiting"  # 招聘举措
    ACCESSIBILITY = "accessibility"  # 无障碍设施


class DiversityDimension(str, Enum):
    """多样性维度"""
    GENDER = "gender"  # 性别
    ETHNICITY = "ethnicity"  # 种族
    AGE = "age"  # 年龄
    EDUCATION = "education"  # 教育背景
    GEOGRAPHY = "geography"  # 地理位置
    EXPERIENCE = "experience"  # 工作经验
    SKILLSET = "skillset"  # 技能组合
    PERSONALITY = "personality"  # 性格类型


class SentimentLevel(str, Enum):
    """情感倾向"""
    VERY_POSITIVE = "very_positive"  # 非常积极
    POSITIVE = "positive"  # 积极
    NEUTRAL = "neutral"  # 中性
    NEGATIVE = "negative"  # 消极
    VERY_NEGATIVE = "very_negative"  # 非常消极


# ==================== 数据模型定义 ====================

@dataclass
class CultureValue:
    """文化价值观定义"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = ""
    name: str = ""  # 价值观名称，如"客户第一"
    description: str = ""  # 价值观描述
    value_type: CultureValueType = CultureValueType.CORE
    behavioral_indicators: List[str] = field(default_factory=list)  # 行为指标
    priority: int = 1  # 优先级
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    created_by: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "name": self.name,
            "description": self.description,
            "value_type": self.value_type.value,
            "behavioral_indicators": self.behavioral_indicators,
            "priority": self.priority,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": self.created_by
        }


@dataclass
class CultureValueAlignment:
    """员工文化价值观对齐度"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = ""
    employee_id: str = ""
    culture_value_id: str = ""
    alignment_score: float = 0.0  # 对齐度分数 0-100
    assessment_date: datetime = field(default_factory=datetime.now)
    assessor_id: str = ""  # 评估者 ID
    evidence_examples: List[str] = field(default_factory=list)  # 证据示例
    comments: str = ""
    improvement_suggestions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "employee_id": self.employee_id,
            "culture_value_id": self.culture_value_id,
            "alignment_score": self.alignment_score,
            "assessment_date": self.assessment_date.isoformat(),
            "assessor_id": self.assessor_id,
            "evidence_examples": self.evidence_examples,
            "comments": self.comments,
            "improvement_suggestions": self.improvement_suggestions
        }


@dataclass
class Recognition:
    """员工认可记录"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = ""
    recipient_id: str = ""  # 被认可人 ID
    recipient_type: str = "individual"  # individual/team
    giver_id: str = ""  # 给予认可的人 ID
    recognition_type: RecognitionType = RecognitionType.PEER
    category: RecognitionCategory = RecognitionCategory.OTHER
    title: str = ""
    description: str = ""
    culture_value_ids: List[str] = field(default_factory=list)  # 关联的价值观
    points: int = 0  # 奖励积分
    badge_id: Optional[str] = None  # 关联的徽章 ID
    status: str = "pending"  # pending/approved/rejected
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "recipient_id": self.recipient_id,
            "recipient_type": self.recipient_type,
            "giver_id": self.giver_id,
            "recognition_type": self.recognition_type.value,
            "category": self.category.value,
            "title": self.title,
            "description": self.description,
            "culture_value_ids": self.culture_value_ids,
            "points": self.points,
            "badge_id": self.badge_id,
            "status": self.status,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class Badge:
    """徽章定义"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = ""
    name: str = ""
    description: str = ""
    category: RecognitionCategory = RecognitionCategory.OTHER
    tier: AwardTier = AwardTier.BRONZE
    icon_url: str = ""
    criteria: Dict[str, Any] = field(default_factory=dict)  # 获取标准
    points_value: int = 0  # 积分价值
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "tier": self.tier.value,
            "icon_url": self.icon_url,
            "criteria": self.criteria,
            "points_value": self.points_value,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class EmployeeBadge:
    """员工获得的徽章"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = ""
    employee_id: str = ""
    badge_id: str = ""
    earned_at: datetime = field(default_factory=datetime.now)
    recognition_id: Optional[str] = None  # 关联的认可记录
    expires_at: Optional[datetime] = None  # 过期时间（如有）
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "employee_id": self.employee_id,
            "badge_id": self.badge_id,
            "earned_at": self.earned_at.isoformat(),
            "recognition_id": self.recognition_id,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None
        }


@dataclass
class TeamCohesionEvent:
    """团队凝聚力活动"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = ""
    team_id: str = ""
    organizer_id: str = ""
    event_type: TeamEventType = TeamEventType.TEAM_BUILDING
    title: str = ""
    description: str = ""
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime = field(default_factory=datetime.now)
    location: str = ""  # 地点或虚拟链接
    max_participants: int = 0  # 0 表示无限制
    participants: List[str] = field(default_factory=list)
    status: str = "planned"  # planned/ongoing/completed/cancelled
    budget: Optional[float] = None
    photos: List[str] = field(default_factory=list)
    feedback_summary: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "team_id": self.team_id,
            "organizer_id": self.organizer_id,
            "event_type": self.event_type.value,
            "title": self.title,
            "description": self.description,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "location": self.location,
            "max_participants": self.max_participants,
            "participants": self.participants,
            "status": self.status,
            "budget": self.budget,
            "photos": self.photos,
            "feedback_summary": self.feedback_summary,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class CultureFitAssessment:
    """文化契合度评估"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = ""
    employee_id: str = ""
    assessor_id: str = ""
    assessment_type: str = "self"  # self/manager/peer/team
    overall_score: float = 0.0  # 总体分数 0-100
    dimension_scores: Dict[str, float] = field(default_factory=dict)  # 各维度分数
    strengths: List[str] = field(default_factory=list)  # 优势
    development_areas: List[str] = field(default_factory=list)  # 待发展领域
    comments: str = ""
    recommendations: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "employee_id": self.employee_id,
            "assessor_id": self.assessor_id,
            "assessment_type": self.assessment_type,
            "overall_score": self.overall_score,
            "dimension_scores": self.dimension_scores,
            "strengths": self.strengths,
            "development_areas": self.development_areas,
            "comments": self.comments,
            "recommendations": self.recommendations,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class DiversityMetric:
    """多样性指标"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = ""
    dimension: DiversityDimension = DiversityDimension.GENDER
    team_id: Optional[str] = None  # 团队 ID，为空则为全公司
    metric_date: datetime = field(default_factory=datetime.now)
    distribution: Dict[str, float] = field(default_factory=dict)  # 分布比例
    representation_rate: float = 0.0  # 代表性比例
    inclusion_index: float = 0.0  # 包容性指数
    year_over_year_change: float = 0.0  # 同比变化
    comments: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "dimension": self.dimension.value,
            "team_id": self.team_id,
            "metric_date": self.metric_date.isoformat(),
            "distribution": self.distribution,
            "representation_rate": self.representation_rate,
            "inclusion_index": self.inclusion_index,
            "year_over_year_change": self.year_over_year_change,
            "comments": self.comments
        }


@dataclass
class InclusionInitiative:
    """包容性举措"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = ""
    initiative_type: InclusionInitiativeType = InclusionInitiativeType.TRAINING
    title: str = ""
    description: str = ""
    owner_id: str = ""
    target_dimensions: List[DiversityDimension] = field(default_factory=list)
    start_date: datetime = field(default_factory=datetime.now)
    end_date: Optional[datetime] = None
    status: str = "planned"  # planned/active/completed/cancelled
    budget: Optional[float] = None
    participants: List[str] = field(default_factory=list)
    impact_metrics: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "initiative_type": self.initiative_type.value,
            "title": self.title,
            "description": self.description,
            "owner_id": self.owner_id,
            "target_dimensions": [d.value for d in self.target_dimensions],
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "status": self.status,
            "budget": self.budget,
            "participants": self.participants,
            "impact_metrics": self.impact_metrics,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class CulturePulse:
    """文化脉冲调查"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = ""
    title: str = ""
    question: str = ""
    question_type: str = "scale"  # scale/multiple_choice/open
    scale_min: int = 1  # 量表最小值
    scale_max: int = 5  # 量表最大值
    scale_labels: Dict[int, str] = field(default_factory=dict)  # 量表标签
    options: List[str] = field(default_factory=list)  # 多选选项
    is_anonymous: bool = True
    frequency: str = "weekly"  # daily/weekly/monthly/quarterly
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "title": self.title,
            "question": self.question,
            "question_type": self.question_type,
            "scale_min": self.scale_min,
            "scale_max": self.scale_max,
            "scale_labels": {str(k): v for k, v in self.scale_labels.items()},
            "options": self.options,
            "is_anonymous": self.is_anonymous,
            "frequency": self.frequency,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by
        }


@dataclass
class CulturePulseResponse:
    """文化脉冲调查回复"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    pulse_id: str = ""
    respondent_id: str = ""  # 回复者 ID（匿名时为空）
    is_anonymous: bool = True
    response_value: Optional[float] = None  # 量表/选择值
    response_text: Optional[str] = None  # 开放文本回复
    sentiment: Optional[SentimentLevel] = None  # AI 分析的情感
    submitted_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "pulse_id": self.pulse_id,
            "respondent_id": self.respondent_id if not self.is_anonymous else None,
            "is_anonymous": self.is_anonymous,
            "response_value": self.response_value,
            "response_text": self.response_text,
            "sentiment": self.sentiment.value if self.sentiment else None,
            "submitted_at": self.submitted_at.isoformat()
        }


@dataclass
class RewardRedemption:
    """积分兑换记录"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = ""
    employee_id: str = ""
    reward_name: str = ""
    reward_description: str = ""
    points_cost: int = 0
    status: str = "pending"  # pending/approved/fulfilled/rejected
    requested_at: datetime = field(default_factory=datetime.now)
    approved_at: Optional[datetime] = None
    fulfilled_at: Optional[datetime] = None
    notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "employee_id": self.employee_id,
            "reward_name": self.reward_name,
            "reward_description": self.reward_description,
            "points_cost": self.points_cost,
            "status": self.status,
            "requested_at": self.requested_at.isoformat(),
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "fulfilled_at": self.fulfilled_at.isoformat() if self.fulfilled_at else None,
            "notes": self.notes
        }


@dataclass
class CultureMetrics:
    """文化指标汇总"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = ""
    metric_date: datetime = field(default_factory=datetime.now)
    
    # 文化价值观对齐度
    avg_culture_alignment: float = 0.0
    culture_alignment_distribution: Dict[str, int] = field(default_factory=dict)
    
    # 认可与奖励
    total_recognitions: int = 0
    recognitions_by_category: Dict[str, int] = field(default_factory=dict)
    avg_points_per_employee: float = 0.0
    badges_earned_count: int = 0
    
    # 团队凝聚力
    team_events_count: int = 0
    avg_event_participation: float = 0.0
    
    # 文化契合度
    avg_culture_fit_score: float = 0.0
    
    # 多样性与包容性
    diversity_index: float = 0.0
    inclusion_index: float = 0.0
    
    # 文化脉冲
    pulse_participation_rate: float = 0.0
    avg_pulse_score: float = 0.0
    
    # 整体文化健康度
    overall_culture_health_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "metric_date": self.metric_date.isoformat(),
            "culture_alignment": {
                "avg_alignment": self.avg_culture_alignment,
                "distribution": self.culture_alignment_distribution
            },
            "recognition": {
                "total": self.total_recognitions,
                "by_category": self.recognitions_by_category,
                "avg_points": self.avg_points_per_employee,
                "badges_earned": self.badges_earned_count
            },
            "team_cohesion": {
                "events_count": self.team_events_count,
                "avg_participation": self.avg_event_participation
            },
            "culture_fit": {
                "avg_score": self.avg_culture_fit_score
            },
            "diversity_inclusion": {
                "diversity_index": self.diversity_index,
                "inclusion_index": self.inclusion_index
            },
            "culture_pulse": {
                "participation_rate": self.pulse_participation_rate,
                "avg_score": self.avg_pulse_score
            },
            "overall_health": {
                "score": self.overall_culture_health_score
            }
        }


# ==================== 数据库持久化层 ====================

import sqlite3
from typing import Optional, List as ListType
import json


class CultureDB:
    """组织文化数据库操作"""
    
    _instance: Optional['CultureDB'] = None
    _conn: Optional[sqlite3.Connection] = None
    
    def __new__(cls, db_path: str = "test.db"):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, db_path: str = "test.db"):
        if self._conn is None:
            self.db_path = db_path
            self._init_db()
    
    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None or self.db_path != self._conn.execute("PRAGMA database_list").fetchone()[2]:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
        return self._conn
    
    def _init_db(self):
        """初始化数据库表"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # 文化价值观表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS culture_values (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                value_type TEXT NOT NULL,
                behavioral_indicators TEXT,
                priority INTEGER DEFAULT 1,
                is_active INTEGER DEFAULT 1,
                created_at TEXT,
                updated_at TEXT,
                created_by TEXT
            )
        ''')
        
        # 员工文化对齐度表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS culture_value_alignments (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                employee_id TEXT NOT NULL,
                culture_value_id TEXT NOT NULL,
                alignment_score REAL DEFAULT 0,
                assessment_date TEXT,
                assessor_id TEXT,
                evidence_examples TEXT,
                comments TEXT,
                improvement_suggestions TEXT,
                FOREIGN KEY (culture_value_id) REFERENCES culture_values(id)
            )
        ''')
        
        # 认可记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recognitions (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                recipient_id TEXT NOT NULL,
                recipient_type TEXT DEFAULT 'individual',
                giver_id TEXT NOT NULL,
                recognition_type TEXT NOT NULL,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                culture_value_ids TEXT,
                points INTEGER DEFAULT 0,
                badge_id TEXT,
                status TEXT DEFAULT 'pending',
                approved_by TEXT,
                approved_at TEXT,
                created_at TEXT,
                metadata TEXT,
                FOREIGN KEY (badge_id) REFERENCES badges(id)
            )
        ''')
        
        # 徽章表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS badges (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                category TEXT NOT NULL,
                tier TEXT NOT NULL,
                icon_url TEXT,
                criteria TEXT,
                points_value INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at TEXT
            )
        ''')
        
        # 员工徽章表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS employee_badges (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                employee_id TEXT NOT NULL,
                badge_id TEXT NOT NULL,
                earned_at TEXT,
                recognition_id TEXT,
                expires_at TEXT,
                FOREIGN KEY (badge_id) REFERENCES badges(id),
                FOREIGN KEY (recognition_id) REFERENCES recognitions(id)
            )
        ''')
        
        # 团队活动表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS team_cohesion_events (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                team_id TEXT NOT NULL,
                organizer_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                start_time TEXT,
                end_time TEXT,
                location TEXT,
                max_participants INTEGER DEFAULT 0,
                participants TEXT,
                status TEXT DEFAULT 'planned',
                budget REAL,
                photos TEXT,
                feedback_summary TEXT,
                created_at TEXT
            )
        ''')
        
        # 文化契合度评估表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS culture_fit_assessments (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                employee_id TEXT NOT NULL,
                assessor_id TEXT NOT NULL,
                assessment_type TEXT NOT NULL,
                overall_score REAL DEFAULT 0,
                dimension_scores TEXT,
                strengths TEXT,
                development_areas TEXT,
                comments TEXT,
                recommendations TEXT,
                created_at TEXT
            )
        ''')
        
        # 多样性指标表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS diversity_metrics (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                dimension TEXT NOT NULL,
                team_id TEXT,
                metric_date TEXT,
                distribution TEXT,
                representation_rate REAL DEFAULT 0,
                inclusion_index REAL DEFAULT 0,
                year_over_year_change REAL DEFAULT 0,
                comments TEXT
            )
        ''')
        
        # 包容性举措表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inclusion_initiatives (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                initiative_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                owner_id TEXT NOT NULL,
                target_dimensions TEXT,
                start_date TEXT,
                end_date TEXT,
                status TEXT DEFAULT 'planned',
                budget REAL,
                participants TEXT,
                impact_metrics TEXT,
                created_at TEXT
            )
        ''')
        
        # 文化脉冲调查表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS culture_pulses (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                title TEXT NOT NULL,
                question TEXT NOT NULL,
                question_type TEXT NOT NULL,
                scale_min INTEGER DEFAULT 1,
                scale_max INTEGER DEFAULT 5,
                scale_labels TEXT,
                options TEXT,
                is_anonymous INTEGER DEFAULT 1,
                frequency TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at TEXT,
                created_by TEXT
            )
        ''')
        
        # 文化脉冲回复表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS culture_pulse_responses (
                id TEXT PRIMARY KEY,
                pulse_id TEXT NOT NULL,
                respondent_id TEXT,
                is_anonymous INTEGER DEFAULT 1,
                response_value REAL,
                response_text TEXT,
                sentiment TEXT,
                submitted_at TEXT,
                FOREIGN KEY (pulse_id) REFERENCES culture_pulses(id)
            )
        ''')
        
        # 积分兑换表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reward_redemptions (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                employee_id TEXT NOT NULL,
                reward_name TEXT NOT NULL,
                reward_description TEXT,
                points_cost INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                requested_at TEXT,
                approved_at TEXT,
                fulfilled_at TEXT,
                notes TEXT
            )
        ''')
        
        # 文化指标汇总表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS culture_metrics (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                metric_date TEXT NOT NULL,
                avg_culture_alignment REAL DEFAULT 0,
                culture_alignment_distribution TEXT,
                total_recognitions INTEGER DEFAULT 0,
                recognitions_by_category TEXT,
                avg_points_per_employee REAL DEFAULT 0,
                badges_earned_count INTEGER DEFAULT 0,
                team_events_count INTEGER DEFAULT 0,
                avg_event_participation REAL DEFAULT 0,
                avg_culture_fit_score REAL DEFAULT 0,
                diversity_index REAL DEFAULT 0,
                inclusion_index REAL DEFAULT 0,
                pulse_participation_rate REAL DEFAULT 0,
                avg_pulse_score REAL DEFAULT 0,
                overall_culture_health_score REAL DEFAULT 0,
                UNIQUE(tenant_id, metric_date)
            )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_culture_values_tenant ON culture_values(tenant_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_recognitions_tenant ON recognitions(tenant_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_recognitions_recipient ON recognitions(recipient_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_badges_tenant ON badges(tenant_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_culture_fit_employee ON culture_fit_assessments(employee_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_diversity_metrics_tenant ON diversity_metrics(tenant_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_culture_pulses_tenant ON culture_pulses(tenant_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_culture_metrics_tenant ON culture_metrics(tenant_id, metric_date)')
        
        conn.commit()
    
    # ==================== CRUD 操作方法 ====================
    
    def save_culture_value(self, value: CultureValue) -> CultureValue:
        """保存文化价值观"""
        conn = self._get_conn()
        cursor = conn.cursor()
        value.updated_at = datetime.now()
        
        cursor.execute('''
            INSERT OR REPLACE INTO culture_values 
            (id, tenant_id, name, description, value_type, behavioral_indicators, priority, is_active, created_at, updated_at, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            value.id, value.tenant_id, value.name, value.description,
            value.value_type.value, json.dumps(value.behavioral_indicators),
            value.priority, 1 if value.is_active else 0,
            value.created_at.isoformat(), value.updated_at.isoformat(), value.created_by
        ))
        conn.commit()
        return value
    
    def get_culture_value(self, value_id: str) -> Optional[CultureValue]:
        """获取文化价值观"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM culture_values WHERE id = ?', (value_id,))
        row = cursor.fetchone()
        if row:
            return self._row_to_culture_value(row)
        return None
    
    def list_culture_values(self, tenant_id: str, active_only: bool = True) -> ListType[CultureValue]:
        """列出文化价值观"""
        conn = self._get_conn()
        cursor = conn.cursor()
        query = 'SELECT * FROM culture_values WHERE tenant_id = ?'
        if active_only:
            query += ' AND is_active = 1'
        query += ' ORDER BY priority ASC, created_at DESC'
        cursor.execute(query, (tenant_id,))
        return [self._row_to_culture_value(row) for row in cursor.fetchall()]
    
    def delete_culture_value(self, value_id: str) -> bool:
        """删除文化价值观"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM culture_values WHERE id = ?', (value_id,))
        conn.commit()
        return cursor.rowcount > 0
    
    def save_alignment(self, alignment: CultureValueAlignment) -> CultureValueAlignment:
        """保存文化对齐度评估"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO culture_value_alignments 
            (id, tenant_id, employee_id, culture_value_id, alignment_score, assessment_date, assessor_id, evidence_examples, comments, improvement_suggestions)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            alignment.id, alignment.tenant_id, alignment.employee_id, alignment.culture_value_id,
            alignment.alignment_score, alignment.assessment_date.isoformat(), alignment.assessor_id,
            json.dumps(alignment.evidence_examples), alignment.comments,
            json.dumps(alignment.improvement_suggestions)
        ))
        conn.commit()
        return alignment
    
    def get_employee_alignments(self, employee_id: str) -> ListType[CultureValueAlignment]:
        """获取员工的文化对齐度"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM culture_value_alignments WHERE employee_id = ?', (employee_id,))
        return [self._row_to_alignment(row) for row in cursor.fetchall()]
    
    def save_recognition(self, recognition: Recognition) -> Recognition:
        """保存认可记录"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO recognitions 
            (id, tenant_id, recipient_id, recipient_type, giver_id, recognition_type, category, title, description, culture_value_ids, points, badge_id, status, approved_by, approved_at, created_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            recognition.id, recognition.tenant_id, recognition.recipient_id, recognition.recipient_type,
            recognition.giver_id, recognition.recognition_type.value, recognition.category.value,
            recognition.title, recognition.description, json.dumps(recognition.culture_value_ids),
            recognition.points, recognition.badge_id, recognition.status, recognition.approved_by,
            recognition.approved_at.isoformat() if recognition.approved_at else None,
            recognition.created_at.isoformat(), json.dumps(recognition.metadata)
        ))
        conn.commit()
        return recognition
    
    def get_recognition(self, recognition_id: str) -> Optional[Recognition]:
        """获取认可记录"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM recognitions WHERE id = ?', (recognition_id,))
        row = cursor.fetchone()
        if row:
            return self._row_to_recognition(row)
        return None
    
    def list_recognitions(self, tenant_id: str, recipient_id: Optional[str] = None, 
                          limit: int = 50) -> ListType[Recognition]:
        """列出认可记录"""
        conn = self._get_conn()
        cursor = conn.cursor()
        query = 'SELECT * FROM recognitions WHERE tenant_id = ?'
        params = [tenant_id]
        if recipient_id:
            query += ' AND recipient_id = ?'
            params.append(recipient_id)
        query += ' ORDER BY created_at DESC LIMIT ?'
        params.append(limit)
        cursor.execute(query, params)
        return [self._row_to_recognition(row) for row in cursor.fetchall()]
    
    def save_badge(self, badge: Badge) -> Badge:
        """保存徽章"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO badges 
            (id, tenant_id, name, description, category, tier, icon_url, criteria, points_value, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            badge.id, badge.tenant_id, badge.name, badge.description,
            badge.category.value, badge.tier.value, badge.icon_url,
            json.dumps(badge.criteria), badge.points_value,
            1 if badge.is_active else 0, badge.created_at.isoformat()
        ))
        conn.commit()
        return badge
    
    def list_badges(self, tenant_id: str, active_only: bool = True) -> ListType[Badge]:
        """列出徽章"""
        conn = self._get_conn()
        cursor = conn.cursor()
        query = 'SELECT * FROM badges WHERE tenant_id = ?'
        if active_only:
            query += ' AND is_active = 1'
        cursor.execute(query, (tenant_id,))
        return [self._row_to_badge(row) for row in cursor.fetchall()]
    
    def award_badge(self, employee_badge: EmployeeBadge) -> EmployeeBadge:
        """授予员工徽章"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO employee_badges (id, tenant_id, employee_id, badge_id, earned_at, recognition_id, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            employee_badge.id, employee_badge.tenant_id, employee_badge.employee_id,
            employee_badge.badge_id, employee_badge.earned_at.isoformat(),
            employee_badge.recognition_id,
            employee_badge.expires_at.isoformat() if employee_badge.expires_at else None
        ))
        conn.commit()
        return employee_badge
    
    def get_employee_badges(self, employee_id: str) -> ListType[EmployeeBadge]:
        """获取员工的徽章"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM employee_badges WHERE employee_id = ?', (employee_id,))
        return [self._row_to_employee_badge(row) for row in cursor.fetchall()]
    
    def save_team_event(self, event: TeamCohesionEvent) -> TeamCohesionEvent:
        """保存团队活动"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO team_cohesion_events 
            (id, tenant_id, team_id, organizer_id, event_type, title, description, start_time, end_time, location, max_participants, participants, status, budget, photos, feedback_summary, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            event.id, event.tenant_id, event.team_id, event.organizer_id,
            event.event_type.value, event.title, event.description,
            event.start_time.isoformat(), event.end_time.isoformat(), event.location,
            event.max_participants, json.dumps(event.participants), event.status,
            event.budget, json.dumps(event.photos), event.feedback_summary,
            event.created_at.isoformat()
        ))
        conn.commit()
        return event
    
    def get_team_event(self, event_id: str) -> Optional[TeamCohesionEvent]:
        """获取团队活动"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM team_cohesion_events WHERE id = ?', (event_id,))
        row = cursor.fetchone()
        if row:
            return self._row_to_team_event(row)
        return None
    
    def list_team_events(self, tenant_id: str, team_id: Optional[str] = None) -> ListType[TeamCohesionEvent]:
        """列出团队活动"""
        conn = self._get_conn()
        cursor = conn.cursor()
        query = 'SELECT * FROM team_cohesion_events WHERE tenant_id = ?'
        params = [tenant_id]
        if team_id:
            query += ' AND team_id = ?'
            params.append(team_id)
        query += ' ORDER BY start_time DESC'
        cursor.execute(query, params)
        return [self._row_to_team_event(row) for row in cursor.fetchall()]
    
    def save_culture_fit_assessment(self, assessment: CultureFitAssessment) -> CultureFitAssessment:
        """保存文化契合度评估"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO culture_fit_assessments 
            (id, tenant_id, employee_id, assessor_id, assessment_type, overall_score, dimension_scores, strengths, development_areas, comments, recommendations, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            assessment.id, assessment.tenant_id, assessment.employee_id, assessment.assessor_id,
            assessment.assessment_type, assessment.overall_score, json.dumps(assessment.dimension_scores),
            json.dumps(assessment.strengths), json.dumps(assessment.development_areas),
            assessment.comments, json.dumps(assessment.recommendations),
            assessment.created_at.isoformat()
        ))
        conn.commit()
        return assessment
    
    def get_employee_culture_fit(self, employee_id: str) -> ListType[CultureFitAssessment]:
        """获取员工的文化契合度评估"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM culture_fit_assessments WHERE employee_id = ? ORDER BY created_at DESC', (employee_id,))
        return [self._row_to_culture_fit_assessment(row) for row in cursor.fetchall()]
    
    def save_diversity_metric(self, metric: DiversityMetric) -> DiversityMetric:
        """保存多样性指标"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO diversity_metrics 
            (id, tenant_id, dimension, team_id, metric_date, distribution, representation_rate, inclusion_index, year_over_year_change, comments)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            metric.id, metric.tenant_id, metric.dimension.value, metric.team_id,
            metric.metric_date.isoformat(), json.dumps(metric.distribution),
            metric.representation_rate, metric.inclusion_index,
            metric.year_over_year_change, metric.comments
        ))
        conn.commit()
        return metric
    
    def get_diversity_metrics(self, tenant_id: str, dimension: Optional[DiversityDimension] = None) -> ListType[DiversityMetric]:
        """获取多样性指标"""
        conn = self._get_conn()
        cursor = conn.cursor()
        query = 'SELECT * FROM diversity_metrics WHERE tenant_id = ?'
        params = [tenant_id]
        if dimension:
            query += ' AND dimension = ?'
            params.append(dimension.value)
        query += ' ORDER BY metric_date DESC'
        cursor.execute(query, params)
        return [self._row_to_diversity_metric(row) for row in cursor.fetchall()]
    
    def save_inclusion_initiative(self, initiative: InclusionInitiative) -> InclusionInitiative:
        """保存包容性举措"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO inclusion_initiatives 
            (id, tenant_id, initiative_type, title, description, owner_id, target_dimensions, start_date, end_date, status, budget, participants, impact_metrics, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            initiative.id, initiative.tenant_id, initiative.initiative_type.value,
            initiative.title, initiative.description, initiative.owner_id,
            json.dumps([d.value for d in initiative.target_dimensions]),
            initiative.start_date.isoformat(),
            initiative.end_date.isoformat() if initiative.end_date else None,
            initiative.status, initiative.budget, json.dumps(initiative.participants),
            json.dumps(initiative.impact_metrics), initiative.created_at.isoformat()
        ))
        conn.commit()
        return initiative
    
    def list_inclusion_initiatives(self, tenant_id: str, status: Optional[str] = None) -> ListType[InclusionInitiative]:
        """列出包容性举措"""
        conn = self._get_conn()
        cursor = conn.cursor()
        query = 'SELECT * FROM inclusion_initiatives WHERE tenant_id = ?'
        params = [tenant_id]
        if status:
            query += ' AND status = ?'
            params.append(status)
        cursor.execute(query, params)
        return [self._row_to_inclusion_initiative(row) for row in cursor.fetchall()]
    
    def save_culture_pulse(self, pulse: CulturePulse) -> CulturePulse:
        """保存文化脉冲调查"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO culture_pulses 
            (id, tenant_id, title, question, question_type, scale_min, scale_max, scale_labels, options, is_anonymous, frequency, is_active, created_at, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            pulse.id, pulse.tenant_id, pulse.title, pulse.question,
            pulse.question_type, pulse.scale_min, pulse.scale_max,
            json.dumps({str(k): v for k, v in pulse.scale_labels.items()}),
            json.dumps(pulse.options), 1 if pulse.is_anonymous else 0,
            pulse.frequency, 1 if pulse.is_active else 0,
            pulse.created_at.isoformat(), pulse.created_by
        ))
        conn.commit()
        return pulse
    
    def list_culture_pulses(self, tenant_id: str, active_only: bool = True) -> ListType[CulturePulse]:
        """列出文化脉冲调查"""
        conn = self._get_conn()
        cursor = conn.cursor()
        query = 'SELECT * FROM culture_pulses WHERE tenant_id = ?'
        if active_only:
            query += ' AND is_active = 1'
        query += ' ORDER BY created_at DESC'
        cursor.execute(query, (tenant_id,))
        return [self._row_to_culture_pulse(row) for row in cursor.fetchall()]
    
    def save_pulse_response(self, response: CulturePulseResponse) -> CulturePulseResponse:
        """保存脉冲调查回复"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO culture_pulse_responses 
            (id, pulse_id, respondent_id, is_anonymous, response_value, response_text, sentiment, submitted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            response.id, response.pulse_id, response.respondent_id,
            1 if response.is_anonymous else 0, response.response_value,
            response.response_text, response.sentiment.value if response.sentiment else None,
            response.submitted_at.isoformat()
        ))
        conn.commit()
        return response
    
    def get_pulse_responses(self, pulse_id: str) -> ListType[CulturePulseResponse]:
        """获取脉冲调查回复"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM culture_pulse_responses WHERE pulse_id = ?', (pulse_id,))
        return [self._row_to_pulse_response(row) for row in cursor.fetchall()]
    
    def save_reward_redemption(self, redemption: RewardRedemption) -> RewardRedemption:
        """保存积分兑换"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO reward_redemptions 
            (id, tenant_id, employee_id, reward_name, reward_description, points_cost, status, requested_at, approved_at, fulfilled_at, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            redemption.id, redemption.tenant_id, redemption.employee_id,
            redemption.reward_name, redemption.reward_description, redemption.points_cost,
            redemption.status, redemption.requested_at.isoformat(),
            redemption.approved_at.isoformat() if redemption.approved_at else None,
            redemption.fulfilled_at.isoformat() if redemption.fulfilled_at else None,
            redemption.notes
        ))
        conn.commit()
        return redemption
    
    def get_employee_redemptions(self, employee_id: str) -> ListType[RewardRedemption]:
        """获取员工的积分兑换记录"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM reward_redemptions WHERE employee_id = ? ORDER BY requested_at DESC', (employee_id,))
        return [self._row_to_reward_redemption(row) for row in cursor.fetchall()]
    
    def save_culture_metrics(self, metrics: CultureMetrics) -> CultureMetrics:
        """保存文化指标"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO culture_metrics 
            (id, tenant_id, metric_date, avg_culture_alignment, culture_alignment_distribution, total_recognitions, recognitions_by_category, avg_points_per_employee, badges_earned_count, team_events_count, avg_event_participation, avg_culture_fit_score, diversity_index, inclusion_index, pulse_participation_rate, avg_pulse_score, overall_culture_health_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            metrics.id, metrics.tenant_id, metrics.metric_date.isoformat(),
            metrics.avg_culture_alignment, json.dumps(metrics.culture_alignment_distribution),
            metrics.total_recognitions, json.dumps(metrics.recognitions_by_category),
            metrics.avg_points_per_employee, metrics.badges_earned_count,
            metrics.team_events_count, metrics.avg_event_participation,
            metrics.avg_culture_fit_score, metrics.diversity_index,
            metrics.inclusion_index, metrics.pulse_participation_rate,
            metrics.avg_pulse_score, metrics.overall_culture_health_score
        ))
        conn.commit()
        return metrics
    
    def get_culture_metrics(self, tenant_id: str, start_date: Optional[datetime] = None, 
                            end_date: Optional[datetime] = None) -> ListType[CultureMetrics]:
        """获取文化指标"""
        conn = self._get_conn()
        cursor = conn.cursor()
        query = 'SELECT * FROM culture_metrics WHERE tenant_id = ?'
        params = [tenant_id]
        if start_date:
            query += ' AND metric_date >= ?'
            params.append(start_date.isoformat())
        if end_date:
            query += ' AND metric_date <= ?'
            params.append(end_date.isoformat())
        query += ' ORDER BY metric_date DESC'
        cursor.execute(query, params)
        return [self._row_to_culture_metrics(row) for row in cursor.fetchall()]
    
    # ==================== 辅助方法 ====================
    
    def _row_to_culture_value(self, row: sqlite3.Row) -> CultureValue:
        return CultureValue(
            id=row["id"], tenant_id=row["tenant_id"], name=row["name"],
            description=row["description"],
            value_type=CultureValueType(row["value_type"]),
            behavioral_indicators=json.loads(row["behavioral_indicators"] or "[]"),
            priority=row["priority"], is_active=bool(row["is_active"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            created_by=row["created_by"]
        )
    
    def _row_to_alignment(self, row: sqlite3.Row) -> CultureValueAlignment:
        return CultureValueAlignment(
            id=row["id"], tenant_id=row["tenant_id"], employee_id=row["employee_id"],
            culture_value_id=row["culture_value_id"], alignment_score=row["alignment_score"],
            assessment_date=datetime.fromisoformat(row["assessment_date"]),
            assessor_id=row["assessor_id"],
            evidence_examples=json.loads(row["evidence_examples"] or "[]"),
            comments=row["comments"],
            improvement_suggestions=json.loads(row["improvement_suggestions"] or "[]")
        )
    
    def _row_to_recognition(self, row: sqlite3.Row) -> Recognition:
        return Recognition(
            id=row["id"], tenant_id=row["tenant_id"], recipient_id=row["recipient_id"],
            recipient_type=row["recipient_type"], giver_id=row["giver_id"],
            recognition_type=RecognitionType(row["recognition_type"]),
            category=RecognitionCategory(row["category"]),
            title=row["title"], description=row["description"],
            culture_value_ids=json.loads(row["culture_value_ids"] or "[]"),
            points=row["points"], badge_id=row["badge_id"],
            status=row["status"], approved_by=row["approved_by"],
            approved_at=datetime.fromisoformat(row["approved_at"]) if row["approved_at"] else None,
            created_at=datetime.fromisoformat(row["created_at"]),
            metadata=json.loads(row["metadata"] or "{}")
        )
    
    def _row_to_badge(self, row: sqlite3.Row) -> Badge:
        return Badge(
            id=row["id"], tenant_id=row["tenant_id"], name=row["name"],
            description=row["description"],
            category=RecognitionCategory(row["category"]),
            tier=AwardTier(row["tier"]), icon_url=row["icon_url"],
            criteria=json.loads(row["criteria"] or "{}"),
            points_value=row["points_value"], is_active=bool(row["is_active"]),
            created_at=datetime.fromisoformat(row["created_at"])
        )
    
    def _row_to_employee_badge(self, row: sqlite3.Row) -> EmployeeBadge:
        return EmployeeBadge(
            id=row["id"], tenant_id=row["tenant_id"], employee_id=row["employee_id"],
            badge_id=row["badge_id"],
            earned_at=datetime.fromisoformat(row["earned_at"]),
            recognition_id=row["recognition_id"],
            expires_at=datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None
        )
    
    def _row_to_team_event(self, row: sqlite3.Row) -> TeamCohesionEvent:
        return TeamCohesionEvent(
            id=row["id"], tenant_id=row["tenant_id"], team_id=row["team_id"],
            organizer_id=row["organizer_id"],
            event_type=TeamEventType(row["event_type"]),
            title=row["title"], description=row["description"],
            start_time=datetime.fromisoformat(row["start_time"]),
            end_time=datetime.fromisoformat(row["end_time"]),
            location=row["location"], max_participants=row["max_participants"],
            participants=json.loads(row["participants"] or "[]"),
            status=row["status"], budget=row["budget"],
            photos=json.loads(row["photos"] or "[]"),
            feedback_summary=row["feedback_summary"],
            created_at=datetime.fromisoformat(row["created_at"])
        )
    
    def _row_to_culture_fit_assessment(self, row: sqlite3.Row) -> CultureFitAssessment:
        return CultureFitAssessment(
            id=row["id"], tenant_id=row["tenant_id"], employee_id=row["employee_id"],
            assessor_id=row["assessor_id"], assessment_type=row["assessment_type"],
            overall_score=row["overall_score"],
            dimension_scores=json.loads(row["dimension_scores"] or "{}"),
            strengths=json.loads(row["strengths"] or "[]"),
            development_areas=json.loads(row["development_areas"] or "[]"),
            comments=row["comments"],
            recommendations=json.loads(row["recommendations"] or "[]"),
            created_at=datetime.fromisoformat(row["created_at"])
        )
    
    def _row_to_diversity_metric(self, row: sqlite3.Row) -> DiversityMetric:
        return DiversityMetric(
            id=row["id"], tenant_id=row["tenant_id"],
            dimension=DiversityDimension(row["dimension"]),
            team_id=row["team_id"],
            metric_date=datetime.fromisoformat(row["metric_date"]),
            distribution=json.loads(row["distribution"] or "{}"),
            representation_rate=row["representation_rate"],
            inclusion_index=row["inclusion_index"],
            year_over_year_change=row["year_over_year_change"],
            comments=row["comments"]
        )
    
    def _row_to_inclusion_initiative(self, row: sqlite3.Row) -> InclusionInitiative:
        return InclusionInitiative(
            id=row["id"], tenant_id=row["tenant_id"],
            initiative_type=InclusionInitiativeType(row["initiative_type"]),
            title=row["title"], description=row["description"],
            owner_id=row["owner_id"],
            target_dimensions=[DiversityDimension(d) for d in json.loads(row["target_dimensions"] or "[]")],
            start_date=datetime.fromisoformat(row["start_date"]),
            end_date=datetime.fromisoformat(row["end_date"]) if row["end_date"] else None,
            status=row["status"], budget=row["budget"],
            participants=json.loads(row["participants"] or "[]"),
            impact_metrics=json.loads(row["impact_metrics"] or "{}"),
            created_at=datetime.fromisoformat(row["created_at"])
        )
    
    def _row_to_culture_pulse(self, row: sqlite3.Row) -> CulturePulse:
        return CulturePulse(
            id=row["id"], tenant_id=row["tenant_id"], title=row["title"],
            question=row["question"], question_type=row["question_type"],
            scale_min=row["scale_min"], scale_max=row["scale_max"],
            scale_labels={int(k): v for k, v in json.loads(row["scale_labels"] or "{}").items()},
            options=json.loads(row["options"] or "[]"),
            is_anonymous=bool(row["is_anonymous"]),
            frequency=row["frequency"], is_active=bool(row["is_active"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            created_by=row["created_by"]
        )
    
    def _row_to_pulse_response(self, row: sqlite3.Row) -> CulturePulseResponse:
        return CulturePulseResponse(
            id=row["id"], pulse_id=row["pulse_id"],
            respondent_id=row["respondent_id"],
            is_anonymous=bool(row["is_anonymous"]),
            response_value=row["response_value"],
            response_text=row["response_text"],
            sentiment=SentimentLevel(row["sentiment"]) if row["sentiment"] else None,
            submitted_at=datetime.fromisoformat(row["submitted_at"])
        )
    
    def _row_to_reward_redemption(self, row: sqlite3.Row) -> RewardRedemption:
        return RewardRedemption(
            id=row["id"], tenant_id=row["tenant_id"], employee_id=row["employee_id"],
            reward_name=row["reward_name"], reward_description=row["reward_description"],
            points_cost=row["points_cost"], status=row["status"],
            requested_at=datetime.fromisoformat(row["requested_at"]),
            approved_at=datetime.fromisoformat(row["approved_at"]) if row["approved_at"] else None,
            fulfilled_at=datetime.fromisoformat(row["fulfilled_at"]) if row["fulfilled_at"] else None,
            notes=row["notes"]
        )
    
    def _row_to_culture_metrics(self, row: sqlite3.Row) -> CultureMetrics:
        return CultureMetrics(
            id=row["id"], tenant_id=row["tenant_id"],
            metric_date=datetime.fromisoformat(row["metric_date"]),
            avg_culture_alignment=row["avg_culture_alignment"],
            culture_alignment_distribution=json.loads(row["culture_alignment_distribution"] or "{}"),
            total_recognitions=row["total_recognitions"],
            recognitions_by_category=json.loads(row["recognitions_by_category"] or "{}"),
            avg_points_per_employee=row["avg_points_per_employee"],
            badges_earned_count=row["badges_earned_count"],
            team_events_count=row["team_events_count"],
            avg_event_participation=row["avg_event_participation"],
            avg_culture_fit_score=row["avg_culture_fit_score"],
            diversity_index=row["diversity_index"],
            inclusion_index=row["inclusion_index"],
            pulse_participation_rate=row["pulse_participation_rate"],
            avg_pulse_score=row["avg_pulse_score"],
            overall_culture_health_score=row["overall_culture_health_score"]
        )


# 导出所有公共类
__all__ = [
    # 枚举
    'CultureValueType',
    'RecognitionType',
    'RecognitionCategory',
    'AwardTier',
    'TeamEventType',
    'InclusionInitiativeType',
    'DiversityDimension',
    'SentimentLevel',
    # 数据模型
    'CultureValue',
    'CultureValueAlignment',
    'Recognition',
    'Badge',
    'EmployeeBadge',
    'TeamCohesionEvent',
    'CultureFitAssessment',
    'DiversityMetric',
    'InclusionInitiative',
    'CulturePulse',
    'CulturePulseResponse',
    'RewardRedemption',
    'CultureMetrics',
    # 数据库
    'CultureDB'
]
