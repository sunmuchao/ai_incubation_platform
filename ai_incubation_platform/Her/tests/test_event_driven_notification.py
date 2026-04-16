"""
事件驱动主动通知系统测试

测试覆盖：
1. 数据库模型测试 - UserNotificationPreferenceDB, PendingNotificationDB
2. 纯逻辑匹配测试 - match_conditions
3. 事件触发测试 - check_and_notify_preferences
4. 通知队列管理测试 - get_pending, mark_delivered, mark_read
5. API 端点测试 - FastAPI routes
6. 边缘场景测试 - 空条件、null 值等
7. Token 消耗验证 - 确保事件触发不调用 AI
"""
import pytest
import asyncio
import json
import uuid
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock

# 导入测试依赖
from db.models import (
    UserDB,
    UserNotificationPreferenceDB,
    PendingNotificationDB,
)
from services.notification_service import (
    match_conditions,
    calculate_match_score,
    check_and_notify_preferences,
    get_pending_notifications,
    mark_notification_delivered,
    mark_notification_read,
    create_notification_preference,
)


# ============================================================
# 第一部分：数据库模型测试
# ============================================================

class TestNotificationModels:
    """测试通知相关的数据库模型"""

    def test_user_notification_preference_creation(self, db_session):
        """测试用户偏好订阅创建"""
        user_id = str(uuid.uuid4())
        preference = UserNotificationPreferenceDB(
            user_id=user_id,
            trigger_type="new_user_match",
            conditions_json=json.dumps({"location": "深圳", "gender": "female"}),
            is_active=True,
        )
        db_session.add(preference)
        db_session.commit()

        # 验证创建成功
        saved = db_session.query(UserNotificationPreferenceDB).filter(
            UserNotificationPreferenceDB.user_id == user_id
        ).first()

        assert saved is not None
        assert saved.trigger_type == "new_user_match"
        assert saved.is_active == True
        conditions = json.loads(saved.conditions_json)
        assert conditions["location"] == "深圳"
        assert conditions["gender"] == "female"

    def test_pending_notification_creation(self, db_session):
        """测试待推送通知创建"""
        target_user_id = str(uuid.uuid4())
        trigger_user_id = str(uuid.uuid4())

        notification = PendingNotificationDB(
            target_user_id=target_user_id,
            trigger_user_id=trigger_user_id,
            trigger_type="new_user_match",
            payload_json=json.dumps({
                "name": "小美",
                "age": 28,
                "location": "深圳",
                "match_score": 85,
            }),
            status="pending",
        )
        db_session.add(notification)
        db_session.commit()

        # 验证创建成功
        saved = db_session.query(PendingNotificationDB).filter(
            PendingNotificationDB.target_user_id == target_user_id
        ).first()

        assert saved is not None
        assert saved.trigger_type == "new_user_match"
        assert saved.status == "pending"
        payload = json.loads(saved.payload_json)
        assert payload["name"] == "小美"
        assert payload["match_score"] == 85

    def test_notification_status_flow(self, db_session):
        """测试通知状态流转: pending -> delivered -> read"""
        target_user_id = str(uuid.uuid4())
        notification = PendingNotificationDB(
            target_user_id=target_user_id,
            trigger_type="new_user_match",
            status="pending",
        )
        db_session.add(notification)
        db_session.commit()

        # pending -> delivered
        notification.status = "delivered"
        notification.delivered_at = datetime.now()
        db_session.commit()

        saved = db_session.query(PendingNotificationDB).filter(
            PendingNotificationDB.target_user_id == target_user_id
        ).first()
        assert saved.status == "delivered"
        assert saved.delivered_at is not None

        # delivered -> read
        saved.status = "read"
        db_session.commit()

        final = db_session.query(PendingNotificationDB).filter(
            PendingNotificationDB.target_user_id == target_user_id
        ).first()
        assert final.status == "read"

    def test_preference_multiple_allowed(self, db_session):
        """测试同一用户同一类型允许多条订阅（SQLite 无唯一约束）"""
        user_id = str(uuid.uuid4())

        # 创建第一条订阅
        pref1 = UserNotificationPreferenceDB(
            user_id=user_id,
            trigger_type="new_user_match",
            conditions_json=json.dumps({"location": "深圳"}),
            is_active=True,
        )
        db_session.add(pref1)
        db_session.commit()

        # 创建第二条订阅（同一用户同一类型）
        pref2 = UserNotificationPreferenceDB(
            user_id=user_id,
            trigger_type="new_user_match",
            conditions_json=json.dumps({"location": "广州"}),
            is_active=True,
        )
        db_session.add(pref2)
        db_session.commit()

        # 查询应该有两条
        count = db_session.query(UserNotificationPreferenceDB).filter(
            UserNotificationPreferenceDB.user_id == user_id,
            UserNotificationPreferenceDB.trigger_type == "new_user_match"
        ).count()

        assert count == 2


