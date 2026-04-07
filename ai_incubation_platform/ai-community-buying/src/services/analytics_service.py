"""
P6 数据分析增强 - 业务逻辑服务

包含:
1. 销售报表服务 (SalesReportService) - 日报/周报/月报生成
2. 用户行为分析服务 (UserBehaviorService) - 转化漏斗/留存分析
3. 商品分析服务 (ProductAnalyticsService) - 销售排行/库存周转
4. 预测分析服务 (PredictionService) - 销量预测/趋势预测
5. 自定义报表服务 (CustomReportService) - 用户自定义分析
"""

import logging
import hashlib
import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
from uuid import uuid4
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, extract, case, Date
from sqlalchemy.sql import text

from models.analytics_entities import (
    SalesReportEntity, SalesReportDetailEntity,
    ReportType, ReportStatus,
    UserFunnelEntity, FunnelStage, UserRetentionEntity, UserBehaviorEntity, UserSegment,
    ProductSalesRankEntity, ProductTurnoverEntity, ProductProfitEntity,
    SalesPredictionEntity, SalesTrendEntity, TrendDirection,
    CustomReportEntity, CustomReportResultEntity
)
from models.entities import (
    OrderEntity, GroupBuyEntity, ProductEntity
)
from core.exceptions import AppException

logger = logging.getLogger(__name__)


# ==================== 工具函数 ====================

