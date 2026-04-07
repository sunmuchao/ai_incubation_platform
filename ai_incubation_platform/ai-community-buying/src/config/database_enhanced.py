"""
数据库配置增强版

支持：
- 连接池配置
- 事务管理
- 索引优化
- 性能监控
"""
from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from dotenv import load_dotenv
import os
import logging
from contextlib import contextmanager
from typing import Generator

load_dotenv()

logger = logging.getLogger(__name__)

# 数据库配置
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./ai_community_buying.db"
)

# 连接池配置
POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "20"))
POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "3600"))

# 根据数据库类型配置引擎
if DATABASE_URL.startswith("sqlite"):
    # SQLite 不支持连接池，但配置check_same_thread=False 允许多线程访问
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=os.getenv("DB_ECHO", "false").lower() == "true"
    )
else:
    # PostgreSQL/MySQL 使用连接池
    engine = create_engine(
        DATABASE_URL,
        poolclass=QueuePool,
        pool_size=POOL_SIZE,
        max_overflow=MAX_OVERFLOW,
        pool_timeout=POOL_TIMEOUT,
        pool_recycle=POOL_RECYCLE,
        echo=os.getenv("DB_ECHO", "false").lower() == "true",
        pool_pre_ping=True  # 连接前 ping 检测，避免连接失效
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ========== 数据库依赖 ==========
def get_db() -> Generator[Session, None, None]:
    """
    获取数据库会话的依赖注入函数

    使用方式:
    @router.get("/items")
    def get_items(db: Session = Depends(get_db)):
        ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    获取数据库会话的上下文管理器

    使用方式:
    with get_db_context() as db:
        db.query(...)
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ========== 事务管理 ==========
class TransactionManager:
    """
    事务管理器

    提供显式的事务边界管理，确保数据一致性。
    """

    @staticmethod
    @contextmanager
    def transaction(db: Session) -> Generator[Session, None, None]:
        """
        事务上下文管理器

        使用方式:
        with TransactionManager.transaction(db) as session:
            # 所有操作在一个事务中
            db.add(item)
            db.update(...)
            # 退出上下文时自动 commit，异常时自动 rollback
        """
        try:
            yield db
            db.commit()
            logger.info("事务提交成功")
        except Exception as e:
            db.rollback()
            logger.error(f"事务回滚：{str(e)}")
            raise

    @staticmethod
    def savepoint(db: Session, name: str):
        """创建保存点"""
        if db.bind.name == 'postgresql':
            db.execute(text(f"SAVEPOINT {name}"))
        elif db.bind.name == 'mysql':
            db.execute(text(f"SAVEPOINT {name}"))
        # SQLite 不支持保存点，跳过

    @staticmethod
    def rollback_to_savepoint(db: Session, name: str):
        """回滚到保存点"""
        if db.bind.name == 'postgresql':
            db.execute(text(f"ROLLBACK TO SAVEPOINT {name}"))
        elif db.bind.name == 'mysql':
            db.execute(text(f"ROLLBACK TO SAVEPOINT {name}"))


# ========== 连接监控 ==========
@event.listens_for(engine, "connect")
def on_connect(dbapi_connection, connection_record):
    """连接建立时的回调"""
    logger.debug(f"数据库连接建立，连接池状态：{engine.pool.status()}")


@event.listens_for(engine, "checkout")
def on_checkout(dbapi_connection, connection_record, connection_proxy):
    """从连接池获取连接时的回调"""
    logger.debug(
        f"连接 checkout: pool_size={engine.pool.size() if hasattr(engine.pool, 'size') else 'N/A'}, "
        f"checked_out={engine.pool.checkedout() if hasattr(engine.pool, 'checkedout') else 'N/A'}"
    )


@event.listens_for(engine, "checkin")
def on_checkin(dbapi_connection, connection_record):
    """连接归还到连接池时的回调"""
    logger.debug(
        f"连接 checkin: pool_size={engine.pool.size() if hasattr(engine.pool, 'size') else 'N/A'}, "
        f"checked_out={engine.pool.checkedout() if hasattr(engine.pool, 'checkedout') else 'N/A'}"
    )


# ========== 性能监控 ==========
@event.listens_for(engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """SQL 执行前的回调，用于记录慢查询"""
    conn.info.setdefault('query_start_time', []).append(__import__('time').time())


@event.listens_for(engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """SQL 执行后的回调，记录执行时间"""
    total = __import__('time').time() - conn.info['query_start_time'].pop(-1)
    threshold = float(os.getenv("SLOW_QUERY_THRESHOLD", "1.0"))

    if total > threshold:
        logger.warning(
            f"慢查询 detected: {total:.3f}s",
            extra={
                "statement": statement[:200],  # 只记录前 200 字符
                "parameters": parameters,
            }
        )


# ========== 数据库健康检查 ==========
def check_db_health() -> dict:
    """
    检查数据库健康状态

    Returns:
        健康状态字典
    """
    try:
        db = SessionLocal()
        # 执行简单查询测试
        db.execute(text("SELECT 1"))

        # 获取连接池状态
        pool_status = {
            "pool_size": engine.pool.size() if hasattr(engine.pool, 'size') else 'N/A',
            "checked_out": engine.pool.checkedout() if hasattr(engine.pool, 'checkedout') else 'N/A',
            "overflow": engine.pool.overflow() if hasattr(engine.pool, 'overflow') else 'N/A',
        }

        db.close()

        return {
            "status": "healthy",
            "database": "connected",
            "pool": pool_status
        }
    except Exception as e:
        logger.error(f"数据库健康检查失败：{str(e)}")
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }
