"""
P7 智能匹配服务

实现基于技能、历史表现和用户偏好的智能匹配算法
"""
import math
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
import uuid


class MatchScore(BaseModel):
    """匹配评分"""
    employee_id: str
    employee_name: str
    overall_score: float  # 综合匹配度 (0-100)
    skill_score: float  # 技能匹配度 (0-100)
    performance_score: float  # 历史表现得分 (0-100)
    preference_score: float  # 用户偏好匹配度 (0-100)
    price_score: float  # 价格匹配度 (0-100)
    availability_score: float  # 可用性得分 (0-100)
    timezone_score: float = 0.0  # 时区匹配度 (0-100, v2 新增)
    language_score: float = 0.0  # 语言匹配度 (0-100, v2 新增)
    match_reasons: List[str] = Field(default_factory=list)  # 匹配理由
    match_details: Dict[str, Any] = Field(default_factory=dict)  # 匹配详情


class JobRequirement(BaseModel):
    """职位需求"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str  # 职位名称
    description: str  # 职位描述
    required_skills: Dict[str, int] = Field(default_factory=dict)  # 需要的技能 {技能名：重要程度 1-5}
    budget_min: Optional[float] = None  # 预算下限
    budget_max: Optional[float] = None  # 预算上限
    preferred_level: Optional[str] = None  # 偏好技能等级 (beginner/intermediate/advanced/expert)
    category: Optional[str] = None  # 职位分类
    urgency: int = 3  # 紧急程度 1-5
    preferences: Dict[str, Any] = Field(default_factory=dict)  # 其他偏好


class MatchingConfig(BaseModel):
    """匹配配置"""
    skill_weight: float = 0.30  # 技能匹配权重
    performance_weight: float = 0.20  # 历史表现权重
    preference_weight: float = 0.15  # 用户偏好权重
    price_weight: float = 0.15  # 价格匹配权重
    availability_weight: float = 0.10  # 可用性权重
    timezone_weight: float = 0.05  # 时区匹配权重 (v2 新增)
    language_weight: float = 0.05  # 语言匹配权重 (v2 新增)
    min_match_score: float = 30.0  # 最低匹配分数
    max_results: int = 20  # 最大返回结果数
    enable_cache: bool = True  # 启用缓存 (v2 新增)
    cache_ttl_seconds: int = 300  # 缓存过期时间 (v2 新增)


class MatchingService:
    """智能匹配服务"""

    def __init__(self):
        self.config = MatchingConfig()
        # 内存存储（实际应使用数据库）
        self._employees: Dict[str, Any] = {}
        self._job_requirements: Dict[str, JobRequirement] = {}
        self._user_preferences: Dict[str, Dict[str, Any]] = {}
        self._match_history: List[Dict[str, Any]] = []
        # v2 新增：匹配结果缓存
        self._match_cache: Dict[str, Dict[str, Any]] = {}

    def register_employee(self, employee: Dict[str, Any]):
        """注册员工到匹配系统"""
        self._employees[employee['id']] = employee

    def update_employee_stats(self, employee_id: str, stats: Dict[str, Any]):
        """更新员工统计数据"""
        if employee_id in self._employees:
            self._employees[employee_id].update(stats)

    def set_user_preference(self, user_id: str, preferences: Dict[str, Any]):
        """设置用户偏好"""
        self._user_preferences[user_id] = preferences

    def calculate_skill_score(self, employee: Dict[str, Any], requirement: JobRequirement) -> tuple[float, List[str], Dict[str, Any]]:
        """
        计算技能匹配分数

        返回：(分数，匹配理由，匹配详情)
        """
        if not requirement.required_skills:
            return 50.0, ["无特定技能要求"], {}

        employee_skills = employee.get('skills', {})
        matched_skills = []
        missing_skills = []
        skill_details = {}

        total_weight = 0
        matched_weight = 0

        for skill_name, importance in requirement.required_skills.items():
            total_weight += importance
            skill_details[skill_name] = {
                'required_level': importance,
                'has_skill': False,
                'employee_level': 0
            }

            # 检查员工是否有该技能
            if skill_name in employee_skills:
                emp_level = employee_skills[skill_name]
                # 将技能等级转换为数值
                level_map = {'beginner': 1, 'intermediate': 2, 'advanced': 3, 'expert': 4}
                emp_level_num = level_map.get(str(emp_level).lower(), 0)

                skill_details[skill_name]['has_skill'] = True
                skill_details[skill_name]['employee_level'] = emp_level_num

                # 技能等级达到要求才算匹配
                if emp_level_num >= 1:  # 至少有该技能
                    matched_skills.append(skill_name)
                    # 根据技能等级和重要程度计算匹配度
                    level_score = min(emp_level_num / 4.0, 1.0)
                    matched_weight += importance * level_score
            else:
                missing_skills.append(skill_name)

        if total_weight == 0:
            return 50.0, ["无特定技能权重"], skill_details

        # 计算技能匹配分数
        base_score = (matched_weight / total_weight) * 100

        # 生成匹配理由
        reasons = []
        if matched_skills:
            reasons.append(f"匹配 {len(matched_skills)} 项技能：{', '.join(matched_skills[:3])}")
        if missing_skills:
            reasons.append(f"缺少 {len(missing_skills)} 项技能")

        # 技能覆盖度奖励
        coverage_bonus = len(matched_skills) / len(requirement.required_skills) * 10 if len(requirement.required_skills) > 0 else 0
        final_score = min(base_score + coverage_bonus, 100.0)

        return final_score, reasons, skill_details

    def calculate_performance_score(self, employee: Dict[str, Any]) -> tuple[float, List[str], Dict[str, Any]]:
        """
        计算历史表现分数

        基于：评分、完成订单数、复雇率、响应时间
        """
        reasons = []
        details = {}

        # 评分得分 (0-40 分)
        rating = employee.get('rating', 0)
        rating_score = (rating / 5.0) * 40
        details['rating'] = rating
        if rating >= 4.5:
            reasons.append(f"优秀评级 ({rating:.1f}星)")
        elif rating >= 4.0:
            reasons.append(f"良好评级 ({rating:.1f}星)")

        # 订单数量得分 (0-25 分)
        total_jobs = employee.get('total_jobs', 0)
        jobs_score = min(total_jobs / 20.0, 1.0) * 25
        details['total_jobs'] = total_jobs
        if total_jobs >= 10:
            reasons.append(f"丰富经验 ({total_jobs}单)")
        elif total_jobs >= 5:
            reasons.append(f"一定经验 ({total_jobs}单)")

        # 复雇率得分 (0-20 分)
        rehire_rate = employee.get('rehire_rate', 0)
        rehire_score = rehire_rate * 20
        details['rehire_rate'] = rehire_rate

        # 完成率得分 (0-15 分)
        completion_rate = employee.get('completion_rate', 1.0)
        completion_score = completion_rate * 15
        details['completion_rate'] = completion_rate

        # 违规扣分
        violation_count = employee.get('violation_count', 0)
        violation_penalty = min(violation_count * 5, 20)
        details['violation_count'] = violation_count
        if violation_count > 0:
            reasons.append(f"有 {violation_count} 次违规记录")

        total_score = rating_score + jobs_score + rehire_score + completion_score - violation_penalty
        total_score = max(0, min(100, total_score))

        return total_score, reasons, details

    def calculate_preference_score(self, employee: Dict[str, Any], user_id: str) -> tuple[float, List[str], Dict[str, Any]]:
        """
        计算用户偏好匹配分数

        基于用户历史行为和显式偏好
        """
        reasons = []
        details = {}
        score = 50.0  # 默认分数

        preferences = self._user_preferences.get(user_id, {})

        if not preferences:
            return score, ["无历史偏好数据"], details

        # 类别偏好
        preferred_categories = preferences.get('preferred_categories', [])
        employee_category = employee.get('category', '')
        if employee_category in preferred_categories:
            score += 15
            reasons.append(f"符合偏好类别：{employee_category}")
        details['category_match'] = employee_category in preferred_categories

        # 价格偏好
        price_preference = preferences.get('price_range', {})
        employee_rate = employee.get('hourly_rate', 0)
        if price_preference:
            min_price = price_preference.get('min', 0)
            max_price = price_preference.get('max', float('inf'))
            if min_price <= employee_rate <= max_price:
                score += 15
                reasons.append("价格在偏好范围内")
                details['price_match'] = True
            else:
                details['price_match'] = False

        # 技能等级偏好
        level_preference = preferences.get('preferred_level', '')
        employee_level = employee.get('level', 'intermediate')
        if level_preference and employee_level == level_preference:
            score += 10
            reasons.append(f"符合偏好等级：{level_preference}")
        details['level_match'] = employee_level == level_preference

        # 历史合作偏好
        past_collaborations = preferences.get('past_collaborations', [])
        if employee.get('id') in past_collaborations:
            score += 20
            reasons.append("曾有愉快合作经历")
            details['past_collaboration'] = True

        score = min(100, max(0, score))
        return score, reasons, details

    def calculate_price_score(self, employee: Dict[str, Any], requirement: JobRequirement) -> tuple[float, List[str], Dict[str, Any]]:
        """
        计算价格匹配分数

        基于职位预算和员工时薪
        """
        reasons = []
        details = {}

        employee_rate = employee.get('hourly_rate', 0)
        budget_min = requirement.budget_min
        budget_max = requirement.budget_max

        if budget_min is None and budget_max is None:
            # 无预算限制，基于市场均价评分
            market_avg = employee.get('market_avg_rate', 50)
            if employee_rate <= market_avg:
                score = 70 + (market_avg - employee_rate) / market_avg * 30
            else:
                score = 70 - (employee_rate - market_avg) / market_avg * 30
            reasons.append("无预算限制，按市场价评分")
        elif budget_max is not None:
            if employee_rate <= budget_max:
                # 在预算内，越接近上限分数越高（质量可能更好）
                if budget_min and employee_rate >= budget_min:
                    # 在预算范围内
                    score = 70 + (employee_rate - budget_min) / (budget_max - budget_min + 0.01) * 30
                    reasons.append("价格在预算范围内")
                else:
                    score = 50 + (budget_max - employee_rate) / budget_max * 20
                    reasons.append("价格低于预算上限")
            else:
                # 超出预算
                over_ratio = (employee_rate - budget_max) / budget_max
                score = max(0, 50 - over_ratio * 100)
                reasons.append(f"价格超出预算 {over_ratio*100:.0f}%")
        else:
            # 只有最低预算
            if employee_rate >= budget_min:
                score = 70
                reasons.append("价格达到最低预算")
            else:
                score = 30
                reasons.append("价格低于最低预算")

        details['employee_rate'] = employee_rate
        details['budget_min'] = budget_min
        details['budget_max'] = budget_max

        return min(100, max(0, score)), reasons, details

    def calculate_availability_score(self, employee: Dict[str, Any]) -> tuple[float, List[str], Dict[str, Any]]:
        """
        计算可用性分数

        基于员工当前状态和响应时间
        """
        reasons = []
        details = {}

        status = employee.get('status', 'offline')

        if status == 'available':
            score = 100
            reasons.append("当前可立即工作")
        elif status == 'training':
            score = 60
            reasons.append("正在训练中，稍后可用")
        elif status == 'hired':
            # 检查是否有并发能力
            concurrent = employee.get('concurrent_capacity', 0)
            if concurrent > 0:
                score = 70
                reasons.append("可并发处理任务")
            else:
                score = 20
                reasons.append("当前已被雇佣")
        else:  # offline
            score = 0
            reasons.append("当前离线")

        details['status'] = status

        # 响应时间奖励
        avg_response_time = employee.get('avg_response_time_hours')
        if avg_response_time is not None:
            if avg_response_time <= 1:
                score = min(100, score + 10)
                reasons.append("响应迅速 (1 小时内)")
                details['response_level'] = 'fast'
            elif avg_response_time <= 4:
                score = min(100, score + 5)
                reasons.append("响应及时 (4 小时内)")
                details['response_level'] = 'normal'
            elif avg_response_time <= 24:
                details['response_level'] = 'slow'
            else:
                score = max(0, score - 10)
                reasons.append("响应较慢")
                details['response_level'] = 'very_slow'

        return min(100, max(0, score)), reasons, details

    def calculate_timezone_score(self, employee: Dict[str, Any], requirement: JobRequirement) -> tuple[float, List[str], Dict[str, Any]]:
        """
        计算时区匹配分数 (v2 新增)

        基于员工时区与工作时间的匹配程度
        """
        reasons = []
        details = {}

        employee_timezone = employee.get('timezone', 'UTC')
        preferred_timezone = requirement.preferences.get('preferred_timezone')

        if not preferred_timezone:
            return 50.0, ["无时区偏好"], {'timezone_match': 'neutral'}

        # 时区匹配度计算
        timezone_offsets = {
            'UTC': 0, 'UTC+1': 1, 'UTC+2': 2, 'UTC+3': 3, 'UTC+4': 4, 'UTC+5': 5,
            'UTC+6': 6, 'UTC+7': 7, 'UTC+8': 8, 'UTC+9': 9, 'UTC+10': 10,
            'UTC-1': -1, 'UTC-2': -2, 'UTC-3': -3, 'UTC-4': -4, 'UTC-5': -5,
            'UTC-6': -6, 'UTC-7': -7, 'UTC-8': -8, 'UTC-9': -9, 'UTC-10': -10
        }

        emp_offset = timezone_offsets.get(employee_timezone, 0)
        pref_offset = timezone_offsets.get(preferred_timezone, 0)
        timezone_diff = abs(emp_offset - pref_offset)

        if timezone_diff == 0:
            score = 100
            reasons.append(f"相同时区 ({employee_timezone})")
            details['timezone_match'] = 'perfect'
        elif timezone_diff <= 2:
            score = 80
            reasons.append(f"相邻时区 (相差{timezone_diff}小时)")
            details['timezone_match'] = 'good'
        elif timezone_diff <= 4:
            score = 60
            reasons.append(f"可接受时差 (相差{timezone_diff}小时)")
            details['timezone_match'] = 'acceptable'
        elif timezone_diff <= 8:
            score = 40
            reasons.append(f"较大时差 (相差{timezone_diff}小时)")
            details['timezone_match'] = 'fair'
        else:
            score = 20
            reasons.append(f"时差较大 (相差{timezone_diff}小时)")
            details['timezone_match'] = 'poor'

        # 检查重叠工作时间
        overlap_hours = max(0, 8 - timezone_diff)
        if overlap_hours >= 4:
            score = min(100, score + 10)
            reasons.append(f"有{overlap_hours}小时重叠工作时间")
            details['overlap_hours'] = overlap_hours

        return min(100, max(0, score)), reasons, details

    def calculate_language_score(self, employee: Dict[str, Any], requirement: JobRequirement) -> tuple[float, List[str], Dict[str, Any]]:
        """
        计算语言匹配分数 (v2 新增)

        基于员工语言能力与职位语言要求
        """
        reasons = []
        details = {}

        employee_languages = employee.get('languages', ['zh'])
        required_language = requirement.preferences.get('required_language', 'zh')
        preferred_languages = requirement.preferences.get('preferred_languages', [])

        if required_language in employee_languages:
            score = 100
            reasons.append(f"满足语言要求 ({required_language})")
            details['language_match'] = 'perfect'

            if len(employee_languages) > 1:
                score = min(100, score + 5)
                reasons.append(f"多语言能力 ({len(employee_languages)}种)")
                details['multilingual'] = True
        elif preferred_languages and any(lang in employee_languages for lang in preferred_languages):
            score = 70
            matched_langs = [lang for lang in preferred_languages if lang in employee_languages]
            reasons.append(f"匹配偏好语言 ({', '.join(matched_langs)})")
            details['language_match'] = 'partial'
        else:
            score = 30
            reasons.append(f"不满足语言要求 (需要{required_language})")
            details['language_match'] = 'poor'

        language_proficiency = employee.get('language_proficiency', {})
        if required_language in language_proficiency:
            proficiency = language_proficiency[required_language]
            proficiency_map = {'native': 100, 'fluent': 90, 'intermediate': 70, 'basic': 50, 'beginner': 30}
            proficiency_bonus = proficiency_map.get(proficiency, 50) - 50
            score = min(100, score + proficiency_bonus * 0.3)
            details['proficiency'] = proficiency

        return min(100, max(0, score)), reasons, details

    def calculate_time_availability_score(self, employee: Dict[str, Any], requirement: JobRequirement) -> tuple[float, List[str], Dict[str, Any]]:
        """
        计算时间可用性分数 (v2 新增)

        基于员工可用工时与职位需求工时的匹配
        """
        reasons = []
        details = {}

        employee_available_hours = employee.get('available_hours_per_week', 40)
        required_hours = requirement.preferences.get('required_hours_per_week', 40)
        employee_schedule = employee.get('weekly_schedule', {})

        if employee_available_hours >= required_hours:
            score = 100
            reasons.append(f"工时充足 ({employee_available_hours}小时/周)")
            details['hours_match'] = 'sufficient'
        else:
            ratio = employee_available_hours / required_hours
            if ratio >= 0.8:
                score = 70
                reasons.append(f"工时基本满足 ({ratio*100:.0f}%)")
                details['hours_match'] = 'partial'
            elif ratio >= 0.5:
                score = 50
                reasons.append(f"工时不足 ({ratio*100:.0f}%)")
                details['hours_match'] = 'insufficient'
            else:
                score = 20
                reasons.append(f"工时严重不足 ({ratio*100:.0f}%)")
                details['hours_match'] = 'poor'

        if employee_schedule:
            required_schedule = requirement.preferences.get('required_schedule', {})
            conflicts = []
            for day, hours in required_schedule.items():
                if day in employee_schedule:
                    emp_hours = set(employee_schedule[day])
                    req_hours = set(hours)
                    if emp_hours & req_hours:
                        conflicts.append(day)

            if conflicts:
                score = max(0, score - len(conflicts) * 10)
                reasons.append(f"日程冲突：{', '.join(conflicts)}")
                details['schedule_conflicts'] = conflicts

        return min(100, max(0, score)), reasons, details

    def match_employees(self, requirement: JobRequirement, user_id: Optional[str] = None,
                        config: Optional[MatchingConfig] = None) -> List[MatchScore]:
        """
        匹配员工与职位需求

        Args:
            requirement: 职位需求
            user_id: 用户 ID（用于获取用户偏好）
            config: 匹配配置（可选，使用默认配置）

        Returns:
            按匹配度排序的员工列表
        """
        if config is None:
            config = self.config

        # v2 新增：检查缓存
        cache_key = f"{requirement.id}:{user_id}"
        if config.enable_cache and cache_key in self._match_cache:
            cached_result = self._match_cache[cache_key]
            cache_age = (datetime.now() - cached_result['timestamp']).total_seconds()
            if cache_age < config.cache_ttl_seconds:
                return cached_result['matches']

        matches = []
        weight_sum = (
            config.skill_weight + config.performance_weight + config.preference_weight +
            config.price_weight + config.availability_weight + config.timezone_weight + config.language_weight
        )

        for emp_id, employee in self._employees.items():
            # 计算各项分数
            skill_score, skill_reasons, skill_details = self.calculate_skill_score(employee, requirement)
            perf_score, perf_reasons, perf_details = self.calculate_performance_score(employee)
            pref_score, pref_reasons, pref_details = self.calculate_preference_score(employee, user_id) if user_id else (50.0, [], {})
            price_score, price_reasons, price_details = self.calculate_price_score(employee, requirement)
            avail_score, avail_reasons, avail_details = self.calculate_availability_score(employee)
            # v2 新增：时区、语言、时间可用性匹配
            timezone_score, timezone_reasons, timezone_details = self.calculate_timezone_score(employee, requirement)
            language_score, language_reasons, language_details = self.calculate_language_score(employee, requirement)
            time_avail_score, time_avail_reasons, time_avail_details = self.calculate_time_availability_score(employee, requirement)

            # 计算综合分数
            overall_score = (
                skill_score * config.skill_weight +
                perf_score * config.performance_weight +
                pref_score * config.preference_weight +
                price_score * config.price_weight +
                avail_score * config.availability_weight +
                timezone_score * config.timezone_weight +
                language_score * config.language_weight
            )

            # 归一化分数（如果权重和不等于 1）
            if weight_sum > 0 and weight_sum != 1.0:
                overall_score /= weight_sum

            # 过滤低于最低分数的
            if overall_score < config.min_match_score:
                continue

            # 收集所有理由
            all_reasons = skill_reasons + perf_reasons + pref_reasons + price_reasons + avail_reasons + timezone_reasons + language_reasons

            match = MatchScore(
                employee_id=employee['id'],
                employee_name=employee.get('name', 'Unknown'),
                overall_score=round(overall_score, 2),
                skill_score=round(skill_score, 2),
                performance_score=round(perf_score, 2),
                preference_score=round(pref_score, 2),
                price_score=round(price_score, 2),
                availability_score=round(avail_score, 2),
                timezone_score=round(timezone_score, 2),
                language_score=round(language_score, 2),
                match_reasons=all_reasons[:5],
                match_details={
                    'skills': skill_details,
                    'performance': perf_details,
                    'preferences': pref_details,
                    'price': price_details,
                    'availability': avail_details,
                    'timezone': timezone_details,
                    'language': language_details,
                    'time_availability': time_avail_details
                }
            )
            matches.append(match)

        # 按综合分数排序
        matches.sort(key=lambda x: x.overall_score, reverse=True)

        # 限制返回数量
        result = matches[:config.max_results]

        # v2 新增：缓存结果
        if config.enable_cache:
            self._match_cache[cache_key] = {
                'matches': result,
                'timestamp': datetime.now()
            }

        return result

    def get_recommendation_explanation(self, match: MatchScore) -> Dict[str, Any]:
        """
        获取推荐解释

        用于向用户解释为什么推荐这个员工
        """
        return {
            'employee_id': match.employee_id,
            'employee_name': match.employee_name,
            'overall_match': f"{match.overall_score:.0f}%",
            'top_reasons': match.match_reasons[:3],
            'score_breakdown': {
                'skill_match': f"{match.skill_score:.0f}%",
                'performance': f"{match.performance_score:.0f}%",
                'preferences': f"{match.preference_score:.0f}%",
                'price_fit': f"{match.price_score:.0f}%",
                'availability': f"{match.availability_score:.0f}%"
            },
            'strengths': [r for r in match.match_reasons if not r.startswith('缺少') and not r.startswith('有') and not r.startswith('当前')],
            'considerations': [r for r in match.match_reasons if r.startswith('缺少') or r.startswith('有') or r.startswith('当前')]
        }

    def record_match_feedback(self, requirement_id: str, employee_id: str,
                              user_selected: bool, feedback: Optional[str] = None):
        """
        记录匹配反馈

        用于优化匹配算法
        """
        self._match_history.append({
            'requirement_id': requirement_id,
            'employee_id': employee_id,
            'user_selected': user_selected,
            'feedback': feedback,
            'timestamp': datetime.now()
        })

    def get_match_statistics(self, requirement_id: Optional[str] = None) -> Dict[str, Any]:
        """
        获取匹配统计信息
        """
        if requirement_id:
            matches = [m for m in self._match_history if m.get('requirement_id') == requirement_id]
        else:
            matches = self._match_history

        if not matches:
            return {'total_matches': 0, 'selection_rate': 0}

        selected = sum(1 for m in matches if m['user_selected'])

        return {
            'total_matches': len(matches),
            'selected': selected,
            'not_selected': len(matches) - selected,
            'selection_rate': selected / len(matches) if matches else 0
        }


# 全局匹配服务实例
matching_service = MatchingService()
