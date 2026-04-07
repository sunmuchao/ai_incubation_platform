"""
审计日志系统

记录敏感操作的完整审计轨迹，用于合规、安全分析和用户行为追踪。
"""
from typing import Optional, Dict, Any
from datetime import datetime
from db.database import get_db
from utils.logger import logger
import json
import uuid


class AuditLogDB:
    """审计日志数据库模型"""
    __tablename__ = "audit_logs"

    # 注意：这是手动定义的类，实际表通过 create_audit_table 创建
    # 字段定义用于参考
    columns = {
        "id": "TEXT PRIMARY KEY",
        "timestamp": "DATETIME DEFAULT CURRENT_TIMESTAMP",
        "actor": "VARCHAR(100) NOT NULL",  # 操作者（用户 ID 或系统）
        "actor_type": "VARCHAR(20)",  # 操作者类型（user/system/ai_agent）
        "action": "VARCHAR(100) NOT NULL",  # 操作类型
        "resource_type": "VARCHAR(50)",  # 资源类型（user/match/conversation 等）
        "resource_id": "VARCHAR(200)",  # 资源 ID
        "request": "TEXT",  # JSON 请求
        "response": "TEXT",  # JSON 响应
        "status": "VARCHAR(20) NOT NULL",  # success/failure
        "trace_id": "VARCHAR(100)",  # 追踪 ID
        "ip_address": "VARCHAR(50)",  # IP 地址
        "user_agent": "TEXT",  # 用户代理
        "metadata": "TEXT"  # JSON 元数据
    }


def create_audit_table():
    """创建审计日志表"""
    from sqlalchemy import text
    db = next(get_db())
    try:
        # 使用 SQLAlchemy 的 execute 方法执行原生 SQL
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id TEXT PRIMARY KEY,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                actor VARCHAR(100) NOT NULL,
                actor_type VARCHAR(20) DEFAULT 'user',
                action VARCHAR(100) NOT NULL,
                resource_type VARCHAR(50),
                resource_id VARCHAR(200),
                request TEXT,
                response TEXT,
                status VARCHAR(20) NOT NULL,
                trace_id VARCHAR(100),
                ip_address VARCHAR(50),
                user_agent TEXT,
                metadata TEXT
            )
        """))

        # 创建索引
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_logs(actor)
        """))
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs(action)
        """))
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_audit_resource ON audit_logs(resource_type, resource_id)
        """))
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp)
        """))
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_audit_trace ON audit_logs(trace_id)
        """))

        db.commit()
        logger.info("Audit log table created successfully")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create audit log table: {e}")
        raise
    finally:
        db.close()


