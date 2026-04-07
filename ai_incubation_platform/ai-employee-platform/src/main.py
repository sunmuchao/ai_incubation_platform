"""
AI 员工出租平台 - 主入口
"""
from fastapi import FastAPI
from contextlib import asynccontextmanager

# Lifespan 事件处理器
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化数据库
    from config.database import init_db
    init_db()
    print("数据库初始化完成")
    yield
    # 关闭时清理资源
    print("应用关闭")

app = FastAPI(
    title="AI Employee Platform",
    description="AI 员工出租和雇佣平台",
    version="21.0.0",  # V21.0.0 - AI Native 转型完成 (DeerFlow 2.0)
    lifespan=lifespan
)

# ==================== 导入路由 ====================
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
from api.observability_enhanced import router as observability_enhanced_router
from api.training import router as training_router
from api.websocket import router as websocket_router
from api.notifications_push import router as notifications_router
# P6 新增路由
from api.payment import router as payment_router
# P7 新增路由
from api.matching import router as matching_router
from api.certifications import router as certifications_router
from api.training_effectiveness import router as training_effectiveness_router
from api.proposals_enhanced import router as proposals_enhanced_router
# P8 新增路由
from api.p8_apis import router as p8_router
from api.wallet_enhanced import router as wallet_enhanced_router
# P9 新增路由
from api.capability_graph import router as capability_graph_router
from api.workflows import router as workflows_router
from api.search_enhanced import router as search_enhanced_router
# P11 新增路由
from api.marketplace_enhanced import router as marketplace_enhanced_router
# P12 新增路由
from api.matching_v2 import router as matching_v2_router
# P13 新增路由
from api.training_effectiveness_v2 import router as training_effectiveness_v2_router
# P14 新增路由
from api.performance import router as performance_router
# P15 新增路由
from api.wellness import router as wellness_router
# P16 新增路由
from api.career_development import router as career_development_router
# P17 新增路由
from api.p17_remote_work import router as remote_work_router
# P18 新增路由
from api.p18_culture import router as culture_router
# P19 新增路由
from api.p19_assistant import router as assistant_router
# P20 AI Native 路由 - DeerFlow 2.0
from api.chat import router as chat_router

# 导入 DeerFlow 集成
try:
    from deerflow_integration import is_deerflow_available
except ImportError:
    is_deerflow_available = lambda: False

# 导入本地 DeerFlow 客户端
try:
    from agents import is_deerflow_available as local_deerflow_available
except ImportError:
    local_deerflow_available = lambda: False

# ==================== 注册安全中间件 ====================
from middleware.security import setup_security_middleware
setup_security_middleware(app)

# ==================== 注册路由 ====================
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
app.include_router(observability_enhanced_router)
app.include_router(training_router)
app.include_router(websocket_router)
app.include_router(notifications_router)
# P6 新增路由注册
app.include_router(payment_router)
# P7 新增路由注册
app.include_router(matching_router)
app.include_router(certifications_router)
app.include_router(training_effectiveness_router)
app.include_router(proposals_enhanced_router)
# P8 新增路由注册
app.include_router(p8_router)
app.include_router(wallet_enhanced_router)
# P9 新增路由注册
app.include_router(capability_graph_router)
app.include_router(workflows_router)
app.include_router(search_enhanced_router)
# P11 新增路由注册
app.include_router(marketplace_enhanced_router)
# P12 新增路由注册
app.include_router(matching_v2_router)
# P13 新增路由注册
app.include_router(training_effectiveness_v2_router)
# P14 新增路由注册
app.include_router(performance_router)
# P15 新增路由注册
app.include_router(wellness_router)
# P16 新增路由注册
app.include_router(career_development_router)
# P17 新增路由注册
app.include_router(remote_work_router)
# P18 新增路由注册
app.include_router(culture_router)
# P19 新增路由注册
app.include_router(assistant_router)
# P20 AI Native 路由注册 - DeerFlow 2.0
app.include_router(chat_router)


