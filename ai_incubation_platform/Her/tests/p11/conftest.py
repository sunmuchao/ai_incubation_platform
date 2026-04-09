"""
P11 测试专用配置

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
from models import p11_models


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
def test_db():
    """创建测试数据库会话"""
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
