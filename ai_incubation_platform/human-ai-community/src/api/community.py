"""
社区 API 路由
"""
from fastapi import APIRouter, HTTPException
from typing import List

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


@router.get("/posts", response_model=List[Post])
async def list_posts(limit: int = 50):
    """获取帖子列表"""
    return community_service.list_posts(limit)


@router.post("/posts", response_model=Post)
async def create_post(post_data: PostCreate):
    """创建帖子"""
    return community_service.create_post(post_data)


@router.get("/posts/{post_id}", response_model=Post)
async def get_post(post_id: str):
    """获取帖子详情"""
    post = community_service.get_post(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@router.post("/comments", response_model=Comment)
async def create_comment(comment_data: CommentCreate):
    """创建评论"""
    try:
        return community_service.create_comment(comment_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/posts/{post_id}/comments", response_model=List[Comment])
async def get_post_comments(post_id: str):
    """获取帖子的评论列表"""
    if not community_service.get_post(post_id):
        raise HTTPException(status_code=404, detail="Post not found")
    return community_service.list_post_comments(post_id)


@router.get("/comments/{comment_id}/replies", response_model=List[Comment])
async def get_comment_replies(comment_id: str):
    """获取评论的回复列表"""
    if not community_service.get_comment(comment_id):
        raise HTTPException(status_code=404, detail="Comment not found")
    return community_service.get_comment_replies(comment_id)


# ==================== 内容审核接口 ====================
@router.get("/reviews/pending", response_model=List[ContentReview])
async def get_pending_reviews(limit: int = 100):
    """获取待审核内容列表"""
    return community_service.get_pending_reviews(limit)


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


# ==================== AI Agent接口 ====================
@router.post("/ai/agents/{agent_name}/generate-post")
async def ai_generate_post(agent_name: str, topic: str, tags: List[str] = None):
    """AI生成帖子"""
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
    try:
        result = community_service.call_ai_agent(agent_name, "generate_reply", {
            "post_id": post_id,
            "context": context
        })
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/ai/posts", response_model=Post)
async def create_ai_post(agent_name: str, post_data: PostCreate):
    """AI创建帖子（接入审核流程）"""
    try:
        # 校验作者是AI类型
        member = community_service.get_member(post_data.author_id)
        if not member or member.member_type != MemberType.AI:
            raise HTTPException(status_code=400, detail="Author must be an AI member")

        # 校验AI Agent已注册
        if agent_name not in community_service._ai_agent_configs:
            raise HTTPException(status_code=400, detail=f"AI Agent {agent_name} not registered")

        return community_service.create_post_with_review(post_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/ai/comments", response_model=Comment)
async def create_ai_comment(agent_name: str, comment_data: CommentCreate):
    """AI创建评论（接入审核流程）"""
    try:
        # 校验作者是AI类型
        member = community_service.get_member(comment_data.author_id)
        if not member or member.member_type != MemberType.AI:
            raise HTTPException(status_code=400, detail="Author must be an AI member")

        # 校验AI Agent已注册
        if agent_name not in community_service._ai_agent_configs:
            raise HTTPException(status_code=400, detail=f"AI Agent {agent_name} not registered")

        return community_service.create_comment_with_review(comment_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 速率限制接口 ====================
@router.post("/rate-limits", response_model=RateLimitConfig)
async def create_rate_limit(config: RateLimitConfig):
    """创建速率限制配置"""
    return community_service.add_rate_limit_config(config)


@router.get("/rate-limits/{resource}/{identifier}/remaining")
async def get_rate_limit_remaining(resource: str, identifier: str):
    """获取剩余可调用次数"""
    remaining = community_service.get_rate_limit_remaining(resource, identifier)
    return {
        "resource": resource,
        "identifier": identifier,
        "remaining": remaining
    }


# ==================== 带审核的内容创建接口 ====================
@router.post("/posts/with-review", response_model=Post)
async def create_post_with_review(post_data: PostCreate):
    """创建帖子并进入审核流程"""
    try:
        return community_service.create_post_with_review(post_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/comments/with-review", response_model=Comment)
async def create_comment_with_review(comment_data: CommentCreate):
    """创建评论并进入审核流程"""
    try:
        return community_service.create_comment_with_review(comment_data)
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
