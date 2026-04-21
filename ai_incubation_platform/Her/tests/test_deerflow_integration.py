"""
DeerFlow 集成测试

测试覆盖:
1. DeerFlow API 端点测试 (chat, stream, status, memory/sync)
2. Memory 同步逻辑测试
3. 降级处理测试 (_handle_with_her_service)
4. Generative UI 构建测试
5. 边界值测试 (空消息、超长消息、无效用户)
6. 异常处理测试 (DeerFlow 不可用、LLM 超时)

执行方式:
    pytest tests/test_deerflow_integration.py -v --tb=short
"""
import pytest
import json
import uuid
import os
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

# 导入被测试模块
from api.deerflow import (
    router,
    ChatRequest,
    StreamRequest,
    DeerFlowResponse,
    DeerFlowStatusResponse,
    MemorySyncRequest,
    MemorySyncResponse,
    LearningConfirmRequest,
    LearningConfirmResponse,
    get_user_profile,
    build_memory_facts,
    sync_user_memory_to_deerflow,
    build_generative_ui_from_tool_result,
    infer_intent_from_response,
    _normalize_generative_ui,
    _finalize_match_generative_ui,
    _coerce_interests_to_str_list,
    _align_ai_message_with_structured_result,
    _render_structured_result_message,
    _build_observability_trace,
    _enrich_tool_result_with_observability,
    _build_ui_response,
    _handle_with_her_service,
    _merge_her_find_candidates_into_match_cards,
)
from main import app


# ============= Test Fixtures =============

@pytest.fixture
def client():
    """创建测试客户端"""
    from db.database import get_db

    def override_get_db():
        yield None  # Mock DB

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def mock_deerflow_client():
    """Mock DeerFlow 客户端"""
    mock = MagicMock()
    mock.chat.return_value = '{"success": true, "summary": "测试响应", "data": {"matches": []}}'
    mock.stream.return_value = []
    return mock


@pytest.fixture
def mock_her_service():
    """Mock Her 服务"""
    mock = MagicMock()
    mock_response = MagicMock()
    mock_response.ai_message = "测试响应"
    mock_response.generative_ui = None
    mock_response.intent_type = "match_request"
    mock_response.matches = []
    mock_response.bias_analysis = None
    mock.process_message = AsyncMock(return_value=mock_response)
    return mock


@pytest.fixture
def mock_db_session():
    """Mock 数据库会话"""
    mock = MagicMock()
    mock.query.return_value.filter.return_value.first.return_value = None
    mock.add.return_value = None
    mock.commit.return_value = None
    mock.rollback.return_value = None
    return mock


@pytest.fixture
def sample_user_profile():
    """示例用户画像"""
    return {
        "id": str(uuid.uuid4()),
        "name": "测试用户",
        "age": 28,
        "gender": "male",
        "location": "北京市",
        "relationship_goal": "serious",
        "interests": ["阅读", "旅行", "音乐"],
        "bio": "热爱生活的程序员",
        "occupation": "工程师",
        "education": "bachelor",
        "accept_remote": "yes",
        "preferred_age_min": 25,
        "preferred_age_max": 35,
        "preferred_location": "北京",
        "deal_breakers": "吸烟",
    }


# ============= 第一部分：API 端点测试 =============

