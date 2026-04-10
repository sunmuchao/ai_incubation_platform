"""
通知服务测试

覆盖范围:
- NotificationService (src/services/notification_service.py)
- ShareService (src/services/notification_service.py)
"""
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime, timedelta
import uuid

from services.notification_service import NotificationService, ShareService, get_notification_service


class TestNotificationServiceInit:
    """测试 NotificationService 初始化"""

    def test_init(self):
        """测试初始化"""
        mock_db = MagicMock()
        service = NotificationService(mock_db)

        assert service.db == mock_db
        assert service._push_client is None
        assert service._sms_client is None
        assert service._voice_client is None
        assert service.CHANNEL_PUSH == "push"
        assert service.CHANNEL_SMS == "sms"
        assert service.CHANNEL_VOICE_CALL == "voice_call"
        assert service.CHANNEL_EMAIL == "email"

    def test_get_notification_service(self):
        """测试工厂函数"""
        mock_db = MagicMock()
        service = get_notification_service(mock_db)

        assert isinstance(service, NotificationService)
        assert service.db == mock_db


class TestSendNotification:
    """测试发送通知"""

    def test_send_notification_default_channel(self):
        """测试默认渠道发送"""
        mock_db = MagicMock()

        service = NotificationService(mock_db)

        with patch.object(service, '_create_notification_record'):
            with patch.object(service, '_send_via_channel', return_value={"success": True}):
                result = service.send_notification(
                    user_id="user-123",
                    notification_type="system_notification",
                    title="系统通知",
                    message="这是一条系统通知"
                )

        assert result["success"] == True
        assert "notification_id" in result
        assert len(result["delivery_results"]) == 1

    def test_send_notification_multiple_channels(self):
        """测试多渠道发送"""
        mock_db = MagicMock()

        service = NotificationService(mock_db)

        with patch.object(service, '_create_notification_record'):
            with patch.object(service, '_send_via_channel', return_value={"success": True}):
                result = service.send_notification(
                    user_id="user-123",
                    notification_type="match_notification",
                    title="匹配通知",
                    message="您有新的匹配",
                    channels=["push", "sms", "email"]
                )

        assert result["success"] == True
        assert len(result["delivery_results"]) == 3

    def test_send_notification_partial_failure(self):
        """测试部分渠道失败"""
        mock_db = MagicMock()

        service = NotificationService(mock_db)

        with patch.object(service, '_create_notification_record'):
            with patch.object(service, '_send_via_channel', side_effect=[
                {"success": True},
                {"success": False, "error": "SMS failed"},
                {"success": True}
            ]):
                result = service.send_notification(
                    user_id="user-123",
                    notification_type="emergency_request",
                    title="紧急通知",
                    message="紧急求助",
                    channels=["push", "sms", "email"]
                )

        assert result["success"] == False
        assert len(result["delivery_results"]) == 3

    def test_send_notification_with_data(self):
        """测试带数据发送"""
        mock_db = MagicMock()

        service = NotificationService(mock_db)

        data = {"match_id": "match-123", "score": 0.85}

        with patch.object(service, '_create_notification_record') as mock_create:
            with patch.object(service, '_send_via_channel', return_value={"success": True}):
                result = service.send_notification(
                    user_id="user-123",
                    notification_type="match_notification",
                    title="匹配通知",
                    message="您有新的匹配",
                    data=data
                )

        mock_create.assert_called_once()


