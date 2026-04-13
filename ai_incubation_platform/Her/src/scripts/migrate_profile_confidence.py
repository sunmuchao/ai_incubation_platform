"""
用户置信度评估系统数据库迁移脚本
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from db.database import engine, SessionLocal
from utils.logger import logger
from datetime import datetime


def run_migration():
    """执行数据库迁移"""
    logger.info("=" * 60)
    logger.info("Profile Confidence System Migration")
    logger.info("=" * 60)

    db = SessionLocal()

    try:
        # 1. 创建 profile_confidence_details 表
        logger.info("Creating profile_confidence_details table...")
        create_table_1 = """
            CREATE TABLE IF NOT EXISTS profile_confidence_details (
                id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(36) NOT NULL UNIQUE,
                overall_confidence FLOAT DEFAULT 0.3 NOT NULL,
                confidence_level VARCHAR(20) DEFAULT 'medium',
                identity_confidence FLOAT DEFAULT 0.0,
                cross_validation_confidence FLOAT DEFAULT 0.0,
                behavior_consistency FLOAT DEFAULT 0.0,
                social_endorsement FLOAT DEFAULT 0.0,
                time_accumulation FLOAT DEFAULT 0.0,
                cross_validation_flags TEXT DEFAULT '{}',
                cross_validation_passed TEXT DEFAULT '[]',
                cross_validation_score_breakdown TEXT DEFAULT '{}',
                interest_consistency_detail TEXT DEFAULT '{}',
                personality_consistency_detail TEXT DEFAULT '{}',
                invite_source_type VARCHAR(50),
                inviter_id VARCHAR(36),
                positive_feedback_rate FLOAT DEFAULT 0.5,
                account_age_days INTEGER DEFAULT 0,
                active_days INTEGER DEFAULT 0,
                profile_completeness_pct FLOAT DEFAULT 0.0,
                last_evaluated_at TIMESTAMP,
                evaluation_version VARCHAR(20) DEFAULT 'v1.0',
                confidence_history TEXT DEFAULT '[]',
                recommended_verifications TEXT DEFAULT '[]',
                completed_verifications TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """
        db.execute(text(create_table_1))
        db.commit()
        logger.info("profile_confidence_details table created")

        # 2. 创建索引
        logger.info("Creating indexes...")
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_confidence_user_id ON profile_confidence_details(user_id)"))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_confidence_level ON profile_confidence_details(confidence_level)"))
        db.commit()
        logger.info("Indexes created")

        # 3. 创建 cross_validation_rules 表
        logger.info("Creating cross_validation_rules table...")
        create_table_2 = """
            CREATE TABLE IF NOT EXISTS cross_validation_rules (
                id VARCHAR(36) PRIMARY KEY,
                rule_key VARCHAR(100) NOT NULL UNIQUE,
                rule_name VARCHAR(200) NOT NULL,
                rule_description TEXT,
                rule_type VARCHAR(50) NOT NULL,
                rule_weight FLOAT DEFAULT 1.0,
                rule_config TEXT DEFAULT '{}',
                anomaly_threshold FLOAT DEFAULT 0.7,
                anomaly_severity_levels TEXT DEFAULT '{}',
                is_active BOOLEAN DEFAULT TRUE,
                version VARCHAR(20) DEFAULT 'v1.0',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        db.execute(text(create_table_2))
        db.commit()
        logger.info("cross_validation_rules table created")

        # 4. 创建 confidence_evaluation_logs 表
        logger.info("Creating confidence_evaluation_logs table...")
        create_table_3 = """
            CREATE TABLE IF NOT EXISTS confidence_evaluation_logs (
                id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(36) NOT NULL,
                trigger_source VARCHAR(50) NOT NULL,
                confidence_before FLOAT,
                confidence_after FLOAT NOT NULL,
                confidence_change FLOAT,
                dimension_changes TEXT DEFAULT '{}',
                evaluation_details TEXT DEFAULT '{}',
                evaluation_time_ms INTEGER,
                evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """
        db.execute(text(create_table_3))
        db.commit()
        logger.info("confidence_evaluation_logs table created")

        # 5. 创建 verification_suggestions 表
        logger.info("Creating verification_suggestions table...")
        create_table_4 = """
            CREATE TABLE IF NOT EXISTS verification_suggestions (
                id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(36) NOT NULL,
                suggestion_type VARCHAR(50) NOT NULL,
                priority VARCHAR(20) DEFAULT 'medium',
                estimated_confidence_boost FLOAT DEFAULT 0.0,
                reason TEXT,
                status VARCHAR(20) DEFAULT 'pending',
                user_feedback TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """
        db.execute(text(create_table_4))
        db.commit()
        logger.info("verification_suggestions table created")

        # 6. 初始化默认交叉验证规则
        logger.info("Initializing default cross validation rules...")
        default_rules = [
            {
                "id": "rule-age-education-001",
                "rule_key": "age_education_match",
                "rule_name": "年龄与学历匹配验证",
                "rule_description": "验证用户年龄与学历毕业年份是否逻辑一致",
                "rule_type": "logic_check",
                "rule_weight": 1.0,
                "rule_config": '{"expected_graduation_age": {"high_school": 18, "college": 20, "bachelor": 22, "master": 25, "phd": 28}}',
            },
            {
                "id": "rule-occupation-income-001",
                "rule_key": "occupation_income_match",
                "rule_name": "职业与收入匹配验证",
                "rule_description": "验证用户职业与收入范围是否合理",
                "rule_type": "statistical_check",
                "rule_weight": 0.8,
                "rule_config": '{"income_ranges": {"student": [0, 10], "tech": [10, 100], "finance": [15, 200]}}',
            },
            {
                "id": "rule-location-activity-001",
                "rule_key": "location_activity_match",
                "rule_name": "地理与活跃时间匹配验证",
                "rule_description": "验证用户地理位置与活跃时间是否一致",
                "rule_type": "behavior_check",
                "rule_weight": 0.5,
                "rule_config": '{}',
            },
        ]

        for rule in default_rules:
            existing = db.execute(text(
                "SELECT id FROM cross_validation_rules WHERE rule_key = :rule_key"
            ), {"rule_key": rule["rule_key"]}).fetchone()

            if not existing:
                insert_sql = """
                    INSERT INTO cross_validation_rules
                    (id, rule_key, rule_name, rule_description, rule_type, rule_weight, rule_config)
                    VALUES (:id, :rule_key, :rule_name, :rule_description, :rule_type, :rule_weight, :rule_config)
                """
                db.execute(text(insert_sql), rule)
                logger.info(f"Inserted rule: {rule['rule_key']}")

        db.commit()
        logger.info("Default rules initialized")

        # 7. 更新 users 表（添加置信度字段）
        logger.info("Updating users table...")
        try:
            db.execute(text("ALTER TABLE users ADD COLUMN profile_confidence FLOAT DEFAULT 0.3"))
            db.commit()
            logger.info("Added profile_confidence column to users table")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                logger.info("profile_confidence column already exists")
            else:
                logger.warning(f"Could not add profile_confidence column: {e}")

        logger.info("=" * 60)
        logger.info("Migration completed successfully!")
        logger.info(f"Completed at: {datetime.now().isoformat()}")
        logger.info("=" * 60)

        return True

    except Exception as e:
        db.rollback()
        logger.error(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        db.close()


if __name__ == "__main__":
    success = run_migration()
    if success:
        print("\nMigration completed successfully!")
    else:
        print("\nMigration failed. Check logs for details.")