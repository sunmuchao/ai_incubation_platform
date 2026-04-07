"""
P7 技能认证考试数据模型
"""
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum, JSON, Array
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
import uuid

from config.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


# ==================== 枚举类型 ====================

class CertificationStatusEnum(str, enum.Enum):
    """认证状态"""
    DRAFT = "draft"  # 草稿
    ACTIVE = "active"  # 启用
    INACTIVE = "inactive"  # 停用
    ARCHIVED = "archived"  # 归档


class QuestionTypeEnum(str, enum.Enum):
    """题目类型"""
    SINGLE_CHOICE = "single_choice"  # 单选题
    MULTIPLE_CHOICE = "multiple_choice"  # 多选题
    TRUE_FALSE = "true_false"  # 判断题
    SHORT_ANSWER = "short_answer"  # 简答题
    CODE_COMPLETION = "code_completion"  # 代码填空
    PRACTICAL_TASK = "practical_task"  # 实操题


class DifficultyLevelEnum(str, enum.Enum):
    """难度等级"""
    EASY = "easy"  # 简单
    MEDIUM = "medium"  # 中等
    HARD = "hard"  # 困难
    EXPERT = "expert"  # 专家


class ExamStatusEnum(str, enum.Enum):
    """考试状态"""
    NOT_STARTED = "not_started"  # 未开始
    IN_PROGRESS = "in_progress"  # 进行中
    SUBMITTED = "submitted"  # 已提交
    GRADED = "graded"  # 已评分
    CERTIFIED = "certified"  # 已认证
    EXPIRED = "expired"  # 已过期


class CertificationLevelEnum(str, enum.Enum):
    """认证等级"""
    FOUNDATION = "foundation"  # 基础级
    INTERMEDIATE = "intermediate"  # 进阶级
    PROFESSIONAL = "professional"  # 专业级
    EXPERT = "expert"  # 专家级


# ==================== 核心模型 ====================

class CertificationDB(Base):
    """认证表 - 定义一个认证考试"""
    __tablename__ = "certifications"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, unique=True, nullable=False)  # 认证名称
    description = Column(Text, nullable=True)  # 认证描述
    skill_category = Column(String, nullable=False)  # 技能分类
    skill_tag_id = Column(String, ForeignKey("skill_tags.id"), nullable=True)  # 关联技能标签

    # 认证等级
    level = Column(SQLEnum(CertificationLevelEnum), default=CertificationLevelEnum.FOUNDATION)

    # 考试配置
    passing_score = Column(Float, default=70.0)  # 及格分数 (0-100)
    time_limit_minutes = Column(Integer, default=60)  # 考试时限 (分钟)
    total_questions = Column(Integer, default=0)  # 题目总数
    valid_days = Column(Integer, default=365)  # 认证有效期 (天)

    # 状态
    status = Column(SQLEnum(CertificationStatusEnum), default=CertificationStatusEnum.DRAFT)

    # 费用
    exam_fee = Column(Float, default=0.0)  # 考试费用
    renewal_fee = Column(Float, default=0.0)  # 续期费用

    # 统计数据
    total_attempts = Column(Integer, default=0)  # 总考试次数
    pass_rate = Column(Float, default=0.0)  # 通过率
    average_score = Column(Float, default=0.0)  # 平均分

    # 认证标识配置
    badge_icon_url = Column(String, nullable=True)  # 徽章图标 URL
    badge_color = Column(String, nullable=True)  # 徽章颜色

    # 创建信息
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关系
    questions = relationship("QuestionDB", back_populates="certification", cascade="all, delete-orphan")
    attempts = relationship("ExamAttemptDB", back_populates="certification", cascade="all, delete-orphan")
    holders = relationship("CertificationHolderDB", back_populates="certification", cascade="all, delete-orphan")


class QuestionDB(Base):
    """题目表"""
    __tablename__ = "exam_questions"

    id = Column(String, primary_key=True, default=generate_uuid)
    certification_id = Column(String, ForeignKey("certifications.id"), nullable=False)

    # 题目信息
    question_type = Column(SQLEnum(QuestionTypeEnum), nullable=False)
    difficulty = Column(SQLEnum(DifficultyLevelEnum), default=DifficultyLevelEnum.MEDIUM)

    # 题目内容
    question_text = Column(Text, nullable=False)  # 题目描述
    question_stem = Column(JSON, nullable=True)  # 题目主干 (富文本/代码等)

    # 选项 (选择题)
    options = Column(JSON, nullable=True)  # 选项列表 [{"key": "A", "text": "..."}]
    correct_answer = Column(JSON, nullable=False)  # 正确答案

    # 评分配置
    score = Column(Float, default=1.0)  # 题目分值
    partial_credit = Column(Boolean, default=False)  # 是否支持部分得分

    # 解析
    explanation = Column(Text, nullable=True)  # 答案解析
    tags = Column(JSON, default=list)  # 题目标签

    # 题目顺序
    order = Column(Integer, default=0)

    # 元数据
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关系
    certification = relationship("CertificationDB", back_populates="questions")


