"""
SQLAlchemy 数据模型定义 - 过渡层

重构说明：
- 此文件现在是过渡层，所有模型已迁移至 db/models/ 目录
- 按领域拆分为 12 个文件，每个 50-200 行
- 保持向后兼容：from db.models import UserDB 仍然有效

迁移后的文件结构：
    db/models/
    ├── __init__.py      → 统一导出
    ├── base.py          → 基础导入
    ├── user.py          → UserDB（核心）
    ├── matching.py      → 匹配领域
    ├── conversation.py  → 对话历史
    ├── chat.py          → 实时聊天
    ├── photo.py         → 照片管理
    ├── verification.py  → 认证验证
    ├── membership.py    → 会员订阅
    ├── video.py         → 视频约会
    ├── ai.py            → AI集成
    ├── precomm.py       → AI预沟通
    ├── safety.py        → 安全领域
    ├── profile.py       → 用户画像
    ├── grayscale.py     → 灰度发布
    └ relationship.py    → 关系进展

版本历史：
- v1.0.0: 单文件 1592 行
- v2.0.0: 拆分为 12 个领域文件

注意事项：
- 此文件仅作为过渡层，未来可能移除
- 推荐直接导入：from db.models.user import UserDB
- 现有代码无需修改导入路径
"""

# 从拆分后的模块导入所有模型
# 保持完全向后兼容
from db.models import *  # noqa: F401, F403

# 导出所有模型（从 db/models/__init__.py 继承）
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