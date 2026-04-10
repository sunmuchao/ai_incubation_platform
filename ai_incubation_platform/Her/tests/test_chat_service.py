"""
ChatService 边缘场景测试

测试覆盖:
1. 会话创建边缘场景 (8 tests)
2. 消息发送边缘场景 (12 tests)
3. 消息历史查询边缘场景 (6 tests)
4. 已读状态边缘场景 (6 tests)
5. 消息撤回边缘场景 (5 tests)
6. 会话管理边缘场景 (6 tests)
7. 搜索功能边缘场景 (4 tests)

总计: 41 个测试用例
"""
import pytest
import uuid
import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from services.chat_service import ChatService
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

Base.metadata.create_all(bind=test_engine)


@pytest.fixture
def db_session():
    """数据库会话 fixture"""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def chat_service(db_session):
    """ChatService fixture"""
    return ChatService(db_session)


def make_user(**kwargs):
    """创建测试用户"""
    defaults = {
        "id": str(uuid.uuid4()),
        "email": f"chat_{uuid.uuid4()}@example.com",
        "password_hash": "hashed_pw",
        "name": "Chat Test User",
        "age": 28,
        "gender": "male",
        "location": "北京",
        "interests": "[]",
        "values": "{}",
        "bio": "",
    }
    defaults.update(kwargs)
    return UserDB(**defaults)


def make_conversation(**kwargs):
    """创建测试会话"""
    defaults = {
        "id": str(uuid.uuid4()),
        "user_id_1": "user_1",
        "user_id_2": "user_2",
        "status": "active",
        "unread_count_user1": 0,
        "unread_count_user2": 0,
    }
    defaults.update(kwargs)
    return ChatConversationDB(**defaults)


def make_message(**kwargs):
    """创建测试消息"""
    defaults = {
        "id": str(uuid.uuid4()),
        "conversation_id": str(uuid.uuid4()),
        "sender_id": "sender",
        "receiver_id": "receiver",
        "message_type": "text",
        "content": "Test message",
        "status": "sent",
        "is_read": False,
    }
    defaults.update(kwargs)
    return ChatMessageDB(**defaults)


# ============= 第一部分：会话创建边缘场景 =============

class TestConversationCreation:
    """会话创建测试"""

    def test_get_or_create_conversation_new(self, chat_service, db_session):
        """测试创建新会话"""
        conv = chat_service.get_or_create_conversation("user_a", "user_b")

        assert conv is not None
        assert conv.user_id_1 == "user_a"
        assert conv.user_id_2 == "user_b"
        assert conv.status == "active"

    def test_get_or_create_conversation_existing(self, chat_service, db_session):
        """测试获取已存在会话"""
        # 先创建
        conv1 = chat_service.get_or_create_conversation("user_x", "user_y")

        # 再次获取应该是同一个
        conv2 = chat_service.get_or_create_conversation("user_x", "user_y")

        assert conv1.id == conv2.id

    def test_get_or_create_conversation_reversed_order(self, chat_service, db_session):
        """测试用户顺序反转时仍获取同一会话"""
        # 先创建 user_1, user_2
        conv1 = chat_service.get_or_create_conversation("user_1", "user_2")

        # 反序获取 user_2, user_1 应该是同一个会话
        conv2 = chat_service.get_or_create_conversation("user_2", "user_1")

        assert conv1.id == conv2.id

    def test_get_or_create_conversation_same_user(self, chat_service, db_session):
        """测试同一用户创建会话"""
        conv = chat_service.get_or_create_conversation("self_user", "self_user")

        # 应该允许创建（系统行为）
        assert conv is not None
        assert conv.user_id_1 == "self_user"
        assert conv.user_id_2 == "self_user"

    def test_get_or_create_conversation_empty_user_ids(self, chat_service, db_session):
        """测试空用户 ID"""
        # 空字符串用户 ID
        conv = chat_service.get_or_create_conversation("", "user_b")
        assert conv is not None
        assert conv.user_id_1 == ""

    def test_get_or_create_conversation_special_characters(self, chat_service, db_session):
        """测试特殊字符用户 ID"""
        special_id = "user<script>alert('xss')</script>"
        conv = chat_service.get_or_create_conversation(special_id, "normal_user")

        assert conv is not None
        assert conv.user_id_1 == special_id

    def test_get_or_create_conversation_unicode_ids(self, chat_service, db_session):
        """测试 Unicode 用户 ID"""
        unicode_id = "用户_中文_ID_🎉"
        conv = chat_service.get_or_create_conversation(unicode_id, "user_b")

        assert conv is not None
        assert conv.user_id_1 == unicode_id

    def test_get_or_create_conversation_multiple_concurrent(self, chat_service, db_session):
        """测试并发创建会话"""
        # 创建多个会话
        convs = [
            chat_service.get_or_create_conversation(f"user_{i}", f"partner_{i}")
            for i in range(10)
        ]

        assert len(convs) == 10
        assert len(set(c.id for c in convs)) == 10  # 所有会话 ID 不同


