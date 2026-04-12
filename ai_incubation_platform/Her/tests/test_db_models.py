"""
数据库模型 CRUD 测试

测试覆盖:
1. UserDB - 用户模型 CRUD (4 tests)
2. MatchHistoryDB - 匹配历史模型 CRUD (4 tests)
3. ChatMessageDB - 聊天消息模型 CRUD (4 tests)
4. ChatConversationDB - 聊天会话模型 CRUD (4 tests)
5. PhotoDB - 照片管理模型 CRUD (4 tests)
6. IdentityVerificationDB - 身份认证模型 CRUD (4 tests)
7. VerificationBadgeDB - 信任徽章模型 CRUD (4 tests)
8. VideoDateDB - 视频约会模型 CRUD (4 tests)
9. UserMembershipDB - 会员状态模型 CRUD (4 tests)
10. MembershipOrderDB - 订单模型 CRUD (4 tests)
11. UserReportDB - 举报记录模型 CRUD (4 tests)
12. SafetyZoneDB - 安全区域模型 CRUD (4 tests)
13. TrustedContactDB - 紧急联系人模型 CRUD (4 tests)
14. FeatureFlagDB - 灰度配置模型 CRUD (4 tests)
15. ABExperimentDB - A/B 实验模型 CRUD (4 tests)

总计: 60 个测试用例
"""
import pytest
import uuid
import json
from datetime import datetime, timedelta

from db.models import (
    UserDB,
    MatchHistoryDB,
    ChatMessageDB,
    ChatConversationDB,
    PhotoDB,
    IdentityVerificationDB,
    VerificationBadgeDB,
    VideoDateDB,
    UserMembershipDB,
    MembershipOrderDB,
    UserReportDB,
    SafetyZoneDB,
    TrustedContactDB,
    FeatureFlagDB,
    ABExperimentDB,
)


# ============= 辅助函数 =============

def generate_uuid() -> str:
    """生成 UUID 字符串"""
    return str(uuid.uuid4())


def make_user(**kwargs) -> UserDB:
    """创建测试用户"""
    defaults = {
        "id": generate_uuid(),
        "name": "测试用户",
        "email": f"test_{uuid.uuid4().hex[:8]}@example.com",
        "password_hash": "hashed_password_123",
        "age": 28,
        "gender": "male",
        "location": "北京市",
        "interests": "[]",
        "values": "{}",
        "bio": "",
    }
    defaults.update(kwargs)
    return UserDB(**defaults)


def make_match_history(**kwargs) -> MatchHistoryDB:
    """创建测试匹配历史"""
    defaults = {
        "id": generate_uuid(),
        "user_id_1": generate_uuid(),
        "user_id_2": generate_uuid(),
        "compatibility_score": 0.85,
        "status": "pending",
        "match_reasoning": "兴趣相投",
        "common_interests": "[]",
        "score_breakdown": "{}",
    }
    defaults.update(kwargs)
    return MatchHistoryDB(**defaults)


def make_chat_message(**kwargs) -> ChatMessageDB:
    """创建测试聊天消息"""
    defaults = {
        "id": generate_uuid(),
        "conversation_id": generate_uuid(),
        "sender_id": generate_uuid(),
        "receiver_id": generate_uuid(),
        "message_type": "text",
        "content": "你好，很高兴认识你！",
        "status": "sent",
        "is_read": False,
    }
    defaults.update(kwargs)
    return ChatMessageDB(**defaults)


def make_chat_conversation(**kwargs) -> ChatConversationDB:
    """创建测试聊天会话"""
    defaults = {
        "id": generate_uuid(),
        "user_id_1": generate_uuid(),
        "user_id_2": generate_uuid(),
        "status": "active",
        "last_message_preview": "你好",
    }
    defaults.update(kwargs)
    return ChatConversationDB(**defaults)


def make_photo(**kwargs) -> PhotoDB:
    """创建测试照片"""
    defaults = {
        "id": generate_uuid(),
        "user_id": generate_uuid(),
        "photo_url": "https://example.com/photo.jpg",
        "photo_type": "profile",
        "display_order": 0,
        "moderation_status": "pending",
        "ai_tags": "[]",
    }
    defaults.update(kwargs)
    return PhotoDB(**defaults)


def make_identity_verification(**kwargs) -> IdentityVerificationDB:
    """创建测试身份认证"""
    defaults = {
        "id": generate_uuid(),
        "user_id": generate_uuid(),
        "real_name": "张三",
        "id_number": "encrypted_id_number",
        "id_number_hash": "hash_value_123",
        "verification_status": "pending",
        "verification_type": "basic",
    }
    defaults.update(kwargs)
    return IdentityVerificationDB(**defaults)


def make_verification_badge(**kwargs) -> VerificationBadgeDB:
    """创建测试信任徽章"""
    defaults = {
        "id": generate_uuid(),
        "user_id": generate_uuid(),
        "badge_type": "identity_verified",
        "status": "active",
        "verification_data": "{}",
        "display_order": 10,
    }
    defaults.update(kwargs)
    return VerificationBadgeDB(**defaults)


def make_video_date(**kwargs) -> VideoDateDB:
    """创建测试视频约会"""
    defaults = {
        "id": generate_uuid(),
        "user_id_1": generate_uuid(),
        "user_id_2": generate_uuid(),
        "status": "scheduled",
        "scheduled_time": datetime.now() + timedelta(days=1),
        "duration_minutes": 30,
        "theme": "初次见面",
        "room_id": f"room_{uuid.uuid4().hex[:8]}",
        "background": "default",
    }
    defaults.update(kwargs)
    return VideoDateDB(**defaults)


def make_user_membership(**kwargs) -> UserMembershipDB:
    """创建测试会员状态"""
    defaults = {
        "id": generate_uuid(),
        "user_id": generate_uuid(),
        "tier": "free",
        "status": "inactive",
        "auto_renew": False,
    }
    defaults.update(kwargs)
    return UserMembershipDB(**defaults)


def make_membership_order(**kwargs) -> MembershipOrderDB:
    """创建测试订单"""
    defaults = {
        "id": generate_uuid(),
        "user_id": generate_uuid(),
        "tier": "premium",
        "duration_months": 12,
        "amount": 299.0,
        "original_amount": 399.0,
        "status": "pending",
    }
    defaults.update(kwargs)
    return MembershipOrderDB(**defaults)


def make_user_report(**kwargs) -> UserReportDB:
    """创建测试举报记录"""
    defaults = {
        "id": generate_uuid(),
        "reporter_id": generate_uuid(),
        "reported_user_id": generate_uuid(),
        "report_type": "inappropriate_behavior",
        "reason": "不当言行",
        "description": "用户在聊天中发送不当内容",
        "status": "pending",
        "priority": 1,
    }
    defaults.update(kwargs)
    return UserReportDB(**defaults)


