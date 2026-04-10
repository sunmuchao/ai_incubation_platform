"""
AI 行为信用分服务

P0 功能：基于用户行为建立信用评分体系，用于：
1. 匹配权重调节
2. 敏感功能限制
3. AI 提醒其他用户
4. 申诉机制

信用等级：
- S (90-100): 极可信用户
- A (75-89): 高度可信
- B (60-74): 普通用户
- C (40-59): 需谨慎
- D (0-39): 高风险
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc
import json

from db.database import SessionLocal
from utils.db_session_manager import db_session, db_session_readonly, optional_db_session
from models.p20_models import BehaviorCreditDB, BehaviorCreditEventDB
from utils.logger import logger


class BehaviorCreditService:
    """行为信用分服务"""

    # 负面行为扣分配置
    NEGATIVE_EVENTS = {
        "harassment_reported": -50,     # 被举报骚扰
        "fake_info_detected": -30,      # 虚假信息
        "aggressive_language": -20,     # 攻击性语言
        "photo_rejected": -10,          # 照片审核不通过
        "ghosting_after_contact": -5,   # 交换联系方式后消失
        "spam_behavior": -15,           # 骚扰行为
        "inappropriate_content": -25,   # 不当内容
    }

    # 正面行为加分配置
    POSITIVE_EVENTS = {
        "complete_profile": +10,        # 完善资料
        "verified_badge": +20,          # 获得认证标识
        "positive_feedback": +15,       # 获得好评
        "active_response": +5,          # 及时回复
        "successful_date": +25,         # 成功约会
        "helpful_behavior": +10,        # 帮助他人
    }

    # 信用等级定义
    CREDIT_LEVELS = {
        "S": (90, 100, "极可信用户"),
        "A": (75, 89, "高度可信"),
        "B": (60, 74, "普通用户"),
        "C": (40, 59, "需谨慎"),
        "D": (0, 39, "高风险"),
    }

    # 限制措施配置
    RESTRICTIONS_BY_LEVEL = {
        "S": [],
        "A": [],
        "B": [],
        "C": ["no_contact_exchange"],  # 禁止主动交换联系方式
        "D": ["no_chat_initiate", "reduced_recommendations"],  # 禁止发起聊天、降低推荐优先级
    }

    def __init__(self, db: Optional[Session] = None):
        self._db: Optional[Session] = db
        self._should_close_db: bool = db is None

    def _get_db(self) -> Session:
        """
        获取数据库会话

        注意：推荐使用 db_session() 上下文管理器代替延迟创建会话模式。

        迁移示例:
            # 旧方式
            service = BehaviorCreditService()
            credit = service.get_or_create_credit(user_id)
            service.close()

            # 新方式（推荐）
            with db_session() as db:
                service = BehaviorCreditService(db=db)
                credit = service.get_or_create_credit(user_id)
        """
        if self._db is None:
            self._db = SessionLocal()
            self._should_close_db = True
        return self._db

    def close(self):
        """关闭数据库会话（仅关闭自己创建的）"""
        if self._should_close_db and self._db is not None:
            try:
                self._db.commit()
                self._db.close()
            except Exception as e:
                logger.error(f"Error closing database session: {e}")
            finally:
                self._db = None
                self._should_close_db = False

    def get_or_create_credit(self, user_id: str) -> BehaviorCreditDB:
        """获取或创建用户信用记录"""
        db = self._get_db()
        credit = db.query(BehaviorCreditDB).filter(
            BehaviorCreditDB.user_id == user_id
        ).first()

        if not credit:
            credit = BehaviorCreditDB(
                user_id=user_id,
                credit_score=100,
                credit_level="B",
                base_score=100,
                positive_score=0,
                negative_score=0
            )
            db.add(credit)
            db.commit()
            db.refresh(credit)
            logger.info(f"Created behavior credit for user {user_id}")

        return credit

    def record_event(
        self,
        user_id: str,
        event_type: str,
        description: str,
        source: str = "system",
        evidence: Optional[Dict] = None,
        related_user_id: Optional[str] = None,
        related_message_id: Optional[str] = None,
        related_report_id: Optional[str] = None
    ) -> Tuple[bool, str, int]:
        """
        记录行为事件并更新信用分

        Args:
            user_id: 用户 ID
            event_type: 事件类型
            description: 事件描述
            source: 事件来源
            evidence: 证据信息
            related_user_id: 相关用户 ID
            related_message_id: 相关消息 ID
            related_report_id: 相关举报 ID

        Returns:
            (success, message, score_change)
        """
        db = self._get_db()

        # 确定分数变化
        score_change = 0
        if event_type in self.NEGATIVE_EVENTS:
            score_change = self.NEGATIVE_EVENTS[event_type]
        elif event_type in self.POSITIVE_EVENTS:
            score_change = self.POSITIVE_EVENTS[event_type]
        else:
            logger.warning(f"Unknown event type: {event_type}")
            return False, f"未知事件类型：{event_type}", 0

        try:
            # 获取当前信用
            credit = self.get_or_create_credit(user_id)
            score_before = credit.credit_score

            # 更新分数
            new_score = max(0, min(100, score_before + score_change))

            if score_change > 0:
                credit.positive_score += score_change
                credit.total_positive_events += 1
            else:
                credit.negative_score += abs(score_change)
                credit.total_negative_events += 1

            credit.credit_score = new_score
            credit.credit_level = self._calculate_level(new_score)

            # 更新限制
            credit.restrictions = json.dumps(
                self.RESTRICTIONS_BY_LEVEL.get(credit.credit_level, [])
            )

            # 创建事件记录
            event = BehaviorCreditEventDB(
                user_id=user_id,
                event_type=event_type,
                score_change=score_change,
                score_before=score_before,
                score_after=new_score,
                description=description,
                evidence=json.dumps(evidence) if evidence else "",
                source=source,
                related_user_id=related_user_id,
                related_message_id=related_message_id,
                related_report_id=related_report_id,
                status="processed",
                processed_by="ai" if source == "ai_detection" else "system"
            )
            db.add(event)

            # 记录等级变化
            if credit.credit_level != self._get_previous_level(credit):
                level_history = json.loads(credit.level_history or "[]")
                level_history.append({
                    "from": self._get_previous_level(credit),
                    "to": credit.credit_level,
                    "at": datetime.now().isoformat()
                })
                credit.level_history = json.dumps(level_history)

            db.commit()
            db.refresh(credit)

            logger.info(
                f"Behavior event recorded: user={user_id}, "
                f"event={event_type}, score_change={score_change}, "
                f"new_score={new_score}, level={credit.credit_level}"
            )

            return True, f"已记录行为事件，信用分{'+' if score_change > 0 else ''}{score_change}", score_change

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to record behavior event: {e}")
            return False, str(e), 0

    def _calculate_level(self, score: int) -> str:
        """根据分数计算信用等级"""
        for level, (min_score, max_score, _) in self.CREDIT_LEVELS.items():
            if min_score <= score <= max_score:
                return level
        return "D"

    def _get_previous_level(self, credit: BehaviorCreditDB) -> str:
        """获取之前的信用等级（简化实现）"""
        return credit.credit_level

    def get_credit_info(self, user_id: str) -> Dict:
        """
        获取用户信用信息

        Returns:
            信用信息字典
        """
        credit = self.get_or_create_credit(user_id)

        return {
            "user_id": user_id,
            "credit_score": credit.credit_score,
            "credit_level": credit.credit_level,
            "level_description": self.CREDIT_LEVELS.get(credit.credit_level, ("", "", ""))[2],
            "base_score": credit.base_score,
            "positive_score": credit.positive_score,
            "negative_score": credit.negative_score,
            "total_positive_events": credit.total_positive_events,
            "total_negative_events": credit.total_negative_events,
            "restrictions": json.loads(credit.restrictions or "[]"),
            "last_calculated_at": credit.last_calculated_at.isoformat() if credit.last_calculated_at else None
        }

    def get_credit_history(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict]:
        """
        获取信用记录历史

        Args:
            user_id: 用户 ID
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            事件历史列表
        """
        db = self._get_db()
        events = db.query(BehaviorCreditEventDB).filter(
            BehaviorCreditEventDB.user_id == user_id
        ).order_by(
            desc(BehaviorCreditEventDB.created_at)
        ).offset(offset).limit(limit).all()

        return [
            {
                "id": event.id,
                "event_type": event.event_type,
                "score_change": event.score_change,
                "score_before": event.score_before,
                "score_after": event.score_after,
                "description": event.description,
                "source": event.source,
                "status": event.status,
                "created_at": event.created_at.isoformat() if event.created_at else None,
                "appeal_result": event.appeal_result
            }
            for event in events
        ]

    def submit_appeal(
        self,
        event_id: str,
        user_id: str,
        appeal_reason: str
    ) -> Tuple[bool, str]:
        """
        提交申诉

        Args:
            event_id: 事件 ID
            user_id: 用户 ID
            appeal_reason: 申诉理由

        Returns:
            (success, message)
        """
        db = self._get_db()

        event = db.query(BehaviorCreditEventDB).filter(
            BehaviorCreditEventDB.id == event_id,
            BehaviorCreditEventDB.user_id == user_id
        ).first()

        if not event:
            return False, "事件不存在"

        if event.status == "overturned":
            return False, "该事件已被推翻"

        event.appeal_reason = appeal_reason
        event.appeal_result = "pending"
        event.status = "appealed"
        event.appeal_processed_at = datetime.now()

        db.commit()

        logger.info(f"Appeal submitted: event_id={event_id}, user_id={user_id}")
        return True, "申诉已提交，等待审核"

    def process_appeal(
        self,
        event_id: str,
        reviewer_id: str,
        approve: bool,
        reason: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        处理申诉

        Args:
            event_id: 事件 ID
            reviewer_id: 审核员 ID
            approve: 是否批准
            reason: 审核理由

        Returns:
            (success, message)
        """
        db = self._get_db()

        event = db.query(BehaviorCreditEventDB).filter(
            BehaviorCreditEventDB.id == event_id
        ).first()

        if not event:
            return False, "事件不存在"

        try:
            if approve:
                # 批准申诉，恢复分数
                credit = self.get_or_create_credit(event.user_id)
                credit.credit_score = event.score_before
                credit.credit_level = self._calculate_level(credit.credit_score)

                if event.score_change > 0:
                    credit.positive_score -= event.score_change
                    credit.total_positive_events -= 1
                else:
                    credit.negative_score -= abs(event.score_change)
                    credit.total_negative_events -= 1

                event.appeal_result = "approved"
                event.status = "overturned"
                logger.info(f"Appeal approved: event_id={event_id}, user_id={event.user_id}")
            else:
                event.appeal_result = "rejected"
                event.status = "processed"
                logger.info(f"Appeal rejected: event_id={event_id}")

            event.appeal_processed_at = datetime.now()
            event.reviewer_id = reviewer_id
            db.commit()

            return True, "申诉处理完成"

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to process appeal: {e}")
            return False, str(e)

    def check_restrictions(self, user_id: str) -> Dict:
        """
        检查用户限制

        Returns:
            限制信息
        """
        credit = self.get_or_create_credit(user_id)
        restrictions = json.loads(credit.restrictions or "[]")

        return {
            "user_id": user_id,
            "credit_level": credit.credit_level,
            "restrictions": restrictions,
            "can_initiate_chat": "no_chat_initiate" not in restrictions,
            "can_exchange_contact": "no_contact_exchange" not in restrictions,
            "has_reduced_recommendations": "reduced_recommendations" in restrictions
        }

    def get_credit_stats(self) -> Dict:
        """获取信用统计"""
        db = self._get_db()

        total_users = db.query(BehaviorCreditDB).count()
        level_distribution = db.query(
            BehaviorCreditDB.credit_level,
            db.func.count(BehaviorCreditDB.id)
        ).group_by(BehaviorCreditDB.credit_level).all()

        return {
            "total_users": total_users,
            "level_distribution": dict(level_distribution),
            "avg_score": db.query(
                db.func.avg(BehaviorCreditDB.credit_score)
            ).scalar() or 0
        }


# 全局单例
behavior_credit_service = BehaviorCreditService()
