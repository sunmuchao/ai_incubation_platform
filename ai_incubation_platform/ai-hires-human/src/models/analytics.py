"""
P10 高级分析与预测 - 数据模型层。

定义预测分析相关的数据模型和实体类。
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ==================== 预测分析基础模型 ====================

class PredictionResult(BaseModel):
    """预测结果基础类。"""
    prediction_type: str
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度")
    predicted_value: Any
    prediction_date: datetime = Field(default_factory=datetime.now)
    model_version: str = "v1.0"
    feature_importance: Optional[Dict[str, float]] = None


# ==================== 任务成功概率预测 ====================

class TaskSuccessPrediction(PredictionResult):
    """任务成功概率预测。"""
    prediction_type: str = "task_success"

    task_id: int
    success_probability: float = Field(..., ge=0.0, le=1.0)
    risk_level: str = Field(..., description="风险等级：low/medium/high/critical")

    # 风险因素
    risk_factors: List[Dict[str, Any]] = Field(default_factory=list)
    # 建议措施
    recommendations: List[str] = Field(default_factory=list)

    # 预测特征
    features: Dict[str, Any] = Field(default_factory=dict)


class TaskSuccessBatchPrediction(BaseModel):
    """批量任务成功概率预测。"""
    predictions: List[TaskSuccessPrediction]
    summary: Dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=datetime.now)


# ==================== 工人流失预警 ====================

class WorkerChurnPrediction(PredictionResult):
    """工人流失预警预测。"""
    prediction_type: str = "worker_churn"

    worker_id: int
    churn_probability: float = Field(..., ge=0.0, le=1.0)
    risk_level: str = Field(..., description="风险等级：low/medium/high/critical")
    predicted_churn_date: Optional[datetime] = None

    # 流失原因分析
    churn_reasons: List[Dict[str, Any]] = Field(default_factory=list)
    # 保留建议
    retention_suggestions: List[str] = Field(default_factory=list)

    # 工人状态特征
    features: Dict[str, Any] = Field(default_factory=dict)


class WorkerChurnBatchPrediction(BaseModel):
    """批量工人流失预警。"""
    predictions: List[WorkerChurnPrediction]
    high_risk_count: int = 0
    medium_risk_count: int = 0
    low_risk_count: int = 0
    summary: Dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=datetime.now)


# ==================== 收入预测 ====================

class RevenueForecast(BaseModel):
    """收入预测数据点。"""
    date: str
    predicted_revenue: float
    lower_bound: float  # 置信区间下界
    upper_bound: float  # 置信区间上界
    predicted_gmv: float
    predicted_tasks: int
    predicted_active_workers: int


class RevenuePrediction(PredictionResult):
    """收入预测。"""
    prediction_type: str = "revenue"

    forecast_period: str = Field(..., description="预测周期：7d/14d/30d/90d")
    forecast: List[RevenueForecast] = Field(default_factory=list)

    # 汇总数据
    total_predicted_revenue: float = 0.0
    growth_rate: float = 0.0  # 环比增长率

    # 影响因素
    key_drivers: List[Dict[str, Any]] = Field(default_factory=list)
    # 风险提示
    risk_warnings: List[str] = Field(default_factory=list)


# ==================== 异常检测 ====================

class AnomalyDetection(BaseModel):
    """异常检测结果。"""
    anomaly_type: str
    severity: str = Field(..., description="严重程度：low/medium/high/critical")
    detected_at: datetime = Field(default_factory=datetime.now)

    # 异常指标
    metric_name: str
    expected_value: float
    actual_value: float
    deviation_percent: float

    # 影响范围
    affected_entities: List[Dict[str, Any]] = Field(default_factory=list)

    # 可能原因
    possible_causes: List[str] = Field(default_factory=list)
    # 建议措施
    recommended_actions: List[str] = Field(default_factory=list)


class AnomalyDetectionReport(BaseModel):
    """异常检测报告。"""
    report_type: str = "anomaly_detection"
    detection_period: str
    anomalies: List[AnomalyDetection] = Field(default_factory=list)

    # 统计
    total_anomalies: int = 0
    critical_count: int = 0
    high_count: int = 0

    # 趋势分析
    trend: str = Field(..., description="异常趋势：improving/stable/worsening")
    generated_at: datetime = Field(default_factory=datetime.now)


# ==================== 高级分析报表 ====================

class AdvancedAnalyticsDashboard(BaseModel):
    """高级分析仪表板数据。"""
    # 预测概览
    task_success_rate: float
    worker_churn_rate: float
    revenue_growth_rate: float
    anomaly_count: int

    # 详细预测
    task_predictions: Optional[TaskSuccessBatchPrediction] = None
    worker_predictions: Optional[WorkerChurnBatchPrediction] = None
    revenue_prediction: Optional[RevenuePrediction] = None
    anomaly_report: Optional[AnomalyDetectionReport] = None

    generated_at: datetime = Field(default_factory=datetime.now)


# ==================== 分析查询参数 ====================

class AnalyticsQueryParams(BaseModel):
    """分析查询参数。"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    organization_id: Optional[str] = None
    task_type: Optional[str] = None
    worker_level: Optional[int] = None

    # 分页
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class PredictionQueryParams(AnalyticsQueryParams):
    """预测查询参数。"""
    # 预测配置
    forecast_period: str = Field(default="30d", description="预测周期")
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    risk_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
