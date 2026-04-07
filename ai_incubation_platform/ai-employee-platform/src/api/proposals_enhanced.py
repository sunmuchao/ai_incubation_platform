"""
P7 提案系统增强 API

提供：
- 提案模板功能
- 邀请投标功能
- 提案点券机制（防 spam）
- 提案数据分析
"""
from fastapi import APIRouter, HTTPException, Query, Body
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import uuid

router = APIRouter(prefix="/api/proposals-enhanced", tags=["P7-提案系统增强"])

# 导入服务
from services.enhanced_proposal_service import enhanced_proposal_service


# ==================== 请求/响应模型 ====================

class ProposalTemplateCreate(BaseModel):
    """创建提案模板"""
    name: str
    title_template: str
    content_template: str
    category: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    is_public: bool = False


class ProposalTemplateUpdate(BaseModel):
    """更新提案模板"""
    name: Optional[str] = None
    title_template: Optional[str] = None
    content_template: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    is_public: Optional[bool] = None


class JobInvitationCreate(BaseModel):
    """创建邀请投标"""
    job_posting_id: str
    invitee_id: str
    employee_id: Optional[str] = None
    message: Optional[str] = None
    expires_days: int = Field(ge=1, le=30, default=7)


class InvitationResponse(BaseModel):
    """邀请响应"""
    accept: bool
    employee_id: Optional[str] = None
    reason: Optional[str] = None


class CouponPurchaseRequest(BaseModel):
    """购买点券请求"""
    amount: int = Field(ge=1, le=100)


# ==================== 提案模板管理端点 ====================

@router.post("/templates", response_model=Dict[str, Any])
async def create_proposal_template(
    template: ProposalTemplateCreate,
    user_id: str = Query(...),
    tenant_id: str = Query(...)
):
    """
    创建提案模板

    用户可以创建常用的提案模板，提高提案效率
    """
    data = template.model_dump()
    data['user_id'] = user_id
    data['tenant_id'] = tenant_id

    created = enhanced_proposal_service.create_template(data)

    return {
        "message": "提案模板创建成功",
        "template_id": created.id,
        "name": created.name
    }


@router.get("/templates", response_model=Dict[str, Any])
async def list_proposal_templates(
    user_id: str = Query(...),
    include_public: bool = True
):
    """
    获取提案模板列表

    包括用户自己的模板和公开的模板
    """
    templates = enhanced_proposal_service.list_templates(user_id, include_public)

    return {
        "total": len(templates),
        "templates": [
            {
                "id": t.id,
                "name": t.name,
                "title_template": t.title_template[:50] + '...' if len(t.title_template) > 50 else t.title_template,
                "content_template": t.content_template[:100] + '...' if len(t.content_template) > 100 else t.content_template,
                "category": t.category,
                "tags": t.tags,
                "usage_count": t.usage_count,
                "is_public": t.is_public,
                "is_mine": t.user_id == user_id
            }
            for t in templates
        ]
    }


@router.get("/templates/{template_id}", response_model=Dict[str, Any])
async def get_proposal_template(template_id: str):
    """
    获取提案模板详情
    """
    template = enhanced_proposal_service.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    return {
        "template": {
            "id": template.id,
            "name": template.name,
            "title_template": template.title_template,
            "content_template": template.content_template,
            "category": template.category,
            "tags": template.tags,
            "usage_count": template.usage_count,
            "created_at": template.created_at.isoformat(),
            "updated_at": template.updated_at.isoformat()
        }
    }


@router.put("/templates/{template_id}")
async def update_proposal_template(template_id: str, update: ProposalTemplateUpdate):
    """
    更新提案模板
    """
    data = update.model_dump(exclude_none=True)
    result = enhanced_proposal_service.update_template(template_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="模板不存在")

    return {"message": "模板更新成功"}


@router.delete("/templates/{template_id}")
async def delete_proposal_template(template_id: str):
    """
    删除提案模板
    """
    success = enhanced_proposal_service.delete_template(template_id)
    if not success:
        raise HTTPException(status_code=404, detail="模板不存在")

    return {"message": "模板已删除"}


@router.post("/templates/{template_id}/use")
async def use_proposal_template(template_id: str):
    """
    使用提案模板

    使用模板时会自动增加使用计数
    """
    template = enhanced_proposal_service.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    enhanced_proposal_service.increment_template_usage(template_id)

    return {
        "message": "模板使用成功",
        "template": {
            "id": template.id,
            "name": template.name,
            "title_template": template.title_template,
            "content_template": template.content_template
        }
    }


