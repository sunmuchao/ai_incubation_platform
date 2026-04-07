"""
P9 多平台/小程序集成 - SQLAlchemy 数据模型实体

定义多平台集成相关的数据库表结构：
- platform_accounts: 平台账号绑定
- platform_orders: 平台订单映射
- platform_notifications: 平台通知记录
- platform_configs: 平台配置
"""

from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from datetime import datetime

from config.database import Base


class PlatformAccountEntity(Base):
    """
    平台账号绑定表

    用于关联平台用户 (微信/支付宝) 与系统内部用户
    支持 UnionID 机制实现多平台账号统一
    """
    __tablename__ = 'platform_accounts'

    id = Column(String(64), primary_key=True)
    user_id = Column(String(64), nullable=False, index=True)
    platform = Column(String(32), nullable=False, index=True)  # wechat, alipay, douyin, etc.
    platform_user_id = Column(String(128), nullable=False)  # 平台用户 ID (openid/user_id)
    union_id = Column(String(128), index=True)  # UnionID (同一开发者账号下的多端用户标识)
    access_token = Column(String(512))  # 平台访问令牌
    refresh_token = Column(String(512))  # 刷新令牌
    token_expires_at = Column(DateTime)  # 令牌过期时间
    session_key = Column(String(256))  # 微信小程序 session_key
    avatar_url = Column(String(512))  # 用户头像
    nickname = Column(String(128))  # 用户昵称
    gender = Column(Integer)  # 性别 (0-未知，1-男，2-女)
    phone = Column(String(32))  # 手机号 (需用户授权获取)
    is_primary = Column(Boolean, default=False)  # 是否主要账号
    is_active = Column(Boolean, default=True)  # 是否激活
    last_sync_at = Column(DateTime)  # 最后同步时间
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    # user = relationship("UserEntity", back_populates="platform_accounts")  # 注释掉，因为测试环境没有 UserEntity

    __table_args__ = (
        UniqueConstraint('platform', 'platform_user_id', name='uq_platform_user'),
        Index('idx_user_platform', 'user_id', 'platform'),
        Index('idx_union_id', 'union_id'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'platform': self.platform,
            'platform_user_id': self.platform_user_id,
            'union_id': self.union_id,
            'avatar_url': self.avatar_url,
            'nickname': self.nickname,
            'gender': self.gender,
            'phone': self.phone,
            'is_primary': self.is_primary,
            'is_active': self.is_active,
            'last_sync_at': self.last_sync_at.isoformat() if self.last_sync_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class PlatformOrderEntity(Base):
    """
    平台订单映射表

    用于关联系统内部订单与平台订单
    支持跨平台订单统一管理
    """
    __tablename__ = 'platform_orders'

    id = Column(String(64), primary_key=True)
    global_order_id = Column(String(64), nullable=False, index=True)
    platform = Column(String(32), nullable=False, index=True)  # wechat, alipay, douyin, etc.
    platform_order_id = Column(String(128), nullable=False, unique=True)  # 平台订单 ID
    platform_order_no = Column(String(128))  # 平台订单号 (展示用)
    transaction_id = Column(String(128))  # 平台支付流水号
    order_status = Column(String(32), default='pending')  # 订单状态 (同步自平台)
    payment_status = Column(String(32), default='unpaid')  # 支付状态 (unpaid/paid/refunding/refunded)
    payment_amount = Column(Integer)  # 支付金额 (分)
    payment_time = Column(DateTime)  # 支付时间
    refund_amount = Column(Integer)  # 退款金额 (分)
    refund_time = Column(DateTime)  # 退款时间
    refund_reason = Column(Text)  # 退款原因
    platform_metadata = Column(Text)  # 平台订单原始数据 (JSON)
    sync_status = Column(String(32), default='pending')  # 同步状态 (pending/synced/failed)
    sync_error = Column(Text)  # 同步错误信息
    last_sync_at = Column(DateTime)  # 最后同步时间
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_global_platform', 'global_order_id', 'platform'),
        Index('idx_platform_status', 'platform', 'order_status'),
        Index('idx_payment_status', 'payment_status'),
    )

    def to_dict(self):
        import json
        return {
            'id': self.id,
            'global_order_id': self.global_order_id,
            'platform': self.platform,
            'platform_order_id': self.platform_order_id,
            'platform_order_no': self.platform_order_no,
            'transaction_id': self.transaction_id,
            'order_status': self.order_status,
            'payment_status': self.payment_status,
            'payment_amount': self.payment_amount,
            'payment_time': self.payment_time.isoformat() if self.payment_time else None,
            'refund_amount': self.refund_amount,
            'refund_time': self.refund_time.isoformat() if self.refund_time else None,
            'refund_reason': self.refund_reason,
            'platform_metadata': json.loads(self.platform_metadata) if self.platform_metadata else None,
            'sync_status': self.sync_status,
            'last_sync_at': self.last_sync_at.isoformat() if self.last_sync_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class PlatformNotificationEntity(Base):
    """
    平台通知记录表

    用于记录发送到各平台的通知消息
    支持订阅消息、模板消息等
    """
    __tablename__ = 'platform_notifications'

    id = Column(String(64), primary_key=True)
    user_id = Column(String(64), nullable=False, index=True)
    platform = Column(String(32), nullable=False, index=True)  # wechat, alipay, etc.
    notification_type = Column(String(32), nullable=False)  # subscribe_msg, template_msg, etc.
    template_id = Column(String(128), nullable=False)  # 模板 ID
    template_name = Column(String(128))  # 模板名称
    recipient = Column(String(128), nullable=False)  # 接收者 (openid/user_id)
    title = Column(String(256))  # 通知标题
    content = Column(Text)  # 通知内容 (JSON 格式)
    page_path = Column(String(512))  # 跳转页面路径
    send_status = Column(String(32), default='pending')  # 发送状态 (pending/sent/failed)
    send_error = Column(Text)  # 发送错误信息
    send_time = Column(DateTime)  # 发送时间
    read_status = Column(Boolean, default=False)  # 是否已读
    read_time = Column(DateTime)  # 阅读时间
    retry_count = Column(Integer, default=0)  # 重试次数
    platform_response = Column(Text)  # 平台响应数据 (JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_user_platform_type', 'user_id', 'platform', 'notification_type'),
        Index('idx_send_status', 'send_status'),
    )

    def to_dict(self):
        import json
        return {
            'id': self.id,
            'user_id': self.user_id,
            'platform': self.platform,
            'notification_type': self.notification_type,
            'template_id': self.template_id,
            'template_name': self.template_name,
            'recipient': self.recipient,
            'title': self.title,
            'content': json.loads(self.content) if self.content else None,
            'page_path': self.page_path,
            'send_status': self.send_status,
            'send_error': self.send_error,
            'send_time': self.send_time.isoformat() if self.send_time else None,
            'read_status': self.read_status,
            'read_time': self.read_time.isoformat() if self.read_time else None,
            'retry_count': self.retry_count,
            'platform_response': json.loads(self.platform_response) if self.platform_response else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class PlatformConfigEntity(Base):
    """
    平台配置表

    存储各平台的配置信息 (AppID, Secret 等)
    """
    __tablename__ = 'platform_configs'

    id = Column(String(64), primary_key=True)
    platform = Column(String(32), nullable=False, unique=True, index=True)  # wechat, alipay, etc.
    platform_name = Column(String(64))  # 平台名称 (展示用)
    app_id = Column(String(128), nullable=False)  # 平台 AppID
    app_secret = Column(String(256), nullable=False)  # 平台 AppSecret (加密存储)
    encoding_aes_key = Column(String(256))  # 消息加密密钥 (微信)
    mch_id = Column(String(64))  # 商户 ID (支付用)
    mch_key = Column(String(256))  # 商户密钥 (加密存储)
    cert_path = Column(String(512))  # 证书路径
    key_path = Column(String(512))  # 私钥路径
    api_version = Column(String(32))  # API 版本
    api_base_url = Column(String(256))  # API 基础 URL
    webhook_url = Column(String(512))  # 回调 URL
    webhook_token = Column(String(128))  # 回调验证 token
    is_enabled = Column(Boolean, default=True)  # 是否启用
    config_json = Column(Text)  # 额外配置 (JSON)
    remarks = Column(Text)  # 备注
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        import json
        # 注意：敏感信息不返回
        return {
            'id': self.id,
            'platform': self.platform,
            'platform_name': self.platform_name,
            'app_id': self.app_id,
            'mch_id': self.mch_id,
            'api_version': self.api_version,
            'api_base_url': self.api_base_url,
            'webhook_url': self.webhook_url,
            'is_enabled': self.is_enabled,
            'config_json': json.loads(self.config_json) if self.config_json else None,
            'remarks': self.remarks,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class PlatformSyncLogEntity(Base):
    """
    平台同步日志表

    记录与各平台的数据同步操作日志
    """
    __tablename__ = 'platform_sync_logs'

    id = Column(String(64), primary_key=True)
    sync_type = Column(String(32), nullable=False, index=True)  # order, account, notification, etc.
    platform = Column(String(32), nullable=False, index=True)
    platform_resource_id = Column(String(128))  # 平台资源 ID
    internal_resource_id = Column(String(64))  # 内部资源 ID
    sync_direction = Column(String(16), nullable=False)  # inbound (平台->内部), outbound (内部->平台)
    sync_action = Column(String(32), nullable=False)  # create, update, delete, query
    sync_status = Column(String(32), default='success')  # success, failed
    request_data = Column(Text)  # 请求数据 (JSON)
    response_data = Column(Text)  # 响应数据 (JSON)
    error_message = Column(Text)  # 错误信息
    duration_ms = Column(Integer)  # 同步耗时 (毫秒)
    operator_id = Column(String(64))  # 操作人 ID
    operator_type = Column(String(32))  # user, system, cron
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index('idx_sync_type_platform', 'sync_type', 'platform'),
        Index('idx_resource_ids', 'platform_resource_id', 'internal_resource_id'),
    )

    def to_dict(self):
        import json
        return {
            'id': self.id,
            'sync_type': self.sync_type,
            'platform': self.platform,
            'platform_resource_id': self.platform_resource_id,
            'internal_resource_id': self.internal_resource_id,
            'sync_direction': self.sync_direction,
            'sync_action': self.sync_action,
            'sync_status': self.sync_status,
            'request_data': json.loads(self.request_data) if self.request_data else None,
            'response_data': json.loads(self.response_data) if self.response_data else None,
            'error_message': self.error_message,
            'duration_ms': self.duration_ms,
            'operator_id': self.operator_id,
            'operator_type': self.operator_type,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
