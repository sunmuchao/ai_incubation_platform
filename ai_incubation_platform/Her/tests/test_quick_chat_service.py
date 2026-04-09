"""
QuickChat 服务测试

测试覆盖:
- AI 建议生成
- 回复建议生成
- 记忆检索集成
- 反馈记录集成
"""
import pytest
import os
import sys
import json
from unittest.mock import MagicMock, patch

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置环境变量
os.environ['OPENAI_API_KEY'] = 'test-key'
os.environ['OPENAI_BASE_URL'] = 'https://test.api/v1'

from services.quick_chat_service import QuickChatService


class TestQuickChatService:
    """QuickChat 服务测试"""

    @pytest.fixture
    def quick_chat_service(self):
        """创建测试服务"""
        # 使用 mock 数据库会话
        service = QuickChatService()
        yield service
        service.close()

    def test_init(self, quick_chat_service):
        """测试初始化"""
        assert quick_chat_service is not None
        assert quick_chat_service.db is not None

    def test_get_ai_advice_basic(self, quick_chat_service, monkeypatch):
        """测试获取 AI 建议 - 基础功能"""
        # Mock LLM 响应
        mock_response = "她可能在忙，建议等她忙完再联系。"

        def mock_call_llm(*args, **kwargs):
            return mock_response

        monkeypatch.setattr('services.quick_chat_service.call_llm', mock_call_llm)

        # Mock 记忆服务
        mock_memory_service = MagicMock()
        mock_memory_service.get_contextual_memories.return_value = []
        monkeypatch.setattr(
            'services.quick_chat_service.get_memory_service',
            lambda: mock_memory_service
        )

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

    def test_get_ai_advice_with_memory(self, quick_chat_service, monkeypatch):
        """测试获取 AI 建议 - 带记忆检索"""
        mock_response = "结合你之前说她工作忙，她可能真的在加班。"

        def mock_call_llm(*args, **kwargs):
            return mock_response

        monkeypatch.setattr('services.quick_chat_service.call_llm', mock_call_llm)

        # Mock 记忆服务返回相关记忆
        mock_memories = [
            {
                "content": "用户女朋友工作很忙，经常加班",
                "category": "relationship",
                "importance": 4
            }
        ]

        mock_memory_service = MagicMock()
        mock_memory_service.get_contextual_memories.return_value = mock_memories
        monkeypatch.setattr(
            'services.quick_chat_service.get_memory_service',
            lambda: mock_memory_service
        )

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
        # 验证记忆服务被调用
        mock_memory_service.get_contextual_memories.assert_called_once()

    def test_get_ai_advice_error_handling(self, quick_chat_service, monkeypatch):
        """测试获取 AI 建议 - 错误处理"""
        def mock_call_llm(*args, **kwargs):
            raise Exception("LLM API 错误")

        monkeypatch.setattr('services.quick_chat_service.call_llm', mock_call_llm)

        result = quick_chat_service.get_ai_advice(
            current_user_id='test_user',
            partner_id='test_partner',
            question='测试问题',
            recent_messages=[]
        )

        # 应该返回默认错误响应
        assert result['answer'] == "抱歉，我现在无法思考，请稍后再试～"

    def test_suggest_reply_basic(self, quick_chat_service, monkeypatch):
        """测试生成回复建议 - 基础功能"""
        mock_response = '''
        {
            "suggestions": [
                {"style": "幽默风趣", "content": "辛苦啦！奶茶已点，请注意查收～"},
                {"style": "真诚关心", "content": "这么晚还在工作，太辛苦了吧"},
                {"style": "延续话题", "content": "加班到这么晚啊，做什么项目？"}
            ]
        }
        '''

        def mock_call_llm(*args, **kwargs):
            return mock_response

        monkeypatch.setattr('services.quick_chat_service.call_llm', mock_call_llm)

        # Mock 记忆服务
        mock_memory_service = MagicMock()
        mock_memory_service.get_contextual_memories.return_value = []
        mock_memory_service.extract_memory_from_dialogue.return_value = []
        monkeypatch.setattr(
            'services.quick_chat_service.get_memory_service',
            lambda: mock_memory_service
        )

        result = quick_chat_service.suggest_reply(
            current_user_id='test_user',
            partner_id='test_partner',
            last_message={"content": "刚加班完，好累", "senderId": "her"},
            recent_messages=[
                {"senderId": "her", "content": "刚加班完，好累"}
            ],
            relationship_stage='初识'
        )

        assert isinstance(result, dict)
        assert result['success'] is True
        assert 'suggestions' in result
        assert len(result['suggestions']) > 0

    def test_suggest_reply_with_id(self, quick_chat_service, monkeypatch):
        """测试生成回复建议 - 包含 ID（用于反馈追踪）"""
        mock_response = '''
        {
            "suggestions": [
                {"style": "幽默风趣", "content": "辛苦啦！"},
                {"style": "真诚关心", "content": "早点休息"}
            ]
        }
        '''

        def mock_call_llm(*args, **kwargs):
            return mock_response

        monkeypatch.setattr('services.quick_chat_service.call_llm', mock_call_llm)

        mock_memory_service = MagicMock()
        mock_memory_service.get_contextual_memories.return_value = []
        mock_memory_service.extract_memory_from_dialogue.return_value = []
        monkeypatch.setattr(
            'services.quick_chat_service.get_memory_service',
            lambda: mock_memory_service
        )

        result = quick_chat_service.suggest_reply(
            current_user_id='test_user',
            partner_id='test_partner',
            last_message={"content": "累了", "senderId": "her"},
            recent_messages=[]
        )

        # 验证每个建议都有 ID
        for suggestion in result['suggestions']:
            assert 'id' in suggestion

    def test_suggest_reply_json_parse_error(self, quick_chat_service, monkeypatch):
        """测试生成回复建议 - JSON 解析错误降级"""
        def mock_call_llm(*args, **kwargs):
            return "这不是有效的 JSON"

        monkeypatch.setattr('services.quick_chat_service.call_llm', mock_call_llm)

        mock_memory_service = MagicMock()
        mock_memory_service.get_contextual_memories.return_value = []
        mock_memory_service.extract_memory_from_dialogue.return_value = []
        monkeypatch.setattr(
            'services.quick_chat_service.get_memory_service',
            lambda: mock_memory_service
        )

        result = quick_chat_service.suggest_reply(
            current_user_id='test_user',
            partner_id='test_partner',
            last_message={"content": "测试", "senderId": "her"},
            recent_messages=[]
        )

        assert result['success'] is True
        assert len(result['suggestions']) > 0

    def test_suggest_reply_with_memory(self, quick_chat_service, monkeypatch):
        """测试生成回复建议 - 带记忆检索"""
        mock_response = '{"suggestions": [{"style": "幽默风趣", "content": "测试"}]}'

        def mock_call_llm(*args, **kwargs):
            return mock_response

        monkeypatch.setattr('services.quick_chat_service.call_llm', mock_call_llm)

        mock_memories = [
            {
                "content": "用户喜欢喝奶茶",
                "category": "preference",
                "importance": 4
            }
        ]

        mock_memory_service = MagicMock()
        mock_memory_service.get_contextual_memories.return_value = mock_memories
        mock_memory_service.extract_memory_from_dialogue.return_value = []
        monkeypatch.setattr(
            'services.quick_chat_service.get_memory_service',
            lambda: mock_memory_service
        )

        result = quick_chat_service.suggest_reply(
            current_user_id='test_user',
            partner_id='test_partner',
            last_message={"content": "累了", "senderId": "her"},
            recent_messages=[]
        )

        # 验证记忆服务被调用
        mock_memory_service.get_contextual_memories.assert_called_once()

    def test_suggest_reply_memory_extraction(self, quick_chat_service, monkeypatch):
        """测试生成回复建议 - 记忆提取"""
        mock_response = '{"suggestions": [{"style": "幽默风趣", "content": "测试"}]}'

        def mock_call_llm(*args, **kwargs):
            return mock_response

        monkeypatch.setattr('services.quick_chat_service.call_llm', mock_call_llm)

        mock_memory_service = MagicMock()
        mock_memory_service.get_contextual_memories.return_value = []
        mock_memory_service.extract_memory_from_dialogue.return_value = []
        monkeypatch.setattr(
            'services.quick_chat_service.get_memory_service',
            lambda: mock_memory_service
        )

        result = quick_chat_service.suggest_reply(
            current_user_id='test_user',
            partner_id='test_partner',
            last_message={"content": "累了", "senderId": "her"},
            recent_messages=[
                {"senderId": "me", "content": "在干嘛"},
                {"senderId": "her", "content": "累了"}
            ]
        )

        # 验证记忆提取被调用（如果有聊天记录）
        mock_memory_service.extract_memory_from_dialogue.assert_called()

    def test_record_suggestion_feedback(self, quick_chat_service, monkeypatch):
        """测试记录建议反馈"""
        mock_feedback_id = 'feedback-uuid-001'

        mock_feedback_service = MagicMock()
        mock_feedback_service.record_feedback.return_value = mock_feedback_id
        monkeypatch.setattr(
            'services.quick_chat_service.get_ai_feedback_service',
            lambda: mock_feedback_service
        )

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

    def test_format_messages_empty(self, quick_chat_service):
        """测试空消息列表格式化"""
        result = quick_chat_service._format_messages([])
        assert result == "暂无聊天记录"

    def test_format_messages_limit(self, quick_chat_service):
        """测试消息数量限制"""
        messages = [{"senderId": "me", "content": f"消息{i}"} for i in range(15)]

        result = quick_chat_service._format_messages(messages)

        # 只应该包含最后 10 条
        assert result.count("\n") <= 9


