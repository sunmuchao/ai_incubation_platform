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

# 注：matchmaking_skill 已废弃删除，匹配逻辑在 ConversationMatchService/HerAdvisorService
from agent.skills.precommunication_skill import get_precommunication_skill
from agent.skills.omniscient_insight_skill import get_omniscient_insight_skill
from agent.skills.relationship_coach_skill import get_relationship_coach_skill
from agent.skills.date_planning_skill import get_date_planning_skill
from agent.skills.bill_analysis_skill import get_bill_analysis_skill
# 注：geo_location_skill, gift_ordering_skill 已删除，改用 REST API
from agent.skills.registry import get_skill_registry, initialize_default_skills


# ========== Fixtures ==========

@pytest.fixture
def skill_registry():
    """初始化 Skill 注册表"""
    return initialize_default_skills()


# 注：geo_location_skill, gift_ordering_skill, matchmaking_skill 已删除，改用 REST API 或 HerAdvisorService


@pytest.fixture
def bill_analysis_skill():
    """获取账单分析 Skill"""
    return get_bill_analysis_skill()


# 注：geo_location_skill, gift_ordering_skill 已删除，相关测试已移除


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
        # matchmaking_assistant 已删除，使用 bill_analysis 测试
        metadata = skill_registry.get_metadata("bill_analysis")
        assert metadata is not None
        assert "description" in metadata


# 注：TestMatchmakingSkill 已删除，matchmaking_skill 废弃
# 匹配逻辑在 ConversationMatchService 和 HerAdvisorService 中测试


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


# 注：TestGeoLocationSkill, TestGiftOrderingSkill 已删除，改用 REST API 测试
# 注：TestSkillEnhancer 已删除，llm.skill_enhancer 模块已废弃


# ========== 测试外部服务集成 ==========
# 注：external_services.py 已移除，相关测试迁移至具体服务测试文件

# class TestExternalServices:
#     """测试外部服务集成 - 已迁移到具体服务测试"""


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

    @pytest.mark.skip(reason="matchmaking_skill 已废弃删除，匹配逻辑在 HerAdvisorService")
    async def test_conversation_priority(self):
        """测试对话优先 - 支持自然语言输入"""
        # matchmaking_skill 已废弃删除
        # 匹配逻辑在 HerAdvisorService 中，详见 test_her_advisor_service.py

    def test_generative_ui(self):
        """测试 Generative UI - 界面动态生成"""
        # UI 组件类型应该由 AI 根据上下文动态选择
        # 已在其他测试中覆盖
        pass


# ========== 新增：API → Skill 架构测试 ==========

class TestEmotionAnalysisSkill:
    """测试情感分析 Skill"""

    @pytest.fixture
    def emotion_skill(self):
        """获取情感分析 Skill"""
        from agent.skills.emotion_analysis_skill import get_emotion_analysis_skill
        return get_emotion_analysis_skill()

    def test_skill_metadata(self, emotion_skill):
        """测试 Skill 元数据"""
        assert emotion_skill.name == "emotion_translator"
        assert emotion_skill.version == "1.0.0"
        assert "微表情" in emotion_skill.description

    def test_input_schema(self, emotion_skill):
        """测试输入 Schema"""
        schema = emotion_skill.get_input_schema()
        assert schema["type"] == "object"
        assert "session_id" in schema["required"]
        assert "analysis_type" in schema["required"]

    @pytest.mark.asyncio
    async def test_execute_returns_correct_structure(self, emotion_skill):
        """测试 execute 返回正确结构"""
        result = await emotion_skill.execute(
            session_id="test_session",
            analysis_type="micro_expression",
            facial_data={"landmarks": []},
            context={"user_id": "user_123"}
        )

        assert result["success"] is True
        assert "ai_message" in result
        assert "skill_metadata" in result


