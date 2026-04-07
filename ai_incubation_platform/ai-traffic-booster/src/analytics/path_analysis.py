"""
用户行为路径分析服务

功能:
- 用户行为路径追踪
- 桑基图数据生成
- 常见路径挖掘
- 路径转化率分析
"""
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, date, timedelta
from collections import defaultdict, Counter
import logging
import json

from schemas.analytics import TrackingEvent, EventType
from analytics.event_tracking import event_tracking_service

logger = logging.getLogger(__name__)


class PathAnalysisService:
    """
    用户行为路径分析服务

    对标 Google Analytics 的用户路径分析能力:
    - 用户行为路径追踪
    - 桑基图数据生成
    - 常见路径挖掘
    - 路径转化率分析
    """

    def __init__(self):
        # 路径分析配置
        self.max_path_length = 5          # 最大路径长度
        self.min_path_frequency = 10      # 最小路径频次
        self.max_sankey_nodes = 50        # 桑基图最大节点数

    def analyze_user_paths(
        self,
        start_date: date,
        end_date: date,
        domain: Optional[str] = None,
        max_paths: int = 20
    ) -> Dict[str, Any]:
        """
        分析用户行为路径

        Args:
            start_date: 开始日期
            end_date: 结束日期
            domain: 域名（可选）
            max_paths: 返回的最大路径数

        Returns:
            路径分析结果
        """
        # 获取事件数据
        events = event_tracking_service.get_events(
            start_date=start_date,
            end_date=end_date,
            limit=10000
        )

        if not events:
            return {"error": "未找到事件数据"}

        # 按会话分组事件
        session_events = self._group_by_session(events)

        # 构建路径
        paths = self._build_paths(session_events)

        # 统计路径频率
        path_counts = Counter(paths)

        # 获取最常见路径
        common_paths = path_counts.most_common(max_paths)

        # 计算路径转化率
        path_conversion = self._calculate_path_conversion(common_paths, session_events)

        # 生成桑基图数据
        sankey_data = self._generate_sankey_data(paths, max_nodes=self.max_sankey_nodes)

        # 路径统计
        path_stats = self._calculate_path_stats(paths)

        return {
            "period": {"start": str(start_date), "end": str(end_date)},
            "total_sessions": len(session_events),
            "total_paths": len(paths),
            "unique_paths": len(path_counts),
            "common_paths": [
                {
                    "path": path,
                    "count": count,
                    "percentage": round(count / len(paths) * 100, 2) if paths else 0
                }
                for path, count in common_paths
            ],
            "path_conversion": path_conversion,
            "sankey_data": sankey_data,
            "path_stats": path_stats
        }

    def analyze_entry_exit_paths(
        self,
        start_date: date,
        end_date: date,
        domain: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        分析入口和退出路径

        Args:
            start_date: 开始日期
            end_date: 结束日期
            domain: 域名

        Returns:
            入口/退出路径分析
        """
        events = event_tracking_service.get_events(
            start_date=start_date,
            end_date=end_date,
            limit=10000
        )

        if not events:
            return {"error": "未找到事件数据"}

        session_events = self._group_by_session(events)

        # 统计入口页面
        entry_pages = Counter()
        exit_pages = Counter()

        for session_id, session_data in session_events.items():
            if session_data["events"]:
                # 入口页面（第一个事件）
                entry_page = session_data["events"][0].context.page_url
                entry_pages[entry_page] += 1

                # 退出页面（最后一个事件）
                exit_page = session_data["events"][-1].context.page_url
                exit_pages[exit_page] += 1

        total_sessions = len(session_events)

        return {
            "period": {"start": str(start_date), "end": str(end_date)},
            "total_sessions": total_sessions,
            "top_entry_pages": [
                {"page": page, "count": count, "percentage": round(count / total_sessions * 100, 2)}
                for page, count in entry_pages.most_common(10)
            ],
            "top_exit_pages": [
                {"page": page, "count": count, "percentage": round(count / total_sessions * 2)}
                for page, count in exit_pages.most_common(10)
            ]
        }

    def analyze_conversion_paths(
        self,
        start_date: date,
        end_date: date,
        conversion_event: str = "purchase"
    ) -> Dict[str, Any]:
        """
        分析转化路径

        Args:
            start_date: 开始日期
            end_date: 结束日期
            conversion_event: 转化事件名称

        Returns:
            转化路径分析
        """
        events = event_tracking_service.get_events(
            start_date=start_date,
            end_date=end_date,
            limit=10000
        )

        if not events:
            return {"error": "未找到事件数据"}

        # 按会话分组
        session_events = self._group_by_session(events)

        # 找出有转化的会话
        converted_sessions = {}
        non_converted_sessions = {}

        for session_id, session_data in session_events.items():
            has_conversion = any(
                e.event_name == conversion_event
                for e in session_data["events"]
            )
            if has_conversion:
                converted_sessions[session_id] = session_data
            else:
                non_converted_sessions[session_id] = session_data

        # 分析转化前的路径
        pre_conversion_paths = []
        for session_id, session_data in converted_sessions.items():
            events_list = session_data["events"]
            for i, event in enumerate(events_list):
                if event.event_name == conversion_event:
                    # 转化前的路径
                    path = [e.context.page_url for e in events_list[:i+1]]
                    pre_conversion_paths.append(path)
                    break

        # 统计路径
        path_counts = Counter(tuple(p) for p in pre_conversion_paths)

        return {
            "period": {"start": str(start_date), "end": str(end_date)},
            "conversion_event": conversion_event,
            "total_conversions": len(converted_sessions),
            "conversion_rate": round(len(converted_sessions) / len(session_events) * 100, 2) if session_events else 0,
            "top_conversion_paths": [
                {
                    "path": list(path),
                    "count": count,
                    "percentage": round(count / len(pre_conversion_paths) * 100, 2) if pre_conversion_paths else 0
                }
                for path, count in path_counts.most_common(10)
            ],
            "avg_steps_to_conversion": round(
                sum(len(p) for p in pre_conversion_paths) / len(pre_conversion_paths), 2
            ) if pre_conversion_paths else 0
        }

    def get_path_drop_off(
        self,
        start_date: date,
        end_date: date,
        target_path: List[str]
    ) -> Dict[str, Any]:
        """
        分析特定路径的流失情况

        Args:
            start_date: 开始日期
            end_date: 结束日期
            target_path: 目标路径

        Returns:
            路径流失分析
        """
        events = event_tracking_service.get_events(
            start_date=start_date,
            end_date=end_date,
            limit=10000
        )

        if not events:
            return {"error": "未找到事件数据"}

        session_events = self._group_by_session(events)

        # 统计每个步骤的到达人数
        step_counts = defaultdict(int)
        step_dropoffs = defaultdict(list)

        for session_id, session_data in session_events.items():
            session_path = [e.context.page_url for e in session_data["events"]]

            # 检查路径匹配
            matched_steps = self._match_path(session_path, target_path)

            for step_idx in matched_steps:
                step_counts[step_idx] += 1

                # 记录在这一步流失的用户
                if step_idx < len(target_path) - 1:
                    next_step_reached = step_idx + 1 in matched_steps
                    if not next_step_reached:
                        step_dropoffs[step_idx].append(session_id)

        # 计算流失率
        dropoff_analysis = []
        for i, step in enumerate(target_path):
            current_count = step_counts.get(i, 0)
            next_count = step_counts.get(i + 1, 0) if i < len(target_path) - 1 else current_count

            dropoff_count = current_count - next_count
            dropoff_rate = dropoff_count / current_count if current_count > 0 else 0

            dropoff_analysis.append({
                "step": i,
                "page": step,
                "users": current_count,
                "dropoff_count": dropoff_count,
                "dropoff_rate": round(dropoff_rate, 4)
            })

        # 找出流失最严重的步骤
        max_dropoff = max(dropoff_analysis, key=lambda x: x["dropoff_rate"]) if dropoff_analysis else None

        return {
            "target_path": target_path,
            "period": {"start": str(start_date), "end": str(end_date)},
            "step_analysis": dropoff_analysis,
            "max_dropoff_step": max_dropoff,
            "recommendations": self._generate_dropoff_recommendations(max_dropoff) if max_dropoff else []
        }

    def _group_by_session(
        self,
        events: List[TrackingEvent]
    ) -> Dict[str, Dict[str, Any]]:
        """按会话分组事件"""
        session_events = defaultdict(lambda: {"events": [], "user_id": None})

        for event in events:
            session_id = event.user.session_id
            session_events[session_id]["events"].append(event)
            session_events[session_id]["user_id"] = event.user.user_id

        # 按时间排序
        for session_id, data in session_events.items():
            data["events"].sort(key=lambda e: e.timestamp)

        return dict(session_events)

    def _build_paths(
        self,
        session_events: Dict[str, Dict[str, Any]]
    ) -> List[Tuple[str, ...]]:
        """构建路径列表"""
        paths = []

        for session_id, data in session_events.items():
            events_list = data["events"]
            if not events_list:
                continue

            # 提取页面路径
            page_path = tuple(e.context.page_url for e in events_list[:self.max_path_length])
            paths.append(page_path)

        return paths

    def _calculate_path_conversion(
        self,
        common_paths: List[Tuple[Tuple[str, ...], int]],
        session_events: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """计算路径转化率"""
        conversion_data = []

        for path, count in common_paths[:10]:
            # 统计此路径的转化数
            conversions = 0
            for session_id, data in session_events.items():
                session_path = tuple(e.context.page_url for e in data["events"][:self.max_path_length])
                if session_path == path:
                    # 检查是否有转化事件
                    has_conversion = any(
                        e.event_name in ["purchase", "sign_up", "form_submit"]
                        for e in data["events"]
                    )
                    if has_conversion:
                        conversions += 1

            conversion_data.append({
                "path": list(path),
                "sessions": count,
                "conversions": conversions,
                "conversion_rate": round(conversions / count * 100, 2) if count > 0 else 0
            })

        return conversion_data

    def _generate_sankey_data(
        self,
        paths: List[Tuple[str, ...]],
        max_nodes: int = 50
    ) -> Dict[str, Any]:
        """
        生成桑基图数据

        Returns:
            {
                "nodes": [{"id": "page1", "label": "页面 1"}, ...],
                "links": [
                    {"source": "page1", "target": "page2", "value": 100},
                    ...
                ]
            }
        """
        # 统计节点
        node_counts = Counter()
        link_counts = defaultdict(int)

        for path in paths:
            for i, page in enumerate(path):
                node_id = f"{i}_{page}"
                node_counts[node_id] += 1

                if i < len(path) - 1:
                    link_key = (f"{i}_{page}", f"{i+1}_{path[i+1]}")
                    link_counts[link_key] += 1

        # 限制节点数量
        top_nodes = node_counts.most_common(max_nodes)
        node_ids = {n[0] for n in top_nodes}

        # 构建节点列表
        nodes = []
        node_index = {}
        for i, (node_id, count) in enumerate(top_nodes):
            nodes.append({
                "id": node_id,
                "label": node_id.split("_", 1)[1] if "_" in node_id else node_id,
                "step": int(node_id.split("_")[0]) if "_" in node_id else 0,
                "visits": count
            })
            node_index[node_id] = i

        # 构建链接列表
        links = []
        for (source, target), value in link_counts.items():
            if source in node_index and target in node_index:
                links.append({
                    "source": node_index[source],
                    "target": node_index[target],
                    "value": value
                })

        return {"nodes": nodes, "links": links}

    def _calculate_path_stats(
        self,
        paths: List[Tuple[str, ...]]
    ) -> Dict[str, Any]:
        """计算路径统计信息"""
        if not paths:
            return {}

        path_lengths = [len(p) for p in paths]

        return {
            "avg_path_length": round(sum(path_lengths) / len(paths), 2),
            "min_path_length": min(path_lengths),
            "max_path_length": max(path_lengths),
            "median_path_length": sorted(path_lengths)[len(path_lengths) // 2]
        }

    def _match_path(
        self,
        session_path: List[str],
        target_path: List[str]
    ) -> List[int]:
        """匹配路径，返回匹配的步骤索引"""
        matched = []
        session_idx = 0

        for target_idx, target_page in enumerate(target_path):
            while session_idx < len(session_path):
                if session_path[session_idx] == target_page:
                    matched.append(target_idx)
                    session_idx += 1
                    break
                session_idx += 1

        return matched

    def _generate_dropoff_recommendations(
        self,
        max_dropoff: Dict[str, Any]
    ) -> List[str]:
        """生成流失优化建议"""
        recommendations = []

        step = max_dropoff["step"]
        page = max_dropoff["page"]
        rate = max_dropoff["dropoff_rate"]

        if rate > 0.7:
            recommendations.append(f"【严重】步骤{step} ({page}) 流失率高达{rate*100:.1f}%，需要立即优化")
        elif rate > 0.5:
            recommendations.append(f"步骤{step} ({page}) 流失率较高 ({rate*100:.1f}%)，建议优化")

        recommendations.extend([
            "检查页面加载速度是否过慢",
            "确认页面内容是否符合用户预期",
            "优化页面导航和 CTA 按钮",
            "考虑添加进度指示器",
            "进行 A/B 测试寻找最优方案"
        ])

        return recommendations[:5]


# 全局服务实例
path_analysis_service = PathAnalysisService()
