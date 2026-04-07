"""
转化漏斗分析服务 - Google Analytics 核心能力对标
"""
from typing import List, Dict, Optional, Any
from datetime import datetime, date, timedelta
import uuid
import logging
from schemas.analytics import (
    FunnelCreateRequest,
    FunnelStep,
    FunnelAnalysisResult,
    FunnelStepResult,
    TrackingEvent,
    EventType
)
from .event_tracking import event_tracking_service

logger = logging.getLogger(__name__)


class FunnelAnalysisService:
    """
    转化漏斗分析服务

    对标 Google Analytics 的漏斗分析能力：
    - 自定义漏斗步骤定义
    - 转化率计算
    - 流失节点识别
    - 优化建议生成
    """

    def __init__(self):
        # 内存存储漏斗定义（生产环境应使用数据库）
        self._funnels: Dict[str, FunnelCreateRequest] = {}
        # 存储预定义的行业标准漏斗模板
        self._templates = self._initialize_templates()

    def _initialize_templates(self) -> Dict[str, List[Dict]]:
        """初始化预定义漏斗模板"""
        return {
            "ecommerce": [
                {"step_name": "查看商品", "event_name": "page_view", "filter": {"page_type": "product"}},
                {"step_name": "加入购物车", "event_name": "add_to_cart", "filter": {}},
                {"step_name": "开始结算", "event_name": "begin_checkout", "filter": {}},
                {"step_name": "完成购买", "event_name": "purchase", "filter": {}}
            ],
            "saas_signup": [
                {"step_name": "访问首页", "event_name": "page_view", "filter": {"page_url": "/"}},
                {"step_name": "点击注册", "event_name": "click", "filter": {"element_id": "signup-btn"}},
                {"step_name": "提交表单", "event_name": "form_submit", "filter": {"form_type": "signup"}},
                {"step_name": "验证邮箱", "event_name": "email_verified", "filter": {}}
            ],
            "content_engagement": [
                {"step_name": "页面浏览", "event_name": "page_view", "filter": {}},
                {"step_name": "滚动 50%", "event_name": "scroll", "filter": {"percent": 50}},
                {"step_name": "点击阅读更多", "event_name": "click", "filter": {"element_class": "read-more"}},
                {"step_name": "订阅通讯", "event_name": "form_submit", "filter": {"form_type": "newsletter"}}
            ],
            "mobile_app_install": [
                {"step_name": "访问下载页", "event_name": "page_view", "filter": {"page_type": "download"}},
                {"step_name": "点击下载", "event_name": "click", "filter": {"element_id": "download-btn"}},
                {"step_name": "应用安装", "event_name": "app_install", "filter": {}},
                {"step_name": "首次打开", "event_name": "app_open", "filter": {"is_first": True}}
            ]
        }

    def create_funnel(self, request: FunnelCreateRequest) -> str:
        """
        创建漏斗分析

        Args:
            request: 漏斗创建请求

        Returns:
            漏斗 ID
        """
        funnel_id = f"funnel_{uuid.uuid4().hex[:12]}"
        request_dict = request.__dict__.copy()
        self._funnels[funnel_id] = request_dict
        request_dict['funnel_id'] = funnel_id

        logger.info(f"Created funnel: {funnel_id}, name={request.funnel_name}, steps={len(request.steps)}")
        return funnel_id

    def get_funnel_template(self, template_name: str) -> Optional[List[FunnelStep]]:
        """
        获取预定义漏斗模板

        Args:
            template_name: 模板名称（ecommerce, saas_signup, content_engagement, mobile_app_install）

        Returns:
            漏斗步骤列表
        """
        template = self._templates.get(template_name)
        if not template:
            return None

        steps = []
        for i, step in enumerate(template):
            steps.append(FunnelStep(
                step_id=f"step_{i+1}",
                step_name=step["step_name"],
                step_order=i+1,
                event_name=step["event_name"],
                description=f"预定义模板步骤"
            ))
        return steps

    def analyze_funnel(
        self,
        funnel_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Optional[FunnelAnalysisResult]:
        """
        执行漏斗分析

        Args:
            funnel_id: 漏斗 ID
            start_date: 开始日期（可选，覆盖漏斗定义中的日期）
            end_date: 结束日期（可选，覆盖漏斗定义中的日期）

        Returns:
            漏斗分析结果
        """
        if funnel_id not in self._funnels:
            logger.error(f"Funnel not found: {funnel_id}")
            return None

        funnel = self._funnels[funnel_id]
        use_start = start_date or funnel["start_date"]
        use_end = end_date or funnel["end_date"]

        # 获取事件数据
        events = self._get_funnel_events(funnel["steps"], use_start, use_end)

        # 分析每个步骤
        step_results = self._analyze_steps(funnel["steps"], events)

        # 计算整体转化率
        if step_results:
            total_entries = step_results[0].users if step_results else 0
            total_completions = step_results[-1].users if step_results else 0
            overall_rate = total_completions / total_entries if total_entries > 0 else 0
        else:
            total_entries = 0
            total_completions = 0
            overall_rate = 0

        # 识别流失严重节点
        drop_off_points = self._identify_drop_offs(step_results)

        # 生成优化建议
        recommendations = self._generate_recommendations(step_results, drop_off_points, funnel)

        return FunnelAnalysisResult(
            funnel_id=funnel_id,
            funnel_name=funnel["funnel_name"],
            period={"start": use_start, "end": use_end},
            total_entries=total_entries,
            total_completions=total_completions,
            overall_conversion_rate=round(overall_rate, 4),
            steps=step_results,
            drop_off_points=drop_off_points,
            recommendations=recommendations
        )

    def _get_funnel_events(
        self,
        steps: List[FunnelStep],
        start_date: date,
        end_date: date
    ) -> List[TrackingEvent]:
        """获取漏斗相关事件"""
        all_events = []

        for step in steps:
            events = event_tracking_service.get_events(
                start_date=start_date,
                end_date=end_date,
                event_name=step.event_name
            )
            all_events.extend(events)

        return all_events

    def _analyze_steps(
        self,
        steps: List[FunnelStep],
        events: List[TrackingEvent]
    ) -> List[FunnelStepResult]:
        """
        分析每个步骤的转化情况

        使用简化的用户匹配逻辑（基于 session_id）
        """
        # 按用户分组事件
        user_events: Dict[str, Dict[int, List[TrackingEvent]]] = {}

        for event in events:
            session_id = event.user.session_id
            if session_id not in user_events:
                user_events[session_id] = {}

            # 找到事件对应的步骤
            for step in steps:
                if event.event_name == step.event_name:
                    step_order = step.step_order
                    if step_order not in user_events[session_id]:
                        user_events[session_id][step_order] = []
                    user_events[session_id][step_order].append(event)
                    break

        # 统计每个步骤的用户数
        step_user_counts = {}
        step_users = {}  # 记录到达每个步骤的用户

        for session_id, session_steps in user_events.items():
            # 检查用户是否按顺序完成步骤
            reached_steps = sorted(session_steps.keys())
            max_reached = max(reached_steps) if reached_steps else 0

            # 统计用户到达的每个步骤
            for step_order in reached_steps:
                if step_order not in step_user_counts:
                    step_user_counts[step_order] = 0
                    step_users[step_order] = set()
                if session_id not in step_users[step_order]:
                    step_user_counts[step_order] += 1
                    step_users[step_order].add(session_id)

        # 构建结果
        results = []
        sorted_steps = sorted(steps, key=lambda x: x.step_order)

        for step in sorted_steps:
            users = step_user_counts.get(step.step_order, 0)
            prev_users = step_user_counts.get(step.step_order - 1, users) if step.step_order > 1 else users
            first_step_users = step_user_counts.get(1, users)

            conversion_rate = users / prev_users if prev_users > 0 else 0
            overall_rate = users / first_step_users if first_step_users > 0 else 0

            results.append(FunnelStepResult(
                step_id=step.step_id,
                step_name=step.step_name,
                step_order=step.step_order,
                users=users,
                conversion_rate=round(conversion_rate, 4),
                overall_conversion_rate=round(overall_rate, 4),
                avg_time_to_step=None  # 简化版本暂不计算
            ))

        return results

    def _identify_drop_offs(
        self,
        step_results: List[FunnelStepResult]
    ) -> List[Dict[str, Any]]:
        """识别流失严重的节点"""
        drop_offs = []

        for i in range(1, len(step_results)):
            prev_step = step_results[i - 1]
            curr_step = step_results[i]

            # 计算流失率
            drop_off_rate = 1 - curr_step.conversion_rate
            drop_off_count = prev_step.users - curr_step.users

            # 如果流失率超过 50%，标记为严重流失点
            if drop_off_rate > 0.5:
                drop_offs.append({
                    "from_step": prev_step.step_name,
                    "to_step": curr_step.step_name,
                    "drop_off_rate": round(drop_off_rate, 4),
                    "drop_off_count": drop_off_count,
                    "severity": "high" if drop_off_rate > 0.7 else "medium"
                })

        # 按流失率排序
        drop_offs.sort(key=lambda x: x["drop_off_rate"], reverse=True)
        return drop_offs

    def _generate_recommendations(
        self,
        step_results: List[FunnelStepResult],
        drop_off_points: List[Dict[str, Any]],
        funnel: Dict
    ) -> List[str]:
        """生成优化建议"""
        recommendations = []

        # 基于流失节点的建议
        for drop_off in drop_off_points:
            from_step = drop_off["from_step"]
            to_step = drop_off["to_step"]
            severity = drop_off["severity"]
            rate = drop_off["drop_off_rate"] * 100

            if severity == "high":
                recommendations.append(
                    f"【严重】从「{from_step}」到「{to_step}」的流失率高达{rate:.1f}%，建议重点优化此环节"
                )
            else:
                recommendations.append(
                    f"从「{from_step}」到「{to_step}」的流失率为{rate:.1f}%，值得关注并优化"
                )

        # 基于整体转化率的建议
        if step_results:
            overall_rate = step_results[-1].overall_conversion_rate * 100

            if overall_rate < 5:
                recommendations.append(
                    f"整体转化率仅{overall_rate:.1f}%，建议全面审查漏斗设计，考虑简化流程"
                )
            elif overall_rate < 15:
                recommendations.append(
                    f"整体转化率{overall_rate:.1f}%处于中等水平，有优化空间"
                )
            else:
                recommendations.append(
                    f"整体转化率{overall_rate:.1f}%表现良好，继续保持并寻找进一步提升的机会"
                )

        # 基于漏斗类型的通用建议
        funnel_name = funnel.get("funnel_name", "").lower()
        if "ecommerce" in funnel_name or "购买" in funnel_name:
            recommendations.extend([
                "考虑提供免费配送或运费补贴，降低购物车放弃率",
                "优化结算流程，减少必填字段数量",
                "添加信任标识（安全支付、退换货政策）提升用户信心"
            ])
        elif "signup" in funnel_name or "注册" in funnel_name:
            recommendations.extend([
                "简化注册表单，只保留必要字段",
                "提供社交账号登录选项，降低注册门槛",
                "考虑分步注册，先让用户体验核心价值"
            ])

        # 如果没有严重问题，给出正向建议
        if not drop_off_points and step_results:
            recommendations.append("漏斗整体表现健康，可以考虑 A/B 测试进一步优化")

        return recommendations

    def compare_funnel_periods(
        self,
        funnel_id: str,
        period1_start: date,
        period1_end: date,
        period2_start: date,
        period2_end: date
    ) -> Dict[str, Any]:
        """
        对比两个时间段的漏斗表现

        Args:
            funnel_id: 漏斗 ID
            period1_start: 第一期开始日期
            period1_end: 第一期结束日期
            period2_start: 第二期开始日期
            period2_end: 第二期结束日期

        Returns:
            对比结果
        """
        result1 = self.analyze_funnel(funnel_id, period1_start, period1_end)
        result2 = self.analyze_funnel(funnel_id, period2_start, period2_end)

        if not result1 or not result2:
            return None

        # 计算变化
        entries_change = (result2.total_entries - result1.total_entries) / max(result1.total_entries, 1)
        completions_change = (result2.total_completions - result1.total_completions) / max(result1.total_completions, 1)
        conversion_change = result2.overall_conversion_rate - result1.overall_conversion_rate

        return {
            "period1": {
                "start": str(period1_start),
                "end": str(period1_end),
                "entries": result1.total_entries,
                "completions": result1.total_completions,
                "conversion_rate": result1.overall_conversion_rate
            },
            "period2": {
                "start": str(period2_start),
                "end": str(period2_end),
                "entries": result2.total_entries,
                "completions": result2.total_completions,
                "conversion_rate": result2.overall_conversion_rate
            },
            "changes": {
                "entries_change": round(entries_change, 4),
                "completions_change": round(completions_change, 4),
                "conversion_rate_change": round(conversion_change, 4)
            },
            "analysis": self._generate_period_comparison_analysis(
                entries_change, completions_change, conversion_change
            )
        }

    def _generate_period_comparison_analysis(
        self,
        entries_change: float,
        completions_change: float,
        conversion_change: float
    ) -> str:
        """生成周期对比分析结论"""
        parts = []

        if entries_change > 0.1:
            parts.append(f"流量增长{entries_change*100:.1f}%")
        elif entries_change < -0.1:
            parts.append(f"流量下降{entries_change*100:.1f}%")
        else:
            parts.append("流量基本持平")

        if conversion_change > 0.01:
            parts.append(f"转化率提升{conversion_change*100:.1f}个百分点")
        elif conversion_change < -0.01:
            parts.append(f"转化率下降{abs(conversion_change)*100:.1f}个百分点")
        else:
            parts.append("转化率基本稳定")

        if completions_change > 0.2:
            parts.append("转化量显著提升")
        elif completions_change < -0.2:
            parts.append("转化量明显下滑")

        return "；".join(parts)


# 全局服务实例
funnel_analysis_service = FunnelAnalysisService()