# ==================== 邀请投标管理端点 ====================

@router.post("/invitations", response_model=Dict[str, Any])
async def create_job_invitation(
    invitation: JobInvitationCreate,
    inviter_id: str = Query(...),
    tenant_id: str = Query(...)
):
    """
    创建邀请投标

    雇主可以主动邀请特定的 AI 员工所有者参与投标
    """
    data = invitation.model_dump()
    data['inviter_id'] = inviter_id
    data['tenant_id'] = tenant_id

    created = enhanced_proposal_service.create_invitation(data)

    return {
        "message": "邀请创建成功",
        "invitation_id": created.id,
        "invitee_id": created.invitee_id,
        "expires_at": created.expires_at.isoformat()
    }


@router.get("/invitations", response_model=Dict[str, Any])
async def list_invitations(
    invitee_id: Optional[str] = Query(None),
    inviter_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None)
):
    """
    获取邀请列表
    """
    invitations = enhanced_proposal_service.list_invitations(invitee_id, inviter_id, status)

    return {
        "total": len(invitations),
        "invitations": [
            {
                "id": i.id,
                "job_posting_id": i.job_posting_id,
                "inviter_id": i.inviter_id,
                "invitee_id": i.invitee_id,
                "employee_id": i.employee_id,
                "message": i.message,
                "status": i.status,
                "created_at": i.created_at.isoformat(),
                "expires_at": i.expires_at.isoformat(),
                "responded_at": i.responded_at.isoformat() if i.responded_at else None
            }
            for i in invitations
        ]
    }


@router.post("/invitations/{invitation_id}/accept")
async def accept_invitation(
    invitation_id: str,
    response_data: Optional[Dict[str, Any]] = Body(None)
):
    """
    接受邀请投标

    可以选择性地指定员工 ID
    """
    employee_id = None
    if response_data and 'employee_id' in response_data:
        employee_id = response_data['employee_id']

    success = enhanced_proposal_service.accept_invitation(invitation_id, employee_id)
    if not success:
        invitation = enhanced_proposal_service.get_invitation(invitation_id)
        if not invitation:
            raise HTTPException(status_code=404, detail="邀请不存在")
        raise HTTPException(status_code=400, detail="无法接受邀请（可能已过期或已响应）")

    return {"message": "邀请已接受"}


@router.post("/invitations/{invitation_id}/decline")
async def decline_invitation(
    invitation_id: str,
    response_data: Optional[Dict[str, Any]] = Body(None)
):
    """
    拒绝邀请投标
    """
    reason = response_data.get('reason') if response_data else None

    success = enhanced_proposal_service.decline_invitation(invitation_id, reason)
    if not success:
        invitation = enhanced_proposal_service.get_invitation(invitation_id)
        if not invitation:
            raise HTTPException(status_code=404, detail="邀请不存在")
        raise HTTPException(status_code=400, detail="无法拒绝邀请（可能已过期或已响应）")

    return {"message": "邀请已拒绝"}


# ==================== 点券管理端点 ====================

@router.get("/coupons/stats")
async def get_coupon_stats(
    user_id: str = Query(...),
    tenant_id: str = Query(...)
):
    """
    获取点券统计

    查看当前点券余额、使用情况和下次刷新时间
    """
    stats = enhanced_proposal_service.get_coupon_stats(user_id, tenant_id)

    return {
        "coupon_stats": stats
    }


@router.get("/coupons/transactions")
async def get_coupon_transactions(
    user_id: str = Query(...),
    tenant_id: str = Query(...),
    limit: int = Query(50, ge=1, le=200)
):
    """
    获取点券交易记录

    查看点券使用和刷新的详细记录
    """
    transactions = enhanced_proposal_service.get_coupon_transactions(user_id, tenant_id, limit)

    return {
        "total": len(transactions),
        "transactions": [
            {
                "id": t.id,
                "transaction_type": t.transaction_type,
                "amount": t.amount,
                "balance_after": t.balance_after,
                "description": t.description,
                "related_proposal_id": t.related_proposal_id,
                "created_at": t.created_at.isoformat()
            }
            for t in transactions
        ]
    }


