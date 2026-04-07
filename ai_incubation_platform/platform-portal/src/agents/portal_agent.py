"""
Portal Agent - AI 孵化平台统一门户智能体

这是 platform-portal 的核心 AI Agent，负责：
1. 意图识别：分析用户需求属于哪个子项目领域
2. 路由分发：将请求转发到对应子项目 Agent
3. 跨项目编排：协调多个子项目完成复杂任务

AI Native 架构原则：
- AI 是前台接待：统一接待用户请求，分发给对应子项目
- AI 是导航员：理解用户意图，推荐合适的子项目
- AI 是协调员：跨项目工作流自动编排
"""
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from tools.intent_tools import identify_intent
from tools.routing_tools import route_to_project, aggregate_results, cross_project_workflow
from tools.registry import TOOLS_REGISTRY, list_tools

logger = logging.getLogger(__name__)


# 预定义的跨项目工作流模板
WORKFLOW_TEMPLATES = {
    "startup_journey": {
        "description": "创业旅程 - 为想要创业的用户提供全方位支持",
        "projects": ["ai-opportunity-miner", "ai-hires-human", "ai-community-buying"],
        "workflow": [
            {"step": 1, "project": "ai-opportunity-miner", "action": "discover_opportunities"},
            {"step": 2, "project": "ai-hires-human", "action": "post_tasks"},
            {"step": 3, "project": "ai-community-buying", "action": "find_resources"},
        ],
    },
    "talent_pipeline": {
        "description": "人才管道 - 构建企业人才供应链",
        "projects": ["ai-employee-platform", "human-ai-community", "ai-hires-human"],
        "workflow": [
            {"step": 1, "project": "ai-employee-platform", "action": "find_candidates"},
            {"step": 2, "project": "human-ai-community", "action": "check_reputation"},
            {"step": 3, "project": "ai-hires-human", "action": "create_contract"},
        ],
    },
    "full_stack_analysis": {
        "description": "全栈分析 - 全面分析系统性能和代码质量",
        "projects": ["ai-code-understanding", "loganalyzer-agent", "ai-runtime-optimizer"],
        "workflow": [
            {"step": 1, "project": "ai-code-understanding", "action": "analyze_code"},
            {"step": 2, "project": "loganalyzer-agent", "action": "analyze_logs"},
            {"step": 3, "project": "ai-runtime-optimizer", "action": "optimize_performance"},
        ],
    },
    "community_growth": {
        "description": "社区增长 - 促进社区活跃度和成员增长",
        "projects": ["human-ai-community", "ai-traffic-booster", "matchmaker-agent"],
        "workflow": [
            {"step": 1, "project": "human-ai-community", "action": "analyze_engagement"},
            {"step": 2, "project": "ai-traffic-booster", "action": "boost_traffic"},
            {"step": 3, "project": "matchmaker-agent", "action": "match_members"},
        ],
    },
}


