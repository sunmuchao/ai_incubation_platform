"""
自主代理引擎测试

测试心跳机制的完整流程：
- 规则解析
- 心跳调度
- HEARTBEAT_OK 协议
- 推送执行
"""
import pytest
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock


class TestHeartbeatRuleParser:
    """测试规则解析器"""

    def test_parse_interval_minutes(self):
        """测试分钟间隔解析"""
        from agent.autonomous.rule_parser import HeartbeatRule

        rule = HeartbeatRule(
            name="test_rule",
            interval="30m",
            prompt="test prompt"
        )

        assert rule.interval_minutes == 30

    def test_parse_interval_hours(self):
        """测试小时间隔解析"""
        from agent.autonomous.rule_parser import HeartbeatRule

        rule = HeartbeatRule(
            name="test_rule",
            interval="1h",
            prompt="test prompt"
        )

        assert rule.interval_minutes == 60

    def test_parse_interval_24h(self):
        """测试24小时间隔解析"""
        from agent.autonomous.rule_parser import HeartbeatRule

        rule = HeartbeatRule(
            name="test_rule",
            interval="24h",
            prompt="test prompt"
        )

        assert rule.interval_minutes == 1440

    def test_is_due_never_run(self):
        """测试从未执行过的规则是否到期"""
        from agent.autonomous.rule_parser import HeartbeatRule

        rule = HeartbeatRule(
            name="test_rule",
            interval="30m",
            prompt="test prompt"
        )

        # 从未执行过，应该到期
        assert rule.is_due(None) == True

    def test_is_due_recently_run(self):
        """测试刚执行过的规则是否到期"""
        from agent.autonomous.rule_parser import HeartbeatRule

        rule = HeartbeatRule(
            name="test_rule",
            interval="30m",
            prompt="test prompt"
        )

        # 刚执行过，应该不到期
        last_run = datetime.now() - timedelta(minutes=5)
        assert rule.is_due(last_run) == False

    def test_is_due_long_time_run(self):
        """测试很久执行过的规则是否到期"""
        from agent.autonomous.rule_parser import HeartbeatRule

        rule = HeartbeatRule(
            name="test_rule",
            interval="30m",
            prompt="test prompt"
        )

        # 很久执行过，应该到期
        last_run = datetime.now() - timedelta(minutes=60)
        assert rule.is_due(last_run) == True

    def test_load_default_rules(self):
        """测试加载默认规则"""
        from agent.autonomous.rule_parser import HeartbeatRuleParser

        parser = HeartbeatRuleParser(rules_file="/nonexistent/file.md")
        rules = parser.load_rules()

        # 应返回默认规则
        assert len(rules) >= 1
        assert rules[0].name == "check_new_matches"


class TestHeartbeatExecutor:
    """测试心跳执行器"""

    def test_parse_heartbeat_ok(self):
        """测试 HEARTBEAT_OK 响应解析"""
        from agent.autonomous.executor import HeartbeatExecutor

        executor = HeartbeatExecutor()
        result = executor._parse_response("HEARTBEAT_OK")

        assert result['type'] == 'heartbeat_ok'
        assert result['action'] is None

    def test_parse_heartbeat_ok_with_message(self):
        """测试带消息的 HEARTBEAT_OK 解析"""
        from agent.autonomous.executor import HeartbeatExecutor

        executor = HeartbeatExecutor()
        result = executor._parse_response("HEARTBEAT_OK\n本次检查无新增匹配。")

        assert result['type'] == 'heartbeat_ok'
        assert result['message'] == "本次检查无新增匹配。"

    def test_parse_action_required(self):
        """测试 ACTION_REQUIRED 响应解析"""
        from agent.autonomous.executor import HeartbeatExecutor

        executor = HeartbeatExecutor()
        response = """
ACTION_REQUIRED
推送对象: user_123, match_456
推送类型: icebreaker
推送理由: 新匹配成功，建议推送破冰建议
推荐内容: 你们有共同兴趣，可以聊聊
"""
        result = executor._parse_response(response)

        assert result['type'] == 'action_required'
        assert result['action_type'] == 'icebreaker'
        assert 'user_123' in result.get('target_users', [])

    def test_assemble_prompt(self):
        """测试提示词组装"""
        from agent.autonomous.executor import HeartbeatExecutor
        from agent.autonomous.rule_parser import HeartbeatRule

        executor = HeartbeatExecutor()

        rules = [
            HeartbeatRule(
                name="test_rule",
                interval="30m",
                prompt="检查测试",
                action_type="icebreaker"
            )
        ]

        context = {
            "user_count": 100,
            "match_count": 50,
            "recent_active_users": 20,
            "new_matches_24h": 10,
            "trigger_type": "scheduled",
            "timestamp": datetime.now().isoformat()
        }

        prompt = executor._assemble_prompt(rules, context)

        # 检查关键内容是否存在
        assert "test_rule" in prompt
        assert "100" in prompt  # user_count
        assert "指导原则" in prompt


