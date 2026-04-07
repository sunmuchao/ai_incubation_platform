"""
数据库配置和会话管理 - P0 数据持久化增强

支持:
- SQLite (开发/测试)
- PostgreSQL (生产)
- 读写分离 (可选)
- 批量写入优化
- 历史数据查询
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator, Optional
from core.config import settings
import logging

logger = logging.getLogger(__name__)

# 数据库 URL 配置
DATABASE_URL = settings.DATABASE_URL or "sqlite:///./ai_traffic_booster.db"

# 确保使用同步 SQLite 驱动
if DATABASE_URL.startswith("sqlite"):
    # 强制使用同步 SQLite 驱动，避免 aiosqlite 导致的异步问题
    DATABASE_URL = DATABASE_URL.replace("sqlite+aiosqlite://", "sqlite:///")

# 创建数据库引擎
if settings.DATABASE_URL and settings.DATABASE_URL.startswith("postgresql"):
    engine = create_engine(
        DATABASE_URL,
        pool_size=20,
        max_overflow=40,
        pool_recycle=3600,
        pool_pre_ping=True,
        echo=settings.DEBUG
    )
else:
    # SQLite 用于开发/测试
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=settings.DEBUG
    )

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基类
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    获取数据库会话的依赖注入函数

    Yields:
        Session: 数据库会话对象

    Example:
        ```python
        @router.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
        ```
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    初始化数据库，创建所有表
    """
    logger.info("Initializing database...")

    # 导入所有模型以确保它们被注册到 Base
    try:
        from . import postgresql_models  # noqa: F401
        logger.info("PostgreSQL models loaded")
    except Exception as e:
        logger.warning(f"Failed to load postgresql_models: {e}")

    try:
        from . import event_writer  # noqa: F401
        logger.info("Event writer models loaded")
    except Exception as e:
        logger.warning(f"Failed to load event_writer models: {e}")

    try:
        from . import historical_query  # noqa: F401
        logger.info("Historical query models loaded")
    except Exception as e:
        logger.warning(f"Failed to load historical_query models: {e}")

    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized successfully")


def drop_db() -> None:
    """
    删除所有表（仅用于测试）
    """
    logger.warning("Dropping all database tables...")
    Base.metadata.drop_all(bind=engine)
    logger.warning("All tables dropped")


# ==================== P0 数据持久化增强导入 ====================

# 延迟导入避免循环依赖
def get_postgresql_models():
    """获取 PostgreSQL 模型模块"""
    from . import postgresql_models
    return postgresql_models


def get_postgresql_config():
    """获取 PostgreSQL 配置模块"""
    from . import postgresql_config
    return postgresql_config


def get_event_writer():
    """获取事件写入模块"""
    from . import event_writer
    return event_writer


def get_historical_query():
    """获取历史数据查询模块"""
    from . import historical_query
    return historical_query


# 便捷函数
def init_postgresql_db(database_url: Optional[str] = None, **kwargs):
    """
    初始化 PostgreSQL 数据库

    Args:
        database_url: 数据库 URL (可选，默认使用 settings.DATABASE_URL)
        **kwargs: 其他配置参数

    Returns:
        数据库管理器实例
    """
    from .postgresql_config import init_database
    db_url = database_url or settings.DATABASE_URL
    return init_database(db_url, **kwargs)


def get_event_writer_instance():
    """获取事件写入器实例"""
    from .event_writer import get_event_writer, init_event_writer
    writer = get_event_writer()
    if writer is None:
        writer = init_event_writer()
    return writer


def get_historical_query_service():
    """获取历史数据查询服务实例"""
    from .historical_query import get_historical_query_service
    return get_historical_query_service()
