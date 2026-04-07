# ==================== P10 新增模型：自动 AI 检测集成 ====================

from sqlalchemy import Column, String, Text, Integer, Float, Boolean, ForeignKey, JSON, Enum as SQLAlchemyEnum, DateTime, func
from sqlalchemy.orm import relationship
from enum import Enum
from .base import BaseModel
import sys
import os
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class DBAIDetection(BaseModel):
    """AI 检测结果表"""
    __tablename__ = "ai_detections"

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()), comment="检测记录 ID")
    content_id = Column(String(36), nullable=False, index=True, comment="内容 ID")
    content_type = Column(String(50), nullable=False, comment="内容类型：post/comment")

    # 检测结果
    is_ai_generated = Column(Boolean, nullable=False, default=False, comment="是否 AI 生成")
    ai_probability = Column(Float, nullable=False, default=0.0, comment="AI 概率 (0-1)")
    confidence = Column(String(50), nullable=False, default="medium", comment="置信度：very_low/low/medium/high/very_high")

    # 检测方法
    detection_methods = Column(JSON, default=list, comment="使用的检测方法列表")
    detection_models = Column(JSON, default=list, comment="使用的检测模型列表")

    # 详细分析结果
    analysis_details = Column(JSON, default=dict, comment="详细分析结果")
    perplexity_score = Column(Float, comment="困惑度分数")
    burstiness_score = Column(Float, comment="爆发度分数")
    pattern_score = Column(Float, comment="模式分数")
    semantic_score = Column(Float, comment="语义分数")

    # 标注状态
    has_label = Column(Boolean, nullable=False, default=False, comment="是否已有 AI 标注")
    label_matches = Column(Boolean, nullable=False, default=True, comment="检测结果与标注是否一致")

    # 检测器信息
    detector_id = Column(String(100), comment="检测器 ID")

    # 时间
    detected_at = Column(DateTime(timezone=True), server_default=func.now(), comment="检测时间")


class DBAIDispute(BaseModel):
    """AI 检测争议表"""
    __tablename__ = "ai_disputes"

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()), comment="争议记录 ID")
    dispute_id = Column(String(36), nullable=False, unique=True, index=True, default=lambda: str(uuid.uuid4()), comment="唯一争议 ID")

    # 关联
    content_id = Column(String(36), nullable=False, index=True, comment="内容 ID")
    content_type = Column(String(50), nullable=False, comment="内容类型")
    detection_id = Column(String(36), ForeignKey("ai_detections.id"), nullable=False, comment="检测记录 ID")
    submitter_id = Column(String(36), ForeignKey("community_members.id"), nullable=False, comment="提交者 ID")

    # 争议信息
    dispute_type = Column(String(50), nullable=False, comment="争议类型")
    description = Column(Text, nullable=False, comment="争议描述")
    evidence = Column(JSON, default=list, comment="证据列表")

    # 处理状态
    status = Column(String(50), nullable=False, default="pending", comment="处理状态")
    resolution = Column(Text, comment="处理结果")
    resolved_at = Column(DateTime(timezone=True), comment="处理时间")
    resolved_by = Column(String(36), ForeignKey("community_members.id"), comment="处理者 ID")

    # 复核结果
    review_result = Column(JSON, comment="复核结果")
    final_determination = Column(String(50), comment="最终裁定")

    # 时间
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")


class DBAIDetectionConfig(BaseModel):
    """AI 检测配置表"""
    __tablename__ = "ai_detection_configs"

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()), comment="配置 ID")
    config_key = Column(String(100), nullable=False, unique=True, comment="配置键")
    config_value = Column(JSON, nullable=False, comment="配置值")
    description = Column(Text, comment="配置描述")
    enabled = Column(Boolean, nullable=False, default=True, comment="是否启用")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")
