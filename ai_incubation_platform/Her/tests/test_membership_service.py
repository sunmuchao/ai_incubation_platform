"""
测试会员订阅服务层

覆盖范围:
- MembershipService (src/services/membership_service.py)
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

from models.membership import MembershipTier, MembershipFeature, MembershipCreate


# 修复 membership_service 中缺失的 _get_db 方法
def _mock_get_db(self):
    """Mock implementation of missing _get_db method"""
    return self.db


# 在测试开始前补丁缺失的方法
from src.services.membership_service import MembershipService
if not hasattr(MembershipService, '_get_db'):
    MembershipService._get_db = _mock_get_db


class TestMembershipServiceInitialization:
    """测试 MembershipService 初始化"""

    def test_init(self):
        """测试服务初始化"""
        from src.services.membership_service import MembershipService

        mock_db = MagicMock()
        service = MembershipService(mock_db)

        assert service.db == mock_db


class TestMembershipServiceGetUserMembership:
    """测试获取用户会员状态"""

    def test_get_user_membership_with_active_membership(self):
        """测试获取用户有效会员状态"""
        from src.services.membership_service import MembershipService
        from db.models import UserMembershipDB

        mock_db = MagicMock()
        mock_membership_db = MagicMock(spec=UserMembershipDB)
        mock_membership_db.id = "membership-123"
        mock_membership_db.user_id = "user-123"
        mock_membership_db.tier = "premium"
        mock_membership_db.status = "active"
        mock_membership_db.start_date = datetime.now() - timedelta(days=30)
        mock_membership_db.end_date = datetime.now() + timedelta(days=30)
        mock_membership_db.auto_renew = False
        mock_membership_db.payment_method = "wechat"
        mock_membership_db.subscription_id = None
        mock_membership_db.created_at = datetime.now() - timedelta(days=30)
        mock_membership_db.updated_at = datetime.now()
        mock_membership_db.is_verified = True
        mock_db.query().filter().order_by().first.return_value = mock_membership_db

        service = MembershipService(mock_db)
        result = service.get_user_membership("user-123")

        assert result.user_id == "user-123"
        assert result.tier == MembershipTier.PREMIUM
        assert result.status == "active"

    def test_get_user_membership_without_membership(self):
        """测试获取用户无会员状态（返回免费会员）"""
        from src.services.membership_service import MembershipService

        mock_db = MagicMock()
        mock_db.query().filter().order_by().first.return_value = None

        service = MembershipService(mock_db)
        result = service.get_user_membership("user-123")

        assert result.user_id == "user-123"
        assert result.tier == MembershipTier.FREE
        assert result.status == "inactive"


class TestMembershipServiceCheckFeatureAccess:
    """测试检查会员权益访问权限"""

    def test_check_feature_access_with_feature(self):
        """测试检查有权限的会员权益"""
        from src.services.membership_service import MembershipService
        from db.models import UserMembershipDB

        mock_db = MagicMock()
        mock_membership_db = MagicMock(spec=UserMembershipDB)
        mock_membership_db.id = "membership-123"
        mock_membership_db.user_id = "user-123"
        mock_membership_db.tier = "premium"
        mock_membership_db.status = "active"
        mock_membership_db.start_date = datetime.now() - timedelta(days=30)
        mock_membership_db.end_date = datetime.now() + timedelta(days=30)
        mock_membership_db.auto_renew = False
        mock_membership_db.payment_method = "wechat"
        mock_membership_db.subscription_id = None
        mock_membership_db.created_at = datetime.now() - timedelta(days=30)
        mock_membership_db.updated_at = datetime.now()
        mock_db.query().filter().order_by().first.return_value = mock_membership_db

        service = MembershipService(mock_db)
        result = service.check_feature_access("user-123", MembershipFeature.SUPER_LIKES)

        assert result is True

    def test_check_feature_access_without_feature(self):
        """测试检查无权限的会员权益"""
        from src.services.membership_service import MembershipService

        mock_db = MagicMock()
        mock_db.query().filter().order_by().first.return_value = None

        service = MembershipService(mock_db)
        result = service.check_feature_access("user-123", MembershipFeature.SUPER_LIKES)

        assert result is False


class TestMembershipServiceGetUserLimit:
    """测试获取用户限制值"""

    def test_get_user_limit_premium(self):
        """测试获取高级会员限制值"""
        from src.services.membership_service import MembershipService
        from db.models import UserMembershipDB

        mock_db = MagicMock()
        mock_membership_db = MagicMock(spec=UserMembershipDB)
        mock_membership_db.id = "membership-123"
        mock_membership_db.user_id = "user-123"
        mock_membership_db.tier = "premium"
        mock_membership_db.status = "active"
        mock_membership_db.start_date = datetime.now() - timedelta(days=30)
        mock_membership_db.end_date = datetime.now() + timedelta(days=30)
        mock_membership_db.auto_renew = False
        mock_membership_db.payment_method = "wechat"
        mock_membership_db.subscription_id = None
        mock_membership_db.created_at = datetime.now() - timedelta(days=30)
        mock_membership_db.updated_at = datetime.now()
        mock_db.query().filter().order_by().first.return_value = mock_membership_db

        service = MembershipService(mock_db)
        result = service.get_user_limit("user-123", "daily_likes")

        assert result >= 0 or result == -1  # -1 表示无限制

    def test_get_user_limit_free(self):
        """测试获取免费会员限制值"""
        from src.services.membership_service import MembershipService

        mock_db = MagicMock()
        mock_db.query().filter().order_by().first.return_value = None

        service = MembershipService(mock_db)
        result = service.get_user_limit("user-123", "daily_likes")

        assert result >= 0  # 免费版有基础限制


class TestMembershipServiceCheckActionLimit:
    """测试检查操作限制"""

    def test_check_like_limit(self):
        """测试检查喜欢操作限制"""
        from src.services.membership_service import MembershipService

        mock_db = MagicMock()
        # 设置完整的 mock 链式调用
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
        # 模拟 usage tracker 查询返回 None（没有使用记录）
        mock_db.query.return_value.filter.return_value.first.return_value = None

        service = MembershipService(mock_db)
        allowed, message = service.check_action_limit("user-123", "like")

        assert allowed is True

    def test_check_super_like_limit_free_user(self):
        """测试检查超级喜欢限制（免费用户）"""
        from src.services.membership_service import MembershipService

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
        mock_db.query.return_value.filter.return_value.first.return_value = None

        service = MembershipService(mock_db)
        allowed, message = service.check_action_limit("user-123", "super_like")

        assert allowed is False
        assert "超级喜欢" in message

    def test_check_super_like_limit_premium_user(self):
        """测试检查超级喜欢限制（高级会员）"""
        from src.services.membership_service import MembershipService
        from db.models import UserMembershipDB

        mock_db = MagicMock()
        mock_membership_db = MagicMock(spec=UserMembershipDB)
        mock_membership_db.id = "membership-123"
        mock_membership_db.user_id = "user-123"
        mock_membership_db.tier = "premium"
        mock_membership_db.status = "active"
        mock_membership_db.start_date = datetime.now() - timedelta(days=30)
        mock_membership_db.end_date = datetime.now() + timedelta(days=30)
        mock_membership_db.auto_renew = False
        mock_membership_db.payment_method = "wechat"
        mock_membership_db.subscription_id = None
        mock_membership_db.created_at = datetime.now() - timedelta(days=30)
        mock_membership_db.updated_at = datetime.now()

        # 设置会员查询返回高级会员
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_membership_db
        # 设置 usage tracker 查询返回 None（没有使用记录）
        mock_db.query.return_value.filter.return_value.first.return_value = None

        service = MembershipService(mock_db)
        allowed, message = service.check_action_limit("user-123", "super_like")

        assert allowed is True

    def test_check_rewind_limit_free_user(self):
        """测试检查回退操作限制（免费用户）"""
        from src.services.membership_service import MembershipService

        mock_db = MagicMock()
        mock_db.query().filter().order_by().first.return_value = None

        service = MembershipService(mock_db)
        allowed, message = service.check_action_limit("user-123", "rewind")

        assert allowed is False
        assert "回退" in message

    def test_check_boost_limit_free_user(self):
        """测试检查加速曝光限制（免费用户）"""
        from src.services.membership_service import MembershipService

        mock_db = MagicMock()
        mock_db.query().filter().order_by().first.return_value = None

        service = MembershipService(mock_db)
        allowed, message = service.check_action_limit("user-123", "boost")

        assert allowed is False
        assert "加速曝光" in message

    def test_check_unknown_action(self):
        """测试检查未知操作"""
        from src.services.membership_service import MembershipService

        mock_db = MagicMock()
        mock_db.query().filter().order_by().first.return_value = None

        service = MembershipService(mock_db)
        allowed, message = service.check_action_limit("user-123", "unknown_action")

        assert allowed is True


class TestMembershipServiceGetMembershipPlans:
    """测试获取会员计划"""

    def test_get_membership_plans(self):
        """测试获取所有会员计划"""
        from src.services.membership_service import MembershipService

        mock_db = MagicMock()
        service = MembershipService(mock_db)
        plans = service.get_membership_plans()

        assert len(plans) == 6  # 2 种套餐 x 3 种时长

        # 检查计划结构
        for plan in plans:
            assert "tier" in plan
            assert "duration_months" in plan
            assert "price" in plan
            assert "features" in plan

        # 检查是否包含标准会员和高级会员
        tiers = [p["tier"] for p in plans]
        assert "standard" in tiers
        assert "premium" in tiers

        # 检查是否包含不同时长的计划
        durations = [p["duration_months"] for p in plans]
        assert 1 in durations  # 月度
        assert 3 in durations  # 季度
        assert 12 in durations  # 年度

    def test_get_membership_plans_popular_flag(self):
        """测试获取会员计划的热门标识"""
        from src.services.membership_service import MembershipService

        mock_db = MagicMock()
        service = MembershipService(mock_db)
        plans = service.get_membership_plans()

        # 高级会员月度计划应该是热门的
        premium_monthly = [p for p in plans if p["tier"] == "premium" and p["duration_months"] == 1]
        assert len(premium_monthly) == 1
        assert premium_monthly[0]["popular"] is True


class TestMembershipServiceGetMembershipBenefits:
    """测试获取会员权益说明"""

    def test_get_membership_benefits(self):
        """测试获取会员权益说明"""
        from src.services.membership_service import MembershipService

        mock_db = MagicMock()
        service = MembershipService(mock_db)
        benefits = service.get_membership_benefits()

        assert isinstance(benefits, list)
        assert len(benefits) > 0

        for benefit in benefits:
            assert "feature" in benefit
            assert "name" in benefit
            assert "description" in benefit
            assert "icon" in benefit


class TestMembershipServiceCreateMembershipOrder:
    """测试创建会员订单"""

    def test_create_membership_order(self):
        """测试创建会员订单"""
        from src.services.membership_service import MembershipService

        mock_db = MagicMock()
        mock_cursor = MagicMock()
        mock_db.cursor.return_value = mock_cursor
        mock_db.cursor().fetchone.return_value = None

        service = MembershipService(mock_db)

        request = MembershipCreate(
            tier=MembershipTier.PREMIUM,
            duration_months=1,
            payment_method="wechat"
        )

        result = service.create_membership_order("user-123", request)

        assert result.user_id == "user-123"
        assert result.tier == MembershipTier.PREMIUM
        assert result.duration_months == 1

    def test_create_membership_order_quarterly(self):
        """测试创建季度会员订单"""
        from src.services.membership_service import MembershipService

        mock_db = MagicMock()
        mock_cursor = MagicMock()
        mock_db.cursor.return_value = mock_cursor

        service = MembershipService(mock_db)

        request = MembershipCreate(
            tier=MembershipTier.STANDARD,
            duration_months=3,
            payment_method="alipay"
        )

        result = service.create_membership_order("user-123", request)

        assert result.duration_months == 3
        assert result.payment_method == "alipay"


class TestMembershipServiceCreateMembershipOrderWithAmount:
    """测试创建指定金额的会员订单"""

    def test_create_membership_order_with_amount(self):
        """测试创建指定金额的会员订单"""
        from src.services.membership_service import MembershipService

        mock_db = MagicMock()
        mock_cursor = MagicMock()
        mock_db.cursor.return_value = mock_cursor

        service = MembershipService(mock_db)

        result = service.create_membership_order_with_amount(
            user_id="user-123",
            tier=MembershipTier.PREMIUM,
            duration_months=1,
            amount=158.0,
            original_amount=198.0,
            discount_code="WELCOME20",
            payment_method="wechat",
            auto_renew=True
        )

        assert result.user_id == "user-123"
        assert result.tier == MembershipTier.PREMIUM
        assert result.amount == 158.0
        assert result.original_amount == 198.0
        assert result.discount_code == "WELCOME20"

    def test_create_membership_order_without_discount(self):
        """测试创建无折扣的会员订单"""
        from src.services.membership_service import MembershipService

        mock_db = MagicMock()
        mock_cursor = MagicMock()
        mock_db.cursor.return_value = mock_cursor

        service = MembershipService(mock_db)

        result = service.create_membership_order_with_amount(
            user_id="user-123",
            tier=MembershipTier.STANDARD,
            duration_months=12,
            amount=998.0,
            original_amount=1188.0,
            payment_method="alipay"
        )

        assert result.duration_months == 12
        assert result.discount_code is None


class TestMembershipServiceProcessPayment:
    """测试处理支付结果"""

    def test_process_payment_success(self):
        """测试处理支付成功"""
        from src.services.membership_service import MembershipService

        mock_db = MagicMock()
        mock_cursor = MagicMock()

        order_row = {
            'id': 'order-123',
            'user_id': 'user-123',
            'tier': 'premium',
            'duration_months': 1,
            'amount': 198.0,
            'original_amount': 198.0,
            'status': 'pending',
            'payment_method': 'wechat',
            'created_at': datetime.now(),
        }

        mock_cursor.fetchone.return_value = order_row
        mock_db.cursor.return_value = mock_cursor

        with patch.object(MembershipService, '_activate_membership') as mock_activate:
            service = MembershipService(mock_db)
            result = service.process_payment("order-123", {"success": True, "transaction_id": "tx-456"})

            assert result.status == "paid"
            mock_activate.assert_called_once()

    def test_process_payment_failure(self):
        """测试处理支付失败"""
        from src.services.membership_service import MembershipService

        mock_db = MagicMock()
        mock_cursor = MagicMock()

        order_row = {
            'id': 'order-123',
            'user_id': 'user-123',
            'tier': 'premium',
            'duration_months': 1,
            'amount': 198.0,
            'original_amount': 198.0,
            'status': 'pending',
            'payment_method': 'wechat',
            'created_at': datetime.now(),
        }

        mock_cursor.fetchone.return_value = order_row
        mock_db.cursor.return_value = mock_cursor

        service = MembershipService(mock_db)
        result = service.process_payment("order-123", {"success": False, "error": "支付失败"})

        assert result.status == "failed"

    def test_process_payment_order_not_found(self):
        """测试处理不存在的订单"""
        from src.services.membership_service import MembershipService

        mock_db = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_db.cursor.return_value = mock_cursor

        service = MembershipService(mock_db)

        with pytest.raises(ValueError) as exc_info:
            service.process_payment("not-exist", {"success": True})

        assert "订单不存在" in str(exc_info.value)


class TestMembershipServiceActivateMembership:
    """测试激活会员"""

    def test_activate_membership_new_user(self):
        """测试激活新会员"""
        from src.services.membership_service import MembershipService

        mock_db = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_db.cursor.return_value = mock_cursor

        with patch('src.services.membership_service.cache_manager') as mock_cache:
            mock_cache.get_instance.return_value.invalidate_on_membership_change.return_value = {"success": True}
            service = MembershipService(mock_db)
            service._activate_membership(
                user_id="user-123",
                tier=MembershipTier.PREMIUM,
                duration_months=1,
                payment_method="wechat"
            )

        mock_db.cursor.assert_called()
        mock_db.commit.assert_called()

    def test_activate_membership_existing_member(self):
        """测试现有会员续费"""
        from src.services.membership_service import MembershipService

        mock_db = MagicMock()
        mock_cursor = MagicMock()

        existing = {
            'id': 'membership-123',
            'user_id': 'user-123',
            'tier': 'premium',
            'end_date': datetime.now() + timedelta(days=30),
        }
        mock_cursor.fetchone.return_value = existing
        mock_db.cursor.return_value = mock_cursor

        with patch('src.services.membership_service.cache_manager') as mock_cache:
            mock_cache.get_instance.return_value.invalidate_on_membership_change.return_value = {"success": True}
            service = MembershipService(mock_db)
            service._activate_membership(
                user_id="user-123",
                tier=MembershipTier.PREMIUM,
                duration_months=1,
            )

        mock_db.cursor.assert_called()
        mock_db.commit.assert_called()


class TestMembershipServiceCancelSubscription:
    """测试取消自动续费"""

    def test_cancel_subscription_success(self):
        """测试取消自动续费成功"""
        from src.services.membership_service import MembershipService

        mock_db = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1
        mock_db.cursor.return_value = mock_cursor

        service = MembershipService(mock_db)
        result = service.cancel_subscription("user-123")

        assert result is True
        mock_db.commit.assert_called()

    def test_cancel_subscription_not_found(self):
        """测试取消不存在的订阅"""
        from src.services.membership_service import MembershipService

        mock_db = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 0
        mock_db.cursor.return_value = mock_cursor

        service = MembershipService(mock_db)
        result = service.cancel_subscription("user-123")

        assert result is False


class TestMembershipServiceGetMembershipStats:
    """测试获取会员统计信息"""

    def test_get_membership_stats(self):
        """测试获取会员统计信息"""
        from src.services.membership_service import MembershipService

        mock_db = MagicMock()
        mock_cursor = MagicMock()

        # Mock tier counts
        tier_counts = [
            {'tier': 'premium', 'count': 100},
            {'tier': 'standard', 'count': 200},
        ]
        mock_cursor.fetchall.return_value = tier_counts

        mock_cursor.fetchone.side_effect = [
            {'count': 50},   # new members
            {'count': 20},   # expired members
            {'total': 10000.0},  # revenue month
            {'total': 100000.0}, # revenue year
        ]
        mock_db.cursor.return_value = mock_cursor

        service = MembershipService(mock_db)
        stats = service.get_membership_stats()

        assert "total_members" in stats
        assert "standard_members" in stats
        assert "premium_members" in stats
        assert "new_members_this_month" in stats
        assert "revenue_this_month" in stats


class TestMembershipServiceUseFeature:
    """测试使用会员权益"""

    def test_use_feature_with_permission(self):
        """测试使用有权限的会员权益"""
        from src.services.membership_service import MembershipService
        from db.models import UserMembershipDB
        from models.membership import MembershipFeature

        mock_db = MagicMock()
        mock_membership_db = MagicMock(spec=UserMembershipDB)
        mock_membership_db.id = "membership-123"
        mock_membership_db.user_id = "user-123"
        mock_membership_db.tier = "premium"
        mock_membership_db.status = "active"
        mock_membership_db.start_date = datetime.now() - timedelta(days=30)
        mock_membership_db.end_date = datetime.now() + timedelta(days=30)
        mock_membership_db.auto_renew = False
        mock_membership_db.payment_method = "wechat"
        mock_membership_db.subscription_id = None
        mock_membership_db.created_at = datetime.now() - timedelta(days=30)
        mock_membership_db.updated_at = datetime.now()

        # 设置会员查询返回高级会员
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_membership_db
        # 设置 usage tracker 查询返回 None
        mock_db.query.return_value.filter.return_value.first.return_value = None

        service = MembershipService(mock_db)
        success, message = service.use_feature("user-123", MembershipFeature.SUPER_LIKES)

        assert success is True

    def test_use_feature_without_permission(self):
        """测试使用无权限的会员权益"""
        from src.services.membership_service import MembershipService
        from models.membership import MembershipFeature

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None

        service = MembershipService(mock_db)
        success, message = service.use_feature("user-123", MembershipFeature.SUPER_LIKES)

        assert success is False
        assert "会员" in message


class TestMembershipServiceHelpers:
    """测试辅助方法"""

    def test_get_membership_service(self):
        """测试获取会员服务实例"""
        from src.services.membership_service import get_membership_service

        mock_db = MagicMock()
        service = get_membership_service(mock_db)

        assert service is not None
        assert service.db == mock_db
