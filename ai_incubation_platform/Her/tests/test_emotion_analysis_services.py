"""
P11 感官洞察服务层单元测试
测试覆盖：情感分析、安全监控、情感报告生成
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session

from services.emotion_analysis_service import (
    EmotionAnalysisService,
    EmotionReportService
)
from services.safety_guardian_service import SafetyMonitoringService
from models.emotion_analysis_models import (
    EmotionAnalysisDB,
    EmotionReportDB,
    EmotionalTrendDB,
    SafetyCheckDB,
    SafetyAlertDB,
    SafetyPlanDB,
    DateSafetySessionDB,
    SensoryInsightDB
)


# ==================== EmotionAnalysisService 测试 ====================

class TestEmotionAnalysisService:
    """情感分析服务测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return EmotionAnalysisService()

    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        session = MagicMock()

        def add_side_effect(record):
            record.created_at = datetime(2024, 1, 15)
            record.id = "test-id"
        session.add.side_effect = add_side_effect
        session.commit.return_value = None
        session.refresh.return_value = None
        return session

    def test_analyze_micro_expression_success(self, service, mock_db_session):
        """测试微表情分析成功"""
        # Arrange
        user_id = "user_001"
        session_id = "session_001"
        facial_data = {
            "expressions": [
                {"type": "genuine_smile", "confidence": 0.85, "duration_ms": 500},
                {"type": "raised_eyebrows", "confidence": 0.5, "duration_ms": 300}
            ],
            "action_units": ["AU12", "AU6"],
            "crow_feet": True,
            "eye_contact_duration": 0.7
        }

        # Act
        analysis_id = service.analyze_micro_expression(
            user_id, session_id, facial_data, mock_db_session
        )

        # Assert
        assert analysis_id is not None
        mock_db_session.add.assert_called_once()

    def test_analyze_micro_expression_empty_data(self, service, mock_db_session):
        """测试空面部数据的微表情分析"""
        # Arrange
        user_id = "user_001"
        session_id = "session_001"
        facial_data = {}

        # Act
        analysis_id = service.analyze_micro_expression(
            user_id, session_id, facial_data, mock_db_session
        )

        # Assert
        assert analysis_id is not None

    def test_analyze_voice_emotion_success(self, service, mock_db_session):
        """测试语音情感分析成功"""
        # Arrange
        user_id = "user_001"
        session_id = "session_001"
        voice_data = {
            "features": {
                "pitch_avg": 220,
                "speech_rate": 5.5,
                "volume_variance": 15,
                "pitch_variance": 20
            },
            "detected_emotions": [
                {"emotion": "happiness", "confidence": 0.75},
                {"emotion": "excitement", "confidence": 0.6}
            ]
        }

        # Act
        analysis_id = service.analyze_voice_emotion(
            user_id, session_id, voice_data, mock_db_session
        )

        # Assert
        assert analysis_id is not None
        mock_db_session.add.assert_called_once()

    def test_analyze_voice_emotion_empty_data(self, service, mock_db_session):
        """测试空语音数据的情感分析"""
        # Arrange
        user_id = "user_001"
        session_id = "session_001"
        voice_data = {}

        # Act
        analysis_id = service.analyze_voice_emotion(
            user_id, session_id, voice_data, mock_db_session
        )

        # Assert
        assert analysis_id is not None

    def test_combined_analysis_success(self, service, mock_db_session):
        """测试多模态情感分析"""
        # Arrange
        user_id = "user_001"
        session_id = "session_001"
        facial_data = {
            "expressions": [{"type": "genuine_smile", "confidence": 0.8, "duration_ms": 500}],
            "crow_feet": True
        }
        voice_data = {
            "features": {"pitch_avg": 200, "speech_rate": 4.5},
            "detected_emotions": [{"emotion": "happiness", "confidence": 0.7}]
        }

        # Act
        insight_id = service.combined_analysis(
            user_id, session_id, facial_data, voice_data, mock_db_session
        )

        # Assert
        assert insight_id is not None

    def test_extract_emotions_from_facial_data(self, service):
        """测试从面部数据提取情感"""
        # Arrange
        facial_data = {
            "expressions": [
                {"type": "genuine_smile", "confidence": 0.9, "duration_ms": 500},
                {"type": "raised_eyebrows", "confidence": 0.5, "duration_ms": 300}
            ]
        }

        # Act
        emotions = service._extract_emotions_from_facial_data(facial_data)

        # Assert
        assert len(emotions) >= 1
        assert all("emotion" in e and "confidence" in e for e in emotions)

    def test_extract_emotions_from_voice_data(self, service):
        """测试从语音数据提取情感"""
        # Arrange
        voice_data = {
            "features": {"pitch_avg": 130, "speech_rate": 2.5},
            "detected_emotions": [
                {"emotion": "anger", "confidence": 0.7},
                {"emotion": "fear", "confidence": 0.4}
            ]
        }

        # Act
        emotions = service._extract_emotions_from_voice_data(voice_data)

        # Assert
        assert len(emotions) >= 1
        assert all("emotion" in e and "confidence" in e for e in emotions)

    def test_calculate_authenticity_score(self, service):
        """测试真实性评分计算"""
        # Arrange
        facial_data = {
            "crow_feet": True,
            "eye_contact_duration": 0.8
        }
        emotions = [{"emotion": "happiness", "confidence": 0.85}]

        # Act
        score = service._calculate_authenticity_score(facial_data, emotions)

        # Assert
        assert 0 <= score <= 1

    def test_calculate_emotional_stability(self, service):
        """测试情感稳定性计算"""
        # Arrange
        voice_data = {
            "features": {
                "pitch_variance": 10,
                "volume_variance": 5
            }
        }

        # Act
        stability = service._calculate_emotional_stability(voice_data)

        # Assert
        assert 0 <= stability <= 1

    def test_detect_inconsistencies(self, service):
        """测试不一致性检测"""
        # Arrange
        facial_data = {"eye_avoidance": True}
        emotions = [{"emotion": "happiness", "confidence": 0.8}]

        # Act
        flags = service._detect_inconsistencies(facial_data, emotions)

        # Assert
        assert isinstance(flags, list)

    def test_detect_cross_modal_inconsistencies(self, service):
        """测试跨模态不一致性检测"""
        # Arrange
        face_emotions = [{"emotion": "happiness", "confidence": 0.8}]
        voice_emotions = [{"emotion": "sadness", "confidence": 0.7}]

        # Act
        flags = service._detect_cross_modal_inconsistencies(face_emotions, voice_emotions)

        # Assert
        assert isinstance(flags, list)

    def test_generate_micro_expression_insights(self, service):
        """测试微表情洞察生成"""
        # Arrange
        emotions = [{"emotion": "happiness", "confidence": 0.9}]
        facial_data = {"expression": "genuine_smile"}

        # Act
        insights = service._generate_micro_expression_insights(emotions, facial_data)

        # Assert
        assert insights is not None
        assert len(insights) > 0

    def test_generate_voice_emotion_insights(self, service):
        """测试语音情感洞察生成"""
        # Arrange
        emotions = [{"emotion": "excitement", "confidence": 0.8}]
        voice_data = {"features": {"speech_rate": 5.5}}

        # Act
        insights = service._generate_voice_emotion_insights(emotions, voice_data)

        # Assert
        assert insights is not None
        assert len(insights) > 0

    def test_merge_emotion_lists(self, service):
        """测试合并情感列表"""
        # Arrange
        face_emotions = [{"emotion": "happiness", "confidence": 0.8, "source": "facial"}]
        voice_emotions = [{"emotion": "happiness", "confidence": 0.7, "source": "voice"}]

        # Act
        merged = service._merge_emotion_lists(face_emotions, voice_emotions)

        # Assert
        assert len(merged) == 1
        assert merged[0]["emotion"] == "happiness"

    def test_get_analysis_by_session(self, service, mock_db_session):
        """测试获取会话的情感分析记录"""
        # Arrange
        session_id = "session_001"

        mock_analysis = MagicMock()
        mock_analysis.id = "analysis_001"
        mock_analysis.session_id = session_id

        mock_query = MagicMock()
        mock_query.filter.return_value.order_by.return_value.first.return_value = mock_analysis
        mock_db_session.query.return_value = mock_query

        # Act
        analysis = service.get_analysis_by_session(session_id, mock_db_session)

        # Assert
        assert analysis is not None

    def test_get_user_analyses(self, service, mock_db_session):
        """测试获取用户的情感分析历史"""
        # Arrange
        user_id = "user_001"
        limit = 10

        mock_analysis = MagicMock()
        mock_analysis.id = "analysis_001"
        mock_analysis.user_id = user_id

        mock_query = MagicMock()
        mock_query.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_analysis]
        mock_db_session.query.return_value = mock_query

        # Act
        analyses = service.get_user_analyses(user_id, limit, mock_db_session)

        # Assert
        assert len(analyses) == 1


