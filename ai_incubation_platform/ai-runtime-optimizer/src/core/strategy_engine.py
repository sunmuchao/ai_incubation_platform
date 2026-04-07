"""
策略引擎：可配置的规则与 LLM 混合策略框架
支持动态加载、优先级排序、条件匹配的分析策略
"""
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
import uuid
import time
from dataclasses import dataclass, field

from core.audit import audit_logger, AuditEventType, AuditStatus


class StrategyType(str, Enum):
    METRICS = "metrics"
    USAGE = "usage"
    HOLISTIC = "holistic"
    CODE_GENERATION = "code_generation"


class StrategyPriority(int, Enum):
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3
    INFO = 4


@dataclass
class StrategyCondition:
    """策略触发条件"""
    field: str  # 检查字段路径，支持点号嵌套
    operator: str  # gt, lt, eq, ne, contains, matches
    value: Any  # 比较值
    negate: bool = False  # 是否取反


@dataclass
class StrategyAction:
    """策略执行动作"""
    suggestion_type: str
    message_template: str  # 支持 {field} 模板变量
    confidence: float
    priority: StrategyPriority = StrategyPriority.MEDIUM
    evidence_fields: List[str] = field(default_factory=list)  # 需要包含的证据字段
    metadata: Dict[str, Any] = field(default_factory=dict)  # 额外元数据


@dataclass
class CodeGenerationRule:
    """代码生成规则映射"""
    suggestion_type: str  # 关联的建议类型
    patch_id: str
    title_template: str
    rationale_template: str
    risk_level: str  # low, medium, high
    file_guess_template: str
    code_template: str  # 支持模板变量
    language: str = "python"
    implementation_kind: str = "snippet"


@dataclass
class CodeRuleEntry:
    """代码规则的来源信息（用于按策略类型/ID 过滤 code_rules）"""

    parent_strategy_id: str
    parent_strategy_type: StrategyType
    rule: CodeGenerationRule


