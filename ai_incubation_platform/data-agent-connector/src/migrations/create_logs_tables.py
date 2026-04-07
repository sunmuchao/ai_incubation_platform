"""
数据库迁移脚本 - 日志持久化与审计系统

创建审计日志、查询日志、访问日志相关表
"""
import sqlite3
from pathlib import Path
from datetime import datetime


def get_db_path() -> str:
    """获取数据库文件路径"""
    data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(exist_ok=True)
    return str(data_dir / "connector.db")


def create_logs_tables(db_path: str):
    """创建日志表"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 创建审计日志表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            tenant_id TEXT NOT NULL,
            user_id TEXT,
            action_type TEXT NOT NULL,
            resource_type TEXT,
            resource_id TEXT,
            request_method TEXT,
            request_path TEXT,
            request_body TEXT,
            response_status INTEGER,
            response_body TEXT,
            ip_address TEXT,
            user_agent TEXT,
            connector_name TEXT,
            query_id TEXT,
            metadata TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 创建审计日志索引
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_logs_tenant ON audit_logs(tenant_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs(user_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action_type)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_logs_resource ON audit_logs(resource_type, resource_id)
    """)

    # 创建查询日志表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS query_logs (
            id TEXT PRIMARY KEY,
            query_id TEXT NOT NULL,
            datasource TEXT NOT NULL,
            sql TEXT NOT NULL,
            connector_name TEXT NOT NULL,
            tenant_id TEXT NOT NULL,
            user_id TEXT,
            duration_ms REAL DEFAULT 0,
            result_rows INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending',
            error_message TEXT,
            rows_returned INTEGER DEFAULT 0,
            bytes_processed INTEGER DEFAULT 0,
            metadata TEXT,
            timestamp TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 创建查询日志索引
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_query_logs_timestamp ON query_logs(timestamp)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_query_logs_datasource ON query_logs(datasource)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_query_logs_status ON query_logs(status)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_query_logs_user ON query_logs(user_id)
    """)

    # 创建访问日志表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS access_logs (
            id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            tenant_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            resource TEXT NOT NULL,
            action TEXT NOT NULL,
            granted INTEGER NOT NULL,
            reason TEXT,
            ip_address TEXT,
            metadata TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 创建访问日志索引
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_access_logs_timestamp ON access_logs(timestamp)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_access_logs_tenant ON access_logs(tenant_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_access_logs_user ON access_logs(user_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_access_logs_granted ON access_logs(granted)
    """)

    # 创建日志保留策略表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS log_retention_policies (
            id TEXT PRIMARY KEY,
            log_type TEXT NOT NULL UNIQUE,
            retention_days INTEGER NOT NULL,
            storage_backend TEXT NOT NULL,
            compression_enabled INTEGER DEFAULT 1,
            export_enabled INTEGER DEFAULT 0,
            export_destination TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 插入默认保留策略
    default_policies = [
        ("policy_audit", "audit", 365, "database", 1, 0, None),
        ("policy_query", "query", 90, "database", 1, 0, None),
        ("policy_access", "access", 180, "database", 1, 0, None)
    ]

    for policy in default_policies:
        cursor.execute("""
            INSERT OR IGNORE INTO log_retention_policies
            (id, log_type, retention_days, storage_backend, compression_enabled, export_enabled, export_destination, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, policy + (datetime.utcnow().isoformat(), datetime.utcnow().isoformat()))

    # 创建日志导出任务表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS log_export_jobs (
            id TEXT PRIMARY KEY,
            log_type TEXT NOT NULL,
            time_range_start TEXT NOT NULL,
            time_range_end TEXT NOT NULL,
            format TEXT DEFAULT 'json',
            destination TEXT,
            tenant_id TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            error_message TEXT,
            file_path TEXT,
            file_size_bytes INTEGER DEFAULT 0,
            record_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            completed_at TEXT
        )
    """)

    conn.commit()
    conn.close()

    print(f"Logs tables created successfully in {db_path}")


if __name__ == "__main__":
    db_path = get_db_path()
    create_logs_tables(db_path)
