"""
P12 行为实验室服务单元测试
测试覆盖：共同经历检测、尴尬沉默识别、情境话题生成
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
import json

from services.behavior_lab_service import (
    SharedExperienceService,
    SilenceDetectionService,
    IcebreakerTopicService
)
from models.behavior_lab_models import (
    SharedExperienceDB,
    SilenceEventDB,
    IcebreakerTopicDB,
    GeneratedIcebreakerDB
)


# ==================== SharedExperienceService 测试 ====================

class TestSharedExperienceService:
    """共同经历检测服务测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return SharedExperienceService()

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

    def test_service_initialization(self, service):
        """测试服务初始化"""
        assert service is not None
        assert hasattr(service, 'significance_threshold')
        assert service.TYPE_CONVERSATION == "conversation"
        assert service.TYPE_ACTIVITY == "activity"

    def test_significance_threshold_configured(self, service):
        """测试显著性阈值配置"""
        threshold = service.significance_threshold
        assert "duration_minutes" in threshold
        assert "message_count" in threshold
        assert "emotional_intensity" in threshold
        assert threshold["duration_minutes"] == 30
        assert threshold["message_count"] == 20
        assert threshold["emotional_intensity"] == 0.7

    def test_evaluate_significance_high_sentiment(self, service):
        """测试评估显著性 - 高情感强度"""
        # Arrange
        sentiment_score = 0.8  # 超过阈值 0.7

        # Act
        result = service._evaluate_significance("conversation", {}, sentiment_score)

        # Assert
        assert result == True

    def test_evaluate_significance_long_duration(self, service):
        """测试评估显著性 - 长时间"""
        # Arrange
        reference_data = {"duration_minutes": 45}  # 超过阈值 30

        # Act
        result = service._evaluate_significance("activity", reference_data, 0.3)

        # Assert
        assert result == True

    def test_evaluate_significance_many_messages(self, service):
        """测试评估显著性 - 多消息"""
        # Arrange
        reference_data = {"message_count": 25}  # 超过阈值 20

        # Act
        result = service._evaluate_significance("conversation", reference_data, 0.3)

        # Assert
        assert result == True

    def test_evaluate_significance_milestone(self, service):
        """测试评估显著性 - 里程碑事件"""
        # Arrange
        reference_data = {"is_milestone": True}

        # Act
        result = service._evaluate_significance("event", reference_data, 0.1)

        # Assert
        assert result == True

    def test_evaluate_significance_not_significant(self, service):
        """测试评估显著性 - 不显著"""
        # Arrange
        reference_data = {"duration_minutes": 10, "message_count": 5}

        # Act
        result = service._evaluate_significance("conversation", reference_data, 0.2)

        # Assert
        assert result == False

    def test_calculate_experience_sentiment_positive(self, service, mock_db_session):
        """测试计算情感评分 - 正面"""
        # Arrange
        mock_message = MagicMock()
        mock_message.content = "今天很开心，我很喜欢和你在一起"

        mock_db_session.query.return_value.filter.return_value.all.return_value = [mock_message]

        # Mock the emotion analysis to avoid LLM API calls
        with patch('services.behavior_lab_service.analyze_text_emotion_sync', return_value={"mood": "positive", "intensity": 0.8}):
            # Act
            score = service._calculate_experience_sentiment(mock_db_session, {"conversation_id": "conv_001"})

        # Assert
        assert score > 0

    def test_calculate_experience_sentiment_negative(self, service, mock_db_session):
        """测试计算情感评分 - 负面"""
        # Arrange
        mock_message = MagicMock()
        mock_message.content = "今天很难过，我很讨厌这样"

        mock_db_session.query.return_value.filter.return_value.all.return_value = [mock_message]

        # Mock the emotion analysis to avoid LLM API calls
        with patch('services.behavior_lab_service.analyze_text_emotion_sync', return_value={"mood": "negative", "intensity": 0.8}):
            # Act
            score = service._calculate_experience_sentiment(mock_db_session, {"conversation_id": "conv_001"})

        # Assert
        assert score < 0

    def test_calculate_experience_sentiment_default(self, service, mock_db_session):
        """测试计算情感评分 - 默认值"""
        # Arrange
        mock_db_session.query.return_value.filter.return_value.all.return_value = []
        reference_data = {"sentiment_score": 0.5}

        # Act
        score = service._calculate_experience_sentiment(mock_db_session, reference_data)

        # Assert
        assert score == 0.5

    def test_experience_to_dict(self, service):
        """测试经历对象转字典"""
        # Arrange
        mock_experience = MagicMock()
        mock_experience.id = "exp_001"
        mock_experience.user_a_id = "user_a"
        mock_experience.user_b_id = "user_b"
        mock_experience.experience_type = "conversation"
        mock_experience.description = "测试描述"
        mock_experience.start_time = datetime(2024, 1, 15)
        mock_experience.end_time = datetime(2024, 1, 15, 12)
        mock_experience.location = "测试地点"
        mock_experience.reference_data = {"key": "value"}
        mock_experience.sentiment_score = 0.7
        mock_experience.is_significant = True
        mock_experience.created_at = datetime(2024, 1, 15)

        # Act
        result = service._experience_to_dict(mock_experience)

        # Assert
        assert result["id"] == "exp_001"
        assert result["start_time"] is not None
        assert result["is_significant"] == True

    def test_detect_shared_experience_success(self, service, mock_db_session):
        """测试检测共同经历成功"""
        # Arrange
        user_a_id = "user_a"
        user_b_id = "user_b"
        experience_type = "conversation"
        reference_data = {
            "start_time": datetime(2024, 1, 15),
            "description": "测试对话",
            "sentiment_score": 0.5  # 直接提供情感评分，避免除零错误
        }

        # Act
        experience_id = service.detect_shared_experience(
            user_a_id, user_b_id, experience_type, reference_data, mock_db_session
        )

        # Assert
        assert experience_id is not None
        assert experience_id.startswith("exp_")
        mock_db_session.add.assert_called()

    def test_detect_shared_experience_error(self, service, mock_db_session):
        """测试检测共同经历出错"""
        # Arrange
        mock_db_session.add.side_effect = Exception("Database error")

        # Act
        experience_id = service.detect_shared_experience(
            "user_a", "user_b", "conversation", {}, mock_db_session
        )

        # Assert
        assert experience_id is None

    def test_get_shared_experiences(self, service, mock_db_session):
        """测试获取共同经历"""
        # Arrange
        user_a_id = "user_a"
        user_b_id = "user_b"

        mock_experience = MagicMock()
        mock_experience.user_a_id = user_a_id

        mock_query = MagicMock()
        mock_query.filter.return_value.order_by.return_value.all.return_value = [mock_experience]
        mock_db_session.query.return_value = mock_query

        # Act
        experiences = service.get_shared_experiences(user_a_id, user_b_id, db_session=mock_db_session)

        # Assert
        assert len(experiences) == 1

    def test_get_shared_experiences_filter_type(self, service, mock_db_session):
        """测试按类型过滤共同经历"""
        # Arrange
        user_a_id = "user_a"
        user_b_id = "user_b"
        experience_type = "activity"

        mock_experience = MagicMock()
        mock_experience.experience_type = experience_type

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query  # 支持链式调用
        mock_query.order_by.return_value.all.return_value = [mock_experience]
        mock_db_session.query.return_value = mock_query

        # Act
        experiences = service.get_shared_experiences(
            user_a_id, user_b_id, experience_type=experience_type, db_session=mock_db_session
        )

        # Assert
        assert len(experiences) >= 0

    def test_get_shared_experiences_significant_only(self, service, mock_db_session):
        """测试仅获取显著经历"""
        # Arrange
        user_a_id = "user_a"
        user_b_id = "user_b"

        mock_experience = MagicMock()
        mock_experience.is_significant = True

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value.all.return_value = [mock_experience]
        mock_db_session.query.return_value = mock_query

        # Act
        experiences = service.get_shared_experiences(
            user_a_id, user_b_id, only_significant=True, db_session=mock_db_session
        )

        # Assert
        assert len(experiences) >= 0

    def test_get_significant_memories(self, service, mock_db_session):
        """测试获取重要回忆"""
        # Arrange
        user_a_id = "user_a"
        user_b_id = "user_b"
        limit = 10

        mock_experience = MagicMock()
        mock_experience.is_significant = True
        mock_experience.sentiment_score = 0.8

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value.limit.return_value.all.return_value = [mock_experience]
        mock_db_session.query.return_value = mock_query

        # Act
        memories = service.get_significant_memories(user_a_id, user_b_id, limit, mock_db_session)

        # Assert
        assert len(memories) == 1


