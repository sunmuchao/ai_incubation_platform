"""
智能验收助手数据模型。

用于 AI 自动检查交付内容是否符合验收标准，支持：
1. NLP 语义相似度匹配
2. 多模态交付检查
3. 验收报告生成
4. 置信度评分
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CheckItemType(str, Enum):
    """验收检查项类型。"""
    TEXT_MATCH = "text_match"  # 文本匹配
    KEYWORD_CHECK = "keyword_check"  # 关键词检查
    FORMAT_CHECK = "format_check"  # 格式检查
    IMAGE_CHECK = "image_check"  # 图片检查
    FILE_CHECK = "file_check"  # 文件检查
    CUSTOM = "custom"  # 自定义检查


class CheckResult(str, Enum):
    """检查结果。"""
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    SKIPPED = "skipped"


class AcceptanceCheckItem(BaseModel):
    """单个验收检查项。"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    criterion: str  # 验收标准原文
    check_type: CheckItemType = CheckItemType.TEXT_MATCH

    # 检查配置
    config: Dict[str, Any] = Field(default_factory=dict)
    """
    配置项示例:
    - text_match: {"threshold": 0.8, "method": "semantic"}
    - keyword_check: {"keywords": ["key1", "key2"], "match_all": true}
    - format_check: {"format": "json", "schema": {...}}
    - image_check: {"min_pixels": 1920*1080, "required_objects": ["person", "building"]}
    """

    # 检查结果
    result: CheckResult = CheckResult.SKIPPED
    score: float = 0.0  # 得分 (0-1)
    details: str = ""  # 详细说明
    evidence: Optional[str] = None  # 证据（如匹配到的文本片段）

    created_at: datetime = Field(default_factory=datetime.now)


class AcceptanceReport(BaseModel):
    """验收报告。"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str
    worker_id: str
    submission_id: str  # 提交记录 ID

    # 验收结果
    overall_result: CheckResult = CheckResult.SKIPPED
    overall_score: float = 0.0  # 总体得分 (0-1)
    confidence: float = 0.0  # AI 置信度

    # 检查项
    check_items: List[AcceptanceCheckItem] = Field(default_factory=list)
    passed_count: int = 0
    failed_count: int = 0
    warning_count: int = 0

    # AI 分析
    ai_analysis: str = ""  # AI 分析报告
    ai_recommendation: str = ""  # AI 建议（通过/拒绝/需要人工复核）
    ai_model_used: str = "rule_based_v1"

    # 交付内容分析
    content_analysis: Dict[str, Any] = Field(default_factory=dict)
    """
    内容分析结果:
    - word_count: 字数
    - sentence_count: 句子数
    - key_phrases: 关键短语
    - sentiment: 情感分析
    - topics: 主题分类
    """

    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    reviewed_by: Optional[str] = None  # 人工复核人（如有）
    reviewed_at: Optional[datetime] = None


class AcceptanceRequest(BaseModel):
    """验收请求。"""

    task_id: str
    worker_id: str
    delivery_content: str
    delivery_attachments: List[str] = Field(default_factory=list)
    acceptance_criteria: List[str] = Field(default_factory=list)
    custom_checks: List[Dict[str, Any]] = Field(default_factory=list)  # 自定义检查配置


class AcceptanceResponse(BaseModel):
    """验收响应。"""

    success: bool
    report_id: Optional[str] = None
    overall_result: CheckResult = CheckResult.SKIPPED
    overall_score: float = 0.0
    confidence: float = 0.0
    recommendation: str = ""  # approve, reject, manual_review
    message: str = ""
    check_summary: Dict[str, int] = Field(default_factory=dict)  # {pass: x, fail: y, warning: z}


class AcceptanceConfig(BaseModel):
    """验收配置。"""

    # 阈值配置
    semantic_similarity_threshold: float = 0.75  # 语义相似度阈值
    keyword_match_ratio: float = 0.8  # 关键词匹配比例
    min_word_count: int = 0  # 最小字数要求

    # 功能开关
    enable_semantic_check: bool = True
    enable_keyword_check: bool = True
    enable_format_check: bool = True
    enable_content_quality_check: bool = True

    # 严格模式
    strict_mode: bool = False  # 严格模式下，任何检查项失败都会导致整体验收失败

    # 自动通过配置
    auto_approve_threshold: float = 0.9  # 自动通过阈值（得分>=此值自动通过）
    auto_reject_threshold: float = 0.5  # 自动拒绝阈值（得分<此值自动拒绝）
