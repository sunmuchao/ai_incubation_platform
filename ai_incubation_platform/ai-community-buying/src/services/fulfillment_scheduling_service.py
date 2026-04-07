"""
智能履约调度服务
核心功能：
1. 配送路径优化算法 (VRP)
2. 自提点人流预测
3. 履约时间窗口推荐
4. 异常处理
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, or_
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, timedelta
from math import radians, sin, cos, sqrt, atan2
import json
import logging
from collections import defaultdict

from models.fulfillment_scheduling_entities import (
    PickupPointEntity, DeliveryRouteEntity, DeliveryTaskEntity,
    TrafficFlowPredictionEntity, TimeWindowRecommendationEntity,
    DeliveryExceptionEntity
)
from models.entities import FulfillmentEntity, OrderEntity, GroupBuyEntity
from core.logging_config import get_logger

logger = get_logger("services.fulfillment_scheduling")


class HaversineDistance:
    """使用 Haversine 公式计算地球表面两点间距离"""

    EARTH_RADIUS_KM = 6371  # 地球半径（公里）

    @staticmethod
    def calculate(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        计算两点间距离（公里）

        Args:
            lat1, lon1: 点 1 的纬度和经度
            lat2, lon2: 点 2 的纬度和经度

        Returns:
            距离（公里）
        """
        lat1_rad = radians(lat1)
        lat2_rad = radians(lat2)
        delta_lat = radians(lat2 - lat1)
        delta_lon = radians(lon2 - lon1)

        a = sin(delta_lat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        return HaversineDistance.EARTH_RADIUS_KM * c


class PathOptimizationAlgorithm:
    """
    路径优化算法 (VRP - Vehicle Routing Problem)

    使用改进的最近邻算法 + 2-opt 优化
    """

    def __init__(self, db: Session):
        self.db = db
        self.logger = logger

    def optimize_route(self, warehouse_location: Tuple[float, float],
                       pickup_point_ids: List[str],
                       constraints: Optional[Dict] = None) -> Dict:
        """
        优化配送路线

        Args:
            warehouse_location: 仓库位置 (纬度，经度)
            pickup_point_ids: 需要配送的自提点 ID 列表
            constraints: 约束条件 {"max_distance": float, "time_windows": dict, "priority_points": list}

        Returns:
            优化后的路线信息
        """
        # 获取自提点详情
        pickup_points = self.db.query(PickupPointEntity).filter(
            PickupPointEntity.id.in_(pickup_point_ids)
        ).all()

        if not pickup_points:
            return {"success": False, "message": "未找到自提点"}

        # 构建距离矩阵
        points = [{"id": "warehouse", "lat": warehouse_location[0], "lon": warehouse_location[1]}]
        points.extend([
            {"id": p.id, "lat": p.latitude, "lon": p.longitude, "entity": p}
            for p in pickup_points
        ])

        n = len(points)
        distance_matrix = [[0.0] * n for _ in range(n)]

        for i in range(n):
            for j in range(i + 1, n):
                dist = HaversineDistance.calculate(
                    points[i]["lat"], points[i]["lon"],
                    points[j]["lat"], points[j]["lon"]
                )
                distance_matrix[i][j] = dist
                distance_matrix[j][i] = dist

        # 使用最近邻算法生成初始路线
        route = self._nearest_neighbor_route(distance_matrix, n, constraints)

        # 使用 2-opt 算法优化路线
        optimized_route = self._two_opt_optimize(route, distance_matrix)

        # 计算总距离和预计时长
        total_distance = sum(
            distance_matrix[optimized_route[i]][optimized_route[i + 1]]
            for i in range(len(optimized_route) - 1)
        )

        # 估计时长（假设平均速度 30km/h + 每站 15 分钟）
        estimated_duration = int((total_distance / 30) * 60 + len(optimized_route) * 15)

        # 构建优化结果
        optimized_stops = []
        for i, idx in enumerate(optimized_route[1:], 1):  # 跳过仓库
            point = points[idx]
            optimized_stops.append({
                "pickup_point_id": point["id"],
                "sequence": i,
                "distance_from_prev": round(distance_matrix[optimized_route[i-1]][idx], 2),
                "eta_offset_minutes": int((total_distance / len(optimized_route)) * i / 30 * 60 + i * 15)
            })

        return {
            "success": True,
            "optimized_stops": optimized_stops,
            "total_distance_km": round(total_distance, 2),
            "estimated_duration_minutes": estimated_duration,
            "stop_count": len(optimized_stops),
            "optimization_score": self._calculate_optimization_score(
                distance_matrix, optimized_route, n
            )
        }

    def _nearest_neighbor_route(self, distance_matrix: List[List[float]], n: int,
                                 constraints: Optional[Dict]) -> List[int]:
        """
        最近邻算法生成初始路线

        Args:
            distance_matrix: 距离矩阵
            n: 点的数量
            constraints: 约束条件

        Returns:
            路线（点的索引列表）
        """
        visited = [False] * n
        route = [0]  # 从仓库出发
        visited[0] = True

        priority_points = constraints.get("priority_points", []) if constraints else []

        current = 0
        while len(route) < n:
            nearest = -1
            nearest_dist = float('inf')

            for i in range(1, n):
                if not visited[i]:
                    # 优先处理高优先级自提点
                    if points := self.db.query(PickupPointEntity).filter(PickupPointEntity.id == str(i)).first():
                        pass

                    dist = distance_matrix[current][i]
                    if dist < nearest_dist:
                        nearest = i
                        nearest_dist = dist

            if nearest != -1:
                visited[nearest] = True
                route.append(nearest)
                current = nearest

        route.append(0)  # 返回仓库
        return route

    def _two_opt_optimize(self, route: List[int], distance_matrix: List[List[float]]) -> List[int]:
        """
        2-opt 算法优化路线

        Args:
            route: 初始路线
            distance_matrix: 距离矩阵

        Returns:
            优化后的路线
        """
        n = len(route)
        improved = True

        while improved:
            improved = False
            for i in range(1, n - 2):
                for j in range(i + 1, n - 1):
                    # 计算当前路径距离
                    old_dist = (
                        distance_matrix[route[i - 1]][route[i]] +
                        distance_matrix[route[j]][route[(j + 1) % n]]
                    )
                    # 计算交换后路径距离
                    new_dist = (
                        distance_matrix[route[i - 1]][route[j]] +
                        distance_matrix[route[i]][route[(j + 1) % n]]
                    )

                    if new_dist < old_dist:
                        # 反转 i 到 j 之间的路径
                        route[i:j + 1] = reversed(route[i:j + 1])
                        improved = True
                        break

                if improved:
                    break

        return route

    def _calculate_optimization_score(self, distance_matrix: List[List[float]],
                                       optimized_route: List[int], n: int) -> float:
        """
        计算优化分数（0-1）

        通过对比优化前后路径长度计算改进比例
        """
        # 计算优化后的总距离
        optimized_dist = sum(
            distance_matrix[optimized_route[i]][optimized_route[i + 1]]
            for i in range(len(optimized_route) - 1)
        )

        # 计算原始顺序的距离
        original_route = list(range(n))
        original_route.append(0)
        original_dist = sum(
            distance_matrix[original_route[i]][original_route[i + 1]]
            for i in range(len(original_route) - 1)
        )

        if original_dist == 0:
            return 1.0

        # 优化分数 = 改进比例
        improvement = (original_dist - optimized_dist) / original_dist
        return min(1.0, max(0.0, 0.5 + improvement))  # 基础分 0.5 + 改进比例


class TrafficFlowPredictor:
    """
    自提点人流预测模型

    使用时序分析 + 特征工程进行人流预测
    """

    def __init__(self, db: Session):
        self.db = db
        self.logger = logger

    def predict_hourly_flow(self, pickup_point_id: str,
                            prediction_date: datetime) -> List[Dict]:
        """
        预测自提点每小时人流量

        Args:
            pickup_point_id: 自提点 ID
            prediction_date: 预测日期

        Returns:
            24 小时的人流预测列表
        """
        # 获取自提点信息
        pickup_point = self.db.query(PickupPointEntity).filter(
            PickupPointEntity.id == pickup_point_id
        ).first()

        if not pickup_point:
            return []

        # 获取历史人流数据
        historical_data = self._get_historical_flow(pickup_point_id, prediction_date)

        # 基于历史和特征进行预测
        predictions = []
        for hour in range(24):
            predicted_flow, confidence, crowd_level = self._predict_single_hour(
                pickup_point, hour, prediction_date, historical_data
            )

            prediction = TrafficFlowPredictionEntity(
                pickup_point_id=pickup_point_id,
                prediction_date=prediction_date,
                hour=hour,
                predicted_flow=predicted_flow,
                confidence=confidence,
                crowd_level=crowd_level,
                features=json.dumps({
                    "day_of_week": prediction_date.weekday(),
                    "is_weekend": prediction_date.weekday() >= 5,
                    "hour": hour
                }),
                model_version="v1"
            )

            self.db.add(prediction)

            predictions.append({
                "hour": hour,
                "predicted_flow": predicted_flow,
                "confidence": confidence,
                "crowd_level": crowd_level
            })

        self.db.commit()

        return predictions

    def _get_historical_flow(self, pickup_point_id: str,
                             prediction_date: datetime) -> Dict[int, List[int]]:
        """
        获取历史人流数据

        返回按小时分组的历史人流数据
        """
        # 查询过去 7 天的预测数据（用作历史参考）
        week_ago = prediction_date - timedelta(days=7)

        historical = self.db.query(TrafficFlowPredictionEntity).filter(
            TrafficFlowPredictionEntity.pickup_point_id == pickup_point_id,
            TrafficFlowPredictionEntity.prediction_date >= week_ago,
            TrafficFlowPredictionEntity.actual_flow.isnot(None)
        ).all()

        # 按小时分组
        hourly_data = defaultdict(list)
        for record in historical:
            hourly_data[record.hour].append(record.actual_flow)

        return hourly_data

    def _predict_single_hour(self, pickup_point: PickupPointEntity, hour: int,
                              prediction_date: datetime,
                              historical_data: Dict[int, List[int]]) -> Tuple[int, float, str]:
        """
        预测单个时段的人流量

        基于以下因素：
        1. 历史同时段人流
        2. 时段特征（工作时间/休息时间）
        3. 日期特征（工作日/周末）

        Returns:
            (预测人流量，置信度，拥挤等级)
        """
        # 获取历史同时段的平均人流
        if hour in historical_data and historical_data[hour]:
            base_flow = sum(historical_data[hour]) / len(historical_data[hour])
            confidence = min(0.9, 0.5 + len(historical_data[hour]) * 0.05)
        else:
            # 无历史数据时使用默认值
            base_flow = pickup_point.capacity * 0.1  # 假设默认人流为容量的 10%
            confidence = 0.3

        # 应用时段系数
        hour_factor = self._get_hour_factor(hour, prediction_date)
        predicted_flow = int(base_flow * hour_factor)

        # 确定拥挤等级
        crowd_level = self._determine_crowd_level(predicted_flow, pickup_point.capacity)

        return predicted_flow, round(confidence, 2), crowd_level

    def _get_hour_factor(self, hour: int, date: datetime) -> float:
        """
        获取时段系数

        典型的人流分布模式：
        - 早高峰：8-10 点
        - 午高峰：12-14 点
        - 晚高峰：18-20 点
        """
        is_weekend = date.weekday() >= 5

        if is_weekend:
            # 周末模式：晚高峰更明显
            hour_factors = {
                range(0, 7): 0.3,
                range(7, 9): 0.5,
                range(9, 12): 0.7,
                range(12, 14): 0.9,
                range(14, 17): 0.8,
                range(17, 21): 1.2,
                range(21, 24): 0.5
            }
        else:
            # 工作日模式：早晚高峰明显
            hour_factors = {
                range(0, 7): 0.2,
                range(7, 10): 1.2,  # 早高峰
                range(10, 12): 0.7,
                range(12, 14): 1.0,  # 午高峰
                range(14, 17): 0.6,
                range(17, 20): 1.3,  # 晚高峰
                range(20, 24): 0.4
            }

        for hour_range, factor in hour_factors.items():
            if hour in hour_range:
                return factor

        return 1.0

    def _determine_crowd_level(self, predicted_flow: int, capacity: int) -> str:
        """根据预测人流确定拥挤等级"""
        if capacity <= 0:
            return "normal"

        utilization = predicted_flow / capacity

        if utilization < 0.3:
            return "low"
        elif utilization < 0.6:
            return "normal"
        elif utilization < 0.8:
            return "high"
        else:
            return "crowded"

    def get_optimal_pickup_times(self, pickup_point_id: str,
                                  prediction_date: datetime,
                                  top_n: int = 3) -> List[Dict]:
        """
        获取最佳取货时段

        Args:
            pickup_point_id: 自提点 ID
            prediction_date: 日期
            top_n: 返回的最佳时段数量

        Returns:
            推荐时段列表
        """
        predictions = self.predict_hourly_flow(pickup_point_id, prediction_date)

        # 筛选低人流时段
        low_crowd_times = [
            p for p in predictions
            if p["crowd_level"] in ["low", "normal"]
        ]

        # 按人流排序
        low_crowd_times.sort(key=lambda x: x["predicted_flow"])

        # 返回最佳时段
        optimal_times = []
        for pred in low_crowd_times[:top_n]:
            optimal_times.append({
                "hour": pred["hour"],
                "time_range": f"{pred['hour']:02d}:00 - {(pred['hour'] + 1) % 24:02d}:00",
                "predicted_flow": pred["predicted_flow"],
                "crowd_level": pred["crowd_level"],
                "confidence": pred["confidence"]
            })

        return optimal_times


class TimeWindowRecommender:
    """
    履约时间窗口推荐器

    基于人流预测、路线优化、自提点状态等因素推荐最佳配送时间窗口
    """

    def __init__(self, db: Session):
        self.db = db
        self.logger = logger
        self.traffic_predictor = TrafficFlowPredictor(db)

    def recommend_windows(self, fulfillment_id: str, pickup_point_id: str,
                          preferred_date: Optional[datetime] = None,
                          window_duration: int = 60) -> Dict:
        """
        推荐履约时间窗口

        Args:
            fulfillment_id: 履约记录 ID
            pickup_point_id: 自提点 ID
            preferred_date: 偏好日期
            window_duration: 窗口时长（分钟）

        Returns:
            推荐结果
        """
        if preferred_date is None:
            preferred_date = datetime.now() + timedelta(days=1)

        # 获取自提点信息
        pickup_point = self.db.query(PickupPointEntity).filter(
            PickupPointEntity.id == pickup_point_id
        ).first()

        if not pickup_point:
            return {"success": False, "message": "自提点不存在"}

        # 获取人流预测
        predictions = self.traffic_predictor.predict_hourly_flow(
            pickup_point_id, preferred_date
        )

        # 筛选可用的时间窗口
        available_windows = []
        for pred in predictions:
            if pred["crowd_level"] in ["low", "normal"]:
                start_hour = pred["hour"]
                start_time = preferred_date.replace(
                    hour=start_hour, minute=0, second=0, microsecond=0
                )
                end_time = start_time + timedelta(minutes=window_duration)

                # 检查是否在营业时间内
                if self._is_within_opening_hours(pickup_point, start_time):
                    available_windows.append({
                        "start": start_time.isoformat(),
                        "end": end_time.isoformat(),
                        "crowd_level": pred["crowd_level"],
                        "confidence": pred["confidence"]
                    })

        if not available_windows:
            return {
                "success": False,
                "message": "当日无可用时间窗口"
            }

        # 按拥挤程度和置信度排序
        available_windows.sort(
            key=lambda x: (
                {"low": 0, "normal": 1, "high": 2, "crowded": 3}[x["crowd_level"]],
                -x["confidence"]
            )
        )

        # 保存推荐记录
        recommendation = TimeWindowRecommendationEntity(
            fulfillment_id=fulfillment_id,
            pickup_point_id=pickup_point_id,
            recommended_windows=available_windows[:5],
            best_window_index=0,
            recommendation_reason=f"推荐人流{available_windows[0]['crowd_level']}时段，置信度{available_windows[0]['confidence']:.0%}",
            confidence=available_windows[0]["confidence"]
        )

        self.db.add(recommendation)
        self.db.commit()

        return {
            "success": True,
            "recommended_windows": available_windows[:5],
            "best_window": available_windows[0],
            "recommendation_reason": recommendation.recommendation_reason
        }

    def _is_within_opening_hours(self, pickup_point: PickupPointEntity,
                                  check_time: datetime) -> bool:
        """检查时间是否在营业时间内"""
        if not pickup_point.opening_hours:
            return True  # 无营业时间限制，默认全天开放

        day_name = check_time.strftime("%A").lower()
        if day_name not in pickup_point.opening_hours:
            return False

        hours = pickup_point.opening_hours[day_name]
        if not hours or hours.get("open") is None:
            return False  # 该日不营业

        check_minutes = check_time.hour * 60 + check_time.minute
        open_minutes = self._time_to_minutes(hours.get("open", "00:00"))
        close_minutes = self._time_to_minutes(hours.get("close", "23:59"))

        return open_minutes <= check_minutes <= close_minutes

    def _time_to_minutes(self, time_str: str) -> int:
        """将时间字符串转换为分钟数"""
        parts = time_str.split(":")
        return int(parts[0]) * 60 + int(parts[1])


class ExceptionHandler:
    """
    配送异常处理器

    负责异常检测、上报、处理和记录
    """

    def __init__(self, db: Session):
        self.db = db
        self.logger = logger

    def report_exception(self, data: Dict) -> Tuple[Optional[DeliveryExceptionEntity], bool]:
        """
        上报配送异常

        Args:
            data: 异常数据

        Returns:
            (异常实体，是否成功)
        """
        try:
            exception = DeliveryExceptionEntity(
                route_id=data.get("route_id"),
                task_id=data.get("task_id"),
                fulfillment_id=data["fulfillment_id"],
                exception_type=data["exception_type"],
                severity=data.get("severity", "low"),
                description=data["description"],
                detected_at=datetime.now(),
                impact_assessment=json.dumps(data.get("impact_assessment", {}))
            )

            self.db.add(exception)

            # 更新关联任务状态
            if data.get("task_id"):
                task = self.db.query(DeliveryTaskEntity).filter(
                    DeliveryTaskEntity.id == data["task_id"]
                ).first()
                if task:
                    task.status = "exception"
                    task.updated_at = datetime.now()

            # 更新关联路线状态
            if data.get("route_id"):
                route = self.db.query(DeliveryRouteEntity).filter(
                    DeliveryRouteEntity.id == data["route_id"]
                ).first()
                if route:
                    route.status = "exception"
                    route.updated_at = datetime.now()

            self.db.commit()
            self.db.refresh(exception)

            self.logger.info("配送异常上报成功", extra={
                "exception_id": exception.id,
                "exception_type": exception.exception_type,
                "severity": exception.severity
            })

            return exception, True

        except Exception as e:
            self.db.rollback()
            self.logger.error(f"上报配送异常失败：{str(e)}")
            return None, False

    def resolve_exception(self, exception_id: str, resolution: str) -> Tuple[Optional[DeliveryExceptionEntity], bool]:
        """
        解决配送异常

        Args:
            exception_id: 异常 ID
            resolution: 解决方案

        Returns:
            (异常实体，是否成功)
        """
        try:
            exception = self.db.query(DeliveryExceptionEntity).filter(
                DeliveryExceptionEntity.id == exception_id
            ).first()

            if not exception:
                return None, False

            exception.resolved_at = datetime.now()
            exception.resolution = resolution
            exception.updated_at = datetime.now()

            # 恢复关联任务状态
            if exception.task_id:
                task = self.db.query(DeliveryTaskEntity).filter(
                    DeliveryTaskEntity.id == exception.task_id
                ).first()
                if task:
                    task.status = "pending"
                    task.updated_at = datetime.now()

            self.db.commit()
            self.db.refresh(exception)

            self.logger.info("配送异常解决成功", extra={
                "exception_id": exception_id,
                "resolution": resolution
            })

            return exception, True

        except Exception as e:
            self.db.rollback()
            self.logger.error(f"解决配送异常失败：{str(e)}")
            return None, False

    def get_exception_stats(self, route_id: str = None,
                            days: int = 7) -> Dict:
        """
        获取异常统计

        Args:
            route_id: 路线 ID
            days: 统计天数

        Returns:
            统计字典
        """
        since = datetime.now() - timedelta(days=days)

        query = self.db.query(DeliveryExceptionEntity).filter(
            DeliveryExceptionEntity.detected_at >= since
        )

        if route_id:
            query = query.filter(DeliveryExceptionEntity.route_id == route_id)

        exceptions = query.all()

        if not exceptions:
            return {
                "total": 0,
                "by_type": {},
                "by_severity": {},
                "resolved_count": 0,
                "resolution_rate": 0.0
            }

        # 按类型统计
        by_type = defaultdict(int)
        by_severity = defaultdict(int)
        resolved_count = 0

        for exc in exceptions:
            by_type[exc.exception_type] += 1
            by_severity[exc.severity] += 1
            if exc.resolved_at:
                resolved_count += 1

        return {
            "total": len(exceptions),
            "by_type": dict(by_type),
            "by_severity": dict(by_severity),
            "resolved_count": resolved_count,
            "resolution_rate": resolved_count / len(exceptions) if exceptions else 0.0
        }


class FulfillmentSchedulingService:
    """
    智能履约调度服务 - 主服务类

    整合路径优化、人流预测、时间窗口推荐、异常处理功能
    """

    def __init__(self, db: Session):
        self.db = db
        self.logger = logger
        self.request_id = ""
        self.user_id = ""

        # 初始化子服务
        self.path_optimizer = PathOptimizationAlgorithm(db)
        self.traffic_predictor = TrafficFlowPredictor(db)
        self.time_window_recommender = TimeWindowRecommender(db)
        self.exception_handler = ExceptionHandler(db)

    def set_request_context(self, request_id: str, user_id: str = ""):
        """设置请求上下文"""
        self.request_id = request_id
        self.user_id = user_id

    def _log(self, level: str, message: str, extra: dict = None):
        """结构化日志"""
        log_data = {"request_id": self.request_id, "user_id": self.user_id}
        if extra:
            log_data.update(extra)
        getattr(self.logger, level)(message, extra=log_data)

    # ========== 自提点管理 ==========

    def create_pickup_point(self, data: Dict) -> Tuple[Optional[PickupPointEntity], bool]:
        """创建自提点"""
        try:
            pickup_point = PickupPointEntity(
                name=data["name"],
                community_id=data["community_id"],
                address=data["address"],
                latitude=data["latitude"],
                longitude=data["longitude"],
                contact_name=data["contact_name"],
                contact_phone=data["contact_phone"],
                opening_hours=data.get("opening_hours"),
                capacity=data.get("capacity", 100)
            )

            self.db.add(pickup_point)
            self.db.commit()
            self.db.refresh(pickup_point)

            self._log("info", "自提点创建成功", {
                "pickup_point_id": pickup_point.id,
                "name": pickup_point.name
            })

            return pickup_point, True

        except Exception as e:
            self.db.rollback()
            self._log("error", f"创建自提点失败：{str(e)}", {"data": data})
            return None, False

    def get_pickup_point(self, pickup_point_id: str) -> Optional[PickupPointEntity]:
        """获取自提点详情"""
        return self.db.query(PickupPointEntity).filter(
            PickupPointEntity.id == pickup_point_id
        ).first()

    def list_pickup_points(self, community_id: str = None,
                           status: str = None) -> List[PickupPointEntity]:
        """获取自提点列表"""
        query = self.db.query(PickupPointEntity)

        if community_id:
            query = query.filter(PickupPointEntity.community_id == community_id)
        if status:
            query = query.filter(PickupPointEntity.status == status)

        return query.all()

    def update_pickup_point_status(self, pickup_point_id: str,
                                    status: str) -> Tuple[Optional[PickupPointEntity], bool]:
        """更新自提点状态"""
        try:
            pickup_point = self.db.query(PickupPointEntity).filter(
                PickupPointEntity.id == pickup_point_id
            ).first()

            if not pickup_point:
                return None, False

            pickup_point.status = status
            pickup_point.updated_at = datetime.now()

            self.db.commit()
            self.db.refresh(pickup_point)

            return pickup_point, True

        except Exception as e:
            self.db.rollback()
            return None, False

    # ========== 配送路线管理 ==========

    def create_delivery_route(self, data: Dict) -> Tuple[Optional[DeliveryRouteEntity], bool]:
        """创建配送路线"""
        try:
            route = DeliveryRouteEntity(
                name=data["name"],
                warehouse_id=data["warehouse_id"],
                driver_id=data.get("driver_id"),
                vehicle_id=data.get("vehicle_id"),
                stops=data.get("stops", []),
                priority=data.get("priority", "normal")
            )

            self.db.add(route)
            self.db.commit()
            self.db.refresh(route)

            self._log("info", "配送路线创建成功", {
                "route_id": route.id,
                "name": route.name
            })

            return route, True

        except Exception as e:
            self.db.rollback()
            self._log("error", f"创建配送路线失败：{str(e)}", {"data": data})
            return None, False

    def optimize_delivery_route(self, warehouse_location: Tuple[float, float],
                                 pickup_point_ids: List[str],
                                 constraints: Optional[Dict] = None) -> Dict:
        """优化配送路线"""
        return self.path_optimizer.optimize_route(
            warehouse_location, pickup_point_ids, constraints
        )

    def get_route(self, route_id: str) -> Optional[DeliveryRouteEntity]:
        """获取配送路线详情"""
        return self.db.query(DeliveryRouteEntity).filter(
            DeliveryRouteEntity.id == route_id
        ).first()

    def update_route_status(self, route_id: str, status: str) -> Tuple[Optional[DeliveryRouteEntity], bool]:
        """更新配送路线状态"""
        try:
            route = self.db.query(DeliveryRouteEntity).filter(
                DeliveryRouteEntity.id == route_id
            ).first()

            if not route:
                return None, False

            route.status = status
            route.updated_at = datetime.now()

            if status == "completed":
                route.completed_at = datetime.now()

            self.db.commit()
            self.db.refresh(route)

            return route, True

        except Exception as e:
            self.db.rollback()
            return None, False

    # ========== 配送任务管理 ==========

    def create_delivery_task(self, data: Dict) -> Tuple[Optional[DeliveryTaskEntity], bool]:
        """创建配送任务"""
        try:
            task = DeliveryTaskEntity(
                route_id=data["route_id"],
                order_id=data["order_id"],
                fulfillment_id=data["fulfillment_id"],
                pickup_point_id=data["pickup_point_id"],
                delivery_time_window_start=data.get("delivery_time_window", {}).get("start"),
                delivery_time_window_end=data.get("delivery_time_window", {}).get("end"),
                window_type=data.get("window_type", "flexible"),
                priority=data.get("priority", "normal")
            )

            self.db.add(task)
            self.db.commit()
            self.db.refresh(task)

            self._log("info", "配送任务创建成功", {
                "task_id": task.id,
                "route_id": task.route_id
            })

            return task, True

        except Exception as e:
            self.db.rollback()
            self._log("error", f"创建配送任务失败：{str(e)}", {"data": data})
            return None, False

    def get_task(self, task_id: str) -> Optional[DeliveryTaskEntity]:
        """获取配送任务详情"""
        return self.db.query(DeliveryTaskEntity).filter(
            DeliveryTaskEntity.id == task_id
        ).first()

    def update_task_status(self, task_id: str, status: str,
                           actual_arrival: datetime = None) -> Tuple[Optional[DeliveryTaskEntity], bool]:
        """更新配送任务状态"""
        try:
            task = self.db.query(DeliveryTaskEntity).filter(
                DeliveryTaskEntity.id == task_id
            ).first()

            if not task:
                return None, False

            task.status = status
            task.updated_at = datetime.now()

            if actual_arrival:
                task.actual_arrival = actual_arrival

            self.db.commit()
            self.db.refresh(task)

            return task, True

        except Exception as e:
            self.db.rollback()
            return None, False

    # ========== 人流预测 ==========

    def predict_pickup_point_traffic(self, pickup_point_id: str,
                                      prediction_date: datetime) -> List[Dict]:
        """预测自提点人流"""
        return self.traffic_predictor.predict_hourly_flow(
            pickup_point_id, prediction_date
        )

    def get_optimal_pickup_times(self, pickup_point_id: str,
                                  date: datetime, top_n: int = 3) -> List[Dict]:
        """获取最佳取货时段"""
        return self.traffic_predictor.get_optimal_pickup_times(
            pickup_point_id, date, top_n
        )

    # ========== 时间窗口推荐 ==========

    def recommend_delivery_windows(self, fulfillment_id: str, pickup_point_id: str,
                                    preferred_date: datetime = None,
                                    window_duration: int = 60) -> Dict:
        """推荐配送时间窗口"""
        return self.time_window_recommender.recommend_windows(
            fulfillment_id, pickup_point_id, preferred_date, window_duration
        )

    # ========== 异常处理 ==========

    def report_delivery_exception(self, data: Dict) -> Tuple[Optional[DeliveryExceptionEntity], bool]:
        """上报配送异常"""
        return self.exception_handler.report_exception(data)

    def resolve_delivery_exception(self, exception_id: str, resolution: str) -> Tuple[Optional[DeliveryExceptionEntity], bool]:
        """解决配送异常"""
        return self.exception_handler.resolve_exception(exception_id, resolution)

    def get_exception_stats(self, route_id: str = None, days: int = 7) -> Dict:
        """获取异常统计"""
        return self.exception_handler.get_exception_stats(route_id, days)

    # ========== 综合调度 ==========

    def schedule_fulfillment(self, fulfillment_id: str, pickup_point_id: str,
                              warehouse_location: Tuple[float, float],
                              preferred_date: datetime = None) -> Dict:
        """
        综合调度：为履约记录安排最优配送方案

        1. 推荐最佳时间窗口
        2. 优化配送路线
        3. 创建配送任务

        Args:
            fulfillment_id: 履约记录 ID
            pickup_point_id: 自提点 ID
            warehouse_location: 仓库位置
            preferred_date: 偏好日期

        Returns:
            调度结果
        """
        # 1. 推荐时间窗口
        window_result = self.recommend_delivery_windows(
            fulfillment_id, pickup_point_id, preferred_date
        )

        if not window_result.get("success"):
            return {
                "success": False,
                "message": "无法推荐合适的时间窗口",
                "details": window_result
            }

        # 2. 获取自提点位置
        pickup_point = self.get_pickup_point(pickup_point_id)
        if not pickup_point:
            return {"success": False, "message": "自提点不存在"}

        # 3. 创建配送任务
        task_data = {
            "route_id": "pending",  # 待分配路线
            "order_id": self._get_order_id_by_fulfillment(fulfillment_id),
            "fulfillment_id": fulfillment_id,
            "pickup_point_id": pickup_point_id,
            "delivery_time_window": window_result["best_window"],
            "window_type": "flexible",
            "priority": "normal"
        }

        task, task_success = self.create_delivery_task(task_data)
        if not task_success:
            return {"success": False, "message": "创建配送任务失败"}

        return {
            "success": True,
            "task_id": task.id,
            "recommended_window": window_result["best_window"],
            "pickup_point": {
                "id": pickup_point.id,
                "name": pickup_point.name,
                "address": pickup_point.address,
                "location": (pickup_point.latitude, pickup_point.longitude)
            },
            "message": "配送调度成功"
        }

    def _get_order_id_by_fulfillment(self, fulfillment_id: str) -> str:
        """通过履约 ID 获取订单 ID"""
        fulfillment = self.db.query(FulfillmentEntity).filter(
            FulfillmentEntity.id == fulfillment_id
        ).first()
        return fulfillment.order_id if fulfillment else ""
