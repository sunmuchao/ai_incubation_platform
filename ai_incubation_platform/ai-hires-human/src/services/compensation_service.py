"""
薪酬管理服务。
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

from models.compensation import (
    SalaryRange,
    ExperienceLevel,
    WorkMode,
    IndustryType,
    BenefitType,
    TransparencyLevel,
    CompensationSurvey,
    SalaryBenchmark,
    NegotiationPosition,
    NegotiationAdvice,
    SalaryAdjustment,
    AdjustmentReason,
    InsurancePlan,
    StockOption,
    Allowance,
    BenefitsPackage,
    CompensationTransparency,
    EquityAnalysis,
    SalaryBenchmarkRequest,
    SalarySurveyRequest,
    NegotiationAdviceRequest,
    RaiseRecommendationRequest,
)

logger = logging.getLogger(__name__)


class CompensationService:
    """薪酬管理服务。"""

    def __init__(self):
        """初始化薪酬管理服务。"""
        # 模拟数据库存储
        self._benchmarks: Dict[str, SalaryBenchmark] = {}
        self._surveys: Dict[str, CompensationSurvey] = {}
        self._negotiations: Dict[str, NegotiationAdvice] = {}
        self._adjustments: Dict[str, SalaryAdjustment] = {}
        self._benefits_packages: Dict[str, BenefitsPackage] = {}
        self._transparency_settings: Dict[str, CompensationTransparency] = {}
        self._equity_analyses: Dict[str, EquityAnalysis] = {}

        # 初始化基准数据
        self._initialize_benchmark_data()

    def _initialize_benchmark_data(self):
        """初始化薪资基准数据（模拟真实数据）。"""
        # 互联网行业技术岗位基准数据
        benchmark_data = [
            {
                "job_title": "软件工程师",
                "skill": "python",
                "industry": IndustryType.TECH,
                "location": "北京",
                "experience_level": ExperienceLevel.JUNIOR,
                "work_mode": WorkMode.HYBRID,
                "salary_range": SalaryRange(
                    min_salary=15000,
                    max_salary=25000,
                    median_salary=20000,
                    percentile_25=17000,
                    percentile_75=23000,
                    currency="CNY",
                    period="monthly"
                ),
                "confidence_score": 0.92,
                "sample_count": 1580,
            },
            {
                "job_title": "软件工程师",
                "skill": "python",
                "industry": IndustryType.TECH,
                "location": "北京",
                "experience_level": ExperienceLevel.MID,
                "work_mode": WorkMode.HYBRID,
                "salary_range": SalaryRange(
                    min_salary=25000,
                    max_salary=40000,
                    median_salary=32000,
                    percentile_25=28000,
                    percentile_75=36000,
                    currency="CNY",
                    period="monthly"
                ),
                "confidence_score": 0.95,
                "sample_count": 2340,
            },
            {
                "job_title": "软件工程师",
                "skill": "python",
                "industry": IndustryType.TECH,
                "location": "北京",
                "experience_level": ExperienceLevel.SENIOR,
                "work_mode": WorkMode.HYBRID,
                "salary_range": SalaryRange(
                    min_salary=40000,
                    max_salary=65000,
                    median_salary=50000,
                    percentile_25=43000,
                    percentile_75=58000,
                    currency="CNY",
                    period="monthly"
                ),
                "confidence_score": 0.89,
                "sample_count": 890,
            },
            {
                "job_title": "软件工程师",
                "skill": "python",
                "industry": IndustryType.TECH,
                "location": "上海",
                "experience_level": ExperienceLevel.MID,
                "work_mode": WorkMode.HYBRID,
                "salary_range": SalaryRange(
                    min_salary=26000,
                    max_salary=42000,
                    median_salary=33000,
                    percentile_25=29000,
                    percentile_75=38000,
                    currency="CNY",
                    period="monthly"
                ),
                "confidence_score": 0.93,
                "sample_count": 2100,
            },
            {
                "job_title": "软件工程师",
                "skill": "python",
                "industry": IndustryType.TECH,
                "location": "深圳",
                "experience_level": ExperienceLevel.MID,
                "work_mode": WorkMode.HYBRID,
                "salary_range": SalaryRange(
                    min_salary=27000,
                    max_salary=43000,
                    median_salary=34000,
                    percentile_25=30000,
                    percentile_75=39000,
                    currency="CNY",
                    period="monthly"
                ),
                "confidence_score": 0.91,
                "sample_count": 1850,
            },
            {
                "job_title": "数据分析师",
                "skill": "sql",
                "industry": IndustryType.FINANCE,
                "location": "北京",
                "experience_level": ExperienceLevel.MID,
                "work_mode": WorkMode.ONSITE,
                "salary_range": SalaryRange(
                    min_salary=20000,
                    max_salary=35000,
                    median_salary=27000,
                    percentile_25=23000,
                    percentile_75=32000,
                    currency="CNY",
                    period="monthly"
                ),
                "confidence_score": 0.88,
                "sample_count": 1200,
            },
            {
                "job_title": "产品经理",
                "skill": "product_management",
                "industry": IndustryType.TECH,
                "location": "北京",
                "experience_level": ExperienceLevel.SENIOR,
                "work_mode": WorkMode.HYBRID,
                "salary_range": SalaryRange(
                    min_salary=35000,
                    max_salary=60000,
                    median_salary=45000,
                    percentile_25=38000,
                    percentile_75=52000,
                    currency="CNY",
                    period="monthly"
                ),
                "confidence_score": 0.87,
                "sample_count": 760,
            },
            {
                "job_title": "UI 设计师",
                "skill": "ui_design",
                "industry": IndustryType.TECH,
                "location": "北京",
                "experience_level": ExperienceLevel.MID,
                "work_mode": WorkMode.REMOTE,
                "salary_range": SalaryRange(
                    min_salary=18000,
                    max_salary=30000,
                    median_salary=23000,
                    percentile_25=20000,
                    percentile_75=27000,
                    currency="CNY",
                    period="monthly"
                ),
                "confidence_score": 0.85,
                "sample_count": 650,
            },
        ]

        for data in benchmark_data:
            benchmark = SalaryBenchmark(**data)
            key = self._get_benchmark_key(
                benchmark.job_title,
                benchmark.skill,
                benchmark.industry,
                benchmark.location,
                benchmark.experience_level,
                benchmark.work_mode
            )
            self._benchmarks[key] = benchmark

        logger.info(f"Initialized {len(self._benchmarks)} salary benchmarks")

    def _get_benchmark_key(
        self,
        job_title: str,
        skill: str,
        industry: IndustryType,
        location: str,
        experience_level: ExperienceLevel,
        work_mode: WorkMode
    ) -> str:
        """生成基准数据键。"""
        return f"{job_title}|{skill}|{industry.value}|{location}|{experience_level.value}|{work_mode.value}"

    # ===== 薪资基准查询 =====

    def get_market_salary_range(
        self,
        request: SalaryBenchmarkRequest
    ) -> SalaryRange:
        """获取市场薪酬范围。"""
        # 尝试精确匹配
        key = self._get_benchmark_key(
            request.job_title or "",
            request.skill,
            request.industry or IndustryType.TECH,
            request.location or "北京",
            request.experience_level or ExperienceLevel.MID,
            request.work_mode or WorkMode.HYBRID
        )

        if key in self._benchmarks:
            return self._benchmarks[key].salary_range

        # 模糊匹配：按技能和地区查找
        for benchmark_key, benchmark in self._benchmarks.items():
            if (request.skill.lower() in benchmark_key.lower() and
                (not request.location or request.location in benchmark_key)):
                return benchmark.salary_range

        # 返回默认范围
        return SalaryRange(
            min_salary=10000,
            max_salary=50000,
            median_salary=25000,
            percentile_25=15000,
            percentile_75=35000,
            currency="CNY",
            period="monthly"
        )

    def get_salary_benchmark(
        self,
        request: SalaryBenchmarkRequest
    ) -> Optional[SalaryBenchmark]:
        """获取完整的薪资基准数据。"""
        key = self._get_benchmark_key(
            request.job_title or "",
            request.skill,
            request.industry or IndustryType.TECH,
            request.location or "北京",
            request.experience_level or ExperienceLevel.MID,
            request.work_mode or WorkMode.HYBRID
        )
        return self._benchmarks.get(key)

    def list_salary_benchmarks(
        self,
        skill: Optional[str] = None,
        industry: Optional[IndustryType] = None,
        location: Optional[str] = None
    ) -> List[SalaryBenchmark]:
        """列出薪资基准数据。"""
        results = []
        for benchmark in self._benchmarks.values():
            if skill and skill.lower() not in benchmark.skill.lower():
                continue
            if industry and benchmark.industry != industry:
                continue
            if location and location not in benchmark.location:
                continue
            results.append(benchmark)
        return results

    # ===== 薪酬调查 =====

    def conduct_salary_survey(
        self,
        request: SalarySurveyRequest
    ) -> CompensationSurvey:
        """进行薪酬调查。"""
        # 基于请求维度聚合数据
        matching_benchmarks = []
        for benchmark in self._benchmarks.values():
            if request.skills and benchmark.skill not in request.skills:
                continue
            if request.industries and benchmark.industry not in request.industries:
                continue
            if request.locations and benchmark.location not in request.locations:
                continue
            matching_benchmarks.append(benchmark)

        if not matching_benchmarks:
            # 返回默认调查结果
            return CompensationSurvey(
                skill=request.skills[0] if request.skills else "general",
                salary_range=SalaryRange(
                    min_salary=10000,
                    max_salary=50000,
                    median_salary=25000,
                    percentile_25=15000,
                    percentile_75=35000,
                    currency="CNY",
                    period="monthly"
                ),
                sample_size=0
            )

        # 计算聚合统计
        all_salaries = []
        total_samples = 0
        for bm in matching_benchmarks:
            all_salaries.extend([
                bm.salary_range.min_salary,
                bm.salary_range.median_salary,
                bm.salary_range.max_salary
            ])
            total_samples += bm.sample_count

        all_salaries.sort()
        survey = CompensationSurvey(
            skill=request.skills[0] if request.skills else "general",
            industry=request.industries[0] if request.industries else None,
            location=request.locations[0] if request.locations else None,
            salary_range=SalaryRange(
                min_salary=min(all_salaries),
                max_salary=max(all_salaries),
                median_salary=all_salaries[len(all_salaries) // 2],
                percentile_25=all_salaries[len(all_salaries) // 4],
                percentile_75=all_salaries[3 * len(all_salaries) // 4],
                currency="CNY",
                period="monthly"
            ),
            sample_size=total_samples,
            yoy_growth=0.08,  # 模拟 8% 同比增长
            mom_growth=0.005  # 模拟 0.5% 环比增长
        )

        self._surveys[survey.survey_id] = survey
        return survey

    def get_salary_trends(
        self,
        skill: str,
        months: int = 12
    ) -> List[Dict]:
        """获取薪酬趋势数据。"""
        # 模拟历史趋势数据
        trends = []
        base_salary = 25000  # 基准月薪

        for i in range(months):
            month_date = datetime.now() - timedelta(days=(months - i) * 30)
            # 模拟薪资增长趋势
            growth_factor = 1 + (i * 0.005)  # 每月 0.5% 增长
            trends.append({
                "date": month_date.strftime("%Y-%m"),
                "median_salary": base_salary * growth_factor,
                "sample_count": 1000 + i * 50
            })

        return trends

    # ===== 薪资谈判支持 =====

    def generate_negotiation_advice(
        self,
        request: NegotiationAdviceRequest
    ) -> NegotiationAdvice:
        """生成薪资谈判建议。"""
        # 获取市场基准
        benchmark_request = SalaryBenchmarkRequest(
            job_title=request.job_title,
            skill=request.skills[0] if request.skills else "general",
            location=request.location
        )
        market_range = self.get_market_salary_range(benchmark_request)

        # 根据立场生成建议
        if request.position == NegotiationPosition.EMPLOYER:
            return self._generate_employer_advice(
                request, market_range
            )
        else:
            return self._generate_worker_advice(
                request, market_range
            )

    def _generate_employer_advice(
        self,
        request: NegotiationAdviceRequest,
        market_range: SalaryRange
    ) -> NegotiationAdvice:
        """生成雇主视角的谈判建议。"""
        # 计算建议报价
        if request.expected_salary:
            # 基于期望薪资调整
            if request.expected_salary <= market_range.min_salary:
                suggested_offer = request.expected_salary
            elif request.expected_salary <= market_range.percentile_75:
                suggested_offer = request.expected_salary * 0.95  # 小幅议价
            else:
                suggested_offer = market_range.percentile_75  # 不超过 75 分位
        else:
            suggested_offer = market_range.median_salary

        advice = NegotiationAdvice(
            position=request.position,
            job_title=request.job_title,
            employer_id=request.employer_id,
            market_range=market_range,
            worker_expected_salary=request.expected_salary,
            suggested_offer=suggested_offer,
            negotiation_range=(
                market_range.min_salary,
                market_range.percentile_75
            ),
            walk_away_price=market_range.max_salary * 1.1,
            strategies=[
                "强调平台发展空间和成长机会",
                "突出项目挑战性和技术栈",
                "提供灵活的工作方式",
                "考虑非金钱激励（股权、培训）"
            ],
            leverage_points=[
                f"市场薪资中位数为{market_range.median_salary:.0f}元",
                f"同类岗位供给充足",
                "平台提供独特的 AI 项目经验"
            ],
            talking_points=[
                "我们提供与 AI 前沿技术深度结合的机会",
                "项目完成后会有行业影响力",
                "团队氛围好，成长空间大"
            ]
        )

        self._negotiations[advice.advice_id] = advice
        return advice

    def _generate_worker_advice(
        self,
        request: NegotiationAdviceRequest,
        market_range: SalaryRange
    ) -> NegotiationAdvice:
        """生成工人视角的谈判建议。"""
        # 计算建议报价
        if request.current_salary:
            # 基于当前薪资建议涨幅
            min_increase = request.current_salary * 1.1  # 至少 10% 涨幅
            target_salary = max(min_increase, market_range.median_salary)
            suggested_offer = min(target_salary, market_range.percentile_75)
        else:
            suggested_offer = market_range.percentile_60 if hasattr(market_range, 'percentile_60') else market_range.percentile_75

        # 生成工人优势分析
        strengths = []
        if request.experience_years and request.experience_years >= 5:
            strengths.append(f"{request.experience_years}年相关经验")
        if request.skills:
            strengths.append(f"掌握{len(request.skills)}项核心技能")

        advice = NegotiationAdvice(
            position=request.position,
            job_title=request.job_title,
            worker_id=request.worker_id,
            market_range=market_range,
            worker_current_salary=request.current_salary,
            worker_expected_salary=request.expected_salary,
            suggested_offer=suggested_offer,
            negotiation_range=(
                market_range.median_salary,
                market_range.max_salary
            ),
            walk_away_price=market_range.min_salary * 0.9,
            strategies=[
                "强调过往项目成果和影响力",
                "展示独特技能组合的价值",
                "表达对项目的热情和理解",
                "准备多个薪资方案供选择"
            ],
            leverage_points=[
                f"市场薪资 75 分位为{market_range.percentile_75:.0f}元",
                "具备项目所需的稀缺技能",
                "有类似项目成功经验"
            ],
            talking_points=[
                "我之前的项目取得了 X%的效果提升",
                "我对这个领域有深入理解和实践经验",
                "我相信我的技能可以为项目带来独特价值"
            ],
            worker_strengths=strengths,
            unique_value_props=[
                "快速学习能力",
                "跨领域知识整合",
                "良好的沟通协作能力"
            ]
        )

        self._negotiations[advice.advice_id] = advice
        return advice

    # ===== 调薪建议 =====

    def generate_raise_recommendation(
        self,
        request: RaiseRecommendationRequest
    ) -> SalaryAdjustment:
        """生成调薪建议。"""
        # 获取工人绩效数据（模拟）
        performance_score = self._get_worker_performance(request.worker_id)

        # 获取市场基准
        market_percentile = self._get_market_percentile(request.worker_id, request.current_salary)

        # 计算调薪幅度
        increase_percentage = 0.0

        # 绩效调薪
        if AdjustmentReason.PERFORMANCE in request.reasons:
            if performance_score >= 4.5:
                increase_percentage += 0.15  # 优秀：15%
            elif performance_score >= 4.0:
                increase_percentage += 0.10  # 良好：10%
            elif performance_score >= 3.5:
                increase_percentage += 0.05  # 一般：5%
            else:
                increase_percentage += 0.02  # 低于一般也有 2% 基础调薪

        # 市场调薪
        if AdjustmentReason.MARKET in request.reasons:
            if market_percentile < 50:
                # 低于市场中位数，建议调整到中位数
                increase_percentage += max(0, (50 - market_percentile) / 100)

        # 通胀调整
        if AdjustmentReason.INFLATION in request.reasons:
            increase_percentage += 0.03  # 假设通胀率 3%

        # 确保至少有基本调薪（至少 2%）
        increase_percentage = max(increase_percentage, 0.02)
        # 确保合理范围（最多 30%）
        increase_percentage = min(increase_percentage, 0.30)

        suggested_new_salary = request.current_salary * (1 + increase_percentage)

        adjustment = SalaryAdjustment(
            worker_id=request.worker_id,
            current_salary=request.current_salary,
            reason=request.reasons[0] if request.reasons else AdjustmentReason.PERFORMANCE,
            reason_details=",".join([r.value for r in request.reasons]),
            suggested_new_salary=suggested_new_salary,
            increase_amount=suggested_new_salary - request.current_salary,
            increase_percentage=increase_percentage,
            performance_score=performance_score,
            market_percentile=market_percentile,
            status="draft"
        )

        self._adjustments[adjustment.adjustment_id] = adjustment
        return adjustment

    def _get_worker_performance(self, worker_id: str) -> float:
        """获取工人绩效分数（模拟）。"""
        # 实际实现应该从数据库获取工人历史任务表现
        import random
        random.seed(hash(worker_id) % 1000)
        return 3.0 + random.random() * 2.0  # 3.0-5.0 分

    def _get_market_percentile(self, worker_id: str, current_salary: float) -> float:
        """获取工人薪资在市场中的百分位（模拟）。"""
        # 简化实现：基于薪资金额估算百分位
        # 假设市场薪资范围 10000-60000
        min_salary = 10000
        max_salary = 60000
        percentile = ((current_salary - min_salary) / (max_salary - min_salary)) * 100
        return max(0, min(100, percentile))

    def list_adjustments(
        self,
        worker_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[SalaryAdjustment]:
        """列出调薪建议。"""
        results = []
        for adjustment in self._adjustments.values():
            if worker_id and adjustment.worker_id != worker_id:
                continue
            if status and adjustment.status != status:
                continue
            results.append(adjustment)
        return results

    # ===== 福利管理 =====

    def create_benefits_package(
        self,
        request: BenefitsPackageRequest
    ) -> BenefitsPackage:
        """创建福利包。"""
        # 基于预算和偏好生成福利组合
        package = BenefitsPackage(
            package_name=request.package_name,
            insurance_plans=self._generate_insurance_plans(request),
            stock_options=self._generate_stock_options(request),
            allowances=self._generate_allowances(request),
            paid_leave_days=15,
            training_budget=request.budget * 0.05 if request.budget else 5000,
            wellness_budget=request.budget * 0.02 if request.budget else 2000
        )

        self._benefits_packages[package.package_id] = package
        return package

    def _generate_insurance_plans(
        self,
        request: BenefitsPackageRequest
    ) -> List[InsurancePlan]:
        """生成保险计划组合。"""
        plans = [
            InsurancePlan(
                plan_name="基础医疗保险",
                insurance_type="health",
                coverage_amount=100000,
                monthly_premium=500,
                employer_contribution_rate=0.8,
                deductible=1000,
                co_pay_rate=0.1
            ),
            InsurancePlan(
                plan_name="补充养老保险",
                insurance_type="retirement",
                coverage_amount=500000,
                monthly_premium=800,
                employer_contribution_rate=0.5,
                deductible=0,
                co_pay_rate=0
            )
        ]
        return plans

    def _generate_stock_options(
        self,
        request: BenefitsPackageRequest
    ) -> List[StockOption]:
        """生成股票期权。"""
        if not request.budget or request.budget < 100000:
            return []

        now = datetime.now()
        options = [
            StockOption(
                shares=1000,
                strike_price=10.0,
                current_price=15.0,
                grant_date=now,
                vesting_start=now,
                vesting_duration_years=4,
                cliff_months=12
            )
        ]
        return options

    def _generate_allowances(
        self,
        request: BenefitsPackageRequest
    ) -> List[Allowance]:
        """生成补贴组合。"""
        allowances = [
            Allowance(
                allowance_type="communication",
                amount=200,
                frequency="monthly"
            ),
            Allowance(
                allowance_type="meal",
                amount=500,
                frequency="monthly"
            )
        ]

        # 远程工作补贴
        if request.preferences.get("remote_work"):
            allowances.append(
                Allowance(
                    allowance_type="remote_work",
                    amount=300,
                    frequency="monthly",
                    conditions="在家办公天数>=10 天/月"
                )
            )

        return allowances

    def get_benefits_package(self, package_id: str) -> Optional[BenefitsPackage]:
        """获取福利包详情。"""
        return self._benefits_packages.get(package_id)

    def list_benefits_packages(self) -> List[BenefitsPackage]:
        """列出所有福利包。"""
        return list(self._benefits_packages.values())

    # ===== 薪酬透明度 =====

    def set_compensation_transparency(
        self,
        task_id: str,
        employer_id: str,
        level: TransparencyLevel,
        show_salary_range: bool = False,
        show_benefits: bool = False
    ) -> CompensationTransparency:
        """设置薪酬透明度。"""
        transparency = CompensationTransparency(
            task_id=task_id,
            employer_id=employer_id,
            level=level,
            show_salary_range=show_salary_range,
            show_benefits=show_benefits,
            show_negotiable=True,
            visible_to_bidders=(level == TransparencyLevel.LIMITED),
            visible_after_acceptance=(level == TransparencyLevel.PRIVATE)
        )

        key = f"{task_id}|{employer_id}"
        self._transparency_settings[key] = transparency
        return transparency

    def get_compensation_transparency(
        self,
        task_id: str
    ) -> Optional[CompensationTransparency]:
        """获取薪酬透明度设置。"""
        for key, transparency in self._transparency_settings.items():
            if transparency.task_id == task_id:
                return transparency
        return None

    # ===== 薪酬公平性分析 =====

    def analyze_pay_equity(
        self,
        employer_id: str,
        include_gender: bool = True,
        include_ethnicity: bool = False
    ) -> EquityAnalysis:
        """分析薪酬公平性。"""
        # 模拟公平性分析数据
        import random

        now = datetime.now()
        analysis = EquityAnalysis(
            employer_id=employer_id,
            start_date=now - timedelta(days=365),
            end_date=now,
            gender_pay_gap=random.uniform(-5, 5) if include_gender else None,
            ethnicity_pay_gap=random.uniform(-3, 3) if include_ethnicity else None,
            equal_pay_violations=[],
            equity_score=random.uniform(80, 95),
            recommendations=[
                "建议定期审核心酬数据",
                "建立透明的薪酬标准",
                "实施薪酬带宽管理"
            ]
        )

        # 检测潜在 violations（模拟）
        if abs(analysis.gender_pay_gap or 0) > 3:
            analysis.equal_pay_violations.append({
                "type": "gender",
                "severity": "medium",
                "description": f"检测到{analysis.gender_pay_gap:.1f}%的性别薪酬差距"
            })

        self._equity_analyses[analysis.analysis_id] = analysis
        return analysis

    def get_equity_analysis(self, analysis_id: str) -> Optional[EquityAnalysis]:
        """获取公平性分析报告。"""
        return self._equity_analyses.get(analysis_id)


# 全局服务实例
_compensation_service: Optional[CompensationService] = None


def get_compensation_service() -> CompensationService:
    """获取薪酬管理服务实例。"""
    global _compensation_service
    if _compensation_service is None:
        _compensation_service = CompensationService()
    return _compensation_service
