"""
测试玫瑰表达服务层

覆盖范围:
- RoseService (src/services/rose_service.py)

测试策略:
- 使用 MagicMock 模拟数据库操作
- Mock MembershipService, UserRepository 等依赖服务
- 覆盖正常流程、边界条件和异常处理
"""
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime, timedelta

from models.rose import (
    RoseBalance,
    RoseSendRequest,
    RoseSendResponse,
    RoseSource,
    RoseStatus,
    StandoutProfile,
    StandoutListResponse,
    ROSE_ALLOCATION,
    ROSE_PACKAGES,
    UserRoseBalanceDB,
    RoseTransactionDB,
    RosePurchaseDB,
)
from models.membership import MembershipTier, UserMembership


class TestRoseServiceInitialization:
    """测试 RoseService 初始化"""

    def test_init(self):
        """测试服务初始化"""
        from src.services.rose_service import RoseService

        mock_db = MagicMock()
        service = RoseService(mock_db)

        assert service.db == mock_db


class TestRoseServiceGetUserBalance:
    """测试获取用户玫瑰余额"""

    def test_get_user_balance_existing_user(self):
        """测试获取已存在用户的玫瑰余额"""
        from src.services.rose_service import RoseService

        mock_db = MagicMock()
        mock_balance_db = MagicMock(spec=UserRoseBalanceDB)
        mock_balance_db.user_id = "user-123"
        mock_balance_db.available_count = 5
        mock_balance_db.sent_this_month = 2
        mock_balance_db.total_received_this_month = 7
        mock_db.query().filter().first.return_value = mock_balance_db

        service = RoseService(mock_db)
        result = service.get_user_balance("user-123")

        assert result.user_id == "user-123"
        assert result.available_count == 5
        assert result.sent_count == 2
        assert result.monthly_allocation == 7
        assert result.purchase_available is True

    def test_get_user_balance_new_user_free_tier(self):
        """测试获取新用户余额（免费会员）"""
        from src.services.rose_service import RoseService

        mock_db = MagicMock()
        mock_db.query().filter().first.return_value = None  # 无现有余额记录

        # Mock the newly created balance object
        mock_new_balance = MagicMock(spec=UserRoseBalanceDB)
        mock_new_balance.user_id = "new-user-123"
        mock_new_balance.available_count = 1
        mock_new_balance.sent_this_month = 0  # 新用户发送数为0
        mock_new_balance.total_received_this_month = 1

        # Mock MembershipService
        with patch('src.services.rose_service.MembershipService') as MockMembershipService:
            mock_membership_svc = MagicMock()
            mock_membership = MagicMock(spec=UserMembership)
            mock_membership.tier = MembershipTier.FREE
            mock_membership_svc.get_user_membership.return_value = mock_membership
            MockMembershipService.return_value = mock_membership_svc

            # Mock UserRoseBalanceDB creation to return our mocked object
            with patch('src.services.rose_service.UserRoseBalanceDB') as MockBalanceDB:
                MockBalanceDB.return_value = mock_new_balance

                service = RoseService(mock_db)
                result = service.get_user_balance("new-user-123")

                # 免费会员每月1个玫瑰
                assert result.user_id == "new-user-123"
                assert result.available_count == 1
                assert result.monthly_allocation == 1

    def test_get_user_balance_new_user_premium_tier(self):
        """测试获取新用户余额（高级会员）"""
        from src.services.rose_service import RoseService

        mock_db = MagicMock()
        mock_db.query().filter().first.return_value = None

        # Mock the newly created balance object
        mock_new_balance = MagicMock(spec=UserRoseBalanceDB)
        mock_new_balance.user_id = "premium-user-123"
        mock_new_balance.available_count = 5
        mock_new_balance.sent_this_month = 0  # 新用户发送数为0
        mock_new_balance.total_received_this_month = 5

        with patch('src.services.rose_service.MembershipService') as MockMembershipService:
            mock_membership_svc = MagicMock()
            mock_membership = MagicMock(spec=UserMembership)
            mock_membership.tier = MembershipTier.PREMIUM
            mock_membership_svc.get_user_membership.return_value = mock_membership
            MockMembershipService.return_value = mock_membership_svc

            # Mock UserRoseBalanceDB creation to return our mocked object
            with patch('src.services.rose_service.UserRoseBalanceDB') as MockBalanceDB:
                MockBalanceDB.return_value = mock_new_balance

                service = RoseService(mock_db)
                result = service.get_user_balance("premium-user-123")

                # 高级会员每月5个玫瑰
                assert result.available_count == 5
                assert result.monthly_allocation == 5


