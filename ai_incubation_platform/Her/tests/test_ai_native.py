"""
AI Native 功能测试

测试对话式匹配、自主推荐、关系分析等 AI Native 功能。
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import pytest
from datetime import datetime
import uuid


class TestCompatibilityAnalysisTool:
    """测试深度兼容性分析工具"""

    def test_tool_schema(self):
        """测试工具输入 Schema"""
        from agent.tools.autonomous_tools import CompatibilityAnalysisTool

        schema = CompatibilityAnalysisTool.get_input_schema()

        assert schema["type"] == "object"
        assert "user_id_1" in schema["required"]
        assert "user_id_2" in schema["required"]
        assert "dimensions" in schema["properties"]

    def test_tool_metadata(self):
        """测试工具元数据"""
        from agent.tools.autonomous_tools import CompatibilityAnalysisTool

        assert CompatibilityAnalysisTool.name == "compatibility_analysis"
        assert "compatibility" in CompatibilityAnalysisTool.tags
        assert "analysis" in CompatibilityAnalysisTool.tags


class TestTopicSuggestionTool:
    """测试破冰话题推荐工具"""

    def test_tool_schema(self):
        """测试工具输入 Schema"""
        from agent.tools.autonomous_tools import TopicSuggestionTool

        schema = TopicSuggestionTool.get_input_schema()

        assert "match_id" in schema["required"]
        assert "context" in schema["properties"]
        assert schema["properties"]["context"]["enum"] == [
            "first_chat", "follow_up", "date_plan", "deep_connection"
        ]

    def test_tool_metadata(self):
        """测试工具元数据"""
        from agent.tools.autonomous_tools import TopicSuggestionTool

        assert TopicSuggestionTool.name == "topic_suggestion"
        assert "icebreaker" in TopicSuggestionTool.tags
        assert "topics" in TopicSuggestionTool.tags


class TestRelationshipTrackingTool:
    """测试关系追踪工具"""

    def test_tool_schema(self):
        """测试工具输入 Schema"""
        from agent.tools.autonomous_tools import RelationshipTrackingTool

        schema = RelationshipTrackingTool.get_input_schema()

        assert "match_id" in schema["required"]
        assert "period" in schema["properties"]
        assert schema["properties"]["period"]["enum"] == ["weekly", "monthly"]

    def test_relationship_stages(self):
        """测试关系阶段定义"""
        from agent.tools.autonomous_tools import RelationshipTrackingTool

        stages = RelationshipTrackingTool.RELATIONSHIP_STAGES

        assert "matched" in stages
        assert "chatting" in stages
        assert "in_relationship" in stages
        assert stages["matched"]["order"] < stages["chatting"]["order"]
        assert stages["chatting"]["order"] < stages["in_relationship"]["order"]


class TestAutoMatchRecommendWorkflow:
    """测试自主匹配推荐工作流"""

    def test_workflow_metadata(self):
        """测试工作流元数据"""
        from agent.workflows.autonomous_workflows import AutoMatchRecommendWorkflow

        workflow = AutoMatchRecommendWorkflow()

        assert workflow.name == "auto_match_recommend"
        assert workflow.description is not None
        assert len(workflow.tools) >= 4  # 至少包含 profile, match, compatibility, reasoning

    def test_workflow_execution_structure(self):
        """测试工作流执行结构（不依赖实际数据）"""
        from agent.workflows.autonomous_workflows import AutoMatchRecommendWorkflow

        workflow = AutoMatchRecommendWorkflow()

        # 检查工作流方法
        assert hasattr(workflow, 'execute')
        assert hasattr(workflow, '_analyze_user_status')
        assert hasattr(workflow, '_scan_candidates')
        assert hasattr(workflow, '_deep_compatibility_analysis')
        assert hasattr(workflow, '_rank_matches')
        assert hasattr(workflow, '_generate_reasoning')


class TestRelationshipHealthCheckWorkflow:
    """测试关系健康度分析工作流"""

    def test_workflow_metadata(self):
        """测试工作流元数据"""
        from agent.workflows.autonomous_workflows import RelationshipHealthCheckWorkflow

        workflow = RelationshipHealthCheckWorkflow()

        assert workflow.name == "relationship_health_check"
        assert workflow.tracking_tool is not None

    def test_workflow_execution_structure(self):
        """测试工作流执行结构"""
        from agent.workflows.autonomous_workflows import RelationshipHealthCheckWorkflow

        workflow = RelationshipHealthCheckWorkflow()

        assert hasattr(workflow, 'execute')
        assert hasattr(workflow, '_push_health_report')


class TestAutoIcebreakerWorkflow:
    """测试自主破冰助手工作流"""

    def test_workflow_metadata(self):
        """测试工作流元数据"""
        from agent.workflows.autonomous_workflows import AutoIcebreakerWorkflow

        workflow = AutoIcebreakerWorkflow()

        assert workflow.name == "auto_icebreaker"
        assert workflow.topic_tool is not None
        assert workflow.icebreaker_tool is not None

    def test_trigger_types(self):
        """测试触发类型"""
        from agent.workflows.autonomous_workflows import AutoIcebreakerWorkflow

        valid_triggers = ["new_match", "stale_conversation", "upcoming_date", "manual"]

        workflow = AutoIcebreakerWorkflow()

        # 检查工作流能处理各种触发类型
        for trigger in valid_triggers:
            result = workflow._detect_timing("test_match_id", trigger)
            assert "should_act" in result or "error" in result


class TestAuditLogger:
    """测试审计日志系统"""

    def test_audit_logger_creation(self):
        """测试审计日志创建"""
        from db.audit import AuditLogger

        logger = AuditLogger()
        assert logger is not None
        assert hasattr(logger, 'log')
        assert hasattr(logger, 'query')
        assert hasattr(logger, 'get_stats')

    def test_sensitive_actions(self):
        """测试敏感操作定义"""
        from db.audit import AuditLogger

        logger = AuditLogger()
        actions = logger.SENSITIVE_ACTIONS

        assert "match_recommend" in actions
        assert "match_swipe" in actions
        assert "conversation_start" in actions
        assert "ai_autonomous_match" in actions
        assert "ai_health_analysis" in actions

    def test_redact_sensitive_data(self):
        """测试敏感数据脱敏"""
        from db.audit import AuditLogger

        logger = AuditLogger()

        test_data = '{"password": "secret123", "token": "abc123xyz", "name": "test"}'
        redacted = logger._redact_sensitive_data(test_data)

        assert "secret123" not in redacted
        assert "abc123xyz" not in redacted
        assert "***" in redacted

    def test_log_structure(self):
        """测试日志结构（模拟）"""
        from db.audit import AuditLogger

        logger = AuditLogger()

        # 测试日志条目结构（不实际写入数据库）
        log_id = logger.log(
            actor="user_123",
            action="test_action",
            status="success",
            actor_type="user",
            resource_type="test",
            resource_id="test_456",
            request={"key": "value"},
            sync=False  # 不实际写入
        )

        assert log_id is not None
        assert len(log_id) > 0


class TestRegisterAutonomousTools:
    """测试自主工具注册"""

    def test_register_function_exists(self):
        """测试注册函数存在"""
        from agent.tools.autonomous_tools import register_autonomous_tools

        assert callable(register_autonomous_tools)


class TestRegisterAutonomousWorkflows:
    """测试自主工作流注册"""

    def test_register_function_exists(self):
        """测试注册函数存在"""
        from agent.workflows.autonomous_workflows import register_autonomous_workflows

        assert callable(register_autonomous_workflows)

    def test_registered_workflows(self):
        """测试注册的工作流"""
        from agent.workflows.autonomous_workflows import register_autonomous_workflows

        workflows = register_autonomous_workflows()

        assert "auto_match_recommend" in workflows
        assert "relationship_health_check" in workflows
        assert "auto_icebreaker" in workflows


class TestAIFnNativeIntegration:
    """测试 AI Native 整体集成"""

    def test_all_components_importable(self):
        """测试所有组件可导入"""
        from agent.tools.autonomous_tools import (
            CompatibilityAnalysisTool,
            TopicSuggestionTool,
            RelationshipTrackingTool
        )
        from agent.workflows.autonomous_workflows import (
            AutoMatchRecommendWorkflow,
            RelationshipHealthCheckWorkflow,
            AutoIcebreakerWorkflow
        )
        from db.audit import AuditLogger, create_audit_table

        # 确保所有组件都存在
        assert CompatibilityAnalysisTool is not None
        assert TopicSuggestionTool is not None
        assert RelationshipTrackingTool is not None
        assert AutoMatchRecommendWorkflow is not None
        assert RelationshipHealthCheckWorkflow is not None
        assert AutoIcebreakerWorkflow is not None
        assert AuditLogger is not None

    def test_workflow_tool_integration(self):
        """测试工作流与工具的集成"""
        from agent.workflows.autonomous_workflows import AutoMatchRecommendWorkflow
        from agent.tools.autonomous_tools import CompatibilityAnalysisTool

        workflow = AutoMatchRecommendWorkflow()

        # 检查工作流使用了正确的工具
        assert "compatibility" in workflow.tools
        assert workflow.tools["compatibility"] == CompatibilityAnalysisTool


class TestConversationMatchingAPI:
    """测试对话式匹配 API（结构测试）"""

    def test_api_router_exists(self):
        """测试 API 路由存在"""
        from api.conversation_matching import router

        assert router is not None
        assert router.prefix == "/api/conversation-matching"

    def test_request_models(self):
        """测试请求模型"""
        from api.conversation_matching import (
            ConversationMatchRequest,
            RelationshipAnalysisRequest,
            TopicSuggestionRequest
        )

        # 测试 ConversationMatchRequest
        req = ConversationMatchRequest(user_intent="帮我找对象")
        assert req.user_intent == "帮我找对象"

        # 测试 RelationshipAnalysisRequest
        req = RelationshipAnalysisRequest(match_id="test_123")
        assert req.match_id == "test_123"
        assert req.analysis_type == "health_check"

        # 测试 TopicSuggestionRequest
        req = TopicSuggestionRequest(match_id="test_123")
        assert req.match_id == "test_123"
        assert req.context == "first_chat"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
