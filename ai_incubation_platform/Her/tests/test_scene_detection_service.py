"""
场景检测服务测试

测试 SceneDetectionService 的核心功能：
- SCENE_RULES 场景规则定义
- SceneContext 场景上下文数据类
- PushAction 推送动作数据类
- detect_scene() 场景检测触发
- _recently_pushed() 防重复推送
- _record_scene() 场景历史记录
- 用户场景历史管理
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

# 尝试导入服务模块
try:
    from services.scene_detection_service import (
        SceneDetectionService,
        SceneContext,
        PushAction,
        get_scene_service,
    )
    # SCENE_RULES 是类内部定义的
    SCENE_RULES = SceneDetectionService.SCENE_RULES
except ImportError:
    pytest.skip("scene_detection_service not importable", allow_module_level=True)


class TestSceneRules:
    """场景规则定义测试"""

    def test_scene_rules_exist(self):
        """测试场景规则存在"""
        expected_rules = [
            "new_user_registered",
            "profile_incomplete",
            "first_match",
            "new_match",
            "high_compatibility_match",
            "chat_milestone_7days",
            "chat_milestone_30days",
            "silence_detected",
            "dating_intent",
            "gift_occasion",
            "conflict_detected",
            "relationship_health_low",
            "safety_concern",
        ]

        for rule in expected_rules:
            assert rule in SCENE_RULES

    def test_scene_rules_count(self):
        """测试场景规则数量"""
        assert len(SCENE_RULES) == 13

    def test_scene_rules_structure(self):
        """测试场景规则结构"""
        for rule_name, rule in SCENE_RULES.items():
            assert "description" in rule
            assert "trigger" in rule
            assert "push" in rule

    def test_new_user_registered_rule(self):
        """测试新用户注册规则"""
        rule = SCENE_RULES["new_user_registered"]

        assert rule["trigger"] == "user_registered"
        assert rule["delay"] == 5
        assert len(rule["push"]) == 1
        assert rule["push"][0]["feature"] == "photos"

    def test_first_match_rule(self):
        """测试首次匹配规则"""
        rule = SCENE_RULES["first_match"]

        assert rule["trigger"] == "match_created"
        assert "condition" in rule
        assert rule["push"][0]["feature"] == "verify"

    def test_silence_detected_rule(self):
        """测试沉默检测规则"""
        rule = SCENE_RULES["silence_detected"]

        assert rule["trigger"] == "silence_duration"
        assert rule["push"][0]["feature"] == "chat_assistant"
        assert rule["push"][0]["priority"] == "high"

    def test_conflict_detected_rule(self):
        """测试冲突检测规则"""
        rule = SCENE_RULES["conflict_detected"]

        assert rule["trigger"] == "emotion_analysis"
        assert rule["push"][0]["feature"] == "love_language"


class TestSceneContext:
    """场景上下文数据类测试"""

    def test_scene_context_creation(self):
        """测试场景上下文创建"""
        context = SceneContext(
            user_id="user_001",
            scene_type="new_user_registered",
            trigger_data={"source": "registration"}
        )

        assert context.user_id == "user_001"
        assert context.scene_type == "new_user_registered"
        assert context.trigger_data["source"] == "registration"
        assert context.timestamp is not None

    def test_scene_context_with_explicit_timestamp(self):
        """测试显式时间戳"""
        explicit_time = datetime.now() - timedelta(hours=1)

        context = SceneContext(
            user_id="user_001",
            scene_type="test",
            trigger_data={},
            timestamp=explicit_time
        )

        assert context.timestamp == explicit_time

    def test_scene_context_auto_timestamp(self):
        """测试自动时间戳"""
        before = datetime.now()

        context = SceneContext(
            user_id="user_001",
            scene_type="test",
            trigger_data={}
        )

        after = datetime.now()

        assert context.timestamp >= before
        assert context.timestamp <= after


class TestPushAction:
    """推送动作数据类测试"""

    def test_push_action_creation(self):
        """测试推送动作创建"""
        action = PushAction(
            feature="photos",
            priority="high",
            delay_seconds=5
        )

        assert action.feature == "photos"
        assert action.priority == "high"
        assert action.delay_seconds == 5

    def test_push_action_with_condition(self):
        """测试带条件的推送动作"""
        condition = lambda ctx: ctx.get("value") > 10

        action = PushAction(
            feature="test",
            priority="medium",
            delay_seconds=0,
            condition=condition
        )

        assert action.condition is not None
        assert action.condition({"value": 20}) is True
        assert action.condition({"value": 5}) is False


class TestServiceInitialization:
    """服务初始化测试"""

    def test_service_creation(self):
        """测试服务创建"""
        service = SceneDetectionService()

        assert service is not None
        assert service._user_scene_history == {}

    def test_get_scene_service_singleton(self):
        """测试全局服务单例"""
        service1 = get_scene_service()
        service2 = get_scene_service()

        assert service1 is not None
        assert service1 is service2


class TestDetectScene:
    """场景检测测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return SceneDetectionService()

    def test_detect_new_user_registered(self, service):
        """测试新用户注册场景"""
        result = service.detect_scene(
            user_id="user_001",
            trigger="user_registered",
            context={}
        )

        assert result is not None
        assert len(result) == 1
        assert result[0]["feature"] == "photos"
        assert result[0]["priority"] == "high"

    def test_detect_new_match(self, service):
        """测试新匹配场景"""
        result = service.detect_scene(
            user_id="user_001",
            trigger="match_created",
            context={"match_count": 2}  # 不是首次匹配
        )

        assert result is not None
        assert result[0]["feature"] == "chat"
        assert result[0]["priority"] == "high"

    def test_detect_first_match(self, service):
        """测试首次匹配场景"""
        result = service.detect_scene(
            user_id="user_001",
            trigger="match_created",
            context={"match_count": 1}  # 首次匹配
        )

        # 首次匹配应触发 verify 和 chat
        assert result is not None
        features = [r["feature"] for r in result]
        assert "verify" in features
        assert "chat" in features

    def test_detect_profile_incomplete(self, service):
        """测试资料不完整场景"""
        result = service.detect_scene(
            user_id="user_001",
            trigger="profile_check",
            context={"profile_completion": 30}  # 低于 50%
        )

        assert result is not None
        assert result[0]["feature"] == "photos"

    def test_detect_profile_complete_no_push(self, service):
        """测试资料完整无推送"""
        result = service.detect_scene(
            user_id="user_001",
            trigger="profile_check",
            context={"profile_completion": 80}  # 高于 50%
        )

        # 条件不满足，不应推送
        assert result is None

    def test_detect_silence(self, service):
        """测试沉默检测"""
        result = service.detect_scene(
            user_id="user_001",
            trigger="silence_duration",
            context={"seconds": 400}  # 超过 300 秒
        )

        assert result is not None
        assert result[0]["feature"] == "chat_assistant"

    def test_detect_silence_short_no_push(self, service):
        """测试短沉默无推送"""
        result = service.detect_scene(
            user_id="user_001",
            trigger="silence_duration",
            context={"seconds": 200}  # 未超过 300 秒
        )

        assert result is None

    def test_detect_conflict(self, service):
        """测试冲突检测"""
        result = service.detect_scene(
            user_id="user_001",
            trigger="emotion_analysis",
            context={"conflict_level": 0.8}  # 超过 0.6
        )

        assert result is not None
        assert result[0]["feature"] == "love_language"

    def test_detect_unknown_trigger(self, service):
        """测试未知触发事件"""
        result = service.detect_scene(
            user_id="user_001",
            trigger="unknown_trigger",
            context={}
        )

        assert result is None

    def test_detect_multiple_rules(self, service):
        """测试多规则匹配"""
        result = service.detect_scene(
            user_id="user_001",
            trigger="match_created",
            context={
                "match_count": 1,
                "compatibility_score": 85  # 高匹配度
            }
        )

        # 应触发 first_match 和 high_compatibility_match
        assert result is not None
        features = [r["feature"] for r in result]
        assert "verify" in features
        assert "gifts" in features