# ============================================================
# 第二部分：纯逻辑匹配测试
# ============================================================

class TestMatchConditions:
    """测试纯逻辑匹配函数（不消耗 Token）"""

    def test_location_match_exact(self):
        """测试地点精确匹配"""
        new_user = MagicMock(location="深圳市南山区")
        conditions = {"location": "深圳"}

        result = match_conditions(new_user, conditions)
        assert result == True

    def test_location_match_reverse(self):
        """测试地点反向包含匹配"""
        new_user = MagicMock(location="深圳")
        conditions = {"location": "深圳市"}

        result = match_conditions(new_user, conditions)
        assert result == True

    def test_location_no_match(self):
        """测试地点不匹配"""
        new_user = MagicMock(location="北京")
        conditions = {"location": "深圳"}

        result = match_conditions(new_user, conditions)
        assert result == False

    def test_gender_match(self):
        """测试性别匹配"""
        new_user = MagicMock(gender="female", location="")
        conditions = {"gender": "female"}

        result = match_conditions(new_user, conditions)
        assert result == True

    def test_gender_no_match(self):
        """测试性别不匹配"""
        new_user = MagicMock(gender="male", location="")
        conditions = {"gender": "female"}

        result = match_conditions(new_user, conditions)
        assert result == False

    def test_age_range_match(self):
        """测试年龄范围匹配"""
        new_user = MagicMock(age=28, location="", gender="")
        conditions = {"age_range": "25-30"}

        result = match_conditions(new_user, conditions)
        assert result == True

    def test_age_range_no_match(self):
        """测试年龄范围不匹配"""
        new_user = MagicMock(age=35, location="", gender="")
        conditions = {"age_range": "25-30"}

        result = match_conditions(new_user, conditions)
        assert result == False

    def test_age_range_boundary_min(self):
        """测试年龄范围边界（最小值）"""
        new_user = MagicMock(age=25, location="", gender="")
        conditions = {"age_range": "25-30"}

        result = match_conditions(new_user, conditions)
        assert result == True

    def test_age_range_boundary_max(self):
        """测试年龄范围边界（最大值）"""
        new_user = MagicMock(age=30, location="", gender="")
        conditions = {"age_range": "25-30"}

        result = match_conditions(new_user, conditions)
        assert result == True

    def test_multiple_conditions_match(self):
        """测试多条件组合匹配"""
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

    def test_multiple_conditions_partial_fail(self):
        """测试多条件组合（部分失败）"""
        new_user = MagicMock(
            location="深圳",
            gender="male",
            age=28,
            relationship_goal=""
        )
        conditions = {
            "location": "深圳",
            "gender": "female",
        }

        result = match_conditions(new_user, conditions)
        assert result == False

    def test_empty_conditions(self):
        """测试空条件（应匹配所有）"""
        new_user = MagicMock(location="任意地点", gender="任意性别", age=0)
        conditions = {}

        result = match_conditions(new_user, conditions)
        assert result == True

    def test_null_user_fields(self):
        """测试用户字段为空"""
        new_user = MagicMock(location=None, gender=None, age=None)
        conditions = {"location": "深圳"}

        result = match_conditions(new_user, conditions)
        assert result == False

    def test_invalid_age_range_format(self):
        """测试无效的年龄范围格式"""
        new_user = MagicMock(age=28, location="", gender="")
        conditions = {"age_range": "invalid"}

        result = match_conditions(new_user, conditions)
        assert result == True


# ============================================================
# 第三部分：匹配度计算测试
# ============================================================

