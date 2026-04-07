"""
P9-002: 推送通知服务

提供通知的创建、发送、管理等能力。
支持多种推送渠道：站内通知、微信推送、邮件、短信等。
"""
import json
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

from models.p9_models import UserNotificationDB, UserPushTokenDB, NotificationTemplateDB, ShareRecordDB, InviteCodeDB, InviteRewardDB, SharePosterDB
from db.models import UserDB
from utils.logger import logger


class NotificationService:
    """用户通知服务"""

    # 通知类型常量
    TYPE_NEW_MATCH = "new_match"
    TYPE_NEW_MESSAGE = "new_message"
    TYPE_MESSAGE_READ = "message_read"
    TYPE_PROFILE_VIEW = "profile_view"
    TYPE_SUPER_LIKE = "super_like"
    TYPE_LIKE_RECEIVED = "like_received"
    TYPE_SYSTEM = "system"
    TYPE_SECURITY_ALERT = "security_alert"
    TYPE_MEMBERSHIP = "membership"
    TYPE_RELATIONSHIP_UPDATE = "relationship_update"

    # 优先级常量
    PRIORITY_LOW = "low"
    PRIORITY_NORMAL = "normal"
    PRIORITY_HIGH = "high"
    PRIORITY_URGENT = "urgent"

    def __init__(self, db: Session):
        self.db = db

    def create_notification(
        self,
        user_id: str,
        notification_type: str,
        title: str,
        content: str,
        related_user_id: Optional[str] = None,
        related_type: Optional[str] = None,
        related_id: Optional[str] = None,
        priority: str = PRIORITY_NORMAL,
        expires_hours: Optional[int] = None
    ) -> UserNotificationDB:
        """创建站内通知"""
        notification = UserNotificationDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            content=content,
            related_user_id=related_user_id,
            related_type=related_type,
            related_id=related_id,
            priority=priority,
            expires_at=datetime.now() + timedelta(hours=expires_hours) if expires_hours else None
        )
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)

        logger.info(f"Notification created: type={notification_type}, user_id={user_id}, id={notification.id}")
        return notification

    def get_unread_count(self, user_id: str) -> int:
        """获取用户未读通知数量"""
        return self.db.query(UserNotificationDB).filter(
            and_(
                UserNotificationDB.user_id == user_id,
                UserNotificationDB.is_read == False,
                UserNotificationDB.is_deleted == False
            )
        ).count()

    def get_notifications(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
        notification_type: Optional[str] = None,
        unread_only: bool = False
    ) -> List[UserNotificationDB]:
        """获取用户通知列表"""
        query = self.db.query(UserNotificationDB).filter(
            and_(
                UserNotificationDB.user_id == user_id,
                UserNotificationDB.is_deleted == False
            )
        )

        if unread_only:
            query = query.filter(UserNotificationDB.is_read == False)

        if notification_type:
            query = query.filter(UserNotificationDB.notification_type == notification_type)

        return query.order_by(desc(UserNotificationDB.created_at)).offset(offset).limit(limit).all()

    def mark_as_read(self, notification_id: str, user_id: str) -> bool:
        """标记通知为已读"""
        notification = self.db.query(UserNotificationDB).filter(
            and_(
                UserNotificationDB.id == notification_id,
                UserNotificationDB.user_id == user_id
            )
        ).first()

        if not notification:
            return False

        notification.is_read = True
        notification.read_at = datetime.now()
        self.db.commit()

        logger.info(f"Notification marked as read: id={notification_id}, user_id={user_id}")
        return True

    def mark_all_as_read(self, user_id: str) -> int:
        """标记所有通知为已读"""
        updated = self.db.query(UserNotificationDB).filter(
            and_(
                UserNotificationDB.user_id == user_id,
                UserNotificationDB.is_read == False,
                UserNotificationDB.is_deleted == False
            )
        ).update({
            UserNotificationDB.is_read: True,
            UserNotificationDB.read_at: datetime.now()
        })
        self.db.commit()
        return updated

    def delete_notification(self, notification_id: str, user_id: str) -> bool:
        """删除通知（软删除）"""
        notification = self.db.query(UserNotificationDB).filter(
            and_(
                UserNotificationDB.id == notification_id,
                UserNotificationDB.user_id == user_id
            )
        ).first()

        if not notification:
            return False

        notification.is_deleted = True
        self.db.commit()

        logger.info(f"Notification deleted: id={notification_id}, user_id={user_id}")
        return True

    def send_match_notification(self, user_id: str, match_user_id: str, match_user_name: str, compatibility_score: float):
        """发送新匹配通知"""
        title = "新的匹配成功！"
        content = f"你和 {match_user_name} 匹配成功了，匹配度 {int(compatibility_score * 100)}%。现在可以开始聊天了！"

        notification = self.create_notification(
            user_id=user_id,
            notification_type=self.TYPE_NEW_MATCH,
            title=title,
            content=content,
            related_user_id=match_user_id,
            related_type="match",
            priority=self.PRIORITY_HIGH
        )

        # 同时发送推送通知
        self._send_push_notification(user_id, title, content, {"type": "new_match", "match_user_id": match_user_id})

        return notification

    def send_message_notification(self, user_id: str, sender_name: str, message_preview: str):
        """发送新消息通知"""
        title = "新消息"
        content = f"{sender_name}: {message_preview[:50]}..."

        notification = self.create_notification(
            user_id=user_id,
            notification_type=self.TYPE_NEW_MESSAGE,
            title=title,
            content=content,
            priority=self.PRIORITY_HIGH
        )

        # 同时发送推送通知
        self._send_push_notification(user_id, title, content, {"type": "new_message"})

        return notification

    def send_super_like_notification(self, user_id: str, sender_name: str):
        """发送超级喜欢通知"""
        title = "有人超级喜欢你！"
        content = f"{sender_name} 对你使用了超级喜欢，你们匹配的几率大大增加！"

        notification = self.create_notification(
            user_id=user_id,
            notification_type=self.TYPE_SUPER_LIKE,
            title=title,
            content=content,
            related_user_id=None,  # 暂时不透露是谁
            priority=self.PRIORITY_URGENT
        )

        # 超级喜欢需要发送推送通知
        self._send_push_notification(user_id, title, content, {"type": "super_like"})

        return notification

    def send_system_notification(self, user_id: str, title: str, content: str, priority: str = PRIORITY_NORMAL):
        """发送系统通知"""
        notification = self.create_notification(
            user_id=user_id,
            notification_type=self.TYPE_SYSTEM,
            title=title,
            content=content,
            priority=priority
        )

        # 系统通知根据优先级决定是否推送
        if priority in [self.PRIORITY_HIGH, self.PRIORITY_URGENT]:
            self._send_push_notification(user_id, title, content, {"type": "system"})

        return notification

    def send_security_alert(self, user_id: str, alert_content: str):
        """发送安全提醒"""
        title = "安全提醒"

        notification = self.create_notification(
            user_id=user_id,
            notification_type=self.TYPE_SECURITY_ALERT,
            title=title,
            content=alert_content,
            priority=self.PRIORITY_URGENT
        )

        # 安全提醒必须发送推送
        self._send_push_notification(user_id, title, alert_content, {"type": "security_alert"})

        return notification

    def register_push_token(
        self,
        user_id: str,
        platform: str,
        token: str,
        device_id: Optional[str] = None,
        device_model: Optional[str] = None,
        app_version: Optional[str] = None
    ) -> UserPushTokenDB:
        """注册推送令牌"""
        # 检查是否已存在相同的 token
        existing = self.db.query(UserPushTokenDB).filter(
            and_(
                UserPushTokenDB.user_id == user_id,
                UserPushTokenDB.token == token
            )
        ).first()

        if existing:
            existing.is_active = True
            existing.last_used_at = datetime.now()
            self.db.commit()
            self.db.refresh(existing)
            return existing

        push_token = UserPushTokenDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            platform=platform,
            token=token,
            device_id=device_id,
            device_model=device_model,
            app_version=app_version
        )
        self.db.add(push_token)
        self.db.commit()
        self.db.refresh(push_token)

        logger.info(f"Push token registered: user_id={user_id}, platform={platform}")
        return push_token

    def unregister_push_token(self, user_id: str, token: str) -> bool:
        """注销推送令牌"""
        push_token = self.db.query(UserPushTokenDB).filter(
            and_(
                UserPushTokenDB.user_id == user_id,
                UserPushTokenDB.token == token
            )
        ).first()

        if not push_token:
            return False

        push_token.is_active = False
        self.db.commit()

        logger.info(f"Push token unregistered: user_id={user_id}")
        return True

    def update_notification_preferences(
        self,
        user_id: str,
        enable_match: Optional[bool] = None,
        enable_message: Optional[bool] = None,
        enable_system: Optional[bool] = None,
        enable_promotion: Optional[bool] = None
    ) -> bool:
        """更新用户通知偏好"""
        push_tokens = self.db.query(UserPushTokenDB).filter(
            UserPushTokenDB.user_id == user_id
        ).all()

        # 如果没有推送令牌，创建一个默认的
        if not push_tokens:
            push_token = UserPushTokenDB(
                id=str(uuid.uuid4()),
                user_id=user_id,
                platform="web",
                token="default_web_token"
            )
            self.db.add(push_token)
            self.db.commit()
            push_tokens = [push_token]
            logger.info(f"Created default push token for user: {user_id}")

        for push_token in push_tokens:
            if enable_match is not None:
                push_token.enable_match_notification = enable_match
            if enable_message is not None:
                push_token.enable_message_notification = enable_message
            if enable_system is not None:
                push_token.enable_system_notification = enable_system
            if enable_promotion is not None:
                push_token.enable_promotion_notification = enable_promotion

        self.db.commit()
        logger.info(f"Notification preferences updated: user_id={user_id}")
        return True

    def get_notification_preferences(self, user_id: str) -> Dict[str, bool]:
        """获取用户通知偏好"""
        push_token = self.db.query(UserPushTokenDB).filter(
            UserPushTokenDB.user_id == user_id,
            UserPushTokenDB.is_active == True
        ).first()

        if not push_token:
            return {
                "enable_match_notification": True,
                "enable_message_notification": True,
                "enable_system_notification": True,
                "enable_promotion_notification": False
            }

        return {
            "enable_match_notification": push_token.enable_match_notification,
            "enable_message_notification": push_token.enable_message_notification,
            "enable_system_notification": push_token.enable_system_notification,
            "enable_promotion_notification": push_token.enable_promotion_notification
        }

    def _send_push_notification(self, user_id: str, title: str, content: str, extra_data: Dict[str, Any] = None):
        """内部方法：发送推送通知"""
        push_tokens = self.db.query(UserPushTokenDB).filter(
            and_(
                UserPushTokenDB.user_id == user_id,
                UserPushTokenDB.is_active == True
            )
        ).all()

        if not push_tokens:
            logger.debug(f"No active push tokens for user: {user_id}")
            return

        # 更新通知的推送状态
        notification = self.db.query(UserNotificationDB).filter(
            UserNotificationDB.user_id == user_id
        ).order_by(desc(UserNotificationDB.created_at)).first()

        if notification:
            notification.push_sent = True
            notification.push_sent_at = datetime.now()

        # TODO: 集成第三方推送服务（如极光推送、个推等）
        for push_token in push_tokens:
            logger.info(f"Push notification sent: user_id={user_id}, platform={push_token.platform}, title={title}")
            # 这里应该调用第三方推送服务的 API
            # 例如：jiguang.push(...), getui.push(...) 等

        self.db.commit()

    def cleanup_expired(self) -> int:
        """清理过期通知"""
        deleted = self.db.query(UserNotificationDB).filter(
            and_(
                UserNotificationDB.expires_at != None,
                UserNotificationDB.expires_at < datetime.now()
            )
        ).delete()
        self.db.commit()

        logger.info(f"Cleaned up {deleted} expired notifications")
        return deleted


