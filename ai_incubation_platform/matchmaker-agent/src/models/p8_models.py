"""
P8 企业数据看板与绩效管理 - 数据模型

包含：
- 企业数据看板模型
- 绩效管理模型
- 组织架构模型
- 运营角色管理模型
"""
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from db.database import Base


# ============= P8-001: 企业数据看板模型 =============

class DashboardMetricsDB(Base):
    """企业核心指标快照"""
    __tablename__ = "dashboard_metrics"

    id = Column(String(36), primary_key=True, index=True)

    # 指标类型
    metric_type = Column(String(50), nullable=False, index=True)
    # metric_type 列表:
    # - user_growth: 用户增长
    # - matching: 匹配数据
    # - revenue: 收入数据
    # - safety: 安全数据
    # - engagement: 活跃度数据

    # 指标数据 (JSON 存储)
    metric_data = Column(JSON, nullable=False)
    # metric_data 示例:
    # {
    #     "total_users": 10000,
    #     "active_users": 5000,
    #     "new_users_today": 100,
    #     "paying_users": 500
    # }

    # 时间维度
    date = Column(DateTime(timezone=True), nullable=False, index=True)
    period = Column(String(20), nullable=False)  # daily, weekly, monthly

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DashboardTrendDB(Base):
    """趋势数据记录"""
    __tablename__ = "dashboard_trends"

    id = Column(String(36), primary_key=True, index=True)

    # 趋势类型
    trend_type = Column(String(50), nullable=False, index=True)
    # trend_type 列表:
    # - user_growth_trend: 用户增长趋势
    # - matching_success_trend: 匹配成功趋势
    # - revenue_trend: 收入趋势
    # - activity_trend: 活跃度趋势

    # 趋势数据点
    data_points = Column(JSON, nullable=False)
    # data_points 示例:
    # [
    #     {"date": "2026-04-01", "value": 100},
    #     {"date": "2026-04-02", "value": 120}
    # ]

    # 时间范围
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DashboardReportDB(Base):
    """数据报告"""
    __tablename__ = "dashboard_reports"

    id = Column(String(36), primary_key=True, index=True)

    # 报告类型
    report_type = Column(String(50), nullable=False)
    # report_type 列表:
    # - daily_summary: 每日摘要
    # - weekly_summary: 每周摘要
    # - monthly_summary: 每月摘要
    # - custom: 自定义报告

    # 报告标题和描述
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # 报告内容
    report_data = Column(JSON, nullable=False)

    # 生成者
    generated_by = Column(String(36), nullable=True)  # 用户 ID 或 "system"

    # 时间范围
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)

    # 状态
    status = Column(String(20), default="active")  # active, archived

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# ============= P8-002: 绩效管理模型 =============

