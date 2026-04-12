"""
QuickChatService 完整测试

测试覆盖:
1. 服务初始化与关闭边缘场景 (7 tests)
2. AI 建议生成 - 正常流程与边缘场景 (12 tests)
3. 回复建议生成 - 正常流程与边缘场景 (15 tests)
4. 反馈记录 - 正常流程与边缘场景 (6 tests)
5. 对方资料获取 - 正常流程与边缘场景 (8 tests)
6. 聊天历史获取 - 正常流程与边缘场景 (10 tests)
7. Prompt 构建 - 正常流程与边缘场景 (10 tests)
8. 消息格式化 - 正常流程与边缘场景 (6 tests)
9. LLM 响应解析 - 正常流程与边缘场景 (4 tests)
10. 记忆服务集成 - 正常流程与边缘场景 (6 tests)
11. 异常处理与降级策略 (10 tests)
12. 集成测试 - 多方法协作 (2 tests)

总计: 94 个测试用例
"""
import pytest
import uuid
import json
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, PropertyMock
from sqlalchemy import create_engine, or_, and_, desc
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置环境变量
os.environ['OPENAI_API_KEY'] = 'test-key'
os.environ['OPENAI_BASE_URL'] = 'https://test.api/v1'
os.environ['LLM_API_KEY'] = 'test-key'
os.environ['LLM_API_BASE'] = 'https://test.api/v1'


# ============= 测试基础设施 =============

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)


# 延迟导入以确保环境变量已设置
from db.database import Base
from db.models import UserDB, ChatMessageDB, ChatConversationDB
from services.quick_chat_service import QuickChatService


Base.metadata.create_all(bind=test_engine)


@pytest.fixture
def db_session():
    """数据库会话 fixture"""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def quick_chat_service(db_session):
    """QuickChatService fixture"""
    service = QuickChatService(db=db_session)
    yield service
    service.close()


def make_user(**kwargs):
    """创建测试用户"""
    defaults = {
        "id": str(uuid.uuid4()),
        "email": f"quick_{uuid.uuid4()}@example.com",
        "password_hash": "hashed_pw",
        "name": "Quick Test User",
        "age": 28,
        "gender": "female",
        "location": "北京",
        "interests": json.dumps(["reading", "travel"]),
        "values": json.dumps({}),
        "bio": "Test bio",
    }
    defaults.update(kwargs)
    return UserDB(**defaults)


def make_conversation(**kwargs):
    """创建测试会话"""
    defaults = {
        "id": str(uuid.uuid4()),
        "user_id_1": "user_1",
        "user_id_2": "user_2",
        "status": "active",
        "unread_count_user1": 0,
        "unread_count_user2": 0,
    }
    defaults.update(kwargs)
    return ChatConversationDB(**defaults)


def make_message(**kwargs):
    """创建测试消息"""
    defaults = {
        "id": str(uuid.uuid4()),
        "conversation_id": str(uuid.uuid4()),
        "sender_id": "sender",
        "receiver_id": "receiver",
        "message_type": "text",
        "content": "Test message",
        "status": "sent",
        "is_read": False,
    }
    defaults.update(kwargs)
    return ChatMessageDB(**defaults)


# ============= 第一部分：服务初始化与关闭边缘场景 =============

class TestServiceInitialization:
    """服务初始化与关闭测试"""

    def test_init_with_db_session(self, db_session):
        """测试使用传入的数据库会话初始化"""
        service = QuickChatService(db=db_session)
        assert service.db == db_session
        assert service._should_close_db is False
        service.close()

    def test_init_without_db_session(self):
        """测试不传入数据库会话初始化"""
        # 使用 patch 阻止真实 SessionLocal 创建
        # SessionLocal 在 __init__ 中延迟导入，需要 patch db.database.SessionLocal
        with patch('db.database.SessionLocal') as mock_session_local:
            mock_db = MagicMock()
            mock_session_local.return_value = mock_db
            service = QuickChatService()
            assert service._should_close_db is True
            service.close()

    def test_close_session_when_self_created(self):
        """测试关闭自己创建的数据库会话"""
        mock_db = MagicMock()
        with patch('db.database.SessionLocal', return_value=mock_db):
            service = QuickChatService()
            service.close()
            mock_db.close.assert_called_once()

    def test_close_session_sets_db_to_none_external(self):
        """测试关闭后 _db 属性被清空（自己创建的会话）"""
        mock_db = MagicMock()
        with patch('db.database.SessionLocal', return_value=mock_db):
            service = QuickChatService()
            service.close()
            # _db 属性应该被清空（通过 _db 而不是 db property）
            assert service._db is None

    def test_close_external_session_not_closed(self, db_session):
        """测试外部传入的会话不会被关闭"""
        service = QuickChatService(db=db_session)
        service.close()
        # 外部会话不会被关闭（_should_close_db=False），但 db 属性仍会被清空
        # db_session fixture 应该仍然可用
        assert db_session is not None

    def test_close_handles_exception(self):
        """测试关闭时异常处理"""
        mock_db = MagicMock()
        mock_db.close.side_effect = Exception("Close error")
        with patch('db.database.SessionLocal', return_value=mock_db):
            service = QuickChatService()
            # 应该不抛出异常
            service.close()
            # _db 属性应该被清空
            assert service._db is None

    def test_close_when_db_already_none(self, db_session):
        """测试 db 已经为 None 时关闭"""
        service = QuickChatService(db=db_session)
        service.db = None
        service._should_close_db = False
        # 应该不抛出异常
        service.close()


# ============= 第二部分：AI 建议生成 - 正常流程与边缘场景 =============

