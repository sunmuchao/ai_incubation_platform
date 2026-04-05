"""
P8 智能风控/信用体系 - 单元测试文件

测试覆盖:
1. 信用体系 (Credit System)
2. 风控规则引擎 (Risk Rule Engine)
3. 黑名单管理 (Blacklist Management)
4. 订单风控 (Order Risk Assessment)
"""
import pytest
import sys
import os
from datetime import datetime, timedelta
from decimal import Decimal

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config.database import Base, get_db
from models.p8_entities import (
    CreditScoreEntity, CreditScoreHistoryEntity, CreditFactorEntity,
    RiskRuleEntity, RiskEventEntity, BlacklistEntity, OrderRiskAssessmentEntity
)


# ====================  测试夹具  ====================

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_p8.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_test_tables():
    """创建测试表"""
    # 只创建 P8 相关的表，避免与其他模块的索引冲突
    from models.p8_entities import (
        CreditScoreEntity, CreditScoreHistoryEntity, CreditFactorEntity,
        RiskRuleEntity, RiskEventEntity, BlacklistEntity, OrderRiskAssessmentEntity
    )
    Base.metadata.create_all(bind=engine)


def drop_test_tables():
    """删除测试表"""
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="module")
def db_engine():
    """数据库引擎夹具"""
    drop_test_tables()  # 确保干净的开始
    create_test_tables()
    yield engine
    drop_test_tables()


@pytest.fixture
def db_session(db_engine):
    """数据库会话夹具"""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    transaction.rollback()
    session.close()
    connection.close()


@pytest.fixture
def client(db_session):
    """测试客户端夹具"""
    # 创建一个最小的 FastAPI 应用用于测试
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    test_app = FastAPI(title="P8 Test")

    # 添加 CORS 中间件
    test_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 导入并注册 P8 路由
    from api.p8_features import router as p8_router
    test_app.include_router(p8_router)

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    test_app.dependency_overrides[get_db] = override_get_db
    yield TestClient(test_app)
    test_app.dependency_overrides.clear()


# ====================  信用体系测试  ====================