@router.post("/coupons/use")
async def use_coupon(
    user_id: str = Query(...),
    tenant_id: str = Query(...),
    proposal_id: str = Query(...)
):
    """
    使用点券

    提交提案时需要消耗点券（防 spam 机制）
    """
    success = enhanced_proposal_service.use_coupon(user_id, tenant_id, proposal_id)
    if not success:
        # 获取点券本检查原因
        book = enhanced_proposal_service.get_or_create_coupon_book(user_id, tenant_id)
        if book.remaining_coupons < 1:
            raise HTTPException(
                status_code=400,
                detail=f"点券不足，当前剩余 {book.remaining_coupons} 点券，等待月度刷新或购买更多点券"
            )
        raise HTTPException(status_code=400, detail="无法使用点券")

    stats = enhanced_proposal_service.get_coupon_stats(user_id, tenant_id)

    return {
        "message": "点券使用成功",
        "remaining_coupons": stats['remaining_coupons']
    }


@router.post("/coupons/refund")
async def refund_coupon(
    user_id: str = Query(...),
    tenant_id: str = Query(...),
    proposal_id: str = Query(...),
    reason: str = Query(...)
):
    """
    退还点券

    当提案被拒绝或职位关闭时，可以退还点券
    """
    success = enhanced_proposal_service.refund_coupon(user_id, tenant_id, proposal_id, reason)
    if not success:
        raise HTTPException(status_code=400, detail="无法退还点券")

    stats = enhanced_proposal_service.get_coupon_stats(user_id, tenant_id)

    return {
        "message": f"点券已退还：{reason}",
        "remaining_coupons": stats['remaining_coupons']
    }


# ==================== 提案数据分析端点 ====================

@router.get("/analytics")
async def get_proposal_analytics(
    user_id: str = Query(...),
    period: Optional[str] = Query("last_30_days", description="分析周期")
):
    """
    获取提案数据分析

    包括接受率、响应率、趋势等统计信息
    """
    analytics = enhanced_proposal_service.analyze_proposals(user_id, period)

    return {
        "user_id": user_id,
        "period": period,
        "analytics": {
            "total_proposals": analytics.total_proposals,
            "pending_proposals": analytics.pending_proposals,
            "accepted_proposals": analytics.accepted_proposals,
            "rejected_proposals": analytics.rejected_proposals,
            "acceptance_rate": analytics.acceptance_rate,
            "response_rate": analytics.response_rate,
            "trend": analytics.trend
        }
    }


@router.get("/dashboard")
async def get_proposal_dashboard(
    user_id: str = Query(...)
):
    """
    获取提案仪表板

    综合展示提案相关的各项指标和建议
    """
    dashboard = enhanced_proposal_service.get_proposal_dashboard(user_id)

    return {
        "user_id": user_id,
        "dashboard": dashboard
    }


@router.get("/stats/breakdown")
async def get_proposal_stats_breakdown(
    user_id: str = Query(...)
):
    """
    获取提案统计详情
    """
    # 这里简化处理，实际应该从服务层获取更详细的分类统计
    return {
        "user_id": user_id,
        "breakdown": {
            "by_category": {},
            "by_job_type": {},
            "by_time_period": {}
        },
        "note": "详细分类统计功能开发中"
    }


# ==================== 批量操作端点 ====================

@router.post("/invitations/bulk-create")
async def bulk_create_invitations(
    job_posting_id: str = Query(...),
    invitee_ids: List[str] = Body(...),
    inviter_id: str = Query(...),
    tenant_id: str = Query(...),
    message: Optional[str] = Body(None),
    expires_days: int = Body(7)
):
    """
    批量创建邀请

    一次性邀请多个 AI 员工所有者参与投标
    """
    created_count = 0
    invitation_ids = []

    for invitee_id in invitee_ids:
        data = {
            'job_posting_id': job_posting_id,
            'invitee_id': invitee_id,
            'inviter_id': inviter_id,
            'tenant_id': tenant_id,
            'message': message,
            'expires_days': expires_days
        }
        invitation = enhanced_proposal_service.create_invitation(data)
        created_count += 1
        invitation_ids.append(invitation.id)

    return {
        "message": f"成功创建 {created_count} 条邀请",
        "invitation_ids": invitation_ids
    }


# ==================== 健康检查 ====================

@router.get("/health")
async def health_check():
    """
    增强提案服务健康检查
    """
    return {
        "status": "healthy",
        "service": "enhanced_proposal_service",
        "version": "v1.0",
        "total_templates": len(enhanced_proposal_service._templates),
        "total_invitations": len(enhanced_proposal_service._invitations),
        "total_coupon_books": len(enhanced_proposal_service._coupon_books)
    }
