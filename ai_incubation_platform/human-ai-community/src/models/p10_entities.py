"""
P10 实体模型：自动 AI 检测集成
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid


class AIDetectionMethod(str, Enum):
    """AI 检测方法"""
    STATISTICAL = "statistical"           # 统计特征分析
    MODEL_BASED = "model_based"           # 基于检测模型
    WATERMARK = "watermark"               # 水印检测
    METADATA = "metadata"                 # 元数据分析
    ENSEMBLE = "ensemble"                 # 集成检测
    PATTERN = "pattern"                   # 模式分析
    SEMANTIC = "semantic"                 # 语义分析


class AIDetectionModel(str, Enum):
    """AI 检测模型"""
    OPENAI_CLASSIFIER = "openai_classifier"     # OpenAI AI 文本分类器
    GPTZERO = "gptzero"                         # GPTZero
    ORIGINALITY_AI = "originality_ai"           # Originality.ai
    COHERE_DETOX = "cohere_detox"               # Cohere Detoxify
    CUSTOM_TRANSFORMER = "custom_transformer"   # 自研 Transformer 检测模型
    RULE_BASED = "rule_based"                   # 规则基检测


class DetectionConfidence(str, Enum):
    """检测置信度"""
    VERY_LOW = "very_low"       # 0-20%
    LOW = "low"                 # 21-40%
    MEDIUM = "medium"           # 41-60%
    HIGH = "high"               # 61-80%
    VERY_HIGH = "very_high"     # 81-100%


class AIDetectionResult(BaseModel):
    """AI 检测结果"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content_id: str  # 内容 ID
    content_type: str  # 内容类型（post/comment）
    is_ai_generated: bool  # 是否 AI 生成
    ai_probability: float  # AI 概率 (0-1)
    confidence: DetectionConfidence  # 置信度
    detection_methods: List[AIDetectionMethod] = Field(default_factory=list)  # 使用的检测方法
    detection_models: List[AIDetectionModel] = Field(default_factory=list)  # 使用的检测模型

    # 详细分析结果
    analysis_details: Dict[str, Any] = Field(default_factory=dict)
    # 各维度评分
    perplexity_score: Optional[float] = None  # 困惑度分数
    burstiness_score: Optional[float] = None  # 爆发度分数
    pattern_score: Optional[float] = None  # 模式分数
    semantic_score: Optional[float] = None  # 语义分数

    # 标注状态
    has_label: bool = False  # 是否已有 AI 标注
    label_matches: bool = True  # 检测结果与标注是否一致

    # 时间
    detected_at: datetime = Field(default_factory=datetime.now)
    detector_id: Optional[str] = None  # 检测器 ID


class AIDisputeType(str, Enum):
    """争议类型"""
    FALSE_POSITIVE = "false_positive"     # 误报（人类内容被检为 AI）
    FALSE_NEGATIVE = "false_negative"     # 漏报（AI 内容未被检出）
    LABEL_DISPUTE = "label_dispute"       # 标注争议（用户不认可标注）
    APPEAL = "appeal"                     # 申诉


class AIDisputeRecord(BaseModel):
    """AI 检测争议记录"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    dispute_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # 关联
    content_id: str  # 内容 ID
    content_type: str  # 内容类型
    detection_id: str  # 检测记录 ID
    submitter_id: str  # 提交者 ID

    # 争议信息
    dispute_type: AIDisputeType  # 争议类型
    description: str  # 争议描述
    evidence: List[str] = Field(default_factory=list)  # 证据列表

    # 处理状态
    status: str = "pending"  # pending, reviewing, resolved
    resolution: Optional[str] = None  # 处理结果
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None  # 处理者 ID

    # 复核结果
    review_result: Optional[Dict[str, Any]] = None  # 复核结果
    final_determination: Optional[str] = None  # 最终裁定

    # 时间
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None


class AIDetectionStats(BaseModel):
    """AI 检测统计"""
    total_scanned: int = 0  # 总扫描内容数
    ai_detected: int = 0  # 检出 AI 内容数
    human_verified: int = 0  # 确认人类内容数
    uncertain: int = 0  # 不确定数

    # 按置信度统计
    by_confidence: Dict[str, int] = Field(default_factory=dict)

    # 按检测方法统计
    by_method: Dict[str, int] = Field(default_factory=dict)

    # 争议统计
    total_disputes: int = 0
    resolved_disputes: int = 0
    overturned_detections: int = 0  # 被推翻的检测

    # 性能统计
    avg_detection_time_ms: float = 0.0
    false_positive_rate: float = 0.0
    false_negative_rate: float = 0.0

    # 扫描覆盖率
    scan_coverage_rate: float = 0.0  # 已扫描/总内容


class AIDisputeResolution(BaseModel):
    """争议处理结果"""
    dispute_id: str
    status: str  # upheld, overturned, inconclusive
    reason: str  # 处理原因
    action_taken: str  # 采取的行动
    detection_updated: bool = False  # 检测结果是否更新
    label_updated: bool = False  # 标签是否更新
    user_notified: bool = True  # 是否通知用户


class DetectionThresholds(BaseModel):
    """检测阈值配置"""
    ai_definitive: float = 0.85  # 确认 AI 阈值
    ai_likely: float = 0.60      # 可能 AI 阈值
    human_definitive: float = 0.20  # 确认人类阈值
    human_likely: float = 0.40      # 可能人类阈值


class ScanConfig(BaseModel):
    """扫描配置"""
    batch_size: int = 100  # 批次大小
    scan_interval_hours: int = 24  # 扫描间隔（小时）
    auto_label: bool = True  # 是否自动标注
    notify_user: bool = True  # 是否通知用户
    priority_scan_new: bool = True  # 优先扫描新内容
