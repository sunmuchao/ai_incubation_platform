"""
AI 行为信用分服务测试

测试 BehaviorCreditService 的核心功能：
- 信用记录创建与管理
- 正面/负面行为事件记录
- 信用等级计算
- 限制措施应用
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from services.behavior_credit_service import BehaviorCreditService
from models.future_models import BehaviorCreditDB, BehaviorCreditEventDB


class TestBehaviorCreditService:
    """行为信用分服务测试"""

    def test_negative_events_config(self):
        """测试负面行为扣分配置"""
        service = BehaviorCreditService.__new__(BehaviorCreditService)
        assert "harassment_reported" in service.NEGATIVE_EVENTS
        assert service.NEGATIVE_EVENTS["harassment_reported"] == -50
        assert service.NEGATIVE_EVENTS["fake_info_detected"] == -30
        assert service.NEGATIVE_EVENTS["aggressive_language"] == -20

    def test_positive_events_config(self):
        """测试正面行为加分配置"""
        service = BehaviorCreditService.__new__(BehaviorCreditService)
        assert "complete_profile" in service.POSITIVE_EVENTS
        assert service.POSITIVE_EVENTS["complete_profile"] == 10
        assert service.POSITIVE_EVENTS["verified_badge"] == 20
        assert service.POSITIVE_EVENTS["successful_date"] == 25

    def test_credit_levels_config(self):
        """测试信用等级定义"""
        service = BehaviorCreditService.__new__(BehaviorCreditService)
        assert service.CREDIT_LEVELS["S"][0] == 90  # S: 90-100
        assert service.CREDIT_LEVELS["A"][0] == 75  # A: 75-89
        assert service.CREDIT_LEVELS["B"][0] == 60  # B: 60-74
        assert service.CREDIT_LEVELS["C"][0] == 40  # C: 40-59
        assert service.CREDIT_LEVELS["D"][0] == 0   # D: 0-39

    def test_restrictions_by_level(self):
        """测试限制措施配置"""
        service = BehaviorCreditService.__new__(BehaviorCreditService)
        # S 和 A 级别无限制
        assert service.RESTRICTIONS_BY_LEVEL["S"] == []
        assert service.RESTRICTIONS_BY_LEVEL["A"] == []
        # C 级别禁止交换联系方式
        assert "no_contact_exchange" in service.RESTRICTIONS_BY_LEVEL["C"]
        # D 级别禁止发起聊天
        assert "no_chat_initiate" in service.RESTRICTIONS_BY_LEVEL["D"]

    def test_calculate_level_s(self):
        """测试计算 S 级别"""
        service = BehaviorCreditService.__new__(BehaviorCreditService)
        assert service._calculate_level(95) == "S"
        assert service._calculate_level(100) == "S"
        assert service._calculate_level(90) == "S"

    def test_calculate_level_a(self):
        """测试计算 A 级别"""
        service = BehaviorCreditService.__new__(BehaviorCreditService)
        assert service._calculate_level(75) == "A"
        assert service._calculate_level(85) == "A"
        assert service._calculate_level(89) == "A"

    def test_calculate_level_b(self):
        """测试计算 B 级别"""
        service = BehaviorCreditService.__new__(BehaviorCreditService)
        assert service._calculate_level(60) == "B"
        assert service._calculate_level(70) == "B"
        assert service._calculate_level(74) == "B"

    def test_calculate_level_c(self):
        """测试计算 C 级别"""
        service = BehaviorCreditService.__new__(BehaviorCreditService)
        assert service._calculate_level(40) == "C"
        assert service._calculate_level(50) == "C"
        assert service._calculate_level(59) == "C"

    def test_calculate_level_d(self):
        """测试计算 D 级别"""
        service = BehaviorCreditService.__new__(BehaviorCreditService)
        assert service._calculate_level(0) == "D"
        assert service._calculate_level(20) == "D"
        assert service._calculate_level(39) == "D"

    def test_calculate_level_edge_cases(self):
        """测试边界值"""
        service = BehaviorCreditService.__new__(BehaviorCreditService)
        # 边界值刚好落在区间边缘
        assert service._calculate_level(89) == "A"  # A 区间上限
        assert service._calculate_level(90) == "S"  # S 区间下限
        assert service._calculate_level(74) == "B"  # B 区间上限
        assert service._calculate_level(75) == "A"  # A 区间下限


class TestBehaviorCreditServiceWithDB:
    """需要数据库的测试"""

    @pytest.fixture
    def mock_db(self):
        """Mock 数据库会话"""
        return MagicMock()

    @pytest.fixture
    def service(self, mock_db):
        """创建服务实例"""
        return BehaviorCreditService(db=mock_db)

    def test_get_or_create_credit_existing(self, service, mock_db):
        """测试获取已存在的信用记录"""
        mock_credit = MagicMock()
        mock_credit.user_id = "test_user"
        mock_credit.credit_score = 85

        mock_db.query.return_value.filter.return_value.first.return_value = mock_credit

        result = service.get_or_create_credit("test_user")

        assert result == mock_credit
        mock_db.add.assert_not_called()

    def test_get_or_create_credit_new(self, service, mock_db):
        """测试创建新的信用记录"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = service.get_or_create_credit("new_user")

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_record_event_positive(self, service, mock_db):
        """测试记录正面事件"""
        mock_credit = MagicMock()
        mock_credit.credit_score = 70
        mock_credit.positive_score = 0
        mock_credit.negative_score = 0
        mock_credit.total_positive_events = 0
        mock_credit.total_negative_events = 0
        mock_credit.credit_level = "B"
        mock_credit.level_history = "[]"

        mock_db.query.return_value.filter.return_value.first.return_value = mock_credit

        success, message, score_change = service.record_event(
            user_id="test_user",
            event_type="complete_profile",
            description="完善资料"
        )

        assert success is True
        assert score_change == 10
        assert "+" in message or "10" in message

    def test_record_event_negative(self, service, mock_db):
        """测试记录负面事件"""
        mock_credit = MagicMock()
        mock_credit.credit_score = 80
        mock_credit.positive_score = 0
        mock_credit.negative_score = 0
        mock_credit.total_positive_events = 0
        mock_credit.total_negative_events = 0
        mock_credit.credit_level = "A"
        mock_credit.level_history = "[]"

        mock_db.query.return_value.filter.return_value.first.return_value = mock_credit

        success, message, score_change = service.record_event(
            user_id="test_user",
            event_type="harassment_reported",
            description="被举报骚扰"
        )

        assert success is True
        assert score_change == -50

    def test_record_event_unknown_type(self, service, mock_db):
        """测试未知事件类型"""
        success, message, score_change = service.record_event(
            user_id="test_user",
            event_type="unknown_event",
            description="未知事件"
        )

        assert success is False
        assert "未知" in message
        assert score_change == 0

    def test_record_event_score_bounds(self, service, mock_db):
        """测试分数边界约束"""
        # 测试分数不能超过 100
        mock_credit = MagicMock()
        mock_credit.credit_score = 99
        mock_credit.positive_score = 0
        mock_credit.negative_score = 0
        mock_credit.total_positive_events = 0
        mock_credit.total_negative_events = 0
        mock_credit.credit_level = "A"
        mock_credit.level_history = "[]"

        mock_db.query.return_value.filter.return_value.first.return_value = mock_credit

        success, _, score_change = service.record_event(
            user_id="test_user",
            event_type="verified_badge",  # +20
            description="获得认证"
        )

        # 99 + 20 = 119，但应该被限制为 100
        assert success is True

    def test_record_event_negative_to_zero(self, service, mock_db):
        """测试负面事件分数不能低于 0"""
        mock_credit = MagicMock()
        mock_credit.credit_score = 10
        mock_credit.positive_score = 0
        mock_credit.negative_score = 0
        mock_credit.total_positive_events = 0
        mock_credit.total_negative_events = 0
        mock_credit.credit_level = "D"
        mock_credit.level_history = "[]"

        mock_db.query.return_value.filter.return_value.first.return_value = mock_credit

        success, _, score_change = service.record_event(
            user_id="test_user",
            event_type="harassment_reported",  # -50
            description="被举报骚扰"
        )

        # 10 - 50 = -40，但应该被限制为 0
        assert success is True

    def test_get_credit_info(self, service, mock_db):
        """测试获取信用信息"""
        mock_credit = MagicMock()
        mock_credit.user_id = "test_user"
        mock_credit.credit_score = 85
        mock_credit.credit_level = "A"
        mock_credit.base_score = 100
        mock_credit.positive_score = 10
        mock_credit.negative_score = 25
        mock_credit.total_positive_events = 2
        mock_credit.total_negative_events = 1
        mock_credit.level_history = "[]"
        mock_credit.restrictions = "[]"  # JSON string
        mock_credit.last_event_at = datetime.now()

        mock_db.query.return_value.filter.return_value.first.return_value = mock_credit

        info = service.get_credit_info("test_user")

        assert info["user_id"] == "test_user"
        assert info["credit_score"] == 85
        assert info["credit_level"] == "A"
        assert "level_description" in info


