"""
AI 流量曝光 - 主入口
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from core.config import settings
from core.response import ResponseMiddleware
from core.exceptions import register_exception_handlers
from core.logging_config import setup_logging, get_logger
from db import init_db
import os

# 导入模块路由
from seo import seo_router
from content import content_router
from analytics import analytics_router, competitor_router

from ab_test import ab_test_router
from api import data_sources_router, dashboard_router
from api.dashboard_enhanced import router as dashboard_enhanced_router
from api.ai_analysis import router as ai_analysis_router
from api.paths_attribution import router as paths_attribution_router
from api.realtime import router as realtime_router
from api.llm_api import router as llm_router
from api.geo_api import router as geo_router
from api.collaboration import router as collaboration_router
from api.ai_optimization import router as ai_optimization_router
from api.logs import router as logs_router
from api.alerts import router as alerts_router
from api.anomaly_detection import router as anomaly_router
from api.root_cause_analysis import router as root_cause_router
from api.suggestions import router as suggestions_router
from api.code_optimization import router as code_optimization_router
from api.learning_loop import router as learning_loop_router
from api.query_assistant import router as query_assistant_router
from api.competitor_analysis import router as competitor_analysis_router
from api.chat import router as chat_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    """
    # 启动时初始化
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Debug mode: {settings.DEBUG}")

    # 初始化日志系统
    setup_logging(
        level="DEBUG" if settings.DEBUG else "INFO",
        log_file="ai_traffic_booster.log" if settings.DEBUG else None
    )

    # 初始化数据库
    if settings.DATABASE_URL:
        init_db()
        logger.info("Database initialized")
    else:
        logger.info("Running without database (in-memory mode)")

    # 初始化 AI Agent 系统
    try:
        from agents.deerflow_client import init_deerflow_client
        from agents.traffic_agent import init_traffic_agent
        from workflows.traffic_workflows import init_traffic_workflows
        from workflows.strategy_workflows import init_strategy_workflows

        init_deerflow_client()
        init_traffic_agent()
        init_traffic_workflows()
        init_strategy_workflows()
        logger.info("AI Agent system initialized (DeerFlow 2.0)")
    except Exception as e:
        logger.warning(f"AI Agent initialization warning: {e}")

    logger.info(f"Modules registered: SEO, Content, Analytics, A/B Test, Competitor Analysis (v1.9), Data Sources, Dashboard (v1.7), AI Analysis, AI 查询助手 (v1.8), AI 自动化优化 (v2.0), 跨平台集成 (v2.1), Cross-Agent Collaboration (P0), 商业化就绪 (v2.2), AI Native Chat (v3.0)")

    yield

    # 关闭时清理
    logger.info(f"Shutting down {settings.APP_NAME}")


