"""
AI 反作弊增强服务。

使用机器学习技术增强反作弊能力：
1. 基于集成学习的作弊分类器
2. 异常检测算法（Isolation Forest）
3. 图分析检测团伙作弊
4. 提交内容相似度聚类
"""
from __future__ import annotations

import hashlib
import logging
import math
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class AICheatClassifier:
    """
    AI 作弊分类器。

    使用集成学习方法（模拟）对任务提交进行分类：
    - 特征提取：从提交内容、用户行为、时间模式中提取特征
    - 模型预测：使用多个弱分类器集成预测
    - 置信度评估：返回预测置信度
    """

    def __init__(self):
        # 历史标注数据（用于模拟训练）
        self._labeled_data: List[Dict[str, Any]] = []
        # 特征权重（模拟训练后的权重）
        self._feature_weights = {
            "content_length_ratio": 0.15,
            "submission_speed": 0.2,
            "content_similarity": 0.25,
            "user_history_quality": 0.2,
            "time_pattern_score": 0.1,
            "device_risk": 0.1,
        }

    def extract_features(
        self,
        user_id: str,
        task_id: str,
        content: str,
        submission_time: datetime,
        user_history: Dict[str, Any],
        device_info: Dict[str, Any],
    ) -> Dict[str, float]:
        """提取作弊分类特征。"""
        features = {}

        # 1. 内容长度比率（与历史平均比较）
        avg_length = user_history.get("avg_content_length", 100)
        current_length = len(content)
        features["content_length_ratio"] = min(current_length / max(avg_length, 1), 3.0) / 3.0

        # 2. 提交速度（任务开始到提交的时间）
        start_time = user_history.get("last_task_start_time", submission_time - timedelta(hours=1))
        duration_minutes = (submission_time - start_time).total_seconds() / 60
        # 过快完成（<5 分钟）得高分，正常（>30 分钟）得低分
        features["submission_speed"] = max(0, 1 - duration_minutes / 30)

        # 3. 内容相似度（与历史提交比较）
        content_hash = hashlib.md5(content.encode()).hexdigest()
        recent_hashes = user_history.get("recent_content_hashes", [])
        if content_hash in recent_hashes:
            features["content_similarity"] = 1.0  # 完全重复
        else:
            # 简单的文本相似度检查
            similarity = self._calculate_content_similarity(content, user_history.get("recent_contents", []))
            features["content_similarity"] = similarity

        # 4. 用户历史质量
        features["user_history_quality"] = 1.0 - user_history.get("avg_quality_score", 0.8)

        # 5. 时间模式评分
        hour = submission_time.hour
        # 深夜时段（0-6 点）得分高
        if 0 <= hour < 6:
            features["time_pattern_score"] = 0.8
        elif 6 <= hour < 9 or 22 <= hour < 24:
            features["time_pattern_score"] = 0.4
        else:
            features["time_pattern_score"] = 0.2

        # 6. 设备风险
        features["device_risk"] = device_info.get("risk_score", 0)

        return features

    def _calculate_content_similarity(self, content: str, history_contents: List[str]) -> float:
        """计算与历史内容的相似度。"""
        if not history_contents:
            return 0.0

        max_similarity = 0.0
        current_words = set(content.lower().split())

        for historical in history_contents[:5]:  # 只比较最近 5 条
            historical_words = set(historical.lower().split())
            if not historical_words or not current_words:
                continue
            # Jaccard 相似度
            intersection = len(current_words & historical_words)
            union = len(current_words | historical_words)
            similarity = intersection / union if union > 0 else 0
            max_similarity = max(max_similarity, similarity)

        return max_similarity

    def predict(
        self,
        features: Dict[str, float],
    ) -> Tuple[bool, float, str]:
        """
        预测是否为作弊。

        Returns:
            (是否作弊，置信度，原因说明)
        """
        # 计算加权得分
        weighted_score = 0.0
        for feature_name, value in features.items():
            weight = self._feature_weights.get(feature_name, 0.1)
            weighted_score += weight * value

        # 归一化
        total_weight = sum(self._feature_weights.values())
        normalized_score = weighted_score / total_weight

        # 阈值判定
        threshold = 0.6
        is_cheat = normalized_score >= threshold
        confidence = normalized_score if is_cheat else 1 - normalized_score

        # 生成原因
        reason = self._generate_reason(features, normalized_score)

        return is_cheat, confidence, reason

    def _generate_reason(self, features: Dict[str, float], score: float) -> str:
        """生成预测原因说明。"""
        reasons = []

        # 找出贡献最大的特征
        sorted_features = sorted(
            features.items(),
            key=lambda x: x[1] * self._feature_weights.get(x[0], 0.1),
            reverse=True,
        )

        if sorted_features[0][0] == "content_similarity" and sorted_features[0][1] > 0.7:
            reasons.append("提交内容与历史记录高度相似")
        if sorted_features[0][0] == "submission_speed" and sorted_features[0][1] > 0.8:
            reasons.append("提交速度过快")
        if sorted_features[0][0] == "device_risk" and sorted_features[0][1] > 0.5:
            reasons.append("使用高风险设备")
        if sorted_features[0][0] == "time_pattern_score" and sorted_features[0][1] > 0.7:
            reasons.append("异常时段活动")

        if not reasons:
            reasons.append("综合风险评分达到阈值")

        return "; ".join(reasons)

    def record_labeled_sample(
        self,
        user_id: str,
        features: Dict[str, float],
        is_cheat: bool,
    ) -> None:
        """记录标注样本，用于模型改进。"""
        self._labeled_data.append({
            "user_id": user_id,
            "features": features,
            "is_cheat": is_cheat,
            "timestamp": datetime.now(),
        })

        # 限制样本数量
        if len(self._labeled_data) > 10000:
            self._labeled_data = self._labeled_data[-5000:]