def get_date_range(report_type: ReportType, reference_date: datetime = None) -> Tuple[datetime, datetime]:
    """获取报表周期的起止日期"""
    if reference_date is None:
        reference_date = datetime.now()

    ref_date = reference_date.date() if hasattr(reference_date, 'date') else reference_date

    if report_type == ReportType.DAILY:
        return ref_date, ref_date
    elif report_type == ReportType.WEEKLY:
        # 周一为周期开始
        days_since_monday = ref_date.weekday()
        monday = ref_date - timedelta(days=days_since_monday)
        sunday = monday + timedelta(days=6)
        return monday, sunday
    elif report_type == ReportType.MONTHLY:
        # 1 号为周期开始
        period_start = ref_date.replace(day=1)
        if ref_date.month == 12:
            period_end = ref_date.replace(year=ref_date.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            period_end = ref_date.replace(month=ref_date.month + 1, day=1) - timedelta(days=1)
        return period_start, period_end
    else:
        return ref_date, ref_date


def calculate_data_hash(data: Dict) -> str:
    """计算数据哈希用于去重"""
    data_str = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(data_str.encode()).hexdigest()


# ==================== 销售报表服务 ====================

class SalesReportService:
    """销售报表服务"""

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
            "service": "SalesReportService",
            "request_id": self._request_id,
            "user_id": self._user_id,
            "message": message,
            **(data or {})
        }
        getattr(logger, level)(log_data)

    def generate_report(
        self,
        report_type: ReportType,
        reference_date: datetime = None,
        organizer_id: str = None,
        community_id: str = None,
        force_regenerate: bool = False
    ) -> SalesReportEntity:
        """
        生成销售报表

        Args:
            report_type: 报表类型 (daily/weekly/monthly)
            reference_date: 参考日期
            organizer_id: 团长 ID (可选，按团长筛选)
            community_id: 社区 ID (可选，按社区筛选)
            force_regenerate: 是否强制重新生成

        Returns:
            SalesReportEntity: 生成的报表
        """
        if reference_date is None:
            reference_date = datetime.now()

        period_start, period_end = get_date_range(report_type, reference_date)

        # 检查是否已存在报表
        existing_report = self.db.query(SalesReportEntity).filter(
            and_(
                SalesReportEntity.report_type == report_type,
                SalesReportEntity.report_date == period_start,
                SalesReportEntity.organizer_id == organizer_id,
                SalesReportEntity.community_id == community_id
            )
        ).first()

        if existing_report and not force_regenerate:
            self._log("info", "报表已存在，返回缓存结果", {
                "report_id": existing_report.id,
                "report_type": report_type.value,
                "report_date": str(period_start)
            })
            return existing_report

        # 构建订单查询
        order_query = self.db.query(OrderEntity).join(
            GroupBuyEntity, OrderEntity.group_buy_id == GroupBuyEntity.id
        )

        # 添加筛选条件
        if organizer_id:
            order_query = order_query.filter(GroupBuyEntity.organizer_id == organizer_id)
        if community_id:
            order_query = order_query.filter(GroupBuyEntity.community_id == community_id)

        # 时间范围筛选
        period_start_dt = datetime.combine(period_start, datetime.min.time())
        period_end_dt = datetime.combine(period_end, datetime.max.time())
        order_query = order_query.filter(
            OrderEntity.created_at >= period_start_dt,
            OrderEntity.created_at <= period_end_dt
        )

        # 核心指标计算
        total_orders = order_query.count()

        # 按状态统计订单
        paid_orders = order_query.filter(OrderEntity.status == "PAID").count()
        completed_orders = order_query.filter(OrderEntity.status == "COMPLETED").count()
        cancelled_orders = order_query.filter(OrderEntity.status == "CANCELLED").count()
        refunded_orders = order_query.filter(OrderEntity.status == "REFUNDED").count()

        # 销售额统计
        total_sales_result = order_query.filter(
            OrderEntity.status == "COMPLETED"
        ).with_entities(func.sum(OrderEntity.total_amount)).scalar() or Decimal(0)

        # GMV (所有已支付订单)
        gmv_result = order_query.filter(
            or_(
                OrderEntity.status == "COMPLETED",
                OrderEntity.status == "PAID"
            )
        ).with_entities(func.sum(OrderEntity.total_amount)).scalar() or Decimal(0)

        # 用户指标
        all_user_ids = order_query.with_entities(OrderEntity.user_id).distinct().all()
        total_users = len(all_user_ids)

        # 新用户统计 (注册 7 天内)
        seven_days_ago = datetime.now() - timedelta(days=7)
        # 简化处理，实际需要关联用户表
        new_users = 0

        # 活跃用户 (7 天内有购买)
        active_user_query = self.db.query(OrderEntity).filter(
            OrderEntity.created_at >= seven_days_ago
        )
        if organizer_id:
            active_user_query = active_user_query.join(GroupBuyEntity).filter(
                GroupBuyEntity.organizer_id == organizer_id
            )
        active_users = active_user_query.with_entities(OrderEntity.user_id).distinct().count()

        # 客单价
        avg_order_value = total_sales / completed_orders if completed_orders > 0 else Decimal(0)

        # 商品指标
        product_stats = order_query.filter(
            OrderEntity.status == "COMPLETED"
        ).with_entities(
            OrderEntity.product_id,
            func.sum(OrderEntity.total_amount).label('sales'),
            func.sum(OrderEntity.quantity).label('quantity')
        ).group_by(OrderEntity.product_id).order_by(
            text('sales DESC')
        ).first()

        total_products = order_query.filter(
            OrderEntity.status == "COMPLETED"
        ).with_entities(OrderEntity.product_id).distinct().count()

        top_product_id = product_stats.product_id if product_stats else None
        top_product_sales = product_stats.sales if product_stats else Decimal(0)

        # 环比数据
        prev_period_start = period_start - timedelta(days=(period_end - period_start).days + 1)
        prev_period_end = period_start - timedelta(days=1)

        prev_period_query = self.db.query(OrderEntity).join(
            GroupBuyEntity, OrderEntity.group_buy_id == GroupBuyEntity.id
        )
        if organizer_id:
            prev_period_query = prev_period_query.filter(GroupBuyEntity.organizer_id == organizer_id)
        if community_id:
            prev_period_query = prev_period_query.filter(GroupBuyEntity.community_id == community_id)

        prev_period_start_dt = datetime.combine(prev_period_start, datetime.min.time())
        prev_period_end_dt = datetime.combine(prev_period_end, datetime.max.time())
        prev_period_query = prev_period_query.filter(
            OrderEntity.created_at >= prev_period_start_dt,
            OrderEntity.created_at <= prev_period_end_dt,
            OrderEntity.status == "COMPLETED"
        )

        prev_gmv = prev_period_query.with_entities(func.sum(OrderEntity.total_amount)).scalar() or Decimal(0)
        prev_orders = prev_period_query.count()

        gmv_growth_rate = (gmv_result - prev_gmv) / prev_gmv if prev_gmv > 0 else Decimal(0)
        orders_growth_rate = (total_orders - prev_orders) / prev_orders if prev_orders > 0 else Decimal(0)

        # 创建或更新报表
        data_hash = calculate_data_hash({
            "report_type": report_type.value,
            "report_date": str(period_start),
            "organizer_id": organizer_id,
            "community_id": community_id,
            "gmv": str(gmv_result),
            "total_sales": str(total_sales_result),
            "total_orders": total_orders
        })

        if existing_report and force_regenerate:
            # 更新现有报表
            existing_report.gmv = gmv_result
            existing_report.total_sales = total_sales_result
            existing_report.total_orders = total_orders
            existing_report.paid_orders = paid_orders
            existing_report.completed_orders = completed_orders
            existing_report.cancelled_orders = cancelled_orders
            existing_report.refunded_orders = refunded_orders
            existing_report.total_users = total_users
            existing_report.new_users = new_users
            existing_report.active_users = active_users
            existing_report.avg_order_value = avg_order_value.quantize(Decimal('0.01'))
            existing_report.total_products = total_products
            existing_report.top_product_id = top_product_id
            existing_report.top_product_sales = top_product_sales
            existing_report.prev_period_gmv = prev_gmv
            existing_report.gmv_growth_rate = gmv_growth_rate
            existing_report.prev_period_orders = prev_orders
            existing_report.orders_growth_rate = orders_growth_rate
            existing_report.status = ReportStatus.COMPLETED
            existing_report.generated_at = datetime.now()
            existing_report.data_hash = data_hash
            report = existing_report
        else:
            # 创建新报表
            report = SalesReportEntity(
                id=str(uuid4()),
                report_type=report_type,
                report_date=period_start,
                period_start=period_start,
                period_end=period_end,
                gmv=gmv_result,
                total_sales=total_sales_result,
                total_orders=total_orders,
                paid_orders=paid_orders,
                completed_orders=completed_orders,
                cancelled_orders=cancelled_orders,
                refunded_orders=refunded_orders,
                total_users=total_users,
                new_users=new_users,
                active_users=active_users,
                avg_order_value=avg_order_value.quantize(Decimal('0.01')),
                total_products=total_products,
                top_product_id=top_product_id,
                top_product_sales=top_product_sales,
                prev_period_gmv=prev_gmv,
                gmv_growth_rate=gmv_growth_rate,
                prev_period_orders=prev_orders,
                orders_growth_rate=orders_growth_rate,
                organizer_id=organizer_id,
                community_id=community_id,
                status=ReportStatus.COMPLETED,
                generated_at=datetime.now(),
                data_hash=data_hash
            )
            self.db.add(report)

        self.db.commit()
        self.db.refresh(report)

        self._log("info", "销售报表生成成功", {
            "report_id": report.id,
            "report_type": report_type.value,
            "gmv": str(gmv_result),
            "total_sales": str(total_sales_result)
        })

        return report

    def get_report(self, report_id: str) -> Optional[SalesReportEntity]:
        """获取报表详情"""
        return self.db.query(SalesReportEntity).filter(
            SalesReportEntity.id == report_id
        ).first()

    def list_reports(
        self,
        report_type: ReportType = None,
        organizer_id: str = None,
        community_id: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """获取报表列表"""
        query = self.db.query(SalesReportEntity)

        if report_type:
            query = query.filter(SalesReportEntity.report_type == report_type)
        if organizer_id:
            query = query.filter(SalesReportEntity.organizer_id == organizer_id)
        if community_id:
            query = query.filter(SalesReportEntity.community_id == community_id)
        if start_date:
            query = query.filter(SalesReportEntity.report_date >= start_date)
        if end_date:
            query = query.filter(SalesReportEntity.report_date <= end_date)

        total = query.count()
        reports = query.order_by(
            SalesReportEntity.report_date.desc()
        ).offset((page - 1) * page_size).limit(page_size).all()

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "reports": reports
        }

    def get_dashboard_summary(self, organizer_id: str = None) -> Dict[str, Any]:
        """获取仪表盘摘要 (今日 + 本月累计)"""
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # 今日数据
        today_query = self.db.query(OrderEntity).join(
            GroupBuyEntity, OrderEntity.group_buy_id == GroupBuyEntity.id
        ).filter(OrderEntity.created_at >= today_start)

        if organizer_id:
            today_query = today_query.filter(GroupBuyEntity.organizer_id == organizer_id)

        today_sales = today_query.filter(
            OrderEntity.status == "COMPLETED"
        ).with_entities(func.sum(OrderEntity.total_amount)).scalar() or Decimal(0)
        today_orders = today_query.count()

        # 本月累计
        month_query = self.db.query(OrderEntity).join(
            GroupBuyEntity, OrderEntity.group_buy_id == GroupBuyEntity.id
        ).filter(OrderEntity.created_at >= month_start)

        if organizer_id:
            month_query = month_query.filter(GroupBuyEntity.organizer_id == organizer_id)

        month_sales = month_query.filter(
            OrderEntity.status == "COMPLETED"
        ).with_entities(func.sum(OrderEntity.total_amount)).scalar() or Decimal(0)
        month_orders = month_query.count()

        return {
            "today": {
                "sales": float(today_sales),
                "orders": today_orders,
                "date": today_start.strftime("%Y-%m-%d")
            },
            "month": {
                "sales": float(month_sales),
                "orders": month_orders,
                "date": month_start.strftime("%Y-%m-%d")
            }
        }


