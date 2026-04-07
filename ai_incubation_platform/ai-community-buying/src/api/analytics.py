"""
P6 数据分析增强 - API 路由

包含:
1. 销售报表 API - 日报/周报/月报
2. 用户行为分析 API - 转化漏斗/留存分析
3. 商品分析 API - 销售排行/库存周转
4. 预测分析 API - 销量预测/趋势预测
5. 自定义报表 API - 用户自定义分析
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from fastapi.responses import Response
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import datetime, date

from config.database import get_db
from sqlalchemy.orm import Session
from models.analytics_entities import ReportType, ReportStatus, UserSegment, TrendDirection
from services.analytics_service import (
    SalesReportService,
    UserBehaviorService,
    ProductAnalyticsService,
    PredictionService,
    CustomReportService
)
from core.exceptions import AppException

# ==================== 路由器定义 ====================

# 销售报表 API 路由
sales_report_router = APIRouter(prefix="/api/analytics/sales-reports", tags=["销售分析"])

# 用户行为分析 API 路由
user_behavior_router = APIRouter(prefix="/api/analytics/user-behavior", tags=["用户行为分析"])

# 商品分析 API 路由
product_analytics_router = APIRouter(prefix="/api/analytics/products", tags=["商品分析"])

# 预测分析 API 路由
prediction_router = APIRouter(prefix="/api/analytics/predictions", tags=["预测分析"])

# 自定义报表 API 路由
custom_report_router = APIRouter(prefix="/api/analytics/custom-reports", tags=["自定义报表"])


# ==================== Pydantic 模型 ====================

# --- 销售报表相关模型 ---

class SalesReportGenerateRequest(BaseModel):
    """生成销售报表请求"""
    report_type: str = Field(..., description="报表类型 (daily/weekly/monthly)")
    reference_date: Optional[str] = Field(None, description="参考日期 (YYYY-MM-DD)")
    organizer_id: Optional[str] = Field(None, description="团长 ID")
    community_id: Optional[str] = Field(None, description="社区 ID")
    force_regenerate: bool = Field(False, description="是否强制重新生成")


class SalesReportListRequest(BaseModel):
    """报表列表请求"""
    report_type: Optional[str] = Field(None, description="报表类型")
    organizer_id: Optional[str] = Field(None, description="团长 ID")
    community_id: Optional[str] = Field(None, description="社区 ID")
    start_date: Optional[str] = Field(None, description="开始日期")
    end_date: Optional[str] = Field(None, description="结束日期")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")


# --- 用户行为分析相关模型 ---

class FunnelCalculateRequest(BaseModel):
    """漏斗计算请求"""
    funnel_date: Optional[str] = Field(None, description="漏斗日期")
    period_type: str = Field("daily", description="周期类型 (daily/weekly/monthly)")
    organizer_id: Optional[str] = Field(None, description="团长 ID")
    community_id: Optional[str] = Field(None, description="社区 ID")


class RetentionCalculateRequest(BaseModel):
    """留存计算请求"""
    cohort_date: Optional[str] = Field(None, description="队列日期")
    cohort_type: str = Field("daily", description="队列类型 (daily/weekly/monthly)")
    organizer_id: Optional[str] = Field(None, description="团长 ID")
    community_id: Optional[str] = Field(None, description="社区 ID")


# --- 商品分析相关模型 ---

class SalesRankRequest(BaseModel):
    """销售排行请求"""
    rank_date: Optional[str] = Field(None, description="排行日期")
    period_type: str = Field("daily", description="周期类型")
    organizer_id: Optional[str] = Field(None, description="团长 ID")
    community_id: Optional[str] = Field(None, description="社区 ID")
    top_n: int = Field(10, ge=1, le=100, description="返回 TOP N")


class TurnoverAnalysisRequest(BaseModel):
    """库存周转分析请求"""
    product_id: str = Field(..., description="商品 ID")
    organizer_id: Optional[str] = Field(None, description="团长 ID")
    analysis_date: Optional[str] = Field(None, description="分析日期")


# --- 预测分析相关模型 ---

class SalesPredictionRequest(BaseModel):
    """销量预测请求"""
    product_id: str = Field(..., description="商品 ID")
    predict_date: Optional[str] = Field(None, description="预测日期")
    organizer_id: Optional[str] = Field(None, description="团长 ID")
    community_id: Optional[str] = Field(None, description="社区 ID")


class TrendAnalysisRequest(BaseModel):
    """趋势分析请求"""
    trend_date: Optional[str] = Field(None, description="分析日期")
    organizer_id: Optional[str] = Field(None, description="团长 ID")
    community_id: Optional[str] = Field(None, description="社区 ID")


# --- 自定义报表相关模型 ---

class CustomReportCreateRequest(BaseModel):
    """创建自定义报表请求"""
    report_name: str = Field(..., description="报表名称", min_length=1, max_length=128)
    report_description: Optional[str] = Field(None, description="报表描述")
    config: Dict[str, Any] = Field(..., description="报表配置")


class CustomReportExecuteRequest(BaseModel):
    """执行自定义报表请求"""
    report_id: str = Field(..., description="报表 ID")


# ==================== 销售报表 API ====================

@sales_report_router.post(
    "/generate",
    response_model=Dict[str, Any],
    summary="生成销售报表"
)
def generate_sales_report(
    request: SalesReportGenerateRequest,
    db: Session = Depends(get_db)
):
    """生成销售报表 (日报/周报/月报)"""
    service = SalesReportService(db)
    service.set_request_context(request_id="auto", user_id="admin")

    try:
        report_type = ReportType(request.report_type)
    except ValueError:
        raise AppException(
            code="INVALID_REPORT_TYPE",
            message=f"无效的报表类型：{request.report_type}",
            status=400
        )

    reference_date = None
    if request.reference_date:
        reference_date = datetime.fromisoformat(request.reference_date)

    report = service.generate_report(
        report_type=report_type,
        reference_date=reference_date,
        organizer_id=request.organizer_id,
        community_id=request.community_id,
        force_regenerate=request.force_regenerate
    )

    return {
        "success": True,
        "message": "报表生成成功",
        "data": {
            "id": report.id,
            "report_type": report.report_type.value,
            "report_date": report.report_date.isoformat(),
            "period_start": report.period_start.isoformat(),
            "period_end": report.period_end.isoformat(),
            "gmv": float(report.gmv),
            "total_sales": float(report.total_sales),
            "total_orders": report.total_orders,
            "completed_orders": report.completed_orders,
            "total_users": report.total_users,
            "avg_order_value": float(report.avg_order_value) if report.avg_order_value else 0,
            "gmv_growth_rate": float(report.gmv_growth_rate) if report.gmv_growth_rate else 0,
            "orders_growth_rate": float(report.orders_growth_rate) if report.orders_growth_rate else 0,
            "status": report.status.value,
            "generated_at": report.generated_at.isoformat() if report.generated_at else None
        }
    }


@sales_report_router.get(
    "/{report_id}",
    response_model=Dict[str, Any],
    summary="获取报表详情"
)
def get_sales_report(
    report_id: str,
    db: Session = Depends(get_db)
):
    """获取销售报表详情"""
    service = SalesReportService(db)
    report = service.get_report(report_id)

    if not report:
        raise AppException(
            code="REPORT_NOT_FOUND",
            message="报表不存在",
            status=404
        )

    return {
        "success": True,
        "data": {
            "id": report.id,
            "report_type": report.report_type.value,
            "report_date": report.report_date.isoformat(),
            "period_start": report.period_start.isoformat(),
            "period_end": report.period_end.isoformat(),
            "gmv": float(report.gmv),
            "total_sales": float(report.total_sales),
            "total_orders": report.total_orders,
            "paid_orders": report.paid_orders,
            "completed_orders": report.completed_orders,
            "cancelled_orders": report.cancelled_orders,
            "refunded_orders": report.refunded_orders,
            "total_users": report.total_users,
            "new_users": report.new_users,
            "active_users": report.active_users,
            "avg_order_value": float(report.avg_order_value) if report.avg_order_value else 0,
            "total_products": report.total_products,
            "top_product_id": report.top_product_id,
            "top_product_sales": float(report.top_product_sales) if report.top_product_sales else 0,
            "prev_period_gmv": float(report.prev_period_gmv) if report.prev_period_gmv else 0,
            "gmv_growth_rate": float(report.gmv_growth_rate) if report.gmv_growth_rate else 0,
            "prev_period_orders": report.prev_period_orders,
            "orders_growth_rate": float(report.orders_growth_rate) if report.orders_growth_rate else 0,
            "organizer_id": report.organizer_id,
            "community_id": report.community_id,
            "status": report.status.value,
            "generated_at": report.generated_at.isoformat() if report.generated_at else None
        }
    }


@sales_report_router.get(
    "",
    response_model=Dict[str, Any],
    summary="获取报表列表"
)
def list_sales_reports(
    report_type: Optional[str] = Query(None, description="报表类型"),
    organizer_id: Optional[str] = Query(None, description="团长 ID"),
    community_id: Optional[str] = Query(None, description="社区 ID"),
    start_date: Optional[str] = Query(None, description="开始日期"),
    end_date: Optional[str] = Query(None, description="结束日期"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db)
):
    """获取销售报表列表"""
    service = SalesReportService(db)

    report_type_enum = None
    if report_type:
        try:
            report_type_enum = ReportType(report_type)
        except ValueError:
            pass

    start_dt = None
    end_dt = None
    if start_date:
        start_dt = datetime.fromisoformat(start_date).date()
    if end_date:
        end_dt = datetime.fromisoformat(end_date).date()

    result = service.list_reports(
        report_type=report_type_enum,
        organizer_id=organizer_id,
        community_id=community_id,
        start_date=start_dt,
        end_date=end_dt,
        page=page,
        page_size=page_size
    )

    return {
        "success": True,
        "data": {
            "total": result["total"],
            "page": result["page"],
            "page_size": result["page_size"],
            "reports": [
                {
                    "id": r.id,
                    "report_type": r.report_type.value,
                    "report_date": r.report_date.isoformat(),
                    "gmv": float(r.gmv),
                    "total_sales": float(r.total_sales),
                    "total_orders": r.total_orders,
                    "status": r.status.value
                }
                for r in result["reports"]
            ]
        }
    }


@sales_report_router.get(
    "/dashboard/summary",
    response_model=Dict[str, Any],
    summary="获取仪表盘摘要"
)
def get_dashboard_summary(
    organizer_id: Optional[str] = Query(None, description="团长 ID"),
    db: Session = Depends(get_db)
):
    """获取仪表盘摘要 (今日 + 本月累计)"""
    service = SalesReportService(db)
    summary = service.get_dashboard_summary(organizer_id)

    return {
        "success": True,
        "data": summary
    }


# ==================== 用户行为分析 API ====================

@user_behavior_router.post(
    "/funnel/calculate",
    response_model=Dict[str, Any],
    summary="计算转化漏斗"
)
def calculate_funnel(
    request: FunnelCalculateRequest,
    db: Session = Depends(get_db)
):
    """计算用户转化漏斗"""
    service = UserBehaviorService(db)
    service.set_request_context(request_id="auto", user_id="admin")

    funnel_date = None
    if request.funnel_date:
        funnel_date = datetime.fromisoformat(request.funnel_date)

    funnel = service.calculate_funnel(
        funnel_date=funnel_date,
        period_type=request.period_type,
        organizer_id=request.organizer_id,
        community_id=request.community_id
    )

    return {
        "success": True,
        "message": "漏斗计算完成",
        "data": {
            "funnel_date": funnel.funnel_date.isoformat(),
            "period_type": funnel.period_type,
            "impression_count": funnel.impression_count,
            "click_count": funnel.click_count,
            "detail_count": funnel.detail_count,
            "cart_count": funnel.cart_count,
            "checkout_count": funnel.checkout_count,
            "payment_count": funnel.payment_count,
            "click_rate": float(funnel.click_rate),
            "detail_rate": float(funnel.detail_rate),
            "cart_rate": float(funnel.cart_rate),
            "checkout_rate": float(funnel.checkout_rate),
            "payment_rate": float(funnel.payment_rate),
            "overall_conversion_rate": float(funnel.overall_conversion_rate)
        }
    }


@user_behavior_router.post(
    "/retention/calculate",
    response_model=Dict[str, Any],
    summary="计算用户留存"
)
def calculate_retention(
    request: RetentionCalculateRequest,
    db: Session = Depends(get_db)
):
    """计算用户留存率"""
    service = UserBehaviorService(db)
    service.set_request_context(request_id="auto", user_id="admin")

    cohort_date = None
    if request.cohort_date:
        cohort_date = datetime.fromisoformat(request.cohort_date)

    retention = service.calculate_retention(
        cohort_date=cohort_date,
        cohort_type=request.cohort_type,
        organizer_id=request.organizer_id,
        community_id=request.community_id
    )

    return {
        "success": True,
        "message": "留存计算完成",
        "data": {
            "cohort_date": retention.cohort_date.isoformat(),
            "cohort_type": retention.cohort_type,
            "cohort_size": retention.cohort_size,
            "retention_users": retention.retention_users,
            "retention_rates": retention.retention_rates,
            "period_days": retention.period_days
        }
    }


@user_behavior_router.get(
    "/{user_id}/segment",
    response_model=Dict[str, Any],
    summary="获取用户分群"
)
def get_user_segment(
    user_id: str,
    db: Session = Depends(get_db)
):
    """获取用户分群标签"""
    service = UserBehaviorService(db)
    segment = service.get_user_segment(user_id)

    return {
        "success": True,
        "data": {
            "user_id": user_id,
            "segment": segment.value,
            "segment_name": {
                "new_user": "新用户",
                "active_user": "活跃用户",
                "silent_user": "沉默用户",
                "lost_user": "流失用户",
                "high_value": "高价值用户"
            }.get(segment.value, segment.value)
        }
    }


@user_behavior_router.post(
    "/{user_id}/analyze",
    response_model=Dict[str, Any],
    summary="分析用户行为"
)
def analyze_user_behavior(
    user_id: str,
    behavior_date: Optional[str] = Query(None, description="分析日期"),
    db: Session = Depends(get_db)
):
    """分析单个用户行为"""
    service = UserBehaviorService(db)
    service.set_request_context(request_id="auto", user_id=user_id)

    date = None
    if behavior_date:
        date = datetime.fromisoformat(behavior_date)

    behavior = service.analyze_user_behavior(user_id, date)

    return {
        "success": True,
        "data": {
            "user_id": behavior.user_id,
            "behavior_date": behavior.behavior_date.isoformat(),
            "view_count": behavior.view_count,
            "click_count": behavior.click_count,
            "cart_count": behavior.cart_count,
            "order_count": behavior.order_count,
            "payment_count": behavior.payment_count,
            "total_spent": float(behavior.total_spent),
            "accumulated_spent": float(behavior.accumulated_spent),
            "user_segment": behavior.user_segment.value
        }
    }


# ==================== 商品分析 API ====================

@product_analytics_router.post(
    "/sales-rank",
    response_model=Dict[str, Any],
    summary="获取商品销售排行"
)
def get_sales_rank(
    request: SalesRankRequest,
    db: Session = Depends(get_db)
):
    """获取商品销售排行榜"""
    service = ProductAnalyticsService(db)
    service.set_request_context(request_id="auto", user_id="admin")

    rank_date = None
    if request.rank_date:
        rank_date = datetime.fromisoformat(request.rank_date)

    sales_rank = service.get_sales_rank(
        rank_date=rank_date,
        period_type=request.period_type,
        organizer_id=request.organizer_id,
        community_id=request.community_id,
        top_n=request.top_n
    )

    return {
        "success": True,
        "message": "销售排行计算完成",
        "data": {
            "rank_date": sales_rank.rank_date.isoformat(),
            "period_type": sales_rank.period_type,
            "total_products": sales_rank.total_products,
            "total_sales": float(sales_rank.total_sales),
            "top_products": sales_rank.top_products
        }
    }


@product_analytics_router.post(
    "/turnover/analyze",
    response_model=Dict[str, Any],
    summary="分析库存周转"
)
def analyze_turnover(
    request: TurnoverAnalysisRequest,
    db: Session = Depends(get_db)
):
    """分析商品库存周转"""
    service = ProductAnalyticsService(db)
    service.set_request_context(request_id="auto", user_id="admin")

    analysis_date = None
    if request.analysis_date:
        analysis_date = datetime.fromisoformat(request.analysis_date)

    turnover = service.analyze_turnover(
        product_id=request.product_id,
        organizer_id=request.organizer_id,
        analysis_date=analysis_date
    )

    return {
        "success": True,
        "message": "库存周转分析完成",
        "data": {
            "product_id": turnover.product_id,
            "analysis_date": turnover.analysis_date.isoformat(),
            "beginning_inventory": turnover.beginning_inventory,
            "ending_inventory": turnover.ending_inventory,
            "avg_inventory": turnover.avg_inventory,
            "sold_quantity": turnover.sold_quantity,
            "turnover_rate": float(turnover.turnover_rate),
            "turnover_days": float(turnover.turnover_days),
            "health_status": turnover.health_status,
            "suggestion": turnover.suggestion
        }
    }


# ==================== 预测分析 API ====================

@prediction_router.post(
    "/sales/predict",
    response_model=Dict[str, Any],
    summary="销量预测"
)
def predict_sales(
    request: SalesPredictionRequest,
    db: Session = Depends(get_db)
):
    """预测商品销量"""
    service = PredictionService(db)
    service.set_request_context(request_id="auto", user_id="admin")

    predict_date = None
    if request.predict_date:
        predict_date = datetime.fromisoformat(request.predict_date)

    prediction = service.predict_sales(
        product_id=request.product_id,
        predict_date=predict_date,
        organizer_id=request.organizer_id,
        community_id=request.community_id
    )

    return {
        "success": True,
        "message": "销量预测完成",
        "data": {
            "product_id": prediction.product_id,
            "predict_date": prediction.predict_date.isoformat(),
            "predicted_quantity": prediction.predicted_quantity,
            "predicted_sales": float(prediction.predicted_sales) if prediction.predicted_sales else 0,
            "confidence_level": float(prediction.confidence_level),
            "prediction_range_low": prediction.prediction_range_low,
            "prediction_range_high": prediction.prediction_range_high,
            "model_name": prediction.model_name,
            "model_version": prediction.model_version
        }
    }


@prediction_router.post(
    "/trend/analyze",
    response_model=Dict[str, Any],
    summary="销售趋势分析"
)
def analyze_trend(
    request: TrendAnalysisRequest,
    db: Session = Depends(get_db)
):
    """分析销售趋势"""
    service = PredictionService(db)
    service.set_request_context(request_id="auto", user_id="admin")

    trend_date = None
    if request.trend_date:
        trend_date = datetime.fromisoformat(request.trend_date)

    trend = service.analyze_trend(
        trend_date=trend_date,
        organizer_id=request.organizer_id,
        community_id=request.community_id
    )

    return {
        "success": True,
        "message": "趋势分析完成",
        "data": {
            "trend_date": trend.trend_date.isoformat(),
            "current_value": float(trend.current_value),
            "prev_value": float(trend.prev_value),
            "change_value": float(trend.change_value),
            "change_rate": float(trend.change_rate),
            "trend_direction": trend.trend_direction.value,
            "trend_strength": trend.trend_strength,
            "ma_7d": float(trend.ma_7d) if trend.ma_7d else 0
        }
    }


# ==================== 自定义报表 API ====================

@custom_report_router.post(
    "",
    response_model=Dict[str, Any],
    summary="创建自定义报表"
)
def create_custom_report(
    request: CustomReportCreateRequest,
    db: Session = Depends(get_db)
):
    """创建自定义报表"""
    service = CustomReportService(db)
    service.set_request_context(request_id="auto", user_id="user")

    report = service.create_report(
        user_id="user",
        report_name=request.report_name,
        config=request.config,
        report_description=request.report_description
    )

    return {
        "success": True,
        "message": "报表创建成功",
        "data": {
            "id": report.id,
            "report_name": report.report_name,
            "report_description": report.report_description,
            "config": report.config,
            "is_active": report.is_active
        }
    }


@custom_report_router.post(
    "/execute",
    response_model=Dict[str, Any],
    summary="执行自定义报表"
)
def execute_custom_report(
    request: CustomReportExecuteRequest,
    db: Session = Depends(get_db)
):
    """执行自定义报表查询"""
    service = CustomReportService(db)
    service.set_request_context(request_id="auto", user_id="user")

    result = service.execute_report(request.report_id)

    return {
        "success": True,
        "message": "报表执行成功",
        "data": {
            "report_id": result.report_id,
            "generated_at": result.generated_at.isoformat(),
            "execution_time_ms": result.execution_time_ms,
            "row_count": result.row_count,
            "status": result.status,
            "result_data": result.result_data
        }
    }


@custom_report_router.get(
    "/{report_id}/history",
    response_model=Dict[str, Any],
    summary="获取报表执行历史"
)
def get_report_history(
    report_id: str,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db)
):
    """获取自定义报表执行历史"""
    service = CustomReportService(db)
    result = service.get_report_history(report_id, page, page_size)

    return {
        "success": True,
        "data": {
            "total": result["total"],
            "page": result["page"],
            "page_size": result["page_size"],
            "results": [
                {
                    "id": r.id,
                    "generated_at": r.generated_at.isoformat(),
                    "execution_time_ms": r.execution_time_ms,
                    "row_count": r.row_count,
                    "status": r.status
                }
                for r in result["results"]
            ]
        }
    }