class TestRoseServiceSendRose:
    """测试发送玫瑰"""

    def test_send_rose_no_balance(self):
        """测试余额不足时发送玫瑰"""
        from src.services.rose_service import RoseService

        mock_db = MagicMock()

        # Mock balance with 0 available
        mock_balance_db = MagicMock(spec=UserRoseBalanceDB)
        mock_balance_db.available_count = 0
        mock_db.query().filter().first.return_value = mock_balance_db

        with patch('src.services.rose_service.MembershipService') as MockMembershipService:
            mock_membership_svc = MagicMock()
            mock_membership = MagicMock(spec=UserMembership)
            mock_membership.tier = MembershipTier.FREE
            mock_membership_svc.get_user_membership.return_value = mock_membership
            MockMembershipService.return_value = mock_membership_svc

            service = RoseService(mock_db)
            request = RoseSendRequest(target_user_id="target-user-123")
            result = service.send_rose("sender-123", request)

            assert result.success is False
            assert "没有可用的玫瑰" in result.message
            assert result.roses_remaining == 0

    def test_send_rose_target_user_not_exist(self):
        """测试目标用户不存在时发送玫瑰"""
        from src.services.rose_service import RoseService

        mock_db = MagicMock()

        # Mock balance with available roses
        mock_balance_db = MagicMock(spec=UserRoseBalanceDB)
        mock_balance_db.user_id = "sender-123"
        mock_balance_db.available_count = 3
        mock_balance_db.sent_this_month = 0
        mock_balance_db.total_received_this_month = 3
        mock_balance_db.free_allocation = 1
        mock_balance_db.membership_allocation = 2
        mock_balance_db.purchased_count = 0
        mock_balance_db.gifted_count = 0

        # Setup mock chain for balance query
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_filter.first.return_value = mock_balance_db
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query

        # Mock MembershipService
        with patch('src.services.rose_service.MembershipService') as MockMembershipService:
            mock_membership_svc = MagicMock()
            mock_membership = MagicMock(spec=UserMembership)
            mock_membership.tier = MembershipTier.STANDARD
            mock_membership_svc.get_user_membership.return_value = mock_membership
            MockMembershipService.return_value = mock_membership_svc

            # Mock UserRepository - target user not found
            with patch('src.services.rose_service.UserRepository') as MockUserRepository:
                mock_user_repo = MagicMock()
                mock_user_repo.get_by_id.return_value = None  # Target user not found
                MockUserRepository.return_value = mock_user_repo

                service = RoseService(mock_db)
                request = RoseSendRequest(target_user_id="non-existent-user")
                result = service.send_rose("sender-123", request)

                assert result.success is False
                assert "目标用户不存在" in result.message

    def test_send_rose_already_sent_to_same_user(self):
        """测试已向同一用户发送过玫瑰"""
        from src.services.rose_service import RoseService

        mock_db = MagicMock()

        # Mock balance
        mock_balance_db = MagicMock(spec=UserRoseBalanceDB)
        mock_balance_db.user_id = "sender-123"
        mock_balance_db.available_count = 3
        mock_balance_db.sent_this_month = 1
        mock_balance_db.total_received_this_month = 3
        mock_balance_db.free_allocation = 1
        mock_balance_db.membership_allocation = 2
        mock_balance_db.purchased_count = 0
        mock_balance_db.gifted_count = 0

        # Mock existing transaction (already sent)
        mock_existing_transaction = MagicMock(spec=RoseTransactionDB)
        mock_existing_transaction.sender_id = "sender-123"
        mock_existing_transaction.receiver_id = "target-123"
        mock_existing_transaction.status = RoseStatus.SENT.value

        # Setup complex mock chain
        mock_query = MagicMock()
        mock_filter1 = MagicMock()
        mock_filter2 = MagicMock()

        # First call returns balance, second call returns existing transaction
        call_count = [0]
        def mock_filter_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_filter1
            return mock_filter2

        mock_query.filter.side_effect = mock_filter_side_effect
        mock_filter1.first.return_value = mock_balance_db
        mock_filter2.first.return_value = mock_existing_transaction
        mock_db.query.return_value = mock_query

        with patch('src.services.rose_service.MembershipService') as MockMembershipService:
            mock_membership_svc = MagicMock()
            mock_membership = MagicMock(spec=UserMembership)
            mock_membership.tier = MembershipTier.STANDARD
            mock_membership_svc.get_user_membership.return_value = mock_membership
            MockMembershipService.return_value = mock_membership_svc

            service = RoseService(mock_db)
            request = RoseSendRequest(target_user_id="target-123")
            result = service.send_rose("sender-123", request)

            assert result.success is False
            assert "已经向该用户发送过玫瑰" in result.message

    def test_send_rose_success_with_match(self):
        """测试成功发送玫瑰并形成匹配（双向玫瑰）"""
        from src.services.rose_service import RoseService

        mock_db = MagicMock()

        # Mock sender user
        mock_sender_user = MagicMock()
        mock_sender_user.id = "sender-123"
        mock_sender_user.name = "发送者"
        mock_sender_user.age = 28
        mock_sender_user.avatar_url = None
        mock_sender_user.location = "北京"
        mock_sender_user.bio = ""
        mock_sender_user.interests = "[]"

        # Mock target user
        mock_target_user = MagicMock()
        mock_target_user.id = "target-123"
        mock_target_user.name = "接收者"
        mock_target_user.age = 26
        mock_target_user.avatar_url = None
        mock_target_user.location = "上海"
        mock_target_user.bio = ""
        mock_target_user.interests = "[]"

        # Mock balance
        mock_balance_db = MagicMock(spec=UserRoseBalanceDB)
        mock_balance_db.user_id = "sender-123"
        mock_balance_db.available_count = 3
        mock_balance_db.sent_this_month = 0
        mock_balance_db.total_received_this_month = 3
        mock_balance_db.free_allocation = 1
        mock_balance_db.membership_allocation = 2
        mock_balance_db.purchased_count = 0
        mock_balance_db.gifted_count = 0

        # Mock reverse transaction (target already sent rose to sender)
        mock_reverse_transaction = MagicMock(spec=RoseTransactionDB)
        mock_reverse_transaction.sender_id = "target-123"
        mock_reverse_transaction.receiver_id = "sender-123"
        mock_reverse_transaction.status = RoseStatus.SENT.value

        # Setup mock chain with multiple queries
        def create_mock_query_chain():
            mock_query = MagicMock()
            mock_filter = MagicMock()
            mock_order = MagicMock()
            mock_filter2 = MagicMock()

            # Track query calls
            call_returns = [
                mock_balance_db,  # get_user_balance balance query
                None,  # existing transaction check (no existing)
                mock_balance_db,  # balance query in send_rose
                mock_reverse_transaction,  # reverse transaction check (match!)
            ]
            call_count = [0]

            def first_side_effect():
                call_count[0] += 1
                if call_count[0] <= len(call_returns):
                    return call_returns[call_count[0] - 1]
                return None

            mock_filter.first.side_effect = first_side_effect
            mock_query.filter.return_value = mock_filter
            mock_filter.order_by.return_value = mock_order
            mock_order.first.return_value = mock_balance_db
            return mock_query

        mock_db.query.return_value = create_mock_query_chain()

        with patch('src.services.rose_service.MembershipService') as MockMembershipService:
            mock_membership_svc = MagicMock()
            mock_membership = MagicMock(spec=UserMembership)
            mock_membership.tier = MembershipTier.STANDARD
            mock_membership_svc.get_user_membership.return_value = mock_membership
            MockMembershipService.return_value = mock_membership_svc

            with patch('src.services.rose_service.UserRepository') as MockUserRepository:
                mock_user_repo = MagicMock()
                mock_user_repo.get_by_id.side_effect = [mock_target_user, mock_sender_user]
                MockUserRepository.return_value = mock_user_repo

                # Mock HerAdvisorService (新架构替代 matchmaker)
                with patch('services.her_advisor_service.get_her_advisor_service') as mock_her_advisor:
                    mock_advisor = MagicMock()
                    mock_advice = MagicMock()
                    mock_advice.compatibility_score = 0.85
                    mock_advisor.generate_match_advice.return_value = mock_advice
                    mock_her_advisor.return_value = mock_advisor

                    # Mock get_user_profile_service
                    with patch('services.user_profile_service.get_user_profile_service') as mock_profile:
                        mock_profile_svc = MagicMock()
                        mock_profile_svc.get_or_create_profile.return_value = (MagicMock(), MagicMock())
                        mock_profile.return_value = mock_profile_svc

                    # Mock _from_db
                    def mock_from_db(user):
                        mock_obj = MagicMock()
                        mock_obj.model_dump.return_value = {
                            "name": user.name,
                            "age": user.age,
                            "avatar_url": user.avatar_url,
                            "location": user.location,
                            "bio": user.bio,
                            "interests": [],
                        }
                        return mock_obj

                    with patch('api.users._from_db', side_effect=mock_from_db):
                        service = RoseService(mock_db)
                        request = RoseSendRequest(target_user_id="target-123", message="你好")
                        result = service.send_rose("sender-123", request)

                        assert result.success is True
                        assert "玫瑰已发送" in result.message
                        assert result.is_match is True
                        assert result.transaction_id is not None

    def test_send_rose_success_no_match(self):
        """测试成功发送玫瑰（无匹配）"""
        from src.services.rose_service import RoseService

        mock_db = MagicMock()

        mock_target_user = MagicMock()
        mock_target_user.id = "target-123"
        mock_target_user.name = "接收者"

        mock_sender_user = MagicMock()
        mock_sender_user.id = "sender-123"
        mock_sender_user.name = "发送者"

        mock_balance_db = MagicMock(spec=UserRoseBalanceDB)
        mock_balance_db.user_id = "sender-123"
        mock_balance_db.available_count = 3
        mock_balance_db.sent_this_month = 0
        mock_balance_db.total_received_this_month = 3
        mock_balance_db.free_allocation = 1
        mock_balance_db.membership_allocation = 2
        mock_balance_db.purchased_count = 0
        mock_balance_db.gifted_count = 0

        def create_mock_query_chain():
            mock_query = MagicMock()
            mock_filter = MagicMock()
            call_returns = [
                mock_balance_db,  # balance
                None,  # no existing transaction
                mock_balance_db,  # balance in send_rose
                None,  # no reverse transaction (no match)
            ]
            call_count = [0]

            def first_side_effect():
                call_count[0] += 1
                if call_count[0] <= len(call_returns):
                    return call_returns[call_count[0] - 1]
                return None

            mock_filter.first.side_effect = first_side_effect
            mock_query.filter.return_value = mock_filter
            return mock_query

        mock_db.query.return_value = create_mock_query_chain()

        with patch('src.services.rose_service.MembershipService') as MockMembershipService:
            mock_membership_svc = MagicMock()
            mock_membership = MagicMock(spec=UserMembership)
            mock_membership.tier = MembershipTier.STANDARD
            mock_membership_svc.get_user_membership.return_value = mock_membership
            MockMembershipService.return_value = mock_membership_svc

            with patch('src.services.rose_service.UserRepository') as MockUserRepository:
                mock_user_repo = MagicMock()
                mock_user_repo.get_by_id.side_effect = [mock_target_user, mock_sender_user]
                MockUserRepository.return_value = mock_user_repo

                # Mock HerAdvisorService (新架构替代 matchmaker)
                with patch('services.her_advisor_service.get_her_advisor_service') as mock_her_advisor:
                    mock_advisor = MagicMock()
                    mock_advice = MagicMock()
                    mock_advice.compatibility_score = 0.7
                    mock_advisor.generate_match_advice.return_value = mock_advice
                    mock_her_advisor.return_value = mock_advisor

                    # Mock get_user_profile_service
                    with patch('services.user_profile_service.get_user_profile_service') as mock_profile:
                        mock_profile_svc = MagicMock()
                        mock_profile_svc.get_or_create_profile.return_value = (MagicMock(), MagicMock())
                        mock_profile.return_value = mock_profile_svc

                    def mock_from_db(user):
                        mock_obj = MagicMock()
                        mock_obj.model_dump.return_value = {
                            "name": user.name,
                            "age": 25,
                            "avatar_url": None,
                            "location": "北京",
                            "bio": "",
                            "interests": [],
                        }
                        return mock_obj

                    with patch('api.users._from_db', side_effect=mock_from_db):
                        service = RoseService(mock_db)
                        request = RoseSendRequest(target_user_id="target-123")
                        result = service.send_rose("sender-123", request)

                        assert result.success is True
                        assert result.is_match is False


