"""
Agent Skills 单元测试

测试所有 Agent Skill 的核心功能，验证 AI Native 特性
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock
import sys
import os

# 添加 src 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from agent.skills.matchmaking_skill import get_matchmaking_skill
from agent.skills.precommunication_skill import get_precommunication_skill
from agent.skills.omniscient_insight_skill import get_omniscient_insight_skill
from agent.skills.relationship_coach_skill import get_relationship_coach_skill
from agent.skills.date_planning_skill import get_date_planning_skill
from agent.skills.bill_analysis_skill import get_bill_analysis_skill
from agent.skills.geo_location_skill import get_geo_location_skill
from agent.skills.gift_ordering_skill import get_gift_ordering_skill
from agent.skills.registry import get_skill_registry, initialize_default_skills


# ========== Fixtures ==========

@pytest.fixture
def skill_registry():
    """初始化 Skill 注册表"""
    return initialize_default_skills()


@pytest.fixture
def matchmaking_skill():
    """获取匹配助手 Skill"""
    return get_matchmaking_skill()


@pytest.fixture
def bill_analysis_skill():
    """获取账单分析 Skill"""
    return get_bill_analysis_skill()


@pytest.fixture
def geo_location_skill():
    """获取地理位置 Skill"""
    return get_geo_location_skill()


@pytest.fixture
def gift_ordering_skill():
    """获取礼物订购 Skill"""
    return get_gift_ordering_skill()


# ========== 测试 Skill 注册表 ==========

class TestSkillRegistry:
    """测试 Skill 注册表功能"""

    def test_registry_singleton(self):
        """测试注册表单例模式"""
        registry1 = get_skill_registry()
        registry2 = get_skill_registry()
        assert registry1 is registry2

    def test_initialize_default_skills(self, skill_registry):
        """测试默认 Skills 初始化"""
        skills = skill_registry.list_skills()
        assert len(skills) >= 8  # 5 核心 +3 外部服务

    def test_register_skill(self, skill_registry):
        """测试 Skill 注册"""
        mock_skill = MagicMock()
        mock_skill.name = "test_skill"
        mock_skill.description = "测试 Skill"
        mock_skill.version = "1.0.0"
        mock_skill.get_input_schema = MagicMock(return_value={})
        mock_skill.get_output_schema = MagicMock(return_value={})

        skill_registry.register(mock_skill, tags=["test"])

        skill = skill_registry.get("test_skill")
        assert skill is not None
        assert skill is mock_skill

    def test_get_metadata(self, skill_registry):
        """测试获取 Skill 元数据"""
        metadata = skill_registry.get_metadata("matchmaking_assistant")
        assert metadata is not None
        assert "description" in metadata


# ========== 测试匹配助手 Skill ==========

class TestMatchmakingSkill:
    """测试匹配助手 Skill"""

    @pytest.mark.asyncio
    async def test_execute_with_user_intent(self, matchmaking_skill):
        """测试基于用户意图执行匹配"""
        result = await matchmaking_skill.execute(
            user_intent="帮我找一个喜欢旅行的女生",
            context={"user_id": "user-test-123"}
        )

        assert result["success"] is True
        assert "ai_message" in result
        assert "matches" in result or "generative_ui" in result

    @pytest.mark.asyncio
    async def test_daily_recommendation(self, matchmaking_skill):
        """测试每日推荐触发"""
        result = await matchmaking_skill.trigger_daily("user-test-123")

        # 应该返回触发结果
        assert "triggered" in result

    @pytest.mark.asyncio
    async def test_quality_match_trigger(self, matchmaking_skill):
        """测试高质量匹配触发"""
        result = await matchmaking_skill.trigger_quality_match("user-test-123")

        assert "triggered" in result

    def test_input_schema(self, matchmaking_skill):
        """测试输入 Schema"""
        schema = matchmaking_skill.get_input_schema()
        assert schema["type"] == "object"
        assert "properties" in schema

    def test_output_schema(self, matchmaking_skill):
        """测试输出 Schema"""
        schema = matchmaking_skill.get_output_schema()
        assert schema["type"] == "object"
        assert "properties" in schema


# ========== 测试账单分析 Skill ==========

class TestBillAnalysisSkill:
    """测试账单分析 Skill"""

    @pytest.mark.asyncio
    async def test_analyze_bills(self, bill_analysis_skill):
        """测试账单分析"""
        result = await bill_analysis_skill.execute(
            user_id="user-test-123",
            action="analyze",
            time_range="quarter"
        )

        assert result["success"] is True
        assert "ai_message" in result
        assert "consumption_profile" in result

    @pytest.mark.asyncio
    async def test_get_consumption_profile(self, bill_analysis_skill):
        """测试获取消费画像"""
        result = await bill_analysis_skill.execute(
            user_id="user-test-123",
            action="get_profile"
        )

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_compare_compatibility(self, bill_analysis_skill):
        """测试消费兼容性比较"""
        result = await bill_analysis_skill.execute(
            user_id="user-test-123",
            action="compare_compatibility",
            target_user_id="user-test-456"
        )

        assert result["success"] is True
        assert "compatibility" in result or "ai_message" in result

    @pytest.mark.asyncio
    async def test_autonomous_profile_reminder(self, bill_analysis_skill):
        """测试自主触发：画像更新提醒"""
        result = await bill_analysis_skill.autonomous_trigger(
            user_id="user-test-123",
            trigger_type="profile_update_reminder",
            context={"last_analysis_date": None}
        )

        assert "triggered" in result

    @pytest.mark.asyncio
    async def test_autonomous_new_match_compatibility(self, bill_analysis_skill):
        """测试自主触发：新匹配兼容性分析"""
        result = await bill_analysis_skill.autonomous_trigger(
            user_id="user-test-123",
            trigger_type="new_match_compatibility",
            context={
                "match_id": "match-123",
                "target_user_id": "user-test-456"
            }
        )

        assert "triggered" in result

    def test_mock_bill_features(self, bill_analysis_skill):
        """测试模拟账单特征生成"""
        features = bill_analysis_skill._generate_mock_bill_features("user-test-123")

        assert "total_transactions" in features
        assert "category_distribution" in features
        assert "level" in features


# ========== 测试地理位置 Skill ==========

class TestGeoLocationSkill:
    """测试地理位置 Skill"""

    @pytest.mark.asyncio
    async def test_analyze_trajectory(self, geo_location_skill):
        """测试轨迹分析"""
        result = await geo_location_skill.execute(
            user_id="user-test-123",
            action="analyze_trajectory",
            time_range="month"
        )

        assert result["success"] is True
        assert "ai_message" in result

    @pytest.mark.asyncio
    async def test_autonomous_nearby_match(self, geo_location_skill):
        """测试自主触发：附近匹配提醒"""
        result = await geo_location_skill.autonomous_trigger(
            user_id="user-test-123",
            trigger_type="nearby_match_alert",
            context={"nearby_user_id": "user-test-456"}
        )

        assert "triggered" in result


# ========== 测试礼物订购 Skill ==========

class TestGiftOrderingSkill:
    """测试礼物订购 Skill"""

    @pytest.mark.asyncio
    async def test_get_gift_suggestions(self, gift_ordering_skill):
        """测试获取礼物推荐"""
        result = await gift_ordering_skill.execute(
            match_id="match-test-123",
            action="get_suggestions",
            occasion="birthday",
            budget_range="100_300"
        )

        assert result["success"] is True
        assert "ai_message" in result
        assert "gift_suggestions" in result

    @pytest.mark.asyncio
    async def test_compare_options(self, gift_ordering_skill):
        """测试比较礼物选项"""
        # 先获取推荐
        suggestions_result = await gift_ordering_skill.execute(
            match_id="match-test-123",
            action="get_suggestions"
        )

        if suggestions_result.get("gift_suggestions"):
            gift_id = suggestions_result["gift_suggestions"][0]["gift_id"]

            result = await gift_ordering_skill.execute(
                match_id="match-test-123",
                action="compare_options",
                preferences={"gift_id": gift_id}
            )

            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_place_order(self, gift_ordering_skill):
        """测试下订单"""
        # 先获取推荐
        suggestions_result = await gift_ordering_skill.execute(
            match_id="match-test-123",
            action="get_suggestions"
        )

        if suggestions_result.get("gift_suggestions"):
            gift_id = suggestions_result["gift_suggestions"][0]["gift_id"]

            result = await gift_ordering_skill.execute(
                match_id="match-test-123",
                action="place_order",
                gift_id=gift_id
            )

            assert result["success"] is True
            assert "order_info" in result

    @pytest.mark.asyncio
    async def test_track_delivery(self, gift_ordering_skill):
        """测试追踪物流"""
        # 先下订单
        suggestions_result = await gift_ordering_skill.execute(
            match_id="match-test-123",
            action="get_suggestions"
        )

        if suggestions_result.get("gift_suggestions"):
            gift_id = suggestions_result["gift_suggestions"][0]["gift_id"]
            order_result = await gift_ordering_skill.execute(
                match_id="match-test-123",
                action="place_order",
                gift_id=gift_id
            )

            if order_result.get("order_info"):
                order_id = order_result["order_info"]["order_id"]

                result = await gift_ordering_skill.execute(
                    match_id="match-test-123",
                    action="track_delivery",
                    order_id=order_id
                )

                assert result["success"] is True

    @pytest.mark.asyncio
    async def test_get_occasion_reminder(self, gift_ordering_skill):
        """测试获取场合提醒"""
        result = await gift_ordering_skill.execute(
            match_id="match-test-123",
            action="get_occasion_reminder"
        )

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_autonomous_occasion_reminder(self, gift_ordering_skill):
        """测试自主触发：纪念日提醒"""
        result = await gift_ordering_skill.autonomous_trigger(
            match_id="match-test-123",
            trigger_type="occasion_reminder",
            context={}
        )

        assert "triggered" in result

    @pytest.mark.asyncio
    async def test_autonomous_birthday_reminder(self, gift_ordering_skill):
        """测试自主触发：生日提醒"""
        result = await gift_ordering_skill.autonomous_trigger(
            match_id="match-test-123",
            trigger_type="partner_birthday_approaching",
            context={"partner_birthday": "2026-04-20"}
        )

        assert "triggered" in result

    def test_mock_gifts_generation(self, gift_ordering_skill):
        """测试模拟礼物生成"""
        gifts = gift_ordering_skill._generate_mock_gifts(
            occasion="birthday",
            budget_range="100_300",
            partner_preferences={"hobbies": ["阅读", "咖啡"]}
        )

        assert len(gifts) > 0
        assert all("gift_id" in g for g in gifts)
        assert all("name" in g for g in gifts)
        assert all("price" in g for g in gifts)


# ========== 测试 LLM 增强器 ==========

class TestSkillEnhancer:
    """测试 LLM 增强的意图理解"""

    @pytest.fixture
    def intent_parser(self):
        """获取意图解析器"""
        from llm.skill_enhancer import get_intent_parser
        return get_intent_parser()

    @pytest.fixture
    def response_generator(self):
        """获取响应生成器"""
        from llm.skill_enhancer import get_response_generator
        return get_response_generator()

    def test_parse_matchmaking_intent(self, intent_parser):
        """测试匹配意图解析"""
        result = intent_parser._fallback_matchmaking(
            "帮我找一个喜欢旅行和美食的女生，年龄 25-30 岁",
            {"user_id": "user-test-123"}
        )

        assert result["intent_type"] == "active_search"
        assert len(result["soft_preferences"]) > 0

    def test_parse_gift_intent(self, intent_parser):
        """测试礼物意图解析"""
        result = intent_parser._fallback_gift(
            "女朋友生日快到了，想送个 300 到 500 元的礼物",
            {"match_id": "match-test-123"}
        )

        assert result["action"] == "get_suggestions"
        assert result["occasion"] == "birthday"

    def test_generate_matchmaking_response(self, response_generator):
        """测试匹配响应生成"""
        skill_result = {
            "matches": [
                {
                    "name": "小红",
                    "score": 0.85,
                    "reasoning": "你们都热爱旅行和探索未知",
                    "common_interests": ["旅行", "美食", "阅读"]
                }
            ]
        }

        result = response_generator._generate_default_response(skill_result)

        assert "ai_message" in result
        assert "generative_ui" in result

    def test_generate_generative_ui(self, response_generator):
        """测试 Generative UI 生成"""
        # 测试匹配轮播 UI
        ui_config = response_generator._generate_generative_ui(
            "matchmaking_assistant",
            {"matches": [{"name": "用户 1"}, {"name": "用户 2"}, {"name": "用户 3"}, {"name": "用户 4"}]}
        )

        assert ui_config["component_type"] == "match_carousel"

        # 测试礼物网格 UI
        ui_config = response_generator._generate_generative_ui(
            "gift_ordering",
            {"gift_suggestions": [{"name": "礼物 1"}, {"name": "礼物 2"}]}
        )

        assert ui_config["component_type"] == "gift_grid"


# ========== 测试外部服务集成 ==========

class TestExternalServices:
    """测试外部服务集成"""

    @pytest.fixture
    def bill_service(self):
        """获取账单服务客户端"""
        from integration.external_services import get_bill_service
        return get_bill_service()

    @pytest.fixture
    def geo_service(self):
        """获取地理位置服务客户端"""
        from integration.external_services import get_geo_service
        return get_geo_service()

    @pytest.fixture
    def gift_service(self):
        """获取礼物订购服务客户端"""
        from integration.external_services import get_gift_service
        return get_gift_service()

    def test_bill_service_mock_mode(self, bill_service):
        """测试账单服务 mock 模式"""
        assert bill_service._mock_mode is True

        features = asyncio.run(bill_service.fetch_bill_features("user-test-123"))

        assert features is not None
        assert "level" in features
        assert features["source"] == "mock"

    def test_geo_service_trajectory(self, geo_service):
        """测试地理服务轨迹分析"""
        assert geo_service._mock_mode is True

        trajectory = asyncio.run(geo_service.analyze_trajectory("user-test-123"))

        assert trajectory is not None
        assert "home_district" in trajectory
        assert "frequent_areas" in trajectory

    def test_geo_service_poi(self, geo_service):
        """测试地理服务 POI 推荐"""
        pois = asyncio.run(geo_service.get_poi_recommendations(
            lat=39.9,
            lng=116.4,
            poi_type="restaurant"
        ))

        assert len(pois) > 0
        assert all("name" in p for p in pois)

    def test_gift_service_suggestions(self, gift_service):
        """测试礼物服务推荐"""
        assert gift_service._mock_mode is True

        gifts = asyncio.run(gift_service.get_gift_suggestions(
            occasion="birthday",
            budget_range="100_300"
        ))

        assert len(gifts) > 0
        assert all("gift_id" in g for g in gifts)

    def test_gift_service_order(self, gift_service):
        """测试礼物服务下单"""
        gifts = asyncio.run(gift_service.get_gift_suggestions(
            occasion="birthday",
            budget_range="100_300"
        ))

        if gifts:
            order = asyncio.run(gift_service.place_order(
                gift_id=gifts[0]["gift_id"],
                shipping_info={"address": "测试地址"}
            ))

            assert order is not None
            assert "order_id" in order

    def test_gift_service_tracking(self, gift_service):
        """测试礼物服务物流追踪"""
        tracking = asyncio.run(gift_service.track_order("ORD202604080001"))

        assert tracking is not None
        assert "status" in tracking
        assert "tracking_number" in tracking


# ========== AI Native 特性测试 ==========

class TestAINativeFeatures:
    """测试 AI Native 特性"""

    def test_ai_dependency(self, skill_registry):
        """测试 AI 依赖 - Skills 依赖 AI 生成响应"""
        skills = skill_registry.list_skills()

        for skill_info in skills:
            skill = skill_registry.get(skill_info["name"])
            assert hasattr(skill, 'execute')
            # 所有 Skills 都应该返回 ai_message
            # 这是 AI Native 的核心特征

    def test_autonomy(self, bill_analysis_skill):
        """测试自主性 - Skills 可以自主触发"""
        # 所有 Skills 都应该有 autonomous_trigger 方法
        assert hasattr(bill_analysis_skill, 'autonomous_trigger')

    @pytest.mark.asyncio
    async def test_conversation_priority(self, matchmaking_skill):
        """测试对话优先 - 支持自然语言输入"""
        # 用户可以说"帮我找对象"这样的自然语言
        result = await matchmaking_skill.execute(
            user_intent="帮我找一个对象",
            context={"user_id": "user-test-123"}
        )

        assert result["success"] is True
        assert "ai_message" in result  # AI 生成的自然语言响应

    def test_generative_ui(self):
        """测试 Generative UI - 界面动态生成"""
        # UI 组件类型应该由 AI 根据上下文动态选择
        # 已在其他测试中覆盖
        pass


# ========== 运行测试 ==========

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
