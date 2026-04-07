"""
流量分析 API 路由
"""
from fastapi import APIRouter, Query, Body, Path
from typing import Optional, List, Dict
from datetime import date, datetime
from schemas.analytics import (
    TrafficOverviewRequest,
    TrafficOverviewResponse,
    PagePerformanceResponse,
    KeywordRankingResponse,
    TrackingEvent,
    TrackingEventResponse,
    TrackingBatchResponse,
    FunnelCreateRequest,
    FunnelAnalysisResult,
    UserSegmentCreateRequest,
    UserSegmentResponse,
    UserSegmentDetail
)
from schemas.common import Response
from core.response import success
from .service import analytics_service
from .event_tracking import event_tracking_service
from .funnel_analysis import funnel_analysis_service
from .user_segment import user_segment_service
from core.exceptions import AnalyticsQueryFailedException

router = APIRouter(prefix="/analytics", tags=["流量分析"])


@router.post("/traffic/overview", response_model=Response[TrafficOverviewResponse])
async def get_traffic_overview(request: TrafficOverviewRequest):
    """
    获取流量概览数据
    - 总体流量指标：访客数、浏览量、平均会话时长、跳出率、转化率等
    - 与上期对比的变化趋势
    - 流量来源分布：自然搜索、直接访问、社交媒体、引荐、付费广告等
    - 每日流量趋势
    - 设备类型分布
    """
    if request.start_date > request.end_date:
        raise AnalyticsQueryFailedException("开始日期不能晚于结束日期")

    if (request.end_date - request.start_date).days > 365:
        raise AnalyticsQueryFailedException("查询时间范围不能超过 1 年")

    result = analytics_service.get_traffic_overview(request)
    return success(data=result)


@router.get("/traffic/pages", response_model=Response[PagePerformanceResponse])
async def get_page_performance(
    start_date: date = Query(..., description="开始日期"),
    end_date: date = Query(..., description="结束日期"),
    domain: Optional[str] = Query(default=None, description="域名筛选")
):
    """
    获取页面性能数据
    - 所有页面的浏览量、独立访客数、平均停留时间、退出率、SEO 分数
    - 表现最好的 Top3 页面
    - 表现不佳需要优化的 Top3 页面
    """
    if start_date > end_date:
        raise AnalyticsQueryFailedException("开始日期不能晚于结束日期")

    result = analytics_service.get_page_performance(start_date, end_date, domain)
    return success(data=result)


@router.get("/keywords/ranking", response_model=Response[KeywordRankingResponse])
async def get_keyword_ranking(
    start_date: date = Query(..., description="开始日期"),
    end_date: date = Query(..., description="结束日期")
):
    """
    获取关键词排名数据
    - 所有关键词的当前排名、搜索量、点击率、流量占比
    - 排名上升的关键词列表
    - 排名下降的关键词列表
    - 新进入前 30 的关键词
    - 掉出前 30 的关键词
    """
    if start_date > end_date:
        raise AnalyticsQueryFailedException("开始日期不能晚于结束日期")

    result = analytics_service.get_keyword_ranking(start_date, end_date)
    return success(data=result)


@router.post("/traffic/import", summary="批量导入流量数据")
async def import_traffic_data(
    data: Dict = Body(..., description="流量数据，包含 data 字段为日志列表")
):
    """
    批量导入流量数据
    - 支持导入标准化的访问日志数据
    - 支持 Nginx、Apache 等多种日志格式的导入
    - 自动识别流量来源和用户行为
    """
    if "data" not in data or not isinstance(data["data"], list):
        raise AnalyticsQueryFailedException("请求格式错误，缺少 data 字段或格式不正确")

    imported_count = analytics_service.import_traffic_data(data["data"])
    return success(data={"imported": imported_count}, message=f"成功导入 {imported_count} 条流量数据")


# ==================== 事件追踪 API (P3 新增) ====================

@router.post("/track", response_model=Response[TrackingEventResponse], summary="追踪单个事件")
async def track_event(event: TrackingEvent):
    """
    追踪单个事件

    对标 Google Analytics 的事件采集能力：
    - 支持页面浏览、点击、表单提交、购买等事件
    - 支持自定义事件属性
    - 自动用户身份识别
    """
    result = event_tracking_service.track_event(event)
    return success(data=result)


@router.post("/track/batch", response_model=Response[TrackingBatchResponse], summary="批量追踪事件")
async def track_batch_events(events: List[TrackingEvent] = Body(...)):
    """
    批量追踪事件

    - 支持批量上报事件（推荐每次不超过 100 条）
    - 部分成功时返回成功/失败数量
    """
    result = event_tracking_service.track_batch(events)
    return success(data=result)


@router.get("/events", summary="查询事件")
async def query_events(
    start_date: date = Query(..., description="开始日期"),
    end_date: date = Query(..., description="结束日期"),
    event_type: Optional[str] = Query(default=None, description="事件类型"),
    event_name: Optional[str] = Query(default=None, description="事件名称"),
    user_id: Optional[str] = Query(default=None, description="用户 ID"),
    session_id: Optional[str] = Query(default=None, description="会话 ID"),
    page_url: Optional[str] = Query(default=None, description="页面 URL"),
    limit: int = Query(default=1000, description="返回数量限制")
):
    """
    查询追踪的事件

    - 支持多维度筛选
    - 返回事件详情
    """
    events = event_tracking_service.get_events(
        start_date=start_date,
        end_date=end_date,
        event_type=event_type,
        event_name=event_name,
        user_id=user_id,
        session_id=session_id,
        page_url=page_url,
        limit=limit
    )
    return success(data={"events": [e.__dict__ for e in events], "total": len(events)})


