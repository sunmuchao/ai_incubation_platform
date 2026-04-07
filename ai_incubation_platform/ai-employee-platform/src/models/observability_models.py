"""
P5 AI 可观测性面板 - 数据模型

记录 AI 员工的工作日志、执行追踪、性能指标等
"""

from sqlalchemy import Column, String, Integer, BigInteger, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum, Float, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from .db_models import Base


class AgentExecutionStatus(str, enum.Enum):
    """Agent 执行状态"""
    PENDING = "pending"  # 等待执行
    RUNNING = "running"  # 执行中
    COMPLETED = "completed"  # 执行完成
    FAILED = "failed"  # 执行失败
    CANCELLED = "cancelled"  # 已取消


class StreamEventType(str, enum.Enum):
    """流式事件类型"""
    EXECUTION_START = "execution_start"  # 执行开始
    THINKING = "thinking"  # 思考中
    TOOL_CALL = "tool_call"  # 工具调用
    TOKEN_GENERATED = "token_generated"  # Token 生成
    API_CALL = "api_call"  # API 调用
    DECISION_MADE = "decision_made"  # 决策做出
    PROGRESS_UPDATE = "progress_update"  # 进度更新
    EXECUTION_COMPLETE = "execution_complete"  # 执行完成
    EXECUTION_FAILED = "execution_failed"  # 执行失败


