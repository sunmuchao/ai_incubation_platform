"""
统一模型注册中心

所有模型按领域分类注册，避免重复定义和循环导入问题。
测试环境只需导入此模块即可获得所有模型定义。

## 领域映射表（语义化命名）

| 功能领域 | 文件 |
|----------|------|
| 身份认证 | identity_models.py |
| 冲突处理 | conflict_models.py |
| 感知层 | perception_models.py |
| 价值观演化 | values_models.py |
| 数字孪生 | digital_twin_models.py |
| 企业管理/验证 | verification_models.py |
| 通知分享 | notification_models.py |
| 关系里程碑 | milestone_models.py |
| 情感分析 | emotion_analysis_models.py |
| 行为实验室 | behavior_lab_models.py |
| 关系增强 | relationship_enhancement_models.py |
| 约会模拟 | date_simulation_models.py |
| 自主约会 | autonomous_dating_models.py |
| 社交部落 | social_tribe_models.py |
| 压力测试 | stress_test_models.py |
| 情感气象 | emotion_weather_models.py |
| 高级功能 | advanced_feature_models.py |
| 未来功能 | future_models.py |
| AI持续学习 | l4_learning_models.py |

详细文档见: models/README.md
"""
from db.database import Base

# 导出 Base 供外部使用
__all__ = ['Base']

# ============================================
# 核心领域模型 (已导入到 db.models)
# ============================================
# 基础用户模型、匹配历史、对话历史、行为事件等
# 这些模型在 db.models 中定义，无需重复导入

# ============================================
# 会员与支付领域
# ============================================
from models.membership import (
    MembershipTier,
    MembershipFeature,
    UserMembership,
    MembershipOrder,
    MembershipCreate,
    MembershipBenefit,
    MEMBERSHIP_FEATURES,
    MEMBERSHIP_LIMITS,
    MEMBERSHIP_PRICES,
    MEMBERSHIP_BENEFITS,
    UserUsageTrackerDB,  # 使用次数追踪器
)
from db.payment_models import (
    CouponDB,
    UserCouponDB,
    RefundDB,
    InvoiceDB,
    FreeTrialDB,
    SubscriptionDB,
)

__all__.extend([
    'MembershipTier', 'MembershipFeature', 'UserMembership', 'MembershipOrder',
    'MembershipCreate', 'MembershipBenefit', 'MEMBERSHIP_FEATURES',
    'MEMBERSHIP_LIMITS', 'MEMBERSHIP_PRICES', 'MEMBERSHIP_BENEFITS',
    'UserUsageTrackerDB',  # 使用次数追踪器
    'CouponDB', 'UserCouponDB', 'RefundDB', 'InvoiceDB',
    'FreeTrialDB', 'SubscriptionDB',
])

# ============================================
# Enterprise: 企业管理领域
# ============================================
from models.verification_models import (
    DepartmentDB,
    OperatorRoleDB,
    UserOperatorDB,
    OperatorActionLogDB,
    ExportTaskDB,
    DashboardMetricsDB,
    DashboardReportDB,
)
from db.audit import AuditLogDB

__all__.extend([
    'DepartmentDB', 'OperatorRoleDB', 'UserOperatorDB', 'OperatorActionLogDB',
    'ExportTaskDB', 'DashboardMetricsDB', 'DashboardReportDB', 'AuditLogDB',
])

# ============================================
# Notification: 通知与分享领域
# ============================================
from models.notification_models import (
    UserNotificationDB,
    UserPushTokenDB,
    NotificationTemplateDB,
    InviteCodeDB,
    ShareRecordDB,
)

__all__.extend([
    'UserNotificationDB', 'UserPushTokenDB', 'NotificationTemplateDB',
    'InviteCodeDB', 'ShareRecordDB',
])

# ============================================
# Milestone: 深度认知领域
# ============================================
from models.milestone_models import (
    RelationshipMilestoneDB,
    RelationshipStageHistoryDB,
    RelationshipInsightDB,
    DateSuggestionDB,
    DateVenueDB,
    CoupleGameDB,
    CoupleGameRoundDB,
    GameResultInsightDB,
)

