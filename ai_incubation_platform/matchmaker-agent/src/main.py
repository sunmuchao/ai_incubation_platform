import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

"""
红娘 Agent - 主入口 - 数据库版本

P0 优化：
- 集成 API 限流中间件
- 增强健康检查端点
- 添加缓存统计端点

v1.23 新增：
- 性能优化仪表板
- 慢查询日志
- 缓存预热机制

AI Native 转型：
- 对话式匹配 API
- 自主匹配工作流
- 审计日志系统
"""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from api.users import router as users_router
from api.matching import router as matching_router
from api.behavior import router as behavior_router
from api.relationship import router as relationship_router
from api.activities import router as activities_router
from api.conversations import router as conversations_router
# P4 新增路由
from api.photos import router as photos_router
from api.identity_verification import router as identity_router
from api.chat import router as chat_router
from db.database import init_db, engine
from config import settings
from utils.logger import logger
from middleware import RateLimitMiddleware
from cache import cache_manager

app = FastAPI(
    title="Matchmaker Agent",
    description="AI 红娘匹配系统（带 JWT 认证和 SQLite 持久化）",
    version="1.23.0",
    debug=settings.debug
)

# 配置 CORS
def get_cors_allow_origins(environment: str, cors_allowed_origins: list) -> list:
    """
    生产环境禁止使用 "*"，要求显式配置可信域名列表（逗号分隔）。
    """
    return ["*"] if environment != "production" else cors_allowed_origins


allow_origins = get_cors_allow_origins(settings.environment, settings.cors_allowed_origins)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册限流中间件
app.add_middleware(RateLimitMiddleware, excluded_paths=["/health", "/docs", "/openapi.json", "/"])

# 初始化数据库
@app.on_event("startup")
async def startup_event():
    """应用启动时初始化数据库"""
    logger.info(f"Starting Matchmaker Agent v{settings.app_version} in {settings.environment} environment")
    logger.info(f"Server listening on {settings.server_host}:{settings.server_port}")
    init_db()
    # 初始化缓存管理器
    cache_manager.get_instance()
    logger.info(f"Cache manager initialized, redis_available={cache_manager.get_cache_stats().get('redis_available', False)}")

    # v1.23: 初始化性能服务并启动缓存预热
    from services.performance_service import perf_service
    logger.info("Performance service initialized")

    # AI Native: 初始化审计日志系统
    from db.audit import init_audit
    init_audit()
    logger.info("Audit logging system initialized")

# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # 避免在日志里输出异常字符串，防止泄露 token/JWT/敏感字段
    logger.error("Unhandled exception", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )

# 注册路由
app.include_router(users_router)
app.include_router(matching_router)
app.include_router(behavior_router)
app.include_router(relationship_router)
app.include_router(activities_router)
app.include_router(conversations_router)
# P4 新增路由
app.include_router(photos_router)
app.include_router(identity_router)
app.include_router(chat_router)
# P5 新增：会员订阅路由
from api.membership import router as membership_router
app.include_router(membership_router)
# P6 新增：视频通话、信任标识、AI 陪伴、关系偏好、对话分析升级
from api.video import router as video_router
from api.verification_badges import router as verification_router
from api.ai_companion import router as companion_router
from api.relationship_preferences import router as relationship_pref_router
from api.recommendation import router as recommendation_router
from api.conversations_v2 import router as conversations_v2_router
from api.safety import router as safety_router
app.include_router(video_router)
app.include_router(verification_router)
app.include_router(companion_router)
app.include_router(relationship_pref_router)
app.include_router(recommendation_router)
app.include_router(conversations_v2_router)
# P7 新增：安全风控 AI
app.include_router(safety_router)
# P8 新增：企业数据看板、绩效管理、组织架构
from api.p8_apis import (
    router_dashboard,
    router_performance,
    router_departments,
    router_operators,
    router_exports
)
app.include_router(router_dashboard)
app.include_router(router_performance)
app.include_router(router_departments)
app.include_router(router_operators)
app.include_router(router_exports)

# P9 新增：推送通知系统、分享机制
# 导入模型以确保表被创建
from models import p9_models
from api.p9_apis import router_notifications, router_share
app.include_router(router_notifications)
app.include_router(router_share)

# P10 新增：关系里程碑追踪增强、约会建议引擎、双人互动游戏
# 导入模型以确保表被创建
from models import p10_models
from api.p10_apis import router_milestones, router_date_suggestions, router_couple_games
app.include_router(router_milestones)
app.include_router(router_date_suggestions)
app.include_router(router_couple_games)

# v1.2 新增：付费功能闭环（优惠券、退款、发票、试用、订阅）
from models import payment
from db import payment_models
from api.payment import router as payment_router
app.include_router(payment_router)

# v1.3 新增：视频约会功能（预约管理、互动小工具、安全保护）
from db.models import VideoDateDB, VideoDateReportDB, IcebreakerQuestionDB, GameSessionDB, VirtualBackgroundDB, UserBlockDB
from api.video_date import router as video_date_router
app.include_router(video_date_router)

# v1.18 新增：关系进阶功能（关系状态管理、约会建议、恋爱指导、聊天建议、礼物推荐、关系健康度）
from models import p18_models
from api.p18_apis import router as p18_router
app.include_router(p18_router)