class TestRoseServiceDetermineRoseSource:
    """测试确定玫瑰来源"""

    def test_determine_rose_source_free_first(self):
        """测试优先使用免费玫瑰"""
        from src.services.rose_service import RoseService

        mock_db = MagicMock()
        mock_balance_db = MagicMock(spec=UserRoseBalanceDB)
        mock_balance_db.free_allocation = 2
        mock_balance_db.membership_allocation = 3
        mock_balance_db.purchased_count = 1
        mock_balance_db.gifted_count = 1

        service = RoseService(mock_db)
        result = service._determine_rose_source(mock_balance_db)

        assert result == RoseSource.FREE_MONTHLY
        assert mock_balance_db.free_allocation == 1  # 应减少

    def test_determine_rose_source_membership_when_free_zero(self):
        """测试免费玫瑰用完后使用会员玫瑰"""
        from src.services.rose_service import RoseService

        mock_db = MagicMock()
        mock_balance_db = MagicMock(spec=UserRoseBalanceDB)
        mock_balance_db.free_allocation = 0
        mock_balance_db.membership_allocation = 2
        mock_balance_db.purchased_count = 1
        mock_balance_db.gifted_count = 1

        service = RoseService(mock_db)
        result = service._determine_rose_source(mock_balance_db)

        assert result == RoseSource.MEMBERSHIP_STANDARD
        assert mock_balance_db.membership_allocation == 1

    def test_determine_rose_source_purchased_when_others_zero(self):
        """测试其他来源用完后使用购买玫瑰"""
        from src.services.rose_service import RoseService

        mock_db = MagicMock()
        mock_balance_db = MagicMock(spec=UserRoseBalanceDB)
        mock_balance_db.free_allocation = 0
        mock_balance_db.membership_allocation = 0
        mock_balance_db.purchased_count = 2
        mock_balance_db.gifted_count = 0

        service = RoseService(mock_db)
        result = service._determine_rose_source(mock_balance_db)

        assert result == RoseSource.PURCHASED
        assert mock_balance_db.purchased_count == 1

    def test_determine_rose_source_gift_last(self):
        """测试最后使用赠送玫瑰"""
        from src.services.rose_service import RoseService

        mock_db = MagicMock()
        mock_balance_db = MagicMock(spec=UserRoseBalanceDB)
        mock_balance_db.free_allocation = 0
        mock_balance_db.membership_allocation = 0
        mock_balance_db.purchased_count = 0
        mock_balance_db.gifted_count = 1

        service = RoseService(mock_db)
        result = service._determine_rose_source(mock_balance_db)

        assert result == RoseSource.GIFT
        assert mock_balance_db.gifted_count == 0

    def test_determine_rose_source_default_when_all_zero(self):
        """测试所有来源都为0时默认返回免费"""
        from src.services.rose_service import RoseService

        mock_db = MagicMock()
        mock_balance_db = MagicMock(spec=UserRoseBalanceDB)
        mock_balance_db.free_allocation = 0
        mock_balance_db.membership_allocation = 0
        mock_balance_db.purchased_count = 0
        mock_balance_db.gifted_count = 0

        service = RoseService(mock_db)
        result = service._determine_rose_source(mock_balance_db)

        assert result == RoseSource.FREE_MONTHLY


