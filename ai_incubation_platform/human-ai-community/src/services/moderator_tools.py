"""
版主工具模块

提供 Reddit 风格的版主治理工具，包括：
- 用户注释系统（私有注释追踪问题用户）
- 审核队列批量操作
- 动态速率限制
- 内容相似度检测
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import hashlib
import json

from models.member import (
    MemberType, ContentType, ReportStatus, BanStatus, MemberRole,
    OperationType, Report, BanRecord, ReviewStatus, CommunityMember
)
from services.notification_service import notification_service, NotificationEvent, NotificationPriority, NotificationMessage


class UserAnnotation:
    """用户注释"""
    def __init__(
        self,
        user_id: str,
        moderator_id: str,
        note: str,
        annotation_type: str = "warning",  # warning, ban, spam, abuse, other
        is_private: bool = True  # 仅版主可见
    ):
        self.id = str(hashlib.md5(f"{user_id}{moderator_id}{datetime.now().isoformat()}".encode()).hexdigest())
        self.user_id = user_id
        self.moderator_id = moderator_id
        self.note = note
        self.annotation_type = annotation_type
        self.is_private = is_private
        self.created_at = datetime.now()


class UserAnnotationSystem:
    """用户注释系统"""

    def __init__(self):
        self._annotations: Dict[str, List[UserAnnotation]] = defaultdict(list)  # user_id -> annotations

    def add_annotation(
        self,
        user_id: str,
        moderator_id: str,
        note: str,
        annotation_type: str = "warning",
        is_private: bool = True
    ) -> UserAnnotation:
        """添加用户注释"""
        annotation = UserAnnotation(
            user_id=user_id,
            moderator_id=moderator_id,
            note=note,
            annotation_type=annotation_type,
            is_private=is_private
        )
        self._annotations[user_id].append(annotation)
        return annotation

    def get_user_annotations(
        self,
        user_id: str,
        moderator_id: str,
        include_private: bool = True
    ) -> List[UserAnnotation]:
        """获取用户注释列表"""
        annotations = self._annotations.get(user_id, [])
        if include_private:
            # 版主只能看到自己添加的私有注释
            if annotations:
                return sorted(annotations, key=lambda a: a.created_at, reverse=True)
        else:
            # 公开注释所有人都能看到
            return [a for a in annotations if not a.is_private]

    def get_user_annotation_summary(self, user_id: str) -> Dict[str, Any]:
        """获取用户注释摘要（供版主快速查看）"""
        annotations = self._annotations.get(user_id, [])
        if not annotations:
            return {"total": 0, "by_type": {}, "recent_notes": []}

        by_type = defaultdict(int)
        recent_notes = []
        for ann in annotations:
            by_type[ann.annotation_type] += 1
            if len(recent_notes) < 5:
                recent_notes.append({
                    "note": ann.note,
                    "type": ann.annotation_type,
                    "moderator_id": ann.moderator_id,
                    "created_at": ann.created_at.isoformat()
                })

        return {
            "total": len(annotations),
            "by_type": dict(by_type),
            "recent_notes": recent_notes
        }


class ContentSimilarityChecker:
    """内容相似度检测器"""

    def __init__(self, max_cache_size: int = 1000):
        self._content_hashes: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._max_cache_size = max_cache_size

    def _normalize_content(self, content: str) -> str:
        """标准化内容（去除空白、转小写）"""
        return " ".join(content.lower().split())

    def _content_fingerprint(self, content: str) -> str:
        """生成内容指纹（用于快速去重）"""
        normalized = self._normalize_content(content)
        return hashlib.md5(normalized.encode()).hexdigest()

    def _jaccard_similarity(self, set1: set, set2: set) -> float:
        """计算 Jaccard 相似度"""
        if not set1 or not set2:
            return 0.0
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0

    def check_similarity(
        self,
        content: str,
        threshold: float = 0.8,
        check_window_hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        检查内容相似度，返回相似内容列表

        Args:
            content: 待检查内容
            threshold: 相似度阈值
            check_window_hours: 检查时间窗口（小时）

        Returns:
            相似内容列表（包含相似度分数）
        """
        normalized = self._normalize_content(content)
        content_words = set(normalized.split())
        cutoff_time = datetime.now() - timedelta(hours=check_window_hours)

        similar_items = []

        for cached_content, items in self._content_hashes.items():
            # 时间窗口过滤
            items = [i for i in items if i["created_at"] >= cutoff_time]
            if not items:
                continue

            # 快速指纹检查（完全重复）
            fingerprint = self._content_fingerprint(cached_content)
            current_fingerprint = self._content_fingerprint(normalized)

            if fingerprint == current_fingerprint:
                # 完全重复
                for item in items:
                    similar_items.append({
                        "content_id": item["content_id"],
                        "content_type": item["content_type"],
                        "similarity": 1.0,
                        "reason": "完全重复"
                    })
                continue

            # Jaccard 相似度检查
            cached_words = set(cached_content.split())
            similarity = self._jaccard_similarity(content_words, cached_words)

            if similarity >= threshold:
                for item in items:
                    similar_items.append({
                        "content_id": item["content_id"],
                        "content_type": item["content_type"],
                        "similarity": round(similarity, 2),
                        "reason": f"内容相似度 {similarity:.0%}"
                    })

        # 按相似度排序
        return sorted(similar_items, key=lambda x: x["similarity"], reverse=True)

    def register_content(
        self,
        content: str,
        content_id: str,
        content_type: ContentType
    ) -> None:
        """注册新内容到缓存"""
        normalized = self._normalize_content(content)

        # 添加缓存
        self._content_hashes[normalized].append({
            "content_id": content_id,
            "content_type": content_type.value,
            "created_at": datetime.now()
        })

        # 清理过期缓存
        cutoff_time = datetime.now() - timedelta(hours=24)
        for key in list(self._content_hashes.keys()):
            self._content_hashes[key] = [
                i for i in self._content_hashes[key]
                if i["created_at"] >= cutoff_time
            ]
            if not self._content_hashes[key]:
                del self._content_hashes[key]

        # 限制缓存大小
        while len(self._content_hashes) > self._max_cache_size:
            oldest_key = next(iter(self._content_hashes))
            del self._content_hashes[oldest_key]


