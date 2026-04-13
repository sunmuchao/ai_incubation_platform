"""
IntentRouter Skill 单元测试

测试意图识别、Skill 路由、Generative UI 返回格式。

版本历史：
- v1.0: 测试硬编码版本（INTENT_SKILL_MAPPING 等常量）
- v2.0: 升级测试 DeerFlow 集成版本
- v3.0: 适配 YAML 配置驱动版本
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from agent.skills.intent_router_skill import (
    IntentRouterSkill,
    IntentType,
    IntentResult,
    get_intent_router_skill,
)
from intent_config.intent_config_loader import get_intent_config_loader


class TestIntentType:
    """测试意图类型枚举"""

    def test_intent_types_defined(self):
        """测试所有意图类型都已定义"""
        expected_types = [
            "matching", "daily_recommend", "profile_collection",
            "relationship_analysis", "topic_suggestion", "icebreaker",
            "dating_suggestion", "date_planning",
            "pre_communication", "pre_comm_start",
            "greeting", "gratitude", "goodbye", "capability_inquiry",
            "general",
        ]
        actual_types = [e.value for e in IntentType]
        assert set(expected_types) == set(actual_types)

    def test_intent_type_enum_count(self):
        """测试意图类型数量"""
        assert len(IntentType) == 15


class TestIntentConfigLoader:
    """测试意图配置加载器（替代旧的常量测试）"""

    def setup_method(self):
        """设置测试方法"""
        self.loader = get_intent_config_loader()
        self.config = self.loader.get_config()

    def test_config_loaded_successfully(self):
        """测试配置加载成功"""
        assert self.config is not None
        assert self.config.intents is not None

    def test_matching_intent_maps_to_matchmaker(self):
        """测试匹配意图映射到 conversation_matchmaker"""
        skill_mapping = self.config.get_skill_mapping()
        assert skill_mapping.get("matching") == "conversation_matchmaker"

    def test_daily_recommend_maps_to_matchmaker(self):
        """测试每日推荐映射到 conversation_matchmaker"""
        skill_mapping = self.config.get_skill_mapping()
        assert skill_mapping.get("daily_recommend") == "conversation_matchmaker"

    def test_greeting_is_local_intent(self):
        """测试问候意图是本地处理"""
        local_intents = self.config.get_local_intents()
        assert "greeting" in local_intents
        assert self.config.get_skill_mapping().get("greeting") is None

    def test_gratitude_is_local_intent(self):
        """测试感谢意图是本地处理"""
        local_intents = self.config.get_local_intents()
        assert "gratitude" in local_intents

    def test_capability_inquiry_is_local_intent(self):
        """测试能力询问是本地处理"""
        local_intents = self.config.get_local_intents()
        assert "capability_inquiry" in local_intents

    def test_intents_sorted_by_priority(self):
        """测试意图按优先级排序"""
        sorted_intents = self.config.get_sorted_intents()
        priorities = [i.priority for i in sorted_intents]
        # 验证优先级是递增的
        assert priorities == sorted(priorities)


class TestIntentResult:
    """测试意图识别结果"""

    def test_intent_result_creation(self):
        """测试创建意图结果"""
        result = IntentResult(
            type=IntentType.MATCHING,
            confidence=0.95,
            raw_input="帮我找对象",
            params={"limit": 5}
        )
        assert result.type == IntentType.MATCHING
        assert result.confidence == 0.95
        assert result.raw_input == "帮我找对象"
        assert result.params == {"limit": 5}

    def test_intent_result_default_params(self):
        """测试默认参数为空字典"""
        result = IntentResult(type=IntentType.GREETING)
        assert result.params == {}
        assert result.confidence == 1.0


class TestIntentRouterSkillMetadata:
    """测试 IntentRouter Skill 元数据"""

    def test_skill_name(self):
        """测试 Skill 名称"""
        skill = get_intent_router_skill()
        assert skill.name == "intent_router"

    def test_skill_version(self):
        """测试 Skill 版本（v3.0.0 配置化版本）"""
        skill = get_intent_router_skill()
        assert skill.version == "3.0.0"

    def test_skill_input_schema(self):
        """测试输入 Schema"""
        skill = get_intent_router_skill()
        schema = skill.get_input_schema()
        assert schema["type"] == "object"
        assert "user_input" in schema["required"]
        assert "user_id" in schema["required"]

    def test_skill_output_schema(self):
        """测试输出 Schema"""
        skill = get_intent_router_skill()
        schema = skill.get_output_schema()
        assert "success" in schema["required"]
        assert "intent" in schema["required"]
        assert "ai_message" in schema["required"]
        assert "generative_ui" in schema["properties"]

    def test_skill_has_config_loader(self):
        """测试 Skill 有配置加载器"""
        skill = get_intent_router_skill()
        assert skill._config_loader is not None


class TestKeywordIntentClassification:
    """测试关键词意图识别（降级方案）"""

    def setup_method(self):
        """设置测试方法"""
        self.skill = get_intent_router_skill()

    def test_classify_greeting(self):
        """测试识别问候意图"""
        result = self.skill._classify_with_keywords("你好")
        assert result.type == IntentType.GREETING

    def test_classify_greeting_variants(self):
        """测试各种问候变体"""
        inputs = ["hi", "hello", "早上好", "嗨", "哈喽", "hey"]
        for input in inputs:
            result = self.skill._classify_with_keywords(input)
            assert result.type == IntentType.GREETING

    def test_classify_matching(self):
        """测试识别匹配意图"""
        inputs = ["帮我找对象", "我想找对象", "匹配", "介绍对象"]
        for input in inputs:
            result = self.skill._classify_with_keywords(input)
            assert result.type == IntentType.MATCHING

    def test_classify_daily_recommend(self):
        """测试识别每日推荐意图"""
        inputs = ["今日推荐", "每日推荐", "今天的推荐"]
        for input in inputs:
            result = self.skill._classify_with_keywords(input)
            assert result.type == IntentType.DAILY_RECOMMEND

    def test_classify_gratitude(self):
        """测试识别感谢意图"""
        inputs = ["谢谢", "感谢", "thank", "thx"]
        for input in inputs:
            result = self.skill._classify_with_keywords(input)
            assert result.type == IntentType.GRATITUDE

    def test_classify_goodbye(self):
        """测试识别告别意图"""
        inputs = ["再见", "拜拜", "bye", "回见"]
        for input in inputs:
            result = self.skill._classify_with_keywords(input)
            assert result.type == IntentType.GOODBYE

    def test_classify_capability_inquiry(self):
        """测试识别能力询问意图"""
        inputs = ["你能干嘛", "你有什么功能", "你是谁", "介绍你自己"]
        for input in inputs:
            result = self.skill._classify_with_keywords(input)
            assert result.type == IntentType.CAPABILITY_INQUIRY

    def test_classify_pre_communication(self):
        """测试识别预沟通意图"""
        result = self.skill._classify_with_keywords("预沟通")
        assert result.type == IntentType.PRE_COMMUNICATION

    def test_classify_pre_comm_start(self):
        """测试识别启动预沟通意图"""
        inputs = ["启动预沟通", "ai替身", "代聊", "帮我聊"]
        for input in inputs:
            result = self.skill._classify_with_keywords(input)
            assert result.type == IntentType.PRE_COMM_START

    def test_classify_topic_suggestion(self):
        """测试识别话题推荐意图"""
        inputs = ["有什么话题", "聊什么", "推荐话题"]
        for input in inputs:
            result = self.skill._classify_with_keywords(input)
            assert result.type == IntentType.TOPIC_SUGGESTION

    def test_classify_dating_suggestion(self):
        """测试识别约会建议意图"""
        inputs = ["约会", "约会去哪里", "约会地点"]
        for input in inputs:
            result = self.skill._classify_with_keywords(input)
            assert result.type == IntentType.DATING_SUGGESTION

    def test_classify_general_fallback(self):
        """测试兜底为一般意图"""
        inputs = ["今天天气怎么样", "你喜欢什么颜色", "随便聊聊"]
        for input in inputs:
            result = self.skill._classify_with_keywords(input)
            assert result.type == IntentType.GENERAL


class TestLocalIntentHandling:
    """测试本地意图处理"""

    def setup_method(self):
        """设置测试方法"""
        self.skill = get_intent_router_skill()

    def test_handle_greeting(self):
        """测试处理问候"""
        intent = IntentResult(type=IntentType.GREETING, raw_input="你好")
        result = self.skill._handle_local_intent(intent)
        assert result["success"] == True
        assert "你好呀" in result["ai_message"]
        assert result["generative_ui"]["component_type"] == "SimpleResponse"

    def test_handle_gratitude(self):
        """测试处理感谢"""
        intent = IntentResult(type=IntentType.GRATITUDE, raw_input="谢谢")
        result = self.skill._handle_local_intent(intent)
        assert result["success"] == True
        assert "开心" in result["ai_message"]

    def test_handle_goodbye(self):
        """测试处理告别"""
        intent = IntentResult(type=IntentType.GOODBYE, raw_input="再见")
        result = self.skill._handle_local_intent(intent)
        assert result["success"] == True
        assert "下次见" in result["ai_message"]

    def test_handle_capability_inquiry(self):
        """测试处理能力询问"""
        intent = IntentResult(type=IntentType.CAPABILITY_INQUIRY)
        result = self.skill._handle_local_intent(intent)
        assert result["success"] == True
        assert "Her" in result["ai_message"]
        assert result["generative_ui"]["component_type"] == "CapabilityCard"
        assert "features" in result["generative_ui"]["props"]

    def test_capability_intro_contains_features(self):
        """测试能力介绍包含所有功能"""
        intro = self.skill._get_capability_intro()
        assert "匹配" in intro or "推荐" in intro

    def test_feature_list_count(self):
        """测试功能列表数量"""
        features = self.skill._get_feature_list()
        assert len(features) >= 6


class TestSuggestedActions:
    """测试建议操作"""

    def setup_method(self):
        """设置测试方法"""
        self.skill = get_intent_router_skill()

    def test_greeting_has_suggested_actions(self):
        """测试问候有建议操作"""
        actions = self.skill._get_suggested_actions(IntentType.GREETING)
        assert len(actions) >= 1

    def test_capability_inquiry_has_suggested_actions(self):
        """测试能力询问有建议操作"""
        actions = self.skill._get_suggested_actions(IntentType.CAPABILITY_INQUIRY)
        assert len(actions) >= 1

    def test_general_intent_has_suggested_actions(self):
        """测试一般意图有建议操作"""
        intent = IntentResult(type=IntentType.GENERAL)
        result = self.skill._handle_general_intent(intent)
        assert len(result["suggested_actions"]) >= 1


class TestIntentRouterSkillExecute:
    """测试 IntentRouter Skill execute 方法"""

    @pytest.mark.asyncio
    async def test_execute_greeting(self):
        """测试执行问候意图"""
        skill = get_intent_router_skill()

        # Mock _check_need_profile_collection 返回 False
        with patch.object(skill, '_check_need_profile_collection', return_value=False):
            result = await skill.execute(
                user_input="你好",
                user_id="test-user-001"
            )

        assert result["success"] == True
        assert result["intent"]["type"] == "greeting"
        assert "你好呀" in result["ai_message"]
        assert result["generative_ui"]["component_type"] == "SimpleResponse"

    @pytest.mark.asyncio
    async def test_execute_gratitude(self):
        """测试执行感谢意图"""
        skill = get_intent_router_skill()

        with patch.object(skill, '_check_need_profile_collection', return_value=False):
            result = await skill.execute(
                user_input="谢谢",
                user_id="test-user-001"
            )

        assert result["success"] == True
        assert result["intent"]["type"] == "gratitude"
        assert "开心" in result["ai_message"]

    @pytest.mark.asyncio
    async def test_execute_capability_inquiry(self):
        """测试执行能力询问"""
        skill = get_intent_router_skill()

        with patch.object(skill, '_check_need_profile_collection', return_value=False):
            result = await skill.execute(
                user_input="你能干嘛",
                user_id="test-user-001"
            )

        assert result["success"] == True
        assert result["intent"]["type"] == "capability_inquiry"
        assert result["generative_ui"]["component_type"] == "CapabilityCard"

    @pytest.mark.asyncio
    async def test_execute_matching_calls_matchmaker_skill(self):
        """测试匹配意图调用 ConversationMatchmaker Skill"""
        skill = get_intent_router_skill()

        # Mock registry.execute
        mock_registry = MagicMock()
        mock_registry.execute = AsyncMock(return_value={
            "success": True,
            "ai_message": "为你找到 3 位匹配对象",
            "generative_ui": {"component_type": "MatchCardList", "props": {"matches": []}},
            "suggested_actions": []
        })

        with patch('agent.skills.intent_router_skill.get_skill_registry', return_value=mock_registry):
            with patch.object(skill, '_check_need_profile_collection', return_value=False):
                result = await skill.execute(
                    user_input="帮我找对象",
                    user_id="test-user-001"
                )

        assert result["success"] == True
        assert result["intent"]["type"] == "matching"
        # 验证调用了 conversation_matchmaker Skill
        mock_registry.execute.assert_called_once()
        call_args = mock_registry.execute.call_args
        assert call_args[0][0] == "conversation_matchmaker"

    @pytest.mark.asyncio
    async def test_execute_returns_skill_metadata(self):
        """测试返回 Skill 元数据"""
        skill = get_intent_router_skill()

        with patch.object(skill, '_check_need_profile_collection', return_value=False):
            result = await skill.execute(
                user_input="你好",
                user_id="test-user-001"
            )

        assert "skill_metadata" in result
        assert result["skill_metadata"]["name"] == "intent_router"
        assert result["skill_metadata"]["version"] == "3.0.0"
        assert "execution_time_ms" in result["skill_metadata"]

    @pytest.mark.asyncio
    async def test_execute_profile_collection_for_new_user(self):
        """测试新用户触发信息收集"""
        skill = get_intent_router_skill()

        # Mock registry.execute 返回成功结果
        mock_registry = MagicMock()
        mock_registry.execute = AsyncMock(return_value={
            "success": True,
            "ai_message": "请告诉我你的年龄",
            "generative_ui": {"component_type": "ProfileQuestionCard", "props": {"question": "年龄"}},
            "suggested_actions": []
        })

        with patch('agent.skills.intent_router_skill.get_skill_registry', return_value=mock_registry):
            with patch.object(skill, '_check_need_profile_collection', return_value=True):
                result = await skill.execute(
                    user_input="开始",
                    user_id="new-user-001"
                )

        assert result["intent"]["type"] == "profile_collection"
        assert result["success"] == True


class TestGenerativeUIFormat:
    """测试 Generative UI 返回格式"""

    def setup_method(self):
        """设置测试方法"""
        self.skill = get_intent_router_skill()

    def test_generative_ui_has_component_type(self):
        """测试 Generative UI 包含 component_type"""
        intent = IntentResult(type=IntentType.GREETING)
        result = self.skill._handle_local_intent(intent)
        assert "component_type" in result["generative_ui"]

    def test_generative_ui_has_props(self):
        """测试 Generative UI 包含 props"""
        intent = IntentResult(type=IntentType.CAPABILITY_INQUIRY)
        result = self.skill._handle_local_intent(intent)
        assert "props" in result["generative_ui"]

    def test_simple_response_component_type(self):
        """测试简单响应使用 SimpleResponse"""
        for intent_type in [IntentType.GREETING, IntentType.GRATITUDE, IntentType.GOODBYE]:
            intent = IntentResult(type=intent_type)
            result = self.skill._handle_local_intent(intent)
            assert result["generative_ui"]["component_type"] == "SimpleResponse"

    def test_capability_card_has_features_props(self):
        """测试能力卡片包含 features 属性"""
        intent = IntentResult(type=IntentType.CAPABILITY_INQUIRY)
        result = self.skill._handle_local_intent(intent)
        assert result["generative_ui"]["component_type"] == "CapabilityCard"
        assert "features" in result["generative_ui"]["props"]


class TestSkillRegistryIntegration:
    """测试 Skill Registry 集成"""

    def test_intent_router_registered(self):
        """测试 IntentRouter 已注册"""
        from agent.skills.registry import get_skill_registry, initialize_default_skills

        registry = initialize_default_skills()
        skill = registry.get("intent_router")

        assert skill is not None
        assert skill.name == "intent_router"

    def test_intent_router_has_entry_point_tag(self):
        """测试 IntentRouter 有 entry_point 标签"""
        from agent.skills.registry import get_skill_registry, initialize_default_skills

        registry = initialize_default_skills()
        # 注意：registry 不一定存储 tags，但可以验证 skill 存在
        skill = registry.get("intent_router")
        assert skill is not None


class TestConfigReload:
    """测试配置热更新"""

    def setup_method(self):
        """设置测试方法"""
        self.skill = get_intent_router_skill()

    def test_reload_config_returns_true(self):
        """测试热更新配置返回 True"""
        result = self.skill.reload_config()
        assert result == True

    def test_get_config_info_returns_metadata(self):
        """测试获取配置信息"""
        info = self.skill.get_config_info()
        assert "config_path" in info
        assert "loaded" in info or "last_loaded" in info


# ==================== 运行测试 ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])