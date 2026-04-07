# -*- coding: utf-8 -*-
"""
v14.0.0 绩效评估增强 - 服务层

绩效评估核心业务逻辑：
- 360 度评估反馈管理
- OKR 目标管理
- 绩效指标计算
- 1 对 1 会议管理
- 晋升推荐生成

作者：AI Employee Platform Team
创建日期：2026-04-05
版本：v14.0.0
"""

import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc

from models.p14_models import (
    ReviewCycle, ReviewDimension, PerformanceReview, ReviewType, ReviewStatus, ReviewCycleStatus,
    Objective, KeyResult, ObjectiveStatus, MetricType,
    PerformanceMetrics, ActionItemStatus,
    OneOnOneMeeting, ActionItem,
    PromotionRecommendation, PromotionHistory, PromotionStatus,
    PerformanceBenchmark,
)

logger = logging.getLogger(__name__)


# ==================== 360 度评估服务 ====================

class ReviewCycleService:
    """评估周期服务"""

    def __init__(self, db: Session):
        self.db = db

    def create_cycle(
        self,
        name: str,
        start_date: datetime,
        end_date: datetime,
        description: str = None,
        review_type: ReviewType = ReviewType._360,
        target_employee_ids: List[str] = None,
        created_by: str = None,
    ) -> ReviewCycle:
        """创建评估周期"""
        cycle = ReviewCycle(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            start_date=start_date,
            end_date=end_date,
            review_type=review_type,
            target_employee_ids=target_employee_ids,
            status=ReviewCycleStatus.PLANNED,
            created_by=created_by,
        )
        self.db.add(cycle)
        self.db.commit()
        self.db.refresh(cycle)
        logger.info(f"Created review cycle: {cycle.id}, name: {name}")
        return cycle

    def get_cycle(self, cycle_id: str) -> Optional[ReviewCycle]:
        """获取评估周期详情"""
        return self.db.query(ReviewCycle).filter(ReviewCycle.id == cycle_id).first()

    def list_cycles(
        self,
        status: ReviewCycleStatus = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[ReviewCycle]:
        """获取评估周期列表"""
        query = self.db.query(ReviewCycle)
        if status:
            query = query.filter(ReviewCycle.status == status)
        return query.order_by(desc(ReviewCycle.created_at)).limit(limit).offset(offset).all()

    def launch_cycle(self, cycle_id: str) -> ReviewCycle:
        """启动评估周期"""
        cycle = self.get_cycle(cycle_id)
        if not cycle:
            raise ValueError(f"Review cycle not found: {cycle_id}")
        if cycle.status != ReviewCycleStatus.PLANNED:
            raise ValueError(f"Cycle cannot be launched from status: {cycle.status}")

        cycle.status = ReviewCycleStatus.ACTIVE
        self.db.commit()
        self.db.refresh(cycle)
        logger.info(f"Launched review cycle: {cycle_id}")
        return cycle

    def complete_cycle(self, cycle_id: str) -> ReviewCycle:
        """完成评估周期"""
        cycle = self.get_cycle(cycle_id)
        if not cycle:
            raise ValueError(f"Review cycle not found: {cycle_id}")

        cycle.status = ReviewCycleStatus.COMPLETED
        self.db.commit()
        self.db.refresh(cycle)
        logger.info(f"Completed review cycle: {cycle_id}")
        return cycle

    def get_cycle_progress(self, cycle_id: str) -> Dict[str, Any]:
        """获取周期进度"""
        cycle = self.get_cycle(cycle_id)
        if not cycle:
            raise ValueError(f"Review cycle not found: {cycle_id}")
        return cycle.calculate_progress()


class PerformanceReviewService:
    """绩效评估服务"""

    def __init__(self, db: Session):
        self.db = db

    def create_review(
        self,
        employee_id: str,
        reviewer_id: str,
        review_type: ReviewType = ReviewType.MANAGER,
        cycle_id: str = None,
        due_date: datetime = None,
    ) -> PerformanceReview:
        """创建绩效评估"""
        review = PerformanceReview(
            id=str(uuid.uuid4()),
            employee_id=employee_id,
            reviewer_id=reviewer_id,
            review_type=review_type,
            cycle_id=cycle_id,
            status=ReviewStatus.DRAFT,
            due_date=due_date,
        )
        self.db.add(review)
        self.db.commit()
        self.db.refresh(review)
        logger.info(f"Created performance review: {review.id} for employee: {employee_id}")
        return review

    def get_review(self, review_id: str) -> Optional[PerformanceReview]:
        """获取评估详情"""
        return self.db.query(PerformanceReview).filter(PerformanceReview.id == review_id).first()

    def get_employee_reviews(
        self,
        employee_id: str,
        status: ReviewStatus = None,
        limit: int = 20,
    ) -> List[PerformanceReview]:
        """获取员工的评估列表"""
        query = self.db.query(PerformanceReview).filter(PerformanceReview.employee_id == employee_id)
        if status:
            query = query.filter(PerformanceReview.status == status)
        return query.order_by(desc(PerformanceReview.created_at)).limit(limit).all()

    def update_review(
        self,
        review_id: str,
        scores: Dict[str, float] = None,
        comments: str = None,
        strengths: List[str] = None,
        areas_for_improvement: List[str] = None,
        goals: List[str] = None,
    ) -> PerformanceReview:
        """更新评估内容"""
        review = self.get_review(review_id)
        if not review:
            raise ValueError(f"Performance review not found: {review_id}")

        if scores is not None:
            review.scores = scores
            review.overall_score = self._calculate_overall_score(scores)
        if comments is not None:
            review.comments = comments
        if strengths is not None:
            review.strengths = strengths
        if areas_for_improvement is not None:
            review.areas_for_improvement = areas_for_improvement
        if goals is not None:
            review.goals = goals

        review.status = ReviewStatus.IN_PROGRESS
        if not review.started_at:
            review.started_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(review)
        logger.info(f"Updated performance review: {review_id}")
        return review

    def submit_review(self, review_id: str) -> PerformanceReview:
        """提交评估"""
        review = self.get_review(review_id)
        if not review:
            raise ValueError(f"Performance review not found: {review_id}")
        if review.status == ReviewStatus.COMPLETED:
            raise ValueError(f"Review already completed: {review_id}")

        review.status = ReviewStatus.SUBMITTED
        review.submitted_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(review)
        logger.info(f"Submitted performance review: {review_id}")
        return review

    def complete_review(self, review_id: str) -> PerformanceReview:
        """完成评估"""
        review = self.get_review(review_id)
        if not review:
            raise ValueError(f"Performance review not found: {review_id}")

        review.status = ReviewStatus.COMPLETED
        review.completed_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(review)
        logger.info(f"Completed performance review: {review_id}")
        return review

    def _calculate_overall_score(self, scores: Dict[str, float]) -> float:
        """计算综合分数"""
        if not scores:
            return 0.0
        return round(sum(scores.values()) / len(scores), 2)

    def get_review_statistics(self, cycle_id: str = None) -> Dict[str, Any]:
        """获取评估统计"""
        query = self.db.query(PerformanceReview)
        if cycle_id:
            query = query.filter(PerformanceReview.cycle_id == cycle_id)

        reviews = query.all()
        if not reviews:
            return {
                "total": 0,
                "by_status": {},
                "by_type": {},
                "avg_score": 0,
            }

        by_status = {}
        by_type = {}
        scores = []

        for review in reviews:
            by_status[review.status.value] = by_status.get(review.status.value, 0) + 1
            by_type[review.review_type.value] = by_type.get(review.review_type.value, 0) + 1
            if review.overall_score:
                scores.append(review.overall_score)

        return {
            "total": len(reviews),
            "by_status": by_status,
            "by_type": by_type,
            "avg_score": round(sum(scores) / len(scores), 2) if scores else 0,
        }


class ReviewDimensionService:
    """评估维度服务"""

    def __init__(self, db: Session):
        self.db = db

    def create_dimension(
        self,
        name: str,
        weight: float = 1.0,
        max_score: float = 5.0,
        description: str = None,
        cycle_id: str = None,
        dimension_type: str = "custom",
    ) -> ReviewDimension:
        """创建评估维度"""
        dimension = ReviewDimension(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            weight=weight,
            max_score=max_score,
            cycle_id=cycle_id,
            dimension_type=dimension_type,
        )
        self.db.add(dimension)
        self.db.commit()
        self.db.refresh(dimension)
        logger.info(f"Created review dimension: {dimension.id}, name: {name}")
        return dimension

    def get_dimension(self, dimension_id: str) -> Optional[ReviewDimension]:
        """获取评估维度"""
        return self.db.query(ReviewDimension).filter(ReviewDimension.id == dimension_id).first()

    def list_dimensions(self, cycle_id: str = None) -> List[ReviewDimension]:
        """获取维度列表"""
        query = self.db.query(ReviewDimension)
        if cycle_id:
            query = query.filter(ReviewDimension.cycle_id == cycle_id)
        return query.all()


# ==================== OKR 目标管理服务 ====================

class ObjectiveService:
    """OKR 目标服务"""

    def __init__(self, db: Session):
        self.db = db

    def create_objective(
        self,
        title: str,
        start_date: datetime,
        due_date: datetime,
        description: str = None,
        employee_id: str = None,
        department_id: str = None,
        company_id: str = None,
        parent_objective_id: str = None,
        created_by: str = None,
    ) -> Objective:
        """创建目标"""
        objective = Objective(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            start_date=start_date,
            due_date=due_date,
            employee_id=employee_id,
            department_id=department_id,
            company_id=company_id,
            parent_objective_id=parent_objective_id,
            created_by=created_by,
        )
        self.db.add(objective)
        self.db.commit()
        self.db.refresh(objective)
        logger.info(f"Created objective: {objective.id}, title: {title}")
        return objective

    def get_objective(self, objective_id: str) -> Optional[Objective]:
        """获取目标详情"""
        return self.db.query(Objective).filter(Objective.id == objective_id).first()

    def get_employee_objectives(
        self,
        employee_id: str,
        status: ObjectiveStatus = None,
        include_children: bool = False,
    ) -> List[Objective]:
        """获取员工的目标列表"""
        query = self.db.query(Objective).filter(Objective.employee_id == employee_id)
        if status:
            query = query.filter(Objective.status == status)
        objectives = query.all()

        if include_children:
            result = []
            for obj in objectives:
                result.append(obj)
                result.extend(obj.children)
            return result
        return objectives

    def update_objective(
        self,
        objective_id: str,
        title: str = None,
        description: str = None,
        progress: float = None,
        status: ObjectiveStatus = None,
        confidence_level: int = None,
    ) -> Objective:
        """更新目标"""
        objective = self.get_objective(objective_id)
        if not objective:
            raise ValueError(f"Objective not found: {objective_id}")

        if title is not None:
            objective.title = title
        if description is not None:
            objective.description = description
        if progress is not None:
            objective.progress = min(100.0, max(0.0, progress))
        if status is not None:
            objective.status = status
        if confidence_level is not None:
            objective.confidence_level = min(10, max(1, confidence_level))

        self.db.commit()
        self.db.refresh(objective)
        logger.info(f"Updated objective: {objective_id}")
        return objective

    def update_objective_progress(self, objective_id: str) -> Objective:
        """根据关键结果自动更新目标进度"""
        objective = self.get_objective(objective_id)
        if not objective:
            raise ValueError(f"Objective not found: {objective_id}")

        key_results = objective.key_results
        if not key_results:
            objective.progress = 0.0
        else:
            # 平均计算所有 KR 的进度
            total_progress = sum(kr.calculate_progress() for kr in key_results)
            objective.progress = round(total_progress / len(key_results), 2)

            # 自动更新状态
            if objective.progress >= 100:
                objective.status = ObjectiveStatus.COMPLETED
            elif objective.progress < 30:
                objective.status = ObjectiveStatus.OFF_TRACK
            elif objective.progress < 70:
                objective.status = ObjectiveStatus.AT_RISK
            else:
                objective.status = ObjectiveStatus.ON_TRACK

        self.db.commit()
        self.db.refresh(objective)
        return objective

    def delete_objective(self, objective_id: str) -> bool:
        """删除目标"""
        objective = self.get_objective(objective_id)
        if not objective:
            raise ValueError(f"Objective not found: {objective_id}")

        self.db.delete(objective)
        self.db.commit()
        logger.info(f"Deleted objective: {objective_id}")
        return True

    def get_objective_tree(self, root_id: str = None) -> List[Dict[str, Any]]:
        """获取目标树形结构"""
        if root_id:
            root = self.get_objective(root_id)
            if not root:
                raise ValueError(f"Objective not found: {root_id}")
            return [self._build_objective_tree(root)]
        else:
            # 获取所有顶级目标
            roots = self.db.query(Objective).filter(Objective.parent_objective_id.is_(None)).all()
            return [self._build_objective_tree(root) for root in roots]

    def _build_objective_tree(self, objective: Objective) -> Dict[str, Any]:
        """构建目标树形数据结构"""
        return {
            "id": objective.id,
            "title": objective.title,
            "progress": objective.progress,
            "status": objective.status.value,
            "children": [self._build_objective_tree(child) for child in objective.children],
        }


class KeyResultService:
    """关键结果服务"""

    def __init__(self, db: Session):
        self.db = db

    def create_key_result(
        self,
        objective_id: str,
        title: str,
        target_value: float,
        metric_type: MetricType = MetricType.NUMBER,
        description: str = None,
        start_value: float = 0.0,
        unit: str = None,
        stretch_target: float = None,
    ) -> KeyResult:
        """创建关键结果"""
        objective = self.db.query(Objective).filter(Objective.id == objective_id).first()
        if not objective:
            raise ValueError(f"Objective not found: {objective_id}")

        key_result = KeyResult(
            id=str(uuid.uuid4()),
            objective_id=objective_id,
            title=title,
            description=description,
            metric_type=metric_type,
            start_value=start_value,
            target_value=target_value,
            current_value=start_value,
            unit=unit,
            stretch_target=stretch_target,
            progress=0.0,
        )
        self.db.add(key_result)
        self.db.commit()
        self.db.refresh(key_result)

        # 更新目标进度
        obj_service = ObjectiveService(self.db)
        obj_service.update_objective_progress(objective_id)

        logger.info(f"Created key result: {key_result.id} for objective: {objective_id}")
        return key_result

    def get_key_result(self, kr_id: str) -> Optional[KeyResult]:
        """获取关键结果"""
        return self.db.query(KeyResult).filter(KeyResult.id == kr_id).first()

    def update_key_result_progress(
        self,
        kr_id: str,
        current_value: float,
        add_checkpoint: bool = True,
    ) -> KeyResult:
        """更新关键结果进度"""
        kr = self.get_key_result(kr_id)
        if not kr:
            raise ValueError(f"Key result not found: {kr_id}")

        kr.current_value = current_value
        kr.progress = kr.calculate_progress()

        # 添加检查点
        if add_checkpoint:
            if kr.checkpoints is None:
                kr.checkpoints = []
            kr.checkpoints.append({
                "date": datetime.utcnow().isoformat(),
                "value": current_value,
            })

        self.db.commit()
        self.db.refresh(kr)

        # 更新目标进度
        obj_service = ObjectiveService(self.db)
        obj_service.update_objective_progress(kr.objective_id)

        logger.info(f"Updated key result {kr_id} progress: {kr.progress}%")
        return kr

    def delete_key_result(self, kr_id: str) -> bool:
        """删除关键结果"""
        kr = self.get_key_result(kr_id)
        if not kr:
            raise ValueError(f"Key result not found: {kr_id}")

        objective_id = kr.objective_id
        self.db.delete(kr)
        self.db.commit()

        # 更新目标进度
        obj_service = ObjectiveService(self.db)
        obj_service.update_objective_progress(objective_id)

        logger.info(f"Deleted key result: {kr_id}")
        return True


# ==================== 绩效指标服务 ====================

class PerformanceMetricsService:
    """绩效指标服务"""

    def __init__(self, db: Session):
        self.db = db

    def create_metrics(
        self,
        employee_id: str,
        period_start: datetime,
        period_end: datetime,
        efficiency_metrics: Dict[str, Any] = None,
        quality_metrics: Dict[str, Any] = None,
        contribution_metrics: Dict[str, Any] = None,
        growth_metrics: Dict[str, Any] = None,
    ) -> PerformanceMetrics:
        """创建绩效指标快照"""
        metrics = PerformanceMetrics(
            id=str(uuid.uuid4()),
            employee_id=employee_id,
            period_start=period_start,
            period_end=period_end,
            **self._flatten_metrics(
                efficiency_metrics,
                quality_metrics,
                contribution_metrics,
                growth_metrics,
            ),
        )
        metrics.overall_performance_score = self._calculate_overall_score(metrics)

        self.db.add(metrics)
        self.db.commit()
        self.db.refresh(metrics)
        logger.info(f"Created performance metrics for employee: {employee_id}")
        return metrics

    def _flatten_metrics(
        self,
        efficiency: Dict,
        quality: Dict,
        contribution: Dict,
        growth: Dict,
    ) -> Dict[str, Any]:
        """扁平化指标数据"""
        result = {}
        if efficiency:
            result.update({
                "avg_response_time": efficiency.get("avg_response_time"),
                "task_completion_rate": efficiency.get("task_completion_rate"),
                "on_time_delivery_rate": efficiency.get("on_time_delivery_rate"),
                "tasks_completed": efficiency.get("tasks_completed", 0),
            })
        if quality:
            result.update({
                "error_rate": quality.get("error_rate"),
                "customer_satisfaction": quality.get("customer_satisfaction"),
                "rework_rate": quality.get("rework_rate"),
            })
        if contribution:
            result.update({
                "revenue_generated": contribution.get("revenue_generated", 0.0),
                "cost_saved": contribution.get("cost_saved", 0.0),
                "hours_saved": contribution.get("hours_saved", 0.0),
            })
        if growth:
            result.update({
                "skills_improved": growth.get("skills_improved"),
                "certifications_earned": growth.get("certifications_earned", 0),
                "training_hours": growth.get("training_hours", 0.0),
            })
        return result

    def _calculate_overall_score(self, metrics: PerformanceMetrics) -> float:
        """计算综合绩效分数"""
        scores = []

        # 效率分数 (25%)
        if metrics.task_completion_rate:
            scores.append(metrics.task_completion_rate * 0.25)
        if metrics.on_time_delivery_rate:
            scores.append(metrics.on_time_delivery_rate * 0.25)

        # 质量分数 (35%)
        if metrics.customer_satisfaction:
            scores.append(metrics.customer_satisfaction * 20)  # 5 分制转百分比
        if metrics.error_rate:
            scores.append((100 - metrics.error_rate) * 0.15)

        # 贡献分数 (25%)
        if metrics.revenue_generated:
            scores.append(min(25, metrics.revenue_generated / 100))  # 上限 25 分

        # 成长分数 (15%)
        if metrics.certifications_earned:
            scores.append(min(10, metrics.certifications_earned * 2))
        if metrics.training_hours:
            scores.append(min(5, metrics.training_hours))

        return round(sum(scores), 2) if scores else 0.0

    def get_employee_metrics(
        self,
        employee_id: str,
        limit: int = 10,
    ) -> List[PerformanceMetrics]:
        """获取员工的绩效指标历史"""
        return (
            self.db.query(PerformanceMetrics)
            .filter(PerformanceMetrics.employee_id == employee_id)
            .order_by(desc(PerformanceMetrics.period_end))
            .limit(limit)
            .all()
        )

    def get_metrics_trend(
        self,
        employee_id: str,
        metric_name: str,
        periods: int = 6,
    ) -> List[Dict[str, Any]]:
        """获取指标趋势"""
        metrics = self.get_employee_metrics(employee_id, limit=periods)
        return [
            {
                "period_end": m.period_end.isoformat() if m.period_end else None,
                "value": getattr(m, metric_name, None),
            }
            for m in reversed(metrics)
        ]

    def get_dashboard(self, employee_ids: List[str] = None) -> Dict[str, Any]:
        """获取综合仪表盘数据"""
        query = self.db.query(PerformanceMetrics)
        if employee_ids:
            query = query.filter(PerformanceMetrics.employee_id.in_(employee_ids))

        metrics = query.all()
        if not metrics:
            return self._empty_dashboard()

        # 计算聚合数据
        total_employees = len(set(m.employee_id for m in metrics))
        latest_metrics = self._get_latest_per_employee(metrics)

        return {
            "summary": {
                "total_employees": total_employees,
                "avg_performance_score": self._avg(latest_metrics, "overall_performance_score"),
                "avg_task_completion_rate": self._avg(latest_metrics, "task_completion_rate"),
                "avg_customer_satisfaction": self._avg(latest_metrics, "customer_satisfaction"),
                "total_revenue_generated": sum(m.revenue_generated or 0 for m in latest_metrics),
            },
            "top_performers": self._get_top_performers(latest_metrics),
            "needs_attention": self._get_needs_attention(latest_metrics),
        }

    def _get_latest_per_employee(self, metrics: List[PerformanceMetrics]) -> List[PerformanceMetrics]:
        """获取每个员工的最新指标"""
        latest = {}
        for m in metrics:
            if m.employee_id not in latest or m.period_end > latest[m.employee_id].period_end:
                latest[m.employee_id] = m
        return list(latest.values())

    def _avg(self, metrics: List[PerformanceMetrics], attr: str) -> float:
        """计算平均值"""
        values = [getattr(m, attr) for m in metrics if getattr(m, attr) is not None]
        return round(sum(values) / len(values), 2) if values else 0.0

    def _get_top_performers(self, metrics: List[PerformanceMetrics], limit: int = 5) -> List[Dict]:
        """获取表现最好的员工"""
        sorted_metrics = sorted(metrics, key=lambda m: m.overall_performance_score or 0, reverse=True)
        return [
            {"employee_id": m.employee_id, "score": m.overall_performance_score}
            for m in sorted_metrics[:limit]
        ]

    def _get_needs_attention(self, metrics: List[PerformanceMetrics], limit: int = 5) -> List[Dict]:
        """获取需要关注的员工"""
        sorted_metrics = sorted(metrics, key=lambda m: m.overall_performance_score or 0)
        return [
            {"employee_id": m.employee_id, "score": m.overall_performance_score}
            for m in sorted_metrics[:limit]
        ]

    def _empty_dashboard(self) -> Dict[str, Any]:
        """返回空仪表盘"""
        return {
            "summary": {
                "total_employees": 0,
                "avg_performance_score": 0,
                "avg_task_completion_rate": 0,
                "avg_customer_satisfaction": 0,
                "total_revenue_generated": 0,
            },
            "top_performers": [],
            "needs_attention": [],
        }


# ==================== 1 对 1 会议服务 ====================

class OneOnOneMeetingService:
    """1 对 1 会议服务"""

    def __init__(self, db: Session):
        self.db = db

    def create_meeting(
        self,
        employee_id: str,
        manager_id: str,
        meeting_date: datetime,
        agenda: str = None,
        meeting_type: str = "regular",
        duration_minutes: int = 30,
    ) -> OneOnOneMeeting:
        """创建会议记录"""
        meeting = OneOnOneMeeting(
            id=str(uuid.uuid4()),
            employee_id=employee_id,
            manager_id=manager_id,
            meeting_date=meeting_date,
            agenda=agenda,
            meeting_type=meeting_type,
            duration_minutes=duration_minutes,
        )
        self.db.add(meeting)
        self.db.commit()
        self.db.refresh(meeting)
        logger.info(f"Created 1:1 meeting: {meeting.id} for employee: {employee_id}")
        return meeting

    def get_meeting(self, meeting_id: str) -> Optional[OneOnOneMeeting]:
        """获取会议详情"""
        return self.db.query(OneOnOneMeeting).filter(OneOnOneMeeting.id == meeting_id).first()

    def get_employee_meetings(
        self,
        employee_id: str,
        limit: int = 20,
    ) -> List[OneOnOneMeeting]:
        """获取员工的会议列表"""
        return (
            self.db.query(OneOnOneMeeting)
            .filter(OneOnOneMeeting.employee_id == employee_id)
            .order_by(desc(OneOnOneMeeting.meeting_date))
            .limit(limit)
            .all()
        )

    def update_meeting(
        self,
        meeting_id: str,
        notes: str = None,
        summary: str = None,
        topics_discussed: List[str] = None,
        follow_up_date: datetime = None,
    ) -> OneOnOneMeeting:
        """更新会议记录"""
        meeting = self.get_meeting(meeting_id)
        if not meeting:
            raise ValueError(f"Meeting not found: {meeting_id}")

        if notes is not None:
            meeting.notes = notes
        if summary is not None:
            meeting.summary = summary
        if topics_discussed is not None:
            meeting.topics_discussed = topics_discussed
        if follow_up_date is not None:
            meeting.follow_up_date = follow_up_date

        self.db.commit()
        self.db.refresh(meeting)
        logger.info(f"Updated meeting: {meeting_id}")
        return meeting

    def create_action_item(
        self,
        meeting_id: str,
        description: str,
        owner_id: str,
        priority: str = "medium",
        owner_type: str = "employee",
        due_date: datetime = None,
    ) -> ActionItem:
        """创建行动项"""
        meeting = self.get_meeting(meeting_id)
        if not meeting:
            raise ValueError(f"Meeting not found: {meeting_id}")

        action_item = ActionItem(
            id=str(uuid.uuid4()),
            meeting_id=meeting_id,
            description=description,
            priority=priority,
            owner_id=owner_id,
            owner_type=owner_type,
            due_date=due_date,
        )
        self.db.add(action_item)
        self.db.commit()
        self.db.refresh(action_item)
        logger.info(f"Created action item: {action_item.id} for meeting: {meeting_id}")
        return action_item

    def update_action_item(
        self,
        action_item_id: str,
        status: ActionItemStatus = None,
        notes: str = None,
    ) -> ActionItem:
        """更新行动项"""
        from models.p14_models import ActionItem
        action_item = self.db.query(ActionItem).filter(ActionItem.id == action_item_id).first()
        if not action_item:
            raise ValueError(f"Action item not found: {action_item_id}")

        if status is not None:
            action_item.status = status
            if status == ActionItemStatus.COMPLETED:
                action_item.completed_at = datetime.utcnow()
        if notes is not None:
            action_item.notes = notes

        self.db.commit()
        self.db.refresh(action_item)
        logger.info(f"Updated action item: {action_item_id}")
        return action_item

    def get_action_items(self, meeting_id: str) -> List[ActionItem]:
        """获取会议的行动项"""
        return self.db.query(ActionItem).filter(ActionItem.meeting_id == meeting_id).all()


# ==================== 晋升推荐服务 ====================

class PromotionService:
    """晋升推荐服务"""

    def __init__(self, db: Session):
        self.db = db

    def generate_promotion_recommendation(
        self,
        employee_id: str,
        current_level: str,
        performance_score: float = None,
        tenure_months: int = None,
        skills_assessment: Dict[str, Any] = None,
    ) -> PromotionRecommendation:
        """生成晋升推荐"""
        # 如果没有提供绩效分数，从历史数据计算
        if performance_score is None:
            performance_score = self._calculate_performance_score(employee_id)

        # 计算推荐分数
        recommendation_score = self._calculate_recommendation_score(
            performance_score, tenure_months, skills_assessment
        )

        # 确定推荐等级
        recommended_level = self._determine_recommended_level(current_level, recommendation_score)

        # 生成推荐理由
        reasons = self._generate_reasons(recommendation_score, performance_score, tenure_months)

        # 收集支持证据
        supporting_evidence = self._collect_supporting_evidence(employee_id, performance_score)

        recommendation = PromotionRecommendation(
            id=str(uuid.uuid4()),
            employee_id=employee_id,
            current_level=current_level,
            recommended_level=recommended_level,
            recommendation_score=recommendation_score,
            reasons=reasons,
            supporting_evidence=supporting_evidence,
            performance_score=performance_score,
            tenure_months=tenure_months,
            skills_assessment=skills_assessment,
        )
        self.db.add(recommendation)
        self.db.commit()
        self.db.refresh(recommendation)
        logger.info(f"Generated promotion recommendation for employee: {employee_id}, score: {recommendation_score}")
        return recommendation

    def _calculate_performance_score(self, employee_id: str) -> float:
        """从历史绩效指标计算绩效分数"""
        from models.p14_models import PerformanceMetrics
        metrics = (
            self.db.query(PerformanceMetrics)
            .filter(PerformanceMetrics.employee_id == employee_id)
            .order_by(desc(PerformanceMetrics.period_end))
            .limit(3)
            .all()
        )
        if not metrics:
            return 0.0
        return round(sum(m.overall_performance_score or 0 for m in metrics) / len(metrics), 2)

    def _calculate_recommendation_score(
        self,
        performance_score: float,
        tenure_months: int,
        skills_assessment: Dict,
    ) -> float:
        """计算推荐分数"""
        score = 0.0

        # 绩效分数权重 50%
        score += performance_score * 0.5

        # 资历权重 20%（假设 12 个月满分）
        if tenure_months:
            tenure_score = min(100, (tenure_months / 12) * 100)
            score += tenure_score * 0.2

        # 技能评估权重 30%
        if skills_assessment:
            skill_scores = [v for v in skills_assessment.values() if isinstance(v, (int, float))]
            if skill_scores:
                avg_skill_score = sum(skill_scores) / len(skill_scores)
                score += avg_skill_score * 0.3

        return round(min(100, score), 2)

    def _determine_recommended_level(self, current_level: str, recommendation_score: float) -> str:
        """确定推荐等级"""
        level_order = ["junior", "mid", "senior", "lead", "principal", "staff"]

        try:
            current_index = level_order.index(current_level.lower())
        except ValueError:
            return f"next_{current_level}"

        if recommendation_score >= 90:
            # 非常优秀，可以连升两级
            new_index = min(current_index + 2, len(level_order) - 1)
        elif recommendation_score >= 75:
            # 优秀，升一级
            new_index = min(current_index + 1, len(level_order) - 1)
        else:
            # 不建议晋升
            new_index = current_index

        return level_order[new_index] if new_index > current_index else current_level

    def _generate_reasons(
        self,
        recommendation_score: float,
        performance_score: float,
        tenure_months: int,
    ) -> List[str]:
        """生成推荐理由"""
        reasons = []

        if performance_score >= 80:
            reasons.append(f"持续高绩效表现 (平均分：{performance_score})")
        elif performance_score >= 60:
            reasons.append(f"稳定的绩效表现 (平均分：{performance_score})")

        if tenure_months and tenure_months >= 12:
            reasons.append(f"在职时间充足 ({tenure_months} 个月)")

        if recommendation_score >= 90:
            reasons.append("表现出超越当前等级的能力")
        elif recommendation_score >= 75:
            reasons.append("具备下一等级的潜力")

        if not reasons:
            reasons.append("建议继续观察和培养")

        return reasons

    def _collect_supporting_evidence(self, employee_id: str, performance_score: float) -> List[Dict]:
        """收集支持证据"""
        evidence = []

        # 最近的绩效评估
        from models.p14_models import PerformanceReview
        recent_reviews = (
            self.db.query(PerformanceReview)
            .filter(PerformanceReview.employee_id == employee_id)
            .filter(PerformanceReview.status == ReviewStatus.COMPLETED)
            .order_by(desc(PerformanceReview.completed_at))
            .limit(3)
            .all()
        )
        for review in recent_reviews:
            evidence.append({
                "type": "performance_review",
                "score": review.overall_score,
                "date": review.completed_at.isoformat() if review.completed_at else None,
            })

        return evidence

    def get_recommendation(self, recommendation_id: str) -> Optional[PromotionRecommendation]:
        """获取晋升推荐"""
        return self.db.query(PromotionRecommendation).filter(PromotionRecommendation.id == recommendation_id).first()

    def get_employee_recommendations(
        self,
        employee_id: str,
        status: PromotionStatus = None,
    ) -> List[PromotionRecommendation]:
        """获取员工的晋升推荐历史"""
        query = self.db.query(PromotionRecommendation).filter(PromotionRecommendation.employee_id == employee_id)
        if status:
            query = query.filter(PromotionRecommendation.status == status)
        return query.order_by(desc(PromotionRecommendation.created_at)).all()

    def approve_promotion(
        self,
        recommendation_id: str,
        reviewed_by: str,
        review_comments: str = None,
    ) -> PromotionRecommendation:
        """审批晋升"""
        recommendation = self.get_recommendation(recommendation_id)
        if not recommendation:
            raise ValueError(f"Promotion recommendation not found: {recommendation_id}")

        recommendation.status = PromotionStatus.APPROVED
        recommendation.reviewed_by = reviewed_by
        recommendation.reviewed_at = datetime.utcnow()
        recommendation.review_comments = review_comments

        self.db.commit()
        self.db.refresh(recommendation)

        # 创建晋升历史
        self._create_promotion_history(recommendation)

        logger.info(f"Approved promotion: {recommendation_id}")
        return recommendation

    def reject_promotion(
        self,
        recommendation_id: str,
        reviewed_by: str,
        review_comments: str = None,
    ) -> PromotionRecommendation:
        """拒绝晋升"""
        recommendation = self.get_recommendation(recommendation_id)
        if not recommendation:
            raise ValueError(f"Promotion recommendation not found: {recommendation_id}")

        recommendation.status = PromotionStatus.REJECTED
        recommendation.reviewed_by = reviewed_by
        recommendation.reviewed_at = datetime.utcnow()
        recommendation.review_comments = review_comments

        self.db.commit()
        self.db.refresh(recommendation)
        logger.info(f"Rejected promotion: {recommendation_id}")
        return recommendation

    def _create_promotion_history(self, recommendation: PromotionRecommendation) -> PromotionHistory:
        """创建晋升历史记录"""
        history = PromotionHistory(
            id=str(uuid.uuid4()),
            employee_id=recommendation.employee_id,
            from_level=recommendation.current_level,
            to_level=recommendation.recommended_level,
            effective_date=datetime.utcnow(),
            recommendation_id=recommendation.id,
            notes=f"Approved by {recommendation.reviewed_by}",
        )
        self.db.add(history)
        self.db.commit()
        self.db.refresh(history)
        return history

    def get_pending_promotions(self) -> List[PromotionRecommendation]:
        """获取待审批的晋升推荐"""
        return (
            self.db.query(PromotionRecommendation)
            .filter(PromotionRecommendation.status == PromotionStatus.PENDING)
            .order_by(desc(PromotionRecommendation.recommendation_score))
            .all()
        )


# ==================== 绩效基准服务 ====================

class BenchmarkService:
    """绩效基准服务"""

    def __init__(self, db: Session):
        self.db = db

    def create_benchmark(
        self,
        name: str,
        category: str,
        percentile_25: float = None,
        percentile_50: float = None,
        percentile_75: float = None,
        average: float = None,
        sample_size: int = None,
        data_source: str = "internal",
        min_experience_months: int = None,
        skill_level: str = None,
    ) -> PerformanceBenchmark:
        """创建绩效基准"""
        benchmark = PerformanceBenchmark(
            id=str(uuid.uuid4()),
            name=name,
            category=category,
            percentile_25=percentile_25,
            percentile_50=percentile_50,
            percentile_75=percentile_75,
            average=average,
            sample_size=sample_size,
            data_source=data_source,
            min_experience_months=min_experience_months,
            skill_level=skill_level,
        )
        self.db.add(benchmark)
        self.db.commit()
        self.db.refresh(benchmark)
        logger.info(f"Created performance benchmark: {benchmark.id}, name: {name}")
        return benchmark

    def get_benchmark(self, benchmark_id: str) -> Optional[PerformanceBenchmark]:
        """获取基准"""
        return self.db.query(PerformanceBenchmark).filter(PerformanceBenchmark.id == benchmark_id).first()

    def list_benchmarks(self, category: str = None) -> List[PerformanceBenchmark]:
        """获取基准列表"""
        query = self.db.query(PerformanceBenchmark)
        if category:
            query = query.filter(PerformanceBenchmark.category == category)
        return query.all()

    def get_benchmarks(self) -> Dict[str, Any]:
        """获取所有基准数据"""
        benchmarks = self.db.query(PerformanceBenchmark).all()
        result = {}
        for b in benchmarks:
            if b.category not in result:
                result[b.category] = []
            result[b.category].append(b.to_dict())
        return result


# ==================== 绩效评估外观服务 ====================

class PerformanceService:
    """绩效评估统一外观服务

    整合所有绩效相关服务，提供统一的接口
    """

    def __init__(self, db: Session):
        self.db = db
        self.review_cycle_service = ReviewCycleService(db)
        self.review_service = PerformanceReviewService(db)
        self.dimension_service = ReviewDimensionService(db)
        self.objective_service = ObjectiveService(db)
        self.key_result_service = KeyResultService(db)
        self.metrics_service = PerformanceMetricsService(db)
        self.meeting_service = OneOnOneMeetingService(db)
        self.promotion_service = PromotionService(db)
        self.benchmark_service = BenchmarkService(db)

    def get_health_status(self) -> Dict[str, Any]:
        """获取服务健康状态"""
        return {
            "status": "healthy",
            "services": {
                "review_cycle": "available",
                "performance_review": "available",
                "objective": "available",
                "key_result": "available",
                "metrics": "available",
                "meeting": "available",
                "promotion": "available",
                "benchmark": "available",
            },
        }
