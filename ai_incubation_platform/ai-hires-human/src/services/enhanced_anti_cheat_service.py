"""
增强反作弊服务 - 设备指纹识别、IP 地址检测、异常行为模式识别。
"""
from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from collections import defaultdict

from models.task import Task

logger = logging.getLogger(__name__)


class DeviceFingerprint:
    """
    设备指纹识别。

    通过多种信号组合生成设备唯一标识：
    - User-Agent
    - IP 地址
    - 屏幕分辨率（如果提供）
    - 时区（如果提供）
    - 语言（如果提供）
    - 其他浏览器特征
    """

    def __init__(self) -> None:
        # 设备指纹缓存：fingerprint -> device_info
        self._device_fingerprints: Dict[str, Dict[str, Any]] = {}
        # IP 到设备指纹的映射：ip -> [fingerprints]
        self._ip_to_devices: Dict[str, Set[str]] = defaultdict(set)
        # 用户 ID 到设备指纹的映射：user_id -> [fingerprints]
        self._user_to_devices: Dict[str, Set[str]] = defaultdict(set)

    def generate_fingerprint(
        self,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
        screen_resolution: Optional[str] = None,
        timezone: Optional[str] = None,
        language: Optional[str] = None,
        canvas_hash: Optional[str] = None,
        webgl_hash: Optional[str] = None,
    ) -> str:
        """
        生成设备指纹。

        组合多个信号生成唯一的设备标识符。
        """
        # 组合所有可用信号
        signals = [
            user_agent or "",
            ip_address or "",
            screen_resolution or "",
            timezone or "",
            language or "",
            canvas_hash or "",
            webgl_hash or "",
        ]

        # 生成哈希
        fingerprint_data = "|".join(signals)
        fingerprint = hashlib.sha256(fingerprint_data.encode("utf-8")).hexdigest()[:32]

        # 缓存设备信息
        if fingerprint not in self._device_fingerprints:
            self._device_fingerprints[fingerprint] = {
                "fingerprint": fingerprint,
                "user_agent": user_agent,
                "ip_address": ip_address,
                "screen_resolution": screen_resolution,
                "timezone": timezone,
                "language": language,
                "canvas_hash": canvas_hash,
                "webgl_hash": webgl_hash,
                "first_seen": datetime.now(),
                "last_seen": datetime.now(),
                "user_ids": set(),
            }

        # 更新最后见到时间
        self._device_fingerprints[fingerprint]["last_seen"] = datetime.now()

        # 更新 IP 到设备映射
        if ip_address:
            self._ip_to_devices[ip_address].add(fingerprint)

        return fingerprint

    def register_user_device(self, user_id: str, fingerprint: str) -> None:
        """注册用户与设备的关联。"""
        self._user_to_devices[user_id].add(fingerprint)
        if fingerprint in self._device_fingerprints:
            self._device_fingerprints[fingerprint]["user_ids"].add(user_id)

    def get_user_devices(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户关联的所有设备。"""
        fingerprints = self._user_to_devices.get(user_id, set())
        return [
            self._device_fingerprints[fp]
            for fp in fingerprints
            if fp in self._device_fingerprints
        ]

    def get_ip_devices(self, ip_address: str) -> List[Dict[str, Any]]:
        """获取同一 IP 下的所有设备。"""
        fingerprints = self._ip_to_devices.get(ip_address, set())
        return [
            self._device_fingerprints[fp]
            for fp in fingerprints
            if fp in self._device_fingerprints
        ]

    def is_suspicious_device(self, fingerprint: str) -> Tuple[bool, Optional[str]]:
        """
        检查设备是否可疑。

        检测逻辑：
        1. 设备是否关联了过多用户账号（>5 个）
        2. 设备特征是否异常（如 User-Agent 为空）
        """
        if fingerprint not in self._device_fingerprints:
            return False, None

        device = self._device_fingerprints[fingerprint]

        # 检查关联用户数
        if len(device["user_ids"]) > 5:
            return True, f"设备关联了{len(device['user_ids'])}个用户账号，超过阈值"

        # 检查 User-Agent 是否异常
        if not device.get("user_agent"):
            return True, "缺少 User-Agent 信息"

        # 检查是否为已知自动化工具
        ua = device.get("user_agent", "").lower()
        automation_patterns = [
            r"headless",
            r"phantomjs",
            r"selenium",
            r"puppeteer",
            r"playwright",
            r"curl",
            r"wget",
        ]
        for pattern in automation_patterns:
            if re.search(pattern, ua):
                return True, f"检测到自动化工具：{pattern}"

        return False, None


class IPDetector:
    """
    IP 地址检测和风险评估。

    功能：
    1. IP 地理位置检测
    2. 代理/VPN 检测
    3. 数据中心 IP 检测
    4. IP 风险评估
    """

    def __init__(self) -> None:
        # IP 记录：ip -> info
        self._ip_records: Dict[str, Dict[str, Any]] = {}
        # IP 黑名单
        self._ip_blacklist: Set[str] = set()
        # 已知数据中心 IP 段（示例）
        self._datacenter_ranges = [
            "10.0.0.0/8",  # 私有网络
            "172.16.0.0/12",
            "192.168.0.0/16",
            # 可以添加更多已知的数据中心 IP 段
        ]
        # 高风险地区（示例）
        self._high_risk_countries = set()

    def analyze_ip(
        self,
        ip_address: str,
        country: Optional[str] = None,
        region: Optional[str] = None,
        city: Optional[str] = None,
        isp: Optional[str] = None,
        is_proxy: Optional[bool] = None,
        is_vpn: Optional[bool] = None,
        is_tor: Optional[bool] = None,
        is_datacenter: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        分析 IP 地址。

        返回 IP 详细信息和风险评分。
        """
        if ip_address not in self._ip_records:
            self._ip_records[ip_address] = {
                "ip": ip_address,
                "country": country,
                "region": region,
                "city": city,
                "isp": isp,
                "is_proxy": is_proxy,
                "is_vpn": is_vpn,
                "is_tor": is_tor,
                "is_datacenter": is_datacenter,
                "first_seen": datetime.now(),
                "last_seen": datetime.now(),
                "usage_count": 0,
            }

        record = self._ip_records[ip_address]
        record["last_seen"] = datetime.now()
        record["usage_count"] += 1

        # 更新信息（如果提供了新的）
        if country:
            record["country"] = country
        if region:
            record["region"] = region
        if city:
            record["city"] = city
        if isp:
            record["isp"] = isp
        if is_proxy is not None:
            record["is_proxy"] = is_proxy
        if is_vpn is not None:
            record["is_vpn"] = is_vpn
        if is_tor is not None:
            record["is_tor"] = is_tor
        if is_datacenter is not None:
            record["is_datacenter"] = is_datacenter

        # 计算风险评分
        risk_score = self._calculate_ip_risk_score(record)

        return {
            **record,
            "risk_score": risk_score,
            "risk_level": self._get_risk_level(risk_score),
        }

    def _calculate_ip_risk_score(self, record: Dict[str, Any]) -> float:
        """
        计算 IP 风险评分（0-1）。

        评分因素：
        - 代理/VPN: +0.3
        - Tor: +0.4
        - 数据中心：+0.2
        - 高风险地区：+0.2
        - 短时间内大量使用：+0.2
        """
        score = 0.0

        if record.get("is_proxy"):
            score += 0.3
        if record.get("is_vpn"):
            score += 0.3
        if record.get("is_tor"):
            score += 0.4
        if record.get("is_datacenter"):
            score += 0.2
        if record.get("country") in self._high_risk_countries:
            score += 0.2

        # 检查使用频率
        if record["usage_count"] > 100:
            score += 0.2

        return min(score, 1.0)

    def _get_risk_level(self, score: float) -> str:
        """根据评分获取风险等级。"""
        if score < 0.3:
            return "low"
        elif score < 0.6:
            return "medium"
        else:
            return "high"

    def is_ip_blacklisted(self, ip_address: str) -> bool:
        """检查 IP 是否在黑名单中。"""
        return ip_address in self._ip_blacklist

    def add_ip_to_blacklist(self, ip_address: str, reason: str) -> None:
        """将 IP 添加到黑名单。"""
        self._ip_blacklist.add(ip_address)
        logger.warning("IP added to blacklist: ip=%s, reason=%s", ip_address, reason)

    def remove_ip_from_blacklist(self, ip_address: str) -> bool:
        """从黑名单中移除 IP。"""
        if ip_address in self._ip_blacklist:
            self._ip_blacklist.remove(ip_address)
            return True
        return False


class BehavioralAnalyzer:
    """
    用户行为模式分析。

    检测异常行为模式：
    1. 提交时间异常（如深夜频繁提交）
    2. 操作速度异常（如过快完成任务）
    3. 任务选择异常（如只接高报酬任务）
    4. 地理位置跳跃（短时间内跨地区）
    """

    def __init__(self) -> None:
        # 用户行为记录：user_id -> [events]
        self._user_events: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        # 用户任务历史：user_id -> [task_info]
        self._user_task_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        # 正常行为基线
        self._normal_behavior_baseline = {
            "min_task_duration_minutes": 5,  # 最短任务完成时间
            "max_submissions_per_hour": 10,  # 每小时最大提交次数
            "night_hours": (0, 6),  # 深夜时段
        }

    def record_event(
        self,
        user_id: str,
        event_type: str,
        task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """记录用户行为事件。"""
        event = {
            "timestamp": datetime.now(),
            "event_type": event_type,
            "task_id": task_id,
            "metadata": metadata or {},
        }
        self._user_events[user_id].append(event)

        # 清理旧事件（保留 24 小时）
        cutoff = datetime.now() - timedelta(hours=24)
        self._user_events[user_id] = [
            e for e in self._user_events[user_id] if e["timestamp"] > cutoff
        ]

    def record_task_completion(
        self,
        user_id: str,
        task_id: str,
        start_time: datetime,
        end_time: datetime,
        reward_amount: float,
        interaction_type: str,
    ) -> None:
        """记录任务完成信息。"""
        task_info = {
            "task_id": task_id,
            "start_time": start_time,
            "end_time": end_time,
            "duration_minutes": (end_time - start_time).total_seconds() / 60,
            "reward_amount": reward_amount,
            "interaction_type": interaction_type,
            "completed_at": end_time,
        }
        self._user_task_history[user_id].append(task_info)

        # 清理旧记录（保留 7 天）
        cutoff = datetime.now() - timedelta(days=7)
        self._user_task_history[user_id] = [
            t for t in self._user_task_history[user_id] if t["completed_at"] > cutoff
        ]

    def analyze_user_behavior(self, user_id: str) -> Dict[str, Any]:
        """
        分析用户行为模式。

        返回行为分析报告和风险评分。
        """
        events = self._user_events.get(user_id, [])
        task_history = self._user_task_history.get(user_id, [])

        if not events and not task_history:
            return {"risk_score": 0.0, "risk_level": "unknown", "flags": []}

        flags = []
        risk_score = 0.0

        # 1. 检查提交频率
        recent_events = [
            e for e in events
            if e["timestamp"] > datetime.now() - timedelta(hours=1)
        ]
        if len(recent_events) > self._normal_behavior_baseline["max_submissions_per_hour"]:
            flags.append({
                "type": "high_frequency",
                "message": f"1 小时内{len(recent_events)}次操作，超过阈值",
            })
            risk_score += 0.3

        # 2. 检查任务完成速度
        for task in task_history:
            if task["duration_minutes"] < self._normal_behavior_baseline["min_task_duration_minutes"]:
                flags.append({
                    "type": "too_fast_completion",
                    "message": f"任务 {task['task_id']} 仅用{task['duration_minutes']:.1f}分钟完成",
                })
                risk_score += 0.2
                break  # 只标记一次

        # 3. 检查深夜活动
        night_events = [
            e for e in events
            if self._normal_behavior_baseline["night_hours"][0] <= e["timestamp"].hour < self._normal_behavior_baseline["night_hours"][1]
        ]
        if len(night_events) > 5:
            flags.append({
                "type": "suspicious_night_activity",
                "message": f"深夜时段{len(night_events)}次操作",
            })
            risk_score += 0.1

        # 4. 检查任务选择模式（只接高报酬任务）
        if len(task_history) >= 5:
            avg_reward = sum(t["reward_amount"] for t in task_history) / len(task_history)
            high_reward_tasks = [t for t in task_history if t["reward_amount"] > avg_reward * 1.5]
            if len(high_reward_tasks) / len(task_history) > 0.8:
                flags.append({
                    "type": "selective_high_reward",
                    "message": "80% 以上任务为高报酬任务，可能存在选择性刷单",
                })
                risk_score += 0.2

        return {
            "risk_score": min(risk_score, 1.0),
            "risk_level": "low" if risk_score < 0.3 else "medium" if risk_score < 0.6 else "high",
            "flags": flags,
            "total_events": len(events),
            "total_tasks": len(task_history),
        }

    def detect_location_hopping(
        self,
        user_id: str,
        locations: List[Tuple[datetime, str]],
    ) -> Tuple[bool, Optional[str]]:
        """
        检测地理位置跳跃。

        locations: [(timestamp, location), ...]
        """
        if len(locations) < 2:
            return False, None

        # 按时间排序
        sorted_locations = sorted(locations, key=lambda x: x[0])

        # 检查短时间内是否有跨地区登录
        for i in range(1, len(sorted_locations)):
            prev_time, prev_loc = sorted_locations[i - 1]
            curr_time, curr_loc = sorted_locations[i]

            time_diff = (curr_time - prev_time).total_seconds() / 60  # 分钟

            # 如果 1 小时内位置变化且位置不同
            if time_diff < 60 and prev_loc != curr_loc:
                # 简单的地理位置距离检查（实际应用应使用更精确的距离计算）
                if self._is_far_location_change(prev_loc, curr_loc):
                    return True, f"检测到异常位置跳跃：{prev_loc} -> {curr_loc}（{time_diff:.0f}分钟）"

        return False, None

    def _is_far_location_change(self, loc1: str, loc2: str) -> bool:
        """检查是否为远距离位置变化（简化实现）。"""
        # 实际实现应使用地理坐标计算距离
        # 这里简单检查是否为不同的城市/地区
        return loc1 != loc2


class EnhancedAntiCheatService:
    """
    增强反作弊服务。

    整合设备指纹、IP 检测、行为分析三大模块，
    提供全面的风险评估和作弊检测能力。
    """

    def __init__(self) -> None:
        self.device_fingerprint = DeviceFingerprint()
        self.ip_detector = IPDetector()
        self.behavioral_analyzer = BehavioralAnalyzer()

        # 风险评分缓存
        self._user_risk_scores: Dict[str, float] = {}
        # 全局风险事件日志
        self._risk_events: List[Dict[str, Any]] = []

    def register_user_activity(
        self,
        user_id: str,
        ip_address: str,
        user_agent: Optional[str] = None,
        screen_resolution: Optional[str] = None,
        timezone: Optional[str] = None,
        language: Optional[str] = None,
    ) -> str:
        """
        注册用户活动。

        生成设备指纹并记录用户 - 设备关联。
        返回设备指纹。
        """
        # 生成设备指纹
        fingerprint = self.device_fingerprint.generate_fingerprint(
            user_agent=user_agent,
            ip_address=ip_address,
            screen_resolution=screen_resolution,
            timezone=timezone,
            language=language,
        )

        # 注册用户 - 设备关联
        self.device_fingerprint.register_user_device(user_id, fingerprint)

        # 记录行为事件
        self.behavioral_analyzer.record_event(
            user_id=user_id,
            event_type="login",
            metadata={"ip": ip_address, "fingerprint": fingerprint},
        )

        return fingerprint

    def get_user_risk_assessment(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户综合风险评估。

        返回包含以下维度的评估报告：
        - 设备风险
        - IP 风险
        - 行为风险
        - 综合风险评分
        """
        # 获取用户设备
        devices = self.device_fingerprint.get_user_devices(user_id)
        device_risks = []
        for device in devices:
            is_suspicious, reason = self.device_fingerprint.is_suspicious_device(device["fingerprint"])
            if is_suspicious:
                device_risks.append({"fingerprint": device["fingerprint"], "reason": reason})

        # 获取用户 IP 风险
        ip_risks = []
        for device in devices:
            if device.get("ip_address"):
                ip_info = self.ip_detector.analyze_ip(device["ip_address"])
                if ip_info["risk_level"] in ["medium", "high"]:
                    ip_risks.append({
                        "ip": device["ip_address"],
                        "risk_level": ip_info["risk_level"],
                        "risk_score": ip_info["risk_score"],
                    })

        # 获取行为风险
        behavior_analysis = self.behavioral_analyzer.analyze_user_behavior(user_id)

        # 计算综合风险评分
        composite_score = self._calculate_composite_risk_score(
            device_risks=device_risks,
            ip_risks=ip_risks,
            behavior_analysis=behavior_analysis,
        )

        # 缓存风险评分
        self._user_risk_scores[user_id] = composite_score

        # 记录风险事件（如果风险较高）
        if composite_score >= 0.5:
            self._log_risk_event(user_id, composite_score, {
                "device_risks": device_risks,
                "ip_risks": ip_risks,
                "behavior_analysis": behavior_analysis,
            })

        return {
            "user_id": user_id,
            "composite_risk_score": composite_score,
            "risk_level": "low" if composite_score < 0.3 else "medium" if composite_score < 0.6 else "high",
            "device_risks": device_risks,
            "ip_risks": ip_risks,
            "behavior_analysis": behavior_analysis,
            "device_count": len(devices),
        }

    def _calculate_composite_risk_score(
        self,
        device_risks: List[Dict],
        ip_risks: List[Dict],
        behavior_analysis: Dict[str, Any],
    ) -> float:
        """计算综合风险评分。"""
        score = 0.0

        # 设备风险权重 30%
        if device_risks:
            score += 0.3 * min(len(device_risks) / 2, 1.0)

        # IP 风险权重 30%
        if ip_risks:
            max_ip_risk = max(r["risk_score"] for r in ip_risks)
            score += 0.3 * max_ip_risk

        # 行为风险权重 40%
        behavior_score = behavior_analysis.get("risk_score", 0)
        score += 0.4 * behavior_score

        return min(score, 1.0)

    def _log_risk_event(
        self,
        user_id: str,
        risk_score: float,
        details: Dict[str, Any],
    ) -> None:
        """记录风险事件。"""
        event = {
            "timestamp": datetime.now(),
            "user_id": user_id,
            "risk_score": risk_score,
            "details": details,
        }
        self._risk_events.append(event)

        # 清理旧事件（保留 7 天）
        cutoff = datetime.now() - timedelta(days=7)
        self._risk_events = [e for e in self._risk_events if e["timestamp"] > cutoff]

        logger.warning(
            "Risk event detected: user_id=%s, risk_score=%.2f, details=%s",
            user_id, risk_score, details
        )

    def check_submission_risk(
        self,
        user_id: str,
        task_id: str,
        content: str,
        ip_address: Optional[str] = None,
    ) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """
        检查提交风险。

        在用户提交任务时调用，综合评估风险。
        返回 (是否允许提交，拒绝原因，风险评估详情)
        """
        # 获取用户风险评估
        risk_assessment = self.get_user_risk_assessment(user_id)

        # 高风险用户直接拒绝
        if risk_assessment["composite_risk_score"] >= 0.8:
            return False, "用户风险评分过高，提交被拒绝", risk_assessment

        # 检查 IP 黑名单
        if ip_address and self.ip_detector.is_ip_blacklisted(ip_address):
            return False, "IP 地址在黑名单中", risk_assessment

        # 检查设备是否可疑
        devices = self.device_fingerprint.get_user_devices(user_id)
        for device in devices:
            is_suspicious, reason = self.device_fingerprint.is_suspicious_device(device["fingerprint"])
            if is_suspicious:
                return False, f"设备可疑：{reason}", risk_assessment

        # 记录提交事件
        self.behavioral_analyzer.record_event(
            user_id=user_id,
            event_type="submission",
            task_id=task_id,
            metadata={"ip": ip_address},
        )

        return True, None, risk_assessment

    def block_ip(self, ip_address: str, reason: str) -> None:
        """封禁 IP 地址。"""
        self.ip_detector.add_ip_to_blacklist(ip_address, reason)

    def unblock_ip(self, ip_address: str) -> bool:
        """解封 IP 地址。"""
        return self.ip_detector.remove_ip_from_blacklist(ip_address)

    def get_risk_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取风险事件日志。"""
        return self._risk_events[-limit:]

    def reset_state(self) -> None:
        """重置状态（用于测试）。"""
        self.device_fingerprint._device_fingerprints.clear()
        self.device_fingerprint._ip_to_devices.clear()
        self.device_fingerprint._user_to_devices.clear()
        self.ip_detector._ip_records.clear()
        self.ip_detector._ip_blacklist.clear()
        self.behavioral_analyzer._user_events.clear()
        self.behavioral_analyzer._user_task_history.clear()
        self._user_risk_scores.clear()
        self._risk_events.clear()


# 全局实例
enhanced_anti_cheat_service = EnhancedAntiCheatService()
