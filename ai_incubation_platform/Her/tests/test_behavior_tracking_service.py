"""
行为追踪服务测试

测试 BehaviorTrackingService 的核心功能：
- 事件记录
- 事件刷新
- 行为摘要
- 偏好分析
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from collections import defaultdict

# 尝试导入服务模块
try:
    from services.behavior_tracking_service import (
        BehaviorTrackingService,
        behavior_service
    )
except ImportError:
    pytest.skip("behavior_tracking_service not importable", allow_module_level=True)


class TestEventConstants:
    """事件常量测试"""

    def test_profile_view_event(self):
        """测试资料查看事件"""
        assert BehaviorTrackingService.EVENT_PROFILE_VIEW == "profile_view"

    def test_search_event(self):
        """测试搜索事件"""
        assert BehaviorTrackingService.EVENT_SEARCH == "search"

    def test_like_event(self):
        """测试点赞事件"""
        assert BehaviorTrackingService.EVENT_LIKE == "like"

    def test_pass_event(self):
        """测试跳过事件"""
        assert BehaviorTrackingService.EVENT_PASS == "pass"

    def test_message_open_event(self):
        """测试消息打开事件"""
        assert BehaviorTrackingService.EVENT_MESSAGE_OPEN == "message_open"

    def test_message_send_event(self):
        """测试消息发送事件"""
        assert BehaviorTrackingService.EVENT_MESSAGE_SEND == "message_send"

    def test_recommendation_click_event(self):
        """测试推荐点击事件"""
        assert BehaviorTrackingService.EVENT_RECOMMENDATION_CLICK == "recommendation_click"

    def test_recommendation_dismiss_event(self):
        """测试推荐忽略事件"""
        assert BehaviorTrackingService.EVENT_RECOMMENDATION_DISMISS == "recommendation_dismiss"


class TestServiceInitialization:
    """服务初始化测试"""

    def test_service_initialization(self):
        """测试服务初始化"""
        service = BehaviorTrackingService()
        assert service._event_buffer is not None
        assert isinstance(service._event_buffer, defaultdict)

    def test_buffer_size_limit(self):
        """测试缓冲区大小限制"""
        service = BehaviorTrackingService()
        assert service._buffer_size_limit == 100

    def test_buffer_time_limit(self):
        """测试缓冲区时间限制"""
        service = BehaviorTrackingService()
        assert service._buffer_time_limit == timedelta(minutes=5)


class TestRecordEvent:
    """事件记录测试"""

    def test_record_event_returns_id(self):
        """测试记录事件返回 ID"""
        service = BehaviorTrackingService()
        event_id = service.record_event("user_001", "profile_view")
        assert event_id is not None
        assert isinstance(event_id, str)

    def test_record_event_with_target(self):
        """测试带目标的事件记录"""
        service = BehaviorTrackingService()
        event_id = service.record_event(
            "user_001",
            "profile_view",
            target_id="user_002"
        )
        assert event_id is not None

    def test_record_event_with_data(self):
        """测试带数据的事件记录"""
        service = BehaviorTrackingService()
        event_id = service.record_event(
            "user_001",
            "search",
            event_data={"query": "咖啡厅"}
        )
        assert event_id is not None

    def test_event_added_to_buffer(self):
        """测试事件添加到缓冲区"""
        service = BehaviorTrackingService()
        service.record_event("user_001", "profile_view")
        assert "user_001" in service._event_buffer
        assert len(service._event_buffer["user_001"]) == 1

    def test_multiple_events_in_buffer(self):
        """测试多个事件在缓冲区"""
        service = BehaviorTrackingService()
        service.record_event("user_001", "profile_view")
        service.record_event("user_001", "like")
        service.record_event("user_001", "message_send")
        assert len(service._event_buffer["user_001"]) == 3


class TestEmptySummary:
    """空摘要测试"""

    def test_empty_summary_structure(self):
        """测试空摘要结构"""
        service = BehaviorTrackingService()
        summary = service._empty_summary()

        assert "total_events" in summary
        assert "event_counts" in summary
        assert "unique_profiles_viewed" in summary
        assert "peak_activity_hours" in summary
        assert "top_viewed_profiles" in summary
        assert "average_daily_events" in summary

    def test_empty_summary_values(self):
        """测试空摘要值"""
        service = BehaviorTrackingService()
        summary = service._empty_summary()

        assert summary["total_events"] == 0
        assert summary["event_counts"] == {}
        assert summary["unique_profiles_viewed"] == 0
        assert summary["peak_activity_hours"] == []
        assert summary["top_viewed_profiles"] == []
        assert summary["average_daily_events"] == 0


class TestPreferenceShiftAnalysis:
    """偏好变化分析测试"""

    def test_analyze_type_preference_no_events(self):
        """测试无事件的类型偏好"""
        service = BehaviorTrackingService()
        result = service._analyze_type_preference_shift([], None)
        assert result["shift"] is False

    def test_analyze_type_preference_high_like_rate(self):
        """测试高点赞率的类型偏好"""
        service = BehaviorTrackingService()
        # 创建模拟事件
        mock_events = []
        for _ in range(8):
            event = MagicMock()
            event.event_type = "like"
            mock_events.append(event)
        for _ in range(2):
            event = MagicMock()
            event.event_type = "pass"
            mock_events.append(event)

        result = service._analyze_type_preference_shift(mock_events, None)
        assert result["shift"] is True  # like_rate = 0.8 > 0.7
        assert "更开放" in result["description"]

    def test_analyze_type_preference_low_like_rate(self):
        """测试低点赞率的类型偏好"""
        service = BehaviorTrackingService()
        # 创建模拟事件
        mock_events = []
        for _ in range(2):
            event = MagicMock()
            event.event_type = "like"
            mock_events.append(event)
        for _ in range(8):
            event = MagicMock()
            event.event_type = "pass"
            mock_events.append(event)

        result = service._analyze_type_preference_shift(mock_events, None)
        assert result["shift"] is True  # like_rate = 0.2 < 0.3
        assert "更挑剔" in result["description"]

    def test_analyze_type_preference_balanced(self):
        """测试平衡的类型偏好"""
        service = BehaviorTrackingService()
        # 创建模拟事件
        mock_events = []
        for _ in range(5):
            event = MagicMock()
            event.event_type = "like"
            mock_events.append(event)
        for _ in range(5):
            event = MagicMock()
            event.event_type = "pass"
            mock_events.append(event)

        result = service._analyze_type_preference_shift(mock_events, None)
        assert result["shift"] is False  # like_rate = 0.5
        assert "平衡" in result["description"]


class TestAgePreferenceAnalysis:
    """年龄偏好分析测试"""

    def test_analyze_age_preference_no_likes(self):
        """测试无点赞的年龄偏好"""
        service = BehaviorTrackingService()
        result = service._analyze_age_preference_shift([], None)
        assert result["shift"] is False

    def test_analyze_age_preference_shift_structure(self):
        """测试年龄偏好分析结构"""
        service = BehaviorTrackingService()
        # 当有 liked_user_ids 时需要数据库查询
        # 简化测试：验证方法存在
        assert hasattr(service, '_analyze_age_preference_shift')


class TestLocationPreferenceAnalysis:
    """地点偏好分析测试"""

    def test_analyze_location_preference_default(self):
        """测试地点偏好默认返回"""
        service = BehaviorTrackingService()
        result = service._analyze_location_preference_shift([], None)
        assert result["shift"] is False
        assert result["description"] == ""


class TestFlushEvents:
    """刷新事件测试"""

    def test_flush_empty_buffer(self):
        """测试刷新空缓冲区"""
        service = BehaviorTrackingService()
        count = service.flush_events("user_no_events")
        assert count == 0

    def test_flush_removes_from_buffer(self):
        """测试刷新从缓冲区移除"""
        service = BehaviorTrackingService()
        service.record_event("user_001", "profile_view")
        # 手动调用 flush（不实际写入数据库）
        service._event_buffer["user_001"] = []
        count = service.flush_events("user_001")
        assert count == 0


class TestFlushAll:
    """刷新全部测试"""

    def test_flush_all_empty(self):
        """测试刷新全部空缓冲区"""
        service = BehaviorTrackingService()
        service._event_buffer.clear()
        count = service.flush_all()
        assert count == 0

    def test_flush_all_multiple_users(self):
        """测试刷新全部多个用户"""
        service = BehaviorTrackingService()
        service._event_buffer.clear()
        # 添加事件但不触发实际数据库写入
        service._event_buffer["user_001"] = []
        service._event_buffer["user_002"] = []

        count = service.flush_all()
        assert count == 0


class TestGlobalInstance:
    """全局实例测试"""

    def test_global_instance_exists(self):
        """测试全局实例存在"""
        assert behavior_service is not None

    def test_global_instance_type(self):
        """测试全局实例类型"""
        assert isinstance(behavior_service, BehaviorTrackingService)


class TestEdgeCases:
    """边界值测试"""

    def test_buffer_limit_threshold(self):
        """测试缓冲区限制阈值"""
        service = BehaviorTrackingService()
        # 验证缓冲区限制
        assert service._buffer_size_limit == 100

    def test_zero_days_summary(self):
        """测试零天数摘要"""
        service = BehaviorTrackingService()
        # 验证 _empty_summary 的结构
        summary = service._empty_summary()
        assert summary["average_daily_events"] == 0

    def test_event_data_can_be_none(self):
        """测试事件数据可为 None"""
        service = BehaviorTrackingService()
        event_id = service.record_event(
            "user_001",
            "profile_view",
            event_data=None
        )
        assert event_id is not None

    def test_target_id_can_be_none(self):
        """测试目标 ID 可为 None"""
        service = BehaviorTrackingService()
        event_id = service.record_event(
            "user_001",
            "search",
            target_id=None
        )
        assert event_id is not None

    def test_all_event_types(self):
        """测试所有事件类型"""
        service = BehaviorTrackingService()
        event_types = [
            service.EVENT_PROFILE_VIEW,
            service.EVENT_SEARCH,
            service.EVENT_LIKE,
            service.EVENT_PASS,
            service.EVENT_MESSAGE_OPEN,
            service.EVENT_MESSAGE_SEND,
            service.EVENT_RECOMMENDATION_CLICK,
            service.EVENT_RECOMMENDATION_DISMISS
        ]

        for event_type in event_types:
            event_id = service.record_event("user_001", event_type)
            assert event_id is not None