app = FastAPI(
    title=settings.APP_NAME,
    description="AI 驱动的流量和曝光优化工具，集成 SEO 分析、内容优化、流量分析、A/B 测试、竞争情报、AI 异常检测、根因分析、优化建议、路径分析、归因分析、实时数据处理、LLM 集成、地理分布分析、跨 Agent 协同等功能",
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# 挂载静态文件目录
frontend_path = os.path.join(os.path.dirname(__file__), '..', 'frontend')
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册响应包装中间件
app.add_middleware(ResponseMiddleware)

# 注册异常处理器
register_exception_handlers(app)

# 注册路由
API_PREFIX = settings.API_PREFIX
app.include_router(seo_router, prefix=API_PREFIX)
app.include_router(content_router, prefix=API_PREFIX)
app.include_router(analytics_router, prefix=API_PREFIX)
app.include_router(ab_test_router, prefix=API_PREFIX)
app.include_router(competitor_router, prefix=API_PREFIX)
app.include_router(data_sources_router, prefix=API_PREFIX)
app.include_router(dashboard_router, prefix=API_PREFIX)
app.include_router(dashboard_enhanced_router, prefix=API_PREFIX)
app.include_router(ai_analysis_router, prefix=API_PREFIX)
app.include_router(paths_attribution_router, prefix=API_PREFIX)
app.include_router(realtime_router, prefix=API_PREFIX)
app.include_router(llm_router, prefix=API_PREFIX)
app.include_router(geo_router, prefix=API_PREFIX)
app.include_router(collaboration_router, prefix=API_PREFIX)
app.include_router(ai_optimization_router, prefix=API_PREFIX)
app.include_router(logs_router, prefix=API_PREFIX)
app.include_router(alerts_router, prefix=API_PREFIX)
app.include_router(anomaly_router, prefix=API_PREFIX)
app.include_router(root_cause_router, prefix=API_PREFIX)
app.include_router(suggestions_router, prefix=API_PREFIX)
app.include_router(code_optimization_router, prefix=API_PREFIX)
app.include_router(learning_loop_router, prefix=API_PREFIX)
app.include_router(query_assistant_router, prefix=API_PREFIX)
app.include_router(competitor_analysis_router, prefix=API_PREFIX)
app.include_router(chat_router, prefix=API_PREFIX)


@app.get("/", summary="根路径", description="服务状态和入口信息")
async def root():
    return {
        "message": "欢迎使用 AI Traffic Booster v3.0 AI Native - 您的虚拟增长团队",
        "status": "running",
        "version": settings.APP_VERSION,
        "modules": {
            # 基础模块
            "SEO 优化": f"{API_PREFIX}/seo",
            "内容优化": f"{API_PREFIX}/content",
            "流量分析": f"{API_PREFIX}/analytics",
            "A/B 测试": f"{API_PREFIX}/ab-test",
            # v1.9 竞品分析增强
            "竞争情报": f"{API_PREFIX}/competitor",
            "竞品追踪": f"{API_PREFIX}/competitor/track",
            "市场份额": f"{API_PREFIX}/competitor/market-share",
            "竞品策略": f"{API_PREFIX}/competitor/strategy",
            # v1.7 可视化增强
            "仪表板": f"{API_PREFIX}/dashboard",
            "AI 洞察": f"{API_PREFIX}/dashboard/insights",
            # AI 能力模块
            "AI 能力分析": f"{API_PREFIX}/ai",
            "AI 异常检测 (P1)": f"{API_PREFIX}/ai/anomaly",
            "AI 根因分析 (P1)": f"{API_PREFIX}/ai/root-cause",
            "优化建议 (P2)": f"{API_PREFIX}/ai/suggestions",
            # v1.8 AI 查询助手
            "AI 查询助手": f"{API_PREFIX}/ai/query",
            "智能报告": f"{API_PREFIX}/ai/query/report/generate",
            # v2.0 自动化优化
            "AI 自动化优化 (v2.0)": f"{API_PREFIX}/ai-optimization",
            "A/B 测试设计": f"{API_PREFIX}/ai-optimization/test-design",
            "代码优化生成": f"{API_PREFIX}/ai-optimization/code/generate",
            # v3.0 AI Native 对话式交互
            "AI 对话助手 (v3.0)": f"{API_PREFIX}/chat/message",
            "主动洞察推送": f"{API_PREFIX}/chat/insights",
            "工作流编排": f"{API_PREFIX}/chat/workflows",
            # 数据与集成
            "数据源": f"{API_PREFIX}/data-sources",
            "日志系统 (P0)": f"{API_PREFIX}/logs",
            "告警通知 (P0)": f"{API_PREFIX}/alerts",
            "持续学习 (P3)": f"{API_PREFIX}/ai/learning",
            # 其他模块
            "路径与归因": f"{API_PREFIX}/analytics/paths",
            "实时数据": f"{API_PREFIX}/realtime",
            "地理分布": f"{API_PREFIX}/geo",
        },
        "ai_native_features": {
            "对话式交互": f"{API_PREFIX}/chat/message - 用自然语言与 AI 助手交流",
            "主动洞察": f"{API_PREFIX}/chat/insights - AI 主动发现并推送异常和机会",
            "自主执行": "AI 在置信度高时自主执行优化策略",
            "工作流编排": f"{API_PREFIX}/chat/workflows - 多步任务自动编排执行"
        },
        "documentation": {
            "Swagger UI": "/docs",
            "ReDoc": "/redoc",
            "部署指南": "/docs/DEPLOYMENT_GUIDE.md",
            "商业化清单": "/docs/COMMERCIALIZATION_CHECKLIST.md",
            "AI Native 白皮书": "/docs/AI_NATIVE_REDESIGN_WHITEPAPER.md"
        }
    }


@app.get("/health", summary="健康检查", description="服务健康状态检查")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "debug": settings.DEBUG
    }


@app.get("/dashboard", summary="可视化仪表板", description="访问可视化仪表板")
async def get_dashboard():
    """重定向到仪表板页面"""
    from fastapi.responses import FileResponse
    dashboard_path = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'dashboard.html')
    if os.path.exists(dashboard_path):
        return FileResponse(dashboard_path)
    return {"error": "Dashboard not found"}


@app.get("/db/init", summary="初始化数据库", description="手动触发数据库初始化（仅开发环境）")
async def init_database():
    """
    手动触发数据库初始化

    仅建议在开发环境下使用，生产环境应使用迁移工具
    """
    if not settings.DEBUG:
        return {"status": "error", "message": "仅开发环境支持此操作"}

    try:
        init_db()
        return {"status": "success", "message": "数据库初始化成功"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        workers=settings.WORKERS
    )
