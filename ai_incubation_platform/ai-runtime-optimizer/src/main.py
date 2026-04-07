"""
AI 运行态优化器 - 主入口
指标 + 用户使用行为 + 代码变更草案（评审后合入）。
"""
import json
import logging
from typing import Any, Dict

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from api.optimizer import router as optimizer_router
from api.p5_features import router as p5_features_router
from api.remediation import router as remediation_router
from api.remediation_v21 import router as remediation_v21_router
from api.causal_inference import router as causal_inference_router
from api.predictive_maintenance_v2 import router as predictive_maintenance_v2_router
from api.observability_v24 import router as observability_v24_router
from api.ai_optimization_v25 import router as ai_optimization_v25_router
from api.ai_native import router as ai_native_router
from core.config import config
from core import observability_engine
from core import llm_integration
from core import audit
from core import remediation_engine

# 配置日志
logging.basicConfig(
    level=logging.DEBUG if config.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Runtime Optimizer",
    description="AI 运行态优化器 — AI Native 自主运维工程师 (DeerFlow 2.0)",
    version="4.0.0 AI Native",
)

app.include_router(optimizer_router)
app.include_router(p5_features_router)
app.include_router(remediation_router)
app.include_router(remediation_v21_router)
app.include_router(causal_inference_router)
app.include_router(predictive_maintenance_v2_router)
app.include_router(observability_v24_router)
app.include_router(ai_optimization_v25_router)
app.include_router(ai_native_router)


@app.on_event("startup")
async def startup_event():
    """应用启动时初始化"""
    logger.info("AI Runtime Optimizer starting up...")

    # 初始化 LLM 集成
    if config.llm_enabled:
        try:
            llm_integration.configure(
                provider=config.llm_provider.value,
                api_key=config.llm_api_key,
                model=config.llm_model
            )
            logger.info(f"LLM integration initialized with provider: {config.llm_provider.value}")
        except Exception as e:
            logger.warning(f"LLM integration failed to initialize: {e}")

    # 初始化审计日志
    logger.info("Audit logger initialized")

    # 初始化告警引擎
    try:
        from core.alert_engine import alert_engine
        logger.info(f"Alert engine initialized with {len(alert_engine._rules)} rules")
    except Exception:
        pass

    # 初始化服务映射
    try:
        from core.service_map import service_map
        logger.info(f"Service map initialized with {len(service_map._services)} services")
    except Exception:
        pass

    # 初始化异常检测器
    logger.info("Anomaly detector initialized")

    # 初始化自主修复引擎
    logger.info("Remediation engine initialized")

    # 初始化可观测性引擎 (v2.4)
    try:
        from core.tracing import global_tracer
        from core.observability_engine import get_observability_engine
        obs_engine = get_observability_engine(tracer=global_tracer)
        logger.info("Observability engine v2.4 initialized")
    except Exception as e:
        logger.warning(f"Observability engine initialization failed: {e}")

    # 初始化 AI Native Agent (DeerFlow 2.0)
    try:
        from agents.optimizer_agent import get_optimizer_agent
        from workflows.optimizer_workflows import register_optimizer_workflows

        agent = get_optimizer_agent()
        register_optimizer_workflows(agent)
        logger.info("AI Native Optimizer Agent initialized (DeerFlow 2.0)")
    except Exception as e:
        logger.warning(f"AI Native Agent initialization failed: {e}")

    logger.info("AI Runtime Optimizer startup complete")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时清理资源"""
    logger.info("AI Runtime Optimizer shutting down...")
    # 如果有 Redis 存储，关闭连接
    try:
        from core.storage_redis import _storage_instance
        if _storage_instance:
            _storage_instance.close()
            logger.info("Redis storage connection closed")
    except Exception:
        pass


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(
    request: Request, exc: RequestValidationError
):
    """统一请求校验失败（422）的返回结构，便于调用方按 error_code 处理。"""

    def _to_jsonable(v):
        if isinstance(v, dict):
            return {k: _to_jsonable(val) for k, val in v.items()}
        if isinstance(v, list):
            return [_to_jsonable(x) for x in v]
        try:
            json.dumps(v)
            return v
        except TypeError:
            return str(v)

    # 审计日志：记录请求校验失败
    audit.audit_logger.log_error(
        error_type="RequestValidationError",
        error_message="request validation failed",
        context={"path": str(request.url), "method": request.method},
    )

    return JSONResponse(
        status_code=422,
        content={
            "status": "error",
            "error_code": "VALIDATION_ERROR",
            "message": "request validation failed",
            "details": _to_jsonable(exc.errors()),
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器"""
    # 审计日志：记录未处理异常
    audit.audit_logger.log_error(
        error_type=type(exc).__name__,
        error_message=str(exc),
        context={"path": str(request.url), "method": request.method},
    )

    logger.exception(f"Unhandled exception: {exc}")

    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "error_code": "INTERNAL_ERROR",
            "message": f"internal server error: {str(exc)}",
        },
    )


