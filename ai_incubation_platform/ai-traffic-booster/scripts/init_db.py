#!/usr/bin/env python3
"""
数据库初始化脚本 - P0 数据持久化

功能:
1. 创建 PostgreSQL 数据库和表
2. 创建索引
3. 初始化基础数据
4. 支持 SQLAlchemy Alembic 迁移

用法:
    python scripts/init_db.py
    python scripts/init_db.py --env production
    python scripts/init_db.py --drop-first
"""
import sys
import os
import argparse
from datetime import datetime

# 添加 src 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from sqlalchemy import text
from core.config import settings
from db import Base, init_db, get_postgresql_models, get_postgresql_config
from db.postgresql_config import db_manager, init_database
from db.postgresql_models import (
    FunnelModel, FunnelStepModel,
    SegmentModel,
    CompetitorModel,
    AlertModel,
)
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='数据库初始化脚本')
    parser.add_argument('--env', type=str, default='development',
                        choices=['development', 'staging', 'production'],
                        help='运行环境')
    parser.add_argument('--drop-first', action='store_true',
                        help='是否先删除现有表')
    parser.add_argument('--create-extensions', action='store_true',
                        help='是否创建 PostgreSQL 扩展 (pg_trgm, uuid-ossp)')
    return parser.parse_args()


def create_postgresql_extensions(session):
    """创建 PostgreSQL 扩展"""
    logger.info("Creating PostgreSQL extensions...")

    # 启用模糊匹配扩展
    try:
        session.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))
        logger.info("  - pg_trgm extension created")
    except Exception as e:
        logger.warning(f"  - pg_trgm extension failed: {e}")

    # 启用 UUID 扩展
    try:
        session.execute(text("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"))
        logger.info("  - uuid-ossp extension created")
    except Exception as e:
        logger.warning(f"  - uuid-ossp extension failed: {e}")

    session.commit()


def create_indexes(session):
    """创建额外的数据库索引"""
    logger.info("Creating database indexes...")

    # Events 表的分区索引 (PostgreSQL 10+)
    # 注意：分区需要在表创建时指定，这里仅创建辅助索引
    indexes = [
        # Event 表索引
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_events_timestamp_date ON events (DATE(timestamp))",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_events_event_type_name ON events (event_type, event_name)",

        # Traffic 表索引
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_traffic_date_hour ON traffic_data_enhanced (date, hour)",

        # Keyword 表索引
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_rankings_tracked_at_date ON keyword_rankings (DATE(tracked_at))",

        # Competitor 表索引
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_competitor_metrics_date_only ON competitor_metrics (DATE(date))",
    ]

    for sql in indexes:
        try:
            session.execute(text(sql))
            logger.info(f"  Index created: {sql.split('idx_')[1].split(' ')[0] if 'idx_' in sql else 'unknown'}")
        except Exception as e:
            logger.warning(f"  Index creation failed: {sql[:50]}... - {e}")

    session.commit()


def initialize_default_data(session):
    """初始化默认数据"""
    logger.info("Initializing default data...")

    # 创建预定义漏斗模板
    default_funnels = [
        {
            "id": "funnel_template_1",
            "name": "电商购买转化漏斗",
            "description": "标准的电商购买流程分析",
            "is_template": True,
            "steps": [
                ("step_1", "查看商品", 1, "page_view"),
                ("step_2", "加入购物车", 2, "add_to_cart"),
                ("step_3", "开始结算", 3, "begin_checkout"),
                ("step_4", "完成购买", 4, "purchase"),
            ]
        },
        {
            "id": "funnel_template_2",
            "name": "SaaS 注册转化漏斗",
            "description": "SaaS 产品用户注册流程分析",
            "is_template": True,
            "steps": [
                ("step_1", "访问首页", 1, "page_view"),
                ("step_2", "点击注册", 2, "click_signup"),
                ("step_3", "填写表单", 3, "form_submit"),
                ("step_4", "验证邮箱", 4, "verify_email"),
            ]
        },
        {
            "id": "funnel_template_3",
            "name": "内容互动漏斗",
            "description": "内容网站用户互动流程分析",
            "is_template": True,
            "steps": [
                ("step_1", "阅读文章", 1, "page_view"),
                ("step_2", "点赞/收藏", 2, "like_or_bookmark"),
                ("step_3", "发表评论", 3, "comment"),
                ("step_4", "分享内容", 4, "share"),
            ]
        },
    ]

    for funnel_data in default_funnels:
        existing = session.query(FunnelModel).filter(FunnelModel.id == funnel_data["id"]).first()
        if not existing:
            funnel = FunnelModel(
                id=funnel_data["id"],
                funnel_name=funnel_data["name"],
                description=funnel_data["description"],
                is_template=funnel_data["is_template"],
                is_active=True,
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2030, 12, 31),
            )
            session.add(funnel)
            session.flush()

            for step_id, step_name, step_order, event_name in funnel_data["steps"]:
                step = FunnelStepModel(
                    funnel_id=funnel.id,
                    step_id=step_id,
                    step_name=step_name,
                    step_order=step_order,
                    event_name=event_name,
                )
                session.add(step)

            logger.info(f"  Created funnel template: {funnel_data['name']}")

    # 创建预定义用户分群模板
    default_segments = [
        {
            "id": "segment_template_1",
            "name": "高价值用户",
            "description": "完成购买且消费金额较高的用户",
            "conditions": [{"field": "event_name", "operator": "eq", "value": "purchase"}],
            "logic": "AND",
            "is_template": True,
        },
        {
            "id": "segment_template_2",
            "name": "移动端用户",
            "description": "使用移动设备访问的用户",
            "conditions": [{"field": "device_type", "operator": "eq", "value": "mobile"}],
            "logic": "AND",
            "is_template": True,
        },
        {
            "id": "segment_template_3",
            "name": "新用户",
            "description": "首次访问的用户",
            "conditions": [{"field": "event_name", "operator": "eq", "value": "page_view"}],
            "logic": "AND",
            "is_template": True,
        },
        {
            "id": "segment_template_4",
            "name": "流失风险用户",
            "description": "超过 7 天未访问的用户",
            "conditions": [{"field": "days_since_last_visit", "operator": "gt", "value": 7}],
            "logic": "AND",
            "is_template": True,
        },
    ]

    for segment_data in default_segments:
        existing = session.query(SegmentModel).filter(SegmentModel.id == segment_data["id"]).first()
        if not existing:
            segment = SegmentModel(
                id=segment_data["id"],
                segment_name=segment_data["name"],
                description=segment_data["description"],
                conditions=segment_data["conditions"],
                logic=segment_data["logic"],
                is_template=segment_data["is_template"],
                is_active=True,
            )
            session.add(segment)
            logger.info(f"  Created segment template: {segment_data['name']}")

    session.commit()
    logger.info("Default data initialized")