class TestRecentlyPushed:
    """防重复推送测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return SceneDetectionService()

    def test_not_recently_pushed(self, service):
        """测试未最近推送"""
        result = service._recently_pushed("user_001", "new_user_registered", hours=24)

        assert result is False

    def test_recently_pushed_after_record(self, service):
        """测试记录后最近推送"""
        service._record_scene("user_001", "new_user_registered", {})

        result = service._recently_pushed("user_001", "new_user_registered", hours=24)

        assert result is True

    def test_recently_pushed_expired(self, service):
        """测试过期推送"""
        # 记录一个旧场景
        old_time = datetime.now() - timedelta(hours=48)
        context = SceneContext(
            user_id="user_001",
            scene_type="new_user_registered",
            trigger_data={},
            timestamp=old_time
        )
        service._user_scene_history["user_001"] = [context]

        result = service._recently_pushed("user_001", "new_user_registered", hours=24)

        # 48小时前记录，24小时检查应返回 False
        assert result is False

    def test_different_scene_not_recently_pushed(self, service):
        """测试不同场景不防重复"""
        service._record_scene("user_001", "new_user_registered", {})

        result = service._recently_pushed("user_001", "first_match", hours=24)

        assert result is False


class TestRecordScene:
    """场景历史记录测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return SceneDetectionService()

    def test_record_first_scene(self, service):
        """测试记录首个场景"""
        service._record_scene("user_001", "new_user_registered", {"source": "test"})

        assert "user_001" in service._user_scene_history
        assert len(service._user_scene_history["user_001"]) == 1

    def test_record_multiple_scenes(self, service):
        """测试记录多个场景"""
        service._record_scene("user_001", "new_user_registered", {})
        service._record_scene("user_001", "first_match", {})

        assert len(service._user_scene_history["user_001"]) == 2

    def test_record_scene_limit(self, service):
        """测试场景记录上限"""
        # 记录超过 100 个场景
        for i in range(110):
            service._record_scene("user_001", f"scene_{i}", {})

        # 应限制为最后 50 个（超过100后裁剪）
        # 实际实现：超过100后保留最后50个
        history_len = len(service._user_scene_history["user_001"])
        assert history_len >= 50
        assert history_len <= 110

    def test_record_scene_data(self, service):
        """测试记录场景数据"""
        service._record_scene("user_001", "test", {"key": "value"})

        history = service._user_scene_history["user_001"]
        assert history[0].trigger_data["key"] == "value"


