"""
SQLAlchemy 数据模型 - 统一导出

所有模型按领域分类导出，保持与原 models.py 完全兼容。

重构说明：
- 原 models.py（1592 行）拆分为 12 个领域文件
- 每个文件 50-200 行，职责清晰
- 导入路径不变：from db.models import UserDB

文件映射：
- user.py          → 用户核心表
- matching.py      → 匹配相关表
- conversation.py  → 对话历史表
- chat.py          → 实时聊天表
- photo.py         → 照片管理表
- verification.py  → 认证验证表
- membership.py    → 会员订阅表
- video.py         → 视频约会表
- ai.py            → AI集成表
- precomm.py       → AI预沟通表
- safety.py        → 安全领域表
- profile.py       → 用户画像表
- grayscale.py     → 灰度发布表
- relationship.py  → 关系进展表
"""

# ============= 基础导入 =============
from db.database import Base
from db.models.base import Column, String, Integer, Float, DateTime, Boolean, Text, ForeignKey, Table, JSON, func, relationship

# ============= 用户核心 =============
from db.models.user import UserDB

# ============= 匹配领域 =============
from db.models.matching import (
    MatchHistoryDB,
    SwipeActionDB,
    UserPreferenceDB,
    UserRelationshipPreferenceDB,
    MatchInteractionDB,
    QuickStartRecordDB,
    UserFeedbackLearningDB,
    ImplicitInferenceDB,
)

# ============= 对话领域 =============
from db.models.conversation import (
    ConversationDB,
    BehaviorEventDB,
    UserProfileUpdateDB,
    ConversationSessionDB,
)

# ============= 实时聊天 =============
from db.models.chat import ChatMessageDB, ChatConversationDB

# ============= 照片管理 =============
from db.models.photo import PhotoDB

# ============= 认证验证 =============
from db.models.verification import (
    IdentityVerificationDB,
    VerificationBadgeDB,
    EducationVerificationDB,
    CareerVerificationDB,
)

# ============= 会员订阅 =============
from db.models.membership import (
    UserMembershipDB,
    MembershipOrderDB,
    MemberFeatureUsageDB,
)

# ============= 视频约会 =============
from db.models.video import (
    VideoCallDB,
    VideoDateDB,
    VideoDateReportDB,
    IcebreakerQuestionDB,
    GameSessionDB,
    VirtualBackgroundDB,
)

# ============= AI集成 =============
from db.models.ai import (
    AICompanionSessionDB,
    AICompanionMessageDB,
    SemanticAnalysisDB,
    LLMMetricsDB,
    UserBehaviorFeatureDB,
)

# ============= AI预沟通 =============
from db.models.precomm import AIPreCommunicationSessionDB, AIPreCommunicationMessageDB

# ============= 安全领域 =============
from db.models.safety import (
    SafetyZoneDB,
    TrustedContactDB,
    UserBlockDB,
    UserReportDB,
)

# ============= 用户画像 =============
from db.models.profile import (
    UserVectorProfileDB,
    ProfileInferenceRecordDB,
    ThirdPartyAuthRecordDB,
    GameTestRecordDB,
    UserSocialMetricsDB,
)

# ============= 灰度发布 =============
from db.models.grayscale import (
    FeatureFlagDB,
    ABExperimentDB,
    UserExperimentAssignmentDB,
)

# ============= 关系进展 =============
from db.models.relationship import RelationshipProgressDB, SavedLocationDB

# ============= 导入外部定义的模型 =============
from models.membership import UserUsageTrackerDB  # noqa: F401

# ============= 统一导出 =============
__all__ = [
    # 基础
    "Base",
    # 用户核心
    "UserDB",
    # 匹配领域
    "MatchHistoryDB",
    "SwipeActionDB",
    "UserPreferenceDB",
    "UserRelationshipPreferenceDB",
    "MatchInteractionDB",
    "QuickStartRecordDB",
    "UserFeedbackLearningDB",
    "ImplicitInferenceDB",
    # 对话领域
    "ConversationDB",
    "BehaviorEventDB",
    "UserProfileUpdateDB",
    "ConversationSessionDB",
    # 实时聊天
    "ChatMessageDB",
    "ChatConversationDB",
    # 照片管理
    "PhotoDB",
    # 认证验证
    "IdentityVerificationDB",
    "VerificationBadgeDB",
    "EducationVerificationDB",
    "CareerVerificationDB",
    # 会员订阅
    "UserMembershipDB",
    "MembershipOrderDB",
    "MemberFeatureUsageDB",
    # 视频约会
    "VideoCallDB",
    "VideoDateDB",
    "VideoDateReportDB",
    "IcebreakerQuestionDB",
    "GameSessionDB",
    "VirtualBackgroundDB",
    # AI集成
    "AICompanionSessionDB",
    "AICompanionMessageDB",
    "SemanticAnalysisDB",
    "LLMMetricsDB",
    "UserBehaviorFeatureDB",
    # AI预沟通
    "AIPreCommunicationSessionDB",
    "AIPreCommunicationMessageDB",
    # 安全领域
    "SafetyZoneDB",
    "TrustedContactDB",
    "UserBlockDB",
    "UserReportDB",
    # 用户画像
    "UserVectorProfileDB",
    "ProfileInferenceRecordDB",
    "ThirdPartyAuthRecordDB",
    "GameTestRecordDB",
    "UserSocialMetricsDB",
    # 灰度发布
    "FeatureFlagDB",
    "ABExperimentDB",
    "UserExperimentAssignmentDB",
    # 关系进展
    "RelationshipProgressDB",
    "SavedLocationDB",
    # 外部导入
    "UserUsageTrackerDB",
]


def get_all_models():
    """获取所有模型类列表"""
    return __all__


def get_model_count():
    """获取模型数量"""
    return len(__all__)