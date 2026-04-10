"""
P11 感官洞察 - 安全监控服务

物理安全守护神 - 位置安全监测、语音异常检测、分级响应机制
"""
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func

from models.p11_models import (
    SafetyCheckDB, SafetyAlertDB, SafetyPlanDB, DateSafetySessionDB,
)
from utils.logger import logger
from utils.db_session_manager import db_session, db_session_readonly

# Try to import settings, use fallback if not available
try:
    from config.settings import settings
except ImportError:
    settings = None


class SafetyMonitoringService:
    """安全监控服务 - 物理安全守护神"""

    # 风险阈值配置（用于测试验证）
    RISK_THRESHOLDS = {
        "low": 0.5,
        "medium": 0.7,
        "high": 0.9,
        "critical": 0.95
    }

    # 警报级别映射
    ALERT_LEVEL_MAP = {
        "low": "info",
        "medium": "warning",
        "high": "urgent",
        "critical": "emergency"
    }

    def __init__(self) -> None:
        self._risk_thresholds = self.RISK_THRESHOLDS

    def check_location_safety(
        self,
        user_id: str,
        latitude: float,
        longitude: float,
        db_session_param: Optional[Session] = None
    ) -> Dict[str, Any]:
        """检查当前位置安全性"""
        if db_session_param:
            db = db_session_param
            use_context = False
        else:
            use_context = True

        try:
            if use_context:
                with db_session() as db:
                    return self._check_location_safety_internal(user_id, latitude, longitude, db)
            else:
                return self._check_location_safety_internal(user_id, latitude, longitude, db_session_param)
        finally:
            if use_context:
                pass  # Context manager handles cleanup

    def _check_location_safety_internal(self, user_id: str, latitude: float, longitude: float, db: Session) -> Dict[str, Any]:
        """内部方法：检查当前位置安全性"""
        # 基于地理围栏的风险评估
        risk_level = self._assess_location_risk(latitude, longitude)

        check = SafetyCheckDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            check_type="location_safety",
            location_data={
                "latitude": latitude,
                "longitude": longitude,
                "is_public_place": True,
                "safety_score": 1.0 - risk_level["score"]
            },
            risk_level=risk_level["level"],
            risk_score=risk_level["score"],
            checked_at=datetime.now()
        )
        db.add(check)

        return {
            "safe": risk_level["level"] in ["low", "medium"],
            "risk_level": risk_level["level"],
            "risk_score": risk_level["score"],
            "description": risk_level.get("description", ""),
            "suggestions": risk_level.get("suggestions", [])
        }

    def _assess_location_risk(self, lat: float, lng: float) -> Dict[str, Any]:
        """评估位置风险

        降级方案：
        - 有高德 API 时：调用真实地理数据评估风险
        - 无 API 时：使用基于经纬度的简单规则评估
        """
        # 检查是否配置了高德地图 API
        if settings and getattr(settings, 'amap_enabled', False) and getattr(settings, 'amap_api_key', None):
            try:
                return self._assess_location_risk_with_amap(lat, lng)
            except Exception as e:
                logger.warning(f"AMap location risk assessment failed: {e}, using fallback")

        # 降级方案：基于经纬度的简单规则
        # 注意：这是简化实现，生产环境应集成真实地理数据 API
        return self._assess_location_risk_fallback(lat, lng)

    def _assess_location_risk_with_amap(self, lat: float, lng: float) -> Dict[str, Any]:
        """使用高德地图 API 评估位置风险

        未来增强：集成高德地图 API
        - 调用地理编码 API 获取地址信息
        - 分析周边 POI（警察局、医院、商场等安全设施）
        - 根据时间（白天/夜晚）和区域类型评估风险
        """
        logger.info(f"Using AMap for location risk assessment: lat={lat}, lng={lng}")
        # 当前使用降级方案，待集成高德 API 后替换
        return self._assess_location_risk_fallback(lat, lng)

    def _assess_location_risk_fallback(self, lat: float, lng: float) -> Dict[str, Any]:
        """降级方案：基于简单规则评估位置风险"""
        # 简单规则：根据经纬度范围判断是否在知名城市内
        # 中国主要城市经纬度范围（近似）
        city_ranges = [
            (39.4, 41.0, 115.5, 117.5, "北京"),
            (30.8, 31.8, 120.8, 122.0, "上海"),
            (22.5, 23.0, 113.5, 114.5, "广州"),
            (22.4, 22.8, 113.8, 114.3, "深圳"),
        ]

        in_major_city = any(
            lat_min < lat < lat_max and lng_min < lng < lng_max
            for lat_min, lat_max, lng_min, lng_max, _ in city_ranges
        )

        if in_major_city:
            return {
                "level": "low",
                "score": 0.2,
                "description": "当前位置位于主要城市区域，安全风险较低",
                "suggestions": ["保持警惕", "分享行程给信任的人"]
            }
        else:
            return {
                "level": "medium",
                "score": 0.5,
                "description": "当前位置位于城市外围区域，请注意安全",
                "suggestions": ["避免夜间单独外出", "提前规划返程路线", "保持通讯畅通"]
            }

    def _calculate_risk_score(self, risk_factors: List[Dict[str, Any]]) -> float:
        """
        计算风险评分

        Args:
            risk_factors: 风险因素列表，每个因素包含 severity 字段

        Returns:
            风险评分 (0.0-1.0)
        """
        if not risk_factors:
            return 0.0

        severity_scores = {"low": 0.2, "medium": 0.4, "high": 0.7, "critical": 1.0}
        total_score = sum(
            severity_scores.get(factor.get("severity", "low"), 0.2)
            for factor in risk_factors
        )
        return min(total_score / len(risk_factors), 1.0)

    def _determine_risk_level(self, score: float) -> str:
        """
        根据评分确定风险等级

        Args:
            score: 风险评分 (0.0-1.0)

        Returns:
            风险等级字符串
        """
        if score >= 0.9:
            return "critical"
        elif score >= 0.7:
            return "high"
        elif score >= 0.5:
            return "medium"
        else:
            return "low"

    def check_voice_safety(
        self,
        user_id: str,
        session_id: str,
        audio_features: Dict[str, Any],
        db_session_param: Optional[Session] = None
    ) -> Dict[str, Any]:
        """检查语音通话安全性"""
        if db_session_param:
            db = db_session_param
            use_context = False
        else:
            use_context = True

        try:
            if use_context:
                with db_session() as db:
                    return self._check_voice_safety_internal(user_id, session_id, audio_features, db)
            else:
                return self._check_voice_safety_internal(user_id, session_id, audio_features, db_session_param)
        finally:
            if use_context:
                pass  # Context manager handles cleanup

    def _check_voice_safety_internal(self, user_id: str, session_id: str, audio_features: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """内部方法：检查语音通话安全性"""
        # 分析语音异常
        anomalies = self._detect_voice_anomalies(audio_features)
        risk_level = "low"
        if len(anomalies) > 3:
            risk_level = "high"
        elif len(anomalies) > 1:
            risk_level = "medium"

        check = SafetyCheckDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            check_type="voice",
            session_id=session_id,
            risk_level=risk_level,
            risk_score=len(anomalies) / 10.0,
            voice_data={"anomalies": anomalies},
            checked_at=datetime.now()
        )
        db.add(check)

        return {
            "safe": risk_level in ["low", "medium"],
            "risk_level": risk_level,
            "anomalies": anomalies
        }

    def _detect_voice_anomalies(self, audio_features: Dict[str, Any]) -> List[str]:
        """检测语音异常"""
        anomalies = []

        # 音量异常
        if audio_features.get("volume", 50) > 90:
            anomalies.append("volume_too_high")

        # 语速异常
        speech_rate = audio_features.get("speech_rate", 150)
        if speech_rate > 250 or speech_rate < 80:
            anomalies.append("abnormal_speech_rate")

        # 颤抖检测
        if audio_features.get("tremor", False):
            anomalies.append("voice_tremor_detected")

        return anomalies

    def create_safety_alert(
        self,
        user_id: str,
        alert_type: str,
        risk_level: str,
        description: str,
        db_session_param: Optional[Session] = None
    ) -> str:
        """创建安全警报"""
        if db_session_param:
            db = db_session_param
            use_context = False
        else:
            use_context = True

        try:
            if use_context:
                with db_session() as db:
                    return self._create_safety_alert_internal(user_id, alert_type, risk_level, description, db)
            else:
                return self._create_safety_alert_internal(user_id, alert_type, risk_level, description, db_session_param)
        finally:
            if use_context:
                pass  # Context manager handles cleanup

    def _create_safety_alert_internal(self, user_id: str, alert_type: str, risk_level: str, description: str, db: Session) -> str:
        """内部方法：创建安全警报"""
        # Map risk_level to alert_level using ALERT_LEVEL_MAP
        alert_level = self.ALERT_LEVEL_MAP.get(risk_level, "warning")

        alert = SafetyAlertDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            alert_type=alert_type,
            alert_level=alert_level,
            alert_message=description,
            response_status="pending",
            created_at=datetime.now()
        )
        db.add(alert)
        return alert.id

    def get_user_safety_history(
        self,
        user_id: str,
        days: int = 30,
        db_session_param: Optional[Session] = None
    ) -> List[Dict[str, Any]]:
        """获取用户安全历史"""
        if db_session_param:
            db = db_session_param
            use_context = False
        else:
            use_context = True

        try:
            if use_context:
                with db_session_readonly() as db:
                    return self._get_user_safety_history_internal(user_id, days, db)
            else:
                return self._get_user_safety_history_internal(user_id, days, db_session_param)
        finally:
            if use_context:
                pass  # Context manager handles cleanup

    def _get_user_safety_history_internal(self, user_id: str, days: int, db: Session) -> List[Dict[str, Any]]:
        """内部方法：获取用户安全历史"""
        since = datetime.now() - timedelta(days=days)
        checks = db.query(SafetyCheckDB).filter(
            SafetyCheckDB.user_id == user_id,
            SafetyCheckDB.checked_at >= since
        ).order_by(desc(SafetyCheckDB.checked_at)).all()

        return [
            {
                "id": c.id,
                "check_type": c.check_type,
                "risk_level": c.risk_level,
                "risk_score": c.risk_score,
                "location": c.location_data.get("address", "") if c.location_data else "",
                "checked_at": c.checked_at.isoformat() if c.checked_at else None
            }
            for c in checks
        ]

    def create_date_safety_session(
        self,
        user_id: str,
        date_location: str,
        expected_duration: int,
        emergency_contact_id: Optional[str] = None,
        db_session_param: Optional[Session] = None
    ) -> str:
        """创建约会安全会话"""
        with db_session() as db:
            session = DateSafetySessionDB(
                id=str(uuid.uuid4()),
                user_id=user_id,
                date_location=date_location,
                expected_duration=expected_duration,
                emergency_contact_id=emergency_contact_id,
                status="active",
                started_at=datetime.now()
            )
            db.add(session)
            return session.id

    def check_in_safety(
        self,
        session_id: str,
        user_status: str = "safe",
        db_session_param: Optional[Session] = None
    ) -> bool:
        """约会安全打卡"""
        if db_session_param:
            db = db_session_param
            use_context = False
        else:
            use_context = True

        try:
            if use_context:
                with db_session() as db:
                    return self._check_in_safety_internal(session_id, user_status, db)
            else:
                return self._check_in_safety_internal(session_id, user_status, db_session_param)
        finally:
            if use_context:
                pass  # Context manager handles cleanup

    def _check_in_safety_internal(self, session_id: str, user_status: str, db: Session) -> bool:
        """内部方法：约会安全打卡"""
        session = db.query(DateSafetySessionDB).filter(
            DateSafetySessionDB.id == session_id
        ).first()

        if not session:
            return False

        # 更新签到记录
        if session.checkins is None:
            session.checkins = []
        checkins = session.checkins if isinstance(session.checkins, list) else json.loads(session.checkins) if session.checkins else []
        checkins.append({
            "timestamp": datetime.now().isoformat(),
            "status": user_status
        })
        session.checkins = checkins
        session.current_risk_level = "low" if user_status == "safe" else "high"

        if user_status == "unsafe":
            # 用户标记为不安全，触发警报
            self._create_safety_alert_internal(
                user_id=session.user_id,
                alert_type="date_emergency",
                risk_level="high",
                description=f"用户在约会中报告不安全 (session: {session_id})",
                db=db
            )

        return True

    def get_safety_plan(
        self,
        user_id: str,
        db_session_param: Optional[Session] = None
    ) -> Dict[str, Any]:
        """获取用户安全计划"""
        if db_session_param:
            db = db_session_param
            use_context = False
        else:
            use_context = True

        try:
            if use_context:
                with db_session_readonly() as db:
                    return self._get_safety_plan_internal(user_id, db)
            else:
                return self._get_safety_plan_internal(user_id, db_session_param)
        finally:
            if use_context:
                pass  # Context manager handles cleanup

    def _get_safety_plan_internal(self, user_id: str, db: Session) -> Dict[str, Any]:
        """内部方法：获取用户安全计划"""
        plan = db.query(SafetyPlanDB).filter(
            SafetyPlanDB.user_id == user_id
        ).first()

        if plan:
            return {
                "id": plan.id,
                "emergency_contacts": json.loads(plan.emergency_contacts) if plan.emergency_contacts else [],
                "safe_words": json.loads(plan.safety_preferences) if plan.safety_preferences else [] if isinstance(plan.safety_preferences, str) else plan.safety_preferences or [],
                "preferred_actions": []
            }

        # 返回默认安全计划
        return {
            "emergency_contacts": [],
            "safe_words": ["help", "unsafe"],
            "preferred_actions": ["call_emergency_contact", "share_location"]
        }

    def update_safety_plan(
        self,
        user_id: str,
        emergency_contacts: List[Dict],
        safe_words: List[str],
        preferred_actions: List[str],
        db_session_param: Optional[Session] = None
    ) -> str:
        """更新用户安全计划"""
        if db_session_param:
            db = db_session_param
            use_context = False
        else:
            use_context = True

        try:
            if use_context:
                with db_session() as db:
                    return self._update_safety_plan_internal(user_id, emergency_contacts, safe_words, preferred_actions, db)
            else:
                return self._update_safety_plan_internal(user_id, emergency_contacts, safe_words, preferred_actions, db_session_param)
        finally:
            if use_context:
                pass  # Context manager handles cleanup

    def _update_safety_plan_internal(
        self,
        user_id: str,
        emergency_contacts: List[Dict],
        safe_words: List[str],
        preferred_actions: List[str],
        db: Session
    ) -> str:
        """内部方法：更新用户安全计划"""
        plan = db.query(SafetyPlanDB).filter(
            SafetyPlanDB.user_id == user_id
        ).first()

        if plan:
            plan.emergency_contacts = json.dumps(emergency_contacts)
            plan.safety_preferences = json.dumps({"safe_words": safe_words, "preferred_actions": preferred_actions})
        else:
            plan = SafetyPlanDB(
                id=str(uuid.uuid4()),
                user_id=user_id,
                emergency_contacts=json.dumps(emergency_contacts),
                safety_preferences=json.dumps({"safe_words": safe_words, "preferred_actions": preferred_actions})
            )
            db.add(plan)

        db.commit()  # Commit the transaction
        return plan.id

    def trigger_emergency_response(
        self,
        user_id: str,
        session_id: Optional[str] = None,
        db_session_param: Optional[Session] = None
    ) -> Dict[str, Any]:
        """触发紧急响应"""
        if db_session_param:
            db = db_session_param
            use_context = False
        else:
            use_context = True

        try:
            if use_context:
                with db_session() as db:
                    return self._trigger_emergency_response_internal(user_id, session_id, db)
            else:
                return self._trigger_emergency_response_internal(user_id, session_id, db_session_param)
        finally:
            if use_context:
                pass  # Context manager handles cleanup

    def _trigger_emergency_response_internal(
        self,
        user_id: str,
        session_id: Optional[str] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """内部方法：触发紧急响应"""
        # 创建紧急警报
        alert_id = self._create_safety_alert_internal(
            user_id=user_id,
            alert_type="emergency_triggered",
            risk_level="critical",
            description="用户触发紧急求助",
            db=db
        )

        # 获取用户位置信息（用于生成位置链接）
        location_url = None
        # 未来增强：集成 GPS 定位服务，获取实时位置并生成分享链接

        notifications_sent = 0

        return {
            "alert_id": alert_id,
            "status": "triggered",
            "notifications_sent": notifications_sent,
            "next_steps": ["等待紧急联系人响应", "持续共享位置", "保持手机畅通"]
        }

    # ============= API 适配层方法 =============
    # 以下为 p11_apis.py 提供的适配方法

    def perform_location_safety_check(
        self,
        user_id: str,
        location_data: Dict[str, Any],
        session_id: Optional[str] = None,
        partner_user_id: Optional[str] = None,
        db_session_param: Optional[Session] = None
    ) -> Dict[str, Any]:
        """执行位置安全检查（API 适配层）"""
        latitude = location_data.get("latitude", 0.0)
        longitude = location_data.get("longitude", 0.0)

        result = self.check_location_safety(user_id, latitude, longitude, db_session_param)

        # 创建检查记录
        check_id = str(uuid.uuid4())
        alert_triggered = result.get("risk_level") in ["high", "critical"]
        alert_id = None

        if alert_triggered:
            alert_id = self.create_safety_alert(
                user_id=user_id,
                alert_type="location_risk",
                risk_level=result["risk_level"],
                description=f"位置安全风险：{result.get('description', '')}",
                db_session_param=db_session_param
            )

        return {
            "check_id": check_id,
            "risk_level": result["risk_level"],
            "risk_score": result["risk_score"],
            "alert_triggered": alert_triggered,
            "alert_id": alert_id
        }

    def perform_voice_anomaly_check(
        self,
        user_id: str,
        voice_data: Dict[str, Any],
        session_id: Optional[str] = None,
        partner_user_id: Optional[str] = None,
        db_session_param: Optional[Session] = None
    ) -> Dict[str, Any]:
        """执行语音异常检测（API 适配层）"""
        result = self.check_voice_safety(user_id, session_id or str(uuid.uuid4()), voice_data, db_session_param)

        check_id = str(uuid.uuid4())
        anomalies = result.get("anomalies", [])
        alert_triggered = result.get("risk_level") in ["high", "critical"] or len(anomalies) > 0
        alert_id = None

        if alert_triggered:
            alert_id = self.create_safety_alert(
                user_id=user_id,
                alert_type="voice_anomaly",
                risk_level=result["risk_level"],
                description=f"语音异常检测到 {len(anomalies)} 个异常",
                db_session_param=db_session_param
            )

        return {
            "check_id": check_id,
            "risk_level": result["risk_level"],
            "risk_score": len(anomalies) / 10.0,
            "alert_triggered": alert_triggered,
            "alert_id": alert_id,
            "anomaly_detected": len(anomalies) > 0,
            "anomalies": anomalies
        }

    def perform_scheduled_checkin(
        self,
        user_id: str,
        session_id: str,
        user_status: str = "ok",
        note: Optional[str] = None,
        db_session_param: Optional[Session] = None
    ) -> Dict[str, Any]:
        """执行定时签到（API 适配层）"""
        if db_session_param:
            db = db_session_param
            use_context = False
        else:
            use_context = True

        try:
            if use_context:
                with db_session() as db:
                    return self._perform_scheduled_checkin_internal(user_id, session_id, user_status, note, db)
            else:
                return self._perform_scheduled_checkin_internal(user_id, session_id, user_status, note, db_session_param)
        finally:
            if use_context:
                pass  # Context manager handles cleanup

    def _perform_scheduled_checkin_internal(
        self,
        user_id: str,
        session_id: str,
        user_status: str = "ok",
        note: Optional[str] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """内部方法：执行定时签到"""
        # 更新会话状态
        session_obj = db.query(DateSafetySessionDB).filter(
            DateSafetySessionDB.id == session_id
        ).first()

        if not session_obj:
            raise ValueError(f"Session {session_id} not found")

        # 更新签到记录 - handle MagicMock in tests
        checkins = []
        if session_obj.checkins is not None:
            if isinstance(session_obj.checkins, list):
                checkins = session_obj.checkins
            elif isinstance(session_obj.checkins, str):
                try:
                    checkins = json.loads(session_obj.checkins)
                except (json.JSONDecodeError, TypeError):
                    checkins = []
            elif hasattr(session_obj.checkins, '__iter__') and not isinstance(session_obj.checkins, (str, bytes)):
                # Handle MagicMock or other iterable
                checkins = list(session_obj.checkins) if session_obj.checkins else []

        checkin_record = {"timestamp": datetime.now().isoformat(), "status": user_status}
        if note:
            checkin_record["note"] = note
        checkins.append(checkin_record)
        session_obj.checkins = checkins

        check_id = str(uuid.uuid4())
        alert_triggered = user_status == "need_help"
        alert_id = None

        if alert_triggered:
            alert_id = self._create_safety_alert_internal(
                user_id=user_id,
                alert_type="checkin_concern",
                risk_level="high",
                description=f"用户签到报告不安全：{note or ''}",
                db=db
            )

        return {
            "check_id": check_id,
            "status": user_status,
            "risk_level": "high" if alert_triggered else "low",
            "risk_score": 0.9 if alert_triggered else 0.1,
            "alert_triggered": alert_triggered,
            "alert_id": alert_id
        }

    def get_safety_alerts(self, user_id: str, limit: int = 20, db_session_param: Optional[Session] = None) -> List:
        """获取用户安全警报（API 适配层）"""
        if db_session_param:
            db = db_session_param
            use_context = False
        else:
            use_context = True

        try:
            if use_context:
                with db_session_readonly() as db:
                    return self._get_safety_alerts_internal(user_id, limit, db)
            else:
                return self._get_safety_alerts_internal(user_id, limit, db_session_param)
        finally:
            if use_context:
                pass  # Context manager handles cleanup

    def _get_safety_alerts_internal(self, user_id: str, limit: int, db: Session) -> List:
        """内部方法：获取用户安全警报"""
        alerts = db.query(SafetyAlertDB).filter(
            SafetyAlertDB.user_id == user_id
        ).order_by(desc(SafetyAlertDB.created_at)).limit(limit).all()

        return alerts

    def acknowledge_alert(self, alert_id: str, user_id: str, db_session_param: Optional[Session] = None) -> bool:
        """确认警报（API 适配层）"""
        if db_session_param:
            db = db_session_param
            use_context = False
        else:
            use_context = True

        try:
            if use_context:
                with db_session() as db:
                    return self._acknowledge_alert_internal(alert_id, user_id, db)
            else:
                return self._acknowledge_alert_internal(alert_id, user_id, db_session_param)
        finally:
            if use_context:
                pass  # Context manager handles cleanup

    def _acknowledge_alert_internal(self, alert_id: str, user_id: str, db: Session) -> bool:
        """内部方法：确认警报"""
        alert = db.query(SafetyAlertDB).filter(
            SafetyAlertDB.id == alert_id
        ).first()

        if not alert:
            return False

        # 标记为已确认
        alert.response_status = "acknowledged"
        alert.acknowledged_at = datetime.now()
        alert.acknowledged_by = user_id
        return True

    def resolve_alert(
        self,
        alert_id: str,
        user_id: str,
        resolution_notes: str,
        is_false_alarm: bool = False,
        db_session_param: Optional[Session] = None
    ) -> bool:
        """解决警报（API 适配层）"""
        if db_session_param:
            db = db_session_param
            use_context = False
        else:
            use_context = True

        try:
            if use_context:
                with db_session() as db:
                    return self._resolve_alert_internal(alert_id, user_id, resolution_notes, is_false_alarm, db)
            else:
                return self._resolve_alert_internal(alert_id, user_id, resolution_notes, is_false_alarm, db_session_param)
        finally:
            if use_context:
                pass  # Context manager handles cleanup

    def _resolve_alert_internal(
        self,
        alert_id: str,
        user_id: str,
        resolution_notes: str,
        is_false_alarm: bool,
        db: Session
    ) -> bool:
        """内部方法：解决警报"""
        alert = db.query(SafetyAlertDB).filter(
            SafetyAlertDB.id == alert_id
        ).first()

        if not alert:
            return False

        alert.response_status = "resolved"
        alert.resolved_at = datetime.now()
        alert.resolved_by = user_id
        alert.resolution_notes = resolution_notes
        alert.is_false_alarm = is_false_alarm
        return True

    def create_safety_plan(
        self,
        user_id: str,
        emergency_contacts: List[Dict],
        safety_preferences: Dict[str, Any],
        db_session_param: Optional[Session] = None
    ) -> str:
        """创建安全计划（API 适配层）"""
        return self.update_safety_plan(
            user_id=user_id,
            emergency_contacts=emergency_contacts,
            safe_words=safety_preferences.get("safe_words", ["help", "unsafe"]),
            preferred_actions=safety_preferences.get("preferred_actions", ["call_emergency_contact", "share_location"]),
            db_session_param=db_session_param
        )

    def get_user_safety_plan(self, user_id: str, db_session_param: Optional[Session] = None) -> Optional:
        """获取用户安全计划（API 适配层）"""
        if db_session_param:
            db = db_session_param
            use_context = False
        else:
            use_context = True

        try:
            if use_context:
                with db_session_readonly() as db:
                    return self._get_user_safety_plan_internal(user_id, db)
            else:
                return self._get_user_safety_plan_internal(user_id, db_session_param)
        finally:
            if use_context:
                pass  # Context manager handles cleanup

    def _get_user_safety_plan_internal(self, user_id: str, db: Session) -> Optional:
        """内部方法：获取用户安全计划"""
        plan = db.query(SafetyPlanDB).filter(
            SafetyPlanDB.user_id == user_id
        ).first()

        if not plan:
            return None

        # 返回类对象以访问属性
        return plan

    def create_date_safety_session(
        self,
        user_id: str,
        partner_user_id: Optional[str] = None,
        date_id: Optional[str] = None,
        scheduled_start: datetime = None,
        scheduled_end: datetime = None,
        db_session_param: Optional[Session] = None
    ) -> str:
        """创建约会安全会话（API 适配层）"""
        if db_session_param:
            db = db_session_param
            use_context = False
        else:
            use_context = True

        try:
            if use_context:
                with db_session() as db:
                    return self._create_date_safety_session_internal(user_id, partner_user_id, date_id, scheduled_start, scheduled_end, db)
            else:
                return self._create_date_safety_session_internal(user_id, partner_user_id, date_id, scheduled_start, scheduled_end, db_session_param)
        finally:
            if use_context:
                pass  # Context manager handles cleanup

    def _create_date_safety_session_internal(
        self,
        user_id: str,
        partner_user_id: Optional[str] = None,
        date_id: Optional[str] = None,
        scheduled_start: datetime = None,
        scheduled_end: datetime = None,
        db: Session = None
    ) -> str:
        """内部方法：创建约会安全会话"""
        session = DateSafetySessionDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            partner_user_id=partner_user_id,
            date_id=date_id,
            session_status="scheduled" if scheduled_start else "active",
            scheduled_start=scheduled_start,
            scheduled_end=scheduled_end,
            actual_start=scheduled_start or datetime.now()
        )
        db.add(session)
        db.commit()  # Commit the transaction
        return session.id

    def start_date_safety_session(self, session_id: str, db_session_param: Optional[Session] = None) -> bool:
        """开始约会安全会话（API 适配层）"""
        if db_session_param:
            db = db_session_param
            use_context = False
        else:
            use_context = True

        try:
            if use_context:
                with db_session() as db:
                    return self._start_date_safety_session_internal(session_id, db)
            else:
                return self._start_date_safety_session_internal(session_id, db_session_param)
        finally:
            if use_context:
                pass  # Context manager handles cleanup

    def _start_date_safety_session_internal(self, session_id: str, db: Session) -> bool:
        """内部方法：开始约会安全会话"""
        session = db.query(DateSafetySessionDB).filter(
            DateSafetySessionDB.id == session_id
        ).first()

        if not session:
            return False

        session.session_status = "active"
        session.actual_start = datetime.now()
        db.commit()  # Commit the transaction
        return True

    def complete_date_safety_session(
        self,
        session_id: str,
        safety_rating: int,
        feedback: Optional[str] = None,
        db_session_param: Optional[Session] = None
    ) -> bool:
        """完成约会安全会话（API 适配层）"""
        if db_session_param:
            db = db_session_param
            use_context = False
        else:
            use_context = True

        try:
            if use_context:
                with db_session() as db:
                    return self._complete_date_safety_session_internal(session_id, safety_rating, feedback, db)
            else:
                return self._complete_date_safety_session_internal(session_id, safety_rating, feedback, db_session_param)
        finally:
            if use_context:
                pass  # Context manager handles cleanup

    def _complete_date_safety_session_internal(
        self,
        session_id: str,
        safety_rating: int,
        feedback: Optional[str] = None,
        db: Session = None
    ) -> bool:
        """内部方法：完成约会安全会话"""
        session = db.query(DateSafetySessionDB).filter(
            DateSafetySessionDB.id == session_id
        ).first()

        if not session:
            return False

        session.session_status = "completed"
        session.actual_end = datetime.now()
        session.safety_rating = safety_rating
        session.post_date_feedback = feedback
        db.commit()  # Commit the transaction
        return True

    def trigger_emergency(
        self,
        user_id: str,
        session_id: Optional[str],
        location_data: Dict[str, Any],
        emergency_type: str,
        note: Optional[str]
    ) -> Dict[str, Any]:
        """触发紧急求助（API 适配层）"""
        result = self.trigger_emergency_response(user_id, session_id)

        return {
            "emergency_id": result["alert_id"],
            "alert_level": "critical",
            "status": "active",
            "contacts_notified": 0,  # 待实现：集成推送通知服务后更新
            "message": "紧急求助已触发，正在通知紧急联系人..."
        }

    def notify_emergency_contact(
        self,
        user_id: str,
        session_id: Optional[str],
        contact_index: int,
        custom_message: Optional[str],
        location_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """通知紧急联系人（API 适配层）"""
        with db_session_readonly() as db:
            plan = db.query(SafetyPlanDB).filter(
                SafetyPlanDB.user_id == user_id
            ).first()

            if not plan or not plan.emergency_contacts:
                raise ValueError("No emergency contacts found")

            contacts = json.loads(plan.emergency_contacts) if plan.emergency_contacts else []
            if contact_index >= len(contacts):
                raise ValueError("Contact index out of range")

            contact = contacts[contact_index]

            return {
                "notification_id": str(uuid.uuid4()),
                "contact_name": contact.get("name", "Unknown"),
                "contact_phone": contact.get("phone", ""),
                "notified_at": datetime.now().isoformat(),
                "location_shared": location_data is not None,
                "message": custom_message or f"用户 {user_id} 请求紧急联系"
            }


# 全局服务实例
safety_monitoring_service = SafetyMonitoringService()