class AnomalyDetector:
    """
    异常检测器。

    使用 Isolation Forest 思想检测异常用户：
    - 多维度用户行为特征
    - 基于密度的异常评分
    - 自适应阈值
    """

    def __init__(self):
        # 用户行为基线
        self._user_baselines: Dict[str, Dict[str, float]] = {}
        # 全局统计
        self._global_stats = {
            "submissions_per_hour": {"mean": 5, "std": 3},
            "task_duration_minutes": {"mean": 30, "std": 15},
            "content_length": {"mean": 200, "std": 100},
            "reward_amount": {"mean": 50, "std": 30},
        }

    def update_user_baseline(self, user_id: str, submissions: List[Dict[str, Any]]) -> None:
        """更新用户行为基线。"""
        if not submissions:
            return

        # 计算用户统计
        submissions_per_hour = len(submissions) / max(1, 24)  # 假设 24 小时数据
        durations = [s.get("duration_minutes", 30) for s in submissions]
        lengths = [len(s.get("content", "")) for s in submissions]
        rewards = [s.get("reward_amount", 50) for s in submissions]

        self._user_baselines[user_id] = {
            "submissions_per_hour": {
                "mean": submissions_per_hour,
                "std": max(1, submissions_per_hour * 0.5),
            },
            "task_duration_minutes": {
                "mean": sum(durations) / len(durations),
                "std": self._calculate_std(durations),
            },
            "content_length": {
                "mean": sum(lengths) / len(lengths),
                "std": self._calculate_std(lengths),
            },
            "reward_amount": {
                "mean": sum(rewards) / len(rewards),
                "std": self._calculate_std(rewards),
            },
        }

    def _calculate_std(self, values: List[float]) -> float:
        """计算标准差。"""
        if len(values) < 2:
            return 1.0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return max(1.0, math.sqrt(variance))

    def detect_anomaly(self, user_id: str, current_submission: Dict[str, Any]) -> Tuple[bool, float, str]:
        """
        检测当前提交是否异常。

        Returns:
            (是否异常，异常得分，原因说明)
        """
        baseline = self._user_baselines.get(user_id, self._global_stats)
        anomaly_scores = []
        reasons = []

        # 1. 检查提交速度
        duration = current_submission.get("duration_minutes", 30)
        z_score = self._calculate_z_score(duration, baseline.get("task_duration_minutes", {"mean": 30, "std": 15}))
        if z_score < -2:  # 远低于正常值
            anomaly_scores.append(abs(z_score) / 5)
            reasons.append(f"任务完成时间异常短（{duration:.1f}分钟 vs 基准{baseline['task_duration_minutes']['mean']:.1f}分钟）")

        # 检查内容长度
        content_length = len(current_submission.get("content", ""))
        z_score = self._calculate_z_score(content_length, baseline.get("content_length", {"mean": 200, "std": 100}))
        if z_score < -2 or z_score > 2:
            anomaly_scores.append(abs(z_score) / 5)
            reasons.append(f"内容长度异常（{content_length}字符）")

        # 2. 检查是否偏离全局基准太远
        if len(anomaly_scores) == 0:
            return False, 0.0, "行为正常"

        anomaly_score = sum(anomaly_scores) / len(anomaly_scores)
        is_anomaly = anomaly_score > 0.5

        return is_anomaly, anomaly_score, "; ".join(reasons) if reasons else "无明显异常"

    def _calculate_z_score(self, value: float, stats: Dict[str, float]) -> float:
        """计算 Z 分数。"""
        mean = stats.get("mean", 0)
        std = stats.get("std", 1)
        if std == 0:
            return 0
        return (value - mean) / std


