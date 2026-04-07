"""
社区 API 路由
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.member import (
    CommunityMember, MemberCreate, Post, PostCreate, MemberType, Comment, CommentCreate,
    ContentType, ReviewStatus, ReviewResult, ContentReview, ReviewRule,
    AgentCallRecord, RateLimitConfig, ReportType, ReportStatus, Report,
    BanStatus, BanRecord, OperationType, AuditLog, UnifiedUserInfo
)
from services.community_service import community_service
from services.community_service import RateLimitExceeded
from services.edit_history_service import edit_history_service
from services.permission_service import permission_service, Permission

router = APIRouter(prefix="/api", tags=["community"])


@router.get("/members", response_model=List[CommunityMember])
async def list_members():
    """获取成员列表"""
    return community_service.list_members()


@router.post("/members", response_model=CommunityMember)
async def create_member(member_data: MemberCreate):
    """创建社区成员"""
    return community_service.create_member(member_data)


@router.get("/members/ai", response_model=List[CommunityMember])
async def list_ai_members():
    """获取 AI 成员列表"""
    return community_service.get_ai_members()


@router.get("/members/{member_id}", response_model=CommunityMember)
async def get_member(member_id: str):
    """获取成员详情"""
    member = community_service.get_member(member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    return member


@router.get("/posts", response_model=List[Post])
async def list_posts(limit: int = 50, author_type: Optional[str] = None):
    """获取帖子列表"""
    parsed_author_type = None
    if author_type:
        try:
            parsed_author_type = MemberType(author_type)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid author_type")
    return community_service.list_posts(limit, author_type=parsed_author_type)


@router.post("/posts", response_model=Post)
async def create_post(post_data: PostCreate):
    """创建帖子"""
    try:
        return community_service.create_post(post_data)
    except RateLimitExceeded as e:
        raise HTTPException(status_code=429, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/posts/{post_id}", response_model=Post)
async def get_post(post_id: str):
    """获取帖子详情"""
    post = community_service.get_post(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@router.get("/posts/{post_id}/review", response_model=ContentReview)
async def get_post_review(post_id: str):
    """获取指定帖子的最新审核结果（不受公开可见性影响）"""
    review = community_service.get_latest_post_review(post_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review record not found")
    return review


@router.post("/comments", response_model=Comment)
async def create_comment(comment_data: CommentCreate):
    """创建评论"""
    try:
        return community_service.create_comment(comment_data)
    except RateLimitExceeded as e:
        raise HTTPException(status_code=429, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/posts/{post_id}/comments", response_model=List[Comment])
async def get_post_comments(post_id: str, author_type: Optional[str] = None):
    """获取帖子的评论列表"""
    if not community_service.get_post(post_id):
        raise HTTPException(status_code=404, detail="Post not found")
    parsed_author_type = None
    if author_type:
        try:
            parsed_author_type = MemberType(author_type)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid author_type")
    return community_service.list_post_comments(post_id, author_type=parsed_author_type)


@router.get("/comments/{comment_id}/replies", response_model=List[Comment])
async def get_comment_replies(comment_id: str):
    """获取评论的回复列表"""
    if not community_service.get_comment(comment_id):
        raise HTTPException(status_code=404, detail="Comment not found")
    return community_service.get_comment_replies(comment_id)


@router.get("/comments/{comment_id}/review", response_model=ContentReview)
async def get_comment_review(comment_id: str):
    """获取指定评论的最新审核结果（不受公开可见性影响）"""
    # 注意：此接口不应用可见性过滤（审核结果对追溯/治理可见）
    review = community_service.get_latest_comment_review(comment_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review record not found")
    return review


# ==================== 内容审核接口 ====================
@router.get("/reviews/pending", response_model=List[ContentReview])
async def get_pending_reviews(limit: int = 100):
    """获取待审核内容列表"""
    return community_service.get_pending_reviews(limit)

@router.get("/reviews/queue")
async def get_review_queue(limit_pending: int = 50, limit_flagged: int = 50):
    """获取人工审核队列（pending/flagged 分组）"""
    return community_service.get_review_queue(limit_pending=limit_pending, limit_flagged=limit_flagged)


@router.get("/reviews/{review_id}", response_model=ContentReview)
async def get_review(review_id: str):
    """获取指定审核记录"""
    review = community_service.get_review_by_id(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review record not found")
    return review


@router.post("/reviews/{review_id}/review", response_model=ContentReview)
async def review_content(review_id: str, status: ReviewStatus, reason: str, reviewer: str):
    """人工审核内容"""
    review = community_service.review_content(review_id, status, reason, reviewer)
    if not review:
        raise HTTPException(status_code=404, detail="Review record not found")
    return review


@router.post("/review-rules", response_model=ReviewRule)
async def create_review_rule(rule: ReviewRule):
    """创建审核规则"""
    return community_service.add_review_rule(rule)

@router.get("/review-rules", response_model=List[ReviewRule])
async def list_review_rules():
    """列出所有审核规则"""
    return community_service.list_review_rules()


class ReviewRuleEnableRequest(BaseModel):
    enabled: bool


@router.post("/review-rules/{rule_id}/set-enabled", response_model=ReviewRule)
async def set_review_rule_enabled(rule_id: str, req: ReviewRuleEnableRequest):
    """启用/禁用审核规则"""
    rule = community_service.set_review_rule_enabled(rule_id=rule_id, enabled=req.enabled)
    if not rule:
        raise HTTPException(status_code=404, detail="Review rule not found")
    return rule


# ==================== AI Agent接口 ====================
@router.post("/ai/agents/{agent_name}/generate-post")
async def ai_generate_post(agent_name: str, topic: str, tags: List[str] = None):
    """AI生成帖子"""
    if not topic or not topic.strip():
        raise HTTPException(status_code=400, detail="topic 不能为空")

    if not community_service.check_rate_limit("ai_generate_post", agent_name):
        raise HTTPException(status_code=429, detail="AI 生成帖子请求过多，请稍后再试")

    try:
        result = community_service.call_ai_agent(agent_name, "generate_post", {
            "topic": topic,
            "tags": tags or []
        })
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/ai/agents/{agent_name}/generate-reply")
async def ai_generate_reply(agent_name: str, post_id: str, context: str = None):
    """AI生成回复"""
    if not post_id or not post_id.strip():
        raise HTTPException(status_code=400, detail="post_id 不能为空")

    if not community_service.check_rate_limit("ai_generate_reply", agent_name):
        raise HTTPException(status_code=429, detail="AI 生成回复请求过多，请稍后再试")

    try:
        result = community_service.call_ai_agent(agent_name, "generate_reply", {
            "post_id": post_id,
            "context": context
        })
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class AIGeneratePublishPostRequest(BaseModel):
    author_id: str
    topic: str
    tags: Optional[List[str]] = None


class AIGeneratePublishReplyRequest(BaseModel):
    author_id: str
    post_id: str
    context: Optional[str] = None
    parent_id: Optional[str] = None


@router.post("/ai/agents/{agent_name}/generate-and-publish-post", response_model=Post)
async def ai_generate_and_publish_post(agent_name: str, req: AIGeneratePublishPostRequest):
    """AI 生成并发布帖子（接入审核流程）"""
    if not req.topic or not req.topic.strip():
        raise HTTPException(status_code=400, detail="topic 不能为空")

    if not community_service.check_rate_limit("ai_generate_post", agent_name):
        raise HTTPException(status_code=429, detail="AI 生成并发布帖子请求过多，请稍后再试")

    member = community_service.get_member(req.author_id)
    if not member or member.member_type != MemberType.AI:
        raise HTTPException(status_code=400, detail="author_id 必须是 AI 成员")

    try:
        generated = community_service.call_ai_agent(
            agent_name,
            "generate_post",
            {"topic": req.topic, "tags": req.tags or []},
        )

        post_data = PostCreate(
            author_id=req.author_id,
            author_type=MemberType.AI,
            title=generated.get("title", ""),
            content=generated.get("content", ""),
            tags=generated.get("tags", req.tags or []),
        )
        return community_service.create_ai_post_with_review(agent_name, post_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/ai/agents/{agent_name}/generate-and-publish-reply", response_model=Comment)
async def ai_generate_and_publish_reply(agent_name: str, req: AIGeneratePublishReplyRequest):
    """AI 生成并发布回复（接入审核流程）"""
    if not req.post_id or not req.post_id.strip():
        raise HTTPException(status_code=400, detail="post_id 不能为空")

    if not community_service.check_rate_limit("ai_generate_reply", agent_name):
        raise HTTPException(status_code=429, detail="AI 生成并发布回复请求过多，请稍后再试")

    member = community_service.get_member(req.author_id)
    if not member or member.member_type != MemberType.AI:
        raise HTTPException(status_code=400, detail="author_id 必须是 AI 成员")

    try:
        generated = community_service.call_ai_agent(
            agent_name,
            "generate_reply",
            {"post_id": req.post_id, "context": req.context},
        )

        comment_data = CommentCreate(
            post_id=req.post_id,
            author_id=req.author_id,
            author_type=MemberType.AI,
            content=generated.get("content", ""),
            parent_id=req.parent_id,
        )
        return community_service.create_ai_comment_with_review(agent_name, comment_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/ai/posts", response_model=Post)
async def create_ai_post(agent_name: str, post_data: PostCreate):
    """AI创建帖子（接入审核流程）"""
    try:
        return community_service.create_ai_post_with_review(agent_name, post_data)
    except RateLimitExceeded as e:
        raise HTTPException(status_code=429, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/ai/comments", response_model=Comment)
async def create_ai_comment(agent_name: str, comment_data: CommentCreate):
    """AI创建评论（接入审核流程）"""
    try:
        return community_service.create_ai_comment_with_review(agent_name, comment_data)
    except RateLimitExceeded as e:
        raise HTTPException(status_code=429, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/ai/agent-calls", response_model=List[AgentCallRecord])
async def list_ai_agent_calls(agent_name: Optional[str] = None, limit: int = 50):
    """查询 AI Agent 调用记录（可按 agent_name 过滤）"""
    return community_service.list_agent_calls(agent_name=agent_name, limit=limit)


# ==================== 速率限制接口 ====================
@router.post("/rate-limits", response_model=RateLimitConfig)
async def create_rate_limit(config: RateLimitConfig):
    """创建速率限制配置"""
    return community_service.add_rate_limit_config(config)


@router.get("/rate-limits/{resource}/{identifier}/remaining")
async def get_rate_limit_remaining(resource: str, identifier: str):
    """获取剩余可调用次数"""
    return community_service.get_rate_limit_details(resource, identifier)


# ==================== 带审核的内容创建接口 ====================
@router.post("/posts/with-review", response_model=Post)
async def create_post_with_review(post_data: PostCreate):
    """创建帖子并进入审核流程"""
    try:
        return community_service.create_post_with_review(post_data)
    except RateLimitExceeded as e:
        raise HTTPException(status_code=429, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/comments/with-review", response_model=Comment)
async def create_comment_with_review(comment_data: CommentCreate):
    """创建评论并进入审核流程"""
    try:
        return community_service.create_comment_with_review(comment_data)
    except RateLimitExceeded as e:
        raise HTTPException(status_code=429, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 社区治理接口 ====================
# 举报接口
@router.post("/reports", response_model=Report)
async def create_report(
    reporter_id: str,
    reported_content_id: str,
    reported_content_type: ContentType,
    report_type: ReportType,
    description: Optional[str] = None,
    evidence: Optional[List[str]] = None
):
    """创建举报"""
    try:
        return community_service.create_report(
            reporter_id=reporter_id,
            reported_content_id=reported_content_id,
            reported_content_type=reported_content_type,
            report_type=report_type,
            description=description,
            evidence=evidence
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/reports/pending", response_model=List[Report])
async def get_pending_reports(limit: int = 100):
    """获取待处理的举报列表"""
    return community_service.list_pending_reports(limit)


@router.post("/reports/{report_id}/process", response_model=Report)
async def process_report(
    report_id: str,
    handler_id: str,
    status: ReportStatus,
    handler_note: Optional[str] = None
):
    """处理举报"""
    try:
        report = community_service.process_report(report_id, handler_id, status, handler_note)
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        return report
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))


# 封禁接口
@router.post("/users/{user_id}/ban", response_model=BanRecord)
async def ban_user(
    user_id: str,
    operator_id: str,
    reason: str,
    ban_type: str = "all",
    duration_hours: Optional[int] = None
):
    """封禁用户"""
    try:
        return community_service.ban_user(
            user_id=user_id,
            operator_id=operator_id,
            reason=reason,
            ban_type=ban_type,
            duration_hours=duration_hours
        )
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post("/bans/{ban_id}/lift", response_model=BanRecord)
async def lift_ban(ban_id: str, operator_id: str, lift_reason: Optional[str] = None):
    """解除封禁"""
    try:
        ban_record = community_service.lift_ban(ban_id, operator_id, lift_reason)
        if not ban_record:
            raise HTTPException(status_code=404, detail="Ban record not found")
        return ban_record
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/users/{user_id}/ban-status")
async def get_user_ban_status(user_id: str):
    """检查用户封禁状态"""
    is_banned = community_service.is_user_banned(user_id)
    ban_records = community_service.get_user_ban_records(user_id)
    return {
        "user_id": user_id,
        "is_banned": is_banned,
        "ban_records": ban_records
    }


# 审计日志接口
@router.get("/audit/logs", response_model=List[AuditLog])
async def get_audit_logs(
    operator_id: Optional[str] = None,
    operation_type: Optional[OperationType] = None,
    limit: int = 100
):
    """查询审计日志"""
    return community_service.list_audit_logs(operator_id, operation_type, limit)


@router.get("/audit/logs/{log_id}", response_model=AuditLog)
async def get_audit_log_by_id(log_id: str):
    """获取指定审计日志"""
    log = community_service.get_audit_log_by_id(log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Audit log not found")
    return log


# ==================== 统一账号体系接口 ====================
@router.post("/auth/sync-user", response_model=CommunityMember)
async def sync_unified_user(user_info: UnifiedUserInfo):
    """从统一账号体系同步用户信息"""
    return community_service.sync_unified_user(user_info)


@router.post("/auth/validate-token")
async def validate_token(token: str):
    """验证统一账号Token"""
    user_info = community_service.validate_unified_token(token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {
        "valid": True,
        "user_info": user_info
    }


@router.get("/users/{user_id}/unified-info")
async def get_unified_user_info(user_id: str):
    """获取用户的统一账号信息"""
    user_info = community_service.get_unified_user_info(user_id)
    if not user_info:
        raise HTTPException(status_code=404, detail="Unified user info not found")
    return user_info


# ==================== 内容编辑接口（Discord 风格优化） ====================

class EditPostRequest(BaseModel):
    """编辑帖子请求"""
    title: Optional[str] = Field(default=None, description="新标题")
    content: Optional[str] = Field(default=None, description="新内容")
    tags: Optional[List[str]] = Field(default=None, description="新标签")
    edit_reason: Optional[str] = Field(default=None, description="编辑原因")


class EditCommentRequest(BaseModel):
    """编辑评论请求"""
    content: str = Field(..., description="新内容")
    edit_reason: Optional[str] = Field(default=None, description="编辑原因")


class EditHistoryResponse(BaseModel):
    """编辑历史响应"""
    content_id: str
    content_type: str
    was_edited: bool
    edit_count: int
    history: List[Dict[str, Any]]


@router.put("/posts/{post_id}", response_model=Post)
async def edit_post(
    post_id: str,
    request: EditPostRequest,
    editor_id: str = Query(...),
    editor_type: str = Query(default="human")
):
    """
    编辑帖子

    只能编辑自己的帖子，除非有 edit_any_post 权限
    """
    post = community_service.get_post_any(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # 检查编辑权限
    try:
        mt = MemberType(editor_type)
    except ValueError:
        mt = MemberType.HUMAN

    can_edit = edit_history_service.can_edit(
        content_type=ContentType.POST,
        content_id=post_id,
        created_at=post.created_at,
        editor_id=editor_id,
        author_id=post.author_id
    )

    if not can_edit["can_edit"]:
        raise HTTPException(status_code=403, detail=can_edit["reason"])

    # 检查是否是作者或有编辑权限
    if editor_id != post.author_id:
        if not permission_service.has_permission(editor_id, mt, MemberRole.MODERATOR, Permission.EDIT_ANY_POST):
            raise HTTPException(status_code=403, detail="只能编辑自己的帖子")

    # 保存旧内容
    old_title = post.title
    old_content = post.content
    old_tags = post.tags.copy()

    # 更新帖子
    if request.title:
        post.title = request.title
    if request.content:
        post.content = request.content
    if request.tags:
        post.tags = request.tags
    post.updated_at = datetime.now()

    # 记录编辑历史
    edit_history_service.edit_content(
        content_type=ContentType.POST,
        content_id=post_id,
        editor_id=editor_id,
        editor_type=mt,
        old_content=f"标题：{old_title}\n内容：{old_content}",
        new_content=f"标题：{post.title}\n内容：{post.content}",
        edit_reason=request.edit_reason
    )

    # 触发 Webhook 通知
    from services.webhook_service import webhook_service, WebhookEvent
    try:
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(webhook_service.send_webhook(
            "system",  # 需要使用实际的 webhook_id
            WebhookEvent.POST_UPDATED,
            {"post_id": post_id, "editor_id": editor_id}
        ))
    except:
        pass  # Webhook 发送失败不影响编辑操作

    return post


@router.get("/posts/{post_id}/edits")
async def get_post_edit_history(post_id: str, limit: int = Query(default=50, ge=1, le=200)):
    """获取帖子编辑历史"""
    post = community_service.get_post_any(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    history = edit_history_service.get_edit_history(ContentType.POST, post_id, limit)
    was_edited = edit_history_service.was_edited(ContentType.POST, post_id)
    edit_count = edit_history_service.get_edit_count(ContentType.POST, post_id)

    return {
        "content_id": post_id,
        "content_type": "post",
        "was_edited": was_edited,
        "edit_count": edit_count,
        "history": history
    }


@router.put("/comments/{comment_id}", response_model=Comment)
async def edit_comment(
    comment_id: str,
    request: EditCommentRequest,
    editor_id: str = Query(...),
    editor_type: str = Query(default="human")
):
    """
    编辑评论

    只能编辑自己的评论，除非有 edit_any_comment 权限
    """
    comment = community_service.get_comment_any(comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    # 检查编辑权限
    try:
        mt = MemberType(editor_type)
    except ValueError:
        mt = MemberType.HUMAN

    can_edit = edit_history_service.can_edit(
        content_type=ContentType.COMMENT,
        content_id=comment_id,
        created_at=comment.created_at,
        editor_id=editor_id,
        author_id=comment.author_id
    )

    if not can_edit["can_edit"]:
        raise HTTPException(status_code=403, detail=can_edit["reason"])

    # 检查是否是作者或有编辑权限
    if editor_id != comment.author_id:
        if not permission_service.has_permission(editor_id, mt, MemberRole.MODERATOR, Permission.EDIT_ANY_COMMENT):
            raise HTTPException(status_code=403, detail="只能编辑自己的评论")

    # 保存旧内容
    old_content = comment.content

    # 更新评论
    comment.content = request.content
    comment.updated_at = datetime.now()

    # 记录编辑历史
    edit_history_service.edit_content(
        content_type=ContentType.COMMENT,
        content_id=comment_id,
        editor_id=editor_id,
        editor_type=mt,
        old_content=old_content,
        new_content=request.content,
        edit_reason=request.edit_reason
    )

    return comment


@router.get("/comments/{comment_id}/edits")
async def get_comment_edit_history(comment_id: str, limit: int = Query(default=50, ge=1, le=200)):
    """获取评论编辑历史"""
    comment = community_service.get_comment_any(comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    history = edit_history_service.get_edit_history(ContentType.COMMENT, comment_id, limit)
    was_edited = edit_history_service.was_edited(ContentType.COMMENT, comment_id)
    edit_count = edit_history_service.get_edit_count(ContentType.COMMENT, comment_id)

    return {
        "content_id": comment_id,
        "content_type": "comment",
        "was_edited": was_edited,
        "edit_count": edit_count,
        "history": history
    }


@router.get("/edits/user/{user_id}/stats")
async def get_user_edit_stats(
    user_id: str,
    days: int = Query(default=30, ge=1, le=365)
):
    """获取用户编辑统计"""
    stats = edit_history_service.get_user_edit_stats(user_id, days)
    return stats


# 导入 datetime（用于编辑时间戳）
from datetime import datetime
from typing import Any
