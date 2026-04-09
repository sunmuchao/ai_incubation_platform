"""
P7 安全风控 AI API

提供内容安全检测、用户风险评估、自动处置等接口。
"""
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional

from db.database import get_db
from auth.jwt import get_current_user
from db.models import UserDB
from services.safety_ai_service import SafetyAIService, get_safety_service, RiskLevel


router = APIRouter(prefix="/api/safety", tags=["safety"])


@router.post("/check-content")
async def check_content_safety(
    content: str = Body(..., description="待检查内容"),
    context_messages: Optional[List[Dict]] = Body(default=None, description="上下文消息"),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """
    检查内容安全性

    检测类型：
    - 骚扰内容
    - 诈骗风险
    - 不当内容
    - 垃圾信息

    返回：
    - is_safe: 是否安全
    - risk_level: 风险等级 (low/medium/high/critical)
    - risk_types: 风险类型列表
    - risk_score: 风险分数 0-100
    - action_suggestion: 建议处置动作
    """
    safety_service = get_safety_service(db)

    result = safety_service.check_content_safety(
        content=content,
        sender_id=current_user.id,
        context_messages=context_messages
    )

    return {
        "success": True,
        "data": result
    }


@router.get("/user-risk/{user_id}")
async def get_user_risk_assessment(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """
    获取用户风险评估

    评估维度：
    - 历史违规记录
    - 行为模式异常
    - 资料真实性

    注意：仅管理员可以查看他人风险评估
    """
    # 权限检查：只能查看自己的风险评估，或者是管理员
    if user_id != current_user.id:
        from utils.admin_check import require_admin
        require_admin(current_user)  # 管理员权限检查

    safety_service = get_safety_service(db)
    result = safety_service.assess_user_risk(user_id)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return {
        "success": True,
        "data": result
    }


@router.get("/stats")
async def get_safety_statistics(
    days: int = 7,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """
    获取安全统计

    返回指定天数内的安全事件统计
    """
    safety_service = get_safety_service(db)
    stats = safety_service.get_safety_stats(days=days)

    return {
        "success": True,
        "data": stats
    }


@router.post("/report-content")
async def report_content(
    reported_user_id: str = Body(..., description="被举报用户 ID"),
    content: str = Body(..., description="举报内容"),
    report_type: str = Body(..., description="举报类型：harassment/scam/spam/other"),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """
    举报不当内容

    用户可主动举报骚扰、诈骗等不良行为
    """
    from db.models import BehaviorEventDB
    import uuid

    # 记录举报事件
    event = BehaviorEventDB(
        id=str(uuid.uuid4()),
        user_id=reported_user_id,
        event_type="user_report",
        event_data={
            "reporter_id": current_user.id,
            "report_type": report_type,
            "content": content[:500]  # 限制长度
        }
    )
    db.add(event)
    db.commit()

    # 检查被举报用户的风险等级
    safety_service = get_safety_service(db)
    risk_assessment = safety_service.assess_user_risk(reported_user_id)

    # 如果风险等级高，自动采取行动
    action_taken = "none"
    if risk_assessment.get("risk_level") == RiskLevel.CRITICAL:
        # 自动临时封禁
        target_user = db.query(UserDB).filter(UserDB.id == reported_user_id).first()
        if target_user:
            target_user.is_active = False
            db.commit()
        action_taken = "auto_ban"
    elif risk_assessment.get("risk_level") == RiskLevel.HIGH:
        action_taken = "flagged_for_review"

    return {
        "success": True,
        "data": {
            "report_id": event.id,
            "risk_assessment": risk_assessment,
            "action_taken": action_taken
        },
        "message": "举报已受理，我们将尽快处理"
    }


@router.get("/checklist")
async def get_safety_checklist(
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """
    获取安全检查清单

    返回平台支持的安全检测类型和说明
    """
    return {
        "success": True,
        "data": {
            "risk_types": [
                {
                    "type": "harassment",
                    "name": "骚扰内容",
                    "description": "检测性骚扰、言语骚扰、威胁性语言等"
                },
                {
                    "type": "scam",
                    "name": "诈骗风险",
                    "description": "检测金钱诈骗、虚假身份、诱导私下联系等"
                },
                {
                    "type": "inappropriate_content",
                    "name": "不当内容",
                    "description": "检测色情、暴力、赌博、毒品等内容"
                },
                {
                    "type": "spam",
                    "name": "垃圾信息",
                    "description": "检测广告推广、URL 链接、联系方式等"
                }
            ],
            "risk_levels": [
                {"level": "low", "name": "低风险", "description": "内容安全，无需处理"},
                {"level": "medium", "name": "中风险", "description": "可能存在问题，建议警告"},
                {"level": "high", "name": "高风险", "description": "存在明显问题，建议限制"},
                {"level": "critical", "name": "严重风险", "description": "严重违规，建议封禁"}
            ],
            "actions": [
                {"action": "none", "name": "无操作"},
                {"action": "warning", "name": "发送警告"},
                {"action": "strong_warning", "name": "严重警告"},
                {"action": "temporary_ban", "name": "临时封禁"},
                {"action": "block_user_and_report", "name": "封禁并上报"}
            ]
        }
    }