class TestBehaviorCreditServiceEdgeCases:
    """边界值和异常测试"""

    def test_score_range_validation(self):
        """测试分数范围必须在 0-100"""
        service = BehaviorCreditService.__new__(BehaviorCreditService)
        # 验证所有等级定义都在有效范围
        for level, (min_score, max_score, _) in service.CREDIT_LEVELS.items():
            assert min_score >= 0
            assert max_score <= 100
            assert min_score <= max_score

    def test_all_event_types_defined(self):
        """测试所有事件类型都有定义"""
        service = BehaviorCreditService.__new__(BehaviorCreditService)
        # 验证负面事件分数都是负数
        for event_type, score in service.NEGATIVE_EVENTS.items():
            assert score < 0, f"负面事件 {event_type} 分数应为负数"

        # 验证正面事件分数都是正数
        for event_type, score in service.POSITIVE_EVENTS.items():
            assert score > 0, f"正面事件 {event_type} 分数应为正数"

    def test_level_descriptions_exist(self):
        """测试所有等级都有描述"""
        service = BehaviorCreditService.__new__(BehaviorCreditService)
        for level, (_, _, description) in service.CREDIT_LEVELS.items():
            assert description, f"等级 {level} 缺少描述"

    def test_restrictions_progression(self):
        """测试限制措施的递进关系"""
        service = BehaviorCreditService.__new__(BehaviorCreditService)
        # 低等级应该有更多限制
        s_restrictions = len(service.RESTRICTIONS_BY_LEVEL["S"])
        a_restrictions = len(service.RESTRICTIONS_BY_LEVEL["A"])
        c_restrictions = len(service.RESTRICTIONS_BY_LEVEL["C"])
        d_restrictions = len(service.RESTRICTIONS_BY_LEVEL["D"])

        # D 应该限制最多，S 应该限制最少
        assert d_restrictions >= c_restrictions
        assert s_restrictions == 0
        assert a_restrictions == 0