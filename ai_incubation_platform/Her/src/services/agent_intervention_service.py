"""
Agent 自主权管控服务

P1 功能：为 AI Agent 的自主行为增加"介入阈值"管控

AI 在发现异常（如账单异常、安全风险）时，需根据用户设置的授权等级决定：
- 私下提醒用户
- 在对话中暗示
- 主动推送建议
- 紧急干预（通知平台）

介入等级：
- silent (0): 仅记录，不提醒
- private (1): 私下提醒用户
- suggestion (2): 在对话中暗示
- active (3): 主动推送建议
- emergency (4): 紧急情况，立即干预
"""
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc
import json

from db.database import SessionLocal
from models.p18_p22_models import PrivacySetting
from utils.logger import logger


class AgentInterventionService:
    """Agent 自主权管控服务"""

    # 介入等级定义
    INTERVENTION_LEVELS = {
        "silent": 0,        # 仅记录，不提醒
        "private": 1,       # 私下提醒用户
        "suggestion": 2,    # 在对话中暗示
        "active": 3,        # 主动推送建议
        "emergency": 4,     # 紧急情况，立即干预
    }

    # 事件严重程度映射
    EVENT_SEVERITY = {
        # 安全类事件
        "safety_risk_detected": 4,       # 安全风险（紧急）
        "harassment_detected": 4,        # 骚扰行为（紧急）
        "abnormal_bill": 3,              # 账单异常（主动推送）
        "unusual_location": 3,           # 位置异常（主动推送）
        "aggressive_language": 2,        # 攻击性语言（对话暗示）
        "fake_info_detected": 2,         # 虚假信息（对话暗示）
        "preference_mismatch": 1,        # 偏好不一致（私下提醒）
        "dating_suggestion": 1,          # 约会建议（私下提醒）
    }

    # 默认介入策略
    DEFAULT_INTERVENTION_STRATEGIES = {
        4: {  # 紧急情况
            "action": "emergency_intervention",
            "notify_platform": True,
            "notify_user": True,
            "message_template": "检测到潜在安全风险，平台已介入处理"
        },
        3: {  # 主动推送
            "action": "push_notification",
            "notify_platform": False,
            "notify_user": True,
            "message_template": "AI 发现异常情况，建议您关注"
        },
        2: {  # 对话暗示
            "action": "chat_suggestion",
            "notify_platform": False,
            "notify_user": True,
            "message_template": "在对话中委婉提醒"
        },
        1: {  # 私下提醒
            "action": "private_notification",
            "notify_platform": False,
            "notify_user": True,
            "message_template": "仅通知当事用户"
        },
        0: {  # 仅记录
            "action": "log_only",
            "notify_platform": False,
            "notify_user": False,
            "message_template": None
        }
    }

    def __init__(self):
        self._db: Optional[Session] = None
        self._should_close_db: bool = False

    def _get_db(self) -> Session:
        """获取数据库会话"""
        if self._db is None:
            self._db = SessionLocal()
            self._should_close_db = True
        return self._db

    def close(self):
        """关闭数据库会话（仅关闭自己创建的）"""
        if self._should_close_db and self._db is not None:
            try:
                self._db.commit()
                self._db.close()
            except Exception as e:
                logger.error(f"Error closing database session: {e}")
            finally:
                self._db = None
                self._should_close_db = False

    def get_user_intervention_level(self, user_id: str) -> int:
        """
        获取用户的 AI 介入等级设置

        Returns:
            介入等级 (0-4)
        """
        db = self._get_db()
        setting = db.query(PrivacySetting).filter(
            PrivacySetting.user_id == user_id
        ).first()

        if not setting:
            # 默认等级：suggestion (在对话中暗示)
            return self.INTERVENTION_LEVELS["suggestion"]

        # 从隐私设置中读取
        ai_intervention = getattr(setting, 'ai_intervention_level', 'suggestion')
        return self.INTERVENTION_LEVELS.get(ai_intervention, 2)

    def set_user_intervention_level(
        self,
        user_id: str,
        level: str
    ) -> Tuple[bool, str]:
        """
        设置用户的 AI 介入等级

        Args:
            user_id: 用户 ID
            level: 等级名称 (silent/private/suggestion/active/emergency)

        Returns:
            (success, message)
        """
        if level not in self.INTERVENTION_LEVELS:
            return False, f"无效的介入等级：{level}"

        db = self._get_db()

        setting = db.query(PrivacySetting).filter(
            PrivacySetting.user_id == user_id
        ).first()

        if not setting:
            setting = PrivacySetting(
                user_id=user_id,
                ai_intervention_level=level,
                data_sharing_consent=True,
                analytics_consent=True
            )
            db.add(setting)
        else:
            setting.ai_intervention_level = level

        db.commit()
        logger.info(f"Set intervention level for user {user_id}: {level}")
        return True, f"已设置 AI 介入等级为：{level}"

    def check_intervention(
        self,
        user_id: str,
        event_type: str,
        event_data: Dict[str, Any]
    ) -> Optional[Dict]:
        """
        检查是否需要介入以及介入方式

        Args:
            user_id: 用户 ID
            event_type: 事件类型
            event_data: 事件数据

        Returns:
            介入配置（如果需要介入），None 表示不打扰
        """
        # 获取用户授权等级
        user_level = self.get_user_intervention_level(user_id)

        # 评估事件严重程度
        severity = self.EVENT_SEVERITY.get(event_type, 1)

        logger.info(
            f"Intervention check: user={user_id}, event={event_type}, "
            f"severity={severity}, user_level={user_level}"
        )

        # 用户设置的授权等级低于事件严重程度时，采用默认策略
        if user_level < severity:
            # 升级介入等级以匹配事件严重性
            final_level = severity
            logger.info(
                f"User level {user_level} < severity {severity}, "
                f"upgrading to {final_level}"
            )
        else:
            final_level = user_level

        # 获取介入策略
        strategy = self.DEFAULT_INTERVENTION_STRATEGIES.get(final_level)

        if not strategy or strategy["action"] == "log_only":
            return None  # 不打扰

        return {
            "level": final_level,
            "action": strategy["action"],
            "notify_platform": strategy["notify_platform"],
            "notify_user": strategy["notify_user"],
            "message": strategy["message_template"],
            "event_type": event_type,
            "event_data": event_data
        }

    def execute_intervention(
        self,
        user_id: str,
        intervention_config: Dict
    ) -> Tuple[bool, str]:
        """
        执行介入

        Args:
            user_id: 用户 ID
            intervention_config: 介入配置

        Returns:
            (success, message)
        """
        action = intervention_config.get("action")

        if action == "emergency_intervention":
            # 紧急干预：通知平台 + 通知用户
            self._notify_platform_admin(user_id, intervention_config)
            self._send_emergency_notification(user_id, intervention_config)
            return True, "已启动紧急干预"

        elif action == "push_notification":
            # 主动推送
            self._send_push_notification(user_id, intervention_config)
            return True, "已发送推送通知"

        elif action == "chat_suggestion":
            # 对话暗示
            self._add_chat_suggestion(user_id, intervention_config)
            return True, "已添加对话建议"

        elif action == "private_notification":
            # 私下提醒
            self._send_private_notification(user_id, intervention_config)
            return True, "已发送私下提醒"

        else:
            logger.warning(f"Unknown intervention action: {action}")
            return False, f"未知的介入动作：{action}"

    def _notify_platform_admin(
        self,
        user_id: str,
        config: Dict
    ):
        """通知平台管理员（紧急干预）"""
        logger.warning(
            f"PLATFORM ALERT: user={user_id}, event={config.get('event_type')}, "
            f"data={config.get('event_data')}"
        )
        # 这里可以集成实际的告警系统（如 Slack、钉钉、短信）

    def _send_emergency_notification(
        self,
        user_id: str,
        config: Dict
    ):
        """发送紧急通知给用户"""
        logger.info(f"Emergency notification to user {user_id}: {config.get('message')}")

    def _send_push_notification(
        self,
        user_id: str,
        config: Dict
    ):
        """发送推送通知"""
        logger.info(f"Push notification to user {user_id}: {config.get('message')}")

    def _send_private_notification(
        self,
        user_id: str,
        config: Dict
    ):
        """发送私下提醒"""
        logger.info(f"Private notification to user {user_id}: {config.get('message')}")

    def _add_chat_suggestion(
        self,
        user_id: str,
        config: Dict
    ):
        """添加对话建议"""
        logger.info(f"Chat suggestion added for user {user_id}: {config.get('message')}")

    def get_intervention_history(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict]:
        """
        获取介入历史

        Args:
            user_id: 用户 ID
            limit: 返回数量
            offset: 偏移量

        Returns:
            介入历史记录
        """
        # 这里可以从数据库查询审计日志
        # 简化实现：返回空列表
        return []

    def get_user_settings(self, user_id: str) -> Dict:
        """
        获取用户的完整设置

        Returns:
            设置字典
        """
        level = self.get_user_intervention_level(user_id)
        level_name = [k for k, v in self.INTERVENTION_LEVELS.items() if v == level][0]

        return {
            "user_id": user_id,
            "intervention_level": level,
            "intervention_level_name": level_name,
            "intervention_level_description": self._get_level_description(level_name)
        }

    def _get_level_description(self, level_name: str) -> str:
        """获取等级描述"""
        descriptions = {
            "silent": "仅在紧急情况下提醒",
            "private": "适度提醒（默认）",
            "suggestion": "主动提供建议（推荐）",
            "active": "全方位指导（适合恋爱新手）",
            "emergency": "仅紧急情况干预"
        }
        return descriptions.get(level_name, "")


# 全局单例
agent_intervention_service = AgentInterventionService()