class TestSafetyGuardianSkill:
    """测试安全守护 Skill"""

    @pytest.fixture
    def safety_skill(self):
        """获取安全守护 Skill"""
        from agent.skills.safety_guardian_skill import get_safety_guardian_skill
        return get_safety_guardian_skill()

    def test_skill_metadata(self, safety_skill):
        """测试 Skill 元数据"""
        assert safety_skill.name == "safety_guardian"
        assert "位置安全" in safety_skill.description

    def test_risk_levels(self, safety_skill):
        """测试风险等级常量"""
        assert safety_skill.RISK_LOW == "low"
        assert safety_skill.RISK_MEDIUM == "medium"
        assert safety_skill.RISK_HIGH == "high"
        assert safety_skill.RISK_CRITICAL == "critical"

    def test_risk_assessment(self, safety_skill):
        """测试风险评估逻辑"""
        # 测试高异常数量触发高风险
        result = safety_skill._assess_risk({
            "risk_level": safety_skill.RISK_LOW,
            "risk_score": 0.3,
            "anomalies": ["a", "b", "c"]  # 3个异常触发高风险
        })
        assert result["level"] == safety_skill.RISK_HIGH
        assert result["requires_action"] is True

        # 测试少量异常触发中等风险
        result = safety_skill._assess_risk({
            "risk_level": safety_skill.RISK_LOW,
            "risk_score": 0.2,
            "anomalies": ["a"]  # 1个异常
        })
        assert result["level"] == safety_skill.RISK_MEDIUM

    @pytest.mark.asyncio
    async def test_execute_location_check(self, safety_skill):
        """测试位置安全检查"""
        result = await safety_skill.execute(
            session_id="test_session",
            check_type="location",
            user_id="user_123",
            location_data={"latitude": 39.9, "longitude": 116.4}
        )

        assert result["success"] is True
        assert "safety_check_result" in result


class TestEmotionMediatorSkill:
    """测试情感调解 Skill"""

    @pytest.fixture
    def mediator_skill(self):
        """获取情感调解 Skill"""
        from agent.skills.emotion_mediator_skill import get_emotion_mediator_skill
        return get_emotion_mediator_skill()

    def test_skill_metadata(self, mediator_skill):
        """测试 Skill 元数据"""
        assert mediator_skill.name == "emotion_mediator"
        assert "吵架预警" in mediator_skill.description

    def test_conflict_detection(self, mediator_skill):
        """测试冲突检测逻辑"""
        conversation_history = [
            {"content": "你总是这样！"},
            {"content": "你从来不关心我！"},
            {"content": "每次都是我的错！"}
        ]

        result = mediator_skill._detect_conflict(conversation_history)

        assert result["level"] in ["low", "medium", "high", "critical"]
        assert result["score"] > 0
        assert len(result["issues"]) > 0

    @pytest.mark.asyncio
    async def test_execute_conflict_detection(self, mediator_skill):
        """测试执行冲突检测"""
        result = await mediator_skill.execute(
            conversation_id="conv_123",
            user_a_id="user_a",
            user_b_id="user_b",
            service_type="conflict_detection"
        )

        assert result["success"] is True
        assert "mediation_result" in result


class TestLoveLanguageTranslatorSkill:
    """测试爱之语翻译 Skill"""

    @pytest.fixture
    def love_skill(self):
        """获取爱之语翻译 Skill"""
        from agent.skills.love_language_translator_skill import get_love_language_translator_skill
        return get_love_language_translator_skill()

    def test_skill_metadata(self, love_skill):
        """测试 Skill 元数据"""
        assert love_skill.name == "love_language_translator"
        assert "肯定的言辞" in str(love_skill.LOVE_LANGUAGES)

    def test_love_language_types(self, love_skill):
        """测试爱之语类型定义"""
        assert "words" in love_skill.LOVE_LANGUAGES
        assert "time" in love_skill.LOVE_LANGUAGES
        assert "gifts" in love_skill.LOVE_LANGUAGES
        assert "acts" in love_skill.LOVE_LANGUAGES
        assert "touch" in love_skill.LOVE_LANGUAGES

    def test_analyze_love_language(self, love_skill):
        """测试爱之语分析"""
        result = love_skill._analyze_love_language("你都没时间陪我")
        assert "time" in result["detected_types"] or result["primary_type"] is not None

    @pytest.mark.asyncio
    async def test_execute_translation(self, love_skill):
        """测试执行翻译"""
        result = await love_skill.execute(
            user_id="user_a",
            target_user_id="user_b",
            expression="你都不夸我",
            translation_type="expression"
        )

        assert result["success"] is True
        assert "translation_result" in result


