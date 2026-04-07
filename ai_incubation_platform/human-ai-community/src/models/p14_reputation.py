"""
P14 声誉系统增强实体模型

实现人类与 AI 共享的声誉评分系统，包括：
- 多维度声誉评分
- 声誉等级与权益
- 行为追踪（正面/负面）
- 声誉恢复机制
- 声誉排行榜
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid


# ==================== 声誉维度 ====================

class ReputationDimension(str, Enum):
    """声誉评估维度"""
    CONTENT_QUALITY = "content_quality"  # 内容质量
    COMMUNITY_CONTRIBUTION = "community_contribution"  # 社区贡献
    COLLABORATION = "collaboration"  # 协作能力
    TRUSTWORTHINESS = "trustworthiness"  # 可信度


class BehaviorType(str, Enum):
    """行为类型"""
    POST_CREATE = "post_create"  # 发帖
    POST_UPVOTED = "post_upvoted"  # 帖子被点赞
    POST_DOWNVOTED = "post_downvoted"  # 帖子被踩
    COMMENT_CREATE = "comment_create"  # 评论
    COMMENT_UPVOTED = "comment_upvoted"  # 评论被点赞
    COMMENT_DOWNVOTED = "comment_downvoted"  # 评论被踩
    HELP_OTHERS = "help_others"  # 帮助他人
    REPORT_VIOLATION = "report_violation"  # 举报违规
    VIOLATION_DETECTED = "violation_detected"  # 违规 detected
    CONTENT_DELETED = "content_deleted"  # 内容被删除
    SPAM_DETECTED = "spam_detected"  # 垃圾内容 detected
    DAILY_CHECKIN = "daily_checkin"  # 每日签到
    CONTENT_EDITED = "content_edited"  # 内容编辑改进


class ReputationLevel(str, Enum):
    """声誉等级"""
    NEWCOMER = "newcomer"  # 新人 (0-100)
    BASIC = "basic"  # 基础 (101-300)
    REGULAR = "regular"  # 普通成员 (301-500)
    ACTIVE = "active"  # 活跃成员 (501-700)
    CONTRIBUTOR = "contributor"  # 贡献者 (701-850)
    LEADER = "leader"  # 领导者 (851-950)
    LEGEND = "legend"  # 传奇 (951-1000)


class ReputationPrivilege(BaseModel):
    """声誉权益"""
    level: ReputationLevel
    min_score: int
    max_score: int
    privileges: List[str]  # 权益列表
    description: str


# ==================== 声誉记录 ====================

class MemberReputation(BaseModel):
    """成员声誉记录（人类与 AI 共享）"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    member_id: str  # 成员 ID（人类或 AI）
    member_type: str = Field(..., description="成员类型：human/ai")  # 成员类型

    # 总体声誉
    total_score: int = Field(default=100, ge=0, le=1000)  # 总分 0-1000
    level: ReputationLevel = ReputationLevel.NEWCOMER

    # 多维度评分（各维度 0-100）
    content_quality_score: float = Field(default=50.0, ge=0, le=100)  # 内容质量
    community_contribution_score: float = Field(default=50.0, ge=0, le=100)  # 社区贡献
    collaboration_score: float = Field(default=50.0, ge=0, le=100)  # 协作能力
    trustworthiness_score: float = Field(default=50.0, ge=0, le=100)  # 可信度

    # 行为统计
    total_posts: int = 0  # 总发帖数
    total_comments: int = 0  # 总评论数
    total_upvotes_received: int = 0  # 收到的总点赞
    total_downvotes_received: int = 0  # 收到的总踩
    helpful_actions: int = 0  # 有益行为数
    violation_actions: int = 0  # 违规行为数

    # 声誉历史
    positive_actions: int = 0  # 正面行为数
    negative_actions: int = 0  # 负面行为数

    # 恢复机制
    probation_mode: bool = False  # 观察模式
    probation_end_date: Optional[datetime] = None  # 观察期结束日期
    restoration_progress: float = Field(default=0.0, ge=0, le=1)  # 恢复进度

    # 时间
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    last_action_at: Optional[datetime] = None

    @property
    def dimension_scores(self) -> Dict[str, float]:
        """获取各维度评分"""
        return {
            ReputationDimension.CONTENT_QUALITY.value: self.content_quality_score,
            ReputationDimension.COMMUNITY_CONTRIBUTION.value: self.community_contribution_score,
            ReputationDimension.COLLABORATION.value: self.collaboration_score,
            ReputationDimension.TRUSTWORTHINESS.value: self.trustworthiness_score,
        }

    def calculate_level(self) -> ReputationLevel:
        """根据总分计算声誉等级"""
        if self.total_score <= 100:
            return ReputationLevel.NEWCOMER
        elif self.total_score <= 300:
            return ReputationLevel.BASIC
        elif self.total_score <= 500:
            return ReputationLevel.REGULAR
        elif self.total_score <= 700:
            return ReputationLevel.ACTIVE
        elif self.total_score <= 850:
            return ReputationLevel.CONTRIBUTOR
        elif self.total_score <= 950:
            return ReputationLevel.LEADER
        else:
            return ReputationLevel.LEGEND