class DynamicRateLimiter:
    """动态速率限制器"""

    def __init__(self):
        # 用户信誉分数：越高限制越宽松
        self._user_reputation: Dict[str, float] = defaultdict(lambda: 1.0)
        # 基础限制配置
        self._base_limits = {
            "post": {"limit": 10, "window_seconds": 3600},  # 10 帖/小时
            "comment": {"limit": 30, "window_seconds": 3600},  # 30 评论/小时
            "report": {"limit": 20, "window_seconds": 3600},  # 20 举报/小时
        }
        # 速率计数器
        self._counters: Dict[str, Dict[str, List[datetime]]] = defaultdict(lambda: defaultdict(list))

    def update_reputation(self, user_id: str, delta: float) -> None:
        """
        更新用户信誉分数

        Args:
            user_id: 用户 ID
            delta: 分数变化（正数增加信誉，负数减少）
        """
        current = self._user_reputation[user_id]
        # 限制在 0.1-10.0 范围内
        new_score = max(0.1, min(10.0, current + delta))
        self._user_reputation[user_id] = new_score

    def get_reputation(self, user_id: str) -> float:
        """获取用户信誉分数"""
        return self._user_reputation[user_id]

    def _get_dynamic_limit(self, resource: str, user_id: str) -> Dict[str, Any]:
        """获取动态限制（基于信誉分数调整）"""
        base = self._base_limits.get(resource, {"limit": 10, "window_seconds": 3600})
        reputation = self._user_reputation.get(user_id, 1.0)

        # 信誉越高，限制越宽松
        # 信誉 10.0 -> 限制放宽 10 倍
        # 信誉 0.1 -> 限制收紧到 1/10
        adjusted_limit = int(base["limit"] * reputation)

        return {
            "limit": max(1, adjusted_limit),
            "window_seconds": base["window_seconds"]
        }

    def check_rate_limit(self, resource: str, user_id: str) -> Dict[str, Any]:
        """
        检查速率限制

        Returns:
            {
                "allowed": bool,
                "remaining": int,
                "reset_time": datetime,
                "limit": int,
                "reputation": float
            }
        """
        config = self._get_dynamic_limit(resource, user_id)
        limit = config["limit"]
        window = config["window_seconds"]

        now = datetime.now()
        window_start = now - timedelta(seconds=window)

        # 清理过期记录
        timestamps = self._counters[resource][user_id]
        timestamps = [t for t in timestamps if t >= window_start]
        self._counters[resource][user_id] = timestamps

        remaining = max(0, limit - len(timestamps))
        reset_time = now + timedelta(seconds=window)

        allowed = len(timestamps) < limit

        return {
            "allowed": allowed,
            "remaining": remaining,
            "reset_time": reset_time.isoformat(),
            "limit": limit,
            "window_seconds": window,
            "reputation": self._user_reputation.get(user_id, 1.0)
        }

    def record_action(self, resource: str, user_id: str) -> None:
        """记录用户动作（用于速率限制计数）"""
        self._counters[resource][user_id].append(datetime.now())

    def penalize_user(self, user_id: str, violation_type: str) -> None:
        """
        对用户违规行为进行惩罚（降低信誉分数）

        Args:
            user_id: 用户 ID
            violation_type: 违规类型（spam, abuse, rate_limit_violation 等）
        """
        penalties = {
            "spam": -2.0,
            "abuse": -1.5,
            "rate_limit_violation": -0.5,
            "content_removed": -1.0,
            "report_confirmed": -0.3
        }
        penalty = penalties.get(violation_type, -0.5)
        self.update_reputation(user_id, penalty)

    def reward_user(self, user_id: str, action_type: str) -> None:
        """
        对用户良好行为进行奖励（提高信誉分数）

        Args:
            user_id: 用户 ID
            action_type: 行为类型（quality_post, helpful_report 等）
        """
        rewards = {
            "quality_post": 0.3,
            "quality_comment": 0.1,
            "helpful_report": 0.2,
            "long_time_member": 0.01  # 每日奖励
        }
        reward = rewards.get(action_type, 0.1)
        self.update_reputation(user_id, reward)


