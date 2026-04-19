"""
订阅推送功能集成测试

测试完整的功能链路：
1. API 端点可用性
2. 创建订阅
3. 新用户注册触发通知
4. 获取待推送通知
5. 标记通知状态
"""
import pytest
import httpx
import asyncio
import json
import uuid
from unittest.mock import patch, MagicMock

# 测试配置
HER_API_URL = "http://localhost:8002"


class TestNotificationAPIEndpoints:
    """测试通知 API 端点"""

    def test_notifications_py_router_defined(self):
        """验证 notifications.py 路由器定义"""
        from api.notifications import router

        assert router.prefix == "/api/notifications"
        assert "notifications" in router.tags

        # 验证端点存在（路由路径包含完整前缀）
        routes = [r.path for r in router.routes]
        assert "/api/notifications/pending" in routes
        assert "/api/notifications/{notification_id}/mark_delivered" in routes
        assert "/api/notifications/{notification_id}/mark_read" in routes
        assert "/api/notifications/preference" in routes

    def test_notification_share_apis_router_defined(self):
        """验证 notification_share_apis.py 路由器定义"""
        from api.notification_share_apis import router_notifications, router_share

        assert router_notifications.prefix == "/api/notifications"
        assert router_share.prefix == "/api/share"


class TestSubscriptionCreation:
    """测试订阅创建功能"""

    def test_create_notification_preference_service(self):
        """测试服务层创建订阅"""
        from services.notification_service import create_notification_preference
        from db.database import get_db
        from db.models import UserNotificationPreferenceDB

        user_id = str(uuid.uuid4())

        # Mock 数据库
        def mock_get_db_gen():
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = None
            yield mock_db

        with patch("db.database.get_db", side_effect=mock_get_db_gen):
            result = create_notification_preference(
                user_id=user_id,
                trigger_type="new_user_match",
                conditions={"location": "深圳", "gender": "female"}
            )

        assert result["success"] == True
        assert result["action"] == "created"

    def test_update_existing_preference_service(self):
        """测试更新已存在的订阅"""
        from services.notification_service import create_notification_preference

        user_id = str(uuid.uuid4())

        # Mock 已存在的订阅
        existing_pref = MagicMock()
        existing_pref.id = 1

        def mock_get_db_gen():
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = existing_pref
            yield mock_db

        with patch("db.database.get_db", side_effect=mock_get_db_gen):
            result = create_notification_preference(
                user_id=user_id,
                trigger_type="new_user_match",
                conditions={"location": "广州"}
            )

        assert result["success"] == True
        assert result["action"] == "updated"


class TestEventTriggerFlow:
    """测试事件触发流程"""

    @pytest.mark.asyncio
    async def test_new_user_triggers_check(self):
        """测试新用户注册触发通知检查"""
        from services.notification_service import check_and_notify_preferences
        from db.models import UserNotificationPreferenceDB, PendingNotificationDB

        # 创建订阅用户
        subscriber_id = str(uuid.uuid4())
        pref = MagicMock()
        pref.user_id = subscriber_id
        pref.trigger_type = "new_user_match"
        pref.conditions_json = json.dumps({"location": "深圳"})
        pref.is_active = True

        # 创建新用户
        new_user = MagicMock()
        new_user.id = str(uuid.uuid4())
        new_user.name = "小美"
        new_user.location = "深圳"
        new_user.gender = "female"
        new_user.age = 28
        new_user.interests = "阅读,旅行"

        # Mock 数据库查询
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = [pref]
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()

        def mock_get_db_gen():
            yield mock_db

        with patch("db.database.get_db", side_effect=mock_get_db_gen):
            await check_and_notify_preferences(new_user)

        # 验证通知被创建
        assert mock_db.add.called
        assert mock_db.commit.called

    @pytest.mark.asyncio
    async def test_no_match_no_notification(self):
        """测试不匹配时不触发通知"""
        from services.notification_service import check_and_notify_preferences

        # 创建订阅用户（偏好深圳）
        subscriber_id = str(uuid.uuid4())
        pref = MagicMock()
        pref.user_id = subscriber_id
        pref.trigger_type = "new_user_match"
        pref.conditions_json = json.dumps({"location": "深圳"})
        pref.is_active = True

        # 创建不匹配的新用户（北京）
        new_user = MagicMock()
        new_user.id = str(uuid.uuid4())
        new_user.location = "北京"
        new_user.gender = "male"

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = [pref]
        mock_db.add = MagicMock()

        def mock_get_db_gen():
            yield mock_db

        with patch("db.database.get_db", side_effect=mock_get_db_gen):
            await check_and_notify_preferences(new_user)

        # 验证没有添加通知
        assert not mock_db.add.called


