"""
数据库基类和会话管理
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, DateTime, func
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import settings

# 创建异步引擎
engine = create_async_engine(
    settings.database_url,
    echo=settings.db_echo,
    future=True
)

# 创建会话工厂
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

#  declarative基类
Base = declarative_base()


class BaseModel(Base):
    """基础模型类，包含通用字段"""
    __abstract__ = True

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False, comment="更新时间")


async def get_db() -> AsyncSession:
    """获取数据库会话依赖"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """初始化数据库表结构"""
    async with engine.begin() as conn:
        # 创建所有表
        await conn.run_sync(Base.metadata.create_all)


async def drop_db() -> None:
    """删除所有表（仅用于开发环境）"""
    if settings.environment == "development":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
