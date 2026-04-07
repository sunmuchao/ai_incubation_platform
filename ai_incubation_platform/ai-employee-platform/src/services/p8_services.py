"""
P8 阶段服务层 - 企业数据分析与绩效管理

服务列表:
1. EnterpriseDashboardService - 企业数据看板服务
2. PerformanceService - 绩效管理服务
3. DepartmentService - 组织架构服务
4. WebhookService - Webhook 集成服务
5. ExportService - 数据导出服务
"""

import uuid
import json
import hashlib
import hmac
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict

from models.p8_models import (
    EnterpriseDashboard, DashboardMetrics, DashboardTrend, DashboardChart,
    PerformanceReview, KPIMetric, PerformanceLevel, PerformanceHistory,
    Department, DepartmentTree, OrganizationChart, DepartmentLevel,
    WebhookSubscription, WebhookDelivery, WebhookPayload, WebhookEventType, WebhookStatus,
    ExportReport, ExportRequest, ReportType, ReportFormat, ReportTemplate
)


# ==================== 企业数据看板服务 ====================

class EnterpriseDashboardService:
    """企业数据看板服务"""

    # 内存存储（生产环境应使用数据库）
    _dashboards: Dict[str, EnterpriseDashboard] = {}
    _metrics_cache: Dict[str, Dict[str, Any]] = {}

    def get_dashboard(
        self,
        tenant_id: str,
        user_id: str,
        period: str = "month"
    ) -> EnterpriseDashboard:
        """获取企业数据看板"""
        cache_key = f"{tenant_id}:{period}"

        # 检查缓存
        if cache_key in self._metrics_cache:
            cached = self._metrics_cache[cache_key]
            if (datetime.now() - cached['generated_at']).seconds < 300:
                return cached['dashboard']

        # 计算指标
        metrics = self._calculate_metrics(tenant_id, period)
        trends = self._calculate_trends(tenant_id, period)
        charts = self._generate_charts(trends)
        top_employees = self._get_top_employees(tenant_id, period)
        alerts = self._generate_alerts(metrics)

        dashboard = EnterpriseDashboard(
            tenant_id=tenant_id,
            user_id=user_id,
            period=period,
            metrics=metrics,
            trends=trends,
            charts=charts,
            top_employees=top_employees,
            alerts=alerts
        )

        # 更新缓存
        self._metrics_cache[cache_key] = {
            'dashboard': dashboard,
            'generated_at': datetime.now()
        }

        return dashboard

    def _calculate_metrics(self, tenant_id: str, period: str) -> DashboardMetrics:
        """计算核心指标"""
        # TODO: 从数据库获取真实数据
        # 这里使用模拟数据
        return DashboardMetrics(
            total_employees=50,
            active_employees=35,
            total_orders=500,
            completed_orders=450,
            total_revenue=125000.0,
            total_cost=85000.0,
            avg_employee_rating=4.6,
            avg_order_completion_time=12.5,
            employee_utilization_rate=0.75
        )

    def _calculate_trends(self, tenant_id: str, period: str) -> Dict[str, List[DashboardTrend]]:
        """计算趋势数据"""
        # 生成最近 30 天的趋势数据
        trends = {
            "revenue": [],
            "orders": [],
            "active_employees": []
        }

        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)

        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            # 模拟数据
            trends["revenue"].append(DashboardTrend(
                date=date_str,
                value=4000 + (hash(date_str) % 2000),
                change_rate=(hash(date_str) % 20 - 10) / 100.0
            ))
            trends["orders"].append(DashboardTrend(
                date=date_str,
                value=15 + (hash(date_str) % 10),
                change_rate=(hash(date_str) % 15 - 7) / 100.0
            ))
            trends["active_employees"].append(DashboardTrend(
                date=date_str,
                value=30 + (hash(date_str) % 10),
                change_rate=(hash(date_str) % 10 - 5) / 100.0
            ))
            current_date += timedelta(days=1)

        return trends

    def _generate_charts(self, trends: Dict[str, List[DashboardTrend]]) -> List[DashboardChart]:
        """生成图表数据"""
        charts = []

        # 收入趋势图
        if "revenue" in trends:
            charts.append(DashboardChart(
                chart_type="line",
                title="收入趋势",
                data=[{"date": t.date, "value": t.value} for t in trends["revenue"]],
                labels=[t.date for t in trends["revenue"]]
            ))

        # 订单分布图
        charts.append(DashboardChart(
            chart_type="pie",
            title="订单状态分布",
            data=[
                {"label": "已完成", "value": 450},
                {"label": "进行中", "value": 35},
                {"label": "已取消", "value": 15}
            ],
            labels=["已完成", "进行中", "已取消"]
        ))

        return charts

    def _get_top_employees(self, tenant_id: str, period: str) -> List[Dict[str, Any]]:
        """获取表现最好的员工"""
        # TODO: 从数据库获取真实数据
        return [
            {"id": "emp-001", "name": "Python 数据分析专家", "rating": 4.9, "orders": 25},
            {"id": "emp-002", "name": "前端开发助手", "rating": 4.8, "orders": 20},
            {"id": "emp-003", "name": "全栈工程师", "rating": 4.7, "orders": 18}
        ]

    def _generate_alerts(self, metrics: DashboardMetrics) -> List[Dict[str, str]]:
        """生成警告/提醒"""
        alerts = []

        if metrics.employee_utilization_rate < 0.5:
            alerts.append({
                "type": "warning",
                "message": "员工利用率低于 50%，建议优化资源配置"
            })

        if metrics.avg_employee_rating < 4.0:
            alerts.append({
                "type": "warning",
                "message": "平均员工评分低于 4.0，建议加强培训"
            })

        return alerts


