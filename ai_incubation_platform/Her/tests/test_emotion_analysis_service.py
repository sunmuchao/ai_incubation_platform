"""
P11 感官洞察服务测试

测试覆盖:
- 微表情分析
- 语音情感分析
- 综合分析
- 情感报告生成
"""
import pytest
import os
import sys
import uuid
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime, timedelta

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置环境变量
os.environ['OPENAI_API_KEY'] = 'test-key'
os.environ['OPENAI_BASE_URL'] = 'https://test.api/v1'


class TestEmotionAnalysisService:
    """情感分析服务测试"""

    @pytest.fixture
    def emotion_service(self):
        """创建测试服务"""
        from services.emotion_analysis_service import EmotionAnalysisService
        return EmotionAnalysisService()

    @pytest.fixture
    def mock_db(self):
        """创建 mock 数据库会话"""
        return MagicMock()

    def test_init(self, emotion_service):
        """测试初始化"""
        assert emotion_service is not None
        assert hasattr(emotion_service, 'SUPPORTED_EMOTIONS')
        assert hasattr(emotion_service, 'MICRO_EXPRESSION_TO_EMOTION')

    def test_supported_emotions(self, emotion_service):
        """测试支持的情感列表"""
        emotions = emotion_service.SUPPORTED_EMOTIONS
        assert "happiness" in emotions
        assert "sadness" in emotions
        assert "anger" in emotions
        assert "nervousness" in emotions

    def test_micro_expression_mapping(self, emotion_service):
        """测试微表情映射"""
        mapping = emotion_service.MICRO_EXPRESSION_TO_EMOTION
        assert mapping["genuine_smile"] == "happiness"
        assert mapping["tight_lips"] == "nervousness"
        assert mapping["raised_eyebrows"] == "surprise"

    def test_analyze_micro_expression(self, emotion_service, mock_db):
        """测试微表情分析"""
        mock_db.add = MagicMock()

        facial_data = {
            "expressions": [
                {"type": "genuine_smile", "confidence": 0.8, "duration_ms": 500},
                {"type": "raised_eyebrows", "confidence": 0.6, "duration_ms": 300}
            ],
            "action_units": ["AU12", "AU1"],
            "crow_feet": True,
            "eye_contact_duration": 0.7
        }

        analysis_id = emotion_service.analyze_micro_expression(
            user_id='test_user',
            session_id='session_001',
            facial_data=facial_data,
            db_session_param=mock_db
        )

        assert analysis_id is not None

    def test_analyze_voice_emotion(self, emotion_service, mock_db):
        """测试语音情感分析"""
        mock_db.add = MagicMock()

        voice_data = {
            "features": {
                "pitch_avg": 220,
                "speech_rate": 4.5,
                "volume_variance": 15
            },
            "detected_emotions": [
                {"emotion": "excitement", "confidence": 0.7}
            ]
        }

        analysis_id = emotion_service.analyze_voice_emotion(
            user_id='test_user',
            session_id='session_001',
            voice_data=voice_data,
            db_session_param=mock_db
        )

        assert analysis_id is not None

    def test_combined_analysis(self, emotion_service, mock_db):
        """测试综合分析"""
        mock_db.add = MagicMock()

        facial_data = {
            "expressions": [{"type": "genuine_smile", "confidence": 0.8}],
            "eye_contact_duration": 0.6
        }

        voice_data = {
            "features": {"pitch_avg": 200, "speech_rate": 4.0},
            "detected_emotions": [{"emotion": "happiness", "confidence": 0.7}]
        }

        analysis_id = emotion_service.combined_analysis(
            user_id='test_user',
            session_id='session_001',
            facial_data=facial_data,
            voice_data=voice_data,
            db_session_param=mock_db
        )

        assert analysis_id is not None

    def test_extract_emotions_from_facial_data(self, emotion_service):
        """测试从面部数据提取情感"""
        facial_data = {
            "expressions": [
                {"type": "genuine_smile", "confidence": 0.9},
                {"type": "raised_eyebrows", "confidence": 0.6}
            ]
        }

        emotions = emotion_service._extract_emotions_from_facial_data(facial_data)

        assert len(emotions) == 2
        assert emotions[0]["emotion"] == "happiness"
        assert emotions[0]["confidence"] == 0.9

    def test_extract_emotions_from_facial_data_empty(self, emotion_service):
        """测试空面部数据"""
        emotions = emotion_service._extract_emotions_from_facial_data({})
        assert emotions == []

    def test_extract_emotions_from_voice_data(self, emotion_service):
        """测试从语音数据提取情感"""
        voice_data = {
            "features": {"pitch_avg": 260, "speech_rate": 5.5},
            "detected_emotions": [{"emotion": "excitement", "confidence": 0.7}]
        }

        emotions = emotion_service._extract_emotions_from_voice_data(voice_data)

        assert len(emotions) >= 1
        assert any(e["emotion"] == "excitement" for e in emotions)

    def test_extract_emotions_from_voice_data_high_pitch(self, emotion_service):
        """测试高音调语音"""
        voice_data = {
            "features": {"pitch_avg": 280, "speech_rate": 6},
            "detected_emotions": []
        }

        emotions = emotion_service._extract_emotions_from_voice_data(voice_data)

        # 高音调 + 快语速应推断为兴奋
        assert any(e["emotion"] == "excitement" for e in emotions)

    def test_extract_emotions_from_voice_data_low_pitch(self, emotion_service):
        """测试低音调语音"""
        voice_data = {
            "features": {"pitch_avg": 120, "speech_rate": 2},
            "detected_emotions": []
        }

        emotions = emotion_service._extract_emotions_from_voice_data(voice_data)

        # 低音调 + 慢语速应推断为悲伤
        assert any(e["emotion"] == "sadness" for e in emotions)

    def test_merge_emotion_lists(self, emotion_service):
        """测试合并情感列表"""
        face_emotions = [
            {"emotion": "happiness", "confidence": 0.8, "source": "facial"}
        ]
        voice_emotions = [
            {"emotion": "happiness", "confidence": 0.6, "source": "voice"},
            {"emotion": "excitement", "confidence": 0.5, "source": "voice"}
        ]

        merged = emotion_service._merge_emotion_lists(face_emotions, voice_emotions)

        assert len(merged) == 2
        # happiness 应被合并
        happiness = next(e for e in merged if e["emotion"] == "happiness")
        assert happiness["confidence"] == 0.7  # 平均值

    def test_calculate_authenticity_score(self, emotion_service):
        """测试真实性评分计算"""
        facial_data = {
            "crow_feet": True,
            "eye_contact_duration": 0.7
        }
        emotions = [{"emotion": "happiness", "confidence": 0.8}]

        score = emotion_service._calculate_authenticity_score(facial_data, emotions)

        assert score > 0.5
        assert score <= 1.0

    def test_calculate_authenticity_score_no_crow_feet(self, emotion_service):
        """测试无鱼尾纹的真实性评分"""
        facial_data = {
            "crow_feet": False,
            "eye_contact_duration": 0.3
        }
        emotions = [{"emotion": "nervousness", "confidence": 0.5}]

        score = emotion_service._calculate_authenticity_score(facial_data, emotions)

        assert score >= 0.5

    def test_calculate_emotional_stability(self, emotion_service):
        """测试情感稳定性计算"""
        voice_data = {
            "features": {
                "pitch_variance": 10,
                "volume_variance": 5
            }
        }

        stability = emotion_service._calculate_emotional_stability(voice_data)

        assert stability >= 0.0
        assert stability <= 1.0

    def test_calculate_emotional_stability_high_variance(self, emotion_service):
        """测试高方差的情感稳定性"""
        voice_data = {
            "features": {
                "pitch_variance": 80,
                "volume_variance": 40
            }
        }

        stability = emotion_service._calculate_emotional_stability(voice_data)

        # 高方差意味着低稳定性
        assert stability < 0.5

    def test_detect_inconsistencies(self, emotion_service):
        """测试不一致性检测"""
        facial_data = {"eye_avoidance": True}
        emotions = [{"emotion": "happiness", "confidence": 0.8}]

        flags = emotion_service._detect_inconsistencies(facial_data, emotions)

        assert len(flags) > 0
        assert flags[0]["type"] == "smile_eye_mismatch"

    def test_detect_inconsistencies_no_issue(self, emotion_service):
        """测试无不一致性"""
        facial_data = {"eye_avoidance": False}
        emotions = [{"emotion": "happiness", "confidence": 0.8}]

        flags = emotion_service._detect_inconsistencies(facial_data, emotions)

        assert flags == []

    def test_detect_cross_modal_inconsistencies(self, emotion_service):
        """测试跨模态不一致性"""
        face_emotions = [{"emotion": "happiness", "confidence": 0.8}]
        voice_emotions = [{"emotion": "sadness", "confidence": 0.7}]

        flags = emotion_service._detect_cross_modal_inconsistencies(face_emotions, voice_emotions)

        assert len(flags) > 0
        assert flags[0]["type"] == "voice_face_mismatch"

    def test_detect_cross_modal_inconsistencies_consistent(self, emotion_service):
        """测试一致的情感"""
        face_emotions = [{"emotion": "happiness", "confidence": 0.8}]
        voice_emotions = [{"emotion": "happiness", "confidence": 0.7}]

        flags = emotion_service._detect_cross_modal_inconsistencies(face_emotions, voice_emotions)

        assert flags == []

    def test_generate_micro_expression_insights(self, emotion_service):
        """测试微表情洞察生成"""
        emotions = [{"emotion": "happiness", "confidence": 0.85}]
        facial_data = {}

        insights = emotion_service._generate_micro_expression_insights(emotions, facial_data)

        assert insights is not None
        assert "happiness" in insights

    def test_generate_voice_emotion_insights(self, emotion_service):
        """测试语音情感洞察生成"""
        emotions = [{"emotion": "excitement", "confidence": 0.7}]
        voice_data = {"features": {"speech_rate": 5.5}}

        insights = emotion_service._generate_voice_emotion_insights(emotions, voice_data)

        assert insights is not None
        assert "excitement" in insights

    def test_get_interaction_recommendation(self, emotion_service):
        """测试互动建议"""
        assert emotion_service._get_interaction_recommendation("happiness") == "保持当前的积极互动节奏"
        assert emotion_service._get_interaction_recommendation("nervousness") == "可以适当放缓节奏，给予更多安全感"
        assert emotion_service._get_interaction_recommendation("interest") == "继续深入当前话题，探索共同兴趣"

    def test_generate_emotional_state_summary(self, emotion_service):
        """测试情感状态总结"""
        emotions = [{"emotion": "happiness", "confidence": 0.9}]

        summary = emotion_service._generate_emotional_state_summary(emotions)

        assert "喜悦" in summary
        assert "强烈" in summary

    def test_generate_emotional_state_summary_medium(self, emotion_service):
        """测试中等强度情感状态"""
        emotions = [{"emotion": "nervousness", "confidence": 0.6}]

        summary = emotion_service._generate_emotional_state_summary(emotions)

        assert "紧张" in summary
        assert "中等" in summary

    def test_generate_eq_tips(self, emotion_service):
        """测试情商建议生成"""
        emotions = [{"emotion": "nervousness", "confidence": 0.7}]
        facial_data = {"eye_avoidance": True}
        voice_data = {"features": {"speech_rate": 6}}

        tips = emotion_service._generate_eq_tips(emotions, facial_data, voice_data)

        assert tips is not None

    def test_get_analysis_by_session(self, emotion_service, mock_db):
        """测试获取会话分析"""
        mock_analysis = MagicMock()
        mock_analysis.id = 'analysis_001'

        with patch('services.emotion_analysis_service.db_session_readonly') as mock_session:
            mock_session.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_session.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_analysis

            result = emotion_service.get_analysis_by_session(
                session_id='session_001'
            )

        assert result is not None

    def test_get_user_analyses(self, emotion_service, mock_db):
        """测试获取用户分析历史"""
        mock_analyses = [MagicMock(id='analysis_001'), MagicMock(id='analysis_002')]

        with patch('services.emotion_analysis_service.db_session_readonly') as mock_session:
            mock_session.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_session.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_analyses

            result = emotion_service.get_user_analyses(
                user_id='test_user',
                limit=10
            )

        assert len(result) == 2


