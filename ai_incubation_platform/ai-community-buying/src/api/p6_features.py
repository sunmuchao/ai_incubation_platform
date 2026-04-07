"""
P6 运营增强阶段 - API 路由

包含：
1. 团长考核 API
2. 售后服务 API
3. 签到积分 API
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import datetime

from config.database import get_db
from sqlalchemy.orm import Session
from models.p6_entities import (
    OrganizerAssessmentEntity, AssessmentLevel, OrganizerAssessmentStatus,
    AfterSalesOrderEntity, AfterSalesType, AfterSalesStatus
)
from services.p6_services import (
    OrganizerAssessmentService,
    AfterSalesService,
    SigninPointsService
)
from core.exceptions import AppException
from core.pagination import PaginatedResponse

# ====================  路由器定义  ====================

# 团长考核 API 路由
organizer_assessment_router = APIRouter(prefix="/api/organizer-assessment", tags=["团长考核"])

# 售后服务 API 路由
after_sales_router = APIRouter(prefix="/api/after-sales", tags=["售后服务"])

# 签到积分 API 路由
signin_points_router = APIRouter(prefix="/api/signin-points", tags=["签到积分"])


# ====================  Pydantic 模型  ====================

# --- 团长考核相关模型 ---

class AssessmentCreateRequest(BaseModel):
    """创建考核记录请求"""
    organizer_id: str = Field(..., description="团长 ID")
    assessment_period: str = Field(..., description="考核周期 (如 2026-01)")
    assessment_type: str = Field(default="monthly", description="考核类型")


class AssessmentScoreRequest(BaseModel):
    """提交考核分数请求"""
    gmv_score: float = Field(0, ge=0, le=100, description="GMV 得分")
    order_score: float = Field(0, ge=0, le=100, description="订单量得分")
    service_score: float = Field(0, ge=0, le=100, description="服务得分")
    complaint_score: float = Field(0, ge=0, le=100, description="投诉得分")
    fulfillment_score: float = Field(0, ge=0, le=100, description="履约得分")
    feedback: Optional[str] = Field(None, description="考核评语")


class AssessmentAppealRequest(BaseModel):
    """考核申诉请求"""
    appeal_reason: str = Field(..., description="申诉理由", min_length=10, max_length=512)


class AssessmentProcessAppealRequest(BaseModel):
    """处理申诉请求"""
    appeal_result: str = Field(..., description="申诉结果", min_length=10, max_length=512)


# --- 售后服务相关模型 ---

class AfterSalesCreateRequest(BaseModel):
    """创建售后申请请求"""
    order_id: str = Field(..., description="订单 ID")
    after_sales_type: str = Field(..., description="售后类型")
    refund_amount: Decimal = Field(..., gt=0, description="退款金额")
    apply_reason: str = Field(..., description="申请原因", max_length=512)
    apply_description: Optional[str] = Field(None, description="详细描述")
    apply_images: Optional[List[str]] = Field(None, description="凭证图片")


class AfterSalesReviewRequest(BaseModel):
    """售后审核请求"""
    approved: bool = Field(..., description="是否通过")
    review_opinion: str = Field(..., description="审核意见", max_length=512)


class AfterSalesReturnRequest(BaseModel):
    """确认退货请求"""
    tracking_no: str = Field(..., description="物流单号")
    carrier: str = Field(..., description="物流公司")


class AfterSalesRefundRequest(BaseModel):
    """执行退款请求"""
    refund_method: str = Field(default="original", description="退款方式")


# --- 签到积分相关模型 ---

class SigninResponse(BaseModel):
    """签到响应"""
    success: bool
    message: str
    signed: bool
    points_earned: Optional[int] = None
    continuous_days: Optional[int] = None
    bonus_type: Optional[str] = None
    current_points: Optional[int] = None


class PointsUseRequest(BaseModel):
    """积分消费请求"""
    points_amount: int = Field(..., gt=0, description="消费积分")
    source: str = Field(..., description="消费来源")
    description: Optional[str] = Field(None, description="描述")


class PointsRedeemRequest(BaseModel):
    """积分兑换请求"""
    item_id: str = Field(..., description="商品 ID")


# ====================  团长考核 API  ====================

@organizer_assessment_router.post(
    "",
    response_model=Dict[str, Any],
    summary="创建考核记录"
)
def create_assessment(
    request: AssessmentCreateRequest,
    db: Session = Depends(get_db)
):
    """创建团长考核记录"""
    service = OrganizerAssessmentService(db)
    service.set_request_context(request_id="auto", user_id="admin")

    assessment = service.create_assessment(
        organizer_id=request.organizer_id,
        assessment_period=request.assessment_period,
        assessment_type=request.assessment_type
    )

    return {
        "success": True,
        "message": "考核记录创建成功",
        "data": {
            "id": assessment.id,
            "organizer_id": assessment.organizer_id,
            "assessment_period": assessment.assessment_period,
            "status": assessment.status.value
        }
    }


@organizer_assessment_router.post(
    "/{assessment_id}/calculate",
    response_model=Dict[str, Any],
    summary="计算考核分数"
)
def calculate_scores(
    assessment_id: str,
    db: Session = Depends(get_db)
):
    """计算团长考核各项得分"""
    service = OrganizerAssessmentService(db)
    service.set_request_context(request_id="auto", user_id="admin")

    assessment = service.get_assessment(assessment_id)
    if not assessment:
        raise AppException(
            code="ASSESSMENT_NOT_FOUND",
            message="考核记录不存在",
            status=404
        )

    scores = service.calculate_scores(
        organizer_id=assessment.organizer_id,
        assessment_period=assessment.assessment_period
    )

    return {
        "success": True,
        "message": "分数计算完成",
        "data": scores
    }


@organizer_assessment_router.put(
    "/{assessment_id}/submit",
    response_model=Dict[str, Any],
    summary="提交考核结果"
)
def submit_assessment(
    assessment_id: str,
    request: AssessmentScoreRequest,
    db: Session = Depends(get_db)
):
    """提交考核结果"""
    service = OrganizerAssessmentService(db)
    service.set_request_context(request_id="auto", user_id="admin")

    scores = {
        "gmv_score": request.gmv_score,
        "order_score": request.order_score,
        "service_score": request.service_score,
        "complaint_score": request.complaint_score,
        "fulfillment_score": request.fulfillment_score,
        "total_score": (
            request.gmv_score * 0.30 +
            request.order_score * 0.25 +
            request.service_score * 0.20 +
            request.complaint_score * 0.15 +
            request.fulfillment_score * 0.10
        )
    }

    # 根据总分确定等级
    total = scores["total_score"]
    if total >= 90:
        level = AssessmentLevel.EXCELLENT
    elif total >= 75:
        level = AssessmentLevel.GOOD
    elif total >= 60:
        level = AssessmentLevel.PASS
    else:
        level = AssessmentLevel.FAIL

    scores["assessment_level"] = level

    assessment = service.submit_assessment(
        assessment_id=assessment_id,
        scores=scores,
        feedback=request.feedback,
        assessor_id="admin"
    )

    return {
        "success": True,
        "message": "考核结果提交成功",
        "data": {
            "id": assessment.id,
            "total_score": float(assessment.total_score),
            "assessment_level": assessment.assessment_level.value,
            "bonus_points": assessment.bonus_points,
            "bonus_amount": float(assessment.bonus_amount)
        }
    }


@organizer_assessment_router.get(
    "/{assessment_id}",
    response_model=Dict[str, Any],
    summary="获取考核详情"
)
def get_assessment(
    assessment_id: str,
    db: Session = Depends(get_db)
):
    """获取考核记录详情"""
    service = OrganizerAssessmentService(db)
    assessment = service.get_assessment(assessment_id)

    if not assessment:
        raise AppException(
            code="ASSESSMENT_NOT_FOUND",
            message="考核记录不存在",
            status=404
        )

    return {
        "success": True,
        "data": {
            "id": assessment.id,
            "organizer_id": assessment.organizer_id,
            "assessment_period": assessment.assessment_period,
            "assessment_type": assessment.assessment_type,
            "total_score": float(assessment.total_score) if assessment.total_score else 0,
            "assessment_level": assessment.assessment_level.value if assessment.assessment_level else None,
            "status": assessment.status.value,
            "gmv_score": float(assessment.gmv_score) if assessment.gmv_score else 0,
            "order_score": float(assessment.order_score) if assessment.order_score else 0,
            "service_score": float(assessment.service_score) if assessment.service_score else 0,
            "complaint_score": float(assessment.complaint_score) if assessment.complaint_score else 0,
            "fulfillment_score": float(assessment.fulfillment_score) if assessment.fulfillment_score else 0,
            "bonus_points": assessment.bonus_points,
            "bonus_amount": float(assessment.bonus_amount) if assessment.bonus_amount else 0,
            "feedback": assessment.feedback,
            "assessed_at": assessment.assessed_at.isoformat() if assessment.assessed_at else None,
            "created_at": assessment.created_at.isoformat()
        }
    }


@organizer_assessment_router.get(
    "",
    response_model=Dict[str, Any],
    summary="获取考核列表"
)
def list_assessments(
    organizer_id: Optional[str] = Query(None, description="团长 ID"),
    status: Optional[str] = Query(None, description="考核状态"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db)
):
    """获取考核记录列表"""
    service = OrganizerAssessmentService(db)

    status_enum = None
    if status:
        try:
            status_enum = OrganizerAssessmentStatus(status)
        except ValueError:
            pass

    result = service.list_assessments(
        organizer_id=organizer_id,
        status=status_enum,
        page=page,
        page_size=page_size
    )

    return {
        "success": True,
        "data": {
            "total": result["total"],
            "page": result["page"],
            "page_size": result["page_size"],
            "items": [
                {
                    "id": a.id,
                    "organizer_id": a.organizer_id,
                    "assessment_period": a.assessment_period,
                    "total_score": float(a.total_score) if a.total_score else 0,
                    "assessment_level": a.assessment_level.value if a.assessment_level else None,
                    "status": a.status.value,
                    "created_at": a.created_at.isoformat()
                }
                for a in result["assessments"]
            ]
        }
    }


@organizer_assessment_router.post(
    "/{assessment_id}/appeal",
    response_model=Dict[str, Any],
    summary="申诉考核结果"
)
def appeal_assessment(
    assessment_id: str,
    request: AssessmentAppealRequest,
    db: Session = Depends(get_db)
):
    """申诉考核结果"""
    service = OrganizerAssessmentService(db)
    service.set_request_context(request_id="auto", user_id="user")

    assessment = service.appeal_assessment(
        assessment_id=assessment_id,
        appeal_reason=request.appeal_reason,
        user_id="user"
    )

    return {
        "success": True,
        "message": "申诉提交成功",
        "data": {
            "id": assessment.id,
            "status": assessment.status.value
        }
    }


@organizer_assessment_router.post(
    "/{assessment_id}/process-appeal",
    response_model=Dict[str, Any],
    summary="处理申诉"
)
def process_appeal(
    assessment_id: str,
    request: AssessmentProcessAppealRequest,
    db: Session = Depends(get_db)
):
    """处理申诉"""
    service = OrganizerAssessmentService(db)

    assessment = service.process_appeal(
        assessment_id=assessment_id,
        appeal_result=request.appeal_result,
        operator_id="admin"
    )

    return {
        "success": True,
        "message": "申诉处理完成",
        "data": {
            "id": assessment.id,
            "status": assessment.status.value,
            "appeal_result": assessment.appeal_result
        }
    }


# ====================  售后服务 API  ====================

@after_sales_router.post(
    "",
    response_model=Dict[str, Any],
    summary="创建售后申请"
)
def create_after_sales(
    request: AfterSalesCreateRequest,
    db: Session = Depends(get_db)
):
    """用户创建售后申请"""
    service = AfterSalesService(db)
    service.set_request_context(request_id="auto", user_id=request.order_id)

    try:
        after_sales_type = AfterSalesType(request.after_sales_type)
    except ValueError:
        raise AppException(
            code="AFTER_SALES_TYPE_INVALID",
            message=f"无效的售后类型：{request.after_sales_type}",
            status=400
        )

    after_sales = service.create_after_sales(
        order_id=request.order_id,
        user_id="user",  # 实际应从认证上下文获取
        after_sales_type=after_sales_type,
        refund_amount=request.refund_amount,
        apply_reason=request.apply_reason,
        apply_description=request.apply_description,
        apply_images=request.apply_images
    )

    return {
        "success": True,
        "message": "售后申请创建成功",
        "data": {
            "id": after_sales.id,
            "after_sales_no": after_sales.after_sales_no,
            "status": after_sales.status.value,
            "refund_amount": float(after_sales.refund_amount)
        }
    }


@after_sales_router.get(
    "/{after_sales_id}",
    response_model=Dict[str, Any],
    summary="获取售后详情"
)
def get_after_sales(
    after_sales_id: str,
    db: Session = Depends(get_db)
):
    """获取售后单详情"""
    service = AfterSalesService(db)
    after_sales = service.get_after_sales(after_sales_id)

    if not after_sales:
        raise AppException(
            code="AFTER_SALES_NOT_FOUND",
            message="售后单不存在",
            status=404
        )

    # 获取日志
    logs = service.get_after_sales_logs(after_sales_id)

    return {
        "success": True,
        "data": {
            "id": after_sales.id,
            "after_sales_no": after_sales.after_sales_no,
            "order_id": after_sales.order_id,
            "user_id": after_sales.user_id,
            "organizer_id": after_sales.organizer_id,
            "after_sales_type": after_sales.after_sales_type.value,
            "status": after_sales.status.value,
            "order_amount": float(after_sales.order_amount),
            "refund_amount": float(after_sales.refund_amount),
            "apply_reason": after_sales.apply_reason,
            "apply_description": after_sales.apply_description,
            "apply_images": after_sales.apply_images.split(",") if after_sales.apply_images else [],
            "review_opinion": after_sales.review_opinion,
            "return_tracking_no": after_sales.return_tracking_no,
            "return_carrier": after_sales.return_carrier,
            "created_at": after_sales.created_at.isoformat(),
            "logs": [
                {
                    "action": log.action,
                    "old_status": log.old_status,
                    "new_status": log.new_status,
                    "remark": log.remark,
                    "created_at": log.created_at.isoformat()
                }
                for log in logs
            ]
        }
    }


@after_sales_router.get(
    "",
    response_model=Dict[str, Any],
    summary="获取售后列表"
)
def list_after_sales(
    user_id: Optional[str] = Query(None, description="用户 ID"),
    organizer_id: Optional[str] = Query(None, description="团长 ID"),
    status: Optional[str] = Query(None, description="售后状态"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db)
):
    """获取售后单列表"""
    service = AfterSalesService(db)

    status_enum = None
    if status:
        try:
            status_enum = AfterSalesStatus(status)
        except ValueError:
            pass

    result = service.list_after_sales(
        user_id=user_id,
        organizer_id=organizer_id,
        status=status_enum,
        page=page,
        page_size=page_size
    )

    return {
        "success": True,
        "data": {
            "total": result["total"],
            "page": result["page"],
            "page_size": result["page_size"],
            "items": [
                {
                    "id": a.id,
                    "after_sales_no": a.after_sales_no,
                    "order_id": a.order_id,
                    "after_sales_type": a.after_sales_type.value,
                    "status": a.status.value,
                    "refund_amount": float(a.refund_amount),
                    "created_at": a.created_at.isoformat()
                }
                for a in result["items"]
            ]
        }
    }


@after_sales_router.post(
    "/{after_sales_id}/review",
    response_model=Dict[str, Any],
    summary="审核售后申请"
)
def review_after_sales(
    after_sales_id: str,
    request: AfterSalesReviewRequest,
    db: Session = Depends(get_db)
):
    """审核售后申请"""
    service = AfterSalesService(db)

    after_sales = service.review_after_sales(
        after_sales_id=after_sales_id,
        reviewer_id="admin",
        approved=request.approved,
        review_opinion=request.review_opinion
    )

    return {
        "success": True,
        "message": f"审核{'通过' if request.approved else '拒绝'}",
        "data": {
            "id": after_sales.id,
            "status": after_sales.status.value
        }
    }


@after_sales_router.post(
    "/{after_sales_id}/return",
    response_model=Dict[str, Any],
    summary="确认退货"
)
def confirm_return(
    after_sales_id: str,
    request: AfterSalesReturnRequest,
    db: Session = Depends(get_db)
):
    """用户确认退货"""
    service = AfterSalesService(db)

    after_sales = service.confirm_return(
        after_sales_id=after_sales_id,
        tracking_no=request.tracking_no,
        carrier=request.carrier,
        user_id="user"
    )

    return {
        "success": True,
        "message": "退货信息已记录",
        "data": {
            "id": after_sales.id,
            "status": after_sales.status.value,
            "tracking_no": after_sales.return_tracking_no
        }
    }


@after_sales_router.post(
    "/{after_sales_id}/refund",
    response_model=Dict[str, Any],
    summary="执行退款"
)
def refund_after_sales(
    after_sales_id: str,
    request: AfterSalesRefundRequest = None,
    db: Session = Depends(get_db)
):
    """执行退款"""
    service = AfterSalesService(db)

    refund_method = request.refund_method if request else "original"

    after_sales = service.refund_after_sales(
        after_sales_id=after_sales_id,
        operator_id="admin",
        refund_method=refund_method
    )

    return {
        "success": True,
        "message": "退款成功",
        "data": {
            "id": after_sales.id,
            "status": after_sales.status.value,
            "refund_amount": float(after_sales.refund_amount),
            "transaction_no": after_sales.refund_transaction_no
        }
    }


@after_sales_router.post(
    "/{after_sales_id}/complete",
    response_model=Dict[str, Any],
    summary="完成售后单"
)
def complete_after_sales(
    after_sales_id: str,
    db: Session = Depends(get_db)
):
    """完成售后单"""
    service = AfterSalesService(db)

    after_sales = service.complete_after_sales(
        after_sales_id=after_sales_id,
        operator_id="admin"
    )

    return {
        "success": True,
        "message": "售后单已完成",
        "data": {
            "id": after_sales.id,
            "status": after_sales.status.value
        }
    }


# ====================  签到积分 API  ====================

@signin_points_router.post(
    "/signin",
    response_model=SigninResponse,
    summary="用户签到"
)
def user_signin(
    user_id: str = Query(..., description="用户 ID"),
    db: Session = Depends(get_db)
):
    """用户每日签到获取积分"""
    service = SigninPointsService(db)
    service.set_request_context(request_id="auto", user_id=user_id)

    result = service.signin(user_id=user_id)

    return SigninResponse(**result)


@signin_points_router.get(
    "/account",
    response_model=Dict[str, Any],
    summary="获取积分账户"
)
def get_points_account(
    user_id: str = Query(..., description="用户 ID"),
    db: Session = Depends(get_db)
):
    """获取用户积分账户信息"""
    service = SigninPointsService(db)
    account = service.get_account(user_id)

    if not account:
        return {
            "success": True,
            "data": {
                "user_id": user_id,
                "available_points": 0,
                "total_points": 0,
                "used_points": 0,
                "level": "normal"
            }
        }

    return {
        "success": True,
        "data": {
            "user_id": account.user_id,
            "available_points": account.available_points,
            "total_points": account.total_points,
            "used_points": account.used_points,
            "level": account.level
        }
    }


@signin_points_router.get(
    "/calendar",
    response_model=Dict[str, Any],
    summary="获取签到日历"
)
def get_signin_calendar(
    user_id: str = Query(..., description="用户 ID"),
    year: int = Query(..., description="年份"),
    month: int = Query(..., ge=1, le=12, description="月份"),
    db: Session = Depends(get_db)
):
    """获取用户月度签到日历"""
    service = SigninPointsService(db)
    records = service.get_signin_calendar(user_id, year, month)

    return {
        "success": True,
        "data": {
            "year": year,
            "month": month,
            "signin_days": [r.signin_date for r in records],
            "total_days": len(records)
        }
    }


@signin_points_router.get(
    "/transactions",
    response_model=Dict[str, Any],
    summary="获取积分流水"
)
def get_transaction_history(
    user_id: str = Query(..., description="用户 ID"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db)
):
    """获取用户积分流水历史"""
    service = SigninPointsService(db)
    result = service.get_transaction_history(user_id, page, page_size)

    return {
        "success": True,
        "data": {
            "total": result["total"],
            "page": result["page"],
            "page_size": result["page_size"],
            "items": [
                {
                    "id": t.id,
                    "transaction_type": t.transaction_type,
                    "points_amount": t.points_amount,
                    "balance_after": t.balance_after,
                    "source": t.source,
                    "description": t.description,
                    "created_at": t.created_at.isoformat()
                }
                for t in result["items"]
            ]
        }
    }


@signin_points_router.post(
    "/use",
    response_model=Dict[str, Any],
    summary="消费积分"
)
def use_points(
    user_id: str = Query(..., description="用户 ID"),
    request: PointsUseRequest = Body(...),
    db: Session = Depends(get_db)
):
    """消费积分"""
    service = SigninPointsService(db)

    result = service.use_points(
        user_id=user_id,
        points_amount=request.points_amount,
        source=request.source,
        description=request.description
    )

    return {
        "success": result["success"],
        "message": result["message"],
        "data": result
    }


@signin_points_router.get(
    "/rules",
    response_model=Dict[str, Any],
    summary="获取积分规则"
)
def get_points_rules(
    db: Session = Depends(get_db)
):
    """获取积分规则列表"""
    service = SigninPointsService(db)
    rules = service.get_points_rules()

    return {
        "success": True,
        "data": [
            {
                "id": r.id,
                "rule_name": r.rule_name,
                "rule_type": r.rule_type,
                "points_value": r.points_value,
                "daily_limit": r.daily_limit,
                "description": r.description
            }
            for r in rules
        ]
    }


@signin_points_router.get(
    "/mall/items",
    response_model=Dict[str, Any],
    summary="获取积分商城商品"
)
def get_mall_items(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db)
):
    """获取积分商城商品列表"""
    service = SigninPointsService(db)
    result = service.get_mall_items(page, page_size)

    return {
        "success": True,
        "data": {
            "total": result["total"],
            "page": result["page"],
            "page_size": result["page_size"],
            "items": [
                {
                    "id": i.id,
                    "item_name": i.item_name,
                    "item_type": i.item_type,
                    "item_description": i.item_description,
                    "points_price": i.points_price,
                    "stock_quantity": i.stock_quantity,
                    "redeem_limit": i.redeem_limit,
                    "redeem_count": i.redeem_count,
                    "image_url": i.image_url
                }
                for i in result["items"]
            ]
        }
    }


@signin_points_router.post(
    "/mall/redeem",
    response_model=Dict[str, Any],
    summary="兑换积分商品"
)
def redeem_item(
    user_id: str = Query(..., description="用户 ID"),
    request: PointsRedeemRequest = Body(...),
    db: Session = Depends(get_db)
):
    """使用积分兑换商品"""
    service = SigninPointsService(db)

    result = service.redeem_item(
        user_id=user_id,
        item_id=request.item_id
    )

    return {
        "success": result["success"],
        "message": result["message"],
        "data": result
    }


@signin_points_router.get(
    "/mall/history",
    response_model=Dict[str, Any],
    summary="获取兑换历史"
)
def get_redemption_history(
    user_id: str = Query(..., description="用户 ID"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db)
):
    """获取用户积分兑换历史"""
    service = SigninPointsService(db)
    result = service.get_redemption_history(user_id, page, page_size)

    return {
        "success": True,
        "data": {
            "total": result["total"],
            "page": result["page"],
            "page_size": result["page_size"],
            "items": [
                {
                    "id": r.id,
                    "redemption_no": r.redemption_no,
                    "item_name": r.item_name,
                    "points_used": r.points_used,
                    "quantity": r.quantity,
                    "status": r.status,
                    "created_at": r.created_at.isoformat()
                }
                for r in result["items"]
            ]
        }
    }