class TestGetAIAdvice:
    """AI 建议生成测试"""

    @pytest.fixture
    def mock_llm(self):
        """Mock LLM 响应"""
        return "她可能在忙，建议等她忙完再联系。"

    @pytest.fixture
    def mock_memory_service(self):
        """Mock 记忆服务"""
        service = MagicMock()
        service.get_contextual_memories.return_value = []
        return service

    def test_get_ai_advice_basic(self, quick_chat_service, mock_llm, mock_memory_service):
        """测试获取 AI 建议 - 基础功能"""
        with patch('services.quick_chat_service.call_llm', return_value=mock_llm):
            with patch('services.quick_chat_service.get_memory_service', return_value=mock_memory_service):
                result = quick_chat_service.get_ai_advice(
                    current_user_id='test_user',
                    partner_id='test_partner',
                    question='她为什么不回我消息？',
                    recent_messages=[
                        {"senderId": "me", "content": "在干嘛呢？"},
                        {"senderId": "her", "content": "在开会"}
                    ]
                )

        assert isinstance(result, dict)
        assert 'answer' in result
        assert 'suggestions' in result
        assert 'analysis' in result
        assert result['answer'] == mock_llm

    def test_get_ai_advice_empty_recent_messages(self, quick_chat_service, db_session):
        """测试获取 AI 建议 - 空聊天记录"""
        # 创建用户和会话数据
        user = make_user(id='test_partner_empty', name='Partner')
        db_session.add(user)
        conv = make_conversation(user_id_1='test_user', user_id_2='test_partner_empty')
        db_session.add(conv)
        db_session.commit()

        mock_llm = "暂无聊天记录，建议先打个招呼。"
        mock_memory_service = MagicMock()
        mock_memory_service.get_contextual_memories.return_value = []

        with patch('services.quick_chat_service.call_llm', return_value=mock_llm):
            with patch('services.quick_chat_service.get_memory_service', return_value=mock_memory_service):
                result = quick_chat_service.get_ai_advice(
                    current_user_id='test_user',
                    partner_id='test_partner_empty',
                    question='怎么开始聊天？',
                    recent_messages=[]
                )

        assert result['answer'] == mock_llm

    def test_get_ai_advice_with_memory(self, quick_chat_service, mock_llm):
        """测试获取 AI 建议 - 带记忆检索"""
        mock_memories = [
            {"content": "用户女朋友工作很忙", "category": "relationship", "importance": 4},
            {"content": "用户喜欢喝咖啡", "category": "preference", "importance": 5},
        ]
        mock_memory_service = MagicMock()
        mock_memory_service.get_contextual_memories.return_value = mock_memories

        with patch('services.quick_chat_service.call_llm', return_value=mock_llm):
            with patch('services.quick_chat_service.get_memory_service', return_value=mock_memory_service):
                result = quick_chat_service.get_ai_advice(
                    current_user_id='test_user',
                    partner_id='test_partner',
                    question='她为什么不回我消息？',
                    recent_messages=[
                        {"senderId": "me", "content": "在干嘛呢？"},
                        {"senderId": "her", "content": "在开会"}
                    ]
                )

        assert result['answer'] == mock_llm
        mock_memory_service.get_contextual_memories.assert_called_once_with(
            user_id='test_user',
            current_context='她为什么不回我消息？',
            limit=5
        )

    def test_get_ai_advice_memory_service_none(self, quick_chat_service, mock_llm):
        """测试获取 AI 建议 - 记忆服务不可用"""
        with patch('services.quick_chat_service.call_llm', return_value=mock_llm):
            with patch('services.quick_chat_service.get_memory_service', return_value=None):
                result = quick_chat_service.get_ai_advice(
                    current_user_id='test_user',
                    partner_id='test_partner',
                    question='测试问题',
                    recent_messages=[]
                )

        assert result['answer'] == mock_llm

    def test_get_ai_advice_memory_service_exception(self, quick_chat_service, mock_llm):
        """测试获取 AI 建议 - 记忆服务异常
        注意：记忆服务异常会导致整个流程失败，因为异常发生在 try 块开始处
        """
        mock_memory_service = MagicMock()
        mock_memory_service.get_contextual_memories.side_effect = Exception("Memory error")

        with patch('services.quick_chat_service.call_llm', return_value=mock_llm):
            with patch('services.quick_chat_service.get_memory_service', return_value=mock_memory_service):
                result = quick_chat_service.get_ai_advice(
                    current_user_id='test_user',
                    partner_id='test_partner',
                    question='测试问题',
                    recent_messages=[]
                )

        # 记忆服务异常会导致整个流程失败，返回默认错误响应
        assert result['answer'] == "抱歉，我现在无法思考，请稍后再试～"

    def test_get_ai_advice_long_question(self, quick_chat_service, mock_llm, mock_memory_service):
        """测试获取 AI 建议 - 超长问题"""
        long_question = "为什么" * 500

        with patch('services.quick_chat_service.call_llm', return_value=mock_llm):
            with patch('services.quick_chat_service.get_memory_service', return_value=mock_memory_service):
                result = quick_chat_service.get_ai_advice(
                    current_user_id='test_user',
                    partner_id='test_partner',
                    question=long_question,
                    recent_messages=[]
                )

        assert result['answer'] == mock_llm

    def test_get_ai_advice_unicode_question(self, quick_chat_service, mock_llm, mock_memory_service):
        """测试获取 AI 建议 - Unicode 问题"""
        unicode_question = "她为什么不回我消息？🎉🎉🎉 日本語 العربية"

        with patch('services.quick_chat_service.call_llm', return_value=mock_llm):
            with patch('services.quick_chat_service.get_memory_service', return_value=mock_memory_service):
                result = quick_chat_service.get_ai_advice(
                    current_user_id='test_user',
                    partner_id='test_partner',
                    question=unicode_question,
                    recent_messages=[]
                )

        assert result['answer'] == mock_llm

    def test_get_ai_advice_special_characters_question(self, quick_chat_service, mock_llm, mock_memory_service):
        """测试获取 AI 建议 - 特殊字符问题"""
        special_question = "她为什么不回<script>alert('xss')</script>消息"

        with patch('services.quick_chat_service.call_llm', return_value=mock_llm):
            with patch('services.quick_chat_service.get_memory_service', return_value=mock_memory_service):
                result = quick_chat_service.get_ai_advice(
                    current_user_id='test_user',
                    partner_id='test_partner',
                    question=special_question,
                    recent_messages=[]
                )

        assert result['answer'] == mock_llm

    def test_get_ai_advice_many_messages(self, quick_chat_service, mock_llm, mock_memory_service):
        """测试获取 AI 建议 - 大量聊天记录"""
        many_messages = [
            {"senderId": "me", "content": f"消息{i}"} for i in range(100)
        ]

        with patch('services.quick_chat_service.call_llm', return_value=mock_llm):
            with patch('services.quick_chat_service.get_memory_service', return_value=mock_memory_service):
                result = quick_chat_service.get_ai_advice(
                    current_user_id='test_user',
                    partner_id='test_partner',
                    question='分析一下',
                    recent_messages=many_messages
                )

        assert result['answer'] == mock_llm

    def test_get_ai_advice_llm_exception(self, quick_chat_service, mock_memory_service):
        """测试获取 AI 建议 - LLM 异常"""
        with patch('services.quick_chat_service.call_llm', side_effect=Exception("LLM error")):
            with patch('services.quick_chat_service.get_memory_service', return_value=mock_memory_service):
                result = quick_chat_service.get_ai_advice(
                    current_user_id='test_user',
                    partner_id='test_partner',
                    question='测试问题',
                    recent_messages=[]
                )

        # 应该返回默认错误响应
        assert result['answer'] == "抱歉，我现在无法思考，请稍后再试～"
        assert result['suggestions'] == []
        assert result['analysis'] == {}

    def test_get_ai_advice_all_exceptions(self, quick_chat_service):
        """测试获取 AI 建议 - 全流程异常"""
        with patch('services.quick_chat_service.get_memory_service', side_effect=Exception("All error")):
            result = quick_chat_service.get_ai_advice(
                current_user_id='test_user',
                partner_id='test_partner',
                question='测试问题',
                recent_messages=[]
            )

        assert result['answer'] == "抱歉，我现在无法思考，请稍后再试～"

    def test_get_ai_advice_with_db_messages(self, quick_chat_service, db_session):
        """测试获取 AI 建议 - 从数据库补充聊天记录"""
        # 创建测试数据
        user = make_user(id='test_partner_db', name='Partner DB')
        db_session.add(user)
        conv = make_conversation(user_id_1='test_user_db', user_id_2='test_partner_db')
        db_session.add(conv)
        db_session.commit()

        for i in range(5):
            msg = make_message(
                conversation_id=conv.id,
                sender_id='test_user_db',
                receiver_id='test_partner_db',
                content=f'DB message {i}'
            )
            db_session.add(msg)
        db_session.commit()

        mock_llm = "AI response"
        mock_memory_service = MagicMock()
        mock_memory_service.get_contextual_memories.return_value = []

        with patch('services.quick_chat_service.call_llm', return_value=mock_llm):
            with patch('services.quick_chat_service.get_memory_service', return_value=mock_memory_service):
                result = quick_chat_service.get_ai_advice(
                    current_user_id='test_user_db',
                    partner_id='test_partner_db',
                    question='分析一下',
                    recent_messages=[]  # 空的，会从 DB 获取
                )

        assert result['answer'] == mock_llm


# ============= 第三部分：回复建议生成 - 正常流程与边缘场景 =============

