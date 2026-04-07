"""
P7 - 用户贡献与社区 API

功能：
1. 用户提交商机/数据源/验证信息
2. 审核工作流
3. 社区投票
4. 积分系统
"""
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from config.database import get_db
from services.p7_contribution_service import get_contribution_service, ContributionService
from models.db_models import UserContributionDB


router = APIRouter(prefix="/api/p7", tags=["P7-用户贡献与社区"])


# ==================== 依赖注入 ====================

def get_current_user_id(x_user_id: str = Header(..., description="用户 ID")) -> str:
    """获取当前用户 ID（从请求头）"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="未授权")
    return x_user_id


def get_current_admin_user_id(
    x_user_id: str = Header(..., description="用户 ID"),
    x_admin_key: str = Header(None, description="管理员密钥"),
) -> str:
    """获取当前管理员用户 ID"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="未授权")
    # 简单管理员验证（生产环境应使用更复杂的鉴权）
    if x_admin_key != "admin_secret_key":  # 应该从环境变量读取
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return x_user_id


# ==================== 贡献管理 ====================

@router.post("/contributions", summary="提交贡献")
def create_contribution(
    contribution_type: str,
    title: str,
    description: str,
    content: dict = None,
    source_url: str = None,
    source_evidence: dict = None,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    用户提交贡献（商机、数据源、验证信息等）

    - **contribution_type**: 贡献类型 (opportunity/data_source/verification/correction)
    - **title**: 标题
    - **description**: 描述
    - **content**: 结构化内容（JSON）
    - **source_url**: 来源 URL
    - **source_evidence**: 证据材料（JSON）
    """
    service = get_contribution_service(db)
    try:
        contribution = service.create_contribution(
            user_id=user_id,
            contribution_type=contribution_type,
            title=title,
            description=description,
            content=content,
            source_url=source_url,
            source_evidence=source_evidence,
        )
        return {
            "success": True,
            "data": contribution.to_dict(),
            "message": "贡献已提交，等待审核",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/contributions", summary="获取贡献列表")
def list_contributions(
    status: str = Query(None, description="筛选状态"),
    contribution_type: str = Query(None, description="筛选类型"),
    user_id: str = Query(None, description="筛选用户"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """获取贡献列表（支持筛选）"""
    service = get_contribution_service(db)
    contributions = service.list_contributions(
        user_id=user_id,
        status=status,
        contribution_type=contribution_type,
        limit=limit,
        offset=offset,
    )
    return {
        "success": True,
        "data": [c.to_dict() for c in contributions],
        "total": len(contributions),
    }


@router.get("/contributions/{contribution_id}", summary="获取贡献详情")
def get_contribution(
    contribution_id: str,
    db: Session = Depends(get_db),
):
    """获取贡献详情"""
    service = get_contribution_service(db)
    contribution = service.get_contribution(contribution_id)
    if not contribution:
        raise HTTPException(status_code=404, detail="贡献不存在")
    return {
        "success": True,
        "data": contribution.to_dict(),
    }


# ==================== 审核管理（管理员） ====================

@router.post("/contributions/{contribution_id}/review", summary="审核贡献")
def review_contribution(
    contribution_id: str,
    status: str,
    review_notes: str = None,
    quality_score: float = Query(None, ge=0, le=100),
    user_id: str = Depends(get_current_admin_user_id),
    db: Session = Depends(get_db),
):
    """
    审核贡献（仅管理员）

    - **status**: 审核状态 (approved/rejected)
    - **review_notes**: 审核意见
    - **quality_score**: 质量评分 (0-100)
    """
    service = get_contribution_service(db)
    try:
        contribution = service.review_contribution(
            contribution_id=contribution_id,
            reviewer_id=user_id,
            status=status,
            review_notes=review_notes,
            quality_score=quality_score,
        )
        return {
            "success": True,
            "data": contribution.to_dict(),
            "message": f"贡献已{('通过' if status == 'approved' else '拒绝')}",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/contributions/{contribution_id}/adopt", summary="采纳贡献")
def adopt_contribution(
    contribution_id: str,
    opportunity_id: str,
    user_id: str = Depends(get_current_admin_user_id),
    db: Session = Depends(get_db),
):
    """
    采纳贡献（将用户提交的商机加入系统）

    - **opportunity_id**: 关联的商机 ID
    """
    service = get_contribution_service(db)
    try:
        contribution = service.adopt_contribution(
            contribution_id=contribution_id,
            opportunity_id=opportunity_id,
        )
        return {
            "success": True,
            "data": contribution.to_dict(),
            "message": "贡献已被采纳",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 社区投票 ====================

@router.post("/contributions/{contribution_id}/vote", summary="投票")
def vote_contribution(
    contribution_id: str,
    vote_type: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    对贡献进行投票

    - **vote_type**: 投票类型 (upvote/downvote)
    """
    if vote_type not in ["upvote", "downvote"]:
        raise HTTPException(status_code=400, detail="无效的投票类型")

    service = get_contribution_service(db)
    try:
        vote = service.vote_contribution(
            user_id=user_id,
            contribution_id=contribution_id,
            vote_type=vote_type,
        )
        return {
            "success": True,
            "data": vote.to_dict(),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 积分系统 ====================

@router.get("/points", summary="获取我的积分")
def get_my_points(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """获取当前用户的积分账户信息"""
    service = get_contribution_service(db)
    points_account = service.get_user_points(user_id)
    if not points_account:
        # 返回空账户
        return {
            "success": True,
            "data": {
                "user_id": user_id,
                "total_points": 0,
                "available_points": 0,
                "spent_points": 0,
                "reputation_level": "bronze",
                "reputation_score": 0.0,
                "contributions_count": 0,
                "approved_contributions_count": 0,
                "adopted_contributions_count": 0,
            },
        }
    return {
        "success": True,
        "data": points_account.to_dict(),
    }


@router.get("/points/transactions", summary="获取积分交易记录")
def get_points_transactions(
    limit: int = Query(50, ge=1, le=100),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """获取当前用户的积分交易记录"""
    service = get_contribution_service(db)
    transactions = service.get_points_transactions(user_id=user_id, limit=limit)
    return {
        "success": True,
        "data": [t.to_dict() for t in transactions],
        "total": len(transactions),
    }


# ==================== 统计数据 ====================

@router.get("/stats/summary", summary="获取贡献统计")
def get_stats_summary(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """获取用户贡献统计摘要"""
    service = get_contribution_service(db)

    # 获取用户所有贡献
    contributions = service.list_contributions(user_id=user_id, limit=1000)

    # 统计
    stats = {
        "user_id": user_id,
        "total_contributions": len(contributions),
        "by_status": {
            "pending": 0,
            "approved": 0,
            "rejected": 0,
        },
        "by_type": {},
        "adopted_count": 0,
        "total_votes": 0,
    }

    for c in contributions:
        # 按状态统计
        if c.status in stats["by_status"]:
            stats["by_status"][c.status] += 1

        # 按类型统计
        if c.contribution_type not in stats["by_type"]:
            stats["by_type"][c.contribution_type] = 0
        stats["by_type"][c.contribution_type] += 1

        # 采纳统计
        if c.is_adopted:
            stats["adopted_count"] += 1

        # 投票统计
        stats["total_votes"] += c.community_votes

    return {
        "success": True,
        "data": stats,
    }