# ==================== 绩效管理服务 ====================

class PerformanceService:
    """绩效管理服务"""

    _reviews: Dict[str, PerformanceReview] = {}
    _kpi_definitions: Dict[str, List[Dict[str, Any]]] = {}

    def create_review(
        self,
        employee_id: str,
        employee_name: str,
        reviewer_id: str,
        tenant_id: str,
        review_period: str,
        kpi_metrics: List[KPIMetric],
        comments: Optional[str] = None
    ) -> PerformanceReview:
        """创建绩效评估"""
        review_id = f"review-{uuid.uuid4().hex[:8]}"

        # 计算总体得分
        overall_score = self._calculate_overall_score(kpi_metrics)
        performance_level = self._determine_performance_level(overall_score)

        # 分析优势和待改进领域
        strengths, areas_for_improvement = self._analyze_performance(kpi_metrics)

        review = PerformanceReview(
            id=review_id,
            employee_id=employee_id,
            employee_name=employee_name,
            reviewer_id=reviewer_id,
            tenant_id=tenant_id,
            review_period=review_period,
            kpi_metrics=kpi_metrics,
            overall_score=overall_score,
            performance_level=performance_level,
            strengths=strengths,
            areas_for_improvement=areas_for_improvement,
            comments=comments
        )

        self._reviews[review_id] = review
        return review

    def get_review(self, review_id: str) -> Optional[PerformanceReview]:
        """获取绩效评估"""
        return self._reviews.get(review_id)

    def get_employee_history(self, employee_id: str) -> PerformanceHistory:
        """获取员工绩效历史"""
        reviews = [
            r for r in self._reviews.values()
            if r.employee_id == employee_id
        ]

        if not reviews:
            return PerformanceHistory(
                employee_id=employee_id,
                reviews=[],
                average_score=0.0,
                trend="stable"
            )

        avg_score = sum(r.overall_score for r in reviews) / len(reviews)

        # 判断趋势
        if len(reviews) >= 2:
            recent_scores = [r.overall_score for r in reviews[-3:]]
            if all(recent_scores[i] <= recent_scores[i+1] for i in range(len(recent_scores)-1)):
                trend = "improving"
            elif all(recent_scores[i] >= recent_scores[i+1] for i in range(len(recent_scores)-1)):
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "stable"

        return PerformanceHistory(
            employee_id=employee_id,
            reviews=reviews,
            average_score=avg_score,
            trend=trend
        )

    def _calculate_overall_score(self, kpi_metrics: List[KPIMetric]) -> float:
        """计算总体得分"""
        if not kpi_metrics:
            return 0.0

        total_weight = sum(m.weight for m in kpi_metrics)
        weighted_score = sum(m.score * m.weight for m in kpi_metrics)

        return weighted_score / total_weight if total_weight > 0 else 0.0

    def _determine_performance_level(self, score: float) -> PerformanceLevel:
        """确定绩效等级"""
        if score >= 90:
            return PerformanceLevel.S
        elif score >= 80:
            return PerformanceLevel.A
        elif score >= 70:
            return PerformanceLevel.B
        elif score >= 60:
            return PerformanceLevel.C
        else:
            return PerformanceLevel.D

    def _analyze_performance(
        self,
        kpi_metrics: List[KPIMetric]
    ) -> tuple:
        """分析绩效表现"""
        strengths = []
        areas_for_improvement = []

        for metric in kpi_metrics:
            if metric.score >= 90:
                strengths.append(f"{metric.metric_name} 表现卓越 ({metric.score}分)")
            elif metric.score >= 80:
                strengths.append(f"{metric.metric_name} 表现优秀 ({metric.score}分)")
            elif metric.score < 60:
                areas_for_improvement.append(f"{metric.metric_name} 需要改进 ({metric.score}分)")

        return strengths, areas_for_improvement

    def get_default_kpi_definitions(self) -> List[Dict[str, Any]]:
        """获取默认 KPI 定义"""
        return [
            {
                "metric_id": "kpi-001",
                "metric_name": "订单完成率",
                "target_value": 95.0,
                "weight": 1.0,
                "description": "完成订单数 / 总订单数"
            },
            {
                "metric_id": "kpi-002",
                "metric_name": "客户满意度",
                "target_value": 4.5,
                "weight": 1.0,
                "description": "客户评分平均值"
            },
            {
                "metric_id": "kpi-003",
                "metric_name": "响应时间",
                "target_value": 2.0,
                "weight": 0.8,
                "description": "平均响应时间（小时）"
            },
            {
                "metric_id": "kpi-004",
                "metric_name": "工作质量",
                "target_value": 90.0,
                "weight": 1.2,
                "description": "工作成果质量评分"
            }
        ]


