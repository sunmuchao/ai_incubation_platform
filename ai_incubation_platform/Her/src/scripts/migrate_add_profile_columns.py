"""
数据库迁移脚本：为 users 表添加画像相关列

执行方式：
    cd Her/src && python scripts/migrate_add_profile_columns.py
"""
import sqlite3
import os

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "matchmaker_agent.db")

# 要添加的新列
NEW_COLUMNS = [
    ("self_profile_json", "TEXT DEFAULT '{}'"),
    ("desire_profile_json", "TEXT DEFAULT '{}'"),
    ("profile_confidence", "REAL DEFAULT 0.3"),
    ("profile_completeness", "REAL DEFAULT 0.0"),
    ("profile_updated_at", "DATETIME NULL"),
]


def migrate():
    """执行迁移"""
    print(f"数据库路径: {DB_PATH}")

    if not os.path.exists(DB_PATH):
        print(f"数据库不存在: {DB_PATH}")
        return False

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 检查现有列
    cursor.execute("PRAGMA table_info(users)")
    existing_columns = {row[1] for row in cursor.fetchall()}
    print(f"现有列: {existing_columns}")

    # 添加新列
    added_count = 0
    for col_name, col_type in NEW_COLUMNS:
        if col_name not in existing_columns:
            try:
                sql = f"ALTER TABLE users ADD COLUMN {col_name} {col_type}"
                print(f"执行: {sql}")
                cursor.execute(sql)
                added_count += 1
                print(f"✅ 已添加列: {col_name}")
            except sqlite3.OperationalError as e:
                print(f"❌ 添加列 {col_name} 失败: {e}")
        else:
            print(f"⏭️ 列已存在: {col_name}")

    conn.commit()
    conn.close()

    print(f"\n迁移完成，新增 {added_count} 个列")
    return True


if __name__ == "__main__":
    migrate()