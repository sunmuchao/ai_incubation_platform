"""
数据-Agent 连接器 - 主入口
"""
import asyncio
from fastapi import FastAPI
from api.query import router as query_router
from api.connectors import router as connectors_router
from api.monitoring import router as monitoring_router
from api.ai_query import router as ai_query_router
from api.data_transform import router as data_transform_router
from api.rbac import router as rbac_router
from api.tenant import router as tenant_router
from api.docs import router as docs_router
from api.unstructured import router as unstructured_router
from api.vector import router as vector_router
from api.semantic_search import router as semantic_search_router
from api.data_quality import router as data_quality_router
from api.schema_recommendation import router as schema_recommendation_router
from api.predictive_monitoring import router as predictive_monitoring_router
from api.logs import router as logs_router
from api.data_governance import router as data_governance_router
from api.lineage import router as lineage_router
from api.enterprise import router as enterprise_router
# from api.ai_native import router as ai_native_router  # 模块不存在，暂时注释
from connectors.base import register_builtin_connectors
from core.connection_manager import connection_manager
from core.audit import audit_logger
from core.rate_limiter import rate_limiter
from core.lineage import lineage_manager
from services.monitoring_service import monitoring_service
from services.rbac_service import init_rbac
from services.tenant_service import init_tenant
from services.vector_index_service import vector_index_service
from services.semantic_search_service import semantic_search_service
from services.data_quality_service import data_quality_service
from services.schema_recommendation_service import schema_recommendation_service
from services.log_storage_service import log_storage_service
from services.log_cleanup_service import log_cleanup_service
from services.log_analytics_service import log_analytics_service
from services.data_governance_service import data_governance_service
from config.database import db_manager
from config.settings import settings
from utils.logger import logger

app = FastAPI(
    title="Data-Agent Connector",
    description="孵化器统一数据出口：多源连接、Schema 发现、查询与 NL2SQL 在安全边界内可审计、可限流",
    version="1.7.0"  # v1.7.0 - AI Native 转型 (DeerFlow 2.0 Agent 框架)
)

# 注册内置连接器
register_builtin_connectors()

# 注册路由
app.include_router(query_router)
app.include_router(connectors_router)
app.include_router(monitoring_router)
app.include_router(ai_query_router)
app.include_router(data_transform_router)
app.include_router(rbac_router)
app.include_router(tenant_router)
app.include_router(docs_router)
app.include_router(unstructured_router)
app.include_router(vector_router)
app.include_router(semantic_search_router)
app.include_router(data_quality_router)
app.include_router(schema_recommendation_router)
app.include_router(predictive_monitoring_router)
app.include_router(logs_router)
app.include_router(data_governance_router)
app.include_router(lineage_router)
app.include_router(enterprise_router)
# app.include_router(ai_native_router)  # 模块不存在，暂时注释