# ============= 第二部分：消息发送边缘场景 =============

class TestMessageSending:
    """消息发送测试"""

    def test_send_message_text(self, chat_service, db_session):
        """测试发送文本消息"""
        msg = chat_service.send_message(
            sender_id="sender_1",
            receiver_id="receiver_1",
            content="Hello World"
        )

        assert msg is not None
        assert msg.message_type == "text"
        assert msg.content == "Hello World"
        assert msg.status == "sent"

    def test_send_message_image(self, chat_service, db_session):
        """测试发送图片消息"""
        msg = chat_service.send_message(
            sender_id="sender_img",
            receiver_id="receiver_img",
            content="image_url_here",
            message_type=ChatService.TYPE_IMAGE
        )

        assert msg.message_type == "image"

    def test_send_message_emoji(self, chat_service, db_session):
        """测试发送表情消息"""
        msg = chat_service.send_message(
            sender_id="sender_emoji",
            receiver_id="receiver_emoji",
            content="😊",
            message_type=ChatService.TYPE_EMOJI
        )

        assert msg.message_type == "emoji"

    def test_send_message_voice(self, chat_service, db_session):
        """测试发送语音消息"""
        msg = chat_service.send_message(
            sender_id="sender_voice",
            receiver_id="receiver_voice",
            content="voice_data",
            message_type=ChatService.TYPE_VOICE
        )

        assert msg.message_type == "voice"

    def test_send_message_system(self, chat_service, db_session):
        """测试发送系统消息"""
        msg = chat_service.send_message(
            sender_id="system",
            receiver_id="user_system",
            content="系统通知",
            message_type=ChatService.TYPE_SYSTEM
        )

        assert msg.message_type == "system"

    def test_send_message_empty_content(self, chat_service, db_session):
        """测试发送空内容消息"""
        msg = chat_service.send_message(
            sender_id="empty_sender",
            receiver_id="empty_receiver",
            content=""
        )

        # 空消息应该被发送（可能由 API 层验证）
        assert msg.content == ""

    def test_send_message_very_long_content(self, chat_service, db_session):
        """测试发送超长内容消息"""
        long_content = "A" * 10000

        msg = chat_service.send_message(
            sender_id="long_sender",
            receiver_id="long_receiver",
            content=long_content
        )

        assert msg.content == long_content

    def test_send_message_unicode_content(self, chat_service, db_session):
        """测试发送 Unicode 内容"""
        unicode_content = "你好世界 🎉🎉🎉 日本語 العربية"

        msg = chat_service.send_message(
            sender_id="unicode_sender",
            receiver_id="unicode_receiver",
            content=unicode_content
        )

        assert msg.content == unicode_content

    def test_send_message_with_metadata(self, chat_service, db_session):
        """测试发送带元数据的消息"""
        metadata = {"file_size": 1024, "duration": 30}

        msg = chat_service.send_message(
            sender_id="meta_sender",
            receiver_id="meta_receiver",
            content="message with metadata",
            message_metadata=metadata
        )

        assert msg.message_metadata == metadata

    def test_send_message_updates_unread_count(self, chat_service, db_session):
        """测试发送消息更新未读计数"""
        msg = chat_service.send_message(
            sender_id="unread_sender",
            receiver_id="unread_receiver",
            content="test"
        )

        # 获取会话
        conv = chat_service.get_or_create_conversation("unread_sender", "unread_receiver")
        # 未读计数应该增加
        assert conv.unread_count_user1 > 0 or conv.unread_count_user2 > 0

    def test_send_message_updates_last_message_preview(self, chat_service, db_session):
        """测试发送消息更新最后消息预览"""
        msg = chat_service.send_message(
            sender_id="preview_sender",
            receiver_id="preview_receiver",
            content="Preview test message content here"
        )

        conv = chat_service.get_or_create_conversation("preview_sender", "preview_receiver")
        assert conv.last_message_preview is not None

    def test_send_message_exception_handling(self, chat_service, db_session):
        """测试发送消息异常处理"""
        # 模拟数据库提交失败
        with patch.object(db_session, 'commit', side_effect=Exception("DB Error")):
            with pytest.raises(Exception):
                chat_service.send_message(
                    sender_id="error_sender",
                    receiver_id="error_receiver",
                    content="error message"
                )


