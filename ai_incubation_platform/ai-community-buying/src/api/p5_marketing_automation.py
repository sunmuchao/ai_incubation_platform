"""
P5 营销自动化系统 - API 路由

包含：
1. 用户分群 API (Customer Segmentation)
2. 营销自动化 API (Marketing Automation)
3. 营销 ROI 分析 API (Marketing ROI Analysis)
4. A/B 测试 API (A/B Testing)
5. 智能优惠券 API (Smart Coupon)
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal

from config.database import get_db
from sqlalchemy.orm import Session
from services.p5_marketing_service import (
    CustomerSegmentationService,
    MarketingAutomationService,
    MarketingROIAnalysisService,
    ABTestService,
    SmartCouponService,
    MarketingEventService
)


# ====================  Pydantic 模型  ====================

# --- 用户分群相关模型 ---

class SegmentCreateRequest(BaseModel):
    """创建分群请求"""
    segment_name: str = Field(..., description="分群名称")
    segment_type: str = Field(..., description="分群类型")
    rules: Dict[str, Any] = Field(default_factory=dict, description="分群规则")
    description: Optional[str] = Field(None, description="分群描述")


class RFMScoreResponse(BaseModel):
    """RFM 评分响应"""
    r_score: int
    f_score: int
    m_score: int
    total_score: int
    segment_type: str


# --- 营销自动化相关模型 ---

class AutomationCreateRequest(BaseModel):
    """创建自动化活动请求"""
    campaign_name: str = Field(..., description="活动名称")
    automation_type: str = Field(..., description="自动化类型")
    trigger_config: Dict[str, Any] = Field(default_factory=dict, description="触发配置")
    target_segment_id: Optional[str] = Field(None, description="目标分群 ID")
    content_config: Dict[str, Any] = Field(default_factory=dict, description="内容配置")
    start_time: Optional[str] = Field(None, description="开始时间")
    end_time: Optional[str] = Field(None, description="结束时间")


class AutomationTriggerRequest(BaseModel):
    """触发自动化请求"""
    user_id: str = Field(..., description="用户 ID")
    event_type: str = Field(..., description="事件类型")
    event_data: Dict[str, Any] = Field(default_factory=dict, description="事件数据")


class ConversionRecordRequest(BaseModel):
    """转化记录请求"""
    trigger_log_id: str = Field(..., description="触发日志 ID")
    conversion_type: str = Field(..., description="转化类型")
    order_id: str = Field(..., description="订单 ID")
    amount: float = Field(..., gt=0, description="转化金额")


# --- A/B 测试相关模型 ---

class ABTestCreateRequest(BaseModel):
    """创建 A/B 测试请求"""
    test_name: str = Field(..., description="测试名称")
    description: Optional[str] = Field(None, description="测试描述")
    goal_type: str = Field(..., description="目标类型")
    goal_metric: str = Field(..., description="核心指标")
    variants_config: List[Dict[str, Any]] = Field(..., description="变体配置")
    traffic_percentage: int = Field(100, ge=1, le=100, description="流量占比")
    sample_size: int = Field(1000, ge=100, description="目标样本量")
    start_time: Optional[str] = Field(None, description="开始时间")
    end_time: Optional[str] = Field(None, description="结束时间")


class ABTestAssignRequest(BaseModel):
    """A/B 测试分配请求"""
    test_id: str = Field(..., description="测试 ID")
    user_id: str = Field(..., description="用户 ID")


class ABTestConcludeRequest(BaseModel):
    """A/B 测试结束请求"""
    winner_variant: str = Field(..., description="胜出变体")


# --- 智能优惠券相关模型 ---

class SmartCouponStrategyCreateRequest(BaseModel):
    """智能优惠券策略创建请求"""
    strategy_name: str = Field(..., description="策略名称")
    description: Optional[str] = Field(None, description="策略描述")
    target_segment_id: Optional[str] = Field(None, description="目标分群 ID")
    coupon_rules: Dict[str, Any] = Field(..., description="优惠券规则")
    trigger_event: Optional[str] = Field(None, description="触发事件")
    max_coupons_per_user: int = Field(1, ge=1, description="每人限领")
    daily_limit: int = Field(1000, ge=1, description="每日发放上限")


class UserCouponPreferenceUpdateRequest(BaseModel):
    """用户优惠券偏好更新请求"""
    preferred_coupon_type: Optional[str] = Field(None, description="偏好优惠券类型")
    preferred_discount_range: Optional[str] = Field(None, description="偏好折扣区间")
    best_send_time: Optional[str] = Field(None, description="最佳发送时间")
    best_channel: Optional[str] = Field(None, description="最佳触达渠道")
    price_sensitivity: Optional[str] = Field(None, description="价格敏感度")


# --- 营销事件相关模型 ---

class MarketingEventTrackRequest(BaseModel):
    """营销事件追踪请求"""
    user_id: str = Field(..., description="用户 ID")
    event_type: str = Field(..., description="事件类型")
    event_data: Dict[str, Any] = Field(default_factory=dict, description="事件数据")
    campaign_id: Optional[str] = Field(None, description="活动 ID")
    coupon_id: Optional[str] = Field(None, description="优惠券 ID")
    order_id: Optional[str] = Field(None, description="订单 ID")


# ====================  路由器定义  ====================

# 用户分群 API 路由
segmentation_router = APIRouter(prefix="/api/p5/segmentation", tags=["P5-用户分群"])

# 营销自动化 API 路由
automation_router = APIRouter(prefix="/api/p5/automation", tags=["P5-营销自动化"])

# 营销 ROI 分析 API 路由
roi_router = APIRouter(prefix="/api/p5/roi", tags=["P5-营销 ROI 分析"])

# A/B 测试 API 路由
abtest_router = APIRouter(prefix="/api/p5/ab-tests", tags=["P5-A/B 测试"])

# 智能优惠券 API 路由
smart_coupon_router = APIRouter(prefix="/api/p5/smart-coupons", tags=["P5-智能优惠券"])

# 营销事件 API 路由
event_router = APIRouter(prefix="/api/p5/events", tags=["P5-营销事件"])


# ====================  用户分群 API  ====================

@segmentation_router.post("/segments")
async def create_segment(request: SegmentCreateRequest, db: Session = Depends(get_db)):
    """创建客户分群"""
    service = CustomerSegmentationService(db)
    segment = service.create_segment(
        segment_name=request.segment_name,
        segment_type=request.segment_type,
        rules=request.rules
    )
    return {"success": True, "segment": segment}


@segmentation_router.get("/segments")
async def list_segments(active_only: bool = Query(True, description="是否仅获取活跃分群"),
                       db: Session = Depends(get_db)):
    """获取客户分群列表"""
    service = CustomerSegmentationService(db)
    segments = service.list_segments(active_only)
    return {"success": True, "segments": segments}


@segmentation_router.get("/segments/{segment_id}/members")
async def get_segment_members(segment_id: str,
                             limit: int = Query(100, ge=1, le=1000, description="返回数量"),
                             db: Session = Depends(get_db)):
    """获取分群成员列表"""
    service = CustomerSegmentationService(db)
    members = service.get_segment_members(segment_id, limit)
    return {"success": True, "members": members}


@segmentation_router.post("/users/{user_id}/update-segment")
async def update_user_segment(user_id: str, db: Session = Depends(get_db)):
    """更新用户分群"""
    service = CustomerSegmentationService(db)
    member = service.update_user_segment(user_id)
    if not member:
        raise HTTPException(status_code=404, detail="用户分群更新失败")
    return {"success": True, "segment_id": member.segment_id, "rfm_total": member.rfm_total}


@segmentation_router.get("/users/{user_id}/rfm-scores")
async def get_user_rfm_scores(user_id: str, db: Session = Depends(get_db)):
    """获取用户 RFM 评分"""
    service = CustomerSegmentationService(db)
    scores = service.calculate_rfm_scores(user_id)
    segment_type = service.determine_segment_type(scores)
    return {
        "success": True,
        "rfm_scores": scores,
        "segment_type": segment_type
    }


@segmentation_router.get("/users/{user_id}/segments")
async def get_user_segments(user_id: str, db: Session = Depends(get_db)):
    """获取用户所属分群"""
    service = CustomerSegmentationService(db)
    segments = service.get_user_segments(user_id)
    return {"success": True, "segments": segments}


# ====================  营销自动化 API  ====================

@automation_router.post("/campaigns")
async def create_automation(request: AutomationCreateRequest, db: Session = Depends(get_db)):
    """创建营销自动化活动"""
    service = MarketingAutomationService(db)

    # 解析时间
    start_time = datetime.fromisoformat(request.start_time) if request.start_time else None
    end_time = datetime.fromisoformat(request.end_time) if request.end_time else None

    config = {
        "campaign_name": request.campaign_name,
        "automation_type": request.automation_type,
        "trigger_config": request.trigger_config,
        "target_segment_id": request.target_segment_id,
        "content_config": request.content_config,
        "start_time": start_time,
        "end_time": end_time
    }

    automation = service.create_automation(config)
    return {"success": True, "automation": automation}


@automation_router.get("/campaigns")
async def list_automations(status: Optional[str] = Query(None, description="活动状态"),
                          db: Session = Depends(get_db)):
    """获取营销自动化活动列表"""
    service = MarketingAutomationService(db)
    automations = service.list_automations(status)
    return {"success": True, "automations": automations}


@automation_router.post("/campaigns/{campaign_id}/trigger")
async def trigger_automation(campaign_id: str, request: AutomationTriggerRequest,
                            db: Session = Depends(get_db)):
    """触发营销自动化"""
    service = MarketingAutomationService(db)

    success = service.trigger_automation(
        automation_id=campaign_id,
        user_id=request.user_id,
        event_data={"event_type": request.event_type, **request.event_data}
    )

    if not success:
        raise HTTPException(status_code=400, detail="触发失败，可能原因：活动不存在/不活跃/用户不在目标人群")

    return {"success": True, "message": "营销自动化已触发"}


@automation_router.post("/conversions/record")
async def record_conversion(request: ConversionRecordRequest, db: Session = Depends(get_db)):
    """记录转化事件"""
    service = MarketingAutomationService(db)
    service.record_conversion(
        trigger_log_id=request.trigger_log_id,
        conversion_type=request.conversion_type,
        order_id=request.order_id,
        amount=Decimal(str(request.amount))
    )
    return {"success": True, "message": "转化已记录"}


@automation_router.get("/campaigns/{campaign_id}/stats")
async def get_automation_stats(campaign_id: str, db: Session = Depends(get_db)):
    """获取自动化活动统计"""
    service = MarketingAutomationService(db)
    stats = service.get_automation_stats(campaign_id)
    return {"success": True, "stats": stats}


# ====================  营销 ROI 分析 API  ====================

@roi_router.post("/calculate")
async def calculate_roi(
    campaign_id: str = Query(..., description="活动 ID"),
    start_date: str = Query(..., description="开始日期 ISO 格式"),
    end_date: str = Query(..., description="结束日期 ISO 格式"),
    db: Session = Depends(get_db)
):
    """计算营销活动 ROI"""
    service = MarketingROIAnalysisService(db)

    roi_record = service.calculate_campaign_roi(
        campaign_id=campaign_id,
        start_date=datetime.fromisoformat(start_date),
        end_date=datetime.fromisoformat(end_date)
    )

    return {
        "success": True,
        "roi": {
            "campaign_id": roi_record.campaign_id,
            "campaign_name": roi_record.campaign_name,
            "total_cost": float(roi_record.total_cost),
            "total_revenue": float(roi_record.total_revenue),
            "roi": float(roi_record.roi),
            "roas": float(roi_record.roas),
            "cpac": float(roi_record.cpac),
            "order_count": roi_record.order_count,
            "customer_count": roi_record.customer_count
        }
    }


@roi_router.get("/reports/{campaign_id}")
async def get_roi_report(campaign_id: str, db: Session = Depends(get_db)):
    """获取 ROI 分析报告"""
    service = MarketingROIAnalysisService(db)
    reports = service.get_roi_report(campaign_id)
    return {"success": True, "reports": reports}


@roi_router.post("/daily-stats/generate")
async def generate_daily_stats(
    campaign_id: str = Query(..., description="活动 ID"),
    stat_date: str = Query(..., description="统计日期 ISO 格式"),
    db: Session = Depends(get_db)
):
    """生成每日统计"""
    service = MarketingROIAnalysisService(db)
    stats = service.generate_daily_stats(
        campaign_id=campaign_id,
        stat_date=datetime.fromisoformat(stat_date)
    )
    return {"success": True, "stats": stats}


# ====================  A/B 测试 API  ====================

@abtest_router.post("/")
async def create_ab_test(request: ABTestCreateRequest, db: Session = Depends(get_db)):
    """创建 A/B 测试"""
    service = ABTestService(db)

    # 解析时间
    start_time = datetime.fromisoformat(request.start_time) if request.start_time else None
    end_time = datetime.fromisoformat(request.end_time) if request.end_time else None

    config = {
        "test_name": request.test_name,
        "description": request.description,
        "goal_type": request.goal_type,
        "goal_metric": request.goal_metric,
        "variants_config": request.variants_config,
        "traffic_percentage": request.traffic_percentage,
        "sample_size": request.sample_size,
        "start_time": start_time,
        "end_time": end_time
    }

    ab_test = service.create_ab_test(config)
    return {"success": True, "test": ab_test}


@abtest_router.post("/assign")
async def assign_variant(request: ABTestAssignRequest, db: Session = Depends(get_db)):
    """为用户分配测试变体"""
    service = ABTestService(db)
    variant = service.assign_variant(
        test_id=request.test_id,
        user_id=request.user_id
    )
    return {"success": True, "variant": variant}


@abtest_router.post("/{test_id}/start")
async def start_test(test_id: str, db: Session = Depends(get_db)):
    """开始 A/B 测试"""
    service = ABTestService(db)
    service.start_test(test_id)
    return {"success": True, "message": f"A/B 测试 {test_id} 已开始"}


@abtest_router.post("/{test_id}/conclude")
async def conclude_test(test_id: str, request: ABTestConcludeRequest, db: Session = Depends(get_db)):
    """结束 A/B 测试"""
    service = ABTestService(db)
    service.conclude_test(test_id, request.winner_variant)
    return {"success": True, "message": f"A/B 测试 {test_id} 已结束，胜者：{request.winner_variant}"}


@abtest_router.post("/{test_id}/conversion")
async def record_ab_test_conversion(
    test_id: str,
    user_id: str = Query(..., description="用户 ID"),
    conversion_value: float = Query(0, description="转化价值"),
    db: Session = Depends(get_db)
):
    """记录 A/B 测试转化"""
    service = ABTestService(db)
    service.record_conversion(
        test_id=test_id,
        user_id=user_id,
        conversion_value=Decimal(str(conversion_value))
    )
    return {"success": True, "message": "转化已记录"}


@abtest_router.get("/{test_id}/analyze")
async def analyze_ab_test(test_id: str, db: Session = Depends(get_db)):
    """分析 A/B 测试结果"""
    service = ABTestService(db)
    result = service.analyze_test(test_id)
    return {"success": True, "analysis": result}


# ====================  智能优惠券 API  ====================

@smart_coupon_router.post("/strategies")
async def create_smart_coupon_strategy(request: SmartCouponStrategyCreateRequest,
                                       db: Session = Depends(get_db)):
    """创建智能优惠券策略"""
    service = SmartCouponService(db)

    strategy = service.create_strategy({
        "strategy_name": request.strategy_name,
        "description": request.description,
        "target_segment_id": request.target_segment_id,
        "coupon_rules": request.coupon_rules,
        "trigger_event": request.trigger_event,
        "max_coupons_per_user": request.max_coupons_per_user,
        "daily_limit": request.daily_limit
    })

    return {"success": True, "strategy": strategy}


@smart_coupon_router.get("/strategies")
async def list_strategies(db: Session = Depends(get_db)):
    """获取智能优惠券策略列表"""
    from models.p5_entities import SmartCouponStrategyEntity
    strategies = db.query(SmartCouponStrategyEntity).all()
    return {"success": True, "strategies": strategies}


@smart_coupon_router.post("/strategies/{strategy_id}/generate")
async def generate_coupon_for_user(strategy_id: str,
                                   user_id: str = Query(..., description="用户 ID"),
                                   db: Session = Depends(get_db)):
    """为用户生成个性化优惠券"""
    service = SmartCouponService(db)
    coupon_config = service.generate_coupon_for_user(user_id, strategy_id)

    if not coupon_config:
        raise HTTPException(status_code=400, detail="无法生成优惠券，可能原因：策略不存在/不活跃/用户不在目标人群")

    return {"success": True, "coupon": coupon_config}


@smart_coupon_router.get("/strategies/{strategy_id}/stats")
async def get_strategy_stats(strategy_id: str, db: Session = Depends(get_db)):
    """获取策略统计"""
    service = SmartCouponService(db)
    stats = service.get_strategy_stats(strategy_id)
    return {"success": True, "stats": stats}


@smart_coupon_router.get("/users/{user_id}/preference")
async def get_user_coupon_preference(user_id: str, db: Session = Depends(get_db)):
    """获取用户优惠券偏好"""
    from models.p5_entities import UserCouponPreferenceEntity
    preference = db.query(UserCouponPreferenceEntity).filter(
        UserCouponPreferenceEntity.user_id == user_id
    ).first()
    return {"success": True, "preference": preference}


@smart_coupon_router.put("/users/{user_id}/preference")
async def update_user_coupon_preference(user_id: str,
                                        request: UserCouponPreferenceUpdateRequest,
                                        db: Session = Depends(get_db)):
    """更新用户优惠券偏好"""
    service = SmartCouponService(db)
    preference_data = request.model_dump(exclude_none=True)
    service.update_user_preference(user_id, preference_data)
    return {"success": True, "message": "偏好已更新"}


# ====================  营销事件 API  ====================

@event_router.post("/track")
async def track_event(request: MarketingEventTrackRequest, db: Session = Depends(get_db)):
    """追踪营销事件"""
    service = MarketingEventService(db)
    service.track_event(
        user_id=request.user_id,
        event_type=request.event_type,
        event_data=request.event_data,
        campaign_id=request.campaign_id,
        coupon_id=request.coupon_id,
        order_id=request.order_id
    )
    return {"success": True, "message": "事件已追踪"}


@event_router.get("/users/{user_id}")
async def get_user_events(user_id: str,
                          event_type: Optional[str] = Query(None, description="事件类型"),
                          limit: int = Query(100, ge=1, le=1000, description="返回数量"),
                          db: Session = Depends(get_db)):
    """获取用户营销事件"""
    service = MarketingEventService(db)
    events = service.get_user_events(user_id, event_type, limit)
    return {"success": True, "events": events}


@event_router.get("/campaigns/{campaign_id}")
async def get_campaign_events(campaign_id: str,
                              limit: int = Query(1000, ge=1, le=10000, description="返回数量"),
                              db: Session = Depends(get_db)):
    """获取活动相关事件"""
    service = MarketingEventService(db)
    events = service.get_campaign_events(campaign_id, limit)
    return {"success": True, "events": events}
