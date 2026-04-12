"""
关系压力测试数据库模型
"""
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, JSON, Text, ForeignKey
from sqlalchemy.sql import func
from db.database import Base


class StressTestDB(Base):
    """压力测试"""
    __tablename__ = "stress_tests"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    partner_id = Column(String(36), nullable=False, index=True)

    # 测试配置
    scenario_type = Column(String(30), nullable=False)  # value_conflict/lifestyle_difference/etc
    relationship_stage = Column(String(20), default="dating")  # dating/committed/married
    questions = Column(JSON, nullable=False)  # 测试问题列表

    # 状态
    status = Column(String(20), default="pending")  # pending/completed
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class StressTestAnswerDB(Base):
    """测试答案"""
    __tablename__ = "stress_test_answers"

    id = Column(String(36), primary_key=True, index=True)
    test_id = Column(String(36), ForeignKey("stress_tests.id"), nullable=False, index=True)
    question_id = Column(String(20), nullable=False)

    # 答案内容
    selected_option = Column(String(10), nullable=False)  # a/b/c/d
    open_response = Column(Text, nullable=True)  # 开放式回答

    # 分析结果
    analysis_result = Column(JSON, nullable=True)  # AI 分析结果

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())