class TestRoseServiceGetStandoutList:
    """测试获取 Standout 列表"""

    def test_get_standout_list_empty(self):
        """测试获取空 Standout 列表"""
        from src.services.rose_service import RoseService

        mock_db = MagicMock()
        mock_db.query().filter().order_by().all.return_value = []

        service = RoseService(mock_db)
        result = service.get_standout_list("user-123")

        assert result.total_count == 0
        assert result.unread_count == 0
        assert len(result.profiles) == 0

    def test_get_standout_list_with_roses(self):
        """测试获取包含玫瑰的 Standout 列表"""
        from src.services.rose_service import RoseService

        mock_db = MagicMock()

        # Mock rose transaction
        mock_rose1 = MagicMock(spec=RoseTransactionDB)
        mock_rose1.sender_id = "sender-123"
        mock_rose1.sent_at = datetime.now() - timedelta(hours=2)
        mock_rose1.message = "你好"
        mock_rose1.compatibility_score = 0.85
        mock_rose1.standout_expires_at = datetime.now() + timedelta(hours=22)
        mock_rose1.is_seen = False

        mock_rose2 = MagicMock(spec=RoseTransactionDB)
        mock_rose2.sender_id = "sender-456"
        mock_rose2.sent_at = datetime.now() - timedelta(hours=5)
        mock_rose2.message = None
        mock_rose2.compatibility_score = 0.72
        mock_rose2.standout_expires_at = datetime.now() + timedelta(hours=19)
        mock_rose2.is_seen = True

        mock_db.query().filter().order_by().all.return_value = [mock_rose1, mock_rose2]

        # Mock sender users
        mock_sender1 = MagicMock()
        mock_sender1.id = "sender-123"
        mock_sender1.name = "发送者1"
        mock_sender1.age = 28
        mock_sender1.avatar_url = "avatar1.jpg"
        mock_sender1.location = "北京"
        mock_sender1.bio = "测试用户"
        mock_sender1.interests = "[]"

        mock_sender2 = MagicMock()
        mock_sender2.id = "sender-456"
        mock_sender2.name = "发送者2"
        mock_sender2.age = 30
        mock_sender2.avatar_url = None
        mock_sender2.location = "上海"
        mock_sender2.bio = ""
        mock_sender2.interests = "[]"

        with patch('src.services.rose_service.UserRepository') as MockUserRepository:
            mock_user_repo = MagicMock()
            mock_user_repo.get_by_id.side_effect = [mock_sender1, mock_sender2]
            MockUserRepository.return_value = mock_user_repo

            def mock_from_db(user):
                mock_obj = MagicMock()
                mock_obj.name = user.name
                mock_obj.age = user.age
                mock_obj.avatar_url = user.avatar_url
                mock_obj.location = user.location
                mock_obj.bio = user.bio
                mock_obj.interests = []
                return mock_obj

            with patch('api.users._from_db', side_effect=mock_from_db):
                service = RoseService(mock_db)
                result = service.get_standout_list("user-123")

                assert result.total_count == 2
                assert result.unread_count == 1  # only rose1 is unseen
                assert len(result.profiles) == 2
                assert result.profiles[0].user_id == "sender-123"

    def test_get_standout_list_sender_not_found(self):
        """测试发送者不存在时跳过"""
        from src.services.rose_service import RoseService

        mock_db = MagicMock()

        mock_rose = MagicMock(spec=RoseTransactionDB)
        mock_rose.sender_id = "deleted-user"
        mock_rose.sent_at = datetime.now()
        mock_rose.is_seen = False

        mock_db.query().filter().order_by().all.return_value = [mock_rose]

        with patch('src.services.rose_service.UserRepository') as MockUserRepository:
            mock_user_repo = MagicMock()
            mock_user_repo.get_by_id.return_value = None  # Sender deleted
            MockUserRepository.return_value = mock_user_repo

            service = RoseService(mock_db)
            result = service.get_standout_list("user-123")

            assert result.total_count == 0