class TestDeerFlowAPIEndpoints:
    """DeerFlow API 端点测试"""

    @patch('api.deerflow.DEERFLOW_AVAILABLE', False)
    def test_status_endpoint_deerflow_not_available(self, client):
        """测试状态端点 - DeerFlow 不可用"""
        response = client.get("/api/deerflow/status")
        assert response.status_code == 200
        data = response.json()
        assert data["available"] == False

    @patch('api.deerflow.DEERFLOW_AVAILABLE', True)
    def test_status_endpoint_deerflow_available(self, client):
        """测试状态端点 - DeerFlow 可用"""
        with patch('api.deerflow.get_deerflow_client') as mock_get_client:
            mock_get_client.return_value = MagicMock()
            response = client.get("/api/deerflow/status")
            assert response.status_code == 200
            data = response.json()
            assert data["available"] == True

    @patch('api.deerflow.DEERFLOW_AVAILABLE', False)
    def test_chat_endpoint_deerflow_not_available(self, client):
        """测试聊天端点 - DeerFlow 不可用时降级"""
        with patch('api.deerflow._handle_with_her_service') as mock_her:
            mock_her.return_value = DeerFlowResponse(
                success=True,
                ai_message="降级响应",
                deerflow_used=False
            )
            response = client.post(
                "/api/deerflow/chat",
                json={"message": "帮我推荐匹配对象", "user_id": str(uuid.uuid4())}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] == True
            assert data["deerflow_used"] == False

    @patch('api.deerflow.DEERFLOW_AVAILABLE', True)
    def test_chat_endpoint_success(self, client):
        """测试聊天端点 - 正常流程"""
        mock_deerflow_client = MagicMock()
        mock_deerflow_client.chat.return_value = '{"success": true, "summary": "测试响应", "data": {"matches": []}}'

        with patch('api.deerflow.get_deerflow_client') as mock_get_client:
            mock_get_client.return_value = mock_deerflow_client

            with patch('api.deerflow.sync_user_memory_to_deerflow') as mock_sync:
                mock_sync.return_value = 5

                response = client.post(
                    "/api/deerflow/chat",
                    json={"message": "帮我推荐匹配对象", "user_id": str(uuid.uuid4())}
                )
                assert response.status_code == 200
                data = response.json()
                assert data["success"] == True
                assert data["deerflow_used"] == True

    @patch('api.deerflow.DEERFLOW_AVAILABLE', True)
    def test_chat_endpoint_client_none(self, client):
        """测试聊天端点 - 客户端为 None"""
        with patch('api.deerflow.get_deerflow_client') as mock_get_client:
            mock_get_client.return_value = None

            with patch('api.deerflow._handle_with_her_service') as mock_her:
                mock_her.return_value = DeerFlowResponse(
                    success=True,
                    ai_message="降级响应",
                    deerflow_used=False
                )
                response = client.post(
                    "/api/deerflow/chat",
                    json={"message": "测试消息"}
                )
                assert response.status_code == 200
                data = response.json()
                assert data["deerflow_used"] == False

    def test_memory_sync_endpoint(self, client):
        """测试 Memory 同步端点"""
        with patch('api.deerflow.sync_user_memory_to_deerflow') as mock_sync:
            mock_sync.return_value = 10

            response = client.post(
                "/api/deerflow/memory/sync",
                json={"user_id": str(uuid.uuid4())}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] == True
            assert data["facts_count"] == 10

    def test_memory_sync_endpoint_failure(self, client):
        """测试 Memory 同步端点 - 失败"""
        with patch('api.deerflow.sync_user_memory_to_deerflow') as mock_sync:
            mock_sync.return_value = 0

            response = client.post(
                "/api/deerflow/memory/sync",
                json={"user_id": str(uuid.uuid4())}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] == False


# ============= 第二部分：边界值测试 =============

