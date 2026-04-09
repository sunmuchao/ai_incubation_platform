"""
数据库迁移脚本 - 添加 sexual_orientation 字段

用途：为现有 users 表添加 sexual_orientation 列
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import get_db, engine
from sqlalchemy import text

def migrate():
    """执行数据库迁移"""
    print("开始数据库迁移：添加 sexual_orientation 字段...")

    # 检查列是否已存在
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT name FROM pragma_table_info('users')
            WHERE name='sexual_orientation'
        """))

        if result.fetchone():
            print("✓ sexual_orientation 列已存在，无需迁移")
            return

        # 列不存在，执行添加
        print("添加 sexual_orientation 列到 users 表...")
        conn.execute(text("""
            ALTER TABLE users
            ADD COLUMN sexual_orientation VARCHAR(20) DEFAULT 'heterosexual'
        """))
        conn.commit()
        print("✓ sexual_orientation 列添加成功！")
        print("  - 默认值：heterosexual (异性恋)")
        print("  - 可选值：heterosexual, homosexual, bisexual")

if __name__ == "__main__":
    migrate()