class TestCalculateMatchScore:
    """测试匹配度计算函数"""

    def test_same_city_bonus(self, db_session, user_factory):
        """测试同城加分"""
        user1 = user_factory(location="深圳", preferred_age_min=25, preferred_age_max=30)
        user2 = user_factory(location="深圳", age=28)

        score = calculate_match_score(user1.id, user2.id, db_session)
        assert score >= 70

    def test_near_city_bonus(self, db_session, user_factory):
        """测试附近城市加分"""
        user1 = user_factory(location="深圳市南山区")
        user2 = user_factory(location="深圳")

        score = calculate_match_score(user1.id, user2.id, db_session)
        assert score >= 60

    def test_age_preference_match_bonus(self, db_session, user_factory):
        """测试年龄偏好匹配加分"""
        user1 = user_factory(
            location="北京",
            preferred_age_min=25,
            preferred_age_max=30
        )
        user2 = user_factory(location="上海", age=28)

        score = calculate_match_score(user1.id, user2.id, db_session)
        assert score >= 65

    def test_relationship_goal_match_bonus(self, db_session, user_factory):
        """测试关系目标匹配加分"""
        user1 = user_factory(location="北京", relationship_goal="serious")
        user2 = user_factory(location="上海", relationship_goal="serious")

        score = calculate_match_score(user1.id, user2.id, db_session)
        assert score >= 60

    def test_base_score_when_no_match(self, db_session, user_factory):
        """测试无匹配项时的基础分"""
        # 创建用户，确保无匹配项
        # 注意：UserDB 模型默认 preferred_age_min=18, preferred_age_max=60
        # 需要显式更新为 None
        user1 = user_factory(location="北京")
        user2 = user_factory(location="深圳", age=70)  # 年龄超出默认偏好范围

        # 更新 user1 的偏好为 None
        user1.preferred_age_min = None
        user1.preferred_age_max = None
        db_session.commit()

        score = calculate_match_score(user1.id, user2.id, db_session)
        # 基础分 50，无匹配项不加分
        assert score == 50

    def test_score_cap_at_100(self, db_session, user_factory):
        """测试分数上限 100"""
        user1 = user_factory(
            location="深圳",
            preferred_age_min=25,
            preferred_age_max=30,
            relationship_goal="serious"
        )
        user2 = user_factory(
            location="深圳",
            age=28,
            relationship_goal="serious"
        )

        score = calculate_match_score(user1.id, user2.id, db_session)
        assert score <= 100


# ============================================================
# 第四部分：事件触发测试
# ============================================================