def make_safety_zone(**kwargs) -> SafetyZoneDB:
    """创建测试安全区域"""
    defaults = {
        "id": generate_uuid(),
        "zone_type": "safe",
        "name": "市中心商圈",
        "latitude": 39.9042,
        "longitude": 116.4074,
        "radius": 500,
        "description": "安全区域",
        "is_active": True,
    }
    defaults.update(kwargs)
    return SafetyZoneDB(**defaults)


def make_trusted_contact(**kwargs) -> TrustedContactDB:
    """创建测试紧急联系人"""
    defaults = {
        "id": generate_uuid(),
        "user_id": generate_uuid(),
        "name": "紧急联系人",
        "phone": "13800138000",
        "relationship": "家人",
        "can_view_location": True,
        "can_receive_emergency": True,
        "display_order": 0,
    }
    defaults.update(kwargs)
    return TrustedContactDB(**defaults)


def make_feature_flag(**kwargs) -> FeatureFlagDB:
    """创建测试灰度配置"""
    defaults = {
        "id": generate_uuid(),
        "flag_key": f"feature_{uuid.uuid4().hex[:8]}",
        "name": "新功能开关",
        "description": "测试灰度功能",
        "is_enabled": False,
        "rollout_percentage": 0,
        "target_user_groups": [],
        "target_cities": [],
        "config_data": {},
    }
    defaults.update(kwargs)
    return FeatureFlagDB(**defaults)


def make_ab_experiment(**kwargs) -> ABExperimentDB:
    """创建测试 A/B 实验"""
    defaults = {
        "id": generate_uuid(),
        "experiment_key": f"exp_{uuid.uuid4().hex[:8]}",
        "name": "按钮颜色实验",
        "description": "测试不同按钮颜色对转化率的影响",
        "status": "draft",
        "variants": [
            {"name": "A", "weight": 50, "config": {"color": "blue"}},
            {"name": "B", "weight": 50, "config": {"color": "red"}}
        ],
        "primary_metric": "click_rate",
        "secondary_metrics": ["conversion_rate"],
        "traffic_allocation": 100,
    }
    defaults.update(kwargs)
    return ABExperimentDB(**defaults)


# ============= 第一部分：UserDB CRUD 测试 =============

class TestUserDBCRUD:
    """用户模型 CRUD 测试"""

    def test_create_user(self, db_session):
        """测试创建用户"""
        user = make_user(id="user_create_1", email="create_user@example.com")
        db_session.add(user)
        db_session.commit()

        # 验证创建成功
        saved = db_session.query(UserDB).filter(UserDB.id == "user_create_1").first()
        assert saved is not None
        assert saved.name == "测试用户"
        assert saved.email == "create_user@example.com"
        assert saved.age == 28
        assert saved.gender == "male"
        assert saved.location == "北京市"
        assert saved.is_active is True
        assert saved.created_at is not None

    def test_read_user(self, db_session):
        """测试查询用户"""
        user = make_user(id="user_read_1", name="查询测试用户")
        db_session.add(user)
        db_session.commit()

        # 按 ID 查询
        found_by_id = db_session.query(UserDB).filter(UserDB.id == "user_read_1").first()
        assert found_by_id is not None
        assert found_by_id.name == "查询测试用户"

        # 按 email 查询
        found_by_email = db_session.query(UserDB).filter(
            UserDB.email == user.email
        ).first()
        assert found_by_email is not None
        assert found_by_email.id == "user_read_1"

        # 查询不存在用户
        not_found = db_session.query(UserDB).filter(UserDB.id == "nonexistent").first()
        assert not_found is None

    def test_update_user(self, db_session):
        """测试更新用户"""
        user = make_user(id="user_update_1", name="原始用户", age=25)
        db_session.add(user)
        db_session.commit()

        # 更新用户信息
        user.name = "更新后用户"
        user.age = 30
        user.location = "上海市"
        user.bio = "这是更新后的简介"
        db_session.commit()

        # 验证更新成功
        updated = db_session.query(UserDB).filter(UserDB.id == "user_update_1").first()
        assert updated.name == "更新后用户"
        assert updated.age == 30
        assert updated.location == "上海市"
        assert updated.bio == "这是更新后的简介"
        assert updated.updated_at is not None

    def test_delete_user(self, db_session):
        """测试删除用户"""
        user = make_user(id="user_delete_1")
        db_session.add(user)
        db_session.commit()

        # 验证用户存在
        existing = db_session.query(UserDB).filter(UserDB.id == "user_delete_1").first()
        assert existing is not None

        # 删除用户
        db_session.delete(user)
        db_session.commit()

        # 验证用户已删除
        deleted = db_session.query(UserDB).filter(UserDB.id == "user_delete_1").first()
        assert deleted is None


# ============= 第二部分：MatchHistoryDB CRUD 测试 =============

class TestMatchHistoryDBCRUD:
    """匹配历史模型 CRUD 测试"""

    def test_create_match_history(self, db_session):
        """测试创建匹配历史"""
        user1 = make_user(id="match_user_1")
        user2 = make_user(id="match_user_2")
        db_session.add_all([user1, user2])
        db_session.commit()

        match = make_match_history(
            id="match_create_1",
            user_id_1="match_user_1",
            user_id_2="match_user_2",
            compatibility_score=0.92,
            match_reasoning="价值观高度匹配",
        )
        db_session.add(match)
        db_session.commit()

        # 验证创建成功
        saved = db_session.query(MatchHistoryDB).filter(
            MatchHistoryDB.id == "match_create_1"
        ).first()
        assert saved is not None
        assert saved.user_id_1 == "match_user_1"
        assert saved.user_id_2 == "match_user_2"
        assert saved.compatibility_score == 0.92
        assert saved.status == "pending"
        assert saved.interaction_count == 0
        assert saved.relationship_stage == "matched"

    def test_read_match_history(self, db_session):
        """测试查询匹配历史"""
        match = make_match_history(
            id="match_read_1",
            user_id_1="reader_1",
            user_id_2="reader_2",
        )
        db_session.add(match)
        db_session.commit()

        # 按 ID 查询
        found = db_session.query(MatchHistoryDB).filter(
            MatchHistoryDB.id == "match_read_1"
        ).first()
        assert found is not None

        # 按用户查询
        by_user1 = db_session.query(MatchHistoryDB).filter(
            MatchHistoryDB.user_id_1 == "reader_1"
        ).all()
        assert len(by_user1) == 1

        # 按状态查询
        pending_matches = db_session.query(MatchHistoryDB).filter(
            MatchHistoryDB.status == "pending"
        ).all()
        assert len(pending_matches) >= 1

    def test_update_match_history(self, db_session):
        """测试更新匹配历史"""
        match = make_match_history(
            id="match_update_1",
            status="pending",
            interaction_count=0,
        )
        db_session.add(match)
        db_session.commit()

        # 更新状态和交互次数
        match.status = "accepted"
        match.interaction_count = 5
        match.relationship_stage = "chatting"
        match.last_interaction_at = datetime.now()
        db_session.commit()

        # 验证更新成功
        updated = db_session.query(MatchHistoryDB).filter(
            MatchHistoryDB.id == "match_update_1"
        ).first()
        assert updated.status == "accepted"
        assert updated.interaction_count == 5
        assert updated.relationship_stage == "chatting"
        assert updated.last_interaction_at is not None

    def test_delete_match_history(self, db_session):
        """测试删除匹配历史"""
        match = make_match_history(id="match_delete_1")
        db_session.add(match)
        db_session.commit()

        # 删除
        db_session.delete(match)
        db_session.commit()

        # 验证已删除
        deleted = db_session.query(MatchHistoryDB).filter(
            MatchHistoryDB.id == "match_delete_1"
        ).first()
        assert deleted is None


