"""
P13 情感调解增强服务单元测试
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import json

from services.relationship_enhancement_service import (
    LoveLanguageProfileService,
    RelationshipTrendService,
    WarningResponseService,
)
from models.relationship_enhancement_models import LoveLanguageType


class TestLoveLanguageProfileService:
    """爱之语画像服务测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return LoveLanguageProfileService()

    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        return MagicMock()

    def test_analyze_user_love_language_with_data(self, service, mock_db_session):
        """测试分析用户爱之语（有数据）"""
        # Arrange
        user_id = "user_001"

        # 创建模拟翻译记录
        mock_translation1 = MagicMock()
        mock_translation1.original_expression = "我喜欢你送的礼物，很用心"
        mock_translation1.true_intention = "感受到对方的心意"
        mock_translation1.suggested_response = "谢谢你的礼物"

        mock_translation2 = MagicMock()
        mock_translation2.original_expression = "谢谢你陪我聊天"
        mock_translation2.true_intention = "享受陪伴的时光"
        mock_translation2.suggested_response = "我也很开心"

        mock_db_session.query.return_value.filter.return_value.all.return_value = [
            mock_translation1, mock_translation2
        ]

        # Mock profile creation
        mock_profile = MagicMock()
        mock_profile.id = "llp_001"
        mock_profile.user_id = user_id
        mock_profile.primary_love_language = None
        mock_profile.words_score = 0
        mock_profile.time_score = 0
        mock_profile.gifts_score = 0
        mock_profile.acts_score = 0
        mock_profile.touch_score = 0

        # 第一次查询返回 None（创建新 profile）
        # 第二次查询返回创建的 profile
        mock_db_session.query.return_value.filter.return_value.first.side_effect = [None, mock_profile, mock_profile]
        mock_db_session.commit.return_value = None
        mock_db_session.refresh.return_value = None

        # Act
        profile = service.analyze_user_love_language(user_id, mock_db_session)

        # Assert
        assert profile is not None
        mock_db_session.add.assert_called()
        mock_db_session.commit.assert_called()

    def test_analyze_user_love_language_no_data(self, service, mock_db_session):
        """测试分析用户爱之语（无数据）"""
        # Arrange
        user_id = "user_001"

        mock_db_session.query.return_value.filter.return_value.all.return_value = []

        mock_profile = MagicMock()
        mock_profile.id = "llp_001"
        mock_profile.user_id = user_id
        mock_profile.primary_love_language = None

        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_profile

        # Act
        profile = service.analyze_user_love_language(user_id, mock_db_session)

        # Assert
        assert profile is not None

    def test_get_user_profile(self, service, mock_db_session):
        """测试获取用户爱之语画像"""
        # Arrange
        user_id = "user_001"

        mock_profile = MagicMock()
        mock_profile.id = "llp_001"
        mock_profile.user_id = user_id
        mock_profile.primary_love_language = LoveLanguageType.WORDS.value
        mock_profile.secondary_love_language = LoveLanguageType.TIME.value
        mock_profile.words_score = 5
        mock_profile.time_score = 3
        mock_profile.gifts_score = 2
        mock_profile.acts_score = 1
        mock_profile.touch_score = 4
        mock_profile.expression_preferences = ["赞美", "鼓励"]
        mock_profile.reception_preferences = ["陪伴", "礼物"]
        mock_profile.confidence_score = 0.8
        mock_profile.assessment_count = 10
        mock_profile.last_updated = datetime(2024, 1, 15)

        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_profile

        # Act
        profile = service.get_user_profile(user_id, mock_db_session)

        # Assert
        assert profile is not None
        assert profile["user_id"] == user_id
        assert profile["primary_love_language"] == LoveLanguageType.WORDS.value
        assert profile["scores"]["words"] == 5

    def test_get_user_profile_not_found(self, service, mock_db_session):
        """测试获取不存在的画像"""
        # Arrange
        user_id = "user_not_exist"

        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        # Act
        profile = service.get_user_profile(user_id, mock_db_session)

        # Assert
        assert profile is None

    def test_get_love_language_description(self, service):
        """测试获取爱之语描述"""
        # Test each love language type
        desc = service.get_love_language_description(LoveLanguageType.WORDS.value)
        assert "肯定的言辞" in desc

        desc = service.get_love_language_description(LoveLanguageType.TIME.value)
        assert "精心时刻" in desc

        desc = service.get_love_language_description(LoveLanguageType.GIFTS.value)
        assert "接受礼物" in desc

        desc = service.get_love_language_description(LoveLanguageType.ACTS.value)
        assert "服务的行动" in desc

        desc = service.get_love_language_description(LoveLanguageType.TOUCH.value)
        assert "身体的接触" in desc

    def test_love_language_keywords_mapping(self, service):
        """测试爱之语关键词映射"""
        # Assert
        assert LoveLanguageType.WORDS.value in service.LOVE_LANGUAGE_KEYWORDS
        assert LoveLanguageType.TIME.value in service.LOVE_LANGUAGE_KEYWORDS
        assert LoveLanguageType.GIFTS.value in service.LOVE_LANGUAGE_KEYWORDS
        assert LoveLanguageType.ACTS.value in service.LOVE_LANGUAGE_KEYWORDS
        assert LoveLanguageType.TOUCH.value in service.LOVE_LANGUAGE_KEYWORDS

        # Verify keywords exist
        assert len(service.LOVE_LANGUAGE_KEYWORDS[LoveLanguageType.WORDS.value]) > 0
        assert len(service.LOVE_LANGUAGE_KEYWORDS[LoveLanguageType.TIME.value]) > 0