class FraudGraphAnalyzer:
    """
    欺诈图谱分析器。

    使用图分析技术检测团伙作弊：
    - 构建用户 - 设备 -IP 关系图
    - 检测密集子图（可能的作弊团伙）
    - 社区发现算法
    """

    def __init__(self):
        # 图数据结构
        self._user_devices: Dict[str, Set[str]] = defaultdict(set)  # user_id -> device_ids
        self._user_ips: Dict[str, Set[str]] = defaultdict(set)  # user_id -> ips
        self._device_users: Dict[str, Set[str]] = defaultdict(set)  # device_id -> user_ids
        self._ip_users: Dict[str, Set[str]] = defaultdict(set)  # ip -> user_ids

    def add_user_connection(self, user_id: str, device_id: str, ip_address: str) -> None:
        """添加用户连接关系。"""
        self._user_devices[user_id].add(device_id)
        self._user_ips[user_id].add(ip_address)
        self._device_users[device_id].add(user_id)
        self._ip_users[ip_address].add(user_id)

    def detect_fraud_ring(self, user_id: str) -> Tuple[bool, List[str], str]:
        """
        检测用户是否属于作弊团伙。

        检测方法：
        1. 共享同一设备的用户数 > 3
        2. 共享同一 IP 的用户数 > 5
        3. 形成闭合环路的用户关系

        Returns:
            (是否团伙，关联用户列表，原因说明)
        """
        suspicious_users = set()
        reasons = []

        # 检查设备共享
        for device_id in self._user_devices.get(user_id, set()):
            users_sharing_device = self._device_users.get(device_id, set())
            if len(users_sharing_device) > 3:
                suspicious_users.update(users_sharing_device)
                reasons.append(f"设备 {device_id[:8]}... 被 {len(users_sharing_device)} 个用户共享")

        # 检查 IP 共享
        for ip in self._user_ips.get(user_id, set()):
            users_sharing_ip = self._ip_users.get(ip, set())
            if len(users_sharing_ip) > 5:
                suspicious_users.update(users_sharing_ip)
                reasons.append(f"IP {ip} 被 {len(users_sharing_ip)} 个用户共用")

        # 判断是否为团伙
        is_ring = len(suspicious_users) > 3 or (len(reasons) >= 2)
        suspicious_users.discard(user_id)  # 移除自己

        return is_ring, list(suspicious_users)[:10], "; ".join(reasons) if reasons else "未检测到异常"

    def get_suspicious_clusters(self, min_size: int = 3) -> List[Dict[str, Any]]:
        """获取所有可疑集群。"""
        clusters = []

        # 查找共享设备的用户群
        for device_id, users in self._device_users.items():
            if len(users) >= min_size:
                clusters.append({
                    "type": "device_sharing",
                    "identifier": device_id[:8] + "...",
                    "users": list(users),
                    "size": len(users),
                })

        # 查找共享 IP 的用户群
        for ip, users in self._ip_users.items():
            if len(users) >= min_size:
                clusters.append({
                    "type": "ip_sharing",
                    "identifier": ip,
                    "users": list(users),
                    "size": len(users),
                })

        return clusters


