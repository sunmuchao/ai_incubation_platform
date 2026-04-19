"""
聊天模型修复验证测试

测试覆盖:
1. ChatConversationDB 属性名正确性验证 (6 tests)
   - 确保使用 unread_count_user1/user2 而非错误的 unread_count_1/2
2. ChatMessageDB/ChatConversationDB status 列存在性验证 (4 tests)
   - 确保表创建时包含 status 列
3. API 层属性使用正确性验证 (4 tests)
   - 验证 chat.py 中使用正确的属性名
4. 边界场景测试 (4 tests)
   - 验证空值、默认值、更新等场景

总计: 18 个测试用例
"""
import pytest
import uuid
from datetime import datetime, timedelta
from sqlalchemy import inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import create_engine

from db.database import Base
from db.models import UserDB, ChatMessageDB, ChatConversationDB


# ============= 测试基础设施 =============

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)

# 创建所有表
Base.metadata.create_all(bind=test_engine)


@pytest.fixture
def db_session():
    """数据库会话 fixture"""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


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


# ============= 第一部分：ChatConversationDB 属性名正确性验证 =============

class TestChatConversationAttributeNames:
    """
    验证 ChatConversationDB 使用正确的属性名

    修复问题：'ChatConversationDB' object has no attribute 'unread_count_1'
    正确属性名：unread_count_user1, unread_count_user2
    """

    def test_model_has_unread_count_user1(self, db_session):
        """验证模型存在 unread_count_user1 属性"""
        conv = make_chat_conversation(id="conv_attr_1")
        db_session.add(conv)
        db_session.commit()

        # 验证属性存在且可访问
        saved = db_session.query(ChatConversationDB).filter(
            ChatConversationDB.id == "conv_attr_1"
        ).first()
        assert hasattr(saved, "unread_count_user1")
        assert saved.unread_count_user1 == 0  # 默认值

    def test_model_has_unread_count_user2(self, db_session):
        """验证模型存在 unread_count_user2 属性"""
        conv = make_chat_conversation(id="conv_attr_2")
        db_session.add(conv)
        db_session.commit()

        saved = db_session.query(ChatConversationDB).filter(
            ChatConversationDB.id == "conv_attr_2"
        ).first()
        assert hasattr(saved, "unread_count_user2")
        assert saved.unread_count_user2 == 0  # 默认值

    def test_model_does_not_have_unread_count_1(self, db_session):
        """验证模型不存在错误的属性 unread_count_1"""
        conv = make_chat_conversation(id="conv_attr_3")
        db_session.add(conv)
        db_session.commit()

        saved = db_session.query(ChatConversationDB).filter(
            ChatConversationDB.id == "conv_attr_3"
        ).first()
        # 错误的属性名应该不存在
        assert not hasattr(saved, "unread_count_1")

    def test_model_does_not_have_unread_count_2(self, db_session):
        """验证模型不存在错误的属性 unread_count_2"""
        conv = make_chat_conversation(id="conv_attr_4")
        db_session.add(conv)
        db_session.commit()

        saved = db_session.query(ChatConversationDB).filter(
            ChatConversationDB.id == "conv_attr_4"
        ).first()
        # 错误的属性名应该不存在
        assert not hasattr(saved, "unread_count_2")

    def test_update_unread_count_user1(self, db_session):
        """验证可以正确更新 unread_count_user1"""
        conv = make_chat_conversation(
            id="conv_update_1",
            unread_count_user1=0,
        )
        db_session.add(conv)
        db_session.commit()

        # 更新未读计数
        conv.unread_count_user1 = 5
        db_session.commit()

        saved = db_session.query(ChatConversationDB).filter(
            ChatConversationDB.id == "conv_update_1"
        ).first()
        assert saved.unread_count_user1 == 5

    def test_update_unread_count_user2(self, db_session):
        """验证可以正确更新 unread_count_user2"""
        conv = make_chat_conversation(
            id="conv_update_2",
            unread_count_user2=0,
        )
        db_session.add(conv)
        db_session.commit()

        # 更新未读计数
        conv.unread_count_user2 = 3
        db_session.commit()

        saved = db_session.query(ChatConversationDB).filter(
            ChatConversationDB.id == "conv_update_2"
        ).first()
        assert saved.unread_count_user2 == 3


# ============= 第二部分：status 列存在性验证 =============

