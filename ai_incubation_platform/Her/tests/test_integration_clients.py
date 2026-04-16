"""
测试集成客户端模块

覆盖范围:
- LLMIntegrationClient (src/integration/llm_client.py)
- PortalIntegrationClient (src/integration/portal_client.py)
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import json


class TestLLMIntegrationClient:
    """测试 LLM 集成客户端"""

    def test_client_initialization_default(self):
        """测试客户端初始化"""
        from src.integration.llm_client import LLMIntegrationClient

        with patch('src.integration.llm_client.settings') as mock_settings:
            mock_settings.llm_enabled = False
            mock_settings.llm_provider = "openai"
            mock_settings.llm_api_key = "test-key"
            mock_settings.llm_api_base = ""
            mock_settings.llm_model = "gpt-4"
            mock_settings.llm_temperature = 0.7
            mock_settings.llm_max_tokens = 1000

            client = LLMIntegrationClient()

            assert client.enabled is False
            assert client.provider == "openai"
            assert client.api_key == "test-key"
            assert client.model == "gpt-4"
            assert client.temperature == 0.7
            assert client.client is None  # disabled 时客户端应为 None

    def test_client_initialization_with_base_url(self):
        """测试带 API 基础 URL 的初始化"""
        from src.integration.llm_client import LLMIntegrationClient

        with patch('src.integration.llm_client.settings') as mock_settings:
            mock_settings.llm_enabled = True
            mock_settings.llm_provider = "qwen"
            mock_settings.llm_api_key = "test-key"
            mock_settings.llm_api_base = "https://dashscope.aliyuncs.com/api/v1"
            mock_settings.llm_model = "qwen-plus"
            mock_settings.llm_temperature = 0.5
            mock_settings.llm_max_tokens = 2000

            client = LLMIntegrationClient()

            assert client.enabled is True
            assert client.api_base == "https://dashscope.aliyuncs.com/api/v1"
            assert client.client is not None

    def test_api_base_auto_config_openai(self):
        """测试 OpenAI API 基础 URL 自动配置"""
        from src.integration.llm_client import LLMIntegrationClient

        with patch('src.integration.llm_client.settings') as mock_settings:
            mock_settings.llm_enabled = True
            mock_settings.llm_provider = "openai"
            mock_settings.llm_api_key = "test-key"
            mock_settings.llm_api_base = ""
            mock_settings.llm_model = "gpt-4"
            mock_settings.llm_temperature = 0.7
            mock_settings.llm_max_tokens = 1000

            client = LLMIntegrationClient()

            assert client.api_base == "https://api.openai.com/v1"

    def test_api_base_auto_config_qwen(self):
        """测试通义千问 API 基础 URL 自动配置"""
        from src.integration.llm_client import LLMIntegrationClient

        with patch('src.integration.llm_client.settings') as mock_settings:
            mock_settings.llm_enabled = True
            mock_settings.llm_provider = "qwen"
            mock_settings.llm_api_key = "test-key"
            mock_settings.llm_api_base = ""
            mock_settings.llm_model = "qwen-plus"
            mock_settings.llm_temperature = 0.7
            mock_settings.llm_max_tokens = 1000

            client = LLMIntegrationClient()

            assert client.api_base == "https://dashscope.aliyuncs.com/api/v1"

    def test_api_base_auto_config_glm(self):
        """测试 GLM API 基础 URL 自动配置"""
        from src.integration.llm_client import LLMIntegrationClient

        with patch('src.integration.llm_client.settings') as mock_settings:
            mock_settings.llm_enabled = True
            mock_settings.llm_provider = "glm"
            mock_settings.llm_api_key = "test-key"
            mock_settings.llm_api_base = ""
            mock_settings.llm_model = "glm-4"
            mock_settings.llm_temperature = 0.7
            mock_settings.llm_max_tokens = 1000

            client = LLMIntegrationClient()

            assert client.api_base == "https://open.bigmodel.cn/api/paas/v4"

    @pytest.mark.asyncio
    async def test_generate_icebreaker_suggestions_disabled(self):
        """测试 LLM 禁用时生成破冰建议"""
        from src.integration.llm_client import LLMIntegrationClient

        with patch('src.integration.llm_client.settings') as mock_settings:
            mock_settings.llm_enabled = False

            client = LLMIntegrationClient()
            user_info = {"name": "张三", "age": 25, "interests": ["旅行"], "location": "北京"}
            matched_info = {"name": "李四", "age": 24, "interests": ["美食"], "location": "上海"}

            suggestions = await client.generate_icebreaker_suggestions(
                user_info=user_info,
                matched_user_info=matched_info,
                common_interests=["阅读"],
                compatibility_score=0.85,
                match_reasoning="共同兴趣：阅读"
            )

            assert len(suggestions) > 0
            assert len(suggestions) <= 5
            assert isinstance(suggestions, list)

    @pytest.mark.asyncio
    async def test_generate_icebreaker_suggestions_with_common_interests(self):
        """测试有共同兴趣时生成破冰建议"""
        from src.integration.llm_client import LLMIntegrationClient

        with patch('src.integration.llm_client.settings') as mock_settings:
            mock_settings.llm_enabled = False

            client = LLMIntegrationClient()
            user_info = {"name": "张三", "age": 25, "interests": ["旅行"], "location": "北京"}
            matched_info = {"name": "李四", "age": 24, "interests": ["美食"], "location": "上海"}

            suggestions = await client.generate_icebreaker_suggestions(
                user_info=user_info,
                matched_user_info=matched_info,
                common_interests=["摄影", "音乐"],
                compatibility_score=0.85,
                match_reasoning="共同兴趣：摄影、音乐"
            )

            # 有共同兴趣时应包含相关破冰话术
            assert len(suggestions) >= 2
            # 应该包含与共同兴趣相关的话术
            all_suggestions = " ".join(suggestions)
            assert "摄影" in all_suggestions or "音乐" in all_suggestions or "爱好" in all_suggestions

    @pytest.mark.asyncio
    async def test_generate_icebreaker_suggestions_no_common_interests(self):
        """测试无共同兴趣时生成破冰建议"""
        from src.integration.llm_client import LLMIntegrationClient

        with patch('src.integration.llm_client.settings') as mock_settings:
            mock_settings.llm_enabled = False

            client = LLMIntegrationClient()
            user_info = {"name": "张三", "age": 25, "interests": ["旅行"], "location": "北京"}
            matched_info = {"name": "李四", "age": 24, "interests": ["美食"], "location": "上海"}

            suggestions = await client.generate_icebreaker_suggestions(
                user_info=user_info,
                matched_user_info=matched_info,
                common_interests=[],
                compatibility_score=0.60,
                match_reasoning="地理位置相近"
            )

            assert len(suggestions) >= 2
            # 默认话术应包含通用开场白
            all_suggestions = " ".join(suggestions)
            assert "你好" in all_suggestions or "匹配" in all_suggestions or "高兴" in all_suggestions

    @pytest.mark.asyncio
    async def test_generate_conversation_topics_disabled(self):
        """测试 LLM 禁用时生成对话话题"""
        from src.integration.llm_client import LLMIntegrationClient

        with patch('src.integration.llm_client.settings') as mock_settings:
            mock_settings.llm_enabled = False

            client = LLMIntegrationClient()
            user_info = {"name": "张三", "age": 25, "interests": ["旅行", "摄影"], "location": "北京"}
            matched_info = {"name": "李四", "age": 24, "interests": ["美食", "电影"], "location": "北京"}

            topics = await client.generate_conversation_topic(
                user_info=user_info,
                matched_user_info=matched_info,
                chat_history=None
            )

            assert len(topics) > 0
            assert len(topics) <= 3
            assert isinstance(topics, list)

    @pytest.mark.asyncio
    async def test_generate_conversation_topics_with_chat_history(self):
        """测试带聊天历史生成对话话题"""
        from src.integration.llm_client import LLMIntegrationClient

        with patch('src.integration.llm_client.settings') as mock_settings:
            mock_settings.llm_enabled = False

            client = LLMIntegrationClient()
            user_info = {"name": "张三", "age": 25, "interests": ["旅行"], "location": "北京"}
            matched_info = {"name": "李四", "age": 24, "interests": ["美食"], "location": "上海"}

            chat_history = [
                {"role": "user", "content": "你好"},
                {"role": "assistant", "content": "你好呀"},
                {"role": "user", "content": "最近有什么好玩的吗？"}
            ]

            topics = await client.generate_conversation_topic(
                user_info=user_info,
                matched_user_info=matched_info,
                chat_history=chat_history
            )

            assert len(topics) > 0
            assert isinstance(topics, list)

    def test_build_icebreaker_prompt(self):
        """测试破冰话术 Prompt 构建"""
        from src.integration.llm_client import LLMIntegrationClient

        with patch('src.integration.llm_client.settings') as mock_settings:
            mock_settings.llm_enabled = False
            client = LLMIntegrationClient()

            user_info = {"name": "张三", "age": 25, "interests": ["旅行", "摄影"], "location": "北京"}
            matched_info = {
                "name": "李四",
                "age": 24,
                "interests": ["美食", "电影"],
                "location": "上海",
                "bio": "热爱生活，喜欢探索新鲜事物"
            }

            prompt = client._build_icebreaker_prompt(
                user_info=user_info,
                matched_user_info=matched_info,
                common_interests=["阅读"],
                compatibility_score=0.85,
                match_reasoning="共同兴趣：阅读"
            )

            assert "张三" in prompt
            assert "李四" in prompt
            assert "25" in prompt
            assert "24" in prompt
            assert "北京" in prompt
            assert "上海" in prompt
            assert "阅读" in prompt
            assert "0.85" in prompt or "85" in prompt
            assert "破冰" in prompt or "开场白" in prompt

    def test_build_topic_prompt(self):
        """测试话题 Prompt 构建"""
        from src.integration.llm_client import LLMIntegrationClient

        with patch('src.integration.llm_client.settings') as mock_settings:
            mock_settings.llm_enabled = False
            client = LLMIntegrationClient()

            user_info = {"name": "张三", "age": 25, "interests": ["旅行"], "location": "北京"}
            matched_info = {"name": "李四", "age": 24, "interests": ["美食"], "location": "上海"}

            prompt = client._build_topic_prompt(
                user_info=user_info,
                matched_user_info=matched_info,
                chat_history=None
            )

            # 检查关键内容（不检查具体格式）
            assert "兴趣" in prompt
            assert "旅行" in prompt
            assert "美食" in prompt
            assert "话题" in prompt or "JSON" in prompt

    def test_build_topic_prompt_with_history(self):
        """测试带历史的话题 Prompt 构建"""
        from src.integration.llm_client import LLMIntegrationClient

        with patch('src.integration.llm_client.settings') as mock_settings:
            mock_settings.llm_enabled = False
            client = LLMIntegrationClient()

            user_info = {"name": "张三", "age": 25, "interests": ["旅行"], "location": "北京"}
            matched_info = {"name": "李四", "age": 24, "interests": ["美食"], "location": "上海"}

            chat_history = [
                {"role": "user", "content": "你好"},
                {"role": "assistant", "content": "你好呀"}
            ]

            prompt = client._build_topic_prompt(
                user_info=user_info,
                matched_user_info=matched_info,
                chat_history=chat_history
            )

            assert "聊天历史" in prompt
            assert "你好" in prompt

    def test_parse_icebreaker_response_json(self):
        """测试 JSON 格式破冰响应解析"""
        from src.integration.llm_client import LLMIntegrationClient

        with patch('src.integration.llm_client.settings') as mock_settings:
            mock_settings.llm_enabled = False
            client = LLMIntegrationClient()

            response = '{"suggestions": ["你好呀", "很高兴认识你", "可以聊聊吗"]}'
            result = client._parse_icebreaker_response(response)

            assert len(result) == 3
            assert "你好呀" in result
            assert "很高兴认识你" in result

    def test_parse_icebreaker_response_text(self):
        """测试文本格式破冰响应解析"""
        from src.integration.llm_client import LLMIntegrationClient

        with patch('src.integration.llm_client.settings') as mock_settings:
            mock_settings.llm_enabled = False
            client = LLMIntegrationClient()

            response = """
            1. 你好呀
            2. 很高兴认识你
            3. 可以聊聊吗
            """
            result = client._parse_icebreaker_response(response)

            assert len(result) > 0
            assert "你好呀" in result

    def test_parse_topic_response_json(self):
        """测试 JSON 格式话题响应解析"""
        from src.integration.llm_client import LLMIntegrationClient

        with patch('src.integration.llm_client.settings') as mock_settings:
            mock_settings.llm_enabled = False
            client = LLMIntegrationClient()

            response = '{"topics": ["聊聊旅行", "聊聊美食", "聊聊电影"]}'
            result = client._parse_topic_response(response)

            assert len(result) == 3
            assert "聊聊旅行" in result

    def test_parse_topic_response_text(self):
        """测试文本格式话题响应解析"""
        from src.integration.llm_client import LLMIntegrationClient

        with patch('src.integration.llm_client.settings') as mock_settings:
            mock_settings.llm_enabled = False
            client = LLMIntegrationClient()

            response = """
            1. 聊聊旅行
            2. 聊聊美食
            3. 聊聊电影
            """
            result = client._parse_topic_response(response)

            assert len(result) > 0

    def test_get_default_icebreakers_no_interests(self):
        """测试无兴趣时的默认破冰话术"""
        from src.integration.llm_client import LLMIntegrationClient

        with patch('src.integration.llm_client.settings') as mock_settings:
            mock_settings.llm_enabled = False
            client = LLMIntegrationClient()

            suggestions = client._get_default_icebreakers([])

            assert len(suggestions) > 0
            assert len(suggestions) <= 5

    def test_get_default_icebreakers_with_interests(self):
        """测试有共同兴趣时的默认破冰话术"""
        from src.integration.llm_client import LLMIntegrationClient

        with patch('src.integration.llm_client.settings') as mock_settings:
            mock_settings.llm_enabled = False
            client = LLMIntegrationClient()

            suggestions = client._get_default_icebreakers(["摄影", "音乐"])

            assert len(suggestions) > 0
            all_suggestions = " ".join(suggestions)
            assert "摄影" in all_suggestions or "音乐" in all_suggestions

    def test_get_default_topics_common_location(self):
        """测试同地点时的默认话题"""
        from src.integration.llm_client import LLMIntegrationClient

        with patch('src.integration.llm_client.settings') as mock_settings:
            mock_settings.llm_enabled = False
            client = LLMIntegrationClient()

            user_info = {"interests": ["旅行"], "location": "北京"}
            matched_info = {"interests": ["美食"], "location": "北京"}

            topics = client._get_default_topics(user_info, matched_info)

            assert len(topics) > 0
            assert len(topics) <= 3
            all_topics = " ".join(topics)
            assert "北京" in all_topics

    def test_get_default_topics_common_interests(self):
        """测试有共同兴趣时的默认话题"""
        from src.integration.llm_client import LLMIntegrationClient

        with patch('src.integration.llm_client.settings') as mock_settings:
            mock_settings.llm_enabled = False
            client = LLMIntegrationClient()

            user_info = {"interests": ["旅行", "摄影"], "location": "北京"}
            matched_info = {"interests": ["旅行", "美食"], "location": "上海"}

            topics = client._get_default_topics(user_info, matched_info)

            assert len(topics) > 0
            all_topics = " ".join(topics)
            assert "旅行" in all_topics

    @pytest.mark.asyncio
    async def test_generate_icebreaker_exception_handling(self):
        """测试破冰话术生成异常处理"""
        from src.integration.llm_client import LLMIntegrationClient

        with patch('src.integration.llm_client.settings') as mock_settings:
            mock_settings.llm_enabled = True

            client = LLMIntegrationClient()
            client.client = AsyncMock()
            client.client.post.side_effect = Exception("API Error")

            user_info = {"name": "张三", "age": 25, "interests": ["旅行"], "location": "北京"}
            matched_info = {"name": "李四", "age": 24, "interests": ["美食"], "location": "上海"}

            # 异常时应返回默认话术
            suggestions = await client.generate_icebreaker_suggestions(
                user_info=user_info,
                matched_user_info=matched_info,
                common_interests=[],
                compatibility_score=0.85,
                match_reasoning="测试"
            )

            assert len(suggestions) > 0  # 应返回默认话术

    @pytest.mark.asyncio
    async def test_generate_conversation_topics_exception_handling(self):
        """测试话题生成异常处理"""
        from src.integration.llm_client import LLMIntegrationClient

        with patch('src.integration.llm_client.settings') as mock_settings:
            mock_settings.llm_enabled = True

            client = LLMIntegrationClient()
            client.client = AsyncMock()
            client.client.post.side_effect = Exception("API Error")

            user_info = {"name": "张三", "age": 25, "interests": ["旅行"], "location": "北京"}
            matched_info = {"name": "李四", "age": 24, "interests": ["美食"], "location": "上海"}

            # 异常时应返回默认话题
            topics = await client.generate_conversation_topic(
                user_info=user_info,
                matched_user_info=matched_info
            )

            assert len(topics) > 0  # 应返回默认话题

    @pytest.mark.asyncio
    async def test_call_llm_success(self):
        """测试成功调用 LLM"""
        from src.integration.llm_client import LLMIntegrationClient

        with patch('src.integration.llm_client.settings') as mock_settings:
            mock_settings.llm_enabled = True
            mock_settings.llm_api_key = "test-key"
            mock_settings.llm_model = "gpt-4"
            mock_settings.llm_temperature = 0.7
            mock_settings.llm_max_tokens = 1000
            mock_settings.llm_api_base = "https://api.openai.com/v1"

            client = LLMIntegrationClient()

            mock_response = MagicMock()
            mock_response.json.return_value = {
                "choices": [{"message": {"content": '{"suggestions": ["你好呀"]}'}}]
            }
            mock_response.raise_for_status = MagicMock()
            client.client = MagicMock()
            client.client.post = AsyncMock(return_value=mock_response)

            result = await client._call_llm("测试 prompt")

            assert result == '{"suggestions": ["你好呀"]}'
            client.client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_client(self):
        """测试关闭客户端"""
        from src.integration.llm_client import LLMIntegrationClient

        with patch('src.integration.llm_client.settings') as mock_settings:
            mock_settings.llm_enabled = True

            client = LLMIntegrationClient()
            client.client = AsyncMock()
            client.client.aclose = AsyncMock()

            await client.close()

            client.client.aclose.assert_called_once()

    def test_close_client_disabled(self):
        """测试关闭已禁用的客户端"""
        from src.integration.llm_client import LLMIntegrationClient

        with patch('src.integration.llm_client.settings') as mock_settings:
            mock_settings.llm_enabled = False

            client = LLMIntegrationClient()
            # 不应抛出异常
            asyncio.run(client.close())


# PortalIntegrationClient 测试已移除 - portal_client.py 已废弃删除
# 新架构使用 DeerFlow + her_tools 集成


class TestGlobalInstances:
    """测试全局实例"""

    def test_llm_client_global_instance(self):
        """测试 LLM 客户端全局实例"""
        from src.integration.llm_client import llm_client
        assert llm_client is not None

    # portal_client 已废弃删除，移除相关测试
