"""
P9 新增数据模型：通知系统与分享机制

P9-002: 推送通知系统
- 站内通知持久化
- 通知类型分类
- 推送状态追踪

P9-003: 分享机制
- 分享记录追踪
- 邀请码管理
- 分享渠道分析
"""
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Text, ForeignKey, JSON, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from db.database import Base


# ============= P9-002: 推送通知系统模型 =============

class UserNotificationDB(Base):
    """用户站内通知"""
    __tablename__ = "user_notifications"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 通知类型
    notification_type = Column(String(50), nullable=False, index=True)
    # 通知类型列表:
    # - new_match: 新的匹配
    # - new_message: 新消息
    # - message_read: 消息已读
    # - profile_view: 有人查看了你的资料
    # - super_like: 有人超级喜欢你
    # - like_received: 有人喜欢了你
    # - system: 系统通知
    # - security_alert: 安全提醒
    # - membership: 会员相关
    # - relationship_update: 关系进展更新

    # 通知内容
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)

    # 通知状态
    is_read = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)

    # 关联数据
    related_user_id = Column(String(36), nullable=True)  # 相关用户 ID（如匹配对象）
    related_type = Column(String(50), nullable=True)  # 相关类型 (match, message, etc.)
    related_id = Column(String(36), nullable=True)  # 相关记录 ID

    # 推送状态
    push_sent = Column(Boolean, default=False)
    push_sent_at = Column(DateTime(timezone=True), nullable=True)
    push_channel = Column(String(20), nullable=True)  # wechat, apns, fcm, email, sms

    # 优先级
    priority = Column(String(20), default="normal")  # low, normal, high, urgent

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    read_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # 索引优化
    __table_args__ = (
        Index('idx_user_created', 'user_id', 'created_at'),
        Index('idx_type_user', 'notification_type', 'user_id'),
    )


class UserPushTokenDB(Base):
    """用户推送令牌（用于第三方推送服务）"""
    __tablename__ = "user_push_tokens"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 推送平台
    platform = Column(String(20), nullable=False)  # ios, android, web, wechat, email
    token = Column(String(500), nullable=False, index=True)

    # 设备信息
    device_id = Column(String(100), nullable=True)
    device_model = Column(String(100), nullable=True)
    app_version = Column(String(50), nullable=True)

    # 令牌状态
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    # 通知偏好
    enable_match_notification = Column(Boolean, default=True)
    enable_message_notification = Column(Boolean, default=True)
    enable_system_notification = Column(Boolean, default=True)
    enable_promotion_notification = Column(Boolean, default=False)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)


class NotificationTemplateDB(Base):
    """通知模板（用于系统化通知）"""
    __tablename__ = "notification_templates"

    id = Column(String(36), primary_key=True, index=True)

    # 模板标识
    template_key = Column(String(100), nullable=False, unique=True, index=True)
    template_name = Column(String(200), nullable=False)

    # 模板内容（支持变量替换）
    title_template = Column(String(200), nullable=False)
    content_template = Column(Text, nullable=False)

    # 通知类型
    notification_type = Column(String(50), nullable=False)

    # 推送渠道
    channels = Column(Text, default="")  # JSON 数组 ["in_app", "push", "email"]

    # 模板变量定义
    variables = Column(Text, default="")  # JSON 对象 {"user_name": "string", "match_count": "number"}

    # 状态
    is_active = Column(Boolean, default=True)
    language = Column(String(10), default="zh-CN")

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# ============= P9-003: 分享机制模型 =============