class TestSendViaChannel:
    """测试渠道发送"""

    def test_send_via_push_channel(self):
        """测试推送渠道"""
        mock_db = MagicMock()
        service = NotificationService(mock_db)

        with patch.object(service, '_send_push', return_value={"success": True}) as mock_push:
            result = service._send_via_channel(
                user_id="user-123",
                channel="push",
                title="测试",
                message="推送测试",
                notification_id="notif-123"
            )

        mock_push.assert_called_once()
        assert result["success"] == True

    def test_send_via_sms_channel(self):
        """测试短信渠道"""
        mock_db = MagicMock()
        service = NotificationService(mock_db)

        with patch.object(service, '_send_sms', return_value={"success": True}) as mock_sms:
            result = service._send_via_channel(
                user_id="user-123",
                channel="sms",
                title="测试",
                message="短信测试",
                notification_id="notif-123"
            )

        mock_sms.assert_called_once()
        assert result["success"] == True

    def test_send_via_voice_call_channel(self):
        """测试语音电话渠道"""
        mock_db = MagicMock()
        service = NotificationService(mock_db)

        with patch.object(service, '_send_voice_call', return_value={"success": True}) as mock_voice:
            result = service._send_via_channel(
                user_id="user-123",
                channel="voice_call",
                title="测试",
                message="语音测试",
                notification_id="notif-123"
            )

        mock_voice.assert_called_once()
        assert result["success"] == True

    def test_send_via_email_channel(self):
        """测试邮件渠道"""
        mock_db = MagicMock()
        service = NotificationService(mock_db)

        with patch.object(service, '_send_email', return_value={"success": True}) as mock_email:
            result = service._send_via_channel(
                user_id="user-123",
                channel="email",
                title="测试",
                message="邮件测试",
                notification_id="notif-123"
            )

        mock_email.assert_called_once()
        assert result["success"] == True

    def test_send_via_unknown_channel(self):
        """测试未知渠道"""
        mock_db = MagicMock()
        service = NotificationService(mock_db)

        result = service._send_via_channel(
            user_id="user-123",
            channel="unknown",
            title="测试",
            message="测试",
            notification_id="notif-123"
        )

        assert result["success"] == False
        assert "未知渠道" in result["error"]

    def test_send_via_channel_error_handling(self):
        """测试渠道发送错误处理"""
        mock_db = MagicMock()
        service = NotificationService(mock_db)

        with patch.object(service, '_send_push', side_effect=Exception("Push error")):
            result = service._send_via_channel(
                user_id="user-123",
                channel="push",
                title="测试",
                message="测试",
                notification_id="notif-123"
            )

        assert result["success"] == False
        assert "Push error" in result["error"]


class TestSendPush:
    """测试推送发送"""

    def test_send_push_mock_mode(self):
        """测试推送 mock 模式"""
        mock_db = MagicMock()
        service = NotificationService(mock_db)

        with patch.object(service, '_get_push_client', return_value=None):
            with patch.object(service, '_record_delivery'):
                result = service._send_push(
                    user_id="user-123",
                    title="测试",
                    message="推送测试",
                    notification_id="notif-123"
                )

        assert result["success"] == True
        assert result["mock"] == True

    def test_send_push_no_tokens(self):
        """测试无推送令牌"""
        mock_db = MagicMock()
        service = NotificationService(mock_db)

        mock_client = MagicMock()

        with patch.object(service, '_get_push_client', return_value=mock_client):
            with patch.object(service, '_get_user_push_tokens', return_value=[]):
                result = service._send_push(
                    user_id="user-123",
                    title="测试",
                    message="推送测试",
                    notification_id="notif-123"
                )

        assert result["success"] == False
        assert "推送令牌" in result["error"]

    def test_send_push_success(self):
        """测试推送成功"""
        mock_db = MagicMock()
        service = NotificationService(mock_db)

        mock_client = MagicMock()
        mock_client.push.return_value = {"success": True}

        with patch.object(service, '_get_push_client', return_value=mock_client):
            with patch.object(service, '_get_user_push_tokens', return_value=["token-1", "token-2"]):
                with patch.object(service, '_record_delivery'):
                    result = service._send_push(
                        user_id="user-123",
                        title="测试",
                        message="推送测试",
                        notification_id="notif-123"
                    )

        assert result["success"] == True
        assert result["channel"] == "push"

    def test_send_push_client_failure(self):
        """测试推送客户端失败"""
        mock_db = MagicMock()
        service = NotificationService(mock_db)

        mock_client = MagicMock()
        mock_client.push.return_value = {"success": False, "error": "推送失败"}

        with patch.object(service, '_get_push_client', return_value=mock_client):
            with patch.object(service, '_get_user_push_tokens', return_value=["token-1"]):
                with patch.object(service, '_record_delivery'):
                    result = service._send_push(
                        user_id="user-123",
                        title="测试",
                        message="推送测试",
                        notification_id="notif-123"
                    )

        assert result["success"] == False
        assert "推送失败" in result["error"]