def test_get_credit_score(client, db_session):
    """测试获取用户信用分"""
    user_id = "test_user_001"

    response = client.get(
        "/api/p8/credit/score",
        params={"user_id": user_id}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == user_id
    assert "credit_score" in data
    assert "credit_level" in data
    print(f"✅ 用户信用分：{data['credit_score']} ({data['credit_level']})")


def test_credit_history(client, db_session):
    """测试获取信用历史"""
    user_id = "test_user_001"

    # 先获取信用分 (会创建记录)
    client.get("/api/p8/credit/score", params={"user_id": user_id})

    response = client.get(
        "/api/p8/credit/history",
        params={"user_id": user_id, "limit": 10}
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    print(f"✅ 信用历史记录数：{len(data)}")


def test_credit_factors(client, db_session):
    """测试获取信用因子"""
    response = client.get("/api/p8/credit/factors")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    print(f"✅ 信用因子数量：{len(data)}")
    for factor in data:
        print(f"   - {factor['factor_code']}: weight={factor.get('weight', 'N/A')}")


def test_update_credit_score(client, db_session):
    """测试更新信用分"""
    user_id = "test_user_002"

    # 先获取信用分
    score_response = client.get("/api/p8/credit/score", params={"user_id": user_id})
    original_score = score_response.json()["credit_score"]

    # 更新信用分
    update_response = client.post(
        "/api/p8/credit/update",
        json={
            "user_id": user_id,
            "change": 50,
            "reason": "测试加分",
            "change_type": "TEST"
        }
    )

    assert update_response.status_code == 200
    data = update_response.json()
    assert data["user_id"] == user_id
    assert data["change"] == 50
    print(f"✅ 信用分更新：{original_score} -> {data['new_score']} (+{data['change']})")


# ====================  风控规则测试  ====================

def test_create_risk_rule(client, db_session):
    """测试创建风控规则"""
    rule_data = {
        "rule_code": "TEST_HIGH_AMOUNT",
        "rule_name": "高额订单风控规则",
        "rule_type": "order",
        "rule_category": "AMOUNT",
        "conditions": [
            {"field": "amount", "operator": ">", "threshold": 1000}
        ],
        "action": "review",
        "risk_score": 20,
        "priority": 50,
        "description": "订单金额超过 1000 元需要审核"
    }

    response = client.post("/api/p8/rules/", json=rule_data)

    assert response.status_code == 200
    data = response.json()
    assert data["rule_code"] == rule_data["rule_code"]
    assert data["rule_name"] == rule_data["rule_name"]
    print(f"✅ 风控规则创建成功：{data['rule_code']}")

    return rule_data["rule_code"]


def test_get_risk_rules(client, db_session):
    """测试获取风控规则列表"""
    response = client.get("/api/p8/rules/")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    print(f"✅ 风控规则数量：{len(data)}")


def test_get_risk_rule(client, db_session):
    """测试获取单个风控规则"""
    # 先创建规则
    rule_code = "TEST_RULE_GET"
    rule_data = {
        "rule_code": rule_code,
        "rule_name": "测试规则",
        "rule_type": "order",
        "conditions": [{"field": "amount", "operator": ">", "threshold": 500}],
        "action": "review",
        "risk_score": 10,
    }
    client.post("/api/p8/rules/", json=rule_data)

    response = client.get(f"/api/p8/rules/{rule_code}")

    assert response.status_code == 200
    data = response.json()
    assert data["rule_code"] == rule_code
    print(f"✅ 获取风控规则成功：{data['rule_name']}")


def test_update_risk_rule(client, db_session):
    """测试更新风控规则"""
    rule_code = "TEST_RULE_UPDATE"

    # 先创建规则
    create_data = {
        "rule_code": rule_code,
        "rule_name": "测试规则",
        "rule_type": "order",
        "conditions": [{"field": "amount", "operator": ">", "threshold": 500}],
        "action": "review",
        "risk_score": 10,
    }
    client.post("/api/p8/rules/", json=create_data)

    # 更新规则
    update_data = {
        "rule_name": "更新后的测试规则",
        "risk_score": 20,
        "is_active": False,
    }

    response = client.put(f"/api/p8/rules/{rule_code}", json=update_data)

    assert response.status_code == 200
    print(f"✅ 风控规则更新成功：{rule_code}")


def test_evaluate_rules(client, db_session):
    """测试规则评估"""
    # 先创建规则
    rule_data = {
        "rule_code": "TEST_EVALUATE_RULE",
        "rule_name": "测试评估规则",
        "rule_type": "order",
        "rule_category": "AMOUNT",
        "conditions": [{"field": "amount", "operator": ">", "threshold": 1000}],
        "action": "review",
        "risk_score": 30,
        "priority": 50,
        "description": "测试规则"
    }
    create_response = client.post("/api/p8/rules/", json=rule_data)
    assert create_response.status_code == 200, f"创建规则失败：{create_response.text}"

    # 测试命中规则 - context 是顶层参数
    response = client.post(
        "/api/p8/rules/evaluate",
        json={
            "context": {
                "user_id": "test_user",
                "amount": 1500,
                "device_id": "test_device"
            },
            "rule_type": "order"
        }
    )

    if response.status_code != 200:
        print(f"错误响应：{response.text}")
    assert response.status_code == 200
    data = response.json()
    assert data["total_risk_score"] >= 30
    assert len(data["hit_rules"]) > 0
    print(f"✅ 规则评估 (命中)：风险分={data['total_risk_score']}, 命中规则数={len(data['hit_rules'])}")

    # 测试不命中规则
    response = client.post(
        "/api/p8/rules/evaluate",
        json={
            "context": {
                "user_id": "test_user",
                "amount": 500,
                "device_id": "test_device"
            },
            "rule_type": "order"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_risk_score"] < 30
    print(f"✅ 规则评估 (未命中)：风险分={data['total_risk_score']}")


def test_delete_risk_rule(client, db_session):
    """测试删除风控规则"""
    rule_code = "TEST_RULE_DELETE"

    # 先创建规则
    rule_data = {
        "rule_code": rule_code,
        "rule_name": "待删除规则",
        "rule_type": "order",
        "conditions": [],
        "action": "review",
        "risk_score": 10,
    }
    client.post("/api/p8/rules/", json=rule_data)

    # 删除规则
    response = client.delete(f"/api/p8/rules/{rule_code}")

    assert response.status_code == 200
    print(f"✅ 风控规则删除成功：{rule_code}")


# ====================  黑名单测试  ====================

def test_add_to_blacklist(client, db_session):
    """测试添加到黑名单"""
    blacklist_data = {
        "target_type": "user",
        "target_value": "blacklist_user_001",
        "reason": "测试黑名单",
        "blacklist_type": "TEMPORARY",
        "days": 30,
        "reason_code": "TEST"
    }

    response = client.post("/api/p8/blacklist/", json=blacklist_data)

    assert response.status_code == 200
    data = response.json()
    assert data["target_type"] == "user"
    assert data["target_value"] == "blacklist_user_001"
    print(f"✅ 添加到黑名单成功：{data['target_type']}:{data['target_value']}")


def test_check_blacklist(client, db_session):
    """测试检查黑名单"""
    user_id = "blacklist_user_002"

    # 先添加到黑名单
    client.post(
        "/api/p8/blacklist/",
        json={
            "target_type": "user",
            "target_value": user_id,
            "reason": "测试检查",
            "blacklist_type": "TEMPORARY",
            "days": 30
        }
    )

    # 检查黑名单
    response = client.get(
        "/api/p8/blacklist/check",
        params={"target_type": "user", "target_value": user_id}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["in_blacklist"] == True
    assert data["record"] is not None
    print(f"✅ 黑名单检查 (在黑名单)：{data['record']['reason']}")

    # 检查不在黑名单的用户
    response = client.get(
        "/api/p8/blacklist/check",
        params={"target_type": "user", "target_value": "normal_user"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["in_blacklist"] == False
    print(f"✅ 黑名单检查 (不在黑名单)：正常用户")


def test_get_blacklist(client, db_session):
    """测试获取黑名单列表"""
    response = client.get("/api/p8/blacklist/")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    print(f"✅ 黑名单记录数：{len(data)}")


def test_remove_from_blacklist(client, db_session):
    """测试从黑名单移除"""
    user_id = "blacklist_user_003"

    # 先添加到黑名单
    client.post(
        "/api/p8/blacklist/",
        json={
            "target_type": "user",
            "target_value": user_id,
            "reason": "测试移除",
            "blacklist_type": "TEMPORARY",
            "days": 30
        }
    )

    # 从黑名单移除 - 使用 params
    response = client.delete(
        "/api/p8/blacklist/",
        params={
            "target_type": "user",
            "target_value": user_id
        }
    )

    assert response.status_code == 200
    print(f"✅ 从黑名单移除成功：{user_id}")


# ====================  订单风控测试  ====================

def test_assess_order_risk_low(client, db_session):
    """测试订单风险评估 - 低风险"""
    order_data = {
        "order_id": "ORDER_LOW_RISK_001",
        "user_id": "normal_user_001",
        "amount": 100,
    }

    response = client.post("/api/p8/order-risk/assess", json=order_data)

    assert response.status_code == 200
    data = response.json()
    assert data["risk_score"] < 40
    assert data["risk_level"] == "low"
    assert data["decision"] == "approve"
    print(f"✅ 低风险订单：风险分={data['risk_score']}, 决策={data['decision']}")


def test_assess_order_risk_high_amount(client, db_session):
    """测试订单风险评估 - 高额订单"""
    order_data = {
        "order_id": "ORDER_HIGH_AMOUNT_001",
        "user_id": "normal_user_002",
        "amount": 6000,  # 高额订单
    }

    response = client.post("/api/p8/order-risk/assess", json=order_data)

    assert response.status_code == 200
    data = response.json()
    assert data["risk_score"] >= 20
    print(f"✅ 高额订单评估：风险分={data['risk_score']}, 决策={data['decision']}")


def test_assess_order_risk_blacklist(client, db_session):
    """测试订单风险评估 - 黑名单用户"""
    user_id = "blacklist_order_user"

    # 先将用户加入黑名单
    client.post(
        "/api/p8/blacklist/",
        json={
            "target_type": "user",
            "target_value": user_id,
            "reason": "欺诈行为",
            "blacklist_type": "PERMANENT"
        }
    )

    order_data = {
        "order_id": "ORDER_BLACKLIST_001",
        "user_id": user_id,
        "amount": 100,
    }

    response = client.post("/api/p8/order-risk/assess", json=order_data)

    assert response.status_code == 200
    data = response.json()
    assert data["risk_score"] >= 50  # 黑名单应该增加 50 分
    assert data["risk_level"] in ["high", "critical"]
    print(f"✅ 黑名单用户订单评估：风险分={data['risk_score']}, 决策={data['decision']}")


def test_get_order_assessment(client, db_session):
    """测试获取订单评估结果"""
    order_id = "ORDER_QUERY_001"
    user_id = "normal_user_003"

    # 先进行评估
    client.post(
        "/api/p8/order-risk/assess",
        json={
            "order_id": order_id,
            "user_id": user_id,
            "amount": 200
        }
    )

    # 获取评估结果
    response = client.get(f"/api/p8/order-risk/assessment/{order_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["order_id"] == order_id
    assert "risk_score" in data
    assert "risk_level" in data
    print(f"✅ 订单评估结果查询：{data['order_id']} - {data['risk_level']}")


def test_report_fraud(client, db_session):
    """测试欺诈举报"""
    order_id = "ORDER_FRAUD_001"
    user_id = "fraud_user_001"

    response = client.post(
        "/api/p8/order-risk/fraud-report",
        json={
            "order_id": order_id,
            "user_id": user_id,
            "reason": "虚假订单",
            "evidence": {"screenshot": "test.png"}
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "event_id" in data
    print(f"✅ 欺诈举报成功：{data['event_id']}")


# ====================  主测试函数  ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