# ==================== 用户行为分析服务 ====================

class UserBehaviorService:
    """用户行为分析服务"""

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
            "service": "UserBehaviorService",
            "request_id": self._request_id,
            "message": message,
            **(data or {})
        }
        getattr(logger, level)(log_data)

    def calculate_funnel(
        self,
        funnel_date: datetime = None,
        period_type: str = "daily",
        organizer_id: str = None,
        community_id: str = None
    ) -> UserFunnelEntity:
        """
        计算用户转化漏斗

        由于缺乏完整的用户行为埋点数据，这里使用订单数据近似计算
        """
        if funnel_date is None:
            funnel_date = datetime.now()

        funnel_date_only = funnel_date.date() if hasattr(funnel_date, 'date') else funnel_date

        # 构建基础查询
        base_query = self.db.query(OrderEntity).join(
            GroupBuyEntity, OrderEntity.group_buy_id == GroupBuyEntity.id
        )

        if organizer_id:
            base_query = base_query.filter(GroupBuyEntity.organizer_id == organizer_id)
        if community_id:
            base_query = base_query.filter(GroupBuyEntity.community_id == community_id)

        # 时间范围
        if period_type == "daily":
            start = datetime.combine(funnel_date_only, datetime.min.time())
            end = datetime.combine(funnel_date_only, datetime.max.time())
        elif period_type == "weekly":
            days_since_monday = funnel_date_only.weekday()
            start = datetime.combine(funnel_date_only - timedelta(days=days_since_monday), datetime.min.time())
            end = start + timedelta(days=7)
        else:  # monthly
            start = datetime.combine(funnel_date_only.replace(day=1), datetime.min.time())
            if funnel_date_only.month == 12:
                end = datetime.combine(funnel_date_only.replace(year=funnel_date_only.year + 1, month=1, day=1), datetime.min.time())
            else:
                end = datetime.combine(funnel_date_only.replace(month=funnel_date_only.month + 1, day=1), datetime.min.time())

        base_query = base_query.filter(OrderEntity.created_at >= start, OrderEntity.created_at < end)

        # 漏斗各阶段 (简化版本，使用订单状态近似)
        # impression: 所有浏览过商品的用户 (用订单用户数近似)
        # click: 点击商品的用户 (用加购用户数近似，这里简化为下单用户)
        # detail: 查看详情的用户 (用下单用户近似)
        # cart: 加购用户 (用下单用户近似)
        # checkout: 提交订单用户
        # payment: 支付成功用户

        all_users = base_query.with_entities(OrderEntity.user_id).distinct().count()
        checkout_users = base_query.with_entities(OrderEntity.user_id).distinct().count()
        payment_users = base_query.filter(
            or_(OrderEntity.status == "PAID", OrderEntity.status == "COMPLETED")
        ).with_entities(OrderEntity.user_id).distinct().count()

        # 简化：假设浏览->点击->详情->加购的转化率约为 50%
        impression_count = all_users * 4 if all_users > 0 else 0
        click_count = all_users * 3 if all_users > 0 else 0
        detail_count = all_users * 2 if all_users > 0 else 0
        cart_count = all_users if all_users > 0 else 0

        # 计算转化率
        click_rate = Decimal(click_count) / Decimal(impression_count) if impression_count > 0 else Decimal(0)
        detail_rate = Decimal(detail_count) / Decimal(click_count) if click_count > 0 else Decimal(0)
        cart_rate = Decimal(cart_count) / Decimal(detail_count) if detail_count > 0 else Decimal(0)
        checkout_rate = Decimal(checkout_users) / Decimal(cart_count) if cart_count > 0 else Decimal(0)
        payment_rate = Decimal(payment_users) / Decimal(checkout_users) if checkout_users > 0 else Decimal(0)
        overall_conversion_rate = Decimal(payment_users) / Decimal(impression_count) if impression_count > 0 else Decimal(0)

        funnel = UserFunnelEntity(
            id=str(uuid4()),
            funnel_date=funnel_date_only,
            period_type=period_type,
            impression_count=impression_count,
            click_count=click_count,
            detail_count=detail_count,
            cart_count=cart_count,
            checkout_count=checkout_users,
            payment_count=payment_users,
            click_rate=click_rate.quantize(Decimal('0.0001')),
            detail_rate=detail_rate.quantize(Decimal('0.0001')),
            cart_rate=cart_rate.quantize(Decimal('0.0001')),
            checkout_rate=checkout_rate.quantize(Decimal('0.0001')),
            payment_rate=payment_rate.quantize(Decimal('0.0001')),
            overall_conversion_rate=overall_conversion_rate.quantize(Decimal('0.0001')),
            organizer_id=organizer_id,
            community_id=community_id
        )

        self.db.add(funnel)
        self.db.commit()
        self.db.refresh(funnel)

        self._log("info", "转化漏斗计算成功", {
            "funnel_date": str(funnel_date_only),
            "overall_conversion_rate": float(overall_conversion_rate)
        })

        return funnel

    def calculate_retention(
        self,
        cohort_date: datetime = None,
        cohort_type: str = "daily",
        organizer_id: str = None,
        community_id: str = None
    ) -> UserRetentionEntity:
        """
        计算用户留存率

        Args:
            cohort_date: 队列日期 (用户首次购买日期)
            cohort_type: 队列类型 (daily/weekly/monthly)
            organizer_id: 团长 ID
            community_id: 社区 ID
        """
        if cohort_date is None:
            cohort_date = datetime.now() - timedelta(days=30)

        cohort_date_only = cohort_date.date() if hasattr(cohort_date, 'date') else cohort_date

        # 获取队列用户 (首次购买在该日期的用户)
        base_query = self.db.query(OrderEntity).join(
            GroupBuyEntity, OrderEntity.group_buy_id == GroupBuyEntity.id
        )

        if organizer_id:
            base_query = base_query.filter(GroupBuyEntity.organizer_id == organizer_id)
        if community_id:
            base_query = base_query.filter(GroupBuyEntity.community_id == community_id)

        # 获取每个用户的首次购买日期
        first_order_subquery = base_query.with_entities(
            OrderEntity.user_id,
            func.min(OrderEntity.created_at).label('first_order_at')
        ).group_by(OrderEntity.user_id).subquery()

        # 筛选出 cohort 用户
        cohort_start = datetime.combine(cohort_date_only, datetime.min.time())
        if cohort_type == "daily":
            cohort_end = cohort_start + timedelta(days=1)
        elif cohort_type == "weekly":
            cohort_end = cohort_start + timedelta(days=7)
        else:
            if cohort_date_only.month == 12:
                cohort_end = datetime.combine(cohort_date_only.replace(year=cohort_date_only.year + 1, month=1, day=1), datetime.min.time())
            else:
                cohort_end = datetime.combine(cohort_date_only.replace(month=cohort_date_only.month + 1, day=1), datetime.min.time())

        cohort_users = self.db.query(first_order_subquery.c.user_id).filter(
            and_(
                first_order_subquery.c.first_order_at >= cohort_start,
                first_order_subquery.c.first_order_at < cohort_end
            )
        ).distinct().all()

        cohort_user_ids = [u[0] for u in cohort_users]
        cohort_size = len(cohort_user_ids)

        if cohort_size == 0:
            retention = UserRetentionEntity(
                id=str(uuid4()),
                cohort_date=cohort_date_only,
                cohort_type=cohort_type,
                cohort_size=0,
                retention_users={},
                retention_rates={},
                period_days=30,
                organizer_id=organizer_id,
                community_id=community_id
            )
            self.db.add(retention)
            self.db.commit()
            return retention

        # 计算各期留存
        retention_users = {}
        retention_rates = {}

        for day in [1, 7, 14, 30]:
            check_date = cohort_start + timedelta(days=day)
            check_end = check_date + timedelta(days=1)

            retained_users = base_query.filter(
                OrderEntity.user_id.in_(cohort_user_ids),
                OrderEntity.created_at >= check_date,
                OrderEntity.created_at < check_end
            ).with_entities(OrderEntity.user_id).distinct().count()

            retention_users[f"day_{day}"] = retained_users
            retention_rates[f"day_{day}"] = round(retained_users / cohort_size, 4) if cohort_size > 0 else 0

        retention = UserRetentionEntity(
            id=str(uuid4()),
            cohort_date=cohort_date_only,
            cohort_type=cohort_type,
            cohort_size=cohort_size,
            retention_users=retention_users,
            retention_rates=retention_rates,
            period_days=30,
            organizer_id=organizer_id,
            community_id=community_id
        )

        self.db.add(retention)
        self.db.commit()
        self.db.refresh(retention)

        self._log("info", "用户留存计算成功", {
            "cohort_date": str(cohort_date_only),
            "cohort_size": cohort_size,
            "day_7_retention": retention_rates.get("day_7", 0)
        })

        return retention

    def get_user_segment(self, user_id: str) -> UserSegment:
        """获取用户分群"""
        # 获取用户首次购买时间
        first_order = self.db.query(OrderEntity).filter(
            OrderEntity.user_id == user_id
        ).order_by(OrderEntity.created_at).first()

        if not first_order:
            return UserSegment.NEW_USER

        # 获取最后购买时间
        last_order = self.db.query(OrderEntity).filter(
            OrderEntity.user_id == user_id
        ).order_by(OrderEntity.created_at.desc()).first()

        days_since_last_order = (datetime.now() - last_order.created_at).days

        if days_since_last_order < 7:
            return UserSegment.ACTIVE_USER
        elif days_since_last_order < 30:
            return UserSegment.SILENT_USER
        else:
            return UserSegment.LOST_USER

    def analyze_user_behavior(
        self,
        user_id: str,
        behavior_date: datetime = None
    ) -> UserBehaviorEntity:
        """分析单个用户行为"""
        if behavior_date is None:
            behavior_date = datetime.now()

        behavior_date_only = behavior_date.date() if hasattr(behavior_date, 'date') else behavior_date
        day_start = datetime.combine(behavior_date_only, datetime.min.time())
        day_end = datetime.combine(behavior_date_only, datetime.max.time())

        # 查询用户当日订单
        orders = self.db.query(OrderEntity).filter(
            OrderEntity.user_id == user_id,
            OrderEntity.created_at >= day_start,
            OrderEntity.created_at <= day_end
        ).all()

        order_count = len(orders)
        payment_count = sum(1 for o in orders if o.status in ["PAID", "COMPLETED"])
        total_spent = sum(o.total_amount for o in orders if o.status == "COMPLETED")

        # 累计消费
        accumulated = self.db.query(func.sum(OrderEntity.total_amount)).filter(
            OrderEntity.user_id == user_id,
            OrderEntity.status == "COMPLETED"
        ).scalar() or Decimal(0)

        # 用户分群
        user_segment = self.get_user_segment(user_id)

        behavior = UserBehaviorEntity(
            id=str(uuid4()),
            user_id=user_id,
            behavior_date=behavior_date_only,
            view_count=order_count * 3,  # 简化估算
            click_count=order_count * 2,
            cart_count=order_count,
            order_count=order_count,
            payment_count=payment_count,
            total_session_time=order_count * 300,  # 估算 5 分钟
            session_count=order_count,
            avg_session_time=Decimal('300.00'),
            total_spent=total_spent,
            accumulated_spent=accumulated,
            user_segment=user_segment
        )

        self.db.add(behavior)
        self.db.commit()
        self.db.refresh(behavior)

        return behavior


