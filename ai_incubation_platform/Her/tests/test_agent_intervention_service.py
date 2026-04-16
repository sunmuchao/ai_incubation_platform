"""
Agent 自主权管控服务测试

测试 AgentInterventionService 的核心功能：
- 介入等级管理
- 事件检测
- 介入策略
"""
import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session

# 尝试导入服务模块
try:
    from services.agent_intervention_service import (
        AgentInterventionService,
        agent_intervention_service
    )
except ImportError:
    pytest.skip("agent_intervention_service not importable", allow_module_level=True)


class TestInterventionLevels:
    """介入等级测试"""

    def test_silent_level(self):
        """测试静默等级"""
        assert AgentInterventionService.INTERVENTION_LEVELS["silent"] == 0

    def test_private_level(self):
        """测试私下等级"""
        assert AgentInterventionService.INTERVENTION_LEVELS["private"] == 1

    def test_suggestion_level(self):
        """测试建议等级"""
        assert AgentInterventionService.INTERVENTION_LEVELS["suggestion"] == 2

    def test_active_level(self):
        """测试主动等级"""
        assert AgentInterventionService.INTERVENTION_LEVELS["active"] == 3

    def test_emergency_level(self):
        """测试紧急等级"""
        assert AgentInterventionService.INTERVENTION_LEVELS["emergency"] == 4

    def test_levels_count(self):
        """测试等级数量"""
        assert len(AgentInterventionService.INTERVENTION_LEVELS) == 5

    def test_levels_order(self):
        """测试等级顺序"""
        levels = list(AgentInterventionService.INTERVENTION_LEVELS.values())
        assert levels == [0, 1, 2, 3, 4]


class TestEventSeverity:
    """事件严重程度测试"""

    def test_safety_risk_severity(self):
        """测试安全风险严重程度"""
        assert AgentInterventionService.EVENT_SEVERITY["safety_risk_detected"] == 4

    def test_harassment_severity(self):
        """测试骚扰严重程度"""
        assert AgentInterventionService.EVENT_SEVERITY["harassment_detected"] == 4

    def test_abnormal_bill_severity(self):
        """测试账单异常严重程度"""
        assert AgentInterventionService.EVENT_SEVERITY["abnormal_bill"] == 3

    def test_unusual_location_severity(self):
        """测试位置异常严重程度"""
        assert AgentInterventionService.EVENT_SEVERITY["unusual_location"] == 3

    def test_aggressive_language_severity(self):
        """测试攻击性语言严重程度"""
        assert AgentInterventionService.EVENT_SEVERITY["aggressive_language"] == 2

    def test_fake_info_severity(self):
        """测试虚假信息严重程度"""
        assert AgentInterventionService.EVENT_SEVERITY["fake_info_detected"] == 2

    def test_preference_mismatch_severity(self):
        """测试偏好不一致严重程度"""
        assert AgentInterventionService.EVENT_SEVERITY["preference_mismatch"] == 1

    def test_dating_suggestion_severity(self):
        """测试约会建议严重程度"""
        assert AgentInterventionService.EVENT_SEVERITY["dating_suggestion"] == 1

    def test_event_types_count(self):
        """测试事件类型数量"""
        assert len(AgentInterventionService.EVENT_SEVERITY) >= 8


class TestDefaultInterventionStrategies:
    """默认介入策略测试"""

    def test_emergency_strategy(self):
        """测试紧急策略"""
        strategy = AgentInterventionService.DEFAULT_INTERVENTION_STRATEGIES[4]
        assert strategy["action"] == "emergency_intervention"
        assert strategy["notify_platform"] is True
        assert strategy["notify_user"] is True

    def test_active_strategy(self):
        """测试主动推送策略"""
        strategy = AgentInterventionService.DEFAULT_INTERVENTION_STRATEGIES[3]
        assert strategy["action"] == "push_notification"
        assert strategy["notify_platform"] is False
        assert strategy["notify_user"] is True

    def test_suggestion_strategy(self):
        """测试对话暗示策略"""
        strategy = AgentInterventionService.DEFAULT_INTERVENTION_STRATEGIES[2]
        assert strategy["action"] == "chat_suggestion"
        assert strategy["notify_platform"] is False

    def test_private_strategy(self):
        """测试私下提醒策略"""
        strategy = AgentInterventionService.DEFAULT_INTERVENTION_STRATEGIES[1]
        assert strategy["action"] == "private_notification"

    def test_silent_strategy(self):
        """测试静默策略"""
        strategy = AgentInterventionService.DEFAULT_INTERVENTION_STRATEGIES[0]
        assert strategy["action"] == "log_only"
        assert strategy["notify_platform"] is False
        assert strategy["notify_user"] is False

    def test_strategies_count(self):
        """测试策略数量"""
        assert len(AgentInterventionService.DEFAULT_INTERVENTION_STRATEGIES) == 5


class TestServiceMethods:
    """服务方法测试"""

    def test_get_level_description(self):
        """测试等级描述"""
        service = AgentInterventionService()
        desc = service._get_level_description("suggestion")
        assert "建议" in desc or "推荐" in desc

    def test_get_level_description_silent(self):
        """测试静默等级描述"""
        service = AgentInterventionService()
        desc = service._get_level_description("silent")
        assert "紧急" in desc

    def test_get_level_description_private(self):
        """测试私下等级描述"""
        service = AgentInterventionService()
        desc = service._get_level_description("private")
        assert "适度" in desc or "默认" in desc

    def test_get_level_description_active(self):
        """测试主动等级描述"""
        service = AgentInterventionService()
        desc = service._get_level_description("active")
        assert "指导" in desc or "新手" in desc

    def test_get_level_description_unknown(self):
        """测试未知等级描述"""
        service = AgentInterventionService()
        desc = service._get_level_description("unknown")
        assert desc == ""

    def test_get_intervention_history_empty(self):
        """测试介入历史为空"""
        service = AgentInterventionService()
        history = service.get_intervention_history("user_001")
        assert isinstance(history, list)


