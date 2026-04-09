#!/usr/bin/env python3
"""
数据库迁移脚本执行工具

用法:
    python scripts/migrations/run_migrations.py

功能:
    1. 自动发现 migrations 目录下的 SQL 迁移文件
    2. 按顺序执行未执行的迁移
    3. 记录已执行的迁移历史
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / 'src'))

from sqlalchemy import create_engine, text

# 使用绝对路径连接数据库，避免相对路径导致的数据库文件不一致问题
DB_PATH = PROJECT_ROOT / 'matchmaker_agent.db'
engine = create_engine(f'sqlite:///{DB_PATH}')


def get_migration_table_sql():
    """创建迁移历史表的 SQL"""
    return """
    CREATE TABLE IF NOT EXISTS migration_history (
        id VARCHAR(36) PRIMARY KEY,
        migration_name VARCHAR(255) NOT NULL UNIQUE,
        executed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        success BOOLEAN DEFAULT TRUE,
        error_message TEXT
    )
    """


def get_executed_migrations_sql():
    """获取已执行的迁移列表"""
    return "SELECT migration_name FROM migration_history WHERE success = TRUE ORDER BY executed_at"


def record_migration_sql(migration_name: str, success: bool, error_message: str = None):
    """记录迁移执行结果"""
    import uuid
    migration_id = str(uuid.uuid4())
    if error_message:
        # 转义单引号
        error_message = error_message.replace("'", "''")
        return f"""
        INSERT INTO migration_history (id, migration_name, success, error_message)
        VALUES ('{migration_id}', '{migration_name}', {str(success).lower()}, '{error_message}')
        """
    else:
        return f"""
        INSERT INTO migration_history (id, migration_name, success)
        VALUES ('{migration_id}', '{migration_name}', {str(success).lower()})
        """


def run_migrations():
    """执行所有迁移"""
    migrations_dir = Path(__file__).parent
    migration_files = sorted(migrations_dir.glob('*.sql'))

    # 排除 run_migrations.py 自己
    migration_files = [f for f in migration_files if not f.name.startswith('run_')]

    if not migration_files:
        print("未找到迁移文件")
        return

    print(f"找到 {len(migration_files)} 个迁移文件:")
    for f in migration_files:
        print(f"  - {f.name}")

    with engine.connect() as conn:
        # 创建迁移历史表
        conn.execute(text(get_migration_table_sql()))
        conn.commit()

        # 获取已执行的迁移
        result = conn.execute(text(get_executed_migrations_sql()))
        executed_migrations = {row[0] for row in result.fetchall()}

        print(f"\n已执行的迁移：{len(executed_migrations)}")

        # 执行未执行的迁移
        pending_migrations = [f for f in migration_files if f.name not in executed_migrations]

        if not pending_migrations:
            print("\n所有迁移已执行")
            return

        print(f"\n待执行的迁移：{len(pending_migrations)}")

        for migration_file in pending_migrations:
            print(f"\n执行迁移：{migration_file.name}")

            try:
                # 读取 SQL 文件
                with open(migration_file, 'r', encoding='utf-8') as f:
                    sql_content = f.read()

                # SQLite 不支持一次执行多条语句，需要按分号分割
                # 移除注释行，分割成单独的语句
                statements = []
                current_statement = []
                for line in sql_content.split('\n'):
                    stripped = line.strip()
                    # 跳过注释行和空行
                    if stripped.startswith('--') or not stripped:
                        continue
                    current_statement.append(line)
                    if ';' in line:
                        full_statement = '\n'.join(current_statement).strip()
                        if full_statement and full_statement != ';':
                            statements.append(full_statement)
                        current_statement = []

                # 执行每条语句
                for stmt in statements:
                    conn.execute(text(stmt))
                conn.commit()

                # 记录成功
                conn.execute(text(record_migration_sql(migration_file.name, True)))
                conn.commit()

                print(f"  ✓ {migration_file.name} 执行成功")

            except Exception as e:
                # 记录失败
                conn.execute(text(record_migration_sql(migration_file.name, False, str(e))))
                conn.rollback()

                print(f"  ✗ {migration_file.name} 执行失败：{e}")
                print("\n迁移过程中断，请修复错误后重新执行")
                return

        print("\n所有迁移执行完成!")


if __name__ == '__main__':
    run_migrations()