# ==================== 商品分析服务 ====================

class ProductAnalyticsService:
    """商品分析服务"""

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
            "service": "ProductAnalyticsService",
            "request_id": self._request_id,
            "message": message,
            **(data or {})
        }
        getattr(logger, level)(log_data)

    def get_sales_rank(
        self,
        rank_date: datetime = None,
        period_type: str = "daily",
        organizer_id: str = None,
        community_id: str = None,
        top_n: int = 10
    ) -> ProductSalesRankEntity:
        """获取商品销售排行"""
        if rank_date is None:
            rank_date = datetime.now()

        rank_date_only = rank_date.date() if hasattr(rank_date, 'date') else rank_date

        # 构建查询
        query = self.db.query(
            OrderEntity.product_id,
            func.sum(OrderEntity.total_amount).label('total_sales'),
            func.sum(OrderEntity.quantity).label('total_quantity'),
            func.count(OrderEntity.id).label('order_count')
        ).join(
            GroupBuyEntity, OrderEntity.group_buy_id == GroupBuyEntity.id
        ).filter(OrderEntity.status == "COMPLETED")

        if organizer_id:
            query = query.filter(GroupBuyEntity.organizer_id == organizer_id)
        if community_id:
            query = query.filter(GroupBuyEntity.community_id == community_id)

        # 时间范围
        if period_type == "daily":
            start = datetime.combine(rank_date_only, datetime.min.time())
            end = datetime.combine(rank_date_only, datetime.max.time())
        elif period_type == "weekly":
            days_since_monday = rank_date_only.weekday()
            start = datetime.combine(rank_date_only - timedelta(days=days_since_monday), datetime.min.time())
            end = start + timedelta(days=7)
        else:
            start = datetime.combine(rank_date_only.replace(day=1), datetime.min.time())
            if rank_date_only.month == 12:
                end = datetime.combine(rank_date_only.replace(year=rank_date_only.year + 1, month=1, day=1), datetime.min.time())
            else:
                end = datetime.combine(rank_date_only.replace(month=rank_date_only.month + 1, day=1), datetime.min.time())

        query = query.filter(OrderEntity.created_at >= start, OrderEntity.created_at < end)

        # 按销售额排序
        results = query.group_by(OrderEntity.product_id).order_by(
            text('total_sales DESC')
        ).limit(top_n).all()

        # 获取商品信息
        product_ids = [r.product_id for r in results]
        products = self.db.query(ProductEntity).filter(ProductEntity.id.in_(product_ids)).all()
        product_map = {p.id: p for p in products}

        # 构建排行数据
        top_products = []
        for i, r in enumerate(results):
            product = product_map.get(r.product_id)
            top_products.append({
                "rank": i + 1,
                "product_id": r.product_id,
                "product_name": product.name if product else "未知商品",
                "sales": float(r.total_sales),
                "quantity": r.total_quantity,
                "order_count": r.order_count
            })

        # 计算总销售额
        total_sales = sum(r.total_sales for r in results)

        sales_rank = ProductSalesRankEntity(
            id=str(uuid4()),
            rank_date=rank_date_only,
            period_type=period_type,
            organizer_id=organizer_id,
            community_id=community_id,
            top_products=top_products,
            total_products=len(results),
            total_sales=total_sales
        )

        self.db.add(sales_rank)
        self.db.commit()
        self.db.refresh(sales_rank)

        return sales_rank

    def analyze_turnover(
        self,
        product_id: str,
        organizer_id: str = None,
        analysis_date: datetime = None
    ) -> ProductTurnoverEntity:
        """分析商品库存周转"""
        if analysis_date is None:
            analysis_date = datetime.now()

        analysis_date_only = analysis_date.date() if hasattr(analysis_date, 'date') else analysis_date

        # 获取商品信息
        product = self.db.query(ProductEntity).filter(ProductEntity.id == product_id).first()
        if not product:
            raise AppException(code="PRODUCT_NOT_FOUND", message=f"商品不存在：{product_id}")

        # 计算 30 天销售数量
        thirty_days_ago = analysis_date - timedelta(days=30)
        sold_quantity = self.db.query(func.sum(OrderEntity.quantity)).join(
            GroupBuyEntity, OrderEntity.group_buy_id == GroupBuyEntity.id
        ).filter(
            OrderEntity.product_id == product_id,
            OrderEntity.status == "COMPLETED",
            OrderEntity.created_at >= thirty_days_ago
        ).scalar() or 0

        # 库存数据
        beginning_inventory = product.stock
        ending_inventory = product.stock
        avg_inventory = (beginning_inventory + ending_inventory) / 2 if (beginning_inventory + ending_inventory) > 0 else 1

        # 周转率 = 销售数量 / 平均库存
        turnover_rate = Decimal(sold_quantity) / Decimal(avg_inventory) if avg_inventory > 0 else Decimal(0)
        # 周转天数 = 30 / 周转率 (30 天周期)
        turnover_days = Decimal(30) / turnover_rate if turnover_rate > 0 else Decimal(999)

        # 健康度评估
        if turnover_days < 7:
            health_status = "risk"  # 周转太快，可能缺货
            suggestion = "建议增加备货，当前库存周转过快"
        elif turnover_days < 30:
            health_status = "healthy"
            suggestion = "库存周转健康，保持当前备货策略"
        elif turnover_days < 60:
            health_status = "overstock"
            suggestion = "库存周转较慢，建议减少备货或促销活动"
        else:
            health_status = "overstock"
            suggestion = "库存严重积压，建议清仓处理"

        turnover = ProductTurnoverEntity(
            id=str(uuid4()),
            product_id=product_id,
            organizer_id=organizer_id,
            analysis_date=analysis_date_only,
            beginning_inventory=beginning_inventory,
            ending_inventory=ending_inventory,
            avg_inventory=avg_inventory,
            sold_quantity=sold_quantity,
            turnover_rate=turnover_rate.quantize(Decimal('0.0001')),
            turnover_days=turnover_days.quantize(Decimal('0.01')),
            health_status=health_status,
            suggestion=suggestion
        )

        self.db.add(turnover)
        self.db.commit()
        self.db.refresh(turnover)

        return turnover


