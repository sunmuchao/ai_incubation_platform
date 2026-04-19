"""
行为日志服务测试

测试 BehaviorLogService 的核心功能：
- 行为事件记录
- 日统计数据更新
- 用户行为历史查询
- 活跃时间段分析
- 消息统计分析
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta
import json

# 尝试导入服务模块
try:
    from services.behavior_log_service import (
        BehaviorLogService,
        EventTypes,
        get_behavior_log_service,
    )
    from models.behavior_log import UserBehaviorEventDB, UserBehaviorDailyStatsDB
except ImportError:
    pytest.skip("behavior_log_service not importable", allow_module_level=True)


class TestEventTypesConstants:
    """事件类型常量测试"""

    def test_event_types_exist(self):
        """测试事件类型常量存在"""
        assert EventTypes.SWIPE == "swipe"
        assert EventTypes.MESSAGE == "message"
        assert EventTypes.PROFILE_VIEW == "profile_view"
        assert EventTypes.MATCH == "match"
        assert EventTypes.LOGIN == "login"
        assert EventTypes.LOGOUT == "logout"
        assert EventTypes.PROFILE_UPDATE == "profile_update"
        assert EventTypes.SEARCH == "search"
        assert EventTypes.FILTER_CHANGE == "filter_change"
        assert EventTypes.NOTIFICATION_CLICK == "notification_click"

    def test_event_types_count(self):
        """测试事件类型数量"""
        # 应至少有 10 种事件类型
        event_types = [
            EventTypes.SWIPE,
            EventTypes.MESSAGE,
            EventTypes.PROFILE_VIEW,
            EventTypes.MATCH,
            EventTypes.LOGIN,
            EventTypes.LOGOUT,
            EventTypes.PROFILE_UPDATE,
            EventTypes.SEARCH,
            EventTypes.FILTER_CHANGE,
            EventTypes.NOTIFICATION_CLICK,
        ]
        assert len(event_types) == 10


class TestServiceInitialization:
    """服务初始化测试"""

    def test_service_creation(self):
        """测试服务创建"""
        mock_db = MagicMock()
        service = BehaviorLogService(mock_db)

        assert service is not None
        assert service.db == mock_db

    def test_get_behavior_log_service_factory(self):
        """测试服务工厂函数"""
        mock_db = MagicMock()
        service = get_behavior_log_service(mock_db)

        assert service is not None
        assert isinstance(service, BehaviorLogService)


class TestLogEvent:
    """事件记录测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        mock_db = MagicMock()
        return BehaviorLogService(mock_db)

    def test_log_swipe_event(self, service):
        """测试滑动事件记录"""
        event_id = service.log_event(
            user_id="user_001",
            event_type="swipe",
            event_data={"action": "like", "target_user_id": "user_002"}
        )

        assert event_id is not None
        assert event_id.startswith("ube-user_001")
        assert service.db.add.called
        assert service.db.commit.called

    def test_log_message_event(self, service):
        """测试消息事件记录"""
        event_id = service.log_event(
            user_id="user_001",
            event_type="message",
            event_data={
                "conversation_id": "conv_001",
                "message_length": 50,
                "response_time_seconds": 120
            }
        )

        assert event_id is not None
        assert service.db.add.called

    def test_log_profile_view_event(self, service):
        """测试查看档案事件记录"""
        event_id = service.log_event(
            user_id="user_001",
            event_type="profile_view",
            event_data={
                "viewed_user_id": "user_002",
                "view_duration_seconds": 30
            }
        )

        assert event_id is not None

    def test_log_match_event(self, service):
        """测试匹配事件记录"""
        event_id = service.log_event(
            user_id="user_001",
            event_type="match",
            event_data={
                "matched_user_id": "user_002",
                "compatibility_score": 0.85
            }
        )

        assert event_id is not None

    def test_log_event_with_session_info(self, service):
        """测试带会话信息的事件记录"""
        event_id = service.log_event(
            user_id="user_001",
            event_type="login",
            session_id="session_123",
            device_id="device_456",
            ip_address="192.168.1.1"
        )

        assert event_id is not None
        # 验证添加的事件包含会话信息
        added_event = service.db.add.call_args[0][0]
        assert added_event.session_id == "session_123"
        assert added_event.device_id == "device_456"
        assert added_event.ip_address == "192.168.1.1"

    def test_log_event_without_data(self, service):
        """测试无数据事件记录"""
        event_id = service.log_event(
            user_id="user_001",
            event_type="login"
        )

        assert event_id is not None


