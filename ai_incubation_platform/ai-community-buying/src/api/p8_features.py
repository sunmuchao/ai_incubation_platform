"""
P8 阶段 - 智能风控/信用体系 API 路由

包含:
1. 信用体系 API
2. 风控规则 API
3. 黑名单 API
4. 订单风控 API
"""
from fastapi import APIRouter, Depends, Query, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal

from config.database import get_db
from services.p8_services import CreditService, RiskRuleService, BlacklistService, OrderRiskService
from models.p8_entities import (
    CreditLevel, RiskLevel, BlacklistType, RiskRuleType, RiskRuleAction, OrderRiskDecision
)
from core.logging_config import get_logger
from core.exceptions import AppException

logger = get_logger("api.p8")

router = APIRouter(prefix="/api/p8", tags=["P8 智能风控"])

# ====================  信用体系 API  ====================

credit_router = APIRouter(prefix="/credit", tags=["信用体系"])


@credit_router.get("/score", response_model=Dict[str, Any])
def get_credit_score(
    user_id: str = Query(..., description="用户 ID"),
    db: Session = Depends(get_db)
):
    """获取用户信用分"""
    service = CreditService(db)
    service.set_request_context(f"req_{datetime.now().timestamp()}", user_id)

    result = service.get_or_create_credit(user_id)

    if not result:
        raise HTTPException(status_code=404, detail="User credit score not found")

    return result


@credit_router.get("/history", response_model=List[Dict[str, Any]])
def get_credit_history(
    user_id: str = Query(..., description="用户 ID"),
    limit: int = Query(20, ge=1, le=100, description="返回记录数限制"),
    db: Session = Depends(get_db)
):
    """获取用户信用历史"""
    service = CreditService(db)
    service.set_request_context(f"req_{datetime.now().timestamp()}", user_id)

    return service.get_credit_history(user_id, limit)


@credit_router.get("/factors", response_model=List[Dict[str, Any]])
def get_credit_factors(db: Session = Depends(get_db)):
    """获取信用因子配置"""
    service = CreditService(db)
    return service.get_credit_factors()


@credit_router.post("/calculate", response_model=Dict[str, Any])
def calculate_credit_score(
    user_id: str = Body(..., description="用户 ID"),
    db: Session = Depends(get_db)
):
    """重新计算用户信用分"""
    service = CreditService(db)
    service.set_request_context(f"req_{datetime.now().timestamp()}", user_id)

    new_score = service.calculate_credit_score(user_id)

    return {
        "user_id": user_id,
        "credit_score": new_score,
        "calculated_at": datetime.now().isoformat(),
    }


@credit_router.post("/update", response_model=Dict[str, Any])
def update_credit_score(
    user_id: str = Body(..., description="用户 ID"),
    change: int = Body(..., description="变化值 (正数增加，负数减少)"),
    reason: str = Body(..., description="变化原因"),
    change_type: str = Body("MANUAL", description="变化类型"),
    db: Session = Depends(get_db)
):
    """更新用户信用分"""
    service = CreditService(db)
    service.set_request_context(f"req_{datetime.now().timestamp()}", user_id)

    new_score = service.update_credit_score(user_id, change, reason, change_type)

    return {
        "user_id": user_id,
        "old_score": service.get_or_create_credit(user_id)["credit_score"] - change,
        "new_score": new_score,
        "change": change,
        "reason": reason,
    }


# ====================  风控规则 API  ====================

rules_router = APIRouter(prefix="/rules", tags=["风控规则"])


@rules_router.get("/", response_model=List[Dict[str, Any]])
def get_all_rules(
    rule_type: Optional[str] = Query(None, description="规则类型"),
    db: Session = Depends(get_db)
):
    """获取所有风控规则"""
    service = RiskRuleService(db)

    rule_type_enum = RiskRuleType(rule_type) if rule_type else None
    rules = service.get_all_rules(rule_type=rule_type_enum)

    return [
        {
            "id": r.id,
            "rule_code": r.rule_code,
            "rule_name": r.rule_name,
            "rule_type": r.rule_type.value,
            "rule_category": r.rule_category,
            "conditions": json.loads(r.conditions) if r.conditions else [],
            "action": r.action.value,
            "risk_score": r.risk_score,
            "priority": r.priority,
            "is_active": r.is_active,
            "hit_count": r.hit_count,
        }
        for r in rules
    ]


@rules_router.get("/{rule_code}", response_model=Dict[str, Any])
def get_rule(
    rule_code: str,
    db: Session = Depends(get_db)
):
    """获取规则详情"""
    service = RiskRuleService(db)
    rule = service.get_rule_by_code(rule_code)

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    return {
        "id": rule.id,
        "rule_code": rule.rule_code,
        "rule_name": rule.rule_name,
        "rule_type": rule.rule_type.value,
        "rule_category": rule.rule_category,
        "conditions": json.loads(rule.conditions) if rule.conditions else [],
        "action": rule.action.value,
        "action_params": json.loads(rule.action_params) if rule.action_params else {},
        "risk_score": rule.risk_score,
        "priority": rule.priority,
        "is_active": rule.is_active,
        "description": rule.description,
    }