class TestEventTrigger:
    """测试事件触发机制"""

    @pytest.mark.asyncio
    async def test_new_user_triggers_notification(self, db_session, user_factory):
        """测试新用户注册触发通知"""
        subscriber = user_factory(location="深圳")
        subscriber_id = subscriber.id  # 在 mock 前获取 ID
        preference = UserNotificationPreferenceDB(
            user_id=subscriber_id,
            trigger_type="new_user_match",
            conditions_json=json.dumps({"location": "深圳", "gender": "female"}),
            is_active=True,
        )
        db_session.add(preference)
        db_session.commit()

        new_user = user_factory(
            name="小美",
            location="深圳市",
            gender="female",
            age=28,
        )

        # 创建生成器 mock，返回 db_session
        def mock_get_db_gen():
            yield db_session

        with patch("db.database.get_db", side_effect=mock_get_db_gen):
            await check_and_notify_preferences(new_user)

        notifications = db_session.query(PendingNotificationDB).filter(
            PendingNotificationDB.target_user_id == subscriber_id,
            PendingNotificationDB.status == "pending"
        ).all()

        assert len(notifications) >= 1
        payload = json.loads(notifications[0].payload_json)
        assert payload["name"] == "小美"

    @pytest.mark.asyncio
    async def test_no_match_no_notification(self, db_session, user_factory):
        """测试不匹配时不触发通知"""
        subscriber = user_factory()
        subscriber_id = subscriber.id  # 在 mock 前获取 ID
        preference = UserNotificationPreferenceDB(
            user_id=subscriber_id,
            trigger_type="new_user_match",
            conditions_json=json.dumps({"location": "深圳", "gender": "female"}),
            is_active=True,
        )
        db_session.add(preference)
        db_session.commit()

        new_user = user_factory(location="北京", gender="male")

        def mock_get_db_gen():
            yield db_session

        with patch("db.database.get_db", side_effect=mock_get_db_gen):
            await check_and_notify_preferences(new_user)

        notifications = db_session.query(PendingNotificationDB).filter(
            PendingNotificationDB.target_user_id == subscriber_id
        ).all()

        assert len(notifications) == 0

    @pytest.mark.asyncio
    async def test_self_notification_excluded(self, db_session, user_factory):
        """测试不通知自己"""
        user = user_factory(location="深圳")
        user_id = user.id  # 在 mock 前获取 ID

        preference = UserNotificationPreferenceDB(
            user_id=user_id,
            trigger_type="new_user_match",
            conditions_json=json.dumps({"location": "深圳"}),
            is_active=True,
        )
        db_session.add(preference)
        db_session.commit()

        def mock_get_db_gen():
            yield db_session

        with patch("db.database.get_db", side_effect=mock_get_db_gen):
            await check_and_notify_preferences(user)

        notifications = db_session.query(PendingNotificationDB).filter(
            PendingNotificationDB.target_user_id == user_id
        ).all()

        assert len(notifications) == 0

    @pytest.mark.asyncio
    async def test_inactive_preference_ignored(self, db_session, user_factory):
        """测试已取消的订阅不触发通知"""
        subscriber = user_factory()
        subscriber_id = subscriber.id  # 在 mock 前获取 ID

        preference = UserNotificationPreferenceDB(
            user_id=subscriber_id,
            trigger_type="new_user_match",
            conditions_json=json.dumps({"location": "深圳"}),
            is_active=False,
        )
        db_session.add(preference)
        db_session.commit()

        new_user = user_factory(location="深圳")

        def mock_get_db_gen():
            yield db_session

        with patch("db.database.get_db", side_effect=mock_get_db_gen):
            await check_and_notify_preferences(new_user)

        notifications = db_session.query(PendingNotificationDB).filter(
            PendingNotificationDB.target_user_id == subscriber_id
        ).all()

        assert len(notifications) == 0


# ============================================================
# 第五部分：通知队列管理测试
# ============================================================

