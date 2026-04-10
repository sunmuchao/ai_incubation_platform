import sys
import os
import json
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

P20 重构：
- 使用统一路由注册中心（routers/__init__.py）
- main.py 精简至 100 行以内
"""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from db.database import init_db, engine
from config import settings
from utils.logger import logger
from middleware import RateLimitMiddleware
from cache import cache_manager
from routers import register_all_routers, get_api_endpoints_summary

# 配置静态文件目录（头像图片）
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static')
os.makedirs(STATIC_DIR, exist_ok=True)

app = FastAPI(
    title="Matchmaker Agent",
    description="AI 红娘匹配系统（带 JWT 认证和 SQLite 持久化）",
    version="1.28.0",
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

# 挂载静态文件目录（头像图片）
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    logger.info(f"Static files mounted from {STATIC_DIR}")

# 初始化数据库
@app.on_event("startup")
async def startup_event():
    """应用启动时初始化数据库"""
    logger.info(f"Starting Matchmaker Agent v{settings.app_version} in {settings.environment} environment")
    logger.info(f"Server listening on {settings.server_host}:{settings.server_port}")

    # 系统重启时自动备份日志（保留历史日志记录）
    from utils.log_backup import backup_logs_on_startup
    backup_logs_on_startup()

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

    # AI Native: 初始化 Skills 注册表
    from agent.skills.registry import initialize_default_skills
    initialize_default_skills()
    logger.info("Skills registry initialized")

    # P1: 启动时检查 API 注册和 Skills 同步
    from utils.api_checker import check_api_registration
    from utils.skills_checker import check_skills_sync

    api_check = check_api_registration(raise_on_error=False)
    skills_check = check_skills_sync(raise_on_error=False)

    if api_check:
        logger.info("✅ API registration check passed")
    else:
        logger.warning("⚠️ API registration check failed, check /api/checker/api-registration for details")

    if skills_check:
        logger.info("✅ Skills sync check passed")
    else:
        logger.warning("⚠️ Skills sync check failed, check /api/checker/skills-sync for details")

    # 从数据库加载所有活跃用户到匹配器
    from db.repositories import UserRepository
    from matching.matcher import matchmaker
    from utils.db_session_manager import db_session

    with db_session() as db:
        user_repo = UserRepository(db)
        users = user_repo.list_all(is_active=True)
        loaded_count = 0
        for db_user in users:
            try:
                # 将数据库用户转换为匹配器需要的字典格式
                interests = []
                if db_user.interests:
                    try:
                        interests = json.loads(db_user.interests)
                    except json.JSONDecodeError:
                        interests = db_user.interests.split(",") if db_user.interests else []

                values = {}
                if db_user.values:
                    try:
                        values = json.loads(db_user.values)
                    except json.JSONDecodeError:
                        pass

                user_dict = {
                    "id": db_user.id,
                    "name": db_user.name,
                    "email": db_user.email,
                    "age": db_user.age,
                    "gender": db_user.gender,
                    "location": db_user.location,
                    "bio": db_user.bio or "",
                    "interests": interests,
                    "values": values,
                    "preferred_age_min": db_user.preferred_age_min or 18,
                    "preferred_age_max": db_user.preferred_age_max or 60,
                    "preferred_location": db_user.preferred_location,
                    "preferred_gender": db_user.preferred_gender,
                }
                matchmaker.register_user(user_dict)
                loaded_count += 1
            except Exception as e:
                logger.warning(f"Failed to load user {db_user.id} to matchmaker: {e}")
        logger.info(f"Loaded {loaded_count} users from database to matchmaker")

# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # 避免在日志里输出异常字符串，防止泄露 token/JWT/敏感字段
    logger.error("Unhandled exception", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )

# 注册路由（使用统一路由注册中心）
register_all_routers(app)

@app.get("/")
async def root():
    return {
        "message": "欢迎使用红娘 Agent 平台",
        "status": "running",
        "version": "1.28.0",
        "features": [
            "JWT 认证", "SQLite 持久化", "AI 匹配算法", "缓存加速", "API 限流",
            "动态画像", "关系追踪", "活动推荐", "照片管理", "实名认证", "实时聊天",
            "会员订阅", "视频通话", "信任标识", "AI 陪伴", "行为学习", "安全风控 AI",
            "对话分析助手", "企业数据看板", "绩效管理", "组织架构", "推送通知",
            "分享机制", "关系里程碑追踪", "约会建议引擎", "双人互动游戏",
            "付费功能闭环", "视频约会", "关系进阶功能",
            "性能监控仪表板", "慢查询日志", "缓存预热",
            "对话式匹配", "自主匹配推荐", "关系健康度分析", "智能破冰助手",
            "AI 视频面诊", "微表情捕捉", "语音情感分析", "位置安全监测", "语音异常检测", "分级响应机制",
            "共同经历检测", "尴尬沉默识别", "情境话题生成", "吵架预警", "爱之语翻译", "关系气象报告",
            "LLM 成本监控", "置信度阈值过滤",
            "爱之语画像", "关系趋势预测", "预警分级响应",
            "约会模拟沙盒", "AI 分身创建", "穿搭推荐", "场所策略", "话题锦囊",
            "自主约会策划", "情感纪念册",
            "部落匹配", "数字小家", "见家长模拟",
            "压力测试", "成长计划", "信任背书",
            "注册对话 AI 红娘",
            "LLM 深度语义匹配", "隐性情绪识别", "价值观偏好提取", "沟通模式分析",
            "AI 预沟通", "消费水平匹配", "地理轨迹匹配", "行为信用分", "防渣黑名单",
            "动态关系教练", "情境感知", "用户确权", "隐私透明", "可解释 AI"
        ],
        "endpoints": get_api_endpoints_summary()
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
        "version": "1.28.0",
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
