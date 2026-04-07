"""
P13 培训效果评估增强 - 服务层

v13 新增功能服务:
- 培训前后技能对比 (Pre/Post Assessment Comparison)
- 培训 ROI 计算 (Return on Investment Calculation)
- 学习路径推荐 (Learning Path Recommendation)
- 培训效果追踪 (Training Impact Tracking)
- 技能认证集成 (Certification Integration)
"""
import math
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import uuid

from models.p13_models import (
    SkillAssessment, AssessmentType, SkillLevel,
    TrainingROI, ROIStatus,
    LearningPath, LearningPathItem, LearningPathStatus, PathRecommendationReason,
    TrainingImpactTracker,
    CertificationIntegration,
    TrainingEffectivenessReport,
    p13_storage
)


class TrainingEffectivenessV2Service:
    """
    培训效果评估增强服务 v2

    在 P7 训练效果评估基础上，增强以下功能:
    1. 培训前后技能对比
    2. 培训 ROI 计算
    3. 学习路径推荐
    4. 培训效果追踪
    5. 技能认证集成
    """

    def __init__(self):
        # 使用全局存储
        self.storage = p13_storage

        # 技能等级阈值
        self.skill_level_thresholds = {
            SkillLevel.BEGINNER: (0, 25),
            SkillLevel.INTERMEDIATE: (26, 50),
            SkillLevel.ADVANCED: (51, 75),
            SkillLevel.EXPERT: (76, 100)
        }

        # ROI 计算基准
        self.roi_benchmarks = {
            "productivity_gain_multiplier": 1.5,  # 生产力提升倍数
            "quality_improvement_multiplier": 1.2,  # 质量提升倍数
            "time_savings_multiplier": 1.0,  # 时间节省倍数
            "error_reduction_multiplier": 1.3  # 错误减少倍数
        }

        # 技能衰减率（天）
        self.skill_decay_half_life = 90  # 技能半衰期 90 天

    # ==================== 技能评估管理 ====================

    def create_assessment(self, data: Dict[str, Any]) -> SkillAssessment:
        """
        创建技能评估记录

        Args:
            data: 评估数据，包含 employee_id, user_id, assessment_type, skill_scores 等

        Returns:
            SkillAssessment: 创建的评估记录
        """
        assessment = SkillAssessment(
            id=str(uuid.uuid4()),
            employee_id=data['employee_id'],
            user_id=data['user_id'],
            tenant_id=data.get('tenant_id', 'default'),
            assessment_type=AssessmentType(data.get('assessment_type', 'pre_assessment')),
            training_id=data.get('training_id'),
            certification_id=data.get('certification_id'),
            skill_scores=data.get('skill_scores', {}),
            skill_levels=self._calculate_skill_levels(data.get('skill_scores', {})),
            overall_score=self._calculate_overall_score(data.get('skill_scores', {})),
            overall_level=self._determine_overall_level(data.get('skill_scores', {})),
            comments=data.get('comments'),
            assessment_data=data.get('assessment_data', {}),
            metadata=data.get('metadata', {})
        )

        self.storage.save_assessment(assessment)
        return assessment

    def get_assessment(self, assessment_id: str) -> Optional[SkillAssessment]:
        """获取评估记录"""
        return self.storage.get_assessment(assessment_id)

    def get_employee_assessments(
        self,
        employee_id: str,
        assessment_type: Optional[AssessmentType] = None,
        training_id: Optional[str] = None
    ) -> List[SkillAssessment]:
        """
        获取员工的评估记录

        Args:
            employee_id: 员工 ID
            assessment_type: 评估类型过滤
            training_id: 培训 ID 过滤

        Returns:
            评估记录列表
        """
        all_assessments = list(self.storage.assessments.values())
        filtered = [a for a in all_assessments if a.employee_id == employee_id]

        if assessment_type:
            filtered = [a for a in filtered if a.assessment_type == assessment_type]

        if training_id:
            filtered = [a for a in filtered if a.training_id == training_id]

        return sorted(filtered, key=lambda x: x.created_at, reverse=True)

    def compare_assessments(
        self,
        employee_id: str,
        pre_assessment_id: str,
        post_assessment_id: str
    ) -> Dict[str, Any]:
        """
        对比培训前后评估结果

        Args:
            employee_id: 员工 ID
            pre_assessment_id: 培训前评估 ID
            post_assessment_id: 培训后评估 ID

        Returns:
            包含技能提升详情的对比结果
        """
        pre = self.storage.get_assessment(pre_assessment_id)
        post = self.storage.get_assessment(post_assessment_id)

        if not pre or not post:
            return {"error": "评估记录不存在"}

        if pre.employee_id != employee_id or post.employee_id != employee_id:
            return {"error": "评估记录不属于该员工"}

        # 计算技能提升
        skill_improvements = {}
        all_skills = set(pre.skill_scores.keys()) | set(post.skill_scores.keys())

        for skill in all_skills:
            pre_score = pre.skill_scores.get(skill, 0)
            post_score = post.skill_scores.get(skill, 0)
            improvement = post_score - pre_score
            skill_improvements[skill] = round(improvement, 2)

        # 计算总体提升
        pre_overall = pre.overall_score
        post_overall = post.overall_score
        overall_improvement = post_overall - pre_overall

        # 确定提升等级
        if overall_improvement >= 30:
            improvement_level = "excellent"
        elif overall_improvement >= 20:
            improvement_level = "good"
        elif overall_improvement >= 10:
            improvement_level = "moderate"
        elif overall_improvement > 0:
            improvement_level = "slight"
        else:
            improvement_level = "none"

        return {
            "employee_id": employee_id,
            "pre_assessment": {
                "id": pre.id,
                "type": pre.assessment_type.value,
                "overall_score": pre.overall_score,
                "overall_level": pre.overall_level.value,
                "skill_scores": pre.skill_scores,
                "created_at": pre.created_at.isoformat()
            },
            "post_assessment": {
                "id": post.id,
                "type": post.assessment_type.value,
                "overall_score": post.overall_score,
                "overall_level": post.overall_level.value,
                "skill_scores": post.skill_scores,
                "created_at": post.created_at.isoformat()
            },
            "skill_improvements": skill_improvements,
            "overall_improvement": round(overall_improvement, 2),
            "improvement_percentage": round(overall_improvement / pre_overall * 100, 2) if pre_overall > 0 else 0,
            "improvement_level": improvement_level
        }

    def _calculate_skill_levels(self, skill_scores: Dict[str, float]) -> Dict[str, SkillLevel]:
        """根据技能分数计算技能等级"""
        levels = {}
        for skill, score in skill_scores.items():
            if score >= 76:
                levels[skill] = SkillLevel.EXPERT
            elif score >= 51:
                levels[skill] = SkillLevel.ADVANCED
            elif score >= 26:
                levels[skill] = SkillLevel.INTERMEDIATE
            else:
                levels[skill] = SkillLevel.BEGINNER
        return levels

    def _calculate_overall_score(self, skill_scores: Dict[str, float]) -> float:
        """计算综合评分（平均分）"""
        if not skill_scores:
            return 0.0
        return round(sum(skill_scores.values()) / len(skill_scores), 2)

    def _determine_overall_level(self, skill_scores: Dict[str, float]) -> SkillLevel:
        """根据综合评分确定总体等级"""
        score = self._calculate_overall_score(skill_scores)
        if score >= 76:
            return SkillLevel.EXPERT
        elif score >= 51:
            return SkillLevel.ADVANCED
        elif score >= 26:
            return SkillLevel.INTERMEDIATE
        else:
            return SkillLevel.BEGINNER

    # ==================== 培训 ROI 计算 ====================

    def calculate_training_roi(self, data: Dict[str, Any]) -> TrainingROI:
        """
        计算培训投资回报率 (ROI)

        ROI = (收益 - 成本) / 成本 * 100%

        Args:
            data: 包含 employee_id, training_cost, time_cost_hours, hourly_rate 等

        Returns:
            TrainingROI: ROI 计算结果
        """
        employee_id = data['employee_id']
        training_id = data.get('training_id')
        certification_id = data.get('certification_id')

        # 成本计算
        training_cost = data.get('training_cost', 0.0)
        time_cost_hours = data.get('time_cost_hours', 0.0)
        hourly_rate = data.get('hourly_rate', 50.0)  # 默认时薪 $50
        time_cost = time_cost_hours * hourly_rate
        opportunity_cost = data.get('opportunity_cost', time_cost * 0.2)  # 机会成本默认为时间成本的 20%
        total_cost = training_cost + time_cost + opportunity_cost

        # 收益计算（基于员工表现提升）
        productivity_gain = self._calculate_productivity_gain(employee_id, total_cost)
        quality_improvement = self._calculate_quality_improvement(employee_id, total_cost)
        time_savings = self._calculate_time_savings(employee_id, total_cost)
        error_reduction = self._calculate_error_reduction(employee_id, total_cost)
        total_benefit = productivity_gain + quality_improvement + time_savings + error_reduction

        # ROI 计算
        if total_cost > 0:
            roi_percentage = (total_benefit - total_cost) / total_cost * 100
        else:
            roi_percentage = 0.0

        # ROI 状态判定
        if roi_percentage > 0:
            roi_status = ROIStatus.POSITIVE
        elif roi_percentage < -50:
            roi_status = ROIStatus.NEGATIVE
        elif roi_percentage >= -50:
            roi_status = ROIStatus.BREAK_EVEN
        else:
            roi_status = ROIStatus.PENDING

        # 回收周期计算（简单估算）
        if total_benefit > 0:
            payback_period_days = int((total_cost / total_benefit) * 30)  # 假设收益是 30 天的
        else:
            payback_period_days = 999  # 无法回收

        roi = TrainingROI(
            id=str(uuid.uuid4()),
            employee_id=employee_id,
            tenant_id=data.get('tenant_id', 'default'),
            training_id=training_id,
            certification_id=certification_id,
            training_cost=training_cost,
            time_cost_hours=time_cost_hours,
            opportunity_cost=opportunity_cost,
            total_cost=total_cost,
            productivity_gain=productivity_gain,
            quality_improvement=quality_improvement,
            time_savings=time_savings,
            error_reduction=error_reduction,
            total_benefit=total_benefit,
            roi_percentage=round(roi_percentage, 2),
            roi_status=roi_status,
            payback_period_days=min(payback_period_days, 365),  # 最多 1 年
            calculation_period_days=data.get('period_days', 30),
            metadata=data.get('metadata', {})
        )

        self.storage.save_roi(roi)
        return roi

    def get_employee_rois(self, employee_id: str, period_days: int = 30) -> List[TrainingROI]:
        """获取员工的 ROI 记录"""
        cutoff_date = datetime.now() - timedelta(days=period_days)
        all_rois = list(self.storage.training_rois.values())
        filtered = [
            r for r in all_rois
            if r.employee_id == employee_id and r.created_at >= cutoff_date
        ]
        return sorted(filtered, key=lambda x: x.created_at, reverse=True)

    def aggregate_roi(self, employee_ids: List[str]) -> Dict[str, Any]:
        """
        聚合计算多个员工的 ROI

        Args:
            employee_ids: 员工 ID 列表

        Returns:
            聚合 ROI 统计
        """
        all_rois = list(self.storage.training_rois.values())
        filtered = [r for r in all_rois if r.employee_id in employee_ids]

        if not filtered:
            return {
                "total_trainings": 0,
                "total_cost": 0.0,
                "total_benefit": 0.0,
                "average_roi": 0.0,
                "positive_roi_count": 0,
                "negative_roi_count": 0
            }

        total_cost = sum(r.total_cost for r in filtered)
        total_benefit = sum(r.total_benefit for r in filtered)
        average_roi = sum(r.roi_percentage for r in filtered) / len(filtered)
        positive_count = sum(1 for r in filtered if r.roi_status == ROIStatus.POSITIVE)
        negative_count = sum(1 for r in filtered if r.roi_status == ROIStatus.NEGATIVE)

        return {
            "total_trainings": len(filtered),
            "total_cost": round(total_cost, 2),
            "total_benefit": round(total_benefit, 2),
            "average_roi": round(average_roi, 2),
            "positive_roi_count": positive_count,
            "negative_roi_count": negative_count,
            "roi_distribution": {
                "positive": positive_count,
                "break_even": sum(1 for r in filtered if r.roi_status == ROIStatus.BREAK_EVEN),
                "negative": negative_count
            }
        }

    def _calculate_productivity_gain(self, employee_id: str, total_cost: float) -> float:
        """
        计算生产力提升收益

        简化计算：假设培训后生产力提升 10-30%
        """
        # 实际应该查询员工任务完成率等指标
        # 这里用简化计算
        base_gain = total_cost * self.roi_benchmarks["productivity_gain_multiplier"]
        # 添加随机因子（模拟不同员工的表现差异）
        factor = 0.5 + (hash(employee_id) % 100) / 100  # 0.5-1.5
        return base_gain * factor

    def _calculate_quality_improvement(self, employee_id: str, total_cost: float) -> float:
        """计算质量提升收益"""
        base_gain = total_cost * self.roi_benchmarks["quality_improvement_multiplier"] * 0.5
        factor = 0.5 + (hash(employee_id) % 100) / 100
        return base_gain * factor

    def _calculate_time_savings(self, employee_id: str, total_cost: float) -> float:
        """计算时间节省收益"""
        base_gain = total_cost * self.roi_benchmarks["time_savings_multiplier"] * 0.3
        factor = 0.5 + (hash(employee_id) % 100) / 100
        return base_gain * factor

    def _calculate_error_reduction(self, employee_id: str, total_cost: float) -> float:
        """计算错误减少收益"""
        base_gain = total_cost * self.roi_benchmarks["error_reduction_multiplier"] * 0.2
        factor = 0.5 + (hash(employee_id) % 100) / 100
        return base_gain * factor

    # ==================== 学习路径推荐 ====================

    def create_learning_path(self, data: Dict[str, Any]) -> LearningPath:
        """
        创建个性化学习路径

        Args:
            data: 包含 employee_id, goal_name, target_skills, current_skills 等

        Returns:
            LearningPath: 创建的学习路径
        """
        current_skills = data.get('current_skills', {})
        target_skills = data.get('target_skills', {})

        # 计算技能差距
        skill_gaps = self._calculate_skill_gaps(current_skills, target_skills)

        # 生成学习路径项目
        path_items = self._generate_path_items(skill_gaps, data.get('available_content', []))

        # 计算总预计时间
        estimated_total_hours = sum(item.estimated_hours for item in path_items)

        # 计算推荐分数
        recommendation_score = self._calculate_recommendation_score(
            skill_gaps,
            data.get('recommendation_reason', PathRecommendationReason.SKILL_GAP)
        )

        path = LearningPath(
            id=str(uuid.uuid4()),
            employee_id=data['employee_id'],
            user_id=data['user_id'],
            tenant_id=data.get('tenant_id', 'default'),
            goal_name=data['goal_name'],
            goal_description=data.get('goal_description'),
            current_skills=current_skills,
            target_skills=target_skills,
            skill_gaps=skill_gaps,
            path_items=path_items,
            status=LearningPathStatus.NOT_STARTED,
            overall_progress=0.0,
            estimated_total_hours=estimated_total_hours,
            recommendation_reason=data.get('recommendation_reason', PathRecommendationReason.SKILL_GAP),
            recommendation_score=recommendation_score,
            estimated_completion_date=datetime.now() + timedelta(hours=estimated_total_hours) if estimated_total_hours > 0 else None,
            metadata=data.get('metadata', {})
        )

        self.storage.save_learning_path(path)
        return path

    def get_learning_path(self, path_id: str) -> Optional[LearningPath]:
        """获取学习路径"""
        return self.storage.get_learning_path(path_id)

    def get_employee_learning_paths(self, employee_id: str) -> List[LearningPath]:
        """获取员工的学习路径"""
        all_paths = list(self.storage.learning_paths.values())
        filtered = [p for p in all_paths if p.employee_id == employee_id]
        return sorted(filtered, key=lambda x: x.created_at, reverse=True)

    def update_path_progress(self, path_id: str, item_id: str, completed: bool, score: Optional[float] = None):
        """
        更新学习路径进度

        Args:
            path_id: 学习路径 ID
            item_id: 学习项目 ID
            completed: 是否完成
            score: 完成分数
        """
        path = self.storage.get_learning_path(path_id)
        if not path:
            return

        for item in path.path_items:
            if item.id == item_id:
                item.is_completed = completed
                item.completed_at = datetime.now() if completed else None
                item.score = score
                break

        # 重新计算总体进度
        total_items = len(path.path_items)
        completed_items = sum(1 for item in path.path_items if item.is_completed)
        path.overall_progress = (completed_items / total_items * 100) if total_items > 0 else 0

        # 更新状态
        if completed_items == total_items:
            path.status = LearningPathStatus.COMPLETED
            path.actual_completion_date = datetime.now()
        elif completed_items > 0:
            path.status = LearningPathStatus.IN_PROGRESS
            if not path.started_at:
                path.started_at = datetime.now()

        self.storage.save_learning_path(path)

    def recommend_learning_path(
        self,
        employee_id: str,
        current_skills: Dict[str, float],
        target_role: str
    ) -> LearningPath:
        """
        基于目标角色推荐学习路径

        Args:
            employee_id: 员工 ID
            current_skills: 当前技能 {skill_name: score}
            target_role: 目标角色，如"高级 Python 开发者"

        Returns:
            LearningPath: 推荐的学习路径
        """
        # 基于目标角色确定目标技能
        target_skills = self._get_role_target_skills(target_role)

        # 创建学习路径
        path_data = {
            "employee_id": employee_id,
            "user_id": "system",
            "tenant_id": "default",
            "goal_name": f"成为{target_role}",
            "goal_description": f"从当前水平提升至{target_role}所需技能水平",
            "current_skills": current_skills,
            "target_skills": target_skills,
            "recommendation_reason": PathRecommendationReason.CAREER_GOAL,
            "available_content": self._get_available_learning_content()
        }

        return self.create_learning_path(path_data)

    def _calculate_skill_gaps(
        self,
        current_skills: Dict[str, float],
        target_skills: Dict[str, float]
    ) -> Dict[str, float]:
        """计算技能差距"""
        gaps = {}
        all_skills = set(current_skills.keys()) | set(target_skills.keys())

        for skill in all_skills:
            current = current_skills.get(skill, 0)
            target = target_skills.get(skill, 50)  # 默认目标 50 分
            gap = target - current
            if gap > 0:  # 只有需要提升的技能才计入差距
                gaps[skill] = round(gap, 2)

        return gaps

    def _generate_path_items(
        self,
        skill_gaps: Dict[str, float],
        available_content: List[Dict[str, Any]]
    ) -> List[LearningPathItem]:
        """
        基于技能差距生成学习路径项目

        Args:
            skill_gaps: 技能差距 {skill_name: gap}
            available_content: 可用学习内容列表

        Returns:
            学习路径项目列表
        """
        path_items = []

        # 按差距大小排序技能
        sorted_gaps = sorted(skill_gaps.items(), key=lambda x: x[1], reverse=True)

        for idx, (skill, gap) in enumerate(sorted_gaps):
            # 根据差距大小确定学习深度
            if gap >= 50:
                depth = "comprehensive"
                estimated_hours = 20.0
            elif gap >= 30:
                depth = "intermediate"
                estimated_hours = 10.0
            else:
                depth = "basic"
                estimated_hours = 5.0

            item = LearningPathItem(
                id=str(uuid.uuid4()),
                content_type="training",
                content_id=f"training_{skill}_{depth}",
                content_name=f"{skill} - {depth}培训",
                content_description=f"提升{skill}技能{gap}分",
                sequence_order=idx,
                is_prerequisite=(idx == 0),  # 第一个为必修
                estimated_hours=estimated_hours,
                target_skills=[skill],
                metadata={"depth": depth, "gap": gap}
            )
            path_items.append(item)

        return path_items

    def _calculate_recommendation_score(
        self,
        skill_gaps: Dict[str, float],
        reason: PathRecommendationReason
    ) -> float:
        """计算推荐分数"""
        if not skill_gaps:
            return 0.0

        # 基础分数：基于平均差距
        avg_gap = sum(skill_gaps.values()) / len(skill_gaps)
        base_score = min(avg_gap * 1.5, 100)  # 最多 100 分

        # 理由加成
        reason_bonus = {
            PathRecommendationReason.SKILL_GAP: 0,
            PathRecommendationReason.CAREER_GOAL: 10,
            PathRecommendationReason.TRENDING_SKILL: 5,
            PathRecommendationReason.PREREQUISITE: 15,
            PathRecommendationReason.PERSONALIZED: 10
        }

        final_score = base_score + reason_bonus.get(reason, 0)
        return min(round(final_score, 2), 100)

    def _get_role_target_skills(self, role: str) -> Dict[str, float]:
        """获取目标角色的技能要求"""
        # 简化版，实际应该从数据库中查询
        role_skills = {
            "高级 Python 开发者": {
                "Python": 85,
                "Django": 75,
                "数据库": 70,
                "API 设计": 75,
                "代码审查": 70
            },
            "数据分析师": {
                "Python": 70,
                "SQL": 80,
                "数据可视化": 75,
                "统计学": 70,
                "机器学习": 60
            },
            "机器学习工程师": {
                "Python": 80,
                "机器学习": 85,
                "深度学习": 75,
                "TensorFlow": 75,
                "数据处理": 70
            }
        }
        return role_skills.get(role, {"通用技能": 60})

    def _get_available_learning_content(self) -> List[Dict[str, Any]]:
        """获取可用学习内容（模拟数据）"""
        return [
            {"id": "cert_001", "type": "certification", "name": "Python 基础认证", "skills": ["Python"]},
            {"id": "cert_002", "type": "certification", "name": "Python 高级认证", "skills": ["Python", "Django"]},
            {"id": "training_001", "type": "training", "name": "SQL 入门", "skills": ["SQL"]},
            {"id": "training_002", "type": "training", "name": "数据可视化实战", "skills": ["数据可视化", "Python"]},
        ]

    # ==================== 培训效果追踪 ====================

    def create_impact_tracker(
        self,
        employee_id: str,
        training_id: str,
        training_name: str,
        pre_score: float,
        post_score: float,
        tenant_id: str = "default"
    ) -> TrainingImpactTracker:
        """
        创建培训效果追踪器

        Args:
            employee_id: 员工 ID
            training_id: 培训 ID
            training_name: 培训名称
            pre_score: 培训前评分
            post_score: 培训后评分
            tenant_id: 租户 ID

        Returns:
            TrainingImpactTracker: 创建的追踪器
        """
        improvement = post_score - pre_score
        improvement_percentage = (improvement / pre_score * 100) if pre_score > 0 else 0

        # 确定影响等级
        if improvement_percentage >= 50:
            impact_level = "high"
        elif improvement_percentage >= 20:
            impact_level = "medium"
        elif improvement_percentage > 0:
            impact_level = "low"
        else:
            impact_level = "negative"

        tracker = TrainingImpactTracker(
            id=str(uuid.uuid4()),
            employee_id=employee_id,
            tenant_id=tenant_id,
            training_id=training_id,
            training_name=training_name,
            pre_training_score=pre_score,
            post_training_score=post_score,
            improvement_percentage=round(improvement_percentage, 2),
            skill_retention_rate=100.0,  # 初始为 100%
            skill_decay_rate=0.0,
            impact_level=impact_level,
            training_completed_at=datetime.now(),
            tracking_end_date=datetime.now() + timedelta(days=90)  # 追踪 90 天
        )

        self.storage.save_impact_tracker(tracker)
        return tracker

    def add_follow_up_score(
        self,
        tracker_id: str,
        score: float,
        metrics: Optional[Dict[str, Any]] = None
    ):
        """
        添加跟踪评估分数

        Args:
            tracker_id: 追踪器 ID
            score: 跟踪评估分数
            metrics: 相关指标
        """
        tracker = self.storage.get_impact_tracker(tracker_id)
        if not tracker:
            return

        # 添加跟踪记录
        tracker.follow_up_scores.append({
            "date": datetime.now().isoformat(),
            "score": score,
            "metrics": metrics or {}
        })

        # 更新技能保持率
        if tracker.follow_up_scores:
            latest_score = tracker.follow_up_scores[-1]["score"]
            tracker.skill_retention_rate = (latest_score / tracker.post_training_score * 100) if tracker.post_training_score > 0 else 0

            # 计算衰减率
            days_since_training = (datetime.now() - tracker.training_completed_at).days
            if days_since_training > 0:
                tracker.skill_decay_rate = (100 - tracker.skill_retention_rate) / days_since_training * 30  # 月度衰减率

        tracker.last_tracked_at = datetime.now()
        self.storage.save_impact_tracker(tracker)

    def get_impact_tracker(self, tracker_id: str) -> Optional[TrainingImpactTracker]:
        """获取效果追踪器"""
        return self.storage.get_impact_tracker(tracker_id)

    def get_employee_impact_trackers(self, employee_id: str) -> List[TrainingImpactTracker]:
        """获取员工的培训效果追踪器"""
        all_trackers = list(self.storage.impact_trackers.values())
        filtered = [t for t in all_trackers if t.employee_id == employee_id]
        return sorted(filtered, key=lambda x: x.training_completed_at, reverse=True)

    # ==================== 认证集成 ====================

    def integrate_certification(self, data: Dict[str, Any]) -> CertificationIntegration:
        """
        集成认证系统

        Args:
            data: 包含 employee_id, certification_id, exam_score, mapped_skills 等

        Returns:
            CertificationIntegration: 认证集成记录
        """
        cert = CertificationIntegration(
            id=str(uuid.uuid4()),
            employee_id=data['employee_id'],
            user_id=data['user_id'],
            tenant_id=data.get('tenant_id', 'default'),
            certification_id=data['certification_id'],
            certification_name=data['certification_name'],
            certification_level=data.get('certification_level', 'basic'),
            exam_score=data.get('exam_score', 0),
            exam_passed=data.get('exam_passed', False),
            exam_attempts=data.get('exam_attempts', 1),
            mapped_skills=data.get('mapped_skills', {}),
            certificate_id=data.get('certificate_id'),
            certificate_issued_at=data.get('certificate_issued_at'),
            certificate_expires_at=data.get('certificate_expires_at'),
            related_training_ids=data.get('related_training_ids', []),
            prerequisite_certifications=data.get('prerequisite_certifications', []),
            metadata=data.get('metadata', {})
        )

        if cert.exam_passed:
            cert.passed_at = datetime.now()

        self.storage.save_certification_integration(cert)
        return cert

    def get_employee_certifications(self, employee_id: str) -> List[CertificationIntegration]:
        """获取员工的认证记录"""
        all_certs = list(self.storage.certification_integrations.values())
        filtered = [c for c in all_certs if c.employee_id == employee_id]
        return sorted(filtered, key=lambda x: x.created_at, reverse=True)

    # ==================== 综合报告 ====================

    def generate_effectiveness_report(
        self,
        employee_id: str,
        period: str = "last_90_days"
    ) -> TrainingEffectivenessReport:
        """
        生成培训效果综合报告

        Args:
            employee_id: 员工 ID
            period: 报告周期

        Returns:
            TrainingEffectivenessReport: 综合报告
        """
        # 计算周期
        end_date = datetime.now()
        if period == "last_30_days":
            start_date = end_date - timedelta(days=30)
        elif period == "last_90_days":
            start_date = end_date - timedelta(days=90)
        else:
            start_date = end_date - timedelta(days=365)

        # 获取相关数据
        assessments = self.get_employee_assessments(employee_id)
        rois = self.get_employee_rois(employee_id, period_days=90)
        learning_paths = self.get_employee_learning_paths(employee_id)
        impact_trackers = self.get_employee_impact_trackers(employee_id)

        # 过滤周期内的数据
        period_assessments = [a for a in assessments if a.created_at >= start_date]
        period_rois = [r for r in rois if r.created_at >= start_date]
        period_paths = [p for p in learning_paths if p.created_at >= start_date]

        # 计算培训统计
        training_ids = set(a.training_id for a in period_assessments if a.training_id)
        completed_trainings = [a for a in period_assessments if a.assessment_type == AssessmentType.POST_ASSESSMENT]

        # 计算技能提升
        skill_improvements = self._calculate_period_improvements(period_assessments)

        # 计算 ROI 统计
        total_cost = sum(r.total_cost for r in period_rois)
        total_benefit = sum(r.total_benefit for r in period_rois)
        average_roi = sum(r.roi_percentage for r in period_rois) / len(period_rois) if period_rois else 0

        # 认证统计
        certifications = self.get_employee_certifications(employee_id)
        passed_certs = [c for c in certifications if c.exam_passed and c.created_at >= start_date]

        # 生成洞察
        insights = self._generate_insights(
            skill_improvements, period_rois, period_paths, impact_trackers
        )
        recommendations = self._generate_recommendations(
            skill_improvements, period_rois, period_paths
        )

        report = TrainingEffectivenessReport(
            id=str(uuid.uuid4()),
            employee_id=employee_id,
            tenant_id="default",
            report_period=period,
            total_trainings=len(training_ids),
            completed_trainings=len(completed_trainings),
            in_progress_trainings=len(training_ids) - len(completed_trainings),
            skills_improved=list(skill_improvements.keys()),
            average_improvement=sum(skill_improvements.values()) / len(skill_improvements) if skill_improvements else 0,
            max_improvement=max(skill_improvements.values()) if skill_improvements else 0,
            total_training_cost=total_cost,
            total_benefit=total_benefit,
            average_roi=average_roi,
            total_certifications=len(certifications),
            passed_certifications=len(passed_certs),
            certification_rate=len(passed_certs) / len(certifications) if certifications else 0,
            active_learning_paths=sum(1 for p in period_paths if p.status == LearningPathStatus.IN_PROGRESS),
            completed_learning_paths=sum(1 for p in period_paths if p.status == LearningPathStatus.COMPLETED),
            learning_path_completion_rate=sum(1 for p in period_paths if p.status == LearningPathStatus.COMPLETED) / len(period_paths) if period_paths else 0,
            insights=insights,
            recommendations=recommendations,
            metadata={"generated_at": datetime.now().isoformat()}
        )

        self.storage.save_report(report)
        return report

    def _calculate_period_improvements(
        self,
        assessments: List[SkillAssessment]
    ) -> Dict[str, float]:
        """计算周期内的技能提升"""
        pre_assessments = [a for a in assessments if a.assessment_type == AssessmentType.PRE_ASSESSMENT]
        post_assessments = [a for a in assessments if a.assessment_type == AssessmentType.POST_ASSESSMENT]

        improvements = {}

        # 配对前后评估
        for post in post_assessments:
            # 找到对应的 pre 评估（同一 training_id 且时间在前）
            pre = next(
                (a for a in pre_assessments
                 if a.training_id == post.training_id and a.created_at < post.created_at),
                None
            )
            if pre:
                for skill in set(pre.skill_scores.keys()) | set(post.skill_scores.keys()):
                    pre_score = pre.skill_scores.get(skill, 0)
                    post_score = post.skill_scores.get(skill, 0)
                    improvement = post_score - pre_score
                    if improvement > 0:
                        improvements[skill] = max(improvements.get(skill, 0), improvement)

        return improvements

    def _generate_insights(
        self,
        skill_improvements: Dict[str, float],
        rois: List[TrainingROI],
        learning_paths: List[LearningPath],
        impact_trackers: List[TrainingImpactTracker]
    ) -> List[str]:
        """生成洞察"""
        insights = []

        if skill_improvements:
            top_improvement = max(skill_improvements.items(), key=lambda x: x[1])
            insights.append(f"提升最快的技能：{top_improvement[0]} (+{top_improvement[1]:.1f}分)")

        positive_rois = [r for r in rois if r.roi_status == ROIStatus.POSITIVE]
        if positive_rois:
            insights.append(f"培训 ROI 为正的比例：{len(positive_rois) / len(rois) * 100:.1f}%" if rois else "培训投资回报良好")

        completed_paths = [p for p in learning_paths if p.status == LearningPathStatus.COMPLETED]
        if completed_paths:
            insights.append(f"已完成 {len(completed_paths)} 个学习路径")

        high_impact = [t for t in impact_trackers if t.impact_level == "high"]
        if high_impact:
            insights.append(f"{len(high_impact)} 个培训产生高影响力")

        if not insights:
            insights.append("持续学习，保持进步")

        return insights

    def _generate_recommendations(
        self,
        skill_improvements: Dict[str, float],
        rois: List[TrainingROI],
        learning_paths: List[LearningPath]
    ) -> List[str]:
        """生成建议"""
        recommendations = []

        # 基于技能提升的建议
        if not skill_improvements:
            recommendations.append("建议参与更多培训项目以提升技能")

        # 基于 ROI 的建议
        negative_rois = [r for r in rois if r.roi_status == ROIStatus.NEGATIVE]
        if negative_rois:
            recommendations.append(f"关注{len(negative_rois)} 个 ROI 为负的培训，评估其必要性")

        # 基于学习路径的建议
        in_progress_paths = [p for p in learning_paths if p.status == LearningPathStatus.IN_PROGRESS]
        if in_progress_paths:
            recommendations.append(f"继续完成{len(in_progress_paths)} 个进行中的学习路径")

        if not recommendations:
            recommendations.append("保持当前学习节奏，持续追踪培训效果")

        return recommendations


# 全局服务实例
training_effectiveness_v2_service = TrainingEffectivenessV2Service()