# ==================== 组织架构服务 ====================

class DepartmentService:
    """企业组织架构服务"""

    _departments: Dict[str, Department] = {}

    def create_department(
        self,
        tenant_id: str,
        name: str,
        parent_id: Optional[str] = None,
        level: DepartmentLevel = DepartmentLevel.DEPARTMENT,
        manager_id: Optional[str] = None,
        description: Optional[str] = None,
        budget: Optional[float] = None
    ) -> Department:
        """创建部门"""
        dept_id = f"dept-{uuid.uuid4().hex[:8]}"

        department = Department(
            id=dept_id,
            tenant_id=tenant_id,
            name=name,
            parent_id=parent_id,
            level=level,
            manager_id=manager_id,
            description=description,
            budget=budget
        )

        self._departments[dept_id] = department
        return department

    def get_department(self, dept_id: str) -> Optional[Department]:
        """获取部门"""
        return self._departments.get(dept_id)

    def get_tenant_departments(self, tenant_id: str) -> List[Department]:
        """获取租户的所有部门"""
        return [
            d for d in self._departments.values()
            if d.tenant_id == tenant_id
        ]

    def get_department_tree(self, tenant_id: str) -> OrganizationChart:
        """获取部门树形结构"""
        departments = self.get_tenant_departments(tenant_id)

        # 构建部门映射
        dept_map = {d.id: d for d in departments}
        children_map: Dict[str, List[DepartmentTree]] = defaultdict(list)

        # 构建树形结构
        root_depts = []
        for dept in departments:
            if dept.parent_id is None:
                root_depts.append(self._build_tree(dept, dept_map, children_map))
            else:
                children_map[dept.parent_id].append(
                    self._build_tree(dept, dept_map, children_map)
                )

        total_employees = sum(self._count_employees(tree) for tree in root_depts)

        return OrganizationChart(
            tenant_id=tenant_id,
            root_departments=root_depts,
            total_departments=len(departments),
            total_ai_employees=total_employees
        )

    def _build_tree(
        self,
        dept: Department,
        dept_map: Dict[str, Department],
        children_map: Dict[str, List[DepartmentTree]]
    ) -> DepartmentTree:
        """递归构建树"""
        children = children_map.get(dept.id, [])
        total_employees = len(dept.ai_employee_ids) + sum(
            self._count_employees(child) for child in children
        )

        return DepartmentTree(
            department=dept,
            children=children,
            total_ai_employees=total_employees
        )

    def _count_employees(self, tree: DepartmentTree) -> int:
        """递归计算员工数"""
        return tree.total_ai_employees

    def update_department(
        self,
        dept_id: str,
        **kwargs
    ) -> Optional[Department]:
        """更新部门"""
        if dept_id not in self._departments:
            return None

        dept = self._departments[dept_id]
        for key, value in kwargs.items():
            if hasattr(dept, key) and value is not None:
                setattr(dept, key, value)

        dept.updated_at = datetime.now()
        return dept

    def delete_department(self, dept_id: str) -> bool:
        """删除部门"""
        if dept_id not in self._departments:
            return False

        # 检查是否有子部门
        has_children = any(
            d.parent_id == dept_id for d in self._departments.values()
        )
        if has_children:
            raise ValueError("无法删除包含子部门的部门")

        del self._departments[dept_id]
        return True


# ==================== Webhook 集成服务 ====================

