"""
第三方通知服务集成

功能:
- 推送通知（极光推送）
- 短信通知（阿里云短信）
- 语音电话通知（阿里云语音服务）
- 邮件通知（SMTP）

使用场景:
- 紧急联系人通知
- 系统通知
- 安全警报
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
import json
import uuid

from db.models import UserDB, TrustedContactDB
from utils.logger import logger
from services.base_service import BaseService


class NotificationService(BaseService):
    """第三方通知服务"""

    # 通知渠道
    CHANNEL_PUSH = "push"
    CHANNEL_SMS = "sms"
    CHANNEL_VOICE_CALL = "voice_call"
    CHANNEL_EMAIL = "email"

    # 通知类型
    TYPE_SAFETY_ALERT = "safety_alert"
    TYPE_EMERGENCY_REQUEST = "emergency_request"
    TYPE_SYSTEM_NOTIFICATION = "system_notification"
    TYPE_MATCH_NOTIFICATION = "match_notification"
    TYPE_MESSAGE_NOTIFICATION = "message_notification"

    def __init__(self, db: Session):
        super().__init__(db)
        self._push_client = None
        self._sms_client = None
        self._voice_client = None

    def _get_push_client(self):
        """获取推送客户端"""
        if self._push_client is None:
            from integration.jpush_client import get_jpush_client
            self._push_client = get_jpush_client()
        return self._push_client

    def _get_sms_client(self):
        """获取短信客户端"""
        from integration.aliyun_sms_client import get_sms_client
        return get_sms_client()

    def send_notification(
        self,
        user_id: str,
        notification_type: str,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        channels: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """发送通知"""
        if channels is None:
            channels = [self.CHANNEL_PUSH]

        notification_id = str(uuid.uuid4())
        self._create_notification_record(
            notification_id=notification_id,
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            data=data
        )

        delivery_results = []
        for channel in channels:
            result = self._send_via_channel(
                user_id=user_id,
                channel=channel,
                title=title,
                message=message,
                notification_id=notification_id
            )
            delivery_results.append(result)

        all_success = all(r.get("success", False) for r in delivery_results)

        return {
            "success": all_success,
            "notification_id": notification_id,
            "delivery_results": delivery_results
        }

    def _create_notification_record(
        self,
        notification_id: str,
        user_id: str,
        notification_type: str,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]]
    ):
        """创建通知记录"""
        from sqlalchemy import text

        self.db.execute(text("""
            INSERT INTO notifications (
                id, user_id, notification_type, title, message, data, is_read, sent_at
            ) VALUES (
                :id, :user_id, :type, :title, :message, :data, FALSE, :sent_at
            )
        """), {
            "id": notification_id,
            "user_id": user_id,
            "type": notification_type,
            "title": title,
            "message": message,
            "data": json.dumps(data) if data else None,
            "sent_at": datetime.now().isoformat()
        })
        self.db.commit()

    def _send_via_channel(
        self,
        user_id: str,
        channel: str,
        title: str,
        message: str,
        notification_id: str
    ) -> Dict[str, Any]:
        """通过指定渠道发送通知"""
        try:
            if channel == self.CHANNEL_PUSH:
                return self._send_push(user_id, title, message, notification_id)
            elif channel == self.CHANNEL_SMS:
                return self._send_sms(user_id, message, notification_id)
            elif channel == self.CHANNEL_VOICE_CALL:
                return self._send_voice_call(user_id, message, notification_id)
            elif channel == self.CHANNEL_EMAIL:
                return self._send_email(user_id, title, message, notification_id)
            else:
                return {"success": False, "error": f"未知渠道：{channel}"}

        except Exception as e:
            logger.error(f"Failed to send via {channel}: {e}")
            return {"success": False, "error": str(e)}

    def _send_push(
        self,
        user_id: str,
        title: str,
        message: str,
        notification_id: str,
        extras: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """发送推送通知"""
        client = self._get_push_client()

        if client is None:
            logger.warning("Push client not available, using mock mode")
            self._record_delivery(notification_id, user_id, self.CHANNEL_PUSH, "sent", "mock")
            return {"success": True, "channel": self.CHANNEL_PUSH, "mock": True}

        try:
            push_tokens = self._get_user_push_tokens(user_id)

            if not push_tokens:
                return {"success": False, "error": "用户没有推送令牌", "channel": self.CHANNEL_PUSH}

            result = client.push(
                target=push_tokens,
                title=title,
                content=message,
                extras=extras or {"notification_id": notification_id}
            )

            if result.get("success"):
                self._record_delivery(notification_id, user_id, self.CHANNEL_PUSH, "sent")
                return {"success": True, "channel": self.CHANNEL_PUSH}
            else:
                self._record_delivery(
                    notification_id, user_id, self.CHANNEL_PUSH, "failed",
                    result.get("error", "未知错误")
                )
                return {"success": False, "error": result.get("error"), "channel": self.CHANNEL_PUSH}

        except Exception as e:
            self._record_delivery(notification_id, user_id, self.CHANNEL_PUSH, "failed", str(e))
            return {"success": False, "error": str(e), "channel": self.CHANNEL_PUSH}

    def _send_sms(
        self,
        user_id: str,
        message: str,
        notification_id: str,
        template_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """发送短信通知"""
        user = self.db.query(UserDB).filter(UserDB.id == user_id).first()
        if not user or not user.phone:
            return {"success": False, "error": "用户未绑定手机号", "channel": self.CHANNEL_SMS}

        client = self._get_sms_client()
        if client is None:
            logger.warning("SMS client not available, using mock mode")
            self._record_delivery(notification_id, user_id, self.CHANNEL_SMS, "sent", "mock")
            return {"success": True, "channel": self.CHANNEL_SMS, "mock": True}

        result = client.send_notification(user.phone, message, template_code)

        if result.get("success"):
            self._record_delivery(notification_id, user_id, self.CHANNEL_SMS, "sent")
            return {"success": True, "channel": self.CHANNEL_SMS}
        else:
            self._record_delivery(
                notification_id, user_id, self.CHANNEL_SMS, "failed",
                result.get("error", "未知错误")
            )
            return {"success": False, "error": result.get("error"), "channel": self.CHANNEL_SMS}

    def _send_voice_call(
        self,
        user_id: str,
        message: str,
        notification_id: str
    ) -> Dict[str, Any]:
        """发送语音电话通知（用于紧急情况）"""
        user = self.db.query(UserDB).filter(UserDB.id == user_id).first()
        if not user or not user.phone:
            return {"success": False, "error": "用户未绑定手机号", "channel": self.CHANNEL_VOICE_CALL}

        logger.warning("Voice call service not yet implemented, using mock mode")
        self._record_delivery(notification_id, user_id, self.CHANNEL_VOICE_CALL, "sent", "mock")
        return {"success": True, "channel": self.CHANNEL_VOICE_CALL, "mock": True}

    def _send_email(
        self,
        user_id: str,
        title: str,
        message: str,
        notification_id: str
    ) -> Dict[str, Any]:
        """发送邮件通知"""
        user = self.db.query(UserDB).filter(UserDB.id == user_id).first()
        if not user or not user.email:
            return {"success": False, "error": "用户没有邮箱", "channel": self.CHANNEL_EMAIL}

        logger.warning("Email service not yet implemented, using mock mode")
        self._record_delivery(notification_id, user_id, self.CHANNEL_EMAIL, "sent", "mock")
        return {"success": True, "channel": self.CHANNEL_EMAIL, "mock": True}

    def _get_user_push_tokens(self, user_id: str) -> List[str]:
        """获取用户的推送令牌列表"""
        from sqlalchemy import text

        result = self.db.execute(text("""
            SELECT push_token FROM push_tokens
            WHERE user_id = :user_id AND is_active = TRUE
        """), {"user_id": user_id})

        return [row[0] for row in result.fetchall()]

    def _record_delivery(
        self,
        notification_id: str,
        user_id: str,
        channel: str,
        status: str,
        response: Optional[str] = None
    ):
        """记录通知发送状态"""
        from sqlalchemy import text

        self.db.execute(text("""
            INSERT INTO notification_delivery_records (
                id, notification_id, user_id, delivery_channel, delivery_status, channel_response, sent_at
            ) VALUES (
                :id, :notification_id, :user_id, :channel, :status, :response, :sent_at
            )
        """), {
            "id": str(uuid.uuid4()),
            "notification_id": notification_id,
            "user_id": user_id,
            "channel": channel,
            "status": status,
            "response": response,
            "sent_at": datetime.now().isoformat()
        })
        self.db.commit()

    def notify_emergency_contacts(
        self,
        user_id: str,
        alert_type: str,
        description: str,
        location_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """通知紧急联系人"""
        contacts = self.db.query(TrustedContactDB).filter(
            TrustedContactDB.user_id == user_id,
            TrustedContactDB.can_receive_emergency == True
        ).all()

        if not contacts:
            return {"success": False, "error": "用户没有设置紧急联系人"}

        title = f"紧急求助 - {alert_type}"
        message = f"您的朋友触发了紧急求助：{description}"
        if location_url:
            message += f"\n位置：{location_url}"

        results = []
        contacts_notified = 0

        for contact in contacts:
            contact_result = self._notify_contact(
                contact_name=contact.name,
                contact_phone=contact.phone,
                title=title,
                message=message
            )
            results.append(contact_result)

            if contact_result.get("success"):
                contacts_notified += 1

        return {
            "success": contacts_notified > 0,
            "contacts_notified": contacts_notified,
            "results": results
        }

    def _notify_contact(
        self,
        contact_name: str,
        contact_phone: str,
        title: str,
        message: str
    ) -> Dict[str, Any]:
        """通知单个紧急联系人"""
        sms_result = self._send_sms_to_contact(contact_phone, message)

        return {
            "contact_name": contact_name,
            "contact_phone": contact_phone,
            "sms_success": sms_result.get("success", False)
        }

    def _send_sms_to_contact(self, phone: str, message: str) -> Dict[str, Any]:
        """向联系人发送短信"""
        client = self._get_sms_client()

        if client is None:
            logger.warning(f"[MOCK SMS] To {phone}: {message}")
            return {"success": True, "mock": True}

        return client.send_notification(phone, message)


def get_notification_service(db: Session) -> NotificationService:
    """获取通知服务实例"""
    return NotificationService(db)


# ============= 分享服务 =============

class ShareService(BaseService):
    """分享与邀请码服务"""

    def __init__(self, db: Session):
        super().__init__(db)

    def create_invite_code(
        self,
        user_id: str,
        code_type: str,
        max_uses: int,
        reward_type: str,
        reward_amount: int,
        expires_days: Optional[int] = None
    ) -> Dict[str, Any]:
        """创建邀请码"""
        import uuid
        from datetime import datetime, timedelta

        code = str(uuid.uuid4())[:8].upper()
        expires_at = None
        if expires_days:
            expires_at = datetime.now() + timedelta(days=expires_days)

        # 插入数据库
        from sqlalchemy import text
        invite_id = str(uuid.uuid4())
        self.db.execute(text("""
            INSERT INTO invite_codes (
                id, code, inviter_user_id, code_type, max_uses, used_count,
                reward_type, reward_amount, is_active, expires_at, created_at
            ) VALUES (
                :id, :code, :user_id, :type, :max, 0, :rtype, :ramount, TRUE, :expires, :created
            )
        """), {
            "id": invite_id,
            "code": code,
            "user_id": user_id,
            "type": code_type,
            "max": max_uses,
            "rtype": reward_type,
            "ramount": reward_amount,
            "expires": expires_at.isoformat() if expires_at else None,
            "created": datetime.now().isoformat()
        })
        self.db.commit()

        return {
            "id": invite_id,
            "code": code,
            "code_type": code_type,
            "max_uses": max_uses,
            "used_count": 0,
            "reward_type": reward_type,
            "reward_amount": reward_amount,
            "reward_description": f"邀请好友可获得{reward_amount}{reward_type}",
            "is_active": True,
            "expires_at": expires_at,
            "created_at": datetime.now()
        }

    def get_user_invite_codes(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户的邀请码列表"""
        from sqlalchemy import text

        result = self.db.execute(text("""
            SELECT id, code, code_type, max_uses, used_count, reward_type, reward_amount,
                   is_active, expires_at, created_at
            FROM invite_codes
            WHERE inviter_user_id = :user_id
            ORDER BY created_at DESC
        """), {"user_id": user_id})

        codes = []
        for row in result.fetchall():
            codes.append({
                "id": row[0],
                "code": row[1],
                "code_type": row[2],
                "max_uses": row[3],
                "used_count": row[4],
                "reward_type": row[5],
                "reward_amount": row[6],
                "is_active": row[7],
                "expires_at": row[8],
                "created_at": row[9]
            })
        return codes

    def validate_invite_code(self, code: str) -> Optional[Dict[str, Any]]:
        """验证邀请码"""
        from sqlalchemy import text
        from datetime import datetime

        result = self.db.execute(text("""
            SELECT id, code, inviter_user_id, code_type, max_uses, used_count,
                   reward_type, reward_amount, is_active, expires_at
            FROM invite_codes
            WHERE code = :code AND is_active = TRUE
        """), {"code": code}).fetchone()

        if not result:
            return None

        # 检查是否过期
        if result[9] and datetime.fromisoformat(str(result[9])) < datetime.now():
            return None

        # 检查是否达到使用次数上限
        if result[5] >= result[4]:
            return None

        return {
            "id": result[0],
            "code": result[1],
            "inviter_user_id": result[2],
            "code_type": result[3],
            "max_uses": result[4],
            "used_count": result[5],
            "reward_type": result[6],
            "reward_amount": result[7],
            "reward_description": f"邀请好友可获得{result[7]}{result[6]}"
        }

    def use_invite_code(
        self,
        code: str,
        invited_user_id: str,
        invited_user_email: str
    ) -> Optional[Dict[str, Any]]:
        """使用邀请码"""
        from sqlalchemy import text
        import uuid

        invite = self.validate_invite_code(code)
        if not invite:
            return None

        # 更新使用次数
        self.db.execute(text("""
            UPDATE invite_codes
            SET used_count = used_count + 1
            WHERE code = :code
        """), {"code": code})

        # 创建奖励记录
        reward_id = str(uuid.uuid4())
        self.db.execute(text("""
            INSERT INTO invite_rewards (
                id, invite_code_id, invited_user_id, inviter_user_id,
                reward_type, reward_amount, is_claimed, created_at
            ) VALUES (
                :id, :code_id, :invited_id, :inviter_id, :rtype, :ramount, FALSE, :created
            )
        """), {
            "id": reward_id,
            "code_id": invite["id"],
            "invited_id": invited_user_id,
            "inviter_id": invite["inviter_user_id"],
            "rtype": invite["reward_type"],
            "ramount": invite["reward_amount"],
            "created": datetime.now().isoformat()
        })

        # 创建分享记录
        share_id = str(uuid.uuid4())
        self.db.execute(text("""
            INSERT INTO share_records (
                id, user_id, share_type, channel, share_url,
                view_count, click_count, convert_count, created_at
            ) VALUES (
                :id, :user_id, 'invite', 'direct', :url, 0, 0, 1, :created
            )
        """), {
            "id": share_id,
            "user_id": invited_user_id,
            "url": f"/invite/{code}",
            "created": datetime.now().isoformat()
        })

        self.db.commit()

        return {
            "reward_type": invite["reward_type"],
            "reward_amount": invite["reward_amount"]
        }

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
    ) -> Dict[str, Any]:
        """创建分享记录"""
        from sqlalchemy import text
        import uuid

        record_id = str(uuid.uuid4())
        self.db.execute(text("""
            INSERT INTO share_records (
                id, user_id, share_type, channel, share_url, content_type, content_id,
                share_title, share_description, share_image_url,
                view_count, click_count, convert_count, created_at
            ) VALUES (
                :id, :user_id, :type, :channel, :url, :ctype, :cid, :title, :desc, :img, 0, 0, 0, :created
            )
        """), {
            "id": record_id,
            "user_id": user_id,
            "type": share_type,
            "channel": channel,
            "url": share_url,
            "ctype": content_type,
            "cid": content_id,
            "title": share_title,
            "desc": share_description,
            "img": share_image_url,
            "created": datetime.now().isoformat()
        })
        self.db.commit()

        return {
            "id": record_id,
            "user_id": user_id,
            "share_type": share_type,
            "channel": channel,
            "share_url": share_url,
            "view_count": 0,
            "click_count": 0,
            "convert_count": 0,
            "created_at": datetime.now()
        }

    def get_share_stats(self, user_id: str) -> Dict[str, Any]:
        """获取分享统计"""
        from sqlalchemy import text

        result = self.db.execute(text("""
            SELECT COUNT(*) as total,
                   COALESCE(SUM(view_count), 0) as total_views,
                   COALESCE(SUM(click_count), 0) as total_clicks,
                   COALESCE(SUM(convert_count), 0) as total_converts
            FROM share_records
            WHERE user_id = :user_id
        """), {"user_id": user_id}).fetchone()

        channel_result = self.db.execute(text("""
            SELECT channel, COUNT(*) as count,
                   COALESCE(SUM(view_count), 0) as views,
                   COALESCE(SUM(click_count), 0) as clicks
            FROM share_records
            WHERE user_id = :user_id
            GROUP BY channel
        """), {"user_id": user_id})

        channel_stats = {}
        for row in channel_result.fetchall():
            channel_stats[row[0]] = {"count": row[1], "views": row[2], "clicks": row[3]}

        return {
            "total_records": result[0],
            "total_views": result[1],
            "total_clicks": result[2],
            "total_converts": result[3],
            "channel_stats": channel_stats
        }

    def get_invite_stats(self, user_id: str) -> Dict[str, Any]:
        """获取邀请统计"""
        from sqlalchemy import text

        result = self.db.execute(text("""
            SELECT COUNT(*) as total_codes,
                   COALESCE(SUM(used_count), 0) as total_invites,
                   COALESCE(SUM(used_count * reward_amount), 0) as total_rewards
            FROM invite_codes
            WHERE inviter_user_id = :user_id
        """), {"user_id": user_id}).fetchone()

        codes_result = self.db.execute(text("""
            SELECT id, code, code_type, used_count, reward_type, reward_amount, created_at
            FROM invite_codes
            WHERE inviter_user_id = :user_id
            ORDER BY created_at DESC
        """), {"user_id": user_id})

        invite_codes = []
        for row in codes_result.fetchall():
            invite_codes.append({
                "id": row[0],
                "code": row[1],
                "type": row[2],
                "used_count": row[3],
                "reward_type": row[4],
                "reward_amount": row[5],
                "created_at": row[6]
            })

        return {
            "total_codes": result[0],
            "total_invites": result[1],
            "total_rewards": result[2],
            "invite_codes": invite_codes
        }


