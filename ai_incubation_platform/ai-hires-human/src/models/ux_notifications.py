"""
用户通知偏好设置数据模型 - v1.22 用户体验优化

提供通知偏好设置功能的数据持久化
"""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, Boolean, Time
from sqlalchemy.ext.asyncio import AsyncSession
from database import Base


class UserNotificationPreferencesDB(Base):
    """用户通知偏好设置数据库模型"""
    __tablename__ = "user_notification_preferences"

    id = Column(String(36), primary_key=True, nullable=False)
    user_id = Column(String(36), nullable=False, index=True, unique=True, comment="用户 ID")

    # ========== 推送通知开关 ==========
    push_task_notifications = Column(Boolean, default=True, comment="推送：任务通知")
    push_message_notifications = Column(Boolean, default=True, comment="推送：消息通知")
    push_payment_notifications = Column(Boolean, default=True, comment="推送：支付通知")
    push_system_notifications = Column(Boolean, default=True, comment="推送：系统通知")
    push_marketing_notifications = Column(Boolean, default=False, comment="推送：营销通知")

    # ========== 邮件通知开关 ==========
    email_task_notifications = Column(Boolean, default=True, comment="邮件：任务通知")
    email_message_notifications = Column(Boolean, default=False, comment="邮件：消息通知")
    email_payment_notifications = Column(Boolean, default=True, comment="邮件：支付通知")
    email_system_notifications = Column(Boolean, default=True, comment="邮件：系统通知")
    email_marketing_notifications = Column(Boolean, default=False, comment="邮件：营销通知")

    # ========== 短信通知开关 ==========
    sms_payment_notifications = Column(Boolean, default=True, comment="短信：支付通知")
    sms_urgent_notifications = Column(Boolean, default=True, comment="短信：紧急通知")
    sms_marketing_notifications = Column(Boolean, default=False, comment="短信：营销通知")

    # ========== 免打扰时段 ==========
    dnd_enabled = Column(Boolean, default=False, comment="是否启用免打扰")
    dnd_start_time = Column(String(8), default='22:00:00', comment="免打扰开始时间 HH:MM:SS")
    dnd_end_time = Column(String(8), default='08:00:00', comment="免打扰结束时间 HH:MM:SS")

    # ========== 通知聚合设置 ==========
    digest_enabled = Column(Boolean, default=True, comment="是否启用通知摘要")
    digest_frequency = Column(String(20), default='daily', comment="摘要频率：hourly/daily/weekly")

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    def __repr__(self):
        return f"<UserNotificationPreferencesDB(id={self.id}, user_id={self.user_id})>"

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "push_notifications": {
                "task": self.push_task_notifications,
                "message": self.push_message_notifications,
                "payment": self.push_payment_notifications,
                "system": self.push_system_notifications,
                "marketing": self.push_marketing_notifications,
            },
            "email_notifications": {
                "task": self.email_task_notifications,
                "message": self.email_message_notifications,
                "payment": self.email_payment_notifications,
                "system": self.email_system_notifications,
                "marketing": self.email_marketing_notifications,
            },
            "sms_notifications": {
                "payment": self.sms_payment_notifications,
                "urgent": self.sms_urgent_notifications,
                "marketing": self.sms_marketing_notifications,
            },
            "do_not_disturb": {
                "enabled": self.dnd_enabled,
                "start_time": self.dnd_start_time,
                "end_time": self.dnd_end_time,
            },
            "digest": {
                "enabled": self.digest_enabled,
                "frequency": self.digest_frequency,
            },
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def get_default_preferences(cls):
        """获取默认偏好设置"""
        return {
            "push_notifications": {
                "task": True,
                "message": True,
                "payment": True,
                "system": True,
                "marketing": False,
            },
            "email_notifications": {
                "task": True,
                "message": False,
                "payment": True,
                "system": True,
                "marketing": False,
            },
            "sms_notifications": {
                "payment": True,
                "urgent": True,
                "marketing": False,
            },
            "do_not_disturb": {
                "enabled": False,
                "start_time": "22:00:00",
                "end_time": "08:00:00",
            },
            "digest": {
                "enabled": True,
                "frequency": "daily",
            },
        }


class UserNotificationDB(Base):
    """用户通知记录数据库模型"""
    __tablename__ = "user_notifications"

    id = Column(String(36), primary_key=True, nullable=False)
    user_id = Column(String(36), nullable=False, index=True, comment="用户 ID")

    # 通知类型
    notification_type = Column(String(50), nullable=False, comment="通知类型：task/message/payment/system/marketing")
    notification_subtype = Column(String(50), nullable=True, comment="通知子类型")

    # 通知内容
    title = Column(String(200), nullable=False, comment="通知标题")
    content = Column(String(1000), nullable=False, comment="通知内容")

    # 通知渠道
    channel = Column(String(20), nullable=False, comment="通知渠道：push/email/sms/in_app")

    # 通知状态
    is_read = Column(Boolean, default=False, comment="是否已读")
    is_sent = Column(Boolean, default=False, comment="是否已发送")
    send_status = Column(String(20), nullable=True, comment="发送状态：pending/sent/failed")

    # 关联数据
    related_entity_type = Column(String(50), nullable=True, comment="关联实体类型：task/payment/message")
    related_entity_id = Column(String(36), nullable=True, comment="关联实体 ID")

    # 动作
    action_url = Column(String(500), nullable=True, comment="点击跳转 URL")
    action_payload = Column(String(1000), nullable=True, comment="动作参数 JSON")

    # 时间戳
    scheduled_at = Column(DateTime, nullable=True, comment="计划发送时间")
    sent_at = Column(DateTime, nullable=True, comment="实际发送时间")
    read_at = Column(DateTime, nullable=True, comment="阅读时间")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    def __repr__(self):
        return f"<UserNotificationDB(id={self.id}, user_id={self.user_id}, type={self.notification_type})>"

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "type": self.notification_type,
            "subtype": self.notification_subtype,
            "title": self.title,
            "content": self.content,
            "channel": self.channel,
            "is_read": self.is_read,
            "is_sent": self.is_sent,
            "send_status": self.send_status,
            "related_entity": {
                "type": self.related_entity_type,
                "id": self.related_entity_id,
            } if self.related_entity_type else None,
            "action": {
                "url": self.action_url,
                "payload": self.action_payload,
            } if self.action_url else None,
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