class TestRoseServiceMarkRoseSeen:
    """测试标记玫瑰已查看"""

    def test_mark_rose_seen_success(self):
        """测试成功标记玫瑰已查看"""
        from src.services.rose_service import RoseService

        mock_db = MagicMock()
        mock_transaction = MagicMock(spec=RoseTransactionDB)
        mock_transaction.id = "transaction-123"
        mock_transaction.is_seen = False

        mock_db.query().filter().first.return_value = mock_transaction

        service = RoseService(mock_db)
        result = service.mark_rose_seen("transaction-123")

        assert result is True
        assert mock_transaction.is_seen is True
        assert mock_transaction.seen_at is not None

    def test_mark_rose_seen_not_found(self):
        """测试标记不存在的玫瑰"""
        from src.services.rose_service import RoseService

        mock_db = MagicMock()
        mock_db.query().filter().first.return_value = None

        service = RoseService(mock_db)
        result = service.mark_rose_seen("non-existent-id")

        assert result is False


class TestRoseServiceRespondToStandout:
    """测试回应 Standout 用户"""

    def test_respond_to_standout_like(self):
        """测试喜欢 Standout 用户"""
        from src.services.rose_service import RoseService

        mock_db = MagicMock()

        mock_rose = MagicMock(spec=RoseTransactionDB)
        mock_rose.sender_id = "standout-user-123"
        mock_rose.receiver_id = "user-123"
        mock_rose.status = RoseStatus.SENT.value
        mock_rose.compatibility_score = 0.8
        mock_rose.is_seen = False

        mock_db.query().filter().first.return_value = mock_rose

        service = RoseService(mock_db)
        success, message = service.respond_to_standout("user-123", "standout-user-123", "like")

        assert success is True
        assert "匹配成功" in message
        assert mock_rose.is_seen is True
        assert mock_rose.status == "matched"

    def test_respond_to_standout_pass(self):
        """测试无感 Standout 用户"""
        from src.services.rose_service import RoseService

        mock_db = MagicMock()

        mock_rose = MagicMock(spec=RoseTransactionDB)
        mock_rose.sender_id = "standout-user-123"
        mock_rose.receiver_id = "user-123"
        mock_rose.status = RoseStatus.SENT.value
        mock_rose.in_standout = True
        mock_rose.is_seen = False

        mock_db.query().filter().first.return_value = mock_rose

        service = RoseService(mock_db)
        success, message = service.respond_to_standout("user-123", "standout-user-123", "pass")

        assert success is True
        assert "已移除" in message
        assert mock_rose.in_standout is False

    def test_respond_to_standout_rose_not_found(self):
        """测试玫瑰记录不存在"""
        from src.services.rose_service import RoseService

        mock_db = MagicMock()
        mock_db.query().filter().first.return_value = None

        service = RoseService(mock_db)
        success, message = service.respond_to_standout("user-123", "standout-user-123", "like")

        assert success is False
        assert "未找到" in message

    def test_respond_to_standout_invalid_action(self):
        """测试无效操作"""
        from src.services.rose_service import RoseService

        mock_db = MagicMock()

        mock_rose = MagicMock(spec=RoseTransactionDB)
        mock_db.query().filter().first.return_value = mock_rose

        service = RoseService(mock_db)
        success, message = service.respond_to_standout("user-123", "standout-user-123", "invalid")

        assert success is False
        assert "无效操作" in message


class TestRoseServicePurchaseRoses:
    """测试购买玫瑰"""

    def test_purchase_roses_single_package(self):
        """测试购买单个玫瑰套餐"""
        from src.services.rose_service import RoseService

        mock_db = MagicMock()

        service = RoseService(mock_db)
        success, message, purchase = service.purchase_roses("user-123", "single", "wechat")

        assert success is True
        assert "购买订单已创建" in message
        assert purchase is not None
        assert purchase.package_type == "single"
        assert purchase.rose_count == 1
        assert purchase.amount == 30
        assert purchase.payment_method == "wechat"
        assert purchase.payment_status == "pending"

    def test_purchase_roses_bundle_3_package(self):
        """测试购买3个玫瑰套餐"""
        from src.services.rose_service import RoseService

        mock_db = MagicMock()

        service = RoseService(mock_db)
        success, message, purchase = service.purchase_roses("user-123", "bundle_3", "alipay")

        assert success is True
        assert purchase.rose_count == 3
        assert purchase.amount == 78

    def test_purchase_roses_bundle_5_package(self):
        """测试购买5个玫瑰套餐"""
        from src.services.rose_service import RoseService

        mock_db = MagicMock()

        service = RoseService(mock_db)
        success, message, purchase = service.purchase_roses("user-123", "bundle_5")

        assert success is True
        assert purchase.rose_count == 5
        assert purchase.amount == 120

    def test_purchase_roses_invalid_package(self):
        """测试无效套餐类型"""
        from src.services.rose_service import RoseService

        mock_db = MagicMock()

        service = RoseService(mock_db)
        success, message, purchase = service.purchase_roses("user-123", "invalid_package")

        assert success is False
        assert "无效的套餐类型" in message
        assert purchase is None


