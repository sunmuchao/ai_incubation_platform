"""
P9 阶段实体模型：AI 内容标注与身份标识系统
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid


class AuthorType(str, Enum):
    """作者类型"""
    HUMAN = "human"           # 纯人类创作
    AI = "ai"                 # 纯 AI 生成
    HYBRID = "hybrid"         # 人机协作（人类创作+AI 辅助）


class AIAssistLevel(str, Enum):
    """AI 辅助程度"""
    NONE = "none"             # 无 AI 辅助 (0%)
    MINIMAL = "minimal"       # 轻微辅助 (1-25%)
    MODERATE = "moderate"     # 中度辅助 (26-50%)
    SUBSTANTIAL = "substantial"  # 大量辅助 (51-75%)
    HIGH = "high"             # 高度辅助 (76-99%)
    FULL = "full"             # 完全 AI 生成 (100%)


class AIAssistType(str, Enum):
    """AI 辅助类型"""
    NONE = "none"             # 无辅助
    POLISH = "polish"         # 润色
    EXPAND = "expand"         # 扩写
    TRANSLATE = "translate"   # 翻译
    SUMMARIZE = "summarize"   # 摘要
    GENERATE = "generate"     # 生成
    SUGGEST = "suggest"       # 建议采纳
    MULTIPLE = "multiple"     # 多种辅助


class ContentLabel(BaseModel):
    """内容标签"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content_id: str  # 内容 ID（帖子或评论 ID）
    content_type: str  # 内容类型（post/comment）
    author_type: AuthorType  # 作者类型
    ai_assist_level: AIAssistLevel = AIAssistLevel.NONE  # AI 辅助程度
    ai_assist_types: List[AIAssistType] = Field(default_factory=list)  # AI 辅助类型列表
    ai_participation_rate: float = 0.0  # AI 参与度百分比 (0-100)

    # AI 模型信息（如果有 AI 参与）
    ai_models: Optional[List[Dict[str, str]]] = None  # [{"provider": "xxx", "model": "xxx"}]

    # 辅助记录引用
    assist_record_ids: List[str] = Field(default_factory=list)  # 关联的 AI 辅助记录 ID

    # 透明度信息
    is_verified: bool = False  # 是否已验证
    verified_at: Optional[datetime] = None
    verified_by: Optional[str] = None  # 验证者 ID

    # 元数据
    badge_text: Optional[str] = None  # 显示徽章文本
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class AIAssistRecord(BaseModel):
    """AI 辅助创作记录"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    record_id: str = Field(default_factory=lambda: str(uuid.uuid4()))  # 唯一记录 ID

    # 内容引用
    content_id: str  # 内容 ID
    content_type: str  # 内容类型
    author_id: str  # 作者 ID

    # 辅助类型
    assist_type: AIAssistType

    # 辅助前后内容
    original_content: str  # 原始内容
    assisted_content: str  # 辅助后内容

    # AI 模型信息
    model_provider: str  # 模型提供方
    model_name: str  # 模型名称
    model_version: Optional[str] = None  # 模型版本

    # 辅助详情
    assist_details: Dict[str, Any] = Field(default_factory=dict)  # 辅助详情（JSON）
    changes_made: List[str] = Field(default_factory=list)  # 修改列表
    confidence_score: float = 0.8  # 置信度

    # 耗时
    duration_ms: Optional[float] = None  # 耗时（毫秒）

    # 时间
    created_at: datetime = Field(default_factory=datetime.now)


class AIAssistCreate(BaseModel):
    """创建 AI 辅助记录请求"""
    content_id: str
    content_type: str
    author_id: str
    assist_type: AIAssistType
    original_content: str
    assisted_content: str
    model_provider: str
    model_name: str
    model_version: Optional[str] = None
    assist_details: Optional[Dict[str, Any]] = None
    changes_made: Optional[List[str]] = None
    confidence_score: float = 0.8
    duration_ms: Optional[float] = None


class ContentLabelCreate(BaseModel):
    """创建内容标签请求"""
    content_id: str
    content_type: str
    author_type: AuthorType
    ai_assist_level: AIAssistLevel = AIAssistLevel.NONE
    ai_assist_types: Optional[List[AIAssistType]] = None
    ai_participation_rate: float = 0.0
    ai_models: Optional[List[Dict[str, str]]] = None
    assist_record_ids: Optional[List[str]] = None


class ContentLabelUpdate(BaseModel):
    """更新内容标签请求"""
    author_type: Optional[AuthorType] = None
    ai_assist_level: Optional[AIAssistLevel] = None
    ai_assist_types: Optional[List[AIAssistType]] = None
    ai_participation_rate: Optional[float] = None
    is_verified: Optional[bool] = None


class AIModelInfo(BaseModel):
    """AI 模型信息"""
    provider: str  # 模型提供方
    model: str  # 模型名称
    version: Optional[str] = None  # 版本


class ContentTransparencyReport(BaseModel):
    """内容透明度报告"""
    content_id: str
    content_type: str
    author_type: AuthorType
    ai_participation_rate: float
    ai_assist_level: AIAssistLevel
    ai_assist_types: List[AIAssistType]
    ai_models_used: List[AIModelInfo]
    assist_history: List[AIAssistRecord]
    transparency_score: float  # 透明度评分 (0-1)
    verification_status: bool
    badge_display: str  # 前端显示的徽章


class AIAssistStats(BaseModel):
    """AI 辅助统计"""
    total_assisted_content: int  # 总辅助内容数
    by_level: Dict[str, int]  # 按辅助程度统计
    by_type: Dict[str, int]  # 按辅助类型统计
    avg_ai_participation: float  # 平均 AI 参与度
    top_ai_models: List[Dict[str, Any]]  # 常用 AI 模型排行
    transparency_rate: float  # 透明标注率


class AuthorTypeStats(BaseModel):
    """作者类型统计"""
    total_content: int
    human_created: int
    ai_generated: int
    hybrid_created: int
    human_percentage: float
    ai_percentage: float
    hybrid_percentage: float