__all__.extend([
    'RelationshipMilestoneDB', 'RelationshipStageHistoryDB', 'RelationshipInsightDB',
    'DateSuggestionDB', 'DateVenueDB', 'CoupleGameDB', 'CoupleGameRoundDB',
    'GameResultInsightDB',
])

# ============================================
# Emotion: 感官洞察领域 (情感分析/安全守护)
# ============================================
from models.emotion_analysis_models import (
    EmotionAnalysisDB,
    EmotionReportDB,
    EmotionalTrendDB,
    SafetyCheckDB,
    SafetyAlertDB,
    SafetyPlanDB,
    DateSafetySessionDB,
    SensoryInsightDB,
    MicroExpressionPatternDB,
    VoicePatternDB,
)

__all__.extend([
    'EmotionAnalysisDB', 'EmotionReportDB', 'EmotionalTrendDB',
    'SafetyCheckDB', 'SafetyAlertDB', 'SafetyPlanDB', 'DateSafetySessionDB',
    'SensoryInsightDB', 'MicroExpressionPatternDB', 'VoicePatternDB',
])

# ============================================
# Behavior: 行为实验室领域
# ============================================
from models.behavior_lab_models import (
    SharedExperienceDB,
    SilenceEventDB,
    IcebreakerTopicDB,
    GeneratedIcebreakerDB,
    EmotionWarningDB,
    LoveLanguageTranslationDB,
    RelationshipWeatherReportDB,
    CalmingKitDB,
)

__all__.extend([
    'SharedExperienceDB', 'SilenceEventDB', 'IcebreakerTopicDB',
    'GeneratedIcebreakerDB', 'EmotionWarningDB', 'LoveLanguageTranslationDB',
    'RelationshipWeatherReportDB', 'CalmingKitDB',
])

# ============================================
# LoveLanguage: 情感调解领域
# ============================================
from models.relationship_enhancement_models import (
    UserLoveLanguageProfileDB,
    RelationshipTrendPredictionDB,
    WarningResponseStrategyDB,
    WarningResponseRecordDB,
    EmotionMediationStatsDB,
)

__all__.extend([
    'UserLoveLanguageProfileDB', 'RelationshipTrendPredictionDB',
    'WarningResponseStrategyDB', 'WarningResponseRecordDB',
    'EmotionMediationStatsDB',
])

# ============================================
# DateSimulation: 实战演习领域
# ============================================
from models.date_simulation_models import (
    AIDateAvatarDB,
    DateSimulationDB,
    SimulationFeedbackDB,
    DateOutfitRecommendationDB,
    DateVenueStrategyDB,
    DateTopicKitDB,
    AgentCollaborationRecordDB,
    MatchmakerAgentSessionDB,
    CoachAgentSessionDB,
    GuardianAgentSessionDB,
)

__all__.extend([
    'AIDateAvatarDB', 'DateSimulationDB', 'SimulationFeedbackDB',
    'DateOutfitRecommendationDB', 'DateVenueStrategyDB', 'DateTopicKitDB',
    'AgentCollaborationRecordDB', 'MatchmakerAgentSessionDB',
    'CoachAgentSessionDB', 'GuardianAgentSessionDB',
])

# ============================================
# AutonomousDating: 虚实结合领域
# ============================================
from models.autonomous_dating_models import (
    AutonomousDatePlanDB,
    DateReservationDB,
    RelationshipAlbumDB,
    SweetMomentDB,
    CoupleFootprintDB,
    GeneratedMediaDB,
)

__all__.extend([
    'AutonomousDatePlanDB', 'DateReservationDB', 'RelationshipAlbumDB',
    'SweetMomentDB', 'CoupleFootprintDB', 'GeneratedMediaDB',
])

# ============================================
# SocialTribe: 圈子融合领域
# ============================================
from models.social_tribe_models import (
    LifestyleTribeDB,
    UserTribeMembershipDB,
    TribeCompatibilityDB,
    CoupleDigitalHomeDB,
    CoupleGoalDB,
    CoupleCheckinDB,
    VirtualRoleDB,
    FamilyMeetingSimulationDB,
)

