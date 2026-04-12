"""
自主代理引擎 - 心跳机制

借鉴 OpenClaw 心跳机制，实现 Her 的主动代理能力。
核心组件：
- HeartbeatScheduler：心跳调度器（APScheduler）
- HeartbeatRuleParser：规则解析器（读取 HEARTBEAT_RULES.md）
- HeartbeatExecutor：心跳执行器（LLM调用 + HEARTBEAT_OK协议）
"""

# 延迟导入，避免循环依赖
def get_scheduler():
    from agent.autonomous.scheduler import HeartbeatScheduler, start_heartbeat, stop_heartbeat
    return HeartbeatScheduler, start_heartbeat, stop_heartbeat

def get_rule_parser():
    from agent.autonomous.rule_parser import HeartbeatRuleParser, HeartbeatRule, load_heartbeat_rules
    return HeartbeatRuleParser, HeartbeatRule, load_heartbeat_rules

def get_executor():
    from agent.autonomous.executor import HeartbeatExecutor, execute_heartbeat
    return HeartbeatExecutor, execute_heartbeat

def get_push_executor():
    from agent.autonomous.push_executor import PushExecutor
    return PushExecutor

def get_event_listener():
    from agent.autonomous.event_listener import EventListener, emit_event
    return EventListener, emit_event


__all__ = [
    "get_scheduler",
    "get_rule_parser",
    "get_executor",
    "get_push_executor",
    "get_event_listener",
]