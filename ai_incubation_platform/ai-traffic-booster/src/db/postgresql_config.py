"""
PostgreSQL 数据库配置 - P0 数据持久化增强

功能:
1. 支持 PostgreSQL 连接池优化
2. 支持异步数据库操作
3. 支持数据库迁移
4. 支持读写分离 (可选)
"""
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, scoped_session
from sqlalchemy.pool import QueuePool
from sqlalchemy.engine import Engine
from contextlib import contextmanager
from typing import Generator, Optional, Dict, Any
from datetime import datetime
import logging
import os

logger = logging.getLogger(__name__)


# ==================== 数据库引擎配置 ====================

class DatabaseConfig:
    """数据库配置类"""

    def __init__(
        self,
        database_url: str,
        pool_size: int = 20,
        max_overflow: int = 40,
        pool_recycle: int = 3600,
        pool_pre_ping: bool = True,
        echo: bool = False,
        echo_pool: bool = False,
        pool_timeout: int = 30,
        poolclass: type = QueuePool
    ):
        self.database_url = database_url
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_recycle = pool_recycle
        self.pool_pre_ping = pool_pre_ping
        self.echo = echo
        self.echo_pool = echo_pool
        self.pool_timeout = pool_timeout
        self.poolclass = poolclass

    def create_engine(self) -> Engine:
        """创建数据库引擎"""
        return create_engine(
            self.database_url,
            pool_size=self.pool_size,
            max_overflow=self.max_overflow,
            pool_recycle=self.pool_recycle,
            pool_pre_ping=self.pool_pre_ping,
            echo=self.echo,
            echo_pool=self.echo_pool,
            pool_timeout=self.pool_timeout,
            poolclass=self.poolclass,
        )


# ==================== 数据库管理器 ====================

