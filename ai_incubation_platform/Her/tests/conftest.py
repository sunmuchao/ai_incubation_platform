"""
测试配置文件

使用统一模型注册中心导入所有模型，避免重复定义和导入问题。
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# ============= 第一步：创建测试数据库引擎 =============
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)

# ============= 第二步：导入并覆盖 SessionLocal =============
from db import database
database.SessionLocal = TestingSessionLocal
database.engine = test_engine

# ============= 第三步：导入基础模型 =============
from db.database import Base

# 导入 db.models 以注册基础模型
from db import models as db_models  # noqa: F401

# ============= 第四步：使用统一模型注册中心导入所有模型 =============
# 这样避免了手动导入各个 pXX_models 导致的重复定义问题
import models  # 导入统一模型中心  # noqa: F401

# ============= 第五步：创建表 =============
Base.metadata.create_all(bind=test_engine)


@pytest.fixture(scope="function")
def db_session():
    """数据库会话 Fixture"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture
def test_user_data():
    """测试用户数据"""
    return {
        "name": "测试用户",
        "email": "test@example.com",
        "age": 28,
        "gender": "male",
        "location": "北京市",
        "preferred_age_min": 22,
        "preferred_age_max": 32,
        "preferred_gender": "female",
        "interests": ["阅读", "旅行", "音乐"],
        "values": {
            "openness": 0.8,
            "conscientiousness": 0.7,
            "extraversion": 0.6,
            "agreeableness": 0.75,
            "neuroticism": 0.3
        },
        "goal": "serious"
    }


@pytest.fixture
def test_cold_start_user():
    """冷启动用户（标签极少）"""
    return {
        "name": "新用户",
        "email": "new@example.com",
        "age": 25,
        "gender": "female",
        "location": "上海市",
        "interests": [],
        "values": {},
        "goal": "serious"
    }
