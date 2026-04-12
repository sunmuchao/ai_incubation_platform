"""
用户匹配偏好数据库模型

提供细化的匹配条件设置
"""
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, JSON, Text, ForeignKey
from sqlalchemy.sql import func
from db.database import Base


class UserMatchingPreferenceDB(Base):
    """用户匹配偏好"""
    __tablename__ = "user_matching_preferences"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # 年龄偏好
    age_min = Column(Integer, default=18)
    age_max = Column(Integer, default=45)

    # 身高偏好
    height_min = Column(Integer, nullable=True)  # cm
    height_max = Column(Integer, nullable=True)  # cm

    # 教育偏好
    education = Column(JSON, nullable=True)  # ["本科", "硕士"]

    # 职业偏好
    occupation = Column(JSON, nullable=True)  # ["互联网", "金融"]

    # 生活习惯偏好
    lifestyle = Column(JSON, nullable=True)  # ["早睡早起", "运动达人"]

    # 兴趣偏好
    interests = Column(JSON, nullable=True)  # ["运动", "音乐", "旅行"]

    # 地理位置
    location_city = Column(String(100), nullable=True)
    max_distance = Column(Integer, default=50)  # 最大距离（km）

    # 交友目的
    relationship_goal = Column(String(50), nullable=True)  # "寻找伴侣", "结交朋友"

    # 关系期望
    relationship_expectation = Column(JSON, nullable=True)  # ["长期关系"]

    # 雷区（不接受）
    deal_breakers = Column(JSON, nullable=True)  # ["抽烟", "酗酒"]

    # 权重配置
    weight_config = Column(JSON, nullable=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<UserMatchingPreferenceDB(user_id={self.user_id})>"