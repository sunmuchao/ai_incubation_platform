"""
社区服务
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import uuid
from collections import defaultdict
import re
from models.member import (
    CommunityMember, MemberCreate, Post, PostCreate, MemberType, Comment, CommentCreate,
    ContentType, ReviewStatus, ReviewResult, ContentReview, ReviewRule,
    AgentCallRecord, RateLimitConfig, ReportType, ReportStatus, Report,
    BanStatus, BanRecord, OperationType, AuditLog, UnifiedUserInfo, MemberRole
)
from services.notification_service import notification_service, NotificationEvent

# DeerFlow 2.0 客户端导入（可选依赖）
try:
    from deerflow_integration import get_deerflow_client, is_deerflow_available
    DEERFLOW_AVAILABLE = is_deerflow_available()
except ImportError:
    DEERFLOW_AVAILABLE = False


class RateLimitExceeded(ValueError):
    """速率限制触发时抛出的异常（API 返回 429）"""


class CommunityService:
    """社区服务"""

    def __init__(self):
        self._members: Dict[str, CommunityMember] = {}
        self._posts: Dict[str, Post] = {}
        self._comments: Dict[str, Comment] = {}  # 评论存储

        # 内容审核相关
        self._content_reviews: Dict[str, ContentReview] = {}  # 审核记录
        self._review_rules: Dict[str, ReviewRule] = {}  # 审核规则
        self._pending_reviews: List[str] = []  # 待审核队列（存储审核记录ID）

        # AI Agent相关
        self._agent_call_records: Dict[str, AgentCallRecord] = {}  # Agent调用记录
        self._ai_agent_configs: Dict[str, Dict[str, Any]] = {}  # AI Agent配置

        # 速率限制相关
        self._rate_limit_configs: Dict[str, RateLimitConfig] = {}  # 速率限制配置
        self._rate_limit_counters: Dict[str, Dict[str, List[datetime]]] = defaultdict(lambda: defaultdict(list))  # 速率计数器: {resource: {identifier: [timestamps]}}

        # 社区治理相关
        self._reports: Dict[str, Report] = {}  # 举报记录
        self._ban_records: Dict[str, BanRecord] = {}  # 封禁记录
        self._audit_logs: Dict[str, AuditLog] = {}  # 审计日志

        # 统一账号体系相关
        self._unified_account_cache: Dict[str, UnifiedUserInfo] = {}  # 统一账号信息缓存

    def create_member(self, data: MemberCreate) -> CommunityMember:
        """创建成员"""
        member = CommunityMember(**data.model_dump())
        self._members[member.id] = member
        return member

    def get_member(self, member_id: str) -> Optional[CommunityMember]:
        """获取成员"""
        return self._members.get(member_id)

    def list_members(self) -> List[CommunityMember]:
        """获取成员列表"""
        return list(self._members.values())

    def create_post(self, data: PostCreate) -> Post:
        """创建帖子"""
        post = Post(**data.model_dump())
        self._posts[post.id] = post
        # 更新成员发帖数
        if data.author_id in self._members:
            self._members[data.author_id].post_count += 1
        return post

    def get_post(self, post_id: str) -> Optional[Post]:
        """获取帖子"""
        post = self._posts.get(post_id)
        if not post:
            return None
        return post if self._is_content_visible(ContentType.POST, post_id) else None

    def list_posts(self, limit: int = 50, author_type: Optional[MemberType] = None) -> List[Post]:
        """获取帖子列表（可选按 author_type 过滤）"""
        posts = sorted(self._posts.values(), key=lambda p: p.created_at, reverse=True)
        visible_posts = [p for p in posts if self._is_content_visible(ContentType.POST, p.id)]
        if author_type:
            visible_posts = [p for p in visible_posts if p.author_type == author_type]
        return visible_posts[:limit]

    def get_ai_members(self) -> List[CommunityMember]:
        """获取 AI 成员列表"""
        return [m for m in self._members.values() if m.member_type == MemberType.AI]

    def get_human_members(self) -> List[CommunityMember]:
        """获取人类成员列表"""
        return [m for m in self._members.values() if m.member_type == MemberType.HUMAN]

    def create_comment(self, data: CommentCreate) -> Comment:
        """创建评论"""
        # 验证帖子存在
        if data.post_id not in self._posts:
            raise ValueError(f"Post {data.post_id} not found")
        # 验证父评论存在（如果有）
        if data.parent_id and data.parent_id not in self._comments:
            raise ValueError(f"Parent comment {data.parent_id} not found")

        comment = Comment(**data.model_dump())
        self._comments[comment.id] = comment
        return comment

    def get_comment(self, comment_id: str) -> Optional[Comment]:
        """获取评论"""
        return self._comments.get(comment_id)

    def list_post_comments(self, post_id: str, author_type: Optional[MemberType] = None) -> List[Comment]:
        """获取帖子的所有评论（可选按 author_type 过滤）"""
        comments = [c for c in self._comments.values() if c.post_id == post_id]
        visible_comments = [c for c in comments if self._is_content_visible(ContentType.COMMENT, c.id)]
        if author_type:
            visible_comments = [c for c in visible_comments if c.author_type == author_type]
        return sorted(visible_comments, key=lambda c: c.created_at)

    def get_comment_replies(self, comment_id: str) -> List[Comment]:
        """获取评论的所有回复"""
        replies = [c for c in self._comments.values() if c.parent_id == comment_id]
        visible_replies = [c for c in replies if self._is_content_visible(ContentType.COMMENT, c.id)]
        return sorted(visible_replies, key=lambda c: c.created_at)

    # ==================== 内容可见性（审核结果） ====================
    def get_post_any(self, post_id: str) -> Optional[Post]:
        """获取帖子（不做审核可见性过滤，便于内部校验）"""
        return self._posts.get(post_id)

    def get_comment_any(self, comment_id: str) -> Optional[Comment]:
        """获取评论（不做审核可见性过滤，便于内部校验）"""
        return self._comments.get(comment_id)

    def _get_latest_review_for_content(
        self,
        content_type: ContentType,
        content_id: str,
    ) -> Optional[ContentReview]:
        """获取某条内容的最新审核记录"""
        reviews = [
            r
            for r in self._content_reviews.values()
            if r.content_type == content_type and r.content_id == content_id
        ]
        if not reviews:
            return None
        return max(reviews, key=lambda r: r.submit_time)

    def _is_content_visible(self, content_type: ContentType, content_id: str) -> bool:
        """审核通过（或从未进入审核）才可见"""
        review = self._get_latest_review_for_content(content_type, content_id)
        return review is None or review.status == ReviewStatus.APPROVED

    # ==================== 内容审核相关方法 ====================
    def submit_content_for_review(self, content_id: str, content_type: ContentType, content: str,
                                 author_id: str, author_type: MemberType) -> ContentReview:
        """提交内容到审核队列"""
        review = ContentReview(
            content_id=content_id,
            content_type=content_type,
            content=content,
            author_id=author_id,
            author_type=author_type,
            status=ReviewStatus.PENDING
        )
        # 基础反滥用：空内容/超长内容直接拒绝（不进入待审核队列）
        normalized = (content or "").strip()
        if not normalized:
            review.status = ReviewStatus.REJECTED
            review.review_result = ReviewResult(
                status=ReviewStatus.REJECTED,
                reason="内容为空",
                reviewer="auto-review-system",
                risk_score=1.0
            )
            self._content_reviews[review.id] = review
            return review

        if len(content) > 20000:
            review.status = ReviewStatus.REJECTED
            review.review_result = ReviewResult(
                status=ReviewStatus.REJECTED,
                reason="内容过长",
                reviewer="auto-review-system",
                risk_score=0.95
            )
            self._content_reviews[review.id] = review
            return review

        self._content_reviews[review.id] = review
        self._pending_reviews.append(review.id)

        # 自动执行初步审核
        self._auto_review_content(review)
        return review

    def _auto_review_content(self, review: ContentReview) -> None:
        """自动审核内容（规则引擎占位实现）"""
        # 规则引擎占位实现：支持 keyword/regex/ai（后续可替换为真实检测器）
        total_risk = 0.0
        matched_reject_rules = []
        matched_flag_rules = []

        # 遍历所有启用的规则
        for rule in self._review_rules.values():
            if not rule.enabled:
                continue

            if self._apply_review_rule(rule, review.content):
                total_risk += rule.risk_score
                if rule.action == "reject":
                    matched_reject_rules.append(rule.name)
                elif rule.action == "flag":
                    matched_flag_rules.append(rule.name)

        # 根据规则 action 与风险分数决定审核结果
        if matched_reject_rules:
            review.status = ReviewStatus.REJECTED
            review.review_result = ReviewResult(
                status=ReviewStatus.REJECTED,
                reason="; ".join([f"触发规则(reject): {n}" for n in matched_reject_rules]),
                reviewer="auto-review-system",
                risk_score=min(1.0, total_risk if total_risk > 0 else 0.9),
            )
            if review.id in self._pending_reviews:
                self._pending_reviews.remove(review.id)
            return

        if total_risk >= 0.8:  # 高风险兜底拒绝
            review.status = ReviewStatus.REJECTED
            review.review_result = ReviewResult(
                status=ReviewStatus.REJECTED,
                reason="内容风险过高",
                reviewer="auto-review-system",
                risk_score=total_risk,
            )
            if review.id in self._pending_reviews:
                self._pending_reviews.remove(review.id)
            return

        if total_risk >= 0.3 or matched_flag_rules:
            review.status = ReviewStatus.FLAGGED
            review.review_result = ReviewResult(
                status=ReviewStatus.FLAGGED,
                reason="内容需要人工审核",
                reviewer="auto-review-system",
                risk_score=total_risk,
            )
            return

        # 低风险，自动通过
        review.status = ReviewStatus.APPROVED
        review.review_result = ReviewResult(
            status=ReviewStatus.APPROVED,
            reason="自动审核通过",
            reviewer="auto-review-system",
            risk_score=total_risk,
        )
        if review.id in self._pending_reviews:
            self._pending_reviews.remove(review.id)

    def _apply_review_rule(self, rule: ReviewRule, content: str) -> bool:
        """应用审核规则（占位实现）"""
        # 规则应用占位实现：keyword/regex/ai
        # - keyword: 直接子串匹配
        # - regex: re.search 匹配（支持 patterns 或 regex）
        # - ai: 用 trigger_keywords 等配置做“占位触发”
        config = rule.config or {}

        if rule.rule_type == "keyword":
            keywords = config.get("keywords", []) or []
            return any(keyword in content for keyword in keywords)

        if rule.rule_type == "regex":
            patterns = config.get("patterns") or config.get("regex") or []
            for pattern in patterns:
                try:
                    if re.search(pattern, content, flags=re.IGNORECASE):
                        return True
                except re.error:
                    # 正则配置错误时忽略，避免服务不可用
                    continue
            return False

        if rule.rule_type == "ai":
            trigger_keywords = config.get("trigger_keywords") or config.get("keywords") or []
            return any(keyword in content for keyword in trigger_keywords)

        # 其他规则类型（custom 等）暂不实现
        return False

    def add_review_rule(self, rule: ReviewRule) -> ReviewRule:
        """添加审核规则"""
        self._review_rules[rule.id] = rule
        return rule

    def list_review_rules(self) -> List[ReviewRule]:
        """列出所有审核规则（含 enabled/disabled）"""
        return list(self._review_rules.values())

    def set_review_rule_enabled(self, rule_id: str, enabled: bool) -> Optional[ReviewRule]:
        """启用/禁用审核规则"""
        rule = self._review_rules.get(rule_id)
        if not rule:
            return None
        rule.enabled = enabled
        rule.updated_at = datetime.now()
        return rule

    def get_pending_reviews(self, limit: int = 100) -> List[ContentReview]:
        """获取待审核内容列表"""
        pending_ids = self._pending_reviews[:limit]
        return [self._content_reviews[rid] for rid in pending_ids if rid in self._content_reviews]

    def get_review_queue(
        self,
        limit_pending: int = 50,
        limit_flagged: int = 50,
    ) -> Dict[str, Any]:
        """获取人工审核队列（占位：pending/flagged 分组）"""
        pending_items = []
        flagged_items = []

        for rid in self._pending_reviews:
            review = self._content_reviews.get(rid)
            if not review:
                continue
            if review.status == ReviewStatus.PENDING:
                pending_items.append(review)
            elif review.status == ReviewStatus.FLAGGED:
                flagged_items.append(review)

        return {
            "pending_total": len(pending_items),
            "flagged_total": len(flagged_items),
            "pending": pending_items[:limit_pending],
            "flagged": flagged_items[:limit_flagged],
        }

    def get_latest_post_review(self, post_id: str) -> Optional[ContentReview]:
        """获取指定帖子的最新审核记录（不受可见性过滤影响）"""
        return self._get_latest_review_for_content(ContentType.POST, post_id)

    def get_latest_comment_review(self, comment_id: str) -> Optional[ContentReview]:
        """获取指定评论的最新审核记录（不受可见性过滤影响）"""
        return self._get_latest_review_for_content(ContentType.COMMENT, comment_id)

    def get_review_by_id(self, review_id: str) -> Optional[ContentReview]:
        """获取指定审核记录（不做可见性过滤）"""
        return self._content_reviews.get(review_id)

    def review_content(self, review_id: str, status: ReviewStatus, reason: str, reviewer: str) -> Optional[ContentReview]:
        """人工审核内容"""
        review = self._content_reviews.get(review_id)
        if not review:
            return None

        review.status = status
        review.review_result = ReviewResult(
            status=status,
            reason=reason,
            reviewer=reviewer,
            review_time=datetime.now()
        )

        # 从待审核队列移除
        if review_id in self._pending_reviews:
            self._pending_reviews.remove(review_id)

        # 发送审核结果通知
        self._notify_review_result(review)

        return review

    def _notify_review_result(self, review: ContentReview) -> None:
        """发送审核结果通知"""
        content_type_name = "帖子" if review.content_type == ContentType.POST else "评论"

        if review.status == ReviewStatus.APPROVED:
            notification_service.notify_content_approved(
                recipient_id=review.author_id,
                content_type=content_type_name,
                content_id=review.content_id,
                content_title=review.content[:50] + "..." if len(review.content) > 50 else review.content
            )
        elif review.status == ReviewStatus.REJECTED:
            notification_service.notify_content_rejected(
                recipient_id=review.author_id,
                content_type=content_type_name,
                content_id=review.content_id,
                content_title=review.content[:50] + "..." if len(review.content) > 50 else review.content,
                reject_reason=review.review_result.reason if review.review_result else "未知原因"
            )

    # ==================== AI Agent相关方法 ====================
    def register_ai_agent(self, agent_name: str, config: Dict[str, Any]) -> None:
        """注册AI Agent配置"""
        self._ai_agent_configs[agent_name] = config

    def list_agent_calls(
        self,
        agent_name: Optional[str] = None,
        limit: int = 50,
    ) -> List[AgentCallRecord]:
        """查询 AI Agent 调用记录（统一 Agent 标准审计占位）"""
        calls = list(self._agent_call_records.values())
        if agent_name:
            calls = [c for c in calls if c.agent_name == agent_name]
        # 按最近调用时间排序（越新越靠前）
        calls = sorted(calls, key=lambda c: c.call_time, reverse=True)
        return calls[:limit]

    def call_ai_agent(self, agent_name: str, action: str, input_params: Dict[str, Any]) -> Dict[str, Any]:
        """调用AI Agent（统一Agent标准占位实现）"""
        call_start = datetime.now()
        status = "success"
        error_msg = None
        output = {}

        try:
            # Agent调用逻辑占位
            if agent_name not in self._ai_agent_configs:
                raise ValueError(f"AI Agent {agent_name} 未注册")

            # 这里是调用具体AI模型的占位
            if action == "generate_post":
                output = self._generate_ai_post(agent_name, input_params)
            elif action == "generate_reply":
                output = self._generate_ai_reply(agent_name, input_params)
            elif action == "review_content":
                output = self._ai_review_content(agent_name, input_params)
            elif action == "publish_post":
                output = {"published": True, "post": input_params.get("post")}
            elif action == "publish_reply":
                output = {"published": True, "comment": input_params.get("comment")}
            else:
                raise ValueError(f"不支持的Agent动作: {action}")

        except Exception as e:
            status = "failed"
            error_msg = str(e)
            output = {"error": error_msg}

        # 记录调用日志
        call_time = (datetime.now() - call_start).total_seconds() * 1000
        record = AgentCallRecord(
            agent_name=agent_name,
            action=action,
            input_params=input_params,
            output_result=output,
            status=status,
            error_message=error_msg,
            call_time=call_start,
            response_time=call_time
        )
        self._agent_call_records[record.id] = record

        return output

    def _generate_ai_post(self, agent_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """生成AI帖子（占位实现）"""
        # 后续实现具体的AI帖子生成逻辑
        return {
            "title": f"AI生成的帖子 - {params.get('topic', '无主题')}",
            "content": "这是AI生成的帖子内容",
            "tags": params.get("tags", [])
        }

    def _generate_ai_reply(self, agent_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """生成AI回复（占位实现）"""
        # 后续实现具体的AI回复生成逻辑
        return {
            "content": "这是AI生成的回复内容",
            "related_post_id": params.get("post_id")
        }

    def _ai_review_content(self, agent_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """AI内容审核（占位实现）"""
        # 后续实现具体的AI内容审核逻辑
        return {
            "risk_score": 0.0,
            "suggestion": "内容合规",
            "should_reject": False
        }

    # ==================== 速率限制相关方法 ====================
    def add_rate_limit_config(self, config: RateLimitConfig) -> RateLimitConfig:
        """添加速率限制配置"""
        self._rate_limit_configs[config.id] = config
        return config

    def check_rate_limit(self, resource: str, identifier: str) -> bool:
        """检查是否超过速率限制"""
        # 同一 resource 可能有多条配置：优先使用“最新添加”的那一条
        matching = [
            c for c in self._rate_limit_configs.values()
            if c.resource == resource and c.enabled
        ]
        config = matching[-1] if matching else None

        if not config:
            return True  # 没有配置限制，允许访问

        now = datetime.now()
        window_start = now.timestamp() - config.window_seconds

        # 清理过期的记录
        timestamps = self._rate_limit_counters[resource][identifier]
        timestamps = [t for t in timestamps if t.timestamp() >= window_start]
        self._rate_limit_counters[resource][identifier] = timestamps

        if len(timestamps) >= config.limit:
            return False  # 超过限制

        # 添加新的记录
        timestamps.append(now)
        return True

    def get_rate_limit_remaining(self, resource: str, identifier: str) -> int:
        """获取剩余可调用次数"""
        matching = [
            c for c in self._rate_limit_configs.values()
            if c.resource == resource and c.enabled
        ]
        config = matching[-1] if matching else None

        if not config:
            return -1  # 无限制

        now = datetime.now()
        window_start = now.timestamp() - config.window_seconds
        timestamps = [t for t in self._rate_limit_counters[resource][identifier]
                      if t.timestamp() >= window_start]

        return max(0, config.limit - len(timestamps))

    def get_rate_limit_details(self, resource: str, identifier: str) -> Dict[str, Any]:
        """获取速率限制详细信息（remaining + 配置）"""
        matching = [
            c for c in self._rate_limit_configs.values()
            if c.resource == resource and c.enabled
        ]
        config = matching[-1] if matching else None

        remaining = self.get_rate_limit_remaining(resource, identifier)
        if not config:
            return {
                "resource": resource,
                "identifier": identifier,
                "remaining": remaining,
                "limit": None,
                "window_seconds": None,
            }

        return {
            "resource": resource,
            "identifier": identifier,
            "remaining": remaining,
            "limit": config.limit,
            "window_seconds": config.window_seconds,
        }

    # ==================== 内容创建的审核集成 ====================
    def create_post_with_review(self, data: PostCreate) -> Post:
        """创建帖子并自动进入审核流程"""
        post = self.create_post(data)

        # 提交审核
        self.submit_content_for_review(
            content_id=post.id,
            content_type=ContentType.POST,
            content=f"{post.title}\n{post.content}",
            author_id=post.author_id,
            author_type=post.author_type
        )

        return post

    def create_comment_with_review(self, data: CommentCreate) -> Comment:
        """创建评论并自动进入审核流程"""
        comment = self.create_comment(data)

        # 提交审核
        self.submit_content_for_review(
            content_id=comment.id,
            content_type=ContentType.COMMENT,
            content=comment.content,
            author_id=comment.author_id,
            author_type=comment.author_type
        )

        return comment

    def create_ai_post_with_review(self, agent_name: str, data: PostCreate) -> Post:
        """AI 通过统一 Agent 标准发布帖子（进入审核流程）"""
        member = self.get_member(data.author_id)
        if not member or member.member_type != MemberType.AI:
            raise ValueError("Author must be an AI member")

        if data.author_type != MemberType.AI:
            raise ValueError("author_type must be ai for AI post publishing")

        if agent_name not in self._ai_agent_configs:
            raise ValueError(f"AI Agent {agent_name} not registered")

        # 仅用于审计/追溯的 Agent 记录（内容仍以提交的 post_data 为准）
        self.call_ai_agent(agent_name, "publish_post", {"post": data.model_dump()})
        return self.create_post_with_review(data)

    def create_ai_comment_with_review(self, agent_name: str, data: CommentCreate) -> Comment:
        """AI 通过统一 Agent 标准发布评论（进入审核流程）"""
        member = self.get_member(data.author_id)
        if not member or member.member_type != MemberType.AI:
            raise ValueError("Author must be an AI member")

        if data.author_type != MemberType.AI:
            raise ValueError("author_type must be ai for AI comment publishing")

        if agent_name not in self._ai_agent_configs:
            raise ValueError(f"AI Agent {agent_name} not registered")

        # 仅用于审计/追溯的 Agent 记录（内容仍以提交的 comment_data 为准）
        self.call_ai_agent(agent_name, "publish_reply", {"comment": data.model_dump()})
        return self.create_comment_with_review(data)

    # ==================== 社区治理相关方法 ====================
    # 举报功能
    def create_report(self, reporter_id: str, reported_content_id: str, reported_content_type: ContentType,
                     report_type: ReportType, description: str = None, evidence: List[str] = None) -> Report:
        """创建举报"""
        # 验证内容存在
        if reported_content_type == ContentType.POST:
            if not self.get_post_any(reported_content_id):
                raise ValueError(f"Post {reported_content_id} not found")
        elif reported_content_type == ContentType.COMMENT:
            if not self.get_comment_any(reported_content_id):
                raise ValueError(f"Comment {reported_content_id} not found")

        # 验证举报人存在
        if not self.get_member(reporter_id):
            raise ValueError(f"Reporter {reporter_id} not found")

        report = Report(
            reporter_id=reporter_id,
            reported_content_id=reported_content_id,
            reported_content_type=reported_content_type,
            report_type=report_type,
            description=description,
            evidence=evidence
        )
        self._reports[report.id] = report

        # 记录审计日志
        self.log_audit(
            operator_id=reporter_id,
            operator_type=self.get_member(reporter_id).member_type,
            operation_type=OperationType.CREATE_MEMBER,  # TODO: 应该有专门的CREATE_REPORT类型
            resource_type=reported_content_type,
            resource_id=reported_content_id,
            after={"report_id": report.id, "report_type": report_type}
        )

        return report

    def get_report(self, report_id: str) -> Optional[Report]:
        """获取举报详情"""
        return self._reports.get(report_id)

    def list_pending_reports(self, limit: int = 100) -> List[Report]:
        """获取待处理的举报列表"""
        pending_reports = [r for r in self._reports.values() if r.status == ReportStatus.PENDING]
        return sorted(pending_reports, key=lambda r: r.created_at)[:limit]

    def process_report(self, report_id: str, handler_id: str, status: ReportStatus, handler_note: str = None) -> Optional[Report]:
        """处理举报"""
        report = self.get_report(report_id)
        if not report:
            return None

        # 验证处理人权限（必须是版主或管理员）
        handler = self.get_member(handler_id)
        if not handler or handler.role not in [MemberRole.MODERATOR, MemberRole.ADMIN]:
            raise ValueError("Handler must be a moderator or admin")

        report.status = status
        report.handler_id = handler_id
        report.handler_note = handler_note
        report.updated_at = datetime.now()

        # 记录审计日志
        self.log_audit(
            operator_id=handler_id,
            operator_type=handler.member_type,
            operation_type=OperationType.PROCESS_REPORT,
            resource_type="report",
            resource_id=report_id,
            before={"status": ReportStatus.PENDING},
            after={"status": status, "handler_note": handler_note}
        )

        # 发送举报处理结果通知
        notification_service.notify_report_processed(
            reporter_id=report.reporter_id,
            report_id=report_id,
            status=status.value,
            handler_note=handler_note
        )

        return report

    # 封禁功能
    def ban_user(self, user_id: str, operator_id: str, reason: str, ban_type: str = "all",
                duration_hours: int = None) -> BanRecord:
        """封禁用户"""
        # 验证用户存在
        user = self.get_member(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        # 验证操作人权限
        operator = self.get_member(operator_id)
        if not operator or operator.role != MemberRole.ADMIN:
            raise ValueError("Operator must be an admin")

        # 计算过期时间
        expire_time = None
        if duration_hours:
            expire_time = datetime.now() + timedelta(hours=duration_hours)

        ban_record = BanRecord(
            user_id=user_id,
            reason=reason,
            ban_type=ban_type,
            duration_hours=duration_hours,
            operator_id=operator_id,
            expire_time=expire_time
        )
        self._ban_records[ban_record.id] = ban_record

        # 记录审计日志
        self.log_audit(
            operator_id=operator_id,
            operator_type=operator.member_type,
            operation_type=OperationType.BAN_USER,
            resource_type="user",
            resource_id=user_id,
            after={"ban_type": ban_type, "duration_hours": duration_hours, "reason": reason}
        )

        return ban_record

    def lift_ban(self, ban_id: str, operator_id: str, lift_reason: str = None) -> Optional[BanRecord]:
        """解除封禁"""
        ban_record = self._ban_records.get(ban_id)
        if not ban_record or ban_record.status != BanStatus.ACTIVE:
            return None

        # 验证操作人权限
        operator = self.get_member(operator_id)
        if not operator or operator.role != MemberRole.ADMIN:
            raise ValueError("Operator must be an admin")

        ban_record.status = BanStatus.LIFTED
        ban_record.lifted_at = datetime.now()
        ban_record.lift_reason = lift_reason

        # 记录审计日志
        self.log_audit(
            operator_id=operator_id,
            operator_type=operator.member_type,
            operation_type=OperationType.LIFT_BAN,
            resource_type="ban_record",
            resource_id=ban_id,
            before={"status": BanStatus.ACTIVE},
            after={"status": BanStatus.LIFTED, "lift_reason": lift_reason}
        )

        return ban_record

    def is_user_banned(self, user_id: str, ban_type: str = "all") -> bool:
        """检查用户是否被封禁"""
        now = datetime.now()
        for record in self._ban_records.values():
            if (record.user_id == user_id and
                record.status == BanStatus.ACTIVE and
                (record.ban_type == ban_type or record.ban_type == "all") and
                (not record.expire_time or record.expire_time > now)):
                return True
        return False

    def get_user_ban_records(self, user_id: str) -> List[BanRecord]:
        """获取用户的封禁记录"""
        records = [r for r in self._ban_records.values() if r.user_id == user_id]
        return sorted(records, key=lambda r: r.created_at, reverse=True)

    # 审计日志功能
    def log_audit(self, operator_id: str, operator_type: MemberType, operation_type: OperationType,
                 resource_type: str = None, resource_id: str = None, before: Dict[str, Any] = None,
                 after: Dict[str, Any] = None, ip_address: str = None, user_agent: str = None,
                 status: str = "success", error_message: str = None) -> AuditLog:
        """记录审计日志"""
        log = AuditLog(
            operator_id=operator_id,
            operator_type=operator_type,
            operation_type=operation_type,
            resource_type=resource_type,
            resource_id=resource_id,
            before=before,
            after=after,
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
            error_message=error_message
        )
        self._audit_logs[log.id] = log
        return log

    def list_audit_logs(self, operator_id: str = None, operation_type: OperationType = None,
                       limit: int = 100) -> List[AuditLog]:
        """查询审计日志"""
        logs = list(self._audit_logs.values())
        if operator_id:
            logs = [log for log in logs if log.operator_id == operator_id]
        if operation_type:
            logs = [log for log in logs if log.operation_type == operation_type]
        return sorted(logs, key=lambda l: l.created_at, reverse=True)[:limit]

    def get_audit_log_by_id(self, log_id: str) -> Optional[AuditLog]:
        """获取指定审计日志"""
        return self._audit_logs.get(log_id)

    # ==================== 统一账号体系对接 ====================
    def sync_unified_user(self, user_info: UnifiedUserInfo) -> CommunityMember:
        """从统一账号体系同步用户信息"""
        # 检查用户是否已存在
        existing_member = self.get_member(user_info.user_id)
        before_state = None

        if existing_member:
            # 更新现有用户信息
            before_state = existing_member.model_dump()
            existing_member.name = user_info.username
            existing_member.email = user_info.email
            # 从统一角色映射到社区角色
            if "admin" in user_info.roles:
                existing_member.role = MemberRole.ADMIN
            elif "moderator" in user_info.roles:
                existing_member.role = MemberRole.MODERATOR
            else:
                existing_member.role = MemberRole.MEMBER
            member = existing_member
        else:
            # 创建新用户
            member = CommunityMember(
                id=user_info.user_id,
                name=user_info.username,
                email=user_info.email,
                member_type=MemberType.HUMAN,
                role=MemberRole.ADMIN if "admin" in user_info.roles else
                     MemberRole.MODERATOR if "moderator" in user_info.roles else
                     MemberRole.MEMBER
            )
            self._members[member.id] = member

        # 缓存统一账号信息
        self._unified_account_cache[user_info.user_id] = user_info

        # 记录审计日志
        self.log_audit(
            operator_id="system",
            operator_type=MemberType.AI,  # 系统操作用AI类型标识
            operation_type=OperationType.UPDATE_MEMBER if existing_member else OperationType.CREATE_MEMBER,
            resource_type="user",
            resource_id=member.id,
            before=before_state,
            after=member.model_dump()
        )

        return member

    def get_unified_user_info(self, user_id: str) -> Optional[UnifiedUserInfo]:
        """获取统一账号信息（优先从缓存获取）"""
        return self._unified_account_cache.get(user_id)

    def validate_unified_token(self, token: str) -> Optional[UnifiedUserInfo]:
        """验证统一账号Token（占位实现，后续对接真实认证服务）"""
        # 这里是Token验证的占位实现
        # 实际项目中会调用统一身份认证服务的接口
        if not token:
            return None

        # 模拟验证成功，返回测试用户信息
        return UnifiedUserInfo(
            user_id=f"user_{token}",
            username=f"用户_{token}",
            email=f"{token}@example.com",
            roles=["member"],
            is_verified=True,
            created_at=datetime.now()
        )

    # ==================== 权限校验集成 ====================
    def check_permission(self, user_id: str, permission: str) -> bool:
        """检查用户权限"""
        user = self.get_member(user_id)
        if not user:
            return False

        # 管理员拥有所有权限
        if user.role == MemberRole.ADMIN:
            return True

        # 版主权限
        if user.role == MemberRole.MODERATOR:
            moderator_permissions = [
                "process_report", "review_content", "delete_post", "delete_comment"
            ]
            if permission in moderator_permissions:
                return True

        # 普通用户权限
        common_permissions = [
            "create_post", "create_comment", "report_content", "view_content"
        ]
        return permission in common_permissions

    # ==================== 操作拦截增强 ====================
    def create_post(self, data: PostCreate) -> Post:
        """创建帖子，添加权限和封禁检查"""
        # 检查用户是否被封禁
        if self.is_user_banned(data.author_id, "post"):
            raise ValueError("您已被禁止发帖")

        # 检查权限
        if not self.check_permission(data.author_id, "create_post"):
            raise ValueError("没有发帖权限")

        # 基础反滥用：空/超长内容直接拒绝
        title = (data.title or "").strip()
        content = (data.content or "").strip()
        if not title:
            raise ValueError("标题不能为空")
        if not content:
            raise ValueError("内容不能为空")
        if len(content) > 20000:
            raise ValueError("内容过长")

        # 速率限制（同一用户/AI 成员按 resource 计数）
        if not self.check_rate_limit("post", data.author_id):
            raise RateLimitExceeded("发帖频率过高，请稍后再试")

        post = Post(**data.model_dump())
        self._posts[post.id] = post
        # 更新成员发帖数
        if data.author_id in self._members:
            self._members[data.author_id].post_count += 1

        # 记录审计日志
        self.log_audit(
            operator_id=data.author_id,
            operator_type=data.author_type,
            operation_type=OperationType.CREATE_POST,
            resource_type="post",
            resource_id=post.id,
            after={"title": post.title, "tags": post.tags}
        )

        return post

    def create_comment(self, data: CommentCreate) -> Comment:
        """创建评论，添加权限和封禁检查"""
        # 验证帖子存在
        if data.post_id not in self._posts:
            raise ValueError(f"Post {data.post_id} not found")
        # 验证父评论存在（如果有）
        if data.parent_id and data.parent_id not in self._comments:
            raise ValueError(f"Parent comment {data.parent_id} not found")

        # 检查用户是否被封禁
        if self.is_user_banned(data.author_id, "comment"):
            raise ValueError("您已被禁止评论")

        # 检查权限
        if not self.check_permission(data.author_id, "create_comment"):
            raise ValueError("没有评论权限")

        # 基础反滥用：空/超长内容直接拒绝
        content = (data.content or "").strip()
        if not content:
            raise ValueError("评论内容不能为空")
        if len(content) > 20000:
            raise ValueError("评论内容过长")

        # 速率限制
        if not self.check_rate_limit("comment", data.author_id):
            raise RateLimitExceeded("评论频率过高，请稍后再试")

        comment = Comment(**data.model_dump())
        self._comments[comment.id] = comment

        # 记录审计日志
        self.log_audit(
            operator_id=data.author_id,
            operator_type=data.author_type,
            operation_type=OperationType.CREATE_COMMENT,
            resource_type="comment",
            resource_id=comment.id,
            after={"post_id": comment.post_id, "parent_id": comment.parent_id}
        )

        # 如果是回复评论，发送通知给被回复的用户
        if data.parent_id:
            self._notify_new_reply(data, comment)

        return comment

    def _notify_new_reply(self, data: CommentCreate, comment: Comment) -> None:
        """发送新回复通知"""
        parent_comment = self.get_comment(data.parent_id)
        if parent_comment:
            # 获取被回复用户的消息
            member = self.get_member(data.author_id)
            member_name = member.name if member else data.author_id
            notification_service.notify_new_reply(
                recipient_id=parent_comment.author_id,
                post_id=data.post_id,
                comment_id=comment.id,
                replier_name=member_name,
                reply_content=comment.content
            )


# 全局服务实例
community_service = CommunityService()


# ==================== DeerFlow 2.0 集成方法 ====================
def _build_generate_post_prompt(input_params: Dict[str, Any]) -> str:
    """构建生成帖子的 prompt"""
    topic = input_params.get("topic", "无主题")
    tags = input_params.get("tags", [])
    return f"请为社区生成一个帖子，主题：{topic}，标签：{', '.join(tags)}。请返回 JSON 格式：{{\"title\": \"标题\", \"content\": \"内容\", \"tags\": []}}"


def _build_generate_reply_prompt(input_params: Dict[str, Any]) -> str:
    """构建生成回复的 prompt"""
    post_id = input_params.get("post_id", "unknown")
    context = input_params.get("context", "")
    return f"请为社区帖子（ID: {post_id}）生成回复，上下文：{context}。请返回 JSON 格式：{{\"content\": \"回复内容\"}}"


def _build_review_content_prompt(input_params: Dict[str, Any]) -> str:
    """构建审核内容的 prompt"""
    content = input_params.get("content", "")
    return f"请审核以下内容是否合规：{content[:500]}。请返回 JSON 格式：{{\"risk_score\": 0.0, \"suggestion\": \"审核意见\", \"should_reject\": false}}"
