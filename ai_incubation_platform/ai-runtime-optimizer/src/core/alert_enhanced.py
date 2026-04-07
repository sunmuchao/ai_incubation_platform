"""
告警系统增强模块：动态基线、告警抑制、升级策略、分析
对标 Datadog Watchdog 智能告警能力
"""
import uuid
import logging
import statistics
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable, Set, Tuple
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict
import asyncio

from core.alert_engine import AlertSeverity

logger = logging.getLogger(__name__)


class EscalationPolicyType(str, Enum):
    """升级策略类型"""
    TIME_BASED = "time_based"  # 基于时间升级
    SEVERITY_BASED = "severity_based"  # 基于严重程度升级
    ACK_TIMEOUT = "ack_timeout"  # 确认超时升级


class SuppressionRuleType(str, Enum):
    """抑制规则类型"""
    DEPENDENCY = "dependency"  # 依赖服务告警抑制
    MAINTENANCE = "maintenance"  # 维护窗口抑制
    DUPLICATE = "duplicate"  # 重复告警抑制
    CASCADE = "cascade"  # 级联告警抑制
    CUSTOM = "custom"  # 自定义抑制


@dataclass
class DynamicBaseline:
    """动态基线配置"""
    metric_name: str
    service_name: Optional[str] = None
    window_hours: int = 24  # 历史数据窗口（小时）
    min_data_points: int = 100  # 最小数据点
    std_multiplier: float = 3.0  # 标准差倍数
    percentile_lower: float = 5.0  # 下百分位
    percentile_upper: float = 95.0  # 上百分位
    seasonal_periods: List[int] = field(default_factory=lambda: [24, 168])  # 季节性周期（小时）
    enabled: bool = True


@dataclass
class BaselineStats:
    """基线统计信息"""
    metric_name: str
    service_name: str
    mean: float
    std_dev: float
    median: float
    p5: float
    p95: float
    min_value: float
    max_value: float
    data_points: int
    seasonal_pattern: Optional[Dict[int, float]] = None  # 按小时的季节性模式
    last_updated: datetime = field(default_factory=datetime.utcnow)


@dataclass
class EscalationPolicy:
    """告警升级策略"""
    id: str
    name: str
    policy_type: EscalationPolicyType
    description: str = ""

    # 时间升级配置
    escalation_levels: List[Dict[str, Any]] = field(default_factory=list)
    # 格式：[{"delay_minutes": 15, "notify": ["user1"]}, {"delay_minutes": 30, "notify": ["manager1"]}]

    # 严重程度升级配置
    auto_escalate_severity: Optional[AlertSeverity] = None  # 自动升级到该严重程度

    # 确认超时配置
    ack_timeout_minutes: int = 30  # 确认超时时间

    # 通知接收者
    notify_users: List[str] = field(default_factory=list)
    notify_channels: List[str] = field(default_factory=list)

    enabled: bool = True
    tags: List[str] = field(default_factory=list)


@dataclass
class SuppressionRule:
    """告警抑制规则"""
    id: str
    name: str
    rule_type: SuppressionRuleType
    description: str = ""

    # 依赖抑制配置
    suppress_dependent_services: bool = False  # 抑制依赖服务告警
    source_services: List[str] = field(default_factory=list)  # 源服务列表

    # 维护窗口配置
    maintenance_start: Optional[datetime] = None
    maintenance_end: Optional[datetime] = None
    recurring_schedule: Optional[Dict[str, Any]] = None  # 重复计划

    # 重复告警抑制
    duplicate_window_seconds: int = 300  # 重复窗口
    duplicate_key_fields: List[str] = field(default_factory=list)

    # 级联抑制
    cascade_depth: int = 2  # 级联深度
    cascade_services: List[str] = field(default_factory=list)

    # 自定义条件
    condition: Optional[Dict[str, Any]] = None

    enabled: bool = True
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AlertAnalytics:
    """告警分析"""
    time_range_start: datetime
    time_range_end: datetime
    total_alerts: int
    alerts_by_severity: Dict[str, int]
    alerts_by_service: Dict[str, int]
    alerts_by_status: Dict[str, int]
    alerts_by_hour: Dict[int, int]  # 按小时统计
    avg_resolution_time_seconds: float
    avg_ack_time_seconds: float
    top_alert_rules: List[Dict[str, Any]]
    suppressed_count: int
    escalated_count: int
    noise_ratio: float  # 噪音告警比例
    mttr_minutes: float  # 平均恢复时间


