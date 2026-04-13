"""
置信度实时更新机制

功能：
- 事件驱动触发器
- 行为模式变化检测器
- 任务队列集成
"""

from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import json
import asyncio
from collections import defaultdict

from utils.logger import logger
from utils.db_session_manager import db_session
from db.models import UserDB, BehaviorEventDB, ChatMessageDB


# ============================================
# 置信度更新触发规则
# ============================================

UPDATE_TRIGGERS = {
    # 高优先级：立即更新（影响重大）
    "identity_verified": {
        "priority": "high",
        "delay": 0,
        "description": "完成实名认证",
    },
    "identity_verification_failed": {
        "priority": "high",
        "delay": 0,
        "description": "实名认证失败",
    },
    "badge_earned": {
        "priority": "high",
        "delay": 0,
        "description": "获得信任徽章",
    },
    "badge_lost": {
        "priority": "high",
        "delay": 0,
        "description": "失去信任徽章",
    },
    "report_received": {
        "priority": "high",
        "delay": 0,
        "description": "收到用户举报",
    },
    "report_confirmed": {
        "priority": "high",
        "delay": 0,
        "description": "举报被确认",
    },
    "profile_major_update": {
        "priority": "high",
        "delay": 0,
        "description": "重要画像信息更新（年龄/学历/职业/收入）",
    },
    "user_banned": {
        "priority": "high",
        "delay": 0,
        "description": "用户被封禁",
    },

    # 中优先级：延迟更新（变化有影响但需等待稳定）
    "profile_minor_update": {
        "priority": "medium",
        "delay": 60,  # 1分钟后
        "description": "次要画像信息更新",
    },
    "behavior_pattern_change": {
        "priority": "medium",
        "delay": 300,  # 5分钟后
        "description": "行为模式变化",
    },
    "feedback_received": {
        "priority": "medium",
        "delay": 0,
        "description": "收到用户反馈",
    },
    "match_completed": {
        "priority": "medium",
        "delay": 60,
        "description": "完成一次匹配",
    },
    "date_completed": {
        "priority": "medium",
        "delay": 120,
        "description": "完成约会",
    },
    "positive_interaction": {
        "priority": "medium",
        "delay": 300,
        "description": "积极互动（好评/感谢）",
    },
    "negative_interaction": {
        "priority": "medium",
        "delay": 0,
        "description": "负面互动（投诉/不满）",
    },

    # 低优先级：批量更新（轻微变化）
    "daily_active": {
        "priority": "low",
        "delay": 3600,  # 1小时后
        "description": "每日活跃",
    },
    "chat_message_sent": {
        "priority": "low",
        "delay": 600,  # 10分钟后
        "description": "发送聊天消息",
    },
    "profile_view": {
        "priority": "low",
        "delay": 1800,  # 30分钟后
        "description": "浏览他人资料",
    },
    "like_received": {
        "priority": "low",
        "delay": 600,
        "description": "收到喜欢",
    },
    "pass_received": {
        "priority": "low",
        "delay": 600,
        "description": "收到跳过",
    },
}


# ============================================
# 置信度更新触发器
# ============================================

