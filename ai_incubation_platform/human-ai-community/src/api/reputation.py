"""
声誉系统 API 端点

提供声誉查询、排行榜、恢复申请等功能
"""
from fastapi import APIRouter, HTTPException, Query, Body, Depends, Request
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.p14_reputation import (
    ReputationLevel, ReputationRankingType, ReputationDimension,
    BehaviorType, REPUTATION_PRIVILEGES
)
from services.reputation_service import get_reputation_service, ReputationService
from middleware.api_auth import verify_api_key, APIAuthMiddleware
from models.member import CommunityMember

router = APIRouter(prefix="/api/reputation", tags=["Reputation"])


# ==================== 声誉查询 ====================

@router.get("/me")
async def get_my_reputation(
    current_user: CommunityMember = Depends(verify_api_key)
):
    """获取当前用户的声誉信息"""
    async for db in get_db_session():
        service = get_reputation_service(db)
        reputation = await service.get_or_create_reputation(
            current_user.id,
            "human" if current_user.member_type.value == "human" else "ai"
        )

        return {
            "member_id": current_user.id,
            "member_name": current_user.name,
            "member_type": current_user.member_type.value,
            "total_score": reputation.total_score,
            "level": reputation.level,
            "dimension_scores": {
                "content_quality": reputation.content_quality_score,
                "community_contribution": reputation.community_contribution_score,
                "collaboration": reputation.collaboration_score,
                "trustworthiness": reputation.trustworthiness_score,
            },
            "statistics": {
                "total_posts": reputation.total_posts,
                "total_comments": reputation.total_comments,
                "total_upvotes_received": reputation.total_upvotes_received,
                "total_downvotes_received": reputation.total_downvotes_received,
                "helpful_actions": reputation.helpful_actions,
                "violation_actions": reputation.violation_actions,
                "positive_actions": reputation.positive_actions,
                "negative_actions": reputation.negative_actions,
            },
            "probation_mode": reputation.probation_mode,
            "probation_end_date": reputation.probation_end_date.isoformat() if reputation.probation_end_date else None,
            "restoration_progress": reputation.restoration_progress,
        }


@router.get("/{member_id}")
async def get_member_reputation(
    member_id: str,
    current_user: CommunityMember = Depends(verify_api_key)
):
    """获取指定成员的声誉信息"""
    async for db in get_db_session():
        service = get_reputation_service(db)
        reputation = await service.get_by_member_id(member_id)

        if not reputation:
            raise HTTPException(status_code=404, detail="声誉记录不存在")

        return {
            "member_id": reputation.member_id,
            "member_type": reputation.member_type,
            "total_score": reputation.total_score,
            "level": reputation.level,
            "dimension_scores": {
                "content_quality": reputation.content_quality_score,
                "community_contribution": reputation.community_contribution_score,
                "collaboration": reputation.collaboration_score,
                "trustworthiness": reputation.trustworthiness_score,
            },
            "statistics": {
                "total_posts": reputation.total_posts,
                "total_comments": reputation.total_comments,
                "total_upvotes_received": reputation.total_upvotes_received,
                "helpful_actions": reputation.helpful_actions,
                "positive_actions": reputation.positive_actions,
                "negative_actions": reputation.negative_actions,
            },
        }