def verify_database():
    """验证数据库连接和表结构"""
    logger.info("Verifying database connection...")

    try:
        with db_manager.session_scope() as session:
            # 测试查询
            result = session.execute(text("SELECT 1"))
            result.fetchone()
            logger.info("  Database connection: OK")

            # 检查表是否存在
            tables = [
                "events", "funnels", "funnel_steps", "funnel_results",
                "segments", "segment_results",
                "competitors", "competitor_metrics", "competitor_keywords", "competitor_backlinks",
                "traffic_data_enhanced", "keyword_rankings",
                "alerts", "alert_history",
            ]

            for table in tables:
                result = session.execute(text(
                    f"SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '{table}')"
                ))
                exists = result.scalar()
                status = "OK" if exists else "MISSING"
                logger.info(f"  Table '{table}': {status}")

            return True
    except Exception as e:
        logger.error(f"Database verification failed: {e}")
        return False


def main():
    """主函数"""
    args = parse_args()

    logger.info(f"=" * 60)
    logger.info(f"Database Initialization Script")
    logger.info(f"Environment: {args.env}")
    logger.info(f"Database URL: {settings.DATABASE_URL}")
    logger.info(f"=" * 60)

    # 检查是否为 PostgreSQL
    is_postgresql = settings.DATABASE_URL and settings.DATABASE_URL.startswith("postgresql")

    if not is_postgresql:
        logger.warning("Current database is not PostgreSQL. Using SQLite mode.")
        logger.info("For full P0 features, please configure PostgreSQL:")
        logger.info("  DATABASE_URL=postgresql://user:password@localhost:5432/ai_traffic_booster")
        # 继续使用 SQLite 进行初始化
        init_db()
        logger.info("SQLite database initialized")
        return 0

    try:
        # 初始化数据库管理器
        init_database(
            database_url=settings.DATABASE_URL,
            pool_size=settings.DATABASE_POOL_SIZE if hasattr(settings, 'DATABASE_POOL_SIZE') else 20,
            max_overflow=settings.DATABASE_MAX_OVERFLOW if hasattr(settings, 'DATABASE_MAX_OVERFLOW') else 40,
        )

        # 如果需要先删除表
        if args.drop_first:
            logger.warning("Dropping existing tables...")
            Base.metadata.drop_all(bind=db_manager.engine)

        # 创建 PostgreSQL 扩展
        if args.create_extensions:
            with db_manager.session_scope() as session:
                create_postgresql_extensions(session)

        # 创建所有表
        logger.info("Creating database tables...")
        from db import postgresql_models  # 导入模型以注册到 Base
        Base.metadata.create_all(bind=db_manager.engine)
        logger.info("Database tables created")

        # 创建额外索引
        with db_manager.session_scope() as session:
            create_indexes(session)

        # 初始化默认数据
        with db_manager.session_scope() as session:
            initialize_default_data(session)

        # 验证数据库
        verify_database()

        logger.info("=" * 60)
        logger.info("Database initialization completed successfully!")
        logger.info("=" * 60)
        return 0

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
