"""
数据库会话管理工具

提供统一的数据库会话管理机制，避免 SessionLocal 滥用导致的连接泄露问题。

使用示例:
    # 方式 1: 使用上下文管理器（推荐）
    with db_session() as db:
        user = db.query(UserDB).filter_by(id=user_id).first()

    # 方式 2: 在服务类中使用
    class MyService:
        def __init__(self, db: Optional[Session] = None):
            self._db = db
            self._own_session = db is None

        def _get_db(self) -> Session:
            return managed_db_session(self._db)

        def close(self):
            cleanup_db_session(self._db, self._own_session)
"""
from contextlib import contextmanager
from typing import Optional, Generator
from sqlalchemy.orm import Session
from db.database import SessionLocal
from utils.logger import logger


@contextmanager
def db_session() -> Generator[Session, None, None]:
    """
    数据库会话上下文管理器

    用法:
        with db_session() as db:
            # 使用 db 进行操作
            db.query(...).all()
        # 自动 commit/rollback/close

    特点:
    - 自动提交事务
    - 异常时自动回滚
    - 自动关闭会话（避免连接泄露）
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
        logger.debug("Database session committed")
    except Exception as e:
        db.rollback()
        logger.error(f"Database session rolled back: {e}")
        raise
    finally:
        db.close()
        logger.debug("Database session closed")


@contextmanager
def db_session_readonly() -> Generator[Session, None, None]:
    """
    只读数据库会话上下文管理器

    用法:
        with db_session_readonly() as db:
            # 只读查询
            users = db.query(UserDB).all()
        # 不 commit，直接 close

    特点:
    - 不提交事务（只读操作不需要）
    - 异常时自动回滚
    - 自动关闭会话
    """
    db = SessionLocal()
    try:
        yield db
        # 只读操作，不需要 commit
    except Exception as e:
        db.rollback()
        logger.error(f"Database session rolled back: {e}")
        raise
    finally:
        db.close()


# ==================== 会话管理工具函数 ====================

@contextmanager
def optional_db_session(db: Optional[Session] = None):
    """
    可选的数据库会话上下文管理器

    如果提供了外部会话，则使用它；否则创建新会话。

    用法:
        def my_method(self, db: Optional[Session] = None):
            with optional_db_session(db) as session:
                # 使用 session 进行操作
                session.query(...).all()
            # 如果是新创建的会话，自动 commit/close

    Args:
        db: 可选的外部数据库会话
    """
    if db is not None:
        # 使用外部会话，不需要管理生命周期
        yield db
    else:
        # 创建新会话，自动管理生命周期
        with db_session() as session:
            yield session


def cleanup_db_session(db: Optional[Session], own_session: bool) -> None:
    """
    清理数据库会话

    Args:
        db: 数据库会话
        own_session: 是否拥有会话所有权
    """
    if own_session and db is not None:
        try:
            db.close()
        except Exception as e:
            logger.error(f"Failed to close database session: {e}")


# ==================== 异步版本 ====================

@contextmanager
def async_db_session_context():
    """
    异步上下文管理器：获取数据库会话

    用法:
        async with async_db_session_context() as db:
            # 使用 db 进行操作

    注意：SQLAlchemy 同步会话在异步函数中使用时，
    确保操作不会阻塞事件循环
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        db.close()


def with_async_db_session(func):
    """
    装饰器：异步函数自动注入数据库会话

    用法:
        @with_async_db_session
        async def some_async_method(self, db: Session, ...):
            ...
    """
    from functools import wraps

    @wraps(func)
    async def wrapper(*args, **kwargs):
        db = SessionLocal()
        try:
            kwargs['db'] = db
            result = await func(*args, **kwargs)
            db.commit()
            return result
        except Exception as e:
            db.rollback()
            logger.error(f"Database session error in {func.__name__}: {e}")
            raise
        finally:
            db.close()

    return wrapper


# 装饰器：自动管理会话
def with_db_session(func):
    """
    装饰器：为函数自动创建和关闭数据库会话

    用法:
        @with_db_session
        def my_function(db: Session, user_id: str):
            return db.query(UserDB).filter_by(id=user_id).first()

    注意:
        被装饰的函数第一个参数必须是 db: Session
    """
    from functools import wraps

    @wraps(func)
    def wrapper(*args, **kwargs):
        with db_session() as db:
            # 将 db 作为第一个参数传入
            if args:
                return func(db, *args[1:], **kwargs)
            else:
                return func(db, **kwargs)

    return wrapper