@app.get("/")
async def root():
    return {
        "message": "欢迎使用 AI 员工平台",
        "status": "running",
        "version": app.version,
        "description": "可训练、可计价、可审计的「数字员工」市场平台",
        "ai_native_features": {
            "deerflow_2_0": True,
            "talent_agent": True,
            "career_workflows": True,
            "chat_interface": True
        },
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
            "observability-enhanced": "/api/observability-enhanced",
            "websocket": "/api/ws",
            "notifications": "/api/notifications",
            # P6 新增端点
            "payment": "/api/payment",
            # P7 新增端点
            "matching": "/api/matching",
            "certifications": "/api/certifications",
            "training-effectiveness": "/api/training-effectiveness",
            "proposals-enhanced": "/api/proposals-enhanced",
            # P8 新增端点
            "enterprise": "/api/enterprise",
            "performance": "/api/performance",
            "departments": "/api/departments",
            "webhooks": "/api/webhooks",
            "exports": "/api/exports",
            "wallet-enhanced": "/api/wallet",
            # P9 新增端点
            "capability-graph": "/api/ai-capability-graph",
            "workflows": "/api/workflows",
            "search": "/api/marketplace/search",
            "marketplace-enhanced": "/api/marketplace-enhanced",
            "matching-v2": "/api/matching-v2",
            "training-effectiveness-v2": "/api/training-effectiveness-v2",
            "performance": "/api/performance",
            "wellness": "/api/wellness",
            "career-development": "/api/career-development",
            # P17 新增端点
            "remote-work": "/api/remote-work",
            # P18 新增端点
            "culture": "/api/culture",
            # P19 新增端点
            "assistant": "/api/assistant",
            # P20 AI Native 端点
            "chat": "/api/chat",
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
            "通知推送服务",
            # P6 新增功能
            "真实支付对接 (支付宝/微信/Stripe)",
            "API 限流防护",
            "安全头增强",
            "请求日志脱敏",
            # P7 新增功能
            "智能匹配算法",
            "技能认证考试",
            "训练效果评估",
            "提案系统增强",
            # P8 新增功能
            "企业数据看板",
            "绩效管理",
            "组织架构管理",
            "Webhook 集成",
            "数据导出报告",
            "钱包充值与自动扣费",
            # P9 新增功能
            "AI 能力图谱",
            "自动化工作流",
            "高级搜索与筛选",
            # P11 新增功能
            "市场排行榜",
            "精选推荐",
            "技能趋势分析",
            "个性化推荐",
            # P12 新增功能
            "向量相似度匹配",
            "文化适配度评估",
            "历史表现加权增强",
            "薪资期望匹配分析",
            "可解释性报告生成",
            # P13 新增功能
            "培训前后技能对比",
            "培训 ROI 计算",
            "学习路径推荐",
            "培训效果追踪",
            "技能认证集成",
            # P14 新增功能
            "360 度评估反馈",
            "OKR 目标管理",
            "绩效仪表盘",
            "1 对 1 会议记录",
            "晋升推荐",
            # P15 新增功能
            "心理健康支持",
            "工作生活平衡",
            "福利管理",
            "员工满意度调查",
            "离职风险预测",
            # P16 新增功能
            "技能图谱管理",
            "职业路径推荐",
            "发展计划制定",
            "导师匹配系统",
            "晋升准备度评估",
            # P17 新增功能
            "远程工作会话管理",
            "在线状态追踪",
            "虚拟工作空间",
            "工作活动记录",
            "团队活动管理",
            "时区协调",
            "虚拟茶水间社交",
            "远程工作政策",
            "远程工作指标分析",
            # P18 新增功能
            "文化价值观管理",
            "员工认可与奖励",
            "徽章系统",
            "团队凝聚力建设",
            "文化契合度评估",
            "多样性与包容性",
            "文化脉冲调查",
            "积分兑换系统",
            # P19 新增功能
            "智能工作助手",
            "日程管理优化",
            "会议摘要生成",
            "工作简报自动化",
            # P20 AI Native 功能 (DeerFlow 2.0)
            "TalentAgent 人才智能体",
            "自主人才匹配工作流",
            "自主职业发展规划工作流",
            "对话式交互接口",
            "工具注册表系统",
            "审计日志追踪"
        ],
        "security_features": {
            "rate_limiting": True,
            "security_headers": True,
            "cors_restricted": True,
            "jwt_enhanced": True,
            "request_logging": True,
        },
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
            "notification_push",
            # P6 新增
            "real_payment_gateway",
            "api_rate_limiting",
            "security_headers",
            "request_logging",
            # P7 新增
            "smart_matching",
            "skill_certification",
            "training_effectiveness",
            "enhanced_proposals",
            # P8 新增
            "enterprise_dashboard",
            "performance_management",
            "organization_structure",
            "webhook_integration",
            "data_export",
            # P9 新增
            "capability_graph",
            "workflow_automation",
            "advanced_search"
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
            "payment": ["alipay", "wechat_pay", "stripe", "balance", "refund"],
            "proposal": ["create", "list", "accept", "reject", "cancel"],
            "time_tracking": ["start_session", "pause", "resume", "end", "log_work", "approve"],
            "escrow": ["create", "fund", "release", "refund", "dispute"],
            "messaging": ["send", "read", "edit", "delete", "conversation"],
            "dispute": ["create", "submit_evidence", "resolve", "escalate"],
            # P5 新增能力
            "file": ["upload", "download", "delete", "list", "storage_usage"],
            "observability": ["execution_tracking", "token_statistics", "work_log", "dashboard"],
            "websocket": ["connect", "realtime_push", "offline_message", "presence"],
            "notification": ["send", "read", "history", "unread_count"],
            # P6 新增能力
            "security": ["rate_limiting", "security_headers", "request_logging"],
            # P7 新增能力
            "matching": ["skill_match", "performance_ranking", "preference_filter", "price_matching", "timezone_match", "language_match", "time_availability", "match_cache"],
            "certification": ["exam_create", "question_manage", "exam_take", "auto_grade", "certificate_issue"],
            "training_effectiveness": ["task_tracking", "accuracy_analysis", "feedback_integration", "capability_scoring"],
            # P8 新增能力
            "enterprise_dashboard": ["metrics_view", "trend_analysis", "chart_generation", "top_employees"],
            "performance": ["review_create", "review_read", "history_track", "kpi_define"],
            "department": ["create", "read", "update", "delete", "tree_view"],
            "webhook": ["subscription_manage", "event_trigger", "delivery_track"],
            "export": ["report_create", "report_download", "template_manage"],
            "wallet_enhanced": ["recharge", "auto_deduction", "installment_payment", "transfer"],
            # P9 新增能力
            "capability_graph": ["get_graph", "similar_employees", "evolution_path", "industry_benchmark"],
            "workflow": ["create", "execute", "list", "activate", "archive"],
            "search": ["advanced_search", "filters", "save_search"],
            # P11 新增能力
            "marketplace_enhanced": ["rankings", "featured", "trending_skills", "personalized_recommendations", "market_stats"],
            # P12 新增能力
            "matching_v2": ["vector_similarity", "cultural_fit", "performance_weighted", "salary_analysis", "explanation_generation", "enhanced_match"],
            # P13 新增能力
            "training_effectiveness_v2": ["pre_post_assessment", "skill_comparison", "roi_calculation", "learning_path_recommendation", "impact_tracking", "certification_integration", "comprehensive_report"],
            # P14 新增能力
            "performance": ["review_cycle_manage", "performance_review", "review_dimension", "okr_objective", "okr_key_result", "performance_metrics", "one_on_one_meeting", "action_item", "promotion_recommendation", "performance_benchmark"],
            # P15 新增能力
            "wellness": ["mental_health_assessment", "stress_level_tracking", "counseling_session", "work_hour_log", "overtime_management", "work_life_balance", "benefit_plan", "leave_management", "satisfaction_survey", "turnover_prediction", "engagement_score", "wellness_alert"],
            # P16 新增能力
            "career_development": ["skill_graph", "employee_skill", "career_role", "career_path_recommendation", "development_plan", "development_goal", "mentorship_matching", "promotion_readiness_assessment"],
            # P17 新增能力
            "remote_work": ["session_management", "presence_tracking", "virtual_workspace", "work_activity", "team_event", "timezone_coordination", "virtual_water_cooler", "policy_management", "metrics_analysis"],
            # P18 新增能力
            "culture": ["culture_values", "recognition", "badge_system", "team_cohesion", "culture_fit_assessment", "diversity_metrics", "culture_pulse", "reward_redemption"],
            # P19 新增能力
            "assistant": ["task_recommendations", "smart_schedule", "meeting_management", "meeting_summary", "action_items", "auto_reports", "report_templates"],
            # P20 AI Native 能力 (DeerFlow 2.0)
            "talent_agent": ["analyze_profile", "match_opportunities", "plan_career", "track_performance", "proactive_scan"],
            "workflows": ["auto_talent_match", "auto_career_planning", "auto_performance_review", "auto_skill_gap_analysis"],
            "tools": ["analyze_employee_profile", "match_opportunities", "plan_career_path", "analyze_skill_gap", "recommend_learning_resources", "match_mentor"],
            "chat": ["career_plan", "skill_analysis", "opportunity_match", "performance_review", "learning_resources", "mentor_match"]
        },
        "integrations": {
            "deerflow_available": deerflow_available or local_deerflow_available(),
            "deerflow_version": "2.0" if (deerflow_available or local_deerflow_available()) else None,
            "local_deerflow_client": local_deerflow_available()
        },
        "payment_channels": {
            "alipay": {"available": True, "methods": ["wap", "qr", "app"]},
            "wechat_pay": {"available": True, "methods": ["native", "jsapi", "h5"]},
            "stripe": {"available": True, "methods": ["card", "alipay"]},
            "balance": {"available": True},
            "wallet_enhanced": {
                "auto_deduction": True,
                "installment_payment": True,
                "wallet_transfer": True
            }
        }
    }


@app.get("/security-info")
async def security_info():
    """
    安全配置信息接口

    显示当前生效的安全配置，用于运维监控
    """
    from config.settings import settings

    return {
        "security_config": {
            "jwt_secret_length": len(settings.jwt_secret) if settings.jwt_secret else 0,
            "jwt_access_token_expire_minutes": settings.jwt_access_token_expire_minutes,
            "jwt_refresh_token_expire_days": settings.jwt_refresh_token_expire_days,
            "cors_origins": settings.cors_origins,
            "environment": settings.environment,
            "is_production": settings.is_production(),
        },
        "rate_limiting": {
            "enabled": True,
            "rules": [
                {"path": "/api/login", "limit": "5/minute"},
                {"path": "/api/register", "limit": "3/minute"},
                {"path": "/api/password", "limit": "3/minute"},
                {"path": "/api/*", "limit": "100/minute"},
            ]
        },
        "security_headers": {
            "X-Frame-Options": "DENY",
            "X-Content-Type-Options": "nosniff",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
            "Content-Security-Policy": "default-src 'self'",
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