# ============= 第三部分：ChatMessageDB CRUD 测试 =============

class TestChatMessageDBCRUD:
    """聊天消息模型 CRUD 测试"""

    def test_create_chat_message(self, db_session):
        """测试创建聊天消息"""
        sender = make_user(id="sender_1")
        receiver = make_user(id="receiver_1")
        db_session.add_all([sender, receiver])
        db_session.commit()

        message = make_chat_message(
            id="msg_create_1",
            sender_id="sender_1",
            receiver_id="receiver_1",
            content="你好，想和你聊聊",
        )
        db_session.add(message)
        db_session.commit()

        # 验证创建成功
        saved = db_session.query(ChatMessageDB).filter(
            ChatMessageDB.id == "msg_create_1"
        ).first()
        assert saved is not None
        assert saved.sender_id == "sender_1"
        assert saved.receiver_id == "receiver_1"
        assert saved.content == "你好，想和你聊聊"
        assert saved.message_type == "text"
        assert saved.status == "sent"
        assert saved.is_read is False

    def test_read_chat_message(self, db_session):
        """测试查询聊天消息"""
        message = make_chat_message(
            id="msg_read_1",
            conversation_id="conv_123",
        )
        db_session.add(message)
        db_session.commit()

        # 按 ID 查询
        found = db_session.query(ChatMessageDB).filter(
            ChatMessageDB.id == "msg_read_1"
        ).first()
        assert found is not None

        # 按会话查询
        by_conv = db_session.query(ChatMessageDB).filter(
            ChatMessageDB.conversation_id == "conv_123"
        ).all()
        assert len(by_conv) == 1

        # 按发送者查询
        by_sender = db_session.query(ChatMessageDB).filter(
            ChatMessageDB.sender_id == message.sender_id
        ).all()
        assert len(by_sender) == 1

    def test_update_chat_message(self, db_session):
        """测试更新聊天消息"""
        message = make_chat_message(
            id="msg_update_1",
            status="sent",
            is_read=False,
        )
        db_session.add(message)
        db_session.commit()

        # 更新消息状态
        message.status = "read"
        message.is_read = True
        message.read_at = datetime.now()
        db_session.commit()

        # 验证更新成功
        updated = db_session.query(ChatMessageDB).filter(
            ChatMessageDB.id == "msg_update_1"
        ).first()
        assert updated.status == "read"
        assert updated.is_read is True
        assert updated.read_at is not None

    def test_delete_chat_message(self, db_session):
        """测试删除聊天消息"""
        message = make_chat_message(id="msg_delete_1")
        db_session.add(message)
        db_session.commit()

        # 删除
        db_session.delete(message)
        db_session.commit()

        # 验证已删除
        deleted = db_session.query(ChatMessageDB).filter(
            ChatMessageDB.id == "msg_delete_1"
        ).first()
        assert deleted is None


# ============= 第四部分：ChatConversationDB CRUD 测试 =============

class TestChatConversationDBCRUD:
    """聊天会话模型 CRUD 测试"""

    def test_create_chat_conversation(self, db_session):
        """测试创建聊天会话"""
        user1 = make_user(id="conv_user_1")
        user2 = make_user(id="conv_user_2")
        db_session.add_all([user1, user2])
        db_session.commit()

        conversation = make_chat_conversation(
            id="conv_create_1",
            user_id_1="conv_user_1",
            user_id_2="conv_user_2",
        )
        db_session.add(conversation)
        db_session.commit()

        # 验证创建成功
        saved = db_session.query(ChatConversationDB).filter(
            ChatConversationDB.id == "conv_create_1"
        ).first()
        assert saved is not None
        assert saved.user_id_1 == "conv_user_1"
        assert saved.user_id_2 == "conv_user_2"
        assert saved.status == "active"
        assert saved.unread_count_user1 == 0
        assert saved.unread_count_user2 == 0

    def test_read_chat_conversation(self, db_session):
        """测试查询聊天会话"""
        conversation = make_chat_conversation(
            id="conv_read_1",
            user_id_1="reader_a",
            user_id_2="reader_b",
        )
        db_session.add(conversation)
        db_session.commit()

        # 按 ID 查询
        found = db_session.query(ChatConversationDB).filter(
            ChatConversationDB.id == "conv_read_1"
        ).first()
        assert found is not None

        # 按用户查询
        by_user = db_session.query(ChatConversationDB).filter(
            ChatConversationDB.user_id_1 == "reader_a"
        ).all()
        assert len(by_user) == 1

        # 查询活跃会话
        active = db_session.query(ChatConversationDB).filter(
            ChatConversationDB.status == "active"
        ).all()
        assert len(active) >= 1

    def test_update_chat_conversation(self, db_session):
        """测试更新聊天会话"""
        conversation = make_chat_conversation(
            id="conv_update_1",
            unread_count_user1=0,
            unread_count_user2=0,
        )
        db_session.add(conversation)
        db_session.commit()

        # 更新会话
        conversation.unread_count_user1 = 3
        conversation.unread_count_user2 = 1
        conversation.last_message_at = datetime.now()
        conversation.last_message_preview = "最新消息预览"
        db_session.commit()

        # 验证更新成功
        updated = db_session.query(ChatConversationDB).filter(
            ChatConversationDB.id == "conv_update_1"
        ).first()
        assert updated.unread_count_user1 == 3
        assert updated.unread_count_user2 == 1
        assert updated.last_message_preview == "最新消息预览"

    def test_delete_chat_conversation(self, db_session):
        """测试删除聊天会话"""
        conversation = make_chat_conversation(id="conv_delete_1")
        db_session.add(conversation)
        db_session.commit()

        # 删除
        db_session.delete(conversation)
        db_session.commit()

        # 验证已删除
        deleted = db_session.query(ChatConversationDB).filter(
            ChatConversationDB.id == "conv_delete_1"
        ).first()
        assert deleted is None


