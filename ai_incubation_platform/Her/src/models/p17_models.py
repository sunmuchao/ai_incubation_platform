"""
P17 终极共振数据库模型

核心理念：人生合伙人
跨越风花雪月，看看你们能不能一起抗住生活的风浪。

包含以下模块：
1. 压力测试 - 危机预演、应对兼容性评估
2. 成长计划 - 共同进化图、资源推送
3. 靠谱背书 - 信任分算法、信用背书系统
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Boolean, Text, JSON, Enum
from sqlalchemy.orm import relationship
import enum

from db.database import Base


# ==================== 压力测试模块 ====================

class CrisisScenarioType(str, enum.Enum):
    """危机场景类型"""
    UNEMPLOYMENT = "unemployment"  # 失业
    FINANCIAL_CRISIS = "financial_crisis"  # 财务危机
    FAMILY_EMERGENCY = "family_emergency"  # 家庭急事
    HEALTH_ISSUE = "health_issue"  # 健康问题
    LONG_DISTANCE = "long_distance"  # 异地恋
    CAREER_CONFLICT = "career_conflict"  # 事业冲突
    VALUE_CONFLICT = "value_conflict"  # 价值观冲突


class StressTestResult(str, enum.Enum):
    """压力测试结果"""
    EXCELLENT = "excellent"  # 优秀 - 共同面对
    GOOD = "good"  # 良好 - 基本一致
    FAIR = "fair"  # 一般 - 需要沟通
    POOR = "poor"  # 较差 - 存在分歧


class StressTestScenarioDB(Base):
    """压力测试场景"""
    __tablename__ = "stress_test_scenarios"

    id = Column(String, primary_key=True)

    # 场景信息
    scenario_name = Column(String, nullable=False)
    scenario_type = Column(String, nullable=False)
    description = Column(Text, nullable=False)

    # 场景详情
    scenario_details = Column(JSON)
    # {background, trigger_event, constraints}

    # 难度等级
    difficulty_level = Column(Integer, default=3)  # 1-5

    # 预期反应
    expected_reactions = Column(JSON)

    # 评估标准
    evaluation_criteria = Column(JSON)

    # 使用次数
    usage_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)


class CoupleStressTestDB(Base):
    """情侣压力测试记录"""
    __tablename__ = "couple_stress_tests"

    id = Column(String, primary_key=True)

    user_a_id = Column(String, ForeignKey("users.id"), nullable=False)
    user_b_id = Column(String, ForeignKey("users.id"), nullable=False)

    # 使用的场景
    scenario_id = Column(String, ForeignKey("stress_test_scenarios.id"))

    # 测试方式
    test_mode = Column(String)  # separate, together

    # 用户 A 的反应
    user_a_response = Column(Text)
    user_a_decision = Column(JSON)

    # 用户 B 的反应
    user_b_response = Column(Text)
    user_b_decision = Column(JSON)

    # 兼容性评估
    compatibility_analysis = Column(JSON)
    # {value_alignment, problem_solving, emotional_support}

    # 测试结果
    test_result = Column(String)

    # AI 分析
    ai_analysis = Column(Text)

    # 建议
    recommendations = Column(JSON)

    is_completed = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)


# ==================== 成长计划模块 ====================

class GrowthPlanDB(Base):
    """成长计划"""
    __tablename__ = "growth_plans"

    id = Column(String, primary_key=True)

    user_a_id = Column(String, ForeignKey("users.id"), nullable=False)
    user_b_id = Column(String, ForeignKey("users.id"), nullable=False)

    # 计划信息
    plan_name = Column(String, nullable=False)
    plan_description = Column(Text)

    # 成长目标
    growth_goals = Column(JSON)
    # [{area, current_level, target_level, timeline}]

    # 成长领域
    growth_areas = Column(JSON)
    # career, health, finance, relationship, personal

    # 共同进化图
    evolution_map = Column(JSON)
    # 可视化的成长路径

    # 当前进度
    overall_progress = Column(Float, default=0.0)

    # 里程碑
    milestones = Column(JSON)
    # [{name, description, achieved, achieved_at}]

    status = Column(String, default="active")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class GrowthResourceDB(Base):
    """成长资源"""
    __tablename__ = "growth_resources"

    id = Column(String, primary_key=True)

    # 资源信息
    resource_title = Column(String, nullable=False)
    resource_type = Column(String)  # article, video, course, book, podcast

    # 内容
    resource_url = Column(String)
    resource_description = Column(Text)

    # 适用领域
    growth_areas = Column(JSON)

    # 难度等级
    difficulty_level = Column(Integer)  # 1-5

    # 预计耗时（分钟）
    estimated_duration = Column(Integer)

    # 评分
    avg_rating = Column(Float, default=0.0)
    usage_count = Column(Integer, default=0)

    # 标签
    tags = Column(JSON)

    created_at = Column(DateTime, default=datetime.utcnow)


class GrowthResourceRecommendationDB(Base):
    """成长资源推荐记录"""
    __tablename__ = "growth_resource_recommendations"

    id = Column(String, primary_key=True)

    user_a_id = Column(String, ForeignKey("users.id"), nullable=False)
    user_b_id = Column(String, ForeignKey("users.id"), nullable=False)

    # 推荐的资源 ID
    resource_id = Column(String, ForeignKey("growth_resources.id"))

    # 推荐理由
    recommendation_reason = Column(Text)

    # 推荐时机
    recommended_at = Column(DateTime, default=datetime.utcnow)

    # 是否已读/已看
    is_consumed = Column(Boolean, default=False)

    # 用户反馈
    user_feedback = Column(String)  # helpful, neutral, not_helpful
    user_rating = Column(Integer)  # 1-5


# ==================== 靠谱背书模块 ====================

class TrustScoreType(str, enum.Enum):
    """信任分类型"""
    RESPONSIBILITY = "responsibility"  # 责任感
    SINCERITY = "sincerity"  # 真诚度
    RELIABILITY = "reliability"  # 可靠性
    EMPATHY = "empathy"  # 共情能力
    CONSISTENCY = "consistency"  # 一致性


class TrustScoreDB(Base):
    """信任分记录"""
    __tablename__ = "trust_scores"

    id = Column(String, primary_key=True)

    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    # 总体信任分
    overall_trust_score = Column(Float, default=50.0)  # 0-100

    # 各维度得分
    responsibility_score = Column(Float, default=50.0)
    sincerity_score = Column(Float, default=50.0)
    reliability_score = Column(Float, default=50.0)
    empathy_score = Column(Float, default=50.0)
    consistency_score = Column(Float, default=50.0)

    # 评分依据
    score_basis = Column(JSON)
    # {completed_promises, honest_actions, supportive_behaviors}

    # 历史行为统计
    behavior_stats = Column(JSON)
    # {promises_kept, promises_broken, supportive_acts}

    # 信任等级
    trust_level = Column(String)  # bronze, silver, gold, platinum

    # 最后更新
    last_updated = Column(DateTime, default=datetime.utcnow)

    created_at = Column(DateTime, default=datetime.utcnow)


class TrustEndorsementDB(Base):
    """信任背书记录"""
    __tablename__ = "trust_endorsements"

    id = Column(String, primary_key=True)

    # 被背书人
    endorsed_user_id = Column(String, ForeignKey("users.id"), nullable=False)

    # 背书人
    endorser_user_id = Column(String, ForeignKey("users.id"), nullable=False)

    # 背书类型
    endorsement_type = Column(String, nullable=False)
    # relationship, cooperation, character, reliability

    # 背书内容
    endorsement_text = Column(Text, nullable=False)

    # 关系背景
    relationship_context = Column(String)
    # ex_partner, colleague, friend, teammate

    # 背书权重
    endorsement_weight = Column(Float, default=1.0)

    # 验证状态
    is_verified = Column(Boolean, default=False)

    # 可见性
    visibility = Column(String, default="public")  # public, private, friends_only

    created_at = Column(DateTime, default=datetime.utcnow)


class TrustEndorsementSummaryDB(Base):
    """信任背书汇总"""
    __tablename__ = "trust_endorsement_summaries"

    id = Column(String, primary_key=True)

    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True)

    # 背书统计
    total_endorsements = Column(Integer, default=0)
    verified_endorsements = Column(Integer, default=0)

    # 按类型分类
    endorsements_by_type = Column(JSON)

    # 加权信任分
    weighted_trust_score = Column(Float, default=0.0)

    # 信任标签
    trust_badges = Column(JSON)
    # ["靠谱伴侣", "言出必行", "温暖体贴"]

    # 背书摘要
    endorsement_highlights = Column(JSON)

    last_updated = Column(DateTime, default=datetime.utcnow)


# 创建全局服务实例（在 p17_services.py 中实现）