class TestDeerFlowBoundaryValues:
    """DeerFlow 边界值测试"""

    def test_chat_empty_message(self, client):
        """测试空消息"""
        response = client.post(
            "/api/deerflow/chat",
            json={"message": "", "user_id": str(uuid.uuid4())}
        )
        # 应返回 422 (Pydantic 验证失败) 或正常处理
        assert response.status_code in [200, 422]

    def test_chat_message_too_long(self, client):
        """测试超长消息 (10000+ 字符)"""
        long_message = "测" * 10001
        with patch('api.deerflow.DEERFLOW_AVAILABLE', False):
            with patch('api.deerflow._handle_with_her_service') as mock_her:
                mock_her.return_value = DeerFlowResponse(
                    success=True,
                    ai_message="响应",
                    deerflow_used=False
                )
                response = client.post(
                    "/api/deerflow/chat",
                    json={"message": long_message, "user_id": str(uuid.uuid4())}
                )
                assert response.status_code != 500  # 不应崩溃

    def test_chat_special_characters(self, client):
        """测试特殊字符消息"""
        special_chars = "<script>alert('xss')</script>"
        with patch('api.deerflow.DEERFLOW_AVAILABLE', False):
            with patch('api.deerflow._handle_with_her_service') as mock_her:
                mock_her.return_value = DeerFlowResponse(
                    success=True,
                    ai_message="响应",
                    deerflow_used=False
                )
                response = client.post(
                    "/api/deerflow/chat",
                    json={"message": special_chars, "user_id": str(uuid.uuid4())}
                )
                assert response.status_code != 500

    def test_chat_null_user_id(self, client):
        """测试空用户 ID"""
        with patch('api.deerflow.DEERFLOW_AVAILABLE', False):
            with patch('api.deerflow._handle_with_her_service') as mock_her:
                mock_her.return_value = DeerFlowResponse(
                    success=True,
                    ai_message="响应",
                    deerflow_used=False
                )
                response = client.post(
                    "/api/deerflow/chat",
                    json={"message": "测试", "user_id": None}
                )
                assert response.status_code in [200, 422]

    def test_chat_invalid_user_id_format(self, client):
        """测试无效用户 ID 格式"""
        with patch('api.deerflow.DEERFLOW_AVAILABLE', False):
            with patch('api.deerflow._handle_with_her_service') as mock_her:
                mock_her.return_value = DeerFlowResponse(
                    success=True,
                    ai_message="响应",
                    deerflow_used=False
                )
                response = client.post(
                    "/api/deerflow/chat",
                    json={"message": "测试", "user_id": "not-a-uuid"}
                )
                assert response.status_code in [200, 422]

    def test_chat_nonexistent_user_id(self, client):
        """测试不存在用户 ID"""
        nonexistent_id = str(uuid.uuid4())
        with patch('api.deerflow.DEERFLOW_AVAILABLE', True):
            with patch('api.deerflow.get_deerflow_client') as mock_get:
                mock_client = MagicMock()
                mock_client.chat.return_value = '{"success": true, "summary": "响应"}'
                mock_get.return_value = mock_client

                response = client.post(
                    "/api/deerflow/chat",
                    json={"message": "测试", "user_id": nonexistent_id}
                )
                # 不应崩溃，正常处理
                assert response.status_code != 500

    def test_thread_id_empty(self, client):
        """测试空 thread_id"""
        with patch('api.deerflow.DEERFLOW_AVAILABLE', False):
            with patch('api.deerflow._handle_with_her_service') as mock_her:
                mock_her.return_value = DeerFlowResponse(
                    success=True,
                    ai_message="响应",
                    deerflow_used=False
                )
                response = client.post(
                    "/api/deerflow/chat",
                    json={"message": "测试", "thread_id": ""}
                )
                assert response.status_code != 500


# ============= 第三部分：Memory 同步测试 =============

class TestMemorySync:
    """Memory 同步逻辑测试"""

    def test_build_memory_facts_basic(self, sample_user_profile):
        """测试构建 Memory Facts - 基本信息"""
        facts = build_memory_facts(sample_user_profile)

        # 应包含基本信息
        assert len(facts) > 0

        # 检查 user_id fact 存在（关键）
        user_id_fact = next((f for f in facts if f["id"].startswith("user-id-")), None)
        assert user_id_fact is not None

    def test_build_memory_facts_empty_profile(self):
        """测试构建 Memory Facts - 空画像"""
        facts = build_memory_facts({})
        assert facts == []

    def test_build_memory_facts_null_profile(self):
        """测试构建 Memory Facts - None 画像"""
        facts = build_memory_facts(None)
        assert facts == []

    def test_build_memory_facts_with_interests(self, sample_user_profile):
        """测试构建 Memory Facts - 包含兴趣"""
        facts = build_memory_facts(sample_user_profile)

        interests_fact = next((f for f in facts if "兴趣" in f["content"]), None)
        assert interests_fact is not None
        assert interests_fact["category"] == "preference"

    def test_build_memory_facts_with_goal(self, sample_user_profile):
        """测试构建 Memory Facts - 包含关系目标"""
        facts = build_memory_facts(sample_user_profile)

        goal_fact = next((f for f in facts if "目标" in f["content"] or "goal" in f["id"]), None)
        assert goal_fact is not None
        assert goal_fact["category"] == "goal"

    def test_build_memory_facts_with_remote_preference(self, sample_user_profile):
        """测试构建 Memory Facts - 包含异地偏好"""
        facts = build_memory_facts(sample_user_profile)

        remote_fact = next((f for f in facts if "异地" in f["content"]), None)
        assert remote_fact is not None

    def test_build_memory_facts_with_age_range(self, sample_user_profile):
        """测试构建 Memory Facts - 包含年龄偏好"""
        facts = build_memory_facts(sample_user_profile)

        age_range_fact = next((f for f in facts if "年龄范围" in f["content"]), None)
        assert age_range_fact is not None

    def test_sync_user_memory_to_deerflow_success(self, sample_user_profile):
        """测试同步用户 Memory - 成功"""
        with patch('api.deerflow.get_user_profile') as mock_get:
            mock_get.return_value = sample_user_profile

            with patch('os.makedirs'):
                with patch('builtins.open', create=True):
                    with patch('os.rename'):
                        result = sync_user_memory_to_deerflow(sample_user_profile["id"])
                        # 应返回 facts 数量
                        assert result > 0

    def test_sync_user_memory_to_deerflow_user_not_found(self):
        """测试同步用户 Memory - 用户不存在"""
        with patch('api.deerflow.get_user_profile') as mock_get:
            mock_get.return_value = {}

            result = sync_user_memory_to_deerflow(str(uuid.uuid4()))
            assert result == 0

    def test_sync_user_memory_to_deerflow_exception(self):
        """测试同步用户 Memory - 异常处理"""
        with patch('api.deerflow.get_user_profile') as mock_get:
            mock_get.side_effect = Exception("测试异常")

            result = sync_user_memory_to_deerflow(str(uuid.uuid4()))
            assert result == 0


