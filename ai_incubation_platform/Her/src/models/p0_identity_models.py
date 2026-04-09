"""
P0: 多源身份核验系统

功能包括：
- 学历认证（学信网 API 对接）
- 职业认证（企业邮箱/LinkedIn）
- 收入认证（税单/银行流水）
- 房产认证（房产证电子凭证）
- 无犯罪记录（公安 API）

每个认证类型对应一个信任勋章，在匹配卡片中直观展示。

注意：IdentityVerificationDB 已在 db.models 中定义，此处不再重复定义。
"""
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, ForeignKey, Text, UniqueConstraint
from sqlalchemy.sql import func
from db.database import Base
from typing import Optional, Dict, Any
from datetime import datetime
import json


class TrustBadgeDB(Base):
    """用户信任勋章"""
    __tablename__ = "trust_badges"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 勋章类型
    badge_type = Column(String(50), nullable=False, unique=True, index=True)
    # 勋章列表:
    # - real_name_verified: 实名认证
    # - education_verified: 学历认证
    # - occupation_verified: 职业认证
    # - income_verified: 收入认证
    # - property_verified: 房产认证
    # - criminal_clear: 无犯罪记录
    # - vehicle_verified: 车辆认证

    # 勋章信息
    badge_name = Column(String(100), nullable=False)
    badge_description = Column(Text, nullable=True)
    badge_icon = Column(String(200), nullable=True)  # 图标 URL 或 emoji

    # 勋章等级（如学历：本科/硕士/博士）
    badge_level = Column(String(50), nullable=True)
    badge_level_value = Column(Integer, default=0)  # 数值化等级

    # 状态
    is_active = Column(Boolean, default=True, index=True)
    is_displayed = Column(Boolean, default=True)  # 是否公开展示

    # 来源验证 ID
    source_verification_id = Column(String(36), ForeignKey("identity_verifications.id"), nullable=True)

    # 时间戳
    earned_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # 更新日期
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class TrustBadgeHistoryDB(Base):
    """信任勋章历史"""
    __tablename__ = "trust_badges_history"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    badge_type = Column(String(50), nullable=False, index=True)

    # 事件类型
    event_type = Column(String(20), nullable=False)
    # earned, lost, renewed, updated, hidden, displayed

    # 事件详情
    event_data = Column(Text, default="")  # JSON 字符串
    event_note = Column(Text, nullable=True)

    # 时间戳
    event_at = Column(DateTime(timezone=True), server_default=func.now())
    actor_id = Column(String(36), nullable=True)  # 操作者 ID（user 或 admin）


class ExternalVerificationAPIConfigDB(Base):
    """外部验证 API 配置"""
    __tablename__ = "external_verification_api_configs"

    id = Column(String(36), primary_key=True, index=True)

    # API 配置
    api_name = Column(String(50), nullable=False, unique=True)
    # 配置列表:
    # - chsi: 学信网 API
    # - enterprise_email: 企业邮箱验证
    # - tax_bureau: 税务局 API
    # - bank_verify: 银行卡验证
    # - property_registry: 房产登记 API
    # - police_record: 公安无犯罪记录 API
    # - vehicle_registry: 车辆管理 API

    api_endpoint = Column(String(500), nullable=True)
    api_key = Column(String(500), nullable=True)
    api_secret = Column(String(500), nullable=True)

    # 配置
    config_data = Column(Text, default="")  # JSON 字符串
    rate_limit = Column(Integer, default=100)  # 每小时请求限制
    timeout_seconds = Column(Integer, default=30)

    # 状态
    is_active = Column(Boolean, default=True)
    last_tested_at = Column(DateTime(timezone=True), nullable=True)
    test_result = Column(String(20), nullable=True)  # success, fail

    # 统计
    total_requests = Column(Integer, default=0)
    successful_requests = Column(Integer, default=0)
    failed_requests = Column(Integer, default=0)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# 注意：TrustScoreDB 已在 p17_models.py 中定义，此处不再重复

# ============= 学历认证专用模型 =============