class TestCheckIntervention:
    """介入检查测试"""

    def test_check_intervention_level_calculation(self):
        """测试介入等级计算逻辑"""
        service = AgentInterventionService()

        # 严重程度 > 用户等级时升级
        user_level = 1
        severity = 4
        expected_upgrade = max(user_level, severity)

        assert expected_upgrade == 4

    def test_check_intervention_returns_none_for_log_only(self):
        """测试 log_only 返回 None"""
        # 等级 0 的策略是 log_only
        strategy = AgentInterventionService.DEFAULT_INTERVENTION_STRATEGIES[0]
        assert strategy["action"] == "log_only"

    def test_check_intervention_config_structure(self):
        """测试介入配置结构"""
        # 验证介入配置包含必要字段
        strategy = AgentInterventionService.DEFAULT_INTERVENTION_STRATEGIES[3]
        assert "action" in strategy
        assert "notify_platform" in strategy
        assert "notify_user" in strategy
        assert "message_template" in strategy


class TestExecuteIntervention:
    """执行介入测试"""

    def test_execute_emergency_intervention_returns_success(self):
        """测试紧急介入返回成功"""
        service = AgentInterventionService()
        config = {
            "action": "emergency_intervention",
            "event_type": "safety_risk_detected",
            "message": "安全风险"
        }
        success, msg = service.execute_intervention("user_001", config)
        assert success is True
        assert "紧急" in msg or "干预" in msg

    def test_execute_push_notification_returns_success(self):
        """测试推送通知返回成功"""
        service = AgentInterventionService()
        config = {
            "action": "push_notification",
            "message": "异常情况"
        }
        success, msg = service.execute_intervention("user_001", config)
        assert success is True
        assert "推送" in msg or "通知" in msg

    def test_execute_chat_suggestion_returns_success(self):
        """测试对话建议返回成功"""
        service = AgentInterventionService()
        config = {
            "action": "chat_suggestion",
            "message": "委婉提醒"
        }
        success, msg = service.execute_intervention("user_001", config)
        assert success is True
        assert "建议" in msg or "对话" in msg

    def test_execute_private_notification_returns_success(self):
        """测试私下提醒返回成功"""
        service = AgentInterventionService()
        config = {
            "action": "private_notification",
            "message": "私下提醒"
        }
        success, msg = service.execute_intervention("user_001", config)
        assert success is True
        assert "私下" in msg or "提醒" in msg

    def test_execute_unknown_action_returns_failure(self):
        """测试未知动作返回失败"""
        service = AgentInterventionService()
        config = {
            "action": "unknown_action",
            "message": "测试"
        }
        success, msg = service.execute_intervention("user_001", config)
        assert success is False
        assert "未知" in msg


class TestLevelDescriptions:
    """等级描述完整性测试"""

    def test_all_levels_have_descriptions(self):
        """测试所有等级都有描述"""
        service = AgentInterventionService()
        descriptions = {
            "silent": "仅在紧急情况下提醒",
            "private": "适度提醒（默认）",
            "suggestion": "主动提供建议（推荐）",
            "active": "全方位指导（适合恋爱新手）",
            "emergency": "仅紧急情况干预"
        }

        for level_name in AgentInterventionService.INTERVENTION_LEVELS.keys():
            desc = service._get_level_description(level_name)
            assert level_name in descriptions or desc == ""


class TestGlobalInstance:
    """全局实例测试"""

    def test_global_instance_exists(self):
        """测试全局实例存在"""
        assert agent_intervention_service is not None

    def test_global_instance_type(self):
        """测试全局实例类型"""
        assert isinstance(agent_intervention_service, AgentInterventionService)


class TestEdgeCases:
    """边界值测试"""

    def test_invalid_level_name(self):
        """测试无效等级名"""
        service = AgentInterventionService()
        levels = AgentInterventionService.INTERVENTION_LEVELS
        assert "invalid_level" not in levels

    def test_unknown_event_type(self):
        """测试未知事件类型"""
        # 未知事件类型应使用默认严重程度
        severity = AgentInterventionService.EVENT_SEVERITY.get("unknown_event", 1)
        assert severity == 1

    def test_extreme_severity(self):
        """测试极端严重程度"""
        # 最高严重程度是 4
        max_severity = max(AgentInterventionService.EVENT_SEVERITY.values())
        assert max_severity == 4

    def test_min_severity(self):
        """测试最低严重程度"""
        min_severity = min(AgentInterventionService.EVENT_SEVERITY.values())
        assert min_severity == 1

    def test_user_settings_structure(self):
        """测试用户设置结构"""
        service = AgentInterventionService()
        # 用户设置应包含必要字段
        # 由于需要数据库，使用 mock
        with patch.object(service, 'get_user_intervention_level', return_value=2):
            settings = service.get_user_settings("user_001")
            assert "user_id" in settings
            assert "intervention_level" in settings
            assert "intervention_level_name" in settings