"""
通知服务：库存预警、团购进度、成团结果通知
"""
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models.entities import NotificationEntity, ProductEntity, GroupBuyEntity
from models.product import GroupBuyStatus

class NotificationService:
    """通知服务"""

    def __init__(self):
        # 库存预警阈值（可配置）
        self.stock_alert_threshold = 10
        # 团购进度通知节点（百分比）
        self.progress_notify_points = [50, 80, 100]
        # 已发送的进度通知缓存，避免重复发送
        self.sent_progress_notifications = set()

    def send_stock_alert(self, db: Session, product: ProductEntity) -> bool:
        """发送库存预警通知"""
        if product.stock > self.stock_alert_threshold:
            return False

        # 检查是否最近已经发送过预警（1小时内不重复发送）
        recent_alert = db.query(NotificationEntity).filter(
            NotificationEntity.type == "stock_alert",
            NotificationEntity.related_id == product.id,
            NotificationEntity.created_at > datetime.now() - timedelta(hours=1)
        ).first()

        if recent_alert:
            return False

        # 创建通知
        notification = NotificationEntity(
            user_id="admin",  # 发送给管理员，后续可配置接收人
            type="stock_alert",
            title=f"库存预警：{product.name}",
            content=f"商品「{product.name}」当前库存仅剩 {product.stock} 件，低于预警阈值 {self.stock_alert_threshold} 件，请及时补货。",
            related_id=product.id
        )
        db.add(notification)
        db.commit()

        return True

    def send_group_progress_notification(self, db: Session, group_buy: GroupBuyEntity) -> bool:
        """发送团购进度通知"""
        if group_buy.status != GroupBuyStatus.OPEN:
            return False

        progress = int((group_buy.current_size / group_buy.target_size) * 100)
        notify_key = f"group_progress_{group_buy.id}_{progress}"

        # 检查是否已经发送过该进度的通知
        if notify_key in self.sent_progress_notifications:
            return False

        # 检查是否达到通知节点
        notify_point = None
        for point in self.progress_notify_points:
            if progress >= point and progress < point + 10:
                notify_point = point
                break

        if not notify_point:
            return False

        # 创建通知给所有成员
        for member in group_buy.members:
            notification = NotificationEntity(
                user_id=member.user_id,
                type="group_progress",
                title=f"团购进度通知：{notify_point}%",
                content=f"您参与的团购已达到 {notify_point}%，还差 {group_buy.target_size - group_buy.current_size} 人即可成团！",
                related_id=group_buy.id
            )
            db.add(notification)

        db.commit()
        self.sent_progress_notifications.add(notify_key)
        return True

    def send_group_result_notification(self, db: Session, group_buy: GroupBuyEntity, success: bool) -> bool:
        """发送团购结果通知（成功/失败）"""
        if success:
            title = "🎉 恭喜！团购成功"
            content = f"您参与的「{group_buy.product.name}」团购已成功成团！订单已生成，请留意后续配送通知。"
            notify_type = "group_success"
        else:
            title = "❌ 遗憾！团购失败"
            content = f"您参与的「{group_buy.product.name}」团购因人数不足已失败，已为您解锁锁定的库存，感谢参与。"
            notify_type = "group_failed"

        # 通知所有成员
        for member in group_buy.members:
            notification = NotificationEntity(
                user_id=member.user_id,
                type=notify_type,
                title=title,
                content=content,
                related_id=group_buy.id
            )
            db.add(notification)

        db.commit()
        return True

    def get_user_notifications(self, db: Session, user_id: str, unread_only: bool = False, limit: int = 20) -> List[NotificationEntity]:
        """获取用户通知列表"""
        query = db.query(NotificationEntity).filter(NotificationEntity.user_id == user_id)
        if unread_only:
            query = query.filter(NotificationEntity.is_read == False)
        return query.order_by(NotificationEntity.created_at.desc()).limit(limit).all()

    def mark_notification_as_read(self, db: Session, notification_id: str, user_id: str) -> Optional[NotificationEntity]:
        """标记通知为已读"""
        notification = db.query(NotificationEntity).filter(
            NotificationEntity.id == notification_id,
            NotificationEntity.user_id == user_id
        ).first()

        if not notification:
            return None

        notification.is_read = True
        notification.read_at = datetime.now()
        db.commit()
        return notification

    def mark_all_as_read(self, db: Session, user_id: str) -> int:
        """标记所有通知为已读"""
        result = db.query(NotificationEntity).filter(
            NotificationEntity.user_id == user_id,
            NotificationEntity.is_read == False
        ).update({
            "is_read": True,
            "read_at": datetime.now()
        })
        db.commit()
        return result

    def check_and_send_stock_alerts(self, db: Session) -> int:
        """检查所有商品库存并发送预警"""
        products = db.query(ProductEntity).filter(
            ProductEntity.status == "active",
            ProductEntity.stock <= self.stock_alert_threshold
        ).all()

        alert_count = 0
        for product in products:
            if self.send_stock_alert(db, product):
                alert_count += 1

        return alert_count


# 全局服务实例
notification_service = NotificationService()
