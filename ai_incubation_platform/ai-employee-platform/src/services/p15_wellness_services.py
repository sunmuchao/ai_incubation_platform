"""
P15 员工福祉管理 - 服务层
版本：v15.0.0
主题：员工福祉管理 (Employee Wellness Management)
"""

from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import asdict
import math

from models.p15_models import (
    # 枚举
    RiskLevel, AssessmentType, SurveyType, QuestionType, LeaveType, LeaveStatus,
    BenefitType, InterventionType, InterventionStatus, AlertType, AlertSeverity,
    CounselingType, CounselingStatus,
    # 模型
    MentalHealthAssessment, StressLevel, CounselingSession, WellnessResource,
    WorkHourLog, OvertimeRecord, WorkLifeBalanceMetrics,
    BenefitPlan, EmployeeBenefitEnrollment, LeaveBalance, LeaveRequest, SubsidyRecord,
    SatisfactionSurvey, SurveyQuestion, SurveyResponse, PulseSurvey, SatisfactionTrend,
    TurnoverRiskPrediction, EngagementScore, RetentionIntervention, RiskFactor,
    WellnessAlert,
    # 数据库
    WellnessDB,
)


# ============================================================================
# 心理健康服务
# ============================================================================

class MentalHealthService:
    """心理健康服务"""

    def __init__(self, db: WellnessDB):
        self.db = db

    def create_assessment(self, employee_id: str, assessment_type: AssessmentType,
                         overall_score: float, dimensions: Dict[str, float],
                         risk_factors: List[str], recommendations: List[str],
                         assessor_id: Optional[str] = None,
                         notes: Optional[str] = None) -> MentalHealthAssessment:
        """创建心理健康评估"""
        assessment = MentalHealthAssessment(
            employee_id=employee_id,
            assessment_type=assessment_type,
            overall_score=overall_score,
            dimensions=dimensions,
            risk_factors=risk_factors,
            recommendations=recommendations,
            assessor_id=assessor_id,
            notes=notes,
        )
        self.db.insert("mental_health_assessments", assessment.to_dict())
        return assessment

    def get_assessment(self, assessment_id: str) -> Optional[MentalHealthAssessment]:
        """获取评估详情"""
        data = self.db.get("mental_health_assessments", assessment_id)
        return MentalHealthAssessment.from_dict(data) if data else None

    def list_assessments(self, employee_id: Optional[str] = None,
                        assessment_type: Optional[AssessmentType] = None,
                        limit: int = 100) -> List[MentalHealthAssessment]:
        """列出评估记录"""
        filters = {}
        if employee_id:
            filters["employee_id"] = employee_id
        if assessment_type:
            filters["assessment_type"] = assessment_type.value

        rows = self.db.list("mental_health_assessments", filters, order_by="created_at DESC", limit=limit)
        return [MentalHealthAssessment.from_dict(row) for row in rows]

    def record_stress_level(self, employee_id: str, stress_score: float,
                           stress_sources: List[str], emotional_state: str,
                           physical_symptoms: Optional[List[str]] = None,
                           sleep_quality: Optional[float] = None,
                           energy_level: Optional[float] = None,
                           measurement_method: Optional[str] = None) -> StressLevel:
        """记录压力水平"""
        stress = StressLevel(
            employee_id=employee_id,
            stress_score=stress_score,
            stress_sources=stress_sources,
            emotional_state=emotional_state,
            physical_symptoms=physical_symptoms or [],
            sleep_quality=sleep_quality,
            energy_level=energy_level,
            measurement_method=measurement_method,
        )
        self.db.insert("stress_levels", stress.to_dict())

        # 如果压力过高，生成预警
        if stress_score >= 80:
            self._create_stress_alert(employee_id, stress_score)

        return stress

    def _create_stress_alert(self, employee_id: str, stress_score: float):
        """创建高压力预警"""
        severity = AlertSeverity.CRITICAL if stress_score >= 90 else AlertSeverity.WARNING
        alert = WellnessAlert(
            employee_id=employee_id,
            alert_type=AlertType.MENTAL_HEALTH,
            severity=severity,
            title="高压力水平预警",
            description=f"员工压力指数达到 {stress_score}，建议及时关注并提供支持",
            trigger_value=stress_score,
            threshold_value=80,
        )
        self.db.insert("wellness_alerts", alert.to_dict())

    def get_stress_history(self, employee_id: str, days: int = 30) -> List[StressLevel]:
        """获取压力历史记录"""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        conn = self.db._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM stress_levels WHERE employee_id = ? AND recorded_at >= ? ORDER BY recorded_at DESC",
            (employee_id, cutoff)
        )
        rows = cursor.fetchall()
        
        return [StressLevel.from_dict(dict(row)) for row in rows]

    def schedule_counseling(self, employee_id: str, counselor_id: str,
                           counseling_type: CounselingType, session_date: datetime,
                           duration_minutes: int = 60) -> CounselingSession:
        """预约心理咨询"""
        session = CounselingSession(
            employee_id=employee_id,
            counselor_id=counselor_id,
            counseling_type=counseling_type,
            session_date=session_date,
            duration_minutes=duration_minutes,
            status=CounselingStatus.SCHEDULED,
            session_number=1,
        )
        # 查询该员工已有的咨询次数
        sessions = self.list_counseling_sessions(employee_id)
        if sessions:
            session.session_number = max(s.session_number for s in sessions) + 1

        self.db.insert("counseling_sessions", session.to_dict())
        return session

    def complete_counseling_session(self, session_id: str, notes: str,
                                   follow_up_required: bool = False,
                                   follow_up_date: Optional[datetime] = None) -> CounselingSession:
        """完成心理咨询会话"""
        session = self.get_counseling_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        session.status = CounselingStatus.COMPLETED
        session.notes = notes
        session.follow_up_required = follow_up_required
        session.follow_up_date = follow_up_date
        session.updated_at = datetime.now()

        self.db.update("counseling_sessions", session_id, session.to_dict())
        return session

    def get_counseling_session(self, session_id: str) -> Optional[CounselingSession]:
        """获取咨询会话详情"""
        data = self.db.get("counseling_sessions", session_id)
        return CounselingSession.from_dict(data) if data else None

    def list_counseling_sessions(self, employee_id: str) -> List[CounselingSession]:
        """列出咨询会话"""
        rows = self.db.list("counseling_sessions", {"employee_id": employee_id},
                           order_by="session_date DESC")
        return [CounselingSession.from_dict(row) for row in rows]

    def add_wellness_resource(self, title: str, description: str,
                             resource_type: str, category: str,
                             url: Optional[str] = None,
                             content: Optional[str] = None,
                             tags: Optional[List[str]] = None,
                             is_featured: bool = False) -> WellnessResource:
        """添加健康资源"""
        resource = WellnessResource(
            title=title,
            description=description,
            resource_type=resource_type,
            category=category,
            url=url,
            content=content,
            tags=tags or [],
            is_featured=is_featured,
        )
        self.db.insert("wellness_resources", resource.to_dict())
        return resource

    def list_wellness_resources(self, category: Optional[str] = None,
                               is_featured: Optional[bool] = None,
                               search: Optional[str] = None) -> List[WellnessResource]:
        """列出健康资源"""
        filters = {}
        if category:
            filters["category"] = category
        if is_featured is not None:
            filters["is_featured"] = 1 if is_featured else 0

        rows = self.db.list("wellness_resources", filters, order_by="created_at DESC")
        resources = [WellnessResource.from_dict(row) for row in rows]

        if search:
            search_lower = search.lower()
            resources = [r for r in resources if
                        search_lower in r.title.lower() or
                        search_lower in r.description.lower() or
                        any(search_lower in tag for tag in r.tags)]

        return resources

    def get_stress_statistics(self, team_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """获取压力统计数据"""
        conn = self.db._get_connection()
        cursor = conn.cursor()

        # 平均压力分数
        cursor.execute("SELECT AVG(stress_score) as avg_score FROM stress_levels")
        row = cursor.fetchone()
        avg_score = row["avg_score"] if row and row["avg_score"] else 0

        # 压力分布
        cursor.execute("""
            SELECT
                SUM(CASE WHEN stress_score < 30 THEN 1 ELSE 0 END) as low,
                SUM(CASE WHEN stress_score >= 30 AND stress_score < 70 THEN 1 ELSE 0 END) as medium,
                SUM(CASE WHEN stress_score >= 70 THEN 1 ELSE 0 END) as high
            FROM stress_levels
            WHERE recorded_at >= date('now', '-30 days')
        """)
        row = cursor.fetchone()
        distribution = {
            "low": row["low"] or 0,
            "medium": row["medium"] or 0,
            "high": row["high"] or 0,
        } if row else {"low": 0, "medium": 0, "high": 0}

        

        return {
            "average_score": round(avg_score, 2),
            "distribution": distribution,
            "total_records": sum(distribution.values()),
        }


# ============================================================================
# 工作生活平衡服务
# ============================================================================

class WorkLifeBalanceService:
    """工作生活平衡服务"""

    # 配置常量
    MAX_DAILY_HOURS = 12
    MAX_WEEKLY_HOURS = 60
    MIN_BREAK_AFTER_HOURS = 4  # 连续工作 4 小时后需要休息
    BREAK_MINUTES = 15
    MAX_CONSECUTIVE_WORK_DAYS = 6

    def __init__(self, db: WellnessDB):
        self.db = db

    def log_work_hours(self, employee_id: str, work_date: date,
                      start_time: datetime, end_time: datetime,
                      break_minutes: int = 0, work_type: str = "office",
                      project_id: Optional[str] = None,
                      task_description: Optional[str] = None) -> WorkHourLog:
        """记录工时"""
        log = WorkHourLog(
            employee_id=employee_id,
            work_date=work_date,
            start_time=start_time,
            end_time=end_time,
            break_minutes=break_minutes,
            work_type=work_type,
            project_id=project_id,
            task_description=task_description,
            is_overtime=work_type == "overtime" or self._is_overtime(work_date, start_time, end_time, break_minutes),
        )
        self.db.insert("work_hour_logs", log.to_dict())

        # 检查是否需要生成预警
        self._check_and_create_alerts(employee_id, work_date, log.total_hours)

        return log

    def _is_overtime(self, work_date: date, start_time: datetime,
                    end_time: datetime, break_minutes: int) -> bool:
        """判断是否属于加班"""
        hours = (end_time - start_time).total_seconds() / 3600 - break_minutes / 60
        return hours > self.MAX_DAILY_HOURS

    def _check_and_create_alerts(self, employee_id: str, work_date: date, hours: float):
        """检查并创建预警"""
        # 检查单日超时
        if hours > self.MAX_DAILY_HOURS:
            alert = WellnessAlert(
                employee_id=employee_id,
                alert_type=AlertType.OVERTIME,
                severity=AlertSeverity.WARNING if hours <= 14 else AlertSeverity.CRITICAL,
                title="单日工作时间过长",
                description=f"员工在 {work_date} 工作了 {hours:.1f} 小时，超过建议上限 {self.MAX_DAILY_HOURS} 小时",
                trigger_value=hours,
                threshold_value=self.MAX_DAILY_HOURS,
                related_entity_id=employee_id,
            )
            self.db.insert("wellness_alerts", alert.to_dict())

        # 检查连续工作天数
        consecutive_days = self._get_consecutive_work_days(employee_id, work_date)
        if consecutive_days >= self.MAX_CONSECUTIVE_WORK_DAYS:
            alert = WellnessAlert(
                employee_id=employee_id,
                alert_type=AlertType.WORK_LIFE_IMBALANCE,
                severity=AlertSeverity.WARNING,
                title="连续工作天数过多",
                description=f"员工已连续工作 {consecutive_days} 天，建议安排休息",
                trigger_value=consecutive_days,
                threshold_value=self.MAX_CONSECUTIVE_WORK_DAYS,
            )
            self.db.insert("wellness_alerts", alert.to_dict())

    def _get_consecutive_work_days(self, employee_id: str, end_date: date) -> int:
        """获取连续工作天数"""
        conn = self.db._get_connection()
        cursor = conn.cursor()

        # 获取最近的工作记录
        cursor.execute("""
            SELECT DISTINCT work_date FROM work_hour_logs
            WHERE employee_id = ? AND work_date <= ?
            ORDER BY work_date DESC
            LIMIT 30
        """, (employee_id, end_date.isoformat()))
        rows = cursor.fetchall()
        

        if not rows:
            return 0

        dates = [date.fromisoformat(row["work_date"]) for row in rows]
        consecutive = 1
        for i in range(1, len(dates)):
            if (dates[i-1] - dates[i]).days == 1:
                consecutive += 1
            else:
                break

        return consecutive

    def record_overtime(self, employee_id: str, overtime_date: date,
                       start_time: datetime, end_time: datetime,
                       reason: str, compensation_type: str = "time_off") -> OvertimeRecord:
        """记录加班"""
        record = OvertimeRecord(
            employee_id=employee_id,
            overtime_date=overtime_date,
            start_time=start_time,
            end_time=end_time,
            reason=reason,
            compensation_type=compensation_type,
        )
        self.db.insert("overtime_records", record.to_dict())
        return record

    def approve_overtime(self, overtime_id: str, approver_id: str,
                        compensation_hours: Optional[float] = None) -> OvertimeRecord:
        """审批加班"""
        record = self.get_overtime(overtime_id)
        if not record:
            raise ValueError(f"Overtime record {overtime_id} not found")

        record.approved = True
        record.approver_id = approver_id
        record.approval_date = datetime.now()
        record.compensation_hours = compensation_hours or record.overtime_hours

        self.db.update("overtime_records", overtime_id, record.to_dict())
        return record

    def get_overtime(self, overtime_id: str) -> Optional[OvertimeRecord]:
        """获取加班记录"""
        data = self.db.get("overtime_records", overtime_id)
        return OvertimeRecord.from_dict(data) if data else None

    def list_overtime_records(self, employee_id: Optional[str] = None,
                             start_date: Optional[date] = None,
                             end_date: Optional[date] = None) -> List[OvertimeRecord]:
        """列出加班记录"""
        filters = {}
        if employee_id:
            filters["employee_id"] = employee_id

        rows = self.db.list("overtime_records", filters, order_by="overtime_date DESC")
        records = [OvertimeRecord.from_dict(row) for row in rows]

        # 日期过滤
        if start_date:
            records = [r for r in records if r.overtime_date >= start_date]
        if end_date:
            records = [r for r in records if r.overtime_date <= end_date]

        return records

    def calculate_balance_score(self, employee_id: str,
                               period_start: Optional[date] = None,
                               period_end: Optional[date] = None) -> WorkLifeBalanceMetrics:
        """计算工作生活平衡分数"""
        if period_end is None:
            period_end = date.today()
        if period_start is None:
            period_start = period_end - timedelta(days=30)

        # 获取工时数据
        work_logs = self._get_work_logs_in_period(employee_id, period_start, period_end)

        # 计算各项指标
        total_hours = sum(log.total_hours for log in work_logs)
        work_days = len(set(log.work_date for log in work_logs))
        avg_daily_hours = total_hours / work_days if work_days > 0 else 0

        # 计算加班比例
        overtime_hours = sum(log.total_hours - 8 for log in work_logs if log.total_hours > 8)
        expected_hours = work_days * 8
        overtime_ratio = overtime_hours / expected_hours if expected_hours > 0 else 0

        # 计算周末工作天数
        weekend_days = sum(1 for log in work_logs if log.work_date.weekday() >= 5)

        # 获取连续工作天数
        consecutive_days = self._get_consecutive_work_days(employee_id, period_end)

        # 计算各子分数
        work_hours_score = max(0, 100 - (avg_daily_hours - 8) * 20) if avg_daily_hours > 8 else 100
        rest_compliance_score = max(0, 100 - (consecutive_days - 5) * 20) if consecutive_days > 5 else 100
        overtime_score = max(0, 100 - overtime_ratio * 100)

        # 获取假期使用分数
        vacation_score = self._calculate_vacation_utilization_score(employee_id)

        # 综合平衡分数
        balance_score = (
            work_hours_score * 0.30 +
            rest_compliance_score * 0.25 +
            overtime_score * 0.20 +
            vacation_score * 0.25
        )

        # 确定风险等级
        if balance_score >= 80:
            risk_level = RiskLevel.LOW
        elif balance_score >= 60:
            risk_level = RiskLevel.MEDIUM
        elif balance_score >= 40:
            risk_level = RiskLevel.HIGH
        else:
            risk_level = RiskLevel.CRITICAL

        # 生成建议
        recommendations = self._generate_balance_recommendations(
            balance_score, avg_daily_hours, overtime_ratio, consecutive_days
        )

        metrics = WorkLifeBalanceMetrics(
            employee_id=employee_id,
            balance_score=round(balance_score, 2),
            work_hours_score=round(work_hours_score, 2),
            rest_compliance_score=round(rest_compliance_score, 2),
            vacation_utilization_score=round(vacation_score, 2),
            overtime_ratio=round(overtime_ratio, 4),
            weekend_work_days=weekend_days,
            average_daily_hours=round(avg_daily_hours, 2),
            consecutive_work_days=consecutive_days,
            risk_level=risk_level,
            recommendations=recommendations,
            period_start=period_start,
            period_end=period_end,
        )

        # 保存记录
        self.db.insert("work_life_balance_metrics", metrics.to_dict())

        return metrics

    def _get_work_logs_in_period(self, employee_id: str,
                                period_start: date, period_end: date) -> List[WorkHourLog]:
        """获取指定期间的工时记录"""
        conn = self.db._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM work_hour_logs
            WHERE employee_id = ? AND work_date BETWEEN ? AND ?
            ORDER BY work_date DESC
        """, (employee_id, period_start.isoformat(), period_end.isoformat()))
        rows = cursor.fetchall()
        
        return [WorkHourLog.from_dict(dict(row)) for row in rows]

    def _calculate_vacation_utilization_score(self, employee_id: str) -> float:
        """计算假期使用分数"""
        balances = self._get_leave_balances(employee_id)
        if not balances:
            return 50  # 默认分数

        total_score = 0
        count = 0
        for balance in balances:
            if balance.leave_type == LeaveType.ANNUAL:
                # 年假使用率在 70-100% 之间得满分
                utilization = balance.used_days / balance.total_days if balance.total_days > 0 else 0
                if 0.7 <= utilization <= 1.0:
                    total_score += 100
                elif utilization < 0.7:
                    total_score += utilization * 100 / 0.7
                else:
                    total_score += 80  # 超额使用扣分
                count += 1

        return total_score / count if count > 0 else 50

    def _get_leave_balances(self, employee_id: str) -> List[LeaveBalance]:
        """获取员工假期余额"""
        rows = self.db.list("leave_balances", {"employee_id": employee_id})
        return [LeaveBalance.from_dict(row) for row in rows]

    def _generate_balance_recommendations(self, balance_score: float,
                                         avg_daily_hours: float,
                                         overtime_ratio: float,
                                         consecutive_days: int) -> List[str]:
        """生成平衡建议"""
        recommendations = []

        if avg_daily_hours > 10:
            recommendations.append("建议减少每日工作时长，保持可持续的工作节奏")
        if overtime_ratio > 0.2:
            recommendations.append("加班比例过高，建议重新分配工作量或增加人手")
        if consecutive_days >= 6:
            recommendations.append("连续工作天数过多，建议安排至少 1 天休息")
        if balance_score < 60:
            recommendations.append("工作生活平衡状况堪忧，建议与管理者沟通调整工作安排")
        elif balance_score < 80:
            recommendations.append("工作生活平衡有待改善，注意适时休息")

        if not recommendations:
            recommendations.append("工作生活平衡状况良好，请继续保持")

        return recommendations

    def get_balance_history(self, employee_id: str,
                           months: int = 6) -> List[WorkLifeBalanceMetrics]:
        """获取平衡历史"""
        start_date = date.today() - timedelta(days=months * 30)
        rows = self.db.list("work_life_balance_metrics",
                           {"employee_id": employee_id},
                           order_by="calculated_at DESC")
        metrics = [WorkLifeBalanceMetrics.from_dict(row) for row in rows]
        return [m for m in metrics if m.period_start and m.period_start >= start_date]


# ============================================================================
# 福利管理服务
# ============================================================================

class BenefitsService:
    """福利管理服务"""

    def __init__(self, db: WellnessDB):
        self.db = db

    def create_benefit_plan(self, name: str, description: str,
                           benefit_type: BenefitType,
                           coverage_type: str = "all",
                           coverage_criteria: Optional[Dict[str, Any]] = None,
                           provider: Optional[str] = None,
                           coverage_amount: Optional[float] = None,
                           employee_contribution: float = 0.0,
                           employer_contribution: float = 1.0,
                           effective_date: Optional[date] = None) -> BenefitPlan:
        """创建福利计划"""
        plan = BenefitPlan(
            name=name,
            description=description,
            benefit_type=benefit_type,
            coverage_type=coverage_type,
            coverage_criteria=coverage_criteria or {},
            provider=provider,
            coverage_amount=coverage_amount,
            employee_contribution=employee_contribution,
            employer_contribution=employer_contribution,
            effective_date=effective_date or date.today(),
        )
        self.db.insert("benefit_plans", plan.to_dict())
        return plan

    def get_benefit_plan(self, plan_id: str) -> Optional[BenefitPlan]:
        """获取福利计划详情"""
        data = self.db.get("benefit_plans", plan_id)
        return BenefitPlan.from_dict(data) if data else None

    def list_benefit_plans(self, benefit_type: Optional[BenefitType] = None,
                          is_active: bool = True) -> List[BenefitPlan]:
        """列出福利计划"""
        filters = {}
        if benefit_type:
            filters["benefit_type"] = benefit_type.value
        if is_active is not None:
            filters["is_active"] = 1 if is_active else 0

        rows = self.db.list("benefit_plans", filters)
        return [BenefitPlan.from_dict(row) for row in rows]

    def enroll_employee(self, employee_id: str, plan_id: str,
                       beneficiary_name: Optional[str] = None,
                       beneficiary_relationship: Optional[str] = None,
                       coverage_start_date: Optional[date] = None) -> EmployeeBenefitEnrollment:
        """员工注册福利计划"""
        enrollment = EmployeeBenefitEnrollment(
            employee_id=employee_id,
            plan_id=plan_id,
            enrollment_date=date.today(),
            status="active",
            beneficiary_name=beneficiary_name,
            beneficiary_relationship=beneficiary_relationship,
            coverage_start_date=coverage_start_date or date.today(),
        )
        self.db.insert("employee_benefit_enrollments", enrollment.to_dict())

        # 更新计划的注册人数
        plan = self.get_benefit_plan(plan_id)
        if plan:
            plan.enrollment_count += 1
            self.db.update("benefit_plans", plan_id, plan.to_dict())

        return enrollment

    def get_employee_benefits(self, employee_id: str) -> List[EmployeeBenefitEnrollment]:
        """获取员工的福利"""
        rows = self.db.list("employee_benefit_enrollments",
                           {"employee_id": employee_id})
        return [EmployeeBenefitEnrollment.from_dict(row) for row in rows]

    # 假期管理
    def get_leave_balance(self, employee_id: str, leave_type: LeaveType,
                         year: int = None) -> Optional[LeaveBalance]:
        """获取假期余额"""
        if year is None:
            year = datetime.now().year

        rows = self.db.list("leave_balances",
                           {"employee_id": employee_id, "leave_type": leave_type.value, "year": year})
        if rows:
            return LeaveBalance.from_dict(rows[0])
        return None

    def get_all_leave_balances(self, employee_id: str,
                               year: int = None) -> List[LeaveBalance]:
        """获取员工所有假期余额"""
        if year is None:
            year = datetime.now().year

        rows = self.db.list("leave_balances",
                           {"employee_id": employee_id, "year": year})
        return [LeaveBalance.from_dict(row) for row in rows]

    def update_leave_balance(self, employee_id: str, leave_type: LeaveType,
                            total_days: float, year: int = None) -> LeaveBalance:
        """更新假期余额（如年假累计）"""
        if year is None:
            year = datetime.now().year

        existing = self.get_leave_balance(employee_id, leave_type, year)

        if existing:
            existing.total_days = total_days
            existing.remaining_days = total_days - existing.used_days
            existing.updated_at = datetime.now()
            self.db.update("leave_balances", existing.id, existing.to_dict())
            return existing
        else:
            balance = LeaveBalance(
                employee_id=employee_id,
                leave_type=leave_type,
                total_days=total_days,
                used_days=0,
                remaining_days=total_days,
                accrued_days=total_days,
                year=year,
            )
            self.db.insert("leave_balances", balance.to_dict())
            return balance

    def request_leave(self, employee_id: str, leave_type: LeaveType,
                     start_date: date, end_date: date,
                     reason: str, handover_notes: Optional[str] = None,
                     contact_during_leave: Optional[str] = None) -> LeaveRequest:
        """申请假期"""
        # 检查假期余额
        balance = self.get_leave_balance(employee_id, leave_type)
        total_days = (end_date - start_date).days + 1

        if balance and balance.remaining_days < total_days:
            raise ValueError(f"假期余额不足：剩余 {balance.remaining_days} 天，申请 {total_days} 天")

        request = LeaveRequest(
            employee_id=employee_id,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            reason=reason,
            handover_notes=handover_notes,
            contact_during_leave=contact_during_leave,
        )
        self.db.insert("leave_requests", request.to_dict())
        return request

    def approve_leave(self, leave_id: str, approver_id: str) -> LeaveRequest:
        """审批假期"""
        request = self.get_leave_request(leave_id)
        if not request:
            raise ValueError(f"Leave request {leave_id} not found")

        request.status = LeaveStatus.APPROVED
        request.approver_id = approver_id
        request.approval_date = datetime.now()

        self.db.update("leave_requests", leave_id, request.to_dict())

        # 更新假期余额
        balance = self.get_leave_balance(request.employee_id, request.leave_type)
        if balance:
            balance.used_days += request.total_days
            balance.remaining_days -= request.total_days
            self.db.update("leave_balances", balance.id, balance.to_dict())

        return request

    def reject_leave(self, leave_id: str, approver_id: str,
                    rejection_reason: str) -> LeaveRequest:
        """拒绝假期申请"""
        request = self.get_leave_request(leave_id)
        if not request:
            raise ValueError(f"Leave request {leave_id} not found")

        request.status = LeaveStatus.REJECTED
        request.approver_id = approver_id
        request.rejection_reason = rejection_reason
        request.updated_at = datetime.now()

        self.db.update("leave_requests", leave_id, request.to_dict())
        return request

    def get_leave_request(self, leave_id: str) -> Optional[LeaveRequest]:
        """获取假期申请"""
        data = self.db.get("leave_requests", leave_id)
        return LeaveRequest.from_dict(data) if data else None

    def list_leave_requests(self, employee_id: Optional[str] = None,
                           status: Optional[LeaveStatus] = None) -> List[LeaveRequest]:
        """列出假期申请"""
        filters = {}
        if employee_id:
            filters["employee_id"] = employee_id
        if status:
            filters["status"] = status.value

        rows = self.db.list("leave_requests", filters, order_by="created_at DESC")
        return [LeaveRequest.from_dict(row) for row in rows]

    def record_subsidy(self, employee_id: str, subsidy_type: str,
                      amount: float, period_start: date,
                      period_end: date,
                      description: Optional[str] = None) -> SubsidyRecord:
        """记录补贴"""
        record = SubsidyRecord(
            employee_id=employee_id,
            subsidy_type=subsidy_type,
            amount=amount,
            period_start=period_start,
            period_end=period_end,
            description=description,
        )
        self.db.insert("subsidy_records", record.to_dict())
        return record

    def list_subsidies(self, employee_id: str,
                      period_start: Optional[date] = None,
                      period_end: Optional[date] = None) -> List[SubsidyRecord]:
        """列出补贴记录"""
        filters = {"employee_id": employee_id}
        rows = self.db.list("subsidy_records", filters, order_by="created_at DESC")
        records = [SubsidyRecord.from_dict(row) for row in rows]

        if period_start:
            records = [r for r in records if r.period_start >= period_start]
        if period_end:
            records = [r for r in records if r.period_end <= period_end]

        return records


# ============================================================================
# 调查服务
# ============================================================================

class SurveyService:
    """满意度调查服务"""

    def __init__(self, db: WellnessDB):
        self.db = db

    def create_survey(self, title: str, description: str,
                     survey_type: SurveyType,
                     is_anonymous: bool = True,
                     target_audience: str = "all",
                     target_criteria: Optional[Dict[str, Any]] = None,
                     start_date: Optional[datetime] = None,
                     end_date: Optional[datetime] = None) -> SatisfactionSurvey:
        """创建调查问卷"""
        survey = SatisfactionSurvey(
            title=title,
            description=description,
            survey_type=survey_type,
            is_anonymous=is_anonymous,
            target_audience=target_audience,
            target_criteria=target_criteria or {},
            start_date=start_date,
            end_date=end_date,
        )
        self.db.insert("satisfaction_surveys", survey.to_dict())
        return survey

    def add_question(self, survey_id: str, question_text: str,
                    question_type: QuestionType, order: int,
                    is_required: bool = True,
                    options: Optional[List[str]] = None,
                    min_value: Optional[float] = None,
                    max_value: Optional[float] = None) -> SurveyQuestion:
        """添加调查问题"""
        question = SurveyQuestion(
            survey_id=survey_id,
            question_text=question_text,
            question_type=question_type,
            order=order,
            is_required=is_required,
            options=options,
            min_value=min_value,
            max_value=max_value,
        )
        self.db.insert("survey_questions", question.to_dict())
        return question

    def get_survey(self, survey_id: str) -> Optional[SatisfactionSurvey]:
        """获取问卷详情"""
        data = self.db.get("satisfaction_surveys", survey_id)
        return SatisfactionSurvey.from_dict(data) if data else None

    def get_survey_questions(self, survey_id: str) -> List[SurveyQuestion]:
        """获取问卷问题"""
        rows = self.db.list("survey_questions", {"survey_id": survey_id},
                           order_by="orders")
        return [SurveyQuestion.from_dict(row) for row in rows]

    def list_surveys(self, survey_type: Optional[SurveyType] = None,
                    is_active: Optional[bool] = None) -> List[SatisfactionSurvey]:
        """列出问卷"""
        filters = {}
        if survey_type:
            filters["survey_type"] = survey_type.value
        if is_active is not None:
            filters["is_active"] = 1 if is_active else 0

        rows = self.db.list("satisfaction_surveys", filters, order_by="created_at DESC")
        return [SatisfactionSurvey.from_dict(row) for row in rows]

    def submit_response(self, survey_id: str,
                       responses: Dict[str, Any],
                       employee_id: Optional[str] = None,
                       overall_score: Optional[float] = None,
                       comments: Optional[str] = None,
                       completion_time_seconds: Optional[int] = None,
                       device_type: Optional[str] = None) -> SurveyResponse:
        """提交问卷回复"""
        survey = self.get_survey(survey_id)
        if not survey:
            raise ValueError(f"Survey {survey_id} not found")

        response = SurveyResponse(
            survey_id=survey_id,
            employee_id=employee_id,
            responses=responses,
            overall_score=overall_score,
            comments=comments,
            completion_time_seconds=completion_time_seconds,
            device_type=device_type,
        )
        self.db.insert("survey_responses", response.to_dict())

        # 更新脉冲调查的回复统计
        self._update_pulse_survey_stats(survey_id)

        return response

    def _update_pulse_survey_stats(self, survey_id: str):
        """更新脉冲调查统计"""
        conn = self.db._get_connection()
        cursor = conn.cursor()

        # 计算回复数和平均分
        cursor.execute("""
            SELECT COUNT(*) as count, AVG(overall_score) as avg_score
            FROM survey_responses
            WHERE survey_id = ?
        """, (survey_id,))
        row = cursor.fetchone()

        if row:
            cursor.execute("""
                UPDATE pulse_surveys
                SET response_count = ?, average_score = ?
                WHERE id = ?
            """, (row["count"], row["avg_score"], survey_id))
            conn.commit()

        

    def create_pulse_survey(self, title: str, question: str,
                           question_type: QuestionType = QuestionType.LIKERT_SCALE,
                           target_audience: str = "all",
                           expires_hours: int = 24) -> PulseSurvey:
        """创建脉冲调查"""
        survey = PulseSurvey(
            title=title,
            question=question,
            question_type=question_type,
            target_audience=target_audience,
            expires_at=datetime.now() + timedelta(hours=expires_hours),
        )
        self.db.insert("pulse_surveys", survey.to_dict())
        return survey

    def get_pulse_surveys(self, is_active: bool = True) -> List[PulseSurvey]:
        """获取脉冲调查"""
        filters = {"is_active": 1 if is_active else 0}
        rows = self.db.list("pulse_surveys", filters, order_by="created_at DESC")
        return [PulseSurvey.from_dict(row) for row in rows]

    def submit_pulse_response(self, survey_id: str, score: float,
                             employee_id: Optional[str] = None,
                             comments: Optional[str] = None) -> SurveyResponse:
        """提交脉冲调查回复"""
        return self.submit_response(
            survey_id=survey_id,
            responses={"score": score},
            employee_id=employee_id,
            overall_score=score,
            comments=comments,
        )

    def get_survey_statistics(self, survey_id: str) -> Dict[str, Any]:
        """获取问卷统计"""
        conn = self.db._get_connection()
        cursor = conn.cursor()

        # 总体统计
        cursor.execute("""
            SELECT COUNT(*) as total, AVG(overall_score) as avg_score,
                   MIN(overall_score) as min_score, MAX(overall_score) as max_score
            FROM survey_responses
            WHERE survey_id = ?
        """, (survey_id,))
        row = cursor.fetchone()

        stats = {
            "total_responses": row["total"] or 0,
            "average_score": round(row["avg_score"], 2) if row["avg_score"] else 0,
            "min_score": row["min_score"] or 0,
            "max_score": row["max_score"] or 0,
            "question_stats": {},
        }

        
        return stats

    def calculate_satisfaction_trend(self, period: str = "monthly",
                                    months: int = 6) -> List[SatisfactionTrend]:
        """计算满意度趋势"""
        trends = []
        end_date = date.today()

        for i in range(months):
            if period == "monthly":
                period_end = end_date - timedelta(days=i * 30)
                period_start = period_end - timedelta(days=30)
            else:
                period_end = end_date - timedelta(days=i * 7)
                period_start = period_end - timedelta(days=7)

            # 获取该期间的回复
            trend = self._calculate_period_trend(period, period_start, period_end)
            if trend:
                trends.append(trend)

        return trends

    def _calculate_period_trend(self, period: str,
                               period_start: date, period_end: date) -> Optional[SatisfactionTrend]:
        """计算单期趋势"""
        conn = self.db._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COUNT(*) as total, AVG(overall_score) as avg_score
            FROM survey_responses sr
            JOIN satisfaction_surveys ss ON sr.survey_id = ss.id
            WHERE DATE(sr.submitted_at) BETWEEN ? AND ?
        """, (period_start.isoformat(), period_end.isoformat()))
        row = cursor.fetchone()
        

        if not row or row["total"] == 0:
            return None

        return SatisfactionTrend(
            period=period,
            period_start=period_start,
            period_end=period_end,
            overall_score=round(row["avg_score"], 2) if row["avg_score"] else 0,
            total_responses=row["total"] or 0,
        )