# ==================== 预测分析服务 ====================

class PredictionService:
    """预测分析服务"""

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
            "service": "PredictionService",
            "request_id": self._request_id,
            "message": message,
            **(data or {})
        }
        getattr(logger, level)(log_data)

    def predict_sales(
        self,
        product_id: str,
        predict_date: datetime = None,
        organizer_id: str = None,
        community_id: str = None
    ) -> SalesPredictionEntity:
        """
        销量预测

        使用简单的移动平均预测，实际生产环境应使用更复杂的模型
        """
        if predict_date is None:
            predict_date = datetime.now() + timedelta(days=1)

        predict_date_only = predict_date.date() if hasattr(predict_date, 'date') else predict_date

        # 获取历史销量数据 (过去 30 天)
        thirty_days_ago = datetime.now() - timedelta(days=30)

        history_query = self.db.query(
            func.date(OrderEntity.created_at).label('sale_date'),
            func.sum(OrderEntity.quantity).label('quantity'),
            func.sum(OrderEntity.total_amount).label('sales')
        ).join(
            GroupBuyEntity, OrderEntity.group_buy_id == GroupBuyEntity.id
        ).filter(
            OrderEntity.product_id == product_id,
            OrderEntity.status == "COMPLETED",
            OrderEntity.created_at >= thirty_days_ago
        )

        if organizer_id:
            history_query = history_query.filter(GroupBuyEntity.organizer_id == organizer_id)
        if community_id:
            history_query = history_query.filter(GroupBuyEntity.community_id == community_id)

        history = history_query.group_by(
            func.date(OrderEntity.created_at)
        ).order_by(
            func.date(OrderEntity.created_at)
        ).all()

        if len(history) == 0:
            # 无历史数据，返回 0 预测
            prediction = SalesPredictionEntity(
                id=str(uuid4()),
                product_id=product_id,
                organizer_id=organizer_id,
                community_id=community_id,
                predict_date=predict_date_only,
                predicted_quantity=0,
                predicted_sales=Decimal(0),
                confidence_level=Decimal(0),
                model_name="no_data",
                predicted_at=datetime.now()
            )
            self.db.add(prediction)
            self.db.commit()
            return prediction

        # 简单移动平均预测
        quantities = [h.quantity for h in history]
        sales_amounts = [h.sales for h in history]

        # 7 日移动平均
        recent_7d = quantities[-7:] if len(quantities) >= 7 else quantities
        avg_quantity = sum(recent_7d) / len(recent_7d)
        avg_sales = sum(recent_7d) / len(recent_7d) if len(recent_7d) > 0 else 0

        # 置信度基于数据量
        confidence = min(0.3 + len(history) * 0.02, 0.9)

        # 预测范围
        std_dev = (max(quantities) - min(quantities)) / 4 if len(quantities) > 1 else avg_quantity * 0.2
        range_low = max(0, int(avg_quantity - std_dev))
        range_high = int(avg_quantity + std_dev)

        prediction = SalesPredictionEntity(
            id=str(uuid4()),
            product_id=product_id,
            organizer_id=organizer_id,
            community_id=community_id,
            predict_date=predict_date_only,
            predicted_quantity=int(avg_quantity),
            predicted_sales=Decimal(str(avg_sales)).quantize(Decimal('0.01')),
            confidence_level=Decimal(str(confidence)).quantize(Decimal('0.0001')),
            prediction_range_low=range_low,
            prediction_range_high=range_high,
            model_name="moving_average_7d",
            model_version="1.0",
            predicted_at=datetime.now()
        )

        self.db.add(prediction)
        self.db.commit()
        self.db.refresh(prediction)

        self._log("info", "销量预测完成", {
            "product_id": product_id,
            "predicted_quantity": int(avg_quantity),
            "confidence": confidence
        })

        return prediction

    def analyze_trend(
        self,
        trend_date: datetime = None,
        organizer_id: str = None,
        community_id: str = None
    ) -> SalesTrendEntity:
        """分析销售趋势"""
        if trend_date is None:
            trend_date = datetime.now()

        trend_date_only = trend_date.date() if hasattr(trend_date, 'date') else trend_date

        # 获取当前值 (今日销售额)
        today_start = datetime.combine(trend_date_only, datetime.min.time())
        today_end = datetime.combine(trend_date_only, datetime.max.time())

        current_query = self.db.query(OrderEntity).join(
            GroupBuyEntity, OrderEntity.group_buy_id == GroupBuyEntity.id
        ).filter(
            OrderEntity.created_at >= today_start,
            OrderEntity.created_at <= today_end,
            OrderEntity.status == "COMPLETED"
        )

        if organizer_id:
            current_query = current_query.filter(GroupBuyEntity.organizer_id == organizer_id)
        if community_id:
            current_query = current_query.filter(GroupBuyEntity.community_id == community_id)

        current_value_raw = current_query.with_entities(func.sum(OrderEntity.total_amount)).scalar()
        current_value = Decimal(str(current_value_raw)) if current_value_raw is not None else Decimal(0)

        # 获取上期值 (昨日销售额)
        yesterday = trend_date_only - timedelta(days=1)
        yesterday_start = datetime.combine(yesterday, datetime.min.time())
        yesterday_end = datetime.combine(yesterday, datetime.max.time())

        prev_query = self.db.query(OrderEntity).join(
            GroupBuyEntity, OrderEntity.group_buy_id == GroupBuyEntity.id
        ).filter(
            OrderEntity.created_at >= yesterday_start,
            OrderEntity.created_at <= yesterday_end,
            OrderEntity.status == "COMPLETED"
        )

        if organizer_id:
            prev_query = prev_query.filter(GroupBuyEntity.organizer_id == organizer_id)
        if community_id:
            prev_query = prev_query.filter(GroupBuyEntity.community_id == community_id)

        prev_value_raw = prev_query.with_entities(func.sum(OrderEntity.total_amount)).scalar()
        prev_value = Decimal(str(prev_value_raw)) if prev_value_raw is not None else Decimal(0)

        # 计算变化
        change_value = current_value - prev_value
        change_rate = change_value / prev_value if prev_value > 0 else Decimal(0)

        # 趋势方向
        if change_rate > Decimal('0.1'):
            trend_direction = TrendDirection.UP
            trend_strength = "strong" if change_rate > Decimal('0.3') else "moderate"
        elif change_rate < Decimal('-0.1'):
            trend_direction = TrendDirection.DOWN
            trend_strength = "strong" if change_rate < Decimal('-0.3') else "moderate"
        else:
            trend_direction = TrendDirection.STABLE
            trend_strength = "weak"

        # 移动平均 (7 日)
        seven_days_ago = trend_date_only - timedelta(days=6)
        ma_7d_query = self.db.query(OrderEntity).join(
            GroupBuyEntity, OrderEntity.group_buy_id == GroupBuyEntity.id
        ).filter(
            OrderEntity.created_at >= datetime.combine(seven_days_ago, datetime.min.time()),
            OrderEntity.created_at <= today_end,
            OrderEntity.status == "COMPLETED"
        )

        if organizer_id:
            ma_7d_query = ma_7d_query.filter(GroupBuyEntity.organizer_id == organizer_id)
        if community_id:
            ma_7d_query = ma_7d_query.filter(GroupBuyEntity.community_id == community_id)

        ma_7d_raw = ma_7d_query.with_entities(func.sum(OrderEntity.total_amount)).scalar() or 0
        ma_7d = Decimal(str(ma_7d_raw)) / 7

        trend = SalesTrendEntity(
            id=str(uuid4()),
            trend_date=trend_date_only,
            current_value=current_value,
            prev_value=prev_value,
            change_value=change_value,
            change_rate=change_rate.quantize(Decimal('0.0001')),
            trend_direction=trend_direction,
            trend_strength=trend_strength,
            ma_7d=ma_7d.quantize(Decimal('0.01'))
        )

        self.db.add(trend)
        self.db.commit()
        self.db.refresh(trend)

        return trend


