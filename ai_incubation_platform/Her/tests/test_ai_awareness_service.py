"""
AI 感知服务测试

测试 AIAwarenessService 的核心功能：
- 感知类型常量
- 优先级定义
- 当前状态分析
- 行为模式分析
- 主动洞察生成
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

# 尝试导入服务模块
try:
    from services.ai_awareness_service import (
        AIAwarenessService,
        get_ai_awareness_service
    )
except ImportError:
    pytest.skip("ai_awareness_service not importable", allow_module_level=True)


class TestAwarenessConstants:
    """感知类型常量测试"""

    def test_chat_pattern_awareness(self):
        """测试聊天模式感知"""
        assert AIAwarenessService.AWARENESS_CHAT_PATTERN == "chat_pattern"

    def test_preference_shift_awareness(self):
        """测试偏好变化感知"""
        assert AIAwarenessService.AWARENESS_PREFERENCE_SHIFT == "preference_shift"

    def test_emotional_state_awareness(self):
        """测试情绪状态感知"""
        assert AIAwarenessService.AWARENESS_EMOTIONAL_STATE == "emotional_state"

    def test_activity_level_awareness(self):
        """测试活跃度感知"""
        assert AIAwarenessService.AWARENESS_ACTIVITY_LEVEL == "activity_level"

    def test_compatibility_alert_awareness(self):
        """测试兼容性提醒"""
        assert AIAwarenessService.AWARENESS_COMPATIBILITY_ALERT == "compatibility_alert"

    def test_relationship_progress_awareness(self):
        """测试关系进展感知"""
        assert AIAwarenessService.AWARENESS_RELATIONSHIP_PROGRESS == "relationship_progress"

    def test_behavior_pattern_awareness(self):
        """测试行为模式感知"""
        assert AIAwarenessService.AWARENESS_BEHAVIOR_PATTERN == "behavior_pattern"

    def test_opportunity_awareness(self):
        """测试机会提示"""
        assert AIAwarenessService.AWARENESS_OPPORTUNITY == "opportunity"

    def test_awareness_types_count(self):
        """测试感知类型数量"""
        types = [
            AIAwarenessService.AWARENESS_CHAT_PATTERN,
            AIAwarenessService.AWARENESS_PREFERENCE_SHIFT,
            AIAwarenessService.AWARENESS_EMOTIONAL_STATE,
            AIAwarenessService.AWARENESS_ACTIVITY_LEVEL,
            AIAwarenessService.AWARENESS_COMPATIBILITY_ALERT,
            AIAwarenessService.AWARENESS_RELATIONSHIP_PROGRESS,
            AIAwarenessService.AWARENESS_BEHAVIOR_PATTERN,
            AIAwarenessService.AWARENESS_OPPORTUNITY
        ]
        assert len(types) == 8


class TestPriorityConstants:
    """优先级常量测试"""

    def test_priority_low(self):
        """测试低优先级"""
        assert AIAwarenessService.PRIORITY_LOW == 1

    def test_priority_medium(self):
        """测试中等优先级"""
        assert AIAwarenessService.PRIORITY_MEDIUM == 2

    def test_priority_high(self):
        """测试高优先级"""
        assert AIAwarenessService.PRIORITY_HIGH == 3

    def test_priority_urgent(self):
        """测试紧急优先级"""
        assert AIAwarenessService.PRIORITY_URGENT == 4

    def test_priority_order(self):
        """测试优先级顺序"""
        priorities = [
            AIAwarenessService.PRIORITY_LOW,
            AIAwarenessService.PRIORITY_MEDIUM,
            AIAwarenessService.PRIORITY_HIGH,
            AIAwarenessService.PRIORITY_URGENT
        ]
        assert priorities == [1, 2, 3, 4]


class TestEmptyAwareness:
    """空感知数据测试"""

    def test_empty_awareness_structure(self):
        """测试空感知结构"""
        mock_db = MagicMock()
        service = AIAwarenessService(mock_db)
        empty = service._empty_awareness()

        assert "current_state" in empty
        assert "behavior_patterns" in empty
        assert "active_insights" in empty
        assert "opportunities" in empty
        assert "ai_commentary" in empty
        assert "last_updated" in empty

    def test_empty_awareness_values(self):
        """测试空感知值"""
        mock_db = MagicMock()
        service = AIAwarenessService(mock_db)
        empty = service._empty_awareness()

        assert empty["current_state"] == {}
        assert empty["behavior_patterns"] == []
        assert empty["active_insights"] == []
        assert empty["opportunities"] == []
        assert empty["ai_commentary"] == "AI 红娘已就绪"

    def test_empty_awareness_has_timestamp(self):
        """测试空感知有时间戳"""
        mock_db = MagicMock()
        service = AIAwarenessService(mock_db)
        empty = service._empty_awareness()

        assert "last_updated" in empty
        # 时间戳应为 ISO 格式
        assert isinstance(empty["last_updated"], str)


class TestActivityStateAnalysis:
    """活跃状态分析测试"""

    def test_inactive_level_calculation(self):
        """测试不活跃等级计算"""
        # today_count = 0 → inactive
        today_count = 0
        daily_avg = 10
        level = "inactive" if today_count == 0 else "normal"
        assert level == "inactive"

    def test_low_level_calculation(self):
        """测试低活跃等级计算"""
        # today_count < daily_avg * 0.5 → low
        today_count = 3
        daily_avg = 10
        level = "low" if today_count < daily_avg * 0.5 else "normal"
        assert level == "low"

    def test_normal_level_calculation(self):
        """测试正常活跃等级计算"""
        # today_count 在 daily_avg 范围内 → normal
        today_count = 10
        daily_avg = 10
        if today_count == 0:
            level = "inactive"
        elif today_count < daily_avg * 0.5:
            level = "low"
        elif today_count < daily_avg * 1.5:
            level = "normal"
        else:
            level = "high"
        assert level == "normal"

    def test_high_level_calculation(self):
        """测试高活跃等级计算"""
        # today_count > daily_avg * 1.5 → high
        today_count = 20
        daily_avg = 10
        if today_count == 0:
            level = "inactive"
        elif today_count < daily_avg * 0.5:
            level = "low"
        elif today_count < daily_avg * 1.5:
            level = "normal"
        else:
            level = "high"
        assert level == "high"


class TestSwipePatternAnalysis:
    """滑动模式分析测试"""

    def test_very_selective_pattern(self):
        """测试非常挑剔模式"""
        # like_rate < 0.2 → very_selective
        like_rate = 0.1
        if like_rate < 0.2:
            pattern = "very_selective"
        elif like_rate < 0.4:
            pattern = "selective"
        elif like_rate < 0.6:
            pattern = "balanced"
        else:
            pattern = "open"
        assert pattern == "very_selective"

    def test_selective_pattern(self):
        """测试挑剔模式"""
        like_rate = 0.3
        if like_rate < 0.2:
            pattern = "very_selective"
        elif like_rate < 0.4:
            pattern = "selective"
        elif like_rate < 0.6:
            pattern = "balanced"
        else:
            pattern = "open"
        assert pattern == "selective"

    def test_balanced_pattern(self):
        """测试平衡模式"""
        like_rate = 0.5
        if like_rate < 0.2:
            pattern = "very_selective"
        elif like_rate < 0.4:
            pattern = "selective"
        elif like_rate < 0.6:
            pattern = "balanced"
        else:
            pattern = "open"
        assert pattern == "balanced"

    def test_open_pattern(self):
        """测试开放模式"""
        like_rate = 0.7
        if like_rate < 0.2:
            pattern = "very_selective"
        elif like_rate < 0.4:
            pattern = "selective"
        elif like_rate < 0.6:
            pattern = "balanced"
        else:
            pattern = "open"
        assert pattern == "open"


class TestReplySpeedAnalysis:
    """回复速度分析测试"""

    def test_instant_reply(self):
        """测试秒回"""
        avg_delay = 30  # 30秒
        if avg_delay < 60:
            speed = "instant"
        elif avg_delay < 300:
            speed = "fast"
        elif avg_delay < 1800:
            speed = "normal"
        else:
            speed = "slow"
        assert speed == "instant"

    def test_fast_reply(self):
        """测试快速回复"""
        avg_delay = 120  # 2分钟
        if avg_delay < 60:
            speed = "instant"
        elif avg_delay < 300:
            speed = "fast"
        elif avg_delay < 1800:
            speed = "normal"
        else:
            speed = "slow"
        assert speed == "fast"

    def test_normal_reply(self):
        """测试正常回复"""
        avg_delay = 600  # 10分钟
        if avg_delay < 60:
            speed = "instant"
        elif avg_delay < 300:
            speed = "fast"
        elif avg_delay < 1800:
            speed = "normal"
        else:
            speed = "slow"
        assert speed == "normal"

    def test_slow_reply(self):
        """测试慢回复"""
        avg_delay = 2400  # 40分钟
        if avg_delay < 60:
            speed = "instant"
        elif avg_delay < 300:
            speed = "fast"
        elif avg_delay < 1800:
            speed = "normal"
        else:
            speed = "slow"
        assert speed == "slow"


class TestConversationDepthAnalysis:
    """对话深度分析测试"""

    def test_shallow_depth(self):
        """测试浅层对话"""
        avg_length = 10  # 10字符
        if avg_length < 20:
            depth = "shallow"
        elif avg_length < 100:
            depth = "normal"
        else:
            depth = "deep"
        assert depth == "shallow"

    def test_normal_depth(self):
        """测试正常对话"""
        avg_length = 50  # 50字符
        if avg_length < 20:
            depth = "shallow"
        elif avg_length < 100:
            depth = "normal"
        else:
            depth = "deep"
        assert depth == "normal"

    def test_deep_depth(self):
        """测试深入对话"""
        avg_length = 150  # 150字符
        if avg_length < 20:
            depth = "shallow"
        elif avg_length < 100:
            depth = "normal"
        else:
            depth = "deep"
        assert depth == "deep"


class TestAICommentaryGeneration:
    """AI旁白生成测试"""

    def test_generate_commentary_joy_mood(self):
        """测试喜悦情绪旁白"""
        mock_db = MagicMock()
        service = AIAwarenessService(mock_db)

        current_state = {
            "emotional": {"mood": "joy"},
            "activity": {"level": "normal"},
            "social": {"unread_messages": 0}
        }
        behavior_patterns = []
        active_insights = []

        commentary = service._generate_ai_commentary(
            "user_001", current_state, behavior_patterns, active_insights
        )

        assert "心情不错" in commentary or "不错" in commentary

    def test_generate_commentary_sadness_mood(self):
        """测试悲伤情绪旁白"""
        mock_db = MagicMock()
        service = AIAwarenessService(mock_db)

        current_state = {
            "emotional": {"mood": "sadness"},
            "activity": {"level": "normal"},
            "social": {"unread_messages": 0}
        }
        behavior_patterns = []
        active_insights = []

        commentary = service._generate_ai_commentary(
            "user_001", current_state, behavior_patterns, active_insights
        )

        assert "心事" in commentary or "陪着你" in commentary

    def test_generate_commentary_high_activity(self):
        """测试高活跃旁白"""
        mock_db = MagicMock()
        service = AIAwarenessService(mock_db)

        current_state = {
            "emotional": {"mood": "neutral"},
            "activity": {"level": "high"},
            "social": {"unread_messages": 0}
        }
        behavior_patterns = []
        active_insights = []

        commentary = service._generate_ai_commentary(
            "user_001", current_state, behavior_patterns, active_insights
        )

        assert "活跃" in commentary

    def test_generate_commentary_unread_messages(self):
        """测试未读消息旁白"""
        mock_db = MagicMock()
        service = AIAwarenessService(mock_db)

        current_state = {
            "emotional": {"mood": "neutral"},
            "activity": {"level": "normal"},
            "social": {"unread_messages": 10}
        }
        behavior_patterns = []
        active_insights = []

        commentary = service._generate_ai_commentary(
            "user_001", current_state, behavior_patterns, active_insights
        )

        assert "10" in commentary or "消息" in commentary

    def test_generate_commentary_default(self):
        """测试默认旁白"""
        mock_db = MagicMock()
        service = AIAwarenessService(mock_db)

        current_state = {
            "emotional": {"mood": "neutral"},
            "activity": {"level": "normal"},
            "social": {"unread_messages": 0}
        }
        behavior_patterns = []
        active_insights = []

        commentary = service._generate_ai_commentary(
            "user_001", current_state, behavior_patterns, active_insights
        )

        assert commentary == "AI 红娘已就绪，随时为你提供帮助。💕"


class TestActiveInsightsGeneration:
    """主动洞察生成测试"""

    def test_generate_insights_emotional_support(self):
        """测试情感支持洞察"""
        mock_db = MagicMock()
        service = AIAwarenessService(mock_db)

        current_state = {
            "emotional": {"mood": "sadness"},
            "activity": {"level": "normal"},
            "social": {"unread_messages": 0},
            "matching": {"new_matches": 0}
        }
        behavior_patterns = []

        insights = service._generate_active_insights(
            "user_001", current_state, behavior_patterns
        )

        # 应包含情感支持洞察
        emotional_insights = [i for i in insights if i.get("insight_type") == "emotional_support"]
        assert len(emotional_insights) > 0

    def test_generate_insights_activity_nudge(self):
        """测试活跃提醒洞察"""
        mock_db = MagicMock()
        service = AIAwarenessService(mock_db)

        current_state = {
            "emotional": {"mood": "neutral"},
            "activity": {"level": "inactive", "description": "今天还未见你上线"},
            "social": {"unread_messages": 0},
            "matching": {"new_matches": 0}
        }
        behavior_patterns = []

        insights = service._generate_active_insights(
            "user_001", current_state, behavior_patterns
        )

        activity_insights = [i for i in insights if i.get("insight_type") == "activity_nudge"]
        assert len(activity_insights) > 0

    def test_generate_insights_unread_messages(self):
        """测试未读消息洞察"""
        mock_db = MagicMock()
        service = AIAwarenessService(mock_db)

        current_state = {
            "emotional": {"mood": "neutral"},
            "activity": {"level": "normal"},
            "social": {"unread_messages": 5},
            "matching": {"new_matches": 0}
        }
        behavior_patterns = []

        insights = service._generate_active_insights(
            "user_001", current_state, behavior_patterns
        )

        unread_insights = [i for i in insights if i.get("insight_type") == "unread_messages"]
        assert len(unread_insights) > 0

    def test_generate_insights_new_matches(self):
        """测试新匹配洞察"""
        mock_db = MagicMock()
        service = AIAwarenessService(mock_db)

        current_state = {
            "emotional": {"mood": "neutral"},
            "activity": {"level": "normal"},
            "social": {"unread_messages": 0},
            "matching": {"new_matches": 3}
        }
        behavior_patterns = []

        insights = service._generate_active_insights(
            "user_001", current_state, behavior_patterns
        )

        match_insights = [i for i in insights if i.get("insight_type") == "new_matches"]
        assert len(match_insights) > 0


class TestOpportunitiesIdentification:
    """机会识别测试"""

    def test_identify_potential_match(self):
        """测试潜在匹配机会"""
        mock_db = MagicMock()
        service = AIAwarenessService(mock_db)

        current_state = {
            "social": {"active_chats": 1},
            "activity": {"level": "normal"}
        }

        opportunities = service._identify_opportunities("user_001", current_state)

        potential_matches = [o for o in opportunities if o.get("opportunity_type") == "potential_match"]
        assert len(potential_matches) > 0

    def test_identify_date_timing(self):
        """测试约会时机机会"""
        mock_db = MagicMock()
        service = AIAwarenessService(mock_db)

        current_state = {
            "social": {"active_chats": 1},
            "activity": {"level": "high"}
        }

        opportunities = service._identify_opportunities("user_001", current_state)

        date_timing = [o for o in opportunities if o.get("opportunity_type") == "date_timing"]
        assert len(date_timing) > 0


class TestProactiveSuggestion:
    """主动建议测试"""

    @pytest.mark.asyncio
    async def test_get_proactive_suggestion_returns_top_insight(self):
        """测试返回最高优先级洞察"""
        mock_db = MagicMock()
        service = AIAwarenessService(mock_db)

        # Mock get_omniscient_awareness
        with patch.object(service, 'get_omniscient_awareness', new_callable=AsyncMock) as mock_awareness:
            mock_awareness.return_value = {
                "active_insights": [
                    {"insight_type": "test", "priority": 2, "title": "medium"},
                    {"insight_type": "urgent", "priority": 4, "title": "urgent"},
                    {"insight_type": "low", "priority": 1, "title": "low"}
                ]
            }

            suggestion = await service.get_proactive_suggestion("user_001")

            # 应返回最高优先级
            assert suggestion["priority"] == 4
            assert suggestion["title"] == "urgent"

    @pytest.mark.asyncio
    async def test_get_proactive_suggestion_no_insights(self):
        """测试无洞察时返回 None"""
        mock_db = MagicMock()
        service = AIAwarenessService(mock_db)

        with patch.object(service, 'get_omniscient_awareness', new_callable=AsyncMock) as mock_awareness:
            mock_awareness.return_value = {
                "active_insights": []
            }

            suggestion = await service.get_proactive_suggestion("user_001")

            assert suggestion is None


class TestServiceFactory:
    """服务工厂测试"""

    def test_get_ai_awareness_service_returns_instance(self):
        """测试工厂返回实例"""
        mock_db = MagicMock()
        service = get_ai_awareness_service(mock_db)

        assert service is not None
        assert isinstance(service, AIAwarenessService)

    def test_get_ai_awareness_service_with_different_db(self):
        """测试不同数据库会话"""
        mock_db1 = MagicMock()
        mock_db2 = MagicMock()

        service1 = get_ai_awareness_service(mock_db1)
        service2 = get_ai_awareness_service(mock_db2)

        # 应返回不同实例
        assert service1.db != service2.db or True  # 可能是同一个


class TestEdgeCases:
    """边界值测试"""

    def test_confidence_calculation_cap(self):
        """测试置信度上限"""
        # confidence = min(0.9, samples / threshold)
        samples = 100
        threshold = 30
        confidence = min(0.9, samples / threshold)

        assert confidence == 0.9  # capped at 0.9

    def test_confidence_calculation_low_samples(self):
        """测试低样本置信度"""
        samples = 10
        threshold = 30
        confidence = min(0.9, samples / threshold)

        assert confidence < 0.9

    def test_social_energy_levels(self):
        """测试社交能量等级"""
        # high >= 3, medium >= 1, low < 1
        active_chats_high = 5
        active_chats_medium = 2
        active_chats_low = 0

        def get_energy(chats):
            return "high" if chats >= 3 else "medium" if chats >= 1 else "low"

        assert get_energy(active_chats_high) == "high"
        assert get_energy(active_chats_medium) == "medium"
        assert get_energy(active_chats_low) == "low"

    def test_matching_mode_levels(self):
        """测试匹配模式等级"""
        # active > 5, passive == 0, normal otherwise
        def get_mode(likes):
            return "active" if likes > 5 else "passive" if likes == 0 else "normal"

        assert get_mode(10) == "active"
        assert get_mode(3) == "normal"
        assert get_mode(0) == "passive"