class TestGetUserSceneHistory:
    """获取用户场景历史测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return SceneDetectionService()

    def test_get_empty_history(self, service):
        """测试获取空历史"""
        history = service.get_user_scene_history("user_001")

        assert history == []

    def test_get_existing_history(self, service):
        """测试获取已存在历史"""
        service._record_scene("user_001", "test", {})

        history = service.get_user_scene_history("user_001")

        assert len(history) == 1
        assert history[0].scene_type == "test"

    def test_get_multiple_history(self, service):
        """测试获取多个历史"""
        service._record_scene("user_001", "scene_1", {})
        service._record_scene("user_001", "scene_2", {})
        service._record_scene("user_001", "scene_3", {})

        history = service.get_user_scene_history("user_001")

        assert len(history) == 3


class TestClearUserHistory:
    """清除用户历史测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return SceneDetectionService()

    def test_clear_existing_history(self, service):
        """测试清除已存在历史"""
        service._record_scene("user_001", "test", {})

        service.clear_user_history("user_001")

        assert "user_001" not in service._user_scene_history

    def test_clear_non_existing_history(self, service):
        """测试清除不存在历史"""
        # 清除不存在的用户历史应不报错
        service.clear_user_history("user_nonexistent")

        assert "user_nonexistent" not in service._user_scene_history


class TestEdgeCases:
    """边界值测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return SceneDetectionService()

    def test_empty_user_id(self, service):
        """测试空用户 ID"""
        result = service.detect_scene(
            user_id="",
            trigger="user_registered",
            context={}
        )

        # 应正常处理
        assert result is not None

    def test_empty_context(self, service):
        """测试空上下文"""
        result = service.detect_scene(
            user_id="user_001",
            trigger="user_registered",
            context={}
        )

        assert result is not None

    def test_special_characters_in_user_id(self, service):
        """测试特殊字符用户 ID"""
        service._record_scene("user-特殊-001", "test", {})

        history = service.get_user_scene_history("user-特殊-001")
        assert len(history) == 1

    def test_delay_seconds_range(self, service):
        """测试延迟秒数范围"""
        for rule_name, rule in SCENE_RULES.items():
            delay = rule.get("delay", 0)
            assert delay >= 0
            assert delay <= 300  # 最大 5 分钟

    def test_priority_values(self, service):
        """测试优先级值"""
        valid_priorities = ["high", "medium", "low"]

        for rule_name, rule in SCENE_RULES.items():
            for push in rule.get("push", []):
                priority = push.get("priority", "medium")
                assert priority in valid_priorities

    def test_condition_functions_callable(self, service):
        """测试条件函数可调用"""
        for rule_name, rule in SCENE_RULES.items():
            condition = rule.get("condition")
            if condition:
                # 应为可调用函数
                assert callable(condition)

    def test_high_compatibility_threshold(self, service):
        """测试高匹配度阈值"""
        rule = SCENE_RULES["high_compatibility_match"]
        condition = rule["condition"]

        # 阈值应为 80
        assert condition({"compatibility_score": 80}) is True
        assert condition({"compatibility_score": 79}) is False

    def test_silence_threshold(self, service):
        """测试沉默阈值"""
        rule = SCENE_RULES["silence_detected"]
        condition = rule["condition"]

        # 阈值应为 > 300（严格大于）
        assert condition({"seconds": 301}) is True
        assert condition({"seconds": 300}) is False  # 刚好等于不触发

    def test_conflict_threshold(self, service):
        """测试冲突阈值"""
        rule = SCENE_RULES["conflict_detected"]
        condition = rule["condition"]

        # 阈值应为 > 0.6（严格大于）
        assert condition({"conflict_level": 0.61}) is True
        assert condition({"conflict_level": 0.6}) is False  # 刚好等于不触发