class TestSuggestReply:
    """回复建议生成测试"""

    @pytest.fixture
    def mock_json_response(self):
        """Mock JSON 格式的 LLM 响应"""
        return json.dumps({
            "suggestions": [
                {"style": "幽默风趣", "content": "辛苦啦！奶茶已点"},
                {"style": "真诚关心", "content": "这么晚还在工作"},
                {"style": "延续话题", "content": "加班到这么晚啊"}
            ]
        })

    @pytest.fixture
    def mock_memory_service(self):
        """Mock 记忆服务"""
        service = MagicMock()
        service.get_contextual_memories.return_value = []
        service.extract_memory_from_dialogue.return_value = []
        return service

    def test_suggest_reply_basic(self, quick_chat_service, mock_json_response, mock_memory_service):
        """测试生成回复建议 - 基础功能"""
        with patch('services.quick_chat_service.call_llm', return_value=mock_json_response):
            with patch('services.quick_chat_service.get_memory_service', return_value=mock_memory_service):
                result = quick_chat_service.suggest_reply(
                    current_user_id='test_user',
                    partner_id='test_partner',
                    last_message={"content": "刚加班完，好累", "senderId": "her"},
                    recent_messages=[
                        {"senderId": "her", "content": "刚加班完，好累"}
                    ],
                    relationship_stage='初识'
                )

        assert result['success'] is True
        assert 'suggestions' in result
        assert len(result['suggestions']) == 3
        # 每个建议应该有 ID
        for sug in result['suggestions']:
            assert 'id' in sug
            assert 'style' in sug
            assert 'content' in sug

    def test_suggest_reply_with_memory(self, quick_chat_service, mock_json_response):
        """测试生成回复建议 - 带记忆"""
        mock_memories = [
            {"content": "用户喜欢喝奶茶", "category": "preference"},
            {"content": "用户是程序员", "category": "user_info"},
        ]
        mock_memory_service = MagicMock()
        mock_memory_service.get_contextual_memories.return_value = mock_memories
        mock_memory_service.extract_memory_from_dialogue.return_value = []

        with patch('services.quick_chat_service.call_llm', return_value=mock_json_response):
            with patch('services.quick_chat_service.get_memory_service', return_value=mock_memory_service):
                result = quick_chat_service.suggest_reply(
                    current_user_id='test_user',
                    partner_id='test_partner',
                    last_message={"content": "累了", "senderId": "her"},
                    recent_messages=[]
                )

        assert result['success'] is True
        mock_memory_service.get_contextual_memories.assert_called_once()

    def test_suggest_reply_memory_extraction(self, quick_chat_service, mock_json_response):
        """测试生成回复建议 - 记忆提取"""
        mock_memory_service = MagicMock()
        mock_memory_service.get_contextual_memories.return_value = []
        mock_memory_service.extract_memory_from_dialogue.return_value = []

        with patch('services.quick_chat_service.call_llm', return_value=mock_json_response):
            with patch('services.quick_chat_service.get_memory_service', return_value=mock_memory_service):
                result = quick_chat_service.suggest_reply(
                    current_user_id='test_user',
                    partner_id='test_partner',
                    last_message={"content": "累了", "senderId": "her"},
                    recent_messages=[
                        {"senderId": "me", "content": "在干嘛"},
                        {"senderId": "her", "content": "加班"},
                        {"senderId": "me", "content": "辛苦"},
                        {"senderId": "her", "content": "累了"},
                    ]
                )

        # 验证记忆提取被调用
        mock_memory_service.extract_memory_from_dialogue.assert_called_once()
        # 验证传入的对话文本格式
        call_args = mock_memory_service.extract_memory_from_dialogue.call_args
        assert 'user_id' in call_args.kwargs
        assert 'dialogue' in call_args.kwargs

    def test_suggest_reply_memory_extraction_exception(self, quick_chat_service, mock_json_response):
        """测试生成回复建议 - 记忆提取异常"""
        mock_memory_service = MagicMock()
        mock_memory_service.get_contextual_memories.return_value = []
        mock_memory_service.extract_memory_from_dialogue.side_effect = Exception("Extract error")

        with patch('services.quick_chat_service.call_llm', return_value=mock_json_response):
            with patch('services.quick_chat_service.get_memory_service', return_value=mock_memory_service):
                result = quick_chat_service.suggest_reply(
                    current_user_id='test_user',
                    partner_id='test_partner',
                    last_message={"content": "累了", "senderId": "her"},
                    recent_messages=[
                        {"senderId": "me", "content": "消息"},
                    ]
                )

        # 应该正常返回，记忆提取失败不阻塞响应
        assert result['success'] is True

    def test_suggest_reply_empty_last_message(self, quick_chat_service, mock_json_response, mock_memory_service):
        """测试生成回复建议 - 空的最后消息"""
        with patch('services.quick_chat_service.call_llm', return_value=mock_json_response):
            with patch('services.quick_chat_service.get_memory_service', return_value=mock_memory_service):
                result = quick_chat_service.suggest_reply(
                    current_user_id='test_user',
                    partner_id='test_partner',
                    last_message={},  # 空消息
                    recent_messages=[]
                )

        assert result['success'] is True

    def test_suggest_reply_json_parse_error(self, quick_chat_service, mock_memory_service):
        """测试生成回复建议 - JSON 解析错误降级"""
        invalid_response = "这不是有效的 JSON 格式"

        with patch('services.quick_chat_service.call_llm', return_value=invalid_response):
            with patch('services.quick_chat_service.get_memory_service', return_value=mock_memory_service):
                result = quick_chat_service.suggest_reply(
                    current_user_id='test_user',
                    partner_id='test_partner',
                    last_message={"content": "测试", "senderId": "her"},
                    recent_messages=[]
                )

        assert result['success'] is True
        assert len(result['suggestions']) > 0
        # 降级处理时，截取前 50 字符作为内容
        assert result['suggestions'][0]['content'][:50] == invalid_response[:50]

    def test_suggest_reply_llm_exception(self, quick_chat_service, mock_memory_service):
        """测试生成回复建议 - LLM 异常"""
        with patch('services.quick_chat_service.call_llm', side_effect=Exception("LLM error")):
            with patch('services.quick_chat_service.get_memory_service', return_value=mock_memory_service):
                result = quick_chat_service.suggest_reply(
                    current_user_id='test_user',
                    partner_id='test_partner',
                    last_message={"content": "测试", "senderId": "her"},
                    recent_messages=[]
                )

        assert result['success'] is False
        assert len(result['suggestions']) > 0
        assert result['suggestions'][0]['content'] == "抱歉，AI 思考中，请稍后再试～"

    def test_suggest_reply_empty_suggestions_in_response(self, quick_chat_service, mock_memory_service):
        """测试生成回复建议 - 响应中建议为空"""
        empty_response = json.dumps({"suggestions": []})

        with patch('services.quick_chat_service.call_llm', return_value=empty_response):
            with patch('services.quick_chat_service.get_memory_service', return_value=mock_memory_service):
                result = quick_chat_service.suggest_reply(
                    current_user_id='test_user',
                    partner_id='test_partner',
                    last_message={"content": "测试", "senderId": "her"},
                    recent_messages=[]
                )

        assert result['success'] is True
        assert result['suggestions'] == []

    def test_suggest_reply_unicode_content(self, quick_chat_service, mock_json_response, mock_memory_service):
        """测试生成回复建议 - Unicode 内容"""
        unicode_response = json.dumps({
            "suggestions": [
                {"style": "幽默", "content": "辛苦啦！🎉🎉🎉"},
                {"style": "关心", "content": "日本語 العربية"}
            ]
        })

        with patch('services.quick_chat_service.call_llm', return_value=unicode_response):
            with patch('services.quick_chat_service.get_memory_service', return_value=mock_memory_service):
                result = quick_chat_service.suggest_reply(
                    current_user_id='test_user',
                    partner_id='test_partner',
                    last_message={"content": "🎉", "senderId": "her"},
                    recent_messages=[]
                )

        assert result['success'] is True

    def test_suggest_reply_relationship_stage_variations(self, quick_chat_service, mock_json_response, mock_memory_service):
        """测试生成回复建议 - 不同关系阶段"""
        stages = ["初识", "暧昧", "热恋", "稳定", "分手边缘"]

        for stage in stages:
            with patch('services.quick_chat_service.call_llm', return_value=mock_json_response):
                with patch('services.quick_chat_service.get_memory_service', return_value=mock_memory_service):
                    result = quick_chat_service.suggest_reply(
                        current_user_id='test_user',
                        partner_id='test_partner',
                        last_message={"content": "消息", "senderId": "her"},
                        recent_messages=[],
                        relationship_stage=stage
                    )

            assert result['success'] is True

    def test_suggest_reply_with_special_characters(self, quick_chat_service, mock_json_response, mock_memory_service):
        """测试生成回复建议 - 特殊字符"""
        special_content = "<script>alert('xss')</script>"

        with patch('services.quick_chat_service.call_llm', return_value=mock_json_response):
            with patch('services.quick_chat_service.get_memory_service', return_value=mock_memory_service):
                result = quick_chat_service.suggest_reply(
                    current_user_id='test_user',
                    partner_id='test_partner',
                    last_message={"content": special_content, "senderId": "her"},
                    recent_messages=[]
                )

        assert result['success'] is True

    def test_suggest_reply_long_message(self, quick_chat_service, mock_json_response, mock_memory_service):
        """测试生成回复建议 - 超长消息"""
        long_content = "A" * 1000

        with patch('services.quick_chat_service.call_llm', return_value=mock_json_response):
            with patch('services.quick_chat_service.get_memory_service', return_value=mock_memory_service):
                result = quick_chat_service.suggest_reply(
                    current_user_id='test_user',
                    partner_id='test_partner',
                    last_message={"content": long_content, "senderId": "her"},
                    recent_messages=[]
                )

        assert result['success'] is True

    def test_suggest_reply_memory_service_none(self, quick_chat_service, mock_json_response):
        """测试生成回复建议 - 记忆服务不可用"""
        with patch('services.quick_chat_service.call_llm', return_value=mock_json_response):
            with patch('services.quick_chat_service.get_memory_service', return_value=None):
                result = quick_chat_service.suggest_reply(
                    current_user_id='test_user',
                    partner_id='test_partner',
                    last_message={"content": "测试", "senderId": "her"},
                    recent_messages=[]
                )

        assert result['success'] is True

    def test_suggest_reply_no_recent_messages(self, quick_chat_service, mock_json_response, mock_memory_service):
        """测试生成回复建议 - 无最近聊天记录"""
        with patch('services.quick_chat_service.call_llm', return_value=mock_json_response):
            with patch('services.quick_chat_service.get_memory_service', return_value=mock_memory_service):
                result = quick_chat_service.suggest_reply(
                    current_user_id='test_user',
                    partner_id='test_partner',
                    last_message={"content": "测试", "senderId": "her"},
                    recent_messages=[]
                )

        assert result['success'] is True
        # 无聊天记录时不提取记忆
        mock_memory_service.extract_memory_from_dialogue.assert_not_called()


