"""
智能成团预测服务

基于回归模型 + 实时计算，预测团购能否成功成团。

特征工程:
- 进度特征：当前进度 (current/target)、剩余时间
- 时间特征：截止时刻、星期几、是否周末
- 历史特征：团长历史成团率、商品历史成团率
- 热度特征：商品浏览人数、收藏人数、每小时加入率
- 环境特征：是否节假日、小时刻

模型选择：初期使用逻辑回归 + 特征工程，后续可升级为 XGBoost/LightGBM
"""
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta
import logging
import json
import math

from models.entities import GroupBuyEntity, ProductEntity, OrderEntity
from models.p0_entities import ProductHeatmapEntity
from models.p0_entities import GroupPredictionEntity, PredictionFeatureEntity
from models.product import GroupBuyStatus

logger = logging.getLogger(__name__)


class GroupPredictionService:
    """智能成团预测服务"""

    def __init__(self, db: Session):
        self.db = db
        self.model_version = "v1.0"

    # ========== 核心预测方法 ==========

    def predict_group_success(self, group_buy_id: str) -> Dict[str, Any]:
        """
        预测团购成团概率

        Args:
            group_buy_id: 团购 ID

        Returns:
            预测结果字典，包含:
            - success_probability: 成团概率 (0-1)
            - predicted_final_size: 预测最终参团人数
            - confidence_level: 置信度等级 (low/medium/high)
            - prediction_category: 预测分类
            - features: 使用的特征数据
            - advice: 优化建议
        """
        # 获取团购信息
        group_buy = self.db.query(GroupBuyEntity).filter(GroupBuyEntity.id == group_buy_id).first()
        if not group_buy:
            return {"error": "团购不存在", "success": False}

        # 如果团购已结束，直接返回结果
        if group_buy.status != GroupBuyStatus.OPEN:
            return {
                "success": True,
                "group_buy_id": group_buy_id,
                "status": "closed",
                "final_status": group_buy.status.value,
                "final_size": group_buy.current_size,
                "message": "团购已结束，无需预测"
            }

        # 提取特征
        features = self._extract_features(group_buy)

        # 计算成团概率（使用逻辑回归模型）
        success_probability = self._calculate_success_probability(features)

        # 预测最终参团人数
        predicted_final_size = self._predict_final_size(group_buy, features, success_probability)

        # 计算置信度
        confidence_level = self._calculate_confidence_level(features, success_probability)

        # 预测分类
        prediction_category = self._classify_prediction(success_probability)

        # 保存预测记录
        prediction = self._save_prediction(group_buy, features, success_probability,
                                           predicted_final_size, confidence_level, prediction_category)

        # 生成优化建议
        advice = self._generate_advice(features, success_probability, prediction_category)

        return {
            "success": True,
            "group_buy_id": group_buy_id,
            "product_id": group_buy.product_id,
            "organizer_id": group_buy.organizer_id,
            "current_size": group_buy.current_size,
            "target_size": group_buy.target_size,
            "progress_ratio": round(group_buy.current_size / group_buy.target_size, 3) if group_buy.target_size > 0 else 0,
            "success_probability": round(success_probability, 3),
            "predicted_final_size": predicted_final_size,
            "confidence_level": confidence_level,
            "prediction_category": prediction_category,
            "model_version": self.model_version,
            "prediction_time": datetime.now().isoformat(),
            "features": features,
            "advice": advice,
            "prediction_id": prediction.id
        }

    def _extract_features(self, group_buy: GroupBuyEntity) -> Dict[str, Any]:
        """提取预测特征"""
        now = datetime.now()

        # 基础信息
        current_size = group_buy.current_size
        target_size = group_buy.target_size
        time_remaining = group_buy.deadline - now
        time_elapsed = now - group_buy.created_at

        # 进度特征
        progress_ratio = current_size / target_size if target_size > 0 else 0

        # 时间特征（小时为单位）
        time_remaining_hours = max(0, time_remaining.total_seconds() / 3600)
        time_elapsed_hours = time_elapsed.total_seconds() / 3600
        deadline_hour_of_day = group_buy.deadline.hour

        # 历史特征 - 团长历史成团率
        organizer_stats = self._get_organizer_history(group_buy.organizer_id)
        organizer_historical_success_rate = organizer_stats["success_rate"]
        organizer_total_groups = organizer_stats["total_groups"]

        # 历史特征 - 商品历史成团率
        product_stats = self._get_product_history(group_buy.product_id)
        product_historical_success_rate = product_stats["success_rate"]

        # 热度特征 - 商品浏览和收藏
        heatmap = self.db.query(ProductHeatmapEntity).filter(
            ProductHeatmapEntity.product_id == group_buy.product_id
        ).first()
        product_view_count = heatmap.total_views_week if heatmap else 0
        product_wishlist_count = heatmap.wishlist_count if heatmap else 0

        # 热度特征 - 每小时加入率
        hourly_join_rate = current_size / max(1, time_elapsed_hours) if time_elapsed_hours > 0 else current_size

        # 环境特征
        day_of_week = now.weekday()  # 0=周一，6=周日
        hour_of_day = now.hour
        is_weekend = day_of_week >= 5
        is_holiday_season = self._is_holiday_season(now)

        features = {
            # 进度特征
            "progress_ratio": round(progress_ratio, 4),
            "current_size": current_size,
            "target_size": target_size,

            # 时间特征
            "time_remaining_hours": round(time_remaining_hours, 2),
            "time_elapsed_hours": round(time_elapsed_hours, 2),
            "deadline_hour_of_day": deadline_hour_of_day,

            # 历史特征
            "organizer_historical_success_rate": round(organizer_historical_success_rate, 4),
            "product_historical_success_rate": round(product_historical_success_rate, 4),
            "organizer_total_groups": organizer_total_groups,

            # 热度特征
            "product_view_count": product_view_count,
            "product_wishlist_count": product_wishlist_count,
            "hourly_join_rate": round(hourly_join_rate, 2),

            # 环境特征
            "day_of_week": day_of_week,
            "hour_of_day": hour_of_day,
            "is_weekend": is_weekend,
            "is_holiday_season": is_holiday_season
        }

        return features

    def _calculate_success_probability(self, features: Dict[str, Any]) -> float:
        """
        计算成团概率 - 使用逻辑回归模型

        特征权重基于以下假设:
        1. 进度是最重要的预测因子
        2. 时间压力对成团概率有显著影响
        3. 历史成功率有一定预测能力
        4. 热度指标反映潜在需求
        """
        # 逻辑回归系数（通过历史数据训练得到，这里是初始值）
        coefficients = {
            "intercept": -1.5,
            "progress_ratio": 3.5,
            "time_remaining_hours": 0.02,
            "organizer_historical_success_rate": 1.0,
            "product_historical_success_rate": 0.8,
            "hourly_join_rate": 0.15,
            "product_view_count": 0.001,
            "is_weekend": 0.3,
            "organizer_total_groups": 0.01
        }

        # 计算线性组合
        linear_combination = coefficients["intercept"]
        linear_combination += coefficients["progress_ratio"] * features["progress_ratio"]
        linear_combination += coefficients["time_remaining_hours"] * features["time_remaining_hours"]
        linear_combination += coefficients["organizer_historical_success_rate"] * features["organizer_historical_success_rate"]
        linear_combination += coefficients["product_historical_success_rate"] * features["product_historical_success_rate"]
        linear_combination += coefficients["hourly_join_rate"] * features["hourly_join_rate"]
        linear_combination += coefficients["product_view_count"] * features["product_view_count"]
        linear_combination += coefficients["is_weekend"] * (1 if features["is_weekend"] else 0)
        linear_combination += coefficients["organizer_total_groups"] * min(features["organizer_total_groups"], 50)

        # Sigmoid 函数转换为概率
        probability = 1 / (1 + math.exp(-linear_combination))

        # 边界处理
        # 如果已经达到目标人数，概率为 1
        if features["progress_ratio"] >= 1.0:
            probability = 1.0

        # 如果时间为负（已过期），概率为 0
        if features["time_remaining_hours"] <= 0:
            probability = 0.0

        return max(0.0, min(1.0, probability))

    def _predict_final_size(self, group_buy: GroupBuyEntity, features: Dict[str, Any],
                            success_probability: float) -> int:
        """预测最终参团人数"""
        current_size = group_buy.current_size
        target_size = group_buy.target_size
        time_remaining_hours = features["time_remaining_hours"]
        hourly_join_rate = features["hourly_join_rate"]

        # 如果已经成团或过期
        if current_size >= target_size or time_remaining_hours <= 0:
            return current_size

        # 方法 1: 基于当前加入率的线性外推
        projected_additional = hourly_join_rate * time_remaining_hours

        # 方法 2: 基于成功概率的期望值
        # 如果成功概率高，趋向于目标人数；如果低，趋向于当前人数
        probability_adjusted = current_size + (target_size - current_size) * success_probability

        # 综合两种方法，给予不同权重
        predicted_size = current_size + projected_additional * 0.6 + (probability_adjusted - current_size) * 0.4

        # 不超过目标人数
        predicted_size = min(predicted_size, target_size)

        return int(round(predicted_size))

    def _calculate_confidence_level(self, features: Dict[str, Any],
                                    success_probability: float) -> str:
        """
        计算置信度等级

        置信度取决于:
        1. 预测概率是否接近边界（0 或 1）
        2. 历史数据是否充足
        3. 特征是否完整
        """
        confidence_score = 0.0

        # 因子 1: 概率离边界的距离（越接近 0 或 1 越确信）
        distance_from_boundary = min(success_probability, 1 - success_probability)
        if distance_from_boundary < 0.1:
            confidence_score += 0.4
        elif distance_from_boundary < 0.2:
            confidence_score += 0.3
        elif distance_from_boundary < 0.3:
            confidence_score += 0.2
        else:
            confidence_score += 0.1

        # 因子 2: 历史数据充足度
        if features["organizer_total_groups"] >= 10:
            confidence_score += 0.3
        elif features["organizer_total_groups"] >= 5:
            confidence_score += 0.2
        else:
            confidence_score += 0.1

        # 因子 3: 时间充足度（时间越充足，预测越不确定）
        if features["time_remaining_hours"] < 6:
            confidence_score += 0.3  # 短期内预测更准确
        elif features["time_remaining_hours"] < 24:
            confidence_score += 0.2
        else:
            confidence_score += 0.1

        # 确定等级
        if confidence_score >= 0.8:
            return "high"
        elif confidence_score >= 0.5:
            return "medium"
        else:
            return "low"

    def _classify_prediction(self, success_probability: float) -> str:
        """根据概率分类预测结果"""
        if success_probability >= 0.8:
            return "highly_likely"  # 极有可能成团
        elif success_probability >= 0.6:
            return "likely"  # 很可能成团
        elif success_probability >= 0.4:
            return "uncertain"  # 不确定
        else:
            return "unlikely"  # 不太可能成团

    def _save_prediction(self, group_buy: GroupBuyEntity, features: Dict[str, Any],
                         success_probability: float, predicted_final_size: int,
                         confidence_level: str, prediction_category: str) -> GroupPredictionEntity:
        """保存预测记录到数据库"""
        # 检查是否已有预测记录，有则更新
        existing = self.db.query(GroupPredictionEntity).filter(
            GroupPredictionEntity.group_buy_id == group_buy.id
        ).first()

        if existing:
            # 更新现有记录
            existing.success_probability = success_probability
            existing.predicted_final_size = predicted_final_size
            existing.confidence_level = confidence_level
            existing.prediction_category = prediction_category
            existing.features = json.dumps(features)
            existing.prediction_time = datetime.now()
            existing.updated_at = datetime.now()
            prediction = existing
        else:
            # 创建新记录
            prediction = GroupPredictionEntity(
                group_buy_id=group_buy.id,
                product_id=group_buy.product_id,
                organizer_id=group_buy.organizer_id,
                success_probability=success_probability,
                predicted_final_size=predicted_final_size,
                confidence_level=confidence_level,
                prediction_category=prediction_category,
                features=json.dumps(features),
                model_version=self.model_version,
                prediction_time=datetime.now()
            )
            self.db.add(prediction)

        self.db.commit()
        self.db.refresh(prediction)

        # 同时保存特征数据用于模型训练
        self._save_feature_history(group_buy, features)

        return prediction

    def _save_feature_history(self, group_buy: GroupBuyEntity, features: Dict[str, Any]) -> None:
        """保存特征历史用于模型训练"""
        feature_record = PredictionFeatureEntity(
            group_buy_id=group_buy.id,
            product_id=group_buy.product_id,
            organizer_id=group_buy.organizer_id,
            progress_ratio=features["progress_ratio"],
            current_size=features["current_size"],
            target_size=features["target_size"],
            time_remaining_hours=features["time_remaining_hours"],
            time_elapsed_hours=features["time_elapsed_hours"],
            deadline_hour_of_day=features["deadline_hour_of_day"],
            organizer_historical_success_rate=features["organizer_historical_success_rate"],
            product_historical_success_rate=features["product_historical_success_rate"],
            organizer_total_groups=features["organizer_total_groups"],
            product_view_count=features["product_view_count"],
            product_wishlist_count=features["product_wishlist_count"],
            hourly_join_rate=features["hourly_join_rate"],
            day_of_week=features["day_of_week"],
            hour_of_day=features["hour_of_day"],
            is_weekend=features["is_weekend"],
            is_holiday_season=features["is_holiday_season"]
        )
        self.db.add(feature_record)
        self.db.commit()

    def _generate_advice(self, features: Dict[str, Any], success_probability: float,
                         prediction_category: str) -> Dict[str, Any]:
        """生成优化建议"""
        advice = {
            "overall_assessment": "",
            "key_factors": [],
            "suggested_actions": []
        }

        # 整体评估
        if prediction_category == "highly_likely":
            advice["overall_assessment"] = "成团概率很高，保持当前策略即可"
        elif prediction_category == "likely":
            advice["overall_assessment"] = "成团概率较高，可适度推广加速成团"
        elif prediction_category == "uncertain":
            advice["overall_assessment"] = "成团前景不明，建议采取措施提高概率"
        else:
            advice["overall_assessment"] = "成团概率较低，需要积极干预"

        # 关键因素分析
        if features["progress_ratio"] >= 0.8:
            advice["key_factors"].append("进度良好：已达到目标人数的 80% 以上")
        elif features["progress_ratio"] < 0.3:
            advice["key_factors"].append("进度缓慢：当前进度不足 30%")

        if features["time_remaining_hours"] < 6:
            advice["key_factors"].append("时间紧张：剩余时间不足 6 小时")
        elif features["time_remaining_hours"] > 48:
            advice["key_factors"].append("时间充裕：还有充足时间等待自然增长")

        if features["hourly_join_rate"] > 2:
            advice["key_factors"].append("增长迅速：每小时超过 2 人加入")
        elif features["hourly_join_rate"] < 0.5:
            advice["key_factors"].append("增长缓慢：每小时加入人数不足 0.5 人")

        if features["organizer_historical_success_rate"] > 0.8:
            advice["key_factors"].append("团长信誉高：历史成团率超过 80%")
        elif features["organizer_historical_success_rate"] < 0.5:
            advice["key_factors"].append("团长信誉一般：历史成团率低于 50%")

        # 建议行动
        if prediction_category in ["unlikely", "uncertain"]:
            if features["time_remaining_hours"] > 12:
                advice["suggested_actions"].append("延长团购截止时间，增加自然增长时间")
            advice["suggested_actions"].append("分享到社区群聊或朋友圈增加曝光")
            advice["suggested_actions"].append("考虑设置限时优惠刺激参团")

            if features["product_view_count"] > 100 and features["progress_ratio"] < 0.5:
                advice["suggested_actions"].append("浏览人数多但转化低，考虑优化商品描述或价格")

        if prediction_category == "likely":
            advice["suggested_actions"].append("推送提醒给已浏览未下单的用户")
            advice["suggested_actions"].append("设置'差 X 人成团'的紧迫感提示")

        if prediction_category == "highly_likely":
            advice["suggested_actions"].append("准备成团后的履约安排")
            advice["suggested_actions"].append("邀请用户分享成功经验")

        return advice

    # ========== 历史统计方法 ==========

    def _get_organizer_history(self, organizer_id: str) -> Dict[str, Any]:
        """获取团长历史成团统计"""
        total_groups = self.db.query(func.count(GroupBuyEntity.id)).filter(
            GroupBuyEntity.organizer_id == organizer_id
        ).scalar() or 0

        success_groups = self.db.query(func.count(GroupBuyEntity.id)).filter(
            GroupBuyEntity.organizer_id == organizer_id,
            GroupBuyEntity.status == GroupBuyStatus.SUCCESS
        ).scalar() or 0

        success_rate = success_groups / total_groups if total_groups > 0 else 0.5  # 默认 50%

        return {
            "total_groups": total_groups,
            "success_groups": success_groups,
            "success_rate": success_rate
        }

    def _get_product_history(self, product_id: str) -> Dict[str, Any]:
        """获取商品历史成团统计"""
        total_groups = self.db.query(func.count(GroupBuyEntity.id)).filter(
            GroupBuyEntity.product_id == product_id
        ).scalar() or 0

        success_groups = self.db.query(func.count(GroupBuyEntity.id)).filter(
            GroupBuyEntity.product_id == product_id,
            GroupBuyEntity.status == GroupBuyStatus.SUCCESS
        ).scalar() or 0

        success_rate = success_groups / total_groups if total_groups > 0 else 0.7  # 默认 70%

        return {
            "total_groups": total_groups,
            "success_groups": success_groups,
            "success_rate": success_rate
        }

    def _is_holiday_season(self, date: datetime) -> bool:
        """判断是否节假日季节（简化实现）"""
        # 主要节假日：元旦、春节、清明、劳动节、端午、中秋、国庆
        month = date.month
        day = date.day

        # 简化判断：1 月 1 日、5 月 1 日、10 月 1 日前后一周
        holiday_dates = [
            (1, 1), (5, 1), (10, 1)
        ]

        for h_month, h_day in holiday_dates:
            if month == h_month and abs(day - h_day) <= 7:
                return True

        return False

    # ========== 批量预测和统计 ==========

    def predict_active_groups(self, organizer_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """批量预测活跃团购的成团概率"""
        query = self.db.query(GroupBuyEntity).filter(
            GroupBuyEntity.status == GroupBuyStatus.OPEN
        )

        if organizer_id:
            query = query.filter(GroupBuyEntity.organizer_id == organizer_id)

        groups = query.all()
        predictions = []

        for group in groups:
            prediction = self.predict_group_success(group.id)
            predictions.append(prediction)

        return predictions

    def get_prediction_history(self, group_buy_id: str) -> List[Dict[str, Any]]:
        """获取团购的预测历史记录"""
        predictions = self.db.query(GroupPredictionEntity).filter(
            GroupPredictionEntity.group_buy_id == group_buy_id
        ).order_by(GroupPredictionEntity.created_at.desc()).all()

        return [
            {
                "id": p.id,
                "success_probability": p.success_probability,
                "predicted_final_size": p.predicted_final_size,
                "confidence_level": p.confidence_level,
                "prediction_category": p.prediction_category,
                "model_version": p.model_version,
                "prediction_time": p.prediction_time.isoformat(),
                "actual_result": p.actual_result,
                "accuracy": p.accuracy
            }
            for p in predictions
        ]

    def update_prediction_result(self, group_buy_id: str, actual_result: str,
                                 actual_final_size: int) -> bool:
        """更新预测的实际结果（用于模型优化）"""
        prediction = self.db.query(GroupPredictionEntity).filter(
            GroupPredictionEntity.group_buy_id == group_buy_id
        ).first()

        if not prediction:
            return False

        prediction.actual_result = actual_result
        prediction.actual_final_size = actual_final_size

        # 计算准确率
        if prediction.predicted_final_size > 0:
            accuracy = 1 - abs(prediction.predicted_final_size - actual_final_size) / max(prediction.predicted_final_size, actual_final_size)
            prediction.accuracy = round(accuracy, 4)

        self.db.commit()

        # 同时更新特征历史
        feature_record = self.db.query(PredictionFeatureEntity).filter(
            PredictionFeatureEntity.group_buy_id == group_buy_id
        ).first()

        if feature_record:
            feature_record.actual_success = (actual_result == "success")
            feature_record.actual_final_size = actual_final_size
            self.db.commit()

        logger.info(f"更新预测结果：团购 {group_buy_id}, 实际结果={actual_result}, 实际人数={actual_final_size}")
        return True

    def get_model_accuracy_stats(self, days: int = 30) -> Dict[str, Any]:
        """获取模型准确率统计"""
        cutoff_date = datetime.now() - timedelta(days=days)

        predictions = self.db.query(GroupPredictionEntity).filter(
            GroupPredictionEntity.prediction_time >= cutoff_date,
            GroupPredictionEntity.actual_result.isnot(None)
        ).all()

        if not predictions:
            return {
                "total_predictions": 0,
                "avg_accuracy": None,
                "high_confidence_accuracy": None,
                "medium_confidence_accuracy": None,
                "low_confidence_accuracy": None
            }

        total = len(predictions)
        avg_accuracy = sum(p.accuracy for p in predictions if p.accuracy is not None) / total

        # 按置信度分组统计
        confidence_stats = {}
        for level in ["high", "medium", "low"]:
            level_preds = [p for p in predictions if p.confidence_level == level and p.accuracy is not None]
            if level_preds:
                confidence_stats[level] = sum(p.accuracy for p in level_preds) / len(level_preds)
            else:
                confidence_stats[level] = None

        return {
            "total_predictions": total,
            "avg_accuracy": round(avg_accuracy, 4) if avg_accuracy else None,
            "high_confidence_accuracy": round(confidence_stats["high"], 4) if confidence_stats["high"] else None,
            "medium_confidence_accuracy": round(confidence_stats["medium"], 4) if confidence_stats["medium"] else None,
            "low_confidence_accuracy": round(confidence_stats["low"], 4) if confidence_stats["low"] else None
        }


# 全局服务实例（用于非依赖注入场景）
_prediction_service_instance = None


def get_prediction_service(db: Session) -> GroupPredictionService:
    """获取预测服务实例"""
    return GroupPredictionService(db)