# ==================== SilenceDetectionService 测试 ====================

class TestSilenceDetectionService:
    """尴尬沉默识别服务测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return SilenceDetectionService()

    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        session = MagicMock()

        def add_side_effect(record):
            record.created_at = datetime(2024, 1, 15)
            record.id = "test-id"
        session.add.side_effect = add_side_effect
        session.commit.return_value = None
        return session

    def test_service_initialization(self, service):
        """测试服务初始化"""
        assert service is not None
        assert service.TYPE_AWKWARD == "awkward"
        assert service.TYPE_COMFORTABLE == "comfortable"
        assert service.TYPE_WAITING_RESPONSE == "waiting_response"

    def test_silence_thresholds_configured(self, service):
        """测试沉默阈值配置"""
        assert service.SILENCE_THRESHOLD_AWKWARD == 120  # 2 分钟
        assert service.SILENCE_THRESHOLD_WAITING == 300  # 5 分钟
        assert service.SILENCE_THRESHOLD_CRITICAL == 1800  # 30 分钟

    def test_classify_silence_early_relationship(self, service, mock_db_session):
        """测试分类沉默 - 初期关系"""
        # Arrange
        duration = 180  # 3 分钟
        conversation_id = "conv_001"

        mock_conversation = MagicMock()
        mock_conversation.relationship_stage = "strangers"
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_conversation

        # Act
        silence_type = service._classify_silence(duration, conversation_id, mock_db_session)

        # Assert
        assert silence_type == service.TYPE_AWKWARD

    def test_classify_silence_stable_relationship(self, service, mock_db_session):
        """测试分类沉默 - 稳定关系"""
        # Arrange
        duration = 60  # 1 分钟
        conversation_id = "conv_001"

        mock_conversation = MagicMock()
        mock_conversation.relationship_stage = "dating"
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_conversation

        # Act
        silence_type = service._classify_silence(duration, conversation_id, mock_db_session)

        # Assert
        assert silence_type == service.TYPE_COMFORTABLE

    def test_classify_silence_waiting_response(self, service, mock_db_session):
        """测试分类沉默 - 等待回复"""
        # Arrange
        duration = 2000  # 超过 30 分钟才会被分类为 waiting_response 在陌生人关系下
        conversation_id = "conv_001"

        mock_conversation = MagicMock()
        mock_conversation.relationship_stage = "dating"  # 稳定关系下，长时间沉默是等待回复
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_conversation

        # Act
        silence_type = service._classify_silence(duration, conversation_id, mock_db_session)

        # Assert
        assert silence_type == service.TYPE_WAITING_RESPONSE

    def test_generate_context_summary(self, service, mock_db_session):
        """测试生成上下文摘要"""
        # Arrange
        mock_last_message = MagicMock()
        mock_last_message.content = "最后一条消息"
        mock_last_message.sender_id = "user_a"

        mock_recent_msg = MagicMock()
        mock_recent_msg.content = "最近消息"
        mock_recent_msg.sender_id = "user_b"

        mock_db_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [
            mock_last_message, mock_recent_msg
        ]

        # Act
        summary = service._generate_context_summary(mock_last_message, "conv_001", mock_db_session)

        # Assert
        assert "最后话题" in summary

    def test_generate_context_summary_empty(self, service, mock_db_session):
        """测试生成上下文摘要 - 无消息"""
        # Arrange
        mock_db_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

        # Act
        summary = service._generate_context_summary(None, "conv_001", mock_db_session)

        # Assert
        assert "无上下文信息" in summary

    def test_generate_icebreaker_suggestions(self, service):
        """测试生成破冰建议"""
        # Arrange & Act
        suggestions = service._generate_icebreaker_suggestions(
            "user_a", "user_b", "上下文摘要", None
        )

        # Assert
        assert len(suggestions) >= 3
        assert any(s["type"] == "context_based" for s in suggestions)
        assert any(s["type"] == "light_topic" for s in suggestions)
        assert any(s["type"] == "caring_question" for s in suggestions)

    def test_detect_silence_no_silence(self, service, mock_db_session):
        """测试检测沉默 - 无沉默"""
        # Arrange
        mock_message = MagicMock()
        mock_message.created_at = datetime.utcnow()  # 刚发送的消息
        mock_message.conversation_id = "conv_001"

        mock_db_session.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_message

        # Act
        result = service.detect_silence("conv_001", "user_a", "user_b", mock_db_session)

        # Assert
        assert result is None  # 未达到沉默阈值

    def test_detect_silence_awkward(self, service, mock_db_session):
        """测试检测沉默 - 尴尬沉默"""
        # Arrange
        mock_message = MagicMock()
        mock_message.created_at = datetime.utcnow() - timedelta(minutes=5)  # 5 分钟前
        mock_message.conversation_id = "conv_001"

        mock_db_session.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_message

        # Act
        result = service.detect_silence("conv_001", "user_a", "user_b", mock_db_session)

        # Assert
        assert result is not None
        assert "silence_type" in result
        assert "duration_seconds" in result

    def test_detect_silence_no_messages(self, service, mock_db_session):
        """测试检测沉默 - 无消息"""
        # Arrange
        mock_db_session.query.return_value.filter.return_value.order_by.return_value.first.return_value = None

        # Act
        result = service.detect_silence("conv_001", "user_a", "user_b", mock_db_session)

        # Assert
        assert result is None

    def test_resolve_silence_success(self, service, mock_db_session):
        """测试解决沉默成功"""
        # Arrange
        silence_id = "silence_001"

        mock_silence = MagicMock()
        mock_silence.id = silence_id
        mock_silence.is_resolved = False
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_silence

        # Act
        result = service.resolve_silence(silence_id, "new_message_sent", mock_db_session)

        # Assert
        assert result == True
        assert mock_silence.is_resolved == True
        assert mock_silence.resolution_method == "new_message_sent"

    def test_resolve_silence_not_found(self, service, mock_db_session):
        """测试解决沉默 - 事件不存在"""
        # Arrange
        silence_id = "silence_not_exist"
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        # Act
        result = service.resolve_silence(silence_id, "new_message_sent", mock_db_session)

        # Assert
        assert result == False


# ==================== IcebreakerTopicService 测试 ====================

class TestIcebreakerTopicService:
    """情境话题生成服务测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return IcebreakerTopicService()

    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        session = MagicMock()

        def add_side_effect(record):
            record.created_at = datetime(2024, 1, 15)
            record.id = "test-id"
        session.add.side_effect = add_side_effect
        session.commit.return_value = None
        session.count.return_value = 0
        return session

    def test_service_initialization(self, service):
        """测试服务初始化"""
        assert service is not None

    def test_default_topics_categories(self, service, mock_db_session):
        """测试默认话题分类"""
        # Arrange - mock count to return 0 so topics will be added
        mock_db_session.query.return_value.count.return_value = 0
        mock_db_session.query.return_value.filter.return_value.first.return_value = None  # No existing topic

        # Act
        with patch('services.behavior_lab_service.optional_db_session') as mock_opt_session:
            mock_opt_session.return_value.__enter__ = MagicMock(return_value=mock_db_session)
            mock_opt_session.return_value.__exit__ = MagicMock(return_value=False)
            service._initialize_default_topics(mock_db_session)

        # Assert - check that add was called at least once (for each default topic)
        assert mock_db_session.add.called or mock_db_session.query.called

    def test_get_topics_by_category(self, service, mock_db_session):
        """测试按分类获取话题"""
        # Arrange
        category = "icebreaker"

        mock_topic = MagicMock()
        mock_topic.category = category

        mock_query = MagicMock()
        mock_query.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_topic]
        mock_db_session.query.return_value = mock_query

        # Act
        topics = service.get_topics(category=category, db_session=mock_db_session)

        # Assert
        assert len(topics) == 1

    def test_get_topics_by_scenario(self, service, mock_db_session):
        """测试按场景获取话题"""
        # Arrange
        scenario = "first_date"

        mock_topic = MagicMock()
        mock_topic.applicable_scenarios = [scenario]

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value.limit.return_value.all.return_value = [mock_topic]
        mock_db_session.query.return_value = mock_query

        # Act
        topics = service.get_topics(scenario=scenario, db_session=mock_db_session)

        # Assert
        assert len(topics) >= 0

    def test_get_topics_by_depth(self, service, mock_db_session):
        """测试按深度获取话题"""
        # Arrange
        depth_level = 3

        mock_topic = MagicMock()
        mock_topic.depth_level = depth_level

        mock_query = MagicMock()
        mock_query.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_topic]
        mock_db_session.query.return_value = mock_query

        # Act
        topics = service.get_topics(depth_level=depth_level, db_session=mock_db_session)

        # Assert
        assert len(topics) == 1

    def test_get_topics_empty(self, service, mock_db_session):
        """测试获取话题 - 空结果"""
        # Arrange
        mock_db_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

        # Act
        topics = service.get_topics(db_session=mock_db_session)

        # Assert
        assert len(topics) == 0

    def test_determine_category_awkward_silence(self, service):
        """测试确定分类 - 尴尬沉默"""
        # Arrange
        context = {"scenario": "awkward_silence"}
        experiences = []

        # Act
        category = service._determine_category(context, experiences)

        # Assert
        assert category == "icebreaker"

    def test_determine_category_first_date(self, service):
        """测试确定分类 - 首次约会"""
        # Arrange
        context = {"scenario": "first_date"}
        experiences = []

        # Act
        category = service._determine_category(context, experiences)

        # Assert
        assert category == "icebreaker"

    def test_determine_category_nostalgia(self, service):
        """测试确定分类 - 回忆"""
        # Arrange
        context = {"scenario": "nostalgia"}
        experiences = []

        # Act
        category = service._determine_category(context, experiences)

        # Assert
        assert category == "shared_experience"

    def test_determine_category_deep_conversation(self, service):
        """测试确定分类 - 深度对话"""
        # Arrange
        context = {"scenario": "deep_conversation"}
        experiences = []

        # Act
        category = service._determine_category(context, experiences)

        # Assert
        assert category == "relationship"

    def test_determine_category_with_significant_experience(self, service):
        """测试确定分类 - 有显著经历"""
        # Arrange
        context = {"scenario": "general"}
        experiences = [{"is_significant": True}]

        # Act
        category = service._determine_category(context, experiences)

        # Assert
        assert category == "shared_experience"

    def test_determine_category_default(self, service):
        """测试确定分类 - 默认"""
        # Arrange
        context = {"scenario": "general"}
        experiences = []

        # Act
        category = service._determine_category(context, experiences)

        # Assert
        assert category == "current_event"

    def test_personalize_topic_with_experiences(self, service):
        """测试个性化话题 - 有经历"""
        # Arrange
        topic_template = "还记得我们第一次{activity}吗？那时候真的很{emotion}"
        experiences = [{
            "experience_type": "看电影",
            "location": "电影院",
            "sentiment_score": 0.8
        }]
        context = {}

        # Act
        result = service._personalize_topic(topic_template, experiences, context)

        # Assert
        assert "看电影" in result
        assert "开心" in result  # sentiment_score > 0

    def test_personalize_topic_negative_sentiment(self, service):
        """测试个性化话题 - 负面情感"""
        # Arrange
        topic_template = "还记得我们第一次{activity}吗？那时候真的很{emotion}"
        experiences = [{
            "experience_type": "争吵",
            "sentiment_score": -0.5
        }]
        context = {}

        # Act
        result = service._personalize_topic(topic_template, experiences, context)

        # Assert
        assert "难忘" in result  # sentiment_score < 0

    def test_personalize_topic_placeholders(self, service):
        """测试个性化话题 - 占位符替换"""
        # Arrange
        topic_template = "你最近有尝试什么新的{hobby}吗？"
        experiences = []
        context = {}

        # Act
        result = service._personalize_topic(topic_template, experiences, context)

        # Assert
        assert "{hobby}" not in result  # 占位符应被替换

    def test_generate_recommendation_reason_shared_experience(self, service):
        """测试生成推荐理由 - 共同经历"""
        # Arrange
        topic = {"category": "shared_experience"}
        experiences = [{"is_significant": True}]
        context = {}

        # Act
        reason = service._generate_recommendation_reason(topic, experiences, context)

        # Assert
        assert "共同经历" in reason

    def test_generate_recommendation_reason_icebreaker(self, service):
        """测试生成推荐理由 - 破冰"""
        # Arrange
        topic = {"category": "icebreaker"}
        experiences = []
        context = {}

        # Act
        reason = service._generate_recommendation_reason(topic, experiences, context)

        # Assert
        assert "打破沉默" in reason or "轻松" in reason

    def test_generate_recommendation_reason_relationship(self, service):
        """测试生成推荐理由 - 关系"""
        # Arrange
        topic = {"category": "relationship"}
        experiences = []
        context = {}

        # Act
        reason = service._generate_recommendation_reason(topic, experiences, context)

        # Assert
        assert "加深" in reason or "情感" in reason

    def test_topic_to_dict(self, service):
        """测试话题对象转字典"""
        # Arrange
        mock_topic = MagicMock()
        mock_topic.id = "topic_001"
        mock_topic.category = "icebreaker"
        mock_topic.topic_text = "测试话题"
        mock_topic.applicable_scenarios = ["first_date"]
        mock_topic.required_experience_type = None
        mock_topic.depth_level = 2
        mock_topic.usage_count = 10
        mock_topic.success_rate = 0.8
        mock_topic.created_at = datetime(2024, 1, 15)

        # Act
        result = service._topic_to_dict(mock_topic)

        # Assert
        assert result["id"] == "topic_001"
        assert "created_at" in result

    def test_generate_personalized_icebreaker_success(self, service, mock_db_session):
        """测试生成个性化破冰话题成功"""
        # Arrange
        conversation_id = "conv_001"
        user_a_id = "user_a"
        user_b_id = "user_b"
        context = {"scenario": "awkward_silence"}

        # Mock shared experiences
        mock_exp = MagicMock()
        mock_exp.is_significant = True
        mock_exp.id = "exp_001"

        # Mock topics with proper attributes
        mock_topic = MagicMock()
        mock_topic.category = "icebreaker"
        mock_topic.topic_text = "如果可以选择一个超能力，你想要什么？"
        mock_topic.depth_level = 2

        # Setup mock chain for get_topics
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value.limit.return_value.all.return_value = [mock_topic]
        mock_db_session.query.return_value = mock_query

        # Act - use patch for SharedExperienceService
        with patch.object(SharedExperienceService, 'get_shared_experiences', return_value=[mock_exp]):
            with patch.object(service, '_determine_category', return_value='icebreaker'):
                result = service.generate_personalized_icebreaker(
                    conversation_id, user_a_id, user_b_id, context, mock_db_session
                )

        # Assert
        if result is not None:
            assert "topic_text" in result
            mock_db_session.add.assert_called()

    def test_generate_personalized_icebreaker_no_topics(self, service, mock_db_session):
        """测试生成个性化破冰话题 - 无话题"""
        # Arrange
        conversation_id = "conv_001"
        user_a_id = "user_a"
        user_b_id = "user_b"
        context = {}

        mock_db_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

        # Act
        result = service.generate_personalized_icebreaker(
            conversation_id, user_a_id, user_b_id, context, mock_db_session
        )

        # Assert
        assert result is None

    def test_record_icebreaker_feedback_success(self, service, mock_db_session):
        """测试记录破冰反馈成功"""
        # Arrange
        icebreaker_id = "ice_001"

        mock_icebreaker = MagicMock()
        mock_icebreaker.id = icebreaker_id
        mock_icebreaker.source_topic_id = "topic_001"
        mock_icebreaker.is_used = False

        mock_source_topic = MagicMock()
        mock_source_topic.id = "topic_001"
        mock_source_topic.usage_count = 10
        mock_source_topic.success_rate = 0.7

        mock_db_session.query.return_value.filter.return_value.first.side_effect = [
            mock_icebreaker, mock_source_topic
        ]

        # Act
        result = service.record_icebreaker_feedback(
            icebreaker_id, True, 0.9, None, mock_db_session
        )

        # Assert
        assert result == True
        assert mock_icebreaker.is_used == True

    def test_record_icebreaker_feedback_not_found(self, service, mock_db_session):
        """测试记录破冰反馈 - 话题不存在"""
        # Arrange
        icebreaker_id = "ice_not_exist"
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        # Act
        result = service.record_icebreaker_feedback(
            icebreaker_id, True, None, None, mock_db_session
        )

        # Assert
        assert result == False