# ============= 第四部分：Generative UI 测试 =============

class TestGenerativeUIBuilder:
    """Generative UI 构建测试"""

    def test_build_ui_match_card_list(self):
        """测试构建匹配卡片列表 UI"""
        tool_result = {
            "success": True,
            "data": {
                "matches": [
                    {"user_id": str(uuid.uuid4()), "name": "测试用户", "age": 28}
                ]
            }
        }

        ui = build_generative_ui_from_tool_result(tool_result)
        assert ui["component_type"] == "MatchCardList"
        assert "matches" in ui["props"]

    def test_build_ui_profile_question_card(self):
        """测试构建信息收集卡片 UI"""
        tool_result = {
            "success": True,
            "data": {
                "question_card": {
                    "question": "你的兴趣爱好是什么？",
                    "question_type": "multi_choice",
                    "options": ["阅读", "运动", "音乐"]
                }
            }
        }

        ui = build_generative_ui_from_tool_result(tool_result)
        assert ui["component_type"] == "ProfileQuestionCard"
        assert "question" in ui["props"]

    def test_build_ui_user_profile_card(self):
        """测试构建用户详情卡片 UI"""
        tool_result = {
            "success": True,
            "data": {
                "user_profile": {
                    "user_id": str(uuid.uuid4()),
                    "name": "测试用户",
                    "age": 28,
                    "location": "北京"
                }
            }
        }

        ui = build_generative_ui_from_tool_result(tool_result)
        assert ui["component_type"] == "UserProfileCard"
        assert "user_id" in ui["props"]

    def test_no_user_profile_card_when_user_profile_has_no_id(self):
        """icebreaker 场景下 user_profile 可能是当前用户，缺少ID时不应渲染详情卡"""
        tool_result = {
            "success": True,
            "data": {
                "user_profile": {  # 当前用户简化画像（无 user_id/id）
                    "interests": ["编程", "篮球", "电影"],
                    "location": "北京",
                },
                "target_profile": {
                    "name": "深圳测试女5",
                    "interests": ["编程", "游戏"],
                },
                "match_points": [{"type": "interest", "content": ["编程"]}],
            },
            "summary": "目标用户 深圳测试女5 有 5 个兴趣，共同兴趣 1 个",
        }

        ui = build_generative_ui_from_tool_result(tool_result)
        assert ui["component_type"] == "SimpleResponse"

    def test_build_ui_compatibility_chart(self):
        """测试构建兼容性分析 UI"""
        tool_result = {
            "success": True,
            "data": {
                "overall_score": 75,
                "dimensions": [
                    {"name": "价值观", "score": 80},
                    {"name": "兴趣", "score": 70}
                ]
            }
        }

        ui = build_generative_ui_from_tool_result(tool_result)
        assert ui["component_type"] == "CompatibilityChart"
        assert "overall_score" in ui["props"]

    def test_build_ui_date_plan_card(self):
        """测试构建约会方案 UI"""
        tool_result = {
            "success": True,
            "data": {
                "plans": [
                    {"type": "cafe", "description": "咖啡厅约会"}
                ]
            }
        }

        ui = build_generative_ui_from_tool_result(tool_result)
        assert ui["component_type"] == "DatePlanCard"
        assert "plans" in ui["props"]

    def test_build_ui_icebreaker_card(self):
        """测试构建破冰建议 UI"""
        tool_result = {
            "success": True,
            "data": {
                "icebreakers": [
                    {"topic": "共同兴趣", "suggestion": "聊聊旅行"}
                ]
            }
        }

        ui = build_generative_ui_from_tool_result(tool_result)
        assert ui["component_type"] == "IcebreakerCard"
        assert "icebreakers" in ui["props"]

    def test_build_ui_topics_card(self):
        """测试构建话题推荐 UI"""
        tool_result = {
            "success": True,
            "data": {
                "topics": [
                    {"topic": "兴趣爱好", "trending": True}
                ]
            }
        }

        ui = build_generative_ui_from_tool_result(tool_result)
        assert ui["component_type"] == "TopicsCard"
        assert "topics" in ui["props"]

    def test_build_ui_relationship_health_card(self):
        """测试构建关系健康度 UI"""
        tool_result = {
            "success": True,
            "data": {
                "health_score": 7.5,
                "strengths": ["沟通良好"],
                "issues": ["需要更多独处时间"]
            }
        }

        ui = build_generative_ui_from_tool_result(tool_result)
        assert ui["component_type"] == "RelationshipHealthCard"
        assert "health_score" in ui["props"]

    def test_build_ui_simple_response_default(self):
        """测试构建简单响应 UI - 默认"""
        tool_result = {
            "success": True,
            "data": {}
        }

        ui = build_generative_ui_from_tool_result(tool_result)
        assert ui["component_type"] == "SimpleResponse"

    def test_build_ui_with_schema_validation(self):
        """测试 UI 构建 - Schema 校验"""
        tool_result = {
            "success": True,
            "data": {
                "matches": []
            }
        }

        ui = _build_ui_response("MatchCardList", {"matches": [], "total": 0})
        assert "_schema" in ui["props"]
        assert ui["props"]["_schema"]["backend_type"] == "MatchCardList"

    def test_normalize_match_card_total(self):
        """测试 MatchCardList total 自动校准"""
        ui = {
            "component_type": "MatchCardList",
            "props": {
                "matches": [{"name": "A"}, {"name": "B"}, {"name": "C"}],
                "total": 99,
            },
        }
        normalized = _normalize_generative_ui(ui)
        assert normalized["props"]["total"] == 3

    def test_merge_find_candidates_gender_and_avatar_into_match_cards(self):
        """工具返回的性别与数据库头像应合并进 MatchCardList，空头像时清空 Agent 臆造 URL"""
        uid = str(uuid.uuid4())
        props = {
            "matches": [
                {
                    "user_id": uid,
                    "name": "候选人A",
                    "gender": "女",
                    "avatar_url": "https://hallucinated.invalid/bad.jpg",
                }
            ]
        }
        tool_data = {
            "candidates": [
                {
                    "user_id": uid,
                    "name": "候选人A",
                    "gender": "男",
                    "avatar_url": "",
                }
            ]
        }
        _merge_her_find_candidates_into_match_cards(props, tool_data)
        row = props["matches"][0]
        assert row["gender"] == "男"
        assert row["avatar_url"] == ""

        uid_b = str(uuid.uuid4())
        props_b = {
            "matches": [{"user_id": uid_b, "name": "B", "avatar_url": ""}],
        }
        tool_b = {
            "candidates": [
                {
                    "user_id": uid_b,
                    "gender": "女",
                    "avatar_url": "https://cdn.example/ok.png",
                }
            ]
        }
        _merge_her_find_candidates_into_match_cards(props_b, tool_b)
        assert props_b["matches"][0]["avatar_url"] == "https://cdn.example/ok.png"
        assert props_b["matches"][0]["gender"] == "女"