class AuditLogger:
    """
    审计日志记录器

    用法:
        audit_logger = AuditLogger()
        audit_logger.log(
            actor="user_123",
            action="match_recommend",
            resource_type="match",
            resource_id="match_456",
            request={"user_id": "user_123"},
            response={"success": True},
            status="success"
        )
    """

    # 需要审计的操作类型
    SENSITIVE_ACTIONS = {
        # 匹配相关
        "match_recommend": "推荐匹配对象",
        "match_swipe": "滑动操作（喜欢/不喜欢）",
        "match_mutual": "双向匹配成功",
        "match_reject": "拒绝匹配",

        # 关系相关
        "relationship_track": "追踪关系进展",
        "relationship_health_check": "关系健康度分析",
        "relationship_stage_change": "关系阶段变更",

        # 对话相关
        "conversation_start": "开始对话",
        "icebreaker_suggest": "推荐破冰话题",
        "message_send": "发送消息",
        "message_read": "阅读消息",

        # 隐私相关
        "profile_view": "查看个人资料",
        "profile_update": "更新个人资料",
        "profile_photo_upload": "上传照片",
        "location_access": "访问位置信息",

        # 安全相关
        "user_report": "举报用户",
        "user_block": "拉黑用户",
        "user_unblock": "解除拉黑",
        "content_moderate": "内容审核",

        # 支付相关
        "payment_create": "创建支付订单",
        "payment_complete": "完成支付",
        "subscription_cancel": "取消订阅",
        "refund_request": "申请退款",

        # AI 自主操作
        "ai_autonomous_match": "AI 自主匹配推荐",
        "ai_health_analysis": "AI 关系分析",
        "ai_topic_suggest": "AI 话题推荐"
    }

    def __init__(self):
        self._buffer = []
        self._buffer_size = 100

    def log(
        self,
        actor: str,
        action: str,
        status: str,
        actor_type: str = "user",
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        request: Optional[Dict] = None,
        response: Optional[Dict] = None,
        trace_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict] = None,
        sync: bool = False
    ) -> str:
        """
        记录审计日志

        Args:
            actor: 操作者（用户 ID 或系统名称）
            action: 操作类型（见 SENSITIVE_ACTIONS）
            status: 操作状态（success/failure）
            actor_type: 操作者类型（user/system/ai_agent）
            resource_type: 资源类型
            resource_id: 资源 ID
            request: 请求数据（自动序列化）
            response: 响应数据（自动序列化）
            trace_id: 追踪 ID（用于关联请求链）
            ip_address: IP 地址
            user_agent: 用户代理
            metadata: 额外元数据
            sync: 是否同步写入（默认异步缓冲）

        Returns:
            审计日志 ID
        """
        # 生成唯一 ID
        log_id = str(uuid.uuid4())

        # 生成或复用 trace_id
        if not trace_id:
            trace_id = str(uuid.uuid4())

        # 序列化 JSON 字段
        request_json = json.dumps(request) if request else None
        response_json = json.dumps(response) if response else None
        metadata_json = json.dumps(metadata) if metadata else None

        # 脱敏敏感信息
        if request_json:
            request_json = self._redact_sensitive_data(request_json)
        if response_json:
            response_json = self._redact_sensitive_data(response_json)

        audit_entry = {
            "id": log_id,
            "timestamp": datetime.now().isoformat(),
            "actor": actor,
            "actor_type": actor_type,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "request": request_json,
            "response": response_json,
            "status": status,
            "trace_id": trace_id,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "metadata": metadata_json
        }

        # 检查是否是敏感操作
        if action in self.SENSITIVE_ACTIONS:
            logger.info(f"Audit: {action} by {actor} - {status}")
        else:
            logger.debug(f"Audit: {action} by {actor} - {status}")

        if sync:
            self._write_immediately(audit_entry)
        else:
            self._buffer.append(audit_entry)
            if len(self._buffer) >= self._buffer_size:
                self._flush_buffer()

        return log_id

    def _redact_sensitive_data(self, json_str: str) -> str:
        """
        脱敏敏感数据

        移除或掩码：
        - 密码
        - token
        - 完整身份证号
        - 完整手机号
        """
        try:
            data = json.loads(json_str)

            # 敏感字段列表
            sensitive_fields = [
                "password", "password_hash", "token", "access_token",
                "refresh_token", "api_key", "secret", "id_number"
            ]

            for field in sensitive_fields:
                if field in data:
                    value = data[field]
                    if isinstance(value, str) and len(value) > 4:
                        # 保留后 4 位
                        data[field] = f"***{value[-4:]}"
                    else:
                        data[field] = "***"

            return json.dumps(data)
        except (json.JSONDecodeError, Exception):
            # 解析失败，返回原始字符串
            return json_str

    def _write_immediately(self, entry: dict):
        """立即写入数据库"""
        try:
            db = next(get_db())
            cursor = db.cursor()

            cursor.execute("""
                INSERT INTO audit_logs
                (id, timestamp, actor, actor_type, action, resource_type, resource_id,
                 request, response, status, trace_id, ip_address, user_agent, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry["id"],
                entry["timestamp"],
                entry["actor"],
                entry["actor_type"],
                entry["action"],
                entry.get("resource_type"),
                entry.get("resource_id"),
                entry.get("request"),
                entry.get("response"),
                entry["status"],
                entry.get("trace_id"),
                entry.get("ip_address"),
                entry.get("user_agent"),
                entry.get("metadata")
            ))

            db.commit()
        except Exception as e:
            logger.error(f"AuditLogger: Failed to write audit log: {e}")

    def _flush_buffer(self):
        """刷新缓冲区"""
        if not self._buffer:
            return

        try:
            db = next(get_db())
            cursor = db.cursor()

            for entry in self._buffer:
                cursor.execute("""
                    INSERT INTO audit_logs
                    (id, timestamp, actor, actor_type, action, resource_type, resource_id,
                     request, response, status, trace_id, ip_address, user_agent, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    entry["id"],
                    entry["timestamp"],
                    entry["actor"],
                    entry["actor_type"],
                    entry["action"],
                    entry.get("resource_type"),
                    entry.get("resource_id"),
                    entry.get("request"),
                    entry.get("response"),
                    entry["status"],
                    entry.get("trace_id"),
                    entry.get("ip_address"),
                    entry.get("user_agent"),
                    entry.get("metadata")
                ))

            db.commit()
            self._buffer.clear()
            logger.debug("AuditLogger: Buffer flushed")

        except Exception as e:
            logger.error(f"AuditLogger: Failed to flush buffer: {e}")

    def flush(self):
        """手动刷新缓冲区"""
        self._flush_buffer()

    def query(
        self,
        actor: Optional[str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> list:
        """
        查询审计日志

        Args:
            actor: 按操作者过滤
            action: 按操作类型过滤
            resource_type: 按资源类型过滤
            resource_id: 按资源 ID 过滤
            trace_id: 按追踪 ID 过滤
            start_time: 起始时间
            end_time: 结束时间
            limit: 返回数量限制

        Returns:
            审计日志列表
        """
        # 先刷新缓冲区
        self._flush_buffer()

        db = next(get_db())
        cursor = db.cursor()

        conditions = []
        params = []

        if actor:
            conditions.append("actor = ?")
            params.append(actor)
        if action:
            conditions.append("action = ?")
            params.append(action)
        if resource_type:
            conditions.append("resource_type = ?")
            params.append(resource_type)
        if resource_id:
            conditions.append("resource_id = ?")
            params.append(resource_id)
        if trace_id:
            conditions.append("trace_id = ?")
            params.append(trace_id)
        if start_time:
            conditions.append("timestamp >= ?")
            params.append(start_time.isoformat())
        if end_time:
            conditions.append("timestamp <= ?")
            params.append(end_time.isoformat())

        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        query = f"""
            SELECT id, timestamp, actor, actor_type, action, resource_type, resource_id,
                   request, response, status, trace_id, metadata
            FROM audit_logs
            {where_clause}
            ORDER BY timestamp DESC
            LIMIT ?
        """
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()

        results = []
        for row in rows:
            results.append({
                "id": row[0],
                "timestamp": row[1],
                "actor": row[2],
                "actor_type": row[3],
                "action": row[4],
                "resource_type": row[5],
                "resource_id": row[6],
                "request": json.loads(row[7]) if row[7] else None,
                "response": json.loads(row[8]) if row[8] else None,
                "status": row[9],
                "trace_id": row[10],
                "metadata": json.loads(row[11]) if row[11] else None
            })

        return results

    def get_stats(self, days: int = 7) -> dict:
        """
        获取审计统计信息

        Args:
            days: 统计天数

        Returns:
            统计信息
        """
        self._flush_buffer()

        db = next(get_db())
        cursor = db.cursor()

        since = (datetime.now() - timedelta(days=days)).isoformat()

        # 总记录数
        cursor.execute("""
            SELECT COUNT(*) FROM audit_logs WHERE timestamp >= ?
        """, (since,))
        total_count = cursor.fetchone()[0]

        # 按操作类型统计
        cursor.execute("""
            SELECT action, COUNT(*) as count
            FROM audit_logs
            WHERE timestamp >= ?
            GROUP BY action
            ORDER BY count DESC
            LIMIT 10
        """, (since,))
        action_stats = {row[0]: row[1] for row in cursor.fetchall()}

        # 按状态统计
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM audit_logs
            WHERE timestamp >= ?
            GROUP BY status
        """, (since,))
        status_stats = {row[0]: row[1] for row in cursor.fetchall()}

        # 失败操作
        cursor.execute("""
            SELECT action, COUNT(*) as count
            FROM audit_logs
            WHERE timestamp >= ? AND status = 'failure'
            GROUP BY action
            ORDER BY count DESC
            LIMIT 5
        """, (since,))
        failure_stats = {row[0]: row[1] for row in cursor.fetchall()}

        return {
            "total_count": total_count,
            "action_stats": action_stats,
            "status_stats": status_stats,
            "failure_stats": failure_stats,
            "period_days": days
        }


# 全局审计日志实例
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """获取审计日志单例实例"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


# 便捷函数
def log_audit(
    actor: str,
    action: str,
    status: str,
    **kwargs
) -> str:
    """
    便捷审计日志记录函数

    用法:
        from db.audit import log_audit
        log_audit(
            actor="user_123",
            action="match_swipe",
            status="success",
            resource_type="match",
            resource_id="match_456"
        )
    """
    return get_audit_logger().log(actor=actor, action=action, status=status, **kwargs)


# 应用启动时初始化
def init_audit():
    """初始化审计日志系统"""
    create_audit_table()
    get_audit_logger()  # 初始化单例
    logger.info("Audit logging system initialized")