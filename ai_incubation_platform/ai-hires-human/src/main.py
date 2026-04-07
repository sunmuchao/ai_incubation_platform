"""
AI 雇佣真人平台 — 当 AI 无法独立完成（尤其真实世界交互）时，雇佣真人执行并回传结果。
"""
import os
import sys
from contextlib import asynccontextmanager

# 支持从仓库根目录执行：PYTHONPATH=src python src/main.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI

from api.meta import router as meta_router
from api.payment import router as payment_router
from api.tasks import router as tasks_router
from api.internal_callbacks import router as internal_callbacks_router
from api.worker_profile import router as worker_profile_router
from api.admin import router as admin_router
from api.reports import router as reports_router
from api.recommendations import router as recommendations_router
from api.quality import router as quality_router
from api.certifications import router as certifications_router
from api.reputation import router as reputation_router
from api.real_payment import router as real_payment_router
from api.batch_tasks import router as batch_tasks_router
from api.escrow import router as escrow_router
from api.enhanced_anti_cheat import router as enhanced_anti_cheat_router
# ===== v1.0.0 新增：P5 迭代功能 =====
from api.dashboard import router as dashboard_router
from api.team import router as team_router
from api.sla import router as sla_router

# ===== v1.1.0 新增：P6 阶段 AI 杀手级功能 =====
from api.task_decomposition import router as task_decomposition_router
from api.intelligent_acceptance import router as intelligent_acceptance_router
from api.quality_prediction import router as quality_prediction_router
from api.ai_anti_cheat import router as ai_anti_cheat_router

# ===== v1.2.0 新增：P7 阶段黄金标准测试 =====
from api.golden_standard import router as golden_standard_router

# ===== v1.3.0 新增：P8 阶段平台化功能 =====
from api.open_api import router as open_api_router
from api.data_contribution import router as data_contribution_router

# ===== v1.4.0 新增：P9 阶段国际化 =====
from api.i18n import router as i18n_router

# ===== v1.5.0 新增：P10 阶段高级分析与预测 =====
from api.analytics import router as analytics_router

# ===== v1.6.0 新增：P11 阶段移动端优化 =====
from api.mobile import router as mobile_router

# ===== v1.14.0 新增：P19 阶段区块链存证 =====
from api.blockchain import router as blockchain_router

# ===== v1.15.0 新增：P20 阶段智能合约支付 =====
from api.smart_contract import router as smart_contract_router

# ===== v1.16.0 新增：P21 阶段批量任务与团队匹配 =====
from api.team_matching import router as team_matching_router

# ===== v1.18.0 新增：P22 阶段质量保证增强 =====
from api.dispute_prevention import router as dispute_prevention_router
from api.quality_improvement import router as quality_improvement_router
from api.quality_dashboard import router as quality_dashboard_router

# ===== v1.19.0 新增：P23 阶段社交网络增强 =====
from api.social import router as social_router

# ===== v1.20.0 新增：P24 阶段职业发展支持 =====
from api.career_development import router as career_development_router

# ===== v1.21.0 新增：法律法规支持 =====
from api.legal_services import router as legal_services_router

# ===== v1.21.0 新增：隐私安全中心 =====
from api.privacy_security import router as privacy_security_router

# ===== v1.22.0 新增：用户体验优化 =====
from api.ux_theme import router as ux_theme_router
from api.ux_notifications import router as ux_notifications_router
from api.ux_feedback import router as ux_feedback_router
from api.ux_onboarding import router as ux_onboarding_router

# ===== v1.23.0 新增：P27 数据分析增强 =====
from api.analytics_enhanced import router as analytics_enhanced_router

# ===== v1.24.0 新增：AI Native 对话式交互 =====
from api.chat import router as chat_router

# ===== v1.25.0 新增：DeerFlow 2.0 Agent 架构 =====
# Agents 和 Tools 已在 src/agents 和 src/tools 中定义

