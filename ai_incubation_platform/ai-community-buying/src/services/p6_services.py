"""
P6 运营增强阶段 - 业务逻辑服务

包含：
1. 团长考核服务 (OrganizerAssessmentService)
2. 售后服务 (AfterSalesService)
3. 签到积分服务 (SigninPointsService)
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
from uuid import uuid4
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, extract

from models.p6_entities import (
    OrganizerAssessmentEntity, AssessmentLevel, OrganizerAssessmentStatus,
    AfterSalesOrderEntity, AfterSalesType, AfterSalesStatus, AfterSalesLogEntity,
    SigninCalendarEntity, PointsAccountEntity, PointsTransactionEntity,
    PointsRuleEntity, PointsMallItemEntity, PointsRedemptionEntity
)
from models.entities import OrderEntity, GroupBuyEntity
from core.exceptions import AppException

logger = logging.getLogger(__name__)


# ==================== 团长考核服务 ====================

class OrganizerAssessmentService:
    """团长考核服务"""

    # 考核指标权重
    WEIGHTS = {
        "gmv": 0.30,           # GMV 得分权重 30%
        "order": 0.25,         # 订单量得分权重 25%
        "service": 0.20,       # 服务得分权重 20%
        "complaint": 0.15,     # 投诉得分权重 15%
        "fulfillment": 0.10    # 履约得分权重 10%
    }

    # 考核等级阈值
    LEVEL_THRESHOLDS = {
        AssessmentLevel.EXCELLENT: 90,
        AssessmentLevel.GOOD: 75,
        AssessmentLevel.PASS: 60,
        AssessmentLevel.FAIL: 0
    }

    def __init__(self, db: Session):
        self.db = db
        self._request_id: Optional[str] = None
        self._user_id: Optional[str] = None

    def set_request_context(self, request_id: str, user_id: str):
        """设置请求上下文"""
        self._request_id = request_id
        self._user_id = user_id

    def _log(self, level: str, message: str, data: Dict[str, Any] = None):
        """结构化日志"""
        log_data = {
            "service": "OrganizerAssessmentService",
            "request_id": self._request_id,
            "user_id": self._user_id,
            "message": message,
            **(data or {})
        }
        getattr(logger, level)(log_data)

    def create_assessment(
        self,
        organizer_id: str,
        assessment_period: str,
        assessment_type: str = "monthly"
    ) -> OrganizerAssessmentEntity:
        """
        创建团长考核记录

        Args:
            organizer_id: 团长 ID
            assessment_period: 考核周期 (如 2026-01 或 2026-W01)
            assessment_type: 考核类型 (weekly/monthly/quarterly)

        Returns:
            OrganizerAssessmentEntity: 创建的考核记录
        """
        # 检查是否已存在
        existing = self.db.query(OrganizerAssessmentEntity).filter(
            and_(
                OrganizerAssessmentEntity.organizer_id == organizer_id,
                OrganizerAssessmentEntity.assessment_period == assessment_period
            )
        ).first()

        if existing:
            self._log("warning", "考核记录已存在", {
                "organizer_id": organizer_id,
                "period": assessment_period
            })
            return existing

        assessment = OrganizerAssessmentEntity(
            id=str(uuid4()),
            organizer_id=organizer_id,
            assessment_period=assessment_period,
            assessment_type=assessment_type,
            status=OrganizerAssessmentStatus.PENDING
        )

        self.db.add(assessment)
        self.db.commit()
        self.db.refresh(assessment)

        self._log("info", "创建考核记录成功", {
            "assessment_id": assessment.id,
            "organizer_id": organizer_id,
            "period": assessment_period
        })

        return assessment

    def calculate_scores(self, organizer_id: str, assessment_period: str) -> Dict[str, Any]:
        """
        计算团长考核各项得分

        基于周期内的订单、GMV、投诉、履约等数据计算各项得分

        Args:
            organizer_id: 团长 ID
            assessment_period: 考核周期

        Returns:
            各项得分字典
        """
        # 解析周期，获取时间范围
        start_date, end_date = self._parse_period(assessment_period)

        # 1. GMV 得分 (基于周期内销售额)
        gmv_result = self.db.query(
            func.sum(OrderEntity.total_amount).label("total_gmv"),
            func.count(OrderEntity.id).label("order_count")
        ).join(
            GroupBuyEntity, OrderEntity.group_buy_id == GroupBuyEntity.id
        ).filter(
            and_(
                GroupBuyEntity.organizer_id == organizer_id,
                OrderEntity.created_at >= start_date,
                OrderEntity.created_at <= end_date,
                OrderEntity.status.in_(["SUCCESS", "COMPLETED"])
            )
        ).first()

        total_gmv = float(gmv_result.total_gmv or 0)
        order_count = gmv_result.order_count or 0

        # GMV 得分计算 (假设目标 GMV 为 10000 元)
        gmv_target = 10000
        gmv_score = min(100, (total_gmv / gmv_target) * 100)

        # 2. 订单量得分 (假设目标订单数为 100 单)
        order_target = 100
        order_score = min(100, (order_count / order_target) * 100)

        # 3. 服务得分 (基于客户满意度，这里简化为订单完成率)
        completed_orders = self.db.query(func.count(OrderEntity.id)).filter(
            and_(
                OrderEntity.group_buy_id.in_(
                    self.db.query(GroupBuyEntity.id).filter(
                        GroupBuyEntity.organizer_id == organizer_id
                    )
                ),
                OrderEntity.status == "COMPLETED",
                OrderEntity.created_at >= start_date,
                OrderEntity.created_at <= end_date
            )
        ).scalar() or 0

        service_score = min(100, (completed_orders / max(1, order_count)) * 100)

        # 4. 投诉得分 (投诉越少分数越高)
        complaint_count = self.db.query(func.count(AfterSalesOrderEntity.id)).filter(
            and_(
                AfterSalesOrderEntity.organizer_id == organizer_id,
                AfterSalesOrderEntity.after_sales_type == AfterSalesType.COMPENSATION,
                AfterSalesOrderEntity.status.in_(["APPROVED", "COMPLETED"]),
                AfterSalesOrderEntity.created_at >= start_date,
                AfterSalesOrderEntity.created_at <= end_date
            )
        ).scalar() or 0

        # 每有一个投诉扣 10 分，最低 0 分
        complaint_score = max(0, 100 - (complaint_count * 10))

        # 5. 履约得分 (基于准时履约率)
        # 这里简化处理，实际需要履约追踪数据
        fulfillment_score = 85  # 默认值

        # 计算总分
        total_score = (
            gmv_score * self.WEIGHTS["gmv"] +
            order_score * self.WEIGHTS["order"] +
            service_score * self.WEIGHTS["service"] +
            complaint_score * self.WEIGHTS["complaint"] +
            fulfillment_score * self.WEIGHTS["fulfillment"]
        )

        # 确定等级
        assessment_level = self._determine_level(total_score)

        self._log("info", "考核分数计算完成", {
            "organizer_id": organizer_id,
            "period": assessment_period,
            "gmv_score": gmv_score,
            "order_score": order_score,
            "service_score": service_score,
            "complaint_score": complaint_score,
            "fulfillment_score": fulfillment_score,
            "total_score": total_score,
            "level": assessment_level.value
        })

        return {
            "gmv_score": round(gmv_score, 2),
            "order_score": round(order_score, 2),
            "service_score": round(service_score, 2),
            "complaint_score": round(complaint_score, 2),
            "fulfillment_score": round(fulfillment_score, 2),
            "total_score": round(total_score, 2),
            "assessment_level": assessment_level,
            "metrics": {
                "total_gmv": total_gmv,
                "order_count": order_count,
                "completed_orders": completed_orders,
                "complaint_count": complaint_count
            }
        }

    def _parse_period(self, assessment_period: str) -> Tuple[datetime, datetime]:
        """解析周期字符串，返回起止时间"""
        # 格式：2026-01 (月度) 或 2026-W01 (周度)
        if "-W" in assessment_period:
            # 周度周期
            parts = assessment_period.split("-W")
            year = int(parts[0])
            week = int(parts[1])
            # 简化处理：返回该年该周的大致时间范围
            start_date = datetime(year, 1, 1) + timedelta(weeks=week - 1)
            end_date = start_date + timedelta(days=6, hours=23, minutes=59, seconds=59)
        else:
            # 月度周期
            parts = assessment_period.split("-")
            year = int(parts[0])
            month = int(parts[1])
            start_date = datetime(year, month, 1)
            if month == 12:
                end_date = datetime(year + 1, 1, 1) - timedelta(seconds=1)
            else:
                end_date = datetime(year, month + 1, 1) - timedelta(seconds=1)

        return start_date, end_date

    def _determine_level(self, total_score: float) -> AssessmentLevel:
        """根据总分确定等级"""
        for level, threshold in self.LEVEL_THRESHOLDS.items():
            if total_score >= threshold:
                return level
        return AssessmentLevel.FAIL

    def submit_assessment(
        self,
        assessment_id: str,
        scores: Dict[str, Any],
        feedback: str = None,
        assessor_id: str = None
    ) -> OrganizerAssessmentEntity:
        """
        提交考核结果

        Args:
            assessment_id: 考核 ID
            scores: 各项得分
            feedback: 考核评语
            assessor_id: 考核人 ID

        Returns:
            OrganizerAssessmentEntity: 更新后的考核记录
        """
        assessment = self.db.query(OrganizerAssessmentEntity).filter(
            OrganizerAssessmentEntity.id == assessment_id
        ).first()

        if not assessment:
            raise AppException(
                code="ASSESSMENT_NOT_FOUND",
                message="考核记录不存在",
                status=404
            )

        if assessment.status != OrganizerAssessmentStatus.PENDING:
            raise AppException(
                code="ASSESSMENT_INVALID_STATUS",
                message=f"当前状态不能提交考核：{assessment.status.value}",
                status=400
            )

        # 更新考核数据
        assessment.gmv_score = Decimal(str(scores.get("gmv_score", 0)))
        assessment.order_score = Decimal(str(scores.get("order_score", 0)))
        assessment.service_score = Decimal(str(scores.get("service_score", 0)))
        assessment.complaint_score = Decimal(str(scores.get("complaint_score", 0)))
        assessment.fulfillment_score = Decimal(str(scores.get("fulfillment_score", 0)))
        assessment.total_score = Decimal(str(scores.get("total_score", 0)))
        assessment.assessment_level = scores.get("assessment_level", AssessmentLevel.PASS)

        # 更新指标数据
        metrics = scores.get("metrics", {})
        assessment.gmv_amount = Decimal(str(metrics.get("total_gmv", 0)))
        assessment.order_count = metrics.get("order_count", 0)
        assessment.customer_count = metrics.get("customer_count", 0)
        assessment.complaint_count = metrics.get("complaint_count", 0)
        assessment.on_time_rate = Decimal(str(metrics.get("on_time_rate", 0)))

        # 计算奖惩
        self._calculate_bonus(assessment)

        assessment.feedback = feedback
        assessment.assessor_id = assessor_id
        assessment.assessed_at = datetime.now()
        assessment.status = OrganizerAssessmentStatus.COMPLETED

        self.db.commit()
        self.db.refresh(assessment)

        self._log("info", "提交考核结果成功", {
            "assessment_id": assessment_id,
            "total_score": float(assessment.total_score),
            "level": assessment.assessment_level.value
        })

        return assessment

    def _calculate_bonus(self, assessment: OrganizerAssessmentEntity):
        """计算奖惩"""
        bonus_points = 0
        penalty_points = 0
        bonus_amount = Decimal("0")

        # 优秀等级奖励
        if assessment.assessment_level == AssessmentLevel.EXCELLENT:
            bonus_points = 100
            bonus_amount = Decimal("200")
        elif assessment.assessment_level == AssessmentLevel.GOOD:
            bonus_points = 50
            bonus_amount = Decimal("100")
        elif assessment.assessment_level == AssessmentLevel.FAIL:
            penalty_points = 50

        assessment.bonus_points = bonus_points
        assessment.penalty_points = penalty_points
        assessment.bonus_amount = bonus_amount

    def get_assessment(self, assessment_id: str) -> Optional[OrganizerAssessmentEntity]:
        """获取考核详情"""
        return self.db.query(OrganizerAssessmentEntity).filter(
            OrganizerAssessmentEntity.id == assessment_id
        ).first()

    def list_assessments(
        self,
        organizer_id: str = None,
        status: OrganizerAssessmentStatus = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """获取考核列表"""
        query = self.db.query(OrganizerAssessmentEntity)

        if organizer_id:
            query = query.filter(OrganizerAssessmentEntity.organizer_id == organizer_id)
        if status:
            query = query.filter(OrganizerAssessmentEntity.status == status)

        total = query.count()
        assessments = query.order_by(
            OrganizerAssessmentEntity.created_at.desc()
        ).offset((page - 1) * page_size).limit(page_size).all()

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "assessments": assessments
        }

    def appeal_assessment(
        self,
        assessment_id: str,
        appeal_reason: str,
        user_id: str
    ) -> OrganizerAssessmentEntity:
        """申诉考核结果"""
        assessment = self.get_assessment(assessment_id)
        if not assessment:
            raise AppException(
                code="ASSESSMENT_NOT_FOUND",
                message="考核记录不存在",
                status=404
            )

        if assessment.status != OrganizerAssessmentStatus.COMPLETED:
            raise AppException(
                code="ASSESSMENT_NOT_COMPLETED",
                message="考核未完成，不能申诉",
                status=400
            )

        assessment.status = OrganizerAssessmentStatus.APPEALED
        assessment.appeal_reason = appeal_reason
        assessment.updated_at = datetime.now()

        self.db.commit()
        self.db.refresh(assessment)

        self._log("info", "考核申诉提交成功", {
            "assessment_id": assessment_id,
            "user_id": user_id
        })

        return assessment

    def process_appeal(
        self,
        assessment_id: str,
        appeal_result: str,
        operator_id: str
    ) -> OrganizerAssessmentEntity:
        """处理申诉"""
        assessment = self.get_assessment(assessment_id)
        if not assessment:
            raise AppException(
                code="ASSESSMENT_NOT_FOUND",
                message="考核记录不存在",
                status=404
            )

        if assessment.status != OrganizerAssessmentStatus.APPEALED:
            raise AppException(
                code="ASSESSMENT_NOT_APPEALED",
                message="考核未申诉",
                status=400
            )

        assessment.appeal_result = appeal_result
        assessment.status = OrganizerAssessmentStatus.COMPLETED
        assessment.updated_at = datetime.now()

        self.db.commit()
        self.db.refresh(assessment)

        self._log("info", "申诉处理完成", {
            "assessment_id": assessment_id,
            "operator_id": operator_id,
            "result": appeal_result
        })

        return assessment


# ==================== 售后服务 ====================

class AfterSalesService:
    """售后服务"""

    def __init__(self, db: Session):
        self.db = db
        self._request_id: Optional[str] = None
        self._user_id: Optional[str] = None

    def set_request_context(self, request_id: str, user_id: str):
        """设置请求上下文"""
        self._request_id = request_id
        self._user_id = user_id

    def _log(self, level: str, message: str, data: Dict[str, Any] = None):
        """结构化日志"""
        log_data = {
            "service": "AfterSalesService",
            "request_id": self._request_id,
            "user_id": self._user_id,
            "message": message,
            **(data or {})
        }
        getattr(logger, level)(log_data)

    def create_after_sales(
        self,
        order_id: str,
        user_id: str,
        after_sales_type: AfterSalesType,
        refund_amount: Decimal,
        apply_reason: str,
        apply_description: str = None,
        apply_images: List[str] = None
    ) -> AfterSalesOrderEntity:
        """
        创建售后申请

        Args:
            order_id: 订单 ID
            user_id: 用户 ID
            after_sales_type: 售后类型
            refund_amount: 退款金额
            apply_reason: 申请原因
            apply_description: 详细描述
            apply_images: 凭证图片列表

        Returns:
            AfterSalesOrderEntity: 创建的售后单
        """
        # 获取订单信息
        order = self.db.query(OrderEntity).filter(OrderEntity.id == order_id).first()
        if not order:
            raise AppException(
                code="ORDER_NOT_FOUND",
                message="订单不存在",
                status=404
            )

        # 检查订单是否已完成
        if order.status not in ["SUCCESS", "COMPLETED"]:
            raise AppException(
                code="ORDER_STATUS_INVALID",
                message="订单状态不支持售后",
                status=400
            )

        # 获取团购信息获取团长 ID
        group_buy = self.db.query(GroupBuyEntity).filter(
            GroupBuyEntity.id == order.group_buy_id
        ).first()
        if not group_buy:
            raise AppException(
                code="GROUP_BUY_NOT_FOUND",
                message="团购不存在",
                status=404
            )

        # 生成售后单号
        after_sales_no = f"AS{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid4().hex[:8].upper()}"

        after_sales = AfterSalesOrderEntity(
            id=str(uuid4()),
            after_sales_no=after_sales_no,
            order_id=order_id,
            user_id=user_id,
            group_buy_id=order.group_buy_id,
            product_id=order.product_id,
            organizer_id=group_buy.organizer_id,
            after_sales_type=after_sales_type,
            status=AfterSalesStatus.PENDING,
            order_amount=order.total_amount,
            refund_amount=refund_amount,
            apply_reason=apply_reason,
            apply_description=apply_description,
            apply_images=",".join(apply_images) if apply_images else None
        )

        self.db.add(after_sales)
        self.db.commit()
        self.db.refresh(after_sales)

        # 记录日志
        self._create_log(
            after_sales_id=after_sales.id,
            operator_id=user_id,
            operator_type="user",
            action="apply",
            new_status=AfterSalesStatus.PENDING.value,
            remark=f"用户申请售后：{apply_reason}"
        )

        self._log("info", "创建售后申请成功", {
            "after_sales_no": after_sales_no,
            "order_id": order_id,
            "type": after_sales_type.value
        })

        return after_sales

    def _create_log(
        self,
        after_sales_id: str,
        operator_id: str,
        operator_type: str,
        action: str,
        old_status: str = None,
        new_status: str = None,
        remark: str = None
    ):
        """创建售后日志"""
        log = AfterSalesLogEntity(
            id=str(uuid4()),
            after_sales_id=after_sales_id,
            operator_id=operator_id,
            operator_type=operator_type,
            action=action,
            old_status=old_status,
            new_status=new_status,
            remark=remark
        )
        self.db.add(log)
        self.db.commit()

    def get_after_sales(self, after_sales_id: str) -> Optional[AfterSalesOrderEntity]:
        """获取售后单详情"""
        return self.db.query(AfterSalesOrderEntity).filter(
            AfterSalesOrderEntity.id == after_sales_id
        ).first()

    def get_by_after_sales_no(self, after_sales_no: str) -> Optional[AfterSalesOrderEntity]:
        """通过售后单号获取"""
        return self.db.query(AfterSalesOrderEntity).filter(
            AfterSalesOrderEntity.after_sales_no == after_sales_no
        ).first()

    def review_after_sales(
        self,
        after_sales_id: str,
        reviewer_id: str,
        approved: bool,
        review_opinion: str
    ) -> AfterSalesOrderEntity:
        """
        审核售后申请

        Args:
            after_sales_id: 售后 ID
            reviewer_id: 审核人 ID
            approved: 是否通过
            review_opinion: 审核意见

        Returns:
            AfterSalesOrderEntity: 更新后的售后单
        """
        after_sales = self.get_after_sales(after_sales_id)
        if not after_sales:
            raise AppException(
                code="AFTER_SALES_NOT_FOUND",
                message="售后单不存在",
                status=404
            )

        if after_sales.status != AfterSalesStatus.PENDING:
            raise AppException(
                code="AFTER_SALES_INVALID_STATUS",
                message=f"当前状态不能审核：{after_sales.status.value}",
                status=400
            )

        old_status = after_sales.status.value

        if approved:
            after_sales.status = AfterSalesStatus.APPROVED
            # 如果是退货退款，需要等待用户退货
            if after_sales.after_sales_type == AfterSalesType.RETURN_REFUND:
                after_sales.status = AfterSalesStatus.RETURNING
        else:
            after_sales.status = AfterSalesStatus.REJECTED
            after_sales.closed_reason = review_opinion
            after_sales.closed_at = datetime.now()

        after_sales.reviewer_id = reviewer_id
        after_sales.review_opinion = review_opinion
        after_sales.reviewed_at = datetime.now()

        self.db.commit()
        self.db.refresh(after_sales)

        # 记录日志
        self._create_log(
            after_sales_id=after_sales_id,
            operator_id=reviewer_id,
            operator_type="admin",
            action="review",
            old_status=old_status,
            new_status=after_sales.status.value,
            remark=f"审核{'通过' if approved else '拒绝'}: {review_opinion}"
        )

        self._log("info", "售后审核完成", {
            "after_sales_id": after_sales_id,
            "approved": approved,
            "opinion": review_opinion
        })

        return after_sales

    def confirm_return(
        self,
        after_sales_id: str,
        tracking_no: str,
        carrier: str,
        user_id: str
    ) -> AfterSalesOrderEntity:
        """
        用户确认退货

        Args:
            after_sales_id: 售后 ID
            tracking_no: 物流单号
            carrier: 物流公司
            user_id: 用户 ID

        Returns:
            AfterSalesOrderEntity: 更新后的售后单
        """
        after_sales = self.get_after_sales(after_sales_id)
        if not after_sales:
            raise AppException(
                code="AFTER_SALES_NOT_FOUND",
                message="售后单不存在",
                status=404
            )

        if after_sales.status != AfterSalesStatus.RETURNING:
            raise AppException(
                code="AFTER_SALES_NOT_RETURNING",
                message="售后单不在退货中状态",
                status=400
            )

        after_sales.return_tracking_no = tracking_no
        after_sales.return_carrier = carrier
        after_sales.returned_at = datetime.now()

        self.db.commit()
        self.db.refresh(after_sales)

        self._log("info", "用户确认退货", {
            "after_sales_id": after_sales_id,
            "tracking_no": tracking_no
        })

        return after_sales

    def refund_after_sales(
        self,
        after_sales_id: str,
        operator_id: str,
        refund_method: str = "original"
    ) -> AfterSalesOrderEntity:
        """
        执行退款

        Args:
            after_sales_id: 售后 ID
            operator_id: 操作人 ID
            refund_method: 退款方式 (original-原路返回，balance-退到余额)

        Returns:
            AfterSalesOrderEntity: 更新后的售后单
        """
        after_sales = self.get_after_sales(after_sales_id)
        if not after_sales:
            raise AppException(
                code="AFTER_SALES_NOT_FOUND",
                message="售后单不存在",
                status=404
            )

        if after_sales.status not in [AfterSalesStatus.APPROVED, AfterSalesStatus.RETURNING]:
            raise AppException(
                code="AFTER_SALES_NOT_APPROVED",
                message="售后单未通过审核",
                status=400
            )

        old_status = after_sales.status.value

        # 执行退款逻辑 (这里简化处理，实际需要对接支付系统)
        refund_transaction_no = f"RF{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid4().hex[:8].upper()}"

        after_sales.refund_method = refund_method
        after_sales.refund_transaction_no = refund_transaction_no
        after_sales.refund_time = datetime.now()
        after_sales.status = AfterSalesStatus.REFUNDED

        self.db.commit()
        self.db.refresh(after_sales)

        # 记录日志
        self._create_log(
            after_sales_id=after_sales_id,
            operator_id=operator_id,
            operator_type="system",
            action="refund",
            old_status=old_status,
            new_status=AfterSalesStatus.REFUNDED.value,
            remark=f"退款成功，流水号：{refund_transaction_no}"
        )

        self._log("info", "退款成功", {
            "after_sales_id": after_sales_id,
            "refund_amount": float(after_sales.refund_amount),
            "transaction_no": refund_transaction_no
        })

        return after_sales

    def complete_after_sales(
        self,
        after_sales_id: str,
        operator_id: str
    ) -> AfterSalesOrderEntity:
        """完成售后单"""
        after_sales = self.get_after_sales(after_sales_id)
        if not after_sales:
            raise AppException(
                code="AFTER_SALES_NOT_FOUND",
                message="售后单不存在",
                status=404
            )

        if after_sales.status != AfterSalesStatus.REFUNDED:
            raise AppException(
                code="AFTER_SALES_NOT_REFUNDED",
                message="售后单未退款",
                status=400
            )

        after_sales.status = AfterSalesStatus.COMPLETED
        self.db.commit()
        self.db.refresh(after_sales)

        self._log("info", "售后单完成", {
            "after_sales_id": after_sales_id
        })

        return after_sales

    def list_after_sales(
        self,
        user_id: str = None,
        organizer_id: str = None,
        status: AfterSalesStatus = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """获取售后列表"""
        query = self.db.query(AfterSalesOrderEntity)

        if user_id:
            query = query.filter(AfterSalesOrderEntity.user_id == user_id)
        if organizer_id:
            query = query.filter(AfterSalesOrderEntity.organizer_id == organizer_id)
        if status:
            query = query.filter(AfterSalesOrderEntity.status == status)

        total = query.count()
        after_sales_list = query.order_by(
            AfterSalesOrderEntity.created_at.desc()
        ).offset((page - 1) * page_size).limit(page_size).all()

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": after_sales_list
        }

    def get_after_sales_logs(self, after_sales_id: str) -> List[AfterSalesLogEntity]:
        """获取售后日志"""
        return self.db.query(AfterSalesLogEntity).filter(
            AfterSalesLogEntity.after_sales_id == after_sales_id
        ).order_by(AfterSalesLogEntity.created_at.desc()).all()


# ==================== 签到积分服务 ====================

class SigninPointsService:
    """签到积分服务"""

    # 签到奖励规则
    SIGNIN_REWARDS = {
        "daily": 10,           # 每日签到基础积分
        "continuous_7": 50,    # 连续 7 天额外奖励
        "continuous_30": 200,  # 连续 30 天额外奖励
    }

    def __init__(self, db: Session):
        self.db = db
        self._request_id: Optional[str] = None
        self._user_id: Optional[str] = None

    def set_request_context(self, request_id: str, user_id: str):
        """设置请求上下文"""
        self._request_id = request_id
        self._user_id = user_id

    def _log(self, level: str, message: str, data: Dict[str, Any] = None):
        """结构化日志"""
        log_data = {
            "service": "SigninPointsService",
            "request_id": self._request_id,
            "user_id": self._user_id,
            "message": message,
            **(data or {})
        }
        getattr(logger, level)(log_data)

    def signin(self, user_id: str) -> Dict[str, Any]:
        """
        用户签到

        Args:
            user_id: 用户 ID

        Returns:
            签到结果字典
        """
        today = datetime.now().strftime("%Y-%m-%d")

        # 检查是否已签到
        existing = self.db.query(SigninCalendarEntity).filter(
            and_(
                SigninCalendarEntity.user_id == user_id,
                SigninCalendarEntity.signin_date == today
            )
        ).first()

        if existing:
            self._log("warning", "用户今日已签到", {"user_id": user_id})
            return {
                "success": False,
                "message": "今日已签到",
                "signed": True
            }

        # 获取用户账户
        account = self._get_or_create_account(user_id)

        # 计算连续签到天数
        continuous_days = self._calculate_continuous_days(user_id, today)

        # 计算获得积分
        base_points = self.SIGNIN_REWARDS["daily"]
        bonus_points = 0
        bonus_type = "normal"

        if continuous_days >= 30:
            bonus_points = self.SIGNIN_REWARDS["continuous_30"]
            bonus_type = "monthly"
        elif continuous_days >= 7:
            bonus_points = self.SIGNIN_REWARDS["continuous_7"]
            bonus_type = "weekly"

        total_points = base_points + bonus_points

        # 创建签到记录
        signin_record = SigninCalendarEntity(
            id=str(uuid4()),
            user_id=user_id,
            signin_date=today,
            signin_time=datetime.now(),
            continuous_days=continuous_days,
            points_earned=total_points,
            bonus_type=bonus_type
        )
        self.db.add(signin_record)

        # 更新账户积分
        account.available_points += total_points
        account.total_points += total_points

        # 检查是否需要升级
        self._check_level_upgrade(account)

        # 记录积分流水
        self._create_transaction(
            user_id=user_id,
            transaction_type="earn",
            points_amount=total_points,
            balance_after=account.available_points,
            source="signin",
            source_id=signin_record.id,
            description=f"签到奖励 (基础{base_points}+额外{bonus_points})"
        )

        self.db.commit()
        self.db.refresh(signin_record)

        self._log("info", "签到成功", {
            "user_id": user_id,
            "points": total_points,
            "continuous_days": continuous_days,
            "bonus_type": bonus_type
        })

        return {
            "success": True,
            "message": "签到成功",
            "signed": True,
            "points_earned": total_points,
            "continuous_days": continuous_days,
            "bonus_type": bonus_type,
            "current_points": account.available_points
        }

    def _get_or_create_account(self, user_id: str) -> PointsAccountEntity:
        """获取或创建积分账户"""
        account = self.db.query(PointsAccountEntity).filter(
            PointsAccountEntity.user_id == user_id
        ).first()

        if not account:
            account = PointsAccountEntity(
                id=str(uuid4()),
                user_id=user_id,
                total_points=0,
                available_points=0,
                used_points=0,
                level="normal"
            )
            self.db.add(account)
            self.db.commit()
            self.db.refresh(account)

        return account

    def _calculate_continuous_days(self, user_id: str, today: str) -> int:
        """计算连续签到天数"""
        today_date = datetime.strptime(today, "%Y-%m-%d")
        continuous = 1

        # 从昨天开始往前推算
        check_date = today_date - timedelta(days=1)

        while True:
            check_date_str = check_date.strftime("%Y-%m-%d")
            record = self.db.query(SigninCalendarEntity).filter(
                and_(
                    SigninCalendarEntity.user_id == user_id,
                    SigninCalendarEntity.signin_date == check_date_str
                )
            ).first()

            if record:
                continuous += 1
                check_date -= timedelta(days=1)
            else:
                break

            # 最多往前查 365 天
            if continuous > 365:
                break

        return continuous

    def _check_level_upgrade(self, account: PointsAccountEntity):
        """检查账户等级是否需要升级"""
        total = account.total_points
        current_level = account.level

        # 等级阈值
        if total >= 10000 and current_level != "platinum":
            account.level = "platinum"
            self._log("info", "账户升级为铂金", {"user_id": account.user_id})
        elif total >= 5000 and current_level != "gold":
            account.level = "gold"
            self._log("info", "账户升级为黄金", {"user_id": account.user_id})
        elif total >= 1000 and current_level != "silver":
            account.level = "silver"
            self._log("info", "账户升级为白银", {"user_id": account.user_id})

    def _create_transaction(
        self,
        user_id: str,
        transaction_type: str,
        points_amount: int,
        balance_after: int,
        source: str,
        source_id: str = None,
        description: str = None,
        expires_at: datetime = None
    ):
        """创建积分流水"""
        transaction = PointsTransactionEntity(
            id=str(uuid4()),
            user_id=user_id,
            transaction_type=transaction_type,
            points_amount=points_amount,
            balance_after=balance_after,
            source=source,
            source_id=source_id,
            description=description,
            expires_at=expires_at
        )
        self.db.add(transaction)

    def get_account(self, user_id: str) -> Optional[PointsAccountEntity]:
        """获取用户积分账户"""
        return self.db.query(PointsAccountEntity).filter(
            PointsAccountEntity.user_id == user_id
        ).first()

    def get_signin_calendar(
        self,
        user_id: str,
        year: int,
        month: int
    ) -> List[SigninCalendarEntity]:
        """获取用户月度签到日历"""
        # 计算该月的起止日期
        if month == 12:
            next_month = datetime(year + 1, 1, 1)
        else:
            next_month = datetime(year, month + 1, 1)
        last_day = next_month - timedelta(days=1)

        start_date = f"{year}-{month:02d}-01"
        end_date = last_day.strftime("%Y-%m-%d")

        return self.db.query(SigninCalendarEntity).filter(
            and_(
                SigninCalendarEntity.user_id == user_id,
                SigninCalendarEntity.signin_date >= start_date,
                SigninCalendarEntity.signin_date <= end_date
            )
        ).order_by(SigninCalendarEntity.signin_date.desc()).all()

    def get_transaction_history(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """获取积分流水历史"""
        query = self.db.query(PointsTransactionEntity).filter(
            PointsTransactionEntity.user_id == user_id
        )

        total = query.count()
        transactions = query.order_by(
            PointsTransactionEntity.created_at.desc()
        ).offset((page - 1) * page_size).limit(page_size).all()

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": transactions
        }

    def use_points(
        self,
        user_id: str,
        points_amount: int,
        source: str,
        source_id: str = None,
        description: str = None
    ) -> Dict[str, Any]:
        """
        消费积分

        Args:
            user_id: 用户 ID
            points_amount: 消费积分数
            source: 消费来源
            source_id: 来源 ID
            description: 描述

        Returns:
            消费结果
        """
        account = self.get_account(user_id)
        if not account:
            return {
                "success": False,
                "message": "积分账户不存在"
            }

        if account.available_points < points_amount:
            return {
                "success": False,
                "message": f"积分不足，当前可用：{account.available_points}"
            }

        # 扣减积分
        account.available_points -= points_amount
        account.used_points += points_amount

        # 记录流水
        self._create_transaction(
            user_id=user_id,
            transaction_type="use",
            points_amount=-points_amount,
            balance_after=account.available_points,
            source=source,
            source_id=source_id,
            description=description
        )

        self.db.commit()

        self._log("info", "积分消费成功", {
            "user_id": user_id,
            "points": points_amount,
            "source": source
        })

        return {
            "success": True,
            "message": "积分消费成功",
            "remaining_points": account.available_points
        }

    def get_points_rules(self) -> List[PointsRuleEntity]:
        """获取积分规则列表"""
        return self.db.query(PointsRuleEntity).filter(
            PointsRuleEntity.is_active == True
        ).all()

    def get_mall_items(self, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """获取积分商城商品列表"""
        query = self.db.query(PointsMallItemEntity).filter(
            PointsMallItemEntity.is_active == True
        )

        total = query.count()
        items = query.order_by(
            PointsMallItemEntity.sort_order,
            PointsMallItemEntity.created_at.desc()
        ).offset((page - 1) * page_size).limit(page_size).all()

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": items
        }

    def redeem_item(
        self,
        user_id: str,
        item_id: str
    ) -> Dict[str, Any]:
        """
        兑换积分商品

        Args:
            user_id: 用户 ID
            item_id: 商品 ID

        Returns:
            兑换结果
        """
        # 获取商品
        item = self.db.query(PointsMallItemEntity).filter(
            PointsMallItemEntity.id == item_id
        ).first()

        if not item:
            return {
                "success": False,
                "message": "商品不存在"
            }

        if not item.is_active:
            return {
                "success": False,
                "message": "商品已下架"
            }

        # 检查库存
        if item.stock_quantity <= 0:
            return {
                "success": False,
                "message": "商品库存不足"
            }

        # 检查每人限兑
        if item.redeem_limit > 0:
            redeemed_count = self.db.query(PointsRedemptionEntity).filter(
                and_(
                    PointsRedemptionEntity.user_id == user_id,
                    PointsRedemptionEntity.item_id == item_id,
                    PointsRedemptionEntity.status == "success"
                )
            ).count()

            if redeemed_count >= item.redeem_limit:
                return {
                    "success": False,
                    "message": f"已达到兑换上限 (每人限兑{item.redeem_limit}件)"
                }

        # 获取用户账户
        account = self.get_account(user_id)
        if not account or account.available_points < item.points_price:
            return {
                "success": False,
                "message": f"积分不足，需要{item.points_price}积分"
            }

        # 扣减积分
        result = self.use_points(
            user_id=user_id,
            points_amount=item.points_price,
            source="redemption",
            source_id=item_id,
            description=f"兑换商品：{item.item_name}"
        )

        if not result["success"]:
            return result

        # 创建兑换记录
        redemption_no = f"RD{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid4().hex[:8].upper()}"
        redemption = PointsRedemptionEntity(
            id=str(uuid4()),
            redemption_no=redemption_no,
            user_id=user_id,
            item_id=item_id,
            item_name=item.item_name,
            points_used=item.points_price,
            quantity=1,
            ref_id=item.ref_id,
            ref_type=item.ref_type,
            status="success"
        )
        self.db.add(redemption)

        # 扣减库存
        item.stock_quantity -= 1
        item.redeem_count += 1

        self.db.commit()
        self.db.refresh(redemption)

        self._log("info", "积分兑换成功", {
            "user_id": user_id,
            "item_id": item_id,
            "points": item.points_price
        })

        return {
            "success": True,
            "message": "兑换成功",
            "redemption_no": redemption_no,
            "item_name": item.item_name,
            "points_used": item.points_price,
            "remaining_points": account.available_points
        }

    def get_redemption_history(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """获取兑换历史"""
        query = self.db.query(PointsRedemptionEntity).filter(
            PointsRedemptionEntity.user_id == user_id
        )

        total = query.count()
        redemptions = query.order_by(
            PointsRedemptionEntity.created_at.desc()
        ).offset((page - 1) * page_size).limit(page_size).all()

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": redemptions
        }