class TestNotificationQueue:
    """测试通知队列管理"""

    def test_get_pending_notifications_service(self):
        """测试获取待推送通知"""
        from services.notification_service import get_pending_notifications

        user_id = str(uuid.uuid4())

        # Mock 待推送通知
        notification = MagicMock()
        notification.id = 1
        notification.trigger_type = "new_user_match"
        notification.trigger_user_id = str(uuid.uuid4())
        notification.payload_json = json.dumps({"name": "小美", "location": "深圳"})
        notification.status = "pending"
        notification.created_at = MagicMock()

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [notification]

        def mock_get_db_gen():
            yield mock_db

        with patch("db.database.get_db", side_effect=mock_get_db_gen):
            result = get_pending_notifications(user_id)

        assert result["total"] == 1
        assert result["has_unread"] == True
        assert len(result["notifications"]) == 1

    def test_mark_notification_delivered_service(self):
        """测试标记通知已推送"""
        from services.notification_service import mark_notification_delivered

        notification_id = 1

        # Mock 通知
        notification = MagicMock()
        notification.id = notification_id
        notification.status = "pending"

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = notification
        mock_db.commit = MagicMock()

        def mock_get_db_gen():
            yield mock_db

        with patch("db.database.get_db", side_effect=mock_get_db_gen):
            success = mark_notification_delivered(notification_id)

        assert success == True
        assert notification.status == "delivered"

    def test_mark_notification_read_service(self):
        """测试标记通知已读"""
        from services.notification_service import mark_notification_read

        notification_id = 1

        notification = MagicMock()
        notification.id = notification_id
        notification.status = "delivered"

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = notification
        mock_db.commit = MagicMock()

        def mock_get_db_gen():
            yield mock_db

        with patch("db.database.get_db", side_effect=mock_get_db_gen):
            success = mark_notification_read(notification_id)

        assert success == True
        assert notification.status == "read"


class TestMatchConditionsLogic:
    """测试纯逻辑匹配"""

    def test_location_match(self):
        """测试地点匹配"""
        from services.notification_service import match_conditions

        new_user = MagicMock(location="深圳市南山区")
        conditions = {"location": "深圳"}

        result = match_conditions(new_user, conditions)
        assert result == True

    def test_gender_match(self):
        """测试性别匹配"""
        from services.notification_service import match_conditions

        new_user = MagicMock(gender="female", location="")
        conditions = {"gender": "female"}

        result = match_conditions(new_user, conditions)
        assert result == True

    def test_age_range_match(self):
        """测试年龄范围匹配"""
        from services.notification_service import match_conditions

        new_user = MagicMock(age=28, location="", gender="")
        conditions = {"age_range": "25-30"}

        result = match_conditions(new_user, conditions)
        assert result == True

    def test_multi_condition_match(self):
        """测试多条件组合匹配"""
        from services.notification_service import match_conditions

        new_user = MagicMock(
            location="深圳",
            gender="female",
            age=28,
            relationship_goal="serious"
        )
        conditions = {
            "location": "深圳",
            "gender": "female",
            "age_range": "25-30",
            "relationship_goal": "serious"
        }

        result = match_conditions(new_user, conditions)
        assert result == True

    def test_no_match_due_to_gender(self):
        """测试性别不匹配"""
        from services.notification_service import match_conditions

        new_user = MagicMock(location="深圳", gender="male")
        conditions = {"location": "深圳", "gender": "female"}

        result = match_conditions(new_user, conditions)
        assert result == False


