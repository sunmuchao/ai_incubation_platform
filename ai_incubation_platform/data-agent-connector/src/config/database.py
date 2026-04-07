"""
数据库配置和连接管理

支持 SQLite 和 PostgreSQL 作为后端存储
"""
from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from typing import Optional, AsyncGenerator, Generator
from contextlib import asynccontextmanager
import os

from config.settings import BaseSettings

# 加载配置
settings = BaseSettings()


class DatabaseConfig:
    """数据库配置"""
    def __init__(self):
        # 从环境变量读取数据库配置
        self.db_type = os.getenv("LINEAGE_DB_TYPE", "sqlite").lower()
        self.db_path = os.getenv("LINEAGE_DB_PATH", "./data/lineage.db")
        self.db_host = os.getenv("LINEAGE_DB_HOST", "localhost")
        self.db_port = os.getenv("LINEAGE_DB_PORT", "5432")
        self.db_name = os.getenv("LINEAGE_DB_NAME", "lineage_db")
        self.db_user = os.getenv("LINEAGE_DB_USER", "postgres")
        self.db_password = os.getenv("LINEAGE_DB_PASSWORD", "postgres")

        # 连接池配置
        self.pool_size = int(os.getenv("LINEAGE_POOL_SIZE", "10"))
        self.max_overflow = int(os.getenv("LINEAGE_MAX_OVERFLOW", "20"))
        self.echo = os.getenv("LINEAGE_ECHO", "false").lower() == "true"

        # 确保数据目录存在
        if self.db_type == "sqlite":
            db_dir = os.path.dirname(self.db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)

    @property
    def sync_url(self) -> str:
        """获取同步数据库 URL"""
        if self.db_type == "sqlite":
            return f"sqlite:///{self.db_path}"
        elif self.db_type == "postgresql":
            return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")

    @property
    def async_url(self) -> str:
        """获取异步数据库 URL"""
        if self.db_type == "sqlite":
            return f"sqlite+aiosqlite:///{self.db_path}"
        elif self.db_type == "postgresql":
            return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")


# 全局数据库配置
db_config = DatabaseConfig()


class DatabaseManager:
    """数据库管理器"""

    def __init__(self, config: DatabaseConfig = None):
        self.config = config or db_config
        self._sync_engine = None
        self._async_engine = None
        self._sync_session_factory = None
        self._async_session_factory = None

    @property
    def sync_engine(self):
        """获取同步数据库引擎"""
        if self._sync_engine is None:
            self._sync_engine = create_engine(
                self.config.sync_url,
                pool_size=self.config.pool_size,
                max_overflow=self.config.max_overflow,
                echo=self.config.echo,
                future=True
            )
            # SQLite 需要启用外键支持
            if self.config.db_type == "sqlite":
                @event.listens_for(self._sync_engine, "connect")
                def set_sqlite_pragma(dbapi_connection, connection_record):
                    cursor = dbapi_connection.cursor()
                    cursor.execute("PRAGMA foreign_keys=ON")
                    cursor.close()
        return self._sync_engine

    @property
    def async_engine(self):
        """获取异步数据库引擎"""
        if self._async_engine is None:
            self._async_engine = create_async_engine(
                self.config.async_url,
                pool_size=self.config.pool_size,
                max_overflow=self.config.max_overflow,
                echo=self.config.echo,
                future=True
            )
        return self._async_engine

    @property
    def sync_session_factory(self):
        """获取同步 Session 工厂"""
        if self._sync_session_factory is None:
            # 导入所有模型以确保它们被注册到 Base
            from models import Base
            Base.metadata.create_all(self.sync_engine)
            self._sync_session_factory = sessionmaker(
                bind=self.sync_engine,
                class_=Session,
                expire_on_commit=False,
                future=True
            )
        return self._sync_session_factory

    @property
    def async_session_factory(self):
        """获取异步 Session 工厂"""
        if self._async_session_factory is None:
            self._async_session_factory = async_sessionmaker(
                self.async_engine,
                class_=AsyncSession,
                expire_on_commit=False,
                future=True
            )
        return self._async_session_factory

    def get_sync_session(self) -> Session:
        """获取同步 Session"""
        return self.sync_session_factory()

    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """获取异步 Session 上下文"""
        session = self.async_session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    async def init_db(self):
        """初始化数据库（创建表）"""
        # 导入所有模型以确保它们被注册到 Base
        from models import Base
        async with self.async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def close(self):
        """关闭数据库连接"""
        if self._async_engine:
            await self._async_engine.dispose()
        if self._sync_engine:
            self._sync_engine.dispose()


# 全局数据库管理器实例
db_manager = DatabaseManager()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """依赖注入：获取数据库 Session"""
    async with db_manager.get_async_session() as session:
        yield session


def get_sync_db_session() -> Generator[Session, None, None]:
    """依赖注入：获取同步数据库 Session"""
    session = db_manager.get_sync_session()
    try:
        yield session
    finally:
        session.close()
