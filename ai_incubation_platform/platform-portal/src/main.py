"""
AI Incubation Platform - Portal
AI Native 统一入口门户

这是平台的统一入口，提供：
- 对话式交互界面
- 智能意图识别
- 路由分发到子项目
- 跨项目工作流编排
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import settings
from api.chat import router as chat_router
from api.workflows import router as workflows_router
from api.tools import router as tools_router

# 配置日志
logging.basicConfig(
    level=logging.INFO if settings.debug else logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# 创建 FastAPI 应用
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI 孵化平台统一门户 - 通过自然语言对话访问所有子项目能力",
    docs_url="/docs",
    redoc_url="/redoc",
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["root"])
async def root():
    """根路径 - 门户介绍"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "description": "AI Native 统一入口门户",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", tags=["health"])
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "platform-portal",
        "version": settings.app_version,
    }


# 注册路由
app.include_router(chat_router)
app.include_router(workflows_router)
app.include_router(tools_router)


@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info("AI Native Portal initialized")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info("Shutting down portal")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