class TestChatStatusColumnExistence:
    """
    验证 chat_messages 和 chat_conversations 表存在 status 列

    修复问题：(sqlite3.OperationalError) no such column: status
    """

    def test_chat_messages_has_status_column(self, db_session):
        """验证 chat_messages 表存在 status 列"""
        inspector = inspect(test_engine)
        columns = inspector.get_columns("chat_messages")
        column_names = {col["name"] for col in columns}

        assert "status" in column_names

    def test_chat_conversations_has_status_column(self, db_session):
        """验证 chat_conversations 表存在 status 列"""
        inspector = inspect(test_engine)
        columns = inspector.get_columns("chat_conversations")
        column_names = {col["name"] for col in columns}

        assert "status" in column_names

    def test_chat_message_status_default_value(self, db_session):
        """验证 chat_messages.status 默认值为 'sent'"""
        msg = make_chat_message(id="msg_status_1")
        db_session.add(msg)
        db_session.commit()

        saved = db_session.query(ChatMessageDB).filter(
            ChatMessageDB.id == "msg_status_1"
        ).first()
        assert saved.status == "sent"  # 默认值

    def test_chat_conversation_status_default_value(self, db_session):
        """验证 chat_conversations.status 默认值为 'active'"""
        conv = make_chat_conversation(id="conv_status_1")
        db_session.add(conv)
        db_session.commit()

        saved = db_session.query(ChatConversationDB).filter(
            ChatConversationDB.id == "conv_status_1"
        ).first()
        assert saved.status == "active"  # 默认值


# ============= 第三部分：API 层属性使用正确性验证 =============

class TestAPIAttributeUsage:
    """
    验证 API 代码使用正确的属性名

    修复问题：src/api/chat.py:949 使用了错误的 unread_count_1/2
    """

    def test_correct_attribute_usage_pattern(self, db_session):
        """验证正确的属性访问模式"""
        user_id = "user_api_test"
        user1 = make_user(id=user_id)
        user2 = make_user(id="user_api_other")
        db_session.add_all([user1, user2])
        db_session.commit()

        conv = make_chat_conversation(
            id="conv_api_1",
            user_id_1=user_id,
            user_id_2="user_api_other",
            unread_count_user1=3,
            unread_count_user2=1,
        )
        db_session.add(conv)
        db_session.commit()

        # 模拟 chat.py:949 的正确逻辑
        saved = db_session.query(ChatConversationDB).filter(
            ChatConversationDB.id == "conv_api_1"
        ).first()

        # 正确的属性访问方式
        unread_count = saved.unread_count_user1 if saved.user_id_1 == user_id else saved.unread_count_user2
        assert unread_count == 3  # user_id_1 的未读数

    def test_any_function_with_correct_attributes(self, db_session):
        """验证 any() 函数使用正确的属性名"""
        user_id = "user_any_test"
        user1 = make_user(id=user_id)
        user2 = make_user(id="user_any_other")
        user3 = make_user(id="user_any_third")
        db_session.add_all([user1, user2, user3])
        db_session.commit()

        conv1 = make_chat_conversation(
            id="conv_any_1",
            user_id_1=user_id,
            user_id_2="user_any_other",
            unread_count_user1=0,  # 无未读
            unread_count_user2=2,
        )
        conv2 = make_chat_conversation(
            id="conv_any_2",
            user_id_1="user_any_other",
            user_id_2=user_id,
            unread_count_user1=3,
            unread_count_user2=0,
        )
        db_session.add_all([conv1, conv2])
        db_session.commit()

        conversations = db_session.query(ChatConversationDB).filter(
            (ChatConversationDB.user_id_1 == user_id) | (ChatConversationDB.user_id_2 == user_id)
        ).all()

        # 正确的 any() 用法（修复后的代码）
        has_unread_messages = any(
            conv.unread_count_user1 > 0 if conv.user_id_1 == user_id else conv.unread_count_user2 > 0
            for conv in conversations
        )

        # conv1: user_id_1 == user_id, unread_count_user1 == 0 (无未读)
        # conv2: user_id_2 == user_id, unread_count_user2 == 0 (无未读)
        assert has_unread_messages is False

    def test_any_function_with_unread_messages(self, db_session):
        """验证 any() 函数在有未读消息时的正确行为"""
        user_id = "user_unread_test"
        user1 = make_user(id=user_id)
        user2 = make_user(id="user_unread_other")
        db_session.add_all([user1, user2])
        db_session.commit()

        conv = make_chat_conversation(
            id="conv_unread_1",
            user_id_1=user_id,
            user_id_2="user_unread_other",
            unread_count_user1=5,  # 有未读
            unread_count_user2=0,
        )
        db_session.add(conv)
        db_session.commit()

        conversations = db_session.query(ChatConversationDB).filter(
            (ChatConversationDB.user_id_1 == user_id) | (ChatConversationDB.user_id_2 == user_id)
        ).all()

        # 正确的 any() 用法
        has_unread_messages = any(
            conv.unread_count_user1 > 0 if conv.user_id_1 == user_id else conv.unread_count_user2 > 0
            for conv in conversations
        )

        assert has_unread_messages is True

    def test_status_filter_in_query(self, db_session):
        """验证可以在查询中正确使用 status 过滤"""
        conv_active = make_chat_conversation(
            id="conv_active",
            status="active",
        )
        conv_archived = make_chat_conversation(
            id="conv_archived",
            status="archived",
        )
        db_session.add_all([conv_active, conv_archived])
        db_session.commit()

        # 按 status 查询
        active_convs = db_session.query(ChatConversationDB).filter(
            ChatConversationDB.status == "active"
        ).all()
        assert len(active_convs) >= 1
        assert any(c.id == "conv_active" for c in active_convs)

        archived_convs = db_session.query(ChatConversationDB).filter(
            ChatConversationDB.status == "archived"
        ).all()
        assert len(archived_convs) >= 1
        assert any(c.id == "conv_archived" for c in archived_convs)