class TestSendSMS:
    """测试短信发送"""

    def test_send_sms_user_no_phone(self):
        """测试用户无手机号"""
        mock_db = MagicMock()

        mock_user = MagicMock()
        mock_user.phone = None
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        service = NotificationService(mock_db)
        result = service._send_sms(
            user_id="user-123",
            message="短信测试",
            notification_id="notif-123"
        )

        assert result["success"] == False
        assert "手机号" in result["error"]

    def test_send_sms_user_not_found(self):
        """测试用户不存在"""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        service = NotificationService(mock_db)
        result = service._send_sms(
            user_id="user-123",
            message="短信测试",
            notification_id="notif-123"
        )

        assert result["success"] == False

    def test_send_sms_mock_mode(self):
        """测试短信 mock 模式"""
        mock_db = MagicMock()

        mock_user = MagicMock()
        mock_user.phone = "13800138000"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        service = NotificationService(mock_db)

        with patch.object(service, '_get_sms_client', return_value=None):
            with patch.object(service, '_record_delivery'):
                result = service._send_sms(
                    user_id="user-123",
                    message="短信测试",
                    notification_id="notif-123"
                )

        assert result["success"] == True
        assert result["mock"] == True

    def test_send_sms_success(self):
        """测试短信发送成功"""
        mock_db = MagicMock()

        mock_user = MagicMock()
        mock_user.phone = "13800138000"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        mock_client = MagicMock()
        mock_client.send_notification.return_value = {"success": True}

        service = NotificationService(mock_db)

        with patch.object(service, '_get_sms_client', return_value=mock_client):
            with patch.object(service, '_record_delivery'):
                result = service._send_sms(
                    user_id="user-123",
                    message="短信测试",
                    notification_id="notif-123"
                )

        assert result["success"] == True


class TestSendVoiceCall:
    """测试语音电话发送"""

    def test_send_voice_call_user_no_phone(self):
        """测试用户无手机号"""
        mock_db = MagicMock()

        mock_user = MagicMock()
        mock_user.phone = None
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        service = NotificationService(mock_db)
        result = service._send_voice_call(
            user_id="user-123",
            message="语音测试",
            notification_id="notif-123"
        )

        assert result["success"] == False
        assert "手机号" in result["error"]

    def test_send_voice_call_mock_mode(self):
        """测试语音电话 mock 模式"""
        mock_db = MagicMock()

        mock_user = MagicMock()
        mock_user.phone = "13800138000"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        service = NotificationService(mock_db)

        with patch.object(service, '_record_delivery'):
            result = service._send_voice_call(
                user_id="user-123",
                message="语音测试",
                notification_id="notif-123"
            )

        assert result["success"] == True
        assert result["mock"] == True


class TestSendEmail:
    """测试邮件发送"""

    def test_send_email_user_no_email(self):
        """测试用户无邮箱"""
        mock_db = MagicMock()

        mock_user = MagicMock()
        mock_user.email = None
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        service = NotificationService(mock_db)
        result = service._send_email(
            user_id="user-123",
            title="邮件测试",
            message="邮件内容",
            notification_id="notif-123"
        )

        assert result["success"] == False
        assert "邮箱" in result["error"]

    def test_send_email_mock_mode(self):
        """测试邮件 mock 模式"""
        mock_db = MagicMock()

        mock_user = MagicMock()
        mock_user.email = "test@example.com"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        service = NotificationService(mock_db)

        with patch.object(service, '_record_delivery'):
            result = service._send_email(
                user_id="user-123",
                title="邮件测试",
                message="邮件内容",
                notification_id="notif-123"
            )

        assert result["success"] == True
        assert result["mock"] == True


