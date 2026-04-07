"""
流量分析模块 schema 定义
"""
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime, date
from enum import Enum


class TrafficSource(str, Enum):
    """流量来源枚举"""
    ORGANIC_SEARCH = "organic_search"
    DIRECT = "direct"
    SOCIAL_MEDIA = "social_media"
    REFERRAL = "referral"
    PAID_AD = "paid_ad"
    EMAIL = "email"
    OTHER = "other"


class DeviceType(str, Enum):
    """设备类型枚举"""
    DESKTOP = "desktop"
    MOBILE = "mobile"
    TABLET = "tablet"
    OTHER = "other"


class TrafficOverviewRequest(BaseModel):
    """流量概览请求"""
    start_date: date = Field(description="开始日期")
    end_date: date = Field(description="结束日期")
    domain: Optional[str] = Field(default=None, description="域名（可选，默认全部）")
    sources: Optional[List[TrafficSource]] = Field(default=None, description="流量来源筛选")


class TrafficMetrics(BaseModel):
    """流量指标"""
    visitors: int = Field(description="访问人数")
    page_views: int = Field(description="页面浏览量")
    avg_session_duration: float = Field(description="平均会话时长（秒）")
    bounce_rate: float = Field(description="跳出率 0-1")
    conversion_rate: float = Field(description="转化率 0-1")
    ctr: float = Field(description="点击率 0-1")
    avg_position: float = Field(description="平均搜索排名")


class TrafficSourceItem(BaseModel):
    """流量来源项"""
    source: TrafficSource = Field(description="流量来源")
    visitors: int = Field(description="访问人数")
    percentage: float = Field(description="占比 0-1")
    conversion_rate: float = Field(description="转化率 0-1")


class TrafficOverviewResponse(BaseModel):
    """流量概览响应"""
    period: Dict[str, date] = Field(description="统计周期")
    total: TrafficMetrics = Field(description="总体指标")
    comparison: Dict[str, float] = Field(description="与上期对比变化率")
    sources: List[TrafficSourceItem] = Field(description="流量来源分布")
    daily_trend: List[Dict[str, Any]] = Field(description="每日趋势数据")
    device_distribution: Dict[DeviceType, float] = Field(description="设备分布占比")


class PagePerformanceItem(BaseModel):
    """页面性能项"""
    url: str = Field(description="页面URL")
    title: str = Field(description="页面标题")
    page_views: int = Field(description="页面浏览量")
    unique_visitors: int = Field(description="独立访客数")
    avg_time_on_page: float = Field(description="平均停留时间（秒）")
    exit_rate: float = Field(description="退出率 0-1")
    seo_score: float = Field(description="SEO分数")


class PagePerformanceResponse(BaseModel):
    """页面性能响应"""
    pages: List[PagePerformanceItem] = Field(description="页面列表")
    total: int = Field(description="总页面数")
    top_performing: List[PagePerformanceItem] = Field(description="表现最好的页面")
    underperforming: List[PagePerformanceItem] = Field(description="表现不佳的页面")


class KeywordRankingItem(BaseModel):
    """关键词排名项"""
    keyword: str = Field(description="关键词")
    current_position: int = Field(description="当前排名")
    previous_position: Optional[int] = Field(default=None, description="上期排名")
    search_volume: int = Field(description="搜索量")
    ctr: float = Field(description="点击率")
    traffic_share: float = Field(description="流量占比 0-1")


class KeywordRankingResponse(BaseModel):
    """关键词排名响应"""
    keywords: List[KeywordRankingItem] = Field(description="关键词列表")
    improved: List[KeywordRankingItem] = Field(description="排名上升的关键词")
    declined: List[KeywordRankingItem] = Field(description="排名下降的关键词")
    new_entries: List[KeywordRankingItem] = Field(description="新进入排名的关键词")
    dropped: List[KeywordRankingItem] = Field(description="掉出排名的关键词")


# ==================== 事件追踪模块 (P3 新增) ====================

class EventType(str, Enum):
    """事件类型枚举"""
    PAGE_VIEW = "page_view"
    CLICK = "click"
    FORM_SUBMIT = "form_submit"
    PURCHASE = "purchase"
    SIGN_UP = "sign_up"
    LOGIN = "login"
    DOWNLOAD = "download"
    VIDEO_PLAY = "video_play"
    CUSTOM = "custom"


class UserIdentity(BaseModel):
    """用户身份标识"""
    user_id: Optional[str] = Field(default=None, description="登录用户 ID")
    device_id: Optional[str] = Field(default=None, description="设备 ID")
    session_id: str = Field(description="会话 ID")
    anonymous_id: Optional[str] = Field(default=None, description="匿名用户 ID")


class EventContext(BaseModel):
    """事件上下文"""
    page_url: str = Field(description="页面 URL")
    page_title: Optional[str] = Field(default=None, description="页面标题")
    referrer: Optional[str] = Field(default=None, description="来源页面")
    user_agent: Optional[str] = Field(default=None, description="User-Agent")
    ip_address: Optional[str] = Field(default=None, description="IP 地址")
    country: Optional[str] = Field(default=None, description="国家")
    city: Optional[str] = Field(default=None, description="城市")
    screen_resolution: Optional[str] = Field(default=None, description="屏幕分辨率")
    language: Optional[str] = Field(default=None, description="语言")
    timezone: Optional[str] = Field(default=None, description="时区")