@router.get("/tracking-snippet", summary="获取前端追踪代码")
async def get_tracking_snippet(site_id: str = Query(..., description="站点 ID")):
    """
    获取前端 JavaScript 追踪代码

    返回可直接嵌入网页的追踪脚本
    """
    snippet = event_tracking_service.generate_client_snippet(site_id)
    return success(data={"site_id": site_id, "snippet": snippet})


# ==================== 转化漏斗 API (P3 新增) ====================

@router.post("/funnel/create", response_model=Response[Dict], summary="创建漏斗分析")
async def create_funnel(request: FunnelCreateRequest):
    """
    创建转化漏斗分析

    对标 Google Analytics 的漏斗分析能力：
    - 自定义漏斗步骤
    - 转化率计算
    - 流失节点识别
    - 优化建议生成
    """
    funnel_id = funnel_analysis_service.create_funnel(request)
    return success(data={"funnel_id": funnel_id, "message": "漏斗创建成功"})


@router.get("/funnel/templates", summary="获取漏斗模板")
async def get_funnel_templates():
    """
    获取预定义的漏斗模板

    内置模板：
    - ecommerce: 电商购买漏斗
    - saas_signup: SaaS 注册漏斗
    - content_engagement: 内容互动漏斗
    - mobile_app_install: App 安装漏斗
    """
    templates = funnel_analysis_service._templates
    return success(data={"templates": list(templates.keys()), "details": templates})


@router.get("/funnel/{funnel_id}/analyze", response_model=Response[FunnelAnalysisResult], summary="分析漏斗")
async def analyze_funnel(
    funnel_id: str = Path(..., description="漏斗 ID"),
    start_date: Optional[date] = Query(default=None, description="开始日期（可选）"),
    end_date: Optional[date] = Query(default=None, description="结束日期（可选）")
):
    """
    执行漏斗分析

    - 计算每个步骤的转化率
    - 识别流失严重的节点
    - 生成优化建议
    """
    result = funnel_analysis_service.analyze_funnel(funnel_id, start_date, end_date)
    if not result:
        raise AnalyticsQueryFailedException("漏斗不存在")
    return success(data=result)


@router.get("/funnel/{funnel_id}/compare", summary="漏斗周期对比")
async def compare_funnel_periods(
    funnel_id: str = Path(..., description="漏斗 ID"),
    period1_start: date = Query(..., description="第一期开始日期"),
    period1_end: date = Query(..., description="第一期结束日期"),
    period2_start: date = Query(..., description="第二期开始日期"),
    period2_end: date = Query(..., description="第二期结束日期")
):
    """
    对比两个时间段的漏斗表现

    - 流量变化分析
    - 转化率变化分析
    - 转化量变化分析
    """
    result = funnel_analysis_service.compare_funnel_periods(
        funnel_id, period1_start, period1_end, period2_start, period2_end
    )
    if not result:
        raise AnalyticsQueryFailedException("漏斗分析失败")
    return success(data=result)


# ==================== 用户分群 API (P3 新增) ====================

@router.post("/segment/create", response_model=Response[UserSegmentResponse], summary="创建用户分群")
async def create_segment(request: UserSegmentCreateRequest):
    """
    创建用户分群

    对标 Google Analytics 的用户分群能力：
    - 多维度条件筛选
    - 动态用户计数
    - 支持 AND/OR 逻辑
    """
    result = user_segment_service.create_segment(request)
    return success(data=result)


@router.get("/segment/templates", summary="获取分群模板")
async def get_segment_templates():
    """
    获取预定义的用户分群模板

    内置模板：
    - high_value_users: 高价值用户
    - mobile_users: 移动端用户
    - new_users: 新用户
    - churned_users: 流失用户
    - engaged_users: 高参与度用户
    - organic_search_users: 自然搜索用户
    """
    templates = user_segment_service._templates
    return success(data={"templates": list(templates.keys())})


@router.get("/segment/list", response_model=Response[List[UserSegmentResponse]], summary="列出所有分群")
async def list_segments():
    """列出所有已创建的用户分群"""
    segments = user_segment_service.list_segments()
    return success(data=segments)


@router.get("/segment/{segment_id}", response_model=Response[UserSegmentDetail], summary="获取分群详情")
async def get_segment_detail(
    segment_id: str = Path(..., description="分群 ID")
):
    """
    获取用户分群详情

    - 分群基本信息
    - 用户人口统计
    - Top 访问页面
    - Top 事件
    - 会话统计
    """
    detail = user_segment_service.get_segment_detail(segment_id)
    if not detail:
        raise AnalyticsQueryFailedException("分群不存在")
    return success(data=detail)


@router.get("/segment/{segment_id}/retention", summary="计算分群留存率")
async def get_segment_retention(
    segment_id: str = Path(..., description="分群 ID"),
    retention_days: int = Query(default=7, description="留存天数")
):
    """
    计算用户留存率

    - 返回每日留存率
    - 支持自定义留存天数
    """
    retention = user_segment_service.calculate_retention(segment_id, retention_days)
    return success(data={"segment_id": segment_id, "retention_rates": retention})


@router.delete("/segment/{segment_id}", summary="删除分群")
async def delete_segment(
    segment_id: str = Path(..., description="分群 ID")
):
    """删除指定的用户分群"""
    success_result = user_segment_service.delete_segment(segment_id)
    if success_result:
        return success(message="分群删除成功")
    else:
        raise AnalyticsQueryFailedException("分群不存在")