class ShareService:
    """分享服务"""

    # 分享类型常量
    TYPE_INVITE_FRIEND = "invite_friend"
    TYPE_SHARE_PROFILE = "share_profile"
    TYPE_SHARE_MATCH = "share_match"
    TYPE_SHARE_ACHIEVEMENT = "share_achievement"
    TYPE_SHARE_POSTER = "share_poster"

    # 分享渠道常量
    CHANNEL_WECHAT_FRIEND = "wechat_friend"
    CHANNEL_WECHAT_MOMENTS = "wechat_moments"
    CHANNEL_QQ = "qq"
    CHANNEL_QQ_ZONE = "qq_zone"
    CHANNEL_WEIBO = "weibo"
    CHANNEL_COPY_LINK = "copy_link"

    def __init__(self, db: Session):
        self.db = db

    def create_invite_code(
        self,
        user_id: str,
        code_type: str = "standard",
        max_uses: int = 10,
        reward_type: str = "credits",
        reward_amount: int = 10,
        expires_days: Optional[int] = None
    ) -> InviteCodeDB:
        """创建邀请码"""
        import random
        import string

        # 生成唯一邀请码
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

        # 检查是否重复
        while self.db.query(InviteCodeDB).filter(InviteCodeDB.code == code).first():
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

        invite_code = InviteCodeDB(
            id=str(uuid.uuid4()),
            code=code,
            inviter_user_id=user_id,
            code_type=code_type,
            max_uses=max_uses,
            reward_type=reward_type,
            reward_amount=reward_amount,
            expires_at=datetime.now() + timedelta(days=expires_days) if expires_days else None
        )
        self.db.add(invite_code)
        self.db.commit()
        self.db.refresh(invite_code)

        logger.info(f"Invite code created: code={code}, user_id={user_id}")
        return invite_code

    def get_user_invite_codes(self, user_id: str) -> List[InviteCodeDB]:
        """获取用户的邀请码列表"""
        return self.db.query(InviteCodeDB).filter(
            and_(
                InviteCodeDB.inviter_user_id == user_id,
                InviteCodeDB.is_active == True
            )
        ).all()

    def validate_invite_code(self, code: str) -> Optional[InviteCodeDB]:
        """验证邀请码是否有效"""
        invite_code = self.db.query(InviteCodeDB).filter(
            and_(
                InviteCodeDB.code == code,
                InviteCodeDB.is_active == True,
                InviteCodeDB.max_uses > InviteCodeDB.used_count
            )
        ).first()

        if not invite_code:
            return None

        # 检查是否过期
        if invite_code.expires_at and invite_code.expires_at < datetime.now():
            return None

        return invite_code

    def use_invite_code(self, code: str, invited_user_id: str, invited_user_email: str) -> Optional[InviteRewardDB]:
        """使用邀请码"""
        invite_code = self.validate_invite_code(code)
        if not invite_code:
            return None

        # 增加使用次数
        invite_code.used_count += 1

        # 创建奖励记录
        reward = InviteRewardDB(
            id=str(uuid.uuid4()),
            invite_code=code,
            inviter_user_id=invite_code.inviter_user_id,
            invited_user_id=invited_user_id,
            invited_user_email=invited_user_email,
            status="registered",
            reward_type=invite_code.reward_type,
            reward_amount=invite_code.reward_amount
        )
        self.db.add(reward)
        self.db.commit()
        self.db.refresh(reward)

        logger.info(f"Invite code used: code={code}, inviter={invite_code.inviter_user_id}, invited={invited_user_id}")
        return reward

    def create_share_record(
        self,
        user_id: str,
        share_type: str,
        channel: str,
        share_url: str,
        content_type: Optional[str] = None,
        content_id: Optional[str] = None,
        share_title: Optional[str] = None,
        share_description: Optional[str] = None,
        share_image_url: Optional[str] = None
    ) -> ShareRecordDB:
        """创建分享记录"""
        share_record = ShareRecordDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            share_type=share_type,
            channel=channel,
            share_url=share_url,
            content_type=content_type,
            content_id=content_id,
            share_title=share_title,
            share_description=share_description,
            share_image_url=share_image_url,
            expires_at=datetime.now() + timedelta(days=7)  # 默认 7 天过期
        )
        self.db.add(share_record)
        self.db.commit()
        self.db.refresh(share_record)

        logger.info(f"Share record created: user_id={user_id}, type={share_type}, channel={channel}")
        return share_record

    def track_share_view(self, share_record_id: str):
        """追踪分享被查看"""
        share_record = self.db.query(ShareRecordDB).filter(
            ShareRecordDB.id == share_record_id
        ).first()

        if share_record:
            share_record.view_count += 1
            self.db.commit()

    def track_share_click(self, share_record_id: str):
        """追踪分享被点击"""
        share_record = self.db.query(ShareRecordDB).filter(
            ShareRecordDB.id == share_record_id
        ).first()

        if share_record:
            share_record.click_count += 1
            self.db.commit()

    def track_share_convert(self, share_record_id: str):
        """追踪分享转化"""
        share_record = self.db.query(ShareRecordDB).filter(
            ShareRecordDB.id == share_record_id
        ).first()

        if share_record:
            share_record.convert_count += 1
            self.db.commit()

    def get_share_stats(self, user_id: str) -> Dict[str, Any]:
        """获取用户分享统计"""
        records = self.db.query(ShareRecordDB).filter(
            ShareRecordDB.user_id == user_id
        ).all()

        total_views = sum(r.view_count for r in records)
        total_clicks = sum(r.click_count for r in records)
        total_converts = sum(r.convert_count for r in records)

        # 按渠道统计
        channel_stats = {}
        for record in records:
            if record.channel not in channel_stats:
                channel_stats[record.channel] = {"views": 0, "clicks": 0, "converts": 0}
            channel_stats[record.channel]["views"] += record.view_count
            channel_stats[record.channel]["clicks"] += record.click_count
            channel_stats[record.channel]["converts"] += record.convert_count

        return {
            "total_records": len(records),
            "total_views": total_views,
            "total_clicks": total_clicks,
            "total_converts": total_converts,
            "channel_stats": channel_stats
        }

    def get_invite_stats(self, user_id: str) -> Dict[str, Any]:
        """获取用户邀请统计"""
        invite_codes = self.db.query(InviteCodeDB).filter(
            InviteCodeDB.inviter_user_id == user_id
        ).all()

        total_invites = sum(ic.used_count for ic in invite_codes)
        total_rewards = self.db.query(InviteRewardDB).filter(
            and_(
                InviteRewardDB.inviter_user_id == user_id,
                InviteRewardDB.rewarded_at != None
            )
        ).count()

        return {
            "total_codes": len(invite_codes),
            "total_invites": total_invites,
            "total_rewards": total_rewards,
            "invite_codes": [{"code": ic.code, "used_count": ic.used_count, "max_uses": ic.max_uses} for ic in invite_codes]
        }


# 常量定义 - 邀请奖励状态
InviteRewardDB.STATUS_PENDING = "pending"
InviteRewardDB.STATUS_REGISTERED = "registered"
InviteRewardDB.STATUS_VERIFIED = "verified"
InviteRewardDB.STATUS_REWARDED = "rewarded"
InviteRewardDB.STATUS_EXPIRED = "expired"
