"""
候选人反馈表迁移脚本

创建两张表：
1. candidate_feedbacks - 候选人反馈记录
2. feedback_statistics - 反馈统计汇总

执行方式：
    python scripts/migrations/create_feedback_tables.py

版本：v1.0
"""
import sys
import os

# 确保 Her 项目根目录在路径中
her_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
src_path = os.path.join(her_root, "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from utils.db_session_manager import db_session
from db.database import engine, Base
from db.models import CandidateFeedbackDB, FeedbackStatisticsDB


def create_feedback_tables():
    """创建候选人反馈相关表"""

    print("=" * 60)
    print("创建候选人反馈表")
    print("=" * 60)

    # 创建表
    try:
        Base.metadata.create_all(
            engine,
            tables=[CandidateFeedbackDB.__table__, FeedbackStatisticsDB.__table__]
        )
        print("✅ 表创建成功！")
        print(f"   - candidate_feedbacks")
        print(f"   - feedback_statistics")
    except Exception as e:
        print(f"❌ 表创建失败：{e}")
        return False

    # 验证表是否存在
    try:
        with db_session() as db:
            # 尝试查询，验证表已创建
            db.execute("SELECT 1 FROM candidate_feedbacks LIMIT 1")
            db.execute("SELECT 1 FROM feedback_statistics LIMIT 1")
        print("✅ 表验证成功！")
    except Exception as e:
        print(f"⚠️ 表验证警告：{e}")

    return True


def drop_feedback_tables():
    """删除候选人反馈相关表（用于回滚）"""

    print("=" * 60)
    print("删除候选人反馈表")
    print("=" * 60)

    try:
        Base.metadata.drop_all(
            engine,
            tables=[CandidateFeedbackDB.__table__, FeedbackStatisticsDB.__table__]
        )
        print("✅ 表删除成功！")
    except Exception as e:
        print(f"❌ 表删除失败：{e}")
        return False

    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="候选人反馈表迁移脚本")
    parser.add_argument("--drop", action="store_true", help="删除表（回滚）")
    args = parser.parse_args()

    if args.drop:
        drop_feedback_tables()
    else:
        create_feedback_tables()