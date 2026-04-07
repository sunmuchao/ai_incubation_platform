"""
编辑历史服务

提供内容编辑和历史记录功能：
- 帖子编辑
- 评论编辑
- 编辑历史记录
- 编辑次数限制
- 编辑时间窗口限制
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import uuid

from models.member import MemberType, ContentType, CommunityMember


class EditRecord:
    """编辑记录"""

    def __init__(
        self,
        content_type: ContentType,
        content_id: str,
        editor_id: str,
        editor_type: MemberType,
        old_content: str,
        new_content: str,
        edit_reason: str = None
    ):
        self.id = str(uuid.uuid4())
        self.content_type = content_type
        self.content_id = content_id
        self.editor_id = editor_id
        self.editor_type = editor_type
        self.old_content = old_content
        self.new_content = new_content
        self.edit_reason = edit_reason
        self.edited_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content_type": self.content_type.value,
            "content_id": self.content_id,
            "editor_id": self.editor_id,
            "editor_type": self.editor_type.value,
            "old_content": self.old_content[:500] + "..." if len(self.old_content) > 500 else self.old_content,
            "new_content": self.new_content[:500] + "..." if len(self.new_content) > 500 else self.new_content,
            "edit_reason": self.edit_reason,
            "edited_at": self.edited_at.isoformat()
        }

    def get_diff_summary(self) -> str:
        """获取编辑差异摘要"""
        old_len = len(self.old_content)
        new_len = len(self.new_content)

        if old_len == new_len:
            return f"内容长度不变 ({old_len} 字符)"
        elif new_len > old_len:
            return f"新增 {new_len - old_len} 字符 ({old_len} -> {new_len})"
        else:
            return f"删除 {old_len - new_len} 字符 ({old_len} -> {new_len})"


class EditHistoryService:
    """编辑历史服务"""

    def __init__(
        self,
        max_edit_count: int = 10,
        edit_time_limit_seconds: int = 3600,
        history_retention_days: int = 90
    ):
        """
        初始化编辑历史服务

        Args:
            max_edit_count: 最大编辑次数
            edit_time_limit_seconds: 可编辑时间窗口（秒）
            history_retention_days: 历史记录保留天数
        """
        self.max_edit_count = max_edit_count
        self.edit_time_limit_seconds = edit_time_limit_seconds
        self.history_retention_days = history_retention_days

        # 编辑历史存储：{content_type: {content_id: [EditRecord]}}
        self._edit_history: Dict[ContentType, Dict[str, List[EditRecord]]] = {
            ContentType.POST: {},
            ContentType.COMMENT: {}
        }

        # 编辑计数：{content_type: {content_id: count}}
        self._edit_counts: Dict[ContentType, Dict[str, int]] = {
            ContentType.POST: {},
            ContentType.COMMENT: {}
        }

    def can_edit(
        self,
        content_type: ContentType,
        content_id: str,
        created_at: datetime,
        editor_id: str,
        author_id: str
    ) -> Dict[str, Any]:
        """
        检查是否可以编辑内容

        Returns:
            {
                "can_edit": bool,
                "reason": str,  # 如果不能编辑的原因
                "edit_count": int,
                "max_edit_count": int,
                "time_remaining": int  # 剩余可编辑时间（秒）
            }
        """
        now = datetime.now()

        # 检查时间窗口
        time_since_creation = (now - created_at).total_seconds()
        time_remaining = self.edit_time_limit_seconds - time_since_creation

        if time_since_creation > self.edit_time_limit_seconds:
            return {
                "can_edit": False,
                "reason": f"超过编辑时间窗口（{self.edit_time_limit_seconds // 60} 分钟）",
                "edit_count": self._edit_counts[content_type].get(content_id, 0),
                "max_edit_count": self.max_edit_count,
                "time_remaining": 0
            }

        # 检查编辑次数
        edit_count = self._edit_counts[content_type].get(content_id, 0)
        if edit_count >= self.max_edit_count:
            return {
                "can_edit": False,
                "reason": f"已达到最大编辑次数（{self.max_edit_count} 次）",
                "edit_count": edit_count,
                "max_edit_count": self.max_edit_count,
                "time_remaining": int(time_remaining)
            }

        # 检查权限（只能编辑自己的内容，除非是管理员）
        # 注意：这里只做基本检查，详细权限检查应在 API 层进行
        if editor_id != author_id:
            # 非作者编辑需要特殊权限（在 API 层检查）
            pass

        return {
            "can_edit": True,
            "reason": None,
            "edit_count": edit_count,
            "max_edit_count": self.max_edit_count,
            "time_remaining": int(time_remaining)
        }

    def edit_content(
        self,
        content_type: ContentType,
        content_id: str,
        editor_id: str,
        editor_type: MemberType,
        old_content: str,
        new_content: str,
        edit_reason: str = None
    ) -> EditRecord:
        """
        编辑内容并记录历史

        Args:
            content_type: 内容类型
            content_id: 内容 ID
            editor_id: 编辑者 ID
            editor_type: 编辑者类型
            old_content: 原始内容
            new_content: 新内容
            edit_reason: 编辑原因

        Returns:
            编辑记录
        """
        # 创建编辑记录
        record = EditRecord(
            content_type=content_type,
            content_id=content_id,
            editor_id=editor_id,
            editor_type=editor_type,
            old_content=old_content,
            new_content=new_content,
            edit_reason=edit_reason
        )

        # 保存历史记录
        if content_id not in self._edit_history[content_type]:
            self._edit_history[content_type][content_id] = []

        self._edit_history[content_type][content_id].append(record)

        # 更新编辑计数
        self._edit_counts[content_type][content_id] = \
            self._edit_counts[content_type].get(content_id, 0) + 1

        # 清理过期历史记录
        self._cleanup_old_records(content_type, content_id)

        return record

    def get_edit_history(
        self,
        content_type: ContentType,
        content_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """获取内容的编辑历史"""
        records = self._edit_history[content_type].get(content_id, [])
        return [r.to_dict() for r in records[-limit:]]

    def get_edit_record(
        self,
        content_type: ContentType,
        content_id: str,
        record_id: str
    ) -> Optional[Dict[str, Any]]:
        """获取特定编辑记录"""
        records = self._edit_history[content_type].get(content_id, [])
        for record in records:
            if record.id == record_id:
                return record.to_dict()
        return None

    def get_edit_count(
        self,
        content_type: ContentType,
        content_id: str
    ) -> int:
        """获取内容的编辑次数"""
        return self._edit_counts[content_type].get(content_id, 0)

    def was_edited(
        self,
        content_type: ContentType,
        content_id: str
    ) -> bool:
        """检查内容是否被编辑过"""
        return content_id in self._edit_history[content_type] and \
               len(self._edit_history[content_type][content_id]) > 0

    def get_last_edit_time(
        self,
        content_type: ContentType,
        content_id: str
    ) -> Optional[datetime]:
        """获取最后编辑时间"""
        records = self._edit_history[content_type].get(content_id, [])
        if records:
            return records[-1].edited_at
        return None

    def _cleanup_old_records(
        self,
        content_type: ContentType,
        content_id: str
    ) -> None:
        """清理过期的历史记录"""
        cutoff_date = datetime.now() - timedelta(days=self.history_retention_days)
        records = self._edit_history[content_type].get(content_id, [])

        if records:
            self._edit_history[content_type][content_id] = [
                r for r in records if r.edited_at >= cutoff_date
            ]

    def get_user_edit_stats(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """获取用户编辑统计"""
        cutoff_date = datetime.now() - timedelta(days=days)

        total_edits = 0
        posts_edited = 0
        comments_edited = 0

        for content_type in [ContentType.POST, ContentType.COMMENT]:
            for content_id, records in self._edit_history[content_type].items():
                recent_records = [r for r in records if r.edited_at >= cutoff_date and r.editor_id == user_id]
                total_edits += len(recent_records)

                if content_type == ContentType.POST:
                    posts_edited += len(set(r.content_id for r in recent_records))
                else:
                    comments_edited += len(set(r.content_id for r in recent_records))

        return {
            "user_id": user_id,
            "period_days": days,
            "total_edits": total_edits,
            "posts_edited": posts_edited,
            "comments_edited": comments_edited,
            "average_edits_per_day": total_edits / days if days > 0 else 0
        }

    def get_content_diff(
        self,
        content_type: ContentType,
        content_id: str,
        record_id: str
    ) -> Dict[str, Any]:
        """获取编辑差异详情"""
        records = self._edit_history[content_type].get(content_id, [])
        record = next((r for r in records if r.id == record_id), None)

        if not record:
            return {"error": "Record not found"}

        # 简单的差异展示
        old_lines = record.old_content.split('\n')
        new_lines = record.new_content.split('\n')

        return {
            "record_id": record_id,
            "old_content": record.old_content,
            "new_content": record.new_content,
            "old_lines": len(old_lines),
            "new_lines": len(new_lines),
            "old_chars": len(record.old_content),
            "new_chars": len(record.new_content),
            "diff_summary": record.get_diff_summary(),
            "edit_reason": record.edit_reason,
            "edited_at": record.edited_at.isoformat()
        }

    def reset_edit_count(
        self,
        content_type: ContentType,
        content_id: str
    ) -> bool:
        """重置编辑计数（管理员操作）"""
        if content_id in self._edit_counts[content_type]:
            self._edit_counts[content_type][content_id] = 0
            return True
        return False

    def clear_edit_history(
        self,
        content_type: ContentType,
        content_id: str
    ) -> int:
        """清除编辑历史（管理员操作）"""
        records = self._edit_history[content_type].get(content_id, [])
        count = len(records)
        self._edit_history[content_type][content_id] = []
        self._edit_counts[content_type][content_id] = 0
        return count


# 全局服务实例
edit_history_service = EditHistoryService(
    max_edit_count=10,
    edit_time_limit_seconds=3600,  # 1 小时
    history_retention_days=90
)
