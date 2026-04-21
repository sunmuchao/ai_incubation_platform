"""
心跳执行器

核心组件：负责调用心跳 LLM 并处理 HEARTBEAT_OK 协议。
功能：
- 组装心跳提示词
- 调用 DeerFlow Agent 判断是否需要行动（个性化决策）
- 解析 HEARTBEAT_OK / 行动指令
- 触发推送执行器（通过 WebSocket 推送到前端对话界面）

【主动性重构 v2】
- 原设计：直接调用 LLM，模板化推送内容
- 新设计：调用 DeerFlow Agent，让 Agent 像真实对话一样思考
- 效果：红娘主动在对话界面说话，而非系统通知
"""
import uuid
import re
import json
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional, TYPE_CHECKING

from utils.logger import logger
from agent.autonomous.rule_parser import HeartbeatRule

# 避免循环导入，使用 TYPE_CHECKING
if TYPE_CHECKING:
    from api.websocket import push_proactive_message_to_user


# HEARTBEAT 协议常量
HEARTBEAT_TOKEN = "HEARTBEAT_OK"
ACTION_TOKEN = "ACTION_REQUIRED"
HEARTBEAT_ACK_MAX_CHARS = 300


# 心跳提示词模板（用于 DeerFlow Agent）
HEARTBEAT_PROMPT_TEMPLATE = """
【心跳检查】请你作为红娘助手，检查以下到期任务并判断是否需要主动联系用户。

## 到期任务列表

{due_rules_section}

## 当前上下文

- 用户总数：{user_count}
- 匹配总数：{match_count}
- 最近24小时活跃用户：{recent_active_users}
- 最近24小时新匹配：{new_matches_24h}
- 触发类型：{trigger_type}
- 特定用户：{specific_user}
- 时间戳：{timestamp}

## 指导原则

1. 如果无事需要处理，回复 HEARTBEAT_OK
2. 如果需要主动联系用户，用自然语言写出要发送的消息（像真实对话一样）
3. 消息要个性化，避免模板化，体现红娘的贴心和专业
4. 注意用户推送偏好设置，尊重免打扰时段（22:00-08:00）
5. 检查是否有重复推送，避免骚扰用户
6. 优先级：破冰建议 > 约会提醒 > 话题激活 > 活跃唤醒 > 关系健康

## 响应格式要求

如果无事需要处理，回复：
```
HEARTBEAT_OK
```

如果需要主动联系用户，直接写出消息内容（用自然语言，像聊天一样）：
```
你好呀！昨天匹配的那位女生还没聊呢，我发现你们都喜欢户外徒步，要不要我帮你想个开场白？
```

请开始检查。
"""