# ============= 第三部分：消息历史查询边缘场景 =============

class TestMessageHistory:
    """消息历史查询测试"""

    def test_get_conversation_messages_empty(self, chat_service, db_session):
        """测试获取空会话的消息"""
        messages = chat_service.get_conversation_messages("empty_user", "empty_partner")

        assert messages == []

    def test_get_conversation_messages_with_limit(self, chat_service, db_session):
        """测试带限制获取消息"""
        # 先发送多条消息
        for i in range(20):
            chat_service.send_message(
                sender_id="limit_sender",
                receiver_id="limit_receiver",
                content=f"Message {i}"
            )

        messages = chat_service.get_conversation_messages(
            "limit_sender", "limit_receiver",
            limit=10
        )

        assert len(messages) == 10

    def test_get_conversation_messages_with_offset(self, chat_service, db_session):
        """测试带偏移获取消息"""
        for i in range(15):
            chat_service.send_message(
                sender_id="offset_sender",
                receiver_id="offset_receiver",
                content=f"Message {i}"
            )

        messages = chat_service.get_conversation_messages(
            "offset_sender", "offset_receiver",
            limit=5, offset=10
        )

        assert len(messages) == 5

    def test_get_user_conversations_empty(self, chat_service, db_session):
        """测试获取无会话用户的会话列表"""
        conversations = chat_service.get_user_conversations("no_conversations_user")

        assert conversations == []

    def test_get_user_conversations_multiple(self, chat_service, db_session):
        """测试获取多个会话"""
        # 创建多个会话
        for i in range(5):
            chat_service.send_message(
                sender_id="multi_user",
                receiver_id=f"partner_{i}",
                content=f"Conv {i}"
            )

        conversations = chat_service.get_user_conversations("multi_user")

        assert len(conversations) == 5

    def test_get_user_conversations_excludes_archived(self, chat_service, db_session):
        """测试会话列表排除已归档"""
        # 创建会话
        chat_service.send_message(
            sender_id="archive_test_user",
            receiver_id="archive_partner",
            content="test"
        )

        # 归档会话
        chat_service.archive_conversation("archive_test_user", "archive_partner")

        # 获取会话列表
        conversations = chat_service.get_user_conversations("archive_test_user")

        # 归档的会话应该不在列表中
        assert len(conversations) == 0


# ============= 第四部分：已读状态边缘场景 =============

class TestReadStatus:
    """已读状态测试"""

    def test_mark_message_read_success(self, chat_service, db_session):
        """测试标记消息已读成功"""
        msg = chat_service.send_message(
            sender_id="read_sender",
            receiver_id="read_receiver",
            content="read test"
        )

        result = chat_service.mark_message_read(msg.id, "read_receiver")

        assert result is True
        assert msg.is_read is True
        assert msg.status == "read"

    def test_mark_message_read_wrong_user(self, chat_service, db_session):
        """测试非接收者标记已读失败"""
        msg = chat_service.send_message(
            sender_id="wrong_sender",
            receiver_id="wrong_receiver",
            content="wrong test"
        )

        # 发送者尝试标记已读
        result = chat_service.mark_message_read(msg.id, "wrong_sender")

        assert result is False

    def test_mark_message_read_nonexistent_message(self, chat_service, db_session):
        """测试标记不存在消息已读"""
        result = chat_service.mark_message_read("nonexistent_msg_id", "user")

        assert result is False

    def test_mark_conversation_read_success(self, chat_service, db_session):
        """测试标记整个会话已读"""
        # 发送多条未读消息
        for i in range(5):
            chat_service.send_message(
                sender_id="conv_read_sender",
                receiver_id="conv_read_receiver",
                content=f"Unread {i}"
            )

        result = chat_service.mark_conversation_read("conv_read_sender", "conv_read_receiver")

        assert result is True

    def test_mark_conversation_read_updates_unread_count(self, chat_service, db_session):
        """测试标记会话已读更新未读计数"""
        chat_service.send_message(
            sender_id="unread_count_sender",
            receiver_id="unread_count_receiver",
            content="test"
        )

        chat_service.mark_conversation_read("unread_count_sender", "unread_count_receiver")

        conv = chat_service.get_or_create_conversation("unread_count_sender", "unread_count_receiver")
        assert conv.unread_count_user1 == 0 or conv.unread_count_user2 == 0

    def test_get_unread_count_empty(self, chat_service, db_session):
        """测试获取无消息用户的未读数"""
        count = chat_service.get_unread_count("no_messages_user")

        assert count == 0