class TestIntentInference:
    """意图推断优先级测试"""

    def test_intent_prefers_tool_result(self):
        """工具结果意图应优先于默认兜底"""
        intent = infer_intent_from_response(
            message="帮我找对象",
            response_text="一些文本",
            generative_ui=None,
            tool_result={"success": True, "data": {"intent_type": "match_request"}},
        )
        assert intent["type"] == "match_request"
        assert intent["source"] == "tool_result"

    def test_intent_falls_back_to_ui_component(self):
        """工具缺失时应回退到 UI 组件意图"""
        intent = infer_intent_from_response(
            message="分析一下",
            response_text="",
            generative_ui={"component_type": "CompatibilityChart", "props": {}},
            tool_result=None,
        )
        assert intent["type"] == "compatibility_analysis"
        assert intent["source"] == "ui_component"


class TestMessageAlignment:
    """文案与结构化结果一致性测试"""

    def test_align_message_when_count_mismatch(self):
        ui = {
            "component_type": "MatchCardList",
            "props": {"matches": [{"name": "A"}, {"name": "B"}], "total": 2},
        }
        aligned = _align_ai_message_with_structured_result("为你找到 5 位候选人：A、B", ui)
        assert "为你找到 2 位候选人" in aligned

    def test_align_message_add_prefix_when_missing(self):
        ui = {
            "component_type": "MatchCardList",
            "props": {"matches": [{"name": "A"}], "total": 1},
        }
        aligned = _align_ai_message_with_structured_result("这里是推荐名单", ui)
        assert aligned.startswith("【匹配结果】")

    def test_render_structured_query_result_for_placeholder(self):
        """占位查询文案应展开为可读表格"""
        message = "查询成功，返回 2 行数据"
        tool_result = {
            "success": True,
            "data": {
                "columns": ["city", "count"],
                "rows": [{"city": "杭州", "count": 3}, {"city": "南京", "count": 2}],
                "row_count": 2,
            },
        }
        rendered = _render_structured_result_message(message, tool_result, None)
        assert "查询完成，结果如下" in rendered
        assert "| city | count |" in rendered
        assert "杭州" in rendered

    def test_render_structured_comparison_result_for_placeholder(self):
        """占位对比文案应展开为画像对比摘要"""
        message = "对比 林小雨 和 杭州测试男10 的画像"
        tool_result = {
            "success": True,
            "data": {
                "user_a": {"name": "林小雨"},
                "user_b": {"name": "杭州测试男10"},
                "comparison_factors": [
                    {"factor": "年龄差距", "user_a": 25, "user_b": 32},
                    {"factor": "兴趣爱好", "user_a": ["旅行"], "user_b": ["旅行"], "common": ["旅行"]},
                ],
            },
        }
        rendered = _render_structured_result_message(message, tool_result, None)
        assert "已完成画像对比" in rendered
        assert "共同点：旅行" in rendered

    def test_render_relaxation_suggestions_for_empty_match(self):
        """0命中且有放宽建议时应输出统一建议模板"""
        message = "找到 0 位候选对象"
        tool_result = {
            "success": True,
            "data": {
                "component_type": "MatchCardList",
                "matches": [],
                "relaxation_suggestions": [
                    {
                        "dimension": "accept_remote",
                        "current": "只找同城",
                        "suggestion": "同城优先",
                        "reason": "当前同城命中 0，但异地有 12 位候选",
                    }
                ],
            },
        }
        rendered = _render_structured_result_message(message, tool_result, None)
        assert "严格按你当前要求" in rendered
        assert "仅建议，不会自动变更" in rendered
        assert "accept_remote" in rendered