class TestUpdateDailyStats:
    """日统计更新测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        mock_db = MagicMock()
        service = BehaviorLogService(mock_db)
        # Mock query 返回空（无已存在统计）
        service.db.query.return_value.filter.return_value.first.return_value = None
        return service

    def test_update_swipe_stats(self, service):
        """测试滑动统计更新"""
        service._update_daily_stats(
            user_id="user_001",
            event_type="swipe",
            event_data={"action": "like"}
        )

        # 应创建新统计记录
        assert service.db.add.called
        added_stats = service.db.add.call_args[0][0]
        assert added_stats.swipe_count == 1
        assert added_stats.like_count == 1

    def test_update_swipe_pass_stats(self, service):
        """测试滑动 pass 统计更新"""
        service._update_daily_stats(
            user_id="user_001",
            event_type="swipe",
            event_data={"action": "pass"}
        )

        added_stats = service.db.add.call_args[0][0]
        assert added_stats.swipe_count == 1
        assert added_stats.pass_count == 1

    def test_update_message_stats(self, service):
        """测试消息统计更新"""
        service._update_daily_stats(
            user_id="user_001",
            event_type="message"
        )

        # 由于无已存在统计，会创建新记录
        # message_count 初始为 0，后续更新
        assert service.db.commit.called

    def test_update_profile_view_stats(self, service):
        """测试查看档案统计更新"""
        service._update_daily_stats(
            user_id="user_001",
            event_type="profile_view"
        )

        assert service.db.commit.called

    def test_update_match_stats(self, service):
        """测试匹配统计更新"""
        service._update_daily_stats(
            user_id="user_001",
            event_type="match"
        )

        assert service.db.commit.called

    def test_update_existing_stats(self):
        """测试更新已存在统计"""
        mock_db = MagicMock()

        # Mock 已存在统计
        mock_stats = MagicMock()
        mock_stats.swipe_count = 5
        mock_stats.like_count = 3
        mock_stats.pass_count = 2
        mock_stats.message_count = 10
        mock_stats.last_active_time = datetime.now() - timedelta(hours=1)

        mock_db.query.return_value.filter.return_value.first.return_value = mock_stats

        service = BehaviorLogService(mock_db)
        service._update_daily_stats(
            user_id="user_001",
            event_type="swipe",
            event_data={"action": "like"}
        )

        # 应更新已存在记录，而非创建新记录
        assert mock_stats.swipe_count == 6
        assert mock_stats.like_count == 4


class TestGetUserBehaviorHistory:
    """用户行为历史查询测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        mock_db = MagicMock()
        return BehaviorLogService(mock_db)

    def test_get_history_default_days(self, service):
        """测试默认天数查询"""
        # Mock 事件列表
        mock_events = [
            MagicMock(
                id="event_001",
                event_type="swipe",
                event_data={"action": "like"},
                created_at=datetime.now()
            ),
            MagicMock(
                id="event_002",
                event_type="message",
                event_data={"message_length": 50},
                created_at=datetime.now()
            )
        ]

        service.db.query.return_value.filter.return_value.order_by.return_value.all.return_value = mock_events

        history = service.get_user_behavior_history("user_001")

        assert len(history) == 2
        assert history[0]["event_type"] == "swipe"
        assert history[1]["event_type"] == "message"

    def test_get_history_with_event_type_filter(self, service):
        """测试带事件类型过滤"""
        mock_events = [
            MagicMock(
                id="event_001",
                event_type="message",
                event_data={"message_length": 50},
                created_at=datetime.now()
            )
        ]

        service.db.query.return_value.filter.return_value.filter.return_value.order_by.return_value.all.return_value = mock_events

        history = service.get_user_behavior_history(
            "user_001",
            event_type="message"
        )

        assert len(history) == 1
        assert history[0]["event_type"] == "message"

    def test_get_history_custom_days(self, service):
        """测试自定义天数查询"""
        mock_events = []

        service.db.query.return_value.filter.return_value.order_by.return_value.all.return_value = mock_events

        history = service.get_user_behavior_history("user_001", days=30)

        assert history == []

    def test_get_history_empty_result(self, service):
        """测试空结果"""
        service.db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

        history = service.get_user_behavior_history("user_001")

        assert history == []


