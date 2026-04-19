"""
Behavior 行为实验室 - 类型定义

@deprecated
此文件已废弃，原因：
1. 完全无任何引用（包括 __init__.py）
2. 概念设计文件，功能从未落地实现
3. 相关功能已迁移到 DeerFlow Skills

替代方案：
- 共同经历检测：context_detector_skill + DeerFlow her_tools
- 尷尬沉默识别：silence_breaker_skill
- 情境话题生成：DeerFlow her_tools 话题推荐

归档日期：2026-04-15
预计删除：立即删除（零风险）

---

为行为实验室模块提供精确的类型定义，替代 Dict[str, Any]
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from typing_extensions import TypedDict


# ==================== 共同经历检测服务类型 ====================

class ExperienceReferenceData(TypedDict, total=False):
    """共同经历参考数据"""
    start_time: datetime
    end_time: Optional[datetime]
    location: Optional[str]
    description: str
    conversation_id: Optional[str]
    activity_type: Optional[str]


class ExperienceSignificanceConfig(TypedDict):
    """经历显著性配置"""
    duration_minutes: int
    message_count: int
    emotional_intensity: float


# ==================== 尴尬沉默识别服务类型 ====================

class SilenceEventConfig(TypedDict):
    """沉默事件配置"""
    silence_threshold_seconds: int
    check_interval_seconds: int
    auto_generate_topics: bool


class SilenceContext(TypedDict, total=False):
    """沉默上下文数据"""
    last_message_time: datetime
    last_message_sender: Optional[str]
    message_gap_seconds: int
    conversation_stage: str
    recent_topics: List[str]


class GeneratedTopic(TypedDict):
    """生成的话题"""
    topic_id: str
    content: str
    relevance_score: float
    source: str


# ==================== 情境话题生成服务类型 ====================

class ConversationContext(TypedDict, total=False):
    """对话上下文"""
    conversation_id: str
    stage: str  # initial, ongoing, deep, stagnant
    last_message_time: datetime
    message_count: int
    recent_topics: List[str]
    user_a_interests: List[str]
    user_b_interests: List[str]
    shared_experiences: List[str]


class UserInterestProfile(TypedDict, total=False):
    """用户兴趣档案"""
    user_id: str
    interests: List[str]
    hobbies: List[str]
    favorite_topics: List[str]
    recent_activity_topics: List[str]


class TopicRecommendation(TypedDict):
    """话题推荐"""
    topic: str
    reason: str
    confidence: float
    source: str  # shared_interest, recent_activity, trending


# ==================== 通用类型 ====================

class ServiceResult(TypedDict, total=False):
    """服务操作结果"""
    success: bool
    message: str
    data: Optional[Any]
    error: Optional[str]


class TimestampedData(TypedDict):
    """带时间戳的数据"""
    created_at: datetime
    updated_at: Optional[datetime]