# ============= 第五部分：PhotoDB CRUD 测试 =============

class TestPhotoDBCRUD:
    """照片管理模型 CRUD 测试"""

    def test_create_photo(self, db_session):
        """测试创建照片"""
        user = make_user(id="photo_user_1")
        db_session.add(user)
        db_session.commit()

        photo = make_photo(
            id="photo_create_1",
            user_id="photo_user_1",
            photo_url="https://example.com/photo1.jpg",
            display_order=0,
        )
        db_session.add(photo)
        db_session.commit()

        # 验证创建成功
        saved = db_session.query(PhotoDB).filter(PhotoDB.id == "photo_create_1").first()
        assert saved is not None
        assert saved.user_id == "photo_user_1"
        assert saved.photo_url == "https://example.com/photo1.jpg"
        assert saved.photo_type == "profile"
        assert saved.display_order == 0
        assert saved.moderation_status == "pending"
        assert saved.is_active is True

    def test_read_photo(self, db_session):
        """测试查询照片"""
        photo = make_photo(id="photo_read_1", user_id="photo_reader")
        db_session.add(photo)
        db_session.commit()

        # 按 ID 查询
        found = db_session.query(PhotoDB).filter(PhotoDB.id == "photo_read_1").first()
        assert found is not None

        # 按用户查询
        by_user = db_session.query(PhotoDB).filter(
            PhotoDB.user_id == "photo_reader"
        ).all()
        assert len(by_user) == 1

        # 查询待审核照片
        pending = db_session.query(PhotoDB).filter(
            PhotoDB.moderation_status == "pending"
        ).all()
        assert len(pending) >= 1

    def test_update_photo(self, db_session):
        """测试更新照片"""
        photo = make_photo(
            id="photo_update_1",
            moderation_status="pending",
            like_count=0,
            view_count=0,
        )
        db_session.add(photo)
        db_session.commit()

        # 更新照片审核状态和统计
        photo.moderation_status = "approved"
        photo.moderated_at = datetime.now()
        photo.moderated_by = "ai"
        photo.like_count = 10
        photo.view_count = 100
        photo.ai_quality_score = 0.85
        db_session.commit()

        # 验证更新成功
        updated = db_session.query(PhotoDB).filter(PhotoDB.id == "photo_update_1").first()
        assert updated.moderation_status == "approved"
        assert updated.like_count == 10
        assert updated.view_count == 100
        assert updated.ai_quality_score == 0.85

    def test_delete_photo(self, db_session):
        """测试删除照片"""
        photo = make_photo(id="photo_delete_1")
        db_session.add(photo)
        db_session.commit()

        # 删除
        db_session.delete(photo)
        db_session.commit()

        # 验证已删除
        deleted = db_session.query(PhotoDB).filter(PhotoDB.id == "photo_delete_1").first()
        assert deleted is None


# ============= 第六部分：IdentityVerificationDB CRUD 测试 =============

class TestIdentityVerificationDBCRUD:
    """身份认证模型 CRUD 测试"""

    def test_create_identity_verification(self, db_session):
        """测试创建身份认证"""
        user = make_user(id="id_verify_user_1")
        db_session.add(user)
        db_session.commit()

        verification = make_identity_verification(
            id="id_verify_create_1",
            user_id="id_verify_user_1",
            real_name="李四",
            id_number_hash="hash_abc123",
        )
        db_session.add(verification)
        db_session.commit()

        # 验证创建成功
        saved = db_session.query(IdentityVerificationDB).filter(
            IdentityVerificationDB.id == "id_verify_create_1"
        ).first()
        assert saved is not None
        assert saved.user_id == "id_verify_user_1"
        assert saved.real_name == "李四"
        assert saved.verification_status == "pending"
        assert saved.verification_type == "basic"

    def test_read_identity_verification(self, db_session):
        """测试查询身份认证"""
        verification = make_identity_verification(
            id="id_verify_read_1",
            user_id="id_reader",
        )
        db_session.add(verification)
        db_session.commit()

        # 按 ID 查询
        found = db_session.query(IdentityVerificationDB).filter(
            IdentityVerificationDB.id == "id_verify_read_1"
        ).first()
        assert found is not None

        # 按用户查询（唯一约束）
        by_user = db_session.query(IdentityVerificationDB).filter(
            IdentityVerificationDB.user_id == "id_reader"
        ).first()
        assert by_user is not None

        # 查询待审核
        pending = db_session.query(IdentityVerificationDB).filter(
            IdentityVerificationDB.verification_status == "pending"
        ).all()
        assert len(pending) >= 1

    def test_update_identity_verification(self, db_session):
        """测试更新身份认证"""
        verification = make_identity_verification(
            id="id_verify_update_1",
            verification_status="pending",
        )
        db_session.add(verification)
        db_session.commit()

        # 更新认证状态
        verification.verification_status = "verified"
        verification.verified_at = datetime.now()
        verification.face_similarity_score = 0.95
        verification.verification_badge = "verified"
        db_session.commit()

        # 验证更新成功
        updated = db_session.query(IdentityVerificationDB).filter(
            IdentityVerificationDB.id == "id_verify_update_1"
        ).first()
        assert updated.verification_status == "verified"
        assert updated.verified_at is not None
        assert updated.face_similarity_score == 0.95

    def test_delete_identity_verification(self, db_session):
        """测试删除身份认证"""
        verification = make_identity_verification(id="id_verify_delete_1")
        db_session.add(verification)
        db_session.commit()

        # 删除
        db_session.delete(verification)
        db_session.commit()

        # 验证已删除
        deleted = db_session.query(IdentityVerificationDB).filter(
            IdentityVerificationDB.id == "id_verify_delete_1"
        ).first()
        assert deleted is None


# ============= 第七部分：VerificationBadgeDB CRUD 测试 =============