# ============================================================================
# 离职风险预测服务
# ============================================================================

class TurnoverPredictionService:
    """离职风险预测服务"""

    # 预测因子权重
    WEIGHTS = {
        "work_hour_trend": 0.15,        # 工时变化趋势
        "satisfaction_score": 0.25,      # 满意度分数（反向）
        "performance_trend": 0.10,       # 绩效变化趋势
        "overtime_frequency": 0.15,      # 加班频率
        "leave_utilization": 0.10,       # 休假使用率（反向）
        "engagement_score": 0.15,        # 敬业度（反向）
        "career_growth": 0.10,           # 职业发展机会（反向）
    }

    def __init__(self, db: WellnessDB):
        self.db = db

    def predict_turnover_risk(self, employee_id: str,
                             work_hour_trend: float = 0.5,
                             satisfaction_score: float = 0.5,
                             performance_trend: float = 0.5,
                             overtime_frequency: float = 0.5,
                             leave_utilization: float = 0.5,
                             engagement_score: float = 0.5,
                             career_growth: float = 0.5) -> TurnoverRiskPrediction:
        """预测离职风险"""
        # 计算风险分数（0-1，越高风险越大）
        # 注意：satisfaction_score、leave_utilization、engagement_score、career_growth 是反向的（分数越高风险越低）
        risk_score = (
            work_hour_trend * self.WEIGHTS["work_hour_trend"] +
            (1 - satisfaction_score) * self.WEIGHTS["satisfaction_score"] +
            (1 - performance_trend) * self.WEIGHTS["performance_trend"] +
            overtime_frequency * self.WEIGHTS["overtime_frequency"] +
            (1 - leave_utilization) * self.WEIGHTS["leave_utilization"] +
            (1 - engagement_score) * self.WEIGHTS["engagement_score"] +
            (1 - career_growth) * self.WEIGHTS["career_growth"]
        )

        # 确定风险等级
        if risk_score >= 0.8:
            risk_level = RiskLevel.CRITICAL
        elif risk_score >= 0.6:
            risk_level = RiskLevel.HIGH
        elif risk_score >= 0.4:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW

        # 分析贡献因素
        prediction_factors = {
            "work_hour_trend": work_hour_trend,
            "satisfaction_score": satisfaction_score,
            "performance_trend": performance_trend,
            "overtime_frequency": overtime_frequency,
            "leave_utilization": leave_utilization,
            "engagement_score": engagement_score,
            "career_growth": career_growth,
        }

        contributing_factors = self._identify_contributing_factors(prediction_factors)
        protective_factors = self._identify_protective_factors(prediction_factors)
        recommended_actions = self._generate_recommendations(risk_level, contributing_factors)

        prediction = TurnoverRiskPrediction(
            employee_id=employee_id,
            risk_score=round(risk_score, 4),
            risk_level=risk_level,
            prediction_factors=prediction_factors,
            contributing_factors=contributing_factors,
            protective_factors=protective_factors,
            recommended_actions=recommended_actions,
            model_version="v1.0",
            confidence_score=0.85,  # 模型置信度
            expires_at=datetime.now() + timedelta(days=30),
        )

        self.db.insert("turnover_risk_predictions", prediction.to_dict())

        # 如果是高风险，创建预警
        if risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            self._create_turnover_alert(employee_id, risk_level, risk_score)

        return prediction

    def _identify_contributing_factors(self, factors: Dict[str, float]) -> List[str]:
        """识别风险贡献因素"""
        contributing = []

        if factors.get("work_hour_trend", 0.5) > 0.7:
            contributing.append("工时呈增长趋势")
        if factors.get("satisfaction_score", 0.5) < 0.3:
            contributing.append("满意度较低")
        if factors.get("performance_trend", 0.5) < 0.3:
            contributing.append("绩效呈下降趋势")
        if factors.get("overtime_frequency", 0.5) > 0.7:
            contributing.append("加班频繁")
        if factors.get("leave_utilization", 0.5) < 0.3:
            contributing.append("假期使用率低")
        if factors.get("engagement_score", 0.5) < 0.3:
            contributing.append("敬业度较低")
        if factors.get("career_growth", 0.5) < 0.3:
            contributing.append("职业发展机会有限")

        return contributing

    def _identify_protective_factors(self, factors: Dict[str, float]) -> List[str]:
        """识别保护因素"""
        protective = []

        if factors.get("work_hour_trend", 0.5) < 0.3:
            protective.append("工时稳定或下降")
        if factors.get("satisfaction_score", 0.5) > 0.7:
            protective.append("满意度较高")
        if factors.get("performance_trend", 0.5) > 0.7:
            protective.append("绩效稳定或提升")
        if factors.get("overtime_frequency", 0.5) < 0.3:
            protective.append("加班较少")
        if factors.get("leave_utilization", 0.5) > 0.7:
            protective.append("假期使用正常")
        if factors.get("engagement_score", 0.5) > 0.7:
            protective.append("敬业度高")
        if factors.get("career_growth", 0.5) > 0.7:
            protective.append("职业发展机会良好")

        return protective

    def _generate_recommendations(self, risk_level: RiskLevel,
                                 contributing_factors: List[str]) -> List[str]:
        """生成推荐行动"""
        recommendations = []

        if risk_level == RiskLevel.CRITICAL:
            recommendations.append("立即安排一对一沟通，了解员工需求")
            recommendations.append("考虑紧急干预措施，如工作调整或薪资调整")

        if "工时呈增长趋势" in contributing_factors:
            recommendations.append("审查工作量分配，考虑减少任务或增加支持")
        if "满意度较低" in contributing_factors:
            recommendations.append("进行满意度调查，识别具体问题")
        if "加班频繁" in contributing_factors:
            recommendations.append("制定加班限制计划，确保工作生活平衡")
        if "职业发展机会有限" in contributing_factors:
            recommendations.append("讨论职业发展路径，提供成长机会")
        if "敬业度较低" in contributing_factors:
            recommendations.append("增强团队活动，提升归属感")

        if not recommendations:
            recommendations.append("继续保持良好状态，定期进行关怀沟通")

        return recommendations

    def _create_turnover_alert(self, employee_id: str,
                              risk_level: RiskLevel, risk_score: float):
        """创建离职风险预警"""
        severity = AlertSeverity.CRITICAL if risk_level == RiskLevel.CRITICAL else AlertSeverity.WARNING
        alert = WellnessAlert(
            employee_id=employee_id,
            alert_type=AlertType.HIGH_TURNOVER_RISK,
            severity=severity,
            title="高离职风险预警",
            description=f"员工离职风险评分为 {risk_score:.2f}，建议及时干预",
            trigger_value=risk_score,
            threshold_value=0.6,
        )
        self.db.insert("wellness_alerts", alert.to_dict())

    def get_prediction(self, employee_id: str) -> Optional[TurnoverRiskPrediction]:
        """获取最新的离职风险预测"""
        rows = self.db.list("turnover_risk_predictions",
                           {"employee_id": employee_id},
                           order_by="prediction_date DESC",
                           limit=1)
        if rows:
            return TurnoverRiskPrediction.from_dict(rows[0])
        return None

    def list_high_risk_employees(self, min_risk_level: RiskLevel = RiskLevel.MEDIUM) -> List[Dict[str, Any]]:
        """列出高风险员工"""
        conn = self.db._get_connection()
        cursor = conn.cursor()

        risk_levels = []
        if min_risk_level == RiskLevel.LOW:
            risk_levels = ["low", "medium", "high", "critical"]
        elif min_risk_level == RiskLevel.MEDIUM:
            risk_levels = ["medium", "high", "critical"]
        elif min_risk_level == RiskLevel.HIGH:
            risk_levels = ["high", "critical"]
        else:
            risk_levels = ["critical"]

        placeholders = ",".join("?" * len(risk_levels))
        cursor.execute(f"""
            SELECT * FROM turnover_risk_predictions
            WHERE risk_level IN ({placeholders})
            ORDER BY risk_score DESC
        """, risk_levels)

        rows = cursor.fetchall()
        

        return [TurnoverRiskPrediction.from_dict(dict(row)).to_dict() for row in rows]

    def create_intervention(self, employee_id: str, intervention_type: InterventionType,
                           description: str, priority: str = "medium",
                           proposed_by: Optional[str] = None,
                           assigned_to: Optional[str] = None,
                           expected_impact: Optional[str] = None,
                           cost_estimate: Optional[float] = None) -> RetentionIntervention:
        """创建留任干预措施"""
        intervention = RetentionIntervention(
            employee_id=employee_id,
            intervention_type=intervention_type,
            description=description,
            priority=priority,
            proposed_by=proposed_by,
            assigned_to=assigned_to,
            expected_impact=expected_impact,
            cost_estimate=cost_estimate,
        )
        self.db.insert("retention_interventions", intervention.to_dict())
        return intervention

    def update_intervention_status(self, intervention_id: str,
                                  status: InterventionStatus,
                                  notes: Optional[str] = None) -> RetentionIntervention:
        """更新干预措施状态"""
        intervention = self.get_intervention(intervention_id)
        if not intervention:
            raise ValueError(f"Intervention {intervention_id} not found")

        intervention.status = status
        intervention.updated_at = datetime.now()
        if notes:
            intervention.notes = notes

        self.db.update("retention_interventions", intervention_id, intervention.to_dict())
        return intervention

    def complete_intervention(self, intervention_id: str,
                             actual_impact: Optional[str] = None) -> RetentionIntervention:
        """完成干预措施"""
        return self.update_intervention_status(
            intervention_id,
            InterventionStatus.COMPLETED,
            f"已完成。实际影响：{actual_impact}" if actual_impact else None
        )

    def get_intervention(self, intervention_id: str) -> Optional[RetentionIntervention]:
        """获取干预措施"""
        data = self.db.get("retention_interventions", intervention_id)
        return RetentionIntervention.from_dict(data) if data else None

    def list_interventions(self, employee_id: Optional[str] = None,
                          status: Optional[InterventionStatus] = None) -> List[RetentionIntervention]:
        """列出干预措施"""
        filters = {}
        if employee_id:
            filters["employee_id"] = employee_id
        if status:
            filters["status"] = status.value

        rows = self.db.list("retention_interventions", filters, order_by="created_at DESC")
        return [RetentionIntervention.from_dict(row) for row in rows]


