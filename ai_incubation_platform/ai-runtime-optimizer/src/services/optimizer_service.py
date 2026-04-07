"""
运行态优化业务层：基于可配置策略引擎的综合分析与代码提案
生产环境可对接：时序库、埋点/分析平台、LLM 生成补丁、安全评审与自动 PR。
"""
from typing import Any, Dict, List, Optional
from dataclasses import asdict, is_dataclass
from enum import Enum

from core import strategy_engine, storage, llm_integration, config
from models.analysis import AnalysisResult, CodeProposalsResult, Suggestion, CodePatch
from models.strategy import RuntimeStrategyExecutionPlan


class OptimizerService:
    def record_metrics(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """记录指标快照"""
        service_name = payload.get("service_name")
        if service_name:
            storage.record_metrics(service_name, payload)
        return {
            "status": "recorded",
            "service": service_name,
            "id": f"metrics-{id(payload)}"
        }

    def record_usage(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """记录用户使用情况聚合"""
        service_name = payload.get("service_name")
        if service_name:
            storage.record_usage(service_name, payload)
        return {
            "status": "recorded",
            "service": service_name,
            "id": f"usage-{id(payload)}"
        }

    def analyze(
        self, snapshot: Dict[str, Any], config_hint: Optional[str]
    ) -> Dict[str, Any]:
        """仅根据指标与配置生成建议（不含行为数据）。"""
        # 执行策略引擎的指标分析
        suggestion_dicts = strategy_engine.execute_metrics_strategies(snapshot)
        suggestions = [Suggestion(**s) for s in suggestion_dicts]

        # LLM增强分析（可选）
        llm_analysis = None
        if llm_integration.enabled:
            llm_analysis = llm_integration.enhance_analysis(
                snapshot=snapshot,
                suggestions=suggestion_dicts
            )

        # 构建分析结果
        result = AnalysisResult(
            service=snapshot.get("service_name", "unknown"),
            config_hint=config_hint,
            suggestions=suggestions,
            usage_informed=False,
            note="仅指标维度；完整分析请使用 /holistic-analyze 并带上用户使用数据。",
        )

        # 端到端追踪：把 analysis_id 填回每个建议项
        for s in suggestions:
            s.analysis_id = result.id

        # 保存结果
        storage.save_analysis_result(result)

        # 构建响应
        response = result.model_dump()
        if llm_analysis:
            response["llm_analysis"] = llm_analysis

        return response

    def holistic_analyze(
        self,
        snapshot: Dict[str, Any],
        config_hint: Optional[str],
        usage: Optional[Dict[str, Any]],
        strategy_plan: Optional[RuntimeStrategyExecutionPlan] = None,
    ) -> Dict[str, Any]:
        """
        综合分析：CPU/内存/延迟/错误率 与 用户使用情况一起推理，
        例如：热点路由慢、低采纳功能、错误与路由关联等。
        """
        trace_id = strategy_plan.trace_id if strategy_plan else None
        strategy_ids = strategy_plan.strategy_ids if strategy_plan else None
        analysis_types = strategy_plan.analysis_strategy_types if strategy_plan else None

        # 输入校验：strategy_ids 必须存在且启用
        if strategy_ids:
            for sid in strategy_ids:
                st = strategy_engine.get_strategy(sid)
                if not st:
                    raise ValueError(f"Unknown strategy_id: {sid}")
                if not st.enabled:
                    raise ValueError(f"Disabled strategy_id: {sid}")

        # 有效的 LLM 开关：None 表示使用全局；且必须全局已配置成功才能调用
        llm_enabled = (
            strategy_plan.llm_enabled
            if strategy_plan and strategy_plan.llm_enabled is not None
            else llm_integration.enabled
        )
        llm_enabled = bool(llm_enabled and llm_integration.enabled)

        # 执行策略引擎的综合分析（规则引擎优先）
        suggestion_dicts = strategy_engine.execute_holistic_strategies(
            snapshot,
            usage,
            trace_id=trace_id,
            strategy_ids=strategy_ids,
            analysis_strategy_types=analysis_types,
        )
        suggestions = [Suggestion(**s) for s in suggestion_dicts]

        # 提取使用洞察
        usage_insights: List[Dict[str, Any]] = []
        if usage:
            top_routes = usage.get("top_routes") or []
            for r in top_routes:
                usage_insights.append({
                    "path": r.get("path", ""),
                    "requests": r.get("requests") or r.get("count") or 0,
                    "p99_ms": r.get("p99_ms"),
                    "error_rate": r.get("error_rate")
                })

        # LLM增强分析（可选）
        llm_analysis = None
        if llm_enabled:
            llm_analysis = llm_integration.enhance_analysis(
                snapshot=snapshot,
                usage=usage,
                suggestions=suggestion_dicts
            )

        # 构建分析结果
        result = AnalysisResult(
            service=snapshot.get("service_name", "unknown"),
            config_hint=config_hint,
            suggestions=suggestions,
            usage_insights=usage_insights,
            usage_informed=bool(usage),
            note="代码变更由 /code-proposals 生成草案；合并前必须经过评审与自动化测试。",
            trace_id=trace_id,
        )

        # 端到端追踪：把 analysis_id 填回每个建议项
        for s in suggestions:
            s.analysis_id = result.id

        # 保存结果
        storage.save_analysis_result(result)

        # 构建响应
        response = result.model_dump()
        if llm_analysis:
            response["llm_analysis"] = llm_analysis

        return response

    def code_proposals(
        self,
        snapshot: Dict[str, Any],
        usage: Optional[Dict[str, Any]],
        config_hint: Optional[str],
        language: str = "python",
        strategy_plan: Optional[RuntimeStrategyExecutionPlan] = None,
    ) -> Dict[str, Any]:
        """
        在综合分析基础上输出「代码变更草案」（示例片段 / 占位 diff）。
        生产环境应替换为：LLM + 仓库上下文生成 unified diff，再经 CI 与人工审核后合并。
        """
        trace_id = strategy_plan.trace_id if strategy_plan else None
        strategy_ids = strategy_plan.strategy_ids if strategy_plan else None
        code_types = strategy_plan.code_strategy_types if strategy_plan else None

        # 先执行综合分析（复用输入校验与规则引擎执行）
        analysis_result = self.holistic_analyze(
            snapshot,
            config_hint,
            usage,
            strategy_plan=strategy_plan,
        )
        suggestion_dicts = analysis_result["suggestions"]

        # 生成代码提案
        context = {
            "snapshot": snapshot,
            "usage": usage,
            "config_hint": config_hint,
            "language": language
        }
        patch_dicts = strategy_engine.generate_code_proposals(
            suggestion_dicts,
            context,
            trace_id=trace_id,
            code_strategy_types=code_types,
            strategy_ids=strategy_ids,
        )

        # LLM增强代码生成（可选）
        llm_enabled = (
            strategy_plan.llm_enabled
            if strategy_plan and strategy_plan.llm_enabled is not None
            else llm_integration.enabled
        )
        llm_enabled = bool(llm_enabled and llm_integration.enabled)

        if llm_enabled:
            for patch in patch_dicts:
                if patch.get("type") != "info":
                    # 找到对应的建议
                    suggestion = next((s for s in suggestion_dicts
                                     if s.get("id") == patch.get("suggestion_id")), None)
                    if suggestion:
                        llm_code = llm_integration.generate_code_patch(suggestion, context)
                        if llm_code:
                            patch["llm_enhanced_code"] = llm_code

        patches = [CodePatch(**p) for p in patch_dicts]

        # 构建代码提案结果
        result = CodeProposalsResult(
            service=snapshot.get("service_name", "unknown"),
            patches=patches,
            requires_human_review=config.require_human_review,
            requires_ci=config.require_ci_check,
            auto_merge_allowed=config.auto_merge_allowed,
            suggestions_echo=[s.get("type") for s in suggestion_dicts],
            trace_id=trace_id,
        )

        # 端到端追踪：把 proposal_id 填回每个补丁
        for p in patches:
            p.proposal_id = result.id

        # 保存结果
        storage.save_code_proposals(result)

        return result.model_dump()

    def latest_recommendations(
        self, service_name: Optional[str]
    ) -> Dict[str, Any]:
        """最近一次 holistic 或纯指标分析的建议列表。"""
        recommendations = storage.get_latest_recommendations(service_name)

        if not recommendations:
            return {
                "recommendations": [],
                "message": "尚无分析结果，请先调用 /analyze 或 /holistic-analyze"
            }

        return {
            "recommendations": recommendations,
            "total": len(recommendations)
        }

    def get_strategies(self, type_filter: Optional[str] = None,
                      enabled_only: bool = True) -> Dict[str, Any]:
        """获取所有策略配置"""
        from core.strategy_engine import StrategyType
        strategy_type = StrategyType(type_filter) if type_filter else None
        strategies = strategy_engine.list_strategies(strategy_type, enabled_only)

        def to_jsonable(obj: Any) -> Any:
            if is_dataclass(obj):
                obj = asdict(obj)
            if isinstance(obj, Enum):
                return obj.value
            if isinstance(obj, dict):
                return {k: to_jsonable(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [to_jsonable(v) for v in obj]
            return obj

        return {
            "strategies": [to_jsonable(s) for s in strategies],
            "total": len(strategies)
        }

    def add_strategy(self, strategy_data: Dict[str, Any]) -> Dict[str, Any]:
        """添加自定义策略"""
        import uuid
        from core.strategy_engine import (
            AnalysisStrategy as EngineAnalysisStrategy,
            StrategyCondition as EngineStrategyCondition,
            StrategyAction as EngineStrategyAction,
            CodeGenerationRule as EngineCodeGenerationRule,
            StrategyType as EngineStrategyType,
            StrategyPriority as EngineStrategyPriority,
        )

        # StrategyCreateRequest 不包含 id，这里生成一个自定义策略 id
        strategy_id = strategy_data.get("id") or f"custom-{uuid.uuid4().hex[:8]}"

        engine_type = EngineStrategyType(strategy_data["type"])

        priority_raw = strategy_data.get(
            "priority",
            EngineStrategyPriority.MEDIUM.name.lower(),
        )
        if isinstance(priority_raw, EngineStrategyPriority):
            engine_priority = priority_raw
        else:
            # 兼容：可能出现 "high" / "StrategyPriority.HIGH"
            priority_last = str(priority_raw).split(".")[-1].upper()
            engine_priority = EngineStrategyPriority[priority_last]

        conditions = [
            EngineStrategyCondition(**c) for c in (strategy_data.get("conditions") or [])
        ]

        actions: List[EngineStrategyAction] = []
        for a in (strategy_data.get("actions") or []):
            a_priority_raw = a.get(
                "priority",
                EngineStrategyPriority.MEDIUM.name.lower(),
            )
            if isinstance(a_priority_raw, EngineStrategyPriority):
                a_priority = a_priority_raw
            else:
                a_priority_last = str(a_priority_raw).split(".")[-1].upper()
                a_priority = EngineStrategyPriority[a_priority_last]
            a = {**a, "priority": a_priority}
            actions.append(EngineStrategyAction(**a))

        code_rules = [
            EngineCodeGenerationRule(**r) for r in (strategy_data.get("code_rules") or [])
        ]

        strategy = EngineAnalysisStrategy(
            id=strategy_id,
            name=strategy_data["name"],
            description=strategy_data["description"],
            type=engine_type,
            enabled=bool(strategy_data.get("enabled", True)),
            conditions=conditions,
            actions=actions,
            code_rules=code_rules,
            priority=engine_priority,
            tags=list(strategy_data.get("tags") or []),
            metadata=dict(strategy_data.get("metadata") or {}),
        )

        strategy_id = strategy_engine.add_strategy(strategy)
        return {
            "status": "created",
            "strategy_id": strategy_id,
        }

    def update_strategy(self, strategy_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新策略配置"""
        from core.strategy_engine import AnalysisStrategy as EngineAnalysisStrategy

        existing = strategy_engine.get_strategy(strategy_id)
        if not existing:
            return {"status": "error", "message": f"Strategy {strategy_id} not found"}

        # existing 是 dataclass，需要转换为 API 层的 Pydantic 模型
        # 先获取策略的原始数据（从 engine 的 _strategies 字典）
        existing_strategy = strategy_engine._strategies.get(strategy_id)
        if not existing_strategy:
            return {"status": "error", "message": f"Strategy {strategy_id} not found"}

        # 构建更新后的策略数据
        updated_data = {
            "id": existing_strategy.id,
            "name": existing_strategy.name,
            "description": existing_strategy.description,
            "type": existing_strategy.type,
            "enabled": existing_strategy.enabled,
            "conditions": existing_strategy.conditions,
            "actions": existing_strategy.actions,
            "code_rules": existing_strategy.code_rules,
            "priority": existing_strategy.priority,
            "tags": existing_strategy.tags,
            "metadata": existing_strategy.metadata,
        }
        # 合并用户提供的更新数据（只更新非 None 字段）
        for key, value in update_data.items():
            if value is not None:
                updated_data[key] = value

        # 创建新的策略实例（使用 engine 层的 dataclass）
        from core.strategy_engine import (
            StrategyCondition as EngineStrategyCondition,
            StrategyAction as EngineStrategyAction,
            CodeGenerationRule as EngineCodeGenerationRule,
            StrategyType as EngineStrategyType,
            StrategyPriority as EngineStrategyPriority,
        )

        # 转换 priority
        priority_raw = updated_data.get("priority", EngineStrategyPriority.MEDIUM)
        if isinstance(priority_raw, EngineStrategyPriority):
            engine_priority = priority_raw
        else:
            priority_last = str(priority_raw).split(".")[-1].upper()
            engine_priority = EngineStrategyPriority[priority_last]

        # 转换 conditions
        conditions = []
        for c in updated_data.get("conditions", []):
            if isinstance(c, EngineStrategyCondition):
                conditions.append(c)
            else:
                conditions.append(EngineStrategyCondition(**c))

        # 转换 actions
        actions = []
        for a in updated_data.get("actions", []):
            if isinstance(a, EngineStrategyAction):
                actions.append(a)
            else:
                a_priority_raw = a.get("priority", EngineStrategyPriority.MEDIUM)
                if isinstance(a_priority_raw, EngineStrategyPriority):
                    a_priority = a_priority_raw
                else:
                    a_priority_last = str(a_priority_raw).split(".")[-1].upper()
                    a_priority = EngineStrategyPriority[a_priority_last]
                a = {**a, "priority": a_priority}
                actions.append(EngineStrategyAction(**a))

        # 转换 code_rules
        code_rules = []
        for r in updated_data.get("code_rules", []):
            if isinstance(r, EngineCodeGenerationRule):
                code_rules.append(r)
            else:
                code_rules.append(EngineCodeGenerationRule(**r))

        updated_strategy = EngineAnalysisStrategy(
            id=updated_data["id"],
            name=updated_data["name"],
            description=updated_data["description"],
            type=EngineStrategyType(updated_data["type"]) if isinstance(updated_data["type"], str) else updated_data["type"],
            enabled=updated_data["enabled"],
            conditions=conditions,
            actions=actions,
            code_rules=code_rules,
            priority=engine_priority,
            tags=updated_data["tags"],
            metadata=updated_data["metadata"],
        )

        # 替换策略
        strategy_engine.remove_strategy(strategy_id)
        new_id = strategy_engine.add_strategy(updated_strategy)

        return {
            "status": "updated",
            "strategy_id": new_id
        }

    def delete_strategy(self, strategy_id: str) -> Dict[str, Any]:
        """删除策略"""
        success = strategy_engine.remove_strategy(strategy_id)
        if success:
            return {"status": "deleted", "strategy_id": strategy_id}
        return {"status": "error", "message": f"Strategy {strategy_id} not found"}


optimizer_service = OptimizerService()