class TestVerificationBadgeDBCRUD:
    """信任徽章模型 CRUD 测试"""

    def test_create_verification_badge(self, db_session):
        """测试创建信任徽章"""
        user = make_user(id="badge_user_1")
        db_session.add(user)
        db_session.commit()

        badge = make_verification_badge(
            id="badge_create_1",
            user_id="badge_user_1",
            badge_type="identity_verified",
            display_order=1,
        )
        db_session.add(badge)
        db_session.commit()

        # 验证创建成功
        saved = db_session.query(VerificationBadgeDB).filter(
            VerificationBadgeDB.id == "badge_create_1"
        ).first()
        assert saved is not None
        assert saved.user_id == "badge_user_1"
        assert saved.badge_type == "identity_verified"
        assert saved.status == "active"
        assert saved.display_order == 1

    def test_read_verification_badge(self, db_session):
        """测试查询信任徽章"""
        badge = make_verification_badge(
            id="badge_read_1",
            user_id="badge_reader",
            badge_type="phone_verified",
        )
        db_session.add(badge)
        db_session.commit()

        # 按 ID 查询
        found = db_session.query(VerificationBadgeDB).filter(
            VerificationBadgeDB.id == "badge_read_1"
        ).first()
        assert found is not None

        # 按用户查询
        by_user = db_session.query(VerificationBadgeDB).filter(
            VerificationBadgeDB.user_id == "badge_reader"
        ).all()
        assert len(by_user) == 1

        # 按徽章类型查询
        by_type = db_session.query(VerificationBadgeDB).filter(
            VerificationBadgeDB.badge_type == "phone_verified"
        ).all()
        assert len(by_type) >= 1

    def test_update_verification_badge(self, db_session):
        """测试更新信任徽章"""
        badge = make_verification_badge(
            id="badge_update_1",
            status="active",
            display_order=5,
        )
        db_session.add(badge)
        db_session.commit()

        # 更新徽章状态
        badge.status = "expired"
        badge.expires_at = datetime.now() - timedelta(days=1)
        badge.display_order = 10
        badge.description = "徽章已过期"
        db_session.commit()

        # 验证更新成功
        updated = db_session.query(VerificationBadgeDB).filter(
            VerificationBadgeDB.id == "badge_update_1"
        ).first()
        assert updated.status == "expired"
        assert updated.expires_at is not None
        assert updated.display_order == 10

    def test_delete_verification_badge(self, db_session):
        """测试删除信任徽章"""
        badge = make_verification_badge(id="badge_delete_1")
        db_session.add(badge)
        db_session.commit()

        # 删除
        db_session.delete(badge)
        db_session.commit()

        # 验证已删除
        deleted = db_session.query(VerificationBadgeDB).filter(
            VerificationBadgeDB.id == "badge_delete_1"
        ).first()
        assert deleted is None


# ============= 第八部分：VideoDateDB CRUD 测试 =============

class TestVideoDateDBCRUD:
    """视频约会模型 CRUD 测试"""

    def test_create_video_date(self, db_session):
        """测试创建视频约会"""
        user1 = make_user(id="video_date_user_1")
        user2 = make_user(id="video_date_user_2")
        db_session.add_all([user1, user2])
        db_session.commit()

        video_date = make_video_date(
            id="video_date_create_1",
            user_id_1="video_date_user_1",
            user_id_2="video_date_user_2",
            scheduled_time=datetime.now() + timedelta(hours=2),
        )
        db_session.add(video_date)
        db_session.commit()

        # 验证创建成功
        saved = db_session.query(VideoDateDB).filter(
            VideoDateDB.id == "video_date_create_1"
        ).first()
        assert saved is not None
        assert saved.user_id_1 == "video_date_user_1"
        assert saved.user_id_2 == "video_date_user_2"
        assert saved.status == "scheduled"
        assert saved.duration_minutes == 30
        assert saved.has_report is False

    def test_read_video_date(self, db_session):
        """测试查询视频约会"""
        video_date = make_video_date(
            id="video_date_read_1",
            user_id_1="vd_reader_1",
            user_id_2="vd_reader_2",
        )
        db_session.add(video_date)
        db_session.commit()

        # 按 ID 查询
        found = db_session.query(VideoDateDB).filter(
            VideoDateDB.id == "video_date_read_1"
        ).first()
        assert found is not None

        # 按用户查询
        by_user = db_session.query(VideoDateDB).filter(
            VideoDateDB.user_id_1 == "vd_reader_1"
        ).all()
        assert len(by_user) == 1

        # 按状态查询
        scheduled = db_session.query(VideoDateDB).filter(
            VideoDateDB.status == "scheduled"
        ).all()
        assert len(scheduled) >= 1

    def test_update_video_date(self, db_session):
        """测试更新视频约会"""
        video_date = make_video_date(
            id="video_date_update_1",
            status="scheduled",
        )
        db_session.add(video_date)
        db_session.commit()

        # 更新约会状态
        video_date.status = "completed"
        video_date.actual_start_time = datetime.now() - timedelta(minutes=30)
        video_date.actual_end_time = datetime.now()
        video_date.actual_duration_minutes = 30
        video_date.rating_user1 = 5
        video_date.rating_user2 = 4
        db_session.commit()

        # 验证更新成功
        updated = db_session.query(VideoDateDB).filter(
            VideoDateDB.id == "video_date_update_1"
        ).first()
        assert updated.status == "completed"
        assert updated.actual_duration_minutes == 30
        assert updated.rating_user1 == 5
        assert updated.rating_user2 == 4

    def test_delete_video_date(self, db_session):
        """测试删除视频约会"""
        video_date = make_video_date(id="video_date_delete_1")
        db_session.add(video_date)
        db_session.commit()

        # 删除
        db_session.delete(video_date)
        db_session.commit()

        # 验证已删除
        deleted = db_session.query(VideoDateDB).filter(
            VideoDateDB.id == "video_date_delete_1"
        ).first()
        assert deleted is None


# ============= 第九部分：UserMembershipDB CRUD 测试 =============