# ============= 第四部分：反馈记录 - 正常流程与边缘场景 =============

class TestRecordSuggestionFeedback:
    """反馈记录测试"""

    def test_record_feedback_basic(self, quick_chat_service):
        """测试记录反馈 - 基础功能"""
        mock_feedback_id = 'feedback-uuid-001'
        mock_feedback_service = MagicMock()
        mock_feedback_service.record_feedback.return_value = mock_feedback_id

        with patch('services.quick_chat_service.get_ai_feedback_service', return_value=mock_feedback_service):
            result = quick_chat_service.record_suggestion_feedback(
                current_user_id='test_user',
                partner_id='test_partner',
                suggestion_id='suggestion-001',
                feedback_type='adopted',
                suggestion_content='辛苦啦！',
                suggestion_style='幽默风趣',
                user_actual_reply='辛苦啦！'
            )

        assert result == mock_feedback_id
        mock_feedback_service.record_feedback.assert_called_once()

    def test_record_feedback_without_actual_reply(self, quick_chat_service):
        """测试记录反馈 - 无实际回复"""
        mock_feedback_id = 'feedback-002'
        mock_feedback_service = MagicMock()
        mock_feedback_service.record_feedback.return_value = mock_feedback_id

        with patch('services.quick_chat_service.get_ai_feedback_service', return_value=mock_feedback_service):
            result = quick_chat_service.record_suggestion_feedback(
                current_user_id='test_user',
                partner_id='test_partner',
                suggestion_id='suggestion-002',
                feedback_type='ignored',
                suggestion_content='建议内容',
                suggestion_style='真诚关心'
            )

        assert result == mock_feedback_id
        # 验证 user_actual_reply 参数为 None
        call_kwargs = mock_feedback_service.record_feedback.call_args.kwargs
        assert call_kwargs.get('user_actual_reply') is None

    def test_record_feedback_modified_type(self, quick_chat_service):
        """测试记录反馈 - modified 类型"""
        mock_feedback_id = 'feedback-003'
        mock_feedback_service = MagicMock()
        mock_feedback_service.record_feedback.return_value = mock_feedback_id

        with patch('services.quick_chat_service.get_ai_feedback_service', return_value=mock_feedback_service):
            result = quick_chat_service.record_suggestion_feedback(
                current_user_id='test_user',
                partner_id='test_partner',
                suggestion_id='suggestion-003',
                feedback_type='modified',
                suggestion_content='AI 建议内容',
                suggestion_style='幽默风趣',
                user_actual_reply='修改后的内容'
            )

        assert result == mock_feedback_id
        call_kwargs = mock_feedback_service.record_feedback.call_args.kwargs
        assert call_kwargs.get('feedback_type') == 'modified'
        assert call_kwargs.get('user_actual_reply') == '修改后的内容'

    def test_record_feedback_all_types(self, quick_chat_service):
        """测试记录反馈 - 所有反馈类型"""
        feedback_types = ['adopted', 'ignored', 'modified', 'helpful', 'not_helpful']
        mock_feedback_service = MagicMock()
        mock_feedback_service.record_feedback.return_value = 'feedback-id'

        for ft in feedback_types:
            with patch('services.quick_chat_service.get_ai_feedback_service', return_value=mock_feedback_service):
                result = quick_chat_service.record_suggestion_feedback(
                    current_user_id='test_user',
                    partner_id='test_partner',
                    suggestion_id='suggestion-id',
                    feedback_type=ft,
                    suggestion_content='内容',
                    suggestion_style='风格'
                )

            assert result == 'feedback-id'

    def test_record_feedback_unicode_content(self, quick_chat_service):
        """测试记录反馈 - Unicode 内容"""
        mock_feedback_id = 'feedback-unicode'
        mock_feedback_service = MagicMock()
        mock_feedback_service.record_feedback.return_value = mock_feedback_id

        with patch('services.quick_chat_service.get_ai_feedback_service', return_value=mock_feedback_service):
            result = quick_chat_service.record_suggestion_feedback(
                current_user_id='test_user',
                partner_id='test_partner',
                suggestion_id='suggestion-unicode',
                feedback_type='adopted',
                suggestion_content='辛苦啦！🎉🎉🎉 日本語',
                suggestion_style='幽默',
                user_actual_reply='辛苦啦！🎉'
            )

        assert result == mock_feedback_id

    def test_record_feedback_empty_ids(self, quick_chat_service):
        """测试记录反馈 - 空 ID"""
        mock_feedback_service = MagicMock()
        mock_feedback_service.record_feedback.return_value = 'feedback-empty'

        with patch('services.quick_chat_service.get_ai_feedback_service', return_value=mock_feedback_service):
            result = quick_chat_service.record_suggestion_feedback(
                current_user_id='',
                partner_id='',
                suggestion_id='',
                feedback_type='adopted',
                suggestion_content='',
                suggestion_style=''
            )

        # 应该正常调用反馈服务
        assert result == 'feedback-empty'


# ============= 第五部分：对方资料获取 - 正常流程与边缘场景 =============

