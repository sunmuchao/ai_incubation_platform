"""
Behavior 行为实验室服务层 - 情感调解模块

包含：
1. 吵架预警服务（灭火器）
2. 爱之语翻译服务
3. 关系气象报告服务

注意：本文件现在作为兼容层，实际实现已拆分为独立服务文件：
- warning_response_service.py: EmotionWarningService
- love_language_translation_service.py: LoveLanguageTranslationService
- weather_service.py: RelationshipWeatherService
"""
from services.warning_response_service import EmotionWarningService, emotion_warning_service
from services.love_language_translation_service import LoveLanguageTranslationService, love_language_service
from services.weather_service import RelationshipWeatherService, relationship_weather_service

# 兼容层：创建一个统一的服务对象，方便旧代码迁移
class EmotionMediationService:
    """情感调解服务（兼容层，实际调用拆分后的服务）"""

    def __init__(self):
        self.warning_service = emotion_warning_service
        self.love_language_service = love_language_service
        self.weather_service = relationship_weather_service

    # 委托方法，保持向后兼容 - EmotionWarningService
    def analyze_conversation_emotion(self, conversation_id, user_a_id, user_b_id, window_messages=20, db=None):
        return self.warning_service.analyze_conversation_emotion(
            conversation_id, user_a_id, user_b_id, window_messages, db
        )

    def create_warning(self, conversation_id, user_a_id, user_b_id, warning_level, trigger_reason, detected_emotions=None, calming_suggestions=None, db=None):
        return self.warning_service.create_warning(
            conversation_id, user_a_id, user_b_id, warning_level, trigger_reason, detected_emotions, calming_suggestions, db
        )

    def get_conversation_warnings(self, conversation_id, db=None):
        return self.warning_service.get_conversation_warnings(conversation_id, db)

    def acknowledge_warning(self, warning_id, db=None):
        return self.warning_service.acknowledge_warning(warning_id, db)

    def resolve_warning(self, warning_id, relationship_improvement=None, db=None):
        return self.warning_service.resolve_warning(warning_id, relationship_improvement, db)

    def get_user_warnings(self, user_id, days=7, only_unresolved=False, db=None):
        return self.warning_service.get_user_warnings(user_id, days, only_unresolved, db)

    # 委托方法 - LoveLanguageTranslationService
    def translate_expression(self, user_id, target_user_id, expression, db=None):
        return self.love_language_service.translate_expression(user_id, target_user_id, expression, db)

    def submit_feedback(self, translation_id, feedback, db=None):
        return self.love_language_service.submit_feedback(translation_id, feedback, db)

    def get_user_translations(self, user_id, limit=20, db=None):
        return self.love_language_service.get_user_translations(user_id, limit, db)

    # 委托方法 - RelationshipWeatherService
    def generate_weather_report(self, user_a_id, user_b_id, report_period="weekly", db=None):
        return self.weather_service.generate_weather_report(user_a_id, user_b_id, report_period, db)

    def get_user_reports(self, user_id, report_period=None, limit=10, db=None):
        return self.weather_service.get_user_reports(user_id, report_period, limit, db)


# 全局服务实例
emotion_mediation_service = EmotionMediationService()

__all__ = [
    "EmotionWarningService",
    "LoveLanguageTranslationService",
    "RelationshipWeatherService",
    "EmotionMediationService",
    "emotion_warning_service",
    "love_language_service",
    "relationship_weather_service",
    "emotion_mediation_service",
]