# ============= 事件驱动主动通知服务 =============

async def check_and_notify_preferences(new_user) -> None:
    """
    检查所有用户的偏好，匹配成功则写入通知队列

    【事件驱动】新用户注册时触发，不消耗 Token

    Args:
        new_user: 新注册的用户对象（UserDB）

    流程：
    1. 查询所有活跃的偏好订阅
    2. 逐个检查是否匹配（纯逻辑，不用 AI）
    3. 匹配成功 → 写入通知队列
    """
    from db.database import get_db
    from db.models import (
        UserNotificationPreferenceDB,
        PendingNotificationDB,
        UserDB,
    )
    from datetime import datetime
    import json

    logger.info(f"[NOTIFICATION_EVENT] 新用户注册触发检查: {new_user.id} ({new_user.name}, {new_user.location})")

    db = next(get_db())
    try:
        # 查询所有活跃的偏好订阅（新用户匹配类型）
        preferences = db.query(UserNotificationPreferenceDB).filter(
            UserNotificationPreferenceDB.is_active == True,
            UserNotificationPreferenceDB.trigger_type == "new_user_match"
        ).all()

        if not preferences:
            logger.info(f"[NOTIFICATION_EVENT] 无活跃偏好订阅，跳过")
            return

        logger.info(f"[NOTIFICATION_EVENT] 检查 {len(preferences)} 个偏好订阅")

        for pref in preferences:
            # 不通知自己
            if pref.user_id == new_user.id:
                continue

            conditions = json.loads(pref.conditions_json or "{}")

            # 纯逻辑匹配（不用 AI，节省 Token）
            if match_conditions(new_user, conditions):
                # 计算匹配度（可选，用于排序）
                match_score = calculate_match_score(pref.user_id, new_user.id, db)

                # 写入通知队列
                notification = PendingNotificationDB(
                    target_user_id=pref.user_id,
                    trigger_user_id=new_user.id,
                    trigger_type="new_user_match",
                    payload_json=json.dumps({
                        "name": new_user.name or "匿名",
                        "age": new_user.age or 0,
                        "location": new_user.location or "",
                        "gender": new_user.gender or "",
                        "match_score": match_score,
                        "interests": new_user.interests.split(",")[:3] if new_user.interests else [],
                    }),
                    status="pending",
                )
                db.add(notification)
                logger.info(f"[NOTIFICATION_EVENT] 匹配成功！通知用户 {pref.user_id}: {new_user.name} ({new_user.location})")

        db.commit()
        logger.info(f"[NOTIFICATION_EVENT] 通知队列写入完成")
    finally:
        db.close()