class TestMatchScoreCalculation:
    """测试匹配度计算"""

    def test_same_city_bonus(self):
        """测试同城加分"""
        from services.notification_service import calculate_match_score

        user1 = MagicMock(
            id=str(uuid.uuid4()),
            location="深圳",
            preferred_age_min=25,
            preferred_age_max=30,
            relationship_goal="serious"
        )
        user2 = MagicMock(
            id=str(uuid.uuid4()),
            location="深圳",
            age=28,
            relationship_goal="serious"
        )

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.side_effect = [user1, user2]

        score = calculate_match_score(user1.id, user2.id, mock_db)

        # 同城 +20，年龄匹配 +15，关系目标 +10，基础分 50 = 95
        assert score >= 70

    def test_different_city_base_score(self):
        """测试不同城市基础分"""
        from services.notification_service import calculate_match_score

        user1 = MagicMock(
            id=str(uuid.uuid4()),
            location="北京",
            preferred_age_min=None,
            preferred_age_max=None,
            relationship_goal=None
        )
        user2 = MagicMock(
            id=str(uuid.uuid4()),
            location="深圳",
            age=50
        )

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.side_effect = [user1, user2]

        score = calculate_match_score(user1.id, user2.id, mock_db)

        # 只有基础分 50
        assert score == 50


class TestMiddlewareIntegration:
    """测试 Agent Middleware 集成"""

    def test_notification_middleware_import(self):
        """测试中间件可导入"""
        from deerflow.agents.middlewares.notification_middleware import NotificationMiddleware

        middleware = NotificationMiddleware()
        assert middleware is not None

    def test_middleware_build_notification_hint(self):
        """测试中间件构建通知提示"""
        from deerflow.agents.middlewares.notification_middleware import NotificationMiddleware

        middleware = NotificationMiddleware()

        notifications = [
            {
                "id": 1,
                "type": "new_user_match",
                "trigger_user_id": "user-123",
                "payload": {
                    "name": "小美",
                    "location": "深圳",
                    "match_score": 85
                }
            }
        ]

        hint = middleware._build_notification_hint(notifications)

        assert "【系统通知】" in hint
        assert "小美" in hint
        assert "深圳" in hint
        assert "85%" in hint
        assert "her_get_target_user" in hint

    def test_middleware_should_check_first_message_only(self):
        """测试中间件只在第一条消息时检查"""
        from deerflow.agents.middlewares.notification_middleware import NotificationMiddleware
        from langchain_core.messages import HumanMessage, AIMessage

        middleware = NotificationMiddleware()

        # 只有第一条用户消息 - 应该检查
        state_first = {"messages": [HumanMessage(content="你好")]}
        assert middleware._should_check_notifications(state_first) == True

        # 有多条消息 - 不应该检查
        state_multi = {"messages": [
            HumanMessage(content="你好"),
            AIMessage(content="你好！"),
            HumanMessage(content="帮我找个对象")
        ]}
        assert middleware._should_check_notifications(state_multi) == False


class TestProductCapabilities:
    """测试产品能力开关"""

    def test_match_pool_subscription_enabled(self):
        """测试匹配池订阅功能已开启"""
        from deerflow.community.her_tools.capabilities_tools import HER_PRODUCT_CAPABILITIES

        capabilities = HER_PRODUCT_CAPABILITIES["capabilities"]

        match_pool_cap = next(
            (c for c in capabilities if c["id"] == "match_pool_subscription"),
            None
        )

        assert match_pool_cap is not None
        assert match_pool_cap["enabled"] == True
        assert "匹配池" in match_pool_cap["user_visible_name_zh"]

    def test_social_interest_notifications_enabled(self):
        """测试社交互动通知功能"""
        from deerflow.community.her_tools.capabilities_tools import HER_PRODUCT_CAPABILITIES

        capabilities = HER_PRODUCT_CAPABILITIES["capabilities"]

        social_cap = next(
            (c for c in capabilities if c["id"] == "social_interest_notifications"),
            None
        )

        assert social_cap is not None
        assert social_cap["enabled"] == True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])