class TestQuickChatServicePartnerProfile:
    """对方资料测试"""

    @pytest.fixture
    def service_with_db(self):
        """创建带数据库连接的服务"""
        from db.database import SessionLocal
        service = QuickChatService(db=SessionLocal())
        yield service
        service.close()

    def test_get_partner_profile_nonexistent(self, quick_chat_service, monkeypatch):
        """测试获取不存在的用户资料"""
        # Mock 数据库查询返回 None
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None
        quick_chat_service.db.query.return_value = mock_query

        profile = quick_chat_service._get_partner_profile('nonexistent-user')

        assert profile['name'] == 'TA'
        assert profile['age'] == '?'
        assert profile['location'] == '未知'


class TestQuickChatServicePrompts:
    """Prompt 构建测试"""

    @pytest.fixture
    def quick_chat_service(self):
        return QuickChatService()

    def test_build_prompt_with_memory_empty(self, quick_chat_service):
        """测试带记忆的 Prompt 构建 - 无记忆"""
        prompt = quick_chat_service._build_prompt_with_memory(
            question='测试问题',
            partner_profile={'name': '小美'},
            recent_messages=[],
            memories=[]
        )

        assert '测试问题' in prompt
        assert '小美' in prompt
        assert '暂无相关记忆' in prompt

    def test_build_prompt_with_memory_present(self, quick_chat_service):
        """测试带记忆的 Prompt 构建 - 有记忆"""
        memories = [
            {"content": "用户喜欢喝奶茶", "importance": 4},
            {"content": "用户工作很忙", "importance": 5}
        ]

        prompt = quick_chat_service._build_prompt_with_memory(
            question='测试问题',
            partner_profile={'name': '小美'},
            recent_messages=[],
            memories=memories
        )

        assert '用户喜欢喝奶茶' in prompt
        assert '用户工作很忙' in prompt

    def test_build_reply_prompt_with_memory(self, quick_chat_service):
        """测试回复建议 Prompt 构建 - 带记忆"""
        memories = [
            {"content": "用户喜欢喝奶茶", "category": "preference"}
        ]

        prompt = quick_chat_service._build_reply_prompt_with_memory(
            partner_profile={'name': '小美'},
            last_message={'content': '累了'},
            recent_messages=[],
            relationship_stage='初识',
            memories=memories
        )

        assert '用户喜欢喝奶茶' in prompt
        assert '小美' in prompt
        assert '累了' in prompt