class EducationCredentialDB(Base):
    """学历凭证"""
    __tablename__ = "education_credentials"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 学历信息
    school_name = Column(String(200), nullable=False)  # 学校名称
    school_location = Column(String(100), nullable=True)  # 学校地点
    degree_type = Column(String(50), nullable=False)  # degree_type: associate, bachelor, master, doctor
    # associate (专科), bachelor (本科), master (硕士), doctor (博士)

    major = Column(String(100), nullable=True)  # 专业
    graduation_year = Column(Integer, nullable=True)  # 毕业年份
    student_id_hash = Column(String(64), nullable=True)  # 学号哈希（用于验证）

    # 验证信息
    chsi_verification_id = Column(String(100), nullable=True)  # 学信网验证码
    verification_status = Column(String(20), default="pending")  # pending, verified, failed
    verified_at = Column(DateTime(timezone=True), nullable=True)

    # 凭证文件
    certificate_url = Column(String(500), nullable=True)  # 学历证书 URL

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 索引
    __table_args__ = (
        UniqueConstraint('user_id', 'degree_type', name='uniq_user_degree'),
    )


# ============= 职业认证专用模型 =============

class OccupationCredentialDB(Base):
    """职业凭证"""
    __tablename__ = "occupation_credentials"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 职业信息
    company_name = Column(String(200), nullable=False)  # 公司名称
    company_type = Column(String(50), nullable=True)  # company_type: state_owned, private, foreign, startup
    # state_owned (国企), private (民企), foreign (外企), startup (创业), public_institution (事业单位)

    industry = Column(String(100), nullable=True)  # 行业
    position = Column(String(100), nullable=True)  # 职位
    employment_type = Column(String(20), nullable=True)  # employment_type: full_time, part_time, contract, self_employed

    # 工作年限
    work_years = Column(Integer, default=0)
    start_date = Column(DateTime(timezone=True), nullable=True)

    # 验证方式
    verification_method = Column(String(50), default="email")
    # email (企业邮箱), certificate (在职证明), social_security (社保记录)

    work_email = Column(String(200), nullable=True)  # 工作邮箱
    email_verified = Column(Boolean, default=False)
    email_verified_at = Column(DateTime(timezone=True), nullable=True)

    # 凭证文件
    proof_document_url = Column(String(500), nullable=True)  # 在职证明 URL

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# ============= 收入认证专用模型 =============

class IncomeCredentialDB(Base):
    """收入凭证"""
    __tablename__ = "income_credentials"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 收入范围
    income_range = Column(String(50), nullable=False)
    # income_range: <5k, 5k-10k, 10k-20k, 20k-30k, 30k-50k, 50k-100k, >100k
    # 单位：月收入（人民币）

    income_type = Column(String(50), nullable=True)
    # income_type: salary, bonus, investment, business, other

    # 验证方式
    verification_method = Column(String(50), default="tax_record")
    # tax_record (纳税记录), bank_statement (银行流水), social_security (社保)

    # 验证信息
    tax_record_hash = Column(String(64), nullable=True)  # 纳税记录哈希
    bank_name = Column(String(100), nullable=True)  # 银行名称

    # 验证状态
    verification_status = Column(String(20), default="pending")
    verified_at = Column(DateTime(timezone=True), nullable=True)

    # 凭证文件
    proof_document_url = Column(String(500), nullable=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# ============= 房产认证专用模型 =============

class PropertyCredentialDB(Base):
    """房产凭证"""
    __tablename__ = "property_credentials"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 房产信息
    property_location = Column(String(300), nullable=False)  # 房产位置
    property_type = Column(String(50), nullable=True)
    # property_type: apartment, villa, commercial, land
    # 住宅 (apartment), 别墅 (villa), 商铺 (commercial), 土地 (land)

    property_area = Column(Float, nullable=True)  # 面积（平方米）
    property_value = Column(Float, nullable=True)  # 估值（万元）

    # 产权信息
    ownership_type = Column(String(50), nullable=True)
    # ownership_type: sole, joint, family
    # 独立所有 (sole), 共有 (joint), 家庭共有 (family)

    property_cert_no = Column(String(100), nullable=True)  # 房产证号（哈希存储）
    property_cert_hash = Column(String(64), nullable=True)  # 房产证号哈希

    # 验证状态
    verification_status = Column(String(20), default="pending")
    verified_at = Column(DateTime(timezone=True), nullable=True)

    # 凭证文件
    property_cert_url = Column(String(500), nullable=True)  # 房产证 URL

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# ============================================
# 模型导出
# ============================================

__all__ = [
    'TrustBadgeDB',
    'TrustBadgeHistoryDB',
    'ExternalVerificationAPIConfigDB',
    'EducationCredentialDB',
    'OccupationCredentialDB',
    'IncomeCredentialDB',
    'PropertyCredentialDB',
]
