"""
P12 测试专用配置

使用独立的内存数据库，避免与主测试配置冲突
"""
import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 添加项目路径
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from db.database import Base
from db import models as db_models  # 导入主模型以获取 UserDB, ConversationDB, ChatMessageDB
from models import behavior_lab_models


@pytest.fixture(scope="function")
def db_session():
    """创建测试数据库会话 - 每个测试独立的数据库"""
    # 每个测试使用独立的内存数据库
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine,
    )
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def sample_users(db_session):
    """创建测试用户 - 使用唯一 ID 避免冲突"""
    unique_id = uuid.uuid4().hex[:8]
    user_a = db_models.UserDB(
        id=f"user_a_{unique_id}",
        name="test_user_a",
        email=f"user_a_{unique_id}@test.com",
        password_hash="hashed_password_123",
        age=28,
        gender="male",
        location="北京"
    )
    user_b = db_models.UserDB(
        id=f"user_b_{unique_id}",
        name="test_user_b",
        email=f"user_b_{unique_id}@test.com",
        password_hash="hashed_password_456",
        age=26,
        gender="female",
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
        id=f"conv_{uuid.uuid4().hex[:8]}",
        user_id_1=user_a.id,
        user_id_2=user_b.id,
        message_content="测试对话内容",
        sender_id=user_a.id
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
            id=f"msg_{uuid.uuid4().hex[:8]}_{i}",
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
