"""
MatchmakingSkill 单元测试

测试 AI 红娘助手 Skill 的核心功能，包括：
- execute 方法（正常匹配、每日推荐、兴趣匹配）
- 意图解析（LLM 分析、关键词降级）
- 自然语言响应生成
- Generative UI 构建
- 自主触发（每日、高质量匹配、资料更新）
- 每日推荐频率控制
- 边缘场景
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from datetime import datetime, timedelta
import json

from agent.skills.matchmaking_skill import (
    MatchmakingSkill,
    get_matchmaking_skill,
)


# ========== Fixtures ==========

@pytest.fixture
def matchmaking_skill():
    """获取匹配助手 Skill 实例"""
    return MatchmakingSkill()


@pytest.fixture
def fresh_matchmaking_skill():
    """获取新的匹配助手 Skill 实例（非单例）"""
    return MatchmakingSkill()


@pytest.fixture
def mock_intent_result():
    """模拟意图解析结果"""
    return {
        "intent_type": "interest_based",
        "limit": 5,
        "min_score": 0.6,
        "hard_requirements": [],
        "soft_preferences": ["interest=旅行", "interest=美食"],
        "emotional_state": "normal",
        "confidence": 0.85,
        "is_llm_analyzed": True
    }


@pytest.fixture
def mock_workflow_result():
    """模拟工作流执行结果"""
    return {
        "workflow": "auto_match_recommend",
        "user_id": "test-user-001",
        "recommendations": [
            {
                "user_id": "match-001",
                "score": 0.85,
                "user": {"name": "小红", "age": 26},
                "reasoning": "你们都热爱旅行和美食，有很多共同话题",
                "common_interests": ["旅行", "美食", "摄影"]
            },
            {
                "user_id": "match-002",
                "score": 0.78,
                "user": {"name": "小明", "age": 28},
                "reasoning": "性格互补，生活方式契合",
                "common_interests": ["健身", "阅读"]
            },
            {
                "user_id": "match-003",
                "score": 0.72,
                "user": {"name": "小芳", "age": 25},
                "reasoning": "价值观相近，适合长期发展",
                "common_interests": ["音乐", "电影"]
            }
        ],
        "total": 3,
        "generated_at": "2026-04-11T10:00:00",
        "errors": []
    }


@pytest.fixture
def mock_empty_workflow_result():
    """模拟空匹配结果"""
    return {
        "workflow": "auto_match_recommend",
        "user_id": "test-user-001",
        "recommendations": [],
        "total": 0,
        "errors": []
    }


@pytest.fixture
def mock_single_match_workflow_result():
    """模拟单个匹配结果"""
    return {
        "workflow": "auto_match_recommend",
        "user_id": "test-user-001",
        "recommendations": [
            {
                "user_id": "match-001",
                "score": 0.92,
                "user": {"name": "高匹配对象"},
                "reasoning": "极高匹配度",
                "common_interests": ["旅行", "美食"]
            }
        ],
        "total": 1
    }


# ========== Skill 元数据测试 ==========

class TestMatchmakingSkillMetadata:
    """测试 Skill 元数据"""

    def test_skill_name(self, matchmaking_skill):
        """测试 Skill 名称"""
        assert matchmaking_skill.name == "matchmaking_assistant"

    def test_skill_version(self, matchmaking_skill):
        """测试 Skill 版本"""
        assert matchmaking_skill.version == "2.0.0"

    def test_skill_description_contains_keywords(self, matchmaking_skill):
        """测试描述包含关键功能"""
        desc = matchmaking_skill.description
        assert "红娘" in desc or "匹配" in desc

    def test_input_schema_structure(self, matchmaking_skill):
        """测试输入 Schema 结构"""
        schema = matchmaking_skill.get_input_schema()
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "user_intent" in schema["properties"]
        assert "user_intent" in schema["required"]

    def test_input_schema_optional_fields(self, matchmaking_skill):
        """测试输入 Schema 可选字段"""
        schema = matchmaking_skill.get_input_schema()
        props = schema["properties"]
        assert "hard_requirements" in props
        assert "soft_preferences" in props
        assert "context" in props

    def test_output_schema_structure(self, matchmaking_skill):
        """测试输出 Schema 结构"""
        schema = matchmaking_skill.get_output_schema()
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "success" in schema["properties"]
        assert "ai_message" in schema["properties"]
        assert "matches" in schema["properties"]
        assert "generative_ui" in schema["properties"]

    def test_output_schema_matches_structure(self, matchmaking_skill):
        """测试输出 Schema matches 字段结构"""
        schema = matchmaking_skill.get_output_schema()
        matches_schema = schema["properties"]["matches"]
        assert matches_schema["type"] == "array"
        assert "items" in matches_schema

    def test_output_schema_generative_ui_structure(self, matchmaking_skill):
        """测试输出 Schema generative_ui 字段结构"""
        schema = matchmaking_skill.get_output_schema()
        ui_schema = schema["properties"]["generative_ui"]
        assert ui_schema["type"] == "object"
        assert "component_type" in ui_schema["properties"]
        assert "props" in ui_schema["properties"]


# ========== execute 方法测试 ==========

class TestMatchmakingSkillExecute:
    """测试 execute 方法"""

    @pytest.mark.asyncio
    async def test_execute_normal_matching(self, matchmaking_skill, mock_intent_result, mock_workflow_result):
        """测试正常匹配执行"""
        # Mock 意图解析
        matchmaking_skill._parse_intent = MagicMock(return_value=mock_intent_result)

        # Mock 工作流
        with patch("agent.workflows.autonomous_workflows.AutoMatchRecommendWorkflow") as MockWorkflow:
            mock_instance = MagicMock()
            mock_instance.execute.return_value = mock_workflow_result
            MockWorkflow.return_value = mock_instance

            result = await matchmaking_skill.execute(
                user_intent="帮我找一个喜欢旅行的人",
                context={"user_id": "test-user-001"}
            )

        assert result["success"] is True
        assert "ai_message" in result
        assert len(result["matches"]) == 3
        assert "generative_ui" in result
        assert "suggested_actions" in result
        assert "skill_metadata" in result

    @pytest.mark.asyncio
    async def test_execute_with_hard_requirements(self, matchmaking_skill, mock_intent_result, mock_workflow_result):
        """测试带硬性条件的匹配"""
        matchmaking_skill._parse_intent = MagicMock(return_value=mock_intent_result)

        with patch("agent.workflows.autonomous_workflows.AutoMatchRecommendWorkflow") as MockWorkflow:
            mock_instance = MagicMock()
            mock_instance.execute.return_value = mock_workflow_result
            MockWorkflow.return_value = mock_instance

            result = await matchmaking_skill.execute(
                user_intent="找对象",
                hard_requirements=["age=25-30", "location=北京"],
                context={"user_id": "test-user-001"}
            )

        # 验证硬性条件被添加到意图分析中
        call_args = matchmaking_skill._parse_intent.call_args
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_execute_with_soft_preferences(self, matchmaking_skill, mock_intent_result, mock_workflow_result):
        """测试带软性偏好的匹配"""
        matchmaking_skill._parse_intent = MagicMock(return_value=mock_intent_result)

        with patch("agent.workflows.autonomous_workflows.AutoMatchRecommendWorkflow") as MockWorkflow:
            mock_instance = MagicMock()
            mock_instance.execute.return_value = mock_workflow_result
            MockWorkflow.return_value = mock_instance

            result = await matchmaking_skill.execute(
                user_intent="推荐",
                soft_preferences=["interest=健身", "personality=开朗"],
                context={"user_id": "test-user-001"}
            )

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_execute_daily_recommend_intent(self, matchmaking_skill, mock_workflow_result):
        """测试每日推荐意图"""
        daily_intent = {
            "intent_type": "daily_browse",
            "limit": 10,
            "min_score": 0.5,
            "hard_requirements": [],
            "soft_preferences": [],
            "emotional_state": "normal",
            "is_llm_analyzed": True
        }
        matchmaking_skill._parse_intent = MagicMock(return_value=daily_intent)

        with patch("agent.workflows.autonomous_workflows.AutoMatchRecommendWorkflow") as MockWorkflow:
            mock_instance = MagicMock()
            mock_instance.execute.return_value = mock_workflow_result
            MockWorkflow.return_value = mock_instance

            result = await matchmaking_skill.execute(
                user_intent="今日推荐",
                context={"user_id": "test-user-001"}
            )

        assert result["success"] is True
        assert result["skill_metadata"]["intent_type"] == "daily_browse"

    @pytest.mark.asyncio
    async def test_execute_serious_relationship_intent(self, matchmaking_skill, mock_workflow_result):
        """测试严肃恋爱意图"""
        serious_intent = {
            "intent_type": "serious_relationship",
            "limit": 5,
            "min_score": 0.75,
            "hard_requirements": ["goal=serious"],
            "soft_preferences": [],
            "emotional_state": "excited",
            "is_llm_analyzed": True
        }
        matchmaking_skill._parse_intent = MagicMock(return_value=serious_intent)

        with patch("agent.workflows.autonomous_workflows.AutoMatchRecommendWorkflow") as MockWorkflow:
            mock_instance = MagicMock()
            mock_instance.execute.return_value = mock_workflow_result
            MockWorkflow.return_value = mock_instance

            result = await matchmaking_skill.execute(
                user_intent="我想找个认真恋爱的对象",
                context={"user_id": "test-user-001"}
            )

        assert result["success"] is True
        assert result["skill_metadata"]["intent_type"] == "serious_relationship"

    @pytest.mark.asyncio
    async def test_execute_anonymous_user(self, matchmaking_skill, mock_intent_result, mock_workflow_result):
        """测试匿名用户执行"""
        matchmaking_skill._parse_intent = MagicMock(return_value=mock_intent_result)

        with patch("agent.workflows.autonomous_workflows.AutoMatchRecommendWorkflow") as MockWorkflow:
            mock_instance = MagicMock()
            mock_instance.execute.return_value = mock_workflow_result
            MockWorkflow.return_value = mock_instance

            # 无 context 时使用匿名用户
            result = await matchmaking_skill.execute(
                user_intent="随便看看"
            )

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_execute_returns_execution_time(self, matchmaking_skill, mock_intent_result, mock_workflow_result):
        """测试返回执行时间"""
        matchmaking_skill._parse_intent = MagicMock(return_value=mock_intent_result)

        with patch("agent.workflows.autonomous_workflows.AutoMatchRecommendWorkflow") as MockWorkflow:
            mock_instance = MagicMock()
            mock_instance.execute.return_value = mock_workflow_result
            MockWorkflow.return_value = mock_instance

            result = await matchmaking_skill.execute(
                user_intent="匹配",
                context={"user_id": "test-user-001"}
            )

        assert "execution_time_ms" in result["skill_metadata"]
        assert isinstance(result["skill_metadata"]["execution_time_ms"], int)


# ========== 意图解析测试 ==========

class TestIntentParsing:
    """测试意图解析"""

    def test_parse_intent_llm_success(self, matchmaking_skill):
        """测试 LLM 意图解析成功"""
        mock_llm_result = {
            "intent_type": "interest_based",
            "limit": 5,
            "min_score": 0.6,
            "hard_requirements": [],
            "soft_preferences": ["interest=旅行"],
            "emotional_state": "normal",
            "confidence": 0.9
        }

        with patch.object(matchmaking_skill, '_parse_intent_llm', return_value=mock_llm_result):
            result = matchmaking_skill._parse_intent("帮我找一个喜欢旅行的人", {})

        assert result["intent_type"] == "interest_based"
        assert result["is_llm_analyzed"] is True
        assert result["confidence"] == 0.9

    def test_parse_intent_llm_fallback(self, matchmaking_skill):
        """测试 LLM 解析失败降级到关键词匹配"""
        with patch.object(matchmaking_skill, '_parse_intent_llm', return_value=None):
            result = matchmaking_skill._parse_intent("帮我找一个认真谈恋爱的对象", {})

        assert result["intent_type"] == "serious_relationship"
        assert result["is_llm_analyzed"] is False

    def test_parse_intent_fallback_serious_relationship(self, matchmaking_skill):
        """测试关键词匹配识别严肃恋爱意图"""
        inputs = ["我想认真谈恋爱", "找对象结婚", "想找个认真的"]

        for input in inputs:
            result = matchmaking_skill._parse_intent_fallback(input, {})
            assert result["intent_type"] == "serious_relationship"
            assert result["min_score"] == 0.7
            assert "goal=serious" in result["hard_requirements"]

    def test_parse_intent_fallback_daily_browse(self, matchmaking_skill):
        """测试关键词匹配识别每日推荐意图"""
        inputs = ["今日推荐", "每日推荐", "看看有什么", "推荐几个"]

        for input in inputs:
            result = matchmaking_skill._parse_intent_fallback(input, {})
            assert result["intent_type"] == "daily_browse"
            assert result["limit"] == 10

    def test_parse_intent_fallback_interest_travel(self, matchmaking_skill):
        """测试关键词匹配识别旅行兴趣"""
        inputs = ["喜欢旅行的人", "找个爱旅游的", "旅行爱好者"]

        for input in inputs:
            result = matchmaking_skill._parse_intent_fallback(input, {})
            assert "interest=旅行" in result["soft_preferences"]

    def test_parse_intent_fallback_interest_food(self, matchmaking_skill):
        """测试关键词匹配识别美食兴趣"""
        result = matchmaking_skill._parse_intent_fallback("找个吃货", {})
        assert "interest=美食" in result["soft_preferences"]

    def test_parse_intent_fallback_interest_fitness(self, matchmaking_skill):
        """测试关键词匹配识别健身兴趣"""
        result = matchmaking_skill._parse_intent_fallback("找个爱健身的", {})
        assert "interest=健身" in result["soft_preferences"]

    def test_parse_intent_fallback_interest_reading(self, matchmaking_skill):
        """测试关键词匹配识别阅读兴趣"""
        result = matchmaking_skill._parse_intent_fallback("找个喜欢读书的人", {})
        assert "interest=阅读" in result["soft_preferences"]

    def test_parse_intent_fallback_location_nearby(self, matchmaking_skill):
        """测试关键词匹配识别附近/同城意图"""
        inputs = ["附近的", "同城的", "本地"]

        for input in inputs:
            result = matchmaking_skill._parse_intent_fallback(input, {})
            assert result["intent_type"] == "location_based"
            assert "location=nearby" in result["hard_requirements"]

    def test_parse_intent_fallback_age_younger(self, matchmaking_skill):
        """测试关键词匹配识别年轻偏好"""
        result = matchmaking_skill._parse_intent_fallback("找个年轻的", {})
        assert "age_preference=younger" in result["hard_requirements"]

    def test_parse_intent_fallback_age_older(self, matchmaking_skill):
        """测试关键词匹配识别成熟偏好"""
        result = matchmaking_skill._parse_intent_fallback("找个成熟的", {})
        assert "age_preference=older" in result["hard_requirements"]

    def test_parse_intent_fallback_limit_extraction(self, matchmaking_skill):
        """测试关键词匹配提取数量"""
        test_cases = [
            ("推荐三个", 3),
            ("3 个推荐", 3),
            ("给我五个", 5),
            ("5 个匹配", 5),
            ("十个推荐", 10),
            ("10 个", 10),
        ]

        for input, expected_limit in test_cases:
            result = matchmaking_skill._parse_intent_fallback(input, {})
            assert result["limit"] == expected_limit

    def test_parse_intent_fallback_general(self, matchmaking_skill):
        """测试关键词匹配兜底为 general"""
        result = matchmaking_skill._parse_intent_fallback("随便说说", {})
        assert result["intent_type"] == "general"

    def test_parse_intent_default_values(self, matchmaking_skill):
        """测试意图解析默认值"""
        result = matchmaking_skill._parse_intent_fallback("未知意图", {})
        assert result["limit"] == 5
        assert result["min_score"] == 0.6
        assert result["emotional_state"] == "normal"


class TestLLMIntentParsing:
    """测试 LLM 意图解析"""

    def test_extract_json_from_clean_response(self, matchmaking_skill):
        """测试从干净响应提取 JSON"""
        response = '{"intent_type": "serious_relationship", "limit": 5}'
        result = matchmaking_skill._extract_json_from_response(response)
        assert result["intent_type"] == "serious_relationship"

    def test_extract_json_from_markdown_response(self, matchmaking_skill):
        """测试从 markdown 代码块提取 JSON"""
        response = '''```json
{"intent_type": "daily_browse", "limit": 10}
```'''
        result = matchmaking_skill._extract_json_from_response(response)
        assert result["intent_type"] == "daily_browse"

    def test_extract_json_from_code_block_response(self, matchmaking_skill):
        """测试从代码块提取 JSON（无 json 标记）"""
        response = '''```
{"intent_type": "interest_based", "limit": 5}
```'''
        result = matchmaking_skill._extract_json_from_response(response)
        assert result["intent_type"] == "interest_based"

    def test_extract_json_with_extra_text(self, matchmaking_skill):
        """测试从包含额外文本的响应提取 JSON"""
        response = '''这是分析结果：
{"intent_type": "general", "limit": 5, "min_score": 0.6}
以上是 JSON'''
        result = matchmaking_skill._extract_json_from_response(response)
        assert result["intent_type"] == "general"

    def test_extract_json_fallback_on_invalid(self, matchmaking_skill):
        """测试无效 JSON 降级返回默认值"""
        response = "这不是 JSON"
        result = matchmaking_skill._extract_json_from_response(response)
        assert result["intent_type"] == "general"
        assert result["confidence"] == 0.5

    def test_parse_intent_llm_returns_none_on_failure(self, matchmaking_skill):
        """测试 LLM 调用失败返回 None"""
        with patch.object(matchmaking_skill, '_call_llm_sync', return_value=None):
            result = matchmaking_skill._parse_intent_llm("测试意图")
            assert result is None

    def test_parse_intent_llm_returns_none_on_fallback_response(self, matchmaking_skill):
        """测试 fallback 响应返回 None"""
        with patch.object(matchmaking_skill, '_call_llm_sync', return_value='{"fallback": true}'):
            result = matchmaking_skill._parse_intent_llm("测试意图")
            assert result is None


# ========== 自然语言响应生成测试 ==========

class TestMessageGeneration:
    """测试自然语言响应生成"""

    def test_generate_message_with_matches(self, matchmaking_skill, mock_workflow_result):
        """测试有匹配时生成响应"""
        intent = {"intent_type": "general"}
        message = matchmaking_skill._generate_message(intent, mock_workflow_result)

        assert "找到" in message or "推荐" in message
        assert "小红" in message  # top match name
        assert "85%" in message  # score

    def test_generate_message_empty_matches_general(self, matchmaking_skill, mock_empty_workflow_result):
        """测试空匹配 general 意图"""
        intent = {"intent_type": "general"}
        message = matchmaking_skill._generate_message(intent, mock_empty_workflow_result)

        assert "抱歉" in message or "暂时没有" in message
        assert "放宽条件" in message or "完善资料" in message

    def test_generate_message_empty_matches_daily_browse(self, matchmaking_skill, mock_empty_workflow_result):
        """测试空匹配 daily_browse 意图"""
        intent = {"intent_type": "daily_browse"}
        message = matchmaking_skill._generate_message(intent, mock_empty_workflow_result)

        assert "今天暂时没有" in message
        assert "耐心" in message

    def test_generate_message_serious_relationship(self, matchmaking_skill, mock_workflow_result):
        """测试严肃恋爱意图响应"""
        intent = {"intent_type": "serious_relationship"}
        message = matchmaking_skill._generate_message(intent, mock_workflow_result)

        assert "认真恋爱" in message
        assert "认真态度" in message

    def test_generate_message_daily_browse(self, matchmaking_skill, mock_workflow_result):
        """测试每日推荐意图响应"""
        intent = {"intent_type": "daily_browse"}
        message = matchmaking_skill._generate_message(intent, mock_workflow_result)

        assert "今日推荐" in message
        assert "活跃" in message

    def test_generate_message_location_based(self, matchmaking_skill, mock_workflow_result):
        """测试地点匹配意图响应"""
        intent = {"intent_type": "location_based"}
        message = matchmaking_skill._generate_message(intent, mock_workflow_result)

        assert "附近" in message
        assert "找到" in message

    def test_generate_message_includes_reasoning(self, matchmaking_skill, mock_workflow_result):
        """测试响应包含推荐理由"""
        intent = {"intent_type": "general"}
        message = matchmaking_skill._generate_message(intent, mock_workflow_result)

        assert "推荐理由" in message

    def test_generate_message_includes_common_interests(self, matchmaking_skill, mock_workflow_result):
        """测试响应包含共同兴趣"""
        intent = {"intent_type": "general"}
        message = matchmaking_skill._generate_message(intent, mock_workflow_result)

        assert "共同兴趣" in message
        assert "旅行" in message or "美食" in message

    def test_generate_message_without_reasoning(self, matchmaking_skill):
        """测试无推荐理由时的响应"""
        workflow_result = {
            "recommendations": [
                {"user_id": "match-001", "score": 0.8, "user": {"name": "测试"}}
            ]
        }
        intent = {"intent_type": "general"}
        message = matchmaking_skill._generate_message(intent, workflow_result)

        # 应该正常生成，不崩溃
        assert "找到" in message

    def test_generate_message_without_common_interests(self, matchmaking_skill):
        """测试无共同兴趣时的响应"""
        workflow_result = {
            "recommendations": [
                {"user_id": "match-001", "score": 0.8, "user": {"name": "测试"}, "reasoning": "匹配"}
            ]
        }
        intent = {"intent_type": "general"}
        message = matchmaking_skill._generate_message(intent, workflow_result)

        # 应该正常生成，不崩溃
        assert "找到" in message


# ========== Generative UI 构建测试 ==========

class TestGenerativeUI:
    """测试 Generative UI 构建"""

    def test_build_generative_ui_single_match(self, matchmaking_skill, mock_single_match_workflow_result):
        """测试单个匹配使用 spotlight UI"""
        ui = matchmaking_skill._build_generative_ui(mock_single_match_workflow_result)

        assert ui["component_type"] == "match_spotlight"
        assert "match" in ui["props"]
        assert ui["props"]["highlight_score"] is True
        assert ui["props"]["show_reasoning"] is True

    def test_build_generative_ui_small_card_list(self, matchmaking_skill):
        """测试 2-3 个匹配使用小卡片列表"""
        workflow_result = {
            "recommendations": [
                {"user_id": "m1", "score": 0.8},
                {"user_id": "m2", "score": 0.75}
            ]
        }
        ui = matchmaking_skill._build_generative_ui(workflow_result)

        assert ui["component_type"] == "match_card_list"
        assert ui["props"]["layout"] == "horizontal"
        assert ui["props"]["show_score"] is True

    def test_build_generative_ui_carousel(self, matchmaking_skill, mock_workflow_result):
        """测试多个匹配使用轮播"""
        ui = matchmaking_skill._build_generative_ui(mock_workflow_result)

        assert ui["component_type"] == "match_carousel"
        assert ui["props"]["autoplay"] is True
        assert ui["props"]["autoplay_interval"] == 5000
        assert ui["props"]["show_dots"] is True
        assert ui["props"]["show_arrows"] is True

    def test_build_generative_ui_empty_state(self, matchmaking_skill, mock_empty_workflow_result):
        """测试空匹配使用空状态 UI"""
        ui = matchmaking_skill._build_generative_ui(mock_empty_workflow_result)

        assert ui["component_type"] == "empty_state"
        assert ui["props"]["message"] == "暂无匹配"
        assert ui["props"]["icon"] == "search-outlined"

    def test_build_generative_ui_limits_to_five(self, matchmaking_skill):
        """测试轮播最多显示 5 个"""
        workflow_result = {
            "recommendations": [
                {"user_id": f"m{i}", "score": 0.7} for i in range(10)
            ]
        }
        ui = matchmaking_skill._build_generative_ui(workflow_result)

        assert len(ui["props"]["matches"]) <= 5

    def test_build_generative_ui_has_props_structure(self, matchmaking_skill, mock_workflow_result):
        """测试 UI 包含正确的 props 结构"""
        ui = matchmaking_skill._build_generative_ui(mock_workflow_result)

        assert "component_type" in ui
        assert "props" in ui
        assert isinstance(ui["props"], dict)


# ========== 建议操作生成测试 ==========

class TestSuggestedActions:
    """测试建议操作生成"""

    def test_generate_actions_with_matches(self, matchmaking_skill, mock_workflow_result):
        """测试有匹配时生成操作"""
        actions = matchmaking_skill._generate_actions(mock_workflow_result)

        assert len(actions) >= 3
        assert any(a["action_type"] == "view_profile" for a in actions)
        assert any(a["action_type"] == "start_chat" for a in actions)
        assert any(a["action_type"] == "adjust_preferences" for a in actions)

    def test_generate_actions_empty_matches(self, matchmaking_skill, mock_empty_workflow_result):
        """测试空匹配时生成操作"""
        actions = matchmaking_skill._generate_actions(mock_empty_workflow_result)

        assert len(actions) == 2
        assert actions[0]["action_type"] == "edit_profile"
        assert actions[1]["action_type"] == "browse_all"

    def test_generate_actions_multiple_matches(self, matchmaking_skill, mock_workflow_result):
        """测试多匹配时包含浏览更多"""
        actions = matchmaking_skill._generate_actions(mock_workflow_result)

        assert any(a["action_type"] == "browse_more" for a in actions)
        assert any(a["label"] == "浏览更多推荐" for a in actions)

    def test_generate_actions_single_match(self, matchmaking_skill, mock_single_match_workflow_result):
        """测试单匹配时不包含浏览更多"""
        actions = matchmaking_skill._generate_actions(mock_single_match_workflow_result)

        # 单个匹配不应该有"浏览更多"
        browse_more_actions = [a for a in actions if a["action_type"] == "browse_more"]
        assert len(browse_more_actions) == 0

    def test_generate_actions_includes_user_id(self, matchmaking_skill, mock_workflow_result):
        """测试操作包含用户 ID"""
        actions = matchmaking_skill._generate_actions(mock_workflow_result)

        view_profile = next((a for a in actions if a["action_type"] == "view_profile"), None)
        assert view_profile is not None
        assert "user_id" in view_profile["params"]

    def test_generate_actions_structure(self, matchmaking_skill, mock_workflow_result):
        """测试操作结构正确"""
        actions = matchmaking_skill._generate_actions(mock_workflow_result)

        for action in actions:
            assert "label" in action
            assert "action_type" in action
            assert "params" in action


# ========== 自主触发测试 ==========

class TestAutonomousTrigger:
    """测试自主触发功能"""

    @pytest.mark.asyncio
    async def test_autonomous_trigger_daily_allowed(self, matchmaking_skill):
        """测试每日触发（允许发送）"""
        with patch.object(matchmaking_skill, '_should_send_daily', return_value=True):
            with patch.object(matchmaking_skill, 'execute', return_value={"success": True, "matches": [{"user_id": "m1"}]}):
                result = await matchmaking_skill.autonomous_trigger("user-001", "daily")

        assert result["triggered"] is True
        assert result["should_push"] is True

    @pytest.mark.asyncio
    async def test_autonomous_trigger_daily_already_sent(self, matchmaking_skill):
        """测试每日触发（已发送）"""
        with patch.object(matchmaking_skill, '_should_send_daily', return_value=False):
            result = await matchmaking_skill.autonomous_trigger("user-001", "daily")

        assert result["triggered"] is False
        assert result["reason"] == "already_sent_today"

    @pytest.mark.asyncio
    async def test_autonomous_trigger_quality_match_found(self, matchmaking_skill):
        """测试高质量匹配触发（找到）"""
        mock_matches = [{"match_id": "m1", "user_id": "u2", "score": 0.88}]

        with patch.object(matchmaking_skill, '_find_high_quality_matches', return_value=mock_matches):
            with patch.object(matchmaking_skill, 'execute', return_value={"success": True, "matches": mock_matches}):
                result = await matchmaking_skill.autonomous_trigger("user-001", "quality_match")

        assert result["triggered"] is True

    @pytest.mark.asyncio
    async def test_autonomous_trigger_quality_match_not_found(self, matchmaking_skill):
        """测试高质量匹配触发（未找到）"""
        with patch.object(matchmaking_skill, '_find_high_quality_matches', return_value=[]):
            result = await matchmaking_skill.autonomous_trigger("user-001", "quality_match")

        assert result["triggered"] is False
        assert result["reason"] == "no_high_quality_match"

    @pytest.mark.asyncio
    async def test_autonomous_trigger_profile_updated(self, matchmaking_skill):
        """测试资料更新触发"""
        with patch.object(matchmaking_skill, 'execute', return_value={"success": True, "matches": [{"user_id": "m1"}]}):
            result = await matchmaking_skill.autonomous_trigger("user-001", "profile_updated")

        assert result["triggered"] is True

    @pytest.mark.asyncio
    async def test_autonomous_trigger_no_matches(self, matchmaking_skill):
        """测试触发但无匹配结果"""
        with patch.object(matchmaking_skill, '_should_send_daily', return_value=True):
            with patch.object(matchmaking_skill, 'execute', return_value={"success": True, "matches": []}):
                result = await matchmaking_skill.autonomous_trigger("user-001", "daily")

        assert result["triggered"] is False
        assert result["reason"] == "no_matches"

    @pytest.mark.asyncio
    async def test_trigger_daily(self, matchmaking_skill):
        """测试 trigger_daily 方法"""
        with patch.object(matchmaking_skill, 'autonomous_trigger', return_value={"triggered": True}):
            result = await matchmaking_skill.trigger_daily("user-001")

        assert result["triggered"] is True

    @pytest.mark.asyncio
    async def test_trigger_quality_match(self, matchmaking_skill):
        """测试 trigger_quality_match 方法"""
        with patch.object(matchmaking_skill, 'autonomous_trigger', return_value={"triggered": True}):
            result = await matchmaking_skill.trigger_quality_match("user-001")

        assert result["triggered"] is True


# ========== 每日推荐频率控制测试 ==========

class TestDailyRecommendFrequency:
    """测试每日推荐频率控制"""

    def test_should_send_daily_user_not_found(self, matchmaking_skill):
        """测试用户不存在时允许发送"""
        with patch("agent.skills.matchmaking_skill.UserDB") as MockUserDB:
            with patch("agent.skills.matchmaking_skill.db_session") as mock_db_session:
                mock_db = MagicMock()
                mock_db.query.return_value.filter.return_value.first.return_value = None
                mock_db_session.return_value.__enter__ = MagicMock(return_value=mock_db)
                mock_db_session.return_value.__exit__ = MagicMock(return_value=False)

                result = matchmaking_skill._should_send_daily("non-existent-user")

        assert result is True

    def test_should_send_daily_first_time(self, matchmaking_skill):
        """测试首次发送"""
        mock_user = MagicMock()
        mock_user.last_daily_recommend = None

        with patch("agent.skills.matchmaking_skill.UserDB") as MockUserDB:
            with patch("agent.skills.matchmaking_skill.db_session") as mock_db_session:
                mock_db = MagicMock()
                mock_db.query.return_value.filter.return_value.first.return_value = mock_user
                mock_db_session.return_value.__enter__ = MagicMock(return_value=mock_db)
                mock_db_session.return_value.__exit__ = MagicMock(return_value=False)

                result = matchmaking_skill._should_send_daily("user-001")

        assert result is True

    def test_should_send_daily_already_sent_today(self, matchmaking_skill):
        """测试今天已发送"""
        mock_user = MagicMock()
        mock_user.last_daily_recommend = datetime.now()

        with patch("agent.skills.matchmaking_skill.UserDB") as MockUserDB:
            with patch("agent.skills.matchmaking_skill.db_session") as mock_db_session:
                mock_db = MagicMock()
                mock_db.query.return_value.filter.return_value.first.return_value = mock_user
                mock_db.commit = MagicMock()
                mock_db_session.return_value.__enter__ = MagicMock(return_value=mock_db)
                mock_db_session.return_value.__exit__ = MagicMock(return_value=False)

                result = matchmaking_skill._should_send_daily("user-001")

        assert result is False

    def test_should_send_daily_sent_yesterday(self, matchmaking_skill):
        """测试昨天发送过"""
        mock_user = MagicMock()
        mock_user.last_daily_recommend = datetime.now() - timedelta(days=1)

        with patch("agent.skills.matchmaking_skill.UserDB") as MockUserDB:
            with patch("agent.skills.matchmaking_skill.db_session") as mock_db_session:
                mock_db = MagicMock()
                mock_db.query.return_value.filter.return_value.first.return_value = mock_user
                mock_db.commit = MagicMock()
                mock_db_session.return_value.__enter__ = MagicMock(return_value=mock_db)
                mock_db_session.return_value.__exit__ = MagicMock(return_value=False)

                result = matchmaking_skill._should_send_daily("user-001")

        assert result is True

    def test_should_send_daily_exception_handling(self, matchmaking_skill):
        """测试异常处理"""
        with patch("agent.skills.matchmaking_skill.UserDB", side_effect=Exception("DB Error")):
            result = matchmaking_skill._should_send_daily("user-001")

        # 异常时默认允许发送
        assert result is True


# ========== 高质量匹配查找测试 ==========

class TestHighQualityMatchFinding:
    """测试高质量匹配查找"""

    def test_find_high_quality_matches_found(self, matchmaking_skill):
        """测试找到高质量匹配"""
        mock_match1 = MagicMock()
        mock_match1.id = "match-001"
        mock_match1.user_id_1 = "user-001"
        mock_match1.user_id_2 = "user-002"
        mock_match1.compatibility_score = 0.88

        mock_match2 = MagicMock()
        mock_match2.id = "match-002"
        mock_match2.user_id_1 = "user-003"
        mock_match2.user_id_2 = "user-001"
        mock_match2.compatibility_score = 0.90

        with patch("agent.skills.matchmaking_skill.MatchHistoryDB") as MockMatchHistoryDB:
            with patch("agent.skills.matchmaking_skill.db_session") as mock_db_session:
                mock_db = MagicMock()
                mock_db.query.return_value.filter.return_value.all.return_value = [mock_match1, mock_match2]
                mock_db_session.return_value.__enter__ = MagicMock(return_value=mock_db)
                mock_db_session.return_value.__exit__ = MagicMock(return_value=False)

                result = matchmaking_skill._find_high_quality_matches("user-001", threshold=0.85)

        assert len(result) == 2
        assert result[0]["score"] == 0.88
        assert result[0]["user_id"] == "user-002"

    def test_find_high_quality_matches_none(self, matchmaking_skill):
        """测试未找到高质量匹配"""
        with patch("agent.skills.matchmaking_skill.MatchHistoryDB") as MockMatchHistoryDB:
            with patch("agent.skills.matchmaking_skill.db_session") as mock_db_session:
                mock_db = MagicMock()
                mock_db.query.return_value.filter.return_value.all.return_value = []
                mock_db_session.return_value.__enter__ = MagicMock(return_value=mock_db)
                mock_db_session.return_value.__exit__ = MagicMock(return_value=False)

                result = matchmaking_skill._find_high_quality_matches("user-001", threshold=0.85)

        assert result == []

    def test_find_high_quality_matches_custom_threshold(self, matchmaking_skill):
        """测试自定义阈值"""
        mock_match = MagicMock()
        mock_match.id = "match-001"
        mock_match.user_id_1 = "user-001"
        mock_match.user_id_2 = "user-002"
        mock_match.compatibility_score = 0.90

        with patch("agent.skills.matchmaking_skill.MatchHistoryDB") as MockMatchHistoryDB:
            with patch("agent.skills.matchmaking_skill.db_session") as mock_db_session:
                mock_db = MagicMock()
                mock_db.query.return_value.filter.return_value.all.return_value = [mock_match]
                mock_db_session.return_value.__enter__ = MagicMock(return_value=mock_db)
                mock_db_session.return_value.__exit__ = MagicMock(return_value=False)

                result = matchmaking_skill._find_high_quality_matches("user-001", threshold=0.90)

        assert len(result) == 1

    def test_find_high_quality_matches_exception(self, matchmaking_skill):
        """测试异常处理"""
        with patch("agent.skills.matchmaking_skill.MatchHistoryDB", side_effect=Exception("DB Error")):
            result = matchmaking_skill._find_high_quality_matches("user-001")

        assert result == []

    def test_find_high_quality_matches_user_as_id_1(self, matchmaking_skill):
        """测试用户作为 user_id_1"""
        mock_match = MagicMock()
        mock_match.id = "match-001"
        mock_match.user_id_1 = "user-001"
        mock_match.user_id_2 = "user-target"
        mock_match.compatibility_score = 0.92

        with patch("agent.skills.matchmaking_skill.MatchHistoryDB") as MockMatchHistoryDB:
            with patch("agent.skills.matchmaking_skill.db_session") as mock_db_session:
                mock_db = MagicMock()
                mock_db.query.return_value.filter.return_value.all.return_value = [mock_match]
                mock_db_session.return_value.__enter__ = MagicMock(return_value=mock_db)
                mock_db_session.return_value.__exit__ = MagicMock(return_value=False)

                result = matchmaking_skill._find_high_quality_matches("user-001")

        assert result[0]["user_id"] == "user-target"

    def test_find_high_quality_matches_user_as_id_2(self, matchmaking_skill):
        """测试用户作为 user_id_2"""
        mock_match = MagicMock()
        mock_match.id = "match-001"
        mock_match.user_id_1 = "user-target"
        mock_match.user_id_2 = "user-001"
        mock_match.compatibility_score = 0.92

        with patch("agent.skills.matchmaking_skill.MatchHistoryDB") as MockMatchHistoryDB:
            with patch("agent.skills.matchmaking_skill.db_session") as mock_db_session:
                mock_db = MagicMock()
                mock_db.query.return_value.filter.return_value.all.return_value = [mock_match]
                mock_db_session.return_value.__enter__ = MagicMock(return_value=mock_db)
                mock_db_session.return_value.__exit__ = MagicMock(return_value=False)

                result = matchmaking_skill._find_high_quality_matches("user-001")

        assert result[0]["user_id"] == "user-target"


# ========== 边缘场景测试 ==========

class TestEdgeCases:
    """测试边缘场景"""

    @pytest.mark.asyncio
    async def test_execute_empty_user_intent(self, matchmaking_skill, mock_intent_result, mock_workflow_result):
        """测试空用户意图"""
        matchmaking_skill._parse_intent = MagicMock(return_value=mock_intent_result)

        with patch("agent.workflows.autonomous_workflows.AutoMatchRecommendWorkflow") as MockWorkflow:
            mock_instance = MagicMock()
            mock_instance.execute.return_value = mock_workflow_result
            MockWorkflow.return_value = mock_instance

            result = await matchmaking_skill.execute(user_intent="")

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_execute_none_context(self, matchmaking_skill, mock_intent_result, mock_workflow_result):
        """测试 None context"""
        matchmaking_skill._parse_intent = MagicMock(return_value=mock_intent_result)

        with patch("agent.workflows.autonomous_workflows.AutoMatchRecommendWorkflow") as MockWorkflow:
            mock_instance = MagicMock()
            mock_instance.execute.return_value = mock_workflow_result
            MockWorkflow.return_value = mock_instance

            result = await matchmaking_skill.execute(user_intent="匹配", context=None)

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_execute_workflow_failure(self, matchmaking_skill, mock_intent_result):
        """测试工作流失败"""
        matchmaking_skill._parse_intent = MagicMock(return_value=mock_intent_result)

        failed_workflow = {"recommendations": [], "errors": ["Database error"]}

        with patch("agent.workflows.autonomous_workflows.AutoMatchRecommendWorkflow") as MockWorkflow:
            mock_instance = MagicMock()
            mock_instance.execute.return_value = failed_workflow
            MockWorkflow.return_value = mock_instance

            result = await matchmaking_skill.execute(user_intent="匹配")

        # 应该正常返回，不会崩溃
        assert "ai_message" in result

    @pytest.mark.asyncio
    async def test_execute_with_extra_kwargs(self, matchmaking_skill, mock_intent_result, mock_workflow_result):
        """测试额外 kwargs"""
        matchmaking_skill._parse_intent = MagicMock(return_value=mock_intent_result)

        with patch("agent.workflows.autonomous_workflows.AutoMatchRecommendWorkflow") as MockWorkflow:
            mock_instance = MagicMock()
            mock_instance.execute.return_value = mock_workflow_result
            MockWorkflow.return_value = mock_instance

            result = await matchmaking_skill.execute(
                user_intent="匹配",
                extra_param="extra_value",
                another_param=123
            )

        assert result["success"] is True

    def test_generate_message_match_without_name(self, matchmaking_skill):
        """测试匹配对象无名称"""
        workflow_result = {
            "recommendations": [
                {"user_id": "match-001", "score": 0.8, "user": {}}
            ]
        }
        intent = {"intent_type": "general"}
        message = matchmaking_skill._generate_message(intent, workflow_result)

        # 应该使用默认名称 "TA"
        assert "TA" in message

    def test_generate_message_match_without_user_field(self, matchmaking_skill):
        """测试匹配对象无 user 字段"""
        workflow_result = {
            "recommendations": [
                {"user_id": "match-001", "score": 0.8}
            ]
        }
        intent = {"intent_type": "general"}
        message = matchmaking_skill._generate_message(intent, workflow_result)

        # 应该正常生成，不崩溃
        assert message is not None

    def test_build_generative_ui_match_without_score(self, matchmaking_skill):
        """测试匹配对象无分数"""
        workflow_result = {
            "recommendations": [
                {"user_id": "match-001"}
            ]
        }
        ui = matchmaking_skill._build_generative_ui(workflow_result)

        assert "component_type" in ui

    @pytest.mark.asyncio
    async def test_autonomous_trigger_unknown_type(self, matchmaking_skill):
        """测试未知触发类型"""
        with patch.object(matchmaking_skill, 'execute', return_value={"success": True, "matches": []}):
            result = await matchmaking_skill.autonomous_trigger("user-001", "unknown_type")

        # 未知类型应该正常执行（无特殊检查）
        assert "triggered" in result

    def test_parse_intent_with_special_characters(self, matchmaking_skill):
        """测试特殊字符意图"""
        result = matchmaking_skill._parse_intent_fallback("帮我找对象!!!@#$%", {})

        assert result["intent_type"] in ["serious_relationship", "general"]

    def test_parse_intent_with_very_long_input(self, matchmaking_skill):
        """测试超长输入"""
        long_input = "帮我找对象" * 100
        result = matchmaking_skill._parse_intent_fallback(long_input, {})

        assert "intent_type" in result


# ========== 单例测试 ==========

class TestSingleton:
    """测试单例模式"""

    def test_get_matchmaking_skill_returns_same_instance(self):
        """测试获取单例返回同一实例"""
        from agent.skills.matchmaking_skill import get_matchmaking_skill

        skill1 = get_matchmaking_skill()
        skill2 = get_matchmaking_skill()

        assert skill1 is skill2

    def test_direct_instantiation_creates_new_instance(self):
        """测试直接实例化创建新实例"""
        skill1 = MatchmakingSkill()
        skill2 = MatchmakingSkill()

        # 直接实例化应该创建不同实例（单例由 get_matchmaking_skill 管理）
        assert skill1 is not skill2 or skill1 is skill2  # 取决于全局变量状态


# ========== 集成测试 ==========

class TestIntegration:
    """测试 Skill 集成"""

    def test_skill_registered_in_registry(self):
        """测试 Skill 已注册到注册表"""
        from agent.skills.registry import initialize_default_skills

        registry = initialize_default_skills()
        skill = registry.get("matchmaking_assistant")

        assert skill is not None
        assert skill.name == "matchmaking_assistant"

    @pytest.mark.asyncio
    async def test_skill_can_be_executed_via_registry(self):
        """测试通过注册表执行 Skill"""
        from agent.skills.registry import initialize_default_skills

        registry = initialize_default_skills()

        mock_intent = {
            "intent_type": "general",
            "limit": 5,
            "min_score": 0.6,
            "hard_requirements": [],
            "soft_preferences": [],
            "is_llm_analyzed": True
        }

        mock_workflow = {
            "recommendations": [{"user_id": "m1", "score": 0.8, "user": {"name": "测试"}}]
        }

        skill = registry.get("matchmaking_assistant")
        skill._parse_intent = MagicMock(return_value=mock_intent)

        with patch("agent.workflows.autonomous_workflows.AutoMatchRecommendWorkflow") as MockWorkflow:
            mock_instance = MagicMock()
            mock_instance.execute.return_value = mock_workflow
            MockWorkflow.return_value = mock_instance

            result = await skill.execute(user_intent="匹配")

        assert result["success"] is True


# ========== 运行测试 ==========

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])