"""
AI 社区团购 - 主入口

版本历史:
- v4.0.0: AI Native 转型 - DeerFlow 2.0 Agent 框架/对话式交互/自主团购/智能选品/主动邀请
- v3.0.0: P10 项目总结与商业化就绪 - 10 轮迭代完成/商业化路线图/技术债务清单/竞品对标总结
- v2.8.0: P8 智能风控/信用体系 - 用户信用评分/欺诈检测/订单风控/黑名单管理/风控规则引擎
- v2.7.0: P7 游戏化运营 - 成就系统/排行榜/砍价玩法
- v2.6.0: P6 数据分析增强 - 销售报表/用户行为分析/商品分析/预测分析/自定义报表
- v2.5.0: P5 营销自动化系统 - 用户分群 (RFM 模型)/营销自动化/ROI 分析/A/B 测试/智能优惠券
- v2.4.0: P4 供应链与履约优化 - 库存预警/智能补货/供应商管理/采购订单
- v2.3.0: P3 用户增长与运营工具 - 邀请裂变/任务中心/会员成长体系/运营活动模板
- v2.2.0: P2 个性化推荐系统 - Wide&Deep 深度排序/用户特征工程/多样性控制
- v2.1.0: P1 需求预测模型升级 - Prophet+LSTM 融合预测/节假日因子/季节性因子
- v2.0.0: P0 AI 选品顾问增强 - 协同过滤/社区画像/季节性因子/节假日因子
- v1.1.0: P1 动态定价引擎 - 成团概率/需求弹性/竞品跟随/时间段/库存压力定价
- v1.0.0: P9 智能履约调度系统 - 路径优化算法 (VRP)+ 自提点人流预测 + 时间窗口推荐 + 异常处理
- v0.9.0: P0 AI 智能成团预测服务 - 基于回归模型 + 实时计算的成团概率预测
- v0.8.0: P7 阶段 - 游戏化运营 (成就/排行榜)/砍价玩法
- v0.7.0: P6 阶段 - 团长考核/售后流程/签到积分
- v0.6.0: P0(P5 增长引擎) - 限时秒杀/新人专享/拼单返现/库存紧张提示
- v0.5.0: P4 阶段 - 履约追踪/团长后台/AI 预测
- v0.4.0: P3 阶段 - 佣金/优惠券/分享裂变
- v0.3.0: P2 阶段 - 事务管理/乐观锁/结构化日志
- v0.2.0: P1 阶段 - 标准化工具层/可插拔通知适配器
- v0.1.0: P0 阶段 - 核心业务闭环
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 导入现有路由
from api.products import router as products_router
from api.recommendation import router as recommendation_router
from api.notification import router as legacy_notification_router

# 导入新增路由
from api.tools import router as tools_router
from api.notifications import router as notifications_router

# 导入 P3 业务路由
from api.commission import router as commission_router
from api.coupons import router as coupons_router
from api.share import router as share_router

# 导入 P4 新增路由
from api.fulfillment import router as fulfillment_router
from api.organizer_dashboard import router as organizer_dashboard_router
from api.demand_forecast import router as demand_forecast_router
# 导入 P1 需求预测增强路由 (Prophet+LSTM)
from api.demand_forecast_enhanced import router as demand_forecast_enhanced_router

# 导入 P0(P5 增长引擎) 新增路由
from api.p0_features import (
    flash_sale_router,
    newbie_router,
    cashback_router,
    stock_alert_router
)

# 导入 P0 AI 智能成团预测路由
from api.group_prediction import router as group_prediction_router

# 导入 P6 运营增强新增路由
from api.p6_features import (
    organizer_assessment_router,
    after_sales_router,
    signin_points_router
)

# 导入 P6 数据分析增强路由
from api.analytics import (
    sales_report_router,
    user_behavior_router,
    product_analytics_router,
    prediction_router,
    custom_report_router
)

# 导入 P7 游戏化运营新增路由
from api.p7_features import (
    achievement_router,
    leaderboard_router,
    bargain_router
)

# 导入 P8 智能风控新增路由
from api.p8_features import router as p8_router

# 导入 P9 智能履约调度系统路由
from api.fulfillment_scheduling import router as fulfillment_scheduling_router

# 导入 P9 多平台集成路由
from api.p9_platform import router as p9_platform_router

# 导入 P1 动态定价引擎路由
from api.dynamic_pricing import router as dynamic_pricing_router

# 导入 P0 AI 选品顾问增强路由
from api.product_selection_enhanced import router as product_selection_router

# 导入 P2 个性化推荐系统路由
from api.recommendation_enhanced import router as recommendation_enhanced_router

# 导入 P3 用户增长与运营工具路由
from api.p3_features import (
    invite_router,
    task_router,
    member_router,
    campaign_router
)

# 导入 P4 供应链与履约优化路由
from api.p4_supply_chain import router as p4_supply_chain_router

# 导入中间件
from middleware.rate_limiter import RateLimitMiddleware, RateLimiter, get_ip_key

# 导入数据库
from config.database import Base, engine, DATABASE_URL

# 导入实体模型（确保所有表都被注册）
from models.entities import (
    ProductEntity, GroupBuyEntity, GroupMemberEntity, OrderEntity,
    NotificationEntity, ProductRecommendationEntity,
    CommissionRuleEntity, CommissionRecordEntity, OrganizerProfileEntity,
    CouponTemplateEntity, CouponEntity,
    ShareInviteEntity, ShareRewardRuleEntity,
    # P4 新增实体
    FulfillmentEntity, FulfillmentEventEntity,
    OrganizerDashboardEntity,
    DemandForecastEntity, CommunityPreferenceEntity
)
# 导入 P0(P5) 新增实体
from models.p0_entities import (
    # 限时秒杀
    FlashSaleEntity, FlashSaleOrderEntity,
    # 新人专享
    NewbieProfileEntity, NewbieProductEntity, NewbieCouponTemplateEntity,
    NewbieTaskEntity, NewbieTaskProgressEntity,
    # 拼单返现
    GroupBuyCashbackEntity, GroupBuyCashbackParticipantEntity, GroupBuyCashbackRecordEntity,
    # 库存提示
    ProductViewTrackerEntity, StockAlertConfigEntity, ProductHeatmapEntity,
    # P0 AI 智能成团预测
    GroupPredictionEntity, PredictionFeatureEntity
)
# 导入 P6 运营增强新增实体
from models.p6_entities import (
    # 团长考核
    OrganizerAssessmentEntity,
    # 售后服务
    AfterSalesOrderEntity, AfterSalesLogEntity,
    # 签到积分
    SigninCalendarEntity, PointsAccountEntity, PointsTransactionEntity,
    PointsRuleEntity, PointsMallItemEntity, PointsRedemptionEntity
)
# 导入 P6 数据分析增强实体
from models.analytics_entities import (
    # 销售报表
    SalesReportEntity, SalesReportDetailEntity,
    # 用户行为分析
    UserFunnelEntity, UserRetentionEntity, UserBehaviorEntity,
    # 商品分析
    ProductSalesRankEntity, ProductTurnoverEntity, ProductProfitEntity,
    # 预测分析
    SalesPredictionEntity, SalesTrendEntity,
    # 自定义报表
    CustomReportEntity, CustomReportResultEntity
)
# 导入 P7 游戏化运营新增实体
from models.p7_entities import (
    # 成就系统
    AchievementDefinitionEntity, UserAchievementEntity, AchievementBadgeEntity,
    # 排行榜
    LeaderboardEntity, LeaderboardHistoryEntity,
    # 砍价玩法
    BargainActivityEntity, BargainOrderEntity, BargainHelpEntity
)
# 导入 P8 智能风控新增实体
from models.p8_entities import (
    # 信用体系
    CreditScoreEntity, CreditScoreHistoryEntity, CreditFactorEntity,
    # 风控规则
    RiskRuleEntity, RiskEventEntity,
    # 黑名单
    BlacklistEntity,
    # 订单风控
    OrderRiskAssessmentEntity
)
# 导入 P3 用户增长与运营工具新增实体
from models.p3_entities import (
    # 邀请裂变
    InviteRelationEntity, InviteRewardRuleEntity, InviteRecordEntity,
    # 任务中心
    TaskDefinitionEntity, UserTaskEntity, TaskProgressLogEntity,
    # 会员成长
    MemberProfileEntity, MemberLevelConfigEntity, GrowthValueLogEntity, MemberBenefitEntity,
    # 运营活动
    CampaignTemplateEntity, CampaignInstanceEntity, CampaignParticipantEntity
)
# 导入 P9 智能履约调度系统新增实体
from models.fulfillment_scheduling_entities import (
    # 自提点
    PickupPointEntity,
    # 配送路线
    DeliveryRouteEntity,
    # 配送任务
    DeliveryTaskEntity,
    # 人流预测
    TrafficFlowPredictionEntity,
    # 时间窗口推荐
    TimeWindowRecommendationEntity,
    # 配送异常
    DeliveryExceptionEntity
)
# 导入 P9 多平台集成新增实体
from models.p9_entities import (
    PlatformAccountEntity,
    PlatformOrderEntity,
    PlatformNotificationEntity,
    PlatformConfigEntity,
    PlatformSyncLogEntity
)
# 导入 P4 供应链与履约优化新增实体
from models.p4_entities import (
    # 库存预警
    InventoryAlertEntity, InventoryAlertActionEntity,
    # 智能补货
    ReplenishmentSuggestionEntity,
    # 供应商管理
    SupplierEntity, SupplierProductEntity,
    # 采购订单
    PurchaseOrderEntity, PurchaseOrderLineEntity,
    # 库存流水
    InventoryTransactionEntity
)
# 导入 P1 动态定价引擎新增实体
from models.pricing_entities import (
    # 动态价格
    DynamicPriceEntity,
    # 价格历史
    PriceHistoryEntity,
    # 定价策略
    PricingStrategyEntity,
    # 价格弹性测试
    PriceElasticityTestEntity,
    # 竞品价格
    CompetitorPriceEntity
)
# 导入 P5 营销自动化系统新增实体
from models.p5_entities import (
    # 用户分群
    CustomerSegmentEntity, CustomerSegmentMemberEntity, CustomerBehaviorEntity,
    # 营销自动化
    MarketingAutomationEntity, AutomationTriggerLogEntity,
    # 营销 ROI 分析
    CampaignROIEntity, CampaignDailyStatsEntity,
    # A/B 测试
    ABTestEntity, ABTestVariantEntity, ABTestUserAssignmentEntity,
    # 智能优惠券
    SmartCouponStrategyEntity, UserCouponPreferenceEntity,
    # 营销事件
    MarketingEventEntity
)

# 导入增强模块
from core.exceptions import register_exception_handlers
from core.logging_config import setup_logging, get_logger
from contextlib import asynccontextmanager

# 初始化日志系统
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    logger.info("正在初始化数据库表...")
    # 使用异步方式创建数据库表
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker

    # 构建异步数据库 URL
    async_db_url = DATABASE_URL
    if async_db_url.startswith("sqlite:///"):
        async_db_url = async_db_url.replace("sqlite:///", "sqlite+aiosqlite:///")
    elif async_db_url.startswith("postgresql://"):
        async_db_url = async_db_url.replace("postgresql://", "postgresql+asyncpg://")

    async_engine = create_async_engine(async_db_url, echo=False)

    try:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("数据库表初始化完成")
    except Exception as e:
        logger.error(f"数据库表初始化失败：{e}")

    yield

    # 关闭时清理
    await async_engine.dispose()
    logger.info("应用已关闭")


# 初始化通知适配器
def init_notification_adapters():
    """初始化通知适配器"""
    from adapters.notification.base import NotificationConfig
    from adapters.notification.memory import InMemoryNotificationAdapter
    from adapters.notification.console import ConsoleNotificationAdapter
    from adapters.notification.registry import register_adapter

    # 注册内存适配器（默认）
    register_adapter(
        name="memory",
        adapter=InMemoryNotificationAdapter(),
        set_default=True
    )

    # 注册控制台适配器（用于演示）
    register_adapter(
        name="console",
        adapter=ConsoleNotificationAdapter()
    )

    logger.info("通知适配器初始化完成")


# 创建 FastAPI 应用
app = FastAPI(
    title="AI Community Buying - AI Native 版",
    description="AI 驱动的社区团购平台 - P10+AI Native 转型 (DeerFlow 2.0 Agent/对话式交互/自主团购) + P9 智能履约调度系统 + P8 智能风控/信用体系 + P7 游戏化运营 + P6 数据分析增强 + P5 营销自动化系统 + P4 供应链与履约优化 + P3 用户增长与运营工具 + P2 个性化推荐 (Wide&Deep 深度排序) + P1 动态定价引擎 + P1 需求预测 (Prophet+LSTM) + P0 AI 选品顾问",
    version="4.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# 注册全局异常处理器
register_exception_handlers(app)
logger.info("全局异常处理器注册完成")

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加速率限制中间件（API 限流）
rate_limiter = RateLimiter(calls=100, period=60.0)  # 每分钟 100 次
app.add_middleware(
    RateLimitMiddleware,
    limiter=rate_limiter,
    key_func=get_ip_key,
    excluded_paths=["/health", "/docs", "/openapi.json"]
)

# 初始化通知适配器
init_notification_adapters()

# 注册路由
app.include_router(products_router)
app.include_router(recommendation_router)
app.include_router(legacy_notification_router)  # 保留向后兼容
app.include_router(tools_router)
app.include_router(notifications_router)
# P3 新增业务路由
app.include_router(commission_router)
app.include_router(coupons_router)
app.include_router(share_router)
# P4 新增业务路由
app.include_router(fulfillment_router)
app.include_router(organizer_dashboard_router)
app.include_router(demand_forecast_router)
# P1 需求预测增强路由 (Prophet+LSTM)
app.include_router(demand_forecast_enhanced_router)
# P0 AI 智能成团预测路由
app.include_router(group_prediction_router)
# P0(P5 增长引擎) 新增业务路由
app.include_router(flash_sale_router)
app.include_router(newbie_router)
app.include_router(cashback_router)
app.include_router(stock_alert_router)
# P6 运营增强新增业务路由
app.include_router(organizer_assessment_router)
app.include_router(after_sales_router)
app.include_router(signin_points_router)
# P7 游戏化运营新增业务路由
app.include_router(achievement_router)
app.include_router(leaderboard_router)
app.include_router(bargain_router)
# P8 智能风控新增业务路由
app.include_router(p8_router)
# P9 智能履约调度系统路由
app.include_router(fulfillment_scheduling_router)
# P9 多平台集成路由
app.include_router(p9_platform_router)
# P1 动态定价引擎路由
app.include_router(dynamic_pricing_router)
# P0 AI 选品顾问增强路由
app.include_router(product_selection_router)
# P2 个性化推荐系统路由
app.include_router(recommendation_enhanced_router)
# P3 用户增长与运营工具路由
app.include_router(invite_router)
app.include_router(task_router)
app.include_router(member_router)
app.include_router(campaign_router)

# P4 供应链与履约优化路由
app.include_router(p4_supply_chain_router)

# P5 营销自动化系统路由
from api.p5_marketing_automation import (
    segmentation_router,
    automation_router,
    roi_router,
    abtest_router,
    smart_coupon_router,
    event_router
)
app.include_router(segmentation_router)
app.include_router(automation_router)
app.include_router(roi_router)
app.include_router(abtest_router)
app.include_router(smart_coupon_router)
app.include_router(event_router)

# P6 数据分析增强路由
app.include_router(sales_report_router)
app.include_router(user_behavior_router)
app.include_router(product_analytics_router)
app.include_router(prediction_router)
app.include_router(custom_report_router)

# AI Native 对话式交互路由（P10+ 智能团购管家）
from api.chat import router as chat_router
app.include_router(chat_router)

logger.info("所有路由注册完成（含 P3 邀请裂变/任务中心/会员成长/运营活动/P4 供应链与履约优化/P5 营销自动化/P6 数据分析增强/P7 游戏化运营/P8 智能风控/P9 多平台集成/P10+AI Native 对话式交互）")


@app.get("/")
async def root():
    return {
        "message": "欢迎使用 AI 社区团购平台 - AI Native 版",
        "status": "running",
        "version": "4.0.0",
        "stage": "P10+ AI Native 转型 (DeerFlow 2.0 Agent)",
        "endpoints": {
            "AI 对话交互": "/api/chat",
            "快捷发起团购": "/api/chat/quick-start",
            "商品管理": "/api/products",
            "团购管理": "/api/groups",
            "订单管理": "/api/orders",
            "智能推荐": "/api/recommendation",
            "个性化推荐 (深度排序)": "/api/recommendation/personalized",
            "用户特征解释": "/api/recommendation/explain",
            "推荐多样性检查": "/api/recommendation/diversity-check",
            "社区热销榜": "/api/recommendation/hot",
            "工具服务": "/api/tools",
            "通知服务": "/api/notifications",
            "佣金系统": "/api/commission",
            "优惠券系统": "/api/coupons",
            "分享裂变": "/api/share",
            "邀请裂变": "/api/p3/invite",
            "任务中心": "/api/p3/tasks",
            "会员成长": "/api/p3/member",
            "运营活动": "/api/p3/campaigns",
            "履约追踪": "/api/fulfillment",
            "智能履约调度": "/api/fulfillment-scheduling",
            "团长管理": "/api/organizer",
            "AI 需求预测": "/api/ai/forecast",
            "AI 需求预测增强": "/api/ai/forecast/advanced",
            "AI 成团预测": "/api/ai/group-prediction",
            "供应链与履约优化": "/api/p4",
            "营销自动化": "/api/p5",
            "用户分群": "/api/p5/segmentation",
            "营销自动化活动": "/api/p5/automation",
            "营销 ROI 分析": "/api/p5/roi",
            "A/B 测试": "/api/p5/ab-tests",
            "智能优惠券": "/api/p5/smart-coupons",
            "营销事件追踪": "/api/p5/events",
            "限时秒杀": "/api/flash-sale",
            "新人专享": "/api/newbie",
            "拼单返现": "/api/group-buy-cashback",
            "库存提示": "/api/stock-alert",
            "团长考核": "/api/organizer-assessment",
            "售后服务": "/api/after-sales",
            "签到积分": "/api/signin-points",
            "数据分析增强": "/api/analytics",
            "销售报表": "/api/analytics/sales-reports",
            "用户行为分析": "/api/analytics/user-behavior",
            "商品分析": "/api/analytics/products",
            "预测分析": "/api/analytics/predictions",
            "自定义报表": "/api/analytics/custom-reports",
            "成就系统": "/api/p7/achievements",
            "排行榜": "/api/p7/leaderboards",
            "砍价玩法": "/api/p7/bargain",
            "智能风控/信用体系": "/api/p8",
            "信用体系": "/api/p8/credit",
            "风控规则": "/api/p8/rules",
            "黑名单管理": "/api/p8/blacklist",
            "订单风控": "/api/p8/order-risk",
            "动态定价": "/api/dynamic-pricing",
            "多平台/小程序集成": "/api/platform",
            "接口文档": "/docs",
            "健康检查": "/health"
        },
        "features": {
            "P0": "商品/库存/团购/订单核心闭环 + AI 智能成团预测 + AI 选品顾问 (协同过滤/社区画像)",
            "P1": "标准化工具层、可插拔通知适配器、速率限制、动态定价引擎、需求预测 (Prophet+LSTM)",
            "P2": "个性化推荐系统 (Wide&Deep 深度排序/用户特征工程/多样性控制)",
            "P3": "邀请裂变系统、任务中心、会员成长体系、运营活动模板",
            "P4": "供应链与履约优化 (库存预警/智能补货/供应商管理/采购订单)",
            "P5": "营销自动化系统 (用户分群/自动化营销/ROI 分析/A/B 测试/智能优惠券)",
            "P6": "数据分析增强 (销售报表/用户行为分析/商品分析/预测分析) + 团长考核/售后流程/签到积分",
            "P7": "游戏化运营 (成就/排行榜)、砍价玩法",
            "P8": "智能风控/信用体系 (用户信用评分/欺诈检测/订单风控/黑名单管理/风控规则引擎)",
            "P9": "智能履约调度系统 (路径优化/人流预测/时间窗口推荐) + 多平台/小程序集成 (微信/支付宝小程序/账号同步/跨平台订单)",
            "P10+": "AI Native 转型 - DeerFlow 2.0 Agent 框架/对话式交互/自主团购/智能选品/主动邀请"
        }
    }


@app.get("/health")
async def health_check():
    """
    健康检查接口

    检查服务状态和数据库连接。
    """
    from config.database_enhanced import check_db_health

    db_health = check_db_health()

    status = "healthy" if db_health["status"] == "healthy" else "degraded"

    return {
        "status": status,
        "version": "1.0.0",
        "checks": {
            "service": "healthy",
            "database": db_health
        }
    }


@app.get("/tools")
async def list_tools():
    """快捷获取工具列表"""
    from tools.registry import get_available_tools
    tools = get_available_tools()
    return {
        "success": True,
        "tools": [
            {
                "name": tool.name,
                "description": tool.description,
                "tags": tool.tags
            }
            for tool in tools
        ]
    }


@app.on_event("startup")
async def startup_event():
    """服务启动时的初始化"""
    logger.info("服务启动中...")
    logger.info(f"数据库引擎：{engine.url.drivername}")
    logger.info("服务启动完成")


@app.on_event("shutdown")
async def shutdown_event():
    """服务关闭时的清理"""
    logger.info("服务关闭中...")
    # 清理数据库连接等资源
    engine.dispose()
    logger.info("服务已关闭")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("COMMUNITY_BUYING_PORT", "8005"))
    log_level = os.getenv("LOG_LEVEL", "info").lower()

    logger.info(f"启动服务：端口 {port}, 日志级别 {log_level}")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level=log_level
    )