class DynamicBaselineManager:
    """动态基线管理器"""

    def __init__(self, max_history_size: int = 10000):
        self._baselines: Dict[str, DynamicBaseline] = {}
        self._baseline_stats: Dict[str, BaselineStats] = {}
        self._metric_history: Dict[str, List[Tuple[datetime, float]]] = defaultdict(list)
        self._max_history_size = max_history_size

    def _get_key(self, service_name: Optional[str], metric_name: str) -> str:
        """生成基线键"""
        return f"{service_name or 'global'}:{metric_name}"

    def create_baseline(self, baseline: DynamicBaseline) -> str:
        """创建动态基线配置"""
        key = self._get_key(baseline.service_name, baseline.metric_name)
        self._baselines[key] = baseline
        logger.info(f"Dynamic baseline created: {key}")
        return key

    def get_baseline(self, service_name: Optional[str], metric_name: str) -> Optional[DynamicBaseline]:
        """获取动态基线配置"""
        key = self._get_key(service_name, metric_name)
        return self._baselines.get(key)

    def record_metric(self, service_name: Optional[str], metric_name: str,
                      value: float, timestamp: Optional[datetime] = None):
        """记录指标值用于基线计算"""
        if timestamp is None:
            timestamp = datetime.utcnow()

        key = self._get_key(service_name, metric_name)
        self._metric_history[key].append((timestamp, value))

        # 限制历史记录大小
        if len(self._metric_history[key]) > self._max_history_size:
            self._metric_history[key] = self._metric_history[key][-self._max_history_size:]

    def calculate_baseline(self, service_name: Optional[str], metric_name: str) -> Optional[BaselineStats]:
        """计算动态基线"""
        key = self._get_key(service_name, metric_name)
        baseline_config = self._baselines.get(key)

        if not baseline_config or not baseline_config.enabled:
            return None

        history = self._metric_history.get(key, [])
        if len(history) < baseline_config.min_data_points:
            return None

        # 过滤时间窗口内的数据
        cutoff_time = datetime.utcnow() - timedelta(hours=baseline_config.window_hours)
        filtered_data = [v for t, v in history if t >= cutoff_time]

        if len(filtered_data) < baseline_config.min_data_points:
            filtered_data = [v for _, v in history[-baseline_config.min_data_points:]]

        values = sorted(filtered_data)
        n = len(values)

        # 计算统计信息
        mean_val = statistics.mean(values)
        std_val = statistics.stdev(values) if n > 1 else 0.0
        median_val = statistics.median(values)

        # 计算百分位
        p5_idx = int(n * baseline_config.percentile_lower / 100)
        p95_idx = int(n * baseline_config.percentile_upper / 100)
        p5_val = values[p5_idx] if p5_idx < n else values[-1]
        p95_val = values[p95_idx] if p95_idx < n else values[-1]

        # 计算季节性模式（按小时）
        seasonal_pattern = self._calculate_seasonal_pattern(service_name, metric_name, baseline_config)

        stats = BaselineStats(
            metric_name=metric_name,
            service_name=service_name or "global",
            mean=mean_val,
            std_dev=std_val,
            median=median_val,
            p5=p5_val,
            p95=p95_val,
            min_value=min(values),
            max_value=max(values),
            data_points=n,
            seasonal_pattern=seasonal_pattern,
            last_updated=datetime.utcnow()
        )

        self._baseline_stats[key] = stats
        return stats

    def _calculate_seasonal_pattern(self, service_name: Optional[str],
                                     metric_name: str, baseline_config: DynamicBaseline) -> Optional[Dict[int, float]]:
        """计算季节性模式（按小时）"""
        key = self._get_key(service_name, metric_name)
        history = self._metric_history.get(key, [])

        if len(history) < baseline_config.min_data_points:
            return None

        # 按小时分组
        hourly_values: Dict[int, List[float]] = defaultdict(list)
        for timestamp, value in history:
            hour = timestamp.hour
            hourly_values[hour].append(value)

        # 计算每小时的均值
        seasonal_pattern = {}
        for hour, values in hourly_values.items():
            if len(values) >= 5:  # 至少 5 个数据点
                seasonal_pattern[hour] = statistics.mean(values)

        return seasonal_pattern if seasonal_pattern else None

    def get_dynamic_thresholds(self, service_name: Optional[str], metric_name: str,
                                current_value: float) -> Optional[Dict[str, Any]]:
        """获取动态阈值"""
        key = self._get_key(service_name, metric_name)

        # 先计算基线
        stats = self.calculate_baseline(service_name, metric_name)
        if not stats:
            return None

        baseline_config = self._baselines.get(key)
        if not baseline_config:
            return None

        # 获取当前小时的季节性期望值
        current_hour = datetime.utcnow().hour
        seasonal_expected = None
        if stats.seasonal_pattern and current_hour in stats.seasonal_pattern:
            seasonal_expected = stats.seasonal_pattern[current_hour]

        # 计算动态阈值
        upper_threshold = stats.mean + baseline_config.std_multiplier * stats.std_dev
        lower_threshold = stats.mean - baseline_config.std_multiplier * stats.std_dev

        # 判断是否异常
        z_score = (current_value - stats.mean) / stats.std_dev if stats.std_dev > 0 else 0
        is_anomaly = abs(z_score) > baseline_config.std_multiplier

        return {
            "upper_threshold": upper_threshold,
            "lower_threshold": lower_threshold,
            "baseline_mean": stats.mean,
            "baseline_std": stats.std_dev,
            "seasonal_expected": seasonal_expected,
            "z_score": z_score,
            "is_anomaly": is_anomaly,
            "deviation_percent": ((current_value - stats.mean) / stats.mean * 100) if stats.mean != 0 else 0
        }


