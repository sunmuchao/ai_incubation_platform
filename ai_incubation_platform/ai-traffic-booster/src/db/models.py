"""
数据库模型定义
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from . import Base


class ABTestStatusEnum(str, enum.Enum):
    """A/B 测试状态枚举"""
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ABTestModel(Base):
    """A/B 测试数据库模型"""
    __tablename__ = "ab_tests"

    id = Column(String(64), primary_key=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    page_url = Column(String(512), nullable=False)
    status = Column(SQLEnum(ABTestStatusEnum), default=ABTestStatusEnum.DRAFT)

    # 测试配置
    variants = Column(JSON, nullable=False)  # 存储变体配置
    goals = Column(JSON, nullable=False)     # 存储目标配置
    confidence_level = Column(Float, default=0.95)
    minimum_sample_size = Column(Integer, default=1000)

    # 时间戳
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(String(64), default="admin")

    # 关联的结果数据
    results = relationship("ABTestResultModel", back_populates="test", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ABTest(id={self.id}, name={self.name}, status={self.status})>"


class ABTestResultModel(Base):
    """A/B 测试结果数据库模型"""
    __tablename__ = "ab_test_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    test_id = Column(String(64), ForeignKey("ab_tests.id"), nullable=False, index=True)

    # 测试结果数据
    current_sample_size = Column(Integer, default=0)
    remaining_sample_size = Column(Integer, default=0)
    metrics = Column(JSON, nullable=False)  # 存储各变体指标
    conclusion = Column(Text, nullable=True)
    recommendations = Column(JSON, nullable=True)  # 存储建议列表
    can_terminate = Column(Boolean, default=False)
    has_winner = Column(Boolean, default=False)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 关联的测试
    test = relationship("ABTestModel", back_populates="results")

    def __repr__(self):
        return f"<ABTestResult(test_id={self.test_id}, sample_size={self.current_sample_size})>"


class SEOAnalysisModel(Base):
    """SEO 分析结果数据库模型"""
    __tablename__ = "seo_analyses"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 分析请求数据
    content_hash = Column(String(64), index=True)  # 内容哈希，用于缓存
    target_keywords = Column(JSON, nullable=False)
    url = Column(String(512), nullable=True)
    title = Column(String(255), nullable=True)
    meta_description = Column(Text, nullable=True)

    # 分析结果数据
    overall_score = Column(Float, nullable=False)
    keyword_density = Column(JSON, nullable=False)
    content_length = Column(Integer, nullable=False)
    readability_score = Column(Float, nullable=False)
    suggestions = Column(JSON, nullable=True)
    issues = Column(JSON, nullable=True)
    strengths = Column(JSON, nullable=True)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<SEOAnalysis(id={self.id}, score={self.overall_score})>"


class TrafficDataModel(Base):
    """流量数据数据库模型"""
    __tablename__ = "traffic_data"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 数据标识
    domain = Column(String(255), nullable=True, index=True)
    path = Column(String(512), nullable=True, index=True)
    date = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD 格式

    # 流量指标
    visitors = Column(Integer, default=0)
    page_views = Column(Integer, default=0)
    unique_visitors = Column(Integer, default=0)

    # 性能指标
    avg_session_duration = Column(Float, default=0.0)
    bounce_rate = Column(Float, default=0.0)
    exit_rate = Column(Float, default=0.0)
    avg_time_on_page = Column(Float, default=0.0)

    # 转化指标
    conversion_rate = Column(Float, default=0.0)
    ctr = Column(Float, default=0.0)

    # SEO 指标
    seo_score = Column(Float, default=0.0)
    avg_position = Column(Float, default=0.0)

    # 原始数据（可选，用于存储完整的日志记录）
    raw_data = Column(JSON, nullable=True)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<TrafficData(date={self.date}, path={self.path}, visitors={self.visitors})>"


class ContentGenerationModel(Base):
    """内容生成记录数据库模型"""
    __tablename__ = "content_generations"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 生成请求数据
    topic = Column(String(512), nullable=False)
    target_keywords = Column(JSON, nullable=False)
    content_type = Column(String(64), nullable=False)
    tone = Column(String(64), nullable=False)
    target_audience = Column(String(255), nullable=True)

    # 生成结果数据
    generated_content = Column(Text, nullable=False)
    generated_title = Column(String(512), nullable=False)
    meta_description = Column(Text, nullable=True)
    outline = Column(JSON, nullable=True)
    seo_score = Column(Float, nullable=False)
    keyword_density = Column(JSON, nullable=False)
    suggestions = Column(JSON, nullable=True)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<ContentGeneration(id={self.id}, topic={self.topic})>"


class KeywordCacheModel(Base):
    """关键词缓存数据库模型"""
    __tablename__ = "keyword_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 缓存键
    seed_keywords_hash = Column(String(64), unique=True, index=True, nullable=False)
    source = Column(String(64), default="mock")  # 数据源标识

    # 缓存数据
    keywords = Column(JSON, nullable=False)

    # 过期时间
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<KeywordCache(seed_hash={self.seed_keywords_hash})>"
