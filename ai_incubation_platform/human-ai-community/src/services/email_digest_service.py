"""
邮件摘要通知服务
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
import logging
import asyncio

logger = logging.getLogger(__name__)


class DigestFrequency(str, Enum):
    """摘要发送频率"""
    DAILY = "daily"  # 每日
    WEEKLY = "weekly"  # 每周
    MONTHLY = "monthly"  # 每月
    NEVER = "never"  # 从不


class EmailDigestService:
    """邮件摘要服务"""

    def __init__(self):
        self._digest_queue: Dict[str, List[dict]] = {}  # 用户摘要队列
        self._user_preferences: Dict[str, Dict[str, Any]] = {}  # 用户摘要偏好
        self._last_digest_time: Dict[str, datetime] = {}  # 上次发送时间

    def set_user_digest_preference(
        self,
        user_id: str,
        frequency: str,
        email: str,
        digest_time: int = 8,  # 默认早上 8 点发送
    ):
        """设置用户摘要偏好"""
        self._user_preferences[user_id] = {
            "frequency": frequency,
            "email": email,
            "digest_time": digest_time,
            "enabled": frequency != DigestFrequency.NEVER.value,
        }
        logger.info(f"设置用户 {user_id} 摘要偏好：frequency={frequency}, email={email}")

    def get_user_digest_preference(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户摘要偏好"""
        return self._user_preferences.get(user_id)

    def add_to_digest(
        self,
        user_id: str,
        notification_type: str,
        title: str,
        content: str,
        metadata: Optional[dict] = None,
    ):
        """添加到摘要队列"""
        if user_id not in self._digest_queue:
            self._digest_queue[user_id] = []

        self._digest_queue[user_id].append({
            "type": notification_type,
            "title": title,
            "content": content,
            "metadata": metadata or {},
            "added_at": datetime.now().isoformat(),
        })

        logger.debug(f"用户 {user_id} 摘要队列新增一条，当前数量：{len(self._digest_queue[user_id])}")

    def get_digest_items(self, user_id: str, limit: int = 50) -> List[dict]:
        """获取用户摘要项"""
        if user_id not in self._digest_queue:
            return []
        return self._digest_queue[user_id][:limit]

    def clear_digest_queue(self, user_id: str):
        """清空用户摘要队列"""
        if user_id in self._digest_queue:
            self._digest_queue[user_id] = []

    def should_send_digest(self, user_id: str) -> bool:
        """检查是否应该发送摘要"""
        if user_id not in self._user_preferences:
            return False

        pref = self._user_preferences[user_id]
        if not pref.get("enabled", False):
            return False

        frequency = pref.get("frequency")
        last_time = self._last_digest_time.get(user_id)

        now = datetime.now()

        # 首次发送
        if last_time is None:
            return self._is_digest_time(now, pref)

        # 检查频率
        if frequency == DigestFrequency.DAILY.value:
            return self._is_daily_due(now, last_time, pref)
        elif frequency == DigestFrequency.WEEKLY.value:
            return self._is_weekly_due(now, last_time, pref)
        elif frequency == DigestFrequency.MONTHLY.value:
            return self._is_monthly_due(now, last_time, pref)

        return False

    def _is_digest_time(self, now: datetime, pref: dict) -> bool:
        """检查是否是摘要发送时间"""
        digest_time = pref.get("digest_time", 8)
        return now.hour == digest_time

    def _is_daily_due(self, now: datetime, last_time: datetime, pref: dict) -> bool:
        """检查是否到了每日摘要时间"""
        if now.date() == last_time.date():
            return False
        return self._is_digest_time(now, pref)

    def _is_weekly_due(self, now: datetime, last_time: datetime, pref: dict) -> bool:
        """检查是否到了每周摘要时间"""
        # 每周一发送
        if now.weekday() != 0:  # 0 = Monday
            return False
        if now.date() == last_time.date():
            return False
        return self._is_digest_time(now, pref)

    def _is_monthly_due(self, now: datetime, last_time: datetime, pref: dict) -> bool:
        """检查是否到了每月摘要时间"""
        # 每月 1 号发送
        if now.day != 1:
            return False
        if now.month == last_time.month and now.year == last_time.year:
            return False
        return self._is_digest_time(now, pref)

    def generate_digest_email(
        self,
        user_id: str,
        include_items: int = 20,
    ) -> Optional[Dict[str, Any]]:
        """生成摘要邮件内容"""
        if user_id not in self._user_preferences:
            return None

        pref = self._user_preferences[user_id]
        items = self.get_digest_items(user_id, include_items)

        if not items:
            return None

        # 按类型分组
        grouped_items: Dict[str, List[dict]] = {}
        for item in items:
            item_type = item.get("type", "other")
            if item_type not in grouped_items:
                grouped_items[item_type] = []
            grouped_items[item_type].append(item)

        # 生成邮件内容
        subject = self._generate_digest_subject(pref, len(items))
        html_content = self._generate_digest_html(pref, grouped_items)
        text_content = self._generate_digest_text(pref, grouped_items)

        return {
            "user_id": user_id,
            "email": pref["email"],
            "subject": subject,
            "html_content": html_content,
            "text_content": text_content,
            "item_count": len(items),
            "groups": grouped_items,
        }

    def _generate_digest_subject(self, pref: dict, item_count: int) -> str:
        """生成摘要邮件主题"""
        frequency = pref.get("frequency", "daily")
        if frequency == "daily":
            period = "每日"
        elif frequency == "weekly":
            period = "每周"
        else:
            period = "每月"

        return f"[人 AI 社区] 您的{period}动态摘要 - 共{item_count}条更新"

    def _generate_digest_html(self, pref: dict, grouped_items: Dict[str, List[dict]]) -> str:
        """生成 HTML 格式摘要"""
        type_names = {
            "content_approved": "内容审核通过",
            "content_rejected": "内容审核结果",
            "reply_added": "新回复",
            "report_processed": "举报处理",
            "new_follower": "新关注",
            "content_liked": "内容被点赞",
            "channel_notification": "频道通知",
        }

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f9f9f9; padding: 20px; border-radius: 0 0 8px 8px; }}
                .section {{ margin-bottom: 20px; }}
                .section-title {{ font-size: 16px; font-weight: bold; color: #667eea; border-bottom: 2px solid #667eea; padding-bottom: 5px; }}
                .item {{ background: white; padding: 10px; margin: 10px 0; border-radius: 4px; border-left: 3px solid #667eea; }}
                .item-title {{ font-weight: bold; }}
                .item-content {{ color: #666; font-size: 14px; }}
                .footer {{ text-align: center; color: #999; font-size: 12px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>人 AI 社区动态摘要</h1>
                    <p>您好！这是您的人 AI 社区动态摘要</p>
                </div>
                <div class="content">
        """

        for item_type, items in grouped_items.items():
            type_name = type_names.get(item_type, item_type)
            html += f"""
            <div class="section">
                <div class="section-title">{type_name} ({len(items)}条)</div>
            """
            for item in items[:10]:  # 每个类型最多显示 10 条
                html += f"""
                <div class="item">
                    <div class="item-title">{item.get('title', '')}</div>
                    <div class="item-content">{item.get('content', '')[:200]}</div>
                </div>
                """
            html += "</div>"

        html += """
                <div class="footer">
                    <p>此邮件由人 AI 社区自动发送</p>
                    <p>如需修改订阅偏好，请访问设置页面</p>
                </div>
            </div>
        </body>
        </html>
        """

        return html

    def _generate_digest_text(self, pref: dict, grouped_items: Dict[str, List[dict]]) -> str:
        """生成纯文本格式摘要"""
        type_names = {
            "content_approved": "内容审核通过",
            "content_rejected": "内容审核结果",
            "reply_added": "新回复",
            "report_processed": "举报处理",
            "new_follower": "新关注",
            "content_liked": "内容被点赞",
            "channel_notification": "频道通知",
        }

        text = "人 AI 社区动态摘要\n"
        text += "=" * 40 + "\n\n"

        total_items = sum(len(items) for items in grouped_items.values())
        text += f"共 {total_items} 条更新\n\n"

        for item_type, items in grouped_items.items():
            type_name = type_names.get(item_type, item_type)
            text += f"\n{type_name} ({len(items)}条)\n"
            text += "-" * 30 + "\n"

            for i, item in enumerate(items[:10], 1):
                text += f"{i}. {item.get('title', '')}\n"
                text += f"   {item.get('content', '')[:100]}\n"

        text += "\n" + "=" * 40 + "\n"
        text += "此邮件由人 AI 社区自动发送\n"
        text += "如需修改订阅偏好，请访问设置页面\n"

        return text

    def record_digest_sent(self, user_id: str):
        """记录摘要已发送"""
        self._last_digest_time[user_id] = datetime.now()
        self.clear_digest_queue(user_id)
        logger.info(f"用户 {user_id} 摘要邮件已发送记录")

    def get_digest_stats(self, user_id: str) -> Dict[str, Any]:
        """获取用户摘要统计"""
        queue_size = len(self._digest_queue.get(user_id, []))
        last_time = self._last_digest_time.get(user_id)
        pref = self._user_preferences.get(user_id, {})

        return {
            "user_id": user_id,
            "queue_size": queue_size,
            "enabled": pref.get("enabled", False),
            "frequency": pref.get("frequency", "never"),
            "last_digest_at": last_time.isoformat() if last_time else None,
        }


# 全局邮件摘要服务实例
email_digest_service = EmailDigestService()