class ConfidenceUpdateTrigger:
    """置信度实时更新触发器"""

    def __init__(self):
        self._pending_updates: Dict[str, List[Dict]] = defaultdict(list)
        self._update_callbacks: List[Callable] = []

    def register_callback(self, callback: Callable):
        """注册更新完成回调"""
        self._update_callbacks.append(callback)

    async def on_event(
        self,
        event_type: str,
        user_id: str,
        event_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        处理置信度更新事件

        Args:
            event_type: 事件类型
            user_id: 用户ID
            event_data: 事件数据

        Returns:
            处理结果
        """
        trigger_config = UPDATE_TRIGGERS.get(event_type)

        if not trigger_config:
            logger.warning(f"未知的事件类型: {event_type}")
            return {"handled": False, "reason": "unknown_event_type"}

        priority = trigger_config["priority"]
        delay = trigger_config["delay"]

        logger.info(f"置信度更新事件: {event_type} for user {user_id}, priority={priority}, delay={delay}s")

        if priority == "high":
            # 立即更新
            result = await self._immediate_update(user_id, event_type, event_data)

        elif priority == "medium":
            # 延迟更新（放入队列）
            await self._schedule_delayed_update(user_id, event_type, event_data, delay)
            result = {"handled": True, "mode": "delayed", "delay": delay}

        else:
            # 批量更新标记
            self._mark_for_batch_update(user_id, event_type, event_data)
            result = {"handled": True, "mode": "batch"}

        return result

    async def _immediate_update(
        self,
        user_id: str,
        event_type: str,
        event_data: Dict
    ) -> Dict[str, Any]:
        """立即执行置信度更新"""
        from services.profile_confidence_service import profile_confidence_service

        try:
            # 执行置信度评估
            result = profile_confidence_service.evaluate_user_confidence(
                user_id=user_id,
                trigger_source=f"event_{event_type}"
            )

            # 检查是否有显著变化
            confidence_change = result.get("overall_confidence", 0.3) - result.get("confidence_before", 0.3)

            if abs(confidence_change) > 0.1:
                # 置信度显著变化，发送通知
                await self._notify_confidence_change(user_id, result, event_type)

            # 执行回调
            for callback in self._update_callbacks:
                try:
                    await callback(user_id, result)
                except Exception as e:
                    logger.warning(f"回调执行失败: {e}")

            return {
                "handled": True,
                "mode": "immediate",
                "confidence": result.get("overall_confidence"),
                "change": confidence_change,
            }

        except Exception as e:
            logger.error(f"立即更新失败: {e}")
            return {"handled": False, "error": str(e)}

    async def _schedule_delayed_update(
        self,
        user_id: str,
        event_type: str,
        event_data: Dict,
        delay: int
    ):
        """调度延迟更新任务"""
        # 添加到待更新队列
        update_task = {
            "user_id": user_id,
            "event_type": event_type,
            "event_data": event_data,
            "scheduled_at": datetime.now() + timedelta(seconds=delay),
            "added_at": datetime.now(),
        }

        self._pending_updates[user_id].append(update_task)

        # 简化实现：创建异步任务处理
        # 实际生产环境应使用任务队列（如 Redis Queue / Celery）
        asyncio.create_task(self._process_delayed_update(update_task))

        logger.info(f"延迟更新任务已调度: user={user_id}, delay={delay}s")

    async def _process_delayed_update(self, task: Dict):
        """处理延迟更新任务"""
        delay = (task["scheduled_at"] - datetime.now()).total_seconds()

        if delay > 0:
            await asyncio.sleep(delay)

        # 执行更新
        await self._immediate_update(
            task["user_id"],
            task["event_type"],
            task["event_data"]
        )

        # 从队列移除
        self._pending_updates[task["user_id"]] = [
            t for t in self._pending_updates[task["user_id"]]
            if t != task
        ]

    def _mark_for_batch_update(
        self,
        user_id: str,
        event_type: str,
        event_data: Dict
    ):
        """标记用户需要批量更新"""
        self._pending_updates[user_id].append({
            "user_id": user_id,
            "event_type": event_type,
            "event_data": event_data,
            "added_at": datetime.now(),
            "mode": "batch",
        })

    async def process_batch_updates(self) -> Dict[str, Any]:
        """批量处理待更新用户"""
        from services.profile_confidence_service import profile_confidence_service

        processed = 0
        failed = 0

        # 获取所有待更新用户
        users_to_update = list(self._pending_updates.keys())

        for user_id in users_to_update:
            try:
                # 合并该用户的所有待处理事件
                events = self._pending_updates[user_id]
                primary_event = events[-1] if events else None

                if primary_event:
                    result = profile_confidence_service.evaluate_user_confidence(
                        user_id=user_id,
                        trigger_source="batch_update"
                    )
                    processed += 1

                # 清空该用户的待更新队列
                self._pending_updates[user_id] = []

            except Exception as e:
                failed += 1
                logger.error(f"批量更新失败 user={user_id}: {e}")

        logger.info(f"批量更新完成: processed={processed}, failed={failed}")

        return {"processed": processed, "failed": failed}

    async def _notify_confidence_change(
        self,
        user_id: str,
        result: Dict,
        event_type: str
    ):
        """通知用户置信度变化"""
        # 简化实现：实际应发送推送通知
        # 这里仅记录日志
        confidence = result.get("overall_confidence", 0)
        level = result.get("confidence_level", "medium")

        logger.info(f"置信度显著变化通知: user={user_id}, confidence={confidence:.2f}, level={level}, trigger={event_type}")


# ============================================
# 行为模式变化检测器
# ============================================

class BehaviorPatternDetector:
    """检测用户行为模式的显著变化"""

    # 行为模式定义
    BEHAVIOR_PATTERNS = {
        "browse_preference": {
            "description": "浏览偏好（喜欢看什么类型的用户）",
            "change_threshold": 0.3,  # 30%以上变化视为显著
        },
        "active_time": {
            "description": "活跃时间分布",
            "change_threshold": 3,  # 时间偏移超过3小时
        },
        "interaction_style": {
            "description": "互动风格（主动/被动）",
            "change_threshold": 0.4,
        },
        "interest_expression": {
            "description": "兴趣表达方式",
            "change_threshold": 0.3,
        },
    }

    def detect_pattern_changes(
        self,
        user_id: str,
        db: Session,
        compare_days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        检测用户行为模式的变化

        Args:
            user_id: 用户ID
            db: 数据库会话
            compare_days: 对比周期（天）

        Returns:
            变化列表
        """
        changes = []

        # 获取两个周期的行为统计
        current_period_end = datetime.now()
        current_period_start = current_period_end - timedelta(days=compare_days)
        previous_period_end = current_period_start
        previous_period_start = previous_period_end - timedelta(days=compare_days)

        current_stats = self._get_behavior_stats(
            user_id, db, current_period_start, current_period_end
        )
        previous_stats = self._get_behavior_stats(
            user_id, db, previous_period_start, previous_period_end
        )

        # 对比浏览偏好变化
        browse_change = self._compare_browse_preference(current_stats, previous_stats)
        if browse_change["change_rate"] > self.BEHAVIOR_PATTERNS["browse_preference"]["change_threshold"]:
            changes.append({
                "pattern": "browse_preference",
                "severity": "medium",
                "detail": f"浏览偏好变化 {browse_change['change_rate']*100:.0f}%",
                "data": browse_change,
            })

        # 对比活跃时间变化
        time_change = self._compare_active_time(current_stats, previous_stats)
        if time_change["shift_hours"] > self.BEHAVIOR_PATTERNS["active_time"]["change_threshold"]:
            changes.append({
                "pattern": "active_time",
                "severity": "low",
                "detail": f"活跃时间偏移 {time_change['shift_hours']}小时",
                "data": time_change,
            })

        # 对比互动风格变化
        interaction_change = self._compare_interaction_style(current_stats, previous_stats)
        if interaction_change["change_rate"] > self.BEHAVIOR_PATTERNS["interaction_style"]["change_threshold"]:
            changes.append({
                "pattern": "interaction_style",
                "severity": "medium",
                "detail": f"互动风格变化",
                "data": interaction_change,
            })

        return changes

    def _get_behavior_stats(
        self,
        user_id: str,
        db: Session,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """获取指定时间段的行为统计"""
        stats = {
            "browse_targets": defaultdict(int),
            "active_hours": defaultdict(int),
            "initiated_interactions": 0,
            "received_interactions": 0,
            "interest_keywords": defaultdict(int),
        }

        # 获取浏览事件
        browse_events = db.query(BehaviorEventDB).filter(
            BehaviorEventDB.user_id == user_id,
            BehaviorEventDB.event_type == "profile_view",
            BehaviorEventDB.created_at >= start_time,
            BehaviorEventDB.created_at <= end_time
        ).all()

        for event in browse_events:
            # 统计活跃小时
            hour = event.created_at.hour
            stats["active_hours"][hour] += 1

            # 统计浏览目标特征
            if event.target_id:
                target_user = db.query(UserDB).filter(UserDB.id == event.target_id).first()
                if target_user:
                    # 统计浏览的职业类型
                    if target_user.occupation:
                        stats["browse_targets"][f"occupation_{target_user.occupation}"] += 1

                    # 统计浏览的兴趣标签
                    try:
                        interests = json.loads(target_user.interests or "[]")
                    except:
                        interests = []
                    for interest in interests:
                        stats["interest_keywords"][interest] += 1

        # 获取互动事件
        interactions = db.query(BehaviorEventDB).filter(
            BehaviorEventDB.user_id == user_id,
            BehaviorEventDB.event_type.in_(["like", "pass", "super_like", "message_sent"]),
            BehaviorEventDB.created_at >= start_time,
            BehaviorEventDB.created_at <= end_time
        ).all()

        for interaction in interactions:
            if interaction.event_type == "message_sent":
                stats["initiated_interactions"] += 1
            else:
                stats["initiated_interactions"] += 1

        # 获取收到的互动
        received = db.query(BehaviorEventDB).filter(
            BehaviorEventDB.target_id == user_id,
            BehaviorEventDB.event_type.in_(["like", "pass", "super_like"]),
            BehaviorEventDB.created_at >= start_time,
            BehaviorEventDB.created_at <= end_time
        ).all()

        stats["received_interactions"] = len(received)

        return stats

    def _compare_browse_preference(
        self,
        current: Dict,
        previous: Dict
    ) -> Dict[str, Any]:
        """对比浏览偏好"""
        current_targets = current["browse_targets"]
        previous_targets = previous["browse_targets"]

        if not current_targets or not previous_targets:
            return {"change_rate": 0, "note": "数据不足"}

        # 计算偏好分布差异
        all_keys = set(current_targets.keys()) | set(previous_targets.keys())

        total_diff = 0
        for key in all_keys:
            current_val = current_targets.get(key, 0)
            previous_val = previous_targets.get(key, 0)

            current_total = sum(current_targets.values())
            previous_total = sum(previous_targets.values())

            current_ratio = current_val / current_total if current_total > 0 else 0
            previous_ratio = previous_val / previous_total if previous_total > 0 else 0

            diff = abs(current_ratio - previous_ratio)
            total_diff += diff

        change_rate = total_diff / 2  # 归一化

        return {
            "change_rate": change_rate,
            "current_top": sorted(current_targets, key=current_targets.get, reverse=True)[:3],
            "previous_top": sorted(previous_targets, key=previous_targets.get, reverse=True)[:3],
        }

    def _compare_active_time(
        self,
        current: Dict,
        previous: Dict
    ) -> Dict[str, Any]:
        """对比活跃时间分布"""
        current_hours = current["active_hours"]
        previous_hours = previous["active_hours"]

        if not current_hours or not previous_hours:
            return {"shift_hours": 0, "note": "数据不足"}

        # 计算主要活跃时间
        def get_peak_hour(hours_dict):
            if not hours_dict:
                return 12
            return max(hours_dict, key=hours_dict.get)

        current_peak = get_peak_hour(current_hours)
        previous_peak = get_peak_hour(previous_hours)

        shift = abs(current_peak - previous_peak)

        return {
            "shift_hours": shift,
            "current_peak_hour": current_peak,
            "previous_peak_hour": previous_peak,
        }

    def _compare_interaction_style(
        self,
        current: Dict,
        previous: Dict
    ) -> Dict[str, Any]:
        """对比互动风格"""
        current_initiated = current["initiated_interactions"]
        current_received = current["received_interactions"]
        previous_initiated = previous["initiated_interactions"]
        previous_received = previous["received_interactions"]

        if current_initiated + current_received == 0 or previous_initiated + previous_received == 0:
            return {"change_rate": 0, "note": "数据不足"}

        # 计算主动性比例
        current_active_ratio = current_initiated / (current_initiated + current_received)
        previous_active_ratio = previous_initiated / (previous_initiated + previous_received)

        change = abs(current_active_ratio - previous_active_ratio)

        return {
            "change_rate": change,
            "current_active_ratio": current_active_ratio,
            "previous_active_ratio": previous_active_ratio,
            "trend": "more_active" if current_active_ratio > previous_active_ratio else "more_passive",
        }


# ============================================
# 定期评估调度器
# ============================================

class ConfidenceScheduler:
    """置信度定期评估调度器"""

    def __init__(self):
        self._running = False
        self._task = None

    async def start(self, interval_hours: int = 24):
        """启动定期评估"""
        self._running = True
        self._task = asyncio.create_task(self._run_periodic_evaluation(interval_hours))
        logger.info(f"置信度定期评估已启动，周期: {interval_hours}小时")

    async def stop(self):
        """停止定期评估"""
        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("置信度定期评估已停止")

    async def _run_periodic_evaluation(self, interval_hours: int):
        """执行定期评估"""
        from services.profile_confidence_service import profile_confidence_service

        while self._running:
            try:
                logger.info("开始定期置信度评估...")

                # 获取需要重新评估的用户
                with db_session() as db:
                    # 获取上次评估时间超过间隔的用户
                    from models.profile_confidence_models import ProfileConfidenceDetailDB

                    stale_users = db.query(ProfileConfidenceDetailDB).filter(
                        ProfileConfidenceDetailDB.last_evaluated_at < datetime.now() - timedelta(hours=interval_hours)
                    ).limit(100).all()

                    user_ids = [u.user_id for u in stale_users]

                # 执行评估
                for user_id in user_ids:
                    try:
                        profile_confidence_service.evaluate_user_confidence(
                            user_id=user_id,
                            trigger_source="periodic"
                        )
                    except Exception as e:
                        logger.warning(f"定期评估失败 user={user_id}: {e}")

                logger.info(f"定期评估完成: {len(user_ids)}个用户")

            except Exception as e:
                logger.error(f"定期评估任务失败: {e}")

            # 等待下一个周期
            await asyncio.sleep(interval_hours * 3600)


# ============================================
# 导出
# ============================================

# 全局实例
confidence_trigger = ConfidenceUpdateTrigger()
behavior_detector = BehaviorPatternDetector()
confidence_scheduler = ConfidenceScheduler()