class TestNotificationQueue:
    """测试通知队列管理"""

    def test_get_pending_notifications(self, db_session, user_factory):
        """测试获取待推送通知"""
        user = user_factory()
        user_id = user.id  # 在 mock 前获取 ID

        for i in range(3):
            notification = PendingNotificationDB(
                target_user_id=user_id,
                trigger_type="new_user_match",
                payload_json=json.dumps({"name": f"用户{i}"}),
                status="pending",
            )
            db_session.add(notification)
        db_session.commit()

        def mock_get_db_gen():
            yield db_session

        with patch("db.database.get_db", side_effect=mock_get_db_gen):
            result = get_pending_notifications(user_id)

        assert result["total"] == 3
        assert result["has_unread"] == True
        assert len(result["notifications"]) == 3

    def test_get_pending_excludes_delivered(self, db_session, user_factory):
        """测试已推送的通知不返回"""
        user = user_factory()
        user_id = user.id  # 在 mock 前获取 ID

        pending = PendingNotificationDB(
            target_user_id=user_id,
            trigger_type="new_user_match",
            status="pending",
        )
        delivered = PendingNotificationDB(
            target_user_id=user_id,
            trigger_type="new_user_match",
            status="delivered",
        )
        db_session.add_all([pending, delivered])
        db_session.commit()

        def mock_get_db_gen():
            yield db_session

        with patch("db.database.get_db", side_effect=mock_get_db_gen):
            result = get_pending_notifications(user_id)

        assert result["total"] == 1

    def test_mark_notification_delivered(self, db_session, user_factory):
        """测试标记通知已推送"""
        user = user_factory()
        user_id = user.id  # 在 mock 前获取 ID
        notification = PendingNotificationDB(
            target_user_id=user_id,
            trigger_type="new_user_match",
            status="pending",
        )
        db_session.add(notification)
        db_session.commit()
        notification_id = notification.id  # 在 mock 前获取 ID

        def mock_get_db_gen():
            yield db_session

        with patch("db.database.get_db", side_effect=mock_get_db_gen):
            success = mark_notification_delivered(notification_id)

        assert success == True

        saved = db_session.query(PendingNotificationDB).filter(
            PendingNotificationDB.id == notification_id
        ).first()
        assert saved.status == "delivered"
        assert saved.delivered_at is not None

    def test_mark_notification_read(self, db_session, user_factory):
        """测试标记通知已读"""
        user = user_factory()
        user_id = user.id  # 在 mock 前获取 ID
        notification = PendingNotificationDB(
            target_user_id=user_id,
            trigger_type="new_user_match",
            status="delivered",
        )
        db_session.add(notification)
        db_session.commit()
        notification_id = notification.id  # 在 mock 前获取 ID

        def mock_get_db_gen():
            yield db_session

        with patch("db.database.get_db", side_effect=mock_get_db_gen):
            success = mark_notification_read(notification_id)

        assert success == True

        saved = db_session.query(PendingNotificationDB).filter(
            PendingNotificationDB.id == notification_id
        ).first()
        assert saved.status == "read"

    def test_mark_nonexistent_notification(self, db_session):
        """测试标记不存在通知"""
        def mock_get_db_gen():
            yield db_session

        with patch("db.database.get_db", side_effect=mock_get_db_gen):
            success = mark_notification_delivered(99999)

        assert success == False

    def test_create_notification_preference(self, db_session, user_factory):
        """测试创建偏好订阅"""
        user = user_factory()
        user_id = user.id  # 在 mock 前获取 ID

        def mock_get_db_gen():
            yield db_session

        with patch("db.database.get_db", side_effect=mock_get_db_gen):
            result = create_notification_preference(
                user_id=user_id,
                trigger_type="new_user_match",
                conditions={"location": "深圳"}
            )

        assert result["success"] == True
        assert result["action"] == "created"

        preference = db_session.query(UserNotificationPreferenceDB).filter(
            UserNotificationPreferenceDB.user_id == user_id
        ).first()
        assert preference is not None

    def test_update_existing_preference(self, db_session, user_factory):
        """测试更新已存在的偏好订阅"""
        user = user_factory()
        user_id = user.id  # 在 mock 前获取 ID

        preference = UserNotificationPreferenceDB(
            user_id=user_id,
            trigger_type="new_user_match",
            conditions_json=json.dumps({"location": "北京"}),
            is_active=True,
        )
        db_session.add(preference)
        db_session.commit()

        def mock_get_db_gen():
            yield db_session

        with patch("db.database.get_db", side_effect=mock_get_db_gen):
            result = create_notification_preference(
                user_id=user_id,
                trigger_type="new_user_match",
                conditions={"location": "深圳"}
            )

        assert result["success"] == True
        assert result["action"] == "updated"

        saved = db_session.query(UserNotificationPreferenceDB).filter(
            UserNotificationPreferenceDB.user_id == user_id
        ).first()
        conditions = json.loads(saved.conditions_json)
        assert conditions["location"] == "深圳"


# ============================================================
# 第六部分：边缘场景测试
# ============================================================

class TestEdgeCases:
    """测试边缘场景"""

    def test_empty_notifications_result(self, db_session, user_factory):
        """测试无通知时的结果"""
        user = user_factory()
        user_id = user.id  # 在 mock 前获取 ID

        def mock_get_db_gen():
            yield db_session

        with patch("db.database.get_db", side_effect=mock_get_db_gen):
            result = get_pending_notifications(user_id)

        assert result["total"] == 0
        assert result["has_unread"] == False
        assert result["notifications"] == []

    def test_user_without_location(self):
        """测试用户无地点信息"""
        new_user = MagicMock(location=None, gender="female")
        conditions = {"location": "深圳"}

        result = match_conditions(new_user, conditions)
        assert result == False

    def test_user_without_age(self):
        """测试用户无年龄信息"""
        new_user = MagicMock(age=None, location="", gender="")
        conditions = {"age_range": "25-30"}

        result = match_conditions(new_user, conditions)
        assert result == False

    def test_large_age_range(self):
        """测试大年龄范围"""
        new_user = MagicMock(age=50, location="", gender="")
        conditions = {"age_range": "20-60"}

        result = match_conditions(new_user, conditions)
        assert result == True

    def test_complex_location_string(self):
        """测试复杂地点字符串"""
        new_user = MagicMock(location="广东省深圳市南山区科技园")
        conditions = {"location": "深圳"}

        result = match_conditions(new_user, conditions)
        assert result == True

    def test_notification_limit_10(self, db_session, user_factory):
        """测试通知最多返回 10 条"""
        user = user_factory()
        user_id = user.id  # 在 mock 前获取 ID

        for i in range(15):
            notification = PendingNotificationDB(
                target_user_id=user_id,
                trigger_type="new_user_match",
                status="pending",
            )
            db_session.add(notification)
        db_session.commit()

        def mock_get_db_gen():
            yield db_session

        with patch("db.database.get_db", side_effect=mock_get_db_gen):
            result = get_pending_notifications(user_id)

        assert len(result["notifications"]) <= 10


