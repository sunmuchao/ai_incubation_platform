"""
核心模块
"""
from core.config import config
from core.strategy_engine import strategy_engine, StrategyEngine, AnalysisStrategy, StrategyType, StrategyPriority
from core.storage import storage, InMemoryStorage
from core.llm_integration import llm_integration, LLMIntegration, BaseLLMClient
from core.audit import audit_logger, AuditLogger, AuditEventType, AuditStatus
from core.alert_engine import alert_engine, AlertEngine, AlertRule, AlertSeverity, AlertStatus
from core.service_map import service_map, ServiceMap, ServiceNode, DependencyEdge, DependencyType
from core.anomaly_detector import anomaly_detector, AnomalyDetector, AnomalyEvent, AnomalyType

# 根据全局配置初始化 LLM（失败不影响主流程）
if config.llm_enabled and not llm_integration.enabled:
    try:
        llm_integration.configure(
            provider=config.llm_provider.value,
            api_key=config.llm_api_key,
            model=config.llm_model,
        )
    except Exception:
        # LLM 未配置或 provider 初始化失败：保持 llm_integration.enabled=False
        pass
