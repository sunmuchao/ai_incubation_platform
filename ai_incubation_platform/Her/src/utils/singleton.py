"""
单例模式统一实现

提供两种实现方式：
1. @singleton 装饰器 - 用于类
2. SingletonMeta 元类 - 用于需要继承的场景

使用示例:
    # 方式 1: 装饰器（推荐）
    @singleton
    class MyService:
        def __init__(self):
            self.data = []

    # 方式 2: 元类（需要继承时）
    class MyService(metaclass=SingletonMeta):
        def __init__(self):
            self.data = []

    # 获取实例
    service = MyService()  # 每次调用返回同一实例
    service = MyService.get_instance()  # 显式获取

    # 重置实例（用于测试）
    MyService.reset_instance()
"""
from typing import Optional, TypeVar, Type, Any
import threading

T = TypeVar('T')


class SingletonMeta(type):
    """
    单例元类

    通过元类实现单例模式，适用于需要继承的场景。
    线程安全，支持 reset_instance() 方法用于测试。

    示例:
        class CacheManager(metaclass=SingletonMeta):
            def __init__(self):
                self._initialized = False

            def initialize(self):
                if self._initialized:
                    return
                # 初始化逻辑
                self._initialized = True

        # 使用
        cache = CacheManager()
        cache.initialize()

        # 测试时重置
        CacheManager.reset_instance()
    """

    _instances: dict = {}
    _lock: threading.Lock = threading.Lock()

    def __call__(cls, *args, **kwargs) -> Any:
        with cls._lock:
            if cls not in cls._instances:
                cls._instances[cls] = super().__call__(*args, **kwargs)
            return cls._instances[cls]

    def get_instance(cls) -> Any:
        """获取单例实例"""
        return cls()

    def reset_instance(cls) -> None:
        """重置单例实例（用于测试）"""
        with cls._lock:
            if cls in cls._instances:
                cls._instances[cls] = None
                del cls._instances[cls]


def singleton(cls: Type[T]) -> Type[T]:
    """
    单例装饰器

    通过装饰器实现单例模式，使用更简洁。
    线程安全，支持 get_instance() 和 reset_instance() 方法。
    **重要**: __init__ 只在首次创建时调用一次。

    示例:
        @singleton
        class MyRegistry:
            def __init__(self):
                self._items = {}

            def register(self, name, item):
                self._items[name] = item

        # 使用
        registry = MyRegistry()  # 每次返回同一实例，__init__ 只调用一次
        registry = MyRegistry.get_instance()  # 显式获取

        # 测试时重置
        MyRegistry.reset_instance()

    Args:
        cls: 要装饰的类

    Returns:
        装饰后的类（具有单例行为）
    """
    instances: dict = {}
    lock = threading.Lock()

    def get_instance() -> T:
        """获取单例实例"""
        with lock:
            if cls not in instances:
                instance = cls.__new__(cls)
                # 标记已初始化，防止 __init__ 再次执行
                instance._singleton_initialized = True
                if hasattr(instance, '__init__'):
                    instance.__init__()
                instances[cls] = instance
            return instances[cls]

    def reset_instance() -> None:
        """重置单例实例（用于测试）"""
        with lock:
            if cls in instances:
                del instances[cls]

    # 为类添加方法
    cls.get_instance = staticmethod(get_instance)
    cls.reset_instance = staticmethod(reset_instance)

    # 重写 __new__ 方法，使其总是返回同一实例
    original_new = cls.__new__

    def singleton_new(new_cls, *args, **kwargs) -> T:
        with lock:
            if cls not in instances:
                if original_new is object.__new__:
                    instance = original_new(new_cls)
                else:
                    instance = original_new(new_cls, *args, **kwargs)
                # 标记已初始化
                instance._singleton_initialized = False
                instances[cls] = instance
            return instances[cls]

    cls.__new__ = singleton_new

    # 重写 __init__ 方法，防止多次初始化
    original_init = cls.__init__ if hasattr(cls, '__init__') else None

    def singleton_init(self, *args, **kwargs):
        if hasattr(self, '_singleton_initialized') and self._singleton_initialized:
            return  # 已初始化，跳过
        self._singleton_initialized = True
        if original_init:
            original_init(self, *args, **kwargs)

    cls.__init__ = singleton_init

    return cls


# 模块级别的单例助手函数
def get_singleton_instance(cls: Type[T]) -> T:
    """
    获取任意类的单例实例

    如果类有 get_instance 方法，调用它；否则创建并缓存实例。

    Args:
        cls: 类类型

    Returns:
        单例实例
    """
    if hasattr(cls, 'get_instance'):
        return cls.get_instance()
    return cls()