def match_conditions(new_user, conditions: dict) -> bool:
    """
    纯逻辑匹配（不用 AI）

    Args:
        new_user: 新注册的用户
        conditions: 偏好条件（JSON）

    Returns:
        是否匹配
    """
    # 地点匹配
    if conditions.get("location"):
        pref_location = conditions["location"]
        user_location = new_user.location or ""

        # 空地点不匹配任何条件
        if not user_location:
            return False

        # 宽松匹配：包含关系即可
        if pref_location not in user_location and user_location not in pref_location:
            return False

    # 性别匹配
    if conditions.get("gender"):
        if new_user.gender != conditions["gender"]:
            return False

    # 年龄范围匹配
    if conditions.get("age_range"):
        age_range = conditions["age_range"]
        if "-" in age_range:
            min_age, max_age = age_range.split("-")
            try:
                min_age = int(min_age)
                max_age = int(max_age)
                # 无年龄信息不匹配
                if new_user.age is None:
                    return False
                if not (min_age <= new_user.age <= max_age):
                    return False
            except ValueError:
                pass

    # 关系目标匹配
    if conditions.get("relationship_goal"):
        if new_user.relationship_goal != conditions["relationship_goal"]:
            return False

    return True


def calculate_match_score(user_id: str, new_user_id: str, db) -> int:
    """
    计算匹配度（简化版，不用 AI）

    Args:
        user_id: 订阅用户
        new_user_id: 新注册用户
        db: 数据库会话

    Returns:
        匹配度分数（0-100）
    """
    try:
        user = db.query(UserDB).filter(UserDB.id == user_id).first()
        new_user = db.query(UserDB).filter(UserDB.id == new_user_id).first()

        if not user or not new_user:
            return 50

        score = 50  # 基础分

        # 地点匹配加分
        if user.location and new_user.location:
            if user.location == new_user.location:
                score += 20  # 同城
            elif user.location in new_user.location or new_user.location in user.location:
                score += 10  # 附近

        # 年龄匹配加分
        if user.preferred_age_min and user.preferred_age_max:
            if user.preferred_age_min <= new_user.age <= user.preferred_age_max:
                score += 15

        # 关系目标匹配加分
        if user.relationship_goal and new_user.relationship_goal:
            if user.relationship_goal == new_user.relationship_goal:
                score += 10

        return min(score, 100)

    except Exception as e:
        logger.warning(f"[NOTIFICATION_EVENT] 计算匹配度失败: {e}")
        return 50


