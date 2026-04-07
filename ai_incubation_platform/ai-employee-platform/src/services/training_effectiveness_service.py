"""
P7 训练效果评估服务

提供：
- 任务完成率统计
- 准确率评估
- 用户反馈整合
- AI 能力评分模型
"""
import math
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import uuid
from enum import Enum
from collections import defaultdict


# ==================== 数据模型 ====================

class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class FeedbackType(str, Enum):
    RATING = "rating"
    COMMENT = "comment"
    BUG_REPORT = "bug_report"
    FEATURE_REQUEST = "feature_request"


class TaskRecord(BaseModel):
    """任务记录"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    employee_id: str
    user_id: str
    tenant_id: str
    task_type: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None


class UserFeedback(BaseModel):
    """用户反馈"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    employee_id: str
    user_id: str
    tenant_id: str
    task_id: Optional[str] = None
    feedback_type: FeedbackType
    rating: Optional[int] = Field(None, ge=1, le=5)  # 1-5 星
    comment: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    is_resolved: bool = False


class CapabilityScore(BaseModel):
    """能力评分"""
    employee_id: str
    capability_name: str
    score: float  # 0-100
    confidence: float  # 0-1，评分置信度
    sample_size: int  # 样本数量
    trend: str  # improving, stable, declining
    last_updated: datetime


class TrainingEffectiveness(BaseModel):
    """训练效果评估"""
    employee_id: str
    evaluation_period: str  # e.g., "last_7_days", "last_30_days"

    # 任务完成指标
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    completion_rate: float

    # 准确率指标
    accurate_tasks: int
    accuracy_rate: float

    # 用户反馈指标
    total_feedback: int
    average_rating: float
    positive_feedback_rate: float

    # 能力评分
    capability_scores: List[CapabilityScore]

    # 综合评分
    overall_score: float
    overall_level: str  # beginner, intermediate, advanced, expert

    # 建议
    strengths: List[str]
    areas_for_improvement: List[str]
    recommended_training: List[str]


# ==================== 服务类 ====================