@app.on_event("startup")
async def startup_event():
    """服务启动事件"""
    logger.info("Starting Data-Agent Connector service", extra={
        "environment": settings.environment,
        "port": settings.port
    })

    # 初始化数据库
    await db_manager.init_db()

    # 运行日志表迁移（P7 新增）
    from migrations.create_logs_tables import create_logs_tables
    db_path = db_manager.config.db_path
    create_logs_tables(db_path)
    logger.info(f"Log tables migration completed in {db_path}")

    # 启动审计日志
    await audit_logger.start()

    # 启动监控服务
    await monitoring_service.start()

    # 启动 CDC 服务
    from services.cdc_service import cdc_service
    await cdc_service.start()

    # 启动数据转换服务
    from services.transform_service import start_transform_service
    await start_transform_service()

    # 启动 dbt 服务
    from services.dbt_service import start_dbt_service
    await start_dbt_service()

    # 初始化 RBAC 服务
    await init_rbac()

    # 初始化多租户服务
    await init_tenant()

    # 初始化 P5 数据智能服务
    await vector_index_service.initialize()
    await semantic_search_service.initialize()
    await data_quality_service.initialize()
    await schema_recommendation_service.initialize()

    # 初始化 v1.5 数据治理服务
    await data_governance_service.initialize()

    # 初始化 P7 日志持久化与审计服务
    await log_storage_service.initialize()
    await log_cleanup_service.initialize()
    # log_analytics_service 不需要初始化

    # 启动空闲连接清理任务
    async def cleanup_idle_connections_loop():
        while True:
            try:
                await connection_manager.cleanup_idle_connections()
                await asyncio.sleep(60)  # 每分钟清理一次
            except Exception as e:
                logger.error("Error in idle connection cleanup", extra={"error": str(e)})
                await asyncio.sleep(10)

    asyncio.create_task(cleanup_idle_connections_loop())

    # 启动系统健康记录任务
    async def record_system_health_loop():
        while True:
            try:
                connectors = await connection_manager.list_connectors()
                await monitoring_service.record_system_health({
                    "status": "healthy",
                    "active_connections": len(connectors),
                    "max_connections": settings.connector.default_max_connections,
                    "connection_pool_usage": len(connectors) / settings.connector.default_max_connections,
                    "current_qps": rate_limiter.requests_in_window / 60,
                    "current_concurrent": rate_limiter.current_concurrent,
                    "rate_limit_enabled": settings.rate_limit.enabled,
                    "total_lineage_nodes": lineage_manager.get_lineage_statistics().get("total_nodes", 0),
                    "total_lineage_edges": lineage_manager.get_lineage_statistics().get("total_edges", 0)
                })
                await asyncio.sleep(30)  # 每 30 秒记录一次
            except Exception as e:
                logger.error("Error in system health recording", extra={"error": str(e)})
                await asyncio.sleep(30)

    asyncio.create_task(record_system_health_loop())

    logger.info("Service started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """服务关闭事件"""
    logger.info("Shutting down Data-Agent Connector service")

    # 停止 v1.5 数据治理服务
    await data_governance_service.close()

    # 停止 P7 日志服务
    await log_cleanup_service.close()
    await log_storage_service.close()

    # 停止 P5 数据智能服务
    await schema_recommendation_service.close()
    await data_quality_service.close()
    await semantic_search_service.close()
    await vector_index_service.close()

    # 停止 dbt 服务
    from services.dbt_service import stop_dbt_service
    await stop_dbt_service()

    # 停止数据转换服务
    from services.transform_service import stop_transform_service
    await stop_transform_service()

    # 停止 CDC 服务
    from services.cdc_service import cdc_service
    await cdc_service.stop()

    # 停止监控服务
    await monitoring_service.stop()

    # 关闭所有连接
    await connection_manager.shutdown()

    # 停止审计日志
    await audit_logger.stop()

    # 关闭数据库连接
    await db_manager.close()

    logger.info("Service shutdown completed")


@app.get("/")
async def root():
    return {
        "message": "欢迎使用数据-Agent 连接器",
        "status": "running",
        "version": "1.6.0",
        "endpoints": {
            "query": "/api/query",
            "connectors": "/api/connectors",
            "monitoring": "/api/monitoring",
            "ai-query": "/api/ai",
            "data-transform": "/api/data",
            "rbac": "/api/rbac",
            "unstructured": "/api/unstructured",
            "vector": "/api/vector",
            "search": "/api/search",
            "quality": "/api/quality",
            "schema": "/api/schema",
            "predictive": "/api/predictive",
            "logs": "/api/logs",
            "governance": "/api/governance",
            "lineage": "/api/lineage",
            "enterprise": "/api/enterprise",
            "docs": "/docs"
        },
        "features": [
            "统一多数据源连接",
            "SQL 安全检查与危险语句拦截",
            "只读/读写权限控制",
            "查询审计日志",
            "请求限流与并发控制",
            "自然语言转 SQL 查询",
            "细粒度 RBAC 权限系统",
            "数据脱敏",
            "22+ 结构化数据连接器支持 (MySQL/PG/BigQuery/ClickHouse/StarRocks/Doris/Databricks/Hive/Presto 等)",
            "6+ 非结构化数据连接器支持 (PDF/Word/Excel/PPT/TXT/Markdown/JSON/XML/Image OCR/Web/Email/Chat)",
            "[P5] 向量索引与语义搜索",
            "[P5] 数据质量监控与异常检测",
            "[P5] 智能 Schema 推荐",
            "[P6] 预测性监控与自愈系统",
            "[P7] 日志持久化与审计系统",
            "[P7] 用户活动分析",
            "[P7] 异常检测",
            "[P7] 合规报告生成",
            "[v1.3] NL2SQL 准确率提升 (Few-Shot 示例学习)",
            "[v1.3] Schema 关系增强 (自动外键发现)",
            "[v1.3] 查询澄清机制 (歧义检测)",
            "[v1.3] SQL 自校正 (执行失败自动修正)",
            "[v1.4] 连接器健康检查标准化",
            "[v1.4] 性能基准测试框架",
            "[v1.4] Schema 发现增强 (外键/索引/分区自动发现)",
            "[v1.5] 数据分类与标签系统",
            "[v1.5] 敏感数据自动识别",
            "[v1.5] 脱敏策略管理",
            "[v1.5] 血缘可视化 API",
            "[v1.5] 治理仪表板",
            "[v1.6] 列级权限控制",
            "[v1.6] 行级策略控制",
            "[v1.6] 租户配额管理",
            "[v1.6] 增强审计日志",
            "[v1.6] 合规报告生成"
        ]
    }


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "version": "1.6.0",
        "metrics": {
            "active_connections": len(await connection_manager.list_connectors()),
            "current_concurrent_queries": rate_limiter.current_concurrent,
            "requests_in_current_window": rate_limiter.requests_in_window
        }
    }


@app.get("/status")
async def get_status():
    """获取系统状态"""
    connectors = await connection_manager.list_connectors()
    return {
        "status": "running",
        "active_connectors_count": len(connectors),
        "active_connectors": connectors,
        "current_concurrent_queries": rate_limiter.current_concurrent,
        "requests_in_current_window": rate_limiter.requests_in_window
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)
