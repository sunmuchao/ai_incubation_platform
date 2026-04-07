"""
通知适配器注册中心 - 管理通知适配器的注册和获取

支持运行时切换适配器，支持多适配器并行。
"""
from typing import Any, Dict, List, Optional, Type
from adapters.notification.base import NotificationAdapter, NotificationConfig
import logging

logger = logging.getLogger(__name__)


class NotificationAdapterRegistry:
    """通知适配器注册中心"""

    def __init__(self):
        self._adapters: Dict[str, NotificationAdapter] = {}
        self._default_adapter: Optional[str] = None

    def register(self, name: str, adapter: NotificationAdapter, set_default: bool = False) -> None:
        """
        注册通知适配器

        Args:
            name: 适配器名称
            adapter: 适配器实例
            set_default: 是否设为默认适配器
        """
        self._adapters[name] = adapter
        if set_default or self._default_adapter is None:
            self._default_adapter = name
        logger.info(f"通知适配器注册成功：{name}")

    def get(self, name: str) -> Optional[NotificationAdapter]:
        """获取指定适配器"""
        return self._adapters.get(name)

    def get_default(self) -> Optional[NotificationAdapter]:
        """获取默认适配器"""
        if self._default_adapter:
            return self._adapters.get(self._default_adapter)
        return None

    def list_adapters(self) -> List[str]:
        """获取所有已注册的适配器名称"""
        return list(self._adapters.keys())

    def set_default(self, name: str) -> bool:
        """设置默认适配器"""
        if name in self._adapters:
            self._default_adapter = name
            logger.info(f"默认适配器已设置为：{name}")
            return True
        logger.warning(f"设置默认适配器失败：{name} 不存在")
        return False

    def send(
        self,
        message: Any,
        adapter_name: Optional[str] = None,
        use_all: bool = False
    ) -> Dict[str, Any]:
        """
        发送通知

        Args:
            message: 通知消息
            adapter_name: 指定适配器名称，为空则使用默认
            use_all: 是否使用所有启用的适配器

        Returns:
            发送结果
        """
        results = {}

        if use_all:
            # 使用所有启用的适配器
            for name, adapter in self._adapters.items():
                if adapter.is_available():
                    result = adapter.send(message)
                    results[name] = result
        else:
            # 使用指定或默认适配器
            adapter = self.get(adapter_name) if adapter_name else self.get_default()
            if adapter:
                result = adapter.send(message)
                results[adapter_name or self._default_adapter] = result
            else:
                logger.error("没有可用的通知适配器")

        return results

    def get_adapter_info(self) -> Dict[str, Any]:
        """获取所有适配器信息"""
        return {
            "default": self._default_adapter,
            "adapters": {
                name: adapter.get_adapter_info()
                for name, adapter in self._adapters.items()
            }
        }


# 全局注册中心
_registry = NotificationAdapterRegistry()


def get_adapter(name: Optional[str] = None) -> Optional[NotificationAdapter]:
    """获取通知适配器"""
    if name:
        return _registry.get(name)
    return _registry.get_default()


def register_adapter(
    name: str,
    adapter: NotificationAdapter,
    set_default: bool = False
) -> None:
    """注册通知适配器"""
    _registry.register(name, adapter, set_default)


def get_default_adapter() -> Optional[NotificationAdapter]:
    """获取默认通知适配器"""
    return _registry.get_default()


def get_registry() -> NotificationAdapterRegistry:
    """获取注册中心实例"""
    return _registry
