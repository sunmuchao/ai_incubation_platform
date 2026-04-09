# 数据库迁移脚本
# 用途：从 SQLite 迁移到 PostgreSQL
# 使用方法：
#   python scripts/migrate_sqlite_to_postgres.py

import os
import sys
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.orm import sessionmaker
import warnings

# 添加 src 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from config import settings
from utils.logger import logger


def migrate_database():
    """
    将 SQLite 数据库迁移到 PostgreSQL

    步骤：
    1. 读取当前 SQLite 数据库
    2. 连接到目标 PostgreSQL 数据库
    3. 创建所有表
    4. 迁移数据
    """
    # 获取源数据库（SQLite）路径
    sqlite_url = os.getenv("SQLITE_DATABASE_URL", "sqlite:///./matchmaker_agent.db")

    # 获取目标数据库（PostgreSQL）URL
    postgres_url = os.getenv("DATABASE_URL")

    if not postgres_url:
        print("错误：请设置 DATABASE_URL 环境变量指向 PostgreSQL 数据库")
        print("示例：DATABASE_URL=postgresql://user:password@localhost:5432/matchmaker")
        sys.exit(1)

    print(f"源数据库：{sqlite_url}")
    print(f"目标数据库：{postgres_url}")
    print("\n开始迁移...")

    # 创建数据库引擎
    sqlite_engine = create_engine(sqlite_url)
    postgres_engine = create_engine(postgres_url)

    # 创建会话
    SQLiteSession = sessionmaker(bind=sqlite_engine)
    PostgresSession = sessionmaker(bind=postgres_engine)

    sqlite_session = SQLiteSession()
    postgres_session = PostgresSession()

    try:
        # 从 SQLite 读取所有表
        metadata = MetaData()
        metadata.reflect(bind=sqlite_engine)

        # 在 PostgreSQL 中创建所有表
        print("\n在 PostgreSQL 中创建表...")
        metadata.create_all(postgres_engine)
        print("表创建完成")

        # 迁移每个表的数据
        for table_name, table in metadata.tables.items():
            if table_name == 'alembic_version':
                continue  # 跳过迁移版本表

            print(f"\n迁移表：{table_name}")

            # 从 SQLite 读取所有数据
            rows = sqlite_session.query(table).all()
            print(f"  读取 {len(rows)} 行数据")

            # 插入到 PostgreSQL
            for row in rows:
                # 将行数据转换为字典
                row_dict = {c.name: getattr(row, c.name) for c in table.columns}
                postgres_session.execute(table.insert().values(**row_dict))

            print(f"  插入 {len(rows)} 行数据完成")

        # 提交事务
        postgres_session.commit()
        print("\n迁移完成!")

        # 验证数据
        postgres_metadata = MetaData()
        postgres_metadata.reflect(bind=postgres_engine)

        print("\n数据验证:")
        for table_name in metadata.tables.keys():
            if table_name == 'alembic_version':
                continue
            count = postgres_session.query(postgres_metadata.tables[table_name]).count()
            print(f"  {table_name}: {count} 行")

    except Exception as e:
        postgres_session.rollback()
        print(f"\n迁移失败：{e}")
        raise
    finally:
        sqlite_session.close()
        postgres_session.close()


if __name__ == "__main__":
    print("=" * 60)
    print("SQLite 到 PostgreSQL 迁移工具")
    print("=" * 60)

    # 确认迁移
    response = input("\n警告：此操作将数据迁移到 PostgreSQL。继续？(yes/no): ")
    if response.lower() != 'yes':
        print("迁移已取消")
        sys.exit(0)

    migrate_database()