@router.get("/members/list")
async def list_members_reputation(
    level: Optional[ReputationLevel] = Query(default=None),
    min_score: Optional[int] = Query(default=None, ge=0, le=1000),
    max_score: Optional[int] = Query(default=None, ge=0, le=1000),
    member_type: Optional[str] = Query(default=None, description="成员类型：human/ai"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: CommunityMember = Depends(verify_api_key)
):
    """获取成员声誉列表"""
    async for db in get_db_session():
        service = get_reputation_service(db)
        members = await service.list_members(
            level=level,
            min_score=min_score,
            max_score=max_score,
            member_type=member_type,
            limit=limit,
            offset=offset
        )

        return {
            "total": len(members),
            "offset": offset,
            "members": [
                {
                    "member_id": m.member_id,
                    "member_type": m.member_type,
                    "total_score": m.total_score,
                    "level": m.level,
                    "content_quality_score": m.content_quality_score,
                    "community_contribution_score": m.community_contribution_score,
                }
                for m in members
            ]
        }


# ==================== 权益查询 ====================

@router.get("/privileges")
async def get_all_privileges(
    current_user: CommunityMember = Depends(verify_api_key)
):
    """获取所有声誉等级对应的权益"""
    privileges = {}
    for level, priv in REPUTATION_PRIVILEGES.items():
        privileges[level.value] = {
            "min_score": priv.min_score,
            "max_score": priv.max_score,
            "privileges": priv.privileges,
            "description": priv.description,
        }

    return {"privileges": privileges}


@router.get("/my-privileges")
async def get_my_privileges(
    current_user: CommunityMember = Depends(verify_api_key)
):
    """获取当前用户的权益"""
    async for db in get_db_session():
        service = get_reputation_service(db)
        privileges = await service.get_privileges(current_user.id)

        return privileges


# ==================== 排行榜 ====================

@router.get("/ranking")
async def get_reputation_ranking(
    ranking_type: ReputationRankingType = Query(
        default=ReputationRankingType.OVERALL,
        description="排行榜类型"
    ),
    member_type: Optional[str] = Query(
        default=None,
        description="成员类型过滤：human/ai"
    ),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: CommunityMember = Depends(verify_api_key)
):
    """获取声誉排行榜"""
    async for db in get_db_session():
        service = get_reputation_service(db)
        rankings = await service.get_ranking(
            ranking_type=ranking_type,
            member_type=member_type,
            limit=limit,
            offset=offset
        )

        return {
            "ranking_type": ranking_type.value,
            "member_type_filter": member_type,
            "total": len(rankings),
            "offset": offset,
            "rankings": [
                {
                    "rank": r.rank,
                    "member_id": r.member_id,
                    "member_name": r.member_name,
                    "member_type": r.member_type,
                    "total_score": r.total_score,
                    "level": r.level.value,
                    "content_quality_score": r.content_quality_score,
                    "community_contribution_score": r.community_contribution_score,
                    "collaboration_score": r.collaboration_score,
                    "trustworthiness_score": r.trustworthiness_score,
                    "total_posts": r.total_posts,
                    "total_upvotes_received": r.total_upvotes_received,
                    "positive_rate": r.positive_rate,
                }
                for r in rankings
            ]
        }


# ==================== 行为日志 ====================

@router.get("/behavior-logs")
async def get_behavior_logs(
    member_id: Optional[str] = Query(default=None),
    is_positive: Optional[bool] = Query(default=None),
    dimension: Optional[ReputationDimension] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: CommunityMember = Depends(verify_api_key)
):
    """获取行为日志（管理员可查看日志）"""
    # 检查权限：只能查看自己的日志，或者是管理员
    if current_user.role not in ["admin", "moderator"]:
        member_id = current_user.id

    from db.models import DBReputationBehaviorLog
    from db.manager import db_manager
    from sqlalchemy import select, and_

    async for db in db_manager.get_session():
        query = select(DBReputationBehaviorLog)
        conditions = []

        if member_id:
            conditions.append(DBReputationBehaviorLog.member_id == member_id)
        if is_positive is not None:
            conditions.append(DBReputationBehaviorLog.is_positive == is_positive)
        if dimension:
            conditions.append(DBReputationBehaviorLog.dimension_affected == dimension.value)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(DBReputationBehaviorLog.created_at.desc())
        query = query.offset(offset).limit(limit)

        result = await db.execute(query)
        logs = result.scalars().all()

        return {
            "total": len(logs),
            "offset": offset,
            "logs": [
                {
                    "id": log.id,
                    "member_id": log.member_id,
                    "behavior_type": log.behavior_type,
                    "is_positive": log.is_positive,
                    "description": log.description,
                    "content_id": log.content_id,
                    "content_type": log.content_type,
                    "score_delta": log.score_delta,
                    "dimension_affected": log.dimension_affected,
                    "created_at": log.created_at.isoformat(),
                }
                for log in logs
            ]
        }


# ==================== 声誉恢复 ====================

@router.post("/restoration/request")
async def request_restoration(
    reason: str = Body(..., embed=True, description="恢复申请原因"),
    commitment_actions: List[str] = Body(default=[], description="承诺完成的恢复动作"),
    current_user: CommunityMember = Depends(verify_api_key)
):
    """申请声誉恢复"""
    async for db in get_db_session():
        service = get_reputation_service(db)

        # 检查是否符合申请条件（分数低于 300 才能申请）
        reputation = await service.get_by_member_id(current_user.id)
        if reputation and reputation.total_score >= 300:
            raise HTTPException(
                status_code=400,
                detail="声誉分数高于 300，不符合恢复申请条件"
            )

        restoration = await service.create_restoration_request(
            member_id=current_user.id,
            reason=reason,
            commitment_actions=commitment_actions
        )

        return {
            "success": True,
            "restoration_id": restoration.id,
            "status": restoration.status,
            "restoration_actions": restoration.restoration_actions,
            "target_score": restoration.target_score,
        }


@router.get("/restoration/{restoration_id}")
async def get_restoration_status(
    restoration_id: str,
    current_user: CommunityMember = Depends(verify_api_key)
):
    """获取恢复申请状态"""
    from db.models import DBReputationRestoration
    from db.manager import db_manager
    from sqlalchemy import select

    async for db in db_manager.get_session():
        result = await db.execute(
            select(DBReputationRestoration).where(
                DBReputationRestoration.id == restoration_id
            )
        )
        restoration = result.scalar_one_or_none()

        if not restoration:
            raise HTTPException(status_code=404, detail="恢复记录不存在")

        # 检查权限
        if restoration.member_id != current_user.id and current_user.role not in ["admin", "moderator"]:
            raise HTTPException(status_code=403, detail="无权查看此恢复记录")

        return {
            "restoration_id": restoration.id,
            "status": restoration.status,
            "previous_score": restoration.previous_score,
            "previous_level": restoration.previous_level,
            "reason": restoration.reason,
            "restoration_actions": restoration.restoration_actions,
            "completed_actions": restoration.completed_actions,
            "progress": restoration.progress,
            "target_score": restoration.target_score,
            "created_at": restoration.created_at.isoformat(),
            "completed_at": restoration.completed_at.isoformat() if restoration.completed_at else None,
            "reviewer_note": restoration.reviewer_note,
        }


@router.post("/restoration/{restoration_id}/complete-action")
async def complete_restoration_action(
    restoration_id: str,
    action: str = Body(..., embed=True, description="要完成的恢复动作"),
    current_user: CommunityMember = Depends(verify_api_key)
):
    """完成恢复动作"""
    async for db in get_db_session():
        service = get_reputation_service(db)

        # 检查权限
        restoration_result = await db.execute(
            select(DBReputationRestoration).where(
                DBReputationRestoration.id == restoration_id
            )
        )
        restoration = restoration_result.scalar_one_or_none()

        if not restoration:
            raise HTTPException(status_code=404, detail="恢复记录不存在")

        if restoration.member_id != current_user.id and current_user.role not in ["admin", "moderator"]:
            raise HTTPException(status_code=403, detail="无权操作此恢复记录")

        try:
            updated = await service.complete_restoration_action(restoration_id, action)

            return {
                "success": True,
                "restoration_id": restoration_id,
                "action": action,
                "progress": updated.progress,
                "status": updated.status,
                "completed_actions": updated.completed_actions,
            }
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))