__all__.extend([
    'LifestyleTribeDB', 'UserTribeMembershipDB', 'TribeCompatibilityDB',
    'CoupleDigitalHomeDB', 'CoupleGoalDB', 'CoupleCheckinDB',
    'VirtualRoleDB', 'FamilyMeetingSimulationDB',
])

# ============================================
# StressTest: 终极共振领域
# ============================================
from models.stress_test_models import (
    StressTestScenarioDB,
    CoupleStressTestDB,
    GrowthPlanDB,
    GrowthResourceDB,
    GrowthResourceRecommendationDB,
    TrustScoreDB,
    TrustEndorsementDB,
    TrustEndorsementSummaryDB,
)

__all__.extend([
    'StressTestScenarioDB', 'CoupleStressTestDB', 'GrowthPlanDB',
    'GrowthResourceDB', 'GrowthResourceRecommendationDB', 'TrustScoreDB',
    'TrustEndorsementDB', 'TrustEndorsementSummaryDB',
])

# ============================================
# EmotionWeather: AI 预沟通领域
# ============================================
from models.emotion_weather_models import (
    RelationshipStateDB,
    DatingAdviceDB,
    LoveGuidanceDB,
    ChatSuggestionDB,
    GiftRecommendationDB,
    RelationshipHealthDB,
)

__all__.extend([
    'RelationshipStateDB', 'DatingAdviceDB', 'LoveGuidanceDB',
    'ChatSuggestionDB', 'GiftRecommendationDB', 'RelationshipHealthDB',
])

# ============================================
# Values: 冲突处理领域
# ============================================
from models.conflict_models import (
    ConflictStyleDB,
    ConflictHistoryDB,
    ConflictCompatibilityDB,
    ConflictResolutionTipDB,
    CommunicationPatternDB,
)

__all__.extend([
    'ConflictStyleDB', 'ConflictHistoryDB', 'ConflictCompatibilityDB',
    'ConflictResolutionTipDB', 'CommunicationPatternDB',
])

# ============================================
# Values: 价值观演化领域
# ============================================
from models.values_models import (
    DeclaredValuesDB,
    InferredValuesDB,
    ValuesDriftDB,
    ValuesEvolutionHistoryDB,
    MatchingWeightAdjustmentDB,
    VALUES_DIMENSIONS,
    VALUES_OPTIONS,
)

__all__.extend([
    'DeclaredValuesDB', 'InferredValuesDB', 'ValuesDriftDB',
    'ValuesEvolutionHistoryDB', 'MatchingWeightAdjustmentDB',
    'VALUES_DIMENSIONS', 'VALUES_OPTIONS',
])

# ============================================
# Values: 感知层领域 (向量数据库)
# ============================================
from models.perception_models import (
    UserVectorDB,
    VectorUpdateHistoryDB,
    VectorSimilarityCacheDB,
    DigitalSubconsciousProfileDB,
    BehaviorVectorMappingDB,
    VECTOR_DIMENSIONS as PERCEPTION_VECTOR_DIMENSIONS,
    SUBCONSCIOUS_TRAITS_LIBRARY,
    ATTACHMENT_STYLE_DESCRIPTIONS,
)

__all__.extend([
    'UserVectorDB', 'VectorUpdateHistoryDB', 'VectorSimilarityCacheDB',
    'DigitalSubconsciousProfileDB', 'BehaviorVectorMappingDB',
    'PERCEPTION_VECTOR_DIMENSIONS', 'SUBCONSCIOUS_TRAITS_LIBRARY',
    'ATTACHMENT_STYLE_DESCRIPTIONS',
])

# ============================================
# Advanced: 下一代迭代领域
# ============================================
from models.advanced_feature_models import (
    AIChatSession,
    AIChatSessionResult,
    ConsumptionProfile,
    GeoTrajectory,
    AuthenticMatchResult,
    BehaviorCredit,
    DateFeedback,
    RiskFlag,
    RelationshipHealth,
    GiftManager,
    DynamicProfile,
    PreferenceDial,
    PrivacySetting,
    AIAuditLog,
    OfflineConversionFunnel,
    CoupleMode,
)
# Future 专用：聊天情感趋势（区别于 Emotion 的 EmotionalTrendDB）
from models.future_models import (
    ChatAssistantSuggestionDB,
    DatePlanDB,
    DateVenueDB as DateVenueP20DB,  # 重命名避免与 milestone_models.DateVenueDB 冲突
    RelationshipConsultationDB,
    RelationshipFAQDB,
    ChatEmotionTrendDB,
    LoveDiaryEntryDB,
    LoveDiaryMemoryDB,
    RelationshipTimelineDB,
    BehaviorCreditDB,
    BehaviorCreditEventDB,
)
# Identity: 多源身份核验模型
from models.identity_models import (
    TrustBadgeDB,
    TrustBadgeHistoryDB,
    ExternalVerificationAPIConfigDB,
    EducationCredentialDB,
    OccupationCredentialDB,
    IncomeCredentialDB,
    PropertyCredentialDB,
)

