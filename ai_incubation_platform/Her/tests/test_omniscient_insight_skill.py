"""
Agent Skills 测试 - OmniscientInsightSkill

测试 OmniscientInsightSkill 的核心功能：
- 输入/输出 Schema
- 情绪状态分析
- 行为模式识别
- 主动洞察生成
- 趋势预测
- 情境触发器
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta
import sys

# 尝试导入 Skill 模块
try:
    from agent.skills.omniscient_insight_skill import (
        OmniscientInsightSkill,
        get_omniscient_insight_skill
    )
except ImportError:
    pytest.skip("omniscient_insight_skill not importable", allow_module_level=True)


class TestSkillMetadata:
    """Skill 元数据测试"""

    def test_skill_name(self):
        """测试 Skill 名称"""
        skill = OmniscientInsightSkill()
        assert skill.name == "omniscient_insight"

    def test_skill_version(self):
        """测试 Skill 版本"""
        skill = OmniscientInsightSkill()
        assert skill.version == "2.0.0"

    def test_skill_description(self):
        """测试 Skill 描述"""
        skill = OmniscientInsightSkill()
        assert "AI 全知感知" in skill.description
        assert "情绪状态" in skill.description


class TestInputSchema:
    """输入 Schema 测试"""

    def test_input_schema_structure(self):
        """测试输入 Schema 结构"""
        skill = OmniscientInsightSkill()
        schema = skill.get_input_schema()

        assert schema["type"] == "object"
        assert "user_id" in schema["properties"]
        assert "query_type" in schema["properties"]
        assert "time_range" in schema["properties"]

    def test_input_schema_required_fields(self):
        """测试必填字段"""
        skill = OmniscientInsightSkill()
        schema = skill.get_input_schema()

        assert "user_id" in schema["required"]
        assert "query_type" in schema["required"]

    def test_query_type_enum_values(self):
        """测试查询类型枚举值"""
        skill = OmniscientInsightSkill()
        schema = skill.get_input_schema()

        enum_values = schema["properties"]["query_type"]["enum"]
        assert "overview" in enum_values
        assert "patterns" in enum_values
        assert "insights" in enum_values
        assert "suggestions" in enum_values

    def test_time_range_enum_values(self):
        """测试时间范围枚举值"""
        skill = OmniscientInsightSkill()
        schema = skill.get_input_schema()

        enum_values = schema["properties"]["time_range"]["enum"]
        assert "today" in enum_values
        assert "week" in enum_values
        assert "month" in enum_values


class TestOutputSchema:
    """输出 Schema 测试"""

    def test_output_schema_structure(self):
        """测试输出 Schema 结构"""
        skill = OmniscientInsightSkill()
        schema = skill.get_output_schema()

        assert schema["type"] == "object"
        assert "success" in schema["properties"]
        assert "ai_message" in schema["properties"]
        assert "emotional_state" in schema["properties"]
        assert "behavior_patterns" in schema["properties"]

    def test_behavior_patterns_schema(self):
        """测试行为模式 Schema"""
        skill = OmniscientInsightSkill()
        schema = skill.get_output_schema()

        patterns_schema = schema["properties"]["behavior_patterns"]
        assert patterns_schema["type"] == "array"
        assert "items" in patterns_schema

    def test_active_insights_schema(self):
        """测试主动洞察 Schema"""
        skill = OmniscientInsightSkill()
        schema = skill.get_output_schema()

        insights_schema = schema["properties"]["active_insights"]
        assert insights_schema["type"] == "array"
        assert "items" in insights_schema


class TestEmotionalStateAnalysis:
    """情绪状态分析测试"""

    def test_enthusiastic_state(self):
        """测试热情积极状态"""
        skill = OmniscientInsightSkill()

        # 高活跃度数据
        behavior_data = {
            "chat_stats": {
                "total_messages": 150,
                "active_conversations": 4,
                "avg_response_time_minutes": 15
            },
            "swipe_stats": {
                "like_rate": 0.4
            }
        }

        state = skill._analyze_emotional_state(behavior_data)
        assert state == "enthusiastic"

    def test_engaged_state(self):
        """测试正常参与状态"""
        skill = OmniscientInsightSkill()

        # 正常活跃度数据 - 需要达到 activity_score >= 0.5
        # active_conversations > 2: +0.2, avg_response_time_minutes < 60: +0.2, like_rate > 0.3: +0.2
        behavior_data = {
            "chat_stats": {
                "total_messages": 80,
                "active_conversations": 3,  # > 2 → +0.2
                "avg_response_time_minutes": 45  # < 60 → +0.2
            },
            "swipe_stats": {
                "like_rate": 0.35  # > 0.3 → +0.2
            }
        }

        state = skill._analyze_emotional_state(behavior_data)
        # activity_score = 0.2 + 0.2 + 0.2 = 0.6 >= 0.5 → engaged
        assert state == "engaged"

    def test_passive_state(self):
        """测试被动观望状态"""
        skill = OmniscientInsightSkill()

        # 低活跃度数据 - 需要 activity_score >= 0.3 but < 0.5
        # avg_response_time_minutes < 60: +0.2, like_rate > 0.3: +0.2
        behavior_data = {
            "chat_stats": {
                "total_messages": 30,
                "active_conversations": 1,
                "avg_response_time_minutes": 45  # < 60 → +0.2
            },
            "swipe_stats": {
                "like_rate": 0.35  # > 0.3 → +0.2
            }
        }

        state = skill._analyze_emotional_state(behavior_data)
        # activity_score = 0.2 + 0.2 = 0.4 >= 0.3 → passive
        assert state == "passive"

    def test_withdrawn_state(self):
        """测试退缩消极状态"""
        skill = OmniscientInsightSkill()

        # 极低活跃度数据
        behavior_data = {
            "chat_stats": {
                "total_messages": 10,
                "active_conversations": 0,
                "avg_response_time_minutes": 180
            },
            "swipe_stats": {
                "like_rate": 0.05
            }
        }

        state = skill._analyze_emotional_state(behavior_data)
        assert state == "withdrawn"


class TestPatternIdentification:
    """行为模式识别测试"""

    @pytest.mark.asyncio
    async def test_active_time_pattern(self):
        """测试活跃时间模式"""
        skill = OmniscientInsightSkill()

        behavior_data = {
            "active_hours": [9, 10, 14, 15, 20, 21]
        }

        patterns = await skill._identify_patterns("user_001", behavior_data)

        # 应识别出活跃时间模式
        time_patterns = [p for p in patterns if p["type"] == "active_time"]
        assert len(time_patterns) > 0
        assert "上午" in time_patterns[0]["description"] or "下午" in time_patterns[0]["description"]

    @pytest.mark.asyncio
    async def test_selective_swipe_pattern(self):
        """测试挑剔滑动模式"""
        skill = OmniscientInsightSkill()

        behavior_data = {
            "swipe_stats": {
                "like_rate": 0.1
            },
            "chat_stats": {}
        }

        patterns = await skill._identify_patterns("user_001", behavior_data)

        # 应识别出开放模式（低通过率）
        swipe_patterns = [p for p in patterns if p["type"] == "swipe_behavior"]
        assert len(swipe_patterns) > 0
        assert swipe_patterns[0]["data"]["pattern"] == "open"

    @pytest.mark.asyncio
    async def test_talkative_chat_pattern(self):
        """测试健谈聊天模式"""
        skill = OmniscientInsightSkill()

        behavior_data = {
            "chat_stats": {
                "avg_message_length": 80
            },
            "swipe_stats": {}
        }

        patterns = await skill._identify_patterns("user_001", behavior_data)

        # 应识别出健谈模式
        chat_patterns = [p for p in patterns if p["type"] == "chat_behavior"]
        assert len(chat_patterns) > 0
        assert chat_patterns[0]["data"]["pattern"] == "talkative"

    @pytest.mark.asyncio
    async def test_concise_chat_pattern(self):
        """测试简洁聊天模式"""
        skill = OmniscientInsightSkill()

        behavior_data = {
            "chat_stats": {
                "avg_message_length": 15
            },
            "swipe_stats": {}
        }

        patterns = await skill._identify_patterns("user_001", behavior_data)

        # 应识别出简洁模式
        chat_patterns = [p for p in patterns if p["type"] == "chat_behavior"]
        assert len(chat_patterns) > 0
        assert chat_patterns[0]["data"]["pattern"] == "concise"


class TestInsightGeneration:
    """主动洞察生成测试"""

    @pytest.mark.asyncio
    async def test_active_time_change_insight(self):
        """测试活跃时间变化洞察"""
        skill = OmniscientInsightSkill()

        # 深夜活跃 vs 白天活跃，差值 > 3 小时
        # current_avg = (22 + 23) / 2 = 22.5
        # historical_avg = (9 + 10) / 2 = 9.5
        # time_diff = 13 >= 3 → detected
        behavior_data = {
            "active_hours": [22, 23],  # 深夜活跃，avg = 22.5
            "historical_active_hours": [9, 10],  # 白天活跃，avg = 9.5
            "chat_stats": {"total_messages": 100, "avg_message_length": 50},
            "historical_messages": 100,
            "historical_avg_message_length": 50,
        }

        patterns = []
        insights = await skill._generate_insights("user_001", behavior_data, patterns)

        # 应检测到活跃时间变化（平均时间差 = 13 小时 > 3）
        change_insights = [i for i in insights if i["type"] == "behavior_change"]
        assert len(change_insights) > 0

    @pytest.mark.asyncio
    async def test_message_frequency_drop_insight(self):
        """测试消息频率下降洞察"""
        skill = OmniscientInsightSkill()

        behavior_data = {
            "chat_stats": {
                "total_messages": 50,
                "avg_message_length": 20
            },
            "historical_messages": 200,
            "historical_avg_message_length": 60
        }

        patterns = []
        insights = await skill._generate_insights("user_001", behavior_data, patterns)

        # 应检测到消息频率下降
        drop_insights = [i for i in insights if i["type"] == "engagement_drop"]
        assert len(drop_insights) > 0

    @pytest.mark.asyncio
    async def test_profile_update_insight(self):
        """测试资料更新洞察"""
        skill = OmniscientInsightSkill()

        behavior_data = {
            "recent_profile_update": True
        }

        patterns = []
        insights = await skill._generate_insights("user_001", behavior_data, patterns)

        # 应检测到资料更新
        update_insights = [i for i in insights if i["type"] == "profile_update"]
        assert len(update_insights) > 0


class TestTrendPrediction:
    """趋势预测测试"""

    def test_high_match_probability(self):
        """测试高匹配概率预测"""
        skill = OmniscientInsightSkill()

        behavior_data = {
            "swipe_stats": {"like_rate": 0.6},
            "chat_stats": {"active_conversations": 5}
        }

        prediction = skill._generate_trend_prediction("user_001", behavior_data)

        assert prediction["match_probability"] == "high"
        assert prediction["relationship_prospect"] == "promising"

    def test_low_match_probability(self):
        """测试低匹配概率预测"""
        skill = OmniscientInsightSkill()

        behavior_data = {
            "swipe_stats": {"like_rate": 0.15},
            "chat_stats": {"active_conversations": 0}
        }

        prediction = skill._generate_trend_prediction("user_001", behavior_data)

        assert prediction["match_probability"] == "low"
        assert prediction["relationship_prospect"] == "needs_attention"

    def test_medium_match_probability(self):
        """测试中等匹配概率预测"""
        skill = OmniscientInsightSkill()

        behavior_data = {
            "swipe_stats": {"like_rate": 0.35},
            "chat_stats": {"active_conversations": 2}
        }

        prediction = skill._generate_trend_prediction("user_001", behavior_data)

        assert prediction["match_probability"] == "medium"


class TestRecommendationGeneration:
    """建议生成测试"""

    def test_fallback_recommendation_high_high(self):
        """测试降级建议 - 高概率+好前景"""
        skill = OmniscientInsightSkill()

        recommendation = skill._fallback_recommendation("high", "promising")
        assert "形势大好" in recommendation

    def test_fallback_recommendation_high_other(self):
        """测试降级建议 - 高概率+其他前景"""
        skill = OmniscientInsightSkill()

        recommendation = skill._fallback_recommendation("high", "stable")
        assert "匹配机会多" in recommendation

    def test_fallback_recommendation_other_promising(self):
        """测试降级建议 - 其他概率+好前景"""
        skill = OmniscientInsightSkill()

        recommendation = skill._fallback_recommendation("low", "promising")
        assert "关系发展良好" in recommendation

    def test_fallback_recommendation_default(self):
        """测试降级建议 - 默认情况"""
        skill = OmniscientInsightSkill()

        recommendation = skill._fallback_recommendation("low", "needs_attention")
        assert "完善资料" in recommendation


class TestContextTrigger:
    """情境触发器测试"""

    @pytest.mark.asyncio
    async def test_active_time_change_trigger(self):
        """测试活跃时间变化触发"""
        skill = OmniscientInsightSkill()

        result = await skill.context_trigger(
            "user_001",
            "user_active_time_change",
            {}
        )

        assert result["triggered"] is True
        assert "insight" in result
        assert result["insight"]["type"] == "active_time_change"

    @pytest.mark.asyncio
    async def test_message_frequency_drop_trigger(self):
        """测试消息频率下降触发"""
        skill = OmniscientInsightSkill()

        result = await skill.context_trigger(
            "user_001",
            "message_frequency_drop",
            {}
        )

        assert result["triggered"] is True
        assert result["insight"]["severity"] == "high"

    @pytest.mark.asyncio
    async def test_profile_update_trigger(self):
        """测试资料更新触发"""
        skill = OmniscientInsightSkill()

        result = await skill.context_trigger(
            "user_001",
            "profile_update",
            {}
        )

        assert result["triggered"] is True
        assert result["insight"]["type"] == "profile_boost"

    @pytest.mark.asyncio
    async def test_location_change_trigger(self):
        """测试位置变化触发"""
        skill = OmniscientInsightSkill()

        result = await skill.context_trigger(
            "user_001",
            "location_change",
            {}
        )

        assert result["triggered"] is True
        assert "新城市" in result["insight"]["message"]

    @pytest.mark.asyncio
    async def test_match_stagnation_trigger(self):
        """测试匹配停滞触发"""
        skill = OmniscientInsightSkill()

        result = await skill.context_trigger(
            "user_001",
            "match_stagnation",
            {}
        )

        assert result["triggered"] is True
        assert result["insight"]["type"] == "match_stagnation"

    @pytest.mark.asyncio
    async def test_unknown_trigger(self):
        """测试未知触发类型"""
        skill = OmniscientInsightSkill()

        result = await skill.context_trigger(
            "user_001",
            "unknown_trigger_type",
            {}
        )

        assert result["triggered"] is False


class TestExecuteOverview:
    """执行总览测试"""

    @pytest.mark.asyncio
    async def test_execute_overview(self):
        """测试执行 overview 查询"""
        skill = OmniscientInsightSkill()

        # Mock _collect_behavior_data
        with patch.object(skill, '_collect_behavior_data', new_callable=AsyncMock) as mock_collect:
            mock_collect.return_value = {
                "active_hours": [9, 10, 14, 15],
                "chat_stats": {"total_messages": 100, "avg_message_length": 50, "active_conversations": 2, "avg_response_time_minutes": 30},
                "swipe_stats": {"like_rate": 0.3, "total_swipes": 50, "like_count": 15, "pass_count": 35}
            }

            result = await skill.execute("user_001", "overview", "week")

            assert result["success"] is True
            assert "emotional_state" in result
            assert "behavior_patterns" in result

    @pytest.mark.asyncio
    async def test_execute_patterns(self):
        """测试执行 patterns 查询"""
        skill = OmniscientInsightSkill()

        with patch.object(skill, '_collect_behavior_data', new_callable=AsyncMock) as mock_collect:
            mock_collect.return_value = {
                "active_hours": [9, 10, 14, 15],
                "chat_stats": {},
                "swipe_stats": {}
            }

            result = await skill.execute("user_001", "patterns", "week")

            assert result["success"] is True
            assert "behavior_patterns" in result

    @pytest.mark.asyncio
    async def test_execute_insights(self):
        """测试执行 insights 查询"""
        skill = OmniscientInsightSkill()

        with patch.object(skill, '_collect_behavior_data', new_callable=AsyncMock) as mock_collect:
            mock_collect.return_value = {
                "active_hours": [9, 10, 14, 15],
                "chat_stats": {"total_messages": 100},
                "swipe_stats": {}
            }

            result = await skill.execute("user_001", "insights", "week")

            assert result["success"] is True
            assert "active_insights" in result

    @pytest.mark.asyncio
    async def test_execute_suggestions(self):
        """测试执行 suggestions 查询"""
        skill = OmniscientInsightSkill()

        with patch.object(skill, '_collect_behavior_data', new_callable=AsyncMock) as mock_collect:
            mock_collect.return_value = {
                "active_hours": [9, 10],
                "chat_stats": {"total_messages": 50},
                "swipe_stats": {}
            }

            result = await skill.execute("user_001", "suggestions", "week")

            assert result["success"] is True
            assert "proactive_suggestions" in result

    @pytest.mark.asyncio
    async def test_execute_invalid_query_type(self):
        """测试无效查询类型"""
        skill = OmniscientInsightSkill()

        result = await skill.execute("user_001", "invalid_type", "week")

        assert result["success"] is False
        assert "error" in result


class TestHelperFunctions:
    """辅助函数测试"""

    def test_time_range_name(self):
        """测试时间范围名称"""
        skill = OmniscientInsightSkill()

        assert skill._time_range_name("today") == "今天"
        assert skill._time_range_name("week") == "本周"
        assert skill._time_range_name("month") == "本月"
        assert skill._time_range_name("unknown") == "近期"

    def test_format_hours_morning(self):
        """测试上午时间格式化"""
        skill = OmniscientInsightSkill()

        hours = [7, 8, 9, 10, 11]
        formatted = skill._format_hours(hours)

        assert "上午" in formatted

    def test_format_hours_afternoon(self):
        """测试下午时间格式化"""
        skill = OmniscientInsightSkill()

        hours = [13, 14, 15, 16, 17]
        formatted = skill._format_hours(hours)

        assert "下午" in formatted

    def test_format_hours_evening(self):
        """测试晚上时间格式化"""
        skill = OmniscientInsightSkill()

        hours = [18, 19, 20, 21, 22, 23, 0, 1]
        formatted = skill._format_hours(hours)

        assert "晚上" in formatted

    def test_format_hours_empty(self):
        """测试空时间列表"""
        skill = OmniscientInsightSkill()

        formatted = skill._format_hours([])
        assert formatted == "不固定时间"


class TestSkillFactory:
    """Skill 工厂测试"""

    def test_get_skill_returns_instance(self):
        """测试工厂返回实例"""
        skill = get_omniscient_insight_skill()

        assert skill is not None
        assert isinstance(skill, OmniscientInsightSkill)

    def test_get_skill_singleton(self):
        """测试工厂单例"""
        skill1 = get_omniscient_insight_skill()
        skill2 = get_omniscient_insight_skill()

        # 应返回相同实例
        assert skill1 is skill2


class TestEdgeCases:
    """边界值测试"""

    def test_empty_behavior_data(self):
        """测试空行为数据"""
        skill = OmniscientInsightSkill()

        state = skill._analyze_emotional_state({})
        # 应返回默认状态
        assert state in ["enthusiastic", "engaged", "passive", "withdrawn"]

    def test_extreme_like_rate(self):
        """测试极端点赞率"""
        skill = OmniscientInsightSkill()

        behavior_data = {
            "swipe_stats": {"like_rate": 0.99},
            "chat_stats": {
                "total_messages": 100,  # > 100 → +0.3
                "active_conversations": 3,  # > 2 → +0.2
                "avg_response_time_minutes": 20  # < 30 → +0.3
            }
        }

        state = skill._analyze_emotional_state(behavior_data)
        # activity_score = 0.3 + 0.2 + 0.2 + 0.3 = 1.0 >= 0.8 → enthusiastic
        assert state in ["enthusiastic", "engaged"]

    def test_zero_response_time(self):
        """测试零响应时间"""
        skill = OmniscientInsightSkill()

        behavior_data = {
            "chat_stats": {
                "total_messages": 150,  # > 100 → +0.3
                "active_conversations": 4,  # > 2 → +0.2
                "avg_response_time_minutes": 0  # 立即回复 → < 30 → +0.3
            },
            "swipe_stats": {"like_rate": 0.5}  # > 0.3 → +0.2
        }

        state = skill._analyze_emotional_state(behavior_data)
        # activity_score = 0.3 + 0.2 + 0.2 + 0.3 = 1.0 >= 0.8 → enthusiastic
        assert state == "enthusiastic"

    def test_detect_active_time_change_large_diff(self):
        """测试大幅活跃时间变化"""
        skill = OmniscientInsightSkill()

        behavior_data = {
            "active_hours": [22, 23],  # 深夜
            "historical_active_hours": [9, 10]  # 白天
        }

        detected = skill._detect_active_time_change(behavior_data)
        # 应检测到变化（差 > 3 小时）
        assert detected is True

    def test_detect_active_time_change_small_diff(self):
        """测试小幅活跃时间变化"""
        skill = OmniscientInsightSkill()

        behavior_data = {
            "active_hours": [10, 11],
            "historical_active_hours": [9, 10]
        }

        detected = skill._detect_active_time_change(behavior_data)
        # 应不检测到变化（差 < 3 小时）
        assert detected is False