# v1.23 新增：性能优化路由
from api.performance import router as performance_router
app.include_router(performance_router)

# AI Native 新增：对话式匹配 API
from api.conversation_matching import router as conversation_matching_router
app.include_router(conversation_matching_router)

@app.get("/")
async def root():
    return {
        "message": "欢迎使用红娘 Agent 平台",
        "status": "running",
        "version": "1.23.0",
        "features": [
            "JWT 认证", "SQLite 持久化", "AI 匹配算法", "缓存加速", "API 限流",
            "动态画像", "关系追踪", "活动推荐", "照片管理", "实名认证", "实时聊天",
            "会员订阅", "视频通话", "信任标识", "AI 陪伴", "行为学习", "安全风控 AI",
            "对话分析助手", "企业数据看板", "绩效管理", "组织架构", "推送通知",
            "分享机制", "关系里程碑追踪", "约会建议引擎", "双人互动游戏",
            "付费功能闭环", "视频约会", "关系进阶功能",
            "性能监控仪表板", "慢查询日志", "缓存预热",  # v1.23 新增
            "对话式匹配", "自主匹配推荐", "关系健康度分析", "智能破冰助手"  # AI Native 新增
        ],
        "endpoints": {
            "users": "/api/users",
            "matching": "/api/matching",
            "behavior": "/api/behavior",
            "relationship": "/api/relationship",
            "activities": "/api/activities",
            "conversations": "/api/conversations",
            "photos": "/api/photos",
            "identity": "/api/auth",
            "chat": "/api/chat",
            "membership": "/api/membership",
            "video": "/api/video",
            "verification": "/api/verification",
            "companion": "/api/companion",
            "relationship-pref": "/api/relationship/preferences",
            "recommendation": "/api/recommendation",
            "safety": "/api/safety",
            "dashboard": "/api/dashboard",
            "performance": "/api/performance",
            "departments": "/api/departments",
            "operators": "/api/operators",
            "exports": "/api/exports",
            "register": "/api/users/register",
            "login": "/api/users/login",
            "refresh": "/api/users/refresh",
            "docs": "/docs",
            "relationship-state": "/api/relationship/state",
            "dating-advice": "/api/dating-advice",
            "love-guidance": "/api/love-guidance",
            "chat-suggestion": "/api/chat-suggestion",
            "gift-recommendation": "/api/gift-recommendation",
            "relationship-health": "/api/relationship/health",
            # v1.23 新增
            "performance-dashboard": "/api/performance/dashboard",
            "slow-queries": "/api/performance/slow-queries",
            "api-stats": "/api/performance/api-stats",
            "cache-stats": "/api/performance/cache/stats",
            # AI Native 新增
            "conversation-match": "/api/conversation-matching/match",
            "daily-recommend": "/api/conversation-matching/daily-recommend",
            "relationship-analyze": "/api/conversation-matching/relationship/analyze",
            "topic-suggest": "/api/conversation-matching/topics/suggest",
            "compatibility": "/api/conversation-matching/compatibility/{user_id}",
            "ai-push": "/api/conversation-matching/ai/push/recommendations"
        }
    }

@app.get("/health")
async def health_check():
    """
    增强的健康检查端点

    检查项：
    - 数据库连接
    - 缓存状态
    - 限流统计
    - v1.23: 性能健康状态
    """
    health_status = {
        "status": "healthy",
        "version": "1.23.0",
        "checks": {}
    }

    # 检查数据库连接
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        health_status["checks"]["database"] = "ok"
    except Exception as e:
        health_status["checks"]["database"] = f"error: {str(e)}"
        health_status["status"] = "degraded"

    # 检查缓存状态
    cache_stats = cache_manager.get_cache_stats()
    health_status["checks"]["cache"] = {
        "redis_connected": cache_stats.get("redis_connected", False),
        "memory_cache_size": cache_stats.get("memory_cache_size", 0),
        "cache_hit_rate": cache_stats.get("cache_hit_rate", 0)
    }

    # 限流统计
    from middleware import rate_limiter
    health_status["rate_limit_stats"] = rate_limiter.get_stats()

    # v1.23: 性能健康检查
    try:
        from services.performance_service import perf_service
        perf_health = perf_service.performance_monitor.get_api_stats()
        health_status["performance"] = {
            "api_error_rate": perf_health.get("error_rate", 0),
            "avg_response_time_ms": perf_health.get("avg_response_time", 0)
        }
    except Exception as e:
        logger.warning(f"Performance check failed: {e}")

    return health_status

@app.get("/metrics")
async def get_metrics():
    """
    获取系统指标（用于 Prometheus/Grafana 集成）

    返回：
    - 缓存统计
    - 限流统计
    - 匹配系统统计
    - v1.23: 性能统计
    """
    from matching.matcher import matchmaker
    from middleware import rate_limiter
    from services.performance_service import perf_service

    return {
        "cache": cache_manager.get_cache_stats(),
        "rate_limiter": rate_limiter.get_stats(),
        "matching": {
            "registered_users": len(matchmaker._users),
            "interest_categories": len(matchmaker._interest_popularity),
        },
        "performance": {
            "uptime_seconds": perf_service.performance_monitor.get_uptime().total_seconds(),
            "slow_queries_count": perf_service.slow_query_logger.get_stats().get("total_slow_queries", 0)
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.server_host, port=settings.server_port)
