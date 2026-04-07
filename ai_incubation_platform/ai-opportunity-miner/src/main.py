"""
AI 商机挖掘 - 主入口

集成 DeerFlow 2.0 Agent 编排，遵循孵化器 Agent 标准：
- 业务动作封装为可调工具
- 敏感操作在工具层强校验与审计
- 多步编排通过 DeerFlow 2.0 统一管理
"""
import sys
import os
import logging
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.opportunity import router as opportunity_router
from api.agent import router as agent_router
from api.intelligence import router as intelligence_router
from api.data_sources import router as data_sources_router
from api.dashboard import router as dashboard_router
from api.investment_chain import router as investment_chain_router
from api.equity_analysis import router as equity_analysis_router
from api.ml_prediction import router as ml_prediction_router
from api.p6_score_recommend import router as p6_score_recommend_router
from api.p6_auth import router as p6_auth_router
from api.p6_payment import router as p6_payment_router
from api.p7_contributions import router as p7_contributions_router
from api.p7_open_api import router as p7_open_api_router
from api.stream import router as stream_router  # v1.5 实时数据流 API
from api.v16_billing import router as v16_billing_router  # v1.6 配额与计费 API
from api.v17_ml_enhanced import router as v17_ml_enhanced_router  # v1.7 AI 驱动增强 API
from api.v18_enterprise import router as v18_enterprise_router  # v1.8 企业级功能 API
from api.v19_ecosystem import router as v19_ecosystem_router  # v1.9 生态建设 API
from api.chat import router as chat_router  # AI Native 对话式 API
from config.database import init_db

