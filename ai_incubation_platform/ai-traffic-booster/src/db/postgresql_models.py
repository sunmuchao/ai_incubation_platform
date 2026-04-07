"""
PostgreSQL 数据库模型定义 - P0 数据持久化增强

包含以下核心表:
1. events - 事件明细存储
2. funnels - 漏斗配置存储
3. segments - 用户分群存储
4. competitors - 竞品数据存储
5. traffic_data_enhanced - 增强流量数据
6. keyword_rankings - 关键词排名历史
7. ab_tests / ab_test_results - A/B 测试 (已有)
8. seo_analyses - SEO 分析 (已有)
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, Boolean, ForeignKey, Enum as SQLEnum, Index, BigInteger
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from . import Base


# ==================== 事件追踪表 ====================

class EventTypeEnum(str, enum.Enum):
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


class DeviceTypeEnum(str, enum.Enum):
    """设备类型枚举"""
    DESKTOP = "desktop"
    MOBILE = "mobile"
    TABLET = "tablet"
    OTHER = "other"


class EventModel(Base):
    """
    事件明细表 - 存储所有追踪事件

    设计要点:
    - 使用 BigInt 作为主键，支持海量数据
    - 按日期和事件类型建立复合索引，加速查询
    - 支持分区表 (按日期分区)
    """
    __tablename__ = "events"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    event_id = Column(String(64), unique=True, nullable=False, index=True)

    # 事件基本信息
    event_type = Column(SQLEnum(EventTypeEnum), nullable=False, index=True)
    event_name = Column(String(255), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)

    # 用户身份
    user_id = Column(String(64), nullable=True, index=True)
    device_id = Column(String(64), nullable=True)
    session_id = Column(String(64), nullable=False, index=True)
    anonymous_id = Column(String(64), nullable=True, index=True)

    # 页面/上下文信息
    page_url = Column(String(512), nullable=False)
    page_title = Column(String(255), nullable=True)
    referrer = Column(String(512), nullable=True)

    # 设备信息
    device_type = Column(SQLEnum(DeviceTypeEnum), nullable=True)
    os = Column(String(64), nullable=True)
    os_version = Column(String(64), nullable=True)
    browser = Column(String(64), nullable=True)
    browser_version = Column(String(64), nullable=True)

    # 地理位置
    country = Column(String(64), nullable=True, index=True)
    region = Column(String(64), nullable=True)
    city = Column(String(64), nullable=True, index=True)
    ip_address = Column(String(45), nullable=True)

    # 事件属性和值
    properties = Column(JSON, nullable=True)
    value = Column(Float, nullable=True)
    currency = Column(String(3), nullable=True)

    # 系统字段
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed = Column(Boolean, default=False)  # 是否已处理

    # 索引优化
    __table_args__ = (
        Index('idx_event_date_type', 'timestamp', 'event_type'),
        Index('idx_event_session_date', 'session_id', 'timestamp'),
        Index('idx_event_user_date', 'user_id', 'timestamp'),
        Index('idx_event_page_date', 'page_url', 'timestamp'),
        Index('idx_event_country_date', 'country', 'timestamp'),
    )

    def __repr__(self):
        return f"<Event(id={self.id}, event_id={self.event_id}, type={self.event_type})>"


# ==================== 漏斗配置表 ====================

class FunnelModel(Base):
    """
    漏斗配置表 - 存储转化漏斗定义
    """
    __tablename__ = "funnels"

    id = Column(String(64), primary_key=True)
    funnel_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    domain = Column(String(255), nullable=True)

    # 状态
    is_active = Column(Boolean, default=True)
    is_template = Column(Boolean, default=False)  # 是否为预定义模板

    # 时间配置
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)

    # 创建信息
    created_by = Column(String(64), default="admin")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 关联的步骤
    steps = relationship("FunnelStepModel", back_populates="funnel", cascade="all, delete-orphan", order_by="FunnelStepModel.step_order")

    __table_args__ = (
        Index('idx_funnel_active', 'is_active'),
        Index('idx_funnel_template', 'is_template'),
    )

    def __repr__(self):
        return f"<Funnel(id={self.id}, name={self.funnel_name})>"


class FunnelStepModel(Base):
    """
    漏斗步骤表 - 存储漏斗的各个步骤
    """
    __tablename__ = "funnel_steps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    funnel_id = Column(String(64), ForeignKey("funnels.id"), nullable=False, index=True)

    # 步骤信息
    step_id = Column(String(32), nullable=False)
    step_name = Column(String(255), nullable=False)
    step_order = Column(Integer, nullable=False)
    event_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # 关联的漏斗
    funnel = relationship("FunnelModel", back_populates="steps")

    __table_args__ = (
        Index('idx_step_funnel_order', 'funnel_id', 'step_order'),
    )

    def __repr__(self):
        return f"<FunnelStep(funnel_id={self.funnel_id}, step_order={self.step_order}, name={self.step_name})>"


class FunnelResultModel(Base):
    """
    漏斗分析结果表 - 缓存漏斗分析结果
    """
    __tablename__ = "funnel_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    funnel_id = Column(String(64), ForeignKey("funnels.id"), nullable=False, index=True)

    # 分析周期
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)

    # 分析结果
    total_entries = Column(Integer, default=0)
    total_completions = Column(Integer, default=0)
    overall_conversion_rate = Column(Float, default=0.0)

    # 各步骤结果 (JSON 存储)
    step_results = Column(JSON, nullable=True)
    drop_off_points = Column(JSON, nullable=True)
    recommendations = Column(JSON, nullable=True)

    # 时间戳
    analyzed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 关联的漏斗
    funnel = relationship("FunnelModel")

    __table_args__ = (
        Index('idx_funnel_result_date', 'funnel_id', 'start_date', 'end_date'),
    )

    def __repr__(self):
        return f"<FunnelResult(funnel_id={self.funnel_id}, conversion_rate={self.overall_conversion_rate})>"


# ==================== 用户分群表 ====================

class SegmentModel(Base):
    """
    用户分群配置表
    """
    __tablename__ = "segments"

    id = Column(String(64), primary_key=True)
    segment_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # 分群条件
    conditions = Column(JSON, nullable=False)  # [{field, operator, value}, ...]
    logic = Column(String(10), default="AND")  # AND / OR

    # 时间范围
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)

    # 状态
    is_active = Column(Boolean, default=True)
    is_template = Column(Boolean, default=False)

    # 创建信息
    created_by = Column(String(64), default="admin")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index('idx_segment_active', 'is_active'),
        Index('idx_segment_template', 'is_template'),
    )

    def __repr__(self):
        return f"<Segment(id={self.id}, name={self.segment_name})>"


class SegmentResultModel(Base):
    """
    用户分群结果表 - 缓存分群分析结果
    """
    __tablename__ = "segment_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    segment_id = Column(String(64), ForeignKey("segments.id"), nullable=False, index=True)

    # 用户统计
    user_count = Column(Integer, default=0)
    user_ids = Column(JSON, nullable=True)  # 用户 ID 列表 (小分群)

    # 用户特征
    demographics = Column(JSON, nullable=True)
    top_pages = Column(JSON, nullable=True)
    top_events = Column(JSON, nullable=True)
    avg_session_duration = Column(Float, default=0.0)
    avg_sessions_per_user = Column(Float, default=0.0)

    # 留存率
    retention_rates = Column(JSON, nullable=True)  # {day1: rate, day7: rate, ...}

    # 时间戳
    analyzed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 关联的分群
    segment = relationship("SegmentModel")

    __table_args__ = (
        Index('idx_segment_result_date', 'segment_id', 'analyzed_at'),
    )

    def __repr__(self):
        return f"<SegmentResult(segment_id={self.segment_id}, user_count={self.user_count})>"


# ==================== 竞品数据表 ====================

class CompetitorModel(Base):
    """
    竞品信息表
    """
    __tablename__ = "competitors"

    id = Column(String(64), primary_key=True)
    domain = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)

    # 分类标签
    tags = Column(JSON, nullable=True)  # ["direct", "seo", "paid"]
    industry = Column(String(128), nullable=True)

    # 状态
    is_active = Column(Boolean, default=True)
    is_tracking = Column(Boolean, default=True)

    # 发现信息
    alexa_rank = Column(Integer, nullable=True)
    estimated_monthly_visits = Column(Integer, nullable=True)

    # 创建信息
    added_by = Column(String(64), default="admin")
    added_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 关联数据
    metrics_history = relationship("CompetitorMetricsModel", back_populates="competitor", cascade="all, delete-orphan")
    keywords = relationship("CompetitorKeywordsModel", back_populates="competitor", cascade="all, delete-orphan")
    backlinks = relationship("CompetitorBacklinksModel", back_populates="competitor", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_competitor_active', 'is_active'),
        Index('idx_competitor_industry', 'industry'),
    )

    def __repr__(self):
        return f"<Competitor(id={self.id}, domain={self.domain})>"


class CompetitorMetricsModel(Base):
    """
    竞品指标历史表
    """
    __tablename__ = "competitor_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    competitor_id = Column(String(64), ForeignKey("competitors.id"), nullable=False, index=True)

    # 日期
    date = Column(DateTime, nullable=False, index=True)

    # 流量指标
    visitors = Column(Integer, default=0)
    page_views = Column(Integer, default=0)
    avg_visit_duration = Column(Float, default=0.0)
    bounce_rate = Column(Float, default=0.0)

    # 来源分布 (JSON)
    traffic_sources = Column(JSON, nullable=True)  # {organic: %, direct: %, ...}

    # 创建设备分布
    device_distribution = Column(JSON, nullable=True)  # {desktop: %, mobile: %, tablet: %}

    # 地理分布 Top5
    geo_distribution = Column(JSON, nullable=True)  # [{country: %, ...}, ...]

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 关联的竞品
    competitor = relationship("CompetitorModel", back_populates="metrics_history")

    __table_args__ = (
        Index('idx_competitor_metrics_date', 'competitor_id', 'date'),
    )

    def __repr__(self):
        return f"<CompetitorMetrics(competitor_id={self.competitor_id}, date={self.date})>"


class CompetitorKeywordsModel(Base):
    """
    竞品关键词表
    """
    __tablename__ = "competitor_keywords"

    id = Column(Integer, primary_key=True, autoincrement=True)
    competitor_id = Column(String(64), ForeignKey("competitors.id"), nullable=False, index=True)

    # 关键词信息
    keyword = Column(String(255), nullable=False, index=True)
    position = Column(Integer, nullable=True)
    search_volume = Column(Integer, default=0)
    cpc = Column(Float, default=0.0)
    competition = Column(Float, default=0.0)
    url = Column(String(512), nullable=True)

    # 时间戳
    captured_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 关联的竞品
    competitor = relationship("CompetitorModel", back_populates="keywords")

    __table_args__ = (
        Index('idx_keyword_competitor', 'competitor_id', 'keyword'),
        Index('idx_keyword_position', 'position'),
    )

    def __repr__(self):
        return f"<CompetitorKeyword(keyword={self.keyword}, position={self.position})>"


class CompetitorBacklinksModel(Base):
    """
    竞品反向链接表
    """
    __tablename__ = "competitor_backlinks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    competitor_id = Column(String(64), ForeignKey("competitors.id"), nullable=False, index=True)

    # 外链信息
    source_url = Column(String(512), nullable=False)
    source_domain = Column(String(255), nullable=False, index=True)
    target_url = Column(String(512), nullable=True)
    anchor_text = Column(String(255), nullable=True)

    # 权重指标
    domain_authority = Column(Integer, nullable=True)
    page_authority = Column(Integer, nullable=True)
    is_dofollow = Column(Boolean, default=True)

    # 时间戳
    discovered_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 关联的竞品
    competitor = relationship("CompetitorModel", back_populates="backlinks")

    __table_args__ = (
        Index('idx_backlink_source', 'source_domain'),
        Index('idx_backlink_authority', 'domain_authority'),
    )

    def __repr__(self):
        return f"<CompetitorBacklink(source={self.source_domain})>"


# ==================== 增强流量数据表 ====================

class TrafficDataEnhancedModel(Base):
    """
    增强流量数据表 - 支持更细粒度的流量分析
    """
    __tablename__ = "traffic_data_enhanced"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # 数据标识
    domain = Column(String(255), nullable=True, index=True)
    path = Column(String(512), nullable=True, index=True)
    date = Column(DateTime, nullable=False, index=True)
    hour = Column(Integer, nullable=True)  # 小时粒度 (0-23)

    # 基础流量指标
    visitors = Column(Integer, default=0)
    unique_visitors = Column(Integer, default=0)
    page_views = Column(Integer, default=0)
    sessions = Column(Integer, default=0)

    # 质量指标
    avg_session_duration = Column(Float, default=0.0)
    bounce_rate = Column(Float, default=0.0)
    pages_per_session = Column(Float, default=0.0)

    # 转化指标
    conversions = Column(Integer, default=0)
    conversion_rate = Column(Float, default=0.0)
    revenue = Column(Float, default=0.0)

    # 流量来源
    source = Column(String(64), nullable=True, index=True)  # organic, direct, social, referral, paid, email
    medium = Column(String(64), nullable=True)
    campaign = Column(String(255), nullable=True)

    # 设备分布
    device_desktop = Column(Integer, default=0)
    device_mobile = Column(Integer, default=0)
    device_tablet = Column(Integer, default=0)

    # 地理信息
    country = Column(String(64), nullable=True, index=True)
    region = Column(String(64), nullable=True)
    city = Column(String(64), nullable=True)

    # 原始数据
    raw_data = Column(JSON, nullable=True)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index('idx_traffic_date_source', 'date', 'source'),
        Index('idx_traffic_date_device', 'date', 'domain'),
        Index('idx_traffic_date_country', 'date', 'country'),
    )

    def __repr__(self):
        return f"<TrafficDataEnhanced(date={self.date}, path={self.path}, visitors={self.visitors})>"


# ==================== 关键词排名历史表 ====================

class KeywordRankingModel(Base):
    """
    关键词排名历史表
    """
    __tablename__ = "keyword_rankings"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # 关键词信息
    keyword = Column(String(255), nullable=False, index=True)
    domain = Column(String(255), nullable=True, index=True)
    url = Column(String(512), nullable=True)

    # 排名数据
    position = Column(Integer, nullable=True, index=True)
    previous_position = Column(Integer, nullable=True)
    position_change = Column(Integer, default=0)

    # 搜索指标
    search_volume = Column(Integer, default=0)
    cpc = Column(Float, default=0.0)
    competition = Column(Float, default=0.0)

    # 表现指标
    ctr = Column(Float, default=0.0)
    traffic_share = Column(Float, default=0.0)

    # 时间戳
    tracked_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index('idx_ranking_keyword_date', 'keyword', 'tracked_at'),
        Index('idx_ranking_domain_date', 'domain', 'tracked_at'),
    )

    def __repr__(self):
        return f"<KeywordRanking(keyword={self.keyword}, position={self.position})>"


# ==================== 告警配置表 ====================

class AlertModel(Base):
    """
    告警配置表
    """
    __tablename__ = "alerts"

    id = Column(String(64), primary_key=True)
    alert_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # 告警类型
    alert_type = Column(String(64), nullable=False)  # traffic_drop, ranking_drop, competitor_change, etc.
    severity = Column(String(16), default="warning")  # info, warning, error, critical

    # 触发条件
    conditions = Column(JSON, nullable=False)
    threshold = Column(Float, nullable=True)

    # 通知配置
    notification_channels = Column(JSON, nullable=True)  # [email, slack, webhook]
    recipients = Column(JSON, nullable=True)

    # 状态
    is_active = Column(Boolean, default=True)
    last_triggered_at = Column(DateTime, nullable=True)

    # 创建信息
    created_by = Column(String(64), default="admin")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 关联的告警历史
    history = relationship("AlertHistoryModel", back_populates="alert", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_alert_active', 'is_active'),
        Index('idx_alert_type', 'alert_type'),
    )

    def __repr__(self):
        return f"<Alert(id={self.id}, name={self.alert_name}, type={self.alert_type})>"


class AlertHistoryModel(Base):
    """
    告警历史表
    """
    __tablename__ = "alert_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_id = Column(String(64), ForeignKey("alerts.id"), nullable=False, index=True)

    # 触发信息
    triggered_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    trigger_reason = Column(Text, nullable=True)
    trigger_value = Column(Float, nullable=True)
    threshold = Column(Float, nullable=True)

    # 通知状态
    notification_sent = Column(Boolean, default=False)
    notification_result = Column(JSON, nullable=True)

    # 关联的告警
    alert = relationship("AlertModel", back_populates="history")

    __table_args__ = (
        Index('idx_alert_history_date', 'alert_id', 'triggered_at'),
    )

    def __repr__(self):
        return f"<AlertHistory(alert_id={self.alert_id}, triggered_at={self.triggered_at})>"


# ==================== 日志持久化表 ====================

class LogLevelEnum(str, enum.Enum):
    """日志级别枚举"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class SystemLogModel(Base):
    """
    系统日志表 - 持久化关键日志
    """
    __tablename__ = "system_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # 日志基本信息
    level = Column(SQLEnum(LogLevelEnum), nullable=False, index=True)
    message = Column(Text, nullable=False)
    logger_name = Column(String(255), nullable=True, index=True)

    # 上下文信息
    trace_id = Column(String(64), nullable=True, index=True)  # 请求追踪 ID
    module = Column(String(128), nullable=True)
    function = Column(String(128), nullable=True)
    line_number = Column(Integer, nullable=True)

    # 额外数据
    extra_data = Column(JSON, nullable=True)  # 结构化额外数据
    request_id = Column(String(64), nullable=True, index=True)

    # 异常信息
    exception_type = Column(String(255), nullable=True)
    exception_message = Column(Text, nullable=True)
    exception_traceback = Column(Text, nullable=True)

    # 性能数据
    duration_ms = Column(Float, nullable=True)  # 操作耗时

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    __table_args__ = (
        Index('idx_log_level_date', 'level', 'created_at'),
        Index('idx_log_trace_date', 'trace_id', 'created_at'),
        Index('idx_log_module_date', 'logger_name', 'created_at'),
    )

    def __repr__(self):
        return f"<SystemLog(id={self.id}, level={self.level}, message={self.message[:50]}...)"
