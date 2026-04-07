"""
竞争情报与竞品分析模块 schema 定义 (P4)
"""
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime, date
from enum import Enum


class CompetitorSource(str, Enum):
    """竞品来源类型"""
    MANUAL = "manual"  # 手动添加
    SIMILARWEB = "similarweb"  # SimilarWeb API
    AHREFS = "ahrefs"  # Ahrefs API
    SEMRUSH = "semrush"  # SEMrush API
    AUTO_DISCOVER = "auto_discover"  # 自动发现


class Competitor(BaseModel):
    """竞品网站信息"""
    competitor_id: Optional[str] = Field(default=None, description="竞品 ID")
    domain: str = Field(description="竞品域名")
    name: Optional[str] = Field(default=None, description="竞品名称")
    description: Optional[str] = Field(default=None, description="竞品描述")
    source: CompetitorSource = Field(default=CompetitorSource.MANUAL, description="竞品来源")
    industry: Optional[str] = Field(default=None, description="所属行业")
    added_at: Optional[datetime] = Field(default=None, description="添加时间")
    tags: Optional[List[str]] = Field(default=None, description="标签列表")


class CompetitorCreateRequest(BaseModel):
    """创建竞品请求"""
    domain: str = Field(description="竞品域名")
    name: Optional[str] = Field(default=None, description="竞品名称")
    description: Optional[str] = Field(default=None, description="竞品描述")
    industry: Optional[str] = Field(default=None, description="所属行业")
    tags: Optional[List[str]] = Field(default=None, description="标签列表")


class CompetitorMetrics(BaseModel):
    """竞品流量指标"""
    domain: str = Field(description="域名")
    total_visits: int = Field(description="总访问量")
    unique_visitors: int = Field(description="独立访客数")
    avg_visit_duration: float = Field(description="平均访问时长 (秒)")
    pages_per_visit: float = Field(description="每次访问页数")
    bounce_rate: float = Field(description="跳出率 0-1")
    traffic_rank: Optional[int] = Field(default=None, description="全球流量排名")
    country_rank: Optional[int] = Field(default=None, description="国家流量排名")
    rank_change: Optional[float] = Field(default=None, description="排名变化率")


class CompetitorTrafficSources(BaseModel):
    """竞品流量来源分布"""
    domain: str = Field(description="域名")
    direct: float = Field(description="直接访问占比 0-1")
    referral: float = Field(description="引荐流量占比 0-1")
    search: float = Field(description="搜索流量占比 0-1")
    social: float = Field(description="社交流量占比 0-1")
    mail: float = Field(description="邮件营销占比 0-1")
    ads: float = Field(description="广告流量占比 0-1")
    display_ads: float = Field(description="展示广告占比 0-1")


class CompetitorKeywords(BaseModel):
    """竞品关键词分析"""
    domain: str = Field(description="域名")
    keyword: str = Field(description="关键词")
    position: int = Field(description="排名位置")
    search_volume: int = Field(description="搜索量")
    cpc: float = Field(description="点击成本")
    competition: float = Field(description="竞争程度 0-1")
    traffic_share: float = Field(description="流量占比 0-1")
    position_change: Optional[int] = Field(default=None, description="排名变化")


class CompetitorTopPages(BaseModel):
    """竞品热门页面"""
    domain: str = Field(description="域名")
    url: str = Field(description="页面 URL")
    title: Optional[str] = Field(default=None, description="页面标题")
    visits: int = Field(description="访问量")
    traffic_share: float = Field(description="流量占比 0-1")
    avg_time_on_page: float = Field(description="平均停留时间 (秒)")
    bounce_rate: float = Field(description="跳出率 0-1")
    top_keyword: Optional[str] = Field(default=None, description="主要关键词")


class CompetitorBacklinks(BaseModel):
    """竞品反向链接"""
    domain: str = Field(description="域名")
    source_url: str = Field(description="来源 URL")
    source_domain: str = Field(description="来源域名")
    anchor_text: Optional[str] = Field(default=None, description="锚文本")
    domain_authority: int = Field(description="来源域名权重")
    link_type: str = Field(description="链接类型：dofollow/nofollow")
    first_seen: Optional[date] = Field(default=None, description="首次发现时间")


class CompetitorAnalysisRequest(BaseModel):
    """竞品分析请求"""
    domains: List[str] = Field(description="竞品域名列表")
    start_date: Optional[date] = Field(default=None, description="开始日期")
    end_date: Optional[date] = Field(default=None, description="结束日期")
    metrics: Optional[List[str]] = Field(default=None, description="需要分析的指标")


class CompetitorComparisonResponse(BaseModel):
    """竞品对比响应"""
    your_domain: str = Field(description="你的域名")
    competitors: List[CompetitorMetrics] = Field(description="竞品指标列表")
    comparison_summary: Dict[str, Any] = Field(description="对比摘要")
    gap_analysis: List[Dict[str, Any]] = Field(description="差距分析")
    opportunities: List[str] = Field(description="发现的机会")
    threats: List[str] = Field(description="识别的威胁")


