"""
SQLAlchemy 数据模型 - 候选人反馈领域

用于记录用户对候选人的反馈，建立反馈闭环，优化后续推荐。

版本：v1.0
"""
from db.models.base import *
import uuid


class CandidateFeedbackDB(Base):
    """
    候选人反馈记录

    记录用户对推荐候选人的反馈（喜欢/不喜欢/中性），用于：
    1. 建立反馈闭环，避免重复推荐不合适的人
    2. 分析偏好模式，优化后续推荐
    3. 构建用户画像偏好维度
    """
    __tablename__ = "candidate_feedbacks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # ===== 核心字段 =====
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    candidate_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 反馈类型：like / dislike / neutral / skip
    feedback_type = Column(String(20), nullable=False, index=True)

    # 不喜欢原因（预设选项）
    dislike_reason = Column(String(50), nullable=True, index=True)
    # 可选值：
    # - "年龄差距太大"
    # - "距离太远"
    # - "兴趣不匹配"
    # - "没有眼缘"
    # - "关系目标不一致"
    # - "其他"

    # 用户自定义原因（自由文本）
    dislike_detail = Column(Text, nullable=True)

    # ===== 上下文信息 =====
    # 本次推荐的查询 ID（关联到 her_find_candidates 的 query_request_id）
    query_request_id = Column(String(36), nullable=True, index=True)

    # 推荐时的匹配分数（用于分析"高分但不喜欢"的情况）
    recommendation_score = Column(Integer, default=0)

    # 推荐时的用户偏好快照（JSON）
    user_preferences_snapshot = Column(JSON, nullable=True)

    # ===== 时间戳 =====
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # ===== 索引设计 =====
    __table_args__ = (
        # 用户+候选人唯一索引：同一用户对同一候选人只能反馈一次
        Index('ix_user_candidate_feedback_unique', 'user_id', 'candidate_id', unique=True),
        # 用户+反馈类型索引：快速查询用户的喜欢/不喜欢列表
        Index('ix_user_feedback_type', 'user_id', 'feedback_type'),
        # 用户+不喜欢原因索引：分析用户偏好模式
        Index('ix_user_dislike_reason', 'user_id', 'dislike_reason'),
    )


class FeedbackStatisticsDB(Base):
    """
    反馈统计汇总（定期聚合，用于快速查询）

    每日聚合用户的反馈统计，避免每次推荐时实时计算。
    """
    __tablename__ = "feedback_statistics"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # ===== 统计字段 =====
    total_feedbacks = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    dislike_count = Column(Integer, default=0)
    neutral_count = Column(Integer, default=0)
    skip_count = Column(Integer, default=0)

    # ===== 不喜欢原因分布（JSON）=====
    # {"年龄差距太大": 5, "距离太远": 3, ...}
    dislike_reason_distribution = Column(JSON, nullable=True)

    # ===== 学习到的偏好维度 =====
    # 基于反馈分析得出的偏好推断
    learned_preferences = Column(JSON, nullable=True)
    # 例如：{"preferred_age_range": [25, 35], "avoid_locations": ["广州"]}

    # ===== 时间戳 =====
    last_feedback_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


__all__ = ["CandidateFeedbackDB", "FeedbackStatisticsDB"]