class TestRelationshipTrendService:
    """关系趋势预测服务测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return RelationshipTrendService()

    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        return MagicMock()

    def test_generate_trend_prediction_with_history(self, service, mock_db_session):
        """测试生成关系趋势预测（有历史数据）"""
        # Arrange
        user_a_id = "user_a"
        user_b_id = "user_b"
        prediction_period = "7d"

        # 创建模拟气象报告
        mock_report1 = MagicMock()
        mock_report1.emotional_temperature = 65.0
        mock_report1.weather_description = "sunny"
        mock_report1.created_at = datetime(2024, 1, 15)

        mock_report2 = MagicMock()
        mock_report2.emotional_temperature = 60.0
        mock_report2.weather_description = "partly_cloudy"
        mock_report2.created_at = datetime(2024, 1, 14)

        # Mock the query chain properly
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value.limit.return_value.all.return_value = [mock_report1, mock_report2]
        mock_db_session.query.return_value = mock_query

        # Mock add to set created_at on the prediction
        def add_side_effect(obj):
            if hasattr(obj, 'created_at'):
                obj.created_at = datetime(2024, 1, 15)
        mock_db_session.add.side_effect = add_side_effect
        mock_db_session.refresh.side_effect = lambda x: None

        # Act
        prediction = service.generate_trend_prediction(
            user_a_id, user_b_id, prediction_period, mock_db_session
        )

        # Assert
        assert prediction is not None
        assert "user_a_id" in prediction
        assert "user_b_id" in prediction
        assert "current_temperature" in prediction
        assert "temperature_trend" in prediction
        mock_db_session.add.assert_called()

    def test_generate_trend_prediction_no_history(self, service, mock_db_session):
        """测试生成关系趋势预测（无历史数据）"""
        # Arrange
        user_a_id = "user_a"
        user_b_id = "user_b"
        prediction_period = "7d"

        mock_db_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

        # Act
        prediction = service.generate_trend_prediction(
            user_a_id, user_b_id, prediction_period, mock_db_session
        )

        # Assert
        assert prediction is not None
        assert prediction["current_temperature"] == 50.0
        assert prediction["temperature_trend"] == service.TREND_STABLE
        assert "message" in prediction

    def test_infer_relationship_stage(self, service):
        """测试推断关系阶段"""
        # Arrange
        mock_report = MagicMock()

        # Test different temperature ranges
        mock_report.emotional_temperature = 85
        stage = service._infer_relationship_stage(mock_report)
        assert stage == service.STAGE_IN_RELATIONSHIP

        mock_report.emotional_temperature = 70
        stage = service._infer_relationship_stage(mock_report)
        assert stage == service.STAGE_DATING

        mock_report.emotional_temperature = 50
        stage = service._infer_relationship_stage(mock_report)
        assert stage == service.STAGE_CHATTING

        mock_report.emotional_temperature = 30
        stage = service._infer_relationship_stage(mock_report)
        assert stage == service.STAGE_MATCHED

    def test_predict_milestones_rising(self, service):
        """测试预测里程碑（上升趋势）"""
        # Arrange
        current_stage = service.STAGE_CHATTING
        trend = service.TREND_RISING

        # Act
        milestones = service._predict_milestones(current_stage, trend)

        # Assert
        assert len(milestones) > 0
        assert milestones[0]["type"] == "stage_progression"

    def test_predict_milestones_declining(self, service):
        """测试预测里程碑（下降趋势）"""
        # Arrange
        current_stage = service.STAGE_CHATTING
        trend = service.TREND_DECLINING

        # Act
        milestones = service._predict_milestones(current_stage, trend)

        # Assert
        assert len(milestones) == 0  # 下降趋势不预测里程碑

    def test_identify_risks(self, service):
        """测试识别风险因素"""
        # Arrange
        trend = service.TREND_DECLINING

        mock_report = MagicMock()
        mock_report.weather_description = "stormy"

        reports = [mock_report]

        # Act
        risks = service._identify_risks(reports, trend)

        # Assert
        assert len(risks) > 0
        assert any(r["type"] == "temperature_decline" for r in risks)

    def test_identify_opportunities(self, service):
        """测试识别机会因素"""
        # Arrange
        trend = service.TREND_RISING

        mock_report = MagicMock()
        mock_report.weather_description = "sunny"

        reports = [mock_report]

        # Act
        opportunities = service._identify_opportunities(reports, trend)

        # Assert
        assert len(opportunities) > 0
        assert any(o["type"] == "temperature_rise" for o in opportunities)

    def test_generate_recommendations_declining(self, service):
        """测试生成建议（下降趋势）"""
        # Arrange
        current_stage = service.STAGE_CHATTING
        trend = service.TREND_DECLINING
        risks = [{"type": "temperature_decline"}]
        opportunities = []

        # Act
        recommendations = service._generate_recommendations(
            current_stage, trend, risks, opportunities
        )

        # Assert
        assert len(recommendations) > 0
        assert any("沟通" in r.get("action", "") for r in recommendations)

    def test_get_stage_name(self, service):
        """测试获取阶段名称"""
        # Test all stages
        assert service._get_stage_name(service.STAGE_MATCHED) == "已匹配"
        assert service._get_stage_name(service.STAGE_CHATTING) == "聊天中"
        assert service._get_stage_name(service.STAGE_DATING) == "约会中"
        assert service._get_stage_name(service.STAGE_IN_RELATIONSHIP) == "恋爱中"

    def test_predict_stage_rising(self, service):
        """测试预测阶段（上升趋势）"""
        # Arrange
        current_stage = service.STAGE_CHATTING
        trend = service.TREND_RISING

        # Act
        predicted = service._predict_stage(current_stage, trend)

        # Assert
        assert predicted == service.STAGE_DATING

    def test_predict_stage_declining(self, service):
        """测试预测阶段（下降趋势）"""
        # Arrange
        current_stage = service.STAGE_DATING
        trend = service.TREND_DECLINING

        # Act
        predicted = service._predict_stage(current_stage, trend)

        # Assert
        assert predicted == service.STAGE_CHATTING

    def test_calculate_stage_change_probability(self, service):
        """测试计算阶段变化概率"""
        # Test rising trend
        prob = service._calculate_stage_change_probability(
            service.STAGE_CHATTING, service.TREND_RISING
        )
        assert abs(prob - 0.7) < 0.01

        # Test declining trend
        prob = service._calculate_stage_change_probability(
            service.STAGE_CHATTING, service.TREND_DECLINING
        )
        assert abs(prob - 0.1) < 0.01

        # Test stable trend
        prob = service._calculate_stage_change_probability(
            service.STAGE_CHATTING, service.TREND_STABLE
        )
        assert abs(prob - 0.3) < 0.01

    def test_get_prediction(self, service, mock_db_session):
        """测试获取预测记录"""
        # Arrange
        prediction_id = "prediction_001"

        mock_prediction = MagicMock()
        mock_prediction.id = prediction_id
        mock_prediction.user_a_id = "user_a"
        mock_prediction.user_b_id = "user_b"
        mock_prediction.prediction_base_date = datetime(2024, 1, 15)
        mock_prediction.prediction_period = "7d"
        mock_prediction.current_temperature = 65.0
        mock_prediction.predicted_temperature = 70.0
        mock_prediction.temperature_trend = service.TREND_RISING
        mock_prediction.current_stage = service.STAGE_CHATTING
        mock_prediction.predicted_stage = service.STAGE_DATING
        mock_prediction.stage_change_probability = 0.7
        mock_prediction.risk_indicators = []
        mock_prediction.opportunity_indicators = []
        mock_prediction.predicted_milestones = []
        mock_prediction.recommended_actions = []
        mock_prediction.model_version = "v1.0"
        mock_prediction.created_at = datetime(2024, 1, 15)
        mock_prediction.expires_at = None

        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_prediction

        # Act
        prediction = service.get_prediction(prediction_id, mock_db_session)

        # Assert
        assert prediction is not None
        assert prediction["id"] == prediction_id


class TestWarningResponseService:
    """预警分级响应服务测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return WarningResponseService()

    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        return MagicMock()

    def test_get_response_strategy(self, service, mock_db_session):
        """测试获取响应策略"""
        # Arrange
        warning_level = service.LEVEL_MEDIUM
        context = {"emotion_keywords": ["烦", "累"]}

        mock_strategy = MagicMock()
        mock_strategy.id = "strategy_medium"
        mock_strategy.warning_level = warning_level
        mock_strategy.response_type = "cooling_technique"
        mock_strategy.response_template = "检测到对话气氛紧张..."
        mock_strategy.expected_effect = "降低情绪激动程度"
        mock_strategy.usage_guide = "适用于情绪开始升级"
        mock_strategy.effectiveness_rating = 0.8

        mock_db_session.query.return_value.filter.return_value.all.return_value = [mock_strategy]

        # Act
        strategy = service.get_response_strategy(warning_level, context, mock_db_session)

        # Assert
        assert strategy is not None
        assert strategy["warning_level"] == warning_level

    def test_get_response_strategy_not_found(self, service, mock_db_session):
        """测试获取不存在的策略"""
        # Arrange
        warning_level = "unknown_level"

        mock_db_session.query.return_value.filter.return_value.all.return_value = []

        # Act
        strategy = service.get_response_strategy(warning_level, None, mock_db_session)

        # Assert
        assert strategy is None

    def test_execute_response(self, service, mock_db_session):
        """测试执行预警响应"""
        # Arrange
        warning_id = "warning_001"
        strategy_id = "strategy_001"
        recipient_user_id = "user_001"
        response_content = "建议深呼吸，冷静一下"
        delivery_method = "push_notification"

        mock_db_session.add.return_value = None
        mock_db_session.commit.return_value = None

        mock_strategy = MagicMock()
        mock_strategy.usage_count = 10
        # Mock query to return strategy
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_strategy
        mock_db_session.query.return_value = mock_query

        # Mock the record that gets created (patch to set created_at)
        def add_side_effect(record):
            record.created_at = datetime(2024, 1, 15)
        mock_db_session.add.side_effect = add_side_effect

        # Act
        result = service.execute_response(
            warning_id, strategy_id, recipient_user_id,
            response_content, delivery_method, mock_db_session
        )

        # Assert
        assert result is not None
        assert result["warning_id"] == warning_id
        assert result["recipient_user_id"] == recipient_user_id
        mock_db_session.add.assert_called()

    def test_submit_response_feedback(self, service, mock_db_session):
        """测试提交响应反馈"""
        # Arrange
        record_id = "record_001"
        feedback = "helpful"
        emotion_change = 0.3
        relationship_improvement = 0.5

        mock_record = MagicMock()
        mock_record.id = record_id
        mock_record.strategy_id = "strategy_001"
        mock_record.user_feedback = None
        mock_record.emotion_change = None
        mock_record.relationship_improvement = None

        mock_strategy = MagicMock()
        mock_strategy.effectiveness_rating = 0.7
        mock_strategy.usage_count = 10

        mock_db_session.query.return_value.filter.return_value.first.side_effect = [
            mock_record, mock_strategy
        ]
        mock_db_session.commit.return_value = None

        # Act
        result = service.submit_response_feedback(
            record_id, feedback, emotion_change,
            relationship_improvement, mock_db_session
        )

        # Assert
        assert result == True
        assert mock_record.user_feedback == feedback
        mock_db_session.commit.assert_called()

    def test_submit_response_feedback_not_found(self, service, mock_db_session):
        """测试提交不存在的反馈记录"""
        # Arrange
        record_id = "record_not_exist"

        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        # Act
        result = service.submit_response_feedback(record_id, "helpful", None, None, mock_db_session)

        # Assert
        assert result == False

    def test_get_response_history(self, service, mock_db_session):
        """测试获取响应历史"""
        # Arrange
        user_id = "user_001"

        mock_record = MagicMock()
        mock_record.id = "record_001"
        mock_record.warning_id = "warning_001"
        mock_record.response_type = "executed"
        mock_record.response_content = "建议内容"
        mock_record.delivery_method = "push_notification"
        mock_record.is_acknowledged = False
        mock_record.user_feedback = "helpful"
        mock_record.emotion_change = 0.3
        mock_record.created_at = datetime(2024, 1, 15)
        mock_record.recipient_user_id = user_id

        # Mock the query chain properly
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value.limit.return_value.all.return_value = [mock_record]
        mock_db_session.query.return_value = mock_query

        # Act
        history = service.get_response_history(user_id, mock_db_session)

        # Assert
        assert len(history) == 1
        assert history[0]["id"] == "record_001"
        assert history[0]["warning_id"] == "warning_001"
        assert history[0]["response_content"] == "建议内容"

    def test_default_strategies_initialization(self, service, mock_db_session):
        """测试默认策略初始化"""
        # Arrange
        mock_db_session.add.return_value = None
        mock_db_session.commit.return_value = None

        # Act
        service._ensure_initialized(mock_db_session)

        # Assert
        assert mock_db_session.add.call_count >= 4  # 4 个级别的策略
        assert service._initialized == True

    def test_ensure_initialization(self, service, mock_db_session):
        """测试确保初始化"""
        # Arrange
        service._initialized = False
        mock_db_session.add.return_value = None
        mock_db_session.commit.return_value = None

        # Act
        service._ensure_initialized(mock_db_session)

        # Assert
        assert service._initialized == True

    def test_warning_levels_complete(self, service):
        """测试预警级别完整性"""
        # Assert
        assert hasattr(service, 'LEVEL_LOW')
        assert hasattr(service, 'LEVEL_MEDIUM')
        assert hasattr(service, 'LEVEL_HIGH')
        assert hasattr(service, 'LEVEL_CRITICAL')
        assert service.LEVEL_LOW == "low"
        assert service.LEVEL_MEDIUM == "medium"
        assert service.LEVEL_HIGH == "high"
        assert service.LEVEL_CRITICAL == "critical"