class TestRoseServiceCompletePurchase:
    """测试完成购买"""

    def test_complete_purchase_with_existing_balance(self):
        """测试完成购买（已有余额记录）"""
        from src.services.rose_service import RoseService

        mock_db = MagicMock()

        mock_purchase = MagicMock(spec=RosePurchaseDB)
        mock_purchase.id = "purchase-123"
        mock_purchase.user_id = "user-123"
        mock_purchase.rose_count = 3
        mock_purchase.payment_status = "pending"

        mock_balance = MagicMock(spec=UserRoseBalanceDB)
        mock_balance.user_id = "user-123"
        mock_balance.available_count = 5
        mock_balance.purchased_count = 0
        mock_balance.total_received_this_month = 5

        # Setup mock chain
        call_count = [0]
        def first_side_effect():
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_purchase
            return mock_balance

        mock_db.query().filter().first.side_effect = first_side_effect

        service = RoseService(mock_db)
        result = service.complete_purchase("purchase-123")

        assert result is True
        assert mock_purchase.payment_status == "paid"
        assert mock_purchase.payment_time is not None
        assert mock_balance.available_count == 8  # 5 + 3
        assert mock_balance.purchased_count == 3

    def test_complete_purchase_without_balance(self):
        """测试完成购买（无余额记录，创建新记录）"""
        from src.services.rose_service import RoseService

        mock_db = MagicMock()

        mock_purchase = MagicMock(spec=RosePurchaseDB)
        mock_purchase.id = "purchase-123"
        mock_purchase.user_id = "new-user-123"
        mock_purchase.rose_count = 5
        mock_purchase.payment_status = "pending"

        # First call returns purchase, second returns None (no balance)
        call_count = [0]
        def first_side_effect():
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_purchase
            return None

        mock_db.query().filter().first.side_effect = first_side_effect

        service = RoseService(mock_db)
        result = service.complete_purchase("purchase-123")

        assert result is True
        assert mock_purchase.payment_status == "paid"

    def test_complete_purchase_not_found(self):
        """测试购买记录不存在"""
        from src.services.rose_service import RoseService

        mock_db = MagicMock()
        mock_db.query().filter().first.return_value = None

        service = RoseService(mock_db)
        result = service.complete_purchase("non-existent-purchase")

        assert result is False


class TestRoseServiceRefreshMonthlyRoses:
    """测试刷新月度玫瑰"""

    def test_refresh_monthly_roses_with_users(self):
        """测试刷新多个用户的月度玫瑰"""
        from src.services.rose_service import RoseService

        mock_db = MagicMock()

        mock_balance1 = MagicMock(spec=UserRoseBalanceDB)
        mock_balance1.user_id = "user-123"
        mock_balance1.available_count = 0  # used all roses

        mock_balance2 = MagicMock(spec=UserRoseBalanceDB)
        mock_balance2.user_id = "user-456"
        mock_balance2.available_count = 2

        mock_db.query().all.return_value = [mock_balance1, mock_balance2]

        with patch('src.services.rose_service.MembershipService') as MockMembershipService:
            mock_membership_svc = MagicMock()

            # Return different membership tiers
            def get_membership_side_effect(user_id):
                mock_membership = MagicMock(spec=UserMembership)
                if user_id == "user-123":
                    mock_membership.tier = MembershipTier.PREMIUM
                else:
                    mock_membership.tier = MembershipTier.FREE
                return mock_membership

            mock_membership_svc.get_user_membership.side_effect = get_membership_side_effect
            MockMembershipService.return_value = mock_membership_svc

            service = RoseService(mock_db)
            result = service.refresh_monthly_roses()

            assert result == 2
            # Premium user gets 5 roses
            assert mock_balance1.available_count == 5
            # Free user gets 1 rose
            assert mock_balance2.available_count == 1

    def test_refresh_monthly_roses_no_users(self):
        """测试无用户时刷新"""
        from src.services.rose_service import RoseService

        mock_db = MagicMock()
        mock_db.query().all.return_value = []

        service = RoseService(mock_db)
        result = service.refresh_monthly_roses()

        assert result == 0


class TestRoseServiceGetRosePackages:
    """测试获取玫瑰购买套餐列表"""

    def test_get_rose_packages(self):
        """测试获取套餐列表"""
        from src.services.rose_service import RoseService

        mock_db = MagicMock()
        service = RoseService(mock_db)
        packages = service.get_rose_packages()

        assert len(packages) == 3  # single, bundle_3, bundle_5

        # Check package structure
        for package in packages:
            assert "type" in package
            assert "count" in package
            assert "price" in package
            assert "original_price" in package
            assert "price_per_rose" in package

        # Check specific packages
        single_package = [p for p in packages if p["type"] == "single"][0]
        assert single_package["count"] == 1
        assert single_package["price"] == 30
        assert single_package["price_per_rose"] == 30.0

        bundle_3 = [p for p in packages if p["type"] == "bundle_3"][0]
        assert bundle_3["count"] == 3
        assert bundle_3["price"] == 78
        assert bundle_3.get("discount") == "省 12 元"

        bundle_5 = [p for p in packages if p["type"] == "bundle_5"][0]
        assert bundle_5["count"] == 5
        assert bundle_5["price"] == 120
        assert bundle_5.get("discount") == "省 30 元"