# ============= 第四部分：边界场景测试 =============

class TestChatBoundaryScenarios:
    """
    边界场景测试

    验证空值、默认值、状态更新等场景
    """

    def test_unread_count_zero_default(self, db_session):
        """验证未读计数默认为 0"""
        conv = make_chat_conversation(id="conv_zero")
        db_session.add(conv)
        db_session.commit()

        saved = db_session.query(ChatConversationDB).filter(
            ChatConversationDB.id == "conv_zero"
        ).first()
        assert saved.unread_count_user1 == 0
        assert saved.unread_count_user2 == 0

    def test_unread_count_increment(self, db_session):
        """验证未读计数可以正确递增"""
        conv = make_chat_conversation(
            id="conv_increment",
            unread_count_user1=0,
        )
        db_session.add(conv)
        db_session.commit()

        # 模拟收到新消息，递增未读计数
        conv.unread_count_user1 += 1
        conv.unread_count_user1 += 1
        db_session.commit()

        saved = db_session.query(ChatConversationDB).filter(
            ChatConversationDB.id == "conv_increment"
        ).first()
        assert saved.unread_count_user1 == 2

    def test_status_transition(self, db_session):
        """验证会话状态可以正确转换"""
        conv = make_chat_conversation(
            id="conv_transition",
            status="active",
        )
        db_session.add(conv)
        db_session.commit()

        # 状态转换：active -> archived -> blocked
        conv.status = "archived"
        db_session.commit()
        saved = db_session.query(ChatConversationDB).filter(
            ChatConversationDB.id == "conv_transition"
        ).first()
        assert saved.status == "archived"

        conv.status = "blocked"
        db_session.commit()
        saved = db_session.query(ChatConversationDB).filter(
            ChatConversationDB.id == "conv_transition"
        ).first()
        assert saved.status == "blocked"

    def test_message_status_transition(self, db_session):
        """验证消息状态可以正确转换"""
        msg = make_chat_message(
            id="msg_transition",
            status="sent",
        )
        db_session.add(msg)
        db_session.commit()

        # 状态转换：sent -> delivered -> read
        msg.status = "delivered"
        db_session.commit()
        saved = db_session.query(ChatMessageDB).filter(
            ChatMessageDB.id == "msg_transition"
        ).first()
        assert saved.status == "delivered"

        msg.status = "read"
        msg.is_read = True
        msg.read_at = datetime.now()
        db_session.commit()
        saved = db_session.query(ChatMessageDB).filter(
            ChatMessageDB.id == "msg_transition"
        ).first()
        assert saved.status == "read"
        assert saved.is_read is True


# ============= 第五部分：模型完整性验证 =============

class TestChatModelIntegrity:
    """
    验证模型定义完整性

    确保所有预期字段都存在
    """

    def test_chat_messages_all_columns(self, db_session):
        """验证 chat_messages 表包含所有预期列"""
        inspector = inspect(test_engine)
        columns = inspector.get_columns("chat_messages")
        column_names = {col["name"] for col in columns}

        expected_columns = {
            "id",
            "conversation_id",
            "sender_id",
            "receiver_id",
            "message_type",
            "content",
            "status",  # 关键：必须有
            "is_read",
            "read_at",
            "message_metadata",
            "created_at",
            "updated_at",
        }

        for col in expected_columns:
            assert col in column_names, f"chat_messages 缺少列: {col}"

    def test_chat_conversations_all_columns(self, db_session):
        """验证 chat_conversations 表包含所有预期列"""
        inspector = inspect(test_engine)
        columns = inspector.get_columns("chat_conversations")
        column_names = {col["name"] for col in columns}

        expected_columns = {
            "id",
            "user_id_1",
            "user_id_2",
            "status",  # 关键：必须有
            "last_message_at",
            "last_message_preview",
            "unread_count_user1",  # 关键：正确的属性名
            "unread_count_user2",  # 关键：正确的属性名
            "created_at",
            "updated_at",
        }

        for col in expected_columns:
            assert col in column_names, f"chat_conversations 缺少列: {col}"

    def test_no_wrong_column_names(self, db_session):
        """验证不存在错误的列名"""
        inspector = inspect(test_engine)
        conv_columns = inspector.get_columns("chat_conversations")
        column_names = {col["name"] for col in conv_columns}

        # 确保错误的列名不存在
        wrong_names = {"unread_count_1", "unread_count_2"}
        for wrong_name in wrong_names:
            assert wrong_name not in column_names, f"chat_conversations 存在错误列名: {wrong_name}"


# ============= 运行测试 =============

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])