# ==================== SafetyMonitoringService 测试 ====================

class TestSafetyMonitoringService:
    """安全监控服务测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return SafetyMonitoringService()

    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        session = MagicMock()

        def add_side_effect(record):
            record.created_at = datetime(2024, 1, 15)
            record.id = "test-id"
        session.add.side_effect = add_side_effect
        session.commit.return_value = None
        session.refresh.return_value = None
        return session

    def test_perform_location_safety_check_success(self, service, mock_db_session):
        """测试执行位置安全检查成功"""
        # Arrange
        user_id = "user_001"
        location_data = {
            "latitude": 39.9042,
            "longitude": 116.4074,
            "is_public_place": True,
            "is_isolated": False
        }

        # Act
        result = service.perform_location_safety_check(
            user_id, location_data, db_session_param=mock_db_session
        )

        # Assert
        assert "check_id" in result
        assert "risk_level" in result
        mock_db_session.add.assert_called()

    def test_perform_location_safety_check_high_risk(self, service, mock_db_session):
        """测试高风险位置检查"""
        # Arrange
        user_id = "user_001"
        location_data = {
            "latitude": 39.9042,
            "longitude": 116.4074,
            "is_public_place": False,
            "is_isolated": True
        }

        # Act
        result = service.perform_location_safety_check(
            user_id, location_data, db_session_param=mock_db_session
        )

        # Assert
        assert "check_id" in result

    def test_perform_voice_anomaly_check_success(self, service, mock_db_session):
        """测试执行语音异常检测成功"""
        # Arrange
        user_id = "user_001"
        voice_data = {
            "stress_level": 0.8,
            "background_noise_level": "chaotic",
            "distress_keywords": ["救命", "帮助"]
        }

        # Act
        result = service.perform_voice_anomaly_check(
            user_id, voice_data, db_session_param=mock_db_session
        )

        # Assert
        assert "check_id" in result
        assert "anomaly_detected" in result

    def test_perform_voice_anomaly_check_normal(self, service, mock_db_session):
        """测试正常语音检查"""
        # Arrange
        user_id = "user_001"
        voice_data = {
            "stress_level": 0.2,
            "background_noise_level": "normal",
            "distress_keywords": []
        }

        # Act
        result = service.perform_voice_anomaly_check(
            user_id, voice_data, db_session_param=mock_db_session
        )

        # Assert
        assert "check_id" in result
        assert result["anomaly_detected"] == False

    def test_perform_scheduled_checkin_ok(self, service, mock_db_session):
        """测试定时签到 - 正常"""
        # Arrange
        user_id = "user_001"
        session_id = "session_001"

        # Act
        result = service.perform_scheduled_checkin(
            user_id, session_id, user_status="ok", db_session_param=mock_db_session
        )

        # Assert
        assert "check_id" in result
        assert result["status"] == "ok"

    def test_perform_scheduled_checkin_need_help(self, service, mock_db_session):
        """测试定时签到 - 需要帮助"""
        # Arrange
        user_id = "user_001"
        session_id = "session_001"

        # Act
        result = service.perform_scheduled_checkin(
            user_id, session_id, user_status="need_help", db_session_param=mock_db_session
        )

        # Assert
        assert "check_id" in result
        assert result["alert_triggered"] == True

    def test_create_safety_plan_new(self, service, mock_db_session):
        """测试创建新安全计划"""
        # Arrange
        user_id = "user_001"
        emergency_contacts = [{"name": "张三", "phone": "13800138000"}]
        safety_preferences = {"auto_alert": True}

        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        # Act
        plan_id = service.create_safety_plan(
            user_id, emergency_contacts, safety_preferences, mock_db_session
        )

        # Assert
        assert plan_id is not None
        mock_db_session.add.assert_called()

    def test_create_safety_plan_update(self, service, mock_db_session):
        """测试更新安全计划"""
        # Arrange
        user_id = "user_001"
        emergency_contacts = [{"name": "张三", "phone": "13800138000"}]
        safety_preferences = {"auto_alert": True}

        mock_existing = MagicMock()
        mock_existing.id = "existing_plan_id"
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_existing

        # Act
        plan_id = service.create_safety_plan(
            user_id, emergency_contacts, safety_preferences, mock_db_session
        )

        # Assert
        assert plan_id == "existing_plan_id"

    def test_get_user_safety_plan(self, service, mock_db_session):
        """测试获取用户安全计划"""
        # Arrange
        user_id = "user_001"

        mock_plan = MagicMock()
        mock_plan.user_id = user_id
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_plan

        # Act
        plan = service.get_user_safety_plan(user_id, mock_db_session)

        # Assert
        assert plan is not None

    def test_get_safety_alerts(self, service, mock_db_session):
        """测试获取用户安全警报"""
        # Arrange
        user_id = "user_001"
        limit = 20

        mock_alert = MagicMock()
        mock_alert.user_id = user_id

        mock_query = MagicMock()
        mock_query.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_alert]
        mock_db_session.query.return_value = mock_query

        # Act
        alerts = service.get_safety_alerts(user_id, limit, mock_db_session)

        # Assert
        assert len(alerts) == 1

    def test_acknowledge_alert(self, service, mock_db_session):
        """测试确认警报"""
        # Arrange
        alert_id = "alert_001"
        user_id = "user_001"

        mock_alert = MagicMock()
        mock_alert.id = alert_id
        mock_alert.user_id = user_id
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_alert

        # Act
        result = service.acknowledge_alert(alert_id, user_id, mock_db_session)

        # Assert
        assert result == True

    def test_acknowledge_alert_not_found(self, service, mock_db_session):
        """测试确认不存在的警报"""
        # Arrange
        alert_id = "alert_not_exist"
        user_id = "user_001"

        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        # Act
        result = service.acknowledge_alert(alert_id, user_id, mock_db_session)

        # Assert
        assert result == False

    def test_resolve_alert(self, service, mock_db_session):
        """测试解决警报"""
        # Arrange
        alert_id = "alert_001"
        user_id = "user_001"
        resolution_notes = "问题已解决"

        mock_alert = MagicMock()
        mock_alert.id = alert_id
        mock_alert.user_id = user_id
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_alert

        # Act
        result = service.resolve_alert(alert_id, user_id, resolution_notes, False, mock_db_session)

        # Assert
        assert result == True

    def test_create_date_safety_session(self, service, mock_db_session):
        """测试创建约会安全会话"""
        # Arrange
        user_id = "user_001"
        partner_user_id = "user_002"
        scheduled_start = datetime(2024, 1, 15, 18, 0)
        scheduled_end = datetime(2024, 1, 15, 20, 0)

        # Act
        session_id = service.create_date_safety_session(
            user_id, partner_user_id, None, scheduled_start, scheduled_end, mock_db_session
        )

        # Assert
        assert session_id is not None

    def test_start_date_safety_session(self, service, mock_db_session):
        """测试开始约会安全会话"""
        # Arrange
        session_id = "session_001"

        mock_session = MagicMock()
        mock_session.id = session_id
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_session

        # Act
        result = service.start_date_safety_session(session_id, mock_db_session)

        # Assert
        assert result == True

    def test_start_date_safety_session_not_found(self, service, mock_db_session):
        """测试开始不存在的会话"""
        # Arrange
        session_id = "session_not_exist"
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        # Act
        result = service.start_date_safety_session(session_id, mock_db_session)

        # Assert
        assert result == False

    def test_complete_date_safety_session(self, service, mock_db_session):
        """测试完成约会安全会话"""
        # Arrange
        session_id = "session_001"
        safety_rating = 5
        feedback = "约会顺利"

        mock_session = MagicMock()
        mock_session.id = session_id
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_session

        # Act
        result = service.complete_date_safety_session(
            session_id, safety_rating, feedback, mock_db_session
        )

        # Assert
        assert result == True

    def test_risk_level_determination(self, service):
        """测试风险级别判定"""
        # Arrange - 根据实际阈值：>=0.9 critical, >=0.7 high, >=0.5 medium, <0.5 low
        risk_scores = [
            (0.1, "low"),      # < 0.5
            (0.35, "low"),     # < 0.5
            (0.5, "medium"),   # >= 0.5
            (0.6, "medium"),   # >= 0.5 且 < 0.7
            (0.7, "high"),     # >= 0.7
            (0.8, "high"),     # >= 0.7 且 < 0.9
            (0.9, "critical"), # >= 0.9
            (0.95, "critical")
        ]

        # Act & Assert
        for score, expected_level in risk_scores:
            level = service._determine_risk_level(score)
            assert level == expected_level, f"Risk score {score} should be {expected_level}, got {level}"

    def test_calculate_risk_score(self, service):
        """测试风险评分计算"""
        # Arrange
        factors_low = [{"severity": "low"}]
        factors_high = [{"severity": "high"}, {"severity": "critical"}]

        # Act
        score_low = service._calculate_risk_score(factors_low)
        score_high = service._calculate_risk_score(factors_high)

        # Assert
        assert 0 <= score_low <= 0.3
        assert score_high > score_low


# ==================== EmotionReportService 测试 ====================

class TestEmotionReportService:
    """情感报告服务测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return EmotionReportService()

    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        session = MagicMock()

        def add_side_effect(record):
            record.created_at = datetime(2024, 1, 15)
            record.id = "test-id"
        session.add.side_effect = add_side_effect
        session.commit.return_value = None
        session.refresh.return_value = None
        return session

    def test_generate_session_report_success(self, service, mock_db_session):
        """测试生成会话情感报告成功"""
        # Arrange
        user_id = "user_001"
        session_id = "session_001"

        mock_analysis = MagicMock()
        mock_analysis.user_id = user_id
        mock_analysis.session_id = session_id
        mock_analysis.micro_expressions = {"detected_emotions": [{"emotion": "happiness", "confidence": 0.8}]}
        mock_analysis.voice_emotions = None

        mock_db_session.query.return_value.filter.return_value.all.return_value = [mock_analysis]

        # Act
        report_id = service.generate_session_report(user_id, session_id, mock_db_session)

        # Assert
        assert report_id is not None
        mock_db_session.add.assert_called()

    def test_generate_session_report_no_data(self, service, mock_db_session):
        """测试无数据时生成报告"""
        # Arrange
        user_id = "user_001"
        session_id = "session_001"

        mock_db_session.query.return_value.filter.return_value.all.return_value = []

        # Act & Assert
        with pytest.raises(ValueError):
            service.generate_session_report(user_id, session_id, mock_db_session)

    def test_get_user_reports(self, service, mock_db_session):
        """测试获取用户情感报告"""
        # Arrange
        user_id = "user_001"
        limit = 10

        mock_report = MagicMock()
        mock_report.user_id = user_id

        mock_query = MagicMock()
        mock_query.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_report]
        mock_db_session.query.return_value = mock_query

        # Act
        reports = service.get_user_reports(user_id, limit, mock_db_session)

        # Assert
        assert len(reports) == 1

    def test_calculate_emotion_distribution(self, service):
        """测试计算情感分布"""
        # Arrange
        emotions = [
            {"emotion": "happiness", "confidence": 0.8},
            {"emotion": "happiness", "confidence": 0.6},
            {"emotion": "sadness", "confidence": 0.4}
        ]

        # Act
        distribution = service._calculate_emotion_distribution(emotions)

        # Assert
        assert "happiness" in distribution
        assert "sadness" in distribution
        assert abs(sum(distribution.values()) - 1.0) < 0.01

    def test_generate_report_summary(self, service):
        """测试生成报告摘要"""
        # Arrange
        distribution = {"happiness": 0.6, "excitement": 0.3, "nervousness": 0.1}

        # Act
        summary = service._generate_report_summary(distribution)

        # Assert
        assert len(summary) > 0
        assert "happiness" in summary or "喜悦" in summary

    def test_calculate_positivity(self, service):
        """测试计算积极度"""
        # Arrange
        distribution_positive = {"happiness": 0.6, "excitement": 0.3}
        distribution_negative = {"sadness": 0.6, "anger": 0.3}

        # Act
        positivity_high = service._calculate_positivity(distribution_positive)
        positivity_low = service._calculate_positivity(distribution_negative)

        # Assert
        assert positivity_high > 0.5
        assert positivity_low < 0.5

    def test_generate_action_items(self, service):
        """测试生成行动建议"""
        # Arrange
        distribution = {"nervousness": 0.4, "happiness": 0.5}

        # Act
        items = service._generate_action_items(distribution)

        # Assert
        assert isinstance(items, list)
        assert len(items) > 0


