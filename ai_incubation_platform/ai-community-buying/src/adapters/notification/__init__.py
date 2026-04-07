"""
通知适配器层 - 可插拔的通知系统

支持多种通知渠道的统一抽象，便于运行时切换和扩展。
"""

from adapters.notification.base import NotificationAdapter, NotificationConfig
from adapters.notification.memory import InMemoryNotificationAdapter
from adapters.notification.database import DatabaseNotificationAdapter
from adapters.notification.console import ConsoleNotificationAdapter
from adapters.notification.registry import NotificationAdapterRegistry, get_adapter, register_adapter

__all__ = [
    # 基类
    "NotificationAdapter",
    "NotificationConfig",
    # 具体实现
    "InMemoryNotificationAdapter",
    "DatabaseNotificationAdapter",
    "ConsoleNotificationAdapter",
    # 注册中心
    "NotificationAdapterRegistry",
    "get_adapter",
    "register_adapter",
]
