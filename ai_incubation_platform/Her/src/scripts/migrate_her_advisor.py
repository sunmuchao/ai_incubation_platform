"""
数据库迁移脚本 - Her 顾问系统

创建双向画像、认知偏差分析、匹配建议相关数据表

Her 的专业知识源于 LLM 内在能力（20年专业顾问人设）
不需要数据库存储案例
"""
from sqlalchemy import create_engine, text
from db.database import engine, Base
from utils.logger import logger
import os


def migrate_her_advisor_tables():
    """
    创建 Her 顾问系统相关数据表

    表：
    - user_profiles: 双向画像存储
    - profile_update_history: 画像更新历史
    - cognitive_bias_analyses: 认知偏差分析记录
    - match_advices: 匹配建议记录
    - user_behavior_events_v2: 用户行为事件（增强版）
    - conversation_preference_inferences: 对话偏好推断
    """
    logger.info("开始 Her 顾问系统数据库迁移...")

    # 导入新模型
    from models.her_advisor_models import (
        UserProfileDB,
        ProfileUpdateHistoryDB,
        CognitiveBiasAnalysisDB,
        MatchAdviceDB,
        UserBehaviorEventDB,
        ConversationPreferenceInferenceDB,
    )

    # 创建表（不包括 HerKnowledgeCaseDB，Her 知识源自 LLM）
    try:
        Base.metadata.create_all(bind=engine, tables=[
            UserProfileDB.__table__,
            ProfileUpdateHistoryDB.__table__,
            CognitiveBiasAnalysisDB.__table__,
            MatchAdviceDB.__table__,
            UserBehaviorEventDB.__table__,
            ConversationPreferenceInferenceDB.__table__,
        ])
        logger.info("Her 顾问系统数据表创建成功")
        return True
    except Exception as e:
        logger.error(f"Her 顾问系统数据表创建失败: {e}")
        return False


def run_migration():
    """执行完整迁移"""
    logger.info("=" * 50)
    logger.info("Her 顾问系统数据库迁移")
    logger.info("=" * 50)

    # 1. 创建数据表（仅结构，不初始化案例）
    success = migrate_her_advisor_tables()

    # Her 的专业知识源于 LLM 自身知识库 + 精心设计的 Prompt
    # 不需要数据库存储案例

    logger.info("=" * 50)
    logger.info("迁移完成（Her 知识源自 LLM 内在能力）")
    logger.info("=" * 50)

    return success


# 为了向后兼容，导入 json
import json


if __name__ == "__main__":
    run_migration()