class TestNotifyEmergencyContacts:
    """测试紧急联系人通知"""

    def test_notify_emergency_contacts_no_contacts(self):
        """测试无紧急联系人"""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = []

        service = NotificationService(mock_db)
        result = service.notify_emergency_contacts(
            user_id="user-123",
            alert_type="紧急求助",
            description="用户触发紧急求助"
        )

        assert result["success"] == False
        assert "紧急联系人" in result["error"]

    def test_notify_emergency_contacts_success(self):
        """测试紧急联系人通知成功"""
        mock_db = MagicMock()

        mock_contact1 = MagicMock()
        mock_contact1.name = "联系人1"
        mock_contact1.phone = "13800138001"

        mock_contact2 = MagicMock()
        mock_contact2.name = "联系人2"
        mock_contact2.phone = "13800138002"

        mock_db.query.return_value.filter.return_value.all.return_value = [mock_contact1, mock_contact2]

        service = NotificationService(mock_db)

        with patch.object(service, '_notify_contact', return_value={"success": True}):
            result = service.notify_emergency_contacts(
                user_id="user-123",
                alert_type="紧急求助",
                description="用户触发紧急求助",
                location_url="https://maps.example.com"
            )

        assert result["success"] == True
        assert result["contacts_notified"] == 2

    def test_notify_emergency_contacts_partial_failure(self):
        """测试部分紧急联系人通知失败"""
        mock_db = MagicMock()

        mock_contact1 = MagicMock()
        mock_contact1.name = "联系人1"
        mock_contact1.phone = "13800138001"

        mock_contact2 = MagicMock()
        mock_contact2.name = "联系人2"
        mock_contact2.phone = "13800138002"

        mock_db.query.return_value.filter.return_value.all.return_value = [mock_contact1, mock_contact2]

        service = NotificationService(mock_db)

        with patch.object(service, '_notify_contact', side_effect=[
            {"success": True},
            {"success": False}
        ]):
            result = service.notify_emergency_contacts(
                user_id="user-123",
                alert_type="紧急求助",
                description="用户触发紧急求助"
            )

        assert result["success"] == True
        assert result["contacts_notified"] == 1


class TestNotifyContact:
    """测试单个紧急联系人通知"""

    def test_notify_contact_success(self):
        """测试单个联系人通知成功"""
        mock_db = MagicMock()
        service = NotificationService(mock_db)

        with patch.object(service, '_send_sms_to_contact', return_value={"success": True}):
            result = service._notify_contact(
                contact_name="联系人",
                contact_phone="13800138000",
                title="紧急通知",
                message="紧急求助"
            )

        assert result["sms_success"] == True

    def test_notify_contact_failure(self):
        """测试单个联系人通知失败"""
        mock_db = MagicMock()
        service = NotificationService(mock_db)

        with patch.object(service, '_send_sms_to_contact', return_value={"success": False}):
            result = service._notify_contact(
                contact_name="联系人",
                contact_phone="13800138000",
                title="紧急通知",
                message="紧急求助"
            )

        assert result["sms_success"] == False


class TestSendSMSToContact:
    """测试向联系人发送短信"""

    def test_send_sms_to_contact_mock(self):
        """测试联系人短信 mock 模式"""
        mock_db = MagicMock()
        service = NotificationService(mock_db)

        with patch.object(service, '_get_sms_client', return_value=None):
            result = service._send_sms_to_contact("13800138000", "测试短信")

        assert result["success"] == True
        assert result["mock"] == True

    def test_send_sms_to_contact_success(self):
        """测试联系人短信发送成功"""
        mock_db = MagicMock()
        service = NotificationService(mock_db)

        mock_client = MagicMock()
        mock_client.send_notification.return_value = {"success": True}

        with patch.object(service, '_get_sms_client', return_value=mock_client):
            result = service._send_sms_to_contact("13800138000", "测试短信")

        assert result["success"] == True


class TestShareServiceInit:
    """测试 ShareService 初始化"""

    def test_init(self):
        """测试初始化"""
        mock_db = MagicMock()
        service = ShareService(mock_db)
        assert service.db == mock_db


class TestCreateInviteCode:
    """测试创建邀请码"""

    def test_create_invite_code(self):
        """测试创建邀请码"""
        mock_db = MagicMock()

        service = ShareService(mock_db)

        with patch('uuid.uuid4', return_value='test-uuid-1234'):
            result = service.create_invite_code(
                user_id="user-123",
                code_type="vip",
                max_uses=10,
                reward_type="积分",
                reward_amount=100
            )

        mock_db.execute.assert_called()
        mock_db.commit.assert_called()
        assert result["code_type"] == "vip"
        assert result["max_uses"] == 10
        assert result["reward_type"] == "积分"
        assert result["reward_amount"] == 100

    def test_create_invite_code_with_expiry(self):
        """测试创建带过期时间的邀请码"""
        mock_db = MagicMock()

        service = ShareService(mock_db)

        with patch('uuid.uuid4', return_value='test-uuid-1234'):
            result = service.create_invite_code(
                user_id="user-123",
                code_type="vip",
                max_uses=10,
                reward_type="积分",
                reward_amount=100,
                expires_days=30
            )

        assert result["expires_at"] is not None


