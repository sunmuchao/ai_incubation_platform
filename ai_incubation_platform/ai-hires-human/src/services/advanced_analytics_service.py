"""
P10 高级分析与预测 - 服务层。

实现预测分析算法和业务逻辑。
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import joinedload

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.analytics import (
    TaskSuccessPrediction,
    TaskSuccessBatchPrediction,
    WorkerChurnPrediction,
    WorkerChurnBatchPrediction,
    RevenuePrediction,
    RevenueForecast,
    AnomalyDetection,
    AnomalyDetectionReport,
    AdvancedAnalyticsDashboard,
    AnalyticsQueryParams,
    PredictionQueryParams,
)
from models.db_models import (
    TaskDB,
    WorkerProfileDB,
    WorkerSubmissionDB,
    PaymentTransactionDB,
    EmployerProfileDB,
)


class AdvancedAnalyticsService:
    """高级分析与预测服务。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ==================== 任务成功概率预测 ====================

    async def predict_task_success(
        self,
        task_id: int,
        params: Optional[PredictionQueryParams] = None,
    ) -> TaskSuccessPrediction:
        """
        预测单个任务的成功概率。

        基于以下因素：
        - 任务报酬合理性
        - 工人历史表现
        - 任务复杂度
        - 时间紧迫性
        - 历史相似任务成功率
        """
        # 获取任务信息
        task_query = select(TaskDB).where(TaskDB.id == task_id)
        result = await self.db.execute(task_query)
        task = result.scalar_one_or_none()

        if not task:
            raise ValueError(f"Task {task_id} not found")

        # 获取接任务工人信息
        success_prob, risk_factors, features = await self._calculate_task_success_prob(task)

        # 确定风险等级
        risk_level = self._classify_risk_level(1 - success_prob)

        # 生成建议
        recommendations = self._generate_task_recommendations(risk_factors, success_prob)

        return TaskSuccessPrediction(
            task_id=task_id,
            success_probability=round(success_prob, 3),
            risk_level=risk_level,
            confidence=min(0.9, 0.5 + len(features) * 0.05),
            predicted_value="success" if success_prob > 0.5 else "failure",
            risk_factors=risk_factors,
            recommendations=recommendations,
            features=features,
        )

    async def predict_batch_task_success(
        self,
        params: PredictionQueryParams,
    ) -> TaskSuccessBatchPrediction:
        """批量预测任务成功概率。"""
        # 获取任务列表
        tasks_query = select(TaskDB)

        if params.start_date:
            tasks_query = tasks_query.where(
                TaskDB.created_at >= params.start_date
            )
        if params.end_date:
            tasks_query = tasks_query.where(
                TaskDB.created_at <= params.end_date
            )
        if params.organization_id:
            tasks_query = tasks_query.where(
                TaskDB.employer_id == params.organization_id
            )

        tasks_query = tasks_query.limit(params.limit)
        result = await self.db.execute(tasks_query)
        tasks = result.scalars().all()

        predictions = []
        for task in tasks:
            try:
                pred = await self.predict_task_success(task.id, params)
                predictions.append(pred)
            except Exception:
                continue

        # 生成摘要
        summary = self._generate_task_predictions_summary(predictions)

        return TaskSuccessBatchPrediction(
            predictions=predictions,
            summary=summary,
        )

    async def _calculate_task_success_prob(
        self,
        task: TaskDB,
    ) -> Tuple[float, List[Dict[str, Any]], Dict[str, Any]]:
        """计算任务成功概率。"""
        features = {}
        risk_factors = []
        base_prob = 0.8  # 基础成功率

        # 1. 报酬合理性分析
        reward_factor = await self._analyze_reward_reasonableness(task)
        features["reward_factor"] = reward_factor
        if reward_factor < 0.7:
            risk_factors.append({
                "factor": "low_reward",
                "impact": -0.15,
                "description": f"任务报酬低于市场水平 (因子：{reward_factor:.2f})"
            })
        base_prob *= reward_factor

        # 2. 时间紧迫性分析
        urgency_factor = self._analyze_time_urgency(task)
        features["urgency_factor"] = urgency_factor
        if urgency_factor < 0.8:
            risk_factors.append({
                "factor": "tight_deadline",
                "impact": -0.1,
                "description": "任务截止时间紧迫"
            })
        base_prob *= urgency_factor

        # 3. 历史相似任务成功率
        historical_rate = await self._get_similar_tasks_success_rate(task)
        features["historical_rate"] = historical_rate
        base_prob = (base_prob + historical_rate) / 2

        # 4. 如果有工人接单，考虑工人历史表现
        if task.accepted_by_worker_id:
            worker_factor = await self._analyze_worker_performance(task.accepted_by_worker_id)
            features["worker_factor"] = worker_factor
            base_prob *= worker_factor

        # 5. 任务复杂度
        complexity_factor = self._analyze_task_complexity(task)
        features["complexity_factor"] = complexity_factor
        if complexity_factor < 0.8:
            risk_factors.append({
                "factor": "high_complexity",
                "impact": -0.1,
                "description": "任务复杂度较高"
            })
        base_prob *= complexity_factor

        # 确保概率在合理范围
        success_prob = max(0.1, min(0.99, base_prob))

        return success_prob, risk_factors, features

    async def _analyze_reward_reasonableness(self, task: TaskDB) -> float:
        """分析报酬合理性。"""
        # 获取同类任务平均报酬
        avg_reward_query = select(
            func.avg(TaskDB.reward_amount)
        ).where(
            TaskDB.interaction_type == task.interaction_type,
            TaskDB.status.in_(["completed", "in_progress"])
        )
        result = await self.db.execute(avg_reward_query)
        avg_reward = result.scalar() or task.reward_amount

        if avg_reward == 0:
            return 1.0

        ratio = task.reward_amount / avg_reward

        # 报酬在平均值的 80%-120% 之间认为合理
        if 0.8 <= ratio <= 1.5:
            return 1.0
        elif ratio < 0.5:
            return 0.5
        elif ratio < 0.8:
            return 0.7
        else:
            return 1.1  # 高报酬略微提高成功率

    def _analyze_time_urgency(self, task: TaskDB) -> float:
        """分析时间紧迫性。"""
        if not task.deadline:
            return 1.0

        now = datetime.now()
        deadline = task.deadline
        created = task.created_at

        if isinstance(deadline, datetime) and isinstance(created, datetime):
            total_duration = (deadline - created).total_seconds()
            remaining = (deadline - now).total_seconds()

            if total_duration <= 0:
                return 0.5

            ratio = remaining / total_duration

            if ratio < 0.1:  # 剩余时间不足 10%
                return 0.6
            elif ratio < 0.3:
                return 0.8
            else:
                return 1.0

        return 1.0

    async def _get_similar_tasks_success_rate(self, task: TaskDB) -> float:
        """获取相似任务的历史成功率。"""
        # 查询相似任务
        query = select(
            func.count(TaskDB.id),
            func.sum(
                func.case(
                    (TaskDB.status == "completed", 1),
                    else_=0
                )
            )
        ).where(
            TaskDB.interaction_type == task.interaction_type,
            TaskDB.created_at >= datetime.now() - timedelta(days=90)
        )

        result = await self.db.execute(query)
        row = result.first()

        if row and row[0] > 0:
            return row[1] / row[0]
        return 0.8  # 默认 80% 成功率

    async def _analyze_worker_performance(self, worker_id: int) -> float:
        """分析工人历史表现。"""
        worker_query = select(WorkerProfileDB).where(
            WorkerProfileDB.worker_id == worker_id
        )
        result = await self.db.execute(worker_query)
        worker = result.scalar_one_or_none()

        if not worker:
            return 1.0

        # 综合评分：成功率、平均评分、完成任务数
        success_rate = worker.success_rate or 0.8
        avg_rating = (worker.average_rating or 4.0) / 5.0
        experience = min(1.0, (worker.completed_tasks or 0) / 100)

        return 0.5 * success_rate + 0.3 * avg_rating + 0.2 * (0.5 + experience * 0.5)

    def _analyze_task_complexity(self, task: TaskDB) -> float:
        """分析任务复杂度。"""
        # 基于描述长度、验收标准数量等简单评估
        complexity = 0.5

        description_len = len(task.description) if task.description else 0
        if description_len > 500:
            complexity += 0.2
        elif description_len > 200:
            complexity += 0.1

        acceptance_len = len(task.acceptance_criteria) if task.acceptance_criteria else 0
        if acceptance_len > 300:
            complexity += 0.2
        elif acceptance_len > 100:
            complexity += 0.1

        # 需要物理交互的任务通常更复杂
        if task.interaction_type == "physical":
            complexity += 0.1

        return max(0.5, min(1.0, complexity))

    def _classify_risk_level(self, risk_score: float) -> str:
        """分类风险等级。"""
        if risk_score >= 0.7:
            return "critical"
        elif risk_score >= 0.5:
            return "high"
        elif risk_score >= 0.3:
            return "medium"
        else:
            return "low"

    def _generate_task_recommendations(
        self,
        risk_factors: List[Dict[str, Any]],
        success_prob: float,
    ) -> List[str]:
        """生成任务建议。"""
        recommendations = []

        for rf in risk_factors:
            if rf["factor"] == "low_reward":
                recommendations.append("建议提高任务报酬以吸引更多优质工人")
            elif rf["factor"] == "tight_deadline":
                recommendations.append("建议延长任务截止时间")
            elif rf["factor"] == "high_complexity":
                recommendations.append("建议将任务拆分为更小的子任务")

        if success_prob < 0.6:
            recommendations.append("建议添加黄金标准测试题以确保质量")
            recommendations.append("建议启用智能验收助手进行实时监控")

        return recommendations

    def _generate_task_predictions_summary(
        self,
        predictions: List[TaskSuccessPrediction],
    ) -> Dict[str, Any]:
        """生成任务预测摘要。"""
        if not predictions:
            return {}

        probs = [p.success_probability for p in predictions]
        risk_levels = {}
        for p in predictions:
            risk_levels[p.risk_level] = risk_levels.get(p.risk_level, 0) + 1

        return {
            "total_tasks": len(predictions),
            "avg_success_probability": round(sum(probs) / len(probs), 3),
            "min_success_probability": round(min(probs), 3),
            "max_success_probability": round(max(probs), 3),
            "risk_distribution": risk_levels,
            "high_risk_tasks": [p.task_id for p in predictions if p.risk_level in ["high", "critical"]],
        }

    # ==================== 工人流失预警 ====================

    async def predict_worker_churn(
        self,
        worker_id: int,
        params: Optional[PredictionQueryParams] = None,
    ) -> WorkerChurnPrediction:
        """预测工人流失概率。"""
        # 获取工人信息
        worker_query = select(WorkerProfileDB).where(
            WorkerProfileDB.worker_id == worker_id
        )
        result = await self.db.execute(worker_query)
        worker = result.scalar_one_or_none()

        if not worker:
            raise ValueError(f"Worker {worker_id} not found")

        churn_prob, reasons, features = await self._calculate_churn_prob(worker)
        risk_level = self._classify_risk_level(churn_prob)
        retention_suggestions = self._generate_retention_suggestions(reasons, churn_prob)

        # 预测流失时间
        predicted_churn_date = None
        if churn_prob > 0.5:
            # 高风险：预测 7-30 天内可能流失
            days = int(30 * (1 - churn_prob))
            predicted_churn_date = datetime.now() + timedelta(days=max(7, days))

        return WorkerChurnPrediction(
            worker_id=worker_id,
            churn_probability=round(churn_prob, 3),
            risk_level=risk_level,
            predicted_churn_date=predicted_churn_date,
            confidence=min(0.85, 0.5 + len(features) * 0.05),
            predicted_value="churn" if churn_prob > 0.5 else "stay",
            churn_reasons=reasons,
            retention_suggestions=retention_suggestions,
            features=features,
        )

    async def predict_batch_worker_churn(
        self,
        params: PredictionQueryParams,
    ) -> WorkerChurnBatchPrediction:
        """批量预测工人流失风险。"""
        # 获取工人列表
        workers_query = select(WorkerProfileDB)

        if params.organization_id:
            # 如果有组织 ID，查询该组织相关的工人
            pass  # TODO: 实现组织过滤逻辑

        workers_query = workers_query.limit(params.limit)
        result = await self.db.execute(workers_query)
        workers = result.scalars().all()

        predictions = []
        high_risk = medium_risk = low_risk = 0

        for worker in workers:
            try:
                pred = await self.predict_worker_churn(worker.worker_id, params)
                predictions.append(pred)
                if pred.risk_level in ["high", "critical"]:
                    high_risk += 1
                elif pred.risk_level == "medium":
                    medium_risk += 1
                else:
                    low_risk += 1
            except Exception:
                continue

        return WorkerChurnBatchPrediction(
            predictions=predictions,
            high_risk_count=high_risk,
            medium_risk_count=medium_risk,
            low_risk_count=low_risk,
            summary={
                "total_workers": len(predictions),
                "churn_rate": round(high_risk / len(predictions), 3) if predictions else 0,
            },
        )

    async def _calculate_churn_prob(
        self,
        worker: WorkerProfileDB,
    ) -> Tuple[float, List[Dict[str, Any]], Dict[str, Any]]:
        """计算工人流失概率。"""
        features = {}
        reasons = []
        base_prob = 0.2  # 基础流失率

        # 1. 活跃度分析
        activity_factor = await self._analyze_worker_activity(worker.worker_id)
        features["activity_factor"] = activity_factor
        if activity_factor < 0.5:
            reasons.append({
                "factor": "low_activity",
                "impact": 0.2,
                "description": "工人近期活跃度低"
            })
            base_prob += 0.2

        # 2. 收入分析
        income_factor = await self._analyze_worker_income(worker.worker_id)
        features["income_factor"] = income_factor
        if income_factor < 0.6:
            reasons.append({
                "factor": "declining_income",
                "impact": 0.25,
                "description": "工人收入呈下降趋势"
            })
            base_prob += 0.25

        # 3. 任务满意度
        satisfaction_factor = self._analyze_satisfaction(worker)
        features["satisfaction_factor"] = satisfaction_factor
        if satisfaction_factor < 0.6:
            reasons.append({
                "factor": "low_satisfaction",
                "impact": 0.3,
                "description": "工人满意度低（评分/成功率下降）"
            })
            base_prob += 0.3

        # 4. 任务获取频率
        frequency_factor = await self._analyze_task_frequency(worker.worker_id)
        features["frequency_factor"] = frequency_factor
        if frequency_factor < 0.5:
            reasons.append({
                "factor": "task_shortage",
                "impact": 0.25,
                "description": "工人获得任务频率下降"
            })
            base_prob += 0.25

        return max(0.1, min(0.9, base_prob)), reasons, features

    async def _analyze_worker_activity(self, worker_id: int) -> float:
        """分析工人活跃度。"""
        # 查询最近 30 天和前 30 天的活动
        now = datetime.now()
        recent_30d = now - timedelta(days=30)
        prev_30d = recent_30d - timedelta(days=30)

        query = select(
            func.count(func.distinct(
                func.date(WorkerSubmissionDB.submitted_at)
            ))
        ).where(
            WorkerSubmissionDB.worker_id == worker_id
        )

        # 最近 30 天活跃天数
        recent_query = query.where(
            WorkerSubmissionDB.submitted_at >= recent_30d
        )
        result = await self.db.execute(recent_query)
        recent_days = result.scalar() or 0

        # 前 30 天活跃天数
        prev_query = query.where(
            WorkerSubmissionDB.submitted_at >= prev_30d,
            WorkerSubmissionDB.submitted_at < recent_30d
        )
        result = await self.db.execute(prev_query)
        prev_days = result.scalar() or 0

        if prev_days == 0:
            return 1.0 if recent_days > 0 else 0.5

        return min(1.5, recent_days / max(prev_days, 1))

    async def _analyze_worker_income(self, worker_id: int) -> float:
        """分析工人收入趋势。"""
        # 简化实现：查询任务完成情况
        now = datetime.now()
        recent_30d = now - timedelta(days=30)
        prev_30d = recent_30d - timedelta(days=30)

        query = select(
            func.count(TaskDB.id)
        ).where(
            TaskDB.accepted_by_worker_id == worker_id,
            TaskDB.status == "completed"
        )

        recent_query = query.where(TaskDB.completed_at >= recent_30d)
        result = await self.db.execute(recent_query)
        recent_count = result.scalar() or 0

        prev_query = query.where(
            TaskDB.completed_at >= prev_30d,
            TaskDB.completed_at < recent_30d
        )
        result = await self.db.execute(prev_query)
        prev_count = result.scalar() or 0

        if prev_count == 0:
            return 1.0 if recent_count > 0 else 0.5

        return min(1.5, recent_count / max(prev_count, 1))

    def _analyze_satisfaction(self, worker: WorkerProfileDB) -> float:
        """分析工人满意度。"""
        # 基于评分和成功率
        rating_score = (worker.average_rating or 4.0) / 5.0
        success_score = worker.success_rate or 0.8

        return 0.6 * rating_score + 0.4 * success_score

    async def _analyze_task_frequency(self, worker_id: int) -> float:
        """分析工人获得任务的频率。"""
        # 类似于活跃度分析，但关注被接受的任务
        now = datetime.now()
        recent_30d = now - timedelta(days=30)
        prev_30d = recent_30d - timedelta(days=30)

        query = select(
            func.count(TaskDB.id)
        ).where(
            TaskDB.accepted_by_worker_id == worker_id
        )

        recent_query = query.where(TaskDB.accepted_at >= recent_30d)
        result = await self.db.execute(recent_query)
        recent_count = result.scalar() or 0

        prev_query = query.where(
            TaskDB.accepted_at >= prev_30d,
            TaskDB.accepted_at < recent_30d
        )
        result = await self.db.execute(prev_query)
        prev_count = result.scalar() or 0

        if prev_count == 0:
            return 1.0 if recent_count > 0 else 0.5

        return min(1.5, recent_count / max(prev_count, 1))

    def _generate_retention_suggestions(
        self,
        reasons: List[Dict[str, Any]],
        churn_prob: float,
    ) -> List[str]:
        """生成保留建议。"""
        suggestions = []

        for reason in reasons:
            if reason["factor"] == "low_activity":
                suggestions.append("发送个性化任务推荐，提高工人参与度")
                suggestions.append("提供活跃度奖励或徽章激励")
            elif reason["factor"] == "declining_income":
                suggestions.append("优先推荐高价值任务")
                suggestions.append("提供技能培训，提升工人接单能力")
            elif reason["factor"] == "low_satisfaction":
                suggestions.append("进行满意度调研，了解具体问题")
                suggestions.append("提供专属客服支持")
            elif reason["factor"] == "task_shortage":
                suggestions.append("优化任务匹配算法，提高匹配精准度")
                suggestions.append("在新任务发布时优先通知")

        if churn_prob > 0.7:
            suggestions.append("建议进行一对一挽留沟通")
            suggestions.append("考虑提供专属奖励或补贴")

        return suggestions

    # ==================== 收入预测 ====================

    async def predict_revenue(
        self,
        params: PredictionQueryParams,
    ) -> RevenuePrediction:
        """预测未来收入。"""
        forecast_period = params.forecast_period or "30d"

        # 解析预测周期
        days = self._parse_forecast_period(forecast_period)

        # 获取历史收入数据
        historical_data = await self._get_historical_revenue(params, days)

        # 生成预测
        forecast = await self._generate_revenue_forecast(historical_data, days)

        # 计算汇总数据
        total_revenue = sum(f.predicted_revenue for f in forecast)
        growth_rate = self._calculate_growth_rate(historical_data, forecast)

        # 分析关键驱动因素
        key_drivers = await self._analyze_revenue_drivers(params)

        # 生成风险提示
        risk_warnings = self._generate_revenue_warnings(forecast, growth_rate)

        return RevenuePrediction(
            forecast_period=forecast_period,
            forecast=forecast,
            total_predicted_revenue=round(total_revenue, 2),
            growth_rate=round(growth_rate, 4),
            confidence=0.75,  # 简化
            predicted_value=total_revenue,
            key_drivers=key_drivers,
            risk_warnings=risk_warnings,
        )

    def _parse_forecast_period(self, period: str) -> int:
        """解析预测周期。"""
        if period.endswith("d"):
            return int(period[:-1])
        elif period.endswith("w"):
            return int(period[:-1]) * 7
        elif period.endswith("m"):
            return int(period[:-1]) * 30
        return 30

    async def _get_historical_revenue(
        self,
        params: PredictionQueryParams,
        lookback_days: int,
    ) -> List[Dict[str, Any]]:
        """获取历史收入数据。"""
        end_date = params.end_date or datetime.now()
        start_date = params.start_date or (end_date - timedelta(days=lookback_days))

        # 查询每日收入
        query = select(
            func.date(PaymentTransactionDB.transaction_date).label("date"),
            func.sum(PaymentTransactionDB.amount).label("revenue")
        ).where(
            PaymentTransactionDB.transaction_type == "platform_fee",
            PaymentTransactionDB.transaction_date >= start_date,
            PaymentTransactionDB.transaction_date <= end_date
        ).group_by(
            func.date(PaymentTransactionDB.transaction_date)
        ).order_by(
            func.date(PaymentTransactionDB.transaction_date)
        )

        result = await self.db.execute(query)
        rows = result.fetchall()

        return [
            {"date": str(row.date), "revenue": float(row.revenue) if row.revenue else 0}
            for row in rows
        ]

    async def _generate_revenue_forecast(
        self,
        historical_data: List[Dict[str, Any]],
        forecast_days: int,
    ) -> List[RevenueForecast]:
        """生成收入预测。"""
        if not historical_data:
            # 如果没有历史数据，返回空预测
            return []

        # 简单移动平均预测
        revenues = [d["revenue"] for d in historical_data[-14:]]  # 取最近 14 天
        avg_revenue = sum(revenues) / len(revenues) if revenues else 0

        # 计算波动率
        if len(revenues) > 1:
            variance = sum((r - avg_revenue) ** 2 for r in revenues) / len(revenues)
            std_dev = variance ** 0.5
        else:
            std_dev = avg_revenue * 0.2

        forecast = []
        last_date = datetime.now()

        for i in range(forecast_days):
            forecast_date = last_date + timedelta(days=i + 1)

            # 简单预测：平均值 + 轻微增长趋势
            growth_factor = 1 + (i * 0.001)  # 每天 0.1% 增长
            predicted = avg_revenue * growth_factor

            # 置信区间随时间扩大
            confidence_width = std_dev * (1 + i * 0.1)

            forecast.append(
                RevenueForecast(
                    date=forecast_date.strftime("%Y-%m-%d"),
                    predicted_revenue=round(predicted, 2),
                    lower_bound=round(max(0, predicted - 1.96 * confidence_width), 2),
                    upper_bound=round(predicted + 1.96 * confidence_width, 2),
                    predicted_gmv=round(predicted * 10, 2),  # 假设平台费率 10%
                    predicted_tasks=int(predicted / 5),  # 假设平均每任务$5
                    predicted_active_workers=int(predicted / 2),  # 假设每工人贡献$2
                )
            )

        return forecast

    def _calculate_growth_rate(
        self,
        historical_data: List[Dict[str, Any]],
        forecast: List[RevenueForecast],
    ) -> float:
        """计算增长率。"""
        if not historical_data or not forecast:
            return 0.0

        # 比较预测期和基期
        base_avg = sum(d["revenue"] for d in historical_data[-7:]) / 7
        forecast_avg = sum(f.predicted_revenue for f in forecast[:7]) / 7

        if base_avg == 0:
            return 0.0

        return (forecast_avg - base_avg) / base_avg

    async def _analyze_revenue_drivers(
        self,
        params: PredictionQueryParams,
    ) -> List[Dict[str, Any]]:
        """分析收入驱动因素。"""
        drivers = []

        # 1. 任务量驱动
        task_query = select(func.count(TaskDB.id)).where(
            TaskDB.created_at >= datetime.now() - timedelta(days=30)
        )
        result = await self.db.execute(task_query)
        task_count = result.scalar() or 0
        drivers.append({
            "driver": "task_volume",
            "value": task_count,
            "impact": "high",
            "description": f"月任务发布量：{task_count}"
        })

        # 2. 活跃工人驱动
        worker_query = select(
            func.count(func.distinct(WorkerSubmissionDB.worker_id))
        ).where(
            WorkerSubmissionDB.submitted_at >= datetime.now() - timedelta(days=30)
        )
        result = await self.db.execute(worker_query)
        worker_count = result.scalar() or 0
        drivers.append({
            "driver": "active_workers",
            "value": worker_count,
            "impact": "high",
            "description": f"月活跃工人：{worker_count}"
        })

        # 3. 平均客单价
        avg_reward_query = select(func.avg(TaskDB.reward_amount))
        result = await self.db.execute(avg_reward_query)
        avg_reward = result.scalar() or 0
        drivers.append({
            "driver": "avg_task_value",
            "value": round(avg_reward, 2),
            "impact": "medium",
            "description": f"平均任务报酬：${avg_reward:.2f}"
        })

        return drivers

    def _generate_revenue_warnings(
        self,
        forecast: List[RevenueForecast],
        growth_rate: float,
    ) -> List[str]:
        """生成收入预警。"""
        warnings = []

        if growth_rate < -0.1:
            warnings.append("收入呈现下降趋势，需关注业务健康度")

        if forecast:
            # 检查预测波动
            revenues = [f.predicted_revenue for f in forecast]
            max_rev = max(revenues)
            min_rev = min(revenues)
            if max_rev > 0 and (max_rev - min_rev) / max_rev > 0.3:
                warnings.append("预测收入波动较大，存在不确定性风险")

        # 检查置信区间
        wide_intervals = [
            f for f in forecast
            if f.upper_bound - f.lower_bound > f.predicted_revenue * 0.5
        ]
        if len(wide_intervals) > len(forecast) * 0.3:
            warnings.append("预测置信区间较宽，建议谨慎参考")

        return warnings

    # ==================== 异常检测 ====================

    async def detect_anomalies(
        self,
        params: Optional[AnalyticsQueryParams] = None,
    ) -> AnomalyDetectionReport:
        """检测系统异常。"""
        anomalies = []

        # 1. 检测任务创建量异常
        task_anomalies = await self._detect_task_anomalies(params)
        anomalies.extend(task_anomalies)

        # 2. 检测工人活跃度异常
        worker_anomalies = await self._detect_worker_anomalies(params)
        anomalies.extend(worker_anomalies)

        # 3. 检测支付异常
        payment_anomalies = await self._detect_payment_anomalies(params)
        anomalies.extend(payment_anomalies)

        # 4. 检测质量异常
        quality_anomalies = await self._detect_quality_anomalies(params)
        anomalies.extend(quality_anomalies)

        # 统计
        critical_count = sum(1 for a in anomalies if a.severity == "critical")
        high_count = sum(1 for a in anomalies if a.severity == "high")

        # 判断趋势
        if critical_count > 0:
            trend = "worsening"
        elif len(anomalies) <= 2:
            trend = "stable"
        else:
            trend = "improving"

        return AnomalyDetectionReport(
            detection_period="30d",
            anomalies=anomalies,
            total_anomalies=len(anomalies),
            critical_count=critical_count,
            high_count=high_count,
            trend=trend,
        )

    async def _detect_task_anomalies(
        self,
        params: Optional[AnalyticsQueryParams],
    ) -> List[AnomalyDetection]:
        """检测任务相关异常。"""
        anomalies = []

        # 检测任务创建量骤降
        now = datetime.now()
        recent_7d = now - timedelta(days=7)
        prev_7d = recent_7d - timedelta(days=7)

        query = select(
            func.count(TaskDB.id)
        ).where(
            TaskDB.created_at >= recent_7d
        )
        result = await self.db.execute(query)
        recent_count = result.scalar() or 0

        prev_query = select(
            func.count(TaskDB.id)
        ).where(
            TaskDB.created_at >= prev_7d,
            TaskDB.created_at < recent_7d
        )
        result = await self.db.execute(prev_query)
        prev_count = result.scalar() or 0

        if prev_count > 0:
            change_rate = (recent_count - prev_count) / prev_count
            if change_rate < -0.5:  # 下降超过 50%
                anomalies.append(
                    AnomalyDetection(
                        anomaly_type="task_volume_drop",
                        severity="high",
                        metric_name="tasks_created",
                        expected_value=prev_count,
                        actual_value=recent_count,
                        deviation_percent=abs(change_rate) * 100,
                        possible_causes=[
                            "市场需求下降",
                            "竞争对手行动",
                            "平台技术问题"
                        ],
                        recommended_actions=[
                            "调研雇主需求",
                            "检查平台可用性",
                            "分析市场趋势"
                        ]
                    )
                )

        return anomalies

    async def _detect_worker_anomalies(
        self,
        params: Optional[AnalyticsQueryParams],
    ) -> List[AnomalyDetection]:
        """检测工人相关异常。"""
        anomalies = []

        # 检测活跃工人骤降
        now = datetime.now()
        recent_7d = now - timedelta(days=7)
        prev_7d = recent_7d - timedelta(days=7)

        query = select(
            func.count(func.distinct(WorkerSubmissionDB.worker_id))
        ).where(
            WorkerSubmissionDB.submitted_at >= recent_7d
        )
        result = await self.db.execute(query)
        recent_count = result.scalar() or 0

        prev_query = select(
            func.count(func.distinct(WorkerSubmissionDB.worker_id))
        ).where(
            WorkerSubmissionDB.submitted_at >= prev_7d,
            WorkerSubmissionDB.submitted_at < recent_7d
        )
        result = await self.db.execute(prev_query)
        prev_count = result.scalar() or 0

        if prev_count > 0:
            change_rate = (recent_count - prev_count) / prev_count
            if change_rate < -0.3:  # 下降超过 30%
                anomalies.append(
                    AnomalyDetection(
                        anomaly_type="worker_activity_drop",
                        severity="critical",
                        metric_name="active_workers",
                        expected_value=prev_count,
                        actual_value=recent_count,
                        deviation_percent=abs(change_rate) * 100,
                        possible_causes=[
                            "工人流失",
                            "季节性因素",
                            "激励政策变化"
                        ],
                        recommended_actions=[
                            "分析工人留存数据",
                            "检查激励政策",
                            "开展工人满意度调研"
                        ]
                    )
                )

        return anomalies

    async def _detect_payment_anomalies(
        self,
        params: Optional[AnalyticsQueryParams],
    ) -> List[AnomalyDetection]:
        """检测支付相关异常。"""
        anomalies = []

        # 检测异常大额支付
        threshold = 10000  # 大额阈值
        query = select(PaymentTransactionDB).where(
            PaymentTransactionDB.amount >= threshold,
            PaymentTransactionDB.transaction_date >= datetime.now() - timedelta(days=7)
        )
        result = await self.db.execute(query)
        large_payments = result.scalars().all()

        if len(large_payments) > 5:  # 一周内超过 5 笔大额
            anomalies.append(
                AnomalyDetection(
                    anomaly_type="unusual_large_payments",
                    severity="medium",
                    metric_name="large_payment_count",
                    expected_value=5,
                    actual_value=len(large_payments),
                    deviation_percent=(len(large_payments) - 5) / 5 * 100,
                    affected_entities=[
                        {"transaction_id": p.id, "amount": p.amount}
                        for p in large_payments[:5]
                    ],
                    possible_causes=[
                        "企业客户批量结算",
                        "异常交易行为"
                    ],
                    recommended_actions=[
                        "核实大额交易背景",
                        "加强反洗钱监控"
                    ]
                )
            )

        return anomalies

    async def _detect_quality_anomalies(
        self,
        params: Optional[AnalyticsQueryParams],
    ) -> List[AnomalyDetection]:
        """检测质量相关异常。"""
        anomalies = []

        # 检测验收通过率骤降
        now = datetime.now()
        recent_7d = now - timedelta(days=7)
        prev_7d = recent_7d - timedelta(days=7)

        # 最近 7 天通过率
        recent_query = select(
            func.count(TaskDB.id),
            func.sum(
                func.case((TaskDB.status == "completed", 1), else_=0)
            )
        ).where(
            TaskDB.completed_at >= recent_7d
        )
        result = await self.db.execute(recent_query)
        recent_row = result.first()
        recent_rate = (recent_row[1] / recent_row[0]) if recent_row and recent_row[0] > 0 else 0

        # 前 7 天通过率
        prev_query = select(
            func.count(TaskDB.id),
            func.sum(
                func.case((TaskDB.status == "completed", 1), else_=0)
            )
        ).where(
            TaskDB.completed_at >= prev_7d,
            TaskDB.completed_at < recent_7d
        )
        result = await self.db.execute(prev_query)
        prev_row = result.first()
        prev_rate = (prev_row[1] / prev_row[0]) if prev_row and prev_row[0] > 0 else 0

        if prev_rate > 0:
            change = prev_rate - recent_rate
            if change > 0.2:  # 通过率下降超过 20%
                anomalies.append(
                    AnomalyDetection(
                        anomaly_type="quality_drop",
                        severity="critical",
                        metric_name="completion_rate",
                        expected_value=prev_rate,
                        actual_value=recent_rate,
                        deviation_percent=change * 100,
                        possible_causes=[
                            "工人质量下降",
                            "验收标准过于严格",
                            "新工人培训不足"
                        ],
                        recommended_actions=[
                            "分析拒绝原因分布",
                            "检查黄金标准测试覆盖率",
                            "加强工人培训"
                        ]
                    )
                )

        return anomalies

    # ==================== 综合分析仪表板 ====================

    async def get_advanced_analytics_dashboard(
        self,
        params: Optional[PredictionQueryParams] = None,
    ) -> AdvancedAnalyticsDashboard:
        """获取高级分析仪表板数据。"""
        if params is None:
            params = PredictionQueryParams()

        # 获取各项预测数据
        task_predictions = await self.predict_batch_task_success(params)
        worker_predictions = await self.predict_batch_worker_churn(params)
        revenue_prediction = await self.predict_revenue(params)
        anomaly_report = await self.detect_anomalies(params)

        # 计算核心指标
        task_success_rate = (
            task_predictions.summary.get("avg_success_probability", 0)
            if task_predictions.predictions else 0.8
        )
        worker_churn_rate = (
            worker_predictions.high_risk_count / len(worker_predictions.predictions)
            if worker_predictions.predictions else 0.1
        )
        revenue_growth_rate = revenue_prediction.growth_rate if revenue_prediction.forecast else 0

        return AdvancedAnalyticsDashboard(
            task_success_rate=round(task_success_rate, 3),
            worker_churn_rate=round(worker_churn_rate, 3),
            revenue_growth_rate=round(revenue_growth_rate, 4),
            anomaly_count=anomaly_report.total_anomalies,
            task_predictions=task_predictions,
            worker_predictions=worker_predictions,
            revenue_prediction=revenue_prediction,
            anomaly_report=anomaly_report,
        )


# 单例服务实例
advanced_analytics_service: Optional[AdvancedAnalyticsService] = None


def get_analytics_service(db: AsyncSession) -> AdvancedAnalyticsService:
    """获取分析服务实例。"""
    return AdvancedAnalyticsService(db)