# ==================== 自定义报表服务 ====================

class CustomReportService:
    """自定义报表服务"""

    def __init__(self, db: Session):
        self.db = db
        self._request_id: Optional[str] = None
        self._user_id: Optional[str] = None

    def set_request_context(self, request_id: str, user_id: str):
        """设置请求上下文"""
        self._request_id = request_id
        self._user_id = user_id

    def create_report(
        self,
        user_id: str,
        report_name: str,
        config: Dict[str, Any],
        report_description: str = None
    ) -> CustomReportEntity:
        """创建自定义报表"""
        report = CustomReportEntity(
            id=str(uuid4()),
            user_id=user_id,
            report_name=report_name,
            report_description=report_description,
            config=config
        )

        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)

        return report

    def execute_report(self, report_id: str) -> CustomReportResultEntity:
        """执行自定义报表查询"""
        import time
        start_time = time.time()

        report = self.db.query(CustomReportEntity).filter(
            CustomReportEntity.id == report_id
        ).first()

        if not report:
            raise AppException(code="REPORT_NOT_FOUND", message="报表不存在")

        if not report.is_active:
            raise AppException(code="REPORT_INACTIVE", message="报表已停用")

        config = report.config

        # 构建查询
        dimensions = config.get("dimensions", [])
        metrics = config.get("metrics", [])
        filters = config.get("filters", [])
        group_by = config.get("group_by", [])
        order_by = config.get("order_by", {})
        limit = config.get("limit", 100)

        # 简化实现：基于订单数据构建结果
        query = self.db.query(OrderEntity).join(
            GroupBuyEntity, OrderEntity.group_buy_id == GroupBuyEntity.id
        )

        # 应用筛选
        for f in filters:
            field = f.get("field")
            op = f.get("op")
            value = f.get("value")

            if field == "status":
                if op == "=":
                    query = query.filter(OrderEntity.status == value)
            elif field == "organizer_id":
                if op == "=":
                    query = query.filter(GroupBuyEntity.organizer_id == value)

        # 时间范围筛选
        date_filter = next((f for f in filters if f.get("field") == "date"), None)
        if date_filter:
            start_date = datetime.combine(
                datetime.fromisoformat(date_filter.get("gte")).date(),
                datetime.min.time()
            )
            end_date = datetime.combine(
                datetime.fromisoformat(date_filter.get("lte")).date(),
                datetime.max.time()
            )
            query = query.filter(OrderEntity.created_at >= start_date, OrderEntity.created_at <= end_date)

        # 执行查询
        orders = query.order_by(OrderEntity.created_at.desc()).limit(limit).all()

        # 构建结果
        result_data = {
            "columns": ["order_id", "user_id", "product_id", "quantity", "total_amount", "status", "created_at"],
            "data": [
                {
                    "order_id": o.id,
                    "user_id": o.user_id,
                    "product_id": o.product_id,
                    "quantity": o.quantity,
                    "total_amount": float(o.total_amount),
                    "status": o.status,
                    "created_at": o.created_at.isoformat()
                }
                for o in orders
            ],
            "summary": {
                "total_orders": len(orders),
                "total_amount": sum(float(o.total_amount) for o in orders)
            }
        }

        execution_time = int((time.time() - start_time) * 1000)

        result = CustomReportResultEntity(
            id=str(uuid4()),
            report_id=report_id,
            generated_at=datetime.now(),
            result_data=result_data,
            execution_time_ms=execution_time,
            row_count=len(orders),
            status="success"
        )

        # 更新报表最后生成时间
        report.last_generated_at = datetime.now()

        self.db.add(result)
        self.db.commit()
        self.db.refresh(result)

        return result

    def get_report_history(self, report_id: str, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """获取报表执行历史"""
        query = self.db.query(CustomReportResultEntity).filter(
            CustomReportResultEntity.report_id == report_id
        ).order_by(CustomReportResultEntity.generated_at.desc())

        total = query.count()
        results = query.offset((page - 1) * page_size).limit(page_size).all()

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "results": results
        }