class TestUserMembershipDBCRUD:
    """会员状态模型 CRUD 测试"""

    def test_create_user_membership(self, db_session):
        """测试创建会员状态"""
        user = make_user(id="membership_user_1")
        db_session.add(user)
        db_session.commit()

        membership = make_user_membership(
            id="membership_create_1",
            user_id="membership_user_1",
            tier="premium",
            status="active",
        )
        db_session.add(membership)
        db_session.commit()

        # 验证创建成功
        saved = db_session.query(UserMembershipDB).filter(
            UserMembershipDB.id == "membership_create_1"
        ).first()
        assert saved is not None
        assert saved.user_id == "membership_user_1"
        assert saved.tier == "premium"
        assert saved.status == "active"
        assert saved.auto_renew is False

    def test_read_user_membership(self, db_session):
        """测试查询会员状态"""
        membership = make_user_membership(
            id="membership_read_1",
            user_id="member_reader",
            tier="standard",
        )
        db_session.add(membership)
        db_session.commit()

        # 按 ID 查询
        found = db_session.query(UserMembershipDB).filter(
            UserMembershipDB.id == "membership_read_1"
        ).first()
        assert found is not None

        # 按用户查询（唯一约束）
        by_user = db_session.query(UserMembershipDB).filter(
            UserMembershipDB.user_id == "member_reader"
        ).first()
        assert by_user is not None

        # 查询活跃会员
        active = db_session.query(UserMembershipDB).filter(
            UserMembershipDB.status == "inactive"
        ).all()
        assert len(active) >= 1

    def test_update_user_membership(self, db_session):
        """测试更新会员状态"""
        membership = make_user_membership(
            id="membership_update_1",
            tier="free",
            status="inactive",
        )
        db_session.add(membership)
        db_session.commit()

        # 升级会员
        membership.tier = "premium"
        membership.status = "active"
        membership.start_date = datetime.now()
        membership.end_date = datetime.now() + timedelta(days=365)
        membership.auto_renew = True
        membership.payment_method = "wechat"
        db_session.commit()

        # 验证更新成功
        updated = db_session.query(UserMembershipDB).filter(
            UserMembershipDB.id == "membership_update_1"
        ).first()
        assert updated.tier == "premium"
        assert updated.status == "active"
        assert updated.auto_renew is True
        assert updated.payment_method == "wechat"

    def test_delete_user_membership(self, db_session):
        """测试删除会员状态"""
        membership = make_user_membership(id="membership_delete_1")
        db_session.add(membership)
        db_session.commit()

        # 删除
        db_session.delete(membership)
        db_session.commit()

        # 验证已删除
        deleted = db_session.query(UserMembershipDB).filter(
            UserMembershipDB.id == "membership_delete_1"
        ).first()
        assert deleted is None


# ============= 第十部分：MembershipOrderDB CRUD 测试 =============

class TestMembershipOrderDBCRUD:
    """订单模型 CRUD 测试"""

    def test_create_membership_order(self, db_session):
        """测试创建订单"""
        user = make_user(id="order_user_1")
        db_session.add(user)
        db_session.commit()

        order = make_membership_order(
            id="order_create_1",
            user_id="order_user_1",
            tier="premium",
            duration_months=12,
            amount=299.0,
        )
        db_session.add(order)
        db_session.commit()

        # 验证创建成功
        saved = db_session.query(MembershipOrderDB).filter(
            MembershipOrderDB.id == "order_create_1"
        ).first()
        assert saved is not None
        assert saved.user_id == "order_user_1"
        assert saved.tier == "premium"
        assert saved.duration_months == 12
        assert saved.amount == 299.0
        assert saved.status == "pending"

    def test_read_membership_order(self, db_session):
        """测试查询订单"""
        order = make_membership_order(
            id="order_read_1",
            user_id="order_reader",
        )
        db_session.add(order)
        db_session.commit()

        # 按 ID 查询
        found = db_session.query(MembershipOrderDB).filter(
            MembershipOrderDB.id == "order_read_1"
        ).first()
        assert found is not None

        # 按用户查询
        by_user = db_session.query(MembershipOrderDB).filter(
            MembershipOrderDB.user_id == "order_reader"
        ).all()
        assert len(by_user) == 1

        # 查询待支付订单
        pending = db_session.query(MembershipOrderDB).filter(
            MembershipOrderDB.status == "pending"
        ).all()
        assert len(pending) >= 1

    def test_update_membership_order(self, db_session):
        """测试更新订单"""
        order = make_membership_order(
            id="order_update_1",
            status="pending",
        )
        db_session.add(order)
        db_session.commit()

        # 支付订单
        order.status = "paid"
        order.payment_method = "alipay"
        order.payment_time = datetime.now()
        order.transaction_id = "trans_abc123"
        db_session.commit()

        # 验证更新成功
        updated = db_session.query(MembershipOrderDB).filter(
            MembershipOrderDB.id == "order_update_1"
        ).first()
        assert updated.status == "paid"
        assert updated.payment_method == "alipay"
        assert updated.payment_time is not None
        assert updated.transaction_id == "trans_abc123"

    def test_delete_membership_order(self, db_session):
        """测试删除订单"""
        order = make_membership_order(id="order_delete_1")
        db_session.add(order)
        db_session.commit()

        # 删除
        db_session.delete(order)
        db_session.commit()

        # 验证已删除
        deleted = db_session.query(MembershipOrderDB).filter(
            MembershipOrderDB.id == "order_delete_1"
        ).first()
        assert deleted is None


# ============= 第十一部分：UserReportDB CRUD 测试 =============

class TestUserReportDBCRUD:
    """举报记录模型 CRUD 测试"""

    def test_create_user_report(self, db_session):
        """测试创建举报记录"""
        reporter = make_user(id="reporter_1")
        reported = make_user(id="reported_1")
        db_session.add_all([reporter, reported])
        db_session.commit()

        report = make_user_report(
            id="report_create_1",
            reporter_id="reporter_1",
            reported_user_id="reported_1",
            report_type="harassment",
            description="用户发送骚扰信息",
        )
        db_session.add(report)
        db_session.commit()

        # 验证创建成功
        saved = db_session.query(UserReportDB).filter(
            UserReportDB.id == "report_create_1"
        ).first()
        assert saved is not None
        assert saved.reporter_id == "reporter_1"
        assert saved.reported_user_id == "reported_1"
        assert saved.report_type == "harassment"
        assert saved.status == "pending"
        assert saved.priority == 1

    def test_read_user_report(self, db_session):
        """测试查询举报记录"""
        report = make_user_report(
            id="report_read_1",
            reporter_id="report_reader",
            report_type="spam",
        )
        db_session.add(report)
        db_session.commit()

        # 按 ID 查询
        found = db_session.query(UserReportDB).filter(
            UserReportDB.id == "report_read_1"
        ).first()
        assert found is not None

        # 按举报人查询
        by_reporter = db_session.query(UserReportDB).filter(
            UserReportDB.reporter_id == "report_reader"
        ).all()
        assert len(by_reporter) == 1

        # 按状态查询
        pending = db_session.query(UserReportDB).filter(
            UserReportDB.status == "pending"
        ).all()
        assert len(pending) >= 1

        # 按举报类型查询
        by_type = db_session.query(UserReportDB).filter(
            UserReportDB.report_type == "spam"
        ).all()
        assert len(by_type) >= 1

    def test_update_user_report(self, db_session):
        """测试更新举报记录"""
        report = make_user_report(
            id="report_update_1",
            status="pending",
            priority=1,
        )
        db_session.add(report)
        db_session.commit()

        # 处理举报
        report.status = "resolved"
        report.reviewed_by = "admin_001"
        report.reviewed_at = datetime.now()
        report.action_taken = "user_banned"
        report.action_details = {"ban_duration": "7_days"}
        db_session.commit()

        # 验证更新成功
        updated = db_session.query(UserReportDB).filter(
            UserReportDB.id == "report_update_1"
        ).first()
        assert updated.status == "resolved"
        assert updated.reviewed_by == "admin_001"
        assert updated.action_taken == "user_banned"

    def test_delete_user_report(self, db_session):
        """测试删除举报记录"""
        report = make_user_report(id="report_delete_1")
        db_session.add(report)
        db_session.commit()

        # 删除
        db_session.delete(report)
        db_session.commit()

        # 验证已删除
        deleted = db_session.query(UserReportDB).filter(
            UserReportDB.id == "report_delete_1"
        ).first()
        assert deleted is None