class ExamAttemptDB(Base):
    """考试尝试记录表"""
    __tablename__ = "exam_attempts"

    id = Column(String, primary_key=True, default=generate_uuid)
    certification_id = Column(String, ForeignKey("certifications.id"), nullable=False)
    user_id = Column(String, nullable=False, index=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=True)

    # 考试状态
    status = Column(SQLEnum(ExamStatusEnum), default=ExamStatusEnum.NOT_STARTED)

    # 答题信息
    answers = Column(JSON, default=list)  # 答案列表 [{"question_id": "...", "answer": "..."}]
    score = Column(Float, nullable=True)  # 得分
    max_score = Column(Float, nullable=True)  # 满分
    percentage = Column(Float, nullable=True)  # 得分百分比

    # 时间信息
    started_at = Column(DateTime, nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    time_spent_seconds = Column(Integer, nullable=True)  # 实际用时 (秒)

    # 结果
    passed = Column(Boolean, nullable=True)
    feedback = Column(Text, nullable=True)  # 考试反馈

    # 详细答题记录
    question_results = Column(JSON, default=list)  # 每题结果 [{"question_id": "...", "correct": true, "score": 1.0}]

    # 创建信息
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关系
    certification = relationship("CertificationDB", back_populates="attempts")


class CertificationHolderDB(Base):
    """认证持有者表"""
    __tablename__ = "certification_holders"

    id = Column(String, primary_key=True, default=generate_uuid)
    certification_id = Column(String, ForeignKey("certifications.id"), nullable=False)
    user_id = Column(String, nullable=False, index=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=True)

    # 认证信息
    certification_name = Column(String, nullable=False)
    certification_level = Column(SQLEnum(CertificationLevelEnum), nullable=False)
    skill_category = Column(String, nullable=False)

    # 获得信息
    obtained_at = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=True)  # 过期时间
    exam_attempt_id = Column(String, nullable=True)  # 关联的考试记录 ID

    # 证书信息
    certificate_number = Column(String, unique=True, nullable=False)  # 证书编号
    certificate_url = Column(String, nullable=True)  # 证书 URL

    # 状态
    status = Column(String, default="active")  # active, expired, revoked

    # 续期信息
    renewal_count = Column(Integer, default=0)
    last_renewed_at = Column(DateTime, nullable=True)

    # 创建信息
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关系
    certification = relationship("CertificationDB", back_populates="holders")
    tenant = relationship("TenantDB", backref="certification_holders")


class QuestionBankDB(Base):
    """题库表 - 可复用的题目集合"""
    __tablename__ = "question_banks"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)  # 题库名称
    description = Column(Text, nullable=True)
    skill_category = Column(String, nullable=False)  # 技能分类

    # 题目列表
    question_ids = Column(JSON, default=list)

    # 元数据
    total_questions = Column(Integer, default=0)
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ==================== 辅助模型 ====================

class ExamConfigDB(Base):
    """考试配置表 - 用于动态生成试卷"""
    __tablename__ = "exam_configs"

    id = Column(String, primary_key=True, default=generate_uuid)
    certification_id = Column(String, ForeignKey("certifications.id"), nullable=True)

    # 组卷规则
    total_questions = Column(Integer, default=20)
    time_limit_minutes = Column(Integer, default=60)
    passing_score = Column(Float, default=70.0)

    # 难度分布 {"easy": 0.3, "medium": 0.5, "hard": 0.2}
    difficulty_distribution = Column(JSON, default=dict)

    # 题型分布 {"single_choice": 0.6, "multiple_choice": 0.3, "true_false": 0.1}
    question_type_distribution = Column(JSON, default=dict)

    # 技能点覆盖
    skill_coverage = Column(JSON, default=list)  # [{"skill": "...", "min_questions": 3}]

    # 随机种子 (用于可重复组卷)
    random_seed = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
