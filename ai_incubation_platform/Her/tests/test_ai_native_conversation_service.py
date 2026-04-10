"""
AI Native 对话服务测试

覆盖范围:
- AINativeConversationService (src/services/ai_native_conversation_service.py)
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime
import json

from services.ai_native_conversation_service import (
    AINativeConversationService,
    KnowledgeDimension,
)


class TestKnowledgeDimension:
    """测试 KnowledgeDimension 类"""

    def test_init(self):
        """测试初始化"""
        dim = KnowledgeDimension(
            name="测试维度",
            priority=1,
            description="测试描述",
            keywords=["关键词1", "关键词2"]
        )

        assert dim.name == "测试维度"
        assert dim.priority == 1
        assert dim.description == "测试描述"
        assert dim.keywords == ["关键词1", "关键词2"]
        assert dim.collected is False
        assert dim.confidence == 0.0
        assert dim.raw_data is None

    def test_collected_flag(self):
        """测试收集状态设置"""
        dim = KnowledgeDimension(
            name="测试",
            priority=1,
            description="描述",
            keywords=[]
        )

        dim.collected = True
        dim.confidence = 0.8
        dim.raw_data = {"key": "value"}

        assert dim.collected is True
        assert dim.confidence == 0.8
        assert dim.raw_data == {"key": "value"}


class TestAINativeConversationServiceInit:
    """测试 AINativeConversationService 初始化"""

    def test_init(self):
        """测试服务初始化"""
        service = AINativeConversationService()

        assert service.sessions == {}
        assert "basic" in service.dimensions
        assert "relationship_goal" in service.dimensions
        assert "ideal_type" in service.dimensions
        assert "personality" in service.dimensions
        assert "lifestyle" in service.dimensions
        assert "interests" in service.dimensions
        assert "values" in service.dimensions

    def test_dimensions_priorities(self):
        """测试知识维度优先级排序"""
        service = AINativeConversationService()

        # 检查优先级
        assert service.dimensions["basic"].priority == 1
        assert service.dimensions["relationship_goal"].priority == 2
        assert service.dimensions["ideal_type"].priority == 3


class TestStartConversation:
    """测试开始对话"""

    @patch('services.ai_native_conversation_service.call_llm')
    @patch('services.ai_native_conversation_service.db_session_readonly')
    def test_start_conversation_new_user(self, mock_db_session, mock_call_llm):
        """测试新用户开始对话"""
        # Mock 数据库会话
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db_session.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_db_session.return_value.__exit__ = MagicMock(return_value=False)

        # Mock LLM 返回
        mock_call_llm.return_value = "你好呀～很高兴认识你！😊"

        service = AINativeConversationService()
        result = service.start_conversation("user-123", "小明")

        assert result["user_id"] == "user-123"
        assert result["user_name"] == "小明"
        assert "ai_message" in result
        assert result["is_completed"] is False
        assert result["current_stage"] == "dynamic_conversation"
        assert "user-123" in service.sessions

    @patch('services.ai_native_conversation_service.call_llm')
    @patch('services.ai_native_conversation_service.db_session_readonly')
    def test_start_conversation_with_existing_profile(self, mock_db_session, mock_call_llm):
        """测试已有资料用户开始对话"""
        # Mock 用户数据
        mock_user = MagicMock()
        mock_user.id = "user-123"
        mock_user.name = "小明"
        mock_user.age = 28
        mock_user.gender = "male"
        mock_user.location = "北京"
        mock_user.bio = "热爱生活"
        mock_user.interests = ["阅读", "旅行"]
        mock_user.goal = "serious"
        mock_user.preferred_age_min = 22
        mock_user.preferred_age_max = 32
        mock_user.preferred_location = "北京"
        mock_user.preferred_gender = "female"

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        mock_db_session.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_db_session.return_value.__exit__ = MagicMock(return_value=False)

        # Mock LLM 返回
        mock_call_llm.return_value = "小明你好呀～看到你28岁在北京，想找认真恋爱的对象～"

        service = AINativeConversationService()
        result = service.start_conversation("user-123", "小明")

        assert result["user_id"] == "user-123"
        # 检查已收集的维度
        state = service.sessions["user-123"]
        assert state.knowledge_base["basic"].collected is True
        assert state.knowledge_base["interests"].collected is True
        assert state.knowledge_base["relationship_goal"].collected is True

    @patch('services.ai_native_conversation_service.call_llm')
    @patch('services.ai_native_conversation_service.db_session_readonly')
    def test_start_conversation_llm_failure(self, mock_db_session, mock_call_llm):
        """测试 LLM 调用失败时的降级处理"""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db_session.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_db_session.return_value.__exit__ = MagicMock(return_value=False)

        # Mock LLM 抛出异常
        mock_call_llm.side_effect = Exception("LLM API Error")

        service = AINativeConversationService()
        result = service.start_conversation("user-123", "小明")

        # 应该返回默认消息
        assert "ai_message" in result
        assert "很高兴认识你" in result["ai_message"] or "你好" in result["ai_message"]


class TestProcessUserMessage:
    """测试处理用户消息"""

    @patch('services.ai_native_conversation_service.call_llm')
    @patch('services.ai_native_conversation_service.db_session_readonly')
    def test_process_user_message(self, mock_db_session, mock_call_llm):
        """测试处理用户消息"""
        # 先创建会话
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db_session.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_db_session.return_value.__exit__ = MagicMock(return_value=False)
        mock_call_llm.return_value = "你好呀～"

        service = AINativeConversationService()
        service.start_conversation("user-123", "小明")

        # Mock LLM 返回 JSON
        mock_call_llm.return_value = json.dumps({
            "extractions": {
                "relationship_goal": "认真恋爱"
            },
            "ai_response": "认真恋爱最好了～那你理想中的感情是什么样的？"
        })

        result = service.process_user_message("user-123", "我想找个认真恋爱的")

        assert "ai_message" in result
        assert result["user_id"] == "user-123"
        assert "conversation_count" in result

    @patch('services.ai_native_conversation_service.call_llm')
    @patch('services.ai_native_conversation_service.db_session_readonly')
    def test_process_user_message_no_session(self, mock_db_session, mock_call_llm):
        """测试无会话时处理用户消息"""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db_session.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_db_session.return_value.__exit__ = MagicMock(return_value=False)
        mock_call_llm.return_value = "你好呀～"

        service = AINativeConversationService()
        result = service.process_user_message("user-456", "你好")

        # 应该自动创建新会话
        assert result["user_id"] == "user-456"
        assert "user-456" in service.sessions

    @patch('services.ai_native_conversation_service.call_llm')
    @patch('services.ai_native_conversation_service.db_session_readonly')
    def test_process_user_message_complete_conversation(self, mock_db_session, mock_call_llm):
        """测试完成对话"""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db_session.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_db_session.return_value.__exit__ = MagicMock(return_value=False)
        mock_call_llm.return_value = "你好呀～"

        service = AINativeConversationService()
        service.start_conversation("user-123", "小明")

        # 模拟高了解度状态
        state = service.sessions["user-123"]
        for dim in state.knowledge_base.values():
            dim.collected = True
            dim.confidence = 1.0
            dim.raw_data = "已收集"
        state.overall_understanding = 0.8

        mock_call_llm.return_value = "太好了～我已经对你有了初步的了解！"

        result = service.process_user_message("user-123", "好的没问题")

        # 对话应该标记为完成
        assert state.is_completed is True


class TestParseJsonResponse:
    """测试 JSON 解析"""

    def test_parse_json_with_markdown_block(self):
        """测试解析带 markdown 代码块的 JSON"""
        service = AINativeConversationService()

        response = '''```json
{"key": "value", "number": 123}
```'''
        result = service._parse_json_response(response)

        assert result == {"key": "value", "number": 123}

    def test_parse_json_plain(self):
        """测试解析普通 JSON"""
        service = AINativeConversationService()

        response = '{"key": "value", "number": 123}'
        result = service._parse_json_response(response)

        assert result == {"key": "value", "number": 123}

    def test_parse_json_with_extra_whitespace(self):
        """测试解析带额外空白的 JSON"""
        service = AINativeConversationService()

        response = '''
        {"key": "value"}
        '''
        result = service._parse_json_response(response)

        assert result == {"key": "value"}


class TestUpdateKnowledgeBase:
    """测试知识图谱更新"""

    def test_update_knowledge_base(self):
        """测试更新知识图谱"""
        service = AINativeConversationService()

        # 创建测试会话状态
        state = service.ConversationState("user-123", "小明")
        state.knowledge_base = {k: KnowledgeDimension(
            name=d.name, priority=d.priority, description=d.description, keywords=d.keywords
        ) for k, d in service.dimensions.items()}

        extracted_info = {
            "extractions": {
                "relationship_goal": "认真恋爱",
                "ideal_type": "温柔善良"
            },
            "confidence": 0.8
        }

        service._update_knowledge_base(state, extracted_info)

        assert state.knowledge_base["relationship_goal"].collected is True
        assert state.knowledge_base["relationship_goal"].raw_data == "认真恋爱"
        assert state.knowledge_base["ideal_type"].collected is True
        assert state.knowledge_base["ideal_type"].raw_data == "温柔善良"

    def test_update_knowledge_base_empty_extractions(self):
        """测试空提取信息"""
        service = AINativeConversationService()

        state = service.ConversationState("user-123", "小明")
        state.knowledge_base = {k: KnowledgeDimension(
            name=d.name, priority=d.priority, description=d.description, keywords=d.keywords
        ) for k, d in service.dimensions.items()}

        extracted_info = {
            "extractions": {},
            "confidence": 0.5
        }

        service._update_knowledge_base(state, extracted_info)

        # 没有信息被收集
        for dim in state.knowledge_base.values():
            assert dim.collected is False


class TestEvaluateUnderstanding:
    """测试了解度评估"""

    def test_evaluate_understanding_empty(self):
        """测试空状态评估"""
        service = AINativeConversationService()

        state = service.ConversationState("user-123", "小明")
        state.knowledge_base = {k: KnowledgeDimension(
            name=d.name, priority=d.priority, description=d.description, keywords=d.keywords
        ) for k, d in service.dimensions.items()}

        service._evaluate_understanding(state)

        assert state.overall_understanding == 0.0

    def test_evaluate_understanding_partial(self):
        """测试部分收集状态"""
        service = AINativeConversationService()

        state = service.ConversationState("user-123", "小明")
        state.knowledge_base = {k: KnowledgeDimension(
            name=d.name, priority=d.priority, description=d.description, keywords=d.keywords
        ) for k, d in service.dimensions.items()}

        # 收集部分维度
        state.knowledge_base["basic"].collected = True
        state.knowledge_base["basic"].confidence = 1.0
        state.knowledge_base["relationship_goal"].collected = True
        state.knowledge_base["relationship_goal"].confidence = 0.8

        service._evaluate_understanding(state)

        assert 0 < state.overall_understanding < 1

    def test_evaluate_understanding_complete(self):
        """测试完全收集状态"""
        service = AINativeConversationService()

        state = service.ConversationState("user-123", "小明")
        state.knowledge_base = {k: KnowledgeDimension(
            name=d.name, priority=d.priority, description=d.description, keywords=d.keywords
        ) for k, d in service.dimensions.items()}

        # 收集所有维度
        for dim in state.knowledge_base.values():
            dim.collected = True
            dim.confidence = 1.0

        service._evaluate_understanding(state)

        assert state.overall_understanding == 1.0


class TestGetSessionStatus:
    """测试获取会话状态"""

    @patch('services.ai_native_conversation_service.call_llm')
    @patch('services.ai_native_conversation_service.db_session_readonly')
    def test_get_session_status_exists(self, mock_db_session, mock_call_llm):
        """测试获取存在会话的状态"""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db_session.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_db_session.return_value.__exit__ = MagicMock(return_value=False)
        mock_call_llm.return_value = "你好呀～"

        service = AINativeConversationService()
        service.start_conversation("user-123", "小明")

        result = service.get_session_status("user-123")

        assert result["exists"] is True
        assert result["user_id"] == "user-123"
        assert result["user_name"] == "小明"
        assert "understanding_level" in result
        assert "collected_dimensions" in result

    def test_get_session_status_not_exists(self):
        """测试获取不存在会话的状态"""
        service = AINativeConversationService()

        result = service.get_session_status("nonexistent-user")

        assert result["exists"] is False


class TestMarkExistingInfo:
    """测试标记已有信息"""

    def test_mark_basic_info(self):
        """测试标记基本信息"""
        service = AINativeConversationService()

        state = service.ConversationState("user-123", "小明")
        state.knowledge_base = {k: KnowledgeDimension(
            name=d.name, priority=d.priority, description=d.description, keywords=d.keywords
        ) for k, d in service.dimensions.items()}

        existing_profile = {
            "name": "小明",
            "age": 28,
            "gender": "male",
            "location": "北京"
        }

        service._mark_existing_info(state, existing_profile)

        assert state.knowledge_base["basic"].collected is True
        assert state.knowledge_base["basic"].confidence == 1.0
        assert state.knowledge_base["basic"].raw_data == existing_profile

    def test_mark_interests_list(self):
        """测试标记兴趣列表"""
        service = AINativeConversationService()

        state = service.ConversationState("user-123", "小明")
        state.knowledge_base = {k: KnowledgeDimension(
            name=d.name, priority=d.priority, description=d.description, keywords=d.keywords
        ) for k, d in service.dimensions.items()}

        existing_profile = {
            "interests": ["阅读", "旅行", "音乐"]
        }

        service._mark_existing_info(state, existing_profile)

        assert state.knowledge_base["interests"].collected is True
        assert state.knowledge_base["interests"].confidence == 1.0

    def test_mark_interests_json_string(self):
        """测试标记 JSON 字符串格式的兴趣"""
        service = AINativeConversationService()

        state = service.ConversationState("user-123", "小明")
        state.knowledge_base = {k: KnowledgeDimension(
            name=d.name, priority=d.priority, description=d.description, keywords=d.keywords
        ) for k, d in service.dimensions.items()}

        existing_profile = {
            "interests": '["阅读", "旅行"]'
        }

        service._mark_existing_info(state, existing_profile)

        assert state.knowledge_base["interests"].collected is True

    def test_mark_goal(self):
        """测试标记关系目标"""
        service = AINativeConversationService()

        state = service.ConversationState("user-123", "小明")
        state.knowledge_base = {k: KnowledgeDimension(
            name=d.name, priority=d.priority, description=d.description, keywords=d.keywords
        ) for k, d in service.dimensions.items()}

        existing_profile = {
            "goal": "serious"
        }

        service._mark_existing_info(state, existing_profile)

        assert state.knowledge_base["relationship_goal"].collected is True
        assert state.knowledge_base["relationship_goal"].raw_data == "serious"

    def test_mark_bio_lifestyle_hint(self):
        """测试从简介推断生活方式"""
        service = AINativeConversationService()

        state = service.ConversationState("user-123", "小明")
        state.knowledge_base = {k: KnowledgeDimension(
            name=d.name, priority=d.priority, description=d.description, keywords=d.keywords
        ) for k, d in service.dimensions.items()}

        existing_profile = {
            "bio": "我是一个热爱生活的人，喜欢运动和旅行，周末经常去爬山。"
        }

        service._mark_existing_info(state, existing_profile)

        # bio 超过 20 字符，应该标记 lifestyle 为部分收集
        assert state.knowledge_base["lifestyle"].collected is True
        assert state.knowledge_base["lifestyle"].confidence == 0.5


class TestGenerateWelcomeMessage:
    """测试生成欢迎消息"""

    @patch('services.ai_native_conversation_service.call_llm')
    def test_generate_welcome_with_profile(self, mock_call_llm):
        """测试有资料时生成欢迎消息"""
        mock_call_llm.return_value = "小明你好呀～看到你28岁在北京，想找个认真恋爱的对象吧？😊"

        service = AINativeConversationService()

        existing_profile = {
            "name": "小明",
            "age": 28,
            "location": "北京"
        }

        message = service._generate_welcome_message("小明", existing_profile)

        assert "小明" in message or "你好" in message
        mock_call_llm.assert_called_once()

    @patch('services.ai_native_conversation_service.call_llm')
    def test_generate_welcome_without_profile(self, mock_call_llm):
        """测试无资料时生成欢迎消息"""
        mock_call_llm.return_value = "你好呀～很高兴认识你！让我了解一下你吧～"

        service = AINativeConversationService()

        message = service._generate_welcome_message("小红", None)

        assert len(message) > 0
        mock_call_llm.assert_called_once()

    @patch('services.ai_native_conversation_service.call_llm')
    def test_generate_welcome_llm_failure(self, mock_call_llm):
        """测试 LLM 失败时的降级消息"""
        mock_call_llm.side_effect = Exception("LLM Error")

        service = AINativeConversationService()

        message = service._generate_welcome_message("小明", None)

        # 应该返回默认消息
        assert "你好" in message or "很高兴" in message


class TestBuildStreamPrompt:
    """测试构建流式 Prompt"""

    @patch('services.ai_native_conversation_service.call_llm')
    @patch('services.ai_native_conversation_service.db_session_readonly')
    def test_build_stream_prompt(self, mock_db_session, mock_call_llm):
        """测试构建流式输出 prompt"""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db_session.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_db_session.return_value.__exit__ = MagicMock(return_value=False)
        mock_call_llm.return_value = "你好呀～"

        service = AINativeConversationService()
        service.start_conversation("user-123", "小明")

        state = service.sessions["user-123"]
        state.conversation_history = [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好呀～"},
            {"role": "user", "content": "我想找个认真恋爱的"}
        ]

        prompt = service._build_stream_prompt(state, "我想找个认真恋爱的")

        assert "AI 助手" in prompt or "AI_PERSONA" in prompt
        assert "认真恋爱" in prompt


class TestExtractFromResponse:
    """测试从回复中提取信息"""

    def test_extract_from_response(self):
        """测试从回复中提取信息（简化版）"""
        service = AINativeConversationService()

        result = service._extract_from_response("这是一个测试回复")

        # 当前实现返回空字典
        assert result == {}


class TestGenerateFarewellMessage:
    """测试生成结束语"""

    @patch('services.ai_native_conversation_service.call_llm')
    def test_generate_farewell(self, mock_call_llm):
        """测试生成结束语"""
        mock_call_llm.return_value = "太好了～我已经对你有了初步的了解！祝你找到属于你的幸福 🌸"

        service = AINativeConversationService()
        state = service.ConversationState("user-123", "小明")
        state.knowledge_base = {k: KnowledgeDimension(
            name=d.name, priority=d.priority, description=d.description, keywords=d.keywords
        ) for k, d in service.dimensions.items()}

        # 设置一些已收集的信息
        state.knowledge_base["basic"].collected = True
        state.knowledge_base["basic"].raw_data = {"name": "小明", "age": 28}
        state.knowledge_base["relationship_goal"].collected = True
        state.knowledge_base["relationship_goal"].raw_data = "认真恋爱"

        message = service._generate_farewell_message(state)

        assert "了解" in message or "幸福" in message or "缘分" in message
        mock_call_llm.assert_called_once()

    @patch('services.ai_native_conversation_service.call_llm')
    def test_generate_farewell_llm_failure(self, mock_call_llm):
        """测试 LLM 失败时的降级结束语"""
        mock_call_llm.side_effect = Exception("LLM Error")

        service = AINativeConversationService()
        state = service.ConversationState("user-123", "小明")
        state.knowledge_base = {k: KnowledgeDimension(
            name=d.name, priority=d.priority, description=d.description, keywords=d.keywords
        ) for k, d in service.dimensions.items()}

        message = service._generate_farewell_message(state)

        # 应该返回默认消息
        assert "了解" in message or "缘分" in message


class TestGlobalInstance:
    """测试全局实例"""

    def test_global_instance_exists(self):
        """测试全局实例存在"""
        from services.ai_native_conversation_service import ai_native_conversation_service

        assert ai_native_conversation_service is not None
        assert isinstance(ai_native_conversation_service, AINativeConversationService)