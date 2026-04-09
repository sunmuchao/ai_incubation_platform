"""
服务层基类

提供公共服务方法，减少重复代码。
"""
from typing import Optional, TypeVar, Generic, Type, Any
from sqlalchemy.orm import Session
from db.database import SessionLocal
from utils.logger import logger

T = TypeVar('T')


class BaseService(Generic[T]):
    """
    服务层基类

    提供公共服务方法：
    - 数据库会话管理
    - 日志记录
    - 错误处理

    使用示例:
        class UserService(BaseService[UserDB]):
            def __init__(self, db: Session = None):
                super().__init__(db)
                self.model = UserDB

            def get_by_id(self, user_id: str) -> Optional[UserDB]:
                return self.db.query(UserDB).filter(UserDB.id == user_id).first()
    """

    def __init__(self, db: Optional[Session] = None, model_class: Optional[Type[T]] = None):
        """
        初始化服务

        Args:
            db: 数据库会话，如果为 None 则自动创建
            model_class: 模型类（可选）
        """
        self._db = db
        self._model_class = model_class
        self._logger = logger

    @property
    def db(self) -> Session:
        """获取数据库会话"""
        if self._db is None:
            self._db = SessionLocal()
        return self._db

    @db.setter
    def db(self, value: Session):
        """设置数据库会话"""
        self._db = value

    @property
    def logger(self):
        """获取日志器"""
        return self._logger

    def _get_db(self) -> Session:
        """
        获取数据库会话（兼容旧代码）

        Returns:
            Session: 数据库会话
        """
        if self._db is None:
            self._db = SessionLocal()
        return self._db

    def _close_db(self):
        """关闭数据库会话（如果是由本服务创建的）"""
        if self._db is not None:
            self._db.close()
            self._db = None

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self._close_db()

    def log_info(self, message: str, **kwargs):
        """记录 INFO 日志"""
        self.logger.info(message, **kwargs)

    def log_error(self, message: str, **kwargs):
        """记录 ERROR 日志"""
        self.logger.error(message, **kwargs)

    def log_debug(self, message: str, **kwargs):
        """记录 DEBUG 日志"""
        self.logger.debug(message, **kwargs)


class SingletonService:
    """
    单例服务基类

    用于创建全局唯一的服务实例。

    使用示例:
        class MyService(SingletonService):
            _instance = None

            def __init__(self):
                if not self._initialized:
                    # 初始化代码
                    self._initialized = True

            @classmethod
            def get_instance(cls):
                if cls._instance is None:
                    cls._instance = cls()
                return cls._instance
    """

    _instance: Optional['SingletonService'] = None
    _initialized: bool = False

    @classmethod
    def get_instance(cls) -> 'SingletonService':
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls):
        """重置单例实例（用于测试）"""
        cls._instance = None
        cls._initialized = False