class TrainingEffectivenessService:
    """训练效果评估服务"""

    def __init__(self):
        # 内存存储（实际应使用数据库）
        self._tasks: Dict[str, TaskRecord] = {}
        self._feedbacks: Dict[str, UserFeedback] = {}
        self._capability_scores: Dict[str, Dict[str, CapabilityScore]] = defaultdict(dict)
        self._evaluations: Dict[str, TrainingEffectiveness] = {}

        # 能力维度定义
        self._capability_dimensions = [
            {"id": "task_completion", "name": "任务完成能力", "weight": 0.25},
            {"id": "accuracy", "name": "准确性", "weight": 0.25},
            {"id": "efficiency", "name": "效率", "weight": 0.15},
            {"id": "reliability", "name": "可靠性", "weight": 0.15},
            {"id": "user_satisfaction", "name": "用户满意度", "weight": 0.20},
        ]

    # ==================== 任务记录管理 ====================

    def record_task(self, data: Dict[str, Any]) -> TaskRecord:
        """记录任务"""
        task = TaskRecord(
            id=str(uuid.uuid4()),
            employee_id=data['employee_id'],
            user_id=data.get('user_id', 'unknown'),
            tenant_id=data.get('tenant_id', 'default'),
            task_type=data.get('task_type', 'general'),
            description=data.get('description', ''),
            status=TaskStatus(data.get('status', 'pending')),
            metrics=data.get('metrics', {}),
            result=data.get('result')
        )

        if data.get('created_at'):
            task.created_at = data['created_at']
        if data.get('started_at'):
            task.started_at = data['started_at']
        if data.get('completed_at'):
            task.completed_at = data['completed_at']
        if data.get('error_message'):
            task.error_message = data['error_message']

        self._tasks[task.id] = task
        return task

    def update_task_status(self, task_id: str, status: TaskStatus, result: Optional[Dict[str, Any]] = None,
                          error_message: Optional[str] = None):
        """更新任务状态"""
        if task_id in self._tasks:
            task = self._tasks[task_id]
            task.status = status
            if result:
                task.result = result
            if error_message:
                task.error_message = error_message
            if status == TaskStatus.COMPLETED:
                task.completed_at = datetime.now()
            elif status == TaskStatus.IN_PROGRESS and not task.started_at:
                task.started_at = datetime.now()

    def get_employee_tasks(self, employee_id: str,
                          start_date: Optional[datetime] = None,
                          end_date: Optional[datetime] = None) -> List[TaskRecord]:
        """获取员工的任务记录"""
        tasks = [t for t in self._tasks.values() if t.employee_id == employee_id]

        if start_date:
            tasks = [t for t in tasks if t.created_at >= start_date]
        if end_date:
            tasks = [t for t in tasks if t.created_at <= end_date]

        return tasks

    # ==================== 用户反馈管理 ====================

    def submit_feedback(self, data: Dict[str, Any]) -> UserFeedback:
        """提交用户反馈"""
        feedback = UserFeedback(
            id=str(uuid.uuid4()),
            employee_id=data['employee_id'],
            user_id=data['user_id'],
            tenant_id=data.get('tenant_id', 'default'),
            feedback_type=FeedbackType(data.get('feedback_type', 'rating')),
            rating=data.get('rating'),
            comment=data.get('comment'),
            tags=data.get('tags', []),
            metadata=data.get('metadata', {}),
            task_id=data.get('task_id')
        )
        self._feedbacks[feedback.id] = feedback
        return feedback

    def get_employee_feedback(self, employee_id: str,
                             start_date: Optional[datetime] = None,
                             end_date: Optional[datetime] = None) -> List[UserFeedback]:
        """获取员工的用户反馈"""
        feedbacks = [f for f in self._feedbacks.values() if f.employee_id == employee_id]

        if start_date:
            feedbacks = [f for f in feedbacks if f.created_at >= start_date]
        if end_date:
            feedbacks = [f for f in feedbacks if f.created_at <= end_date]

        return feedbacks

    # ==================== 任务完成率统计 ====================

    def calculate_completion_rate(self, employee_id: str,
                                  start_date: Optional[datetime] = None,
                                  end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        计算任务完成率

        Returns:
            包含总数、完成数、失败数、完成率的字典
        """
        tasks = self.get_employee_tasks(employee_id, start_date, end_date)

        total = len(tasks)
        completed = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
        failed = sum(1 for t in tasks if t.status == TaskStatus.FAILED)
        cancelled = sum(1 for t in tasks if t.status == TaskStatus.CANCELLED)
        in_progress = sum(1 for t in tasks if t.status == TaskStatus.IN_PROGRESS)

        # 完成率 = 完成数 / (总数 - 取消数)
        effective_total = total - cancelled
        completion_rate = (completed / effective_total * 100) if effective_total > 0 else 0

        return {
            "total_tasks": total,
            "completed_tasks": completed,
            "failed_tasks": failed,
            "cancelled_tasks": cancelled,
            "in_progress_tasks": in_progress,
            "completion_rate": round(completion_rate, 2),
            "failure_rate": round((failed / effective_total * 100) if effective_total > 0 else 0, 2)
        }

    # ==================== 准确率评估 ====================

    def calculate_accuracy_rate(self, employee_id: str,
                               start_date: Optional[datetime] = None,
                               end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        计算准确率

        基于任务结果的质量指标评估准确率
        """
        tasks = self.get_employee_tasks(employee_id, start_date, end_date)
        completed_tasks = [t for t in tasks if t.status == TaskStatus.COMPLETED]

        if not completed_tasks:
            return {
                "total_evaluated": 0,
                "accurate_tasks": 0,
                "accuracy_rate": 0
            }

        accurate_count = 0
        accuracy_scores = []

        for task in completed_tasks:
            # 从指标中获取准确率
            accuracy = task.metrics.get('accuracy', None)

            if accuracy is not None:
                accuracy_scores.append(accuracy)
                if accuracy >= 0.8:  # 80% 以上算准确
                    accurate_count += 1
            elif task.metrics.get('passed', False):
                accurate_count += 1
                accuracy_scores.append(1.0)
            elif task.error_message:
                accuracy_scores.append(0.0)
            else:
                # 默认认为完成的任务是准确的
                accurate_count += 1
                accuracy_scores.append(1.0)

        avg_accuracy = sum(accuracy_scores) / len(accuracy_scores) if accuracy_scores else 0

        return {
            "total_evaluated": len(completed_tasks),
            "accurate_tasks": accurate_count,
            "accuracy_rate": round(avg_accuracy * 100, 2),
            "accuracy_scores": accuracy_scores
        }

    # ==================== 用户反馈整合 ====================

    def analyze_feedback(self, employee_id: str,
                        start_date: Optional[datetime] = None,
                        end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        分析用户反馈

        Returns:
            包含反馈统计、平均评分、情感分析的字典
        """
        feedbacks = self.get_employee_feedback(employee_id, start_date, end_date)

        if not feedbacks:
            return {
                "total_feedback": 0,
                "average_rating": 0,
                "rating_distribution": {},
                "positive_rate": 0,
                "common_tags": [],
                "sentiment": "neutral"
            }

        # 评分反馈
        rating_feedbacks = [f for f in feedbacks if f.rating is not None]

        # 评分分布
        rating_dist = defaultdict(int)
        for f in rating_feedbacks:
            rating_dist[f.rating] += 1

        # 平均评分
        avg_rating = sum(f.rating for f in rating_feedbacks) / len(rating_feedbacks) if rating_feedbacks else 0

        # 正面反馈率 (4-5 星为正面)
        positive_count = sum(1 for f in rating_feedbacks if f.rating >= 4)
        positive_rate = (positive_count / len(rating_feedbacks) * 100) if rating_feedbacks else 0

        # 常见标签
        tag_counts = defaultdict(int)
        for f in feedbacks:
            for tag in f.tags:
                tag_counts[tag] += 1
        common_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        # 情感分析（简化版，基于评分）
        if avg_rating >= 4:
            sentiment = "positive"
        elif avg_rating >= 3:
            sentiment = "neutral"
        else:
            sentiment = "negative"

        return {
            "total_feedback": len(feedbacks),
            "average_rating": round(avg_rating, 2),
            "rating_distribution": dict(rating_dist),
            "positive_rate": round(positive_rate, 2),
            "common_tags": common_tags,
            "sentiment": sentiment
        }

    # ==================== AI 能力评分模型 ====================

    def calculate_capability_scores(self, employee_id: str) -> List[CapabilityScore]:
        """
        计算各维度能力评分
        """
        # 获取最近 30 天的数据
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)

        completion_stats = self.calculate_completion_rate(employee_id, start_date, end_date)
        accuracy_stats = self.calculate_accuracy_rate(employee_id, start_date, end_date)
        feedback_stats = self.analyze_feedback(employee_id, start_date, end_date)

        # 获取历史评分用于计算趋势
        prev_end_date = start_date
        prev_start_date = prev_end_date - timedelta(days=30)

        prev_completion = self.calculate_completion_rate(employee_id, prev_start_date, prev_end_date)

        scores = []

        # 1. 任务完成能力 (25%)
        completion_score = completion_stats['completion_rate']
        completion_trend = self._calculate_trend(completion_stats['completion_rate'],
                                                  prev_completion['completion_rate'])
        scores.append(CapabilityScore(
            employee_id=employee_id,
            capability_name="任务完成能力",
            score=completion_score,
            confidence=min(1.0, completion_stats['total_tasks'] / 10),
            sample_size=completion_stats['total_tasks'],
            trend=completion_trend,
            last_updated=datetime.now()
        ))

        # 2. 准确性 (25%)
        accuracy_score = accuracy_stats['accuracy_rate']
        scores.append(CapabilityScore(
            employee_id=employee_id,
            capability_name="准确性",
            score=accuracy_score,
            confidence=min(1.0, accuracy_stats['total_evaluated'] / 5),
            sample_size=accuracy_stats['total_evaluated'],
            trend="stable",  # 简化处理
            last_updated=datetime.now()
        ))

        # 3. 效率 (15%)
        efficiency_score = self._calculate_efficiency_score(employee_id, start_date, end_date)
        scores.append(CapabilityScore(
            employee_id=employee_id,
            capability_name="效率",
            score=efficiency_score,
            confidence=0.7,
            sample_size=completion_stats['completed_tasks'],
            trend="stable",
            last_updated=datetime.now()
        ))

        # 4. 可靠性 (15%)
        reliability_score = self._calculate_reliability_score(employee_id, start_date, end_date)
        scores.append(CapabilityScore(
            employee_id=employee_id,
            capability_name="可靠性",
            score=reliability_score,
            confidence=0.8,
            sample_size=completion_stats['total_tasks'],
            trend="stable",
            last_updated=datetime.now()
        ))

        # 5. 用户满意度 (20%)
        satisfaction_score = feedback_stats['average_rating'] / 5 * 100 if feedback_stats['total_feedback'] > 0 else 50
        scores.append(CapabilityScore(
            employee_id=employee_id,
            capability_name="用户满意度",
            score=satisfaction_score,
            confidence=min(1.0, feedback_stats['total_feedback'] / 5),
            sample_size=feedback_stats['total_feedback'],
            trend="stable",
            last_updated=datetime.now()
        ))

        # 更新缓存
        for score in scores:
            self._capability_scores[employee_id][score.capability_name] = score

        return scores

    def _calculate_efficiency_score(self, employee_id: str,
                                    start_date: datetime, end_date: datetime) -> float:
        """计算效率分数"""
        tasks = self.get_employee_tasks(employee_id, start_date, end_date)
        completed_tasks = [t for t in tasks if t.status == TaskStatus.COMPLETED and t.started_at and t.completed_at]

        if not completed_tasks:
            return 50.0  # 默认分数

        # 计算平均完成时间
        total_duration = 0
        for task in completed_tasks:
            duration = (task.completed_at - task.started_at).total_seconds()
            total_duration += duration

        avg_duration = total_duration / len(completed_tasks)

        # 根据平均完成时间评分（简化：假设 1 小时内完成为优秀）
        if avg_duration <= 3600:  # 1 小时
            return 100.0
        elif avg_duration <= 7200:  # 2 小时
            return 80.0
        elif avg_duration <= 14400:  # 4 小时
            return 60.0
        elif avg_duration <= 28800:  # 8 小时
            return 40.0
        else:
            return 20.0

    def _calculate_reliability_score(self, employee_id: str,
                                     start_date: datetime, end_date: datetime) -> float:
        """计算可靠性分数"""
        tasks = self.get_employee_tasks(employee_id, start_date, end_date)

        if not tasks:
            return 50.0

        # 可靠性基于：按时完成率、错误率
        completed = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
        failed = sum(1 for t in tasks if t.status == TaskStatus.FAILED)

        # 按时完成（假设有 deadline 字段）
        on_time = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED and
                     not t.metrics.get('overdue', False))

        completion_rate = completed / len(tasks) if tasks else 0
        on_time_rate = on_time / len(tasks) if tasks else 0
        error_rate = failed / len(tasks) if tasks else 0

        # 可靠性分数
        reliability = (completion_rate * 0.4 + on_time_rate * 0.4 + (1 - error_rate) * 0.2) * 100
        return reliability

    def _calculate_trend(self, current: float, previous: float) -> str:
        """计算趋势"""
        if previous == 0:
            return "stable"

        change = (current - previous) / previous * 100

        if change > 10:
            return "improving"
        elif change > 5:
            return "slightly_improving"
        elif change < -10:
            return "declining"
        elif change < -5:
            return "slightly_declining"
        else:
            return "stable"

    # ==================== 综合评估 ====================

    def evaluate_training_effectiveness(self, employee_id: str,
                                        period: str = "last_30_days") -> TrainingEffectiveness:
        """
        综合评估训练效果

        Args:
            employee_id: 员工 ID
            period: 评估周期 (last_7_days, last_30_days, last_90_days)

        Returns:
            TrainingEffectiveness: 训练效果评估结果
        """
        # 计算周期
        end_date = datetime.now()
        if period == "last_7_days":
            start_date = end_date - timedelta(days=7)
        elif period == "last_30_days":
            start_date = end_date - timedelta(days=30)
        elif period == "last_90_days":
            start_date = end_date - timedelta(days=90)
        else:
            start_date = end_date - timedelta(days=30)

        # 获取各项统计
        completion_stats = self.calculate_completion_rate(employee_id, start_date, end_date)
        accuracy_stats = self.calculate_accuracy_rate(employee_id, start_date, end_date)
        feedback_stats = self.analyze_feedback(employee_id, start_date, end_date)
        capability_scores = self.calculate_capability_scores(employee_id)

        # 计算综合评分
        overall_score = self._calculate_overall_score(
            completion_stats, accuracy_stats, feedback_stats, capability_scores
        )

        # 确定等级
        overall_level = self._determine_level(overall_score)

        # 生成优势和改进建议
        strengths = self._identify_strengths(capability_scores)
        areas_for_improvement = self._identify_improvement_areas(capability_scores)
        recommended_training = self._generate_training_recommendations(
            capability_scores, areas_for_improvement
        )

        evaluation = TrainingEffectiveness(
            employee_id=employee_id,
            evaluation_period=period,
            total_tasks=completion_stats['total_tasks'],
            completed_tasks=completion_stats['completed_tasks'],
            failed_tasks=completion_stats['failed_tasks'],
            completion_rate=completion_stats['completion_rate'],
            accurate_tasks=accuracy_stats['accurate_tasks'],
            accuracy_rate=accuracy_stats['accuracy_rate'],
            total_feedback=feedback_stats['total_feedback'],
            average_rating=feedback_stats['average_rating'],
            positive_feedback_rate=feedback_stats['positive_rate'],
            capability_scores=capability_scores,
            overall_score=overall_score,
            overall_level=overall_level,
            strengths=strengths,
            areas_for_improvement=areas_for_improvement,
            recommended_training=recommended_training
        )

        self._evaluations[f"{employee_id}_{period}"] = evaluation
        return evaluation

    def _calculate_overall_score(self, completion_stats: Dict, accuracy_stats: Dict,
                                 feedback_stats: Dict, capability_scores: List[CapabilityScore]) -> float:
        """计算综合评分"""
        # 各维度权重
        weights = {
            'completion': 0.25,
            'accuracy': 0.25,
            'satisfaction': 0.20,
            'capabilities': 0.30
        }

        # 完成率得分
        completion_score = completion_stats['completion_rate']

        # 准确率得分
        accuracy_score = accuracy_stats['accuracy_rate']

        # 满意度得分（转换为 0-100）
        satisfaction_score = feedback_stats['average_rating'] / 5 * 100 if feedback_stats['total_feedback'] > 0 else 50

        # 能力得分（加权平均）
        if capability_scores:
            capability_score = sum(
                cs.score * next((d['weight'] for d in self._capability_dimensions if d['name'] == cs.capability_name), 0.2)
                for cs in capability_scores
            ) / sum(d['weight'] for d in self._capability_dimensions)
        else:
            capability_score = 50

        # 综合评分
        overall = (
            completion_score * weights['completion'] +
            accuracy_score * weights['accuracy'] +
            satisfaction_score * weights['satisfaction'] +
            capability_score * weights['capabilities']
        )

        return round(overall, 2)

    def _determine_level(self, score: float) -> str:
        """根据分数确定等级"""
        if score >= 90:
            return "expert"
        elif score >= 75:
            return "advanced"
        elif score >= 60:
            return "intermediate"
        else:
            return "beginner"

    def _identify_strengths(self, capability_scores: List[CapabilityScore]) -> List[str]:
        """识别优势"""
        strengths = []
        high_scores = [cs for cs in capability_scores if cs.score >= 75]

        for cs in high_scores:
            if cs.trend == "improving":
                strengths.append(f"{cs.capability_name}持续提升")
            else:
                strengths.append(f"{cs.capability_name}优秀 ({cs.score:.0f}分)")

        if not strengths:
            strengths.append("各项能力均衡发展")

        return strengths

    def _identify_improvement_areas(self, capability_scores: List[CapabilityScore]) -> List[str]:
        """识别需要改进的领域"""
        areas = []
        low_scores = [cs for cs in capability_scores if cs.score < 60]

        for cs in low_scores:
            if cs.trend == "declining":
                areas.append(f"{cs.capability_name}需要重点关注（呈下降趋势）")
            else:
                areas.append(f"{cs.capability_name}有待提升（当前{cs.score:.0f}分）")

        return areas

    def _generate_training_recommendations(self, capability_scores: List[CapabilityScore],
                                          improvement_areas: List[str]) -> List[str]:
        """生成训练建议"""
        recommendations = []

        for cs in capability_scores:
            if cs.score < 70:
                if cs.capability_name == "任务完成能力":
                    recommendations.append("增加任务练习量，提高任务完成率")
                elif cs.capability_name == "准确性":
                    recommendations.append("加强质量检查，减少错误输出")
                elif cs.capability_name == "效率":
                    recommendations.append("优化处理流程，提高响应速度")
                elif cs.capability_name == "可靠性":
                    recommendations.append("提高稳定性，减少异常和超时")
                elif cs.capability_name == "用户满意度":
                    recommendations.append("关注用户反馈，改进交互体验")

        if not recommendations:
            recommendations.append("保持当前训练强度，持续提升各项能力")

        return recommendations

    # ==================== 报表导出 ====================

    def generate_report(self, employee_id: str, period: str = "last_30_days") -> Dict[str, Any]:
        """
        生成训练效果评估报告
        """
        evaluation = self.evaluate_training_effectiveness(employee_id, period)

        return {
            "employee_id": employee_id,
            "report_type": "training_effectiveness",
            "evaluation_period": evaluation.evaluation_period,
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "overall_score": evaluation.overall_score,
                "overall_level": evaluation.overall_level,
                "total_tasks": evaluation.total_tasks,
                "completion_rate": evaluation.completion_rate,
                "accuracy_rate": evaluation.accuracy_rate,
                "average_rating": evaluation.average_rating
            },
            "capability_breakdown": [
                {
                    "name": cs.capability_name,
                    "score": cs.score,
                    "confidence": cs.confidence,
                    "trend": cs.trend
                }
                for cs in evaluation.capability_scores
            ],
            "insights": {
                "strengths": evaluation.strengths,
                "areas_for_improvement": evaluation.areas_for_improvement,
                "recommended_training": evaluation.recommended_training
            }
        }


# 全局服务实例
training_effectiveness_service = TrainingEffectivenessService()
