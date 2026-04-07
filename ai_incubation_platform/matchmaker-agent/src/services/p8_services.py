"""
P8 企业数据看板与绩效管理 - 业务服务层

包含服务：
- EnterpriseDashboardService: 企业数据看板服务
- PerformanceService: 绩效管理服务
- DepartmentService: 组织架构服务
- OperatorService: 运营角色服务
- ExportService: 数据导出服务
"""
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc
from models.p8_models import (
    DashboardMetricsDB, DashboardTrendDB, DashboardReportDB,
    KPIMetricDB, PerformanceReviewDB, OperatorPerformanceDB,
    DepartmentDB, OperatorRoleDB, UserOperatorDB, OperatorActionLogDB,
    ExportTaskDB
)
from db.models import UserDB, MatchHistoryDB, UserMembershipDB, MembershipOrderDB
from db.models import BehaviorEventDB, ChatMessageDB, SwipeActionDB


class EnterpriseDashboardService:
    """企业数据看板服务"""

    def __init__(self, db: Session):
        self.db = db

    def get_dashboard_overview(self, days: int = 7) -> Dict[str, Any]:
        """
        获取企业数据看板概览

        返回核心指标：
        - 用户数据：总数、活跃数、新增数
        - 匹配数据：总匹配数、成功率、进行中
        - 收入数据：总收入、订单数、付费用户数
        - 安全数据：举报数、处理率、违规数
        """
        today = datetime.now()
        start_date = today - timedelta(days=days)

        # 用户数据
        user_stats = self._get_user_stats(start_date)

        # 匹配数据
        match_stats = self._get_match_stats(start_date)

        # 收入数据
        revenue_stats = self._get_revenue_stats(start_date)

        # 安全数据
        safety_stats = self._get_safety_stats(start_date)

        # 活跃度数据
        engagement_stats = self._get_engagement_stats(start_date)

        return {
            "user_metrics": user_stats,
            "match_metrics": match_stats,
            "revenue_metrics": revenue_stats,
            "safety_metrics": safety_stats,
            "engagement_metrics": engagement_stats,
            "period_days": days,
            "generated_at": today.isoformat()
        }

    def _get_user_stats(self, start_date: datetime) -> Dict[str, Any]:
        """获取用户统计数据"""
        total_users = self.db.query(UserDB).count()
        active_users = self.db.query(UserDB).filter(
            UserDB.is_active == True
        ).count()

        # 新增用户 (通过行为事件推断)
        new_users = self.db.query(BehaviorEventDB).filter(
            BehaviorEventDB.event_type == "user_register",
            BehaviorEventDB.created_at >= start_date
        ).count()

        # 付费用户
        paying_users = self.db.query(UserMembershipDB).filter(
            UserMembershipDB.status == "active"
        ).count()

        return {
            "total_users": total_users,
            "active_users": active_users,
            "new_users": new_users,
            "paying_users": paying_users,
            "conversion_rate": round(paying_users / max(total_users, 1) * 100, 2)
        }

    def _get_match_stats(self, start_date: datetime) -> Dict[str, Any]:
        """获取匹配统计数据"""
        total_matches = self.db.query(MatchHistoryDB).count()

        successful_matches = self.db.query(MatchHistoryDB).filter(
            MatchHistoryDB.status == "accepted"
        ).count()

        pending_matches = self.db.query(MatchHistoryDB).filter(
            MatchHistoryDB.status == "pending"
        ).count()

        # 匹配成功率
        success_rate = round(successful_matches / max(total_matches, 1) * 100, 2)

        return {
            "total_matches": total_matches,
            "successful_matches": successful_matches,
            "pending_matches": pending_matches,
            "success_rate": success_rate
        }

    def _get_revenue_stats(self, start_date: datetime) -> Dict[str, Any]:
        """获取收入统计数据"""
        # 付费订单
        paid_orders = self.db.query(MembershipOrderDB).filter(
            MembershipOrderDB.status == "paid",
            MembershipOrderDB.payment_time >= start_date
        ).all()

        total_revenue = sum(order.amount for order in paid_orders)
        order_count = len(paid_orders)

        # 平均订单金额
        avg_order_value = round(total_revenue / max(order_count, 1), 2)

        return {
            "total_revenue": round(total_revenue, 2),
            "order_count": order_count,
            "avg_order_value": avg_order_value,
            "period_days": (datetime.now() - start_date).days
        }

    def _get_safety_stats(self, start_date: datetime) -> Dict[str, Any]:
        """获取安全统计数据"""
        # 举报事件
        reports = self.db.query(BehaviorEventDB).filter(
            BehaviorEventDB.event_type == "user_report",
            BehaviorEventDB.created_at >= start_date
        ).all()

        # 违规事件
        violations = self.db.query(BehaviorEventDB).filter(
            BehaviorEventDB.event_type == "safety_violation",
            BehaviorEventDB.created_at >= start_date
        ).count()

        report_count = len(reports)
        handled_reports = sum(1 for r in reports if r.event_data.get("handled", False))

        return {
            "report_count": report_count,
            "handled_reports": handled_reports,
            "handle_rate": round(handled_reports / max(report_count, 1) * 100, 2),
            "violation_count": violations
        }

    def _get_engagement_stats(self, start_date: datetime) -> Dict[str, Any]:
        """获取活跃度统计数据"""
        # 滑动行为数
        swipe_count = self.db.query(SwipeActionDB).filter(
            SwipeActionDB.created_at >= start_date
        ).count()

        # 消息数
        message_count = self.db.query(ChatMessageDB).filter(
            ChatMessageDB.created_at >= start_date
        ).count()

        # 日均活跃
        days = max((datetime.now() - start_date).days, 1)

        return {
            "total_swipes": swipe_count,
            "total_messages": message_count,
            "avg_daily_swipes": round(swipe_count / days, 2),
            "avg_daily_messages": round(message_count / days, 2)
        }

    def get_trend_data(
        self,
        trend_type: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        获取趋势数据

        支持的趋势类型:
        - user_growth_trend: 用户增长趋势
        - matching_success_trend: 匹配成功趋势
        - revenue_trend: 收入趋势
        """
        data_points = []
        current = start_date

        while current <= end_date:
            next_day = current + timedelta(days=1)

            if trend_type == "user_growth_trend":
                count = self.db.query(BehaviorEventDB).filter(
                    BehaviorEventDB.event_type == "user_register",
                    BehaviorEventDB.created_at >= current,
                    BehaviorEventDB.created_at < next_day
                ).count()
                value = count
            elif trend_type == "matching_success_trend":
                count = self.db.query(MatchHistoryDB).filter(
                    MatchHistoryDB.status == "accepted",
                    MatchHistoryDB.created_at >= current,
                    MatchHistoryDB.created_at < next_day
                ).count()
                value = count
            elif trend_type == "revenue_trend":
                orders = self.db.query(MembershipOrderDB).filter(
                    MembershipOrderDB.status == "paid",
                    MembershipOrderDB.payment_time >= current,
                    MembershipOrderDB.payment_time < next_day
                ).all()
                value = sum(order.amount for order in orders)
            else:
                value = 0

            data_points.append({
                "date": current.strftime("%Y-%m-%d"),
                "value": value
            })

            current = next_day

        return {
            "trend_type": trend_type,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "data_points": data_points
        }

    def generate_report(
        self,
        report_type: str,
        start_date: datetime,
        end_date: datetime,
        generated_by: str = "system"
    ) -> Dict[str, Any]:
        """生成数据报告"""
        # 获取周期内数据
        overview = self.get_dashboard_overview(
            days=(end_date - start_date).days
        )

        report_data = {
            "report_type": report_type,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "overview": overview,
            "trends": {
                "user_growth": self.get_trend_data(
                    "user_growth_trend", start_date, end_date
                ),
                "matching": self.get_trend_data(
                    "matching_success_trend", start_date, end_date
                ),
                "revenue": self.get_trend_data(
                    "revenue_trend", start_date, end_date
                )
            }
        }

        # 保存到数据库
        report = DashboardReportDB(
            id=str(uuid.uuid4()),
            report_type=report_type,
            title=f"{report_type}报告 ({start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')})",
            description=f"自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            report_data=report_data,
            generated_by=generated_by,
            start_date=start_date,
            end_date=end_date,
            status="active"
        )
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)

        return {
            "report_id": report.id,
            "report_data": report_data
        }

    def get_reports(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取报告列表"""
        reports = self.db.query(DashboardReportDB).order_by(
            desc(DashboardReportDB.created_at)
        ).limit(limit).all()

        return [
            {
                "id": r.id,
                "title": r.title,
                "report_type": r.report_type,
                "created_at": r.created_at.isoformat(),
                "status": r.status
            }
            for r in reports
        ]


class PerformanceService:
    """绩效管理服务"""

    def __init__(self, db: Session):
        self.db = db

    def get_kpi_definitions(self) -> List[Dict[str, Any]]:
        """获取 KPI 指标定义列表"""
        kpis = self.db.query(KPIMetricDB).filter(
            KPIMetricDB.is_active == True
        ).all()

        return [
            {
                "id": k.id,
                "metric_name": k.metric_name,
                "description": k.description,
                "target_value": k.target_value,
                "current_value": k.current_value,
                "weight": k.weight,
                "unit": k.unit,
                "achievement_rate": round(
                    k.current_value / max(k.target_value, 0.01) * 100, 2
                )
            }
            for k in kpis
        ]

    def update_kpi_value(
        self,
        metric_name: str,
        new_value: float
    ) -> Dict[str, Any]:
        """更新 KPI 当前值"""
        kpi = self.db.query(KPIMetricDB).filter(
            KPIMetricDB.metric_name == metric_name
        ).first()

        if not kpi:
            raise ValueError(f"KPI {metric_name} not found")

        kpi.current_value = new_value
        self.db.commit()
        self.db.refresh(kpi)

        return {
            "id": kpi.id,
            "metric_name": kpi.metric_name,
            "target_value": kpi.target_value,
            "current_value": kpi.current_value,
            "achievement_rate": round(
                kpi.current_value / max(kpi.target_value, 0.01) * 100, 2
            )
        }

    def create_performance_review(
        self,
        user_id: str,
        review_type: str,
        period_start: datetime,
        period_end: datetime,
        period_type: str,
        reviewed_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """创建绩效评估"""
        # 获取 KPI 数据
        kpis = self.db.query(KPIMetricDB).filter(
            KPIMetricDB.is_active == True
        ).all()

        # 计算各 KPI 得分
        kpi_scores = {}
        total_weighted_score = 0
        total_weight = 0

        for kpi in kpis:
            achievement_rate = kpi.current_value / max(kpi.target_value, 0.01)
            # 得分计算：达成率最高 100 分
            score = min(achievement_rate * 100, 100)
            weighted_score = score * kpi.weight

            kpi_scores[kpi.metric_name] = {
                "target": kpi.target_value,
                "actual": kpi.current_value,
                "score": round(score, 2),
                "weight": kpi.weight
            }

            total_weighted_score += weighted_score
            total_weight += kpi.weight

        # 综合评分
        overall_score = round(total_weighted_score / max(total_weight, 0.01), 2)

        # 绩效等级
        if overall_score >= 90:
            performance_level = "S"
        elif overall_score >= 80:
            performance_level = "A"
        elif overall_score >= 70:
            performance_level = "B"
        elif overall_score >= 60:
            performance_level = "C"
        else:
            performance_level = "D"

        # 创建评估记录
        review = PerformanceReviewDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            review_type=review_type,
            period_start=period_start,
            period_end=period_end,
            period_type=period_type,
            kpi_scores=kpi_scores,
            overall_score=overall_score,
            performance_level=performance_level,
            review_comments=f"自动生成的{period_type}绩效评估",
            reviewed_by=reviewed_by or "system"
        )
        self.db.add(review)
        self.db.commit()
        self.db.refresh(review)

        return {
            "review_id": review.id,
            "overall_score": review.overall_score,
            "performance_level": review.performance_level,
            "kpi_scores": kpi_scores
        }

    def get_performance_history(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """获取绩效历史"""
        reviews = self.db.query(PerformanceReviewDB).filter(
            PerformanceReviewDB.user_id == user_id
        ).order_by(
            desc(PerformanceReviewDB.created_at)
        ).limit(limit).all()

        return [
            {
                "id": r.id,
                "review_type": r.review_type,
                "period_start": r.period_start.isoformat(),
                "period_end": r.period_end.isoformat(),
                "period_type": r.period_type,
                "overall_score": r.overall_score,
                "performance_level": r.performance_level,
                "created_at": r.created_at.isoformat()
            }
            for r in reviews
        ]

    def get_performance_summary(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """获取绩效摘要"""
        # 历史平均分数
        reviews = self.db.query(PerformanceReviewDB).filter(
            PerformanceReviewDB.user_id == user_id
        ).all()

        if not reviews:
            return {
                "user_id": user_id,
                "total_reviews": 0,
                "avg_score": 0,
                "best_level": None,
                "trend": "stable"
            }

        avg_score = sum(r.overall_score for r in reviews) / len(reviews)
        levels = ["D", "C", "B", "A", "S"]
        best_level = max(levels, key=lambda x: levels.index(x) if any(r.performance_level == x for r in reviews) else -1)

        # 趋势分析 (最近 3 次)
        recent = sorted(reviews, key=lambda x: x.created_at, reverse=True)[:3]
        if len(recent) >= 2:
            recent_scores = [r.overall_score for r in recent]
            if recent_scores[0] > recent_scores[-1]:
                trend = "improving"
            elif recent_scores[0] < recent_scores[-1]:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "stable"

        return {
            "user_id": user_id,
            "total_reviews": len(reviews),
            "avg_score": round(avg_score, 2),
            "best_level": best_level,
            "trend": trend
        }


class DepartmentService:
    """组织架构服务"""

    def __init__(self, db: Session):
        self.db = db

    def create_department(
        self,
        name: str,
        code: str,
        level: int,
        parent_id: Optional[str] = None,
        description: Optional[str] = None,
        manager_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """创建部门"""
        # 检查编码是否已存在
        existing = self.db.query(DepartmentDB).filter(
            DepartmentDB.code == code
        ).first()
        if existing:
            raise ValueError(f"部门编码 {code} 已存在")

        dept = DepartmentDB(
            id=str(uuid.uuid4()),
            name=name,
            code=code,
            parent_id=parent_id,
            level=level,
            description=description,
            manager_id=manager_id,
            is_active=True,
            sort_order=0
        )
        self.db.add(dept)
        self.db.commit()
        self.db.refresh(dept)

        return self._dept_to_dict(dept)

    def get_department(self, dept_id: str) -> Optional[Dict[str, Any]]:
        """获取部门详情"""
        dept = self.db.query(DepartmentDB).filter(
            DepartmentDB.id == dept_id
        ).first()

        if not dept:
            return None

        return self._dept_to_dict(dept)

    def get_departments(self, is_active: bool = True) -> List[Dict[str, Any]]:
        """获取部门列表"""
        query = self.db.query(DepartmentDB)
        if is_active:
            query = query.filter(DepartmentDB.is_active == True)

        depts = query.order_by(DepartmentDB.level, DepartmentDB.sort_order).all()

        return [self._dept_to_dict(d) for d in depts]

    def get_department_tree(self) -> List[Dict[str, Any]]:
        """获取组织架构树"""
        # 获取所有一级部门
        root_depts = self.db.query(DepartmentDB).filter(
            DepartmentDB.level == 1,
            DepartmentDB.is_active == True
        ).order_by(DepartmentDB.sort_order).all()

        def build_tree(dept: DepartmentDB) -> Dict[str, Any]:
            """递归构建部门树"""
            children = self.db.query(DepartmentDB).filter(
                DepartmentDB.parent_id == dept.id,
                DepartmentDB.is_active == True
            ).order_by(DepartmentDB.sort_order).all()

            return {
                "id": dept.id,
                "name": dept.name,
                "code": dept.code,
                "level": dept.level,
                "description": dept.description,
                "manager_id": dept.manager_id,
                "children": [build_tree(child) for child in children]
            }

        return [build_tree(dept) for dept in root_depts]

    def update_department(
        self,
        dept_id: str,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """更新部门"""
        dept = self.db.query(DepartmentDB).filter(
            DepartmentDB.id == dept_id
        ).first()

        if not dept:
            return None

        # 更新允许的字段
        allowed_fields = ["name", "code", "level", "parent_id", "description", "manager_id", "sort_order"]
        for field in allowed_fields:
            if field in kwargs:
                setattr(dept, field, kwargs[field])

        self.db.commit()
        self.db.refresh(dept)

        return self._dept_to_dict(dept)

    def delete_department(self, dept_id: str) -> bool:
        """删除部门 (软删除)"""
        dept = self.db.query(DepartmentDB).filter(
            DepartmentDB.id == dept_id
        ).first()

        if not dept:
            return False

        dept.is_active = False
        self.db.commit()

        return True

    def _dept_to_dict(self, dept: DepartmentDB) -> Dict[str, Any]:
        """将部门对象转换为字典"""
        return {
            "id": dept.id,
            "name": dept.name,
            "code": dept.code,
            "parent_id": dept.parent_id,
            "level": dept.level,
            "description": dept.description,
            "manager_id": dept.manager_id,
            "is_active": dept.is_active,
            "sort_order": dept.sort_order,
            "created_at": dept.created_at.isoformat() if dept.created_at else None,
            "updated_at": dept.updated_at.isoformat() if dept.updated_at else None
        }


class OperatorService:
    """运营角色服务"""

    def __init__(self, db: Session):
        self.db = db

    def create_role(
        self,
        role_name: str,
        description: str,
        permissions: List[str]
    ) -> Dict[str, Any]:
        """创建角色"""
        role = OperatorRoleDB(
            id=str(uuid.uuid4()),
            role_name=role_name,
            description=description,
            permissions=permissions,
            is_active=True
        )
        self.db.add(role)
        self.db.commit()
        self.db.refresh(role)

        return self._role_to_dict(role)

    def get_roles(self, is_active: bool = True) -> List[Dict[str, Any]]:
        """获取角色列表"""
        query = self.db.query(OperatorRoleDB)
        if is_active:
            query = query.filter(OperatorRoleDB.is_active == True)

        roles = query.all()
        return [self._role_to_dict(r) for r in roles]

    def assign_role_to_user(
        self,
        user_id: str,
        role_id: str,
        department_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """给用户分配角色"""
        # 检查是否已有角色
        existing = self.db.query(UserOperatorDB).filter(
            UserOperatorDB.user_id == user_id,
            UserOperatorDB.is_active == True
        ).first()

        if existing:
            # 更新现有角色
            existing.role_id = role_id
            existing.department_id = department_id
            self.db.commit()
            self.db.refresh(existing)
            operator = existing
        else:
            # 创建新分配
            operator = UserOperatorDB(
                id=str(uuid.uuid4()),
                user_id=user_id,
                role_id=role_id,
                department_id=department_id,
                is_active=True
            )
            self.db.add(operator)
            self.db.commit()
            self.db.refresh(operator)

        return {
            "user_id": user_id,
            "role_id": role_id,
            "department_id": department_id,
            "appointed_at": operator.appointed_at.isoformat()
        }

    def get_user_roles(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户的角色"""
        operators = self.db.query(UserOperatorDB).filter(
            UserOperatorDB.user_id == user_id,
            UserOperatorDB.is_active == True
        ).all()

        result = []
        for op in operators:
            role = self.db.query(OperatorRoleDB).filter(
                OperatorRoleDB.id == op.role_id
            ).first()
            if role:
                result.append({
                    "role": self._role_to_dict(role),
                    "department_id": op.department_id,
                    "appointed_at": op.appointed_at.isoformat()
                })

        return result

    def get_user_permissions(self, user_id: str) -> List[str]:
        """获取用户权限列表"""
        operators = self.db.query(UserOperatorDB).filter(
            UserOperatorDB.user_id == user_id,
            UserOperatorDB.is_active == True
        ).all()

        permissions = set()
        for op in operators:
            role = self.db.query(OperatorRoleDB).filter(
                OperatorRoleDB.id == op.role_id
            ).first()
            if role:
                permissions.update(role.permissions)

        return list(permissions)

    def log_operator_action(
        self,
        operator_id: str,
        action_type: str,
        target_type: Optional[str],
        target_id: Optional[str],
        action_details: Optional[Dict],
        result: str,
        ip_address: Optional[str]
    ) -> Dict[str, Any]:
        """记录运营操作日志"""
        log = OperatorActionLogDB(
            id=str(uuid.uuid4()),
            operator_id=operator_id,
            action_type=action_type,
            target_type=target_type,
            target_id=target_id,
            action_details=action_details,
            result=result,
            ip_address=ip_address
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)

        return {
            "log_id": log.id,
            "operator_id": log.operator_id,
            "action_type": log.action_type,
            "created_at": log.created_at.isoformat()
        }

    def get_action_logs(
        self,
        operator_id: Optional[str] = None,
        action_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """获取操作日志"""
        query = self.db.query(OperatorActionLogDB)

        if operator_id:
            query = query.filter(OperatorActionLogDB.operator_id == operator_id)
        if action_type:
            query = query.filter(OperatorActionLogDB.action_type == action_type)

        logs = query.order_by(
            desc(OperatorActionLogDB.created_at)
        ).limit(limit).all()

        return [
            {
                "id": log.id,
                "operator_id": log.operator_id,
                "action_type": log.action_type,
                "target_type": log.target_type,
                "target_id": log.target_id,
                "result": log.result,
                "ip_address": log.ip_address,
                "created_at": log.created_at.isoformat(),
                "action_details": log.action_details
            }
            for log in logs
        ]

    def _role_to_dict(self, role: OperatorRoleDB) -> Dict[str, Any]:
        """将角色对象转换为字典"""
        return {
            "id": role.id,
            "role_name": role.role_name,
            "description": role.description,
            "permissions": role.permissions,
            "is_active": role.is_active,
            "created_at": role.created_at.isoformat() if role.created_at else None
        }


class ExportService:
    """数据导出服务"""

    def __init__(self, db: Session):
        self.db = db

    def create_export_task(
        self,
        requested_by: str,
        export_type: str,
        export_format: str,
        export_params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """创建导出任务"""
        task = ExportTaskDB(
            id=str(uuid.uuid4()),
            requested_by=requested_by,
            export_type=export_type,
            export_format=export_format,
            export_params=export_params,
            status="pending"
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)

        return {
            "task_id": task.id,
            "status": task.status,
            "export_type": task.export_type,
            "export_format": task.export_format,
            "created_at": task.created_at.isoformat()
        }

    def get_export_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取导出任务状态"""
        task = self.db.query(ExportTaskDB).filter(
            ExportTaskDB.id == task_id
        ).first()

        if not task:
            return None

        return {
            "task_id": task.id,
            "requested_by": task.requested_by,
            "export_type": task.export_type,
            "export_format": task.export_format,
            "status": task.status,
            "file_url": task.file_url,
            "file_size": task.file_size,
            "error_message": task.error_message,
            "created_at": task.created_at.isoformat(),
            "completed_at": task.completed_at.isoformat() if task.completed_at else None
        }

    def get_export_history(
        self,
        requested_by: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """获取导出历史"""
        tasks = self.db.query(ExportTaskDB).filter(
            ExportTaskDB.requested_by == requested_by
        ).order_by(
            desc(ExportTaskDB.created_at)
        ).limit(limit).all()

        return [
            {
                "task_id": task.id,
                "export_type": task.export_type,
                "export_format": task.export_format,
                "status": task.status,
                "created_at": task.created_at.isoformat(),
                "completed_at": task.completed_at.isoformat() if task.completed_at else None
            }
            for task in tasks
        ]

    def complete_export_task(
        self,
        task_id: str,
        file_url: str,
        file_size: int
    ) -> bool:
        """标记导出任务完成"""
        task = self.db.query(ExportTaskDB).filter(
            ExportTaskDB.id == task_id
        ).first()

        if not task:
            return False

        task.status = "completed"
        task.file_url = file_url
        task.file_size = file_size
        task.completed_at = datetime.now()
        task.expires_at = datetime.now() + timedelta(days=7)  # 7 天后过期

        self.db.commit()
        return True

    def fail_export_task(
        self,
        task_id: str,
        error_message: str
    ) -> bool:
        """标记导出任务失败"""
        task = self.db.query(ExportTaskDB).filter(
            ExportTaskDB.id == task_id
        ).first()

        if not task:
            return False

        task.status = "failed"
        task.error_message = error_message
        task.completed_at = datetime.now()

        self.db.commit()
        return True
