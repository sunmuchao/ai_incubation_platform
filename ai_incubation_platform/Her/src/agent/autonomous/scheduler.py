"""
心跳调度器

基于 APScheduler 实现定时心跳触发。
核心功能：
- 定时触发心跳（默认 30 分钟）
- 规则筛选与执行
- 分布式锁防止重复执行
- 支持立即触发（事件驱动）
"""
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

from utils.logger import logger
from db.database import get_db
from db.autonomous_models import HeartbeatRuleStateDB
from agent.autonomous.rule_parser import HeartbeatRuleParser, HeartbeatRule


# 默认心跳间隔（分钟）
DEFAULT_HEARTBEAT_INTERVAL = 30

# 心跳状态常量
HEARTBEAT_RESULT_EXECUTED = "executed"
HEARTBEAT_RESULT_SKIPPED = "skipped"
HEARTBEAT_RESULT_OK = "heartbeat_ok"
HEARTBEAT_RESULT_ERROR = "error"


class HeartbeatScheduler:
    """
    心跳调度器

    使用 APScheduler 定时触发心跳检查
    """

    def __init__(
        self,
        heartbeat_interval: int = DEFAULT_HEARTBEAT_INTERVAL,
        max_workers: int = 2
    ):
        self.heartbeat_interval = heartbeat_interval
        self.max_workers = max_workers

        # 调度器配置
        self.scheduler = BackgroundScheduler(
            jobstores={
                'default': MemoryJobStore()
            },
            executors={
                'default': ThreadPoolExecutor(max_workers)
            },
            job_defaults={
                'coalesce': True,  # 合并错过的任务
                'max_instances': 1,  # 同一时间最多1个实例
                'misfire_grace_time': 60  # 错过执行的宽容时间
            }
        )

        # 规则解析器
        self.rule_parser = HeartbeatRuleParser()

        # 运行状态
        self.is_running = False
        self.last_heartbeat_at: Optional[datetime] = None
        self.heartbeat_count = 0

        logger.info(f"HeartbeatScheduler initialized with interval={heartbeat_interval}m, max_workers={max_workers}")

    def start(self):
        """
        启动心跳调度器
        """
        if self.is_running:
            logger.warning("HeartbeatScheduler is already running")
            return

        # 加载规则
        self.rule_parser.load_rules()

        # 添加心跳任务
        self.scheduler.add_job(
            func=self._run_heartbeat,
            trigger=IntervalTrigger(minutes=self.heartbeat_interval),
            id='heartbeat_main',
            name='Main Heartbeat Check',
            replace_existing=True
        )

        # 启动调度器
        self.scheduler.start()
        self.is_running = True

        logger.info(f"HeartbeatScheduler started, interval={self.heartbeat_interval}m")

        # 立即执行一次心跳（可选）
        # self._run_heartbeat()

    def stop(self):
        """
        停止心跳调度器
        """
        if not self.is_running:
            logger.warning("HeartbeatScheduler is not running")
            return

        self.scheduler.shutdown(wait=False)
        self.is_running = False

        logger.info("HeartbeatScheduler stopped")

    def trigger_immediate(self, rule_name: str = None, user_id: str = None):
        """
        立即触发心跳（事件驱动）

        Args:
            rule_name: 指定执行的规则名称
            user_id: 指定用户ID（可选）
        """
        logger.info(f"Immediate heartbeat triggered, rule={rule_name}, user={user_id}")

        # 立即执行
        self._run_heartbeat(
            specific_rule=rule_name,
            specific_user=user_id,
            trigger_type="event"
        )

    def _run_heartbeat(
        self,
        specific_rule: str = None,
        specific_user: str = None,
        trigger_type: str = "scheduled"
    ):
        """
        执行心跳检查

        Args:
            specific_rule: 指定执行的规则（事件驱动时）
            specific_user: 指定用户（事件驱动时）
            trigger_type: 触发类型（scheduled/event）
        """
        heartbeat_id = str(uuid.uuid4())
        started_at = datetime.now()

        logger.info(f"🫀 [HEARTBEAT:{heartbeat_id}] Starting heartbeat, trigger={trigger_type}")

        try:
            # 获取规则执行状态
            rule_states = self._get_rule_states()

            # 筛选到期规则
            if specific_rule:
                # 事件驱动：执行指定规则
                due_rules = [r for r in self.rule_parser.rules if r.name == specific_rule]
            else:
                # 定时触发：筛选到期规则
                due_rules = self.rule_parser.get_due_rules(rule_states)

            # 检查是否跳过
            if self.rule_parser.should_skip_heartbeat(due_rules):
                self._record_heartbeat_skip(heartbeat_id)
                return

            # 执行心跳（调用心跳执行器）
            from agent.autonomous.executor import execute_heartbeat

            result = execute_heartbeat(
                heartbeat_id=heartbeat_id,
                due_rules=due_rules,
                context=self._build_heartbeat_context(specific_user),
                trigger_type=trigger_type
            )

            # 更新规则状态
            self._update_rule_states(due_rules, result)

            # 记录心跳完成
            self.last_heartbeat_at = datetime.now()
            self.heartbeat_count += 1

            logger.info(f"🫀 [HEARTBEAT:{heartbeat_id}] Completed, result={result['type']}")

        except Exception as e:
            logger.error(f"🫀 [HEARTBEAT:{heartbeat_id}] Failed: {e}", exc_info=True)
            self._record_heartbeat_error(heartbeat_id, str(e))

    def _get_rule_states(self) -> Dict[str, datetime]:
        """
        获取规则执行状态

        Returns:
            规则名称到最后执行时间的映射
        """
        rule_states = {}

        try:
            db = next(get_db())
            states = db.query(HeartbeatRuleStateDB).all()

            for state in states:
                rule_states[state.rule_name] = state.last_run_at

        except Exception as e:
            logger.warning(f"Failed to get rule states: {e}")

        return rule_states

    def _update_rule_states(
        self,
        due_rules: List[HeartbeatRule],
        result: Dict[str, Any]
    ):
        """
        更新规则执行状态
        """
        try:
            db = next(get_db())

            for rule in due_rules:
                # 查找现有状态记录
                state = db.query(HeartbeatRuleStateDB).filter(
                    HeartbeatRuleStateDB.rule_name == rule.name
                ).first()

                if state:
                    # 更新状态
                    state.last_run_at = datetime.now()
                    state.run_count += 1

                    if result['type'] == 'heartbeat_ok':
                        state.last_result = HEARTBEAT_RESULT_OK
                    elif result['type'] == 'action_required':
                        state.last_result = HEARTBEAT_RESULT_EXECUTED
                        state.action_count += 1
                        state.last_action = result.get('action_type', 'unknown')
                    elif result['type'] == 'skipped':
                        state.last_result = HEARTBEAT_RESULT_SKIPPED
                        state.skip_count += 1
                    elif result['type'] == 'error':
                        state.last_result = HEARTBEAT_RESULT_ERROR
                        state.error_count += 1
                        state.last_error = result.get('error', 'unknown')

                else:
                    # 创建新状态记录
                    state = HeartbeatRuleStateDB(
                        id=str(uuid.uuid4()),
                        rule_name=rule.name,
                        last_run_at=datetime.now(),
                        last_result=HEARTBEAT_RESULT_EXECUTED if result['type'] == 'action_required' else HEARTBEAT_RESULT_OK,
                        run_count=1,
                        action_count=1 if result['type'] == 'action_required' else 0
                    )
                    db.add(state)

            db.commit()

        except Exception as e:
            logger.error(f"Failed to update rule states: {e}")

    def _build_heartbeat_context(self, specific_user: str = None) -> Dict[str, Any]:
        """
        构建心跳上下文

        包含用户数、匹配数等统计信息
        """
        context = {
            "trigger_type": "scheduled",
            "specific_user": specific_user,
            "timestamp": datetime.now().isoformat()
        }

        try:
            db = next(get_db())

            # 获取统计信息
            from db.models import UserDB, MatchHistoryDB
            from sqlalchemy import func

            # 用户数
            user_count = db.query(func.count(UserDB.id)).scalar() or 0
            context["user_count"] = user_count

            # 匹配数
            match_count = db.query(func.count(MatchHistoryDB.id)).scalar() or 0
            context["match_count"] = match_count

            # 最近活跃用户（过去24小时有登录）
            from datetime import timedelta
            recent_active = db.query(func.count(UserDB.id)).filter(
                UserDB.last_login >= datetime.now() - timedelta(hours=24)
            ).scalar() or 0
            context["recent_active_users"] = recent_active

            # 新匹配（过去24小时）
            new_matches = db.query(func.count(MatchHistoryDB.id)).filter(
                MatchHistoryDB.created_at >= datetime.now() - timedelta(hours=24)
            ).scalar() or 0
            context["new_matches_24h"] = new_matches

        except Exception as e:
            logger.warning(f"Failed to build heartbeat context: {e}")

        return context

    def _record_heartbeat_skip(self, heartbeat_id: str):
        """
        记录心跳跳过
        """
        self.last_heartbeat_at = datetime.now()
        self.heartbeat_count += 1
        logger.info(f"🫀 [HEARTBEAT:{heartbeat_id}] Skipped (reason=no-rules-due)")

    def _record_heartbeat_error(self, heartbeat_id: str, error: str):
        """
        记录心跳错误
        """
        logger.error(f"🫀 [HEARTBEAT:{heartbeat_id}] Error: {error}")

    def get_status(self) -> Dict[str, Any]:
        """
        获取调度器状态
        """
        return {
            "is_running": self.is_running,
            "heartbeat_interval": self.heartbeat_interval,
            "last_heartbeat_at": self.last_heartbeat_at.isoformat() if self.last_heartbeat_at else None,
            "heartbeat_count": self.heartbeat_count,
            "rules_count": len(self.rule_parser.rules),
            "scheduler_jobs": len(self.scheduler.get_jobs()) if self.is_running else 0
        }


# ============= 全局调度器实例 =============

_global_scheduler: Optional[HeartbeatScheduler] = None


def get_scheduler() -> HeartbeatScheduler:
    """
    获取全局调度器实例
    """
    if _global_scheduler is None:
        _global_scheduler = HeartbeatScheduler()
    return _global_scheduler


def start_heartbeat(interval: int = DEFAULT_HEARTBEAT_INTERVAL):
    """
    启动心跳调度器（便捷函数）
    """
    global _global_scheduler
    _global_scheduler = HeartbeatScheduler(heartbeat_interval=interval)
    _global_scheduler.start()
    return _global_scheduler


def stop_heartbeat():
    """
    停止心跳调度器（便捷函数）
    """
    if _global_scheduler:
        _global_scheduler.stop()


# ============= 导出 =============

__all__ = [
    "HeartbeatScheduler",
    "get_scheduler",
    "start_heartbeat",
    "stop_heartbeat",
    "DEFAULT_HEARTBEAT_INTERVAL",
]