@dataclass
class AnalysisStrategy:
    """分析策略定义"""
    id: str
    name: str
    description: str
    type: StrategyType
    enabled: bool = True
    conditions: List[StrategyCondition] = field(default_factory=list)
    actions: List[StrategyAction] = field(default_factory=list)
    code_rules: List[CodeGenerationRule] = field(default_factory=list)
    priority: StrategyPriority = StrategyPriority.MEDIUM
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class StrategyEngine:
    def __init__(self):
        self._strategies: Dict[str, AnalysisStrategy] = {}
        self._code_rules: Dict[str, List[CodeRuleEntry]] = {}
        self._load_default_strategies()

    def _load_default_strategies(self):
        """加载默认内置策略"""
        # 高错误率策略
        self.add_strategy(AnalysisStrategy(
            id="built-in-high-error-rate",
            name="高错误率检测",
            description="错误率超过阈值时触发告警",
            type=StrategyType.METRICS,
            conditions=[
                StrategyCondition(
                    field="error_rate",
                    operator="gt",
                    value=0.01
                )
            ],
            actions=[
                StrategyAction(
                    suggestion_type="reliability",
                    message_template="排查错误率升高来源（日志/trace），检查依赖超时与重试策略",
                    confidence=0.7,
                    evidence_fields=["error_rate"]
                )
            ],
            code_rules=[
                CodeGenerationRule(
                    suggestion_type="reliability",
                    patch_id="patch-reliability-error-handling",
                    title_template="优化错误处理与重试策略",
                    rationale_template="错误率过高，需完善错误捕获与降级机制",
                    risk_level="medium",
                    file_guess_template="src/utils/error_handlers.py",
                    code_template=(
                        "# 示例：添加重试机制与降级策略\n"
                        "from tenacity import retry, stop_after_attempt, wait_exponential\n"
                        "\n"
                        "@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))\n"
                        "async def call_external_service(...):\n"
                        "    try:\n"
                        "        return await client.request(...)\n"
                        "    except Exception as e:\n"
                        "        logger.error(f\"External service failed: {e}\")\n"
                        "        return get_fallback_response()\n"
                    )
                )
            ],
            priority=StrategyPriority.CRITICAL,
            tags=["reliability", "metrics"]
        ))

        # 高 P99 延迟策略
        self.add_strategy(AnalysisStrategy(
            id="built-in-high-latency",
            name="高延迟检测",
            description="P99 延迟超过阈值时触发优化建议",
            type=StrategyType.METRICS,
            conditions=[
                StrategyCondition(
                    field="latency_p99_ms",
                    operator="gt",
                    value=500
                )
            ],
            actions=[
                StrategyAction(
                    suggestion_type="latency",
                    message_template="检查慢查询与外部 IO；评估缓存与连接池参数",
                    confidence=0.65,
                    evidence_fields=["latency_p99_ms"]
                )
            ],
            code_rules=[
                CodeGenerationRule(
                    suggestion_type="latency",
                    patch_id="patch-pool-timeout",
                    title_template="收紧外部调用超时与连接池配置",
                    rationale_template="P99 延迟过高，需优化连接池参数与超时设置",
                    risk_level="low",
                    file_guess_template="src/config.py",
                    code_template=(
                        "# 示例：优化连接池与超时配置\n"
                        "HTTP_CLIENT_TIMEOUT_S = 8\n"
                        "DB_POOL_SIZE = 20\n"
                        "DB_QUERY_TIMEOUT_S = 10\n"
                    )
                )
            ],
            priority=StrategyPriority.HIGH,
            tags=["performance", "metrics"]
        ))

        # 高 CPU 使用率策略
        self.add_strategy(AnalysisStrategy(
            id="built-in-high-cpu",
            name="高 CPU 使用率检测",
            description="CPU 使用率超过阈值时触发扩容或优化建议",
            type=StrategyType.METRICS,
            conditions=[
                StrategyCondition(
                    field="cpu_percent",
                    operator="gt",
                    value=85
                )
            ],
            actions=[
                StrategyAction(
                    suggestion_type="capacity",
                    message_template="评估水平扩容或热点代码优化（Profiling）",
                    confidence=0.6,
                    evidence_fields=["cpu_percent"]
                )
            ],
            code_rules=[
                CodeGenerationRule(
                    suggestion_type="capacity",
                    patch_id="patch-cpu-optimization",
                    title_template="热点代码性能优化建议",
                    rationale_template="CPU 使用率过高，建议优化热点路径或水平扩容",
                    risk_level="high",
                    file_guess_template="src/services/",
                    code_template=(
                        "# 示例：热点代码优化方向\n"
                        "# 1. 考虑将计算密集型操作异步化\n"
                        "# 2. 优化算法复杂度\n"
                        "# 3. 增加缓存层减少重复计算\n"
                        "# 4. 水平扩容实例数量\n"
                    )
                )
            ],
            priority=StrategyPriority.HIGH,
            tags=["capacity", "metrics"]
        ))

        # 热点路由高延迟策略
        self.add_strategy(AnalysisStrategy(
            id="built-in-hot-route-latency",
            name="热点路由高延迟检测",
            description="高流量路由延迟过高时触发缓存/优化建议",
            type=StrategyType.USAGE,
            conditions=[
                StrategyCondition(
                    field="requests",
                    operator="gt",
                    value=500
                ),
                StrategyCondition(
                    field="p99_ms",
                    operator="gt",
                    value=700
                )
            ],
            actions=[
                StrategyAction(
                    suggestion_type="usage_hotspot_latency",
                    message_template="路由 {path} 流量大且 P99 偏高，优先考虑缓存、异步化或读副本",
                    confidence=0.72,
                    evidence_fields=["path", "requests", "p99_ms"]
                )
            ],
            code_rules=[
                CodeGenerationRule(
                    suggestion_type="usage_hotspot_latency",
                    patch_id="patch-cache-hot-route",
                    title_template="为热点路由 {path} 增加短期缓存",
                    rationale_template="路由 {path} 流量大且延迟高，建议添加缓存层",
                    risk_level="medium",
                    file_guess_template="src/api/routes.py",
                    code_template=(
                        "# 示例：为热点路由添加缓存\n"
                        "from fastapi_cache.decorator import cache\n"
                        "\n"
                        "@cache(expire=60)\n"
                        "@router.get(\"{path}\")\n"
                        "async def get_hot_data(...):\n"
                        "    # 业务逻辑\n"
                        "    ...\n"
                    )
                )
            ],
            priority=StrategyPriority.HIGH,
            tags=["performance", "usage", "routing"]
        ))

        # 路由错误率过高策略
        self.add_strategy(AnalysisStrategy(
            id="built-in-route-high-error",
            name="路由高错误率检测",
            description="特定路由错误率过高时触发排查建议",
            type=StrategyType.USAGE,
            conditions=[
                StrategyCondition(
                    field="error_rate",
                    operator="gt",
                    value=0.02
                )
            ],
            actions=[
                StrategyAction(
                    suggestion_type="usage_error_correlation",
                    message_template="路由 {path} 错误率偏高，结合 trace 查下游与输入校验",
                    confidence=0.68,
                    evidence_fields=["path", "error_rate"]
                )
            ],
            code_rules=[
                CodeGenerationRule(
                    suggestion_type="usage_error_correlation",
                    patch_id="patch-route-validation",
                    title_template="增强路由 {path} 的输入校验与错误处理",
                    rationale_template="路由 {path} 错误率过高，建议增强输入校验",
                    risk_level="low",
                    file_guess_template="src/api/routes.py",
                    code_template=(
                        "# 示例：增强输入校验\n"
                        "from pydantic import ValidationError\n"
                        "\n"
                        "@router.post(\"{path}\")\n"
                        "async def handle_route(request: Request):\n"
                        "    try:\n"
                        "        data = await request.json()\n"
                        "        validated = RequestModel(**data)\n"
                        "    except ValidationError as e:\n"
                        "        return JSONResponse(status_code=400, content={\"error\": str(e)})\n"
                        "    ...\n"
                    )
                )
            ],
            priority=StrategyPriority.HIGH,
            tags=["reliability", "usage", "routing"]
        ))

        # 低功能采纳率策略
        self.add_strategy(AnalysisStrategy(
            id="built-in-low-feature-adoption",
            name="低功能采纳率检测",
            description="功能使用率过低时提示评估是否下线",
            type=StrategyType.USAGE,
            conditions=[
                StrategyCondition(
                    field="adoption_ratio",
                    operator="lt",
                    value=0.03
                )
            ],
            actions=[
                StrategyAction(
                    suggestion_type="usage_low_adoption",
                    message_template="功能「{feature}」使用率极低：检查入口曝光、引导或考虑合并/下线",
                    confidence=0.55,
                    evidence_fields=["feature", "adoption_ratio"]
                )
            ],
            code_rules=[
                CodeGenerationRule(
                    suggestion_type="usage_low_adoption",
                    patch_id="patch-feature-flag-off",
                    title_template="低采纳功能 {feature} 默认关闭或合并入口",
                    rationale_template="功能 {feature} 使用率过低，建议默认关闭减少维护成本",
                    risk_level="medium",
                    file_guess_template="src/features/flags.py",
                    code_template=(
                        "# 示例：功能开关默认关闭\n"
                        "FEATURE_{feature_upper}_ENABLED = False\n"
                    )
                )
            ],
            priority=StrategyPriority.LOW,
            tags=["product", "usage", "feature"]
        ))

    def add_strategy(self, strategy: AnalysisStrategy) -> str:
        """添加策略"""
        if strategy.id in self._strategies:
            raise ValueError(f"Strategy ID {strategy.id} already exists")
        self._strategies[strategy.id] = strategy

        # 索引代码规则
        for rule in strategy.code_rules:
            if rule.suggestion_type not in self._code_rules:
                self._code_rules[rule.suggestion_type] = []
            self._code_rules[rule.suggestion_type].append(
                CodeRuleEntry(
                    parent_strategy_id=strategy.id,
                    parent_strategy_type=strategy.type,
                    rule=rule,
                )
            )

        return strategy.id

    def remove_strategy(self, strategy_id: str) -> bool:
        """移除策略"""
        if strategy_id in self._strategies:
            del self._strategies[strategy_id]
            # 清理对应的代码规则索引（简单实现，实际可优化）
            self._rebuild_code_rules_index()
            return True
        return False

    def _rebuild_code_rules_index(self):
        """重建代码规则索引"""
        self._code_rules.clear()
        for strategy in self._strategies.values():
            for rule in strategy.code_rules:
                if rule.suggestion_type not in self._code_rules:
                    self._code_rules[rule.suggestion_type] = []
                self._code_rules[rule.suggestion_type].append(
                    CodeRuleEntry(
                        parent_strategy_id=strategy.id,
                        parent_strategy_type=strategy.type,
                        rule=rule,
                    )
                )

    def get_strategy(self, strategy_id: str) -> Optional[AnalysisStrategy]:
        """获取策略"""
        return self._strategies.get(strategy_id)

    def list_strategies(self, type_filter: Optional[StrategyType] = None,
                       enabled_only: bool = True) -> List[AnalysisStrategy]:
        """列出策略"""
        strategies = list(self._strategies.values())
        if enabled_only:
            strategies = [s for s in strategies if s.enabled]
        if type_filter:
            strategies = [s for s in strategies if s.type == type_filter]
        return sorted(strategies, key=lambda s: s.priority)

    def _get_nested_value(self, data: Dict[str, Any], field_path: str) -> Any:
        """获取嵌套字段值"""
        current = data
        for part in field_path.split('.'):
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current

    def _evaluate_condition(self, data: Dict[str, Any], condition: StrategyCondition) -> bool:
        """评估单个条件"""
        value = self._get_nested_value(data, condition.field)
        if value is None:
            return False

        op = condition.operator
        target = condition.value

        try:
            if op == "gt":
                result = value > target
            elif op == "lt":
                result = value < target
            elif op == "eq":
                result = value == target
            elif op == "ne":
                result = value != target
            elif op == "contains":
                result = target in value if isinstance(value, (list, str, dict)) else False
            elif op == "matches":
                import re
                result = bool(re.match(target, str(value)))
            else:
                result = False
        except (TypeError, ValueError):
            result = False

        return not result if condition.negate else result

    def _match_strategy(self, data: Dict[str, Any], strategy: AnalysisStrategy) -> bool:
        """检查数据是否匹配策略的所有条件"""
        if not strategy.enabled:
            return False
        return all(self._evaluate_condition(data, cond) for cond in strategy.conditions)

    def _render_template(self, template: str, context: Dict[str, Any]) -> str:
        """渲染模板字符串"""
        try:
            return template.format(**context)
        except KeyError as e:
            # 缺失字段时返回原始模板
            return template

    def execute_metrics_strategies(
        self,
        snapshot: Dict[str, Any],
        trace_id: Optional[str] = None,
        strategy_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """执行所有指标类策略（可按请求 trace_id/strategy_ids 过滤）"""
        start_time = time.time()
        results: List[Dict[str, Any]] = []
        strategies = self.list_strategies(type_filter=StrategyType.METRICS)
        if strategy_ids:
            id_set = set(strategy_ids)
            strategies = [s for s in strategies if s.id in id_set]

        executed_strategy_ids = []
        for strategy in strategies:
            if self._match_strategy(snapshot, strategy):
                executed_strategy_ids.append(strategy.id)
                for action in strategy.actions:
                    context = {**snapshot}
                    evidence = {field: self._get_nested_value(snapshot, field)
                              for field in action.evidence_fields}

                    id_parts = ["suggestion"]
                    if trace_id:
                        id_parts.append(trace_id)
                    id_parts.append(uuid.uuid4().hex[:8])
                    suggestion = {
                        "id": "-".join(id_parts),
                        "trace_id": trace_id,
                        "strategy_id": strategy.id,
                        "type": action.suggestion_type,
                        "action": self._render_template(action.message_template, context),
                        "confidence": action.confidence,
                        "priority": action.priority.name.lower(),
                        "evidence": evidence,
                        "tags": strategy.tags
                    }
                    results.append(suggestion)

        duration_ms = (time.time() - start_time) * 1000

        # 审计日志：策略执行
        for sid in executed_strategy_ids:
            audit_logger.log_strategy_execute(
                strategy_id=sid,
                strategy_type=StrategyType.METRICS.value,
                input_data={"snapshot_keys": list(snapshot.keys())},
                suggestions_count=len([r for r in results if r.get("strategy_id") == sid]),
                trace_id=trace_id,
                service_name=snapshot.get("service_name"),
                duration_ms=duration_ms / max(len(executed_strategy_ids), 1),
                status=AuditStatus.SUCCESS
            )

        return sorted(results, key=lambda x: StrategyPriority[x["priority"].upper()])

    def execute_usage_strategies(
        self,
        usage: Dict[str, Any],
        trace_id: Optional[str] = None,
        strategy_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """执行所有使用情况类策略（可按请求 trace_id/strategy_ids 过滤）"""
        start_time = time.time()
        results: List[Dict[str, Any]] = []
        strategies = self.list_strategies(type_filter=StrategyType.USAGE)
        if strategy_ids:
            id_set = set(strategy_ids)
            strategies = [s for s in strategies if s.id in id_set]

        executed_strategy_ids = []

        # 处理路由列表
        top_routes = usage.get("top_routes") or []
        for route in top_routes:
            route_context = {**route, **usage}
            for strategy in strategies:
                if self._match_strategy(route_context, strategy):
                    if strategy.id not in executed_strategy_ids:
                        executed_strategy_ids.append(strategy.id)
                    for action in strategy.actions:
                        context = {**route_context, "path": route.get("path", "")}
                        evidence = {field: self._get_nested_value(context, field)
                                  for field in action.evidence_fields}

                        id_parts = ["suggestion"]
                        if trace_id:
                            id_parts.append(trace_id)
                        id_parts.append(uuid.uuid4().hex[:8])
                        suggestion = {
                            "id": "-".join(id_parts),
                            "trace_id": trace_id,
                            "strategy_id": strategy.id,
                            "type": action.suggestion_type,
                            "action": self._render_template(action.message_template, context),
                            "confidence": action.confidence,
                            "priority": action.priority.name.lower(),
                            "evidence": evidence,
                            "tags": strategy.tags
                        }
                        results.append(suggestion)

        # 处理功能采纳率
        feature_adoption = usage.get("feature_adoption") or {}
        for feature, ratio in feature_adoption.items():
            feature_context = {"feature": feature, "adoption_ratio": ratio, **usage}
            for strategy in strategies:
                if self._match_strategy(feature_context, strategy):
                    if strategy.id not in executed_strategy_ids:
                        executed_strategy_ids.append(strategy.id)
                    for action in strategy.actions:
                        context = {**feature_context}
                        evidence = {field: self._get_nested_value(context, field)
                                  for field in action.evidence_fields}

                        id_parts = ["suggestion"]
                        if trace_id:
                            id_parts.append(trace_id)
                        id_parts.append(uuid.uuid4().hex[:8])
                        suggestion = {
                            "id": "-".join(id_parts),
                            "trace_id": trace_id,
                            "strategy_id": strategy.id,
                            "type": action.suggestion_type,
                            "action": self._render_template(action.message_template, context),
                            "confidence": action.confidence,
                            "priority": action.priority.name.lower(),
                            "evidence": evidence,
                            "tags": strategy.tags
                        }
                        results.append(suggestion)

        duration_ms = (time.time() - start_time) * 1000

        # 审计日志：策略执行
        for sid in executed_strategy_ids:
            audit_logger.log_strategy_execute(
                strategy_id=sid,
                strategy_type=StrategyType.USAGE.value,
                input_data={"usage_keys": list(usage.keys())},
                suggestions_count=len([r for r in results if r.get("strategy_id") == sid]),
                trace_id=trace_id,
                service_name=usage.get("service_name"),
                duration_ms=duration_ms / max(len(executed_strategy_ids), 1),
                status=AuditStatus.SUCCESS
            )

        return sorted(results, key=lambda x: StrategyPriority[x["priority"].upper()])

    def execute_holistic_strategies(
        self,
        snapshot: Dict[str, Any],
        usage: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
        strategy_ids: Optional[List[str]] = None,
        analysis_strategy_types: Optional[List[StrategyType]] = None,
    ) -> List[Dict[str, Any]]:
        """执行综合分析策略（可按请求选择策略类型/策略 ID；规则引擎优先）"""

        # 默认行为：仅执行 METRICS +（若有 usage 则执行）USAGE；不默认执行 HOLISTIC（避免影响一致性测试）
        if analysis_strategy_types is None:
            types = {StrategyType.METRICS}
            if usage:
                types.add(StrategyType.USAGE)
        else:
            types = set(analysis_strategy_types)

        results: List[Dict[str, Any]] = []

        if StrategyType.METRICS in types:
            results.extend(
                self.execute_metrics_strategies(
                    snapshot,
                    trace_id=trace_id,
                    strategy_ids=strategy_ids,
                )
            )

        if StrategyType.USAGE in types and usage:
            results.extend(
                self.execute_usage_strategies(
                    usage,
                    trace_id=trace_id,
                    strategy_ids=strategy_ids,
                )
            )

        if StrategyType.HOLISTIC in types:
            results.extend(
                self.execute_holistic_type_strategies(
                    snapshot,
                    usage=usage,
                    trace_id=trace_id,
                    strategy_ids=strategy_ids,
                )
            )

        return sorted(results, key=lambda x: StrategyPriority[x["priority"].upper()])

    def execute_holistic_type_strategies(
        self,
        snapshot: Dict[str, Any],
        usage: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
        strategy_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """执行 HOLISTIC 类型策略（跨维度条件：在 merged_data 上匹配）"""

        results: List[Dict[str, Any]] = []
        strategies = self.list_strategies(type_filter=StrategyType.HOLISTIC)
        if strategy_ids:
            id_set = set(strategy_ids)
            strategies = [s for s in strategies if s.id in id_set]

        merged_data = {**snapshot, "usage": usage or {}}
        if usage:
            merged_data.update(usage)

        for strategy in strategies:
            if not self._match_strategy(merged_data, strategy):
                continue
            for action in strategy.actions:
                evidence = {
                    field: self._get_nested_value(merged_data, field)
                    for field in action.evidence_fields
                }

                id_parts = ["suggestion"]
                if trace_id:
                    id_parts.append(trace_id)
                id_parts.append(uuid.uuid4().hex[:8])

                results.append(
                    {
                        "id": "-".join(id_parts),
                        "trace_id": trace_id,
                        "strategy_id": strategy.id,
                        "type": action.suggestion_type,
                        "action": self._render_template(action.message_template, merged_data),
                        "confidence": action.confidence,
                        "priority": action.priority.name.lower(),
                        "evidence": evidence,
                        "tags": strategy.tags,
                    }
                )

        return sorted(results, key=lambda x: StrategyPriority[x["priority"].upper()])

    def generate_code_proposals(
        self,
        suggestions: List[Dict[str, Any]],
        context: Dict[str, Any],
        trace_id: Optional[str] = None,
        code_strategy_types: Optional[List[StrategyType]] = None,
        strategy_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """根据建议生成代码提案（规则引擎 + 请求级策略筛选，可选 LLM 增强在 service 层完成）"""
        start_time = time.time()
        patches: List[Dict[str, Any]] = []
        code_type_set = set(code_strategy_types) if code_strategy_types else None
        strategy_id_set = set(strategy_ids) if strategy_ids else None
        generated_patch_ids = []

        for suggestion in suggestions:
            suggestion_type = suggestion.get("type")
            suggestion_id = suggestion.get("id")
            suggestion_strategy_id = suggestion.get("strategy_id")

            if not suggestion_type:
                continue

            entries = self._code_rules.get(suggestion_type, [])
            matched_entries: List[CodeRuleEntry] = []
            for entry in entries:
                if code_type_set is not None and entry.parent_strategy_type not in code_type_set:
                    continue
                if strategy_id_set is not None and entry.parent_strategy_id not in strategy_id_set:
                    continue
                matched_entries.append(entry)

            if not matched_entries:
                # 即使没匹配到代码规则，也需要生成可追踪的"信息类补丁"，便于后续接 LLM/diff
                suffix = f"-{trace_id}" if trace_id else ""
                patch_id = f"patch-no-op{suffix}-{uuid.uuid4().hex[:8]}"
                patches.append(
                    {
                        "id": patch_id,
                        "suggestion_id": suggestion_id,
                        "strategy_id": suggestion_strategy_id,
                        "trace_id": trace_id,
                        "title": "暂无自动匹配补丁类型",
                        "rationale": "请接入 LLM + 仓库索引，根据建议生成真实 diff",
                        "risk": "none",
                        "file_guess": None,
                        "language": context.get("language", "python"),
                        "implementation_kind": "documentation",
                        "code": "# 无占位代码；请使用 holistic-analyze 结果驱动生成。\n",
                        "type": "info",
                    }
                )
                generated_patch_ids.append(patch_id)
                continue

            for entry in matched_entries:
                rule = entry.rule

                # 构建模板上下文
                template_context = {
                    **context,
                    **suggestion.get("evidence", {}),
                    "suggestion": suggestion,
                }

                # 特殊处理功能名大写
                if "feature" in template_context:
                    template_context["feature_upper"] = template_context["feature"].upper()

                # 渲染模板
                id_parts = [rule.patch_id]
                if trace_id:
                    id_parts.append(trace_id)
                id_parts.append(uuid.uuid4().hex[:8])
                patch_id = "-".join(id_parts)

                title = self._render_template(rule.title_template, template_context)
                rationale = self._render_template(rule.rationale_template, template_context)
                file_guess = self._render_template(rule.file_guess_template, template_context)
                code = self._render_template(rule.code_template, template_context)

                patches.append(
                    {
                        "id": patch_id,
                        "suggestion_id": suggestion_id,
                        "strategy_id": suggestion_strategy_id,
                        "trace_id": trace_id,
                        "title": title,
                        "rationale": rationale,
                        "risk": rule.risk_level,
                        "file_guess": file_guess,
                        "language": rule.language,
                        "implementation_kind": rule.implementation_kind,
                        "code": code,
                        "type": suggestion_type,
                    }
                )
                generated_patch_ids.append(patch_id)

        duration_ms = (time.time() - start_time) * 1000

        # 审计日志：代码生成
        for patch_id in generated_patch_ids[:5]:  # 限制日志数量，避免过多
            audit_logger.log_code_generate(
                patch_id=patch_id,
                suggestion_id=next((s.get("id") for s in suggestions if s.get("type") == patch_id.split("-")[0]), ""),
                language=context.get("language", "python"),
                trace_id=trace_id,
                service_name=context.get("snapshot", {}).get("service_name"),
                duration_ms=duration_ms / max(len(generated_patch_ids), 1),
                status=AuditStatus.SUCCESS
            )

        return patches


# 全局策略引擎实例
strategy_engine = StrategyEngine()