class TestSilenceBreakerSkill:
    """测试沉默破冰 Skill"""

    @pytest.fixture
    def silence_skill(self):
        """获取沉默破冰 Skill"""
        from agent.skills.silence_breaker_skill import get_silence_breaker_skill
        return get_silence_breaker_skill()

    def test_skill_metadata(self, silence_skill):
        """测试 Skill 元数据"""
        assert silence_skill.name == "silence_breaker"
        assert "尴尬沉默检测" in silence_skill.description

    def test_silence_thresholds(self, silence_skill):
        """测试沉默阈值"""
        assert silence_skill.SILENCE_THRESHOLD["minor"] == 5
        assert silence_skill.SILENCE_THRESHOLD["moderate"] == 10
        assert silence_skill.SILENCE_THRESHOLD["severe"] == 15
        assert silence_skill.SILENCE_THRESHOLD["critical"] == 30

    def test_classify_silence_level(self, silence_skill):
        """测试沉默等级分类"""
        assert silence_skill._classify_silence_level(3) == "normal"
        assert silence_skill._classify_silence_level(7) == "minor"  # 5-10秒是 minor
        assert silence_skill._classify_silence_level(12) == "moderate"  # 10-15秒是 moderate
        assert silence_skill._classify_silence_level(20) == "severe"
        assert silence_skill._classify_silence_level(35) == "critical"

    @pytest.mark.asyncio
    async def test_execute_generates_topics(self, silence_skill):
        """测试执行生成话题"""
        result = await silence_skill.execute(
            conversation_id="conv_123",
            user_a_id="user_a",
            user_b_id="user_b",
            silence_duration=12.0
        )

        assert result["success"] is True
        assert "silence_analysis" in result
        assert "generated_topics" in result


class TestDateCoachSkill:
    """测试约会教练 Skill（含实时指导）"""

    @pytest.fixture
    def coach_skill(self):
        """获取约会教练 Skill"""
        from agent.skills.date_coach_skill import get_date_coach_skill
        return get_date_coach_skill()

    def test_skill_metadata(self, coach_skill):
        """测试 Skill 元数据"""
        assert coach_skill.name == "date_coach"
        assert "约会模拟" in coach_skill.description

    def test_service_types_include_realtime_help(self, coach_skill):
        """测试服务类型包含 realtime_help"""
        schema = coach_skill.get_input_schema()
        service_types = schema["properties"]["service_type"]["enum"]
        assert "realtime_help" in service_types

    @pytest.mark.asyncio
    async def test_execute_outfit_recommendation(self, coach_skill):
        """测试执行穿搭推荐"""
        result = await coach_skill.execute(
            user_id="user_123",
            service_type="outfit_recommendation",
            date_context={"date_type": "first_date", "weather": "sunny"}
        )

        assert result["success"] is True
        assert "outfit_suggestions" in result["coach_result"]

    @pytest.mark.asyncio
    async def test_execute_realtime_help(self, coach_skill):
        """测试执行实时指导（原 DateAssistantSkill 功能）"""
        result = await coach_skill.execute(
            user_id="user_123",
            service_type="realtime_help",
            date_context={"date_type": "first_date"}
        )

        assert result["success"] is True
        assert "realtime_tips" in result["coach_result"]


# 注：TestDateAssistantSkillDeprecated 已删除，date_assistant_skill 模块已废弃
# DateCoachSkill 包含 realtime_help 功能的测试在 TestDateCoachSkill 中


class TestAPIArchitectureIntegration:
    """测试 API → Skill 架构集成"""

    @pytest.mark.skip(reason="API files renamed from p11/p12/p13 to semantic names")
    def test_p11_apis_import_skills(self):
        """测试 P11 APIs 导入 Skills - 已重命名为 emotion_analysis_apis"""
        import api.p11_apis as p11_module
        import inspect
        source = inspect.getsource(p11_module)

        assert "from agent.skills.emotion_analysis_skill import" in source
        assert "from agent.skills.safety_guardian_skill import" in source

    @pytest.mark.skip(reason="API files renamed from p11/p12/p13 to semantic names")
    def test_p12_apis_import_skills(self):
        """测试 P12 APIs 导入 Skills - 已重命名为 behavior_lab_apis"""
        import api.p12_apis as p12_module
        import inspect
        source = inspect.getsource(p12_module)

        assert "from agent.skills.emotion_mediator_skill import" in source
        assert "from agent.skills.love_language_translator_skill import" in source
        assert "from agent.skills.silence_breaker_skill import" in source

    @pytest.mark.skip(reason="API files renamed from p11/p12/p13 to semantic names")
    def test_p13_apis_import_skills(self):
        """测试 P13 APIs 导入 Skills - 已重命名"""
        import api.p13_apis as p13_module
        import inspect
        source = inspect.getsource(p13_module)

        assert "from agent.skills.love_language_translator_skill import" in source
        assert "from agent.skills.emotion_mediator_skill import" in source


# ========== 运行测试 ==========

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
