"""
Your Turn 提醒服务测试

测试 YourTurnReminderService 的核心功能：
- 提醒配置常量
- 获取待处理提醒
- 判断是否显示提醒
- 标记提醒已显示
- 获取提醒统计
- 忽略提醒
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

# 尝试导入服务模块
try:
    from services.your_turn_service import (
        YourTurnReminderService,
        get_your_turn_service,
    )
except ImportError:
    pytest.skip("your_turn_service not importable", allow_module_level=True)


class TestReminderConfiguration:
    """提醒配置常量测试"""

    def test_reminder_delay_hours(self):
        """测试首次提醒延迟"""
        assert YourTurnReminderService.REMINDER_DELAY_HOURS == 24

    def test_reminder_interval_hours(self):
        """测试提醒间隔"""
        assert YourTurnReminderService.REMINDER_INTERVAL_HOURS == 48

    def test_max_reminders(self):
        """测试最大提醒次数"""
        assert YourTurnReminderService.MAX_REMINDERS == 3

    def test_reminder_expire_days(self):
        """测试提醒过期天数"""
        assert YourTurnReminderService.REMINDER_EXPIRE_DAYS == 7


class TestServiceInitialization:
    """服务初始化测试"""

    def test_service_creation(self):
        """测试服务创建"""
        mock_db = MagicMock()
        service = YourTurnReminderService(mock_db)

        assert service is not None
        assert service.db == mock_db

    def test_get_your_turn_service_factory(self):
        """测试服务工厂函数"""
        mock_db = MagicMock()
        service = get_your_turn_service(mock_db)

        assert service is not None
        assert isinstance(service, YourTurnReminderService)


class TestMarkReminderShown:
    """标记提醒已显示测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        mock_db = MagicMock()
        return YourTurnReminderService(mock_db)

    def test_mark_new_reminder(self, service):
        """测试标记新提醒"""
        # Mock 无已存在记录
        service.db.query.return_value.filter.return_value.first.return_value = None

        result = service.mark_reminder_shown("user_001", "conv_001")

        assert result is True
        assert service.db.add.called
        assert service.db.commit.called

    def test_mark_existing_reminder(self, service):
        """测试标记已存在提醒"""
        # Mock 已存在记录
        mock_existing = MagicMock()
        mock_existing.shown_count = 1
        mock_existing.last_shown_at = datetime.now() - timedelta(hours=1)

        service.db.query.return_value.filter.return_value.first.return_value = mock_existing

        result = service.mark_reminder_shown("user_001", "conv_001")

        assert result is True
        assert mock_existing.shown_count == 2
        assert service.db.commit.called

    def test_mark_creates_valid_record(self, service):
        """测试创建有效记录"""
        service.db.query.return_value.filter.return_value.first.return_value = None

        service.mark_reminder_shown("user_001", "conv_001")

        added_record = service.db.add.call_args[0][0]
        assert added_record.user_id == "user_001"
        assert added_record.conversation_id == "conv_001"
        assert added_record.shown_count == 1


class TestDismissReminder:
    """忽略提醒测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        mock_db = MagicMock()
        return YourTurnReminderService(mock_db)

    def test_dismiss_existing_reminder(self, service):
        """测试忽略已存在提醒"""
        mock_reminder = MagicMock()
        mock_reminder.dismissed = False
        mock_reminder.dismissed_at = None

        service.db.query.return_value.filter.return_value.first.return_value = mock_reminder

        result = service.dismiss_reminder("user_001", "conv_001")

        assert result is True
        assert mock_reminder.dismissed is True
        assert mock_reminder.dismissed_at is not None
        assert service.db.commit.called

    def test_dismiss_non_existing_reminder(self, service):
        """测试忽略不存在提醒"""
        service.db.query.return_value.filter.return_value.first.return_value = None

        result = service.dismiss_reminder("user_001", "conv_001")

        assert result is False


class TestGetReminderStats:
    """提醒统计测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        mock_db = MagicMock()
        return YourTurnReminderService(mock_db)

    def test_get_stats_no_pending(self, service):
        """测试无待处理统计"""
        # Mock get_pending_reminders 返回空
        with patch.object(service, 'get_pending_reminders', return_value=[]):
            stats = service.get_reminder_stats("user_001")

            assert stats["pending_count"] == 0
            assert stats["total_waiting_hours"] == 0
            assert stats["oldest_waiting_hours"] == 0

    def test_get_stats_single_pending(self, service):
        """测试单个待处理统计"""
        mock_reminders = [
            {
                "conversation_id": "conv_001",
                "hours_waiting": 30
            }
        ]

        with patch.object(service, 'get_pending_reminders', return_value=mock_reminders):
            stats = service.get_reminder_stats("user_001")

            assert stats["pending_count"] == 1
            assert stats["total_waiting_hours"] == 30
            assert stats["oldest_waiting_hours"] == 30

    def test_get_stats_multiple_pending(self, service):
        """测试多个待处理统计"""
        mock_reminders = [
            {
                "conversation_id": "conv_001",
                "hours_waiting": 24
            },
            {
                "conversation_id": "conv_002",
                "hours_waiting": 48
            },
            {
                "conversation_id": "conv_003",
                "hours_waiting": 72
            }
        ]

        with patch.object(service, 'get_pending_reminders', return_value=mock_reminders):
            stats = service.get_reminder_stats("user_001")

            assert stats["pending_count"] == 3
            assert stats["total_waiting_hours"] == 144  # 24 + 48 + 72
            assert stats["oldest_waiting_hours"] == 72


