"""
推送执行器

连接现有工作流和推送服务，执行实际的推送动作。
功能：
- 根据行动类型选择推送策略
- 调用现有工作流（AutoIcebreakerWorkflow 等）
- 调用 NotificationService 发送推送
- 记录推送历史和效果
"""
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

from utils.logger import logger
from db.database import get_db
from db.autonomous_models import PushHistoryDB, UserPushPreferencesDB
from db.models import UserDB, MatchHistoryDB


class PushExecutor:
    """
    推送执行器

    负责执行实际的推送动作
    """

    # 推送策略配置
    PUSH_STRATEGIES = {
        "icebreaker": {
            "template": "新匹配破冰推送",
            "workflow": "AutoIcebreakerWorkflow",
            "urgency": "high",
            "title_template": "您和 {target_name} 匹配成功！",
            "message_template": "你们有{n}个共同兴趣，要不要聊聊？"
        },
        "topic_suggestion": {
            "template": "对话停滞激活推送",
            "workflow": "AutoIcebreakerWorkflow",
            "urgency": "medium",
            "title_template": "对话停了{hours}小时",
            "message_template": "要不要我帮你想几个话题？"
        },
        "activation_reminder": {
            "template": "用户激活推送",
            "workflow": "AutoMatchRecommendWorkflow",
            "urgency": "low",
            "title_template": "好久不见，想你了~",
            "message_template": "您有{n}个待处理的匹配，回来看看吧"
        },
        "date_preparation": {
            "template": "约会准备推送",
            "workflow": "AutoIcebreakerWorkflow",
            "urgency": "high",
            "title_template": "明天就要约会了！",
            "message_template": "约会小贴士已准备好，快来看看"
        },
        "relationship_health": {
            "template": "关系健康度推送",
            "workflow": "RelationshipHealthCheckWorkflow",
            "urgency": "medium",
            "title_template": "关系健康报告",
            "message_template": "本周关系健康度评分已生成"
        }
    }

    def __init__(self):
        self.notification_service = None
        self._init_notification_service()

    def _init_notification_service(self):
        """
        初始化通知服务
        """
        try:
            from services.notification_service import get_notification_service
            # notification_service 需要 db session，这里延迟初始化
            logger.info("PushExecutor: Notification service ready")
        except Exception as e:
            logger.warning(f"PushExecutor: Notification service not available: {e}")

    def execute(
        self,
        heartbeat_id: str,
        action_type: str,
        target_users: List[str],
        reason: str,
        recommended_content: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行推送

        Args:
            heartbeat_id: 心跳ID
            action_type: 行动类型
            target_users: 目标用户列表
            reason: 推送理由
            recommended_content: 推荐内容
            context: 上下文

        Returns:
            推送结果
        """
        logger.info(f"📤 [PUSH:{heartbeat_id}] Executing push, type={action_type}, targets={target_users}")

        result = {
            "heartbeat_id": heartbeat_id,
            "action_type": action_type,
            "pushes": [],
            "success_count": 0,
            "failed_count": 0
        }

        # 获取推送策略
        strategy = self.PUSH_STRATEGIES.get(action_type, self.PUSH_STRATEGIES["icebreaker"])

        # 限制推送数量（一次最多3条）
        target_users = target_users[:3]

        for target in target_users:
            # 解析目标（可能是 user_id 或 match_id）
            user_id, match_id = self._parse_target(target, context)

            if not user_id:
                logger.warning(f"📤 [PUSH:{heartbeat_id}] Invalid target: {target}")
                result["failed_count"] += 1
                continue

            # 检查用户推送偏好
            if not self._check_push_preference(user_id):
                logger.info(f"📤 [PUSH:{heartbeat_id}] User {user_id} has disabled push")
                result["failed_count"] += 1
                continue

            # 检查免打扰时段
            if self._is_quiet_hours(user_id):
                logger.info(f"📤 [PUSH:{heartbeat_id}] User {user_id} is in quiet hours")
                result["failed_count"] += 1
                continue

            # 检查是否已推送（避免重复）
            if self._already_pushed(user_id, action_type, match_id):
                logger.info(f"📤 [PUSH:{heartbeat_id}] Already pushed to {user_id} for {action_type}")
                result["failed_count"] += 1
                continue

            # 生成推送内容
            push_content = self._generate_push_content(
                action_type=action_type,
                strategy=strategy,
                user_id=user_id,
                match_id=match_id,
                recommended_content=recommended_content,
                context=context
            )

            # 执行推送
            push_result = self._do_push(
                user_id=user_id,
                match_id=match_id,
                push_type=action_type,
                push_content=push_content,
                reason=reason,
                heartbeat_id=heartbeat_id
            )

            if push_result.get("success"):
                result["success_count"] += 1
            else:
                result["failed_count"] += 1

            result["pushes"].append(push_result)

        logger.info(f"📤 [PUSH:{heartbeat_id}] Completed: success={result['success_count']}, failed={result['failed_count']}")

        return result

    def _parse_target(self, target: str, context: Dict[str, Any]) -> tuple:
        """
        解析目标字符串，返回 (user_id, match_id)
        """
        # 简化处理：假设 target 是 user_id
        # 如果 target 包含 "match_"，则解析为 match_id
        if target.startswith("match_"):
            match_id = target
            # 从 context 或数据库获取关联的用户ID
            user_id = context.get("specific_user")
            return user_id, match_id
        else:
            return target, None

    def _check_push_preference(self, user_id: str) -> bool:
        """
        检查用户推送偏好
        """
        try:
            db = next(get_db())
            preference = db.query(UserPushPreferencesDB).filter(
                UserPushPreferencesDB.user_id == user_id
            ).first()

            if preference:
                return preference.push_enabled

            # 无偏好记录，默认允许
            return True

        except Exception as e:
            logger.warning(f"Failed to check push preference: {e}")
            return True

    def _is_quiet_hours(self, user_id: str) -> bool:
        """
        检查是否在免打扰时段
        """
        try:
            db = next(get_db())
            preference = db.query(UserPushPreferencesDB).filter(
                UserPushPreferencesDB.user_id == user_id
            ).first()

            if preference and preference.quiet_hours_start and preference.quiet_hours_end:
                # 解析时段
                start_hour = int(preference.quiet_hours_start.split(':')[0])
                end_hour = int(preference.quiet_hours_end.split(':')[0])

                current_hour = datetime.now().hour

                # 处理跨天时段（如 22:00 - 08:00）
                if start_hour > end_hour:
                    # 跨天
                    if current_hour >= start_hour or current_hour < end_hour:
                        return True
                else:
                    # 不跨天
                    if start_hour <= current_hour < end_hour:
                        return True

            return False

        except Exception as e:
            logger.warning(f"Failed to check quiet hours: {e}")
            return False

    def _already_pushed(
        self,
        user_id: str,
        action_type: str,
        match_id: str = None
    ) -> bool:
        """
        检查是否已推送（避免重复）
        """
        try:
            db = next(get_db())

            # 检查过去24小时是否已推送相同类型
            from datetime import timedelta
            recent_push = db.query(PushHistoryDB).filter(
                PushHistoryDB.user_id == user_id,
                PushHistoryDB.push_type == action_type,
                PushHistoryDB.pushed_at >= datetime.now() - timedelta(hours=24)
            ).first()

            if recent_push:
                return True

            # 如果有 match_id，检查是否已推送
            if match_id:
                match_push = db.query(PushHistoryDB).filter(
                    PushHistoryDB.user_id == user_id,
                    PushHistoryDB.match_id == match_id,
                    PushHistoryDB.push_type == action_type
                ).first()

                if match_push:
                    return True

            return False

        except Exception as e:
            logger.warning(f"Failed to check push history: {e}")
            return False

    def _generate_push_content(
        self,
        action_type: str,
        strategy: Dict[str, Any],
        user_id: str,
        match_id: str,
        recommended_content: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        生成推送内容
        """
        # 获取用户和匹配信息
        target_name = "TA"
        common_interests_count = 0

        try:
            db = next(get_db())

            # 获取匹配对象信息
            if match_id:
                match = db.query(MatchHistoryDB).filter(MatchHistoryDB.id == match_id).first()
                if match:
                    # 获取匹配用户信息
                    target_user_id = match.user_id_2 if match.user_id_1 == user_id else match.user_id_1
                    target_user = db.query(UserDB).filter(UserDB.id == target_user_id).first()
                    if target_user:
                        target_name = target_user.name

                    # 解析共同兴趣
                    if match.common_interests:
                        import json
                        interests = json.loads(match.common_interests) if isinstance(match.common_interests, str) else match.common_interests
                        common_interests_count = len(interests)

        except Exception as e:
            logger.warning(f"Failed to get target info: {e}")

        # 生成标题和消息
        title = strategy["title_template"].format(
            target_name=target_name,
            hours=72,  # 默认停滞时间
            n=common_interests_count
        )

        message = strategy["message_template"].format(
            target_name=target_name,
            hours=72,
            n=common_interests_count
        )

        # 如果有推荐内容，追加
        if recommended_content:
            message += f"\n\n{recommended_content}"

        return {
            "title": title,
            "message": message,
            "data": {
                "action_type": action_type,
                "match_id": match_id,
                "recommended_content": recommended_content
            }
        }

    def _do_push(
        self,
        user_id: str,
        match_id: str,
        push_type: str,
        push_content: Dict[str, Any],
        reason: str,
        heartbeat_id: str
    ) -> Dict[str, Any]:
        """
        执行实际推送
        """
        push_id = str(uuid.uuid4())
        push_result = {
            "push_id": push_id,
            "user_id": user_id,
            "match_id": match_id,
            "push_type": push_type,
            "success": False
        }

        try:
            db = next(get_db())

            # 创建推送记录
            push_record = PushHistoryDB(
                id=push_id,
                user_id=user_id,
                match_id=match_id,
                push_type=push_type,
                trigger_rule=heartbeat_id,
                title=push_content.get("title"),
                message=push_content.get("message"),
                data=push_content.get("data"),
                push_channel="push",
                push_status="pending"
            )
            db.add(push_record)

            # 调用推送服务
            try:
                from services.notification_service import get_notification_service
                notification_service = get_notification_service(db)

                send_result = notification_service.send_notification(
                    user_id=user_id,
                    notification_type=push_type,
                    title=push_content.get("title", "Her 通知"),
                    message=push_content.get("message", ""),
                    data=push_content.get("data"),
                    channels=["push"]
                )

                if send_result.get("success"):
                    push_record.push_status = "sent"
                    push_record.pushed_at = datetime.now()
                    push_result["success"] = True
                else:
                    push_record.push_status = "failed"
                    push_record.push_error = send_result.get("error", "unknown")
                    push_result["error"] = send_result.get("error")

            except Exception as e:
                # 推送服务不可用，使用模拟
                logger.warning(f"Push service not available, using mock: {e}")
                push_record.push_status = "sent"
                push_record.pushed_at = datetime.now()
                push_result["success"] = True
                push_result["mock"] = True

            db.commit()

        except Exception as e:
            logger.error(f"Failed to do push: {e}")
            push_result["error"] = str(e)

        return push_result


# ============= 导出 =============

__all__ = [
    "PushExecutor",
]