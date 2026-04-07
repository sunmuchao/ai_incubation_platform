"""
P11: AI 员工市场增强服务
版本：v11.0.0
功能：排行榜、精选推荐、技能趋势、个性化推荐
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import json

from models.employee import AIEmployee, EmployeeStatus, SkillLevel
from models.p11_models import (
    MarketRanking, RankingCategory, RankingPeriod,
    FeaturedEmployee, SkillTrend, MarketInsight,
    UserBehavior, PersonalizedRecommendation, RecommendationType,
    RankingQueryRequest, MarketSearchRequest, MarketStatsResponse,
    RankingResponse, FeaturedListResponse, TrendingSkillsResponse
)
from services.employee_service import employee_service


class MarketEnhancedService:
    """市场增强服务"""

    def __init__(self):
        # 内存存储（生产环境应使用数据库）
        self._rankings: Dict[str, MarketRanking] = {}
        self._featured: Dict[str, FeaturedEmployee] = {}
        self._skill_trends: Dict[str, SkillTrend] = {}
        self._user_behaviors: List[UserBehavior] = []
        self._recommendations: Dict[str, PersonalizedRecommendation] = {}

        # 缓存
        self._market_stats_cache: Optional[Dict[str, Any]] = None
        self._market_stats_cached_at: Optional[datetime] = None
        self._cache_ttl_seconds = 300  # 5 分钟缓存

    # ==================== 排行榜功能 ====================

    def calculate_ranking(self, category: RankingCategory, period: RankingPeriod,
                         skill_tag: Optional[str] = None,
                         industry: Optional[str] = None) -> MarketRanking:
        """计算排行榜"""
        # 获取所有可用员工
        employees = employee_service.list_employees(EmployeeStatus.AVAILABLE)

        if not employees:
            return self._create_empty_ranking(category, period, skill_tag, industry)

        # 根据分类过滤
        if category == RankingCategory.BY_SKILL and skill_tag:
            employees = [e for e in employees if skill_tag.lower() in [s.lower() for s in e.skills.keys()]]
        elif category == RankingCategory.BY_INDUSTRY and industry:
            # 暂时简化处理，实际应用需要行业字段
            pass

        # 计算排名分数
        scored_employees = []
        for emp in employees:
            score = self._calculate_employee_score(emp, category, period)
            scored_employees.append({
                "employee_id": emp.id,
                "name": emp.name,
                "avatar": emp.avatar,
                "score": round(score, 2),
                "rating": emp.rating,
                "total_jobs": emp.total_jobs,
                "hourly_rate": emp.hourly_rate,
                "skills": list(emp.skills.keys())[:5],  # 只显示前 5 个技能
            })

        # 排序
        scored_employees.sort(key=lambda x: x["score"], reverse=True)

        # 添加排名变化（简化版本，实际应用需要历史数据对比）
        for i, emp in enumerate(scored_employees):
            emp["rank"] = i + 1
            emp["change"] = "0"  # 实际应用需要对比上期排名

        # 创建排行榜
        now = datetime.now()
        ranking = MarketRanking(
            category=category,
            period=period,
            skill_tag=skill_tag,
            industry=industry,
            rankings=scored_employees[:100],  # 只保留前 100 名
            calculated_at=now,
            expires_at=self._get_period_end(period, now),
            total_employees=len(employees)
        )

        # 存储排行榜
        ranking_key = self._get_ranking_key(category, period, skill_tag, industry)
        self._rankings[ranking_key] = ranking

        return ranking

    def get_ranking(self, category: RankingCategory, period: RankingPeriod,
                   skill_tag: Optional[str] = None,
                   industry: Optional[str] = None,
                   limit: int = 10) -> Optional[MarketRanking]:
        """获取排行榜（优先使用缓存）"""
        ranking_key = self._get_ranking_key(category, period, skill_tag, industry)

        # 检查缓存
        if ranking_key in self._rankings:
            ranking = self._rankings[ranking_key]
            # 检查是否过期
            if ranking.expires_at > datetime.now() and ranking.is_active:
                return RankingResponse(
                    category=ranking.category.value,
                    period=ranking.period.value,
                    skill_tag=ranking.skill_tag,
                    industry=ranking.industry,
                    rankings=ranking.rankings[:limit],
                    total_employees=ranking.total_employees,
                    calculated_at=ranking.calculated_at,
                    expires_at=ranking.expires_at,
                    algorithm_version=ranking.algorithm_version
                )

        # 缓存未命中或过期，重新计算
        ranking = self.calculate_ranking(category, period, skill_tag, industry)
        return RankingResponse(
            category=ranking.category.value,
            period=ranking.period.value,
            skill_tag=ranking.skill_tag,
            industry=ranking.industry,
            rankings=ranking.rankings[:limit],
            total_employees=ranking.total_employees,
            calculated_at=ranking.calculated_at,
            expires_at=ranking.expires_at,
            algorithm_version=ranking.algorithm_version
        )

    def _calculate_employee_score(self, employee: AIEmployee,
                                  category: RankingCategory,
                                  period: RankingPeriod) -> float:
        """计算员工排名分数"""
        # 基础分数：评级 (0-5) * 20 = 0-100
        base_score = employee.rating * 20

        # 经验分数：log(工作次数 + 1) * 10
        import math
        experience_score = math.log(employee.total_jobs + 1) * 10

        # 收入分数：归一化处理
        income_score = min(employee.total_earnings / 100, 20)

        # 新人奖励（针对新人榜）
        newcomer_bonus = 0
        if category == RankingCategory.NEWCOMER:
            # 创建时间在 7 天内且工作次数少于 5 次
            if (datetime.now() - employee.created_at).days <= 7 and employee.total_jobs < 5:
                newcomer_bonus = 15

        # 增长奖励（针对增长最快榜）
        growth_bonus = 0
        if category == RankingCategory.FASTEST_GROWING:
            # 简化版本，实际应用需要历史数据
            growth_bonus = min(employee.total_jobs * 2, 20)

        # 综合分数
        total_score = base_score + experience_score + income_score + newcomer_bonus + growth_bonus

        return total_score

    def _get_ranking_key(self, category: RankingCategory, period: RankingPeriod,
                        skill_tag: Optional[str], industry: Optional[str]) -> str:
        """生成排行榜缓存键"""
        key_parts = [category.value, period.value]
        if skill_tag:
            key_parts.append(f"skill_{skill_tag}")
        if industry:
            key_parts.append(f"industry_{industry}")
        return "_".join(key_parts)

    def _get_period_end(self, period: RankingPeriod, now: datetime) -> datetime:
        """计算周期结束时间"""
        if period == RankingPeriod.DAILY:
            return now + timedelta(days=1)
        elif period == RankingPeriod.WEEKLY:
            return now + timedelta(weeks=1)
        elif period == RankingPeriod.MONTHLY:
            return now + timedelta(days=30)
        else:  # ALL_TIME
            return now + timedelta(days=365)

    def _create_empty_ranking(self, category: RankingCategory, period: RankingPeriod,
                             skill_tag: Optional[str], industry: Optional[str]) -> MarketRanking:
        """创建空排行榜"""
        now = datetime.now()
        return MarketRanking(
            category=category,
            period=period,
            skill_tag=skill_tag,
            industry=industry,
            rankings=[],
            calculated_at=now,
            expires_at=self._get_period_end(period, now),
            total_employees=0
        )

    # ==================== 精选推荐功能 ====================

    def create_featured_employee(self, employee_id: str, reason: str,
                                 featured_type: str, priority: int = 0,
                                 highlight_title: Optional[str] = None,
                                 highlight_description: Optional[str] = None,
                                 badge: Optional[str] = None,
                                 duration_days: int = 7,
                                 created_by: str = "admin") -> FeaturedEmployee:
        """创建精选员工"""
        now = datetime.now()
        featured = FeaturedEmployee(
            employee_id=employee_id,
            reason=reason,
            featured_type=featured_type,
            priority=priority,
            highlight_title=highlight_title,
            highlight_description=highlight_description,
            badge=badge,
            start_at=now,
            end_at=now + timedelta(days=duration_days),
            created_by=created_by
        )
        self._featured[featured.id] = featured
        return featured

    def get_featured_employees(self, limit: int = 10,
                               featured_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取精选员工列表"""
        now = datetime.now()
        results = []

        for featured in self._featured.values():
            # 过滤过期和未激活的
            if not featured.is_active or featured.end_at < now:
                continue

            # 按类型过滤
            if featured_type and featured.featured_type != featured_type:
                continue

            # 获取员工详情
            employee = employee_service.get_employee(featured.employee_id)
            if employee:
                results.append({
                    "id": featured.id,
                    "employee": self._employee_to_dict(employee),
                    "reason": featured.reason,
                    "featured_type": featured.featured_type,
                    "priority": featured.priority,
                    "highlight_title": featured.highlight_title,
                    "highlight_description": featured.highlight_description,
                    "badge": featured.badge,
                    "click_count": featured.click_count,
                    "conversion_count": featured.conversion_count
                })

        # 按优先级排序
        results.sort(key=lambda x: x["priority"], reverse=True)
        return results[:limit]

    def track_featured_click(self, featured_id: str):
        """追踪精选员工点击"""
        if featured_id in self._featured:
            self._featured[featured_id].click_count += 1

    def track_featured_conversion(self, featured_id: str):
        """追踪精选员工转化"""
        if featured_id in self._featured:
            self._featured[featured_id].conversion_count += 1

    # ==================== 技能趋势功能 ====================

    def calculate_skill_trends(self, period_days: int = 7) -> List[SkillTrend]:
        """计算技能趋势"""
        employees = employee_service.list_employees(EmployeeStatus.AVAILABLE)

        # 统计技能数据
        skill_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "count": 0,
            "total_jobs": 0,
            "total_earnings": 0.0,
            "search_count": 0,
            "levels": []
        })

        for emp in employees:
            for skill_name, skill_level in emp.skills.items():
                skill_stats[skill_name]["count"] += 1
                skill_stats[skill_name]["total_jobs"] += emp.total_jobs
                skill_stats[skill_name]["total_earnings"] += emp.total_earnings
                skill_stats[skill_name]["levels"].append(skill_level.value)

        # 生成趋势数据
        now = datetime.now()
        trends = []
        prev_trends = self._skill_trends.copy()

        for skill_name, stats in skill_stats.items():
            # 计算平均时薪
            avg_hourly_rate = stats["total_earnings"] / max(stats["total_jobs"], 1)

            # 计算趋势得分
            demand_score = min(stats["count"] * 2, 50)  # 需求得分
            growth_score = min(stats["total_jobs"] / max(stats["count"], 1) * 5, 30)  # 增长得分
            value_score = min(avg_hourly_rate / 10, 20)  # 价值得分

            trend_score = demand_score + growth_score + value_score

            # 确定趋势方向
            prev_trend = prev_trends.get(skill_name)
            if prev_trend:
                if trend_score > prev_trend.trend_score * 1.1:
                    trend_direction = "up"
                    rank_change = 1
                elif trend_score < prev_trend.trend_score * 0.9:
                    trend_direction = "down"
                    rank_change = -1
                else:
                    trend_direction = "stable"
                    rank_change = 0
            else:
                trend_direction = "up"
                rank_change = 1

            trend = SkillTrend(
                skill_name=skill_name,
                category="technical",  # 简化处理
                trend_score=round(trend_score, 2),
                growth_rate=round(trend_score / max(prev_trend.trend_score if prev_trend else trend_score, 1) - 1, 4),
                demand_index=round(demand_score, 2),
                supply_index=round(stats["count"], 2),
                search_count=stats["search_count"],
                hire_count=stats["total_jobs"],
                avg_hourly_rate=round(avg_hourly_rate, 2),
                trend_direction=trend_direction,
                rank_change=rank_change,
                period_start=now - timedelta(days=period_days),
                period_end=now
            )

            self._skill_trends[skill_name] = trend
            trends.append(trend)

        # 按趋势得分排序
        trends.sort(key=lambda t: t.trend_score, reverse=True)
        return trends

    def get_trending_skills(self, limit: int = 10,
                           trend_direction: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取热门技能"""
        trends = self.calculate_skill_trends()
        results = []

        for trend in trends:
            if trend_direction and trend.trend_direction != trend_direction:
                continue

            results.append({
                "skill_name": trend.skill_name,
                "category": trend.category,
                "trend_score": trend.trend_score,
                "growth_rate": f"{trend.growth_rate * 100:.1f}%",
                "demand_index": trend.demand_index,
                "supply_index": trend.supply_index,
                "avg_hourly_rate": trend.avg_hourly_rate,
                "trend_direction": trend.trend_direction,
                "rank_change": trend.rank_change
            })

        return results[:limit]

    # ==================== 个性化推荐功能 ====================

    def record_user_behavior(self, user_id: str, tenant_id: str,
                            behavior_type: str, target_type: str,
                            target_id: str, context: Optional[Dict[str, Any]] = None,
                            result: Optional[str] = None):
        """记录用户行为"""
        behavior = UserBehavior(
            user_id=user_id,
            tenant_id=tenant_id,
            behavior_type=behavior_type,
            target_type=target_type,
            target_id=target_id,
            context=context or {},
            result=result
        )
        self._user_behaviors.append(behavior)

        # 清理旧数据（保留最近 1000 条）
        if len(self._user_behaviors) > 1000:
            self._user_behaviors = self._user_behaviors[-1000:]

    def get_personalized_recommendations(self, user_id: str,
                                         limit: int = 10) -> PersonalizedRecommendation:
        """获取个性化推荐"""
        now = datetime.now()

        # 检查缓存
        if user_id in self._recommendations:
            rec = self._recommendations[user_id]
            if rec.expires_at > now:
                return rec

        # 获取用户行为
        user_behaviors = [b for b in self._user_behaviors if b.user_id == user_id]

        # 分析用户偏好
        user_preferences = self._analyze_user_preferences(user_behaviors)

        # 获取候选员工
        candidates = employee_service.list_employees(EmployeeStatus.AVAILABLE)

        # 计算匹配分数
        scored_candidates = []
        for emp in candidates:
            score = self._calculate_match_score(emp, user_preferences)
            if score > 0.3:  # 过滤低分
                scored_candidates.append({
                    "employee_id": emp.id,
                    "score": round(score, 3),
                    "reason": self._generate_recommendation_reason(emp, user_preferences)
                })

        # 排序
        scored_candidates.sort(key=lambda x: x["score"], reverse=True)

        # 创建推荐结果
        recommendation = PersonalizedRecommendation(
            user_id=user_id,
            recommendation_type=RecommendationType.PERSONALIZED,
            recommendations=scored_candidates[:limit],
            algorithm="content_based",
            factors=user_preferences.get("factors", {}),
            generated_at=now,
            expires_at=now + timedelta(hours=1)
        )

        self._recommendations[user_id] = recommendation
        return recommendation

    def _analyze_user_preferences(self, behaviors: List[UserBehavior]) -> Dict[str, Any]:
        """分析用户偏好"""
        if not behaviors:
            return {
                "preferred_skills": [],
                "price_range": {"min": 0, "max": 100},
                "min_rating": 4.0,
                "factors": {"skill_match": 0.4, "price_preference": 0.2, "rating": 0.2, "past_hires": 0.2}
            }

        # 统计技能偏好
        skill_counts: Dict[str, int] = defaultdict(int)
        prices = []
        ratings = []

        for behavior in behaviors:
            if behavior.target_type == "employee":
                employee = employee_service.get_employee(behavior.target_id)
                if employee:
                    for skill in employee.skills.keys():
                        skill_counts[skill] += 1
                    prices.append(employee.hourly_rate)
                    ratings.append(employee.rating)

        # 提取 top 技能
        preferred_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            "preferred_skills": [s[0] for s in preferred_skills],
            "avg_price": sum(prices) / len(prices) if prices else 50,
            "avg_rating": sum(ratings) / len(ratings) if ratings else 4.0,
            "factors": {"skill_match": 0.4, "price_preference": 0.2, "rating": 0.2, "past_hires": 0.2}
        }

    def _calculate_match_score(self, employee: AIEmployee,
                               user_preferences: Dict[str, Any]) -> float:
        """计算匹配分数"""
        score = 0.0

        # 技能匹配 (40%)
        preferred_skills = set(user_preferences.get("preferred_skills", []))
        employee_skills = set(employee.skills.keys())
        skill_overlap = len(preferred_skills & employee_skills)
        skill_score = min(skill_overlap / max(len(preferred_skills), 1), 1.0)
        score += skill_score * 0.4

        # 价格匹配 (20%)
        avg_price = user_preferences.get("avg_price", 50)
        if avg_price > 0:
            price_diff = abs(employee.hourly_rate - avg_price) / avg_price
            price_score = max(0, 1 - price_diff)
            score += price_score * 0.2

        # 评级匹配 (20%)
        rating_score = employee.rating / 5.0
        score += rating_score * 0.2

        # 历史雇佣 (20%)
        # 简化处理：有历史雇佣记录则加分
        hire_score = min(employee.total_jobs / 10, 1.0)
        score += hire_score * 0.2

        return score

    def _generate_recommendation_reason(self, employee: AIEmployee,
                                        user_preferences: Dict[str, Any]) -> str:
        """生成推荐理由"""
        preferred_skills = set(user_preferences.get("preferred_skills", []))
        employee_skills = set(employee.skills.keys())
        overlap = preferred_skills & employee_skills

        if overlap:
            return f"与你关注的 {', '.join(list(overlap)[:2])} 技能匹配"
        elif employee.rating >= 4.8:
            return f"高评分 AI 员工 ({employee.rating}星)"
        elif employee.total_jobs > 20:
            return f"热门选择 (已服务{employee.total_jobs}个客户)"
        else:
            return "基于你的偏好推荐"

    def _employee_to_dict(self, employee: AIEmployee) -> Dict[str, Any]:
        """将员工对象转为字典"""
        return {
            "id": employee.id,
            "name": employee.name,
            "avatar": employee.avatar,
            "description": employee.description,
            "skills": list(employee.skills.keys()),
            "hourly_rate": employee.hourly_rate,
            "rating": employee.rating,
            "total_jobs": employee.total_jobs,
            "status": employee.status.value
        }

    # ==================== 市场统计功能 ====================

    def get_market_stats(self, force_refresh: bool = False) -> MarketStatsResponse:
        """获取市场统计数据"""
        now = datetime.now()

        # 检查缓存
        if not force_refresh and self._market_stats_cache:
            if (now - self._market_stats_cached_at).total_seconds() < self._cache_ttl_seconds:
                return MarketStatsResponse(**self._market_stats_cache)

        # 获取所有员工
        employees = employee_service.list_employees(EmployeeStatus.AVAILABLE)

        if not employees:
            return MarketStatsResponse(
                total_employees=0,
                active_employees=0,
                total_categories=0,
                total_skills=0,
                avg_hourly_rate=0,
                median_hourly_rate=0,
                top_categories=[],
                trending_skills=[],
                new_employees_today=0,
                new_employees_week=0
            )

        # 计算统计数据
        all_skills = set()
        category_counts: Dict[str, int] = defaultdict(int)
        hourly_rates = []
        new_today = 0
        new_week = 0

        for emp in employees:
            hourly_rates.append(emp.hourly_rate)
            all_skills.update(emp.skills.keys())

            # 统计新员工
            days_since_creation = (now - emp.created_at).days
            if days_since_creation <= 1:
                new_today += 1
            if days_since_creation <= 7:
                new_week += 1

        # 计算中位数
        hourly_rates.sort()
        median_hourly_rate = hourly_rates[len(hourly_rates) // 2] if hourly_rates else 0

        # 获取热门技能
        trending_skills = [t["skill_name"] for t in self.get_trending_skills(limit=5)]

        stats = {
            "total_employees": len(employees),
            "active_employees": len([e for e in employees if e.status == EmployeeStatus.AVAILABLE]),
            "total_categories": len(category_counts),
            "total_skills": len(all_skills),
            "avg_hourly_rate": sum(hourly_rates) / len(hourly_rates) if hourly_rates else 0,
            "median_hourly_rate": median_hourly_rate,
            "top_categories": [{"name": k, "count": v} for k, v in
                              sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:5]],
            "trending_skills": trending_skills,
            "new_employees_today": new_today,
            "new_employees_week": new_week
        }

        self._market_stats_cache = stats
        self._market_stats_cached_at = now

        return MarketStatsResponse(**stats)


# 单例
market_enhanced_service = MarketEnhancedService()