class TestEmotionReportService:
    """情感报告服务测试"""

    @pytest.fixture
    def report_service(self):
        """创建测试服务"""
        from services.emotion_analysis_service import EmotionReportService
        return EmotionReportService()

    @pytest.fixture
    def mock_db(self):
        """创建 mock 数据库会话"""
        return MagicMock()

    def test_init(self, report_service):
        """测试初始化"""
        assert report_service is not None
        assert hasattr(report_service, 'emotion_analysis_service')

    def test_calculate_emotion_distribution(self, report_service):
        """测试情感分布计算"""
        emotions = [
            {"emotion": "happiness", "confidence": 0.8},
            {"emotion": "happiness", "confidence": 0.6},
            {"emotion": "sadness", "confidence": 0.4}
        ]

        distribution = report_service._calculate_emotion_distribution(emotions)

        assert "happiness" in distribution
        assert "sadness" in distribution
        # happiness 应占更大比例
        assert distribution["happiness"] > distribution["sadness"]

    def test_calculate_emotion_distribution_empty(self, report_service):
        """测试空情感列表"""
        distribution = report_service._calculate_emotion_distribution([])
        assert distribution == {}

    def test_generate_report_summary(self, report_service):
        """测试报告摘要生成"""
        distribution = {"happiness": 0.6, "excitement": 0.3, "nervousness": 0.1}

        summary = report_service._generate_report_summary(distribution)

        assert "喜悦" in summary
        assert "60%" in summary

    def test_generate_report_summary_empty(self, report_service):
        """测试空分布的摘要"""
        summary = report_service._generate_report_summary({})
        assert "未检测到" in summary

    def test_calculate_positivity(self, report_service):
        """测试积极度计算"""
        distribution = {"happiness": 0.5, "excitement": 0.3, "sadness": 0.2}

        positivity = report_service._calculate_positivity(distribution)

        assert positivity > 0.5  # 正向情感占多数

    def test_calculate_positivity_negative(self, report_service):
        """测试负向情感为主的积极度"""
        distribution = {"sadness": 0.6, "anger": 0.3, "happiness": 0.1}

        positivity = report_service._calculate_positivity(distribution)

        assert positivity < 0.5  # 负向情感占多数

    def test_calculate_positivity_neutral(self, report_service):
        """测试中性情感分布"""
        distribution = {"nervousness": 0.5}  # 不属于正向或负向

        positivity = report_service._calculate_positivity(distribution)

        assert positivity == 0.5  # 无正向/负向情感时的默认值

    def test_generate_action_items(self, report_service):
        """测试行动建议生成"""
        distribution = {"happiness": 0.6}

        items = report_service._generate_action_items(distribution)

        assert len(items) > 0
        assert any("积极" in item for item in items)

    def test_generate_action_items_nervousness(self, report_service):
        """测试紧张情绪的行动建议"""
        distribution = {"nervousness": 0.4}

        items = report_service._generate_action_items(distribution)

        assert any("紧张" in item for item in items)

    def test_generate_action_items_interest(self, report_service):
        """测试兴趣情绪的行动建议"""
        distribution = {"interest": 0.5}

        items = report_service._generate_action_items(distribution)

        assert any("兴趣" in item for item in items)

    def test_generate_action_items_sadness(self, report_service):
        """测试悲伤情绪的行动建议"""
        distribution = {"sadness": 0.3}

        items = report_service._generate_action_items(distribution)

        assert any("低落" in item for item in items)

    def test_generate_action_items_default(self, report_service):
        """测试默认行动建议"""
        distribution = {"comfort": 0.5}

        items = report_service._generate_action_items(distribution)

        # 无特定建议时返回默认
        assert len(items) > 0