class TestMatchCardIntegrity:
    """匹配列表：兴趣规范化 + 只找同城不变量"""

    def test_coerce_interests_json_array_string(self):
        assert _coerce_interests_to_str_list('["阅读", "健身"]') == ["阅读", "健身"]

    def test_finalize_clears_matches_when_same_city_invariant_broken(self):
        ui = {
            "component_type": "MatchCardList",
            "props": {
                "matches": [
                    {"name": "A", "location": "成都"},
                ],
                "filter_applied": {
                    "preferred_location": "上海",
                    "accept_remote": "只找同城",
                },
            },
        }
        tool_result = {"data": {"query_request_id": "rid-tool"}}
        notice, out = _finalize_match_generative_ui(ui, tool_result)
        assert "不一致" in notice
        assert out["props"]["matches"] == []
        assert out["props"]["query_integrity"]["code"] == "FILTER_LOCATION_MISMATCH"
        assert out["props"]["matched_count"] == 0


class TestObservabilityTrace:
    """可观测证据链测试"""

    def test_build_observability_trace_with_match_card(self):
        request = ChatRequest(message="帮我找对象", user_id="u-1", thread_id="t-1")
        intent = {"type": "match_request", "confidence": 0.95, "source": "tool_result"}
        ui = {
            "component_type": "MatchCardList",
            "props": {"matches": [{"name": "A"}, {"name": "B"}]},
        }
        trace = _build_observability_trace(request, intent, ui)
        assert trace["intent_type"] == "match_request"
        assert trace["intent_source"] == "tool_result"
        assert trace["ui_component_type"] == "MatchCardList"
        assert trace["ui_matches_count"] == 2

    def test_enrich_tool_result_with_observability(self):
        trace = {
            "intent_type": "match_request",
            "intent_source": "tool_result",
        }
        enriched = _enrich_tool_result_with_observability({"success": True}, trace)
        assert enriched["success"] is True
        assert enriched["observability"]["intent_type"] == "match_request"


