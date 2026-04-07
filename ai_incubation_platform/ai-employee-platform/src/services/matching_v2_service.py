"""
P12 高级匹配算法增强 - 服务层

包含：
1. 向量相似度匹配服务
2. 文化适配度评估服务
3. 历史表现加权增强服务
4. 薪资期望匹配分析服务
5. 可解释性报告生成服务
"""
import math
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel
import random

from models.p12_models import (
    EmployeeVector, JobVector, VectorSimilarityCache,
    CulturalFitProfile, CulturalFitMatch, CommunicationStyle,
    FeedbackStyle, WorkSchedulePreference, DecisionStyle,
    CollaborationStyle,
    WeightedPerformanceScore, PerformanceTrend, ProjectComplexity,
    EmployeeSalaryAnalysis, SalaryBenchmark, PricingStrategy,
    MatchExplanation, MatchScoreBreakdown, MatchStrength, MatchRisk,
    ConfidenceLevel, TrendDirection,
    p12_storage
)


# ==================== 向量相似度匹配服务 ====================

class VectorMatchingService:
    """向量相似度匹配服务"""

    def __init__(self):
        self.vector_dimension = 384  # Sentence Transformer 默认维度
        self.similarity_cache_ttl_hours = 24

    def generate_embedding(self, text: str) -> List[float]:
        """
        生成文本嵌入向量

        实际生产中应调用真实的嵌入模型（如 Sentence Transformer 或 OpenAI Embedding）
        这里使用伪向量进行演示
        """
        # 使用文本的哈希值生成确定性伪随机向量
        text_hash = hash(text)
        random.seed(text_hash)
        vector = [random.gauss(0, 1) for _ in range(self.vector_dimension)]

        # 归一化向量（L2 归一化）
        magnitude = math.sqrt(sum(v * v for v in vector))
        if magnitude > 0:
            vector = [v / magnitude for v in vector]

        return vector

    def cosine_similarity(self, vector1: List[float], vector2: List[float]) -> float:
        """
        计算余弦相似度

        余弦相似度 = (A · B) / (||A|| * ||B||)
        由于向量已归一化，简化为点积
        """
        if len(vector1) != len(vector2):
            raise ValueError("向量维度不匹配")

        # 点积
        dot_product = sum(a * b for a, b in zip(vector1, vector2))

        # 对于归一化向量，余弦相似度就是点积
        # 限制在 [-1, 1] 范围内
        dot_product = max(-1.0, min(1.0, dot_product))

        # 转换到 [0, 1] 范围（0 表示完全不相似，1 表示完全相似）
        similarity = (dot_product + 1) / 2

        return similarity

    def vectorize_employee(self, employee: Dict[str, Any]) -> EmployeeVector:
        """
        生成员工技能向量

        整合员工的技能、经验、描述等文本信息生成嵌入向量
        """
        # 构建综合文本
        skill_texts = []

        # 技能列表
        skills = employee.get('skills', {})
        for skill_name, level in skills.items():
            skill_texts.append(f"{skill_name}: {level}")

        # 个人描述
        if employee.get('description'):
            skill_texts.append(employee['description'])

        # 类别
        if employee.get('category'):
            skill_texts.append(employee['category'])

        # 经验描述
        if employee.get('experience_years'):
            skill_texts.append(f"{employee['experience_years']} years experience")

        # 合并文本
        combined_text = " | ".join(skill_texts)

        # 生成向量
        vector = self.generate_embedding(combined_text)

        # 创建向量对象
        employee_vector = EmployeeVector(
            employee_id=employee['id'],
            skill_vector=vector,
            vector_model_version="sentence-transformer-v1.0",
            skill_tags=list(skills.keys()),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        # 保存到存储
        p12_storage.save_employee_vector(employee_vector)

        return employee_vector

    def vectorize_job(self, job: Dict[str, Any]) -> JobVector:
        """
        生成职位需求向量
        """
        # 构建综合文本
        text_parts = []

        # 职位标题
        if job.get('title'):
            text_parts.append(f"Title: {job['title']}")

        # 职位描述
        if job.get('description'):
            text_parts.append(f"Description: {job['description']}")

        # 技能要求
        required_skills = job.get('required_skills', {})
        if required_skills:
            skills_text = ", ".join([f"{skill}(重要性{imp})" for skill, imp in required_skills.items()])
            text_parts.append(f"Required Skills: {skills_text}")

        # 类别
        if job.get('category'):
            text_parts.append(f"Category: {job['category']}")

        combined_text = " | ".join(text_parts)

        # 生成向量
        vector = self.generate_embedding(combined_text)

        # 创建向量对象
        job_vector = JobVector(
            job_id=job.get('id', str(uuid.uuid4())),
            job_vector=vector,
            vector_model_version="sentence-transformer-v1.0",
            requirements_text=combined_text,
            created_at=datetime.now()
        )

        # 保存到存储
        p12_storage.save_job_vector(job_vector)

        return job_vector

    def get_cached_similarity(self, employee_id: str, job_id: str) -> Optional[float]:
        """获取缓存的相似度分数"""
        cache_key = f"{employee_id}:{job_id}"
        if cache_key in p12_storage.vector_cache:
            cache = p12_storage.vector_cache[cache_key]
            if cache.expires_at > datetime.now():
                return cache.similarity_score
        return None

    def cache_similarity(self, employee_id: str, job_id: str, similarity: float):
        """缓存相似度分数"""
        cache_key = f"{employee_id}:{job_id}"
        cache = VectorSimilarityCache(
            employee_id=employee_id,
            job_id=job_id,
            similarity_score=similarity,
            computed_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=self.similarity_cache_ttl_hours)
        )
        p12_storage.vector_cache[cache_key] = cache

    def match_by_vector_similarity(
        self,
        job: Dict[str, Any],
        employees: List[Dict[str, Any]],
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        基于向量相似度匹配员工

        返回按相似度排序的员工列表
        """
        # 生成职位向量
        job_vector_obj = self.vectorize_job(job)
        job_vector = job_vector_obj.job_vector

        results = []

        for employee in employees:
            # 检查缓存
            if use_cache:
                cached_score = self.get_cached_similarity(employee['id'], job['id'])
                if cached_score is not None:
                    results.append({
                        'employee_id': employee['id'],
                        'employee_name': employee.get('name', 'Unknown'),
                        'vector_similarity': cached_score,
                        'from_cache': True
                    })
                    continue

            # 获取或生成员工向量
            emp_vector_obj = p12_storage.get_employee_vector(employee['id'])
            if emp_vector_obj is None:
                emp_vector_obj = self.vectorize_employee(employee)

            # 计算相似度
            similarity = self.cosine_similarity(emp_vector_obj.skill_vector, job_vector)

            # 缓存结果
            if use_cache:
                self.cache_similarity(employee['id'], job['id'], similarity)

            results.append({
                'employee_id': employee['id'],
                'employee_name': employee.get('name', 'Unknown'),
                'vector_similarity': round(similarity * 100, 2),  # 转换为 0-100 分数
                'from_cache': False
            })

        # 按相似度排序
        results.sort(key=lambda x: x['vector_similarity'], reverse=True)

        return results


# ==================== 文化适配度评估服务 ====================

class CulturalFitService:
    """文化适配度评估服务"""

    def __init__(self):
        # 风格匹配矩阵
        self.communication_compatibility = {
            (CommunicationStyle.FREQUENT, CommunicationStyle.FREQUENT): 1.0,
            (CommunicationStyle.FREQUENT, CommunicationStyle.MODERATE): 0.7,
            (CommunicationStyle.FREQUENT, CommunicationStyle.MINIMAL): 0.3,
            (CommunicationStyle.MODERATE, CommunicationStyle.FREQUENT): 0.7,
            (CommunicationStyle.MODERATE, CommunicationStyle.MODERATE): 1.0,
            (CommunicationStyle.MODERATE, CommunicationStyle.MINIMAL): 0.6,
            (CommunicationStyle.MINIMAL, CommunicationStyle.FREQUENT): 0.3,
            (CommunicationStyle.MINIMAL, CommunicationStyle.MODERATE): 0.6,
            (CommunicationStyle.MINIMAL, CommunicationStyle.MINIMAL): 1.0,
        }

        self.feedback_compatibility = {
            (FeedbackStyle.DIRECT, FeedbackStyle.DIRECT): 1.0,
            (FeedbackStyle.DIRECT, FeedbackStyle.DIPLOMATIC): 0.6,
            (FeedbackStyle.DIPLOMATIC, FeedbackStyle.DIRECT): 0.6,
            (FeedbackStyle.DIPLOMATIC, FeedbackStyle.DIPLOMATIC): 1.0,
        }

        self.collaboration_compatibility = {
            (CollaborationStyle.INDEPENDENT, CollaborationStyle.INDEPENDENT): 0.8,
            (CollaborationStyle.INDEPENDENT, CollaborationStyle.COLLABORATIVE): 0.5,
            (CollaborationStyle.COLLABORATIVE, CollaborationStyle.INDEPENDENT): 0.5,
            (CollaborationStyle.COLLABORATIVE, CollaborationStyle.COLLABORATIVE): 1.0,
        }

    def create_cultural_profile(
        self,
        user_id: str,
        user_type: str = "employee",
        profile_data: Optional[Dict[str, Any]] = None
    ) -> CulturalFitProfile:
        """
        创建文化适配档案
        """
        profile = CulturalFitProfile(
            user_id=user_id,
            user_type=user_type,
            communication_style=CommunicationStyle(profile_data.get('communication_style', 'moderate')) if profile_data and profile_data.get('communication_style') else CommunicationStyle.MODERATE,
            communication_notes=profile_data.get('communication_notes', '') if profile_data else '',
            feedback_style=FeedbackStyle(profile_data.get('feedback_style', 'direct')) if profile_data and profile_data.get('feedback_style') else FeedbackStyle.DIRECT,
            feedback_notes=profile_data.get('feedback_notes', '') if profile_data else '',
            work_schedule_preference=WorkSchedulePreference(profile_data.get('work_schedule_preference', 'flexible')) if profile_data and profile_data.get('work_schedule_preference') else WorkSchedulePreference.FLEXIBLE,
            timezone=profile_data.get('timezone', 'UTC') if profile_data else 'UTC',
            working_hours_start=profile_data.get('working_hours_start', 9) if profile_data else 9,
            working_hours_end=profile_data.get('working_hours_end', 18) if profile_data else 18,
            decision_style=DecisionStyle(profile_data.get('decision_style', 'data_driven')) if profile_data and profile_data.get('decision_style') else DecisionStyle.DATA_DRIVEN,
            decision_notes=profile_data.get('decision_notes', '') if profile_data else '',
            collaboration_style=CollaborationStyle(profile_data.get('collaboration_style', 'collaborative')) if profile_data and profile_data.get('collaboration_style') else CollaborationStyle.COLLABORATIVE,
            collaboration_notes=profile_data.get('collaboration_notes', '') if profile_data else '',
            meeting_preference=profile_data.get('meeting_preference', 'video') if profile_data else 'video',
            documentation_preference=profile_data.get('documentation_preference', 'detailed') if profile_data else 'detailed',
        )

        p12_storage.save_cultural_profile(profile)
        return profile

    def assess_cultural_fit(
        self,
        employee_profile: CulturalFitProfile,
        employer_profile: CulturalFitProfile
    ) -> CulturalFitMatch:
        """
        评估员工与雇主的文化适配度
        """
        # 沟通风格适配
        comm_key = (employee_profile.communication_style, employer_profile.communication_style)
        communication_fit = self.communication_compatibility.get(comm_key, 0.5) * 100

        # 反馈风格适配
        feedback_key = (employee_profile.feedback_style, employer_profile.feedback_style)
        feedback_fit = self.feedback_compatibility.get(feedback_key, 0.5) * 100

        # 协作风格适配
        collab_key = (employee_profile.collaboration_style, employer_profile.collaboration_style)
        collaboration_fit = self.collaboration_compatibility.get(collab_key, 0.5) * 100

        # 工作时间适配
        schedule_fit = self._calculate_schedule_fit(employee_profile, employer_profile)

        # 决策风格适配
        decision_fit = self._calculate_decision_fit(employee_profile, employer_profile)

        # 计算总体适配度（加权平均）
        overall_fit = (
            communication_fit * 0.25 +
            feedback_fit * 0.15 +
            schedule_fit * 0.20 +
            decision_fit * 0.15 +
            collaboration_fit * 0.25
        )

        # 生成优势和潜在冲突
        strengths = []
        potential_conflicts = []
        suggestions = []

        if communication_fit >= 80:
            strengths.append(f"沟通风格高度匹配（{communication_fit:.0f}%）")
        elif communication_fit < 60:
            potential_conflicts.append(f"沟通风格差异较大（{communication_fit:.0f}%）")
            suggestions.append("建议明确沟通频率和方式期望")

        if feedback_fit >= 80:
            strengths.append(f"反馈风格兼容（{feedback_fit:.0f}%）")
        elif feedback_fit < 60:
            potential_conflicts.append(f"反馈风格可能存在冲突（{feedback_fit:.0f}%）")
            suggestions.append("建议采用更中性的反馈方式")

        if schedule_fit >= 80:
            strengths.append(f"工作时间高度重叠")
        elif schedule_fit < 60:
            potential_conflicts.append(f"工作时间重叠较少")
            suggestions.append("建议提前协调会议时间")

        if collaboration_fit >= 80:
            strengths.append(f"协作风格匹配（{collaboration_fit:.0f}%）")
        elif collaboration_fit < 60:
            potential_conflicts.append(f"协作风格差异明显")
            suggestions.append("建议明确独立工作与协作的边界")

        # 创建匹配结果
        match = CulturalFitMatch(
            employee_id=employee_profile.user_id,
            employer_id=employer_profile.user_id,
            overall_fit_score=round(overall_fit, 2),
            communication_fit=round(communication_fit, 2),
            feedback_fit=round(feedback_fit, 2),
            schedule_fit=round(schedule_fit, 2),
            decision_fit=round(decision_fit, 2),
            collaboration_fit=round(collaboration_fit, 2),
            strengths=strengths,
            potential_conflicts=potential_conflicts,
            suggestions=suggestions,
            computed_at=datetime.now()
        )

        return match

    def _calculate_schedule_fit(
        self,
        employee_profile: CulturalFitProfile,
        employer_profile: CulturalFitProfile
    ) -> float:
        """计算工作时间适配度"""
        # 简化计算：比较工作时间重叠程度
        emp_start = employee_profile.working_hours_start
        emp_end = employee_profile.working_hours_end
        emp_start_req = employer_profile.working_hours_start
        emp_end_req = employer_profile.working_hours_end

        # 计算重叠时间
        overlap_start = max(emp_start, emp_start_req)
        overlap_end = min(emp_end, emp_end_req)
        overlap_hours = max(0, overlap_end - overlap_start)

        # 计算适配度（假设标准工作时间为 8 小时）
        if overlap_hours >= 6:
            return 100
        elif overlap_hours >= 4:
            return 70 + (overlap_hours - 4) * 15
        elif overlap_hours >= 2:
            return 40 + (overlap_hours - 2) * 15
        else:
            return overlap_hours * 20

    def _calculate_decision_fit(
        self,
        employee_profile: CulturalFitProfile,
        employer_profile: CulturalFitProfile
    ) -> float:
        """计算决策风格适配度"""
        if employee_profile.decision_style == employer_profile.decision_style:
            return 100
        else:
            # 数据驱动和直觉驱动可以互补
            return 70


# ==================== 历史表现加权增强服务 ====================

class EnhancedPerformanceService:
    """历史表现加权增强服务"""

    def __init__(self):
        self.half_life_days = 30  # 半衰期 30 天

    def calculate_time_decay_factor(self, days_ago: int) -> float:
        """
        计算时间衰减因子

        使用指数衰减：decay = 0.5 ^ (days / half_life)
        """
        if days_ago <= 0:
            return 1.0

        decay = math.pow(0.5, days_ago / self.half_life_days)
        return decay

    def calculate_complexity_score(self, project: Dict[str, Any]) -> float:
        """
        计算项目复杂度分数（1-5 分）
        """
        factors = {}

        # 技术难度
        tech_difficulty = project.get('technical_difficulty', 3)
        factors['technical_difficulty'] = tech_difficulty

        # 范围大小
        scope_size = project.get('scope_size', 3)  # 1-5
        factors['scope_size'] = scope_size

        # 团队规模
        team_size = project.get('team_size', 1)
        team_factor = min(5, 1 + team_size / 2)  # 1 人=1, 8 人+=5
        factors['team_complexity'] = team_factor

        # 截止压力
        deadline_pressure = project.get('deadline_pressure', 3)
        factors['deadline_pressure'] = deadline_pressure

        # 加权平均
        complexity = (
            tech_difficulty * 0.4 +
            scope_size * 0.3 +
            team_factor * 0.15 +
            deadline_pressure * 0.15
        )

        return min(5.0, max(1.0, complexity))

    def calculate_weighted_performance(
        self,
        employee: Dict[str, Any],
        project_history: Optional[List[Dict[str, Any]]] = None
    ) -> WeightedPerformanceScore:
        """
        计算加权表现分数
        """
        # 基础分数
        rating = employee.get('rating', 0)
        completion_rate = employee.get('completion_rate', 1.0)
        rehire_rate = employee.get('rehire_rate', 0)
        on_time_rate = employee.get('on_time_delivery_rate', 1.0)

        rating_score = (rating / 5.0) * 40  # 0-40 分
        completion_score = completion_rate * 25  # 0-25 分
        rehire_score = rehire_rate * 20  # 0-20 分
        on_time_score = on_time_rate * 15  # 0-15 分

        base_score = rating_score + completion_score + rehire_score + on_time_score

        # 时间衰减因子（基于最近的 project）
        time_decay_multiplier = 1.0
        if project_history:
            weighted_decay = 0
            total_weight = 0
            now = datetime.now()

            for project in project_history:
                completed_date = project.get('completed_date')
                if completed_date:
                    if isinstance(completed_date, str):
                        completed_date = datetime.fromisoformat(completed_date.replace('Z', '+00:00')).replace(tzinfo=None)

                    days_ago = (now - completed_date).days
                    decay = self.calculate_time_decay_factor(days_ago)
                    rating_weight = project.get('rating', 3) / 5.0

                    weighted_decay += decay * rating_weight
                    total_weight += rating_weight

            if total_weight > 0:
                time_decay_multiplier = weighted_decay / total_weight

        # 复杂度奖励
        complexity_bonus = 1.0
        if project_history:
            complexity_scores = []
            for project in project_history:
                complexity = self.calculate_complexity_score(project)
                complexity_scores.append(complexity)

            avg_complexity = sum(complexity_scores) / len(complexity_scores)
            # 平均复杂度>3 给予奖励
            if avg_complexity > 3:
                complexity_bonus = 1.0 + (avg_complexity - 3) * 0.1

        # 客户类型权重
        client_type_weight = 1.0
        enterprise_projects = sum(1 for p in (project_history or []) if p.get('client_type') == 'enterprise')
        if project_history and enterprise_projects > 0:
            enterprise_ratio = enterprise_projects / len(project_history)
            client_type_weight = 1.0 + enterprise_ratio * 0.2

        # 计算最终分数
        final_score = base_score * time_decay_multiplier * complexity_bonus * client_type_weight
        final_score = min(100, max(0, final_score))

        # 计算趋势
        trend = self._calculate_trend(employee, project_history)

        return WeightedPerformanceScore(
            employee_id=employee['id'],
            overall_score=round(final_score, 2),
            rating_score=round(rating_score, 2),
            completion_rate_score=round(completion_score, 2),
            rehire_rate_score=round(rehire_score, 2),
            on_time_delivery_score=round(on_time_score, 2),
            time_decay_multiplier=round(time_decay_multiplier, 3),
            complexity_bonus=round(complexity_bonus, 3),
            client_type_weight=round(client_type_weight, 3),
            trend=trend,
            breakdown={
                'base_score': round(base_score, 2),
                'adjustment_factor': round(time_decay_multiplier * complexity_bonus * client_type_weight, 3)
            },
            computed_at=datetime.now()
        )

    def _calculate_trend(
        self,
        employee: Dict[str, Any],
        project_history: Optional[List[Dict[str, Any]]] = None
    ) -> PerformanceTrend:
        """计算表现趋势"""
        if not project_history:
            return PerformanceTrend(
                employee_id=employee['id'],
                period_days=30,
                recent_score=0,
                previous_score=0,
                trend_direction="stable",
                trend_percentage=0,
                trend_analysis="数据不足"
            )

        now = datetime.now()
        recent_ratings = []
        previous_ratings = []

        for project in project_history:
            completed_date = project.get('completed_date')
            if completed_date:
                if isinstance(completed_date, str):
                    completed_date = datetime.fromisoformat(completed_date.replace('Z', '+00:00')).replace(tzinfo=None)

                days_ago = (now - completed_date).days
                rating = project.get('rating', 3)

                if days_ago <= 30:
                    recent_ratings.append(rating)
                elif days_ago <= 60:
                    previous_ratings.append(rating)

        recent_avg = sum(recent_ratings) / len(recent_ratings) if recent_ratings else 0
        previous_avg = sum(previous_ratings) / len(previous_ratings) if previous_ratings else recent_avg

        if previous_avg > 0:
            trend_pct = ((recent_avg - previous_avg) / previous_avg) * 100
        else:
            trend_pct = 0

        if trend_pct > 5:
            direction = "improving"
            analysis = f"表现呈上升趋势（+{trend_pct:.1f}%）"
        elif trend_pct < -5:
            direction = "declining"
            analysis = f"表现有所下滑（{trend_pct:.1f}%）"
        else:
            direction = "stable"
            analysis = "表现稳定"

        return PerformanceTrend(
            employee_id=employee['id'],
            period_days=30,
            recent_score=round(recent_avg * 20, 2),  # 转换为 0-100
            previous_score=round(previous_avg * 20, 2),
            trend_direction=direction,
            trend_percentage=round(trend_pct, 2),
            trend_analysis=analysis,
            computed_at=datetime.now()
        )


# ==================== 薪资分析服务 ====================

class SalaryAnalysisService:
    """薪资期望匹配分析服务"""

    def __init__(self):
        # 模拟市场基准数据
        self.market_benchmarks = {
            ('engineering', 'beginner'): {'p10': 15, 'p25': 20, 'p50': 25, 'p75': 30, 'p90': 40},
            ('engineering', 'intermediate'): {'p10': 25, 'p25': 35, 'p50': 45, 'p75': 60, 'p90': 80},
            ('engineering', 'advanced'): {'p10': 40, 'p25': 55, 'p50': 70, 'p75': 90, 'p90': 120},
            ('engineering', 'expert'): {'p10': 60, 'p25': 80, 'p50': 100, 'p75': 130, 'p90': 180},
            ('design', 'beginner'): {'p10': 12, 'p25': 18, 'p50': 22, 'p75': 28, 'p90': 35},
            ('design', 'intermediate'): {'p10': 20, 'p25': 28, 'p50': 35, 'p75': 45, 'p90': 60},
            ('design', 'advanced'): {'p10': 30, 'p25': 42, 'p50': 55, 'p75': 70, 'p90': 90},
            ('design', 'expert'): {'p10': 45, 'p25': 60, 'p50': 80, 'p75': 100, 'p90': 130},
            ('writing', 'beginner'): {'p10': 10, 'p25': 15, 'p50': 20, 'p75': 25, 'p90': 32},
            ('writing', 'intermediate'): {'p10': 18, 'p25': 25, 'p50': 32, 'p75': 42, 'p90': 55},
            ('writing', 'advanced'): {'p10': 25, 'p25': 35, 'p50': 45, 'p75': 60, 'p90': 80},
            ('writing', 'expert'): {'p10': 35, 'p25': 50, 'p50': 65, 'p75': 85, 'p90': 110},
        }

    def get_market_benchmark(self, category: str, level: str) -> Optional[SalaryBenchmark]:
        """获取市场基准数据"""
        key = (category.lower(), level.lower())
        data = self.market_benchmarks.get(key)

        if not data:
            # 默认基准
            data = {'p10': 20, 'p25': 30, 'p50': 40, 'p75': 55, 'p90': 75}

        return SalaryBenchmark(
            skill_category=category,
            experience_level=level,
            percentile_10=data['p10'],
            percentile_25=data['p25'],
            percentile_50=data['p50'],
            percentile_75=data['p75'],
            percentile_90=data['p90'],
            sample_size=1000,
            currency="USD",
            period="hourly",
            region="global",
            updated_at=datetime.now()
        )

    def analyze_employee_salary(
        self,
        employee: Dict[str, Any]
    ) -> EmployeeSalaryAnalysis:
        """
        分析员工薪资
        """
        current_rate = employee.get('hourly_rate', 0)
        category = employee.get('category', 'engineering')
        level = employee.get('level', 'intermediate')
        rating = employee.get('rating', 4.0)

        # 获取市场基准
        benchmark = self.get_market_benchmark(category, level)

        # 计算市场分位数
        if current_rate <= benchmark.percentile_10:
            percentile = 10
            strategy = "underpriced"
        elif current_rate <= benchmark.percentile_25:
            percentile = 17.5
            strategy = "underpriced"
        elif current_rate <= benchmark.percentile_50:
            percentile = 37.5 + (current_rate - benchmark.percentile_25) / (benchmark.percentile_50 - benchmark.percentile_25 + 0.01) * 25
            strategy = "fair"
        elif current_rate <= benchmark.percentile_75:
            percentile = 62.5 + (current_rate - benchmark.percentile_50) / (benchmark.percentile_75 - benchmark.percentile_50 + 0.01) * 25
            strategy = "fair"
        elif current_rate <= benchmark.percentile_90:
            percentile = 82.5 + (current_rate - benchmark.percentile_75) / (benchmark.percentile_90 - benchmark.percentile_75 + 0.01) * 15
            strategy = "premium"
        else:
            percentile = 95
            strategy = "overpriced"

        # 计算相对于中位数的百分比
        vs_median = ((current_rate - benchmark.percentile_50) / benchmark.percentile_50) * 100 if benchmark.percentile_50 > 0 else 0

        # 计算性价比分数（考虑技能和表现）
        skill_score = min(100, rating * 20)  # 0-100
        if strategy == "underpriced":
            value_score = min(100, skill_score * 1.3)  # 低价高价值
        elif strategy == "fair":
            value_score = skill_score
        elif strategy == "premium":
            value_score = skill_score * 0.9  # 溢价稍减价值
        else:
            value_score = skill_score * 0.7  # 过高定价降低价值

        # 生成建议
        suggestions = []
        if strategy == "underpriced":
            suggestions.append(f"当前薪资低于市场中位数的 {abs(vs_median):.0f}%")
            suggestions.append(f"建议调整薪资到 ${benchmark.percentile_50:.0f} - ${benchmark.percentile_75:.0f}/小时")
        elif strategy == "fair":
            suggestions.append("当前薪资处于市场合理范围")
            suggestions.append(f"可考虑在 ${benchmark.percentile_75:.0f} 范围内调整")
        elif strategy == "premium":
            suggestions.append(f"当前薪资高于市场中位数的 {vs_median:.0f}%")
            suggestions.append("确保高技能水平和高评价支撑溢价")
        else:
            suggestions.append(f"当前薪资显著高于市场水平（+{vs_median:.0f}%）")
            suggestions.append("建议重新评估定价策略或提升技能展示")

        return EmployeeSalaryAnalysis(
            employee_id=employee['id'],
            current_rate=current_rate,
            currency="USD",
            market_percentile=round(percentile, 1),
            vs_median=round(vs_median, 1),
            pricing_strategy=strategy,
            value_score=round(value_score, 1),
            suggested_rate_min=benchmark.percentile_25,
            suggested_rate_max=benchmark.percentile_75,
            pricing_suggestions=suggestions,
            analyzed_at=datetime.now()
        )


# ==================== 可解释性报告生成服务 ====================

class MatchExplanationService:
    """可解释性报告生成服务"""

    def __init__(self):
        self.vector_service = VectorMatchingService()
        self.cultural_service = CulturalFitService()
        self.performance_service = EnhancedPerformanceService()
        self.salary_service = SalaryAnalysisService()

    def generate_explanation(
        self,
        match_id: str,
        employee: Dict[str, Any],
        job: Dict[str, Any],
        match_scores: Dict[str, float]
    ) -> MatchExplanation:
        """
        生成匹配解释报告
        """
        # 分数分解
        breakdown = MatchScoreBreakdown(
            skill_match=match_scores.get('skill_score', 0),
            performance_match=match_scores.get('performance_score', 0),
            cultural_fit=match_scores.get('cultural_fit', 0),
            price_fit=match_scores.get('price_score', 0),
            availability_match=match_scores.get('availability_score', 0),
            vector_similarity=match_scores.get('vector_similarity', 0),
            weighted_score=match_scores.get('overall_score', 0)
        )

        # 计算总体分数
        overall_score = breakdown.weighted_score

        # 确定置信度
        if overall_score >= 80:
            confidence_level = "high"
            confidence_score = 0.9
        elif overall_score >= 60:
            confidence_level = "medium"
            confidence_score = 0.7
        else:
            confidence_level = "low"
            confidence_score = 0.5

        # 生成优势列表
        strengths = []
        if breakdown.skill_match >= 70:
            strengths.append(MatchStrength(
                category="skill",
                description=f"技能匹配度高（{breakdown.skill_match:.0f}%）",
                impact_score=8.0,
                evidence=self._generate_skill_evidence(employee, job)
            ))

        if breakdown.performance_match >= 70:
            strengths.append(MatchStrength(
                category="performance",
                description=f"历史表现优秀（{breakdown.performance_match:.0f}%）",
                impact_score=7.5,
                evidence=f"评分：{employee.get('rating', 0):.1f}/5, 完成率：{employee.get('completion_rate', 0)*100:.0f}%"
            ))

        if breakdown.vector_similarity >= 70:
            strengths.append(MatchStrength(
                category="semantic",
                description=f"语义相似度高（{breakdown.vector_similarity:.0f}%）",
                impact_score=7.0,
                evidence="技能和职位描述的语义匹配度高"
            ))

        if breakdown.price_fit >= 70:
            strengths.append(MatchStrength(
                category="price",
                description=f"价格在预算范围内（{breakdown.price_fit:.0f}%）",
                impact_score=6.0
            ))

        # 生成风险列表
        risks = []
        if breakdown.skill_match < 50:
            risks.append(MatchRisk(
                category="skill",
                description="技能匹配度较低",
                severity="high",
                mitigation="建议进行技能测试或面试验证",
                probability=0.7
            ))

        if breakdown.availability_match < 50:
            risks.append(MatchRisk(
                category="availability",
                description="员工当前可用性较低",
                severity="medium",
                mitigation="确认开始时间和工作进度安排",
                probability=0.5
            ))

        if breakdown.cultural_fit < 50:
            risks.append(MatchRisk(
                category="cultural",
                description="文化适配度可能存在风险",
                severity="medium",
                mitigation="建议前期加强沟通，明确期望",
                probability=0.4
            ))

        # 生成建议
        suggestions = []
        if overall_score >= 80:
            suggestions.append("强烈推荐，匹配度非常高")
        elif overall_score >= 60:
            suggestions.append("推荐，但建议进行面试确认")
        else:
            suggestions.append("谨慎考虑，建议寻找其他候选")

        if breakdown.vector_similarity > breakdown.skill_match:
            suggestions.append("语义分析显示潜在匹配，建议进一步评估")

        # 生成自然语言解释
        explanation_text = self._generate_natural_language_explanation(
            employee, job, breakdown, overall_score
        )

        # 提取关键因素
        key_factors = []
        if breakdown.skill_match >= 60:
            key_factors.append("技能匹配")
        if breakdown.performance_match >= 60:
            key_factors.append("优秀历史表现")
        if breakdown.vector_similarity >= 60:
            key_factors.append("语义高度相关")
        if breakdown.price_fit < 50:
            key_factors.append("价格考虑")

        explanation = MatchExplanation(
            id=str(uuid.uuid4()),
            match_id=match_id,
            employee_id=employee['id'],
            job_id=job.get('id', str(uuid.uuid4())),
            overall_score=round(overall_score, 2),
            confidence_level=confidence_level,
            confidence_score=confidence_score,
            score_breakdown=breakdown,
            strengths=strengths,
            risks=risks,
            suggestions=suggestions,
            explanation_text=explanation_text,
            key_factors=key_factors,
            generated_at=datetime.now(),
            model_version="v12.0.0"
        )

        p12_storage.save_match_explanation(explanation)
        return explanation

    def _generate_skill_evidence(self, employee: Dict[str, Any], job: Dict[str, Any]) -> str:
        """生成技能证据"""
        emp_skills = list(employee.get('skills', {}).keys())[:3]
        job_skills = list(job.get('required_skills', {}).keys())[:3]

        if emp_skills and job_skills:
            matched = set(emp_skills) & set(job_skills)
            if matched:
                return f"匹配技能：{', '.join(matched)}"

        return f"员工技能：{', '.join(emp_skills) if emp_skills else '未指定'}"

    def _generate_natural_language_explanation(
        self,
        employee: Dict[str, Any],
        job: Dict[str, Any],
        breakdown: MatchScoreBreakdown,
        overall_score: float
    ) -> str:
        """生成自然语言解释"""
        emp_name = employee.get('name', '该员工')
        job_title = job.get('title', '该职位')

        if overall_score >= 80:
            intro = f"{emp_name} 与 {job_title} 的匹配度非常高（{overall_score:.0f}%）。"
        elif overall_score >= 60:
            intro = f"{emp_name} 与 {job_title} 有较好的匹配度（{overall_score:.0f}%）。"
        else:
            intro = f"{emp_name} 与 {job_title} 的匹配度一般（{overall_score:.0f}%）。"

        # 分析主要优势
        highlights = []
        if breakdown.skill_match >= 70:
            highlights.append(f"技能匹配度{breakdown.skill_match:.0f}%")
        if breakdown.performance_match >= 70:
            highlights.append(f"历史表现{breakdown.performance_match:.0f}%")
        if breakdown.vector_similarity >= 70:
            highlights.append(f"语义相似度{breakdown.vector_similarity:.0f}%")

        if highlights:
            body = f"主要优势：{'、'.join(highlights)}。"
        else:
            body = "建议进一步评估候选人的适配性。"

        return intro + " " + body


# ==================== 统一服务接口 ====================

class MatchingV2Service:
    """匹配算法 V2 统一服务接口"""

    def __init__(self):
        self.vector_service = VectorMatchingService()
        self.cultural_service = CulturalFitService()
        self.performance_service = EnhancedPerformanceService()
        self.salary_service = SalaryAnalysisService()
        self.explanation_service = MatchExplanationService()

    def enhanced_match(
        self,
        job: Dict[str, Any],
        employees: List[Dict[str, Any]],
        include_explanation: bool = False
    ) -> List[Dict[str, Any]]:
        """
        增强版匹配算法

        整合所有 v12 新特性进行匹配
        """
        # 1. 向量相似度匹配
        vector_results = self.vector_service.match_by_vector_similarity(job, employees)

        # 2. 计算各项分数并整合
        enriched_results = []

        for emp_result in vector_results:
            employee = next((e for e in employees if e['id'] == emp_result['employee_id']), None)
            if not employee:
                continue

            # 获取向量相似度
            vector_similarity = emp_result['vector_similarity']

            # 计算性能分数
            perf_score = self.performance_service.calculate_weighted_performance(employee)

            # 计算薪资分析
            salary_analysis = self.salary_service.analyze_employee_salary(employee)

            # 综合分数（简化版，实际应该更复杂）
            overall_score = (
                vector_similarity * 0.35 +
                perf_score.overall_score * 0.30 +
                salary_analysis.value_score * 0.20 +
                employee.get('availability_score', 50) * 0.15
            )

            result = {
                'employee_id': employee['id'],
                'employee_name': employee.get('name', 'Unknown'),
                'overall_score': round(overall_score, 2),
                'vector_similarity': vector_similarity,
                'performance_score': perf_score.overall_score,
                'value_score': salary_analysis.value_score,
                'pricing_strategy': salary_analysis.pricing_strategy,
                'performance_trend': perf_score.trend.trend_direction if perf_score.trend else 'stable',
                'from_cache': emp_result.get('from_cache', False)
            }

            # 生成解释（可选）
            if include_explanation:
                match_scores = {
                    'skill_score': vector_similarity,
                    'performance_score': perf_score.overall_score,
                    'price_score': 100 - abs(salary_analysis.vs_median),
                    'availability_score': employee.get('availability_score', 50),
                    'vector_similarity': vector_similarity,
                    'overall_score': overall_score
                }
                explanation = self.explanation_service.generate_explanation(
                    match_id=str(uuid.uuid4()),
                    employee=employee,
                    job=job,
                    match_scores=match_scores
                )
                result['explanation_id'] = explanation.id

            enriched_results.append(result)

        # 按综合分数排序
        enriched_results.sort(key=lambda x: x['overall_score'], reverse=True)

        return enriched_results


# 全局服务实例
vector_matching_service = VectorMatchingService()
cultural_fit_service = CulturalFitService()
enhanced_performance_service = EnhancedPerformanceService()
salary_analysis_service = SalaryAnalysisService()
match_explanation_service = MatchExplanationService()
matching_v2_service = MatchingV2Service()