class ReputationBehaviorLog(BaseModel):
    """声誉行为日志"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    member_id: str  # 成员 ID
    member_type: str  # 成员类型

    # 行为信息
    behavior_type: BehaviorType  # 行为类型
    is_positive: bool  # 是否为正面行为
    description: str  # 行为描述

    # 关联内容
    content_id: Optional[str] = None  # 关联内容 ID
    content_type: Optional[str] = None  # 关联内容类型

    # 影响
    score_delta: int  # 分数变化
    dimension_affected: Optional[ReputationDimension] = None  # 影响的维度

    # 上下文
    context: Dict[str, Any] = Field(default_factory=dict)  # 上下文信息
    ip_address: Optional[str] = None  # IP 地址

    # 时间
    created_at: datetime = Field(default_factory=datetime.now)


class ReputationRestoration(BaseModel):
    """声誉恢复记录"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    member_id: str
    member_type: str

    # 恢复前状态
    previous_score: int
    previous_level: ReputationLevel

    # 恢复原因
    reason: str  # 恢复原因
    reason_type: str  # 原因类型：appeal, auto_restore, admin_action

    # 恢复动作
    restoration_actions: List[str] = Field(default_factory=list)  # 恢复动作列表
    completed_actions: List[str] = Field(default_factory=list)  # 已完成动作

    # 恢复进度
    progress: float = Field(default=0.0, ge=0, le=1)  # 恢复进度 0-1
    target_score: int  # 目标分数

    # 状态
    status: str = Field(default="in_progress", description="状态：in_progress, completed, failed")

    # 时间
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    # 审核
    reviewer_id: Optional[str] = None  # 审核者 ID
    reviewer_note: Optional[str] = None  # 审核备注


# ==================== 声誉排行榜 ====================

class ReputationRankingEntry(BaseModel):
    """声誉排行榜条目"""
    rank: int
    member_id: str
    member_name: str
    member_type: str  # human/ai
    total_score: int
    level: ReputationLevel
    # 各维度分数
    content_quality_score: float
    community_contribution_score: float
    collaboration_score: float
    trustworthiness_score: float
    # 统计
    total_posts: int
    total_upvotes_received: int
    positive_rate: float  # 正面行为率


class ReputationRankingType(str, Enum):
    """排行榜类型"""
    OVERALL = "overall"  # 综合排行
    CONTENT_QUALITY = "content_quality"  # 内容质量排行
    COMMUNITY_CONTRIBUTION = "community_contribution"  # 社区贡献排行
    COLLABORATION = "collaboration"  # 协作能力排行
    TRUSTWORTHINESS = "trustworthiness"  # 可信度排行
    NEWCOMER = "newcomer"  # 新人进步排行
    AI_AGENT = "ai_agent"  # AI Agent 排行
    HUMAN = "human"  # 人类用户排行


# ==================== 请求/响应模型 ====================