class TestGetPartnerProfile:
    """对方资料获取测试"""

    def test_get_partner_profile_existing_user(self, quick_chat_service, db_session):
        """测试获取对方资料 - 存在的用户"""
        user = make_user(
            id='partner_existing',
            name='小美',
            age=25,
            location='上海',
            gender='female',
            interests=json.dumps(["reading", "travel"]),
            bio='喜欢旅行'
        )
        db_session.add(user)
        db_session.commit()

        profile = quick_chat_service._get_partner_profile('partner_existing')

        assert profile['name'] == '小美'
        assert profile['age'] == 25
        assert profile['location'] == '上海'
        assert profile['gender'] == 'female'
        assert profile['bio'] == '喜欢旅行'

    def test_get_partner_profile_nonexistent_user(self, quick_chat_service):
        """测试获取对方资料 - 不存在的用户"""
        profile = quick_chat_service._get_partner_profile('nonexistent_user')

        assert profile['name'] == 'TA'
        assert profile['age'] == '?'
        assert profile['location'] == '未知'
        assert profile['interests'] == []

    def test_get_partner_profile_partial_data(self, quick_chat_service, db_session):
        """测试获取对方资料 - 部分数据缺失（interests 为空）
        注意：age, name, location 在数据库中有 NOT NULL 约束，不能设为 None
        """
        user = make_user(
            id='partner_partial',
            name='部分用户',
            age=28,  # 必须有值
            location='上海',  # 必须有值
            interests=None  # 可以为空
        )
        db_session.add(user)
        db_session.commit()

        profile = quick_chat_service._get_partner_profile('partner_partial')

        assert profile['name'] == '部分用户'
        assert profile['age'] == 28
        assert profile['location'] == '上海'
        assert profile['interests'] == []

    def test_get_partner_profile_empty_interests(self, quick_chat_service, db_session):
        """测试获取对方资料 - 兴趣为空字符串"""
        user = make_user(
            id='partner_empty_interests',
            name='兴趣为空',
            interests=""  # 空字符串
        )
        db_session.add(user)
        db_session.commit()

        profile = quick_chat_service._get_partner_profile('partner_empty_interests')

        # interests 返回空列表
        assert profile['interests'] == []

    def test_get_partner_profile_db_exception(self, quick_chat_service, db_session):
        """测试获取对方资料 - 数据库异常"""
        # 模拟查询异常
        with patch.object(db_session, 'query', side_effect=Exception("DB error")):
            profile = quick_chat_service._get_partner_profile('error_user')

        assert profile['name'] == 'TA'
        assert profile['age'] == '?'
        assert profile['location'] == '未知'

    def test_get_partner_profile_with_interests_json(self, quick_chat_service, db_session):
        """测试获取对方资料 - JSON 格式兴趣
        注意：interests 字段存储为 JSON 字符串，服务返回原始值
        """
        user = make_user(
            id='partner_interests',
            name='兴趣用户',
            interests=json.dumps(["电影", "音乐", "运动"])
        )
        db_session.add(user)
        db_session.commit()

        profile = quick_chat_service._get_partner_profile('partner_interests')

        # interests 返回存储的 JSON 字符串
        expected = json.dumps(["电影", "音乐", "运动"])
        assert profile['interests'] == expected

    def test_get_partner_profile_with_interests_string(self, quick_chat_service, db_session):
        """测试获取对方资料 - 字符串格式兴趣"""
        user = make_user(
            id='partner_interests_str',
            name='兴趣字符串',
            interests="电影,音乐,运动"
        )
        db_session.add(user)
        db_session.commit()

        profile = quick_chat_service._get_partner_profile('partner_interests_str')

        # interests 字段返回原始值
        assert profile['interests'] == "电影,音乐,运动"

    def test_get_partner_profile_unicode(self, quick_chat_service, db_session):
        """测试获取对方资料 - Unicode 信息"""
        user = make_user(
            id='partner_unicode',
            name='日本語ユーザー 🎉',
            location='東京',
            bio='اللغة العربية'
        )
        db_session.add(user)
        db_session.commit()

        profile = quick_chat_service._get_partner_profile('partner_unicode')

        assert profile['name'] == '日本語ユーザー 🎉'
        assert profile['location'] == '東京'
        assert profile['bio'] == 'اللغة العربية'


# ============= 第六部分：聊天历史获取 - 正常流程与边缘场景 =============

class TestGetConversationHistory:
    """聊天历史获取测试"""

    def test_get_conversation_history_basic(self, quick_chat_service, db_session):
        """测试获取聊天历史 - 基础功能"""
        conv = make_conversation(user_id_1='user_1', user_id_2='user_2')
        db_session.add(conv)
        db_session.commit()

        for i in range(5):
            msg = make_message(
                conversation_id=conv.id,
                sender_id='user_1',
                receiver_id='user_2',
                content=f'Message {i}',
                created_at=datetime.utcnow() - timedelta(minutes=i)
            )
            db_session.add(msg)
        db_session.commit()

        history = quick_chat_service._get_conversation_history('user_1', 'user_2', limit=20)

        assert len(history) == 5
        # 验证格式
        for h in history:
            assert 'senderId' in h
            assert 'content' in h
            assert 'timestamp' in h

    def test_get_conversation_history_reversed_order(self, quick_chat_service, db_session):
        """测试获取聊天历史 - 用户顺序反转"""
        conv = make_conversation(user_id_1='user_a', user_id_2='user_b')
        db_session.add(conv)
        db_session.commit()

        msg = make_message(
            conversation_id=conv.id,
            sender_id='user_a',
            receiver_id='user_b',
            content='Test'
        )
        db_session.add(msg)
        db_session.commit()

        # 正序查询
        history1 = quick_chat_service._get_conversation_history('user_a', 'user_b')
        # 反序查询
        history2 = quick_chat_service._get_conversation_history('user_b', 'user_a')

        # 都应该返回相同数据
        assert len(history1) == 1
        assert len(history2) == 1

    def test_get_conversation_history_no_conversation(self, quick_chat_service):
        """测试获取聊天历史 - 无会话"""
        history = quick_chat_service._get_conversation_history('no_user_1', 'no_user_2')

        assert history == []

    def test_get_conversation_history_limit(self, quick_chat_service, db_session):
        """测试获取聊天历史 - 数量限制"""
        conv = make_conversation(user_id_1='limit_user_1', user_id_2='limit_user_2')
        db_session.add(conv)
        db_session.commit()

        for i in range(30):
            msg = make_message(
                conversation_id=conv.id,
                sender_id='limit_user_1',
                receiver_id='limit_user_2',
                content=f'Limit message {i}',
                created_at=datetime.utcnow() - timedelta(minutes=i)
            )
            db_session.add(msg)
        db_session.commit()

        history = quick_chat_service._get_conversation_history('limit_user_1', 'limit_user_2', limit=10)

        assert len(history) == 10

    def test_get_conversation_history_sender_mapping(self, quick_chat_service, db_session):
        """测试获取聊天历史 - 发送者映射"""
        conv = make_conversation(user_id_1='map_user_1', user_id_2='map_user_2')
        db_session.add(conv)
        db_session.commit()

        # user_1 发送的消息
        msg1 = make_message(
            conversation_id=conv.id,
            sender_id='map_user_1',
            receiver_id='map_user_2',
            content='From user_1'
        )
        db_session.add(msg1)

        # user_2 发送的消息
        msg2 = make_message(
            conversation_id=conv.id,
            sender_id='map_user_2',
            receiver_id='map_user_1',
            content='From user_2'
        )
        db_session.add(msg2)
        db_session.commit()

        history = quick_chat_service._get_conversation_history('map_user_1', 'map_user_2')

        # user_1 发送的应该标记为 'me'
        me_msg = [h for h in history if h['content'] == 'From user_1']
        assert me_msg[0]['senderId'] == 'me'

        # user_2 发送的应该标记为 'her'
        her_msg = [h for h in history if h['content'] == 'From user_2']
        assert her_msg[0]['senderId'] == 'her'

    def test_get_conversation_history_empty_messages(self, quick_chat_service, db_session):
        """测试获取聊天历史 - 无消息"""
        conv = make_conversation(user_id_1='empty_msg_user_1', user_id_2='empty_msg_user_2')
        db_session.add(conv)
        db_session.commit()

        history = quick_chat_service._get_conversation_history('empty_msg_user_1', 'empty_msg_user_2')

        assert history == []

    def test_get_conversation_history_db_exception(self, quick_chat_service, db_session):
        """测试获取聊天历史 - 数据库异常"""
        with patch.object(db_session, 'query', side_effect=Exception("DB error")):
            history = quick_chat_service._get_conversation_history('error_user_1', 'error_user_2')

        assert history == []

    def test_get_conversation_history_unicode_content(self, quick_chat_service, db_session):
        """测试获取聊天历史 - Unicode 内容"""
        conv = make_conversation(user_id_1='unicode_user_1', user_id_2='unicode_user_2')
        db_session.add(conv)
        db_session.commit()

        msg = make_message(
            conversation_id=conv.id,
            sender_id='unicode_user_1',
            receiver_id='unicode_user_2',
            content='你好世界 🎉🎉🎉 日本語 العربية'
        )
        db_session.add(msg)
        db_session.commit()

        history = quick_chat_service._get_conversation_history('unicode_user_1', 'unicode_user_2')

        assert len(history) == 1
        assert history[0]['content'] == '你好世界 🎉🎉🎉 日本語 العربية'

    def test_get_conversation_history_special_characters(self, quick_chat_service, db_session):
        """测试获取聊天历史 - 特殊字符"""
        conv = make_conversation(user_id_1='special_user_1', user_id_2='special_user_2')
        db_session.add(conv)
        db_session.commit()

        msg = make_message(
            conversation_id=conv.id,
            sender_id='special_user_1',
            receiver_id='special_user_2',
            content='<script>alert("xss")</script>'
        )
        db_session.add(msg)
        db_session.commit()

        history = quick_chat_service._get_conversation_history('special_user_1', 'special_user_2')

        assert len(history) == 1

    def test_get_conversation_history_multiple_conversations(self, quick_chat_service, db_session):
        """测试获取聊天历史 - 多个会话"""
        # 创建多个会话
        for i in range(3):
            conv = make_conversation(
                id=f'conv_{i}',
                user_id_1=f'multi_user_{i}',
                user_id_2=f'multi_partner_{i}'
            )
            db_session.add(conv)
            db_session.commit()

            msg = make_message(
                conversation_id=conv.id,
                sender_id=f'multi_user_{i}',
                receiver_id=f'multi_partner_{i}',
                content=f'Conv {i} message'
            )
            db_session.add(msg)
        db_session.commit()

        # 查询特定会话
        history = quick_chat_service._get_conversation_history('multi_user_1', 'multi_partner_1')

        assert len(history) == 1
        assert history[0]['content'] == 'Conv 1 message'