@app.get("/")
async def root():
    return {
        "message": "欢迎使用 AI 运行态优化器 (AI Native v4.0)",
        "status": "running",
        "version": "4.0.0 AI Native",
        "features": [
            "可配置策略引擎",
            "指标与用户行为综合分析",
            "代码变更草案生成",
            "可追踪建议 ID",
            "输入校验",
            "可选 LLM 增强 (支持 OpenAI/Claude)",
            "Redis 持久化存储",
            "审计日志",
            "告警系统 (多渠道通知)",
            "服务依赖映射",
            "AI 异常检测",
            "【P5 新增】预测性维护 v1",
            "【P5 新增】知识图谱 v2",
            "【P6 新增】自主修复引擎 v1",
            "【v1.1 新增】影响分析服务",
            "【v1.1 新增】案例库服务",
            "【v2.1 新增】执行引擎 V2（沙箱隔离）",
            "【v2.1 新增】验证引擎（指标比对）",
            "【v2.1 新增】回滚管理器（快照管理）",
            "【v2.1 新增】审批工作流（多级审批）",
            "【v2.2 新增】因果图构建（DAG）",
            "【v2.2 新增】贝叶斯因果推断",
            "【v2.2 新增】因果效应量化",
            "【v2.2 新增】反事实推理",
            "【v2.2 新增】d-分离判断",
            "【v2.2 新增】因果链可视化",
            "【v2.3 新增】健康度评分系统（多维度）",
            "【v2.3 新增】剩余寿命预测（RUL）",
            "【v2.3 新增】预测性告警（提前 7 天）",
            "【v2.3 新增】维护计划优化器",
            "【v2.4 新增】统一可观测性引擎",
            "【v2.4 新增】日志聚合与模式聚类",
            "【v2.4 新增】分布式追踪增强",
            "【v2.4 新增】服务健康评分",
            "【v2.4 新增】关联分析 (追踪 + 日志)",
            "【v2.5 新增】AI 优化建议引擎",
            "【v2.5 新增】性能瓶颈分析",
            "【v2.5 新增】资源优化建议",
            "【v2.5 新增】成本优化分析",
            "【v4.0 AI Native 新增】DeerFlow 2.0 Agent 框架",
            "【v4.0 AI Native 新增】感知 Agent - 主动发现异常",
            "【v4.0 AI Native 新增】诊断 Agent - 多 Agent 协同根因分析",
            "【v4.0 AI Native 新增】修复 Agent - AI 自主执行修复",
            "【v4.0 AI Native 新增】优化 Agent - AI 生成优化建议",
            "【v4.0 AI Native 新增】对话式 API - 自然语言交互",
            "【v4.0 AI Native 新增】Generative UI - AI 动态生成仪表板",
            "【v4.0 AI Native 新增】Tools 注册表 - 可扩展工具系统",
            "【v4.0 AI Native 新增】Workflows - 声明式工作流编排",
        ],
        "endpoints": {
            "metrics": "/api/runtime/metrics",
            "usage": "/api/runtime/usage",
            "analyze": "/api/runtime/analyze",
            "holistic_analyze": "/api/runtime/holistic-analyze",
            "code_proposals": "/api/runtime/code-proposals",
            "recommendations": "/api/runtime/recommendations",
            "strategies_management": "/api/runtime/strategies",
            "alerts": "/api/runtime/alerts",
            "service_map": "/api/runtime/service-map",
            "anomaly_detection": "/api/runtime/anomaly",
            "p5_features": "/api/p5",
            "remediation": "/api/remediation",
            "remediation_v21": "/api/remediation/v2.1",
            "causal_inference": "/api/root-cause/v2.2",
            "predictive_maintenance_v2": "/api/predictive-maintenance/v2.3",
            "observability_v24": "/api/observability/v2.4",
            "optimization_v25": "/api/optimization/v2.5",
            "ai_native": {
                "ask": "/api/ai/ask - 自然语言问答",
                "diagnose": "/api/ai/diagnose - AI 深度诊断",
                "remediate": "/api/ai/remediate - 自主修复",
                "optimize": "/api/ai/optimize - 优化建议",
                "dashboard": "/api/ai/dashboard - 动态仪表板",
                "autonomous_loop": "/api/ai/autonomous-loop - 自主运维循环",
                "tools": "/api/ai/tools - 工具列表",
            },
            "health": "/health",
            "docs": "/docs",
        },
        "auto_merge_default": False,
    }


@app.get("/health")
async def health_check():
    """健康检查，包含依赖组件状态"""
    health_status = {
        "status": "healthy",
        "checks": {
            "api": "ok"
        }
    }

    # 检查 LLM 状态
    if config.llm_enabled:
        if llm_integration.enabled:
            health_status["checks"]["llm"] = "ok"
        else:
            health_status["checks"]["llm"] = "not_configured"
            health_status["status"] = "degraded"

    # 检查 Redis 状态（如果使用）
    if config.storage_type == "redis":
        try:
            from core.storage_redis import get_redis_storage
            storage = get_redis_storage(config.redis_url)
            redis_health = storage.health_check()
            health_status["checks"]["redis"] = redis_health
            if redis_health.get("status") != "healthy":
                health_status["status"] = "degraded"
        except Exception as e:
            health_status["checks"]["redis"] = {"status": "unhealthy", "error": str(e)}
            health_status["status"] = "degraded"

    return health_status


if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("PORT", config.port))
    uvicorn.run(app, host="0.0.0.0", port=port)