class TestGetUserInviteCodes:
    """测试获取用户邀请码"""

    def test_get_user_invite_codes(self):
        """测试获取邀请码列表"""
        mock_db = MagicMock()

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            ("id-1", "CODE1", "vip", 10, 5, "积分", 100, True, None, None),
            ("id-2", "CODE2", "premium", 5, 2, "积分", 50, True, None, None)
        ]
        mock_db.execute.return_value = mock_result

        service = ShareService(mock_db)
        result = service.get_user_invite_codes("user-123")

        assert len(result) == 2
        assert result[0]["code"] == "CODE1"
        assert result[1]["code"] == "CODE2"

    def test_get_user_invite_codes_empty(self):
        """测试无邀请码"""
        mock_db = MagicMock()

        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_db.execute.return_value = mock_result

        service = ShareService(mock_db)
        result = service.get_user_invite_codes("user-123")

        assert len(result) == 0


class TestValidateInviteCode:
    """测试验证邀请码"""

    def test_validate_invite_code_valid(self):
        """测试有效邀请码"""
        mock_db = MagicMock()

        # 模拟 fetchone 返回的元组，确保使用真实整数
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (
            "id-1", "CODE1", "user-123", "vip", 10, 5, "积分", 100, True, None
        )
        # 确保索引访问返回真实值
        mock_result.__getitem__ = lambda self, key: (
            "id-1", "CODE1", "user-123", "vip", 10, 5, "积分", 100, True, None
        )[key]
        mock_db.execute.return_value = mock_result

        service = ShareService(mock_db)
        result = service.validate_invite_code("CODE1")

        assert result is not None
        assert result["code"] == "CODE1"
        assert result["reward_type"] == "积分"

    def test_validate_invite_code_not_found(self):
        """测试邀请码不存在"""
        mock_db = MagicMock()

        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_db.execute.return_value = mock_result

        service = ShareService(mock_db)
        result = service.validate_invite_code("INVALID")

        assert result is None

    def test_validate_invite_code_expired(self):
        """测试已过期邀请码"""
        mock_db = MagicMock()

        expired_date = datetime.now() - timedelta(days=1)

        mock_result = MagicMock()
        mock_result.fetchone.return_value = (
            "id-1", "CODE1", "user-123", "vip", 10, 5, "积分", 100, True, expired_date.isoformat()
        )
        mock_db.execute.return_value = mock_result

        service = ShareService(mock_db)
        result = service.validate_invite_code("CODE1")

        assert result is None

    def test_validate_invite_code_max_uses_reached(self):
        """测试达到使用上限"""
        mock_db = MagicMock()

        # 模拟 fetchone 返回的元组，max_uses=10, used_count=10
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (
            "id-1", "CODE1", "user-123", "vip", 10, 10, "积分", 100, True, None
        )
        # 确保索引访问返回真实值
        mock_result.__getitem__ = lambda self, key: (
            "id-1", "CODE1", "user-123", "vip", 10, 10, "积分", 100, True, None
        )[key]
        mock_db.execute.return_value = mock_result

        service = ShareService(mock_db)
        result = service.validate_invite_code("CODE1")

        assert result is None


class TestUseInviteCode:
    """测试使用邀请码"""

    def test_use_invite_code_invalid(self):
        """测试使用无效邀请码"""
        mock_db = MagicMock()
        service = ShareService(mock_db)

        with patch.object(service, 'validate_invite_code', return_value=None):
            result = service.use_invite_code("INVALID", "user-456", "test@example.com")

        assert result is None

    def test_use_invite_code_success(self):
        """测试使用邀请码成功"""
        mock_db = MagicMock()
        service = ShareService(mock_db)

        invite = {
            "id": "invite-1",
            "code": "CODE1",
            "inviter_user_id": "user-123",
            "reward_type": "积分",
            "reward_amount": 100
        }

        with patch.object(service, 'validate_invite_code', return_value=invite):
            with patch('uuid.uuid4', return_value='test-uuid'):
                result = service.use_invite_code("CODE1", "user-456", "test@example.com")

        mock_db.execute.assert_called()
        mock_db.commit.assert_called()
        assert result["reward_type"] == "积分"
        assert result["reward_amount"] == 100


