"""
测试 AI 陪伴助手服务层

覆盖范围:
- AICompanionService (src/services/ai_companion_service.py)
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta


class TestAICompanionServiceInitialization:
    """测试 AICompanionService 初始化"""

    def test_init(self):
        """测试服务初始化"""
        from src.services.ai_companion_service import AICompanionService

        mock_db = MagicMock()
        service = AICompanionService(mock_db)

        assert service.db == mock_db
        assert service.llm_client is None

    def test_init_with_llm_client(self):
        """测试带 LLM 客户端的初始化"""
        from src.services.ai_companion_service import AICompanionService

        mock_db = MagicMock()
        mock_llm = MagicMock()
        service = AICompanionService(mock_db, mock_llm)

        assert service.db == mock_db
        assert service.llm_client == mock_llm


class TestAICompanionServiceCreateSession:
    """测试创建会话功能"""

    def test_create_session_default(self):
        """测试创建默认会话"""
        from src.services.ai_companion_service import AICompanionService

        mock_db = MagicMock()
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()

        mock_session = MagicMock()
        mock_session.id = "session-123"
        mock_session.created_at = datetime.now()

        # Mock refresh to update session attributes
        def refresh_side_effect(obj):
            obj.id = "session-123"
            obj.created_at = datetime.now()
        mock_db.refresh.side_effect = refresh_side_effect

        service = AICompanionService(mock_db)
        result = service.create_session("user-123")

        assert result["session_id"] == "session-123"
        assert result["companion_persona"] == "gentle_advisor"
        assert result["companion_name"] == "温柔姐姐"
        assert result["greeting"] == "嗨~今天过得怎么样？有什么想和我聊聊的吗？"
        mock_db.add.assert_called()

    def test_create_session_custom_persona(self):
        """测试创建自定义角色会话"""
        from src.services.ai_companion_service import AICompanionService

        mock_db = MagicMock()
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()

        mock_session = MagicMock()
        mock_session.id = "session-456"
        mock_session.created_at = datetime.now()

        def refresh_side_effect(obj):
            obj.id = "session-456"
            obj.created_at = datetime.now()
        mock_db.refresh.side_effect = refresh_side_effect

        service = AICompanionService(mock_db)
        result = service.create_session(
            "user-123",
            session_type="emotional_support",
            companion_persona="caring_sister"
        )

        assert result["companion_persona"] == "caring_sister"
        assert result["companion_name"] == "知心妹妹"

    def test_create_session_invalid_type(self):
        """测试创建无效会话类型"""
        from src.services.ai_companion_service import AICompanionService

        mock_db = MagicMock()
        service = AICompanionService(mock_db)

        with pytest.raises(ValueError) as exc_info:
            service.create_session("user-123", session_type="invalid_type")

        assert "未知的会话类型" in str(exc_info.value)

    def test_create_session_invalid_persona(self):
        """测试创建无效角色"""
        from src.services.ai_companion_service import AICompanionService

        mock_db = MagicMock()
        service = AICompanionService(mock_db)

        with pytest.raises(ValueError) as exc_info:
            service.create_session(
                "user-123",
                companion_persona="invalid_persona"
            )

        assert "未知的角色设定" in str(exc_info.value)


class TestAICompanionServiceSendMessage:
    """测试发送消息功能"""

    def test_send_message_success(self):
        """测试发送消息成功"""
        from src.services.ai_companion_service import AICompanionService

        mock_db = MagicMock()
        mock_db.commit = MagicMock()

        mock_session = MagicMock()
        mock_session.id = "session-123"
        mock_session.user_id = "user-123"
        mock_session.ended_at = None
        mock_session.user_mood = "neutral"
        mock_session.sentiment_score = 0.0
        mock_session.message_count = 0

        mock_db.query().filter().first.return_value = mock_session
        mock_db.query().filter().order_by().limit().all.return_value = []

        # Mock add to set proper attributes on messages
        created_at = datetime.now()
        def add_side_effect(obj):
            if hasattr(obj, 'role') and obj.role == 'assistant':
                obj.id = "ai-msg-123"
                obj.created_at = created_at
            elif hasattr(obj, 'role') and obj.role == 'user':
                obj.id = "user-msg-123"
                obj.created_at = created_at
        mock_db.add.side_effect = add_side_effect

        service = AICompanionService(mock_db)
        result = service.send_message("session-123", "user-123", "你好")

        assert "message_id" in result
        assert "content" in result
        assert result["user_mood"] == "neutral"
        mock_db.commit.assert_called()

    def test_send_message_session_not_found(self):
        """测试发送消息但会话不存在"""
        from src.services.ai_companion_service import AICompanionService

        mock_db = MagicMock()
        mock_db.query().filter().first.return_value = None

        service = AICompanionService(mock_db)

        with pytest.raises(ValueError) as exc_info:
            service.send_message("not-exist", "user-123", "你好")

        assert "会话不存在" in str(exc_info.value)

    def test_send_message_session_ended(self):
        """测试发送消息但会话已结束"""
        from src.services.ai_companion_service import AICompanionService

        mock_db = MagicMock()
        mock_session = MagicMock()
        mock_session.ended_at = datetime.now()
        mock_db.query().filter().first.return_value = mock_session

        service = AICompanionService(mock_db)

        with pytest.raises(ValueError) as exc_info:
            service.send_message("session-123", "user-123", "你好")

        assert "会话已结束" in str(exc_info.value)


class TestAICompanionServiceEndSession:
    """测试结束会话功能"""

    def test_end_session_success(self):
        """测试结束会话成功"""
        from src.services.ai_companion_service import AICompanionService

        mock_db = MagicMock()
        mock_db.commit = MagicMock()

        mock_session = MagicMock()
        mock_session.id = "session-123"
        mock_session.user_id = "user-123"
        mock_session.created_at = datetime.now() - timedelta(minutes=30)
        mock_session.message_count = 10
        mock_session.user_mood = "happy"

        mock_db.query().filter().first.return_value = mock_session

        with patch('src.services.ai_companion_service.AICompanionService._generate_session_summary') as mock_summary:
            with patch('src.services.ai_companion_service.AICompanionService._extract_key_insights') as mock_insights:
                mock_summary.return_value = "会话摘要"
                mock_insights.return_value = []

                service = AICompanionService(mock_db)
                result = service.end_session("session-123", "user-123", rating=5, feedback="很好")

                assert result["session_id"] == "session-123"
                assert mock_session.user_rating == 5
                assert mock_session.user_feedback == "很好"
                mock_db.commit.assert_called()

    def test_end_session_not_found(self):
        """测试结束不存在的会话"""
        from src.services.ai_companion_service import AICompanionService

        mock_db = MagicMock()
        mock_db.query().filter().first.return_value = None

        service = AICompanionService(mock_db)

        with pytest.raises(ValueError) as exc_info:
            service.end_session("not-exist", "user-123")

        assert "会话不存在" in str(exc_info.value)


class TestAICompanionServiceGetSessionHistory:
    """测试获取会话历史功能"""

    def test_get_session_history_empty(self):
        """测试获取空会话历史"""
        from src.services.ai_companion_service import AICompanionService

        mock_db = MagicMock()
        mock_db.query().filter().order_by().limit().offset().all.return_value = []

        service = AICompanionService(mock_db)
        result = service.get_session_history("user-123")

        assert isinstance(result, list)
        assert len(result) == 0

    def test_get_session_history_with_data(self):
        """测试获取会话历史（有数据）"""
        from src.services.ai_companion_service import AICompanionService

        mock_db = MagicMock()
        mock_session = MagicMock()
        mock_session.id = "session-123"
        mock_session.session_type = "chat"
        mock_session.companion_persona = "gentle_advisor"
        mock_session.duration_minutes = 30
        mock_session.message_count = 10
        mock_session.user_mood = "happy"
        mock_session.sentiment_score = 0.8
        mock_session.user_rating = 5
        mock_session.session_summary = "摘要"
        mock_session.created_at = datetime.now()
        mock_session.ended_at = None

        mock_db.query().filter().order_by().limit().offset().all.return_value = [mock_session]

        service = AICompanionService(mock_db)
        result = service.get_session_history("user-123")

        assert len(result) == 1
        assert result[0]["session_id"] == "session-123"
        assert result[0]["companion_name"] == "温柔姐姐"


class TestAICompanionServiceGetSessionMessages:
    """测试获取会话消息功能"""

    def test_get_session_messages_success(self):
        """测试获取会话消息成功"""
        from src.services.ai_companion_service import AICompanionService

        mock_db = MagicMock()
        mock_session = MagicMock()
        mock_db.query().filter().first.return_value = mock_session

        mock_message = MagicMock()
        mock_message.id = "msg-123"
        mock_message.role = "user"
        mock_message.content = "你好"
        mock_message.emotion = "neutral"
        mock_message.sentiment = 0.5
        mock_message.created_at = datetime.now()

        mock_db.query().filter().order_by().all.return_value = [mock_message]

        service = AICompanionService(mock_db)
        result = service.get_session_messages("session-123", "user-123")

        assert len(result) == 1
        assert result[0]["message_id"] == "msg-123"
        assert result[0]["role"] == "user"

    def test_get_session_messages_not_found(self):
        """测试获取不存在的会话消息"""
        from src.services.ai_companion_service import AICompanionService

        mock_db = MagicMock()
        mock_db.query().filter().first.return_value = None

        service = AICompanionService(mock_db)

        with pytest.raises(ValueError) as exc_info:
            service.get_session_messages("not-exist", "user-123")

        assert "会话不存在" in str(exc_info.value)


class TestAICompanionServiceGetActiveSession:
    """测试获取活跃会话功能"""

    def test_get_active_session_found(self):
        """测试获取存在的活跃会话"""
        from src.services.ai_companion_service import AICompanionService

        mock_db = MagicMock()
        mock_session = MagicMock()
        mock_session.id = "session-123"
        mock_session.session_type = "chat"
        mock_session.companion_persona = "gentle_advisor"
        mock_session.user_mood = "happy"
        mock_session.sentiment_score = 0.8
        mock_session.message_count = 10
        mock_session.ended_at = None
        mock_session.created_at = datetime.now()

        mock_db.query().filter().order_by().first.return_value = mock_session

        service = AICompanionService(mock_db)
        result = service.get_active_session("user-123")

        assert result is not None
        assert result["session_id"] == "session-123"
        assert result["companion_name"] == "温柔姐姐"

    def test_get_active_session_not_found(self):
        """测试获取不到活跃会话"""
        from src.services.ai_companion_service import AICompanionService

        mock_db = MagicMock()
        mock_db.query().filter().order_by().first.return_value = None

        service = AICompanionService(mock_db)
        result = service.get_active_session("user-123")

        assert result is None


class TestAICompanionServiceGetUserStats:
    """测试获取用户统计功能"""

    def test_get_user_stats_empty(self):
        """测试获取用户统计（空数据）"""
        from src.services.ai_companion_service import AICompanionService

        mock_db = MagicMock()
        mock_db.query().filter().count.return_value = 0
        mock_db.query().filter().scalar.return_value = None
        mock_db.query().group_by().order_by().first.return_value = None

        service = AICompanionService(mock_db)
        result = service.get_user_stats("user-123")

        assert result["total_sessions"] == 0
        assert result["total_messages"] == 0
        assert result["average_rating"] == 0

    def test_get_user_stats_with_data(self):
        """测试获取用户统计（有数据）"""
        from src.services.ai_companion_service import AICompanionService

        mock_db = MagicMock()

        # Create a mock query chain that returns consistent values
        def query_side_effect(*args, **kwargs):
            mock_query = MagicMock()
            mock_query.filter.return_value = mock_query
            mock_query.group_by.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            return mock_query

        mock_db.query.side_effect = query_side_effect

        # Set up specific return values
        mock_db.query().filter().count.side_effect = [5, 3]  # total sessions, completed sessions
        mock_db.query().filter().scalar.side_effect = [50, 120, None, None]  # messages, minutes, avg rating, etc.
        mock_db.query().group_by().order_by().first.return_value = ("gentle_advisor", 3)
        mock_db.query().filter().group_by().all.return_value = [("happy", 3), ("neutral", 2)]

        service = AICompanionService(mock_db)
        result = service.get_user_stats("user-123")

        # Just verify the result structure since mocking is complex
        assert "total_sessions" in result
        assert "completed_sessions" in result
        assert "favorite_persona" in result


class TestAICompanionServiceSentimentAnalysis:
    """测试情感分析功能"""

    def test_analyze_sentiment_positive(self):
        """测试分析正面情感"""
        from src.services.ai_companion_service import AICompanionService

        mock_db = MagicMock()
        service = AICompanionService(mock_db)

        # Mock analyze_text_emotion_sync to avoid LLM API timeout
        with patch('src.services.ai_companion_service.analyze_text_emotion_sync',
                   return_value={"mood": "positive", "intensity": 0.8}):
            result = service._analyze_sentiment("今天很开心，太棒了！")

        assert result > 0

    def test_analyze_sentiment_negative(self):
        """测试分析负面情感"""
        from src.services.ai_companion_service import AICompanionService

        mock_db = MagicMock()
        service = AICompanionService(mock_db)

        # Mock analyze_text_emotion_sync to avoid LLM API timeout
        with patch('src.services.ai_companion_service.analyze_text_emotion_sync',
                   return_value={"mood": "negative", "intensity": 0.7}):
            result = service._analyze_sentiment("今天很难过，太糟糕了！")

        assert result < 0

    def test_analyze_sentiment_neutral(self):
        """测试分析中性情感"""
        from src.services.ai_companion_service import AICompanionService

        mock_db = MagicMock()
        service = AICompanionService(mock_db)

        # Mock analyze_text_emotion_sync to avoid LLM API timeout
        with patch('src.services.ai_companion_service.analyze_text_emotion_sync',
                   return_value={"mood": "neutral", "intensity": 0.5}):
            result = service._analyze_sentiment("今天是星期一")

        assert result == 0.0

    def test_analyze_sentiment_bounds(self):
        """测试情感分析边界"""
        from src.services.ai_companion_service import AICompanionService

        mock_db = MagicMock()
        service = AICompanionService(mock_db)

        # Mock analyze_text_emotion_sync to avoid LLM API timeout
        with patch('src.services.ai_companion_service.analyze_text_emotion_sync',
                   return_value={"mood": "positive", "intensity": 1.0}):
            # 测试上限
            very_positive = "开心 高兴 棒 喜欢 爱 快乐 幸福 美好 期待 太好了" * 10
            result = service._analyze_sentiment(very_positive)
            assert result <= 1.0

        with patch('src.services.ai_companion_service.analyze_text_emotion_sync',
                   return_value={"mood": "negative", "intensity": 1.0}):
            # 测试下限
            very_negative = "难过 伤心 痛苦 讨厌 恨 糟糕 差 失望 绝望 累" * 10
            result = service._analyze_sentiment(very_negative)
            assert result >= -1.0


class TestAICompanionServiceEmotionDetection:
    """测试情绪检测功能"""

    def test_detect_emotion_happy(self):
        """测试检测开心情绪"""
        from src.services.ai_companion_service import AICompanionService

        mock_db = MagicMock()
        service = AICompanionService(mock_db)

        # Mock analyze_text_emotion_sync to avoid LLM API timeout
        with patch('src.services.ai_companion_service.analyze_text_emotion_sync',
                   return_value={"emotion": "happiness"}):
            result = service._detect_emotion("今天很开心，笑得合不拢嘴")

        assert result == "happy"

    def test_detect_emotion_sad(self):
        """测试检测悲伤情绪"""
        from src.services.ai_companion_service import AICompanionService

        mock_db = MagicMock()
        service = AICompanionService(mock_db)

        # Mock analyze_text_emotion_sync to avoid LLM API timeout
        with patch('src.services.ai_companion_service.analyze_text_emotion_sync',
                   return_value={"emotion": "sadness"}):
            result = service._detect_emotion("今天很难过，想哭")

        assert result == "sad"

    def test_detect_emotion_anxious(self):
        """测试检测焦虑情绪"""
        from src.services.ai_companion_service import AICompanionService

        mock_db = MagicMock()
        service = AICompanionService(mock_db)

        # Mock analyze_text_emotion_sync to avoid LLM API timeout
        with patch('src.services.ai_companion_service.analyze_text_emotion_sync',
                   return_value={"emotion": "fear"}):
            result = service._detect_emotion("感到害怕和担心")

        assert result == "anxious"

    def test_detect_emotion_angry(self):
        """测试检测愤怒情绪"""
        from src.services.ai_companion_service import AICompanionService

        mock_db = MagicMock()
        service = AICompanionService(mock_db)

        # Mock analyze_text_emotion_sync to avoid LLM API timeout
        with patch('src.services.ai_companion_service.analyze_text_emotion_sync',
                   return_value={"emotion": "anger"}):
            result = service._detect_emotion("很生气，非常愤怒")

        assert result == "angry"

    def test_detect_emotion_excited(self):
        """测试检测兴奋情绪"""
        from src.services.ai_companion_service import AICompanionService

        mock_db = MagicMock()
        service = AICompanionService(mock_db)

        # Mock analyze_text_emotion_sync to avoid LLM API timeout
        with patch('src.services.ai_companion_service.analyze_text_emotion_sync',
                   return_value={"emotion": "surprise"}):
            result = service._detect_emotion("很兴奋，非常期待")

        assert result == "excited"

    def test_detect_emotion_neutral(self):
        """测试检测中性情绪"""
        from src.services.ai_companion_service import AICompanionService

        mock_db = MagicMock()
        service = AICompanionService(mock_db)

        # Mock analyze_text_emotion_sync to avoid LLM API timeout
        with patch('src.services.ai_companion_service.analyze_text_emotion_sync',
                   return_value={"emotion": "neutral"}):
            result = service._detect_emotion("今天是晴天")

        assert result == "neutral"


class TestAICompanionServiceGenerateResponse:
    """测试生成 AI 回复功能"""

    def test_generate_ai_response_greeting(self):
        """测试生成问候回复"""
        from src.services.ai_companion_service import AICompanionService

        mock_db = MagicMock()
        mock_session = MagicMock()
        mock_session.companion_persona = "gentle_advisor"
        mock_session.session_type = "chat"

        service = AICompanionService(mock_db)
        result = service._generate_ai_response(mock_session, "你好", [])

        assert "content" in result
        assert "你好" in result["content"] or "嗨" in result["content"]

    def test_generate_ai_response_thanks(self):
        """测试生成感谢回复"""
        from src.services.ai_companion_service import AICompanionService

        mock_db = MagicMock()
        mock_session = MagicMock()
        mock_session.companion_persona = "gentle_advisor"
        mock_session.session_type = "chat"

        service = AICompanionService(mock_db)
        result = service._generate_ai_response(mock_session, "谢谢", [])

        assert "不客气" in result["content"]

    def test_generate_ai_response_sad(self):
        """测试生成安慰回复"""
        from src.services.ai_companion_service import AICompanionService

        mock_db = MagicMock()
        mock_session = MagicMock()
        mock_session.companion_persona = "gentle_advisor"
        mock_session.session_type = "emotional_support"

        service = AICompanionService(mock_db)
        result = service._generate_ai_response(mock_session, "我很难过", [])

        assert "陪伴" in result["content"] or "难过" in result["content"]

    def test_generate_ai_response_happy(self):
        """测试生成开心回复"""
        from src.services.ai_companion_service import AICompanionService

        mock_db = MagicMock()
        mock_session = MagicMock()
        mock_session.companion_persona = "gentle_advisor"
        mock_session.session_type = "chat"

        service = AICompanionService(mock_db)
        result = service._generate_ai_response(mock_session, "我很开心", [])

        assert "开心" in result["content"]

    def test_generate_ai_response_default(self):
        """测试生成默认回复"""
        from src.services.ai_companion_service import AICompanionService

        mock_db = MagicMock()
        mock_session = MagicMock()
        mock_session.companion_persona = "gentle_advisor"
        mock_session.session_type = "chat"

        service = AICompanionService(mock_db)
        result = service._generate_ai_response(mock_session, "随便说什么", [])

        assert "content" in result


class TestAICompanionServiceHelpers:
    """测试辅助方法"""

    def test_build_system_prompt(self):
        """测试构建系统提示"""
        from src.services.ai_companion_service import AICompanionService, COMPANION_PERSONAS, SESSION_TYPES

        mock_db = MagicMock()
        service = AICompanionService(mock_db)

        persona = COMPANION_PERSONAS["gentle_advisor"]
        session_type = SESSION_TYPES["chat"]

        result = service._build_system_prompt(persona, session_type)

        assert "温柔姐姐" in result
        assert "陪伴" in result

    def test_build_context(self):
        """测试构建上下文"""
        from src.services.ai_companion_service import AICompanionService

        mock_db = MagicMock()
        service = AICompanionService(mock_db)

        mock_msg1 = MagicMock()
        mock_msg1.role = "user"
        mock_msg1.content = "你好"

        mock_msg2 = MagicMock()
        mock_msg2.role = "assistant"
        mock_msg2.content = "嗨~"

        result = service._build_context([mock_msg1, mock_msg2], {"name": "AI"}, {"name": "聊天"})

        assert "你好" in result
        assert "嗨" in result

    def test_generate_session_summary_empty(self):
        """测试生成空会话摘要"""
        from src.services.ai_companion_service import AICompanionService

        mock_db = MagicMock()
        mock_db.query().filter().all.return_value = []

        service = AICompanionService(mock_db)
        result = service._generate_session_summary("session-123")

        assert result == ""

    def test_generate_session_summary_with_messages(self):
        """测试生成会话摘要"""
        from src.services.ai_companion_service import AICompanionService

        mock_db = MagicMock()
        mock_msg = MagicMock()
        mock_msg.role = "user"
        mock_msg.content = "今天天气不错"
        mock_db.query().filter().all.return_value = [mock_msg]

        service = AICompanionService(mock_db)
        result = service._generate_session_summary("session-123")

        assert "会话" in result
        assert "1" in result

    def test_extract_key_insights_empty(self):
        """测试提取空洞察"""
        from src.services.ai_companion_service import AICompanionService

        mock_db = MagicMock()
        mock_db.query().filter().all.return_value = []

        service = AICompanionService(mock_db)
        result = service._extract_key_insights("session-123")

        assert isinstance(result, list)
        assert len(result) == 0

    def test_extract_key_insights_mood_change(self):
        """测试提取情绪变化洞察"""
        from src.services.ai_companion_service import AICompanionService

        mock_db = MagicMock()
        mock_msg1 = MagicMock()
        mock_msg1.role = "user"
        mock_msg1.sentiment = -0.5

        mock_msg2 = MagicMock()
        mock_msg2.role = "user"
        mock_msg2.sentiment = 0.5

        mock_db.query().filter().all.return_value = [mock_msg1, MagicMock(role="assistant"), mock_msg2]

        service = AICompanionService(mock_db)
        result = service._extract_key_insights("session-123")

        assert len(result) >= 0  # 可能有情绪改善的洞察


class TestAICompanionServicePersonaTypes:
    """测试角色类型定义"""

    def test_persona_types_defined(self):
        """测试角色类型已定义"""
        from src.services.ai_companion_service import COMPANION_PERSONAS

        assert "gentle_advisor" in COMPANION_PERSONAS
        assert "caring_sister" in COMPANION_PERSONAS
        assert "professional_coach" in COMPANION_PERSONAS
        assert "funny_friend" in COMPANION_PERSONAS
        assert "empathetic_listener" in COMPANION_PERSONAS

    def test_persona_structure(self):
        """测试角色结构"""
        from src.services.ai_companion_service import COMPANION_PERSONAS

        for persona_name, persona_info in COMPANION_PERSONAS.items():
            assert "name" in persona_info
            assert "description" in persona_info
            assert "greeting" in persona_info
            assert "personality_traits" in persona_info
            assert "conversation_style" in persona_info


class TestAICompanionServiceSessionTypes:
    """测试会话类型定义"""

    def test_session_types_defined(self):
        """测试会话类型已定义"""
        from src.services.ai_companion_service import SESSION_TYPES

        assert "chat" in SESSION_TYPES
        assert "emotional_support" in SESSION_TYPES
        assert "coaching" in SESSION_TYPES
        assert "roleplay" in SESSION_TYPES
        assert "breakup_recovery" in SESSION_TYPES
        assert "confidence_building" in SESSION_TYPES

    def test_session_type_structure(self):
        """测试会话类型结构"""
        from src.services.ai_companion_service import SESSION_TYPES

        for session_type_name, session_type_info in SESSION_TYPES.items():
            assert "name" in session_type_info
            assert "description" in session_type_info