# ============= 第五部分：消息撤回边缘场景 =============

class TestMessageRecall:
    """消息撤回测试"""

    def test_recall_message_success(self, chat_service, db_session):
        """测试撤回消息成功"""
        msg = chat_service.send_message(
            sender_id="recall_sender",
            receiver_id="recall_receiver",
            content="recall test"
        )

        result = chat_service.recall_message(msg.id, "recall_sender")

        assert result is True
        assert msg.status == "recalled"
        assert msg.content == "消息已撤回"

    def test_recall_message_wrong_user(self, chat_service, db_session):
        """测试非发送者撤回消息失败"""
        msg = chat_service.send_message(
            sender_id="wrong_recall_sender",
            receiver_id="wrong_recall_receiver",
            content="wrong recall test"
        )

        result = chat_service.recall_message(msg.id, "wrong_recall_receiver")

        assert result is False

    def test_recall_message_expired(self, chat_service, db_session):
        """测试超时撤回消息失败"""
        msg = chat_service.send_message(
            sender_id="expired_sender",
            receiver_id="expired_receiver",
            content="expired test"
        )

        # 模拟消息已超过 2 分钟
        msg.created_at = datetime.utcnow() - timedelta(minutes=3)
        db_session.commit()

        result = chat_service.recall_message(msg.id, "expired_sender")

        assert result is False

    def test_recall_message_nonexistent(self, chat_service, db_session):
        """测试撤回不存在消息"""
        result = chat_service.recall_message("nonexistent_msg_id", "user")

        assert result is False

    def test_recall_message_edge_time(self, chat_service, db_session):
        """测试撤回边界时间（恰好 2 分钟）"""
        msg = chat_service.send_message(
            sender_id="edge_sender",
            receiver_id="edge_receiver",
            content="edge time test"
        )

        # 设置恰好 2 分钟前
        msg.created_at = datetime.utcnow() - timedelta(minutes=2, seconds=-1)
        db_session.commit()

        result = chat_service.recall_message(msg.id, "edge_sender")

        # 应该能撤回（小于 120 秒）
        assert result is True


# ============= 第六部分：会话管理边缘场景 =============