def get_pending_notifications(user_id: str) -> dict:
    """
    获取用户待推送通知

    Args:
        user_id: 用户 ID

    Returns:
        {"notifications": [...], "total": N, "has_unread": bool}
    """
    from db.database import get_db
    from db.models import PendingNotificationDB
    import json

    db = next(get_db())
    try:
        notifications = db.query(PendingNotificationDB).filter(
            PendingNotificationDB.target_user_id == user_id,
            PendingNotificationDB.status == "pending"
        ).order_by(PendingNotificationDB.created_at.desc()).limit(10).all()

        result = []
        for n in notifications:
            payload = json.loads(n.payload_json or "{}")
            result.append({
                "id": n.id,
                "type": n.trigger_type,
                "trigger_user_id": n.trigger_user_id,
                "payload": payload,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            })

        return {
            "notifications": result,
            "total": len(result),
            "has_unread": len(result) > 0,
        }
    finally:
        db.close()


def mark_notification_delivered(notification_id: int) -> bool:
    """标记通知已推送"""
    from db.database import get_db
    from db.models import PendingNotificationDB
    from datetime import datetime

    db = next(get_db())
    try:
        notification = db.query(PendingNotificationDB).filter(
            PendingNotificationDB.id == notification_id
        ).first()

        if notification:
            notification.status = "delivered"
            notification.delivered_at = datetime.now()
            db.commit()
            return True
        return False
    finally:
        db.close()