class TestRoseServiceGetRoseService:
    """测试获取玫瑰服务实例"""

    def test_get_rose_service(self):
        """测试获取服务实例"""
        from src.services.rose_service import get_rose_service

        mock_db = MagicMock()
        service = get_rose_service(mock_db)

        assert service is not None
        assert service.db == mock_db


class TestRoseAllocationConfig:
    """测试玫瑰分配配置"""

    def test_rose_allocation_free(self):
        """测试免费会员玫瑰分配"""
        assert ROSE_ALLOCATION["free"]["monthly_roses"] == 1
        assert ROSE_ALLOCATION["free"]["purchase_price"] == 30

    def test_rose_allocation_standard(self):
        """测试标准会员玫瑰分配"""
        assert ROSE_ALLOCATION["standard"]["monthly_roses"] == 3
        assert ROSE_ALLOCATION["standard"]["purchase_price"] == 20

    def test_rose_allocation_premium(self):
        """测试高级会员玫瑰分配"""
        assert ROSE_ALLOCATION["premium"]["monthly_roses"] == 5
        assert ROSE_ALLOCATION["premium"]["purchase_price"] == 15

    def test_rose_packages_config(self):
        """测试玫瑰购买套餐配置"""
        assert ROSE_PACKAGES["single"]["count"] == 1
        assert ROSE_PACKAGES["single"]["price"] == 30

        assert ROSE_PACKAGES["bundle_3"]["count"] == 3
        assert ROSE_PACKAGES["bundle_3"]["price"] == 78
        assert "discount" in ROSE_PACKAGES["bundle_3"]

        assert ROSE_PACKAGES["bundle_5"]["count"] == 5
        assert ROSE_PACKAGES["bundle_5"]["price"] == 120
        assert "discount" in ROSE_PACKAGES["bundle_5"]


class TestRoseModels:
    """测试玫瑰相关模型"""

    def test_rose_source_enum(self):
        """测试玫瑰来源枚举"""
        assert RoseSource.FREE_MONTHLY.value == "free_monthly"
        assert RoseSource.MEMBERSHIP_STANDARD.value == "membership_standard"
        assert RoseSource.MEMBERSHIP_PREMIUM.value == "membership_premium"
        assert RoseSource.PURCHASED.value == "purchased"
        assert RoseSource.GIFT.value == "gift"

    def test_rose_status_enum(self):
        """测试玫瑰状态枚举"""
        assert RoseStatus.AVAILABLE.value == "available"
        assert RoseStatus.SENT.value == "sent"
        assert RoseStatus.EXPIRED.value == "expired"

    def test_rose_balance_model(self):
        """测试玫瑰余额模型"""
        balance = RoseBalance(
            user_id="user-123",
            available_count=5,
            sent_count=2,
            monthly_allocation=7,
            next_refresh_date=datetime.now() + timedelta(days=30),
            purchase_available=True,
        )

        assert balance.user_id == "user-123"
        assert balance.available_count == 5
        assert balance.sent_count == 2
        assert balance.purchase_available is True

    def test_rose_send_request_model(self):
        """测试发送玫瑰请求模型"""
        request = RoseSendRequest(
            target_user_id="target-123",
            message="你好，想认识你",
        )

        assert request.target_user_id == "target-123"
        assert request.message == "你好，想认识你"

    def test_rose_send_response_model(self):
        """测试发送玫瑰响应模型"""
        response = RoseSendResponse(
            success=True,
            message="玫瑰已发送",
            roses_remaining=4,
            transaction_id="tx-123",
            is_match=False,
        )

        assert response.success is True
        assert response.roses_remaining == 4
        assert response.is_match is False

    def test_standout_profile_model(self):
        """测试 Standout 用户资料模型"""
        profile = StandoutProfile(
            user_id="sender-123",
            user_data={
                "name": "发送者",
                "age": 28,
                "location": "北京",
            },
            rose_received_at=datetime.now(),
            rose_count=1,
            latest_message="你好",
            compatibility_score=0.85,
            standout_expires_at=datetime.now() + timedelta(hours=24),
            is_liked=False,
            is_passed=False,
        )

        assert profile.user_id == "sender-123"
        assert profile.compatibility_score == 0.85
        assert profile.rose_count == 1

    def test_standout_list_response_model(self):
        """测试 Standout 列表响应模型"""
        response = StandoutListResponse(
            profiles=[],
            total_count=0,
            unread_count=0,
        )

        assert response.total_count == 0
        assert response.unread_count == 0
        assert len(response.profiles) == 0