class KPIMetricDB(Base):
    """KPI 指标定义"""
    __tablename__ = "kpi_metrics"

    id = Column(String(36), primary_key=True, index=True)

    # KPI 名称
    metric_name = Column(String(100), nullable=False, unique=True)
    # metric_name 列表:
    # - match_success_rate: 匹配成功率
    # - user_satisfaction: 用户满意度
    # - response_time: 响应时间
    # - user_growth: 用户增长
    # - revenue: 收入
    # - safety_score: 安全评分

    # KPI 描述
    description = Column(Text, nullable=True)

    # 目标值
    target_value = Column(Float, nullable=False)

    # 当前值
    current_value = Column(Float, default=0.0)

    # 权重 (用于综合评分)
    weight = Column(Float, default=1.0)

    # 单位
    unit = Column(String(50), nullable=True)  # %, 分，个，etc.

    # 状态
    is_active = Column(Boolean, default=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class PerformanceReviewDB(Base):
    """绩效评估记录"""
    __tablename__ = "performance_reviews"

    id = Column(String(36), primary_key=True, index=True)

    # 评估对象
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    review_type = Column(String(50), nullable=False)
    # review_type 列表:
    # - ai_matchmaker: AI 红娘绩效
    # - operator: 运营人员绩效
    # - system: 系统整体绩效

    # 评估周期
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    period_type = Column(String(20), nullable=False)  # daily, weekly, monthly, quarterly

    # KPI 评分
    kpi_scores = Column(JSON, nullable=False)
    # kpi_scores 示例:
    # {
    #     "match_success_rate": {"target": 20, "actual": 18, "score": 90, "weight": 1.0},
    #     "user_satisfaction": {"target": 4.5, "actual": 4.3, "score": 85, "weight": 1.0}
    # }

    # 综合评分
    overall_score = Column(Float, nullable=False)

    # 绩效等级
    performance_level = Column(String(5), nullable=True)
    # performance_level: S (90-100), A (80-89), B (70-79), C (60-69), D (<60)

    # 评估意见
    review_comments = Column(Text, nullable=True)

    # 评估者
    reviewed_by = Column(String(36), nullable=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class OperatorPerformanceDB(Base):
    """运营人员绩效追踪"""
    __tablename__ = "operator_performance"

    id = Column(String(36), primary_key=True, index=True)

    # 运营人员 ID
    operator_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 绩效指标
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(Float, nullable=False)

    # 时间周期
    period_date = Column(DateTime(timezone=True), nullable=False, index=True)

    # 详情
    metric_details = Column(JSON, nullable=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ============= P8-003: 组织架构模型 =============

class DepartmentDB(Base):
    """部门组织架构"""
    __tablename__ = "departments"

    id = Column(String(36), primary_key=True, index=True)

    # 部门名称
    name = Column(String(100), nullable=False)

    # 部门编码
    code = Column(String(50), nullable=False, unique=True)

    # 父部门 ID (用于层级结构)
    parent_id = Column(String(36), ForeignKey("departments.id"), nullable=True, index=True)

    # 部门层级
    level = Column(Integer, nullable=False, default=1)
    # level 说明:
    # 1: headquarters (总部)
    # 2: division (事业部)
    # 3: department (部门)
    # 4: team (团队)

    # 部门描述
    description = Column(Text, nullable=True)

    # 部门负责人
    manager_id = Column(String(36), nullable=True)

    # 部门状态
    is_active = Column(Boolean, default=True)

    # 排序
    sort_order = Column(Integer, default=0)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 自引用关系
    children = relationship("DepartmentDB", backref="parent", remote_side=[id])


class OperatorRoleDB(Base):
    """运营角色定义"""
    __tablename__ = "operator_roles"

    id = Column(String(36), primary_key=True, index=True)

    # 角色名称
    role_name = Column(String(50), nullable=False, unique=True)
    # role_name 列表:
    # - super_admin: 超级管理员
    # - operations_manager: 运营经理
    # - content_moderator: 内容审核员
    # - customer_service: 客服人员
    # - data_analyst: 数据分析师

    # 角色描述
    description = Column(Text, nullable=True)

    # 权限列表
    permissions = Column(JSON, nullable=False)
    # permissions 示例:
    # [
    #     "dashboard:view",
    #     "user:view",
    #     "user:ban",
    #     "report:view",
    #     "report:export"
    # ]

    # 角色状态
    is_active = Column(Boolean, default=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class UserOperatorDB(Base):
    """用户 - 运营角色关联"""
    __tablename__ = "user_operators"

    id = Column(String(36), primary_key=True, index=True)

    # 用户 ID
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # 角色 ID
    role_id = Column(String(36), ForeignKey("operator_roles.id"), nullable=False, index=True)

    # 部门 ID
    department_id = Column(String(36), ForeignKey("departments.id"), nullable=True, index=True)

    # 角色状态
    is_active = Column(Boolean, default=True)

    # 任职时间
    appointed_at = Column(DateTime(timezone=True), server_default=func.now())
    expired_at = Column(DateTime(timezone=True), nullable=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class OperatorActionLogDB(Base):
    """运营操作日志"""
    __tablename__ = "operator_action_logs"

    id = Column(String(36), primary_key=True, index=True)

    # 操作者
    operator_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 操作类型
    action_type = Column(String(50), nullable=False, index=True)
    # action_type 列表:
    # - user_ban: 封禁用户
    # - user_unban: 解封用户
    # - content_delete: 删除内容
    # - report_handle: 处理举报
    # - data_export: 导出数据
    # - settings_change: 修改配置

    # 操作对象
    target_type = Column(String(50), nullable=True)  # user, report, content, setting
    target_id = Column(String(36), nullable=True, index=True)

    # 操作详情
    action_details = Column(JSON, nullable=True)

    # 操作结果
    result = Column(String(20), nullable=True)  # success, failed, partial

    # IP 地址
    ip_address = Column(String(45), nullable=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ============= P8-004: 数据导出模型 =============

class ExportTaskDB(Base):
    """数据导出任务"""
    __tablename__ = "export_tasks"

    id = Column(String(36), primary_key=True, index=True)

    # 请求者
    requested_by = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 导出类型
    export_type = Column(String(50), nullable=False)
    # export_type 列表:
    # - user_data: 用户数据
    # - analytics: 分析数据
    # - performance: 绩效数据
    # - financial: 财务数据
    # - safety: 安全数据

    # 导出格式
    export_format = Column(String(20), nullable=False)
    # export_format: json, csv, excel, pdf

    # 导出参数
    export_params = Column(JSON, nullable=True)
    # export_params 示例:
    # {
    #     "start_date": "2026-04-01",
    #     "end_date": "2026-04-30",
    #     "filters": {"department": "operations"}
    # }

    # 任务状态
    status = Column(String(20), default="pending")
    # status: pending, processing, completed, failed

    # 文件信息
    file_url = Column(String(500), nullable=True)
    file_size = Column(Integer, nullable=True)  # 字节

    # 错误信息
    error_message = Column(Text, nullable=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
