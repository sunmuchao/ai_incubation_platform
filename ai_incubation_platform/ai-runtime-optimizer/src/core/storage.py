"""
存储层：分析结果与状态持久化
当前为内存实现，生产环境可扩展为数据库/缓存
"""
from typing import Any, Dict, List, Optional
from datetime import datetime
from collections import defaultdict

from models.analysis import AnalysisResult, CodeProposalsResult


class InMemoryStorage:
    def __init__(self):
        self._metrics_records: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._usage_records: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._analysis_results: Dict[str, List[AnalysisResult]] = defaultdict(list)
        self._proposal_results: Dict[str, List[CodeProposalsResult]] = defaultdict(list)
        self._last_analysis: Optional[AnalysisResult] = None
        self._last_holistic: Optional[AnalysisResult] = None
        self._max_records_per_service = 100  # 每个服务最多保留记录数

    def record_metrics(self, service_name: str, metrics: Dict[str, Any]) -> None:
        """记录指标快照"""
        record = {
            "timestamp": datetime.utcnow(),
            "data": metrics
        }
        self._metrics_records[service_name].append(record)
        # 清理旧记录
        if len(self._metrics_records[service_name]) > self._max_records_per_service:
            self._metrics_records[service_name].pop(0)

    def record_usage(self, service_name: str, usage: Dict[str, Any]) -> None:
        """记录使用情况"""
        record = {
            "timestamp": datetime.utcnow(),
            "data": usage
        }
        self._usage_records[service_name].append(record)
        # 清理旧记录
        if len(self._usage_records[service_name]) > self._max_records_per_service:
            self._usage_records[service_name].pop(0)

    def save_analysis_result(self, result: AnalysisResult) -> None:
        """保存分析结果"""
        self._analysis_results[result.service].append(result)
        self._last_analysis = result
        if result.usage_informed:
            self._last_holistic = result
        # 清理旧记录
        if len(self._analysis_results[result.service]) > self._max_records_per_service:
            self._analysis_results[result.service].pop(0)

    def save_code_proposals(self, result: CodeProposalsResult) -> None:
        """保存代码提案结果"""
        self._proposal_results[result.service].append(result)
        # 清理旧记录
        if len(self._proposal_results[result.service]) > self._max_records_per_service:
            self._proposal_results[result.service].pop(0)

    def get_last_metrics(self, service_name: str) -> Optional[Dict[str, Any]]:
        """获取服务最新的指标"""
        records = self._metrics_records.get(service_name, [])
        if records:
            return records[-1]["data"]
        return None

    def get_last_usage(self, service_name: str) -> Optional[Dict[str, Any]]:
        """获取服务最新的使用情况"""
        records = self._usage_records.get(service_name, [])
        if records:
            return records[-1]["data"]
        return None

    def get_last_analysis(self, service_name: Optional[str] = None) -> Optional[AnalysisResult]:
        """获取最新的分析结果"""
        if service_name:
            records = self._analysis_results.get(service_name, [])
            return records[-1] if records else None
        return self._last_analysis

    def get_last_holistic(self, service_name: Optional[str] = None) -> Optional[AnalysisResult]:
        """获取最新的综合分析结果"""
        if service_name:
            records = [r for r in self._analysis_results.get(service_name, []) if r.usage_informed]
            return records[-1] if records else None
        return self._last_holistic

    def get_latest_recommendations(self, service_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取最新的建议列表"""
        # 优先返回综合分析结果
        result = self.get_last_holistic(service_name)
        if not result:
            result = self.get_last_analysis(service_name)

        if not result:
            return []

        return [
            {
                "id": s.id,
                "strategy_id": s.strategy_id,
                "type": s.type,
                "action": s.action,
                "confidence": s.confidence,
                "priority": s.priority,
                "evidence": s.evidence,
                "tags": s.tags,
                "created_at": s.created_at.isoformat()
            }
            for s in result.suggestions
        ]

    def get_analysis_history(self, service_name: str, limit: int = 20) -> List[AnalysisResult]:
        """获取服务的分析历史"""
        records = self._analysis_results.get(service_name, [])
        return sorted(records, key=lambda x: x.created_at, reverse=True)[:limit]

    def get_proposal_history(self, service_name: str, limit: int = 20) -> List[CodeProposalsResult]:
        """获取服务的代码提案历史"""
        records = self._proposal_results.get(service_name, [])
        return sorted(records, key=lambda x: x.created_at, reverse=True)[:limit]

    def get_all_services(self) -> List[str]:
        """获取所有有记录的服务名"""
        services = set()
        services.update(self._metrics_records.keys())
        services.update(self._usage_records.keys())
        services.update(self._analysis_results.keys())
        services.update(self._proposal_results.keys())
        return sorted(list(services))


# 全局存储实例
storage = InMemoryStorage()