class DatabaseManager:
    """
    数据库管理器

    功能:
    - 管理数据库引擎和会话
    - 支持主从分离 (读写分离)
    - 提供上下文管理器
    - 支持健康检查
    """

    def __init__(self):
        self._engine: Optional[Engine] = None
        self._read_engine: Optional[Engine] = None  # 只读副本 (可选)
        self._session_factory: Optional[sessionmaker] = None
        self._read_session_factory: Optional[sessionmaker] = None
        self._initialized = False

    def initialize(
        self,
        database_url: str,
        read_database_url: Optional[str] = None,
        pool_size: int = 20,
        max_overflow: int = 40,
        **kwargs
    ) -> None:
        """
        初始化数据库连接

        Args:
            database_url: 主数据库 URL
            read_database_url: 只读副本 URL (可选，用于读写分离)
            pool_size: 连接池大小
            max_overflow: 最大溢出连接数
            **kwargs: 其他配置参数
        """
        if self._initialized:
            logger.warning("Database already initialized")
            return

        logger.info(f"Initializing database with URL: {self._mask_url(database_url)}")

        # 创建主引擎 (写)
        config = DatabaseConfig(
            database_url=database_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            **kwargs
        )
        self._engine = config.create_engine()
        self._session_factory = sessionmaker(autocommit=False, autoflush=False, bind=self._engine)

        # 创建只读引擎 (可选)
        if read_database_url:
            logger.info(f"Initializing read replica with URL: {self._mask_url(read_database_url)}")
            read_config = DatabaseConfig(
                database_url=read_database_url,
                pool_size=pool_size,
                max_overflow=max_overflow,
                **kwargs
            )
            self._read_engine = read_config.create_engine()
            self._read_session_factory = sessionmaker(autocommit=False, autoflush=False, bind=self._read_engine)

        self._initialized = True
        logger.info("Database initialized successfully")

    def _mask_url(self, url: str) -> str:
        """掩盖数据库 URL 中的密码"""
        if "@" in url:
            prefix, rest = url.split("@", 1)
            if ":" in prefix:
                base, password = prefix.rsplit(":", 1)
                return f"{base}:***@{rest}"
        return url

    @property
    def engine(self) -> Engine:
        """获取主引擎"""
        if not self._initialized:
            raise RuntimeError("Database not initialized")
        return self._engine

    @property
    def read_engine(self) -> Engine:
        """获取只读引擎"""
        if not self._read_engine:
            return self._engine  # 降级到主引擎
        return self._read_engine

    def get_session(self, read_only: bool = False) -> Session:
        """
        获取数据库会话

        Args:
            read_only: 是否使用只读会话

        Returns:
            数据库会话对象
        """
        if not self._initialized:
            # 自动初始化数据库
            logger.warning("Database not initialized, auto-initializing...")
            from core.config import settings
            db_url = settings.DATABASE_URL or "sqlite:///./ai_traffic_booster.db"
            self.initialize(database_url=db_url)
            if not self._initialized:
                raise RuntimeError("Database not initialized and auto-init failed")

        if read_only and self._read_session_factory:
            return self._read_session_factory()
        return self._session_factory()

    @contextmanager
    def session_scope(self, read_only: bool = False) -> Generator[Session, None, None]:
        """
        会话上下文管理器

        用法:
            with db_manager.session_scope() as session:
                session.query(...).all()

        Args:
            read_only: 是否使用只读会话
        """
        session = self.get_session(read_only=read_only)
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_dependency(self, read_only: bool = False) -> Generator[Session, None, None]:
        """
        FastAPI 依赖注入版本

        用法:
            @app.get("/items")
            def get_items(db: Session = Depends(db_manager.get_dependency)):
                return db.query(...).all()
        """
        session = self.get_session(read_only=read_only)
        try:
            yield session
        finally:
            session.close()

    def create_tables(self, base: declarative_base) -> None:
        """创建所有表"""
        logger.info("Creating database tables...")
        base.metadata.create_all(bind=self._engine)
        logger.info("Database tables created successfully")

    def drop_tables(self, base: declarative_base) -> None:
        """删除所有表 (谨慎使用)"""
        logger.warning("Dropping all database tables...")
        base.metadata.drop_all(bind=self._engine)
        logger.warning("All tables dropped")

    def check_health(self) -> Dict[str, Any]:
        """
        检查数据库健康状态

        Returns:
            健康状态字典
        """
        try:
            with self.session_scope() as session:
                # 执行简单查询测试连接
                result = session.execute(text("SELECT 1"))
                result.fetchone()

                # 获取连接池状态
                pool_status = {
                    "pool_size": self._engine.pool.size(),
                    "checked_in": self._engine.pool.checkedin(),
                    "checked_out": self._engine.pool.checkedout(),
                    "overflow": self._engine.pool.overflow(),
                    "invalid": self._engine.pool.invalidatedcount() if hasattr(self._engine.pool, 'invalidatedcount') else 0,
                }

                return {
                    "status": "healthy",
                    "database": "connected",
                    "pool": pool_status,
                    "timestamp": datetime.utcnow().isoformat()
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    def execute_query(self, query: str, params: Optional[Dict] = None, read_only: bool = True) -> list:
        """
        执行原生 SQL 查询

        Args:
            query: SQL 查询语句
            params: 查询参数
            read_only: 是否使用只读连接

        Returns:
            查询结果列表
        """
        with self.session_scope(read_only=read_only) as session:
            result = session.execute(text(query), params or {})
            return result.fetchall()

    def dispose(self) -> None:
        """释放数据库连接"""
        if self._engine:
            self._engine.dispose()
            logger.info("Database engine disposed")
        if self._read_engine:
            self._read_engine.dispose()
            logger.info("Read replica engine disposed")
        self._initialized = False


# ==================== 全局实例 ====================

# 全局数据库管理器实例
db_manager = DatabaseManager()


def get_db_manager() -> DatabaseManager:
    """获取数据库管理器实例"""
    return db_manager


def init_database(
    database_url: str,
    read_database_url: Optional[str] = None,
    **kwargs
) -> DatabaseManager:
    """
    初始化全局数据库

    Args:
        database_url: 主数据库 URL
        read_database_url: 只读副本 URL (可选)
        **kwargs: 其他配置参数

    Returns:
        数据库管理器实例
    """
    db_manager.initialize(
        database_url=database_url,
        read_database_url=read_database_url,
        **kwargs
    )
    return db_manager


# 兼容旧代码的函数
def get_db_session():
    """获取数据库会话 (兼容旧代码)"""
    return db_manager.get_session()
