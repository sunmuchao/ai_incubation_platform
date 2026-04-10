"""
AI 约会助手服务单元测试
测试覆盖：智能聊天助手、约会策划、关系咨询、情感分析、恋爱日记
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
import json


class TestChatAssistantService:
    """智能聊天助手服务测试"""

    @pytest.fixture
    def mock_db(self):
        """模拟数据库会话"""
        session = MagicMock()
        session.add.return_value = None
        session.commit.return_value = None
        session.refresh.return_value = None
        return session

    @pytest.fixture
    def service(self, mock_db):
        """创建服务实例"""
        from services.ai_date_assistant_service import ChatAssistantService
        return ChatAssistantService(mock_db)

    def test_service_initialization(self, service, mock_db):
        """测试服务初始化"""
        assert service is not None
        assert service.db == mock_db

    def test_generate_reply_suggestion_tired(self, service, mock_db):
        """测试生成回复建议 - 对方累了"""
        mock_suggestion = MagicMock()
        mock_suggestion.suggestion_type = "reply_suggestion"
        mock_suggestion.tone = "caring"
        mock_db.refresh.return_value = mock_suggestion

        # Mock analyze_text_emotion_sync to avoid LLM API timeout
        with patch('services.ai_date_assistant_service.analyze_text_emotion_sync',
                   return_value={"mood": "neutral", "emotion": "neutral", "is_tired": True}):
            result = service.generate_reply_suggestion(
                user_id="user_001",
                received_message="今天好累啊，工作辛苦了",
                target_user_id="user_002"
            )

        assert result is not None
        assert result.tone == "caring"

    def test_generate_reply_suggestion_positive(self, service, mock_db):
        """测试生成回复建议 - 对方心情好"""
        mock_suggestion = MagicMock()
        mock_suggestion.tone = "cheerful"
        mock_db.refresh.return_value = mock_suggestion

        # Mock analyze_text_emotion_sync to avoid LLM API timeout
        with patch('services.ai_date_assistant_service.analyze_text_emotion_sync',
                   return_value={"mood": "positive", "emotion": "happiness"}):
            result = service.generate_reply_suggestion(
                user_id="user_001",
                received_message="今天好开心，嘻嘻",
                target_user_id="user_002"
            )

        assert result is not None
        assert result.tone == "cheerful"

    def test_generate_reply_suggestion_question(self, service, mock_db):
        """测试生成回复建议 - 对方提问"""
        mock_suggestion = MagicMock()
        mock_suggestion.tone = "thoughtful"
        mock_db.refresh.return_value = mock_suggestion

        # Mock analyze_text_emotion_sync to avoid LLM API timeout
        with patch('services.ai_date_assistant_service.analyze_text_emotion_sync',
                   return_value={"mood": "neutral", "emotion": "neutral"}):
            result = service.generate_reply_suggestion(
                user_id="user_001",
                received_message="你知道为什么吗？",
                target_user_id="user_002"
            )

        assert result is not None
        assert result.tone == "thoughtful"

    def test_generate_reply_suggestion_default(self, service, mock_db):
        """测试生成回复建议 - 默认聊天"""
        mock_suggestion = MagicMock()
        mock_suggestion.tone = "casual"
        mock_db.refresh.return_value = mock_suggestion

        # Mock analyze_text_emotion_sync to avoid LLM API timeout
        with patch('services.ai_date_assistant_service.analyze_text_emotion_sync',
                   return_value={"mood": "neutral", "emotion": "neutral"}):
            # 使用不包含情绪词的测试用例
            result = service.generate_reply_suggestion(
                user_id="user_001",
                received_message="哦哦知道了",
                target_user_id="user_002"
            )

        assert result is not None

    def test_analyze_message_mood_positive(self, service):
        """测试分析消息情绪 - 正向"""
        # Mock analyze_text_emotion_sync to avoid LLM API timeout
        with patch('services.ai_date_assistant_service.analyze_text_emotion_sync',
                   return_value={"mood": "positive", "emotion": "happiness"}):
            result = service._analyze_message_mood("今天好开心，棒棒哒")
        assert result["mood"] == "positive"
        assert result["is_tired"] == False

    def test_analyze_message_mood_negative(self, service):
        """测试分析消息情绪 - 负向"""
        # Mock analyze_text_emotion_sync to avoid LLM API timeout
        with patch('services.ai_date_assistant_service.analyze_text_emotion_sync',
                   return_value={"mood": "negative", "emotion": "sadness"}):
            result = service._analyze_message_mood("今天好难过，伤心")
        assert result["mood"] == "negative"

    def test_analyze_message_mood_tired(self, service):
        """测试分析消息情绪 - 累"""
        # Mock analyze_text_emotion_sync to avoid LLM API timeout
        with patch('services.ai_date_assistant_service.analyze_text_emotion_sync',
                   return_value={"mood": "neutral", "emotion": "neutral", "is_tired": True}):
            result = service._analyze_message_mood("好累啊，想睡觉")
        assert result["is_tired"] == True

    def test_analyze_message_mood_neutral(self, service):
        """测试分析消息情绪 - 中性"""
        # Mock analyze_text_emotion_sync to avoid LLM API timeout
        with patch('services.ai_date_assistant_service.analyze_text_emotion_sync',
                   return_value={"mood": "neutral", "emotion": "neutral"}):
            # 使用不包含情绪词的测试用例（避免"好"字匹配 positive_words）
            result = service._analyze_message_mood("哦哦知道了")
        assert result["mood"] == "neutral"

    def test_analyze_message_intent_question(self, service):
        """测试分析消息意图 - 提问"""
        result = service._analyze_message_intent("你在做什么？")
        assert result["is_question"] == True
        assert result["intent"] == "question"

    def test_analyze_message_intent_sharing(self, service):
        """测试分析消息意图 - 分享"""
        result = service._analyze_message_intent("我今天去了一个好吃的餐厅")
        assert result["is_sharing"] == True
        assert result["intent"] == "sharing"

    def test_analyze_message_intent_chat(self, service):
        """测试分析消息意图 - 聊天"""
        result = service._analyze_message_intent("你好")
        assert result["is_question"] == False
        assert result["is_sharing"] == False
        assert result["intent"] == "chat"

    def test_generate_reply_suggestions_tired(self, service):
        """测试生成回复建议 - 累了"""
        mood = {"is_tired": True, "mood": "neutral"}
        intent = {"is_question": False, "is_sharing": False, "intent": "chat"}
        primary, alternatives = service._generate_reply_suggestions("好累", mood, intent, None)
        assert len(primary) > 0
        assert len(alternatives) > 0

    def test_generate_reply_suggestions_positive(self, service):
        """测试生成回复建议 - 心情好"""
        mood = {"is_tired": False, "mood": "positive"}
        intent = {"is_question": False, "is_sharing": False, "intent": "chat"}
        primary, alternatives = service._generate_reply_suggestions("好开心", mood, intent, None)
        assert len(primary) > 0
        assert len(alternatives) > 0

    def test_generate_topics_from_interests(self, service, mock_db):
        """测试基于兴趣生成话题"""
        user = MagicMock()
        target_user = MagicMock()

        topics = service._generate_topics_from_interests(user, target_user)

        assert len(topics) > 0
        assert all("text" in t and "reasoning" in t for t in topics)

    def test_analyze_and_suggest_emoji(self, service):
        """测试推荐表情符号"""
        result = service._analyze_and_suggest_emoji("今天好开心")
        assert "primary" in result
        assert "alternatives" in result
        assert isinstance(result["alternatives"], list)

    def test_suggest_tone_caring(self, service):
        """测试建议语气 - 关心"""
        mood = {"is_tired": True}
        intent = {}
        assert service._suggest_tone(mood, intent) == "caring"

    def test_suggest_tone_cheerful(self, service):
        """测试建议语气 - 愉快"""
        mood = {"mood": "positive"}
        intent = {}
        assert service._suggest_tone(mood, intent) == "cheerful"

    def test_suggest_tone_thoughtful(self, service):
        """测试建议语气 - 思考"""
        mood = {}
        intent = {"is_question": True}
        assert service._suggest_tone(mood, intent) == "thoughtful"

    def test_suggest_tone_casual(self, service):
        """测试建议语气 - 随意"""
        mood = {}
        intent = {}
        assert service._suggest_tone(mood, intent) == "casual"

    def test_generate_reasoning_tired(self, service):
        """测试生成推荐理由 - 累了"""
        mood = {"is_tired": True}
        intent = {}
        reasoning = service._generate_reasoning(mood, intent)
        assert len(reasoning) > 0

    def test_mark_as_used_success(self, service, mock_db):
        """测试标记建议已使用 - 成功"""
        mock_suggestion = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_suggestion

        result = service.mark_as_used("suggestion_001", "修改后的文本", 5)

        assert result == True
        assert mock_suggestion.status == "used"

    def test_mark_as_used_not_found(self, service, mock_db):
        """测试标记建议已使用 - 未找到"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = service.mark_as_used("nonexistent_id")

        assert result == False

    def test_recommend_topics_success(self, service, mock_db):
        """测试推荐话题成功"""
        mock_user = MagicMock()
        mock_db.query.return_value.filter.return_value.first.side_effect = [mock_user, mock_user]

        result = service.recommend_topics("user_001", "user_002")

        assert isinstance(result, list)

    def test_recommend_topics_user_not_found(self, service, mock_db):
        """测试推荐话题 - 用户不存在"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = service.recommend_topics("user_001", "user_002")

        assert result == []


class TestDatePlanningService:
    """约会策划服务测试"""

    @pytest.fixture
    def mock_db(self):
        """模拟数据库会话"""
        session = MagicMock()
        session.add.return_value = None
        session.commit.return_value = None
        session.refresh.return_value = None
        return session

    @pytest.fixture
    def service(self, mock_db):
        """创建服务实例"""
        from services.ai_date_assistant_service import DatePlanningService
        return DatePlanningService(mock_db)

    def test_service_initialization(self, service, mock_db):
        """测试服务初始化"""
        assert service is not None
        assert service.db == mock_db

    def test_create_date_plan_first_date(self, service, mock_db):
        """测试创建约会计划 - 首次约会"""
        mock_plan = MagicMock()
        mock_plan.plan_type = "first_date"
        mock_plan.title = "首次约会计划"
        mock_db.refresh.return_value = mock_plan

        result = service.create_date_plan(
            user_id="user_001",
            partner_user_id="user_002",
            plan_type="first_date"
        )

        assert result is not None
        assert result.plan_type == "first_date"

    def test_create_date_plan_anniversary(self, service, mock_db):
        """测试创建约会计划 - 纪念日"""
        mock_plan = MagicMock()
        mock_plan.plan_type = "anniversary"
        mock_plan.title = "纪念日庆祝计划"
        mock_db.refresh.return_value = mock_plan

        result = service.create_date_plan(
            user_id="user_001",
            partner_user_id="user_002",
            plan_type="anniversary"
        )

        assert result is not None

    def test_create_date_plan_weekend(self, service, mock_db):
        """测试创建约会计划 - 周末"""
        mock_plan = MagicMock()
        mock_plan.plan_type = "weekend_date"
        mock_db.refresh.return_value = mock_plan

        result = service.create_date_plan(
            user_id="user_001",
            partner_user_id="user_002",
            plan_type="weekend_date"
        )

        assert result is not None

    def test_recommend_venues_basic(self, service, mock_db):
        """测试推荐地点 - 基础"""
        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

        result = service.recommend_venues("北京市")

        assert isinstance(result, list)

    def test_get_venue_detail_found(self, service, mock_db):
        """测试获取地点详情 - 找到"""
        mock_venue = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_venue

        result = service.get_venue_detail("venue_001")

        assert result is not None

    def test_get_venue_detail_not_found(self, service, mock_db):
        """测试获取地点详情 - 未找到"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = service.get_venue_detail("nonexistent_venue")

        assert result is None

    def test_accept_plan_success(self, service, mock_db):
        """测试接受计划成功"""
        mock_plan = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_plan

        result = service.accept_plan("plan_001", "user_001")

        assert result == True

    def test_accept_plan_not_found(self, service, mock_db):
        """测试接受计划 - 未找到"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = service.accept_plan("nonexistent_plan", "user_001")

        assert result == False

    def test_complete_plan_success(self, service, mock_db):
        """测试完成计划成功"""
        mock_plan = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_plan

        result = service.complete_plan("plan_001", rating=5, feedback="很好的约会")

        assert result == True
        assert mock_plan.status == "completed"

    def test_complete_plan_not_found(self, service, mock_db):
        """测试完成计划 - 未找到"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = service.complete_plan("nonexistent_plan")

        assert result == False

    def test_generate_date_plan_first_date(self, service):
        """测试生成约会计划内容 - 首次约会"""
        result = service._generate_date_plan("first_date", "u1", "u2", {})
        assert "title" in result
        assert "activities" in result