class DeviceInfo(BaseModel):
    """设备信息"""
    device_type: DeviceType = Field(description="设备类型")
    os: Optional[str] = Field(default=None, description="操作系统")
    os_version: Optional[str] = Field(default=None, description="操作系统版本")
    browser: Optional[str] = Field(default=None, description="浏览器")
    browser_version: Optional[str] = Field(default=None, description="浏览器版本")


class TrackingEvent(BaseModel):
    """追踪事件"""
    event_id: Optional[str] = Field(default=None, description="事件 ID")
    event_type: EventType = Field(description="事件类型")
    event_name: str = Field(description="事件名称")
    timestamp: datetime = Field(description="事件时间戳")
    user: UserIdentity = Field(description="用户身份")
    context: EventContext = Field(description="事件上下文")
    device: Optional[DeviceInfo] = Field(default=None, description="设备信息")
    properties: Optional[Dict[str, Any]] = Field(default=None, description="事件属性")
    value: Optional[float] = Field(default=None, description="事件值 (如金额)")
    currency: Optional[str] = Field(default=None, description="货币单位")


class TrackingEventResponse(BaseModel):
    """事件追踪响应"""
    event_id: str = Field(description="事件 ID")
    status: str = Field(description="处理状态")
    message: str = Field(description="响应消息")


class TrackingBatchResponse(BaseModel):
    """批量事件追踪响应"""
    total: int = Field(description="总事件数")
    success: int = Field(description="成功数")
    failed: int = Field(description="失败数")
    message: str = Field(description="响应消息")


# ==================== 转化漏斗模块 (P3 新增) ====================

class FunnelStep(BaseModel):
    """漏斗步骤"""
    step_id: str = Field(description="步骤 ID")
    step_name: str = Field(description="步骤名称")
    step_order: int = Field(description="步骤顺序")
    event_name: str = Field(description="关联事件名称")
    description: Optional[str] = Field(default=None, description="步骤描述")


class FunnelCreateRequest(BaseModel):
    """创建漏斗请求"""
    funnel_name: str = Field(description="漏斗名称")
    description: Optional[str] = Field(default=None, description="漏斗描述")
    steps: List[FunnelStep] = Field(description="漏斗步骤列表")
    start_date: date = Field(description="开始日期")
    end_date: date = Field(description="结束日期")
    domain: Optional[str] = Field(default=None, description="域名筛选")


class FunnelStepResult(BaseModel):
    """漏斗步骤结果"""
    step_id: str = Field(description="步骤 ID")
    step_name: str = Field(description="步骤名称")
    step_order: int = Field(description="步骤顺序")
    users: int = Field(description="该步骤用户数")
    conversion_rate: float = Field(description="转化率 (相对上一步)")
    overall_conversion_rate: float = Field(description="整体转化率 (相对第一步)")
    avg_time_to_step: Optional[float] = Field(default=None, description="平均到达时间 (秒)")


class FunnelAnalysisResult(BaseModel):
    """漏斗分析结果"""
    funnel_id: str = Field(description="漏斗 ID")
    funnel_name: str = Field(description="漏斗名称")
    period: Dict[str, date] = Field(description="统计周期")
    total_entries: int = Field(description="入口总用户数")
    total_completions: int = Field(description="完成总用户数")
    overall_conversion_rate: float = Field(description="整体转化率")
    steps: List[FunnelStepResult] = Field(description="各步骤结果")
    drop_off_points: List[Dict[str, Any]] = Field(description="流失严重节点")
    recommendations: List[str] = Field(description="优化建议")


# ==================== 用户分群模块 (P3 新增) ====================

class SegmentCondition(BaseModel):
    """分群条件"""
    field: str = Field(description="字段名称")
    operator: str = Field(description="操作符：eq, neq, gt, lt, contains, in")
    value: Any = Field(description="比较值")


class UserSegmentCreateRequest(BaseModel):
    """创建用户分群请求"""
    segment_name: str = Field(description="分群名称")
    description: Optional[str] = Field(default=None, description="分群描述")
    conditions: List[SegmentCondition] = Field(description="分群条件列表")
    logic: str = Field(default="AND", description="条件逻辑：AND, OR")
    start_date: Optional[date] = Field(default=None, description="开始日期")
    end_date: Optional[date] = Field(default=None, description="结束日期")


class UserSegmentResponse(BaseModel):
    """用户分群响应"""
    segment_id: str = Field(description="分群 ID")
    segment_name: str = Field(description="分群名称")
    description: Optional[str] = Field(description="分群描述")
    user_count: int = Field(description="用户数量")
    conditions: List[SegmentCondition] = Field(description="分群条件")
    logic: str = Field(description="条件逻辑")
    created_at: datetime = Field(description="创建时间")


class UserSegmentDetail(BaseModel):
    """用户分群详情"""
    segment: UserSegmentResponse = Field(description="分群信息")
    user_demographics: Dict[str, Any] = Field(description="用户人口统计")
    top_pages: List[Dict[str, Any]] = Field(description="常访问页面 TopN")
    top_events: List[Dict[str, Any]] = Field(description="高频事件 TopN")
    avg_session_duration: float = Field(description="平均会话时长")
    avg_sessions_per_user: float = Field(description="人均会话数")
    retention_rate: Optional[float] = Field(default=None, description="留存率")