# ============= 第十二部分：SafetyZoneDB CRUD 测试 =============

class TestSafetyZoneDBCRUD:
    """安全区域模型 CRUD 测试"""

    def test_create_safety_zone(self, db_session):
        """测试创建安全区域"""
        zone = make_safety_zone(
            id="zone_create_1",
            zone_type="safe",
            name="市中心安全区",
            latitude=39.9042,
            longitude=116.4074,
            radius=1000,
        )
        db_session.add(zone)
        db_session.commit()

        # 验证创建成功
        saved = db_session.query(SafetyZoneDB).filter(
            SafetyZoneDB.id == "zone_create_1"
        ).first()
        assert saved is not None
        assert saved.zone_type == "safe"
        assert saved.name == "市中心安全区"
        assert saved.latitude == 39.9042
        assert saved.longitude == 116.4074
        assert saved.radius == 1000
        assert saved.is_active is True

    def test_read_safety_zone(self, db_session):
        """测试查询安全区域"""
        zone = make_safety_zone(
            id="zone_read_1",
            zone_type="danger",
            name="危险区域",
        )
        db_session.add(zone)
        db_session.commit()

        # 按 ID 查询
        found = db_session.query(SafetyZoneDB).filter(
            SafetyZoneDB.id == "zone_read_1"
        ).first()
        assert found is not None

        # 按类型查询
        safe_zones = db_session.query(SafetyZoneDB).filter(
            SafetyZoneDB.zone_type == "safe"
        ).all()
        assert len(safe_zones) >= 1

        # 查询活跃区域
        active = db_session.query(SafetyZoneDB).filter(
            SafetyZoneDB.is_active == True
        ).all()
        assert len(active) >= 1

    def test_update_safety_zone(self, db_session):
        """测试更新安全区域"""
        zone = make_safety_zone(
            id="zone_update_1",
            radius=500,
            is_active=True,
        )
        db_session.add(zone)
        db_session.commit()

        # 更新区域
        zone.radius = 800
        zone.description = "更新后的安全区域描述"
        zone.is_active = False
        db_session.commit()

        # 验证更新成功
        updated = db_session.query(SafetyZoneDB).filter(
            SafetyZoneDB.id == "zone_update_1"
        ).first()
        assert updated.radius == 800
        assert updated.is_active is False
        assert updated.updated_at is not None

    def test_delete_safety_zone(self, db_session):
        """测试删除安全区域"""
        zone = make_safety_zone(id="zone_delete_1")
        db_session.add(zone)
        db_session.commit()

        # 删除
        db_session.delete(zone)
        db_session.commit()

        # 验证已删除
        deleted = db_session.query(SafetyZoneDB).filter(
            SafetyZoneDB.id == "zone_delete_1"
        ).first()
        assert deleted is None


# ============= 第十三部分：TrustedContactDB CRUD 测试 =============

class TestTrustedContactDBCRUD:
    """紧急联系人模型 CRUD 测试"""

    def test_create_trusted_contact(self, db_session):
        """测试创建紧急联系人"""
        user = make_user(id="contact_user_1")
        db_session.add(user)
        db_session.commit()

        contact = make_trusted_contact(
            id="contact_create_1",
            user_id="contact_user_1",
            name="张妈妈",
            phone="13900139000",
            relationship="母亲",
        )
        db_session.add(contact)
        db_session.commit()

        # 验证创建成功
        saved = db_session.query(TrustedContactDB).filter(
            TrustedContactDB.id == "contact_create_1"
        ).first()
        assert saved is not None
        assert saved.user_id == "contact_user_1"
        assert saved.name == "张妈妈"
        assert saved.phone == "13900139000"
        assert saved.relationship == "母亲"
        assert saved.can_view_location is True
        assert saved.can_receive_emergency is True

    def test_read_trusted_contact(self, db_session):
        """测试查询紧急联系人"""
        contact = make_trusted_contact(
            id="contact_read_1",
            user_id="contact_reader",
            name="测试联系人",
        )
        db_session.add(contact)
        db_session.commit()

        # 按 ID 查询
        found = db_session.query(TrustedContactDB).filter(
            TrustedContactDB.id == "contact_read_1"
        ).first()
        assert found is not None

        # 按用户查询
        by_user = db_session.query(TrustedContactDB).filter(
            TrustedContactDB.user_id == "contact_reader"
        ).all()
        assert len(by_user) == 1

        # 按手机号查询
        by_phone = db_session.query(TrustedContactDB).filter(
            TrustedContactDB.phone == "13800138000"
        ).all()
        assert len(by_phone) >= 1

    def test_update_trusted_contact(self, db_session):
        """测试更新紧急联系人"""
        contact = make_trusted_contact(
            id="contact_update_1",
            name="旧联系人",
            can_view_location=True,
        )
        db_session.add(contact)
        db_session.commit()

        # 更新联系人
        contact.name = "新联系人"
        contact.phone = "13700137000"
        contact.relationship = "朋友"
        contact.can_view_location = False
        contact.display_order = 1
        db_session.commit()

        # 验证更新成功
        updated = db_session.query(TrustedContactDB).filter(
            TrustedContactDB.id == "contact_update_1"
        ).first()
        assert updated.name == "新联系人"
        assert updated.phone == "13700137000"
        assert updated.can_view_location is False
        assert updated.updated_at is not None

    def test_delete_trusted_contact(self, db_session):
        """测试删除紧急联系人"""
        contact = make_trusted_contact(id="contact_delete_1")
        db_session.add(contact)
        db_session.commit()

        # 删除
        db_session.delete(contact)
        db_session.commit()

        # 验证已删除
        deleted = db_session.query(TrustedContactDB).filter(
            TrustedContactDB.id == "contact_delete_1"
        ).first()
        assert deleted is None


