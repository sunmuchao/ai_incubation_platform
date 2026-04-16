"""
服务模块导出 - P3

注：以下服务已废弃并归档，不再导出：
- dynamic_profile_service → DeerFlow her_tools 动态画像
- quick_start_service → /api/profile/quickstart 直接操作数据库
- vector_adjustment_service → 被 quick_start_service 引用（孤岛链）
"""
from services.behavior_tracking_service import behavior_service, BehaviorTrackingService
from services.conversation_analysis_service import conversation_analyzer, ConversationAnalysisService
from services.relationship_progress_service import relationship_progress_service, RelationshipProgressService
from services.activity_recommendation_service import activity_recommendation_service, ActivityRecommendationService, MapAPIService, GeoService
from services.behavior_log_service import BehaviorLogService, get_behavior_log_service
from services.report_service import ReportService, get_report_service, ReportStatus, ReportType
from services.grayscale_config_service import (
    GrayscaleConfigService,
    get_grayscale_config_service,
    FeatureFlag,
    ExperimentVariant,
    ExperimentResult,
    init_default_feature_flags,
    init_default_ab_experiments,
)

__all__ = [
    "behavior_service",
    "BehaviorTrackingService",
    "conversation_analyzer",
    "ConversationAnalysisService",
    "relationship_progress_service",
    "RelationshipProgressService",
    "activity_recommendation_service",
    "ActivityRecommendationService",
    "MapAPIService",
    "GeoService",
    # 新增服务
    "BehaviorLogService",
    "get_behavior_log_service",
    "ReportService",
    "get_report_service",
    "ReportStatus",
    "ReportType",
    # 灰度配置服务
    "GrayscaleConfigService",
    "get_grayscale_config_service",
    "FeatureFlag",
    "ExperimentVariant",
    "ExperimentResult",
    "init_default_feature_flags",
    "init_default_ab_experiments",
]