# ============================================================================
# 敬业度服务
# ============================================================================

class EngagementService:
    """敬业度服务"""

    def __init__(self, db: WellnessDB):
        self.db = db

    def calculate_engagement_score(self, employee_id: str,
                                   dimension_scores: Dict[str, float],
                                   behavioral_indicators: Dict[str, float],
                                   survey_score: Optional[float] = None,
                                   manager_assessment: Optional[float] = None,
                                   peer_assessment: Optional[float] = None) -> EngagementScore:
        """计算敬业度分数"""
        # 综合计算总体分数
        scores = []

        # 维度分数（40%）
        if dimension_scores:
            dim_avg = sum(dimension_scores.values()) / len(dimension_scores)
            scores.append(dim_avg * 0.4)

        # 行为指标（30%）
        if behavioral_indicators:
            beh_avg = sum(behavioral_indicators.values()) / len(behavioral_indicators)
            scores.append(beh_avg * 0.3)

        # 调查分数（15%）
        if survey_score:
            scores.append(survey_score * 0.15)

        # 管理者评估（10%）
        if manager_assessment:
            scores.append(manager_assessment * 0.10)

        # 同事评估（5%）
        if peer_assessment:
            scores.append(peer_assessment * 0.05)

        overall_score = sum(scores) if scores else 50

        # 确定趋势
        trend = self._determine_engagement_trend(employee_id, overall_score)

        engagement = EngagementScore(
            employee_id=employee_id,
            overall_score=round(overall_score, 2),
            dimension_scores=dimension_scores,
            behavioral_indicators=behavioral_indicators,
            survey_score=survey_score,
            manager_assessment=manager_assessment,
            peer_assessment=peer_assessment,
            trend=trend,
        )

        self.db.insert("engagement_scores", engagement.to_dict())
        return engagement

    def _determine_engagement_trend(self, employee_id: str,
                                   current_score: float) -> str:
        """确定敬业度趋势"""
        # 获取历史分数
        rows = self.db.list("engagement_scores",
                           {"employee_id": employee_id},
                           order_by="calculated_at DESC",
                           limit=3)

        if len(rows) < 2:
            return "stable"

        historical = [EngagementScore.from_dict(row).overall_score for row in rows]
        recent_avg = sum(historical[:2]) / 2

        if current_score > recent_avg + 5:
            return "improving"
        elif current_score < recent_avg - 5:
            return "declining"
        else:
            return "stable"

    def get_engagement_score(self, employee_id: str) -> Optional[EngagementScore]:
        """获取最新的敬业度分数"""
        rows = self.db.list("engagement_scores",
                           {"employee_id": employee_id},
                           order_by="calculated_at DESC",
                           limit=1)
        if rows:
            return EngagementScore.from_dict(rows[0])
        return None

    def get_engagement_history(self, employee_id: str,
                              months: int = 6) -> List[EngagementScore]:
        """获取敬业度历史"""
        cutoff = datetime.now() - timedelta(days=months * 30)
        rows = self.db.list("engagement_scores",
                           {"employee_id": employee_id},
                           order_by="calculated_at DESC")
        scores = [EngagementScore.from_dict(row) for row in rows]
        return [s for s in scores if s.calculated_at >= cutoff]