class SuppressionEngine:
    """告警抑制引擎"""

    def __init__(self):
        self._rules: Dict[str, SuppressionRule] = {}
        self._suppressed_alerts: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._recent_alert_keys: Dict[str, datetime] = {}  # 用于重复检测

    def create_suppression_rule(self, rule: SuppressionRule) -> str:
        """创建抑制规则"""
        self._rules[rule.id] = rule
        logger.info(f"Suppression rule created: {rule.id} - {rule.name}")
        return rule.id

    def get_rule(self, rule_id: str) -> Optional[SuppressionRule]:
        """获取抑制规则"""
        return self._rules.get(rule_id)

    def list_rules(self, enabled_only: bool = True) -> List[SuppressionRule]:
        """列出抑制规则"""
        rules = list(self._rules.values())
        if enabled_only:
            rules = [r for r in rules if r.enabled]
        return rules

    def should_suppress(self, alert_data: Dict[str, Any],
                        service_dependencies: Optional[Dict[str, List[str]]] = None) -> Tuple[bool, Optional[str]]:
        """检查告警是否应该被抑制"""
        service_name = alert_data.get("service_name")

        for rule in self._rules.values():
            if not rule.enabled:
                continue

            should_suppress, reason = self._check_suppression_rule(rule, alert_data, service_dependencies)
            if should_suppress:
                return True, reason

        return False, None

    def _check_suppression_rule(self, rule: SuppressionRule, alert_data: Dict[str, Any],
                                 service_dependencies: Optional[Dict[str, List[str]]]) -> Tuple[bool, Optional[str]]:
        """检查单条抑制规则"""
        service_name = alert_data.get("service_name")

        # 维护窗口抑制
        if rule.rule_type == SuppressionRuleType.MAINTENANCE:
            now = datetime.utcnow()
            if rule.maintenance_start and rule.maintenance_end:
                if rule.maintenance_start <= now <= rule.maintenance_end:
                    return True, f"Maintenance window: {rule.name}"

            # 检查重复计划
            if rule.recurring_schedule:
                if self._check_recurring_schedule(rule.recurring_schedule, now):
                    return True, f"Recurring maintenance: {rule.name}"

        # 依赖服务抑制
        if rule.rule_type == SuppressionRuleType.DEPENDENCY:
            if rule.suppress_dependent_services and service_dependencies:
                for source_svc in rule.source_services:
                    if source_svc in service_dependencies:
                        dependents = service_dependencies.get(source_svc, [])
                        if service_name in dependents:
                            return True, f"Dependency suppression: {source_svc} is down"

        # 重复告警抑制
        if rule.rule_type == SuppressionRuleType.DUPLICATE:
            dup_key = self._build_duplicate_key(rule, alert_data)
            last_time = self._recent_alert_keys.get(dup_key)
            if last_time:
                elapsed = (datetime.utcnow() - last_time).total_seconds()
                if elapsed < rule.duplicate_window_seconds:
                    return True, f"Duplicate suppression (within {rule.duplicate_window_seconds}s)"

            # 记录本次告警
            self._recent_alert_keys[dup_key] = datetime.utcnow()

        # 级联告警抑制
        if rule.rule_type == SuppressionRuleType.CASCADE:
            if service_name in rule.cascade_services:
                # 检查上游服务是否有告警
                if self._has_upstream_alert(service_name, rule.cascade_depth):
                    return True, f"Cascade suppression: upstream service has alert"

        return False, None

    def _build_duplicate_key(self, rule: SuppressionRule, alert_data: Dict[str, Any]) -> str:
        """构建重复检测键"""
        key_parts = []
        for field_name in rule.duplicate_key_fields:
            value = alert_data.get(field_name, "unknown")
            key_parts.append(f"{field_name}:{value}")
        return "|".join(key_parts)

    def _check_recurring_schedule(self, schedule: Dict[str, Any], current_time: datetime) -> bool:
        """检查重复维护计划"""
        day_of_week = schedule.get("day_of_week")  # 0-6, 0=Monday
        start_hour = schedule.get("start_hour", 0)
        end_hour = schedule.get("end_hour", 24)

        current_day = current_time.weekday()
        current_hour = current_time.hour

        if day_of_week is not None and current_day != day_of_week:
            return False

        return start_hour <= current_hour < end_hour

    def _has_upstream_alert(self, service_name: str, depth: int) -> bool:
        """检查上游服务是否有告警（简化实现）"""
        # 实际实现应该查询告警系统
        return False

    def record_suppressed_alert(self, alert_id: str, reason: str, alert_data: Dict[str, Any]):
        """记录被抑制的告警"""
        self._suppressed_alerts[alert_id].append({
            "reason": reason,
            "data": alert_data,
            "timestamp": datetime.utcnow()
        })
        logger.debug(f"Alert suppressed: {alert_id} - {reason}")

    def get_suppression_stats(self) -> Dict[str, Any]:
        """获取抑制统计"""
        total_suppressed = sum(len(alerts) for alerts in self._suppressed_alerts.values())
        return {
            "total_rules": len(self._rules),
            "enabled_rules": len([r for r in self._rules.values() if r.enabled]),
            "total_suppressed_alerts": total_suppressed,
            "suppression_by_rule": self._count_suppressions_by_rule()
        }

    def _count_suppressions_by_rule(self) -> Dict[str, int]:
        """按规则统计抑制数"""
        # 简化实现
        return {}