class KeywordGapAnalysis(BaseModel):
    """关键词差距分析"""
    your_keywords: List[Dict[str, Any]] = Field(description="你的关键词")
    competitor_keywords: List[Dict[str, Any]] = Field(description="竞品关键词")
    shared_keywords: List[Dict[str, Any]] = Field(description="共同关键词")
    your_unique: List[Dict[str, Any]] = Field(description="你独有的关键词")
    competitor_unique: List[Dict[str, Any]] = Field(description="竞品独有的关键词")
    missing_opportunities: List[Dict[str, Any]] = Field(description="缺失的机会关键词")


class ContentGapAnalysis(BaseModel):
    """内容差距分析"""
    your_top_content: List[Dict[str, Any]] = Field(description="你的热门内容")
    competitor_top_content: List[Dict[str, Any]] = Field(description="竞品热门内容")
    content_opportunities: List[str] = Field(description="内容机会主题")
    content_format_gaps: List[Dict[str, Any]] = Field(description="内容形式差距")


class BacklinkGapAnalysis(BaseModel):
    """反向链接差距分析"""
    your_backlinks_count: int = Field(description="你的反向链接数")
    competitor_backlinks_count: int = Field(description="竞品反向链接数")
    shared_domains: List[str] = Field(description="共同引用域名")
    competitor_exclusive_domains: List[str] = Field(description="竞品独有的引用域名")
    link_building_opportunities: List[Dict[str, Any]] = Field(description="外链建设机会")


class MarketPositionAnalysis(BaseModel):
    """市场定位分析"""
    market_share: Dict[str, float] = Field(description="市场份额分布")
    growth_trend: Dict[str, float] = Field(description="增长趋势")
    audience_overlap: Dict[str, float] = Field(description="受众重叠度")
    positioning_map: List[Dict[str, Any]] = Field(description="定位图谱")


class CompetitorAlert(BaseModel):
    """竞品动态告警"""
    alert_id: str = Field(description="告警 ID")
    competitor_domain: str = Field(description="竞品域名")
    alert_type: str = Field(description="告警类型")
    title: str = Field(description="告警标题")
    description: str = Field(description="告警描述")
    severity: str = Field(description="严重程度：low/medium/high/critical")
    detected_at: datetime = Field(description="检测时间")
    impact_score: Optional[float] = Field(default=None, description="影响分数 0-100")


class CompetitorAlertCreateRequest(BaseModel):
    """创建竞品告警请求"""
    competitor_domains: Optional[List[str]] = Field(default=None, description="监竞品域名列表")
    alert_types: Optional[List[str]] = Field(default=None, description="告警类型列表")
    severity_threshold: str = Field(default="low", description="告警级别阈值")


class CompetitorTrackingRequest(BaseModel):
    """竞品追踪请求"""
    domain: str = Field(description="竞品域名")
    tracking_metrics: List[str] = Field(description="追踪指标列表")
    frequency: str = Field(default="daily", description="追踪频率：daily/weekly/monthly")
    notifications: Optional[bool] = Field(default=True, description="是否开启通知")


class CompetitorReportConfig(BaseModel):
    """竞品报告配置"""
    report_name: str = Field(description="报告名称")
    competitors: List[str] = Field(description="竞品域名列表")
    sections: List[str] = Field(description="报告章节")
    format: str = Field(default="pdf", description="报告格式：pdf/html/markdown")
    schedule: Optional[str] = Field(default=None, description="生成计划：daily/weekly/monthly")
    recipients: Optional[List[str]] = Field(default=None, description="接收者邮箱列表")


# ==================== 市场趋势分析 ====================

class MarketTrend(BaseModel):
    """市场趋势"""
    trend_id: str = Field(description="趋势 ID")
    trend_name: str = Field(description="趋势名称")
    category: str = Field(description="趋势类别")
    growth_rate: float = Field(description="增长率")
    search_volume_trend: List[Dict[str, Any]] = Field(description="搜索量趋势")
    related_keywords: List[str] = Field(description="相关关键词")
    confidence_score: float = Field(description="置信度 0-1")
    detected_at: datetime = Field(description="检测时间")


class IndustryBenchmark(BaseModel):
    """行业基准"""
    industry: str = Field(description="行业")
    metric_name: str = Field(description="指标名称")
    percentile_25: float = Field(description="25 分位值")
    percentile_50: float = Field(description="50 分位值/中位数")
    percentile_75: float = Field(description="75 分位值")
    percentile_90: float = Field(description="90 分位值")
    sample_size: int = Field(description="样本数量")


class SWOTAnalysis(BaseModel):
    """SWOT 分析结果"""
    strengths: List[str] = Field(description="优势列表")
    weaknesses: List[str] = Field(description="劣势列表")
    opportunities: List[str] = Field(description="机会列表")
    threats: List[str] = Field(description="威胁列表")
    strategic_recommendations: List[str] = Field(description="战略建议")
