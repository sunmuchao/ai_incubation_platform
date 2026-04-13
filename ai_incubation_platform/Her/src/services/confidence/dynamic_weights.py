"""
动态权重优化系统

功能：
- 用户群体差异化权重配置
- 权重自适应优化器
- A/B测试支持
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import json

from utils.logger import logger
from db.models import UserDB


# ============================================
# 用户群体差异化权重配置
# ============================================

USER_GROUP_WEIGHTS = {
    "new_user": {
        "base_score": 0.20,
        "identity": 0.30,       # 新用户身份验证最重要
        "cross_validation": 0.25,
        "behavior": 0.10,       # 行为数据不足，权重低
        "social": 0.15,
        "time": 0.0,            # 无时间积累
        "description": "新用户（注册 < 7天）",
        "min_days": 0,
        "max_days": 7,
    },
    "early_user": {
        "base_score": 0.25,
        "identity": 0.25,
        "cross_validation": 0.25,
        "behavior": 0.15,
        "social": 0.15,
        "time": 0.05,
        "description": "早期用户（注册 7-30天）",
        "min_days": 7,
        "max_days": 30,
    },
    "active_user": {
        "base_score": 0.30,
        "identity": 0.20,
        "cross_validation": 0.20,
        "behavior": 0.20,       # 活跃用户行为数据丰富
        "social": 0.15,
        "time": 0.15,           # 时间积累有贡献
        "description": "活跃用户（注册 > 30天，活跃 > 10天）",
        "min_days": 30,
        "max_days": 365,
    },
    "verified_user": {
        "base_score": 0.35,
        "identity": 0.15,       # 身份已验证，权重降低
        "cross_validation": 0.25,
        "behavior": 0.20,
        "social": 0.20,
        "time": 0.10,
        "description": "已实名认证用户",
        "requires_verification": True,
    },
    "vip_user": {
        "base_score": 0.40,     # VIP有更高的基础信任
        "identity": 0.20,
        "cross_validation": 0.20,
        "behavior": 0.15,
        "social": 0.15,
        "time": 0.10,
        "description": "VIP会员用户",
        "requires_vip": True,
    },
    "long_term_user": {
        "base_score": 0.30,
        "identity": 0.15,
        "cross_validation": 0.20,
        "behavior": 0.20,
        "social": 0.20,
        "time": 0.20,           # 老用户时间积累权重高
        "description": "长期用户（注册 > 180天）",
        "min_days": 180,
        "max_days": 9999,
    },
}

# 默认权重（无法判断群体时使用）
DEFAULT_WEIGHTS = {
    "base_score": 0.30,
    "identity": 0.25,
    "cross_validation": 0.20,
    "behavior": 0.15,
    "social": 0.10,
    "time": 0.0,
}


class UserGroupClassifier:
    """用户群体分类器"""

    def classify_user(self, user: UserDB, db: Session) -> str:
        """
        根据用户特征判断所属群体

        Returns:
            群体标识：new_user, early_user, active_user, verified_user, vip_user, long_term_user
        """
        # 计算注册天数
        account_age_days = 0
        if user.created_at:
            account_age_days = (datetime.now() - user.created_at).days

        # 检查VIP状态
        if hasattr(user, 'membership_tier') and user.membership_tier in ['premium', 'vip']:
            return "vip_user"

        # 检查实名认证状态
        from db.models import IdentityVerificationDB
        verification = db.query(IdentityVerificationDB).filter(
            IdentityVerificationDB.user_id == user.id,
            IdentityVerificationDB.verification_status == 'verified'
        ).first()
        if verification:
            return "verified_user"

        # 检查长期用户
        if account_age_days >= 180:
            return "long_term_user"

        # 检查活跃用户
        # 活跃天数估算（简化实现）
        active_days = self._estimate_active_days(user, db)
        if account_age_days >= 30 and active_days >= 10:
            return "active_user"

        # 检查早期用户
        if account_age_days >= 7:
            return "early_user"

        # 默认新用户
        return "new_user"

    def _estimate_active_days(self, user: UserDB, db: Session) -> int:
        """估算用户活跃天数"""
        # 通过最后登录时间和登录次数估算
        # 简化实现：假设每天登录一次
        if hasattr(user, 'last_login') and user.last_login:
            login_count = getattr(user, 'login_count', 0) or 1
            # 如果没有登录次数字段，用注册时间估算
            if not login_count:
                account_days = (datetime.now() - user.created_at).days if user.created_at else 0
                return min(account_days // 2, 10)  # 假设一半天数活跃
            return min(login_count, account_days if user.created_at else 10)
        return 0

    def get_weights_for_group(self, group: str) -> Dict[str, float]:
        """获取指定群体的权重配置"""
        return USER_GROUP_WEIGHTS.get(group, DEFAULT_WEIGHTS)


# ============================================
# 权重自适应优化器
# ============================================

class WeightOptimizer:
    """基于反馈的自适应权重优化器"""

    # 历史反馈数据存储（简化版，实际应存数据库）
    _feedback_history: List[Dict] = []
    _current_weights: Dict[str, float] = DEFAULT_WEIGHTS.copy()
    _optimization_log: List[Dict] = []

    def record_feedback(
        self,
        user_id: str,
        predicted_confidence: float,
        actual_trustworthiness: float,
        dimensions: Dict[str, float],
        db: Session = None
    ):
        """
        记录置信度预测与实际可信度的对比

        Args:
            user_id: 用户ID
            predicted_confidence: 系统预测的置信度
            actual_trustworthiness: 实际可信度（从举报/好评/投诉等推断）
            dimensions: 各维度置信度分数
        """
        feedback = {
            "user_id": user_id,
            "predicted": predicted_confidence,
            "actual": actual_trustworthiness,
            "dimensions": dimensions,
            "error": abs(predicted_confidence - actual_trustworthiness),
            "timestamp": datetime.now().isoformat(),
        }

        self._feedback_history.append(feedback)

        # 每100条反馈进行一次优化
        if len(self._feedback_history) % 100 == 0:
            self.optimize_weights()

    def optimize_weights(self) -> Dict[str, float]:
        """
        基于历史反馈优化权重

        方法：
        - 分析各维度的预测误差
        - 误差大的维度减少权重
        - 误差小的维度增加权重

        Returns:
            新的权重配置
        """
        if len(self._feedback_history) < 50:
            logger.info(f"反馈样本不足（{len(self._feedback_history)}条），暂不优化权重")
            return self._current_weights

        logger.info(f"开始权重优化，当前反馈样本：{len(self._feedback_history)}条")

        # 计算各维度的平均贡献误差
        dimension_errors = {}
        for dim in ["identity", "cross_validation", "behavior", "social", "time"]:
            errors = []
            for feedback in self._feedback_history[-200:]:  # 最近200条
                dim_value = feedback["dimensions"].get(dim, 0)
                dim_contribution = dim_value * self._current_weights.get(dim, 0.2)
                # 加权误差：贡献越大，误差影响越大
                weighted_error = feedback["error"] * (dim_contribution / feedback["predicted"] if feedback["predicted"] > 0 else 0)
                errors.append(weighted_error)

            avg_error = sum(errors) / len(errors) if errors else 0
            dimension_errors[dim] = avg_error

        # 总误差
        total_error = sum(dimension_errors.values())

        if total_error == 0:
            logger.info("无误差，权重保持不变")
            return self._current_weights

        # 调整权重
        new_weights = {}
        for dim in self._current_weights:
            if dim == "base_score":
                new_weights[dim] = self._current_weights[dim]
                continue

            # 误差比例大的维度减少权重
            error_ratio = dimension_errors.get(dim, 0) / total_error if total_error > 0 else 0

            # 调整幅度：误差比例越大，调整越大（但限制在±10%）
            adjustment = -0.05 * error_ratio  # 最大-5%

            new_weight = self._current_weights[dim] + adjustment

            # 确保权重在合理范围（5%-35%）
            new_weight = max(0.05, min(0.35, new_weight))
            new_weights[dim] = new_weight

        # 记录优化日志
        optimization_log = {
            "timestamp": datetime.now().isoformat(),
            "before": self._current_weights.copy(),
            "after": new_weights.copy(),
            "dimension_errors": dimension_errors,
            "sample_size": len(self._feedback_history),
        }
        self._optimization_log.append(optimization_log)

        # 更新当前权重
        self._current_weights = new_weights

        logger.info(f"权重优化完成: {self._current_weights}")

        return self._current_weights

    def get_current_weights(self) -> Dict[str, float]:
        """获取当前权重"""
        return self._current_weights.copy()

    def reset_weights(self):
        """重置为默认权重"""
        self._current_weights = DEFAULT_WEIGHTS.copy()
        logger.info("权重已重置为默认值")


# ============================================
# 反馈数据收集服务
# ============================================

class FeedbackCollector:
    """用户反馈收集服务"""

    def collect_match_feedback(
        self,
        user_id: str,
        match_user_id: str,
        feedback_type: str,
        detail: str = "",
        db: Session = None
    ) -> Dict[str, Any]:
        """
        收集用户对匹配对象可信度的反馈

        Args:
            user_id: 反馈者ID
            match_user_id: 被反馈的匹配对象ID
            feedback_type: 反馈类型
                - "accurate": 置信度判断准确
                - "inaccurate_high": 高估了可信度（实际不可信）
                - "inaccurate_low": 低估了可信度（实际可信）
                - "fake_info": 发现虚假信息
                - "scam_behavior": 发现诈骗行为
            detail: 详细描述

        Returns:
            反馈处理结果
        """
        from utils.db_session_manager import db_session
        from models.profile_confidence_models import ConfidenceEvaluationLogDB

        # 记录反馈到数据库
        with db_session() as session:
            # 获取被反馈用户的置信度记录
            from models.profile_confidence_models import ProfileConfidenceDetailDB
            confidence_detail = session.query(ProfileConfidenceDetailDB).filter(
                ProfileConfidenceDetailDB.user_id == match_user_id
            ).first()

            predicted_confidence = confidence_detail.overall_confidence if confidence_detail else 0.3

            # 根据反馈类型推断实际可信度
            actual_trustworthiness_map = {
                "accurate": predicted_confidence,  # 准确 → 实际与预测相同
                "inaccurate_high": predicted_confidence - 0.3,  # 高估 → 实际更低
                "inaccurate_low": predicted_confidence + 0.2,   # 低估 → 实际更高
                "fake_info": 0.1,  # 虚假信息 → 极低可信
                "scam_behavior": 0.05,  # 诈骗 → 极低可信
            }

            actual_trustworthiness = actual_trustworthiness_map.get(feedback_type, predicted_confidence)
            actual_trustworthiness = max(0, min(1, actual_trustworthiness))

            # 获取各维度分数
            dimensions = {}
            if confidence_detail:
                dimensions = {
                    "identity": confidence_detail.identity_confidence,
                    "cross_validation": confidence_detail.cross_validation_confidence,
                    "behavior": confidence_detail.behavior_consistency,
                    "social": confidence_detail.social_endorsement,
                    "time": confidence_detail.time_accumulation,
                }

            # 触发权重优化器记录
            optimizer = WeightOptimizer()
            optimizer.record_feedback(
                user_id=match_user_id,
                predicted_confidence=predicted_confidence,
                actual_trustworthiness=actual_trustworthiness,
                dimensions=dimensions,
            )

            # 如果发现虚假信息，立即更新置信度
            if feedback_type in ["fake_info", "scam_behavior"]:
                if confidence_detail:
                    confidence_detail.overall_confidence = 0.1
                    confidence_detail.confidence_level = "low"
                    confidence_detail.cross_validation_flags = json.dumps({
                        "user_reported_fake_info": {
                            "severity": "high",
                            "detail": detail or f"用户反馈：{feedback_type}",
                            "reported_by": user_id,
                        }
                    })
                    session.commit()

                    logger.warning(f"用户 {match_user_id} 被标记为虚假信息，置信度降至0.1")

            logger.info(f"反馈收集完成: {feedback_type} from {user_id} about {match_user_id}")

            return {
                "success": True,
                "feedback_type": feedback_type,
                "predicted": predicted_confidence,
                "actual": actual_trustworthiness,
                "recorded": True,
            }


# ============================================
# A/B测试框架
# ============================================

class ConfidenceABTesting:
    """置信度算法A/B测试框架"""

    _experiments: Dict[str, Dict] = {}

    def create_experiment(
        self,
        experiment_id: str,
        name: str,
        control_weights: Dict[str, float],
        treatment_weights: Dict[str, float],
        traffic_split: float = 0.5,  # 50%流量分配到实验组
        duration_days: int = 7
    ):
        """
        创建A/B测试实验

        Args:
            experiment_id: 实验ID
            name: 实验名称
            control_weights: 对照组权重
            treatment_weights: 实验组权重
            traffic_split: 实验组流量比例
            duration_days: 实验持续天数
        """
        experiment = {
            "id": experiment_id,
            "name": name,
            "control_weights": control_weights,
            "treatment_weights": treatment_weights,
            "traffic_split": traffic_split,
            "start_time": datetime.now(),
            "end_time": datetime.now() + timedelta(days=duration_days),
            "control_results": [],
            "treatment_results": [],
            "status": "running",
        }

        self._experiments[experiment_id] = experiment
        logger.info(f"A/B测试实验创建: {name} (ID: {experiment_id})")

    def assign_user_to_group(self, experiment_id: str, user_id: str) -> str:
        """
        将用户分配到实验组或对照组

        Returns:
            "control" 或 "treatment"
        """
        experiment = self._experiments.get(experiment_id)
        if not experiment or experiment["status"] != "running":
            return "control"  # 默认对照组

        # 使用用户ID哈希决定分组（确保同一用户始终在同一组）
        hash_value = hash(user_id + experiment_id) % 100
        if hash_value < experiment["traffic_split"] * 100:
            return "treatment"
        return "control"

    def get_weights_for_experiment(self, experiment_id: str, group: str) -> Dict[str, float]:
        """获取实验指定组的权重配置"""
        experiment = self._experiments.get(experiment_id)
        if not experiment:
            return DEFAULT_WEIGHTS

        if group == "treatment":
            return experiment["treatment_weights"]
        return experiment["control_weights"]

    def record_experiment_result(
        self,
        experiment_id: str,
        user_id: str,
        group: str,
        predicted_confidence: float,
        actual_trustworthiness: float,
        user_satisfaction: float = None
    ):
        """记录实验结果"""
        experiment = self._experiments.get(experiment_id)
        if not experiment:
            return

        result = {
            "user_id": user_id,
            "predicted": predicted_confidence,
            "actual": actual_trustworthiness,
            "error": abs(predicted_confidence - actual_trustworthiness),
            "satisfaction": user_satisfaction,
            "timestamp": datetime.now().isoformat(),
        }

        if group == "treatment":
            experiment["treatment_results"].append(result)
        else:
            experiment["control_results"].append(result)

    def analyze_experiment(self, experiment_id: str) -> Dict[str, Any]:
        """
        分析实验结果

        Returns:
            实验分析报告
        """
        experiment = self._experiments.get(experiment_id)
        if not experiment:
            return {"error": "实验不存在"}

        control_results = experiment["control_results"]
        treatment_results = experiment["treatment_results"]

        if len(control_results) < 30 or len(treatment_results) < 30:
            return {"note": "样本不足，需要更多数据"}

        # 计算平均误差
        control_avg_error = sum(r["error"] for r in control_results) / len(control_results)
        treatment_avg_error = sum(r["error"] for r in treatment_results) / len(treatment_results)

        # 计算满意度（如果有）
        control_satisfaction = None
        treatment_satisfaction = None
        if control_results and control_results[0].get("satisfaction"):
            control_satisfaction = sum(r["satisfaction"] for r in control_results if r["satisfaction"]) / len([r for r in control_results if r["satisfaction"]])
        if treatment_results and treatment_results[0].get("satisfaction"):
            treatment_satisfaction = sum(r["satisfaction"] for r in treatment_results if r["satisfaction"]) / len([r for r in treatment_results if r["satisfaction"]])

        # 判断实验组是否更好
        improvement = control_avg_error - treatment_avg_error
        treatment_better = improvement > 0.02  # 至少提升2%

        return {
            "experiment_id": experiment_id,
            "name": experiment["name"],
            "control_sample_size": len(control_results),
            "treatment_sample_size": len(treatment_results),
            "control_avg_error": control_avg_error,
            "treatment_avg_error": treatment_avg_error,
            "error_improvement": improvement,
            "control_satisfaction": control_satisfaction,
            "treatment_satisfaction": treatment_satisfaction,
            "treatment_better": treatment_better,
            "recommendation": "adopt_treatment" if treatment_better else "keep_control",
            "status": experiment["status"],
        }


# ============================================
# 导出
# ============================================

# 全局单例
user_group_classifier = UserGroupClassifier()
weight_optimizer = WeightOptimizer()
feedback_collector = FeedbackCollector()
ab_testing = ConfidenceABTesting()