class WebhookService:
    """Webhook 集成服务"""

    _subscriptions: Dict[str, WebhookSubscription] = {}
    _deliveries: Dict[str, WebhookDelivery] = {}

    def create_subscription(
        self,
        tenant_id: str,
        created_by: str,
        name: str,
        url: str,
        events: List[WebhookEventType]
    ) -> WebhookSubscription:
        """创建 Webhook 订阅"""
        sub_id = f"webhook-{uuid.uuid4().hex[:8]}"
        secret = self._generate_secret()

        subscription = WebhookSubscription(
            id=sub_id,
            tenant_id=tenant_id,
            created_by=created_by,
            name=name,
            url=url,
            events=events,
            secret=secret
        )

        self._subscriptions[sub_id] = subscription
        return subscription

    def get_subscription(self, sub_id: str) -> Optional[WebhookSubscription]:
        """获取 Webhook 订阅"""
        return self._subscriptions.get(sub_id)

    def get_tenant_subscriptions(self, tenant_id: str) -> List[WebhookSubscription]:
        """获取租户的所有 Webhook 订阅"""
        return [
            s for s in self._subscriptions.values()
            if s.tenant_id == tenant_id
        ]

    def update_subscription(
        self,
        sub_id: str,
        **kwargs
    ) -> Optional[WebhookSubscription]:
        """更新 Webhook 订阅"""
        if sub_id not in self._subscriptions:
            return None

        sub = self._subscriptions[sub_id]
        for key, value in kwargs.items():
            if hasattr(sub, key) and value is not None:
                setattr(sub, key, value)

        sub.updated_at = datetime.now()
        return sub

    def delete_subscription(self, sub_id: str) -> bool:
        """删除 Webhook 订阅"""
        if sub_id not in self._subscriptions:
            return False

        del self._subscriptions[sub_id]
        return True

    def trigger_webhook(
        self,
        tenant_id: str,
        event_type: WebhookEventType,
        data: Dict[str, Any]
    ) -> List[WebhookDelivery]:
        """触发 Webhook 事件"""
        subscriptions = [
            s for s in self.get_tenant_subscriptions(tenant_id)
            if s.status == WebhookStatus.ACTIVE and event_type in s.events
        ]

        deliveries = []
        for sub in subscriptions:
            delivery = self._deliver_webhook(sub, event_type, data)
            deliveries.append(delivery)

        return deliveries

    def _deliver_webhook(
        self,
        subscription: WebhookSubscription,
        event_type: WebhookEventType,
        data: Dict[str, Any]
    ) -> WebhookDelivery:
        """投递 Webhook"""
        delivery_id = f"delivery-{uuid.uuid4().hex[:8]}"

        # 构建 payload
        payload = WebhookPayload(
            event_id=delivery_id,
            event_type=event_type,
            tenant_id=subscription.tenant_id,
            timestamp=datetime.now(),
            data=data
        )

        # 计算签名
        signature = self._compute_signature(
            subscription.secret,
            json.dumps(payload.dict(), default=str)
        )

        # 准备请求
        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Signature": signature,
            "X-Webhook-Event": event_type.value,
        }
        if subscription.headers:
            headers.update(subscription.headers)

        # 发送请求
        delivery = WebhookDelivery(
            id=delivery_id,
            subscription_id=subscription.id,
            event_type=event_type,
            payload=payload.dict(),
            status="pending"
        )

        try:
            response = requests.post(
                subscription.url,
                json=payload.dict(default=str),
                headers=headers,
                timeout=10
            )

            delivery.status = "success" if response.ok else "failed"
            delivery.response_code = response.status_code
            delivery.response_body = response.text

            if response.ok:
                subscription.success_count += 1
                subscription.last_triggered_at = datetime.now()
            else:
                subscription.failure_count += 1

        except Exception as e:
            delivery.status = "failed"
            delivery.response_body = str(e)
            subscription.failure_count += 1

        self._deliveries[delivery_id] = delivery
        return delivery

    def _generate_secret(self) -> str:
        """生成 Webhook 密钥"""
        return uuid.uuid4().hex + uuid.uuid4().hex

    def _compute_signature(self, secret: str, payload: str) -> str:
        """计算签名"""
        return hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()

    def get_delivery_history(
        self,
        subscription_id: str,
        limit: int = 50
    ) -> List[WebhookDelivery]:
        """获取投递历史"""
        deliveries = [
            d for d in self._deliveries.values()
            if d.subscription_id == subscription_id
        ]

        # 按时间倒序排序
        deliveries.sort(key=lambda d: d.created_at, reverse=True)
        return deliveries[:limit]


# ==================== 数据导出服务 ====================