class TestRoseServiceEdgeCases:
    """测试边界条件"""

    def test_send_rose_with_message_exceeding_length(self):
        """测试发送附带消息的玫瑰"""
        from src.services.rose_service import RoseService

        mock_db = MagicMock()

        mock_balance_db = MagicMock(spec=UserRoseBalanceDB)
        mock_balance_db.available_count = 3
        mock_balance_db.sent_this_month = 0
        mock_balance_db.total_received_this_month = 3
        mock_balance_db.free_allocation = 1
        mock_balance_db.membership_allocation = 2
        mock_balance_db.purchased_count = 0
        mock_balance_db.gifted_count = 0

        mock_target_user = MagicMock()
        mock_target_user.id = "target-123"

        mock_sender_user = MagicMock()
        mock_sender_user.id = "sender-123"

        def create_mock_query_chain():
            mock_query = MagicMock()
            mock_filter = MagicMock()
            call_returns = [
                mock_balance_db,
                None,  # no existing transaction
                mock_balance_db,
                None,  # no match
            ]
            call_count = [0]

            def first_side_effect():
                call_count[0] += 1
                if call_count[0] <= len(call_returns):
                    return call_returns[call_count[0] - 1]
                return None

            mock_filter.first.side_effect = first_side_effect
            mock_query.filter.return_value = mock_filter
            return mock_query

        mock_db.query.return_value = create_mock_query_chain()

        with patch('src.services.rose_service.MembershipService') as MockMembershipService:
            mock_membership_svc = MagicMock()
            mock_membership = MagicMock(spec=UserMembership)
            mock_membership.tier = MembershipTier.STANDARD
            mock_membership_svc.get_user_membership.return_value = mock_membership
            MockMembershipService.return_value = mock_membership_svc

            with patch('src.services.rose_service.UserRepository') as MockUserRepository:
                mock_user_repo = MagicMock()
                mock_user_repo.get_by_id.side_effect = [mock_target_user, mock_sender_user]
                MockUserRepository.return_value = mock_user_repo

                # Mock HerAdvisorService (新架构替代 matchmaker)
                with patch('services.her_advisor_service.get_her_advisor_service') as mock_her_advisor:
                    mock_advisor = MagicMock()
                    mock_advice = MagicMock()
                    mock_advice.compatibility_score = 0.7
                    mock_advisor.generate_match_advice.return_value = mock_advice
                    mock_her_advisor.return_value = mock_advisor

                    # Mock get_user_profile_service
                    with patch('services.user_profile_service.get_user_profile_service') as mock_profile:
                        mock_profile_svc = MagicMock()
                        mock_profile_svc.get_or_create_profile.return_value = (MagicMock(), MagicMock())
                        mock_profile.return_value = mock_profile_svc

                    def mock_from_db(user):
                        mock_obj = MagicMock()
                        mock_obj.model_dump.return_value = {"name": user.name, "age": 25}
                        return mock_obj

                    with patch('api.users._from_db', side_effect=mock_from_db):
                        service = RoseService(mock_db)
                        # Long message
                        request = RoseSendRequest(
                            target_user_id="target-123",
                            message="这是一条很长的消息" * 10
                        )
                        result = service.send_rose("sender-123", request)

                        # Should still succeed (validation might be elsewhere)
                        assert result.success is True

    def test_get_user_balance_next_refresh_date(self):
        """测试下次刷新日期计算"""
        from src.services.rose_service import RoseService

        mock_db = MagicMock()
        mock_balance_db = MagicMock(spec=UserRoseBalanceDB)
        mock_balance_db.available_count = 5
        mock_balance_db.sent_this_month = 2
        mock_balance_db.total_received_this_month = 7
        mock_db.query().filter().first.return_value = mock_balance_db

        service = RoseService(mock_db)
        result = service.get_user_balance("user-123")

        # Next refresh should be next month's first day
        now = datetime.now()
        expected_refresh = datetime(now.year, now.month, 1) + timedelta(days=32)
        expected_refresh = datetime(expected_refresh.year, expected_refresh.month, 1)

        assert result.next_refresh_date.month != now.month or result.next_refresh_date.year != now.year

    def test_send_rose_compatibility_calculation_exception(self):
        """测试匹配度计算异常时的默认处理"""
        from src.services.rose_service import RoseService

        mock_db = MagicMock()

        mock_balance_db = MagicMock(spec=UserRoseBalanceDB)
        mock_balance_db.available_count = 3
        mock_balance_db.sent_this_month = 0
        mock_balance_db.total_received_this_month = 3
        mock_balance_db.free_allocation = 1
        mock_balance_db.membership_allocation = 2
        mock_balance_db.purchased_count = 0
        mock_balance_db.gifted_count = 0

        mock_target_user = MagicMock()
        mock_sender_user = MagicMock()

        def create_mock_query_chain():
            mock_query = MagicMock()
            mock_filter = MagicMock()
            call_returns = [mock_balance_db, None, mock_balance_db, None]
            call_count = [0]

            def first_side_effect():
                call_count[0] += 1
                if call_count[0] <= len(call_returns):
                    return call_returns[call_count[0] - 1]
                return None

            mock_filter.first.side_effect = first_side_effect
            mock_query.filter.return_value = mock_filter
            return mock_query

        mock_db.query.return_value = create_mock_query_chain()

        with patch('src.services.rose_service.MembershipService') as MockMembershipService:
            mock_membership_svc = MagicMock()
            mock_membership = MagicMock(spec=UserMembership)
            mock_membership.tier = MembershipTier.STANDARD
            mock_membership_svc.get_user_membership.return_value = mock_membership
            MockMembershipService.return_value = mock_membership_svc

            with patch('src.services.rose_service.UserRepository') as MockUserRepository:
                mock_user_repo = MagicMock()
                mock_user_repo.get_by_id.side_effect = [mock_target_user, mock_sender_user]
                MockUserRepository.return_value = mock_user_repo

                # Mock HerAdvisorService to raise exception (测试异常处理)
                with patch('services.her_advisor_service.get_her_advisor_service') as mock_her_advisor:
                    mock_advisor = MagicMock()
                    mock_advisor.generate_match_advice.side_effect = Exception("Calculation error")
                    mock_her_advisor.return_value = mock_advisor

                    # Mock get_user_profile_service
                    with patch('services.user_profile_service.get_user_profile_service') as mock_profile:
                        mock_profile_svc = MagicMock()
                        mock_profile_svc.get_or_create_profile.return_value = (MagicMock(), MagicMock())
                        mock_profile.return_value = mock_profile_svc

                    def mock_from_db(user):
                        mock_obj = MagicMock()
                        mock_obj.model_dump.return_value = {"name": "test"}
                        return mock_obj

                    with patch('api.users._from_db', side_effect=mock_from_db):
                        service = RoseService(mock_db)
                        request = RoseSendRequest(target_user_id="target-123")
                        result = service.send_rose("sender-123", request)

                        # Should still succeed with default compatibility score
                        assert result.success is True