"""
A/B测试模块 schema 定义
"""
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class ABTestStatus(str, Enum):
    """A/B测试状态枚举"""
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ABTestVariant(BaseModel):
    """测试变体"""
    id: str = Field(description="变体ID")
    name: str = Field(description="变体名称")
    description: Optional[str] = Field(default=None, description="变体描述")
    traffic_percentage: float = Field(description="流量分配百分比 0-1", ge=0, le=1)
    content: Dict[str, Any] = Field(description="变体内容配置")
    is_control: bool = Field(default=False, description="是否为对照组")


class ABTestGoal(BaseModel):
    """测试目标"""
    name: str = Field(description="目标名称")
    metric: str = Field(description="指标名称")
    target_value: float = Field(description="目标值")
    operator: str = Field(default="increase", description="操作方向 increase/decrease")


class ABTestCreateRequest(BaseModel):
    """创建A/B测试请求"""
    name: str = Field(description="测试名称", min_length=1)
    description: Optional[str] = Field(default=None, description="测试描述")
    page_url: str = Field(description="测试页面URL")
    variants: List[ABTestVariant] = Field(description="测试变体列表", min_length=2)
    goals: List[ABTestGoal] = Field(description="测试目标列表", min_length=1)
    start_time: Optional[datetime] = Field(default=None, description="开始时间")
    end_time: Optional[datetime] = Field(default=None, description="结束时间")
    confidence_level: float = Field(default=0.95, description="置信水平", ge=0.8, le=0.99)
    minimum_sample_size: int = Field(default=1000, description="最小样本量", ge=100)


class ABTestResponse(BaseModel):
    """A/B测试响应"""
    id: str = Field(description="测试ID")
    name: str = Field(description="测试名称")
    description: Optional[str] = Field(default=None, description="测试描述")
    page_url: str = Field(description="测试页面URL")
    status: ABTestStatus = Field(description="测试状态")
    variants: List[ABTestVariant] = Field(description="测试变体列表")
    goals: List[ABTestGoal] = Field(description="测试目标列表")
    start_time: Optional[datetime] = Field(default=None, description="开始时间")
    end_time: Optional[datetime] = Field(default=None, description="结束时间")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")
    created_by: str = Field(description="创建人")
    confidence_level: float = Field(description="置信水平")
    minimum_sample_size: int = Field(description="最小样本量")


class ABTestMetrics(BaseModel):
    """测试指标"""
    variant_id: str = Field(description="变体ID")
    variant_name: str = Field(description="变体名称")
    visitors: int = Field(description="访客数")
    conversions: int = Field(description="转化数")
    conversion_rate: float = Field(description="转化率 0-1")
    improvement: float = Field(description="相对于对照组的提升率")
    statistical_significance: float = Field(description="统计显著性 0-1")
    is_winner: bool = Field(default=False, description="是否为获胜变体")


class ABTestResultResponse(BaseModel):
    """A/B测试结果响应"""
    test_id: str = Field(description="测试ID")
    test_name: str = Field(description="测试名称")
    status: ABTestStatus = Field(description="测试状态")
    current_sample_size: int = Field(description="当前样本量")
    remaining_sample_size: int = Field(description="剩余需要样本量")
    confidence_level: float = Field(description="置信水平")
    metrics: List[ABTestMetrics] = Field(description="各变体指标")
    conclusion: Optional[str] = Field(default=None, description="测试结论")
    recommendations: List[str] = Field(description="建议列表")
    can_terminate: bool = Field(description="是否可以终止测试")
    has_winner: bool = Field(description="是否已产生显著获胜者")


class ABTestListResponse(BaseModel):
    """A/B测试列表响应"""
    tests: List[ABTestResponse] = Field(description="测试列表")
    total: int = Field(description="总数量")
    running: int = Field(description="运行中数量")
    completed: int = Field(description="已完成数量")
    draft: int = Field(description="草稿数量")