class EscalationManager:
    """告警升级管理器"""

    def __init__(self, notification_handler: Optional[Callable] = None):
        self._policies: Dict[str, EscalationPolicy] = {}
        self._escalation_timers: Dict[str, asyncio.Task] = {}
        self._notification_handler = notification_handler
        self._escalated_alerts: List[Dict[str, Any]] = []

    def create_policy(self, policy: EscalationPolicy) -> str:
        """创建升级策略"""
        self._policies[policy.id] = policy
        logger.info(f"Escalation policy created: {policy.id} - {policy.name}")
        return policy.id

    def get_policy(self, policy_id: str) -> Optional[EscalationPolicy]:
        """获取升级策略"""
        return self._policies.get(policy_id)

    def list_policies(self, enabled_only: bool = True) -> List[EscalationPolicy]:
        """列出升级策略"""
        policies = list(self._policies.values())
        if enabled_only:
            policies = [p for p in policies if p.enabled]
        return policies

    async def start_escalation_timer(self, alert_id: str, policy: EscalationPolicy,
                                      alert_data: Dict[str, Any]):
        """启动告警升级计时器"""
        if alert_id in self._escalation_timers:
            return

        async def escalation_task():
            await asyncio.sleep(policy.ack_timeout_minutes * 60)
            await self._execute_escalation(alert_id, policy, alert_data)

        task = asyncio.create_task(escalation_task())
        self._escalation_timers[alert_id] = task

    def cancel_escalation_timer(self, alert_id: str):
        """取消升级计时器"""
        if alert_id in self._escalation_timers:
            self._escalation_timers[alert_id].cancel()
            del self._escalation_timers[alert_id]

    async def _execute_escalation(self, alert_id: str, policy: EscalationPolicy,
                                   alert_data: Dict[str, Any]):
        """执行升级"""
        logger.info(f"Executing escalation for alert {alert_id} with policy {policy.id}")

        # 记录升级事件
        self._escalated_alerts.append({
            "alert_id": alert_id,
            "policy_id": policy.id,
            "escalated_at": datetime.utcnow(),
            "alert_data": alert_data
        })

        # 发送升级通知
        if self._notification_handler:
            for user in policy.notify_users:
                await self._notification_handler(user, alert_id, policy)

        # 如果配置了自动升级严重程度
        # 这需要告警引擎的配合

    def get_escalation_stats(self) -> Dict[str, Any]:
        """获取升级统计"""
        return {
            "total_policies": len(self._policies),
            "enabled_policies": len([p for p in self._policies.values() if p.enabled]),
            "total_escalations": len(self._escalated_alerts),
            "active_timers": len(self._escalation_timers)
        }