class TestShouldShowReminder:
    """判断是否显示提醒测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        mock_db = MagicMock()
        return YourTurnReminderService(mock_db)

    def test_should_show_found(self, service):
        """测试应显示提醒"""
        mock_reminders = [
            {
                "conversation_id": "conv_001",
                "hours_waiting": 30
            }
        ]

        with patch.object(service, 'get_pending_reminders', return_value=mock_reminders):
            should_show, detail = service.should_show_reminder("user_001", "conv_001")

            assert should_show is True
            assert detail is not None
            assert detail["conversation_id"] == "conv_001"

    def test_should_show_not_found(self, service):
        """测试不应显示提醒"""
        mock_reminders = [
            {
                "conversation_id": "conv_002",
                "hours_waiting": 30
            }
        ]

        with patch.object(service, 'get_pending_reminders', return_value=mock_reminders):
            should_show, detail = service.should_show_reminder("user_001", "conv_001")

            assert should_show is False
            assert detail is None

    def test_should_show_empty_list(self, service):
        """测试空提醒列表"""
        with patch.object(service, 'get_pending_reminders', return_value=[]):
            should_show, detail = service.should_show_reminder("user_001", "conv_001")

            assert should_show is False
            assert detail is None


class TestEdgeCases:
    """边界值测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        mock_db = MagicMock()
        return YourTurnReminderService(mock_db)

    def test_zero_waiting_hours(self, service):
        """测试零等待小时"""
        mock_reminders = [
            {
                "conversation_id": "conv_001",
                "hours_waiting": 0
            }
        ]

        with patch.object(service, 'get_pending_reminders', return_value=mock_reminders):
            stats = service.get_reminder_stats("user_001")

            assert stats["total_waiting_hours"] == 0
            assert stats["oldest_waiting_hours"] == 0

    def test_large_waiting_hours(self, service):
        """测试大等待小时"""
        mock_reminders = [
            {
                "conversation_id": "conv_001",
                "hours_waiting": 1000
            }
        ]

        with patch.object(service, 'get_pending_reminders', return_value=mock_reminders):
            stats = service.get_reminder_stats("user_001")

            assert stats["total_waiting_hours"] == 1000
            assert stats["oldest_waiting_hours"] == 1000

    def test_multiple_same_conversation(self, service):
        """测试重复对话"""
        mock_reminders = [
            {
                "conversation_id": "conv_001",
                "hours_waiting": 24
            },
            {
                "conversation_id": "conv_001",
                "hours_waiting": 48
            }
        ]

        with patch.object(service, 'get_pending_reminders', return_value=mock_reminders):
            stats = service.get_reminder_stats("user_001")

            # 即使有重复，统计仍正常计算
            assert stats["pending_count"] == 2

    def test_special_characters_in_ids(self, service):
        """测试特殊字符 ID"""
        service.db.query.return_value.filter.return_value.first.return_value = None

        result = service.mark_reminder_shown("user-特殊-001", "conv-特殊-001")

        assert result is True

    def test_empty_user_id(self, service):
        """测试空用户 ID"""
        service.db.query.return_value.filter.return_value.first.return_value = None

        result = service.mark_reminder_shown("", "conv_001")

        assert result is True

    def test_empty_conversation_id(self, service):
        """测试空对话 ID"""
        service.db.query.return_value.filter.return_value.first.return_value = None

        result = service.mark_reminder_shown("user_001", "")

        assert result is True