class TestPushExecutor:
    """测试推送执行器"""

    def test_push_strategies_exist(self):
        """测试推送策略配置"""
        from agent.autonomous.push_executor import PushExecutor

        executor = PushExecutor()

        # 检查策略存在
        assert "icebreaker" in executor.PUSH_STRATEGIES
        assert "topic_suggestion" in executor.PUSH_STRATEGIES
        assert "activation_reminder" in executor.PUSH_STRATEGIES

    def test_generate_push_content(self):
        """测试推送内容生成"""
        from agent.autonomous.push_executor import PushExecutor

        executor = PushExecutor()
        strategy = executor.PUSH_STRATEGIES["icebreaker"]

        content = executor._generate_push_content(
            action_type="icebreaker",
            strategy=strategy,
            user_id="test_user",
            match_id="test_match",
            recommended_content="测试推荐内容",
            context={}
        )

        assert "title" in content
        assert "message" in content
        assert "测试推荐内容" in content["message"]


class TestEventListener:
    """测试事件监听器"""

    def test_supported_events(self):
        """测试支持的事件类型"""
        from agent.autonomous.event_listener import EventListener

        listener = EventListener()

        assert "match_created" in listener.SUPPORTED_EVENTS
        assert "message_sent" in listener.SUPPORTED_EVENTS
        assert "user_login" in listener.SUPPORTED_EVENTS

    def test_event_priority(self):
        """测试事件优先级"""
        from agent.autonomous.event_listener import EventListener

        listener = EventListener()

        assert listener.EVENT_PRIORITY["match_created"] == "high"
        assert listener.EVENT_PRIORITY["message_sent"] == "medium"
        assert listener.EVENT_PRIORITY["profile_updated"] == "low"


class TestHeartbeatScheduler:
    """测试心跳调度器"""

    def test_scheduler_initialization(self):
        """测试调度器初始化"""
        from agent.autonomous.scheduler import HeartbeatScheduler

        scheduler = HeartbeatScheduler(heartbeat_interval=30)

        assert scheduler.heartbeat_interval == 30
        assert scheduler.is_running == False

    def test_get_status(self):
        """测试获取调度器状态"""
        from agent.autonomous.scheduler import HeartbeatScheduler

        scheduler = HeartbeatScheduler(heartbeat_interval=30)
        status = scheduler.get_status()

        assert "is_running" in status
        assert "heartbeat_interval" in status
        assert status["is_running"] == False


# ============= 集成测试 =============

class TestHeartbeatIntegration:
    """心跳流程集成测试"""

    @pytest.mark.asyncio
    async def test_full_heartbeat_flow(self):
        """
        测试完整心跳流程

        流程：
        1. 加载规则
        2. 筛选到期规则
        3. 执行心跳
        4. 处理响应
        """
        from agent.autonomous.rule_parser import HeartbeatRuleParser, HeartbeatRule
        from agent.autonomous.executor import HeartbeatExecutor

        # 1. 使用默认规则（不依赖文件）
        parser = HeartbeatRuleParser(rules_file="/nonexistent/file.md")
        # 获取默认规则并赋值给 parser.rules
        parser.rules = parser._get_default_rules()

        assert len(parser.rules) >= 1

        # 2. 筛选到期规则（全部从未执行，应该都到期）
        rule_states = {}
        due_rules = parser.get_due_rules(rule_states)

        assert len(due_rules) >= 1

        # 3. 执行心跳（使用 mock LLM）
        executor = HeartbeatExecutor()

        # 模拟 LLM 返回 HEARTBEAT_OK
        with patch.object(executor, '_call_llm', return_value="HEARTBEAT_OK"):
            result = executor.execute(
                heartbeat_id="test_heartbeat_001",
                due_rules=due_rules,
                context={"user_count": 100, "match_count": 50},
                trigger_type="scheduled"
            )

            assert result['type'] == 'heartbeat_ok'

        # 4. 模拟需要行动的场景
        with patch.object(executor, '_call_llm', return_value="ACTION_REQUIRED\n推送对象: user_123\n推送类型: icebreaker\n推送理由: 测试"):
            result = executor.execute(
                heartbeat_id="test_heartbeat_002",
                due_rules=due_rules,
                context={"user_count": 100, "match_count": 50},
                trigger_type="scheduled"
            )

            assert result['type'] == 'action_required'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])