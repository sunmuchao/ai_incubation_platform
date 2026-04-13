"""
SQLAlchemy 数据模型 - 关系进展领域

包含：关系进展记录、收藏地点等
"""
from db.models.base import *

class RelationshipProgressDB(Base):
    """关系进展记录"""
    __tablename__ = "relationship_progress"

    id = Column(String(36), primary_key=True, index=True)
    user_id_1 = Column(String(36), nullable=False, index=True)
    user_id_2 = Column(String(36), nullable=False, index=True)

    progress_type = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)

    progress_score = Column(Integer, default=5)

    related_data = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SavedLocationDB(Base):
    """收藏的地点/活动推荐"""
    __tablename__ = "saved_locations"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), nullable=False, index=True)

    location_name = Column(String(200), nullable=False)
    location_type = Column(String(50), nullable=False)
    address = Column(String(500), nullable=True)

    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    reason = Column(Text, nullable=True)
    tags = Column(Text, default="")

    rating = Column(Float, nullable=True)
    price_level = Column(Integer, nullable=True)

    source = Column(String(50), default="manual")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)

__all__ = ["RelationshipProgressDB", "SavedLocationDB"]