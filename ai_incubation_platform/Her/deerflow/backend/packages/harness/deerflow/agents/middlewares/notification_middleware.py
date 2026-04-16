"""
Notification Middleware - 事件驱动主动通知

架构说明：
- DeerFlow harness 不能导入 Her app 代码（边界规则）
- 通过 HTTP API 调用 Her 通知服务获取待推送通知
- 在对话开始前注入通知提示，让 Agent 主动推送

流程：
1. 用户打开 App → Agent 对话开始
2. Middleware 检查通知队列 → 有待推送
3. 注入提示消息：【系统通知】有位深圳的小姐姐刚加入...
4. Agent 看到提示 → 主动说："嘿！有个好消息..."
"""
import logging
from typing import NotRequired, override
import httpx

from langchain.agents import AgentState
from langchain.agents.middleware import AgentMiddleware
from langgraph.runtime import Runtime

logger = logging.getLogger(__name__)

# Her API 地址（可通过环境变量配置）
HER_API_BASE_URL = "http://localhost:8002"


class NotificationMiddlewareState(AgentState):
    """Compatible with the ThreadState schema."""

    notifications: NotRequired[list | None]


class NotificationMiddleware(AgentMiddleware[NotificationMiddlewareState]):
    """
    主动推送通知 Middleware

    在对话开始前检查 Her API 通知队列，如果有待推送通知，
    注入提示消息让 Agent 主动告知用户。

    Token 消耗：只在生成推送消息时用一次 Token
    """

    state_schema = NotificationMiddlewareState

    def _get_pending_notifications(self, user_id: str) -> dict | None:
        """
        通过 HTTP API 获取待推送通知

        Args:
            user_id: 用户 ID

        Returns:
            {"notifications": [...], "has_unread": bool} 或 None
        """
        try:
            response = httpx.get(
                f"{HER_API_BASE_URL}/api/notifications/pending",
                params={"user_id": user_id},
                timeout=5.0,
            )

            if response.status_code == 200:
                return response.json()

        except Exception as e:
            logger.debug(f"[NotificationMiddleware] 获取通知失败: {e}")

        return None

    def _build_notification_hint(self, notifications: list) -> str:
        """
        构建通知提示（让 Agent 知道要主动说）

        Args:
            notifications: 通知列表

        Returns:
            提示消息文本
        """
        hints = []

        for n in notifications[:3]:  # 只提示最近 3 条
            payload = n.get("payload", {})
            trigger_type = n.get("type", "")
            notification_id = n.get("id")

            if trigger_type == "new_user_match":
                # 新用户匹配通知
                name = payload.get("name", "匿名")
                location = payload.get("location", "未知")
                match_score = payload.get("match_score", 50)
                trigger_user_id = n.get("trigger_user_id", "")

                hints.append(
                    f"【系统通知】有位 {location} 的 {name} 刚加入平台，匹配度 {match_score}%。"
                    f"请主动告知用户，并调用 her_get_target_user(target_user_id=\"{trigger_user_id}\") 展示详情。"
                    f"通知ID: {notification_id}"
                )

            elif trigger_type == "mutual_like":
                # 互相喜欢通知
                name = payload.get("name", "TA")
                hints.append(
                    f"【系统通知】你和 {name} 互相喜欢了！配对成功！"
                    f"请主动告知用户，恭喜他们配对成功。"
                    f"通知ID: {notification_id}"
                )

        return "\n\n".join(hints)

    def _should_check_notifications(self, state: NotificationMiddlewareState) -> bool:
        """
        判断是否需要检查通知

        只在对话开始时（第一条消息）检查，避免重复检查
        """
        messages = state.get("messages", [])

        # 只有第一条用户消息时才检查
        user_messages = [m for m in messages if m.type == "human"]
        return len(user_messages) == 1

    def _get_user_id_from_config(self, runtime: Runtime) -> str | None:
        """
        从 Runtime config 中获取 user_id

        Her API 会将 user_id 传入 configurable
        """
        config = runtime.config if hasattr(runtime, "config") else {}
        configurable = config.get("configurable", {})
        return configurable.get("user_id")

    def _check_and_inject_notifications(self, state: NotificationMiddlewareState, runtime: Runtime) -> dict | None:
        """
        检查通知并注入提示消息

        Returns:
            {"messages": [HumanMessage(...)]} 或 None
        """
        if not self._should_check_notifications(state):
            return None

        user_id = self._get_user_id_from_config(runtime)
        if not user_id:
            logger.debug("[NotificationMiddleware] 无 user_id，跳过通知检查")
            return None

        # 获取待推送通知
        result = self._get_pending_notifications(user_id)
        if not result or not result.get("has_unread"):
            logger.debug(f"[NotificationMiddleware] 用户 {user_id} 无待推送通知")
            return None

        notifications = result.get("notifications", [])
        if not notifications:
            return None

        logger.info(f"[NotificationMiddleware] 用户 {user_id} 有 {len(notifications)} 条待推送通知")

        # 构建提示消息
        hint = self._build_notification_hint(notifications)

        if not hint:
            return None

        # 注入 HumanMessage 到消息开头
        from langchain_core.messages import HumanMessage

        notification_message = HumanMessage(content=hint)

        # 返回更新
        return {
            "messages": [notification_message],
            "notifications": notifications,  # 存储通知列表，供后续标记已推送
        }

    @override
    def before_model(self, state: NotificationMiddlewareState, runtime: Runtime) -> dict | None:
        """
        在 LLM 调用前检查通知

        这是同步版本，适用于非异步环境
        """
        return self._check_and_inject_notifications(state, runtime)

    @override
    async def abefore_model(self, state: NotificationMiddlewareState, runtime: Runtime) -> dict | None:
        """
        在 LLM 调用前检查通知（异步版本）
        """
        return self._check_and_inject_notifications(state, runtime)

    @override
    def after_model(self, state: NotificationMiddlewareState, runtime: Runtime) -> dict | None:
        """
        在 LLM 调用后标记通知已推送

        如果 Agent 已经推送了通知，标记为 delivered
        """
        notifications = state.get("notifications")
        if not notifications:
            return None

        # 检查 AI 消息是否包含通知相关内容（简化判断）
        messages = state.get("messages", [])
        ai_messages = [m for m in messages if m.type == "ai"]

        if ai_messages:
            last_ai_content = ai_messages[-1].content if ai_messages else ""

            # 如果 AI 消息包含"好消息"、"刚加入"、"匹配"等关键词，认为已推送
            if any(kw in str(last_ai_content) for kw in ["好消息", "刚加入", "匹配", "小姐姐", "小哥哥"]):
                # 标记第一条通知为已推送
                first_notification_id = notifications[0].get("id")
                if first_notification_id:
                    self._mark_notification_delivered(first_notification_id)

        # 清除 notifications 状态
        return {"notifications": None}

    def _mark_notification_delivered(self, notification_id: int) -> bool:
        """标记通知已推送"""
        try:
            response = httpx.post(
                f"{HER_API_BASE_URL}/api/notifications/{notification_id}/mark_delivered",
                timeout=5.0,
            )
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"[NotificationMiddleware] 标记通知失败: {e}")
            return False


__all__ = ["NotificationMiddleware"]