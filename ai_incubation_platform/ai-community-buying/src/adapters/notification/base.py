"""
通知适配器基类 - 定义统一的通知接口

所有通知适配器必须继承此基类，实现统一的通知发送接口。
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class NotificationConfig(BaseModel):
    """通知配置"""
    adapter_name: str = Field(..., description="适配器名称")
    enabled: bool = Field(default=True, description="是否启用")
    config: Dict[str, Any] = Field(default_factory=dict, description="适配器特定配置")


class NotificationMessage(BaseModel):
    """通知消息"""
    user_id: str = Field(..., description="接收用户 ID")
    type: str = Field(..., description="通知类型")
    title: str = Field(..., description="通知标题")
    content: str = Field(..., description="通知内容")
    related_id: Optional[str] = Field(default=None, description="关联 ID（商品 ID、团购 ID 等）")
    data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="附加数据")
    priority: str = Field(default="normal", description="优先级：low, normal, high, urgent")


class NotificationResult(BaseModel):
    """通知发送结果"""
    success: bool = Field(..., description="是否发送成功")
    message_id: Optional[str] = Field(default=None, description="消息 ID")
    error: Optional[str] = Field(default=None, description="错误信息")
    sent_at: datetime = Field(default_factory=datetime.now)


class NotificationAdapter(ABC):
    """
    通知适配器基类

    所有通知适配器必须继承此类，实现统一的通知发送接口。
    """

    def __init__(self, config: Optional[NotificationConfig] = None):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.enabled = config.enabled if config else True

    @abstractmethod
    def send(self, message: NotificationMessage) -> NotificationResult:
        """
        发送单条通知

        Args:
            message: 通知消息

        Returns:
            NotificationResult: 发送结果
        """
        pass

    @abstractmethod
    def send_batch(self, messages: List[NotificationMessage]) -> List[NotificationResult]:
        """
        批量发送通知

        Args:
            messages: 通知消息列表

        Returns:
            List[NotificationResult]: 每条消息的发送结果
        """
        pass

    @abstractmethod
    def get_user_notifications(
        self,
        user_id: str,
        unread_only: bool = False,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        获取用户通知列表

        Args:
            user_id: 用户 ID
            unread_only: 是否只获取未读
            limit: 数量限制

        Returns:
            通知列表
        """
        pass

    @abstractmethod
    def mark_as_read(self, user_id: str, message_id: str) -> bool:
        """
        标记通知为已读

        Args:
            user_id: 用户 ID
            message_id: 消息 ID

        Returns:
            是否成功
        """
        pass

    @abstractmethod
    def mark_all_as_read(self, user_id: str) -> int:
        """
        标记所有通知为已读

        Args:
            user_id: 用户 ID

        Returns:
            已标记的数量
        """
        pass

    def is_available(self) -> bool:
        """检查适配器是否可用"""
        return self.enabled

    def validate_config(self) -> bool:
        """验证配置是否有效"""
        return True

    def get_adapter_info(self) -> Dict[str, Any]:
        """获取适配器信息"""
        return {
            "name": self.__class__.__name__,
            "enabled": self.enabled,
            "config_valid": self.validate_config()
        }
