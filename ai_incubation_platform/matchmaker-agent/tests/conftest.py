"""
测试配置文件
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# ============= 第一步：创建测试数据库引擎 =============
# 全局测试数据库配置
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
# 在导入任何使用 SessionLocal 的模块之前，先覆盖它
import src.db.database
src.db.database.SessionLocal = TestingSessionLocal
src.db.database.engine = test_engine

# ============= 第三步：导入所有模型以确保表被注册到 Base.metadata =============
# 必须在导入 main 之前导入模型，确保表被注册
from src.db.database import Base
import src.db.models  # noqa: F401
import src.models.p9_models  # noqa: F401
import src.models.p10_models  # noqa: F401
import src.models.user  # noqa: F401
import src.models.membership  # noqa: F401
import src.models.p8_models  # noqa: F401

# ============= 第四步：创建表 =============
# 在导入 main 之前先创建表
Base.metadata.create_all(bind=test_engine)

# ============= 第五步：导入 main 和 app =============
# 此时 SessionLocal 已被覆盖，模型已注册，表已创建
from fastapi.testclient import TestClient
from src.main import app
from src.db.database import get_db
from typing import Generator


@pytest.fixture(scope="function")
def db_session():
    """数据库会话 Fixture"""
    # 表已经在导入时创建，这里只需要提供会话
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture(scope="function")
def client(db_session) -> Generator[TestClient, None, None]:
    """测试客户端 Fixture"""
    # 使用内存数据库进行测试

    def override_get_db():
        # 在同一个测试函数内复用同一个 Session，保证跨请求数据一致
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


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
    """冷启动测试用户（标签极少）"""
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