class TestRelationshipConsultantService:
    """关系咨询服务测试"""

    @pytest.fixture
    def mock_db(self):
        """模拟数据库会话"""
        session = MagicMock()
        session.add.return_value = None
        session.commit.return_value = None
        session.refresh.return_value = None
        return session

    @pytest.fixture
    def service(self, mock_db):
        """创建服务实例"""
        from services.ai_date_assistant_service import RelationshipConsultantService
        return RelationshipConsultantService(mock_db)

    def test_service_initialization(self, service, mock_db):
        """测试服务初始化"""
        assert service is not None
        assert service.db == mock_db

    def test_consult_relationship_confusion(self, service, mock_db):
        """测试咨询 - 关系困惑"""
        mock_consultation = MagicMock()
        mock_consultation.consult_type = "relationship_confusion"
        mock_db.refresh.return_value = mock_consultation

        result = service.consult(
            user_id="user_001",
            question="他到底喜不喜欢我？",
            consult_type="relationship_confusion"
        )

        assert result is not None

    def test_consult_conflict_resolution(self, service, mock_db):
        """测试咨询 - 冲突解决"""
        mock_consultation = MagicMock()
        mock_db.refresh.return_value = mock_consultation

        result = service.consult(
            user_id="user_001",
            question="我们经常吵架怎么办？",
            consult_type="conflict_resolution"
        )

        assert result is not None

    def test_get_faq_basic(self, service, mock_db):
        """测试获取 FAQ - 基础"""
        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

        result = service.get_faq()

        assert isinstance(result, list)

    def test_mark_faq_helpful_true(self, service, mock_db):
        """测试标记 FAQ 有用 - 是"""
        mock_faq = MagicMock()
        mock_faq.helpful_count = 0
        mock_db.query.return_value.filter.return_value.first.return_value = mock_faq

        result = service.mark_faq_helpful("faq_001", is_helpful=True)

        assert result == True
        assert mock_faq.helpful_count == 1

    def test_mark_faq_helpful_not_found(self, service, mock_db):
        """测试标记 FAQ 有用 - 未找到"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = service.mark_faq_helpful("nonexistent_faq", is_helpful=True)

        assert result == False


class TestEmotionAnalyzerService:
    """情感分析服务测试"""

    @pytest.fixture
    def mock_db(self):
        """模拟数据库会话"""
        session = MagicMock()
        session.add.return_value = None
        session.commit.return_value = None
        session.refresh.return_value = None
        return session

    @pytest.fixture
    def service(self, mock_db):
        """创建服务实例"""
        from services.ai_date_assistant_service import EmotionAnalyzerService
        return EmotionAnalyzerService(mock_db)

    def test_service_initialization(self, service, mock_db):
        """测试服务初始化"""
        assert service is not None
        assert service.db == mock_db

    def test_analyze_conversation_success(self, service, mock_db):
        """测试分析聊天记录成功"""
        mock_analysis = MagicMock()
        mock_analysis.sentiment_label = "positive"
        mock_db.refresh.return_value = mock_analysis

        # Patch EmotionAnalysisDB to avoid initialization issues
        with patch('services.ai_date_assistant_service.EmotionAnalysisDB') as mock_cls:
            mock_cls.return_value = mock_analysis

            result = service.analyze_conversation(
                user_id="user_001",
                partner_user_id="user_002",
                analysis_type="full"
            )

            assert result is not None

    def test_get_sentiment_trend_success(self, service, mock_db):
        """测试获取情感趋势成功"""
        # Setup mock query chain that returns empty list
        mock_query = MagicMock()
        mock_query.filter.return_value.order_by.return_value.all.return_value = []
        mock_db.query.return_value = mock_query

        result = service.get_sentiment_trend("user_001", "user_002", days=7)

        assert isinstance(result, list)

    def test_get_compatibility_score_success(self, service, mock_db):
        """测试获取匹配度评分成功"""
        mock_analysis = MagicMock()
        mock_analysis.compatibility_score = 85.0

        # Setup mock query chain
        mock_query = MagicMock()
        mock_query.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_analysis]
        mock_db.query.return_value = mock_query

        result = service.get_compatibility_score("user_001", "user_002")

        assert isinstance(result, float)

    def test_get_compatibility_score_no_data(self, service, mock_db):
        """测试获取匹配度评分 - 无数据"""
        # Setup mock query chain
        mock_query = MagicMock()
        mock_query.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        mock_db.query.return_value = mock_query

        result = service.get_compatibility_score("user_001", "user_002")

        assert result == 0.0

    def test_perform_emotion_analysis(self, service):
        """测试执行情感分析"""
        result = service._perform_emotion_analysis("full")

        assert "sentiment_score" in result
        assert "sentiment_label" in result


class TestLoveDiaryService:
    """恋爱日记服务测试"""

    @pytest.fixture
    def mock_db(self):
        """模拟数据库会话"""
        session = MagicMock()
        session.add.return_value = None
        session.commit.return_value = None
        session.refresh.return_value = None
        return session

    @pytest.fixture
    def service(self, mock_db):
        """创建服务实例"""
        from services.ai_date_assistant_service import LoveDiaryService
        return LoveDiaryService(mock_db)

    def test_service_initialization(self, service, mock_db):
        """测试服务初始化"""
        assert service is not None
        assert service.db == mock_db

    def test_create_entry_success(self, service, mock_db):
        """测试创建日记成功"""
        mock_entry = MagicMock()
        mock_entry.title = "今天的约会"
        mock_db.refresh.return_value = mock_entry

        result = service.create_entry(
            user_id="user_001",
            title="今天的约会",
            content="今天和他去了一家很好吃的餐厅",
            entry_type="manual_entry",
            mood="happy"
        )

        assert result is not None
        assert result.title == "今天的约会"

    def test_get_entries_basic(self, service, mock_db):
        """测试获取日记列表 - 基础"""
        mock_db.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []

        result = service.get_entries("user_001")

        assert isinstance(result, list)

    def test_get_timeline_success(self, service, mock_db):
        """测试获取时间线成功"""
        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

        result = service.get_timeline("user_001", "user_002")

        assert isinstance(result, list)

    def test_add_timeline_event_success(self, service, mock_db):
        """测试添加时间线事件成功"""
        mock_event = MagicMock()
        mock_event.is_milestone = True
        mock_db.refresh.return_value = mock_event

        result = service.add_timeline_event(
            user_id_1="user_001",
            user_id_2="user_002",
            event_type="first_date",
            title="第一次约会",
            event_date=datetime.now(),
            is_milestone=True
        )

        assert result is not None
        assert result.is_milestone == True

    def test_create_memory_success(self, service, mock_db):
        """测试创建回忆成功"""
        mock_memory = MagicMock()
        mock_db.refresh.return_value = mock_memory

        result = service.create_memory(
            user_id="user_001",
            memory_type="special_day",
            title="特别的纪念日",
            description="难忘的一天",
            memory_date=datetime.now(),
            emotion="happy"
        )

        assert result is not None

    def test_share_entry_success(self, service, mock_db):
        """测试分享日记成功"""
        mock_entry = MagicMock()
        mock_entry.is_private = False
        mock_db.query.return_value.filter.return_value.first.return_value = mock_entry

        result = service.share_entry("entry_001", "user_001")

        assert result == True

    def test_share_entry_private(self, service, mock_db):
        """测试分享日记 - 私密"""
        mock_entry = MagicMock()
        mock_entry.is_private = True
        mock_db.query.return_value.filter.return_value.first.return_value = mock_entry

        result = service.share_entry("entry_001", "user_001")

        assert result == False

    def test_share_entry_not_found(self, service, mock_db):
        """测试分享日记 - 未找到"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = service.share_entry("nonexistent_entry", "user_001")

        assert result == False
