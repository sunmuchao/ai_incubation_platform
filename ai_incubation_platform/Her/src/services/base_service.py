"""
服务层基类

提供公共服务方法，减少重复代码。

统一数据库会话管理模式：
- 推荐方式：使用 db_session 上下文管理器
- 服务类方式：继承 BaseService，使用 self.db 属性
- 自动创建：设置 auto_create_session=True 时自动创建会话（使用后需调用 close()）

使用示例:
    # 方式 1：使用上下文管理器（推荐）
    with db_session() as db:
        service = UserService(db=db, model_class=UserDB)
        users = service.list_all()

    # 方式 2：自动创建会话（需手动关闭）
    service = UserService(auto_create_session=True, model_class=UserDB)
    users = service.list_all()
    service.close()

    # 方式 3：外部传入会话
    def my_api_endpoint(db: Session = Depends(get_db)):
        service = UserService(db=db)
        return service.list_all()
"""
from typing import Optional, TypeVar, Generic, Type, Any, List, Dict, Callable
from sqlalchemy.orm import Session, Query
from sqlalchemy import desc, asc
from utils.db_session_manager import db_session, db_session_readonly
from utils.logger import logger
from db.database import SessionLocal

T = TypeVar('T')


class BaseService(Generic[T]):
    """
    服务层基类

    提供公共服务方法：
    - 数据库会话管理（支持自动创建）
    - 日志记录
    - 通用 CRUD 操作

    会话管理模式：
    1. 外部传入（推荐）：MyService(db=session)
    2. 自动创建：MyService(auto_create_session=True)，使用后需调用 close()
    """

    def __init__(
        self,
        db: Optional[Session] = None,
        model_class: Optional[Type[T]] = None,
        auto_create_session: bool = False
    ):
        """
        初始化服务

        Args:
            db: 数据库会话，如果为 None 则需要设置 auto_create_session 或外部传入
            model_class: 模型类（用于通用 CRUD 方法）
            auto_create_session: 是否自动创建会话（使用后需调用 close()）
        """
        self._db = db
        self._model_class = model_class
        self._logger = logger
        self._auto_create_session = auto_create_session
        self._own_session = False

        # 如果启用自动创建且未传入会话，则创建新会话
        if auto_create_session and db is None:
            self._db = SessionLocal()
            self._own_session = True

    # ==================== 数据库会话管理 ====================

    @property
    def db(self) -> Session:
        """获取数据库会话"""
        if self._db is None:
            if self._auto_create_session:
                self._db = SessionLocal()
                self._own_session = True
            else:
                raise RuntimeError(
                    "数据库会话未设置。请通过以下方式之一提供会话：\n"
                    "1. 构造函数传入: MyService(db=session)\n"
                    "2. 使用上下文管理器: with db_session() as db: service = MyService(db=db)\n"
                    "3. 自动创建: MyService(auto_create_session=True)"
                )
        return self._db

    @db.setter
    def db(self, value: Session):
        """设置数据库会话"""
        self._db = value
        self._own_session = False

    def close(self):
        """关闭数据库会话（仅在自动创建时有效）"""
        if self._own_session and self._db is not None:
            try:
                self._db.commit()
                self._db.close()
                self._logger.debug("Database session closed")
            except Exception as e:
                self._logger.error(f"Failed to close database session: {e}")
            finally:
                self._db = None
                self._own_session = False

    @property
    def logger(self):
        """获取日志器"""
        return self._logger

    # ==================== 通用 CRUD 方法 ====================

    def get_by_id(self, record_id: Any, model_class: Type[T] = None) -> Optional[T]:
        """
        通过 ID 获取单条记录

        Args:
            record_id: 记录 ID
            model_class: 模型类（可选，默认使用 self._model_class）

        Returns:
            记录对象或 None

        使用示例:
            user = service.get_by_id(user_id)
            # 等价于: db.query(UserDB).filter(UserDB.id == user_id).first()
        """
        model = model_class or self._model_class
        if model is None:
            raise ValueError("model_class is required")
        return self.db.query(model).filter(model.id == record_id).first()

    def get_by_field(self, field_name: str, value: Any, model_class: Type[T] = None) -> Optional[T]:
        """
        通过单个字段获取单条记录

        Args:
            field_name: 字段名
            value: 字段值
            model_class: 模型类（可选）

        Returns:
            记录对象或 None

        使用示例:
            user = service.get_by_field("email", "test@example.com")
        """
        model = model_class or self._model_class
        if model is None:
            raise ValueError("model_class is required")
        return self.db.query(model).filter(getattr(model, field_name) == value).first()

    def list_by_field(self, field_name: str, value: Any, model_class: Type[T] = None,
                      order_by: str = None, desc_order: bool = False,
                      limit: int = None, offset: int = None) -> List[T]:
        """
        通过单个字段获取多条记录

        Args:
            field_name: 字段名
            value: 字段值
            model_class: 模型类（可选）
            order_by: 排序字段
            desc_order: 是否降序
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            记录列表

        使用示例:
            messages = service.list_by_field("conversation_id", conv_id, order_by="created_at", desc_order=True)
        """
        model = model_class or self._model_class
        if model is None:
            raise ValueError("model_class is required")

        query = self.db.query(model).filter(getattr(model, field_name) == value)

        if order_by:
            order_field = getattr(model, order_by)
            query = query.order_by(desc(order_field) if desc_order else asc(order_field))

        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        return query.all()

    def list_all(self, model_class: Type[T] = None, order_by: str = None,
                 desc_order: bool = False, limit: int = None, offset: int = None,
                 **filters) -> List[T]:
        """
        获取所有记录（支持过滤）

        Args:
            model_class: 模型类（可选）
            order_by: 排序字段
            desc_order: 是否降序
            limit: 返回数量限制
            offset: 偏移量
            **filters: 过滤条件

        Returns:
            记录列表

        使用示例:
            users = service.list_all(is_active=True, order_by="created_at", desc_order=True, limit=10)
        """
        model = model_class or self._model_class
        if model is None:
            raise ValueError("model_class is required")

        query = self.db.query(model)

        # 应用过滤条件
        for field, value in filters.items():
            if hasattr(model, field):
                query = query.filter(getattr(model, field) == value)

        # 排序
        if order_by:
            order_field = getattr(model, order_by)
            query = query.order_by(desc(order_field) if desc_order else asc(order_field))

        # 分页
        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        return query.all()

    def count(self, model_class: Type[T] = None, **filters) -> int:
        """
        统计记录数量

        Args:
            model_class: 模型类（可选）
            **filters: 过滤条件

        Returns:
            记录数量

        使用示例:
            count = service.count(is_active=True)
        """
        model = model_class or self._model_class
        if model is None:
            raise ValueError("model_class is required")

        query = self.db.query(model)
        for field, value in filters.items():
            if hasattr(model, field):
                query = query.filter(getattr(model, field) == value)

        return query.count()

    def exists(self, record_id: Any, model_class: Type[T] = None) -> bool:
        """
        检查记录是否存在

        Args:
            record_id: 记录 ID
            model_class: 模型类（可选）

        Returns:
            是否存在
        """
        return self.get_by_id(record_id, model_class) is not None

    def create(self, model_class: Type[T] = None, **kwargs) -> T:
        """
        创建新记录

        Args:
            model_class: 模型类（可选）
            **kwargs: 字段值

        Returns:
            新创建的记录

        使用示例:
            user = service.create(name="张三", email="test@example.com")
        """
        model = model_class or self._model_class
        if model is None:
            raise ValueError("model_class is required")

        record = model(**kwargs)
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def update(self, record: T, **kwargs) -> T:
        """
        更新记录

        Args:
            record: 要更新的记录
            **kwargs: 要更新的字段

        Returns:
            更新后的记录

        使用示例:
            user = service.update(user, name="李四", age=30)
        """
        for key, value in kwargs.items():
            if hasattr(record, key):
                setattr(record, key, value)
        self.db.commit()
        self.db.refresh(record)
        return record

    def delete(self, record: T) -> bool:
        """
        删除记录

        Args:
            record: 要删除的记录

        Returns:
            是否成功
        """
        try:
            self.db.delete(record)
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            self.log_error(f"Failed to delete record: {e}")
            return False

    def delete_by_id(self, record_id: Any, model_class: Type[T] = None) -> bool:
        """
        通过 ID 删除记录

        Args:
            record_id: 记录 ID
            model_class: 模型类（可选）

        Returns:
            是否成功
        """
        record = self.get_by_id(record_id, model_class)
        if record is None:
            return False
        return self.delete(record)

    # ==================== 日志方法 ====================

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