app = FastAPI(
    title="AI Opportunity Miner",
    description="AI 商机挖掘系统 - 基于 DeerFlow 2.0 Agent 编排，集成 CB Insights 风格商业情报功能，支持真实数据源接入",
    version="0.9.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# 配置 CORS 以支持前端访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 启动事件处理
@app.on_event("startup")
async def startup_event():
    """应用启动时初始化数据库"""
    init_db()
    # 初始化演示数据
    from services.opportunity_service import opportunity_service
    opportunity_service.discover_opportunities()
    # 初始化投资关系链和股权穿透图数据
    from services.investment_chain_service import investment_chain_service
    try:
        from services.equity_analysis import EquityAnalysisService
        equity_analysis_service = EquityAnalysisService()
    except Exception as e:
        logger.warning(f"Failed to initialize equity_analysis_service: {e}")
        equity_analysis_service = None
    logger.info("Investment chain and equity analysis services initialized")
    # 初始化 ML 预测服务
    from services.ml_prediction_service import ml_prediction_service
    ml_prediction_service.initialize()
    logger.info("ML prediction service initialized")

    # v1.5 启动实时数据流服务
    from services.stream_service import stream_service
    from services.websocket_service import websocket_service
    from services.event_processor import event_processor

    await stream_service.start()
    await websocket_service.start()
    await event_processor.start()
    logger.info("Real-time stream services initialized (v1.5)")

# 关闭事件处理
@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时清理资源"""
    from services.stream_service import stream_service
    from services.websocket_service import websocket_service
    from services.event_processor import event_processor

    await stream_service.stop()
    await websocket_service.stop()
    await event_processor.stop()
    logger.info("Real-time stream services stopped")

# 注册路由
app.include_router(opportunity_router)  # 传统 REST API
app.include_router(agent_router)  # Agent 工具 API
app.include_router(intelligence_router)  # 商业情报 API（CB Insights 风格）
app.include_router(data_sources_router)  # 数据源 API（P3 新增）
app.include_router(dashboard_router)  # 可视化仪表板 API（P3 新增）
app.include_router(investment_chain_router)  # 投资关系链 API（P4 新增）
app.include_router(equity_analysis_router)  # 股权穿透 API（P4 新增）
app.include_router(ml_prediction_router)  # ML 预测 API（P4 新增）
app.include_router(p6_score_recommend_router)  # P6 商机评分与推荐 API
app.include_router(p6_auth_router)  # P6 用户认证与订阅管理 API
app.include_router(p6_payment_router)  # P6 支付与订单管理 API
app.include_router(p7_contributions_router)  # P7 用户贡献与社区 API
app.include_router(p7_open_api_router)  # P7 开放 API 平台 API
app.include_router(stream_router)  # v1.5 实时数据流 API
app.include_router(v16_billing_router)  # v1.6 配额与计费 API
app.include_router(v17_ml_enhanced_router)  # v1.7 AI 驱动增强 API
app.include_router(v18_enterprise_router)  # v1.8 企业级功能 API
app.include_router(v19_ecosystem_router)  # v1.9 生态建设 API
app.include_router(chat_router)  # AI Native 对话式 API

@app.get("/")
async def root():
    return {
        "message": "欢迎使用 AI 商机挖掘系统",
        "version": "3.0.0 AI Native",
        "status": "running",
        "agent_runtime": "DeerFlow 2.0",
        "ai_native_features": {
            "chat": "/api/chat - 对话式交互",
            "proactive_discovery": "POST /api/chat/proactive - 主动商机发现",
            "agent_status": "/api/agent/status - Agent 运行状态",
        },
        "v1_6_commercial": {
            "quota": "/api/v1.6/quota",
            "billing": "/api/v1.6/billing",
            "packages": "/api/v1.6/packages",
            "tenants": "/api/v1.6/tenants",
        },
        "p6_features": {
            "auth": "/api/p6/auth",
            "payment": "/api/p6/payment",
            "invoice": "/api/p6/invoice",
            "trial": "/api/p6/subscription/trial",
            "score_recommend": "/api/p6/score",
        },
        "p7_features": {
            "user_contributions": "/api/p7/contributions",
            "community_votes": "/api/p7/contributions/{id}/vote",
            "points_system": "/api/p7/points",
            "open_api_platform": "/api/p7/open-api",
        },
        "v1_5_realtime": {
            "websocket": "/api/stream/ws (WebSocket)",
            "subscribe": "POST /api/stream/subscribe",
            "unsubscribe": "POST /api/stream/unsubscribe",
            "subscriptions": "GET /api/stream/subscriptions",
            "history": "POST /api/stream/history",
            "stats": "GET /api/stream/stats",
            "publish": "POST /api/stream/publish",
            "health": "GET /api/stream/health",
        },
        "endpoints": {
            "opportunities": "/api/opportunities",
            "trends": "/api/trends",
            "agent_tools": "/api/agent/tools",
            "agent_workflows": {
                "discover": "POST /api/agent/workflow/discover",
                "analyze": "POST /api/agent/workflow/analyze",
                "export": "POST /api/agent/workflow/export/{opp_id}",
            },
            "intelligence": {
                "events": "/api/intelligence/events",
                "graph": "/api/intelligence/graph",
                "alerts": "/api/intelligence/alerts",
                "trend_analysis": "/api/intelligence/trend",
            },
            "investment_chain": {
                "list": "/api/investment/list",
                "network": "/api/investment/network",
                "trend": "/api/investment/trend",
                "path": "/api/investment/path",
                "investor_profile": "/api/investment/investor/{investor_name}",
            },
            "equity_analysis": {
                "ownership": "/api/equity/ownership/{company_id}",
                "shareholders": "/api/equity/shareholders/{company_id}",
                "beneficial_owners": "/api/equity/beneficial-owners/{company_id}",
                "actual_controllers": "/api/equity/actual-controllers/{company_id}",
                "tree": "/api/equity/tree/{company_id}",
            },
            "ml_prediction": {
                "forecast_industries": "/api/ml/forecast/industries",
                "forecast_industry": "/api/ml/forecast/industry/{industry}",
                "hot_industries": "/api/ml/forecast/hot-industries",
                "trending_investors": "/api/ml/trending-investors",
                "sentiment": "/api/ml/sentiment",
                "opportunity_score": "/api/ml/opportunity-score/{industry}",
                "classify_news": "POST /api/ml/classify/news",
            },
            "data_sources": {
                "status": "/api/data/sources/status",
                "configure": "POST /api/data/sources/{type}/configure",
                "cache_clear": "POST /api/data/sources/cache/clear",
                "query": {
                    "enterprise": "/api/data/query/enterprise",
                    "financing": "/api/data/query/financing",
                    "patent": "/api/data/query/patent",
                    "news": "/api/data/query/news",
                },
            },
            "p6_score_recommend": {
                "score_opportunity": "POST /api/p6/score/opportunity",
                "get_score": "GET /api/p6/score/{opportunity_id}",
                "predict_success": "POST /api/p6/ml/predict-success",
                "recommend": "POST /api/p6/recommend",
                "policy_search": "GET /api/p6/policy/search",
                "supply_chain": "GET /api/p6/supply-chain/{company_name}",
                "health_status": "GET /api/p6/health/sources",
            },
            "p6_auth": {
                "register": "POST /api/p6/auth/register",
                "login": "POST /api/p6/auth/login",
                "me": "GET /api/p6/auth/me",
                "subscription_plans": "GET /api/p6/auth/subscription/plans",
                "my_subscription": "GET /api/p6/auth/subscription/my-plan",
                "upgrade_subscription": "POST /api/p6/auth/subscription/upgrade",
                "usage_stats": "GET /api/p6/auth/usage/stats",
                "audit_logs": "GET /api/p6/auth/audit-logs",
            },
            "p6_payment": {
                "create_order": "POST /api/p6/payment/create-order",
                "get_order": "GET /api/p6/payment/orders/{order_id}",
                "initiate_payment": "POST /api/p6/payment/pay/{order_id}",
                "payment_methods": "GET /api/p6/payment/methods",
                "refund": "POST /api/p6/payment/refund/{order_id}",
                "invoice_request": "POST /api/p6/invoice/request",
                "invoice_history": "GET /api/p6/invoice/history",
                "start_trial": "POST /api/p6/subscription/start-trial",
                "trial_status": "GET /api/p6/subscription/trial-status",
            },
            "v1_6_billing": {
                "quota_record": "POST /api/v1.6/quota/record-usage",
                "quota_check": "POST /api/v1.6/quota/check",
                "quota_configs": "GET /api/v1.6/quota/configs",
                "billing_account": "GET /api/v1.6/billing/account",
                "billing_item": "POST /api/v1.6/billing/item",
                "packages": "GET /api/v1.6/packages",
                "purchase_package": "POST /api/v1.6/packages/purchase",
                "tenants": "POST /api/v1.6/tenants",
                "tenant_users": "GET /api/v1.6/tenants/{tenant_id}/users",
                "sso_config": "POST /api/v1.6/tenants/{tenant_id}/sso",
            },
            "v1_7_ml_enhanced": {
                "enhanced_score": "POST /api/v1.7/ml/enhanced-score",
                "trend_prediction": "POST /api/v1.7/ml/trend-prediction",
                "compare_opportunities": "POST /api/v1.7/ml/compare-opportunities",
                "ml_insights": "GET /api/v1.7/ml/insights",
                "hot_industries": "GET /api/v1.7/ml/hot-industries",
            },
            "v1_8_enterprise": {
                "white_label": "POST /api/v1.8/enterprise/white-label",
                "sso_session": "POST /api/v1.8/enterprise/sso/session",
                "api_apps": "POST /api/v1.8/open-api/apps",
                "webhooks": "POST /api/v1.8/webhooks",
                "enterprise_features": "GET /api/v1.8/enterprise/features",
            },
            "v1_9_ecosystem": {
                "market_apps": "GET /api/v1.9/market/apps",
                "connectors": "GET /api/v1.9/connectors",
                "developer_profile": "POST /api/v1.9/developer/profile",
                "data_partners": "GET /api/v1.9/data-partners",
                "docs": "GET /api/v1.9/docs",
                "sdks": "GET /api/v1.9/sdks",
            },
            "audit_logs": "/api/agent/audit-logs",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/agent/status")
async def agent_status():
    """获取 Agent 运行时状态"""
    from agents.opportunity_agent import get_opportunity_agent

    agent = get_opportunity_agent()

    return {
        "deerflow_available": agent.df_client is not None if agent.df_client else False,
        "tools_registered": len(agent.tools_registry),
        "audit_logs_count": len(agent._audit_logs),
        "tools_schema": agent.get_tools_schema(),
        "push_callbacks_registered": len(agent.push_callbacks),
    }

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("PORT", 8009))
    uvicorn.run(app, host="0.0.0.0", port=port)