# ==================== 集成测试 ====================

class TestP11ServiceIntegration:
    """P11 服务集成测试"""

    def test_emotion_analysis_workflow(self):
        """测试情感分析完整工作流"""
        # Arrange
        service = EmotionAnalysisService()
        mock_db = MagicMock()

        def add_side_effect(record):
            record.created_at = datetime(2024, 1, 15)
            record.id = "test-id"
        mock_db.add.side_effect = add_side_effect
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None

        facial_data = {
            "expressions": [{"type": "genuine_smile", "confidence": 0.9, "duration_ms": 500}],
            "action_units": ["AU12", "AU6"],
            "crow_feet": True,
            "eye_contact_duration": 0.7
        }

        # Act
        analysis_id = service.analyze_micro_expression(
            "user_001", "session_001", facial_data, mock_db
        )

        # Assert
        assert analysis_id is not None

    def test_safety_monitoring_workflow(self):
        """测试安全监控完整工作流"""
        # Arrange
        service = SafetyMonitoringService()
        mock_db = MagicMock()

        def add_side_effect(record):
            record.created_at = datetime(2024, 1, 15)
            record.id = "test-id"
        mock_db.add.side_effect = add_side_effect
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None

        location_data = {
            "latitude": 39.9042,
            "longitude": 116.4074,
            "is_public_place": True
        }

        # Act - call with mock_db directly
        result = service.perform_location_safety_check(
            "user_001", location_data, mock_db
        )

        # Assert
        assert "check_id" in result

    def test_supported_emotions_coverage(self):
        """测试支持的情感覆盖范围"""
        service = EmotionAnalysisService()

        # Assert
        assert len(service.SUPPORTED_EMOTIONS) >= 10
        assert "happiness" in service.SUPPORTED_EMOTIONS
        assert "sadness" in service.SUPPORTED_EMOTIONS
        assert "anger" in service.SUPPORTED_EMOTIONS

    def test_micro_expression_mapping(self):
        """测试微表情到情感映射"""
        service = EmotionAnalysisService()

        # Assert
        assert "genuine_smile" in service.MICRO_EXPRESSION_TO_EMOTION
        assert service.MICRO_EXPRESSION_TO_EMOTION["genuine_smile"] == "happiness"

    def test_risk_thresholds_defined(self):
        """测试风险阈值定义"""
        service = SafetyMonitoringService()

        # Assert
        assert "low" in service.RISK_THRESHOLDS
        assert "medium" in service.RISK_THRESHOLDS
        assert "high" in service.RISK_THRESHOLDS
        assert "critical" in service.RISK_THRESHOLDS

    def test_alert_level_map_defined(self):
        """测试警报级别映射定义"""
        service = SafetyMonitoringService()

        # Assert
        assert "low" in service.ALERT_LEVEL_MAP
        assert "medium" in service.ALERT_LEVEL_MAP
        assert "high" in service.ALERT_LEVEL_MAP
        assert "critical" in service.ALERT_LEVEL_MAP
