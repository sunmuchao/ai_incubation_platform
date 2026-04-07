"""
质量预测模型数据模型。

用于预测任务交付质量，支持：
1. 质量风险评分
2. 质量特征分析
3. 预测依据解释
4. 历史质量趋势
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class QualityLevel(str, Enum):
    """质量等级。"""
    EXCELLENT = "excellent"  # 优秀
    GOOD = "good"  # 良好
    AVERAGE = "average"  # 一般
    POOR = "poor"  # 较差
    HIGH_RISK = "high_risk"  # 高风险


class PredictionStatus(str, Enum):
    """预测状态。"""
    PENDING = "pending"  # 待预测
    PREDICTED = "predicted"  # 已预测
    VERIFIED = "verified"  # 已验证（实际结果与预测一致）
    INCORRECT = "incorrect"  # 预测错误


class QualityFeature(BaseModel):
    """质量特征。"""

    name: str
    value: float
    weight: float = 1.0  # 特征权重
    description: str = ""
    risk_contribution: float = 0.0  # 对风险的贡献度


class QualityPrediction(BaseModel):
    """质量预测结果。"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str
    worker_id: str

    # 预测结果
    predicted_quality_level: QualityLevel = QualityLevel.AVERAGE
    quality_score: float = 0.5  # 质量得分 (0-1)
    risk_score: float = 0.5  # 风险得分 (0-1，越高风险越大)

    # 预测置信度
    confidence: float = 0.0
    prediction_reason: str = ""  # 预测依据

    # 特征分析
    features: List[QualityFeature] = Field(default_factory=list)
    positive_factors: List[str] = Field(default_factory=list)  # 积极因素
    risk_factors: List[str] = Field(default_factory=list)  # 风险因素

    # 建议措施
    recommendations: List[str] = Field(default_factory=list)

    # 状态追踪
    status: PredictionStatus = PredictionStatus.PENDING
    actual_quality_level: Optional[QualityLevel] = None
    actual_quality_score: Optional[float] = None

    # 元数据
    model_version: str = "v1.0"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    verified_at: Optional[datetime] = None


class QualityPredictionRequest(BaseModel):
    """质量预测请求。"""

    task_id: str
    worker_id: str
    task_description: str = ""
    task_complexity: str = "medium"  # low, medium, high
    reward_amount: float = 0.0
    deadline_hours: Optional[int] = None


class QualityPredictionResponse(BaseModel):
    """质量预测响应。"""

    success: bool
    prediction_id: Optional[str] = None
    predicted_quality: QualityLevel = QualityLevel.AVERAGE
    quality_score: float = 0.0
    risk_score: float = 0.0
    confidence: float = 0.0
    message: str = ""
    risk_level: str = ""  # low, medium, high
    recommendations: List[str] = Field(default_factory=list)


class QualityModelConfig(BaseModel):
    """质量模型配置。"""

    # 特征权重
    worker_history_weight: float = 0.3  # 工人历史表现权重
    task_complexity_weight: float = 0.2  # 任务复杂度权重
    reward_adequacy_weight: float = 0.15  # 报酬合理性权重
    deadline_pressure_weight: float = 0.15  # 期限压力权重
    description_quality_weight: float = 0.2  # 描述质量权重

    # 阈值配置
    high_quality_threshold: float = 0.8  # 高质量阈值
    acceptable_quality_threshold: float = 0.6  # 可接受质量阈值
    high_risk_threshold: float = 0.7  # 高风险阈值

    # 模型参数
    enable_auto_learning: bool = True  # 启用自动学习
    min_training_samples: int = 100  # 最小训练样本数
