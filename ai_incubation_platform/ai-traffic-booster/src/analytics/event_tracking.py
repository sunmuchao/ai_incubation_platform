"""
事件追踪服务 - Google Analytics 核心能力对标
"""
from typing import List, Dict, Optional
from datetime import datetime, date, timedelta
import uuid
import hashlib
import logging
from schemas.analytics import (
    TrackingEvent,
    TrackingEventResponse,
    TrackingBatchResponse,
    EventType,
    UserIdentity,
    EventContext
)

logger = logging.getLogger(__name__)


class EventTrackingService:
    """
    事件追踪服务

    对标 Google Analytics 的事件采集能力：
    - 自动事件追踪（页面浏览、点击、表单提交等）
    - 自定义事件
    - 用户身份识别（匿名/登录用户）
    - 跨会话追踪
    """

    def __init__(self):
        # 内存存储事件数据（生产环境应使用数据库）
        self._events: List[TrackingEvent] = []
        self._user_sessions: Dict[str, Dict] = {}
        # 预定义事件模板
        self._event_templates = self._initialize_event_templates()

    def _initialize_event_templates(self) -> Dict[str, Dict]:
        """初始化预定义事件模板"""
        return {
            "page_view": {
                "category": "engagement",
                "required_params": ["page_url", "page_title"],
                "optional_params": ["referrer", "device"]
            },
            "click": {
                "category": "engagement",
                "required_params": ["element_id", "element_text"],
                "optional_params": ["target_url", "element_class"]
            },
            "form_submit": {
                "category": "conversion",
                "required_params": ["form_id", "form_name"],
                "optional_params": ["form_type", "fields_count"]
            },
            "purchase": {
                "category": "conversion",
                "required_params": ["transaction_id", "value", "currency"],
                "optional_params": ["items", "coupon", "shipping"]
            },
            "sign_up": {
                "category": "conversion",
                "required_params": ["method"],
                "optional_params": ["user_id", "plan_type"]
            },
            "login": {
                "category": "authentication",
                "required_params": ["method"],
                "optional_params": ["user_id", "success"]
            },
            "download": {
                "category": "engagement",
                "required_params": ["file_name", "file_type"],
                "optional_params": ["file_size", "download_source"]
            },
            "video_play": {
                "category": "engagement",
                "required_params": ["video_id", "video_title"],
                "optional_params": ["duration", "current_time", "percent_complete"]
            }
        }

    def track_event(self, event: TrackingEvent) -> TrackingEventResponse:
        """
        追踪单个事件

        Args:
            event: 追踪事件对象

        Returns:
            追踪响应
        """
        # 生成事件 ID
        if not event.event_id:
            event.event_id = f"evt_{uuid.uuid4().hex[:16]}"

        # 验证事件
        validation_result = self._validate_event(event)
        if not validation_result["valid"]:
            return TrackingEventResponse(
                event_id=event.event_id,
                status="failed",
                message=validation_result["error"]
            )

        # 增强事件数据
        enriched_event = self._enrich_event(event)

        # 存储事件
        self._events.append(enriched_event)

        # 更新用户会话
        self._update_user_session(enriched_event)

        logger.info(f"Event tracked: {event.event_id}, type={event.event_type}, name={event.event_name}")

        return TrackingEventResponse(
            event_id=event.event_id,
            status="success",
            message="Event tracked successfully"
        )

    def track_batch(self, events: List[TrackingEvent]) -> TrackingBatchResponse:
        """
        批量追踪事件

        Args:
            events: 事件列表

        Returns:
            批量追踪响应
        """
        success_count = 0
        failed_count = 0

        for event in events:
            response = self.track_event(event)
            if response.status == "success":
                success_count += 1
            else:
                failed_count += 1

        return TrackingBatchResponse(
            total=len(events),
            success=success_count,
            failed=failed_count,
            message=f"Successfully processed {success_count} events, {failed_count} failed"
        )

    def get_events(
        self,
        start_date: date,
        end_date: date,
        event_type: Optional[EventType] = None,
        event_name: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        page_url: Optional[str] = None,
        limit: int = 1000
    ) -> List[TrackingEvent]:
        """
        查询事件

        Args:
            start_date: 开始日期
            end_date: 结束日期
            event_type: 事件类型筛选
            event_name: 事件名称筛选
            user_id: 用户 ID 筛选
            session_id: 会话 ID 筛选
            page_url: 页面 URL 筛选
            limit: 返回数量限制

        Returns:
            事件列表
        """
        filtered_events = []

        for event in self._events:
            # 日期筛选
            event_date = event.timestamp.date()
            if event_date < start_date or event_date > end_date:
                continue

            # 事件类型筛选
            if event_type and event.event_type != event_type:
                continue

            # 事件名称筛选
            if event_name and event.event_name != event_name:
                continue

            # 用户 ID 筛选
            if user_id and event.user.user_id != user_id:
                continue

            # 会话 ID 筛选
            if session_id and event.user.session_id != session_id:
                continue

            # 页面 URL 筛选
            if page_url and page_url not in event.context.page_url:
                continue

            filtered_events.append(event)

            if len(filtered_events) >= limit:
                break

        return filtered_events

    def _validate_event(self, event: TrackingEvent) -> Dict:
        """验证事件数据"""
        # 检查时间戳
        if event.timestamp > datetime.now():
            return {"valid": False, "error": "Event timestamp cannot be in the future"}

        # 检查必填字段
        if not event.event_name:
            return {"valid": False, "error": "Event name is required"}

        if not event.user.session_id:
            return {"valid": False, "error": "Session ID is required"}

        if not event.context.page_url:
            return {"valid": False, "error": "Page URL is required"}

        # 检查预定义事件的必填参数
        template = self._event_templates.get(event.event_name)
        if template:
            required_params = template.get("required_params", [])
            if event.properties:
                for param in required_params:
                    if param not in event.properties:
                        logger.warning(f"Missing required parameter: {param} for event {event.event_name}")

        return {"valid": True}

    def _enrich_event(self, event: TrackingEvent) -> TrackingEvent:
        """增强事件数据"""
        # 生成匿名 ID（如果没有）
        if not event.user.anonymous_id:
            # 使用设备 ID + session ID 生成
            id_source = f"{event.user.device_id or ''}-{event.user.session_id}"
            event.user.anonymous_id = f"anon_{hashlib.md5(id_source.encode()).hexdigest()[:16]}"

        # 解析 User-Agent
        if event.context.user_agent and event.device:
            device_info = self._parse_user_agent(event.context.user_agent)
            if not event.device.browser:
                event.device.browser = device_info.get("browser")
            if not event.device.os:
                event.device.os = device_info.get("os")

        return event

    def _parse_user_agent(self, user_agent: str) -> Dict:
        """解析 User-Agent（简化版本）"""
        result = {"browser": "Unknown", "os": "Unknown"}

        # 检测浏览器
        if "Chrome" in user_agent:
            result["browser"] = "Chrome"
        elif "Firefox" in user_agent:
            result["browser"] = "Firefox"
        elif "Safari" in user_agent and "Chrome" not in user_agent:
            result["browser"] = "Safari"
        elif "Edg" in user_agent:
            result["browser"] = "Edge"
        elif "MSIE" in user_agent or "Trident" in user_agent:
            result["browser"] = "IE"

        # 检测操作系统
        if "Windows" in user_agent:
            result["os"] = "Windows"
        elif "Mac OS" in user_agent:
            result["os"] = "macOS"
        elif "Linux" in user_agent:
            result["os"] = "Linux"
        elif "Android" in user_agent:
            result["os"] = "Android"
        elif "iOS" in user_agent or "iPhone" in user_agent or "iPad" in user_agent:
            result["os"] = "iOS"

        return result

    def _update_user_session(self, event: TrackingEvent):
        """更新用户会话信息"""
        session_id = event.user.session_id
        user_id = event.user.user_id or event.user.anonymous_id

        if session_id not in self._user_sessions:
            self._user_sessions[session_id] = {
                "user_id": user_id,
                "start_time": event.timestamp,
                "last_activity": event.timestamp,
                "events": [],
                "pages": set()
            }

        session = self._user_sessions[session_id]
        session["last_activity"] = event.timestamp
        session["events"].append(event.event_id)
        session["pages"].add(event.context.page_url)

    def get_session_stats(self, session_id: str) -> Optional[Dict]:
        """获取会话统计"""
        if session_id not in self._user_sessions:
            return None

        session = self._user_sessions[session_id]
        duration = (session["last_activity"] - session["start_time"]).total_seconds()

        return {
            "session_id": session_id,
            "user_id": session["user_id"],
            "start_time": session["start_time"],
            "duration_seconds": duration,
            "event_count": len(session["events"]),
            "page_count": len(session["pages"])
        }

    def generate_client_snippet(self, site_id: str) -> str:
        """
        生成前端追踪代码片段

        Args:
            site_id: 站点 ID

        Returns:
            JavaScript 追踪代码
        """
        return f"""
<!-- AI Traffic Booster Tracking Code -->
<script>
(function() {{
    var ATB = window.ATB = window.ATB || {{}};
    ATB.siteId = '{site_id}';
    ATB.endpoint = 'http://localhost:8008/api/analytics/track';

    // 生成匿名 ID
    ATB.anonymousId = localStorage.getItem('atb_anonymous_id');
    if (!ATB.anonymousId) {{
        ATB.anonymousId = 'anon_' + Math.random().toString(36).substr(2, 16);
        localStorage.setItem('atb_anonymous_id', ATB.anonymousId);
    }}

    // 生成 Session ID
    ATB.sessionId = sessionStorage.getItem('atb_session_id');
    if (!ATB.sessionId) {{
        ATB.sessionId = 'sess_' + Math.random().toString(36).substr(2, 16);
        sessionStorage.setItem('atb_session_id', ATB.sessionId);
    }}

    // 页面浏览追踪
    function trackPageView() {{
        var eventData = {{
            event_type: 'page_view',
            event_name: 'page_view',
            timestamp: new Date().toISOString(),
            user: {{
                session_id: ATB.sessionId,
                anonymous_id: ATB.anonymousId
            }},
            context: {{
                page_url: window.location.href,
                page_title: document.title,
                referrer: document.referrer,
                user_agent: navigator.userAgent,
                screen_resolution: screen.width + 'x' + screen.height,
                language: navigator.language,
                timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
            }}
        }};

        fetch(ATB.endpoint, {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify(eventData)
        }}).catch(console.error);
    }}

    // 自动追踪点击事件（可配置）
    document.addEventListener('click', function(e) {{
        var target = e.target;
        var eventData = {{
            event_type: 'click',
            event_name: 'click',
            timestamp: new Date().toISOString(),
            user: {{
                session_id: ATB.sessionId,
                anonymous_id: ATB.anonymousId
            }},
            context: {{
                page_url: window.location.href,
                page_title: document.title
            }},
            properties: {{
                element_id: target.id || null,
                element_text: target.innerText || target.textContent,
                element_class: target.className || null,
                target_url: target.href || null
            }}
        }};

        // 异步发送，不阻塞点击
        navigator.sendBeacon(ATB.endpoint, JSON.stringify(eventData));
    }});

    // 页面加载完成后追踪
    if (document.readyState === 'loading') {{
        document.addEventListener('DOMContentLoaded', trackPageView);
    }} else {{
        trackPageView();
    }}

    // 暴露全局追踪方法
    window.ATBTrack = function(eventName, properties) {{
        var eventData = {{
            event_type: 'custom',
            event_name: eventName,
            timestamp: new Date().toISOString(),
            user: {{
                session_id: ATB.sessionId,
                anonymous_id: ATB.anonymousId
            }},
            context: {{
                page_url: window.location.href,
                page_title: document.title
            }},
            properties: properties || {{}}
        }};

        fetch(ATB.endpoint, {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify(eventData)
        }}).catch(console.error);
    }};
}})();
</script>
<!-- End AI Traffic Booster Tracking Code -->
"""


# 全局服务实例
event_tracking_service = EventTrackingService()
