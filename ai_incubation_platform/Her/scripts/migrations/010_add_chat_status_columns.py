#!/usr/bin/env python3
"""
迁移脚本 010: 为聊天表添加 status 列

功能:
1. 为 chat_messages 表添加 status 列（消息状态：sent/delivered/read/recalled）
2. 为 chat_conversations 表添加 status 列（会话状态：active/archived/block）
3. 检查列是否存在，不存在才添加（幂等性）
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
        print(f"  ⊙ {table_name}.{column_name} 已存在，跳过")
        return True

    sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
    if default_value:
        sql += f" DEFAULT '{default_value}'"

    try:
        with engine.connect() as conn:
            conn.execute(text(sql))
            conn.commit()
        print(f"  ✓ {table_name}.{column_name} 添加成功")
        return True
    except Exception as e:
        print(f"  ✗ {table_name}.{column_name} 添加失败：{e}")
        return False


def run_migration():
    """执行迁移"""
    print("=" * 50)
    print("迁移脚本 010: 为聊天表添加 status 列")
    print("=" * 50)

    # 检查表是否存在
    existing_tables = inspect(engine).get_table_names()

    print("\n检查现有表...")
    print(f"现有表：{existing_tables}")

    # 处理 chat_messages 表
    if 'chat_messages' in existing_tables:
        print("\n===== chat_messages 表 =====")
        add_column_if_not_exists('chat_messages', 'status', 'VARCHAR(20)', 'sent')
    else:
        print("\n⚠️ chat_messages 表不存在，跳过")

    # 处理 chat_conversations 表
    if 'chat_conversations' in existing_tables:
        print("\n===== chat_conversations 表 =====")
        add_column_if_not_exists('chat_conversations', 'status', 'VARCHAR(20)', 'active')
    else:
        print("\n⚠️ chat_conversations 表不存在，跳过")

    print("\n" + "=" * 50)
    print("迁移完成!")
    print("=" * 50)

    # 显示最终列数量
    if 'chat_messages' in existing_tables:
        msg_columns = get_existing_columns('chat_messages')
        print(f"\nchat_messages 表列数：{len(msg_columns)}")

    if 'chat_conversations' in existing_tables:
        conv_columns = get_existing_columns('chat_conversations')
        print(f"\nchat_conversations 表列数：{len(conv_columns)}")

    return True


if __name__ == '__main__':
    run_migration()