class TestCreateShareRecord:
    """测试创建分享记录"""

    def test_create_share_record(self):
        """测试创建分享记录"""
        mock_db = MagicMock()
        service = ShareService(mock_db)

        with patch('uuid.uuid4', return_value='test-uuid'):
            result = service.create_share_record(
                user_id="user-123",
                share_type="profile",
                channel="wechat",
                share_url="https://example.com/share/123"
            )

        mock_db.execute.assert_called()
        mock_db.commit.assert_called()
        assert result["share_type"] == "profile"
        assert result["channel"] == "wechat"

    def test_create_share_record_with_content(self):
        """测试带内容创建分享记录"""
        mock_db = MagicMock()
        service = ShareService(mock_db)

        with patch('uuid.uuid4', return_value='test-uuid'):
            result = service.create_share_record(
                user_id="user-123",
                share_type="profile",
                channel="wechat",
                share_url="https://example.com/share/123",
                content_type="user_profile",
                content_id="profile-123",
                share_title="分享标题",
                share_description="分享描述",
                share_image_url="https://example.com/image.jpg"
            )

        assert result["share_type"] == "profile"


class TestGetShareStats:
    """测试获取分享统计"""

    def test_get_share_stats(self):
        """测试获取分享统计"""
        mock_db = MagicMock()

        mock_total_result = MagicMock()
        mock_total_result.fetchone.return_value = (10, 100, 50, 5)

        mock_channel_result = MagicMock()
        mock_channel_result.fetchall.return_value = [
            ("wechat", 5, 60, 30),
            ("qq", 3, 30, 15),
            ("link", 2, 10, 5)
        ]

        mock_db.execute.side_effect = [mock_total_result, mock_channel_result]

        service = ShareService(mock_db)
        result = service.get_share_stats("user-123")

        assert result["total_records"] == 10
        assert result["total_views"] == 100
        assert result["total_clicks"] == 50
        assert "channel_stats" in result

    def test_get_share_stats_empty(self):
        """测试无分享记录"""
        mock_db = MagicMock()

        mock_total_result = MagicMock()
        mock_total_result.fetchone.return_value = (0, 0, 0, 0)

        mock_channel_result = MagicMock()
        mock_channel_result.fetchall.return_value = []

        mock_db.execute.side_effect = [mock_total_result, mock_channel_result]

        service = ShareService(mock_db)
        result = service.get_share_stats("user-123")

        assert result["total_records"] == 0
        assert result["channel_stats"] == {}


class TestGetInviteStats:
    """测试获取邀请统计"""

    def test_get_invite_stats(self):
        """测试获取邀请统计"""
        mock_db = MagicMock()

        mock_total_result = MagicMock()
        mock_total_result.fetchone.return_value = (3, 10, 1000)

        mock_codes_result = MagicMock()
        mock_codes_result.fetchall.return_value = [
            ("id-1", "CODE1", "vip", 5, "积分", 100, None),
            ("id-2", "CODE2", "premium", 3, "积分", 50, None),
            ("id-3", "CODE3", "basic", 2, "积分", 20, None)
        ]

        mock_db.execute.side_effect = [mock_total_result, mock_codes_result]

        service = ShareService(mock_db)
        result = service.get_invite_stats("user-123")

        assert result["total_codes"] == 3
        assert result["total_invites"] == 10
        assert len(result["invite_codes"]) == 3

    def test_get_invite_stats_empty(self):
        """测试无邀请记录"""
        mock_db = MagicMock()

        mock_total_result = MagicMock()
        mock_total_result.fetchone.return_value = (0, 0, 0)

        mock_codes_result = MagicMock()
        mock_codes_result.fetchall.return_value = []

        mock_db.execute.side_effect = [mock_total_result, mock_codes_result]

        service = ShareService(mock_db)
        result = service.get_invite_stats("user-123")

        assert result["total_codes"] == 0
        assert result["invite_codes"] == []