class AlertAnalyticsEngine:
    """告警分析引擎"""

    def __init__(self):
        self._alert_records: List[Dict[str, Any]] = []
        self._max_records = 100000

    def record_alert(self, alert_data: Dict[str, Any]):
        """记录告警数据用于分析"""
        self._alert_records.append({
            **alert_data,
            "recorded_at": datetime.utcnow()
        })

        # 限制记录数量
        if len(self._alert_records) > self._max_records:
            self._alert_records = self._alert_records[-self._max_records:]

    def analyze(self, time_range_start: Optional[datetime] = None,
                time_range_end: Optional[datetime] = None) -> AlertAnalytics:
        """执行告警分析"""
        if time_range_start is None:
            time_range_start = datetime.utcnow() - timedelta(days=7)
        if time_range_end is None:
            time_range_end = datetime.utcnow()

        # 过滤时间范围内的数据
        filtered = [
            r for r in self._alert_records
            if time_range_start <= r.get("triggered_at", datetime.utcnow()) <= time_range_end
        ]

        # 按严重程度统计
        by_severity = defaultdict(int)
        for r in filtered:
            severity = r.get("severity", "unknown")
            by_severity[str(severity)] += 1

        # 按服务统计
        by_service = defaultdict(int)
        for r in filtered:
            service = r.get("service_name", "unknown")
            by_service[service] += 1

        # 按状态统计
        by_status = defaultdict(int)
        for r in filtered:
            status = r.get("status", "unknown")
            by_status[str(status)] += 1

        # 按小时统计
        by_hour = defaultdict(int)
        for r in filtered:
            hour = r.get("triggered_at", datetime.utcnow()).hour
            by_hour[hour] += 1

        # 计算平均解决时间
        resolution_times = []
        ack_times = []
        for r in filtered:
            if r.get("resolved_at") and r.get("triggered_at"):
                delta = (r["resolved_at"] - r["triggered_at"]).total_seconds()
                resolution_times.append(delta)
            if r.get("acknowledged_at") and r.get("triggered_at"):
                delta = (r["acknowledged_at"] - r["triggered_at"]).total_seconds()
                ack_times.append(delta)

        avg_resolution = statistics.mean(resolution_times) if resolution_times else 0
        avg_ack = statistics.mean(ack_times) if ack_times else 0
        mttr = avg_resolution / 60 if avg_resolution else 0

        # Top 告警规则
        rule_counts = defaultdict(int)
        for r in filtered:
            rule_id = r.get("rule_id", "unknown")
            rule_name = r.get("rule_name", "Unknown")
            rule_counts[(rule_id, rule_name)] += 1

        top_rules = sorted(
            [{"rule_id": k[0], "rule_name": k[1], "count": v} for k, v in rule_counts.items()],
            key=lambda x: x["count"],
            reverse=True
        )[:10]

        return AlertAnalytics(
            time_range_start=time_range_start,
            time_range_end=time_range_end,
            total_alerts=len(filtered),
            alerts_by_severity=dict(by_severity),
            alerts_by_service=dict(by_service),
            alerts_by_status=dict(by_status),
            alerts_by_hour=dict(by_hour),
            avg_resolution_time_seconds=avg_resolution,
            avg_ack_time_seconds=avg_ack,
            top_alert_rules=top_rules,
            suppressed_count=0,
            escalated_count=0,
            noise_ratio=0.0,
            mttr_minutes=mttr
        )

    def get_recent_alerts(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取最近告警记录"""
        return sorted(
            self._alert_records,
            key=lambda x: x.get("triggered_at", datetime.utcnow()),
            reverse=True
        )[:limit]


# 全局实例
dynamic_baseline_manager = DynamicBaselineManager()
suppression_engine = SuppressionEngine()
escalation_manager = EscalationManager()
analytics_engine = AlertAnalyticsEngine()


def create_default_suppression_rules():
    """创建默认抑制规则"""
    # 级联告警抑制
    suppression_engine.create_suppression_rule(SuppressionRule(
        id="cascade-infra-alerts",
        name="基础设施告警级联抑制",
        rule_type=SuppressionRuleType.CASCADE,
        description="当基础设施服务告警时，抑制依赖服务的告警",
        cascade_depth=2,
        cascade_services=["database", "cache", "message-queue"],
        enabled=True
    ))

    # 重复告警抑制
    suppression_engine.create_suppression_rule(SuppressionRule(
        id="duplicate-rate-limit",
        name="重复告警速率限制",
        rule_type=SuppressionRuleType.DUPLICATE,
        description="5 分钟内相同告警只发送一次",
        duplicate_window_seconds=300,
        duplicate_key_fields=["rule_id", "service_name"],
        enabled=True
    ))


def create_default_escalation_policies():
    """创建默认升级策略"""
    # 标准升级策略
    escalation_manager.create_policy(EscalationPolicy(
        id="standard-escalation",
        name="标准升级策略",
        policy_type=EscalationPolicyType.ACK_TIMEOUT,
        description="30 分钟未确认则升级",
        ack_timeout_minutes=30,
        notify_users=["oncall-primary"],
        notify_channels=["pagerduty", "slack"],
        enabled=True
    ))

    # 紧急升级策略
    escalation_manager.create_policy(EscalationPolicy(
        id="critical-escalation",
        name="紧急升级策略",
        policy_type=EscalationPolicyType.ACK_TIMEOUT,
        description="15 分钟未确认则升级到经理",
        ack_timeout_minutes=15,
        escalation_levels=[
            {"delay_minutes": 15, "notify": ["oncall-primary"]},
            {"delay_minutes": 30, "notify": ["oncall-secondary", "manager"]}
        ],
        notify_users=["oncall-primary", "oncall-secondary"],
        notify_channels=["pagerduty", "phone"],
        enabled=True,
        tags=["critical"]
    ))


# 初始化默认规则
create_default_suppression_rules()
create_default_escalation_policies()