# ============= 第十四部分：FeatureFlagDB CRUD 测试 =============

class TestFeatureFlagDBCRUD:
    """灰度配置模型 CRUD 测试"""

    def test_create_feature_flag(self, db_session):
        """测试创建灰度配置"""
        flag = make_feature_flag(
            id="flag_create_1",
            flag_key="new_chat_ui",
            name="新版聊天界面",
            description="测试新版聊天界面的用户体验",
            rollout_percentage=10,
        )
        db_session.add(flag)
        db_session.commit()

        # 验证创建成功
        saved = db_session.query(FeatureFlagDB).filter(
            FeatureFlagDB.id == "flag_create_1"
        ).first()
        assert saved is not None
        assert saved.flag_key == "new_chat_ui"
        assert saved.name == "新版聊天界面"
        assert saved.rollout_percentage == 10
        assert saved.is_enabled is False
        assert saved.target_user_groups == []

    def test_read_feature_flag(self, db_session):
        """测试查询灰度配置"""
        flag = make_feature_flag(
            id="flag_read_1",
            flag_key="video_date_beta",
        )
        db_session.add(flag)
        db_session.commit()

        # 按 ID 查询
        found = db_session.query(FeatureFlagDB).filter(
            FeatureFlagDB.id == "flag_read_1"
        ).first()
        assert found is not None

        # 按唯一 key 查询
        by_key = db_session.query(FeatureFlagDB).filter(
            FeatureFlagDB.flag_key == "video_date_beta"
        ).first()
        assert by_key is not None

        # 查询已启用功能
        enabled = db_session.query(FeatureFlagDB).filter(
            FeatureFlagDB.is_enabled == True
        ).all()
        # 应该没有启用的（默认都是 False）
        assert len(enabled) == 0

    def test_update_feature_flag(self, db_session):
        """测试更新灰度配置"""
        flag = make_feature_flag(
            id="flag_update_1",
            is_enabled=False,
            rollout_percentage=0,
        )
        db_session.add(flag)
        db_session.commit()

        # 开启灰度
        flag.is_enabled = True
        flag.rollout_percentage = 50
        flag.target_user_groups = ["new_user", "vip"]
        flag.target_cities = ["北京", "上海"]
        flag.config_data = {"theme": "dark"}
        flag.start_time = datetime.now()
        flag.end_time = datetime.now() + timedelta(days=30)
        db_session.commit()

        # 验证更新成功
        updated = db_session.query(FeatureFlagDB).filter(
            FeatureFlagDB.id == "flag_update_1"
        ).first()
        assert updated.is_enabled is True
        assert updated.rollout_percentage == 50
        assert updated.target_user_groups == ["new_user", "vip"]
        assert updated.updated_at is not None

    def test_delete_feature_flag(self, db_session):
        """测试删除灰度配置"""
        flag = make_feature_flag(id="flag_delete_1")
        db_session.add(flag)
        db_session.commit()

        # 删除
        db_session.delete(flag)
        db_session.commit()

        # 验证已删除
        deleted = db_session.query(FeatureFlagDB).filter(
            FeatureFlagDB.id == "flag_delete_1"
        ).first()
        assert deleted is None


# ============= 第十五部分：ABExperimentDB CRUD 测试 =============

class TestABExperimentDBCRUD:
    """A/B 实验模型 CRUD 测试"""

    def test_create_ab_experiment(self, db_session):
        """测试创建 A/B 实验"""
        experiment = make_ab_experiment(
            id="exp_create_1",
            experiment_key="button_color_test",
            name="按钮颜色 A/B 测试",
            status="draft",
            traffic_allocation=50,
        )
        db_session.add(experiment)
        db_session.commit()

        # 验证创建成功
        saved = db_session.query(ABExperimentDB).filter(
            ABExperimentDB.id == "exp_create_1"
        ).first()
        assert saved is not None
        assert saved.experiment_key == "button_color_test"
        assert saved.name == "按钮颜色 A/B 测试"
        assert saved.status == "draft"
        assert saved.traffic_allocation == 50
        assert len(saved.variants) == 2

    def test_read_ab_experiment(self, db_session):
        """测试查询 A/B 实验"""
        experiment = make_ab_experiment(
            id="exp_read_1",
            experiment_key="match_algo_test",
            status="running",
        )
        db_session.add(experiment)
        db_session.commit()

        # 按 ID 查询
        found = db_session.query(ABExperimentDB).filter(
            ABExperimentDB.id == "exp_read_1"
        ).first()
        assert found is not None

        # 按唯一 key 查询
        by_key = db_session.query(ABExperimentDB).filter(
            ABExperimentDB.experiment_key == "match_algo_test"
        ).first()
        assert by_key is not None

        # 按状态查询
        running = db_session.query(ABExperimentDB).filter(
            ABExperimentDB.status == "running"
        ).all()
        assert len(running) >= 1

    def test_update_ab_experiment(self, db_session):
        """测试更新 A/B 实验"""
        experiment = make_ab_experiment(
            id="exp_update_1",
            status="draft",
            traffic_allocation=100,
        )
        db_session.add(experiment)
        db_session.commit()

        # 启动实验
        experiment.status = "running"
        experiment.start_time = datetime.now()
        experiment.end_time = datetime.now() + timedelta(days=14)
        experiment.traffic_allocation = 80
        experiment.variants = [
            {"name": "A", "weight": 70, "config": {"algorithm": "v1"}},
            {"name": "B", "weight": 30, "config": {"algorithm": "v2"}},
        ]
        db_session.commit()

        # 验证更新成功
        updated = db_session.query(ABExperimentDB).filter(
            ABExperimentDB.id == "exp_update_1"
        ).first()
        assert updated.status == "running"
        assert updated.traffic_allocation == 80
        assert updated.start_time is not None
        assert updated.updated_at is not None

    def test_delete_ab_experiment(self, db_session):
        """测试删除 A/B 实验"""
        experiment = make_ab_experiment(id="exp_delete_1")
        db_session.add(experiment)
        db_session.commit()

        # 删除
        db_session.delete(experiment)
        db_session.commit()

        # 验证已删除
        deleted = db_session.query(ABExperimentDB).filter(
            ABExperimentDB.id == "exp_delete_1"
        ).first()
        assert deleted is None


# ============= 运行测试 =============

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])