#!/usr/bin/env python3
"""
迁移脚本 009: 添加 QuickStart 扩展字段和匹配偏好字段

功能:
1. 检查字段是否存在，不存在才添加
2. 支持重复执行（幂等性）
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / 'src'))

from sqlalchemy import create_engine, text, inspect

# 使用绝对路径连接数据库
DB_PATH = PROJECT_ROOT / 'matchmaker_agent.db'
engine = create_engine(f'sqlite:///{DB_PATH}')


def get_existing_columns(table_name: str) -> set:
    """获取表中已存在的列名"""
    inspector = inspect(engine)
    columns = inspector.get_columns(table_name)
    return {col['name'] for col in columns}


def add_column_if_not_exists(table_name: str, column_name: str, column_type: str, default_value: str = None):
    """如果列不存在，则添加列"""
    existing = get_existing_columns(table_name)

    if column_name in existing:
        print(f"  ⊙ {column_name} 已存在，跳过")
        return True

    sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
    if default_value:
        sql += f" DEFAULT {default_value}"

    try:
        with engine.connect() as conn:
            conn.execute(text(sql))
            conn.commit()
        print(f"  ✓ {column_name} 添加成功")
        return True
    except Exception as e:
        print(f"  ✗ {column_name} 添加失败：{e}")
        return False


def create_index_if_not_exists(index_name: str, table_name: str, column_name: str):
    """创建索引（SQLite 支持 IF NOT EXISTS）"""
    sql = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({column_name})"

    try:
        with engine.connect() as conn:
            conn.execute(text(sql))
            conn.commit()
        print(f"  ✓ 索引 {index_name} 创建成功")
        return True
    except Exception as e:
        print(f"  ✗ 索引 {index_name} 创建失败：{e}")
        return False


def run_migration():
    """执行迁移"""
    print("=" * 50)
    print("迁移脚本 009: 添加 QuickStart 扩展字段和匹配偏好字段")
    print("=" * 50)

    # 检查 users 表是否存在
    existing_tables = inspect(engine).get_table_names()
    if 'users' not in existing_tables:
        print("✗ users 表不存在，请先执行基础迁移")
        return False

    print("\n检查 users 表现有列...")
    existing_columns = get_existing_columns('users')
    print(f"现有列数量：{len(existing_columns)}")

    print("\n===== QuickStart 扩展字段 =====")
    add_column_if_not_exists('users', 'height', 'INTEGER')
    add_column_if_not_exists('users', 'has_car', 'BOOLEAN')
    add_column_if_not_exists('users', 'housing', 'VARCHAR(20)')

    print("\n===== 一票否决维度 =====")
    add_column_if_not_exists('users', 'want_children', 'VARCHAR(20)')
    add_column_if_not_exists('users', 'spending_style', 'VARCHAR(20)')

    print("\n===== 核心价值观维度 =====")
    add_column_if_not_exists('users', 'family_importance', 'FLOAT')
    add_column_if_not_exists('users', 'work_life_balance', 'VARCHAR(20)')

    print("\n===== 迁移能力维度 =====")
    add_column_if_not_exists('users', 'migration_willingness', 'FLOAT')
    add_column_if_not_exists('users', 'accept_remote', 'VARCHAR(20)')

    print("\n===== 生活方式维度 =====")
    add_column_if_not_exists('users', 'sleep_type', 'VARCHAR(20)')

    print("\n===== 偏好设置 =====")
    add_column_if_not_exists('users', 'preferred_age_min', 'INTEGER', '18')
    add_column_if_not_exists('users', 'preferred_age_max', 'INTEGER', '60')
    add_column_if_not_exists('users', 'preferred_location', 'VARCHAR(200)')

    print("\n===== 创建索引 =====")
    create_index_if_not_exists('idx_users_want_children', 'users', 'want_children')
    create_index_if_not_exists('idx_users_spending_style', 'users', 'spending_style')
    create_index_if_not_exists('idx_users_accept_remote', 'users', 'accept_remote')
    create_index_if_not_exists('idx_users_preferred_location', 'users', 'preferred_location')

    print("\n" + "=" * 50)
    print("迁移完成!")
    print("=" * 50)

    # 显示最终列数量
    final_columns = get_existing_columns('users')
    print(f"\n最终列数量：{len(final_columns)}")

    return True


if __name__ == '__main__':
    run_migration()