class ReputationQuery(BaseModel):
    """声誉查询参数"""
    member_id: Optional[str] = None
    member_type: Optional[str] = None
    level: Optional[ReputationLevel] = None
    min_score: Optional[int] = Field(None, ge=0, le=1000)
    max_score: Optional[int] = Field(None, ge=0, le=1000)
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class RankingQuery(BaseModel):
    """排行榜查询参数"""
    ranking_type: ReputationRankingType = ReputationRankingType.OVERALL
    member_type: Optional[str] = None  # human/ai
    limit: int = Field(default=100, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class RestorationRequest(BaseModel):
    """声誉恢复申请"""
    member_id: str
    member_type: str
    reason: str
    commitment_actions: List[str] = Field(default_factory=list)  # 承诺完成的恢复动作


class RestorationAction(BaseModel):
    """声誉恢复动作"""
    action_type: str
    description: str
    score_reward: int  # 完成动作可获得的分数奖励
    difficulty: str = Field(default="medium", description="难度：easy, medium, hard")


# ==================== 权益配置 ====================

REPUTATION_PRIVILEGES: Dict[ReputationLevel, ReputationPrivilege] = {
    ReputationLevel.NEWCOMER: ReputationPrivilege(
        level=ReputationLevel.NEWCOMER,
        min_score=0,
        max_score=100,
        privileges=[
            "view_content",  # 查看内容
            "basic_search",  # 基础搜索
        ],
        description="新人阶段 - 熟悉社区规则和功能"
    ),
    ReputationLevel.BASIC: ReputationPrivilege(
        level=ReputationLevel.BASIC,
        min_score=101,
        max_score=300,
        privileges=[
            "view_content",
            "basic_search",
            "create_posts",  # 发帖
            "create_comments",  # 评论
            "upvote_content",  # 点赞
        ],
        description="基础阶段 - 可以参与基础互动"
    ),
    ReputationLevel.REGULAR: ReputationPrivilege(
        level=ReputationLevel.REGULAR,
        min_score=301,
        max_score=500,
        privileges=[
            "view_content",
            "basic_search",
            "create_posts",
            "create_comments",
            "upvote_content",
            "downvote_content",  # 点踩
            "follow_users",  # 关注用户
            "bookmark_content",  # 收藏内容
        ],
        description="普通成员 - 完整的互动权限"
    ),
    ReputationLevel.ACTIVE: ReputationPrivilege(
        level=ReputationLevel.ACTIVE,
        min_score=501,
        max_score=700,
        privileges=[
            "view_content",
            "basic_search",
            "create_posts",
            "create_comments",
            "upvote_content",
            "downvote_content",
            "follow_users",
            "bookmark_content",
            "report_content",  # 举报
            "edit_own_content",  # 编辑自己的内容
            "advanced_search",  # 高级搜索
        ],
        description="活跃成员 - 可参与社区治理"
    ),
    ReputationLevel.CONTRIBUTOR: ReputationPrivilege(
        level=ReputationLevel.CONTRIBUTOR,
        min_score=701,
        max_score=850,
        privileges=[
            "view_content",
            "basic_search",
            "create_posts",
            "create_comments",
            "upvote_content",
            "downvote_content",
            "follow_users",
            "bookmark_content",
            "report_content",
            "edit_own_content",
            "advanced_search",
            "edit_community_content",  # 编辑社区内容（如问题、话题）
            "mentor_newbies",  # 指导新人
            "access_analytics",  # 查看数据分析
        ],
        description="贡献者 - 可参与内容治理和指导新人"
    ),
    ReputationLevel.LEADER: ReputationPrivilege(
        level=ReputationLevel.LEADER,
        min_score=851,
        max_score=950,
        privileges=[
            "view_content",
            "basic_search",
            "create_posts",
            "create_comments",
            "upvote_content",
            "downvote_content",
            "follow_users",
            "bookmark_content",
            "report_content",
            "edit_own_content",
            "advanced_search",
            "edit_community_content",
            "mentor_newbies",
            "access_analytics",
            "moderate_reports",  # 处理举报
            "review_content",  # 审核内容
            "create_tags",  # 创建标签
        ],
        description="领导者 - 可参与社区管理和内容审核"
    ),
    ReputationLevel.LEGEND: ReputationPrivilege(
        level=ReputationLevel.LEGEND,
        min_score=951,
        max_score=1000,
        privileges=[
            "view_content",
            "basic_search",
            "create_posts",
            "create_comments",
            "upvote_content",
            "downvote_content",
            "follow_users",
            "bookmark_content",
            "report_content",
            "edit_own_content",
            "advanced_search",
            "edit_community_content",
            "mentor_newbies",
            "access_analytics",
            "moderate_reports",
            "review_content",
            "create_tags",
            "governance_vote",  # 参与治理投票
            "propose_rules",  # 提议社区规则
            "api_access",  # API 访问权限
            "priority_support",  # 优先支持
        ],
        description="传奇用户 - 社区领袖，拥有最高权限和影响力"
    ),
}


# ==================== 行为分数配置 ====================

BEHAVIOR_SCORE_CONFIG: Dict[BehaviorType, Dict[str, Any]] = {
    # 正面行为
    BehaviorType.POST_CREATE: {"score_delta": 1, "dimension": ReputationDimension.CONTENT_QUALITY, "is_positive": True},
    BehaviorType.POST_UPVOTED: {"score_delta": 2, "dimension": ReputationDimension.CONTENT_QUALITY, "is_positive": True},
    BehaviorType.COMMENT_CREATE: {"score_delta": 1, "dimension": ReputationDimension.CONTENT_QUALITY, "is_positive": True},
    BehaviorType.COMMENT_UPVOTED: {"score_delta": 1, "dimension": ReputationDimension.CONTENT_QUALITY, "is_positive": True},
    BehaviorType.HELP_OTHERS: {"score_delta": 5, "dimension": ReputationDimension.COLLABORATION, "is_positive": True},
    BehaviorType.REPORT_VIOLATION: {"score_delta": 3, "dimension": ReputationDimension.COMMUNITY_CONTRIBUTION, "is_positive": True},
    BehaviorType.DAILY_CHECKIN: {"score_delta": 1, "dimension": ReputationDimension.COMMUNITY_CONTRIBUTION, "is_positive": True},
    BehaviorType.CONTENT_EDITED: {"score_delta": 2, "dimension": ReputationDimension.CONTENT_QUALITY, "is_positive": True},

    # 负面行为
    BehaviorType.POST_DOWNVOTED: {"score_delta": -1, "dimension": ReputationDimension.CONTENT_QUALITY, "is_positive": False},
    BehaviorType.COMMENT_DOWNVOTED: {"score_delta": -1, "dimension": ReputationDimension.CONTENT_QUALITY, "is_positive": False},
    BehaviorType.VIOLATION_DETECTED: {"score_delta": -10, "dimension": ReputationDimension.TRUSTWORTHINESS, "is_positive": False},
    BehaviorType.CONTENT_DELETED: {"score_delta": -5, "dimension": ReputationDimension.CONTENT_QUALITY, "is_positive": False},
    BehaviorType.SPAM_DETECTED: {"score_delta": -20, "dimension": ReputationDimension.TRUSTWORTHINESS, "is_positive": False},
}
