"""
P15 阶段：内容推荐系统增强 - 数据库模型导入

用于在数据库初始化时创建推荐系统相关的表
"""
from .base import BaseModel
from models.p15_recommendation import (
    DBReadingHistory,
    DBContentTag,
    DBPostTag,
    DBUserInterest,
    DBRecommendationLog,
    DBRecommendationConfig,
)

# 导出所有推荐系统相关模型
__all__ = [
    "DBReadingHistory",
    "DBContentTag",
    "DBPostTag",
    "DBUserInterest",
    "DBRecommendationLog",
    "DBRecommendationConfig",
]