class LogLevel(str, enum.Enum):
    """日志级别"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AgentExecutionDB(Base):
    """Agent 执行记录"""
    __tablename__ = "agent_executions"

    id = Column(String(64), primary_key=True)  # 执行 ID

    # 关联信息
    employee_id = Column(String(64), ForeignKey("ai_employees.id"), nullable=False)  # AI 员工 ID
    order_id = Column(String(64), ForeignKey("orders.id"), nullable=True)  # 关联订单 ID
    tenant_id = Column(String(64), ForeignKey("tenants.id"), nullable=False)  # 租户 ID
    user_id = Column(String(64), ForeignKey("users.id"), nullable=False)  # 触发用户 ID

    # 执行信息
    task_description = Column(Text, nullable=False)  # 任务描述
    execution_status = Column(SQLEnum(AgentExecutionStatus), default=AgentExecutionStatus.PENDING)  # 执行状态
    deerflow_task_id = Column(String(128), nullable=True)  # DeerFlow 任务 ID

    # 性能指标
    start_time = Column(DateTime, nullable=True)  # 开始时间
    end_time = Column(DateTime, nullable=True)  # 结束时间
    duration_ms = Column(Integer, nullable=True)  # 执行耗时 (毫秒)
    progress_percent = Column(Integer, default=0)  # 执行进度百分比 (0-100)

    # Token 消耗
    prompt_tokens = Column(Integer, default=0)  # 输入 Token 数
    completion_tokens = Column(Integer, default=0)  # 输出 Token 数
    total_tokens = Column(Integer, default=0)  # 总 Token 数
    token_cost = Column(Float, default=0.0)  # Token 成本 (美元)

    # Token 明细 (v1.1 新增)
    token_details = Column(JSON, nullable=True)  # Token 使用明细 [{step, prompt_tokens, completion_tokens, model, cost}]

    # API 调用统计
    api_call_count = Column(Integer, default=0)  # API 调用次数
    external_api_calls = Column(JSON, nullable=True)  # 外部 API 调用详情 [{url, method, status, latency}]

    # 执行结果
    result_summary = Column(Text, nullable=True)  # 执行结果摘要
    error_message = Column(Text, nullable=True)  # 错误信息
    error_stack = Column(Text, nullable=True)  # 错误堆栈

    # 决策追踪
    decision_tree = Column(JSON, nullable=True)  # 决策树 [{step, decision, reasoning}]
    tool_calls = Column(JSON, nullable=True)  # 工具调用记录 [{tool_name, input, output, duration}]

    # 流式事件 (v1.1 新增)
    stream_events = Column(JSON, nullable=True)  # 流式事件列表 [{event_id, event_type, timestamp, data}]

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联关系
    employee = relationship("AIEmployeeDB", back_populates="executions")
    logs = relationship("AgentLogDB", back_populates="execution", cascade="all, delete-orphan")
    metrics = relationship("AgentMetricDB", back_populates="execution", cascade="all, delete-orphan")
    stream_events_rel = relationship("StreamEventDB", back_populates="execution", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "order_id": self.order_id,
            "task_description": self.task_description[:200] + "..." if self.task_description and len(self.task_description) > 200 else self.task_description,
            "execution_status": self.execution_status.value,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "progress_percent": self.progress_percent,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "token_cost": self.token_cost,
            "token_details": self.token_details,
            "api_call_count": self.api_call_count,
            "result_summary": self.result_summary,
            "error_message": self.error_message,
            "stream_events": self.stream_events,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class StreamEventDB(Base):
    """
    Agent 流式事件记录 (v1.1 新增)

    用于实时追踪 AI 执行的每个事件，支持 WebSocket 推送
    """
    __tablename__ = "agent_stream_events"

    id = Column(String(64), primary_key=True)  # 事件 ID
    event_sequence = Column(Integer, nullable=False)  # 事件序号 (用于排序)

    # 关联信息
    execution_id = Column(String(64), ForeignKey("agent_executions.id"), nullable=False)  # 执行 ID
    tenant_id = Column(String(64), ForeignKey("tenants.id"), nullable=False)  # 租户 ID

    # 事件信息
    event_type = Column(SQLEnum(StreamEventType), nullable=False)  # 事件类型
    event_data = Column(JSON, nullable=True)  # 事件数据 {content, token_count, tool_info, etc.}

    # Token 追踪 (v1.1 新增)
    token_delta = Column(Integer, default=0)  # 本次事件产生的 Token 数
    cumulative_tokens = Column(Integer, default=0)  # 累计 Token 数

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # 关联关系
    execution = relationship("AgentExecutionDB", back_populates="stream_events_rel")

    def to_dict(self):
        return {
            "id": self.id,
            "event_sequence": self.event_sequence,
            "execution_id": self.execution_id,
            "event_type": self.event_type.value,
            "event_data": self.event_data,
            "token_delta": self.token_delta,
            "cumulative_tokens": self.cumulative_tokens,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AgentLogDB(Base):
    """Agent 执行日志"""
    __tablename__ = "agent_logs"

    id = Column(String(64), primary_key=True)  # 日志 ID

    # 关联信息
    execution_id = Column(String(64), ForeignKey("agent_executions.id"), nullable=False)  # 执行 ID
    tenant_id = Column(String(64), ForeignKey("tenants.id"), nullable=False)  # 租户 ID

    # 日志信息
    log_level = Column(SQLEnum(LogLevel), default=LogLevel.INFO)  # 日志级别
    log_message = Column(Text, nullable=False)  # 日志内容
    log_category = Column(String(50), nullable=True)  # 日志分类 (tool_call/decision/api_call/thinking)

    # 上下文信息
    round_id = Column(String(64), nullable=True)  # 轮次 ID (用于多轮对话)
    step_number = Column(Integer, nullable=True)  # 步骤序号
    context_data = Column(JSON, nullable=True)  # 上下文数据 {parameters, state, etc.}

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # 关联关系
    execution = relationship("AgentExecutionDB", back_populates="logs")

    def to_dict(self):
        return {
            "id": self.id,
            "execution_id": self.execution_id,
            "log_level": self.log_level.value,
            "log_message": self.log_message,
            "log_category": self.log_category,
            "round_id": self.round_id,
            "step_number": self.step_number,
            "context_data": self.context_data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AgentMetricDB(Base):
    """Agent 性能指标"""
    __tablename__ = "agent_metrics"

    id = Column(String(64), primary_key=True)  # 指标 ID

    # 关联信息
    execution_id = Column(String(64), ForeignKey("agent_executions.id"), nullable=False)  # 执行 ID
    tenant_id = Column(String(64), ForeignKey("tenants.id"), nullable=False)  # 租户 ID

    # 指标类型
    metric_type = Column(String(50), nullable=False)  # 指标类型 (latency/token_usage/api_cost/success_rate)
    metric_name = Column(String(100), nullable=False)  # 指标名称

    # 指标值
    metric_value = Column(Float, nullable=False)  # 指标值
    metric_unit = Column(String(20), nullable=True)  # 单位 (ms/tokens/USD/percentage)

    # 维度信息
    dimensions = Column(JSON, nullable=True)  # 维度信息 {model, endpoint, operation}

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关联关系
    execution = relationship("AgentExecutionDB", back_populates="metrics")

    def to_dict(self):
        return {
            "id": self.id,
            "execution_id": self.execution_id,
            "metric_type": self.metric_type,
            "metric_name": self.metric_name,
            "metric_value": self.metric_value,
            "metric_unit": self.metric_unit,
            "dimensions": self.dimensions,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AgentWorkLogDB(Base):
    """
    AI 员工工作日志

    自动记录 AI 员工的工作过程，用于交付和审计
    """
    __tablename__ = "agent_work_logs"

    id = Column(String(64), primary_key=True)  # 工作日志 ID

    # 关联信息
    employee_id = Column(String(64), ForeignKey("ai_employees.id"), nullable=False)  # AI 员工 ID
    order_id = Column(String(64), ForeignKey("orders.id"), nullable=True)  # 订单 ID（可为空，支持无订单的执行）
    execution_id = Column(String(64), ForeignKey("agent_executions.id"), nullable=True)  # 执行 ID
    tenant_id = Column(String(64), ForeignKey("tenants.id"), nullable=False)  # 租户 ID
    user_id = Column(String(64), ForeignKey("users.id"), nullable=False)  # 关联用户 ID

    # 工作会话信息
    session_id = Column(String(64), nullable=True)  # 工作会话 ID
    session_start_time = Column(DateTime, nullable=True)  # 会话开始时间
    session_end_time = Column(DateTime, nullable=True)  # 会话结束时间

    # 工作内容
    work_description = Column(Text, nullable=False)  # 工作内容描述
    work_type = Column(String(50), nullable=False)  # 工作类型 (task_execution/communication/deliverable/research)

    # 交付物
    deliverables = Column(JSON, nullable=True)  # 交付物列表 [{file_id, filename, description}]
    deliverable_urls = Column(JSON, nullable=True)  # 交付物 URL 列表

    # 时间追踪
    time_spent_minutes = Column(Integer, default=0)  # 花费时间 (分钟)
    billable_time_minutes = Column(Integer, default=0)  # 计费时间 (分钟)

    # 状态
    is_submitted = Column(Boolean, default=False)  # 是否已提交
    is_reviewed = Column(Boolean, default=False)  # 是否已审核
    review_status = Column(String(20), default="pending")  # 审核状态 (pending/approved/rejected)
    review_comments = Column(Text, nullable=True)  # 审核意见

    # 自动标记
    is_auto_generated = Column(Boolean, default=True)  # 是否自动生成
    auto_generate_source = Column(String(50), nullable=True)  # 自动生成来源 (execution_log/time_tracking)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    submitted_at = Column(DateTime, nullable=True)  # 提交时间
    reviewed_at = Column(DateTime, nullable=True)  # 审核时间

    def to_dict(self):
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "order_id": self.order_id,
            "execution_id": self.execution_id,
            "work_description": self.work_description,
            "work_type": self.work_type,
            "deliverables": self.deliverables,
            "deliverable_urls": self.deliverable_urls,
            "time_spent_minutes": self.time_spent_minutes,
            "billable_time_minutes": self.billable_time_minutes,
            "is_submitted": self.is_submitted,
            "is_reviewed": self.is_reviewed,
            "review_status": self.review_status,
            "is_auto_generated": self.is_auto_generated,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
        }


# 添加到 db_models 的关联关系
def add_observability_relationships():
    """添加可观测性关联关系到现有模型"""
    from .db_models import AIEmployeeDB

    # AIEmployeeDB 关联
    if not hasattr(AIEmployeeDB, 'executions'):
        AIEmployeeDB.executions = relationship("AgentExecutionDB", back_populates="employee", lazy="dynamic")
