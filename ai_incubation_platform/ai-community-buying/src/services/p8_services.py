"""
P8 阶段 - 智能风控/信用体系服务层

包含:
1. 信用服务 (CreditService)
2. 风控规则服务 (RiskRuleService)
3. 黑名单服务 (BlacklistService)
4. 订单风控服务 (OrderRiskService)
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
import json
import logging
import re

from models.p8_entities import (
    CreditScoreEntity, CreditScoreHistoryEntity, CreditFactorEntity,
    RiskRuleEntity, RiskEventEntity, BlacklistEntity, OrderRiskAssessmentEntity,
    CreditLevel, RiskLevel, BlacklistType, RiskRuleType, RiskRuleAction, OrderRiskDecision
)
from core.logging_config import get_logger

logger = get_logger("services.p8")


# ====================  信用服务  ====================

class CreditService:
    """信用体系服务"""

    def __init__(self, db: Session):
        self.db = db
        self.logger = logger
        self.request_id = ""
        self.user_id = ""
        # 信用因子权重 (默认配置)
        self.factor_weights = {
            "order_completion_rate": 0.25,  # 订单完成率
            "fulfillment_score": 0.20,       # 履约记录
            "activity_days": 0.10,           # 活跃天数
            "purchase_amount": 0.15,         # 消费金额
            "review_quality": 0.10,          # 评价质量
            "complaint_rate": 0.10,          # 投诉率 (反向)
            "refund_rate": 0.10,             # 退款率 (反向)
        }

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

    def get_credit_score(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户信用分"""
        credit_score = self.db.query(CreditScoreEntity).filter(
            CreditScoreEntity.user_id == user_id
        ).first()

        if not credit_score:
            return None

        return {
            "user_id": user_id,
            "credit_score": credit_score.credit_score,
            "credit_level": credit_score.credit_level.value,
            "factor_scores": json.loads(credit_score.factor_scores) if credit_score.factor_scores else {},
            "valid_from": credit_score.valid_from.isoformat() if credit_score.valid_from else None,
            "valid_until": credit_score.valid_until.isoformat() if credit_score.valid_until else None,
        }

    def get_or_create_credit(self, user_id: str) -> Dict[str, Any]:
        """获取或创建用户信用分"""
        credit_score = self.db.query(CreditScoreEntity).filter(
            CreditScoreEntity.user_id == user_id
        ).first()

        if not credit_score:
            # 创建默认信用分
            credit_score = CreditScoreEntity(
                id=f"credit_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                user_id=user_id,
                credit_score=500,
                credit_level=CreditLevel.FAIR,
                factor_scores=json.dumps({}),
            )
            self.db.add(credit_score)
            self.db.commit()

        return {
            "user_id": user_id,
            "credit_score": credit_score.credit_score,
            "credit_level": credit_score.credit_level.value,
        }

    def calculate_credit_score(self, user_id: str) -> int:
        """
        计算用户信用分

        基于多维度因子动态计算信用分:
        - order_completion_rate: 订单完成率 (0-100)
        - fulfillment_score: 履约记录 (0-100)
        - activity_days: 活跃天数 (归一化 0-100)
        - purchase_amount: 消费金额 (归一化 0-100)
        - review_quality: 评价质量 (0-100)
        - complaint_rate: 投诉率 (反向 0-100)
        - refund_rate: 退款率 (反向 0-100)
        """
        from models.entities import OrderEntity
        from models.p6_entities import SigninCalendarEntity

        # 1. 订单完成率 = 已完成订单数 / 总订单数 * 100
        total_orders = self.db.query(OrderEntity).filter(
            OrderEntity.user_id == user_id
        ).count()

        completed_orders = self.db.query(OrderEntity).filter(
            and_(
                OrderEntity.user_id == user_id,
                OrderEntity.status == "completed"
            )
        ).count()

        order_completion_rate = (completed_orders / total_orders * 100) if total_orders > 0 else 50

        # 2. 履约记录 (基于签到和自提情况)
        signin_days = self.db.query(func.count(SigninCalendarEntity.id)).filter(
            SigninCalendarEntity.user_id == user_id
        ).scalar() or 0
        fulfillment_score = min(100, signin_days * 2)  # 每个签到天 +2 分，上限 100

        # 3. 活跃天数 (归一化)
        activity_days = signin_days
        activity_score = min(100, activity_days)  # 最多 100 天

        # 4. 消费金额 (归一化，假设 10000 元为满分)
        total_amount = self.db.query(func.sum(OrderEntity.total_amount)).filter(
            and_(
                OrderEntity.user_id == user_id,
                OrderEntity.status == "completed"
            )
        ).scalar() or 0
        purchase_score = min(100, (total_amount / 10000) * 100)

        # 5. 评价质量 (简化：有评价的订单比例)
        orders_with_review = self.db.query(OrderEntity).filter(
            and_(
                OrderEntity.user_id == user_id,
                OrderEntity.review_comment.isnot(None),
                OrderEntity.review_comment != ""
            )
        ).count()
        review_quality = (orders_with_review / completed_orders * 100) if completed_orders > 0 else 50

        # 6. 投诉率 (反向，简化处理)
        complaint_count = 0  # 需要从投诉表获取
        complaint_rate = (complaint_count / total_orders * 100) if total_orders > 0 else 0
        complaint_score = 100 - complaint_rate

        # 7. 退款率 (反向)
        refund_count = self.db.query(OrderEntity).filter(
            and_(
                OrderEntity.user_id == user_id,
                OrderEntity.status == "refunded"
            )
        ).count()
        refund_rate = (refund_count / total_orders * 100) if total_orders > 0 else 0
        refund_score = 100 - refund_rate

        # 各因子得分
        factors = {
            "order_completion_rate": order_completion_rate,
            "fulfillment_score": fulfillment_score,
            "activity_days": activity_score,
            "purchase_amount": purchase_score,
            "review_quality": review_quality,
            "complaint_rate": complaint_score,
            "refund_rate": refund_score,
        }

        # 加权计算
        base_score = 500  # 基础分
        weighted_score = 0
        for factor_code, factor_value in factors.items():
            weight = self.factor_weights.get(factor_code, 0.1)
            weighted_score += factor_value * weight

        # 信用分 = 基础分 + 加权分 * 3.5 (将 0-100 映射到 0-350)
        final_score = int(base_score + weighted_score * 3.5)

        # 限制在 300-850 范围
        final_score = max(300, min(850, final_score))

        # 更新信用分
        self._update_credit_score(user_id, final_score, factors, "system_calculate")

        return final_score

    def _get_credit_level(self, score: int) -> CreditLevel:
        """根据信用分获取信用等级"""
        if score >= 750:
            return CreditLevel.EXCELLENT
        elif score >= 700:
            return CreditLevel.VERY_GOOD
        elif score >= 650:
            return CreditLevel.GOOD
        elif score >= 600:
            return CreditLevel.FAIR
        else:
            return CreditLevel.POOR

    def _update_credit_score(self, user_id: str, new_score: int, factors: Dict[str, float], reason: str):
        """更新用户信用分"""
        credit_score = self.db.query(CreditScoreEntity).filter(
            CreditScoreEntity.user_id == user_id
        ).first()

        if credit_score:
            old_score = credit_score.credit_score
            if old_score != new_score:
                # 记录历史
                history = CreditScoreHistoryEntity(
                    id=f"ch_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    user_id=user_id,
                    old_score=old_score,
                    new_score=new_score,
                    score_change=new_score - old_score,
                    change_reason=reason,
                    change_type="CALCULATE",
                    created_at=datetime.now(),
                )
                self.db.add(history)

                # 更新信用分
                credit_score.credit_score = new_score
                credit_score.credit_level = self._get_credit_level(new_score)
                credit_score.factor_scores = json.dumps(factors)
                credit_score.updated_at = datetime.now()

                self._log("info", f"Credit score updated for user {user_id}: {old_score} -> {new_score}",
                         extra={"old_score": old_score, "new_score": new_score})
        else:
            # 创建新记录
            credit_score = CreditScoreEntity(
                id=f"credit_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                user_id=user_id,
                credit_score=new_score,
                credit_level=self._get_credit_level(new_score),
                factor_scores=json.dumps(factors),
            )
            self.db.add(credit_score)

        self.db.commit()

    def update_credit_score(self, user_id: str, change: int, reason: str,
                            change_type: str = "MANUAL", related_order_id: str = None) -> int:
        """
        更新信用分 (增量更新)

        Args:
            user_id: 用户 ID
            change: 变化值 (正数增加，负数减少)
            reason: 变化原因
            change_type: 变化类型
            related_order_id: 关联订单 ID

        Returns:
            新的信用分
        """
        credit_score = self.db.query(CreditScoreEntity).filter(
            CreditScoreEntity.user_id == user_id
        ).first()

        if not credit_score:
            # 创建默认信用分
            credit_score = CreditScoreEntity(
                id=f"credit_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                user_id=user_id,
                credit_score=500,
                credit_level=CreditLevel.FAIR,
            )
            self.db.add(credit_score)
            self.db.flush()

        old_score = credit_score.credit_score
        new_score = max(300, min(850, old_score + change))

        # 记录历史
        history = CreditScoreHistoryEntity(
            id=f"ch_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            user_id=user_id,
            old_score=old_score,
            new_score=new_score,
            score_change=change,
            change_reason=reason,
            change_type=change_type,
            related_order_id=related_order_id,
        )
        self.db.add(history)

        # 更新信用分
        credit_score.credit_score = new_score
        credit_score.credit_level = self._get_credit_level(new_score)
        credit_score.updated_at = datetime.now()

        self.db.commit()

        self._log("info", f"Credit score updated for user {user_id}: {old_score} -> {new_score} ({change:+d})",
                 extra={"old_score": old_score, "new_score": new_score, "change": change})

        return new_score

    def get_credit_history(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """获取用户信用历史"""
        history_list = self.db.query(CreditScoreHistoryEntity).filter(
            CreditScoreHistoryEntity.user_id == user_id
        ).order_by(desc(CreditScoreHistoryEntity.created_at)).limit(limit).all()

        return [
            {
                "id": h.id,
                "old_score": h.old_score,
                "new_score": h.new_score,
                "score_change": h.score_change,
                "change_reason": h.change_reason,
                "change_type": h.change_type,
                "related_order_id": h.related_order_id,
                "created_at": h.created_at.isoformat() if h.created_at else None,
            }
            for h in history_list
        ]

    def get_credit_factors(self) -> List[Dict[str, Any]]:
        """获取信用因子配置"""
        factors = self.db.query(CreditFactorEntity).filter(
            CreditFactorEntity.is_active == True
        ).all()

        if not factors:
            # 返回默认因子
            return [
                {"factor_code": code, "factor_name": code, "weight": float(weight)}
                for code, weight in self.factor_weights.items()
            ]

        return [
            {
                "id": f.id,
                "factor_code": f.factor_code,
                "factor_name": f.factor_name,
                "weight": float(f.weight),
                "calculation_method": f.calculation_method,
                "description": f.description,
            }
            for f in factors
        ]


# ====================  风控规则服务  ====================

class RiskRuleService:
    """风控规则引擎服务"""

    def __init__(self, db: Session):
        self.db = db
        self.logger = logger
        self.request_id = ""
        self.user_id = ""
        self._rule_cache = {}
        self._cache_timestamp = datetime.now()

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

    def get_all_rules(self, rule_type: RiskRuleType = None,
                      is_active: bool = True) -> List[RiskRuleEntity]:
        """获取所有风控规则"""
        query = self.db.query(RiskRuleEntity)

        if rule_type:
            query = query.filter(RiskRuleEntity.rule_type == rule_type)
        if is_active:
            query = query.filter(RiskRuleEntity.is_active == True)

        return query.order_by(RiskRuleEntity.priority).all()

    def get_rule_by_code(self, rule_code: str) -> Optional[RiskRuleEntity]:
        """通过规则代码获取规则"""
        return self.db.query(RiskRuleEntity).filter(
            RiskRuleEntity.rule_code == rule_code
        ).first()

    def add_rule(self, rule_data: Dict[str, Any]) -> RiskRuleEntity:
        """添加风控规则"""
        rule = RiskRuleEntity(
            id=f"rule_{rule_data['rule_code']}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            rule_code=rule_data["rule_code"],
            rule_name=rule_data["rule_name"],
            rule_type=rule_data.get("rule_type", RiskRuleType.ORDER),
            rule_category=rule_data.get("rule_category", "CUSTOM"),
            conditions=json.dumps(rule_data.get("conditions", [])),
            action=rule_data.get("action", RiskRuleAction.REVIEW),
            action_params=json.dumps(rule_data.get("action_params", {})),
            risk_score=rule_data.get("risk_score", 0),
            priority=rule_data.get("priority", 100),
            description=rule_data.get("description", ""),
            created_by=self.user_id or "system",
        )

        self.db.add(rule)
        self.db.commit()

        self._log("info", f"Risk rule added: {rule.rule_code}",
                 extra={"rule_code": rule.rule_code})

        return rule

    def update_rule(self, rule_code: str, updates: Dict[str, Any]) -> Optional[RiskRuleEntity]:
        """更新风控规则"""
        rule = self.get_rule_by_code(rule_code)
        if not rule:
            return None

        for key, value in updates.items():
            if hasattr(rule, key):
                if key in ["conditions", "action_params", "examples"]:
                    setattr(rule, key, json.dumps(value) if isinstance(value, dict) else value)
                else:
                    setattr(rule, key, value)

        rule.updated_at = datetime.now()
        self.db.commit()

        self._log("info", f"Risk rule updated: {rule_code}",
                 extra={"rule_code": rule_code})

        return rule

    def delete_rule(self, rule_code: str) -> bool:
        """删除风控规则"""
        rule = self.get_rule_by_code(rule_code)
        if not rule:
            return False

        self.db.delete(rule)
        self.db.commit()

        self._log("info", f"Risk rule deleted: {rule_code}",
                 extra={"rule_code": rule_code})

        return True

    def evaluate_rules(self, context: Dict[str, Any],
                       rule_type: RiskRuleType = None) -> Tuple[List[Dict], float]:
        """
        评估规则

        Args:
            context: 评估上下文 (包含 user_id, order_amount, device_id 等)
            rule_type: 规则类型

        Returns:
            (命中的规则列表，总风险评分)
        """
        # 获取有效规则
        rules = self.get_all_rules(rule_type=rule_type, is_active=True)

        hit_rules = []
        total_risk_score = 0

        for rule in rules:
            if self._evaluate_condition(rule, context):
                hit_rules.append({
                    "rule_code": rule.rule_code,
                    "rule_name": rule.rule_name,
                    "action": rule.action.value,
                    "risk_score": rule.risk_score,
                })
                total_risk_score += rule.risk_score

                # 更新命中统计
                rule.hit_count += 1
                rule.last_hit_at = datetime.now()

        if hit_rules:
            self.db.commit()

        return hit_rules, total_risk_score

    def _evaluate_condition(self, rule: RiskRuleEntity, context: Dict[str, Any]) -> bool:
        """评估单个规则的条件"""
        try:
            conditions = json.loads(rule.conditions) if isinstance(rule.conditions, str) else rule.conditions
        except:
            return False

        if not conditions:
            return False

        # 支持单个条件或条件列表 (AND 逻辑)
        if isinstance(conditions, dict):
            conditions = [conditions]

        for condition in conditions:
            field = condition.get("field")
            operator = condition.get("operator")
            threshold = condition.get("threshold")
            values = condition.get("values")  # for 'in' operator

            # 获取上下文中的值
            value = self._get_nested_value(context, field)
            if value is None:
                return False

            # 评估条件
            if not self._compare(value, operator, threshold, values):
                return False

        return True

    def _get_nested_value(self, context: Dict[str, Any], field: str) -> Any:
        """获取嵌套字段的值"""
        keys = field.split(".")
        value = context
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        return value

    def _compare(self, value: Any, operator: str, threshold: Any, values: List = None) -> bool:
        """比较操作"""
        if operator == ">":
            return value > threshold
        elif operator == "<":
            return value < threshold
        elif operator == ">=":
            return value >= threshold
        elif operator == "<=":
            return value <= threshold
        elif operator == "=":
            return value == threshold
        elif operator == "in":
            return value in (values or [])
        elif operator == "contains":
            return str(threshold) in str(value)
        elif operator == "matches":
            return bool(re.match(str(threshold), str(value)))
        elif operator == "!=":
            return value != threshold
        else:
            return False

    def _get_risk_level(self, risk_score: int) -> RiskLevel:
        """根据风险评分获取风险等级"""
        if risk_score >= 80:
            return RiskLevel.CRITICAL
        elif risk_score >= 60:
            return RiskLevel.HIGH
        elif risk_score >= 40:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    def _get_decision(self, risk_level: RiskLevel,
                      hit_rules: List[Dict]) -> Tuple[OrderRiskDecision, str]:
        """根据风险等级和命中规则生成决策"""
        # 检查是否有关键规则命中
        for rule in hit_rules:
            if rule["action"] == "reject":
                return OrderRiskDecision.REJECT, f"命中拒绝规则：{rule['rule_name']}"
            elif rule["action"] == "review":
                return OrderRiskDecision.REVIEW, f"命中审核规则：{rule['rule_name']}"

        # 基于风险等级决策
        if risk_level == RiskLevel.CRITICAL:
            return OrderRiskDecision.REJECT, "风险评分过高"
        elif risk_level == RiskLevel.HIGH:
            return OrderRiskDecision.REVIEW, "风险评分较高"
        elif risk_level == RiskLevel.MEDIUM:
            return OrderRiskDecision.REVIEW, "风险评分中等"
        else:
            return OrderRiskDecision.APPROVE, "风险评分低"


# ====================  黑名单服务  ====================

class BlacklistService:
    """黑名单管理服务"""

    def __init__(self, db: Session):
        self.db = db
        self.logger = logger
        self.request_id = ""
        self.user_id = ""

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

    def add_to_blacklist(self, target_type: BlacklistType, target_value: str,
                         reason: str, blacklist_type: str = "TEMPORARY",
                         days: int = 30, reason_code: str = None,
                         evidence: Dict = None) -> BlacklistEntity:
        """
        添加到黑名单

        Args:
            target_type: 目标类型 (USER/DEVICE/ADDRESS/PHONE)
            target_value: 目标值
            reason: 原因描述
            blacklist_type: 黑名单类型 (PERMANENT/TEMPORARY/SPECIFIC)
            days: 有效天数 (仅临时黑名单有效)
            reason_code: 原因代码
            evidence: 证据数据

        Returns:
            黑名单记录
        """
        # 检查是否已存在
        existing = self.db.query(BlacklistEntity).filter(
            and_(
                BlacklistEntity.target_type == target_type,
                BlacklistEntity.target_value == target_value,
                BlacklistEntity.is_active == True
            )
        ).first()

        if existing:
            self._log("warning", f"Target already in blacklist: {target_type}:{target_value}")
            return existing

        # 计算过期时间
        expire_at = None
        if blacklist_type == "TEMPORARY":
            expire_at = datetime.now() + timedelta(days=days)

        blacklist = BlacklistEntity(
            id=f"bl_{target_type.value}_{target_value}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            target_type=target_type,
            target_value=target_value,
            blacklist_type=blacklist_type,
            reason=reason,
            reason_code=reason_code,
            expire_at=expire_at,
            evidence=json.dumps(evidence) if evidence else None,
            created_by=self.user_id or "system",
        )

        self.db.add(blacklist)
        self.db.commit()

        self._log("info", f"Added to blacklist: {target_type}:{target_value}",
                 extra={"target_type": target_type.value, "target_value": target_value})

        return blacklist

    def remove_from_blacklist(self, target_type: BlacklistType,
                              target_value: str) -> bool:
        """从黑名单移除"""
        blacklist = self.db.query(BlacklistEntity).filter(
            and_(
                BlacklistEntity.target_type == target_type,
                BlacklistEntity.target_value == target_value,
                BlacklistEntity.is_active == True
            )
        ).first()

        if not blacklist:
            return False

        blacklist.is_active = False
        blacklist.updated_at = datetime.now()
        self.db.commit()

        self._log("info", f"Removed from blacklist: {target_type}:{target_value}",
                 extra={"target_type": target_type.value, "target_value": target_value})

        return True

    def check_blacklist(self, target_type: BlacklistType,
                        target_value: str) -> Tuple[bool, Optional[Dict]]:
        """
        检查是否在黑名单

        Returns:
            (是否在黑名单，黑名单记录)
        """
        blacklist = self.db.query(BlacklistEntity).filter(
            and_(
                BlacklistEntity.target_type == target_type,
                BlacklistEntity.target_value == target_value,
                BlacklistEntity.is_active == True,
                or_(
                    BlacklistEntity.expire_at.is_(None),
                    BlacklistEntity.expire_at > datetime.now()
                )
            )
        ).first()

        if blacklist:
            return True, {
                "id": blacklist.id,
                "target_type": blacklist.target_type.value,
                "target_value": blacklist.target_value,
                "blacklist_type": blacklist.blacklist_type,
                "reason": blacklist.reason,
                "reason_code": blacklist.reason_code,
                "expire_at": blacklist.expire_at.isoformat() if blacklist.expire_at else None,
            }

        return False, None

    def get_blacklist(self, target_type: BlacklistType = None,
                      page: int = 1, limit: int = 50) -> List[Dict[str, Any]]:
        """获取黑名单列表"""
        query = self.db.query(BlacklistEntity).filter(
            BlacklistEntity.is_active == True
        )

        if target_type:
            query = query.filter(BlacklistEntity.target_type == target_type)

        blacklist_list = query.order_by(desc(BlacklistEntity.created_at)).offset(
            (page - 1) * limit
        ).limit(limit).all()

        return [
            {
                "id": bl.id,
                "target_type": bl.target_type.value,
                "target_value": bl.target_value,
                "blacklist_type": bl.blacklist_type,
                "reason": bl.reason,
                "reason_code": bl.reason_code,
                "expire_at": bl.expire_at.isoformat() if bl.expire_at else None,
                "created_at": bl.created_at.isoformat() if bl.created_at else None,
            }
            for bl in blacklist_list
        ]

    def get_expired_blacklists(self) -> List[BlacklistEntity]:
        """获取过期的黑名单"""
        return self.db.query(BlacklistEntity).filter(
            and_(
                BlacklistEntity.is_active == True,
                BlacklistEntity.expire_at.isnot(None),
                BlacklistEntity.expire_at < datetime.now()
            )
        ).all()


# ====================  订单风控服务  ====================

class OrderRiskService:
    """订单风控服务"""

    def __init__(self, db: Session):
        self.db = db
        self.logger = logger
        self.request_id = ""
        self.user_id = ""
        self.credit_service = CreditService(db)
        self.rule_service = RiskRuleService(db)
        self.blacklist_service = BlacklistService(db)

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

    def assess_order_risk(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        评估订单风险

        Args:
            order_data: 订单数据，包含:
                - order_id: 订单 ID
                - user_id: 用户 ID
                - amount: 订单金额
                - product_ids: 商品 ID 列表
                - device_id: 设备 ID
                - address: 收货地址
                - phone: 手机号

        Returns:
            风险评估结果
        """
        user_id = order_data.get("user_id")
        order_id = order_data.get("order_id", f"temp_{datetime.now().timestamp()}")

        risk_score = 0
        risk_factors = []

        # 1. 用户信用风险评估
        credit_info = self.credit_service.get_or_create_credit(user_id)
        credit_score = credit_info.get("credit_score", 500)

        if credit_score < 400:
            risk_score += 30
            risk_factors.append({
                "factor": "credit_risk",
                "description": f"用户信用分过低：{credit_score}",
                "score_contribution": 30,
            })
        elif credit_score < 550:
            risk_score += 15
            risk_factors.append({
                "factor": "credit_risk",
                "description": f"用户信用分较低：{credit_score}",
                "score_contribution": 15,
            })

        # 2. 黑名单检查
        blacklist_checks = [
            (BlacklistType.USER, user_id),
        ]

        # 添加设备黑名单检查
        if order_data.get("device_id"):
            blacklist_checks.append((BlacklistType.DEVICE, order_data["device_id"]))

        # 添加手机号黑名单检查
        if order_data.get("phone"):
            blacklist_checks.append((BlacklistType.PHONE, order_data["phone"]))

        for bl_type, bl_value in blacklist_checks:
            in_blacklist, bl_record = self.blacklist_service.check_blacklist(bl_type, bl_value)
            if in_blacklist:
                risk_score += 50
                risk_factors.append({
                    "factor": "blacklist",
                    "description": f"命中黑名单：{bl_type.value}={bl_value}",
                    "blacklist_record": bl_record,
                    "score_contribution": 50,
                })

        # 3. 订单金额风险评估
        amount = order_data.get("amount", 0)
        if amount > 5000:
            risk_score += 20
            risk_factors.append({
                "factor": "amount_risk",
                "description": f"订单金额过高：{amount}",
                "score_contribution": 20,
            })
        elif amount > 2000:
            risk_score += 10
            risk_factors.append({
                "factor": "amount_risk",
                "description": f"订单金额较高：{amount}",
                "score_contribution": 10,
            })

        # 4. 规则引擎评估
        hit_rules, rule_risk_score = self.rule_service.evaluate_rules(
            order_data, rule_type=RiskRuleType.ORDER
        )
        risk_score += rule_risk_score
        if hit_rules:
            risk_factors.append({
                "factor": "rule_hit",
                "description": f"命中 {len(hit_rules)} 条风控规则",
                "hit_rules": hit_rules,
                "score_contribution": rule_risk_score,
            })

        # 5. 限制风险分上限
        risk_score = min(100, risk_score)

        # 确定风险等级
        risk_level = self._get_risk_level(risk_score)

        # 生成决策
        decision, decision_reason = self._make_decision(risk_level, hit_rules)

        # 保存评估结果
        assessment = self._save_assessment(
            order_id=order_id,
            user_id=user_id,
            risk_score=risk_score,
            risk_level=risk_level,
            risk_factors=risk_factors,
            hit_rules=hit_rules,
            decision=decision,
            decision_reason=decision_reason,
            assessment_context=order_data,
        )

        return {
            "order_id": order_id,
            "user_id": user_id,
            "risk_score": risk_score,
            "risk_level": risk_level.value,
            "risk_factors": risk_factors,
            "hit_rules": hit_rules,
            "decision": decision.value,
            "decision_reason": decision_reason,
        }

    def _get_risk_level(self, risk_score: int) -> RiskLevel:
        """根据风险评分获取风险等级"""
        if risk_score >= 80:
            return RiskLevel.CRITICAL
        elif risk_score >= 60:
            return RiskLevel.HIGH
        elif risk_score >= 40:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    def _make_decision(self, risk_level: RiskLevel,
                       hit_rules: List[Dict]) -> Tuple[OrderRiskDecision, str]:
        """生成风险决策"""
        # 检查是否有关键规则命中
        for rule in hit_rules:
            if rule["action"] == "reject":
                return OrderRiskDecision.REJECT, f"命中拒绝规则：{rule['rule_name']}"
            elif rule["action"] == "review":
                return OrderRiskDecision.REVIEW, f"命中审核规则：{rule['rule_name']}"

        # 基于风险等级决策
        if risk_level == RiskLevel.CRITICAL:
            return OrderRiskDecision.REJECT, "风险评分过高，拒绝订单"
        elif risk_level == RiskLevel.HIGH:
            return OrderRiskDecision.REVIEW, "风险评分较高，需要人工审核"
        elif risk_level == RiskLevel.MEDIUM:
            return OrderRiskDecision.REVIEW, "风险评分中等，建议审核"
        else:
            return OrderRiskDecision.APPROVE, "风险评分低，自动通过"

    def _save_assessment(self, order_id: str, user_id: str,
                         risk_score: int, risk_level: RiskLevel,
                         risk_factors: List[Dict], hit_rules: List[Dict],
                         decision: OrderRiskDecision, decision_reason: str,
                         assessment_context: Dict[str, Any]) -> OrderRiskAssessmentEntity:
        """保存订单风险评估结果"""
        assessment = OrderRiskAssessmentEntity(
            id=f"ora_{order_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            order_id=order_id,
            user_id=user_id,
            risk_score=risk_score,
            risk_level=risk_level,
            risk_factors=json.dumps(risk_factors),
            hit_rules=json.dumps(hit_rules),
            decision=decision,
            decision_reason=decision_reason,
            assessment_context=json.dumps(assessment_context),
            assessed_by=self.user_id or "system",
        )

        self.db.add(assessment)
        self.db.commit()

        return assessment

    def get_order_assessment(self, order_id: str) -> Optional[Dict[str, Any]]:
        """获取订单风险评估结果"""
        assessment = self.db.query(OrderRiskAssessmentEntity).filter(
            OrderRiskAssessmentEntity.order_id == order_id
        ).first()

        if not assessment:
            return None

        return {
            "order_id": assessment.order_id,
            "user_id": assessment.user_id,
            "risk_score": assessment.risk_score,
            "risk_level": assessment.risk_level.value,
            "risk_factors": json.loads(assessment.risk_factors) if assessment.risk_factors else [],
            "hit_rules": json.loads(assessment.hit_rules) if assessment.hit_rules else [],
            "decision": assessment.decision.value,
            "decision_reason": assessment.decision_reason,
            "created_at": assessment.created_at.isoformat() if assessment.created_at else None,
        }

    def report_fraud(self, order_id: str, user_id: str,
                     reason: str, evidence: Dict = None) -> str:
        """
        举报欺诈行为

        Args:
            order_id: 订单 ID
            user_id: 用户 ID
            reason: 举报原因
            evidence: 证据数据

        Returns:
            风险事件 ID
        """
        event = RiskEventEntity(
            id=f"re_{order_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            event_type="FRAUD",
            user_id=user_id,
            order_id=order_id,
            risk_level=RiskLevel.HIGH,
            risk_score=80,
            hit_rules=json.dumps([]),
            evidence=json.dumps(evidence) if evidence else None,
            description=reason,
            status="pending",
        )

        self.db.add(event)
        self.db.commit()

        self._log("info", f"Fraud reported for order {order_id}",
                 extra={"order_id": order_id, "user_id": user_id})

        return event.id