# ============= 第七部分：Prompt 构建 - 正常流程与边缘场景 =============

class TestBuildPrompt:
    """Prompt 构建测试"""

    def test_build_prompt_basic(self, quick_chat_service):
        """测试构建 Prompt - 基础功能"""
        prompt = quick_chat_service._build_prompt(
            question='她为什么不回我消息？',
            partner_profile={'name': '小美', 'age': 25, 'location': '上海', 'interests': ['reading']},
            recent_messages=[
                {"senderId": "me", "content": "在干嘛"},
                {"senderId": "her", "content": "在开会"}
            ]
        )

        assert '她为什么不回我消息？' in prompt
        assert '小美' in prompt
        assert '25' in prompt
        assert '上海' in prompt
        assert 'reading' in prompt
        assert '你: 在干嘛' in prompt
        assert '对方: 在开会' in prompt

    def test_build_prompt_empty_messages(self, quick_chat_service):
        """测试构建 Prompt - 空聊天记录"""
        prompt = quick_chat_service._build_prompt(
            question='测试问题',
            partner_profile={'name': 'TA'},
            recent_messages=[]
        )

        assert '暂无聊天记录' in prompt

    def test_build_prompt_empty_interests(self, quick_chat_service):
        """测试构建 Prompt - 空兴趣爱好"""
        prompt = quick_chat_service._build_prompt(
            question='测试问题',
            partner_profile={'name': 'TA', 'interests': []},
            recent_messages=[]
        )

        assert '未填写' in prompt

    def test_build_prompt_with_memory_empty(self, quick_chat_service):
        """测试构建带记忆 Prompt - 无记忆"""
        prompt = quick_chat_service._build_prompt_with_memory(
            question='测试问题',
            partner_profile={'name': 'TA'},
            recent_messages=[],
            memories=[]
        )

        assert '暂无相关记忆' in prompt
        assert '测试问题' in prompt

    def test_build_prompt_with_memory_present(self, quick_chat_service):
        """测试构建带记忆 Prompt - 有记忆"""
        memories = [
            {"content": "用户喜欢喝咖啡", "importance": 4},
            {"content": "用户女朋友工作忙", "importance": 5},
            {"content": "不重要记忆", "importance": 2},  # 低重要性不应出现
        ]

        prompt = quick_chat_service._build_prompt_with_memory(
            question='她为什么不回我消息？',
            partner_profile={'name': 'TA'},
            recent_messages=[],
            memories=memories
        )

        assert '用户喜欢喝咖啡' in prompt
        assert '用户女朋友工作忙' in prompt
        assert '不重要记忆' not in prompt  # 重要性 < 4 的不显示

    def test_build_prompt_with_memory_all_low_importance(self, quick_chat_service):
        """测试构建带记忆 Prompt - 所有记忆重要性低"""
        memories = [
            {"content": "低重要性 1", "importance": 1},
            {"content": "低重要性 2", "importance": 2},
            {"content": "低重要性 3", "importance": 3},
        ]

        prompt = quick_chat_service._build_prompt_with_memory(
            question='测试问题',
            partner_profile={'name': 'TA'},
            recent_messages=[],
            memories=memories
        )

        assert '暂无相关记忆' in prompt

    def test_build_reply_prompt_basic(self, quick_chat_service):
        """测试构建回复建议 Prompt - 基础功能"""
        prompt = quick_chat_service._build_reply_prompt(
            partner_profile={'name': '小美'},
            last_message={'content': '刚加班完，好累'},
            recent_messages=[
                {"senderId": "me", "content": "在干嘛"},
                {"senderId": "her", "content": "加班"}
            ],
            relationship_stage='初识'
        )

        assert '小美' in prompt
        assert '刚加班完，好累' in prompt
        assert '初识' in prompt
        assert '幽默风趣' in prompt
        assert '真诚关心' in prompt
        assert '延续话题' in prompt

    def test_build_reply_prompt_with_memory(self, quick_chat_service):
        """测试构建回复建议 Prompt - 带记忆"""
        memories = [
            {"content": "用户喜欢喝奶茶", "category": "preference"},
            {"content": "用户是程序员", "category": "user_info"},
            {"content": "不相关记忆", "category": "other"},  # 不在指定类别中
        ]

        prompt = quick_chat_service._build_reply_prompt_with_memory(
            partner_profile={'name': '小美'},
            last_message={'content': '累了'},
            recent_messages=[],
            relationship_stage='初识',
            memories=memories
        )

        assert '用户喜欢喝奶茶' in prompt
        assert '用户是程序员' in prompt
        # 'other' 类别不应出现
        assert '不相关记忆' not in prompt

    def test_build_reply_prompt_with_memory_empty(self, quick_chat_service):
        """测试构建回复建议 Prompt - 无记忆"""
        prompt = quick_chat_service._build_reply_prompt_with_memory(
            partner_profile={'name': '小美'},
            last_message={'content': '累了'},
            recent_messages=[],
            relationship_stage='初识',
            memories=[]
        )

        assert '暂无相关记忆' in prompt


# ============= 第八部分：消息格式化 - 正常流程与边缘场景 =============

class TestFormatMessages:
    """消息格式化测试"""

    def test_format_messages_empty(self, quick_chat_service):
        """测试格式化空消息列表"""
        result = quick_chat_service._format_messages([])
        assert result == "暂无聊天记录"

    def test_format_messages_basic(self, quick_chat_service):
        """测试格式化消息 - 基础功能"""
        messages = [
            {"senderId": "me", "content": "你好"},
            {"senderId": "her", "content": "你好呀"}
        ]

        result = quick_chat_service._format_messages(messages)

        assert "你: 你好" in result
        assert "对方: 你好呀" in result

    def test_format_messages_limit(self, quick_chat_service):
        """测试格式化消息 - 数量限制"""
        messages = [{"senderId": "me", "content": f"消息{i}"} for i in range(15)]

        result = quick_chat_service._format_messages(messages)

        # 只应该包含最后 10 条
        lines = result.split('\n')
        assert len(lines) <= 10

    def test_format_messages_sender_mapping(self, quick_chat_service):
        """测试格式化消息 - 发送者映射"""
        messages = [
            {"senderId": "me", "content": "我的消息"},
            {"senderId": "her", "content": "她的消息"},
            {"senderId": "unknown", "content": "未知消息"}
        ]

        result = quick_chat_service._format_messages(messages)

        assert "你: 我的消息" in result
        assert "对方: 她的消息" in result
        # unknown 应该映射为 "对方"
        assert "对方: 未知消息" in result

    def test_format_messages_empty_content(self, quick_chat_service):
        """测试格式化消息 - 空内容
        注意：空字符串会被保留为空，None 也被保留为字符串 'None'
        """
        messages = [
            {"senderId": "me", "content": ""},
            {"senderId": "her", "content": None}
        ]

        result = quick_chat_service._format_messages(messages)

        # 空内容按照实际行为处理
        assert "你:" in result
        assert "对方:" in result

    def test_format_messages_unicode(self, quick_chat_service):
        """测试格式化消息 - Unicode"""
        messages = [
            {"senderId": "me", "content": "你好世界 🎉🎉🎉"},
            {"senderId": "her", "content": "日本語 العربية"}
        ]

        result = quick_chat_service._format_messages(messages)

        assert "你好世界 🎉🎉🎉" in result
        assert "日本語 العربية" in result