class ShareRecordDB(Base):
    """分享记录"""
    __tablename__ = "share_records"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 分享类型
    share_type = Column(String(50), nullable=False)
    # 分享类型列表:
    # - invite_friend: 邀请好友
    # - share_profile: 分享个人主页
    # - share_match: 分享匹配成功
    # - share_achievement: 分享成就
    # - share_poster: 分享海报

    # 分享渠道
    channel = Column(String(50), nullable=False)
    # 渠道列表:
    # - wechat_friend: 微信好友
    # - wechat_moments: 朋友圈
    # - qq: QQ
    # - qq_zone: QQ 空间
    # - weibo: 微博
    # - copy_link: 复制链接

    # 分享内容
    content_type = Column(String(50), nullable=True)  # profile, match, poster, link
    content_id = Column(String(36), nullable=True)  # 相关内容 ID
    share_url = Column(String(500), nullable=False)  # 分享链接
    share_title = Column(String(200), nullable=True)  # 分享标题
    share_description = Column(Text, nullable=True)  # 分享描述
    share_image_url = Column(String(500), nullable=True)  # 分享图片

    # 分享结果追踪
    view_count = Column(Integer, default=0)  # 被浏览次数
    click_count = Column(Integer, default=0)  # 被点击次数
    convert_count = Column(Integer, default=0)  # 转化次数（如注册）

    # 分享状态
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class InviteCodeDB(Base):
    """邀请码"""
    __tablename__ = "invite_codes"

    id = Column(String(36), primary_key=True, index=True)
    code = Column(String(50), nullable=False, unique=True, index=True)

    # 邀请人
    inviter_user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 邀请码类型
    code_type = Column(String(20), default="standard")
    # 类型列表:
    # - standard: 普通邀请码
    # - vip: VIP 邀请码（更高奖励）
    # - event: 活动邀请码
    # - partner: 合作伙伴邀请码

    # 使用限制
    max_uses = Column(Integer, default=10)  # 最大使用次数，-1 为无限制
    used_count = Column(Integer, default=0)

    # 奖励配置
    reward_type = Column(String(20), default="credits")  # credits, membership, coupon
    reward_amount = Column(Integer, default=10)  # 奖励数量
    reward_description = Column(String(200), nullable=True)

    # 有效期
    is_active = Column(Boolean, default=True)
    starts_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class InviteRewardDB(Base):
    """邀请奖励记录"""
    __tablename__ = "invite_rewards"

    id = Column(String(36), primary_key=True, index=True)

    # 邀请码
    invite_code = Column(String(50), ForeignKey("invite_codes.code"), nullable=False, index=True)
    inviter_user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 被邀请人
    invited_user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    invited_user_email = Column(String(255), nullable=True)

    # 邀请状态
    status = Column(String(20), default="pending")
    # 状态列表:
    # - pending: 待注册
    # - registered: 已注册
    # - verified: 已验证（完成实名认证）
    # - rewarded: 已发放奖励
    # - expired: 已过期

    # 奖励信息
    reward_type = Column(String(20), nullable=True)
    reward_amount = Column(Integer, nullable=True)
    rewarded_at = Column(DateTime(timezone=True), nullable=True)

    # 被邀请人质量评分（用于防作弊）
    quality_score = Column(Float, nullable=True)
    is_valid_invite = Column(Boolean, default=True)  # 是否为有效邀请

    # 时间戳
    invited_at = Column(DateTime(timezone=True), server_default=func.now())
    registered_at = Column(DateTime(timezone=True), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)


class SharePosterDB(Base):
    """分享海报模板"""
    __tablename__ = "share_posters"

    id = Column(String(36), primary_key=True, index=True)

    # 海报标识
    poster_key = Column(String(100), nullable=False, unique=True, index=True)
    poster_name = Column(String(200), nullable=False)

    # 海报类型
    poster_type = Column(String(50), nullable=False)
    # 类型列表:
    # - profile_card: 个人名片
    # - match_success: 匹配成功
    # - achievement: 成就分享
    # - invite: 邀请海报
    # - event: 活动海报

    # 海报配置
    background_url = Column(String(500), nullable=True)
    template_data = Column(Text, default="")  # JSON 配置

    # 状态
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)

    # 使用统计
    use_count = Column(Integer, default=0)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
