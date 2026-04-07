"""
数据库初始化脚本。

用法:
    python db_init.py

功能:
1. 创建所有数据库表
2. 创建索引
3. 插入初始数据（可选）
"""
import asyncio
import sys
from pathlib import Path

# 添加父目录到路径，以便导入模块
sys.path.insert(0, str(Path(__file__).parent))

from database import engine, Base
from models.db_models import (
    TaskDB,
    PaymentTransactionDB,
    WalletDB,
    AntiCheatHashDB,
    WorkerSubmissionDB,
    WorkerProfileDB,
)


async def init_database():
    """初始化数据库表结构。"""
    print("正在创建数据库表...")

    async with engine.begin() as conn:
        # 创建所有表
        await conn.run_sync(Base.metadata.create_all)

    print("数据库表创建完成！")

    # 验证表是否存在
    async with engine.connect() as conn:
        result = await conn.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
        )
        tables = result.fetchall()
        print(f"当前数据库中的表：{[t[0] for t in tables]}")


async def main():
    """主函数。"""
    try:
        await init_database()
        print("\n数据库初始化完成！")
    except Exception as e:
        print(f"\n数据库初始化失败：{e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