# DigitalTwin: 数字分身预聊模型
from models.digital_twin_models import (
    DigitalTwinProfile,
    DigitalTwinSimulation,
    DigitalTwinReport,
)

# L4: AI 持续学习模型
from models.l4_learning_models import (
    UserPreferenceMemory,
    BehaviorLearningPattern,
    MatchingWeightAdjustment,
    UserLearningProfile,
)

# AI 反馈模型
from models.ai_feedback_models import (
    AIFeedbackDB,
    AIFeedbackOutcomeDB,
)

__all__.extend([
    'AIChatSession', 'AIChatSessionResult', 'ConsumptionProfile',
    'GeoTrajectory', 'AuthenticMatchResult', 'BehaviorCredit',
    'DateFeedback', 'RiskFlag', 'RelationshipHealth', 'GiftManager',
    'DynamicProfile', 'PreferenceDial', 'PrivacySetting', 'AIAuditLog',
    'OfflineConversionFunnel', 'CoupleMode',
    # Future 专用模型
    'ChatAssistantSuggestionDB', 'DatePlanDB', 'DateVenueP20DB',
    'RelationshipConsultationDB', 'RelationshipFAQDB', 'ChatEmotionTrendDB',
    'LoveDiaryEntryDB', 'LoveDiaryMemoryDB', 'RelationshipTimelineDB',
    'BehaviorCreditDB', 'BehaviorCreditEventDB',
    # Identity: 多源身份核验模型
    'TrustBadgeDB', 'TrustBadgeHistoryDB',
    'ExternalVerificationAPIConfigDB',
    'EducationCredentialDB', 'OccupationCredentialDB',
    'IncomeCredentialDB', 'PropertyCredentialDB',
    # DigitalTwin: 数字分身预聊模型
    'DigitalTwinProfile', 'DigitalTwinSimulation', 'DigitalTwinReport',
    # L4: AI 持续学习模型
    'UserPreferenceMemory', 'BehaviorLearningPattern', 'MatchingWeightAdjustment', 'UserLearningProfile',
    # AI 反馈模型
    'AIFeedbackDB', 'AIFeedbackOutcomeDB',
])

# ============================================
# Advanced 别名映射（兼容旧代码引用）
# 注意：以下别名仅保留被实际引用的，已删除未使用的别名
# ============================================
PreCommunicationSessionDB = AIChatSession
ConsumptionProfileDB = ConsumptionProfile
# 注意：BehaviorCreditDB 在 future_models.py 中有真实定义，此处不再创建别名以避免覆盖

# 添加到 __all__
__all__.extend([
    'PreCommunicationSessionDB', 'ConsumptionProfileDB',
])

# ============================================
# 审计日志模型 (单独在 db.audit 中)
# ============================================
# 注意：AuditLogDB 已在 verification_models 中定义，无需重复导入


def register_all_models():
    """
    注册所有模型到 SQLAlchemy

    调用此函数确保所有模型表都被创建。
    通常在应用启动时调用一次。
    """
    # 导入所有模块以确保模型注册
    # 由于我们已经在上面导入了所有类，模型已经注册到 Base.metadata
    pass


def get_all_model_classes():
    """
    获取所有模型类的列表

    返回:
        list: 所有模型类的列表
    """
    return __all__


def get_model_by_name(name: str):
    """
    根据名称获取模型类

    Args:
        name: 模型类名称

    Returns:
        模型类，如果不存在则返回 None
    """
    if name in globals():
        return globals()[name]
    return None
