"""
用户向量画像模型

存储用户的向量表示，用于基于向量相似度的匹配。
每个用户有多维向量：
- attribute_vector: 属性向量（年龄、性别、位置、兴趣等）
- behavior_vector: 行为向量（滑动、浏览、互动模式）
- conversation_vector: 对话向量（聊天内容、话题偏好）
- fused_vector: 融合向量（加权合并后的最终向量）
"""
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.sql import func
from db.database import Base
import numpy as np


class UserVectorPortraitDB(Base):
    """
    用户向量画像表

    存储用户的各类向量表示，用于精准匹配
    """
    __tablename__ = "user_vector_portraits"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # ==================== 属性向量 ====================
    # 从用户资料提取：年龄、性别、位置、兴趣、价值观等
    # 维度：128 维
    attribute_vector = Column(Text, nullable=True)  # JSON 字符串，存储 np.array

    # ==================== 行为向量 ====================
    # 从用户行为提取：滑动模式、浏览偏好、互动频率等
    # 维度：64 维
    behavior_vector = Column(Text, nullable=True)  # JSON 字符串

    # ==================== 对话向量 ====================
    # 从聊天内容提取：话题偏好、情感表达、沟通风格等
    # 维度：64 维
    conversation_vector = Column(Text, nullable=True)  # JSON 字符串

    # ==================== 融合向量 ====================
    # 加权合并属性、行为、对话向量
    # 维度：128 维
    fused_vector = Column(Text, nullable=True)  # JSON 字符串

    # ==================== 向量权重 ====================
    # 各维度向量的权重配置
    vector_weights = Column(JSON, default={
        "attribute": 0.20,    # 属性权重 20%
        "behavior": 0.35,     # 行为权重 35% - "身体很诚实"
        "conversation": 0.25, # 对话权重 25%
        "implicit": 0.20      # 隐性特征权重 20%
    })

    # ==================== 元数据 ====================
    # 向量版本（用于追踪向量更新）
    vector_version = Column(String(20), default="v1")

    # 各向量最后更新时间
    attribute_vector_updated_at = Column(DateTime(timezone=True), nullable=True)
    behavior_vector_updated_at = Column(DateTime(timezone=True), nullable=True)
    conversation_vector_updated_at = Column(DateTime(timezone=True), nullable=True)
    fused_vector_updated_at = Column(DateTime(timezone=True), nullable=True)

    # 数据源统计（用于计算置信度）
    behavior_events_count = Column(Integer, default=0)  # 行为事件数量
    conversation_messages_count = Column(Integer, default=0)  # 对话消息数量

    # 向量质量评分（0-1，基于数据量和多样性）
    vector_quality_score = Column(Float, default=0.0)

    # ==================== 时间戳 ====================
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def get_attribute_vector(self) -> np.ndarray:
        """获取属性向量"""
        if self.attribute_vector:
            import json
            return np.array(json.loads(self.attribute_vector))
        return None

    def get_behavior_vector(self) -> np.ndarray:
        """获取行为向量"""
        if self.behavior_vector:
            import json
            return np.array(json.loads(self.behavior_vector))
        return None

    def get_conversation_vector(self) -> np.ndarray:
        """获取对话向量"""
        if self.conversation_vector:
            import json
            return np.array(json.loads(self.conversation_vector))
        return None

    def get_fused_vector(self) -> np.ndarray:
        """获取融合向量"""
        if self.fused_vector:
            import json
            return np.array(json.loads(self.fused_vector))
        return None

    def set_vector(self, vector_type: str, vector: np.ndarray):
        """设置向量"""
        import json
        from datetime import datetime

        vector_json = json.dumps(vector.tolist())

        if vector_type == "attribute":
            self.attribute_vector = vector_json
            self.attribute_vector_updated_at = datetime.now()
        elif vector_type == "behavior":
            self.behavior_vector = vector_json
            self.behavior_vector_updated_at = datetime.now()
        elif vector_type == "conversation":
            self.conversation_vector = vector_json
            self.conversation_vector_updated_at = datetime.now()
        elif vector_type == "fused":
            self.fused_vector = vector_json
            self.fused_vector_updated_at = datetime.now()


class VectorSimilarityCacheDB(Base):
    """
    向量相似度缓存表

    预计算并缓存用户之间的相似度，提升查询性能
    """
    __tablename__ = "vector_similarity_cache"

    id = Column(String(36), primary_key=True, index=True)

    # 用户对（有序存储，user_id_1 < user_id_2 避免重复）
    user_id_1 = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    user_id_2 = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 相似度分数
    overall_similarity = Column(Float, nullable=False)  # 总体相似度 0-1

    # 分维度相似度
    attribute_similarity = Column(Float, nullable=True)
    behavior_similarity = Column(Float, nullable=True)
    conversation_similarity = Column(Float, nullable=True)

    # 计算元数据
    computation_version = Column(String(20), default="v1")

    # 时间戳
    computed_at = Column(DateTime(timezone=True), server_default=func.now())

    # 唯一约束
    __table_args__ = (
        # 确保用户对不重复
        # 可以添加：UniqueConstraint('user_id_1', 'user_id_2', name='unique_user_pair')
        {"sqlite_autoincrement": True}
    )