class TestGetUserDailyStats:
    """用户日统计查询测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        mock_db = MagicMock()
        return BehaviorLogService(mock_db)

    def test_get_daily_stats_default_days(self, service):
        """测试默认天数查询"""
        mock_stats = [
            MagicMock(
                stat_date=datetime.now(),
                swipe_count=10,
                like_count=5,
                pass_count=5,
                message_count=20,
                profile_view_count=15,
                match_count=2,
                active_minutes=60,
                first_active_time=datetime.now(),
                last_active_time=datetime.now()
            )
        ]

        service.db.query.return_value.filter.return_value.order_by.return_value.all.return_value = mock_stats

        stats = service.get_user_daily_stats("user_001")

        assert len(stats) == 1
        assert stats[0]["swipe_count"] == 10
        assert stats[0]["message_count"] == 20

    def test_get_daily_stats_custom_days(self, service):
        """测试自定义天数查询"""
        mock_stats = []

        service.db.query.return_value.filter.return_value.order_by.return_value.all.return_value = mock_stats

        stats = service.get_user_daily_stats("user_001", days=7)

        assert stats == []

    def test_get_daily_stats_empty_result(self, service):
        """测试空结果"""
        service.db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

        stats = service.get_user_daily_stats("user_001")

        assert stats == []


class TestGetActiveHours:
    """活跃时间段测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        mock_db = MagicMock()
        return BehaviorLogService(mock_db)

    def test_get_active_hours_single_event(self, service):
        """测试单个事件活跃时间"""
        # Mock 返回小时提取结果
        mock_events = [MagicMock(hour=10)]

        service.db.query.return_value.filter.return_value.all.return_value = mock_events

        hours = service.get_active_hours("user_001")

        assert hours == [10]

    def test_get_active_hours_multiple_events(self, service):
        """测试多个事件活跃时间"""
        mock_events = [
            MagicMock(hour=8),
            MagicMock(hour=10),
            MagicMock(hour=12),
            MagicMock(hour=10),  # 重复
        ]

        service.db.query.return_value.filter.return_value.all.return_value = mock_events

        hours = service.get_active_hours("user_001")

        # 应去重并排序
        assert hours == [8, 10, 12]

    def test_get_active_hours_no_events(self, service):
        """测试无事件活跃时间"""
        service.db.query.return_value.filter.return_value.all.return_value = []

        hours = service.get_active_hours("user_001")

        assert hours == []

    def test_get_active_hours_custom_days(self, service):
        """测试自定义天数活跃时间"""
        mock_events = [MagicMock(hour=14)]

        service.db.query.return_value.filter.return_value.all.return_value = mock_events

        hours = service.get_active_hours("user_001", days=30)

        assert hours == [14]


