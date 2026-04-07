"""
AI 员工出租平台 - 主入口
版本：0.4.0 (数据库持久化重构版)
"""
from fastapi import FastAPI, Depends
import logging
from fastapi.security import HTTPBearer
import os
import sys

# 添加 src 到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入配置和日志
from config.database import engine, Base, init_db, get_db
from config.settings import settings
from config.logging_config import setup_logging

# 导入中间件
from middleware.logging import setup_middleware as setup_logging_middleware
from middleware.exceptions import setup_exception_handlers

# 导入路由
from api.employees import router as employees_router
from api.marketplace import router as marketplace_router

# 导入数据库模型（用于创建表）
from models import db_models  # noqa: F401

# 设置日志
setup_logging()
logger = logging.getLogger(__name__)

# 创建 FastAPI 应用
app = FastAPI(
    title=settings.app_name,
    description="可训练、可计价、可审计的数字员工市场平台",
    version=settings.app_version,
    debug=settings.debug
)

# 设置中间件
setup_logging_middleware(app)
setup_exception_handlers(app)

# 初始化数据库
@app.on_event("startup")
async def startup_event():
    """应用启动时初始化数据库"""
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialized successfully")

@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "欢迎使用 AI 员工平台",
        "status": "running",
        "version": settings.app_version,
        "description": settings.description if hasattr(settings, 'description') else "可训练、可计价、可审计的数字员工市场平台",
        "endpoints": {
            "employees": "/api/employees",
            "orders": "/api/employees/orders/{order_id}",
            "marketplace": "/api/marketplace",
            "health": "/health",
            "docs": "/docs",
            "openapi": "/openapi.json"
        },
        "core_features": [
            "AI 员工档案管理",
            "租赁订单状态机",
            "自动计费与分成",
            "能力搜索与评级",
            "交易审计可追溯",
            "训练数据版本化",
            "DeerFlow Agent 运行时对接",
            "评价评级系统",
            "基础风控能力",
            "多租户隔离",
            "统一身份认证",
            "用量统计与账单",
            "支付系统对接"
        ],
        "database": {
            "type": "SQLite" if settings.database_url.startswith("sqlite") else "PostgreSQL",
            "url": settings.database_url
        }
    }

@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "version": settings.app_version,
        "features": [
            "employee_management",
            "order_management",
            "billing_calculation",
            "marketplace_search",
            "rating_system",
            "training_data_versioning",
            "deerflow_agent_integration",
            "review_and_rating",
            "risk_management",
            "multi_tenant_isolation",
            "user_authentication",
            "usage_tracking",
            "invoicing_system",
            "payment_processing"
        ],
        "capabilities": {
            "employee": ["create", "read", "list", "search", "status_update", "training", "risk_check"],
            "order": ["create", "read", "confirm", "start", "complete", "cancel", "review"],
            "billing": ["auto_calculation", "platform_fee", "owner_earning"],
            "rating": ["post_completion", "average_calculation", "review_likes", "tagging"],
            "training": ["data_upload", "versioning", "deerflow_training", "model_versioning"],
            "risk": ["content_check", "risk_scoring", "risk_level", "blocking"],
            "tenant": ["create", "read", "list", "status_management", "quota_control"],
            "auth": ["user_management", "jwt_login", "role_based_access"],
            "usage": ["tracking", "statistics", "export"],
            "invoice": ["generate", "issue", "payment_tracking"],
            "payment": ["multi_method_support", "wallet", "third_party_gateway"]
        },
        "database": {
            "connected": True,
            "type": "SQLite" if settings.database_url.startswith("sqlite") else "PostgreSQL"
        }
    }

# 注册路由
app.include_router(employees_router, prefix="/api/employees", tags=["employees"])
app.include_router(marketplace_router, prefix="/api/marketplace", tags=["marketplace"])

if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting server on {settings.host}:{settings.port}")
    uvicorn.run(app, host=settings.host, port=settings.port)