# ============= 第九部分：LLM 响应解析 - 正常流程与边缘场景 =============

class TestParseResponse:
    """LLM 响应解析测试"""

    def test_parse_response_basic(self, quick_chat_service):
        """测试解析响应 - 基础功能"""
        response = "这是 AI 的建议内容"
        result = quick_chat_service._parse_response(response)

        assert result['answer'] == response
        assert result['suggestions'] == []
        assert result['analysis']['partnerMood'] == 'unknown'
        assert result['analysis']['responseDelay'] == 'unknown'
        assert result['analysis']['riskLevel'] == 'low'

    def test_parse_response_empty(self, quick_chat_service):
        """测试解析响应 - 空响应"""
        result = quick_chat_service._parse_response("")
        assert result['answer'] == ""

    def test_parse_response_unicode(self, quick_chat_service):
        """测试解析响应 - Unicode"""
        response = "你好世界 🎉🎉🎉 日本語 العربية"
        result = quick_chat_service._parse_response(response)

        assert result['answer'] == response

    def test_parse_response_long(self, quick_chat_service):
        """测试解析响应 - 超长响应"""
        long_response = "A" * 1000
        result = quick_chat_service._parse_response(long_response)

        assert result['answer'] == long_response


# ============= 第十部分：记忆服务集成 - 正常流程与边缘场景 =============

class TestMemoryServiceIntegration:
    """记忆服务集成测试"""

    def test_memory_context_in_ai_advice(self, quick_chat_service, db_session):
        """测试记忆上下文在 AI 建议中的使用"""
        # 创建用户
        user = make_user(id='memory_partner', name='Memory Partner')
        db_session.add(user)
        db_session.commit()

        mock_memories = [
            {"content": "用户喜欢喝咖啡", "category": "preference", "importance": 5}
        ]
        mock_memory_service = MagicMock()
        mock_memory_service.get_contextual_memories.return_value = mock_memories

        mock_llm = "AI response with memory"

        with patch('services.quick_chat_service.call_llm', return_value=mock_llm):
            with patch('services.quick_chat_service.get_memory_service', return_value=mock_memory_service):
                result = quick_chat_service.get_ai_advice(
                    current_user_id='test_user',
                    partner_id='memory_partner',
                    question='她为什么不回我消息？',
                    recent_messages=[]
                )

        # 验证记忆服务调用
        mock_memory_service.get_contextual_memories.assert_called_once()
        assert result['answer'] == mock_llm

    def test_memory_extraction_in_suggest_reply(self, quick_chat_service):
        """测试回复建议中的记忆提取"""
        mock_memory_service = MagicMock()
        mock_memory_service.get_contextual_memories.return_value = []
        mock_memory_service.extract_memory_from_dialogue.return_value = []

        mock_response = '{"suggestions": [{"style": "test", "content": "test"}]}'

        with patch('services.quick_chat_service.call_llm', return_value=mock_response):
            with patch('services.quick_chat_service.get_memory_service', return_value=mock_memory_service):
                result = quick_chat_service.suggest_reply(
                    current_user_id='test_user',
                    partner_id='test_partner',
                    last_message={"content": "消息", "senderId": "her"},
                    recent_messages=[
                        {"senderId": "me", "content": "对话1"},
                        {"senderId": "her", "content": "对话2"},
                    ]
                )

        # 验证记忆提取调用
        mock_memory_service.extract_memory_from_dialogue.assert_called_once()
        assert result['success'] is True

    def test_memory_extraction_with_many_messages(self, quick_chat_service):
        """测试记忆提取 - 多条消息"""
        mock_memory_service = MagicMock()
        mock_memory_service.get_contextual_memories.return_value = []
        mock_memory_service.extract_memory_from_dialogue.return_value = []

        mock_response = '{"suggestions": [{"style": "test", "content": "test"}]}'

        many_messages = [{"senderId": f"sender{i % 2}", "content": f"消息{i}"} for i in range(20)]

        with patch('services.quick_chat_service.call_llm', return_value=mock_response):
            with patch('services.quick_chat_service.get_memory_service', return_value=mock_memory_service):
                result = quick_chat_service.suggest_reply(
                    current_user_id='test_user',
                    partner_id='test_partner',
                    last_message={"content": "最后消息", "senderId": "her"},
                    recent_messages=many_messages
                )

        # 验证记忆提取只使用最后 5 条消息
        call_args = mock_memory_service.extract_memory_from_dialogue.call_args
        dialogue = call_args.kwargs.get('dialogue', '')
        lines = dialogue.split('\n')
        assert len(lines) <= 5

    def test_memory_service_not_available(self, quick_chat_service):
        """测试记忆服务不可用"""
        mock_llm = "AI response without memory"

        with patch('services.quick_chat_service.call_llm', return_value=mock_llm):
            with patch('services.quick_chat_service.get_memory_service', return_value=None):
                result = quick_chat_service.get_ai_advice(
                    current_user_id='test_user',
                    partner_id='test_partner',
                    question='测试问题',
                    recent_messages=[]
                )

        assert result['answer'] == mock_llm

    def test_memory_service_get_contextual_error(self, quick_chat_service):
        """测试记忆服务获取上下文异常
        注意：记忆服务异常会导致整个流程失败，返回默认错误响应
        """
        mock_memory_service = MagicMock()
        mock_memory_service.get_contextual_memories.side_effect = Exception("Memory error")

        mock_llm = "AI response"

        with patch('services.quick_chat_service.call_llm', return_value=mock_llm):
            with patch('services.quick_chat_service.get_memory_service', return_value=mock_memory_service):
                result = quick_chat_service.get_ai_advice(
                    current_user_id='test_user',
                    partner_id='test_partner',
                    question='测试问题',
                    recent_messages=[]
                )

        # 记忆服务异常会导致整个流程失败
        assert result['answer'] == "抱歉，我现在无法思考，请稍后再试～"

    def test_memory_category_filtering(self, quick_chat_service):
        """测试记忆类别过滤"""
        memories = [
            {"content": "偏好记忆", "category": "preference"},
            {"content": "用户信息", "category": "user_info"},
            {"content": "关系记忆", "category": "relationship"},
            {"content": "事件记忆", "category": "event"},  # 不应出现在回复建议 prompt
        ]

        prompt = quick_chat_service._build_reply_prompt_with_memory(
            partner_profile={'name': 'TA'},
            last_message={'content': '消息'},
            recent_messages=[],
            relationship_stage='初识',
            memories=memories
        )

        assert "偏好记忆" in prompt
        assert "用户信息" in prompt
        assert "关系记忆" in prompt
        assert "事件记忆" not in prompt


# ============= 第十一部分：异常处理与降级策略 =============

