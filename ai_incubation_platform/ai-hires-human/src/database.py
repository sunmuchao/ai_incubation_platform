"""
数据库配置与基础模型。
"""
import os
from datetime import datetime
from typing import AsyncGenerator

from sqlalchemy import DateTime, func
from sqlalchemy.ext.asyncio import AsyncAttrs, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# 数据库配置
# 从环境变量或 .env 文件读取，默认使用 SQLite 进行测试
import os
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# 检查是否配置了 PostgreSQL
pg_url = os.getenv("AI_HIRES_HUMAN_DATABASE_URL")
if pg_url:
    DATABASE_URL = pg_url
else:
    # 默认使用 SQLite 进行测试
    DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# 创建异步引擎
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(AsyncAttrs, DeclarativeBase):
    """基础模型类，包含通用字段。"""
    __abstract__ = True

    id: Mapped[str] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """依赖注入：获取数据库会话。"""
    async with AsyncSessionLocal() as session:
        yield session


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """依赖注入：获取数据库会话（别名）。"""
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    """初始化数据库表结构。"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
