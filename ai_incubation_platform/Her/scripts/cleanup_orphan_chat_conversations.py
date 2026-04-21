"""
聊天脏会话治理脚本

目标：
- 识别 chat_conversations 中引用了不存在用户的会话（孤儿会话）
- 默认仅做安全治理：将会话状态标记为 orphaned，并清空未读计数
- 支持可选硬删除模式（危险操作，需显式指定）

用法：
  # 仅预览，不改数据库
  python scripts/cleanup_orphan_chat_conversations.py --dry-run

  # 执行安全治理（推荐）
  python scripts/cleanup_orphan_chat_conversations.py --apply

  # 执行硬删除（谨慎）
  python scripts/cleanup_orphan_chat_conversations.py --apply --delete
"""

import argparse
import os
import sys
from collections import Counter
from typing import Dict, List, Tuple

from sqlalchemy.orm import Session, aliased

# 添加 src 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from db.database import SessionLocal  # noqa: E402
from db.models import ChatConversationDB, UserDB  # noqa: E402


def find_orphan_conversations(db: Session) -> List[Tuple[ChatConversationDB, bool, bool]]:
    """查找孤儿会话：user_id_1/user_id_2 任一不存在。"""
    user1 = aliased(UserDB)
    user2 = aliased(UserDB)

    rows = (
        db.query(ChatConversationDB, user1.id, user2.id)
        .outerjoin(user1, ChatConversationDB.user_id_1 == user1.id)
        .outerjoin(user2, ChatConversationDB.user_id_2 == user2.id)
        .all()
    )

    result: List[Tuple[ChatConversationDB, bool, bool]] = []
    for conv, user1_id, user2_id in rows:
        missing_user1 = user1_id is None
        missing_user2 = user2_id is None
        if missing_user1 or missing_user2:
            result.append((conv, missing_user1, missing_user2))
    return result


def summarize(orphan_rows: List[Tuple[ChatConversationDB, bool, bool]]) -> Dict[str, int]:
    """聚合统计信息。"""
    counter = Counter()
    for _, missing_user1, missing_user2 in orphan_rows:
        if missing_user1 and missing_user2:
            counter["both_missing"] += 1
        elif missing_user1:
            counter["missing_user_1"] += 1
        elif missing_user2:
            counter["missing_user_2"] += 1
    counter["total"] = len(orphan_rows)
    return dict(counter)


def apply_safe_cleanup(db: Session, orphan_rows: List[Tuple[ChatConversationDB, bool, bool]]) -> int:
    """
    安全治理策略：
    - status -> orphaned
    - unread_count_user1/unread_count_user2 -> 0
    """
    updated = 0
    for conv, _, _ in orphan_rows:
        conv.status = "orphaned"
        conv.unread_count_user1 = 0
        conv.unread_count_user2 = 0
        updated += 1
    return updated


def apply_hard_delete(db: Session, orphan_rows: List[Tuple[ChatConversationDB, bool, bool]]) -> int:
    """硬删除孤儿会话（危险）。"""
    deleted = 0
    for conv, _, _ in orphan_rows:
        db.delete(conv)
        deleted += 1
    return deleted


def main() -> int:
    parser = argparse.ArgumentParser(description="治理聊天孤儿会话")
    parser.add_argument("--dry-run", action="store_true", help="仅预览，不改数据库")
    parser.add_argument("--apply", action="store_true", help="执行治理")
    parser.add_argument("--delete", action="store_true", help="配合 --apply 使用，执行硬删除")
    parser.add_argument("--limit", type=int, default=20, help="预览样本条数（默认 20）")
    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        print("请指定 --dry-run 或 --apply")
        return 1

    db = SessionLocal()
    try:
        orphan_rows = find_orphan_conversations(db)
        summary = summarize(orphan_rows)

        print("=== 孤儿会话扫描结果 ===")
        print(f"total={summary.get('total', 0)}")
        print(f"missing_user_1={summary.get('missing_user_1', 0)}")
        print(f"missing_user_2={summary.get('missing_user_2', 0)}")
        print(f"both_missing={summary.get('both_missing', 0)}")
        print("")

        if orphan_rows:
            print(f"=== 样本（前 {min(args.limit, len(orphan_rows))} 条）===")
            for conv, missing_user1, missing_user2 in orphan_rows[: args.limit]:
                print(
                    f"id={conv.id} user_id_1={conv.user_id_1} user_id_2={conv.user_id_2} "
                    f"status={conv.status} missing_user_1={missing_user1} missing_user_2={missing_user2}"
                )
            print("")

        if args.dry_run:
            print("Dry run 完成：未对数据库做任何修改。")
            return 0

        if not orphan_rows:
            print("无需治理：未发现孤儿会话。")
            return 0

        if args.delete:
            changed = apply_hard_delete(db, orphan_rows)
            action = "hard_delete"
        else:
            changed = apply_safe_cleanup(db, orphan_rows)
            action = "mark_orphaned"

        db.commit()
        print(f"治理完成：action={action}, affected={changed}")
        return 0

    except Exception as exc:
        db.rollback()
        print(f"执行失败：{exc}")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
