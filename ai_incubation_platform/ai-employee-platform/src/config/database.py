"""
数据库配置和会话管理
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
import os

# 数据库 URL - 支持 SQLite 和 PostgreSQL
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./ai_employee_platform.db"  # 默认使用 SQLite
)

# PostgreSQL 示例:
# DATABASE_URL = "postgresql://user:password@localhost:5432/ai_employee_platform"

# 创建数据库引擎
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}  # SQLite 需要
    )
else:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=10, max_overflow=20)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 基础模型类
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    获取数据库会话依赖
    在 FastAPI 中作为依赖注入使用
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """初始化数据库，创建所有表"""
    # 先添加延迟关联关系（避免循环依赖）
    try:
        from models.file_models import add_file_relationships
        add_file_relationships()
    except Exception as e:
        print(f"Warning: Failed to add file relationships: {e}")

    try:
        from models.observability_models import add_observability_relationships
        add_observability_relationships()
    except Exception as e:
        print(f"Warning: Failed to add observability relationships: {e}")

    try:
        from models.p4_models import add_p4_relationships
        add_p4_relationships()
    except Exception as e:
        print(f"Warning: Failed to add p4 relationships: {e}")

    try:
        from models.p4_training_models import add_training_relationships
        add_training_relationships()
    except Exception as e:
        print(f"Warning: Failed to add training relationships: {e}")

    # 创建所有表
    Base.metadata.create_all(bind=engine)