class HeartbeatExecutor:
    """
    心跳执行器

    调用 DeerFlow Agent 判断是否需要行动（主动性重构）
    """

    def __init__(self):
        self.deerflow_client = None
        self._init_deerflow_client()

    def _init_deerflow_client(self):
        """
        初始化 DeerFlow 客户端

        使用 Her 的 deerflow.py 中的 get_deerflow_client
        """
        try:
            # 导入 Her 的 DeerFlow 客户端
            import sys
            import os
            # 确保 Her 的 src 目录在 Python 路径中
            her_src_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            if her_src_path not in sys.path:
                sys.path.insert(0, her_src_path)

            from api.deerflow import get_deerflow_client, DEERFLOW_AVAILABLE

            if DEERFLOW_AVAILABLE:
                self.deerflow_client = get_deerflow_client()
                logger.info("HeartbeatExecutor: DeerFlow client initialized")
            else:
                logger.warning("HeartbeatExecutor: DeerFlow not available, using fallback")
                self.deerflow_client = None
        except Exception as e:
            logger.warning(f"HeartbeatExecutor: Failed to init DeerFlow client: {e}")
            self.deerflow_client = None

    def execute(
        self,
        heartbeat_id: str,
        due_rules: List[HeartbeatRule],
        context: Dict[str, Any],
        trigger_type: str = "scheduled"
    ) -> Dict[str, Any]:
        """
        执行心跳检查

        Args:
            heartbeat_id: 心跳ID
            due_rules: 到期规则列表
            context: 心跳上下文
            trigger_type: 触发类型

        Returns:
            心跳结果
        """
        logger.info(f"🫀 [EXECUTOR:{heartbeat_id}] Executing with {len(due_rules)} due rules")

        # 组装心跳提示词
        prompt = self._assemble_prompt(due_rules, context)

        # 调用 DeerFlow Agent（而非直接调 LLM）
        agent_response = self._call_deerflow_agent(heartbeat_id, prompt, context)

        # 解析响应
        result = self._parse_response(agent_response)

        # 如果需要行动，触发 WebSocket 推送
        if result['type'] == 'action_required':
            self._trigger_websocket_push(heartbeat_id, result, context)

        return result

    def _assemble_prompt(
        self,
        due_rules: List[HeartbeatRule],
        context: Dict[str, Any]
    ) -> str:
        """
        组装心跳提示词
        """
        # 到期规则部分
        due_rules_text = "\n".join([
            f"- [{rule.name}] (间隔 {rule.interval})\n  任务: {rule.prompt}\n  行动类型: {rule.action_type or '未指定'}"
            for rule in due_rules
        ])

        return HEARTBEAT_PROMPT_TEMPLATE.format(
            due_rules_section=due_rules_text,
            user_count=context.get('user_count', 0),
            match_count=context.get('match_count', 0),
            recent_active_users=context.get('recent_active_users', 0),
            new_matches_24h=context.get('new_matches_24h', 0),
            trigger_type=context.get('trigger_type', 'scheduled'),
            specific_user=context.get('specific_user', '无'),
            timestamp=context.get('timestamp', datetime.now().isoformat()),
        )

    def _call_deerflow_agent(
        self,
        heartbeat_id: str,
        prompt: str,
        context: Dict[str, Any]
    ) -> str:
        """
        调用 DeerFlow Agent（而非直接调 LLM）

        使用 DeerFlow 的 chat 方法，让 Agent 像真实对话一样思考
        """
        if self.deerflow_client is None:
            logger.warning(f"🫀 [EXECUTOR:{heartbeat_id}] DeerFlow client not available, using fallback")
            return self._get_fallback_response(prompt)

        try:
            logger.debug(f"🫀 [EXECUTOR:{heartbeat_id}] Calling DeerFlow Agent with prompt length={len(prompt)}")

            # 使用 DeerFlow 的 chat 方法
            # thread_id 使用固定的 "heartbeat" 表示心跳专用对话
            thread_id = "heartbeat-proactive-agent"

            # 调用 DeerFlow Agent（使用 chat 方法）
            response = self.deerflow_client.chat(prompt, thread_id=thread_id)

            # 提取响应文本
            if isinstance(response, dict):
                content = response.get('ai_message', '') or response.get('text', '') or str(response)
            elif isinstance(response, str):
                content = response
            else:
                content = str(response)

            logger.debug(f"🫀 [EXECUTOR:{heartbeat_id}] Agent response: {content[:200]}...")
            return content

        except Exception as e:
            logger.error(f"🫀 [EXECUTOR:{heartbeat_id}] DeerFlow Agent call failed: {e}")
            return self._get_fallback_response(prompt)

    def _get_fallback_response(self, prompt: str) -> str:
        """
        获取降级响应（DeerFlow 不可用时）
        """
        # 简单判断：如果有 check_new_matches 规则，返回行动指令
        if "check_new_matches" in prompt:
            return "你好呀！有新的匹配对象等你查看，要不要我帮你看看？"
        elif "check_stale_conversations" in prompt:
            return "你之前的聊天好像停了几天了，要不要我帮你想几个话题继续聊聊？"
        elif "check_user_activity" in prompt:
            return "好久不见！有新的人在等你，回来看看吧~"
        else:
            return "HEARTBEAT_OK"

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """
        解析 DeerFlow Agent 响应

        支持 HEARTBEAT_OK 和自然语言消息两种格式
        """
        response = response.strip()

        # 检查 HEARTBEAT_OK（无事可做）
        if response.startswith(HEARTBEAT_TOKEN):
            remaining = response[len(HEARTBEAT_TOKEN):].strip()

            # 如果剩余内容超过限制，可能不是纯粹的 OK
            if len(remaining) > HEARTBEAT_ACK_MAX_CHARS:
                logger.warning(f"HEARTBEAT_OK response too long, treating as unclear")
                return {
                    "type": "unclear",
                    "message": response
                }

            return {
                "type": "heartbeat_ok",
                "message": remaining if remaining else None,
                "action": None
            }

        # 其他情况：Agent 输出了自然语言消息，需要推送
        # 新设计：直接把 Agent 的消息作为推送内容
        logger.info(f"Parsed action: Agent wants to send message: {response[:100]}...")
        return {
            "type": "action_required",
            "action_type": "proactive_message",
            "message": response,  # Agent 的自然语言消息
            "reason": "Agent 主动判断需要联系用户",
        }

    def _trigger_websocket_push(
        self,
        heartbeat_id: str,
        action_result: Dict[str, Any],
        context: Dict[str, Any]
    ):
        """
        触发 WebSocket 推送（而非极光推送）

        将 Agent 的消息推送到前端对话界面，让用户看到红娘主动说话
        """
        try:
            # 获取目标用户（从 context 或规则中提取）
            specific_user = context.get('specific_user')

            if not specific_user:
                logger.warning(f"🫀 [EXECUTOR:{heartbeat_id}] No specific user to push to")
                return

            # 调用 WebSocket 推送服务
            from api.websocket import push_proactive_message_to_user

            message = action_result.get('message', '')

            logger.info(f"🫀 [EXECUTOR:{heartbeat_id}] Pushing to user {specific_user}: {message[:50]}...")

            push_result = push_proactive_message_to_user(
                user_id=specific_user,
                message=message,
                heartbeat_id=heartbeat_id
            )

            action_result["push_result"] = push_result

        except Exception as e:
            logger.error(f"🫀 [EXECUTOR:{heartbeat_id}] Failed to trigger WebSocket push: {e}")
            action_result["push_error"] = str(e)


def execute_heartbeat(
    heartbeat_id: str,
    due_rules: List[HeartbeatRule],
    context: Dict[str, Any],
    trigger_type: str = "scheduled"
) -> Dict[str, Any]:
    """
    执行心跳（便捷函数）
    """
    executor = HeartbeatExecutor()
    return executor.execute(heartbeat_id, due_rules, context, trigger_type)


# ============= 导出 =============

__all__ = [
    "HeartbeatExecutor",
    "execute_heartbeat",
    "HEARTBEAT_TOKEN",
    "ACTION_TOKEN",
]