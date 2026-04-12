"""
自主代理引擎数据模型

心跳机制相关数据表：
- HeartbeatRuleStateDB：规则执行状态追踪
- PushHistoryDB：推送历史记录
"""
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, JSON, Index
from sqlalchemy.sql import func
from db.database import Base
from utils.logger import logger


class HeartbeatRuleStateDB(Base):
    """
    心跳规则执行状态表

    记录每个规则的最后执行时间、结果、统计信息
    用于判断规则是否到期执行
    """
    __tablename__ = "heartbeat_rule_state"

    id = Column(String(64), primary_key=True)
    rule_name = Column(String(64), nullable=False, index=True, comment="规则名称")
    user_id = Column(String(64), nullable=True, index=True, comment="用户ID（全局规则时为NULL）")

    # 执行状态
    last_run_at = Column(DateTime(timezone=True), nullable=True, comment="最后执行时间")
    last_result = Column(String(32), nullable=True, comment="最后结果：executed/skipped/heartbeat_ok")
    last_action = Column(String(128), nullable=True, comment="最后执行的行动")
    last_error = Column(Text, nullable=True, comment="最后执行错误信息")

    # 统计信息
    run_count = Column(Integer, default=0, comment="执行次数")
    action_count = Column(Integer, default=0, comment="实际行动次数（非 HEARTBEAT_OK）")
    skip_count = Column(Integer, default=0, comment="跳过次数（无到期规则）")
    error_count = Column(Integer, default=0, comment="错误次数")

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 索引
    __table_args__ = (
        Index('idx_rule_user', 'rule_name', 'user_id'),
    )

    def __repr__(self):
        return f"<HeartbeatRuleState(rule={self.rule_name}, last_run={self.last_run_at}, result={self.last_result})>"


class PushHistoryDB(Base):
    """
    推送历史记录表

    记录每次推送的详细信息，用于效果追踪和避免重复推送
    """
    __tablename__ = "push_history"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(64), nullable=False, index=True, comment="接收推送的用户ID")
    match_id = Column(String(64), nullable=True, index=True, comment="关联的匹配ID（如果有）")

    # 推送类型
    push_type = Column(String(32), nullable=False, index=True, comment="推送类型：icebreaker/topic/activation/date/health")
    trigger_type = Column(String(32), nullable=True, comment="触发时机类型")
    trigger_rule = Column(String(64), nullable=True, comment="触发的规则名称")

    # 推送内容
    title = Column(String(128), nullable=True, comment="推送标题")
    message = Column(Text, nullable=True, comment="推送正文")
    data = Column(JSON, nullable=True, comment="推送携带的数据")

    # 推送渠道
    push_channel = Column(String(32), default="push", comment="推送渠道：push/sms/email")

    # 推送结果
    push_status = Column(String(16), default="pending", comment="推送状态：pending/sent/delivered/failed")
    push_error = Column(Text, nullable=True, comment="失败原因")
    pushed_at = Column(DateTime(timezone=True), nullable=True, comment="推送时间")

    # 用户响应
    response_type = Column(String(16), nullable=True, comment="响应类型：clicked/ignored/acted/dismissed")
    response_time_seconds = Column(Integer, nullable=True, comment="响应时间（秒）")
    responded_at = Column(DateTime(timezone=True), nullable=True, comment="响应时间")

    # 效果追踪
    action_taken = Column(String(64), nullable=True, comment="用户采取的具体行动")
    action_result = Column(Text, nullable=True, comment="行动结果")
    conversion_success = Column(Boolean, default=False, comment="是否成功转化")

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 紧凑索引
    __table_args__ = (
        Index('idx_push_user_type', 'user_id', 'push_type'),
        Index('idx_push_time', 'pushed_at'),
    )

    def __repr__(self):
        return f"<PushHistory(user={self.user_id}, type={self.push_type}, status={self.push_status})>"


class TriggerEventDB(Base):
    """
    触发事件记录表

    记录关键业务事件（match_created、message_sent等），用于事件驱动触发心跳
    """
    __tablename__ = "trigger_events"

    id = Column(String(64), primary_key=True)
    event_type = Column(String(32), nullable=False, index=True, comment="事件类型：match_created/message_sent/date_scheduled等")
    event_source = Column(String(64), nullable=True, index=True, comment="事件来源（用户ID/匹配ID等）")

    # 事件数据
    event_data = Column(JSON, nullable=True, comment="事件详情")

    # 触发结果
    triggered_action = Column(String(32), nullable=True, comment="触发的行动类型")
    triggered_push_id = Column(String(64), nullable=True, comment="触发的推送ID")
    heartbeat_triggered = Column(Boolean, default=False, comment="是否触发了心跳")

    # 处理状态
    processed = Column(Boolean, default=False, comment="是否已处理")
    processed_at = Column(DateTime(timezone=True), nullable=True, comment="处理时间")

    # 时间戳
    event_time = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<TriggerEvent(type={self.event_type}, source={self.event_source}, processed={self.processed})>"


class UserPushPreferencesDB(Base):
    """
    用户推送偏好设置表

    用户可配置推送开关、主动程度、免打扰时段等
    """
    __tablename__ = "user_push_preferences"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(64), nullable=False, unique=True, index=True, comment="用户ID")

    # 推送开关
    push_enabled = Column(Boolean, default=True, comment="是否开启推送")

    # 主动程度
    proactive_level = Column(String(16), default="medium", comment="主动程度：high/medium/low/none")

    # 免打扰时段
    quiet_hours_start = Column(String(8), default="22:00", comment="免打扰开始时间")
    quiet_hours_end = Column(String(8), default="08:00", comment="免打扰结束时间")

    # 推送渠道偏好（JSON数组）
    preferred_channels = Column(JSON, nullable=True, comment="偏好渠道：['push', 'sms']")

    # 各类型推送开关（JSON对象）
    type_preferences = Column(JSON, nullable=True, comment="各类型推送开关：{'icebreaker': true, 'topic': false}")

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<UserPushPreferences(user={self.user_id}, enabled={self.push_enabled}, level={self.proactive_level})>"


# ============= 初始化函数 =============

def init_autonomous_tables():
    """
    初始化自主代理相关表

    在数据库初始化时调用，确保新表被创建
    """
    from db.database import engine
    Base.metadata.create_all(bind=engine)
    logger.info("Autonomous agent tables initialized: heartbeat_rule_state, push_history, trigger_events, user_push_preferences")


# ============= 数据模型导出 =============

__all__ = [
    "HeartbeatRuleStateDB",
    "PushHistoryDB",
    "TriggerEventDB",
    "UserPushPreferencesDB",
    "init_autonomous_tables",
]