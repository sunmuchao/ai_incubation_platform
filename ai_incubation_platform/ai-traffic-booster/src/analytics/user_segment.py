"""
用户分群分析服务 - Google Analytics 核心能力对标
"""
from typing import List, Dict, Optional, Any
from datetime import datetime, date, timedelta
import uuid
import logging
from schemas.analytics import (
    UserSegmentCreateRequest,
    UserSegmentResponse,
    UserSegmentDetail,
    SegmentCondition,
    TrackingEvent,
    DeviceType
)
from .event_tracking import event_tracking_service

logger = logging.getLogger(__name__)


class UserSegmentService:
    """
    用户分群分析服务

    对标 Google Analytics 的用户分群能力：
    - 多维度用户分群（行为、设备、来源等）
    - 动态用户计数
    - 分群特征分析
    - 留存分析
    """

    def __init__(self):
        # 内存存储分群定义（生产环境应使用数据库）
        self._segments: Dict[str, Dict] = {}
        # 预定义分群模板
        self._templates = self._initialize_templates()

    def _initialize_templates(self) -> Dict[str, Dict]:
        """初始化预定义分群模板"""
        return {
            "high_value_users": {
                "name": "高价值用户",
                "description": "完成购买或转化的用户",
                "conditions": [
                    {"field": "event_name", "operator": "in", "value": ["purchase", "form_submit"]},
                    {"field": "value", "operator": "gt", "value": 0}
                ],
                "logic": "OR"
            },
            "mobile_users": {
                "name": "移动端用户",
                "description": "使用移动设备访问的用户",
                "conditions": [
                    {"field": "device_type", "operator": "eq", "value": "mobile"}
                ],
                "logic": "AND"
            },
            "new_users": {
                "name": "新用户",
                "description": "首次访问的用户（7 天内）",
                "conditions": [
                    {"field": "days_since_first_visit", "operator": "lte", "value": 7}
                ],
                "logic": "AND"
            },
            "churned_users": {
                "name": "流失用户",
                "description": "超过 30 天未访问的用户",
                "conditions": [
                    {"field": "days_since_last_visit", "operator": "gt", "value": 30}
                ],
                "logic": "AND"
            },
            "engaged_users": {
                "name": "高参与度用户",
                "description": "会话时长长、事件数多的用户",
                "conditions": [
                    {"field": "avg_session_duration", "operator": "gt", "value": 180},
                    {"field": "events_per_session", "operator": "gt", "value": 5}
                ],
                "logic": "AND"
            },
            "organic_search_users": {
                "name": "自然搜索用户",
                "description": "通过搜索引擎访问的用户",
                "conditions": [
                    {"field": "referrer", "operator": "contains", "value": "google"},
                    {"field": "referrer", "operator": "contains", "value": "baidu", "logic_modifier": "OR"},
                    {"field": "referrer", "operator": "contains", "value": "bing", "logic_modifier": "OR"}
                ],
                "logic": "OR"
            }
        }

    def create_segment(self, request: UserSegmentCreateRequest) -> UserSegmentResponse:
        """
        创建用户分群

        Args:
            request: 分群创建请求

        Returns:
            分群响应
        """
        segment_id = f"seg_{uuid.uuid4().hex[:12]}"

        # 计算用户数量
        user_count = self._count_segment_users(request)

        segment_data = {
            "segment_id": segment_id,
            "segment_name": request.segment_name,
            "description": request.description,
            "conditions": [c.__dict__ for c in request.conditions],
            "logic": request.logic,
            "start_date": request.start_date,
            "end_date": request.end_date,
            "user_count": user_count,
            "created_at": datetime.now()
        }

        self._segments[segment_id] = segment_data

        logger.info(f"Created segment: {segment_id}, name={request.segment_name}, users={user_count}")

        return UserSegmentResponse(
            segment_id=segment_id,
            segment_name=request.segment_name,
            description=request.description,
            user_count=user_count,
            conditions=request.conditions,
            logic=request.logic,
            created_at=datetime.now()
        )

    def get_segment_template(self, template_name: str) -> Optional[UserSegmentCreateRequest]:
        """
        获取预定义分群模板

        Args:
            template_name: 模板名称

        Returns:
            分群创建请求
        """
        template = self._templates.get(template_name)
        if not template:
            return None

        conditions = [
            SegmentCondition(
                field=c["field"],
                operator=c["operator"],
                value=c["value"]
            )
            for c in template["conditions"]
        ]

        return UserSegmentCreateRequest(
            segment_name=template["name"],
            description=template["description"],
            conditions=conditions,
            logic=template["logic"]
        )

    def get_segment_detail(self, segment_id: str) -> Optional[UserSegmentDetail]:
        """
        获取分群详情

        Args:
            segment_id: 分群 ID

        Returns:
            分群详情
        """
        if segment_id not in self._segments:
            return None

        segment_data = self._segments[segment_id]

        # 获取分群用户的行为特征
        user_stats = self._analyze_segment_users(segment_data)

        return UserSegmentDetail(
            segment=UserSegmentResponse(
                segment_id=segment_id,
                segment_name=segment_data["segment_name"],
                description=segment_data["description"],
                user_count=segment_data["user_count"],
                conditions=[SegmentCondition(**c) for c in segment_data["conditions"]],
                logic=segment_data["logic"],
                created_at=segment_data["created_at"]
            ),
            user_demographics=user_stats["demographics"],
            top_pages=user_stats["top_pages"],
            top_events=user_stats["top_events"],
            avg_session_duration=user_stats["avg_session_duration"],
            avg_sessions_per_user=user_stats["avg_sessions_per_user"],
            retention_rate=user_stats.get("retention_rate")
        )

    def _count_segment_users(self, request: UserSegmentCreateRequest) -> int:
        """
        计算分群用户数量

        简化实现：基于事件属性进行过滤
        """
        # 获取时间范围内的事件
        events = event_tracking_service.get_events(
            start_date=request.start_date or (datetime.now().date() - timedelta(days=30)),
            end_date=request.end_date or datetime.now().date()
        )

        if not events:
            return 0

        # 按条件过滤用户
        matching_users = set()

        for event in events:
            if self._event_matches_conditions(event, request.conditions, request.logic):
                user_id = event.user.user_id or event.user.session_id
                matching_users.add(user_id)

        return len(matching_users)

    def _event_matches_conditions(
        self,
        event: TrackingEvent,
        conditions: List[SegmentCondition],
        logic: str
    ) -> bool:
        """
        检查事件是否满足分群条件

        Args:
            event: 事件对象
            conditions: 条件列表
            logic: 逻辑运算符（AND/OR）

        Returns:
            是否匹配
        """
        if not conditions:
            return True

        results = []
        for condition in conditions:
            result = self._check_single_condition(event, condition)
            results.append(result)

        if logic == "AND":
            return all(results)
        else:  # OR
            return any(results)

    def _check_single_condition(
        self,
        event: TrackingEvent,
        condition: SegmentCondition
    ) -> bool:
        """检查单个条件"""
        field = condition.field
        operator = condition.operator
        value = condition.value

        # 获取字段值
        field_value = self._get_field_value(event, field)

        if field_value is None:
            return False

        # 执行比较
        if operator == "eq":
            return field_value == value
        elif operator == "neq":
            return field_value != value
        elif operator == "gt":
            return float(field_value) > float(value)
        elif operator == "lt":
            return float(field_value) < float(value)
        elif operator == "gte":
            return float(field_value) >= float(value)
        elif operator == "lte":
            return float(field_value) <= float(value)
        elif operator == "contains":
            return str(value).lower() in str(field_value).lower()
        elif operator == "in":
            return field_value in value
        elif operator == "startswith":
            return str(field_value).startswith(str(value))
        elif operator == "endswith":
            return str(field_value).endswith(str(value))

        return False

    def _get_field_value(self, event: TrackingEvent, field: str) -> Any:
        """
        从事件中获取字段值

        支持的字段：
        - event_name, event_type, page_url, user_id, session_id
        - device_type, os, browser
        - country, city, referrer
        - value (事件值)
        - 自定义属性 (properties 中)
        """
        # 基础字段
        if field == "event_name":
            return event.event_name
        elif field == "event_type":
            return event.event_type.value
        elif field == "page_url":
            return event.context.page_url
        elif field == "user_id":
            return event.user.user_id or event.user.anonymous_id
        elif field == "session_id":
            return event.user.session_id
        elif field == "value":
            return event.value or 0

        # 设备字段
        if event.device:
            if field == "device_type":
                return event.device.device_type.value
            elif field == "os":
                return event.device.os
            elif field == "browser":
                return event.device.browser

        # 上下文字段
        if field == "country":
            return event.context.country
        elif field == "city":
            return event.context.city
        elif field == "referrer":
            return event.context.referrer
        elif field == "page_title":
            return event.context.page_title

        # 自定义属性
        if event.properties and field in event.properties:
            return event.properties.get(field)

        return None

    def _analyze_segment_users(self, segment_data: Dict) -> Dict[str, Any]:
        """
        分析分群用户特征

        返回：
        - 人口统计信息
        - Top 页面
        - Top 事件
        - 会话统计
        """
        # 获取分群相关事件
        start_date = segment_data.get("start_date") or (datetime.now().date() - timedelta(days=30))
        end_date = segment_data.get("end_date") or datetime.now().date()

        events = event_tracking_service.get_events(
            start_date=start_date,
            end_date=end_date
        )

        if not events:
            return {
                "demographics": {},
                "top_pages": [],
                "top_events": [],
                "avg_session_duration": 0,
                "avg_sessions_per_user": 0
            }

        # 设备分布
        device_counts = {}
        os_counts = {}
        page_counts = {}
        event_counts = {}
        session_durations = []

        for event in events:
            # 设备统计
            if event.device:
                device_type = event.device.device_type.value
                device_counts[device_type] = device_counts.get(device_type, 0) + 1

                os_name = event.device.os or "Unknown"
                os_counts[os_name] = os_counts.get(os_name, 0) + 1

            # 页面统计
            page_url = event.context.page_url
            page_counts[page_url] = page_counts.get(page_url, 0) + 1

            # 事件统计
            event_name = event.event_name
            event_counts[event_name] = event_counts.get(event_name, 0) + 1

        # 计算会话时长（简化）
        sessions = {}
        for event in events:
            session_id = event.user.session_id
            if session_id not in sessions:
                sessions[session_id] = {"events": [], "duration": 0}
            sessions[session_id]["events"].append(event)

        for session_id, session_data in sessions.items():
            if len(session_data["events"]) >= 2:
                timestamps = [e.timestamp for e in session_data["events"]]
                duration = (max(timestamps) - min(timestamps)).total_seconds()
                session_durations.append(duration)

        avg_duration = sum(session_durations) / len(session_durations) if session_durations else 0

        # Top 页面
        top_pages = sorted(
            [{"page": k, "count": v} for k, v in page_counts.items()],
            key=lambda x: x["count"],
            reverse=True
        )[:10]

        # Top 事件
        top_events = sorted(
            [{"event": k, "count": v} for k, v in event_counts.items()],
            key=lambda x: x["count"],
            reverse=True
        )[:10]

        return {
            "demographics": {
                "devices": device_counts,
                "os": os_counts
            },
            "top_pages": top_pages,
            "top_events": top_events,
            "avg_session_duration": round(avg_duration, 2),
            "avg_sessions_per_user": len(sessions) / max(len(set(e.user.user_id or e.user.session_id for e in events)), 1)
        }

    def list_segments(self) -> List[UserSegmentResponse]:
        """列出所有分群"""
        return [
            UserSegmentResponse(
                segment_id=data["segment_id"],
                segment_name=data["segment_name"],
                description=data["description"],
                user_count=data["user_count"],
                conditions=[SegmentCondition(**c) for c in data["conditions"]],
                logic=data["logic"],
                created_at=data["created_at"]
            )
            for data in self._segments.values()
        ]

    def delete_segment(self, segment_id: str) -> bool:
        """删除分群"""
        if segment_id in self._segments:
            del self._segments[segment_id]
            logger.info(f"Deleted segment: {segment_id}")
            return True
        return False

    def calculate_retention(
        self,
        segment_id: str,
        retention_days: int = 7
    ) -> Dict[str, float]:
        """
        计算分群留存率

        Args:
            segment_id: 分群 ID
            retention_days: 留存天数

        Returns:
            每日留存率
        """
        if segment_id not in self._segments:
            return {}

        segment_data = self._segments[segment_id]
        start_date = segment_data.get("start_date") or (datetime.now().date() - timedelta(days=30))

        # 获取分群用户
        events = event_tracking_service.get_events(
            start_date=start_date,
            end_date=datetime.now().date()
        )

        # 按用户分组首次访问时间
        user_first_visit = {}
        user_visits = {}

        for event in events:
            user_id = event.user.user_id or event.user.session_id
            visit_date = event.timestamp.date()

            if user_id not in user_first_visit:
                user_first_visit[user_id] = visit_date
                user_visits[user_id] = set()
            user_visits[user_id].add(visit_date)

        # 计算队列留存
        cohorts = {}  # {cohort_date: {day_0: count, day_1: count, ...}}

        for user_id, first_date in user_first_visit.items():
            cohort_key = first_date.isoformat()
            if cohort_key not in cohorts:
                cohorts[cohort_key] = {i: 0 for i in range(retention_days)}
                cohorts[cohort_key][0] = 0  # 初始为 0，后面统计

            # 统计该用户的留存天数
            visits = user_visits.get(user_id, set())
            for day in range(retention_days):
                check_date = first_date + timedelta(days=day)
                if check_date in visits:
                    cohorts[cohort_key][day] = cohorts[cohort_key].get(day, 0) + 1

        # 计算留存率
        retention_rates = {}
        for cohort_key, cohort_data in cohorts.items():
            day_0_count = cohort_data.get(0, 0)
            if day_0_count > 0:
                for day, count in cohort_data.items():
                    key = f"day_{day}"
                    if key not in retention_rates:
                        retention_rates[key] = []
                    retention_rates[key].append(count / day_0_count)

        # 平均留存率
        avg_retention = {
            key: round(sum(values) / len(values), 4)
            for key, values in retention_rates.items()
        }

        return avg_retention


# 全局服务实例
user_segment_service = UserSegmentService()
