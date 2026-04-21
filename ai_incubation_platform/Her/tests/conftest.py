"""
测试配置文件

使用统一模型注册中心导入所有模型，避免重复定义和导入问题。
增强测试隔离：每个测试独立数据库，统一 mock fixture。
"""
import pytest
import os
import uuid
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import MagicMock, patch, AsyncMock

# ============= 第一步：创建测试数据库引擎 =============
# 使用随机数据库路径确保 pytest-xdist 各 worker 独立
_worker_id = os.environ.get("PYTEST_XDIST_WORKER", "gw0")
test_engine = create_engine(
    f"sqlite:///:memory:{_worker_id}_{uuid.uuid4().hex[:8]}",
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

# ============= 第五步：为所有表添加 extend_existing =============
# 解决测试中表重复定义的问题
for table_name in list(Base.metadata.tables.keys()):
    Base.metadata.tables[table_name].extend_existing = True

# ============= 第六步：创建表 =============
Base.metadata.create_all(bind=test_engine)


@pytest.fixture(scope="function")
def db_session():
    """数据库会话 Fixture - 每个测试独立清理数据"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        # 清理所有表数据（按依赖顺序反向删除）
        for table in reversed(Base.metadata.sorted_tables):
            try:
                db.execute(text(f"DELETE FROM {table.name}"))
            except Exception:
                pass  # 表可能不存在或被锁定
        db.commit()
        db.close()


# ============= 统一 Mock Fixture =============

@pytest.fixture
def mock_llm():
    """统一 LLM mock fixture"""
    with patch("llm.client.call_llm") as mock:
        mock.return_value = '{"result": "mocked"}'
        yield mock


@pytest.fixture
def mock_llm_async():
    """统一异步 LLM mock fixture"""
    async_mock = AsyncMock(return_value='{"result": "mocked"}')
    with patch("llm.client.call_llm_async", async_mock):
        yield async_mock


@pytest.fixture
def mock_redis():
    """统一 Redis mock fixture"""
    mock = MagicMock()
    mock.get.return_value = None
    mock.set.return_value = True
    mock.delete.return_value = True
    mock.exists.return_value = False
    with patch("utils.cache_manager.redis_client", mock):
        yield mock


@pytest.fixture
def mock_cache():
    """统一缓存 mock fixture"""
    with patch("utils.cache_manager.CacheManager") as mock:
        mock_instance = MagicMock()
        mock_instance.get.return_value = None
        mock_instance.set.return_value = True
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_db_session():
    """统一数据库 mock fixture（用于不需要真实数据库的测试）"""
    mock = MagicMock()
    mock.query.return_value.filter.return_value.first.return_value = None
    mock.query.return_value.filter.return_value.all.return_value = []
    mock.add.return_value = None
    mock.commit.return_value = None
    mock.rollback.return_value = None
    mock.close.return_value = None
    yield mock


# ============= 测试数据工厂 =============

@pytest.fixture
def user_factory(db_session):
    """用户数据工厂"""
    from db.models import UserDB

    def create_user(**kwargs):
        defaults = {
            "id": str(uuid.uuid4()),
            "email": f"test_{uuid.uuid4().hex[:8]}@example.com",
            "password_hash": "hashed_password",
            "name": "Test User",
            "age": 28,
            "gender": "male",
            "location": "北京",
            "interests": "[]",
            "values": "{}",
            "bio": "",
        }
        defaults.update(kwargs)
        user = UserDB(**defaults)
        db_session.add(user)
        db_session.commit()
        return user

    return create_user


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
