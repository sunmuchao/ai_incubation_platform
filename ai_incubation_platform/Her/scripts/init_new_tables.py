"""
新表初始化脚本

用于在现有数据库中创建新增的表：
- user_behavior_events (用户行为事件)
- user_behavior_daily_stats (用户行为日统计)
- user_reports (用户举报)

使用方法:
    python scripts/init_new_tables.py
"""
import sys
import os

# 添加 src 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from db.database import engine, Base
from services.behavior_log_service import UserBehaviorEventDB, UserBehaviorDailyStatsDB
from services.report_service import UserReportDB
from utils.logger import logger


def init_new_tables():
    """初始化新表"""
    logger.info("Initializing new database tables...")

    # 创建所有表（如果已存在则跳过）
    Base.metadata.create_all(bind=engine)

    logger.info("New tables created successfully:")
    logger.info("  - user_behavior_events")
    logger.info("  - user_behavior_daily_stats")
    logger.info("  - user_reports")

    return True


if __name__ == "__main__":
    try:
        init_new_tables()
        print("✓ Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize tables: {e}")
        print(f"✗ Failed: {e}")
        sys.exit(1)
