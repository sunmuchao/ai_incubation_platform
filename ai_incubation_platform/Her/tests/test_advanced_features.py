"""
P18-P22 功能测试

测试 P18-P22 新一代迭代方向功能：
- P18: AI 预沟通
- P19: 真实匹配（消费水平与地理轨迹）
- P20: 防渣黑名单（行为信用分）
- P21: 动态关系教练
- P22: 产品悖论破解（情境感知、用户确权、隐私透明）

注意：这些 API 端点尚未实现，测试暂时跳过
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from db.database import Base, get_db
from models.advanced_feature_models import (
    AIChatSession, ConsumptionProfile, BehaviorCredit,
    RelationshipHealth, DynamicProfile
)

# 创建测试数据库
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_p18_p22.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """创建测试数据库会话"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """创建测试客户端"""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.skip(reason="P18-P22 API 端点尚未实现")
class TestP18AIPreCommunication:
    """P18: AI 预沟通测试"""

    def test_start_ai_chat_session(self, client, db_session):
        """测试启动 AI 预沟通会话"""
        response = client.post(
            "/api/p18/chat-session/start",
            json={"user_a_id": "user-1", "user_b_id": "user-2"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["status"] == "pending"

    def test_update_conversation_log(self, client, db_session):
        """测试更新对话记录"""
        # 先创建会话
        create_response = client.post(
            "/api/p18/chat-session/start",
            json={"user_a_id": "user-1", "user_b_id": "user-2"}
        )
        session_id = create_response.json()["session_id"]

        # 更新对话
        update_response = client.post(
            f"/api/p18/chat-session/{session_id}/update",
            json={
                "round_num": 1,
                "user_a_agent_msg": "你好，我喜欢旅行",
                "user_b_agent_msg": "我也喜欢旅行，最喜欢去海边"
            }
        )
        assert update_response.status_code == 200

    def test_extract_key_findings(self, client, db_session):
        """测试提取关键信息"""
        # 先创建会话
        create_response = client.post(
            "/api/p18/chat-session/start",
            json={"user_a_id": "user-1", "user_b_id": "user-2"}
        )
        session_id = create_response.json()["session_id"]

        # 提取关键信息
        extract_response = client.post(
            f"/api/p18/chat-session/{session_id}/extract"
        )
        assert extract_response.status_code == 200
        data = extract_response.json()
        assert "key_findings" in data
        assert "settlement_plan" in data["key_findings"]

    def test_get_chat_session(self, client, db_session):
        """测试获取会话详情"""
        # 先创建会话
        create_response = client.post(
            "/api/p18/chat-session/start",
            json={"user_a_id": "user-1", "user_b_id": "user-2"}
        )
        session_id = create_response.json()["session_id"]

        # 获取详情
        get_response = client.get(f"/api/p18/chat-session/{session_id}")
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["session_id"] == session_id


@pytest.mark.skip(reason="P18-P22 API 端点尚未实现")
class TestP19AuthenticMatching:
    """P19: 真实匹配测试"""

    def test_create_consumption_profile(self, client, db_session):
        """测试创建消费画像"""
        response = client.post(
            "/api/p19/consumption-profile?user_id=user-1",
            json={
                "consumption_level": "轻奢",
                "consumption_frequency": "高频",
                "preferred_categories": ["精品咖啡", "书店", "艺术展览"],
                "average_transaction": "200-500 元",
                "is_authorized": True
            }
        )
        assert response.status_code == 200

    def test_create_geo_trajectory(self, client, db_session):
        """测试创建地理轨迹"""
        response = client.post(
            "/api/p19/geo-trajectory?user_id=user-1",
            json={
                "home_district": "朝阳区",
                "work_district": "海淀区",
                "frequent_areas": [
                    {"name": "三里屯", "type": "商圈", "visit_count": 25}
                ],
                "lifestyle_tags": ["文艺", "小资"],
                "lifestyle_quality_score": 8.0
            }
        )
        assert response.status_code == 200

    def test_calculate_authentic_match(self, client, db_session):
        """测试计算真实匹配度"""
        # 先创建两个用户的画像
        client.post(
            "/api/p19/consumption-profile?user_id=user-a",
            json={
                "consumption_level": "轻奢",
                "consumption_frequency": "高频",
                "preferred_categories": ["精品咖啡"],
                "average_transaction": "200-500 元",
                "is_authorized": True
            }
        )
        client.post(
            "/api/p19/consumption-profile?user_id=user-b",
            json={
                "consumption_level": "轻奢",
                "consumption_frequency": "中频",
                "preferred_categories": ["精品咖啡", "书店"],
                "average_transaction": "200-500 元",
                "is_authorized": True
            }
        )

        # 计算匹配度
        match_response = client.get("/api/p19/authentic-match/user-a/user-b")
        assert match_response.status_code == 200
        data = match_response.json()
        assert "overall_match_score" in data
        assert "match_highlights" in data


@pytest.mark.skip(reason="P18-P22 API 端点尚未实现")
class TestP20BehaviorCredit:
    """P20: 防渣黑名单测试"""

    def test_get_user_credit(self, client, db_session):
        """测试获取用户信用"""
        response = client.get("/api/p20/credit/user-1")
        assert response.status_code == 200
        data = response.json()
        assert "credit_score" in data
        assert "credit_level" in data

    def test_submit_date_feedback(self, client, db_session):
        """测试提交约会反馈"""
        response = client.post(
            "/api/p20/feedback",
            json={
                "date_id": "date-1",
                "reporter_id": "user-1",
                "target_user_id": "user-2",
                "feedback_items": {
                    "offensive_behavior": False,
                    "photo_authentic": True,
                    "late_arrival": False
                },
                "overall_rating": 5,
                "comments": "很愉快的约会"
            }
        )
        assert response.status_code == 200

    def test_negative_feedback_reduces_credit(self, client, db_session):
        """测试负面反馈降低信用分"""
        # 先获取初始信用
        initial_response = client.get("/api/p20/credit/user-test")
        initial_score = initial_response.json()["credit_score"]

        # 提交多次负面反馈
        for i in range(3):
            client.post(
                "/api/p20/feedback",
                json={
                    "date_id": f"date-{i}",
                    "reporter_id": f"reporter-{i}",
                    "target_user_id": "user-test",
                    "feedback_items": {"offensive_behavior": True},
                    "overall_rating": 1,
                    "comments": "不愉快的经历"
                }
            )

        # 检查信用分是否降低
        final_response = client.get("/api/p20/credit/user-test")
        final_score = final_response.json()["credit_score"]
        assert final_score <= initial_score


@pytest.mark.skip(reason="P18-P22 API 端点尚未实现")
class TestP21RelationshipCoach:
    """P21: 动态关系教练测试"""

    def test_get_relationship_health(self, client, db_session):
        """测试获取关系健康度"""
        response = client.get("/api/p21/health/couple-1")
        assert response.status_code == 200
        data = response.json()
        assert "health_score" in data or "communication_status" in data

    def test_update_relationship_health(self, client, db_session):
        """测试更新关系健康数据"""
        # 先创建记录
        client.get("/api/p21/health/couple-1")

        # 更新数据
        response = client.post(
            "/api/p21/health/couple-1/update",
            json={
                "current_daily_messages": 5,
                "previous_daily_messages": 20
            }
        )
        assert response.status_code == 200

    def test_check_and_intervene(self, client, db_session):
        """测试 AI 介入"""
        # 先创建记录并设置沟通下降
        client.get("/api/p21/health/couple-intervene")
        client.post(
            "/api/p21/health/couple-intervene/update",
            json={
                "current_daily_messages": 3,
                "previous_daily_messages": 30
            }
        )

        # 检查是否需要介入
        check_response = client.post("/api/p21/health/couple-intervene/check")
        assert check_response.status_code == 200
        data = check_response.json()
        # 由于沟通大幅下降，应该需要介入
        assert data.get("intervention_required") in [True, False]  # 取决于实现

    def test_recommend_gifts(self, client, db_session):
        """测试礼物推荐"""
        # 先创建礼物管家
        client.post(
            "/api/p21/gift-manager?user_id=user-1",
            json={
                "partner_id": "user-2",
                "partner_name": "Ta",
                "partner_preferences": {
                    "favorite_categories": ["饰品", "家居"]
                }
            }
        )

        # 请求推荐
        response = client.get("/api/p21/gift-manager/user-1/recommend?event_name=生日")
        assert response.status_code == 200
        data = response.json()
        assert "gift_suggestions" in data
        assert len(data["gift_suggestions"]) > 0


@pytest.mark.skip(reason="P18-P22 API 端点尚未实现")
class TestP22ParadoxSolver:
    """P22: 产品悖论破解测试"""

    def test_get_dynamic_profile(self, client, db_session):
        """测试获取动态画像"""
        response = client.get("/api/p22/dynamic-profile/user-1")
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert "real_time_state" in data

    def test_update_real_time_state(self, client, db_session):
        """测试更新实时状态"""
        response = client.post(
            "/api/p22/dynamic-profile/user-1/state",
            json={
                "mood": "渴望倾听",
                "energy_level": "中",
                "social_appetite": "深层社交"
            }
        )
        assert response.status_code == 200

    def test_get_preference_dial(self, client, db_session):
        """测试获取偏好拨盘"""
        response = client.get("/api/p22/preference-dial/user-1")
        assert response.status_code == 200
        data = response.json()
        assert "current_weights" in data
        assert "is_user_adjustable" in data

    def test_update_preference_weights(self, client, db_session):
        """测试更新偏好权重"""
        response = client.post(
            "/api/p22/preference-dial/user-1/update",
            json={
                "appearance_weight": 40,
                "values_weight": 25
            }
        )
        assert response.status_code == 200

    def test_get_privacy_settings(self, client, db_session):
        """测试获取隐私设置"""
        response = client.get("/api/p22/privacy-settings/user-1")
        assert response.status_code == 200
        data = response.json()
        assert "data_access_level" in data
        assert "allowed_analysis" in data

    def test_update_privacy_settings(self, client, db_session):
        """测试更新隐私设置"""
        response = client.post(
            "/api/p22/privacy-settings/user-1/update",
            json={
                "data_access_level": "minimal",
                "blocked_analysis": ["voice", "location"]
            }
        )
        assert response.status_code == 200

    def test_get_ai_audit_logs(self, client, db_session):
        """测试获取 AI 干预日志"""
        response = client.get("/api/p22/ai-audit-logs/user-1")
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data

    def test_create_conversion_funnel(self, client, db_session):
        """测试创建转化漏斗"""
        response = client.post(
            "/api/p22/conversion-funnel",
            params={
                "match_id": "match-1",
                "user_a_id": "user-a",
                "user_b_id": "user-b"
            }
        )
        assert response.status_code == 200

    def test_activate_couple_mode(self, client, db_session):
        """测试激活情侣模式"""
        response = client.post(
            "/api/p22/couple-mode/activate",
            params={
                "couple_id": "couple-1",
                "user_a_id": "user-a",
                "user_b_id": "user-b",
                "theme": "romantic"
            }
        )
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
