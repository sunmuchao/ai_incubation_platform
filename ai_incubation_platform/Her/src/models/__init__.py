"""
统一模型注册中心

所有模型按领域分类注册，避免重复定义和循环导入问题。
测试环境只需导入此模块即可获得所有模型定义。

## 领域映射表（P系列 → 功能领域）

| P系列 | 领域 | 文件 |
|-------|------|------|
| P0 | 身份认证 | p0_identity_models.py |
| P1 | 冲突/感知/价值观 | p1_conflict_models.py, p1_perception_models.py, p1_values_models.py |
| P2 | 数字孪生 | p2_digital_twin_models.py |
| P8 | 企业管理 | p8_models.py |
| P9 | 通知分享 | p9_models.py |
| P10 | 关系里程碑/约会建议 | p10_models.py |
| P11 | 情感分析/安全守护 | p11_models.py |
| P12 | 行为实验室 | p12_models.py |
| P13 | 爱之语/预警响应 | p13_models.py |
| P14 | 约会模拟沙盒 | p14_models.py |
| P15 | 自主约会策划 | p15_models.py |
| P16 | 部落匹配/数字小家 | p16_models.py |
| P17 | 压力测试/成长计划 | p17_models.py |
| P18 | 关系状态管理 | p18_models.py |
| P18-P22 | AI预沟通/消费画像 | p18_p22_models.py |
| P20 | 智能聊天助手 | p20_models.py |
| L4 | AI持续学习 | l4_learning_models.py |

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
# P8: 企业管理领域
# ============================================
from models.p8_models import (
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
# P9: 通知与分享领域
# ============================================
from models.p9_models import (
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
# P10: 深度认知领域
# ============================================
from models.p10_models import (
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
# P11: 感官洞察领域 (情感分析/安全守护)
# ============================================
from models.p11_models import (
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
# P12: 行为实验室领域
# ============================================
from models.p12_models import (
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
# P13: 情感调解领域
# ============================================
from models.p13_models import (
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
# P14: 实战演习领域
# ============================================
from models.p14_models import (
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
# P15: 虚实结合领域
# ============================================
from models.p15_models import (
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
# P16: 圈子融合领域
# ============================================
from models.p16_models import (
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
# P17: 终极共振领域
# ============================================
from models.p17_models import (
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
# P18: AI 预沟通领域
# ============================================
from models.p18_models import (
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
# P1: 冲突处理领域
# ============================================
from models.p1_conflict_models import (
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
# P1: 价值观演化领域
# ============================================
from models.p1_values_models import (
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
# P1: 感知层领域 (向量数据库)
# ============================================
from models.p1_perception_models import (
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
# P18-P22: 下一代迭代领域
# ============================================
from models.p18_p22_models import (
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
# P20 专用：聊天情感趋势（区别于 P11 的 EmotionalTrendDB）
from models.p20_models import (
    ChatAssistantSuggestionDB,
    DatePlanDB,
    DateVenueDB as DateVenueP20DB,  # 重命名避免与 p10_models.DateVenueDB 冲突
    RelationshipConsultationDB,
    RelationshipFAQDB,
    ChatEmotionTrendDB,
    LoveDiaryEntryDB,
    LoveDiaryMemoryDB,
    RelationshipTimelineDB,
    BehaviorCreditDB,
    BehaviorCreditEventDB,
)
# P0: 多源身份核验模型
from models.p0_identity_models import (
    TrustBadgeDB,
    TrustBadgeHistoryDB,
    ExternalVerificationAPIConfigDB,
    EducationCredentialDB,
    OccupationCredentialDB,
    IncomeCredentialDB,
    PropertyCredentialDB,
)

# P2: 数字分身预聊模型
from models.p2_digital_twin_models import (
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

__all__.extend([
    'AIChatSession', 'AIChatSessionResult', 'ConsumptionProfile',
    'GeoTrajectory', 'AuthenticMatchResult', 'BehaviorCredit',
    'DateFeedback', 'RiskFlag', 'RelationshipHealth', 'GiftManager',
    'DynamicProfile', 'PreferenceDial', 'PrivacySetting', 'AIAuditLog',
    'OfflineConversionFunnel', 'CoupleMode',
    # P20 专用模型
    'ChatAssistantSuggestionDB', 'DatePlanDB', 'DateVenueP20DB',
    'RelationshipConsultationDB', 'RelationshipFAQDB', 'ChatEmotionTrendDB',
    'LoveDiaryEntryDB', 'LoveDiaryMemoryDB', 'RelationshipTimelineDB',
    'BehaviorCreditDB', 'BehaviorCreditEventDB',
    # P0: 多源身份核验模型
    'TrustBadgeDB', 'TrustBadgeHistoryDB',
    'ExternalVerificationAPIConfigDB',
    'EducationCredentialDB', 'OccupationCredentialDB',
    'IncomeCredentialDB', 'PropertyCredentialDB',
    # P2: 数字分身预聊模型
    'DigitalTwinProfile', 'DigitalTwinSimulation', 'DigitalTwinReport',
    # L4: AI 持续学习模型
    'UserPreferenceMemory', 'BehaviorLearningPattern', 'MatchingWeightAdjustment', 'UserLearningProfile',
])

# ============================================
# P18-P22 别名映射（兼容旧代码引用）
# 注意：以下别名仅保留被实际引用的，已删除未使用的别名
# ============================================
PreCommunicationSessionDB = AIChatSession
ConsumptionProfileDB = ConsumptionProfile
# 注意：BehaviorCreditDB 在 p20_models.py 中有真实定义，此处不再创建别名以避免覆盖

# 添加到 __all__
__all__.extend([
    'PreCommunicationSessionDB', 'ConsumptionProfileDB',
])

# ============================================
# 审计日志模型 (单独在 db.audit 中)
# ============================================
# 注意：AuditLogDB 已在 p8_models 中定义，无需重复导入


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
