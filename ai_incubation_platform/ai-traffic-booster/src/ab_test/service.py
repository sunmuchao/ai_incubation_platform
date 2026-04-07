"""
A/B测试服务实现
"""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import uuid
import random
import math
from core.exceptions import (
    ABTestTrafficAllocationInvalidException,
    ABTestControlVariantInvalidException,
)
from schemas.ab_test import (
    ABTestCreateRequest,
    ABTestResponse,
    ABTestResultResponse,
    ABTestListResponse,
    ABTestStatus,
    ABTestVariant,
    ABTestMetrics
)
import logging

logger = logging.getLogger(__name__)


class ABTestService:
    """A/B测试服务"""

    def __init__(self):
        # 内存存储测试数据，演示用
        self._tests: Dict[str, ABTestResponse] = {}
        self._test_results: Dict[str, ABTestResultResponse] = {}
        self._initialize_sample_data()

    def _initialize_sample_data(self):
        """初始化示例数据"""
        # 创建几个示例测试
        sample_tests = [
            {
                "name": "首页标题优化测试",
                "description": "测试不同首页标题对点击率的影响",
                "page_url": "/",
                "variants": [
                    ABTestVariant(
                        id="var-1",
                        name="对照组",
                        description="原标题：专业的SEO优化工具",
                        traffic_percentage=0.5,
                        content={"title": "专业的SEO优化工具"},
                        is_control=True
                    ),
                    ABTestVariant(
                        id="var-2",
                        name="测试组A",
                        description="新标题：AI驱动的流量增长平台",
                        traffic_percentage=0.5,
                        content={"title": "AI驱动的流量增长平台"},
                        is_control=False
                    )
                ],
                "goals": [{"name": "点击率提升", "metric": "ctr", "target_value": 0.1, "operator": "increase"}]
            },
            {
                "name": "产品页CTA按钮测试",
                "description": "测试不同CTA按钮文本对转化率的影响",
                "page_url": "/products/ai-tool",
                "variants": [
                    ABTestVariant(
                        id="var-1",
                        name="对照组",
                        description="按钮文本：立即购买",
                        traffic_percentage=0.33,
                        content={"cta_text": "立即购买"},
                        is_control=True
                    ),
                    ABTestVariant(
                        id="var-2",
                        name="测试组A",
                        description="按钮文本：免费试用",
                        traffic_percentage=0.33,
                        content={"cta_text": "免费试用"},
                        is_control=False
                    ),
                    ABTestVariant(
                        id="var-3",
                        name="测试组B",
                        description="按钮文本：开始使用",
                        traffic_percentage=0.34,
                        content={"cta_text": "开始使用"},
                        is_control=False
                    )
                ],
                "goals": [{"name": "转化率提升", "metric": "conversion_rate", "target_value": 0.05, "operator": "increase"}]
            },
            {
                "name": "博客文章配图测试",
                "description": "测试不同类型配图对文章阅读完成率的影响",
                "page_url": "/blog/seo-guide",
                "variants": [
                    ABTestVariant(
                        id="var-1",
                        name="对照组",
                        description="无配图",
                        traffic_percentage=0.5,
                        content={"has_image": False},
                        is_control=True
                    ),
                    ABTestVariant(
                        id="var-2",
                        name="测试组A",
                        description="信息图配图",
                        traffic_percentage=0.5,
                        content={"has_image": True, "image_type": "infographic"},
                        is_control=False
                    )
                ],
                "goals": [{"name": "阅读完成率提升", "metric": "completion_rate", "target_value": 0.6, "operator": "increase"}]
            }
        ]

        for i, test_data in enumerate(sample_tests):
            test_id = f"test-{uuid.uuid4().hex[:8]}"
            created_at = datetime.now() - timedelta(days=random.randint(1, 30))
            start_time = created_at + timedelta(hours=1)
            end_time = start_time + timedelta(days=14) if i < 2 else None

            if i == 0:
                status = ABTestStatus.COMPLETED
            elif i == 1:
                status = ABTestStatus.RUNNING
            else:
                status = ABTestStatus.DRAFT

            test = ABTestResponse(
                id=test_id,
                name=test_data["name"],
                description=test_data["description"],
                page_url=test_data["page_url"],
                status=status,
                variants=test_data["variants"],
                goals=test_data["goals"],
                start_time=start_time if status != ABTestStatus.DRAFT else None,
                end_time=end_time if status == ABTestStatus.COMPLETED else None,
                created_at=created_at,
                updated_at=datetime.now(),
                created_by="admin",
                confidence_level=0.95,
                minimum_sample_size=1000
            )
            self._tests[test_id] = test

            # 生成测试结果
            if status in [ABTestStatus.RUNNING, ABTestStatus.COMPLETED]:
                self._generate_test_result(test)

    def create_test(self, request: ABTestCreateRequest, created_by: str = "admin") -> ABTestResponse:
        """创建A/B测试"""
        test_id = f"test-{uuid.uuid4().hex[:8]}"
        now = datetime.now()

        # 验证流量分配总和为1
        total_traffic = sum(v.traffic_percentage for v in request.variants)
        if not math.isclose(total_traffic, 1.0, rel_tol=1e-9):
            raise ABTestTrafficAllocationInvalidException(
                f"流量分配总和必须为1，当前为{total_traffic}"
            )

        # 验证只有一个对照组
        control_count = sum(1 for v in request.variants if v.is_control)
        if control_count != 1:
            raise ABTestControlVariantInvalidException(
                f"必须且只能有一个对照组，当前有{control_count}个"
            )

        test = ABTestResponse(
            id=test_id,
            name=request.name,
            description=request.description,
            page_url=request.page_url,
            status=ABTestStatus.DRAFT,
            variants=request.variants,
            goals=request.goals,
            start_time=request.start_time,
            end_time=request.end_time,
            created_at=now,
            updated_at=now,
            created_by=created_by,
            confidence_level=request.confidence_level,
            minimum_sample_size=request.minimum_sample_size
        )

        self._tests[test_id] = test
        return test

    def get_test_list(self) -> ABTestListResponse:
        """获取测试列表"""
        tests = list(self._tests.values())

        running = sum(1 for t in tests if t.status == ABTestStatus.RUNNING)
        completed = sum(1 for t in tests if t.status == ABTestStatus.COMPLETED)
        draft = sum(1 for t in tests if t.status == ABTestStatus.DRAFT)

        return ABTestListResponse(
            tests=tests,
            total=len(tests),
            running=running,
            completed=completed,
            draft=draft
        )

    def get_test_detail(self, test_id: str) -> ABTestResponse:
        """获取测试详情"""
        if test_id not in self._tests:
            return None
        return self._tests[test_id]

    def get_test_result(self, test_id: str) -> Optional[ABTestResultResponse]:
        """获取测试结果"""
        test = self.get_test_detail(test_id)
        if not test:
            return None

        if test.status not in [ABTestStatus.RUNNING, ABTestStatus.COMPLETED]:
            return None

        if test_id not in self._test_results:
            self._generate_test_result(test)

        return self._test_results[test_id]

    def start_test(self, test_id: str) -> Optional[ABTestResponse]:
        """启动测试"""
        test = self.get_test_detail(test_id)
        if not test or test.status != ABTestStatus.DRAFT:
            return None

        test.status = ABTestStatus.RUNNING
        test.start_time = datetime.now()
        test.updated_at = datetime.now()
        return test

    def stop_test(self, test_id: str) -> Optional[ABTestResponse]:
        """停止测试"""
        test = self.get_test_detail(test_id)
        if not test or test.status != ABTestStatus.RUNNING:
            return None

        test.status = ABTestStatus.COMPLETED
        test.end_time = datetime.now()
        test.updated_at = datetime.now()
        return test

    def _generate_test_result(self, test: ABTestResponse) -> ABTestResultResponse:
        """生成测试结果数据"""
        # 计算运行天数
        if test.start_time:
            days_running = (datetime.now() - test.start_time).days
        else:
            days_running = 0

        # 生成样本数据
        current_sample_size = random.randint(
            test.minimum_sample_size // 2 if test.status == ABTestStatus.RUNNING else test.minimum_sample_size,
            test.minimum_sample_size * 3
        )

        remaining_sample_size = max(0, test.minimum_sample_size - current_sample_size)

        # 找到对照组
        control_variant = next(v for v in test.variants if v.is_control)

        # 生成各变体指标
        metrics = []
        control_conversion_rate = 0.0
        winner_id = None
        max_improvement = 0

        for variant in test.variants:
            visitors = int(current_sample_size * variant.traffic_percentage)
            if variant.is_control:
                conversion_rate = random.uniform(0.03, 0.07)
                control_conversion_rate = conversion_rate
                improvement = 0.0
                statistical_significance = 1.0
                is_winner = False
            else:
                # 测试组比对照组有随机提升/下降
                improvement = random.uniform(-0.2, 0.4)
                conversion_rate = control_conversion_rate * (1 + improvement)
                statistical_significance = random.uniform(0.5, 0.99) if days_running >= 7 else random.uniform(0.1, 0.8)
                is_winner = improvement > 0 and statistical_significance >= test.confidence_level

            if is_winner and improvement > max_improvement:
                max_improvement = improvement
                winner_id = variant.id

            metrics.append(ABTestMetrics(
                variant_id=variant.id,
                variant_name=variant.name,
                visitors=visitors,
                conversions=int(visitors * conversion_rate),
                conversion_rate=round(conversion_rate, 4),
                improvement=round(improvement, 4),
                statistical_significance=round(statistical_significance, 4),
                is_winner=is_winner
            ))

        # 确定是否有明确的获胜者
        has_winner = winner_id is not None
        can_terminate = has_winner or current_sample_size >= test.minimum_sample_size * 2

        # 生成结论和建议
        conclusion = None
        recommendations = []

        if test.status == ABTestStatus.COMPLETED:
            if has_winner:
                winner = next(v for v in test.variants if v.id == winner_id)
                winner_metric = next(m for m in metrics if m.variant_id == winner_id)
                conclusion = f"测试已完成，变体 '{winner.name}' 以 {winner_metric.statistical_significance*100:.1f}% 的统计显著性获胜，相比对照组提升了 {winner_metric.improvement*100:.1f}%"
                recommendations.append(f"建议全量切换到获胜变体 '{winner.name}'")
            else:
                conclusion = "测试已完成，但没有表现出统计显著差异的变体"
                recommendations.append("建议结束当前测试，设计新的测试方案")
                recommendations.append("可以考虑增加样本量或调整测试变量")
        elif test.status == ABTestStatus.RUNNING:
            if has_winner:
                winner = next(v for v in test.variants if v.id == winner_id)
                winner_metric = next(m for m in metrics if m.variant_id == winner_id)
                conclusion = f"测试进行中，变体 '{winner.name}' 目前表现最优，已达到统计显著性"
                recommendations.append("可以考虑提前终止测试，全量切换到获胜变体")
            elif current_sample_size >= test.minimum_sample_size:
                conclusion = "测试进行中，已达到最小样本量，但尚未出现显著差异"
                recommendations.append("建议继续运行测试以收集更多数据")
            else:
                conclusion = "测试进行中，样本量不足，暂无法得出可靠结论"
                recommendations.append(f"还需要 {remaining_sample_size} 个样本量才能达到最小要求")

        recommendations.append("持续监控各变体的性能表现")
        recommendations.append("注意排除外部因素对测试结果的干扰")

        result = ABTestResultResponse(
            test_id=test.id,
            test_name=test.name,
            status=test.status,
            current_sample_size=current_sample_size,
            remaining_sample_size=remaining_sample_size,
            confidence_level=test.confidence_level,
            metrics=metrics,
            conclusion=conclusion,
            recommendations=recommendations,
            can_terminate=can_terminate,
            has_winner=has_winner
        )

        self._test_results[test.id] = result
        return result


# 全局服务实例
ab_test_service = ABTestService()