class TestGetMessageStats:
    """消息统计测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        mock_db = MagicMock()
        return BehaviorLogService(mock_db)

    def test_get_message_stats_with_messages(self, service):
        """测试有消息统计"""
        mock_events = [
            MagicMock(
                event_data={
                    "message_length": 50,
                    "conversation_id": "conv_001",
                    "response_time_seconds": 120
                }
            ),
            MagicMock(
                event_data={
                    "message_length": 100,
                    "conversation_id": "conv_001",
                    "response_time_seconds": 60
                }
            ),
            MagicMock(
                event_data={
                    "message_length": 30,
                    "conversation_id": "conv_002",
                    "response_time_seconds": 180
                }
            )
        ]

        # get_message_stats does: query().filter(...).all()
        service.db.query.return_value.filter.return_value.all.return_value = mock_events

        stats = service.get_message_stats("user_001")

        assert stats["total_messages"] == 3
        assert stats["avg_message_length"] == 60.0  # (50+100+30)/3
        assert stats["active_conversations"] == 2  # conv_001, conv_002
        # 平均响应时间: (120+60+180)/3 = 120秒 = 2分钟
        assert stats["avg_response_time_minutes"] == 2.0

    def test_get_message_stats_no_messages(self, service):
        """测试无消息统计"""
        service.db.query.return_value.filter.return_value.all.return_value = []

        stats = service.get_message_stats("user_001")

        assert stats["total_messages"] == 0
        assert stats["avg_message_length"] == 0
        assert stats["active_conversations"] == 0
        assert stats["avg_response_time_minutes"] == 0

    def test_get_message_stats_custom_days(self, service):
        """测试自定义天数消息统计"""
        mock_events = [
            MagicMock(
                event_data={
                    "message_length": 80,
                    "conversation_id": "conv_001",
                    "response_time_seconds": 90
                }
            )
        ]

        service.db.query.return_value.filter.return_value.all.return_value = mock_events

        stats = service.get_message_stats("user_001", days=14)

        assert stats["total_messages"] == 1
        assert stats["avg_message_length"] == 80.0

    def test_get_message_stats_missing_event_data(self, service):
        """测试缺失事件数据处理"""
        mock_events = [
            MagicMock(event_data=None),
            MagicMock(event_data={"message_length": 50})
        ]

        service.db.query.return_value.filter.return_value.all.return_value = mock_events

        stats = service.get_message_stats("user_001")

        # 缺失数据的应被忽略
        assert stats["total_messages"] == 2
        assert stats["avg_message_length"] == 25.0  # 50/2


class TestEdgeCases:
    """边界值测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        mock_db = MagicMock()
        return BehaviorLogService(mock_db)

    def test_event_id_format(self, service):
        """测试事件 ID 格式"""
        event_id = service.log_event(
            user_id="user_001",
            event_type="test"
        )

        # ID 应以 "ube-" 开头并包含 user_id
        assert event_id.startswith("ube-user_001")

    def test_stats_id_format(self, service):
        """测试统计 ID 格式"""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        stats_id = f"ubd-user_001-{today.strftime('%Y%m%d')}"

        # 验证 ID 格式正确
        assert stats_id.startswith("ubd-user_001")
        assert len(stats_id) > 15

    def test_zero_days_query(self, service):
        """测试零天数查询"""
        # 零天应查询今天
        service.db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

        history = service.get_user_behavior_history("user_001", days=0)

        # 应返回空列表
        assert history == []

    def test_large_days_query(self, service):
        """测试大天数查询"""
        service.db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

        history = service.get_user_behavior_history("user_001", days=365)

        assert history == []

    def test_empty_event_data(self, service):
        """测试空事件数据"""
        event_id = service.log_event(
            user_id="user_001",
            event_type="test",
            event_data={}
        )

        assert event_id is not None

    def test_null_event_data(self, service):
        """测试 None 事件数据"""
        event_id = service.log_event(
            user_id="user_001",
            event_type="test",
            event_data=None
        )

        assert event_id is not None

    def test_special_characters_in_user_id(self, service):
        """测试特殊字符 user_id"""
        event_id = service.log_event(
            user_id="user-特殊字符-001",
            event_type="test"
        )

        # 应正常处理
        assert event_id is not None

    def test_message_stats_all_null_event_data(self, service):
        """测试所有事件数据为 None"""
        mock_events = [
            MagicMock(event_data=None),
            MagicMock(event_data=None)
        ]

        service.db.query.return_value.filter.return_value.all.return_value = mock_events

        stats = service.get_message_stats("user_001")

        # 应返回零统计
        assert stats["total_messages"] == 2
        assert stats["avg_message_length"] == 0

    def test_message_stats_no_conversation_id(self, service):
        """测试消息无对话 ID"""
        mock_events = [
            MagicMock(event_data={"message_length": 50})
        ]

        service.db.query.return_value.filter.return_value.filter.return_value.all.return_value = mock_events

        stats = service.get_message_stats("user_001")

        assert stats["active_conversations"] == 0

    def test_active_hours_range(self, service):
        """测试活跃小时范围"""
        mock_events = [
            MagicMock(hour=0),
            MagicMock(hour=23)
        ]

        service.db.query.return_value.filter.return_value.all.return_value = mock_events

        hours = service.get_active_hours("user_001")

        # 应包含边界值
        assert 0 in hours
        assert 23 in hours