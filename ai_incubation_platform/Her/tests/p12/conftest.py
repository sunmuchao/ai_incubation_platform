"""
P12 测试专用配置

使用独立的内存数据库，避免与主测试配置冲突
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 添加项目路径
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from db.database import Base
from db import models as db_models  # 导入主模型以获取 UserDB, ConversationDB, ChatMessageDB
from models import p12_models


# 创建测试数据库引擎
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)


@pytest.fixture(scope="function")
def db_session():
    """创建测试数据库会话"""
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def sample_users(db_session):
    """创建测试用户"""
    user_a = db_models.UserDB(
        id="user_a_001",
        username="test_user_a",
        email="user_a@test.com",
        age=28,
        location="北京"
    )
    user_b = db_models.UserDB(
        id="user_b_001",
        username="test_user_b",
        email="user_b@test.com",
        age=26,
        location="北京"
    )
    db_session.add(user_a)
    db_session.add(user_b)
    db_session.commit()
    return user_a, user_b


@pytest.fixture
def sample_conversation(db_session, sample_users):
    """创建测试对话"""
    user_a, user_b = sample_users
    conversation = db_models.ConversationDB(
        id="conv_001",
        user_a_id=user_a.id,
        user_b_id=user_b.id,
        status="active"
    )
    db_session.add(conversation)
    db_session.commit()
    return conversation


@pytest.fixture
def sample_messages(db_session, sample_conversation, sample_users):
    """创建测试消息"""
    user_a, user_b = sample_users
    messages = []
    now = __import__('datetime').datetime.utcnow()

    for i in range(10):
        msg = db_models.ChatMessageDB(
            id=f"msg_{i}",
            conversation_id=sample_conversation.id,
            sender_id=user_a.id if i % 2 == 0 else user_b.id,
            receiver_id=user_b.id if i % 2 == 0 else user_a.id,
            content=f"测试消息 {i}",
            created_at=now - __import__('datetime').timedelta(minutes=(10 - i) * 5)
        )
        messages.append(msg)
        db_session.add(msg)

    db_session.commit()
    return messages
