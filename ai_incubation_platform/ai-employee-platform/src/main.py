"""
AI 员工出租平台 - 主入口
"""
from fastapi import FastAPI
from api.employees import router as employees_router
from api.marketplace import router as marketplace_router
from api.reviews import router as reviews_router
# P4 新增路由
from api.proposals import router as proposals_router
from api.time_tracking import router as time_tracking_router
from api.escrow import router as escrow_router
from api.messaging import router as messaging_router
from api.disputes import router as disputes_router
# P5 新增路由
from api.files import router as files_router
from api.observability import router as observability_router
from api.websocket import router as websocket_router
from api.notifications_push import router as notifications_router

# 导入 DeerFlow 集成
try:
    from deerflow_integration import is_deerflow_available
except ImportError:
    is_deerflow_available = lambda: False

app = FastAPI(
    title="AI Employee Platform",
    description="AI 员工出租和雇佣平台",
    version="0.6.0"  # P5 功能版本
)

# 注册路由
app.include_router(employees_router)
app.include_router(marketplace_router)
app.include_router(reviews_router)
# P4 新增路由注册
app.include_router(proposals_router)
app.include_router(time_tracking_router)
app.include_router(escrow_router)
app.include_router(messaging_router)
app.include_router(disputes_router)
# P5 新增路由注册
app.include_router(files_router)
app.include_router(observability_router)
app.include_router(websocket_router)
app.include_router(notifications_router)

@app.get("/")
async def root():
    return {
        "message": "欢迎使用 AI 员工平台",
        "status": "running",
        "version": app.version,
        "description": "可训练、可计价、可审计的「数字员工」市场平台",
        "endpoints": {
            "employees": "/api/employees",
            "orders": "/api/employees/orders/{order_id}",
            "marketplace": "/api/marketplace",
            "proposals": "/api/proposals",
            "time-tracking": "/api/time-tracking",
            "escrow": "/api/escrow",
            "messaging": "/api/messaging",
            "disputes": "/api/disputes",
            # P5 新增端点
            "files": "/api/files",
            "observability": "/api/observability",
            "websocket": "/api/ws",
            "notifications": "/api/notifications",
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
            "支付系统对接",
            "提案/投标系统",
            "时间追踪与工作验证",
            "支付托管 (Escrow)",
            "消息系统",
            "争议解决机制",
            # P5 新增功能
            "文件存储服务",
            "AI 可观测性面板",
            "WebSocket 实时消息",
            "通知推送服务"
        ],
        "integrations": {
            "deerflow_available": is_deerflow_available()
        }
    }

@app.get("/health")
async def health_check():
    """健康检查接口"""
    deerflow_available = is_deerflow_available()
    return {
        "status": "healthy",
        "version": app.version,
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
            "payment_processing",
            "proposal_bidding_system",
            "time_tracking_verification",
            "escrow_payment",
            "messaging_system",
            "dispute_resolution",
            # P5 新增
            "file_storage",
            "ai_observability",
            "websocket_realtime",
            "notification_push"
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
            "payment": ["multi_method_support", "wallet", "third_party_gateway"],
            "proposal": ["create", "list", "accept", "reject", "cancel"],
            "time_tracking": ["start_session", "pause", "resume", "end", "log_work", "approve"],
            "escrow": ["create", "fund", "release", "refund", "dispute"],
            "messaging": ["send", "read", "edit", "delete", "conversation"],
            "dispute": ["create", "submit_evidence", "resolve", "escalate"],
            # P5 新增能力
            "file": ["upload", "download", "delete", "list", "storage_usage"],
            "observability": ["execution_tracking", "token_statistics", "work_log", "dashboard"],
            "websocket": ["connect", "realtime_push", "offline_message", "presence"],
            "notification": ["send", "read", "history", "unread_count"]
        },
        "integrations": {
            "deerflow_available": deerflow_available,
            "deerflow_version": "2.0" if deerflow_available else None
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