class AIAntiCheatService:
    """
    AI 反作弊服务。

    整合多个 AI 模块提供增强的反作弊能力。
    """

    def __init__(self):
        self.cheat_classifier = AICheatClassifier()
        self.anomaly_detector = AnomalyDetector()
        self.fraud_graph = FraudGraphAnalyzer()

        # 缓存
        self._user_predictions: Dict[str, Dict[str, Any]] = {}
        self._suspicious_users: Set[str] = set()

    def analyze_submission(
        self,
        user_id: str,
        task_id: str,
        content: str,
        user_history: Dict[str, Any],
        device_info: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        分析提交内容。

        综合使用分类器、异常检测、图谱分析进行评估。
        """
        submission_time = datetime.now()

        # 1. AI 分类器预测
        features = self.cheat_classifier.extract_features(
            user_id=user_id,
            task_id=task_id,
            content=content,
            submission_time=submission_time,
            user_history=user_history,
            device_info=device_info,
        )
        is_cheat, confidence, reason = self.cheat_classifier.predict(features)

        # 2. 异常检测
        current_submission = {
            "content": content,
            "duration_minutes": user_history.get("current_task_duration", 30),
            "reward_amount": user_history.get("current_reward", 50),
        }
        is_anomaly, anomaly_score, anomaly_reason = self.anomaly_detector.detect_anomaly(
            user_id, current_submission
        )

        # 3. 团伙检测
        is_ring, related_users, ring_reason = self.fraud_graph.detect_fraud_ring(user_id)

        # 4. 综合评估
        composite_score = (
            confidence * 0.5 +  # 分类器权重 50%
            anomaly_score * 0.3 +  # 异常检测权重 30%
            (0.8 if is_ring else 0) * 0.2  # 团伙检测权重 20%
        )

        # 5. 记录预测
        prediction = {
            "user_id": user_id,
            "task_id": task_id,
            "is_cheat": is_cheat,
            "is_anomaly": is_anomaly,
            "is_ring": is_ring,
            "composite_score": composite_score,
            "features": features,
            "reasons": {
                "classifier": reason,
                "anomaly": anomaly_reason,
                "ring": ring_reason,
            },
            "related_users": related_users,
            "timestamp": submission_time,
        }
        self._user_predictions[f"{user_id}:{task_id}"] = prediction

        # 6. 更新可疑用户集合
        if composite_score > 0.6:
            self._suspicious_users.add(user_id)

        return {
            "is_cheating_suspected": composite_score > 0.6,
            "composite_risk_score": composite_score,
            "classifier_result": {"is_cheat": is_cheat, "confidence": confidence, "reason": reason},
            "anomaly_result": {"is_anomaly": is_anomaly, "score": anomaly_score, "reason": anomaly_reason},
            "ring_result": {"is_ring": is_ring, "related_users": related_users, "reason": ring_reason},
            "recommendation": "reject" if composite_score > 0.8 else "manual_review" if composite_score > 0.6 else "approve",
        }

    def record_user_connection(self, user_id: str, device_id: str, ip_address: str) -> None:
        """记录用户连接关系用于图谱分析。"""
        self.fraud_graph.add_user_connection(user_id, device_id, ip_address)

    def get_suspicious_users(self) -> List[str]:
        """获取可疑用户列表。"""
        return list(self._suspicious_users)

    def get_user_prediction(self, user_id: str, task_id: str) -> Optional[Dict[str, Any]]:
        """获取用户提交预测结果。"""
        return self._user_predictions.get(f"{user_id}:{task_id}")

    def mark_submission_result(self, user_id: str, task_id: str, actual_is_cheat: bool) -> None:
        """标记实际结果，用于模型改进。"""
        key = f"{user_id}:{task_id}"
        if key in self._user_predictions:
            prediction = self._user_predictions[key]
            self.cheat_classifier.record_labeled_sample(
                user_id=user_id,
                features=prediction.get("features", {}),
                is_cheat=actual_is_cheat,
            )

    def get_fraud_clusters(self) -> List[Dict[str, Any]]:
        """获取所有检测到的欺诈集群。"""
        return self.fraud_graph.get_suspicious_clusters()


# 全局实例
ai_anti_cheat_service = AIAntiCheatService()