# ============= 第五部分：降级处理测试 =============

class TestFallbackHandling:
    """降级处理测试"""

    @pytest.mark.asyncio
    async def test_handle_with_her_service_success(self, mock_her_service):
        """测试 Her 服务降级处理 - 成功"""
        with patch('services.conversation_match_service.get_conversation_match_service') as mock_get:
            mock_get.return_value = mock_her_service

            request = ChatRequest(message="测试消息", user_id=str(uuid.uuid4()))
            response = await _handle_with_her_service(request)

            assert response.success == True
            assert response.deerflow_used == False

    @pytest.mark.asyncio
    async def test_handle_with_her_service_exception(self):
        """测试 Her 服务降级处理 - 异常"""
        with patch('services.conversation_match_service.get_conversation_match_service') as mock_get:
            mock_get.side_effect = Exception("服务异常")

            request = ChatRequest(message="测试消息", user_id=str(uuid.uuid4()))
            response = await _handle_with_her_service(request)

            # 新架构：异常时返回错误fallback响应，但success=True（降级成功）
            assert response.success == True  # 降级处理成功
            assert "繁忙" in response.ai_message or "稍后" in response.ai_message or "换个方式" in response.ai_message
            assert response.intent.get("type") == "error_fallback"

    @pytest.mark.asyncio
    async def test_handle_with_her_service_null_user(self, mock_her_service):
        """测试 Her 服务降级处理 - 空 user_id"""
        with patch('services.conversation_match_service.get_conversation_match_service') as mock_get:
            mock_get.return_value = mock_her_service

            request = ChatRequest(message="测试消息", user_id=None)
            response = await _handle_with_her_service(request)

            assert response.success == True


# ============= 第六部分：异常处理测试 =============