# ============================================================================
# 统一外观服务
# ============================================================================

class WellnessService:
    """员工福祉统一外观服务"""

    def __init__(self, db_path: str = ":memory:"):
        self.db = WellnessDB(db_path)
        self.mental_health = MentalHealthService(self.db)
        self.work_life_balance = WorkLifeBalanceService(self.db)
        self.benefits = BenefitsService(self.db)
        self.survey = SurveyService(self.db)
        self.turnover_prediction = TurnoverPredictionService(self.db)
        self.engagement = EngagementService(self.db)

    def get_wellness_dashboard(self, employee_id: str) -> Dict[str, Any]:
        """获取员工福祉仪表盘"""
        return {
            "mental_health": {
                "latest_assessment": self._get_latest_assessment_summary(employee_id),
                "stress_level": self._get_latest_stress(employee_id),
            },
            "work_life_balance": {
                "balance_score": self._get_latest_balance_score(employee_id),
                "overtime_hours": self._get_overtime_summary(employee_id),
                "leave_balance": self._get_leave_balance_summary(employee_id),
            },
            "engagement": {
                "overall_score": self._get_engagement_summary(employee_id),
            },
            "turnover_risk": {
                "risk_level": self._get_turnover_risk_summary(employee_id),
            },
            "alerts": self._get_active_alerts(employee_id),
        }

    def _get_latest_assessment_summary(self, employee_id: str) -> Optional[Dict[str, Any]]:
        assessments = self.mental_health.list_assessments(employee_id, limit=1)
        if assessments:
            a = assessments[0]
            return {
                "id": a.id,
                "type": a.assessment_type.value,
                "score": a.overall_score,
                "date": a.created_at.isoformat(),
            }
        return None

    def _get_latest_stress(self, employee_id: str) -> Optional[Dict[str, Any]]:
        stresses = self.mental_health.get_stress_history(employee_id, days=7)
        if stresses:
            s = stresses[0]
            return {
                "score": s.stress_score,
                "emotional_state": s.emotional_state,
                "date": s.recorded_at.isoformat(),
            }
        return None

    def _get_latest_balance_score(self, employee_id: str) -> Optional[Dict[str, Any]]:
        metrics = self.work_life_balance.get_balance_history(employee_id, months=1)
        if metrics:
            m = metrics[0]
            return {
                "score": m.balance_score,
                "risk_level": m.risk_level.value,
                "recommendations": m.recommendations[:3],
            }
        return None

    def _get_overtime_summary(self, employee_id: str) -> Dict[str, Any]:
        records = self.work_life_balance.list_overtime_records(employee_id)
        total_hours = sum(r.overtime_hours for r in records)
        return {
            "total_hours": round(total_hours, 2),
            "count": len(records),
        }

    def _get_leave_balance_summary(self, employee_id: str) -> List[Dict[str, Any]]:
        balances = self.benefits.get_all_leave_balances(employee_id)
        return [{
            "type": b.leave_type.value,
            "remaining_days": b.remaining_days,
            "total_days": b.total_days,
        } for b in balances]

    def _get_engagement_summary(self, employee_id: str) -> Optional[Dict[str, Any]]:
        engagement = self.engagement.get_engagement_score(employee_id)
        if engagement:
            return {
                "score": engagement.overall_score,
                "trend": engagement.trend,
            }
        return None

    def _get_turnover_risk_summary(self, employee_id: str) -> Optional[Dict[str, Any]]:
        prediction = self.turnover_prediction.get_prediction(employee_id)
        if prediction:
            return {
                "risk_level": prediction.risk_level.value,
                "risk_score": prediction.risk_score,
            }
        return None

    def _get_active_alerts(self, employee_id: str) -> List[Dict[str, Any]]:
        rows = self.db.list("wellness_alerts",
                           {"employee_id": employee_id, "is_resolved": 0},
                           order_by="triggered_at DESC",
                           limit=10)
        return [{
            "id": a["id"],
            "type": a["alert_type"],
            "severity": a["severity"],
            "title": a["title"],
            "triggered_at": a["triggered_at"],
        } for a in rows]


# ============================================================================
# 服务工厂
# ============================================================================

def create_wellness_services(db_path: str = ":memory:") -> WellnessService:
    """创建福祉服务实例"""
    return WellnessService(db_path)