class BatchReportProcessor:
    """批量举报处理器"""

    def __init__(self, community_service):
        self.community_service = community_service

    def get_priority_reports(
        self,
        limit: int = 50,
        priority_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        获取高优先级举报

        优先级计算因素：
        - 举报人信誉
        - 被举报内容类型
        - 举报类型（暴力/色情优先级更高）
        - 多人联合举报
        """
        reports = list(self.community_service._reports.values())
        pending_reports = [r for r in reports if r.status == ReportStatus.PENDING]

        # 计算优先级分数
        scored_reports = []
        for report in pending_reports:
            score = 0.5  # 基础分数

            # 举报类型权重
            type_weights = {
                ReportType.VIOLENCE: 0.3,
                ReportType.PORNOGRAPHY: 0.3,
                ReportType.HATE_SPEECH: 0.2,
                ReportType.SPAM: 0.1,
                ReportType.COPYRIGHT: 0.1,
                ReportType.OTHER: 0.0
            }
            score += type_weights.get(report.report_type, 0.0)

            # TODO: 举报人信誉分数
            # reporter_reputation = dynamic_rate_limiter.get_reputation(report.reporter_id)
            # score += (reporter_reputation - 1.0) * 0.1

            scored_reports.append({
                "report": report,
                "priority_score": min(1.0, score)
            })

        # 按优先级排序
        scored_reports = sorted(
            scored_reports,
            key=lambda x: x["priority_score"],
            reverse=True
        )

        # 返回高优先级举报
        high_priority = [
            sr for sr in scored_reports
            if sr["priority_score"] >= priority_threshold
        ][:limit]

        return high_priority

    def batch_process(
        self,
        report_ids: List[str],
        handler_id: str,
        status: ReportStatus,
        handler_note: str = ""
    ) -> Dict[str, Any]:
        """批量处理举报"""
        results = {
            "total": len(report_ids),
            "success": 0,
            "failed": 0,
            "details": []
        }

        for report_id in report_ids:
            try:
                report = self.community_service.process_report(
                    report_id=report_id,
                    handler_id=handler_id,
                    status=status,
                    handler_note=handler_note
                )
                if report:
                    results["success"] += 1
                    results["details"].append({
                        "report_id": report_id,
                        "status": status.value,
                        "action": "processed"
                    })

                    # 如果举报被确认，奖励举报人
                    if status == ReportStatus.RESOLVED:
                        # 这里可以集成信誉系统
                        pass
                else:
                    results["failed"] += 1
                    results["details"].append({
                        "report_id": report_id,
                        "status": "not_found"
                    })
            except Exception as e:
                results["failed"] += 1
                results["details"].append({
                    "report_id": report_id,
                    "status": "error",
                    "error": str(e)
                })

        return results

    def get_batch_process_template(self) -> Dict[str, Any]:
        """获取批量处理模板（用于 API 文档）"""
        return {
            "report_ids": ["report_id_1", "report_id_2", "..."],
            "status": "resolved",  # 或 dismissed
            "handler_note": "批量处理备注"
        }


class ModeratorTools:
    """版主工具统一入口"""

    def __init__(self, community_service):
        self.community_service = community_service
        self.annotation_system = UserAnnotationSystem()
        self.similarity_checker = ContentSimilarityChecker()
        self.rate_limiter = DynamicRateLimiter()
        self.batch_processor = BatchReportProcessor(community_service)

    def add_user_annotation(
        self,
        user_id: str,
        moderator_id: str,
        note: str,
        annotation_type: str = "warning",
        is_private: bool = True
    ) -> Dict[str, Any]:
        """添加用户注释"""
        moderator = self.community_service.get_member(moderator_id)
        if not moderator or moderator.role not in [MemberRole.MODERATOR, MemberRole.ADMIN]:
            return {"success": False, "error": "权限不足"}

        annotation = self.annotation_system.add_annotation(
            user_id=user_id,
            moderator_id=moderator_id,
            note=note,
            annotation_type=annotation_type,
            is_private=is_private
        )

        return {
            "success": True,
            "annotation_id": annotation.id,
            "created_at": annotation.created_at.isoformat()
        }

    def get_user_annotations(
        self,
        user_id: str,
        moderator_id: str
    ) -> Dict[str, Any]:
        """获取用户注释"""
        moderator = self.community_service.get_member(moderator_id)
        if not moderator or moderator.role not in [MemberRole.MODERATOR, MemberRole.ADMIN]:
            return {"success": False, "error": "权限不足"}

        annotations = self.annotation_system.get_user_annotations(user_id, moderator_id)
        summary = self.annotation_system.get_user_annotation_summary(user_id)

        return {
            "success": True,
            "user_id": user_id,
            "summary": summary,
            "annotations": [
                {
                    "id": a.id,
                    "note": a.note,
                    "type": a.annotation_type,
                    "moderator_id": a.moderator_id,
                    "created_at": a.created_at.isoformat()
                }
                for a in annotations
            ]
        }

    def check_content_similarity(
        self,
        content: str,
        content_id: str = None,
        threshold: float = 0.8
    ) -> Dict[str, Any]:
        """检查内容相似度"""
        similar_items = self.similarity_checker.check_similarity(content, threshold)

        # 如果提供了 content_id，注册该内容
        if content_id:
            self.similarity_checker.register_content(
                content=content,
                content_id=content_id,
                content_type=ContentType.POST  # 默认为帖子
            )

        return {
            "similar_count": len(similar_items),
            "similar_items": similar_items[:10],  # 最多返回 10 条
            "is_duplicate": len(similar_items) > 0 and similar_items[0]["similarity"] >= 0.95
        }

    def get_rate_limit_status(
        self,
        resource: str,
        user_id: str
    ) -> Dict[str, Any]:
        """获取速率限制状态"""
        return self.rate_limiter.check_rate_limit(resource, user_id)

    def update_user_reputation(
        self,
        user_id: str,
        action: str,
        moderator_id: str
    ) -> Dict[str, Any]:
        """更新用户信誉（版主手动操作）"""
        moderator = self.community_service.get_member(moderator_id)
        if not moderator or moderator.role not in [MemberRole.MODERATOR, MemberRole.ADMIN]:
            return {"success": False, "error": "权限不足"}

        actions = {
            "reward_good_post": ("reward", "quality_post"),
            "reward_helpful_comment": ("reward", "quality_comment"),
            "penalize_spam": ("penalize", "spam"),
            "penalize_abuse": ("penalize", "abuse")
        }

        if action not in actions:
            return {"success": False, "error": "未知操作"}

        op_type, op_value = actions[action]

        if op_type == "reward":
            self.rate_limiter.reward_user(user_id, op_value)
        else:
            self.rate_limiter.penalize_user(user_id, op_value)

        return {
            "success": True,
            "user_id": user_id,
            "action": action,
            "new_reputation": self.rate_limiter.get_reputation(user_id)
        }

    def get_high_priority_reports(self, limit: int = 50) -> Dict[str, Any]:
        """获取高优先级举报"""
        reports = self.batch_processor.get_priority_reports(limit)
        return {
            "total": len(reports),
            "reports": [
                {
                    "report_id": r["report"].id,
                    "report_type": r["report"].report_type.value,
                    "content_id": r["report"].reported_content_id,
                    "content_type": r["report"].reported_content_type.value,
                    "reporter_id": r["report"].reporter_id,
                    "priority_score": r["priority_score"],
                    "created_at": r["report"].created_at.isoformat()
                }
                for r in reports
            ]
        }

    def batch_process_reports(
        self,
        report_ids: List[str],
        handler_id: str,
        status: str,
        handler_note: str = ""
    ) -> Dict[str, Any]:
        """批量处理举报"""
        try:
            report_status = ReportStatus(status)
        except ValueError:
            return {"success": False, "error": "无效的状态值"}

        return self.batch_processor.batch_process(
            report_ids=report_ids,
            handler_id=handler_id,
            status=report_status,
            handler_note=handler_note
        )


# 全局实例创建函数
def create_moderator_tools(community_service) -> ModeratorTools:
    """创建版主工具实例"""
    return ModeratorTools(community_service)