# ==================== 统计信息 ====================

@router.get("/statistics")
async def get_reputation_statistics(
    current_user: CommunityMember = Depends(verify_api_key)
):
    """获取声誉系统统计信息（管理员专用）"""
    if current_user.role not in ["admin", "moderator"]:
        raise HTTPException(status_code=403, detail="需要管理员权限")

    async for db in get_db_session():
        service = get_reputation_service(db)
        stats = await service.get_statistics()

        return stats


# ==================== 管理员功能 ====================

@router.post("/admin/{member_id}/update-score")
async def admin_update_score(
    member_id: str,
    score_delta: int = Body(..., embed=True, description="分数变化量"),
    reason: str = Body(..., embed=True, description="调整原因"),
    current_user: CommunityMember = Depends(verify_api_key)
):
    """管理员手动调整声誉分数"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")

    async for db in get_db_session():
        service = get_reputation_service(db)

        reputation = await service.get_by_member_id(member_id)
        if not reputation:
            raise HTTPException(status_code=404, detail="声誉记录不存在")

        old_score = reputation.total_score
        new_score = max(0, min(1000, old_score + score_delta))
        reputation.total_score = new_score

        # 更新等级
        new_level = service._calculate_level(new_score)
        reputation.level = new_level.value

        await db.commit()
        await db.refresh(reputation)

        # 记录管理员操作日志
        logger.info(
            f"管理员 {current_user.id} 调整用户 {member_id} 声誉分数："
            f"{old_score} -> {new_score}, 原因：{reason}"
        )

        return {
            "success": True,
            "member_id": member_id,
            "old_score": old_score,
            "new_score": new_score,
            "new_level": new_level.value,
            "reason": reason,
        }


# 辅助函数
async def get_db_session():
    """获取数据库会话"""
    from db.manager import db_manager
    async for db in db_manager.get_session():
        yield db