@rules_router.post("/", response_model=Dict[str, Any])
def create_rule(
    rule_code: str = Body(..., description="规则代码"),
    rule_name: str = Body(..., description="规则名称"),
    rule_type: str = Body("order", description="规则类型"),
    rule_category: str = Body("CUSTOM", description="规则分类"),
    conditions: List[Dict] = Body([], description="条件配置"),
    action: str = Body("review", description="执行动作"),
    risk_score: int = Body(0, description="风险评分"),
    priority: int = Body(100, description="优先级"),
    description: str = Body("", description="规则描述"),
    db: Session = Depends(get_db)
):
    """创建风控规则"""
    import json as json_lib
    service = RiskRuleService(db)
    service.set_request_context(f"req_{datetime.now().timestamp()}")

    try:
        rule_type_enum = RiskRuleType(rule_type)
        action_enum = RiskRuleAction(action)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid enum value: {e}")

    rule_data = {
        "rule_code": rule_code,
        "rule_name": rule_name,
        "rule_type": rule_type_enum,
        "rule_category": rule_category,
        "conditions": conditions,
        "action": action_enum,
        "risk_score": risk_score,
        "priority": priority,
        "description": description,
    }

    rule = service.add_rule(rule_data)

    return {
        "id": rule.id,
        "rule_code": rule.rule_code,
        "rule_name": rule.rule_name,
        "created_at": rule.created_at.isoformat() if rule.created_at else None,
    }


@rules_router.put("/{rule_code}", response_model=Dict[str, Any])
def update_rule(
    rule_code: str,
    rule_name: Optional[str] = Body(None, description="规则名称"),
    rule_category: Optional[str] = Body(None, description="规则分类"),
    conditions: Optional[List[Dict]] = Body(None, description="条件配置"),
    action: Optional[str] = Body(None, description="执行动作"),
    risk_score: Optional[int] = Body(None, description="风险评分"),
    priority: Optional[int] = Body(None, description="优先级"),
    is_active: Optional[bool] = Body(None, description="是否启用"),
    description: Optional[str] = Body(None, description="规则描述"),
    db: Session = Depends(get_db)
):
    """更新风控规则"""
    service = RiskRuleService(db)
    service.set_request_context(f"req_{datetime.now().timestamp()}")

    updates = {}
    for key, value in [
        ("rule_name", rule_name),
        ("rule_category", rule_category),
        ("conditions", conditions),
        ("action", action),
        ("risk_score", risk_score),
        ("priority", priority),
        ("is_active", is_active),
        ("description", description),
    ]:
        if value is not None:
            updates[key] = value

    # 转换枚举值
    if "action" in updates:
        try:
            updates["action"] = RiskRuleAction(updates["action"])
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid action: {e}")

    rule = service.update_rule(rule_code, updates)

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    return {
        "rule_code": rule.rule_code,
        "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
    }


@rules_router.delete("/{rule_code}")
def delete_rule(
    rule_code: str,
    db: Session = Depends(get_db)
):
    """删除风控规则"""
    service = RiskRuleService(db)
    service.set_request_context(f"req_{datetime.now().timestamp()}")

    success = service.delete_rule(rule_code)

    if not success:
        raise HTTPException(status_code=404, detail="Rule not found")

    return {"message": f"Rule {rule_code} deleted successfully"}


@rules_router.post("/evaluate", response_model=Dict[str, Any])
def evaluate_rules(
    context: Dict[str, Any] = Body(..., description="评估上下文"),
    rule_type: Optional[str] = Body(None, description="规则类型"),
    db: Session = Depends(get_db)
):
    """评估规则"""
    service = RiskRuleService(db)
    service.set_request_context(f"req_{datetime.now().timestamp()}")

    rule_type_enum = RiskRuleType(rule_type) if rule_type else None
    hit_rules, total_risk_score = service.evaluate_rules(context, rule_type=rule_type_enum)

    # 确定风险等级
    if total_risk_score >= 80:
        risk_level = "critical"
    elif total_risk_score >= 60:
        risk_level = "high"
    elif total_risk_score >= 40:
        risk_level = "medium"
    else:
        risk_level = "low"

    return {
        "hit_rules": hit_rules,
        "total_risk_score": total_risk_score,
        "risk_level": risk_level,
        "evaluated_at": datetime.now().isoformat(),
    }


# ====================  黑名单 API  ====================

blacklist_router = APIRouter(prefix="/blacklist", tags=["黑名单管理"])


@blacklist_router.get("/", response_model=List[Dict[str, Any]])
def get_blacklist(
    target_type: Optional[str] = Query(None, description="目标类型"),
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(50, ge=1, le=200, description="每页数量"),
    db: Session = Depends(get_db)
):
    """获取黑名单列表"""
    service = BlacklistService(db)
    service.set_request_context(f"req_{datetime.now().timestamp()}")

    target_type_enum = BlacklistType(target_type) if target_type else None
    return service.get_blacklist(target_type=target_type_enum, page=page, limit=limit)