# ===== 用户认证 =====
from api.auth import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理。"""
    # 启动时初始化
    from config.logging_config import setup_logging
    from services.callback_retry_service import callback_retry_service
    from services.team_service import TeamService
    from database import AsyncSessionLocal, Base, engine

    # 初始化日志系统
    setup_logging()

    # 创建数据库表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 启动回调重试调度器
    await callback_retry_service.start()

    # 初始化系统角色
    try:
        async with AsyncSessionLocal() as db:
            team_service = TeamService(db)
            await team_service.initialize_system_roles()
    except Exception as e:
        pass  # 忽略初始化错误

    yield

    # 关闭时清理
    await callback_retry_service.stop()


app = FastAPI(
    title="AI Hires Human",
    description=(
        "AI 因能力边界（线下到场、物理操作、合规人工判断等）发布任务，"
        "真人接单、交付，由 AI 雇主验收；默认创建即可接单。"
    ),
    version="1.24.0",
    lifespan=lifespan,
)

# 添加 CORS 中间件
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制为具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加限流中间件
from middleware.rate_limit import RateLimitMiddleware
app.add_middleware(RateLimitMiddleware)

app.include_router(tasks_router)
app.include_router(meta_router)
app.include_router(payment_router)
app.include_router(internal_callbacks_router)
app.include_router(worker_profile_router)
app.include_router(admin_router)
app.include_router(reports_router)
app.include_router(recommendations_router)
app.include_router(quality_router)
app.include_router(certifications_router)
app.include_router(reputation_router)
app.include_router(real_payment_router)
app.include_router(batch_tasks_router)
app.include_router(escrow_router)
app.include_router(enhanced_anti_cheat_router)
# ===== v1.0.0 新增：P5 迭代功能 =====
app.include_router(dashboard_router)
app.include_router(team_router)
app.include_router(sla_router)
# ===== v1.1.0 新增：P6 阶段 AI 杀手级功能 =====
app.include_router(task_decomposition_router)
app.include_router(intelligent_acceptance_router)
app.include_router(quality_prediction_router)
app.include_router(ai_anti_cheat_router)
# ===== v1.2.0 新增：P7 阶段黄金标准测试 =====
app.include_router(golden_standard_router)
# ===== v1.3.0 新增：P8 阶段平台化功能 =====
app.include_router(open_api_router)
app.include_router(data_contribution_router)
# ===== v1.4.0 新增：P9 阶段国际化 =====
app.include_router(i18n_router)
# ===== v1.5.0 新增：P10 阶段高级分析与预测 =====
app.include_router(analytics_router)
# ===== v1.6.0 新增：P11 阶段移动端优化 =====
app.include_router(mobile_router)
# ===== v1.14.0 新增：P19 阶段区块链存证 =====
app.include_router(blockchain_router)
# ===== v1.15.0 新增：P20 阶段智能合约支付 =====
app.include_router(smart_contract_router)
# ===== v1.16.0 新增：P21 阶段批量任务与团队匹配 =====
app.include_router(team_matching_router)
# ===== v1.18.0 新增：P22 阶段质量保证增强 =====
app.include_router(dispute_prevention_router)
app.include_router(quality_improvement_router)
app.include_router(quality_dashboard_router)
# ===== v1.19.0 新增：P23 阶段社交网络增强 =====
app.include_router(social_router)
# ===== v1.20.0 新增：P24 阶段职业发展支持 =====
app.include_router(career_development_router)
# ===== v1.21.0 新增：法律法规支持 =====
app.include_router(legal_services_router)
# ===== v1.21.0 新增：隐私安全中心 =====
app.include_router(privacy_security_router)
# ===== v1.22.0 新增：用户体验优化 =====
app.include_router(ux_theme_router)
app.include_router(ux_notifications_router)
app.include_router(ux_feedback_router)
app.include_router(ux_onboarding_router)
# ===== v1.23.0 新增：P27 数据分析增强 =====
app.include_router(analytics_enhanced_router)

# ===== v1.24.0 新增：AI Native 对话式交互 =====
app.include_router(chat_router)

# ===== 用户认证 =====
app.include_router(auth_router)


@app.get("/")
async def root():
    return {
        "message": "AI 雇佣真人平台",
        "vision": (
            "当 AI 要做一件事但做不到时（与真实世界交互、需肉身或人工签核），"
            "通过本平台雇佣真人完成，并把交付结果回传给上游 AI / Agent。"
        ),
        "status": "running",
        "version": "1.24.0",
        "endpoints": {
            "tasks": "/api/tasks",
            "task_search": "/api/tasks/search",
            "payment": "/api/payment",
            "real_payment": "/api/payment/real",  # 真实支付渠道
            "workers": "/api/workers",
            "admin": "/api/admin",
            "reports": "/api/reports",
            "agent_tools": "/api/meta/agent-tools",
            # ===== v0.7.0 新增：竞品对标优化功能 =====
            "recommendations": "/api/recommendations",  # 智能任务推荐
            "quality": "/api/quality",  # 质量控制（黄金标准、可信度）
            "certifications": "/api/certifications",  # 资格认证
            # ===== v0.8.0 新增：P3 功能 =====
            "reputation": "/api/reputation",  # 信誉体系
            # ===== v0.9.0 新增：P4 功能 =====
            "batch-tasks": "/api/batch-tasks",  # 批量任务管理（CSV 导入）
            "escrow": "/api/escrow",  # Escrow 资金托管
            "anti-cheat": "/api/anti-cheat",  # 增强反作弊（设备指纹、IP 检测、行为分析）
            # ===== v1.0.0 新增：P5 功能 =====
            "dashboard": "/api/dashboard",  # 实时数据仪表板
            "team": "/api/team",  # 团队权限管理
            "sla": "/api/sla",  # SLA 服务等级协议
            # ===== v1.1.0 新增：P6 功能 =====
            "task-decomposition": "/api/task-decomposition",  # AI 任务分解
            "intelligent-acceptance": "/api/intelligent-acceptance",  # 智能验收助手
            "quality-prediction": "/api/quality-prediction",  # 质量预测模型
            "ai-anti-cheat": "/api/ai-anti-cheat",  # 反作弊 AI 增强
            # ===== v1.2.0 新增：P7 功能 =====
            "golden-standard": "/api/golden-standard",  # 黄金标准测试与认证
            # ===== v1.3.0 新增：P8 功能 =====
            "open-api": "/api/open",  # 开放 API（开发者门户）
            "contributions": "/api/contributions",  # 用户贡献数据机制
            # ===== v1.4.0 新增：P9 功能 =====
            "i18n": "/api/i18n",  # 国际化与多语言支持
            # ===== v1.5.0 新增：P10 功能 =====
            "analytics": "/api/analytics",  # 高级分析与预测
            # ===== v1.6.0 新增：P11 功能 =====
            "mobile": "/api/mobile",  # 移动端优化
            # ===== v1.14.0 新增：P19 功能 =====
            "blockchain": "/api/blockchain",  # 区块链存证
            # ===== v1.15.0 新增：P20 功能 =====
            "smart-contracts": "/api/smart-contracts",  # 智能合约支付
            # ===== v1.16.0 新增：P21 功能 =====
            "team-matching": "/api/team-matching",  # 团队匹配与批量任务分配
            # ===== v1.18.0 新增：P22 质量保证增强 =====
            "dispute-prevention": "/api/dispute-prevention",  # 争议预防与预警
            "quality-improvement": "/api/quality-improvement",  # 质量改进建议
            "quality-dashboard": "/api/quality-dashboard",  # 质量保证仪表板
            # ===== v1.19.0 新增：P23 社交网络增强 =====
            "social": "/api/social",  # 社交网络（动态、圈子、好友）
            # ===== v1.20.0 新增：P24 职业发展支持 =====
            "career": "/api/career",  # 职业发展支持（职业规划、技能提升、就业指导、创业支持、人脉拓展）
            # ===== v1.21.0 新增：法律法规支持 =====
            "legal": "/api/legal",  # 法律法规支持（合同模板、法务咨询、权益保护、税务规划、合规检查）
            # ===== v1.21.0 新增：隐私安全中心 =====
            "privacy-security": "/api/privacy-security",  # 隐私安全中心（设备管理、举报、安全课堂）
            # ===== v1.22.0 新增：用户体验优化 =====
            "ux-theme": "/api/ux/theme",  # 个性化主题设置（深色模式、强调色、字体大小）
            "ux-notifications": "/api/ux/notifications",  # 通知偏好设置（推送/邮件/短信、免打扰）
            "ux-feedback": "/api/ux/feedback",  # 用户反馈系统（bug 报告、功能建议）
            "ux-onboarding": "/api/ux/onboarding",  # 新手引导流程（任务清单、进度追踪）
            # ===== v1.23.0 新增：P27 数据分析增强 =====
            "analytics-enhanced": "/api/analytics",  # 数据分析增强（平台统计/用户行为/匹配效果/收入分析）
            # ===== v1.24.0 新增：AI Native 对话式交互 =====
            "chat": "/api/chat",  # 对话式交互（自然语言发布任务、查询、匹配）
            # ==============================
            "docs": "/docs",
        },
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("AI_HIRES_HUMAN_PORT", "8004"))
    uvicorn.run(app, host="0.0.0.0", port=port)
