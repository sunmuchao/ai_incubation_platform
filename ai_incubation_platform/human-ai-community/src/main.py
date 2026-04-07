"""
人 AI 共建社区 - 主入口
"""
import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from contextlib import asynccontextmanager

from api.community import router as community_router
from api.notifications import router as notification_router
from api.governance import router as governance_router
from api.moderator import router as moderator_router
from api.permissions import router as permissions_router
from api.webhooks import router as webhooks_router
from api.interaction import router as interaction_router
from api.search import router as search_router
from api.levels import router as level_router
from api.posts_hot import router as hot_posts_router
from api.channels import router as channels_router
from api.channel_enhanced import router as channel_enhanced_router
from api.user_groups import router as user_groups_router
from api.permission_audit import router as permission_audit_router
from api.websocket_notifications import router as websocket_router
from api.ai_features import router as ai_features_router
from api.admin import router as admin_router
from api.p6_features import router as p6_router
from api.p9_features import router as p9_router
from api.api_keys import router as api_keys_router
from api.p10_features import router as p10_router
from api.p11_features import router as p11_router
from api.economy import router as economy_router
from api.reputation import router as reputation_router
from api.feed import router as feed_router
from api.p16_features import router as p16_router
from api.p17_integration import router as p17_router
from api.i18n import router as i18n_router
from api.agent_chat import router as agent_chat_router
from api.generative_ui import router as generative_ui_router
from middleware.api_auth import APIAuthMiddleware
from services.community_service import community_service
from services.notification_service import notification_service, NotificationType, NotificationEvent, WebSocketNotificationAdapter
from services.websocket_notification_service import websocket_notification_service
from demo_data import init_demo_data
from core.logging_config import setup_logging, get_logger
from core.config import settings
from db.manager import db_manager

# 配置日志
setup_logging(
    level="DEBUG" if settings.debug else "INFO",
    log_to_file=settings.debug,
    log_file=f"logs/community_{settings.environment}.log" if settings.debug else None,
    log_format="colored" if settings.debug else "structured",
)

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    logger.info("应用启动中...")

    # 初始化数据库
    db_manager.initialize()
    await db_manager.init_tables()
    logger.info("数据库初始化完成")

    # 初始化演示数据
    if not community_service.list_members():
        logger.info("初始化演示数据...")
        init_demo_data()

    # 初始化通知服务
    _init_notification_defaults()

    # 初始化搜索索引
    await _init_search_index()

    logger.info(f"应用启动完成，端口：{settings.port}")

    yield

    # 关闭时清理
    logger.info("应用关闭中...")
    await db_manager.close()
    logger.info("应用已关闭")


app = FastAPI(
    title="Human-AI Community",
    description="人类和 AI 共建的社区平台",
    version="1.19.0",
    lifespan=lifespan,
)

# 添加 API 认证中间件
app.add_middleware(APIAuthMiddleware)

# 注册路由
app.include_router(community_router)
app.include_router(notification_router)
app.include_router(governance_router)
app.include_router(moderator_router)
app.include_router(permissions_router)
app.include_router(webhooks_router)
app.include_router(interaction_router)
app.include_router(search_router)
app.include_router(level_router)
app.include_router(hot_posts_router)
app.include_router(channels_router)
app.include_router(channel_enhanced_router)
app.include_router(user_groups_router)
app.include_router(permission_audit_router)
app.include_router(websocket_router)
app.include_router(ai_features_router)
app.include_router(admin_router)
app.include_router(p6_router)
app.include_router(p9_router)
app.include_router(api_keys_router)
app.include_router(p10_router)
app.include_router(p11_router)
app.include_router(economy_router)
app.include_router(reputation_router)
app.include_router(feed_router)
app.include_router(p16_router)
app.include_router(p17_router)
app.include_router(i18n_router)
app.include_router(agent_chat_router)
app.include_router(generative_ui_router)


def _init_notification_defaults():
    """初始化通知服务默认配置"""
    # 注册 WebSocket 适配器
    ws_adapter = WebSocketNotificationAdapter(websocket_notification_service)
    notification_service.register_adapter(ws_adapter)

    # 订阅内容审核事件，默认使用站内信通知
    notification_service.subscribe_event(
        NotificationEvent.CONTENT_APPROVED,
        [NotificationType.IN_APP]
    )
    notification_service.subscribe_event(
        NotificationEvent.CONTENT_REJECTED,
        [NotificationType.IN_APP]
    )
    notification_service.subscribe_event(
        NotificationEvent.REPLY_ADDED,
        [NotificationType.IN_APP]
    )
    notification_service.subscribe_event(
        NotificationEvent.REPORT_PROCESSED,
        [NotificationType.IN_APP]
    )
    notification_service.subscribe_event(
        NotificationEvent.RATE_LIMIT_WARNING,
        [NotificationType.IN_APP, NotificationType.EMAIL]
    )
    logger.info("通知服务默认配置初始化完成")


async def _init_search_index():
    """初始化搜索索引"""
    try:
        from services.search_service import SearchService
        async with db_manager.get_session() as db:
            search_service = SearchService(db)
            success = await search_service.init_search_index()
            if success:
                logger.info("搜索索引初始化完成")
            else:
                logger.info("搜索索引已存在，跳过初始化")
    except Exception as e:
        logger.error(f"搜索索引初始化失败：{e}")


@app.get("/")
async def root():
    return {
        "message": "欢迎使用人 AI 共建社区",
        "status": "running",
        "version": "1.20.0",
        "ai_native": True,
        "endpoints": {
            "members": "/api/members",
            "posts": "/api/posts",
            "comments": "/api/comments",
            "channels": "/api/channels",
            "channels-enhanced": "/api/channels (enhanced)",
            "user-groups": "/api/user-groups",
            "audit": "/api/audit",
            "ai-features": "/api/ai",
            "agent-chat": "/api/v2/chat",
            "generative-ui": "/api/v2/ui",
            "p6-features": "/api/p6",
            "p17-integration": "/api/p17",
            "i18n": "/api/i18n",
            "api-keys": "/api/api-keys",
            "webhooks": "/api/webhooks",
            "admin": "/api/admin",
            "docs": "/docs",
            "health": "/health",
            "websocket": "/api/ws/notifications",
            "reputation": "/api/reputation",
            "feed": "/api/feed"
        }
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "environment": settings.environment,
        "database": "connected" if db_manager._initialized else "not_initialized"
    }


@app.get("/api/health/db")
async def db_health_check():
    """数据库健康检查"""
    try:
        # 尝试获取数据库连接
        from sqlalchemy import text
        async with db_manager._session_factory() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"数据库健康检查失败：{e}")
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}


if __name__ == "__main__":
    import uvicorn
    # 确保 logs 目录存在
    os.makedirs("logs", exist_ok=True)
    uvicorn.run(app, host="0.0.0.0", port=settings.port)