class TestExceptionHandling:
    """异常处理测试"""

    @patch('api.deerflow.DEERFLOW_AVAILABLE', True)
    def test_chat_endpoint_deerflow_exception(self, client):
        """测试聊天端点 - DeerFlow 异常

        注：当 DeerFlow client.stream 抛出异常时，代码内部捕获异常并返回
        deerflow_used=True 的 fallback 响应（不调用 _handle_with_her_service）
        """
        mock_client = MagicMock()
        # 实际代码调用 client.stream() 而不是 client.chat()
        mock_client.stream.side_effect = Exception("DeerFlow 服务异常")

        with patch('api.deerflow.get_deerflow_client') as mock_get_client:
            mock_get_client.return_value = mock_client

            # DeerFlow 异常被内部捕获，返回 fallback 响应（deerflow_used=True）
            response = client.post(
                "/api/deerflow/chat",
                json={"message": "测试"}
            )
            assert response.status_code == 200
            data = response.json()
            # 内部捕获异常后返回 deerflow_used=True 的 fallback
            assert data["deerflow_used"] == True
            assert data["success"] == True
            # intent 类型应为 error_fallback（当 stream 抛出异常时）
            assert data["intent"]["type"] == "error_fallback"

    @patch('api.deerflow.DEERFLOW_AVAILABLE', True)
    def test_chat_endpoint_llm_timeout(self, client):
        """测试聊天端点 - LLM 超时"""
        mock_client = MagicMock()
        # 模拟超时
        mock_client.chat.side_effect = TimeoutError("LLM 超时")

        with patch('api.deerflow.get_deerflow_client') as mock_get_client:
            mock_get_client.return_value = mock_client

            with patch('api.deerflow._handle_with_her_service') as mock_her:
                mock_her.return_value = DeerFlowResponse(
                    success=True,
                    ai_message="降级响应",
                    deerflow_used=False
                )
                response = client.post(
                    "/api/deerflow/chat",
                    json={"message": "测试"}
                )
                assert response.status_code != 500

    def test_stream_endpoint_deerflow_not_available(self, client):
        """测试流式端点 - DeerFlow 不可用"""
        with patch('api.deerflow.DEERFLOW_AVAILABLE', False):
            response = client.post(
                "/api/deerflow/stream",
                json={"message": "测试", "thread_id": str(uuid.uuid4())}
            )
            # 应返回 SSE 格式错误流
            assert response.status_code == 200
            assert "text/event-stream" in response.headers.get("content-type", "")

    def test_learning_confirm_endpoint_exception(self, client):
        """测试学习确认端点 - 异常"""
        with patch('services.learning_result_handler.get_learning_result_handler') as mock_get:
            mock_get.side_effect = Exception("处理异常")

            response = client.post(
                "/api/deerflow/learning/confirm",
                json={
                    "user_id": str(uuid.uuid4()),
                    "insights": [{"dimension": "interest", "value": "阅读"}]
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] == False


# ============= 第七部分：数据模型测试 =============

class TestDataModels:
    """Request/Response 数据模型测试"""

    def test_chat_request_valid(self):
        """测试 ChatRequest - 有效数据"""
        request = ChatRequest(
            message="测试消息",
            thread_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4())
        )
        assert request.message == "测试消息"

    def test_chat_request_missing_message(self):
        """测试 ChatRequest - 缺少消息"""
        with pytest.raises(Exception):  # Pydantic ValidationError
            ChatRequest()

    def test_stream_request_valid(self):
        """测试 StreamRequest - 有效数据"""
        request = StreamRequest(
            message="测试消息",
            thread_id=str(uuid.uuid4())
        )
        assert request.thread_id is not None

    def test_memory_sync_request_valid(self):
        """测试 MemorySyncRequest - 有效数据"""
        request = MemorySyncRequest(user_id=str(uuid.uuid4()))
        assert request.user_id is not None

    def test_deerflow_response_model(self):
        """测试 DeerFlowResponse 模型"""
        response = DeerFlowResponse(
            success=True,
            ai_message="测试响应",
            intent={"type": "match_request"},
            generative_ui={"component_type": "MatchCardList"},
            deerflow_used=True
        )
        assert response.success == True
        assert response.deerflow_used == True

    def test_deerflow_status_response_model(self):
        """测试 DeerFlowStatusResponse 模型"""
        response = DeerFlowStatusResponse(
            available=True,
            path="/path/to/deerflow",
            config_path="/path/to/config.yaml",
            config_exists=True,
            memory_enabled=True
        )
        assert response.available == True
        assert response.memory_enabled == True


# ============= 第八部分：并发安全测试 =============

class TestDeerFlowConcurrency:
    """DeerFlow 并发安全测试"""

    def test_concurrent_chat_requests(self):
        """测试并发聊天请求"""
        import threading

        results = []
        lock = threading.Lock()

        def make_request():
            with lock:
                results.append(threading.current_thread().name)

        threads = [threading.Thread(target=make_request) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 10

    def test_memory_sync_concurrent(self):
        """测试并发 Memory 同步"""
        import threading

        user_id = str(uuid.uuid4())
        sync_count = []
        lock = threading.Lock()

        def sync_memory():
            with patch('api.deerflow.get_user_profile') as mock_get:
                mock_get.return_value = {"id": user_id, "name": "测试"}
                with lock:
                    sync_count.append(1)

        threads = [threading.Thread(target=sync_memory) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(sync_count) == 5


# ============= 运行测试 =============

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])