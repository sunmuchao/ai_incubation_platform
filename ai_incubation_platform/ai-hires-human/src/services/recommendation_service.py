"""
智能任务推荐服务 - 基于工人画像和任务特征的匹配推荐系统。

功能：
1. 基于内容的推荐（技能匹配）
2. 基于偏好的推荐（交互类型、报酬、时长）
3. 基于行为的推荐（活跃时段、历史行为）
4. 混合排序算法
5. v1.16.0 新增：双向推荐、历史表现加权、薪资匹配
"""
from __future__ import annotations

import math
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from models.task import Task, TaskStatus
from models.worker_profile import WorkerProfile, TaskRecommendation, WorkerRecommendation

import logging

logger = logging.getLogger(__name__)


class RecommendationService:
    """
    智能任务推荐服务。

    推荐算法说明：
    1. 技能匹配分数 (0-40 分): 基于工人技能与任务需求的匹配度
    2. 偏好匹配分数 (0-30 分): 基于工人偏好的匹配度
    3. 质量匹配分数 (0-20 分): 基于工人质量等级与任务要求的匹配
    4. 时效匹配分数 (0-10 分): 基于活跃时段和任务紧急度

    v1.16.0 新增：
    5. 历史表现加权：基于工人历史任务表现调整推荐分数
    6. 薪资期望匹配：基于工人收入预期和任务报酬匹配度
    7. 双向推荐：支持为工人推荐任务和为任务推荐工人

    总分 100 分，按分数排序推荐
    """

    def __init__(self) -> None:
        # 权重配置
        self.SKILL_WEIGHT = 0.40  # 技能匹配权重
        self.PREFERENCE_WEIGHT = 0.30  # 偏好匹配权重
        self.QUALITY_WEIGHT = 0.20  # 质量匹配权重
        self.TIMING_WEIGHT = 0.10  # 时效匹配权重

        # v1.16.0 新增：历史表现加权系数
        self.HISTORY_WEIGHT = 0.15  # 历史表现权重
        self.SALARY_MATCH_WEIGHT = 0.10  # 薪资匹配权重

    def _calculate_skill_match_score(
        self,
        worker: WorkerProfile,
        task: Task
    ) -> Tuple[float, List[str]]:
        """
        计算技能匹配分数 (0-40 分)。
        返回 (分数，匹配原因列表)
        """
        reasons = []
        score = 0.0

        worker_skills = set(k.lower() for k in worker.skills.keys())
        worker_verified = set(s.lower() for s in worker.verified_skills)
        task_required_skills = set(k.lower() for k in task.required_skills.keys())

        if not task_required_skills:
            # 任务无技能要求，给基础分
            score = 20.0
            reasons.append("任务无特殊技能要求")
            return score, reasons

        # 计算匹配的技能数量
        matched_skills = worker_skills & task_required_skills
        verified_matched = worker_verified & task_required_skills

        skill_match_rate = len(matched_skills) / len(task_required_skills) if task_required_skills else 0
        verified_bonus = len(verified_matched) * 5  # 每个验证技能额外加 5 分

        # 技能匹配分数 = 基础匹配 (40 分 * 匹配率) + 验证技能加分
        score = min(40.0, 40.0 * skill_match_rate + verified_bonus)

        if matched_skills:
            reasons.append(f"匹配技能：{', '.join(matched_skills)}")
        if verified_matched:
            reasons.append(f"已验证技能：{', '.join(verified_matched)}")

        # 技能缺口提示
        missing_skills = task_required_skills - worker_skills
        if missing_skills and len(missing_skills) <= 2:
            reasons.append(f"建议学习：{', '.join(missing_skills)}")

        return max(0, score), reasons

    def _calculate_preference_match_score(
        self,
        worker: WorkerProfile,
        task: Task
    ) -> Tuple[float, List[str]]:
        """
        计算偏好匹配分数 (0-30 分)。
        返回 (分数，匹配原因列表)
        """
        reasons = []
        score = 0.0

        # 1. 交互类型偏好匹配 (0-10 分)
        if worker.preferred_interaction_types:
            if task.interaction_type.value in worker.preferred_interaction_types:
                score += 10.0
                reasons.append(f"偏好的交互类型：{task.interaction_type.value}")
        else:
            # 无偏好设置，给平均分
            score += 5.0

        # 2. 报酬偏好匹配 (0-10 分)
        if worker.min_reward_preference > 0:
            if task.reward_amount >= worker.min_reward_preference:
                score += 10.0
                reasons.append(f"报酬符合预期 (¥{task.reward_amount})")
            else:
                # 报酬低于预期，按比例给分
                ratio = task.reward_amount / worker.min_reward_preference
                score += 10.0 * ratio
        else:
            # 无报酬偏好，给基础分
            score += 5.0

        # 3. 任务时长匹配 (0-10 分)
        if worker.max_task_duration_hours and task.deadline:
            hours_until_deadline = (task.deadline - datetime.now()).total_seconds() / 3600
            if hours_until_deadline <= worker.max_task_duration_hours:
                score += 10.0
                reasons.append(f"任务时长在偏好范围内")
        else:
            score += 5.0

        return min(30.0, score), reasons

    def _calculate_quality_match_score(
        self,
        worker: WorkerProfile,
        task: Task
    ) -> Tuple[float, List[str]]:
        """
        计算质量匹配分数 (0-20 分)。
        返回 (分数，匹配原因列表)
        """
        reasons = []
        score = 0.0

        # 1. 可信度评分映射 (0-10 分)
        score += worker.trust_score * 10.0
        if worker.trust_score >= 0.9:
            reasons.append(f"高可信度工人 ({worker.trust_score:.1%})")
        elif worker.trust_score >= 0.7:
            reasons.append(f"良好可信度 ({worker.trust_score:.1%})")

        # 2. 质量等级映射 (0-5 分)
        tier_scores = {
            "platinum": 5.0,
            "gold": 4.0,
            "silver": 3.0,
            "bronze": 2.0
        }
        tier_score = tier_scores.get(worker.quality_tier, 1.0)
        score += tier_score
        reasons.append(f"质量等级：{worker.quality_tier}")

        # 3. 成功率映射 (0-5 分)
        score += worker.success_rate * 5.0
        if worker.success_rate >= 0.95:
            reasons.append(f"优秀成功率 ({worker.success_rate:.1%})")

        return min(20.0, score), reasons

    def _calculate_timing_match_score(
        self,
        worker: WorkerProfile,
        task: Task
    ) -> Tuple[float, List[str]]:
        """
        计算时效匹配分数 (0-10 分)。
        返回 (分数，匹配原因列表)
        """
        reasons = []
        score = 0.0

        # 1. 活跃时段匹配 (0-5 分)
        current_hour = datetime.now().hour
        if worker.active_hours and current_hour in worker.active_hours:
            score += 5.0
            reasons.append("当前为活跃时段")
        else:
            score += 2.5

        # 2. 任务紧急度匹配 (0-5 分)
        if task.deadline:
            hours_until_deadline = (task.deadline - datetime.now()).total_seconds() / 3600
            if hours_until_deadline < 24:
                # 紧急任务，优先推荐给当前活跃的工人
                score += 5.0
                reasons.append("紧急任务优先")
            elif hours_until_deadline < 72:
                score += 3.0
            else:
                score += 1.0
        else:
            score += 2.5

        return min(10.0, score), reasons

    def _calculate_historical_performance_score(
        self,
        worker: WorkerProfile,
        task: Task
    ) -> Tuple[float, List[str]]:
        """
        v1.16.0 新增：计算历史表现分数 (0-15 分)。
        基于工人历史任务表现进行评估。
        返回 (分数，匹配原因列表)
        """
        reasons = []
        score = 0.0

        # 1. 完成任务数 (0-5 分)
        if worker.completed_tasks >= 100:
            score += 5.0
            reasons.append(f"经验丰富 ({worker.completed_tasks} 个完成任务)")
        elif worker.completed_tasks >= 50:
            score += 4.0
            reasons.append(f"熟练工人 ({worker.completed_tasks} 个完成任务)")
        elif worker.completed_tasks >= 20:
            score += 3.0
            reasons.append(f"有一定经验 ({worker.completed_tasks} 个完成任务)")
        elif worker.completed_tasks >= 5:
            score += 2.0
            reasons.append(f"新手工人 ({worker.completed_tasks} 个完成任务)")
        else:
            score += 1.0
            reasons.append("新注册工人")

        # 2. 成功率 (0-5 分)
        if worker.success_rate >= 0.98:
            score += 5.0
            reasons.append(f"优秀成功率 ({worker.success_rate:.1%})")
        elif worker.success_rate >= 0.95:
            score += 4.0
            reasons.append(f"高成功率 ({worker.success_rate:.1%})")
        elif worker.success_rate >= 0.90:
            score += 3.0
            reasons.append(f"良好成功率 ({worker.success_rate:.1%})")
        elif worker.success_rate >= 0.80:
            score += 2.0
            reasons.append(f"一般成功率 ({worker.success_rate:.1%})")
        else:
            score += 1.0

        # 3. 平均评分 (0-5 分)
        if worker.average_rating >= 4.8:
            score += 5.0
            reasons.append(f"接近满分评价 ({worker.average_rating:.1f}/5.0)")
        elif worker.average_rating >= 4.5:
            score += 4.0
            reasons.append(f"高评价 ({worker.average_rating:.1f}/5.0)")
        elif worker.average_rating >= 4.0:
            score += 3.0
            reasons.append(f"良好评价 ({worker.average_rating:.1f}/5.0)")
        elif worker.average_rating >= 3.5:
            score += 2.0
            reasons.append(f"一般评价 ({worker.average_rating:.1f}/5.0)")
        else:
            score += 1.0

        return min(15.0, score), reasons

    def _calculate_salary_match_score(
        self,
        worker: WorkerProfile,
        task: Task
    ) -> Tuple[float, List[str]]:
        """
        v1.16.0 新增：计算薪资期望匹配分数 (0-10 分)。
        基于工人最低报酬偏好和任务报酬进行匹配。
        返回 (分数，匹配原因列表)
        """
        reasons = []
        score = 0.0

        # 1. 报酬绝对值匹配 (0-5 分)
        if worker.min_reward_preference > 0:
            if task.reward_amount >= worker.min_reward_preference:
                # 报酬达到或超过预期
                ratio = task.reward_amount / worker.min_reward_preference
                if ratio >= 1.5:
                    score += 5.0
                    reasons.append(f"报酬远超预期 (¥{task.reward_amount} vs 期望¥{worker.min_reward_preference})")
                elif ratio >= 1.2:
                    score += 4.0
                    reasons.append(f"报酬高于预期 (¥{task.reward_amount})")
                else:
                    score += 3.0
                    reasons.append(f"报酬符合预期 (¥{task.reward_amount})")
            else:
                # 报酬低于预期，按比例给分
                ratio = task.reward_amount / worker.min_reward_preference
                if ratio >= 0.8:
                    score += 2.0
                    reasons.append(f"报酬略低于预期 (¥{task.reward_amount})")
                else:
                    score += 1.0
                    reasons.append(f"报酬明显低于预期 (¥{task.reward_amount})")
        else:
            # 无明确偏好，给基础分
            score += 3.0

        # 2. 收入水平匹配 (0-5 分)
        # 基于工人历史总收入判断其对报酬的敏感度
        if worker.total_earnings > 10000:
            # 高收入工人，可能对低价任务不敏感
            if task.reward_amount >= 500:
                score += 5.0
                reasons.append("高价值任务匹配高收入工人")
            elif task.reward_amount >= 100:
                score += 3.0
            else:
                score += 2.0
                reasons.append("低价值任务可能吸引力不足")
        elif worker.total_earnings > 1000:
            # 中等收入工人
            if task.reward_amount >= 200:
                score += 5.0
            elif task.reward_amount >= 50:
                score += 4.0
            else:
                score += 3.0
        else:
            # 低收入/新工人，对报酬敏感度较低
            score += 4.0
            reasons.append("新工人对任务报酬敏感度较低")

        return min(10.0, score), reasons

    def calculate_match_score(
        self,
        worker: WorkerProfile,
        task: Task
    ) -> Tuple[float, Dict[str, float], List[str]]:
        """
        计算综合匹配分数。
        返回 (总分，各维度分数，匹配原因列表)

        v1.16.0 更新：新增历史表现和薪资匹配维度
        """
        skill_score, skill_reasons = self._calculate_skill_match_score(worker, task)
        pref_score, pref_reasons = self._calculate_preference_match_score(worker, task)
        quality_score, quality_reasons = self._calculate_quality_match_score(worker, task)
        timing_score, timing_reasons = self._calculate_timing_match_score(worker, task)
        history_score, history_reasons = self._calculate_historical_performance_score(worker, task)
        salary_score, salary_reasons = self._calculate_salary_match_score(worker, task)

        # 加权总分 (v1.16.0 更新权重配置)
        total_score = (
            skill_score * self.SKILL_WEIGHT +
            pref_score * self.PREFERENCE_WEIGHT +
            quality_score * self.QUALITY_WEIGHT +
            timing_score * self.TIMING_WEIGHT +
            history_score * (self.HISTORY_WEIGHT / 15.0) * 10.0 +  # 归一化到 10 分制
            salary_score * (self.SALARY_MATCH_WEIGHT / 10.0) * 10.0  # 归一化到 10 分制
        )

        dimension_scores = {
            "skill": skill_score,
            "preference": pref_score,
            "quality": quality_score,
            "timing": timing_score,
            "history": history_score,
            "salary": salary_score
        }

        all_reasons = skill_reasons + pref_reasons + quality_reasons + timing_reasons + history_reasons + salary_reasons

        return total_score, dimension_scores, all_reasons

    def recommend_tasks_for_worker(
        self,
        worker: WorkerProfile,
        available_tasks: List[Task],
        limit: int = 10
    ) -> List[TaskRecommendation]:
        """
        为工人推荐任务。
        """
        recommendations = []

        for task in available_tasks:
            if task.status != TaskStatus.PUBLISHED:
                continue

            # 跳过工人已接的任务
            if task.worker_id == worker.worker_id:
                continue

            score, dimension_scores, reasons = self.calculate_match_score(worker, task)

            # 只推荐匹配度>20 分的任务
            if score >= 20.0:
                recommendations.append(TaskRecommendation(
                    task_id=task.id,
                    title=task.title,
                    reward_amount=task.reward_amount,
                    interaction_type=task.interaction_type.value,
                    match_score=round(score, 2),
                    match_reasons=reasons[:5]  # 最多显示 5 个原因
                ))

        # 按匹配分数排序
        recommendations.sort(key=lambda r: r.match_score, reverse=True)

        return recommendations[:limit]

    def get_recommendation_explanation(
        self,
        worker: WorkerProfile,
        task: Task
    ) -> str:
        """
        获取推荐解释文本。
        """
        score, _, reasons = self.calculate_match_score(worker, task)

        if score >= 80:
            level = "强烈推荐"
        elif score >= 60:
            level = "推荐"
        elif score >= 40:
            level = "可以考虑"
        else:
            level = "匹配度较低"

        reason_str = "; ".join(reasons[:3])
        return f"{level} (匹配分{score:.1f}): {reason_str}"

    def update_quality_tier(self, worker: WorkerProfile) -> str:
        """
        根据工人表现更新质量等级。
        返回更新后的等级
        """
        # 基于可信度、成功率、黄金标准通过率计算
        composite_score = (
            worker.trust_score * 0.4 +
            worker.success_rate * 0.3 +
            (worker.gold_standard_tests_passed / max(1, worker.gold_standard_tests_total)) * 0.3
        )

        if composite_score >= 0.95:
            worker.quality_tier = "platinum"
        elif composite_score >= 0.85:
            worker.quality_tier = "gold"
        elif composite_score >= 0.70:
            worker.quality_tier = "silver"
        else:
            worker.quality_tier = "bronze"

        return worker.quality_tier

    def recommend_workers_for_task(
        self,
        task: Task,
        available_workers: List[WorkerProfile],
        limit: int = 10
    ) -> List[WorkerRecommendation]:
        """
        v1.16.0 新增：为任务推荐合适的工人。

        双向推荐算法：
        1. 技能匹配：工人技能与任务需求的匹配度
        2. 质量匹配：工人质量等级与任务要求的匹配
        3. 历史表现：基于工人历史任务表现
        4. 薪资匹配：工人期望报酬与任务报酬的匹配
        5. 可用性：工人当前是否可接任务

        返回匹配度>20 分的工人，按匹配分数降序排列
        """
        recommendations = []

        for worker in available_workers:
            score, dimension_scores, reasons = self.calculate_match_score(worker, task)

            # 只推荐匹配度>20 分的工人
            if score >= 20.0:
                # 估算报酬范围
                if worker.total_earnings > 10000:
                    reward_range = f"¥{int(task.reward_amount * 0.8)}-¥{int(task.reward_amount * 1.2)}"
                elif worker.total_earnings > 1000:
                    reward_range = f"¥{int(task.reward_amount * 0.9)}-¥{int(task.reward_amount * 1.1)}"
                else:
                    reward_range = f"¥{int(task.reward_amount * 0.95)}-¥{int(task.reward_amount * 1.05)}"

                recommendations.append(WorkerRecommendation(
                    worker_id=worker.worker_id,
                    name=worker.name,
                    skills=worker.skills,
                    trust_score=worker.trust_score,
                    success_rate=worker.success_rate,
                    quality_tier=worker.quality_tier,
                    completed_tasks=worker.completed_tasks,
                    average_rating=worker.average_rating,
                    match_score=round(score, 2),
                    match_reasons=reasons[:5],  # 最多显示 5 个原因
                    estimated_reward_range=reward_range
                ))

        # 按匹配分数排序
        recommendations.sort(key=lambda r: r.match_score, reverse=True)

        return recommendations[:limit]

    def get_detailed_recommendation_explanation(
        self,
        worker: WorkerProfile,
        task: Task
    ) -> Dict:
        """
        v1.16.0 新增：获取详细的推荐解释报告。

        返回：
        - overall_score: 综合匹配分数
        - dimension_scores: 各维度分数
        - match_reasons: 匹配原因列表
        - recommendation_level: 推荐等级
        - skill_match_details: 技能匹配详情
        - historical_performance_details: 历史表现详情
        """
        score, dimension_scores, reasons = self.calculate_match_score(worker, task)

        # 确定推荐等级
        if score >= 80:
            level = "强烈推荐"
        elif score >= 60:
            level = "推荐"
        elif score >= 40:
            level = "可以考虑"
        else:
            level = "匹配度较低"

        # 技能匹配详情
        skill_match_details = {
            "worker_skills": list(worker.skills.keys()),
            "required_skills": list(task.required_skills.keys()),
            "matched_skills": list(set(worker.skills.keys()) & set(task.required_skills.keys())),
            "verified_skills": worker.verified_skills,
            "match_rate": len(set(worker.skills.keys()) & set(task.required_skills.keys())) / max(1, len(task.required_skills.keys()))
        }

        # 历史表现详情
        historical_performance_details = {
            "completed_tasks": worker.completed_tasks,
            "success_rate": worker.success_rate,
            "average_rating": worker.average_rating,
            "trust_score": worker.trust_score,
            "quality_tier": worker.quality_tier,
            "gold_standard_passed": worker.gold_standard_tests_passed,
            "gold_standard_total": worker.gold_standard_tests_total
        }

        return {
            "overall_score": round(score, 2),
            "dimension_scores": {k: round(v, 2) for k, v in dimension_scores.items()},
            "match_reasons": reasons,
            "recommendation_level": level,
            "skill_match_details": skill_match_details,
            "historical_performance_details": historical_performance_details
        }


# 全局服务实例
recommendation_service = RecommendationService()