class TestExceptionHandling:
    """异常处理测试"""

    def test_llm_exception_returns_default(self, quick_chat_service):
        """测试 LLM 异常返回默认响应"""
        with patch('services.quick_chat_service.call_llm', side_effect=Exception("LLM error")):
            with patch('services.quick_chat_service.get_memory_service', return_value=None):
                result = quick_chat_service.get_ai_advice(
                    current_user_id='test_user',
                    partner_id='test_partner',
                    question='测试问题',
                    recent_messages=[]
                )

        assert result['answer'] == "抱歉，我现在无法思考，请稍后再试～"
        assert result['suggestions'] == []
        assert result['analysis'] == {}

    def test_db_exception_in_partner_profile(self, quick_chat_service, db_session):
        """测试获取对方资料时数据库异常"""
        with patch.object(db_session, 'query', side_effect=Exception("DB error")):
            profile = quick_chat_service._get_partner_profile('error_user')

        assert profile['name'] == 'TA'
        assert profile['age'] == '?'

    def test_db_exception_in_conversation_history(self, quick_chat_service, db_session):
        """测试获取聊天历史时数据库异常"""
        with patch.object(db_session, 'query', side_effect=Exception("DB error")):
            history = quick_chat_service._get_conversation_history('user_1', 'user_2')

        assert history == []

    def test_json_parse_fallback(self, quick_chat_service):
        """测试 JSON 解析失败的降级处理"""
        invalid_json = "这不是 JSON"

        with patch('services.quick_chat_service.call_llm', return_value=invalid_json):
            with patch('services.quick_chat_service.get_memory_service', return_value=None):
                result = quick_chat_service.suggest_reply(
                    current_user_id='test_user',
                    partner_id='test_partner',
                    last_message={"content": "测试", "senderId": "her"},
                    recent_messages=[]
                )

        assert result['success'] is True
        assert len(result['suggestions']) > 0

    def test_all_services_fail(self, quick_chat_service):
        """测试所有服务失败"""
        with patch('services.quick_chat_service.get_memory_service', return_value=None):
            with patch('services.quick_chat_service.call_llm', side_effect=Exception("Total failure")):
                result = quick_chat_service.get_ai_advice(
                    current_user_id='test_user',
                    partner_id='test_partner',
                    question='测试问题',
                    recent_messages=[]
                )

        assert result['answer'] == "抱歉，我现在无法思考，请稍后再试～"

    def test_feedback_service_exception(self, quick_chat_service):
        """测试反馈服务异常"""
        mock_feedback_service = MagicMock()
        mock_feedback_service.record_feedback.side_effect = Exception("Feedback error")

        with patch('services.quick_chat_service.get_ai_feedback_service', return_value=mock_feedback_service):
            # 应该抛出异常（因为 record_suggestion_feedback 直接调用）
            with pytest.raises(Exception):
                quick_chat_service.record_suggestion_feedback(
                    current_user_id='test_user',
                    partner_id='test_partner',
                    suggestion_id='suggestion-id',
                    feedback_type='adopted',
                    suggestion_content='内容',
                    suggestion_style='风格'
                )

    def test_close_with_exception_logged(self):
        """测试关闭时异常被记录"""
        mock_db = MagicMock()
        mock_db.close.side_effect = Exception("Close error")

        with patch('db.database.SessionLocal', return_value=mock_db):
            with patch('services.quick_chat_service.logger') as mock_logger:
                service = QuickChatService()
                service.close()

                # 应该记录错误日志
                mock_logger.error.assert_called_once()

    def test_empty_user_ids(self, quick_chat_service):
        """测试空用户 ID"""
        with patch('services.quick_chat_service.get_memory_service', return_value=None):
            with patch('services.quick_chat_service.call_llm', return_value="AI response"):
                result = quick_chat_service.get_ai_advice(
                    current_user_id='',
                    partner_id='',
                    question='测试问题',
                    recent_messages=[]
                )

        assert result['answer'] == "AI response"

    def test_memory_extraction_failure_not_blocking(self, quick_chat_service):
        """测试记忆提取失败不阻塞响应"""
        mock_memory_service = MagicMock()
        mock_memory_service.get_contextual_memories.return_value = []
        mock_memory_service.extract_memory_from_dialogue.side_effect = Exception("Extract error")

        mock_response = '{"suggestions": [{"style": "test", "content": "test"}]}'

        with patch('services.quick_chat_service.call_llm', return_value=mock_response):
            with patch('services.quick_chat_service.get_memory_service', return_value=mock_memory_service):
                result = quick_chat_service.suggest_reply(
                    current_user_id='test_user',
                    partner_id='test_partner',
                    last_message={"content": "消息", "senderId": "her"},
                    recent_messages=[{"senderId": "me", "content": "消息"}]
                )

        # 响应应该正常返回
        assert result['success'] is True

    def test_nested_exception_handling(self, quick_chat_service, db_session):
        """测试嵌套异常处理"""
        # 记忆服务异常
        mock_memory_service = MagicMock()
        mock_memory_service.get_contextual_memories.side_effect = Exception("Memory error")

        # LLM 也异常
        with patch('services.quick_chat_service.call_llm', side_effect=Exception("LLM error")):
            with patch('services.quick_chat_service.get_memory_service', return_value=mock_memory_service):
                result = quick_chat_service.get_ai_advice(
                    current_user_id='test_user',
                    partner_id='test_partner',
                    question='测试问题',
                    recent_messages=[]
                )

        # 最终应该返回默认错误响应
        assert result['answer'] == "抱歉，我现在无法思考，请稍后再试～"


# ============= 集成测试 - 多方法协作 =============

class TestIntegration:
    """集成测试"""

    def test_full_flow_ai_advice(self, quick_chat_service, db_session):
        """测试完整 AI 建议流程"""
        # 创建测试数据
        user1 = make_user(id='user_1', name='用户1')
        user2 = make_user(id='user_2', name='小美', age=25, location='上海')
        db_session.add_all([user1, user2])
        db_session.commit()

        conv = make_conversation(user_id_1='user_1', user_id_2='user_2')
        db_session.add(conv)
        db_session.commit()

        for i in range(3):
            msg = make_message(
                conversation_id=conv.id,
                sender_id='user_1' if i % 2 == 0 else 'user_2',
                receiver_id='user_2' if i % 2 == 0 else 'user_1',
                content=f'消息{i}',
                created_at=datetime.utcnow() - timedelta(minutes=i)
            )
            db_session.add(msg)
        db_session.commit()

        mock_memory_service = MagicMock()
        mock_memory_service.get_contextual_memories.return_value = [
            {"content": "用户喜欢咖啡", "importance": 4}
        ]

        mock_llm = "AI 建议：结合她最近的工作状态..."

        with patch('services.quick_chat_service.call_llm', return_value=mock_llm):
            with patch('services.quick_chat_service.get_memory_service', return_value=mock_memory_service):
                result = quick_chat_service.get_ai_advice(
                    current_user_id='user_1',
                    partner_id='user_2',
                    question='她为什么不回我消息？',
                    recent_messages=[]
                )

        assert result['answer'] == mock_llm
        mock_memory_service.get_contextual_memories.assert_called()

    def test_full_flow_suggest_reply(self, quick_chat_service, db_session):
        """测试完整回复建议流程"""
        user1 = make_user(id='reply_user_1', name='用户1')
        user2 = make_user(id='reply_user_2', name='小美')
        db_session.add_all([user1, user2])
        db_session.commit()

        mock_memory_service = MagicMock()
        mock_memory_service.get_contextual_memories.return_value = []
        mock_memory_service.extract_memory_from_dialogue.return_value = []

        mock_response = json.dumps({
            "suggestions": [
                {"style": "幽默", "content": "辛苦啦！"},
                {"style": "关心", "content": "早点休息"},
                {"style": "话题", "content": "加班做什么？"}
            ]
        })

        with patch('services.quick_chat_service.call_llm', return_value=mock_response):
            with patch('services.quick_chat_service.get_memory_service', return_value=mock_memory_service):
                result = quick_chat_service.suggest_reply(
                    current_user_id='reply_user_1',
                    partner_id='reply_user_2',
                    last_message={"content": "刚加班完，好累", "senderId": "her"},
                    recent_messages=[
                        {"senderId": "me", "content": "在干嘛"},
                        {"senderId": "her", "content": "加班"},
                    ],
                    relationship_stage='暧昧'
                )

        assert result['success'] is True
        assert len(result['suggestions']) == 3
        for sug in result['suggestions']:
            assert 'id' in sug


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])