class PortalAgent:
    """
    门户智能体 - AI 孵化平台的统一入口

    这是 AI Native 架构的核心组件，提供：
    - 对话式交互界面
    - 智能意图识别
    - 自主路由决策
    - 跨项目编排能力
    """

    def __init__(self, deerflow_api_key: Optional[str] = None):
        """
        初始化门户智能体

        Args:
            deerflow_api_key: DeerFlow API 密钥（可选，用于增强 AI 能力）
        """
        self._context: Dict[str, Any] = {}
        self._session_id: Optional[str] = None
        self._request_history: List[Dict[str, Any]] = []
        self._deerflow_api_key = deerflow_api_key

        # 置信度阈值配置
        self._auto_route_threshold = 0.8  # 自动路由阈值
        self._clarification_threshold = 0.5  # 需要澄清的阈值

        logger.info("PortalAgent initialized")

    async def chat(
        self,
        message: str,
        user_id: str,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        对话式交互入口 - AI Native 核心接口

        用户通过自然语言与门户交互，Agent 自主决策如何处理请求。

        Args:
            message: 用户自然语言消息
            user_id: 用户 ID
            session_id: 会话 ID（可选，用于上下文连续性）
            context: 额外上下文信息

        Returns:
            Agent 响应，包含：
            - response: 响应消息
            - action: 采取的行动
            - project: 路由到的项目（如果有）
            - confidence: 置信度
            - suggestions: 后续建议
        """
        self._session_id = session_id or str(uuid.uuid4())

        logger.info(f"[Session {self._session_id}] User {user_id}: {message[:100]}...")

        # 1. 意图识别
        intent_result = await identify_intent(message)
        project = intent_result.get("project", "platform-portal")
        confidence = intent_result.get("confidence", 0.5)

        logger.info(f"[Session {self._session_id}] Intent: {project} (confidence: {confidence:.2f})")

        # 2. 根据置信度决定行动
        if confidence < self._clarification_threshold:
            # 置信度过低，需要用户澄清
            response = await self._ask_for_clarification(message, intent_result)
            action = "clarify"
        elif project == "platform-portal":
            # 用户询问门户本身或使用跨项目功能
            response = await self._handle_portal_query(message, intent_result)
            action = "portal_query"
        elif confidence >= self._auto_route_threshold:
            # 高置信度，直接路由
            response = await self._auto_route_to_project(project, message, user_id, intent_result)
            action = "auto_route"
        else:
            # 中等置信度，提供推荐并请求确认
            response = await self._recommend_and_confirm(project, message, intent_result)
            action = "recommend"

        # 3. 记录请求历史
        self._record_request(message, response, intent_result)

        # 4. 更新上下文
        if context:
            self._context.update(context)

        return {
            "session_id": self._session_id,
            "user_id": user_id,
            "message": message,
            "response": response,
            "action": action,
            "project": project,
            "confidence": confidence,
            "timestamp": datetime.now().isoformat(),
        }

    async def _ask_for_clarification(
        self,
        message: str,
        intent_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """请求用户澄清意图"""
        alternatives = intent_result.get("alternative_projects", [])

        clarification_text = "我不太确定您的需求，请问您是想：\n\n"

        if alternatives:
            for i, alt in enumerate(alternatives[:3], 1):
                project = alt.get("project", "unknown")
                desc = self._get_project_description(project)
                clarification_text += f"{i}. {desc}\n"

        clarification_text += "\n或者您可以更详细地描述您的需求。"

        return {
            "type": "clarification",
            "message": clarification_text,
            "suggestions": [alt.get("project") for alt in alternatives[:3]],
        }

    async def _handle_portal_query(
        self,
        message: str,
        intent_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """处理门户相关查询"""
        # 检查是否是跨项目工作流请求
        workflow_match = self._detect_workflow_request(message)

        if workflow_match:
            workflow_name = workflow_match["workflow"]
            return await self._execute_workflow(workflow_name, {"user_message": message})

        # 返回门户介绍和项目列表
        project_list = self._get_project_list()

        return {
            "type": "portal_info",
            "message": f"欢迎使用 AI 孵化平台门户！我可以帮助您访问以下子项目：\n\n{project_list}",
            "projects": list(self._get_all_projects().keys()),
            "workflows": list(WORKFLOW_TEMPLATES.keys()),
        }

    async def _auto_route_to_project(
        self,
        project: str,
        message: str,
        user_id: str,
        intent_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """自动路由到子项目"""
        logger.info(f"Auto-routing to {project}")

        # 构建路由负载
        payload = {
            "user_id": user_id,
            "message": message,
            "session_id": self._session_id,
            "context": self._context,
            "intent": intent_result,
        }

        # 调用路由工具
        try:
            result = await route_to_project(project=project, payload=payload)

            if result.get("success"):
                return {
                    "type": "routed",
                    "project": project,
                    "data": result.get("data"),
                    "message": f"已将您的请求转发到 {project}，正在处理中...",
                }
            else:
                return {
                    "type": "error",
                    "project": project,
                    "error": result.get("error"),
                    "message": f"路由到 {project} 失败：{result.get('error')}",
                }

        except Exception as e:
            logger.error(f"Failed to route to {project}: {e}")
            return {
                "type": "error",
                "project": project,
                "error": str(e),
                "message": f"处理请求时发生错误：{str(e)}",
            }

    async def _recommend_and_confirm(
        self,
        project: str,
        message: str,
        intent_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """推荐项目并请求确认"""
        project_desc = self._get_project_description(project)
        confidence = intent_result.get("confidence", 0.5)

        return {
            "type": "recommendation",
            "message": f"根据您的描述，我建议您使用 **{project}**。\n\n"
                       f"**项目说明**: {project_desc}\n"
                       f"**匹配度**: {confidence:.0%}\n\n"
                       f"请问是否需要我帮您转接到该项目？",
            "recommended_project": project,
            "confidence": confidence,
            "alternatives": intent_result.get("alternative_projects", []),
        }

    async def execute_workflow(
        self,
        workflow_name: str,
        user_id: str,
        input_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        执行跨项目工作流

        Args:
            workflow_name: 工作流名称
            user_id: 用户 ID
            input_data: 输入数据

        Returns:
            工作流执行结果
        """
        logger.info(f"Executing workflow: {workflow_name}")

        if workflow_name not in WORKFLOW_TEMPLATES:
            return {
                "success": False,
                "error": f"Unknown workflow: {workflow_name}",
                "available_workflows": list(WORKFLOW_TEMPLATES.keys()),
            }

        template = WORKFLOW_TEMPLATES[workflow_name]
        projects_involved = template["projects"]

        result = await cross_project_workflow(
            workflow_name=workflow_name,
            projects_involved=projects_involved,
            input_data=input_data or {"user_id": user_id},
        )

        return {
            "success": True,
            "workflow_name": workflow_name,
            "description": template["description"],
            "projects_involved": projects_involved,
            "results": result,
        }

    def _detect_workflow_request(self, message: str) -> Optional[Dict[str, Any]]:
        """检测用户是否请求执行工作流"""
        message_lower = message.lower()

        # 关键词匹配工作流
        workflow_keywords = {
            "startup_journey": ["创业", "startup", "开办公司", "创办"],
            "talent_pipeline": ["招聘", "人才", "招聘流程", "hiring"],
            "full_stack_analysis": ["代码分析", "性能分析", "系统分析", "analysis"],
            "community_growth": ["社区运营", "社区增长", "community"],
        }

        for workflow_name, keywords in workflow_keywords.items():
            if any(kw in message_lower for kw in keywords):
                return {"workflow": workflow_name, "confidence": 0.8}

        return None

    async def _execute_workflow(
        self,
        workflow_name: str,
        input_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """执行工作流并返回响应"""
        user_id = input_data.get("user_id", "anonymous")

        result = await self.execute_workflow(workflow_name, user_id, input_data)

        if result.get("success"):
            return {
                "type": "workflow_result",
                "workflow_name": workflow_name,
                "description": result.get("description"),
                "projects_involved": result.get("projects_involved"),
                "message": f"已启动跨项目工作流 '{workflow_name}'，正在协调 {len(result.get('projects_involved', []))} 个子项目...",
                "results": result.get("results"),
            }
        else:
            return {
                "type": "error",
                "error": result.get("error"),
                "available_workflows": result.get("available_workflows"),
            }

    def _get_project_description(self, project: str) -> str:
        """获取项目描述"""
        projects = self._get_all_projects()
        if project in projects:
            return projects[project].get("description", "未知项目")
        return "未知项目"

    def _get_project_list(self) -> str:
        """获取项目列表字符串"""
        projects = self._get_all_projects()
        lines = []
        for name, info in projects.items():
            lines.append(f"- **{name}**: {info.get('description', 'N/A')[:50]}...")
        return "\n".join(lines)

    def _get_all_projects(self) -> Dict[str, Any]:
        """获取所有子项目信息"""
        # 从意图识别工具导入
        from tools.intent_tools import SUB_PROJECTS
        return SUB_PROJECTS

    def _record_request(
        self,
        message: str,
        response: Dict[str, Any],
        intent_result: Dict[str, Any],
    ) -> None:
        """记录请求历史"""
        self._request_history.append({
            "message": message,
            "response": response,
            "intent": intent_result,
            "timestamp": datetime.now().isoformat(),
            "session_id": self._session_id,
        })

        # 限制历史记录长度
        if len(self._request_history) > 100:
            self._request_history = self._request_history[-100:]

    def get_context(self, key: str, default: Any = None) -> Any:
        """获取上下文"""
        return self._context.get(key, default)

    def set_context(self, key: str, value: Any) -> None:
        """设置上下文"""
        self._context[key] = value

    def get_session_history(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取会话历史"""
        if session_id:
            return [r for r in self._request_history if r.get("session_id") == session_id]
        return self._request_history


# 全局门户智能体实例
portal_agent = PortalAgent()
