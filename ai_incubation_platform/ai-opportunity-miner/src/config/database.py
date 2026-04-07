"""
数据库配置和会话管理
使用 SQLite 作为默认存储（便于演示和开发）
支持无缝切换到 PostgreSQL/MySQL
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from config.settings import settings
import os

# 数据库 URL - 默认使用 SQLite
DATABASE_URL = settings.database_url or f"sqlite:///{os.path.join(settings.data_dir, 'opportunity_miner.db')}"

# 确保使用同步 SQLite 驱动
if DATABASE_URL.startswith("sqlite"):
    # 强制使用同步 SQLite 驱动，避免 aiosqlite 导致的异步问题
    DATABASE_URL = DATABASE_URL.replace("sqlite+aiosqlite://", "sqlite:///")

# 对于 SQLite，需要特殊配置以支持检查约束
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

# 创建引擎
engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=settings.debug,  # 调试模式下打印 SQL
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 基础模型类
Base = declarative_base()


def get_db() -> Session:
    """
    获取数据库会话的依赖注入函数
    用于 FastAPI 路由
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化数据库，创建所有表"""
    # 导入所有模型以注册到 Base
    from models import opportunity  # noqa: F401
    from models import db_models  # noqa: F401
    # 导入 P7 模型（确保注册）
    from models.db_models import (  # noqa: F401
        UserContributionDB, UserPointsDB, PointsTransactionDB,
        CommunityVoteDB, CommunityCommentDB, APIKeyDB, APIUsageLogDB
    )

    Base.metadata.create_all(bind=engine)


def reset_db():
    """重置数据库，删除所有表后重新创建"""
    from models import opportunity  # noqa: F401

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
