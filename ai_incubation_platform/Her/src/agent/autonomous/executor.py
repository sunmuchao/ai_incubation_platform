"""
心跳执行器

核心组件：负责调用心跳 LLM 并处理 HEARTBEAT_OK 协议。
功能：
- 组装心跳提示词
- 调用 LLM 判断是否需要行动
- 解析 HEARTBEAT_OK / 行动指令
- 触发推送执行器
"""
import uuid
import re
import json
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional

from utils.logger import logger
from agent.autonomous.rule_parser import HeartbeatRule


# HEARTBEAT 协议常量
HEARTBEAT_TOKEN = "HEARTBEAT_OK"
ACTION_TOKEN = "ACTION_REQUIRED"
HEARTBEAT_ACK_MAX_CHARS = 300


# 心跳提示词模板
HEARTBEAT_PROMPT_TEMPLATE = """
你是 Her 约会助手的心跳代理。请检查以下到期任务并判断是否需要采取行动。

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

{guidelines_section}

## 响应格式要求

如果无事需要处理，回复：
```
HEARTBEAT_OK
```

如果需要推送，回复：
```
ACTION_REQUIRED
推送对象: <用户ID>, <匹配ID>
推送类型: <icebreaker/topic/activation/date/health>
推送理由: <为什么需要推送>
推荐内容: <具体的推送内容建议>
```

请开始检查。
"""


class HeartbeatExecutor:
    """
    心跳执行器

    调用 LLM 判断是否需要行动
    """

    def __init__(self):
        self.llm_client = None
        self._init_llm_client()

    def _init_llm_client(self):
        """
        初始化 LLM 客户端

        适配现有 LLMIntegrationClient
        """
        try:
            from integration.llm_client import llm_client
            self.llm_client = llm_client
            logger.info("HeartbeatExecutor: LLM client initialized (using existing LLMIntegrationClient)")
        except Exception as e:
            logger.warning(f"HeartbeatExecutor: Failed to init LLM client: {e}")
            self.llm_client = None

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

        # 调用 LLM（同步包装异步调用）
        llm_response = self._call_llm(heartbeat_id, prompt)

        # 解析响应
        result = self._parse_response(llm_response)

        # 如果需要行动，触发推送执行器
        if result['type'] == 'action_required':
            self._trigger_push_executor(heartbeat_id, result, context)

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

        # 指导原则部分
        guidelines_text = """
1. 如果无事需要处理，回复 HEARTBEAT_OK
2. 如果需要推送，必须明确说明推送对象、类型和理由
3. 推送内容要个性化，避免模板化
4. 注意用户推送偏好设置，尊重免打扰时段
5. 检查是否有重复推送，避免骚扰用户
6. 优先级：icebreaker > date > topic > activation > health
7. 一次心跳最多推送3条消息
"""

        return HEARTBEAT_PROMPT_TEMPLATE.format(
            due_rules_section=due_rules_text,
            user_count=context.get('user_count', 0),
            match_count=context.get('match_count', 0),
            recent_active_users=context.get('recent_active_users', 0),
            new_matches_24h=context.get('new_matches_24h', 0),
            trigger_type=context.get('trigger_type', 'scheduled'),
            specific_user=context.get('specific_user', '无'),
            timestamp=context.get('timestamp', datetime.now().isoformat()),
            guidelines_section=guidelines_text
        )

    def _call_llm(self, heartbeat_id: str, prompt: str) -> str:
        """
        调用 LLM

        适配现有 LLMIntegrationClient.generate_chat
        使用线程安全的调用方式，避免 event loop 问题
        """
        if self.llm_client is None:
            logger.warning(f"🫀 [EXECUTOR:{heartbeat_id}] LLM client not available, using mock response")
            return self._get_mock_response(prompt)

        try:
            logger.debug(f"🫀 [EXECUTOR:{heartbeat_id}] Calling LLM with prompt length={len(prompt)}")

            # 使用新的事件循环调用异步方法（线程安全）
            new_loop = asyncio.new_event_loop()
            try:
                response = new_loop.run_until_complete(self.llm_client.generate_chat(prompt))
            finally:
                new_loop.close()

            # 提取响应文本
            if isinstance(response, dict):
                content = response.get('text', '') or response.get('message', '') or str(response)
            elif isinstance(response, str):
                content = response
            else:
                content = str(response)

            logger.debug(f"🫀 [EXECUTOR:{heartbeat_id}] LLM response: {content[:200]}...")
            return content

        except Exception as e:
            logger.error(f"🫀 [EXECUTOR:{heartbeat_id}] LLM call failed: {e}")
            return self._get_mock_response(prompt)

    def _get_mock_response(self, prompt: str) -> str:
        """
        获取模拟响应（用于测试或 LLM 不可用时）
        """
        # 简单判断：如果有 check_new_matches 规则，返回行动指令
        if "check_new_matches" in prompt:
            return """
ACTION_REQUIRED
推送对象: user_demo_001, match_demo_001
推送类型: icebreaker
推送理由: 检测到新匹配，建议推送破冰建议
推荐内容: 你们有3个共同兴趣，可以从这些话题开始聊
"""
        else:
            return "HEARTBEAT_OK"

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """
        解析 LLM 响应

        支持 HEARTBEAT_OK 和 ACTION_REQUIRED 两种格式
        """
        response = response.strip()

        # 检查 HEARTBEAT_OK
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

        # 检查 ACTION_REQUIRED
        if response.startswith(ACTION_TOKEN) or "ACTION_REQUIRED" in response:
            return self._parse_action_response(response)

        # 无法识别，返回 unclear
        logger.warning(f"Unrecognized heartbeat response format")
        return {
            "type": "unclear",
            "message": response
        }

    def _parse_action_response(self, response: str) -> Dict[str, Any]:
        """
        解析行动指令响应
        """
        result = {
            "type": "action_required",
            "actions": []
        }

        # 提取推送对象
        user_match = re.search(r'推送对象:\s*(.+)', response)
        if user_match:
            targets = user_match.group(1).strip()
            # 解析用户ID和匹配ID
            target_parts = targets.replace(',', ' ').split()
            result["target_users"] = target_parts

        # 提取推送类型
        type_match = re.search(r'推送类型:\s*(\S+)', response)
        if type_match:
            result["action_type"] = type_match.group(1).strip()

        # 提取推送理由
        reason_match = re.search(r'推送理由:\s*(.+)', response)
        if reason_match:
            result["reason"] = reason_match.group(1).strip()

        # 提取推荐内容
        content_match = re.search(r'推荐内容:\s*(.+)', response)
        if content_match:
            result["recommended_content"] = content_match.group(1).strip()

        logger.info(f"Parsed action: type={result.get('action_type')}, targets={result.get('target_users')}")

        return result

    def _trigger_push_executor(
        self,
        heartbeat_id: str,
        action_result: Dict[str, Any],
        context: Dict[str, Any]
    ):
        """
        触发推送执行器
        """
        try:
            from agent.autonomous.push_executor import PushExecutor

            executor = PushExecutor()
            push_result = executor.execute(
                heartbeat_id=heartbeat_id,
                action_type=action_result.get('action_type', 'unknown'),
                target_users=action_result.get('target_users', []),
                reason=action_result.get('reason', ''),
                recommended_content=action_result.get('recommended_content', ''),
                context=context
            )

            action_result["push_result"] = push_result

        except Exception as e:
            logger.error(f"🫀 [EXECUTOR:{heartbeat_id}] Failed to trigger push executor: {e}")
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