def mark_notification_read(notification_id: int) -> bool:
    """标记通知已读"""
    from db.database import get_db
    from db.models import PendingNotificationDB

    db = next(get_db())
    try:
        notification = db.query(PendingNotificationDB).filter(
            PendingNotificationDB.id == notification_id
        ).first()

        if notification:
            notification.status = "read"
            db.commit()
            return True
        return False
    finally:
        db.close()


def create_notification_preference(
    user_id: str,
    trigger_type: str,
    conditions: dict
) -> dict:
    """
    创建通知偏好订阅

    Args:
        user_id: 用户 ID
        trigger_type: 触发类型（new_user_match, mutual_like, etc.）
        conditions: 匹配条件

    Returns:
        创建结果
    """
    from db.database import get_db
    from db.models import UserNotificationPreferenceDB
    import json

    db = next(get_db())
    try:
        # 检查是否已存在
        existing = db.query(UserNotificationPreferenceDB).filter(
            UserNotificationPreferenceDB.user_id == user_id,
            UserNotificationPreferenceDB.trigger_type == trigger_type
        ).first()

        if existing:
            # 更新条件
            existing.conditions_json = json.dumps(conditions)
            existing.is_active = True
            db.commit()
            return {"success": True, "action": "updated", "id": existing.id}

        # 创建新订阅
        preference = UserNotificationPreferenceDB(
            user_id=user_id,
            trigger_type=trigger_type,
            conditions_json=json.dumps(conditions),
            is_active=True,
        )
        db.add(preference)
        db.commit()

        return {"success": True, "action": "created", "id": preference.id}
    finally:
        db.close()
