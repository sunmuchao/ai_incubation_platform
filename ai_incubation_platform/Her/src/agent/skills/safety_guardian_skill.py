"""
安全守护 Skill - 物理安全守护神

AI 安全保镖核心 Skill - 位置安全监测、语音异常检测、分级响应机制
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from agent.skills.base import BaseSkill
from utils.logger import logger
import json


class SafetyGuardianSkill:
    """
    AI 安全守护神 Skill - 实时保护用户安全

    核心能力:
    - 位置安全监测（地理围栏、危险区域预警）
    - 语音异常检测（求救信号、颤抖、异常音量）
    - 分级响应机制（低风险提醒 → 高风险报警 → 紧急联系人）
    - 安全计划管理（紧急联系人、安全偏好）

    自主触发:
    - 用户到达陌生/危险地点
    - 语音通话检测到异常（求救、颤抖）
    - 约会过程中安全检查超时
    - 用户触发 SOS 请求
    """

    name = "safety_guardian"
    version = "1.0.0"
    description = """
    AI 安全守护神，实时保护用户的人身安全

    能力:
    - 位置安全监测：检测是否到达危险区域
    - 语音异常检测：识别求救信号、颤抖、异常音量
    - 分级响应：根据风险等级自动采取相应措施
    - 紧急联系人：一键通知信任的人
    - 安全计划：个性化安全偏好设置
    """

    # 风险等级常量
    RISK_LOW = "low"
    RISK_MEDIUM = "medium"
    RISK_HIGH = "high"
    RISK_CRITICAL = "critical"

    # 风险阈值
    RISK_THRESHOLDS = {
        RISK_LOW: 0.3,
        RISK_MEDIUM: 0.6,
        RISK_HIGH: 0.8,
        RISK_CRITICAL: 0.95
    }

    def get_input_schema(self) -> dict:
        """获取输入参数 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "会话 ID（约会/通话）"
                },
                "check_type": {
                    "type": "string",
                    "enum": ["location", "voice", "scheduled_checkin", "sos"],
                    "description": "安全检查类型"
                },
                "user_id": {
                    "type": "string",
                    "description": "用户 ID"
                },
                "location_data": {
                    "type": "object",
                    "properties": {
                        "latitude": {"type": "number"},
                        "longitude": {"type": "number"},
                        "address": {"type": "string"}
                    },
                    "description": "位置数据"
                },
                "audio_features": {
                    "type": "object",
                    "properties": {
                        "volume": {"type": "number"},
                        "speech_rate": {"type": "number"},
                        "tremor": {"type": "boolean"},
                        "keywords": {"type": "array", "items": {"type": "string"}}
                    },
                    "description": "语音特征数据"
                },
                "partner_user_id": {
                    "type": "string",
                    "description": "约会对象 ID"
                },
                "context": {
                    "type": "object",
                    "properties": {
                        "date_id": {"type": "string"},
                        "relationship_stage": {"type": "string"},
                        "meeting_type": {"type": "string"}  # first_date, regular, etc.
                    }
                }
            },
            "required": ["session_id", "check_type", "user_id"]
        }

    def get_output_schema(self) -> dict:
        """获取输出参数 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "ai_message": {"type": "string"},
                "safety_check_result": {
                    "type": "object",
                    "properties": {
                        "check_id": {"type": "string"},
                        "risk_level": {"type": "string"},
                        "risk_score": {"type": "number"},
                        "is_safe": {"type": "boolean"},
                        "anomalies": {"type": "array"},
                        "location_description": {"type": "string"}
                    }
                },
                "generative_ui": {
                    "type": "object",
                    "properties": {
                        "component_type": {"type": "string"},
                        "props": {"type": "object"}
                    }
                },
                "suggested_actions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "label": {"type": "string"},
                            "action_type": {"type": "string"},
                            "params": {"type": "object"}
                        }
                    }
                },
                "alert_triggered": {"type": "boolean"},
                "alert_level": {"type": "string"},
                "emergency_contacts_notified": {"type": "boolean"}
            },
            "required": ["success", "ai_message", "safety_check_result"]
        }

    async def execute(
        self,
        session_id: str,
        check_type: str,
        user_id: str,
        location_data: Optional[Dict[str, Any]] = None,
        audio_features: Optional[Dict[str, Any]] = None,
        partner_user_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> dict:
        """
        执行安全守护 Skill

        Args:
            session_id: 会话 ID
            check_type: 检查类型 (location, voice, scheduled_checkin, sos)
            user_id: 用户 ID
            location_data: 位置数据
            audio_features: 语音特征数据
            partner_user_id: 约会对象 ID
            context: 上下文信息
            **kwargs: 额外参数

        Returns:
            Skill 执行结果
        """
        logger.info(f"SafetyGuardianSkill: Executing for user={user_id}, session={session_id}, type={check_type}")

        start_time = datetime.now()

        # Step 1: 执行安全检查
        safety_result = await self._perform_safety_check(
            session_id=session_id,
            check_type=check_type,
            user_id=user_id,
            location_data=location_data,
            audio_features=audio_features,
            partner_user_id=partner_user_id
        )

        # Step 2: 评估风险等级
        risk_assessment = self._assess_risk(safety_result)

        # Step 3: 生成自然语言响应
        ai_message = self._generate_safety_message(safety_result, risk_assessment)

        # Step 4: 构建 Generative UI
        generative_ui = self._build_safety_ui(safety_result, risk_assessment)

        # Step 5: 生成建议操作
        suggested_actions = self._generate_actions(risk_assessment)

        # Step 6: 检查是否需要触发警报
        alert_info = self._check_alert_needed(risk_assessment)

        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        return {
            "success": True,
            "ai_message": ai_message,
            "safety_check_result": safety_result,
            "generative_ui": generative_ui,
            "suggested_actions": suggested_actions,
            "alert_triggered": alert_info.get("triggered", False),
            "alert_level": alert_info.get("level"),
            "emergency_contacts_notified": alert_info.get("contacts_notified", False),
            "skill_metadata": {
                "name": self.name,
                "version": self.version,
                "execution_time_ms": int(execution_time),
                "check_type": check_type,
                "risk_level": risk_assessment.get("level")
            }
        }

    async def _perform_safety_check(
        self,
        session_id: str,
        check_type: str,
        user_id: str,
        location_data: Optional[Dict] = None,
        audio_features: Optional[Dict] = None,
        partner_user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """执行安全检查"""
        from db.database import SessionLocal
        from services.p11_safety_service import safety_monitoring_service

        db = SessionLocal()
        result = {
            "check_id": None,
            "is_safe": True,
            "risk_level": self.RISK_LOW,
            "risk_score": 0,
            "anomalies": [],
            "location_description": ""
        }

        try:
            if check_type == "location" and location_data:
                # 位置安全检查
                lat = location_data.get("latitude", 0)
                lng = location_data.get("longitude", 0)

                check_result = safety_monitoring_service.check_location_safety(
                    user_id=user_id,
                    latitude=lat,
                    longitude=lng,
                    db_session_param=db
                )

                result["check_id"] = str(datetime.now().timestamp())
                result["is_safe"] = check_result.get("safe", True)
                result["risk_level"] = check_result.get("risk_level", self.RISK_LOW)
                result["risk_score"] = check_result.get("risk_score", 0)
                result["location_description"] = check_result.get("description", "")

            elif check_type == "voice" and audio_features:
                # 语音安全检查
                check_result = safety_monitoring_service.check_voice_safety(
                    user_id=user_id,
                    session_id=session_id,
                    audio_features=audio_features,
                    db_session_param=db
                )

                result["check_id"] = str(datetime.now().timestamp())
                result["is_safe"] = check_result.get("safe", True)
                result["risk_level"] = check_result.get("risk_level", self.RISK_LOW)
                result["anomalies"] = check_result.get("anomalies", [])

            elif check_type == "scheduled_checkin":
                # 定时签到检查
                result["check_id"] = str(datetime.now().timestamp())
                result["is_safe"] = True
                result["risk_level"] = self.RISK_LOW

            elif check_type == "sos":
                # SOS 紧急检查 - 直接最高风险
                result["check_id"] = str(datetime.now().timestamp())
                result["is_safe"] = False
                result["risk_level"] = self.RISK_CRITICAL
                result["risk_score"] = 1.0

            return result

        except Exception as e:
            logger.error(f"SafetyGuardianSkill: Safety check failed: {e}")
            return result
        finally:
            db.close()

    def _assess_risk(self, safety_result: Dict) -> Dict[str, Any]:
        """评估风险等级"""
        risk_level = safety_result.get("risk_level", self.RISK_LOW)
        risk_score = safety_result.get("risk_score", 0)
        anomalies = safety_result.get("anomalies", [])

        # 根据异常数量调整风险等级
        if len(anomalies) >= 3:
            risk_level = self.RISK_HIGH
        elif len(anomalies) >= 1:
            risk_level = max(risk_level, self.RISK_MEDIUM)

        # 计算综合风险评分
        anomaly_score = min(len(anomalies) / 5.0, 1.0)
        combined_score = max(risk_score, anomaly_score)

        return {
            "level": risk_level,
            "score": combined_score,
            "anomaly_count": len(anomalies),
            "requires_action": risk_level in [self.RISK_HIGH, self.RISK_CRITICAL],
            "requires_notification": risk_level == self.RISK_CRITICAL
        }

    def _generate_safety_message(self, safety_result: Dict, risk_assessment: Dict) -> str:
        """生成安全提示消息"""
        risk_level = risk_assessment.get("level", self.RISK_LOW)
        is_safe = safety_result.get("is_safe", True)
        location_desc = safety_result.get("location_description", "")
        anomaly_count = risk_assessment.get("anomaly_count", 0)

        if is_safe and risk_level == self.RISK_LOW:
            message = "当前环境安全，请继续享受约会~\n"
            if location_desc:
                message += f"位置：{location_desc}"
        elif risk_level == self.RISK_MEDIUM:
            message = "检测到一些异常情况，请保持警惕。\n"
            if anomaly_count > 0:
                message += f"检测到{anomaly_count}项异常：{', '.join(safety_result.get('anomalies', [])[:3])}\n"
            message += "\n建议：\n- 分享行程给信任的人\n- 保持手机畅通\n- 选择人多的地方"
        elif risk_level == self.RISK_HIGH:
            message = "⚠️ 检测到较高安全风险！\n"
            message += "\n请立即采取以下措施：\n"
            message += "- 尽快离开当前位置\n"
            message += "- 联系紧急联系人\n"
            message += "- 必要时拨打 110"
        elif risk_level == self.RISK_CRITICAL:
            message = "🚨 紧急警报！检测到严重安全威胁！\n\n"
            message += "请立即：\n"
            message += "1. 拨打 110 报警\n"
            message += "2. 联系紧急联系人\n"
            message += "3. 尽快前往安全地点\n\n"
            message += "系统已通知您的紧急联系人！"
        else:
            message = "安全检查完成。"

        return message

    def _build_safety_ui(self, safety_result: Dict, risk_assessment: Dict) -> Dict[str, Any]:
        """构建安全 UI"""
        risk_level = risk_assessment.get("level", self.RISK_LOW)
        risk_score = risk_assessment.get("score", 0)

        # 根据风险等级选择 UI 类型
        if risk_level == self.RISK_LOW:
            return {
                "component_type": "safety_status",
                "props": {
                    "status": "safe",
                    "icon": "shield-check",
                    "message": "环境安全",
                    "risk_score": risk_score
                }
            }
        elif risk_level == self.RISK_MEDIUM:
            return {
                "component_type": "safety_alert",
                "props": {
                    "status": "caution",
                    "icon": "shield-exclamation",
                    "message": "保持警惕",
                    "risk_score": risk_score,
                    "anomalies": safety_result.get("anomalies", [])
                }
            }
        elif risk_level == self.RISK_HIGH:
            return {
                "component_type": "safety_alert",
                "props": {
                    "status": "warning",
                    "icon": "shield-warning",
                    "message": "高风险环境",
                    "risk_score": risk_score,
                    "anomalies": safety_result.get("anomalies", []),
                    "show_emergency_contacts": True
                }
            }
        else:  # CRITICAL
            return {
                "component_type": "safety_emergency",
                "props": {
                    "status": "critical",
                    "icon": "alert-circle",
                    "message": "紧急危险",
                    "risk_score": risk_score,
                    "show_sos_button": True,
                    "show_emergency_contacts": True,
                    "auto_dial_110": True
                }
            }

    def _generate_actions(self, risk_assessment: Dict) -> List[Dict[str, Any]]:
        """生成建议操作"""
        actions = []
        risk_level = risk_assessment.get("level", self.RISK_LOW)
        requires_action = risk_assessment.get("requires_action", False)
        requires_notification = risk_assessment.get("requires_notification", False)

        if risk_level == self.RISK_LOW:
            actions.append({
                "label": "分享行程",
                "action_type": "share_location",
                "params": {}
            })
            actions.append({
                "label": "设置定时签到",
                "action_type": "schedule_checkin",
                "params": {"interval_minutes": 30}
            })

        elif risk_level == self.RISK_MEDIUM:
            actions.append({
                "label": "通知信任的人",
                "action_type": "notify_contact",
                "params": {}
            })
            actions.append({
                "label": "查看安全建议",
                "action_type": "view_safety_tips",
                "params": {}
            })

        elif risk_level == self.RISK_HIGH:
            actions.append({
                "label": "拨打紧急联系人",
                "action_type": "call_emergency_contact",
                "params": {}
            })
            actions.append({
                "label": "发送位置",
                "action_type": "send_location",
                "params": {}
            })

        elif risk_level == self.RISK_CRITICAL:
            actions.append({
                "label": "拨打 110",
                "action_type": "dial_110",
                "params": {}
            })
            actions.append({
                "label": "SOS 警报",
                "action_type": "send_sos",
                "params": {}
            })
            if requires_notification:
                actions.append({
                    "label": "通知所有紧急联系人",
                    "action_type": "notify_all_contacts",
                    "params": {}
                })

        return actions

    def _check_alert_needed(self, risk_assessment: Dict) -> Dict[str, Any]:
        """检查是否需要触发警报"""
        risk_level = risk_assessment.get("level", self.RISK_LOW)
        requires_notification = risk_assessment.get("requires_notification", False)

        if risk_level == self.RISK_CRITICAL:
            return {
                "triggered": True,
                "level": "critical",
                "contacts_notified": requires_notification
            }
        elif risk_level == self.RISK_HIGH:
            return {
                "triggered": True,
                "level": "high",
                "contacts_notified": False
            }

        return {"triggered": False, "level": None}

    async def trigger_emergency(
        self,
        user_id: str,
        emergency_type: str = "general",
        location_data: Optional[Dict[str, Any]] = None,
        note: Optional[str] = None,
        **kwargs
    ) -> dict:
        """
        触发紧急求助

        Args:
            user_id: 用户 ID
            emergency_type: 紧急类型 (general, medical, danger, harassment)
            location_data: 位置数据
            note: 备注说明
            **kwargs: 额外参数

        Returns:
            紧急求助结果
        """
        logger.info(f"SafetyGuardianSkill: Emergency triggered for user={user_id}, type={emergency_type}")

        from services.p11_safety_service import safety_monitoring_service
        from db.database import SessionLocal

        db = SessionLocal()
        try:
            # 调用安全服务的紧急求助方法
            result = safety_monitoring_service.trigger_emergency(
                user_id=user_id,
                session_id=kwargs.get("session_id"),
                location_data=location_data,
                emergency_type=emergency_type,
                note=note,
                db_session_param=db
            )

            # 生成 AI 消息
            ai_message = self._generate_emergency_message(result, emergency_type)

            # 构建紧急 UI
            generative_ui = self._build_emergency_ui(result)

            # 生成建议操作
            suggested_actions = self._generate_emergency_actions(result)

            return {
                "success": True,
                "ai_message": ai_message,
                "emergency_data": result,
                "generative_ui": generative_ui,
                "suggested_actions": suggested_actions,
                "skill_metadata": {
                    "name": self.name,
                    "version": self.version,
                    "emergency_type": emergency_type
                }
            }

        except Exception as e:
            logger.error(f"SafetyGuardianSkill: Emergency trigger failed: {e}")
            return {
                "success": False,
                "ai_message": "紧急求助失败，请直接拨打 110",
                "error": str(e)
            }
        finally:
            db.close()

    async def notify_emergency_contact(
        self,
        user_id: str,
        contact_index: int = 0,
        session_id: Optional[str] = None,
        message: Optional[str] = None,
        location_data: Optional[Dict[str, Any]] = None,
        share_location: bool = True,
        **kwargs
    ) -> dict:
        """
        通知紧急联系人

        Args:
            user_id: 用户 ID
            contact_index: 联系人索引
            session_id: 会话 ID
            message: 自定义消息
            location_data: 位置数据
            share_location: 是否分享位置
            **kwargs: 额外参数

        Returns:
            通知结果
        """
        logger.info(f"SafetyGuardianSkill: Notifying emergency contact for user={user_id}")

        from services.p11_safety_service import safety_monitoring_service
        from db.database import SessionLocal

        db = SessionLocal()
        try:
            result = safety_monitoring_service.notify_emergency_contact(
                user_id=user_id,
                session_id=session_id,
                contact_index=contact_index,
                custom_message=message,
                location_data=location_data if share_location else None,
                db_session_param=db
            )

            ai_message = f"已通知您的紧急联系人{result.get('contact_name', '')}，{result.get('message', '')}"

            return {
                "success": True,
                "ai_message": ai_message,
                "notification_data": result,
                "skill_metadata": {
                    "name": self.name,
                    "version": self.version,
                    "contact_notified": result.get('contact_name', '')
                }
            }

        except Exception as e:
            logger.error(f"SafetyGuardianSkill: Notify contact failed: {e}")
            return {
                "success": False,
                "ai_message": "通知失败，请重试或直接联系紧急联系人",
                "error": str(e)
            }
        finally:
            db.close()

    def _generate_emergency_message(self, result: Dict, emergency_type: str) -> str:
        """生成紧急求助 AI 消息"""
        alert_level = result.get("alert_level", "unknown")
        contacts_notified = result.get("contacts_notified", 0)

        type_labels = {
            "general": "一般紧急",
            "medical": "医疗急救",
            "danger": "人身危险",
            "harassment": "骚扰威胁"
        }

        message = f"🚨 紧急求助已触发（{type_labels.get(emergency_type, emergency_type)}）\n\n"
        message += f"警报级别：{alert_level.upper()}\n"
        message += f"已通知{contacts_notified}位紧急联系人\n\n"
        message += "请保持冷静，等待救援人员到达。"

        return message

    def _build_emergency_ui(self, result: Dict) -> Dict[str, Any]:
        """构建紧急 UI"""
        return {
            "component_type": "emergency_panel",
            "props": {
                "alert_level": result.get("alert_level", "unknown"),
                "emergency_id": result.get("emergency_id", ""),
                "contacts_notified": result.get("contacts_notified", 0),
                "show_countdown": True,
                "show_location": True,
                "emergency_status": result.get("status", "active")
            }
        }

    def _generate_emergency_actions(self, result: Dict) -> List[Dict[str, Any]]:
        """生成紧急建议操作"""
        actions = [
            {
                "label": "拨打 110",
                "action_type": "dial_110",
                "params": {}
            },
            {
                "label": "分享实时位置",
                "action_type": "share_live_location",
                "params": {}
            },
            {
                "label": "联系所有紧急联系人",
                "action_type": "notify_all_contacts",
                "params": {}
            }
        ]

        if result.get("status") == "active":
            actions.append({
                "label": "取消警报",
                "action_type": "cancel_emergency",
                "params": {"emergency_id": result.get("emergency_id")}
            })

        return actions

    async def autonomous_trigger(
        self,
        user_id: str,
        session_id: str,
        trigger_type: str,
        context: Optional[Dict] = None
    ) -> dict:
        """
        自主触发安全检查

        Args:
            user_id: 用户 ID
            session_id: 会话 ID
            trigger_type: 触发类型 (location_change, checkin_timeout, anomaly_detected)
            context: 上下文信息

        Returns:
            触发结果
        """
        logger.info(f"SafetyGuardianSkill: Autonomous trigger for user={user_id}, type={trigger_type}")

        # 检查触发条件
        if trigger_type == "location_change":
            # 用户位置大幅变化
            pass
        elif trigger_type == "checkin_timeout":
            # 定时签到超时
            pass
        elif trigger_type == "anomaly_detected":
            # 检测到异常
            pass
        elif trigger_type == "sos":
            # 用户触发 SOS
            return await self.execute(
                session_id=session_id,
                check_type="sos",
                user_id=user_id,
                context=context
            )

        # 执行检查
        result = await self.execute(
            session_id=session_id,
            check_type="location",
            user_id=user_id,
            context=context
        )

        if result.get("alert_triggered"):
            return {
                "triggered": True,
                "result": result,
                "should_push": True,
                "alert_level": result.get("alert_level")
            }

        return {"triggered": False, "result": result}


# 全局 Skill 实例
_safety_guardian_skill_instance: Optional[SafetyGuardianSkill] = None


def get_safety_guardian_skill() -> SafetyGuardianSkill:
    """获取安全守护 Skill 单例实例"""
    global _safety_guardian_skill_instance
    if _safety_guardian_skill_instance is None:
        _safety_guardian_skill_instance = SafetyGuardianSkill()
    return _safety_guardian_skill_instance