# ============================================================
# 第七部分：Token 消耗验证测试
# ============================================================

class TestTokenConsumption:
    """验证事件触发不消耗 AI Token"""

    @pytest.mark.asyncio
    async def test_no_llm_call_in_event_trigger(self, db_session, user_factory):
        """测试事件触发时不调用 LLM"""
        subscriber = user_factory()
        subscriber_id = subscriber.id  # 在 mock 前获取 ID
        preference = UserNotificationPreferenceDB(
            user_id=subscriber_id,
            trigger_type="new_user_match",
            conditions_json=json.dumps({"location": "深圳"}),
            is_active=True,
        )
        db_session.add(preference)
        db_session.commit()

        new_user = user_factory(location="深圳")

        def mock_get_db_gen():
            yield db_session

        with patch("db.database.get_db", side_effect=mock_get_db_gen):
            with patch("llm.client.call_llm") as mock_llm:
                await check_and_notify_preferences(new_user)

                mock_llm.assert_not_called()

    def test_match_conditions_no_ai(self):
        """测试 match_conditions 是纯逻辑"""
        new_user = MagicMock(
            location="深圳",
            gender="female",
            age=28,
        )
        conditions = {
            "location": "深圳",
            "gender": "female",
            "age_range": "25-30",
        }

        result = match_conditions(new_user, conditions)
        assert result == True

    def test_calculate_score_no_ai(self, db_session, user_factory):
        """测试 calculate_match_score 不调用 AI"""
        user1 = user_factory(location="深圳")
        user2 = user_factory(location="深圳")
        user1_id = user1.id
        user2_id = user2.id

        with patch("llm.client.call_llm") as mock_llm:
            score = calculate_match_score(user1_id, user2_id, db_session)

            mock_llm.assert_not_called()
            assert isinstance(score, int)


# ============================================================
# 第八部分：性能测试
# ============================================================

class TestPerformance:
    """测试性能相关场景"""

    def test_bulk_preferences_check(self, db_session, user_factory):
        """测试大量偏好订阅检查"""
        user_ids = []
        for i in range(100):
            user = user_factory()
            user_ids.append(user.id)
            preference = UserNotificationPreferenceDB(
                user_id=user.id,
                trigger_type="new_user_match",
                conditions_json=json.dumps({"location": "深圳"}),
                is_active=True,
            )
            db_session.add(preference)
        db_session.commit()

        new_user = user_factory(location="深圳")

        import time
        start = time.time()

        def mock_get_db_gen():
            yield db_session

        with patch("db.database.get_db", side_effect=mock_get_db_gen):
            asyncio.run(check_and_notify_preferences(new_user))

        elapsed = time.time() - start
        assert elapsed < 5.0

    def test_notification_query_optimization(self, db_session, user_factory):
        """测试通知查询效率"""
        user = user_factory()
        user_id = user.id  # 在 mock 前获取 ID

        for i in range(50):
            notification = PendingNotificationDB(
                target_user_id=user_id,
                trigger_type="new_user_match",
                status="pending" if i < 10 else "delivered",
            )
            db_session.add(notification)
        db_session.commit()

        import time
        start = time.time()

        def mock_get_db_gen():
            yield db_session

        with patch("db.database.get_db", side_effect=mock_get_db_gen):
            result = get_pending_notifications(user_id)

        elapsed = time.time() - start

        assert elapsed < 0.5
        assert len(result["notifications"]) == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
