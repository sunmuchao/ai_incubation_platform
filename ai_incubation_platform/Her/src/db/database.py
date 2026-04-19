"""
数据库连接管理模块

优化配置：
- 连接池大小可调
- 支持预 ping 检测
- 连接回收机制
"""
from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from config import settings
from utils.logger import logger, get_trace_id

# 数据库配置
DATABASE_URL = settings.database_url

# 确保使用同步 SQLite 驱动
if DATABASE_URL.startswith("sqlite:///"):
    # 强制使用同步 SQLite 驱动，避免 aiosqlite 导致的异步问题
    DATABASE_URL = DATABASE_URL.replace("sqlite+aiosqlite://", "sqlite:///")

# 连接池配置（生产环境优化）
POOL_SIZE = int(settings.database_pool_size) if hasattr(settings, 'database_pool_size') else 30
MAX_OVERFLOW = int(settings.database_max_overflow) if hasattr(settings, 'database_max_overflow') else 60
POOL_TIMEOUT = int(settings.database_pool_timeout) if hasattr(settings, 'database_pool_timeout') else 10
POOL_RECYCLE = int(settings.database_pool_recycle) if hasattr(settings, 'database_pool_recycle') else 1800  # 30 分钟

# 创建数据库引擎
if "sqlite" in DATABASE_URL:
    # SQLite 配置（开发/测试）
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,  # 使用前检测连接有效性
        pool_recycle=POOL_RECYCLE,
    )
    logger.info("SQLite database engine created (development mode)")
else:
    # PostgreSQL 配置（生产环境）
    engine = create_engine(
        DATABASE_URL,
        pool_size=POOL_SIZE,
        max_overflow=MAX_OVERFLOW,
        pool_timeout=POOL_TIMEOUT,
        pool_pre_ping=True,  # 使用前检测连接有效性
        pool_recycle=POOL_RECYCLE,  # 连接回收时间，避免 MySQL/PostgreSQL 超时断开
    )
    logger.info(f"PostgreSQL database engine created with pool_size={POOL_SIZE}, max_overflow={MAX_OVERFLOW}")

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基类
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    获取数据库会话的依赖注入函数
    用于 FastAPI 路由的 Depends
    """
    trace_id = get_trace_id()
    logger.debug(f"🗄️ [DB:SESSION] Acquiring session trace_id={trace_id}")
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        # 🔧 [修复] 捕获完整的验证错误详情（Pydantic ValidationError 包含字段信息）
        error_detail = str(e)
        if hasattr(e, 'errors'):
            # Pydantic ValidationError 有 errors() 方法返回详细字段错误
            error_detail = f"{e} - Details: {e.errors()}"
        logger.error(f"🗄️ [DB:SESSION] Error during session trace_id={trace_id} error={error_detail}", exc_info=True)
        raise
    finally:
        logger.debug(f"🗄️ [DB:SESSION] Closing session trace_id={trace_id}")
        db.close()


def init_db() -> None:
    """
    初始化数据库 - 创建所有表
    """
    logger.info("Initializing database...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized successfully")


def reset_db() -> None:
    """
    重置数据库 - 删除所有表并重新创建
    仅用于开发/测试环境
    """
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
