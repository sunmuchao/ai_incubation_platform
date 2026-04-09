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


class BaseService:
    """
    服务基类

    提供统一的数据库会话管理，支持两种使用方式:
    1. 依赖注入（推荐，用于 API 层）
    2. 自管理会话（用于后台任务/定时任务）

    使用示例:
        # 方式 1: 依赖注入
        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            service = UserService(db)
            return service.get_all()

        # 方式 2: 自管理会话（定时任务）
        def daily_task():
            service = UserService()  # 不传 db
            result = service.get_all()
            service.close()  # 记得关闭
    """

    def __init__(self, db: Optional[Session] = None):
        """
        初始化服务

        Args:
            db: 数据库会话（可选）
                 - 如果提供，使用该会话（由调用者管理生命周期）
                 - 如果不提供，自动创建新会话（由本服务管理生命周期）
        """
        self._db = db
        self._own_session = db is None  # 是否拥有会话所有权
        self._closed = False

    def _get_db(self) -> Session:
        """
        获取数据库会话

        Returns:
            Session: 数据库会话
        """
        if self._db is None:
            self._db = SessionLocal()
            self._own_session = True
            logger.debug(f"{self.__class__.__name__}: Created new database session")
        return self._db

    def close(self) -> None:
        """
        关闭数据库会话

        仅在服务拥有会话所有权时关闭（即 __init__ 时未传入 db）
        """
        if self._closed:
            return

        if self._own_session and self._db:
            try:
                self._db.close()
                logger.debug(f"{self.__class__.__name__}: Database session closed")
            except Exception as e:
                logger.error(f"{self.__class__.__name__}: Failed to close session: {e}")
            finally:
                self._db = None
                self._own_session = False
                self._closed = True

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()


def managed_db_session(db: Optional[Session] = None) -> Session:
    """
    获取受管理的数据库会话

    用于服务类内部方法，当需要在方法内确保有会话时使用。

    Args:
        db: 当前会话（可能为 None）

    Returns:
        Session: 有效的数据库会话

    注意:
        此函数不会关闭会话，调用者需要负责关闭
    """
    if db is not None:
        return db
    return SessionLocal()


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
