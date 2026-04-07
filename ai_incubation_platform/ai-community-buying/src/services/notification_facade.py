"""
通知服务 Facade - 统一通知服务接口

整合通知适配器和业务逻辑，提供统一的通知发送接口。
"""
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import logging

from adapters.notification.base import NotificationMessage, NotificationResult
from adapters.notification.registry import (
    get_default_adapter,
    get_adapter,
    NotificationAdapterRegistry
)

logger = logging.getLogger(__name__)


class NotificationServiceFacade:
    """
    通知服务外观类

    提供统一的通知发送接口，底层可切换不同的通知适配器。
    支持库存预警、团购进度、成团结果等业务通知。
    """

    def __init__(
        self,
        db_session: Optional[Session] = None,
        adapter_name: Optional[str] = None
    ):
        self.db = db_session
        self.adapter_name = adapter_name
        self._adapter = None

        # 库存预警阈值
        self.stock_alert_threshold = 10
        self.stock_critical_threshold = 5

        # 团购进度通知节点（百分比）
        self.progress_notify_points = [50, 80, 100]

    def _get_adapter(self):
        """获取通知适配器"""
        if self._adapter is None:
            if self.adapter_name:
                self._adapter = get_adapter(self.adapter_name)
            if self._adapter is None:
                self._adapter = get_default_adapter()
        return self._adapter

    def send_notification(
        self,
        user_id: str,
        type: str,
        title: str,
        content: str,
        related_id: Optional[str] = None,
        priority: str = "normal",
        data: Optional[Dict[str, Any]] = None
    ) -> Optional[NotificationResult]:
        """
        发送通知

        Args:
            user_id: 接收用户 ID
            type: 通知类型
            title: 通知标题
            content: 通知内容
            related_id: 关联 ID
            priority: 优先级
            data: 附加数据

        Returns:
            发送结果
        """
        adapter = self._get_adapter()
        if not adapter:
            logger.error("没有可用的通知适配器")
            return None

        message = NotificationMessage(
            user_id=user_id,
            type=type,
            title=title,
            content=content,
            related_id=related_id,
            priority=priority,
            data=data or {}
        )

        return adapter.send(message)

    def send_stock_alert(
        self,
        product_id: str,
        product_name: str,
        current_stock: int,
        admin_user_id: str = "admin"
    ) -> Optional[NotificationResult]:
        """
        发送库存预警通知

        Args:
            product_id: 商品 ID
            product_name: 商品名称
            current_stock: 当前库存
            admin_user_id: 管理员用户 ID

        Returns:
            发送结果
        """
        if current_stock <= 0:
            alert_level = "紧急"
            priority = "urgent"
            content = f"商品「{product_name}」已售罄，当前库存为 0，请立即补货！"
        elif current_stock <= self.stock_critical_threshold:
            alert_level = "严重"
            priority = "high"
            content = f"商品「{product_name}」库存仅剩 {current_stock} 件，已低于临界值，请尽快补货。"
        elif current_stock <= self.stock_alert_threshold:
            alert_level = "警告"
            priority = "normal"
            content = f"商品「{product_name}」库存仅剩 {current_stock} 件，低于预警阈值，请安排补货。"
        else:
            return None  # 不需要预警

        return self.send_notification(
            user_id=admin_user_id,
            type="stock_alert",
            title=f"📦 库存预警 ({alert_level}): {product_name}",
            content=content,
            related_id=product_id,
            priority=priority,
            data={
                "product_id": product_id,
                "product_name": product_name,
                "current_stock": current_stock,
                "alert_level": alert_level
            }
        )

    def send_group_progress_notification(
        self,
        group_id: str,
        group_name: str,
        current_size: int,
        target_size: int,
        member_user_ids: List[str]
    ) -> List[NotificationResult]:
        """
        发送团购进度通知

        Args:
            group_id: 团购 ID
            group_name: 团购名称
            current_size: 当前人数
            target_size: 目标人数
            member_user_ids: 成员用户 ID 列表

        Returns:
            发送结果列表
        """
        progress = int((current_size / target_size) * 100) if target_size > 0 else 0

        # 检查是否达到通知节点
        notify_point = None
        for point in self.progress_notify_points:
            if progress >= point and progress < point + 10:
                notify_point = point
                break

        if not notify_point:
            return []  # 不需要通知

        results = []
        remaining = target_size - current_size

        for user_id in member_user_ids:
            result = self.send_notification(
                user_id=user_id,
                type="group_progress",
                title=f"📈 团购进度：{notify_point}%",
                content=f"您参与的「{group_name}」已达到 {notify_point}%，还差 {remaining} 人即可成团！",
                related_id=group_id,
                priority="normal",
                data={
                    "group_id": group_id,
                    "group_name": group_name,
                    "current_size": current_size,
                    "target_size": target_size,
                    "progress": progress,
                    "notify_point": notify_point
                }
            )
            if result:
                results.append(result)

        return results

    def send_group_success_notification(
        self,
        group_id: str,
        group_name: str,
        member_user_ids: List[str]
    ) -> List[NotificationResult]:
        """
        发送团购成功通知

        Args:
            group_id: 团购 ID
            group_name: 团购名称
            member_user_ids: 成员用户 ID 列表

        Returns:
            发送结果列表
        """
        results = []

        for user_id in member_user_ids:
            result = self.send_notification(
                user_id=user_id,
                type="group_success",
                title="🎉 恭喜！团购成功",
                content=f"您参与的「{group_name}」团购已成功成团！订单已生成，请留意后续配送通知。",
                related_id=group_id,
                priority="normal",
                data={
                    "group_id": group_id,
                    "group_name": group_name,
                    "status": "success"
                }
            )
            if result:
                results.append(result)

        return results

    def send_group_failure_notification(
        self,
        group_id: str,
        group_name: str,
        member_user_ids: List[str],
        reason: str = "人数不足"
    ) -> List[NotificationResult]:
        """
        发送团购失败通知

        Args:
            group_id: 团购 ID
            group_name: 团购名称
            member_user_ids: 成员用户 ID 列表
            reason: 失败原因

        Returns:
            发送结果列表
        """
        results = []

        for user_id in member_user_ids:
            result = self.send_notification(
                user_id=user_id,
                type="group_failed",
                title="❌ 遗憾！团购失败",
                content=f"您参与的「{group_name}」团购因{reason}已失败，已为您解锁锁定的库存，感谢参与。",
                related_id=group_id,
                priority="normal",
                data={
                    "group_id": group_id,
                    "group_name": group_name,
                    "status": "failed",
                    "reason": reason
                }
            )
            if result:
                results.append(result)

        return results

    def get_user_notifications(
        self,
        user_id: str,
        unread_only: bool = False,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """获取用户通知列表"""
        adapter = self._get_adapter()
        if not adapter:
            return []

        return adapter.get_user_notifications(user_id, unread_only, limit)

    def mark_notification_as_read(
        self,
        user_id: str,
        message_id: str
    ) -> bool:
        """标记通知为已读"""
        adapter = self._get_adapter()
        if not adapter:
            return False
        return adapter.mark_as_read(user_id, message_id)

    def mark_all_as_read(self, user_id: str) -> int:
        """标记所有通知为已读"""
        adapter = self._get_adapter()
        if not adapter:
            return 0
        return adapter.mark_all_as_read(user_id)


# 全局服务实例（用于向后兼容）
_facade: Optional[NotificationServiceFacade] = None


def get_notification_facade(
    db_session: Optional[Session] = None,
    adapter_name: Optional[str] = None
) -> NotificationServiceFacade:
    """获取通知服务外观实例"""
    global _facade
    if _facade is None:
        _facade = NotificationServiceFacade(db_session, adapter_name)
    return _facade