@blacklist_router.get("/check", response_model=Dict[str, Any])
def check_blacklist(
    target_type: str = Query(..., description="目标类型 (user/device/address/phone)"),
    target_value: str = Query(..., description="目标值"),
    db: Session = Depends(get_db)
):
    """检查是否在黑名单"""
    service = BlacklistService(db)
    service.set_request_context(f"req_{datetime.now().timestamp()}")

    try:
        target_type_enum = BlacklistType(target_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid target type: {e}")

    in_list, record = service.check_blacklist(target_type_enum, target_value)

    return {
        "in_blacklist": in_list,
        "record": record,
        "checked_at": datetime.now().isoformat(),
    }


@blacklist_router.post("/", response_model=Dict[str, Any])
def add_to_blacklist(
    target_type: str = Body(..., description="目标类型"),
    target_value: str = Body(..., description="目标值"),
    reason: str = Body(..., description="原因描述"),
    blacklist_type: str = Body("TEMPORARY", description="黑名单类型"),
    days: int = Body(30, ge=1, le=365, description="有效天数"),
    reason_code: Optional[str] = Body(None, description="原因代码"),
    db: Session = Depends(get_db)
):
    """添加到黑名单"""
    service = BlacklistService(db)
    service.set_request_context(f"req_{datetime.now().timestamp()}")

    try:
        target_type_enum = BlacklistType(target_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid target type: {e}")

    blacklist = service.add_to_blacklist(
        target_type=target_type_enum,
        target_value=target_value,
        reason=reason,
        blacklist_type=blacklist_type,
        days=days,
        reason_code=reason_code,
    )

    return {
        "id": blacklist.id,
        "target_type": blacklist.target_type.value,
        "target_value": blacklist.target_value,
        "reason": blacklist.reason,
        "expire_at": blacklist.expire_at.isoformat() if blacklist.expire_at else None,
    }


@blacklist_router.delete("/")
def remove_from_blacklist(
    target_type: str = Query(..., description="目标类型"),
    target_value: str = Query(..., description="目标值"),
    db: Session = Depends(get_db)
):
    """从黑名单移除"""
    service = BlacklistService(db)
    service.set_request_context(f"req_{datetime.now().timestamp()}")

    try:
        target_type_enum = BlacklistType(target_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid target type: {e}")

    success = service.remove_from_blacklist(target_type_enum, target_value)

    if not success:
        raise HTTPException(status_code=404, detail="Blacklist record not found")

    return {"message": f"Removed from blacklist: {target_type}:{target_value}"}


# ====================  订单风控 API  ====================

order_risk_router = APIRouter(prefix="/order-risk", tags=["订单风控"])


@order_risk_router.post("/assess", response_model=Dict[str, Any])
def assess_order_risk(
    order_id: str = Body(..., description="订单 ID"),
    user_id: str = Body(..., description="用户 ID"),
    amount: float = Body(0, description="订单金额"),
    device_id: Optional[str] = Body(None, description="设备 ID"),
    address: Optional[str] = Body(None, description="收货地址"),
    phone: Optional[str] = Body(None, description="手机号"),
    db: Session = Depends(get_db)
):
    """评估订单风险"""
    service = OrderRiskService(db)
    service.set_request_context(f"req_{datetime.now().timestamp()}", user_id)

    order_data = {
        "order_id": order_id,
        "user_id": user_id,
        "amount": amount,
        "device_id": device_id,
        "address": address,
        "phone": phone,
    }

    result = service.assess_order_risk(order_data)

    return result


@order_risk_router.get("/assessment/{order_id}", response_model=Dict[str, Any])
def get_order_assessment(
    order_id: str,
    db: Session = Depends(get_db)
):
    """获取订单风险评估结果"""
    service = OrderRiskService(db)
    service.set_request_context(f"req_{datetime.now().timestamp()}")

    result = service.get_order_assessment(order_id)

    if not result:
        raise HTTPException(status_code=404, detail="Assessment not found")

    return result


@order_risk_router.post("/fraud-report", response_model=Dict[str, Any])
def report_fraud(
    order_id: str = Body(..., description="订单 ID"),
    user_id: str = Body(..., description="用户 ID"),
    reason: str = Body(..., description="举报原因"),
    evidence: Optional[Dict] = Body(None, description="证据数据"),
    db: Session = Depends(get_db)
):
    """举报欺诈行为"""
    service = OrderRiskService(db)
    service.set_request_context(f"req_{datetime.now().timestamp()}", user_id)

    event_id = service.report_fraud(order_id, user_id, reason, evidence)

    return {
        "event_id": event_id,
        "order_id": order_id,
        "reported_at": datetime.now().isoformat(),
    }


# 导入 json 模块
import json

# 注册子路由到主 router
router.include_router(credit_router)
router.include_router(rules_router)
router.include_router(blacklist_router)
router.include_router(order_risk_router)