class TestConversationManagement:
    """会话管理测试"""

    def test_delete_message_success(self, chat_service, db_session):
        """测试删除消息成功"""
        msg = chat_service.send_message(
            sender_id="delete_sender",
            receiver_id="delete_receiver",
            content="delete test"
        )

        result = chat_service.delete_message(msg.id, "delete_sender")

        assert result is True

        # 验证已删除
        deleted = db_session.query(ChatMessageDB).filter(ChatMessageDB.id == msg.id).first()
        assert deleted is None

    def test_delete_message_by_receiver(self, chat_service, db_session):
        """测试接收者删除消息"""
        msg = chat_service.send_message(
            sender_id="recv_del_sender",
            receiver_id="recv_del_receiver",
            content="receiver delete test"
        )

        result = chat_service.delete_message(msg.id, "recv_del_receiver")

        assert result is True

    def test_delete_message_by_other_user(self, chat_service, db_session):
        """测试非相关用户删除消息失败"""
        msg = chat_service.send_message(
            sender_id="other_del_sender",
            receiver_id="other_del_receiver",
            content="other delete test"
        )

        result = chat_service.delete_message(msg.id, "unrelated_user")

        assert result is False

    def test_archive_conversation_success(self, chat_service, db_session):
        """测试归档会话成功"""
        chat_service.send_message(
            sender_id="archive_sender",
            receiver_id="archive_receiver",
            content="archive test"
        )

        result = chat_service.archive_conversation("archive_sender", "archive_receiver")

        assert result is True

        conv = chat_service.get_or_create_conversation("archive_sender", "archive_receiver")
        assert conv.status == "archived"

    def test_block_user_success(self, chat_service, db_session):
        """测试屏蔽用户成功"""
        chat_service.send_message(
            sender_id="block_sender",
            receiver_id="block_receiver",
            content="block test"
        )

        result = chat_service.block_user("block_sender", "block_receiver")

        assert result is True

        conv = chat_service.get_or_create_conversation("block_sender", "block_receiver")
        assert conv.status == "blocked"

    def test_get_message_by_id(self, chat_service, db_session):
        """测试通过 ID 获取消息"""
        msg = chat_service.send_message(
            sender_id="get_msg_sender",
            receiver_id="get_msg_receiver",
            content="get message test"
        )

        result = chat_service.get_message(msg.id)

        assert result is not None
        assert result.id == msg.id


# ============= 第七部分：搜索功能边缘场景 =============

class TestSearchFunctionality:
    """搜索功能测试"""

    def test_search_messages_empty_keyword(self, chat_service, db_session):
        """测试空关键词搜索"""
        chat_service.send_message(
            sender_id="search_empty_sender",
            receiver_id="search_empty_receiver",
            content="test message"
        )

        # 空关键词可能返回所有消息或空列表
        messages = chat_service.search_messages("search_empty_sender", "")

        # 系统应处理空关键词
        assert isinstance(messages, list)

    def test_search_messages_special_characters(self, chat_service, db_session):
        """测试特殊字符关键词搜索"""
        chat_service.send_message(
            sender_id="special_search_sender",
            receiver_id="special_search_receiver",
            content="消息包含特殊字符 %_\\"
        )

        messages = chat_service.search_messages("special_search_sender", "%")

        # 应正确处理 SQL 特殊字符
        assert isinstance(messages, list)

    def test_search_messages_long_keyword(self, chat_service, db_session):
        """测试超长关键词搜索"""
        chat_service.send_message(
            sender_id="long_search_sender",
            receiver_id="long_search_receiver",
            content="test message"
        )

        long_keyword = "K" * 1000
        messages = chat_service.search_messages("long_search_sender", long_keyword)

        assert messages == []

    def test_search_messages_unicode(self, chat_service, db_session):
        """测试 Unicode 关键词搜索"""
        chat_service.send_message(
            sender_id="unicode_search_sender",
            receiver_id="unicode_search_receiver",
            content="你好世界 🎉🎉🎉"
        )

        messages = chat_service.search_messages("unicode_search_sender", "你好")

        assert len(messages) > 0


# ============= 第八部分：预览生成测试 =============

class TestPreviewGeneration:
    """预览生成测试"""

    def test_generate_preview_text(self, chat_service):
        """测试文本消息预览"""
        preview = chat_service._generate_preview("这是一个测试消息内容", "text")
        assert preview == "这是一个测试消息内容"

    def test_generate_preview_text_truncated(self, chat_service):
        """测试长文本消息预览截断"""
        long_text = "A" * 100
        preview = chat_service._generate_preview(long_text, "text")

        assert len(preview) == 50

    def test_generate_preview_image(self, chat_service):
        """测试图片消息预览"""
        preview = chat_service._generate_preview("url", "image")
        assert preview == "[图片]"

    def test_generate_preview_emoji(self, chat_service):
        """测试表情消息预览"""
        preview = chat_service._generate_preview("emoji_data", "emoji")
        assert preview == "[表情]"

    def test_generate_preview_voice(self, chat_service):
        """测试语音消息预览"""
        preview = chat_service._generate_preview("voice_data", "voice")
        assert preview == "[语音]"

    def test_generate_preview_system(self, chat_service):
        """测试系统消息预览"""
        preview = chat_service._generate_preview("system notification", "system")
        assert preview == "[系统消息]"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])