class ExportService:
    """数据导出服务"""

    _reports: Dict[str, ExportReport] = {}
    _templates: Dict[str, ReportTemplate] = {}

    def create_export(
        self,
        tenant_id: str,
        requested_by: str,
        request: ExportRequest
    ) -> ExportReport:
        """创建导出任务"""
        report_id = f"export-{uuid.uuid4().hex[:8]}"

        report = ExportReport(
            id=report_id,
            tenant_id=tenant_id,
            requested_by=requested_by,
            report_type=request.report_type,
            format=request.format,
            status="pending",
            period=request.period,
            filters=request.filters
        )

        self._reports[report_id] = report

        # 异步处理导出
        self._process_export(report_id, request)

        return report

    def get_report(self, report_id: str) -> Optional[ExportReport]:
        """获取导出报告"""
        return self._reports.get(report_id)

    def get_tenant_reports(self, tenant_id: str) -> List[ExportReport]:
        """获取租户的导出历史"""
        return [
            r for r in self._reports.values()
            if r.tenant_id == tenant_id
        ]

    def _process_export(
        self,
        report_id: str,
        request: ExportRequest
    ):
        """处理导出任务（模拟异步）"""
        import threading

        def process():
            try:
                report = self._reports[report_id]
                report.status = "processing"
                report.progress = 10

                # 模拟处理时间
                import time
                time.sleep(1)
                report.progress = 50

                # 生成文件（模拟）
                if request.format == ReportFormat.JSON:
                    content = self._generate_json_report(request)
                elif request.format == ReportFormat.CSV:
                    content = self._generate_csv_report(request)
                elif request.format == ReportFormat.EXCEL:
                    content = self._generate_excel_report(request)
                else:  # PDF
                    content = self._generate_pdf_report(request)

                report.progress = 90

                # 保存文件（模拟）
                report.file_url = f"/api/exports/{report_id}.{request.format.value}"
                report.file_size = len(content) if isinstance(content, bytes) else len(content.encode())
                report.status = "completed"
                report.progress = 100
                report.completed_at = datetime.now()
                report.expires_at = datetime.now() + timedelta(days=7)

            except Exception as e:
                report = self._reports[report_id]
                report.status = "failed"
                report.error_message = str(e)

        thread = threading.Thread(target=process)
        thread.daemon = True
        thread.start()

    def _generate_json_report(self, request: ExportRequest) -> str:
        """生成 JSON 报告"""
        data = self._get_report_data(request)
        return json.dumps(data, indent=2, default=str)

    def _generate_csv_report(self, request: ExportRequest) -> str:
        """生成 CSV 报告"""
        data = self._get_report_data(request)
        # 简单 CSV 生成
        if isinstance(data, list) and data:
            headers = list(data[0].keys())
            lines = [",".join(headers)]
            for row in data:
                lines.append(",".join(str(row.get(h, "")) for h in headers))
            return "\n".join(lines)
        return ""

    def _generate_excel_report(self, request: ExportRequest) -> bytes:
        """生成 Excel 报告（需要 openpyxl 库）"""
        # 简化实现，实际需要 openpyxl
        return b"Excel file content (binary)"

    def _generate_pdf_report(self, request: ExportRequest) -> bytes:
        """生成 PDF 报告（需要 reportlab 库）"""
        # 简化实现，实际需要 reportlab
        return b"PDF file content (binary)"

    def _get_report_data(self, request: ExportRequest) -> Any:
        """获取报告数据"""
        # TODO: 根据报告类型获取真实数据
        return {
            "report_type": request.report_type.value,
            "period": request.period,
            "filters": request.filters,
            "data": {
                "total_records": 100,
                "summary": "Report summary"
            }
        }

    def create_template(
        self,
        tenant_id: str,
        created_by: str,
        name: str,
        report_type: ReportType,
        format: ReportFormat,
        template_config: Dict[str, Any]
    ) -> ReportTemplate:
        """创建报告模板"""
        template_id = f"template-{uuid.uuid4().hex[:8]}"

        template = ReportTemplate(
            id=template_id,
            tenant_id=tenant_id,
            name=name,
            report_type=report_type,
            format=format,
            template_config=template_config,
            created_by=created_by
        )

        self._templates[template_id] = template
        return template

    def get_templates(self, tenant_id: str) -> List[ReportTemplate]:
        """获取租户的报告模板"""
        return [
            t for t in self._templates.values()
            if t.tenant_id == tenant_id
        ]


# ==================== 服务实例 ====================

dashboard_service = EnterpriseDashboardService()
performance_service = PerformanceService()
department_service = DepartmentService()
webhook_service = WebhookService()
export_service = ExportService()
