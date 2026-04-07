"""
Connector Agent - 数据连接器智能 Agent

实现 AI Native 的核心能力：
1. 自主发现并连接数据源
2. 自主推断 schema 并转换
3. 对话式交互替代手动配置
"""
import re
import json
import os
import sys
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import logger


class AgentState(Enum):
    """Agent 状态"""
    IDLE = "idle"
    THINKING = "thinking"
    EXECUTING = "executing"
    WAITING_FOR_CLARIFICATION = "waiting_for_clarification"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class AgentResponse:
    """Agent 响应"""
    success: bool
    message: str
    state: AgentState = AgentState.IDLE
    data: Optional[Dict[str, Any]] = None
    clarification_questions: List[str] = field(default_factory=list)
    suggested_actions: List[str] = field(default_factory=list)
    thinking_process: List[str] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "message": self.message,
            "state": self.state.value,
            "data": self.data,
            "clarification_questions": self.clarification_questions,
            "suggested_actions": self.suggested_actions,
            "thinking_process": self.thinking_process,
            "error": self.error
        }


@dataclass
class Intent:
    """用户意图"""
    type: str  # connect, disconnect, query, schema, lineage, etc.
    entities: Dict[str, Any]
    confidence: float
    ambiguities: List[str] = field(default_factory=list)
    implicit_needs: List[str] = field(default_factory=list)


class ConnectorAgent:
    """
    数据连接器智能 Agent

    核心能力：
    1. 意图理解 - 解析用户自然语言，提取意图和实体
    2. 主动澄清 - 检测歧义并生成澄清问题
    3. 自主执行 - 调用工具完成数据源连接、查询等任务
    4. 洞察生成 - 分析结果并提供深度洞察
    5. 对话管理 - 维护多轮对话上下文
    """

    def __init__(self, tools_registry: Optional[Dict] = None):
        """
        初始化 Connector Agent

        参数:
            tools_registry: 工具注册表（可选，默认使用内置工具）
        """
        self.tools = tools_registry
        self.state = AgentState.IDLE
        self._conversation_context: Dict[str, Any] = {}
        self._thinking_log: List[str] = []

        # 从环境变量加载工具
        if self.tools is None:
            try:
                from src.tools import TOOLS_REGISTRY
                self.tools = TOOLS_REGISTRY
            except ImportError:
                self.tools = {}
                logger.warning("Tools not available, agent will run in limited mode")

    async def run(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """
        执行任务

        参数:
            task: 任务描述（自然语言）
            context: 上下文信息

        返回:
            AgentResponse: Agent 响应
        """
        self.state = AgentState.THINKING
        self._thinking_log = []
        self._conversation_context.update(context or {})

        self._log_thinking(f"收到任务：{task}")

        try:
            # 1. 意图理解
            intent = await self._parse_intent(task)
            self._log_thinking(f"识别意图：{intent.type} (置信度：{intent.confidence})")

            # 2. 检查歧义
            if intent.ambiguities:
                self.state = AgentState.WAITING_FOR_CLARIFICATION
                return await self._handle_ambiguity(intent, task)

            # 3. 执行对应操作
            self.state = AgentState.EXECUTING
            response = await self._execute_intent(intent, task)

            # 4. 生成后续建议
            response.suggested_actions = self._generate_suggested_actions(intent, response)

            self.state = AgentState.COMPLETED
            return response

        except Exception as e:
            self.state = AgentState.ERROR
            logger.error(f"Agent execution failed: {e}")
            return AgentResponse(
                success=False,
                message="任务执行失败",
                state=AgentState.ERROR,
                error=str(e),
                thinking_process=self._thinking_log
            )

    def _log_thinking(self, message: str):
        """记录思考过程"""
        self._thinking_log.append(message)
        logger.debug(f"[Agent Thinking] {message}")

    async def _parse_intent(self, text: str) -> Intent:
        """
        解析用户意图

        使用规则 + 启发式方法识别意图类型和实体
        """
        text_lower = text.lower().strip()

        # 意图识别规则
        intent_patterns = [
            # 连接数据源
            (r"(连接|添加 | 注册 | 绑定)\s*(到)?\s*(数据源 | 数据库|mysql|postgres|mongo|redis|api)", "connect", 0.9),
            (r"(create|add|connect|register)\s*(a)?\s*(data\s*source|database|connection)", "connect", 0.9),

            # 断开连接
            (r"(断开 | 删除 | 移除|解除)\s*(连接 | 数据源 | 数据库)", "disconnect", 0.9),
            (r"(disconnect|remove|delete|drop)\s*(connection|datasource|database)", "disconnect", 0.9),

            # 查询数据
            (r"(查询 | 查找 | 搜索 | 获取)\s*(数据 | 记录 | 信息)?\s*(从 | 在)?", "query", 0.8),
            (r"(query|select|find|search|get)\s*(data|records|info)?", "query", 0.8),

            # 自然语言查询
            (r"(我想看 | 我想查 | 帮我查 | 显示 | 展示)", "nl_query", 0.85),
            (r"(show|i want to see|help me find|display)", "nl_query", 0.85),

            # Schema 查询
            (r"(查看 | 获取 | 列出|显示)\s*(表结构|schema|字段 | 表)", "schema", 0.9),
            (r"(show|get|list|describe)\s*(schema|tables|columns|structure)", "schema", 0.9),

            # 数据血缘
            (r"(血缘 | 依赖 | 影响 | 来源)", "lineage", 0.85),
            (r"(lineage|dependency|impact|upstream|downstream)", "lineage", 0.85),

            # 列出连接器
            (r"(列出 | 显示 | 查看)\s*(所有 | 已连接 | 可用)\s*(数据源 | 连接器)", "list_connectors", 0.9),
            (r"(list|show|view)\s*(all|available|connected)\s*(sources|connectors)", "list_connectors", 0.9),
        ]

        # 匹配意图
        best_match = None
        best_score = 0.0

        for pattern, intent_type, score in intent_patterns:
            if re.search(pattern, text_lower):
                if score > best_score:
                    best_score = score
                    best_match = intent_type

        if best_match:
            intent_type = best_match
        else:
            # 默认根据关键词判断
            if any(k in text_lower for k in ["连接", "connect", "添加", "add"]):
                intent_type = "connect"
            elif any(k in text_lower for k in ["断开", "disconnect", "删除", "delete"]):
                intent_type = "disconnect"
            elif any(k in text_lower for k in ["查询", "query", "查找", "search"]):
                intent_type = "query"
            else:
                intent_type = "unknown"
                best_score = 0.5

        # 提取实体
        entities = self._extract_entities(text, intent_type)

        # 检测歧义
        ambiguities = self._detect_ambiguities(text, intent_type, entities)

        # 推断隐式需求
        implicit_needs = self._infer_implicit_needs(intent_type, entities)

        return Intent(
            type=intent_type,
            entities=entities,
            confidence=best_score,
            ambiguities=ambiguities,
            implicit_needs=implicit_needs
        )

    def _extract_entities(self, text: str, intent_type: str) -> Dict[str, Any]:
        """提取实体信息"""
        entities = {}
        text_lower = text.lower()

        # 数据源名称
        datasource_patterns = [
            (r"(mysql|postgres|postgresql|mongodb|mongo|redis|elasticsearch|es|sqlite)", "type"),
            (r"(数据源 | 数据库|连接)\s*[:：]?\s*([\w\-_]+)", "name"),
        ]

        for pattern, entity_type in datasource_patterns:
            match = re.search(pattern, text_lower)
            if match:
                if entity_type == "type":
                    entities["connector_type"] = match.group(1)
                elif entity_type == "name":
                    entities["name"] = match.group(2)

        # 连接器类型推断
        if "connector_type" not in entities:
            type_mapping = {
                "mysql": "mysql",
                "postgres": "postgresql",
                "postgresql": "postgresql",
                "mongo": "mongodb",
                "mongodb": "mongodb",
                "redis": "redis",
                "sqlite": "sqlite",
                "elastic": "elasticsearch",
                "api": "rest_api"
            }
            for key, value in type_mapping.items():
                if key in text_lower:
                    entities["connector_type"] = value
                    break

        # 角色
        if any(k in text_lower for k in ["只读", "read.only", "readonly"]):
            entities["role"] = "read_only"
        elif any(k in text_lower for k in ["读写", "read.write", "readwrite", "可写"]):
            entities["role"] = "read_write"
        else:
            entities["role"] = "read_only"  # 默认只读

        # 表名
        table_match = re.search(r"(表 | 表结构)\s*[:：]?\s*([\w\-_]+)", text_lower)
        if table_match:
            entities["table_name"] = table_match.group(2)

        # 查询条件
        if intent_type in ["query", "nl_query"]:
            entities["query_text"] = text

        return entities

    def _detect_ambiguities(
        self,
        text: str,
        intent_type: str,
        entities: Dict[str, Any]
    ) -> List[str]:
        """检测歧义"""
        ambiguities = []

        if intent_type == "connect":
            if "connector_type" not in entities:
                ambiguities.append("connector_type_missing")
            if "name" not in entities:
                ambiguities.append("name_missing")

        if intent_type == "query":
            if "connector_name" not in entities and "connector_type" not in entities:
                ambiguities.append("datasource_missing")

        if intent_type == "schema":
            if "connector_name" not in entities and "connector_type" not in entities:
                ambiguities.append("datasource_missing")

        return ambiguities

    def _infer_implicit_needs(
        self,
        intent_type: str,
        entities: Dict[str, Any]
    ) -> List[str]:
        """推断隐式需求"""
        needs = []

        if intent_type == "connect":
            needs.append("verify_connection")
            needs.append("fetch_schema")

        if intent_type == "query":
            needs.append("auto_visualize")
            needs.append("generate_insights")

        if intent_type == "schema":
            needs.append("show_relationships")

        return needs

    async def _handle_ambiguity(self, intent: Intent, original_text: str) -> AgentResponse:
        """处理歧义"""
        questions = []

        for ambiguity in intent.ambiguities:
            if ambiguity == "connector_type_missing":
                questions.append("请问您要连接什么类型的数据库？(MySQL/PostgreSQL/MongoDB/Redis/SQLite/Elasticsearch/REST API)")
            elif ambiguity == "name_missing":
                questions.append("请为这个连接器起一个名字（例如：production_db, analytics_mysql）")
            elif ambiguity == "datasource_missing":
                questions.append("请问您想查询哪个数据源？")

        # 生成选项
        options = {
            "connector_type": ["MySQL", "PostgreSQL", "MongoDB", "Redis", "SQLite", "Elasticsearch", "REST API"],
            "role": ["只读", "读写"]
        }

        return AgentResponse(
            success=False,
            message="需要更多信息才能执行",
            state=AgentState.WAITING_FOR_CLARIFICATION,
            clarification_questions=questions,
            data={"options": options},
            thinking_process=self._thinking_log
        )

    async def _execute_intent(self, intent: Intent, original_text: str) -> AgentResponse:
        """执行意图"""
        self._log_thinking(f"执行意图：{intent.type}")

        handlers = {
            "connect": self._handle_connect,
            "disconnect": self._handle_disconnect,
            "query": self._handle_query,
            "nl_query": self._handle_nl_query,
            "schema": self._handle_schema,
            "lineage": self._handle_lineage,
            "list_connectors": self._handle_list_connectors,
        }

        handler = handlers.get(intent.type)
        if handler:
            return await handler(intent.entities, original_text)
        else:
            return AgentResponse(
                success=False,
                message=f"未知意图类型：{intent.type}",
                thinking_process=self._thinking_log
            )

    async def _handle_connect(
        self,
        entities: Dict[str, Any],
        original_text: str
    ) -> AgentResponse:
        """处理连接数据源意图"""
        self._log_thinking(f"连接数据源：type={entities.get('connector_type')}, name={entities.get('name')}")

        # 使用工具连接
        if "connect_datasource" in self.tools:
            from src.tools import tool_connect_datasource

            name = entities.get("name", f"connector_{entities.get('connector_type', 'unknown')}")
            connector_type = entities.get("connector_type")

            if not connector_type:
                return AgentResponse(
                    success=False,
                    message="无法确定数据库类型，请明确指定（如 MySQL/PostgreSQL/MongoDB 等）",
                    thinking_process=self._thinking_log
                )

            result = await tool_connect_datasource(
                name=name,
                connector_type=connector_type,
                role=entities.get("role", "read_only")
            )

            if result.success:
                self._log_thinking(f"连接成功：{name}")

                # 自动获取 schema
                self._log_thinking("自动获取 Schema...")
                schema_info = await self._auto_fetch_schema(name)

                return AgentResponse(
                    success=True,
                    message=f"成功连接到数据源 {name}（类型：{connector_type}）",
                    data={
                        "connector_name": name,
                        "connector_type": connector_type,
                        "schema_summary": schema_info
                    },
                    suggested_actions=[
                        f"查看 {name} 的表结构",
                        f"查询 {name} 中的数据",
                        "列出所有已连接的数据源"
                    ],
                    thinking_process=self._thinking_log
                )
            else:
                return AgentResponse(
                    success=False,
                    message="连接失败",
                    error=result.error,
                    thinking_process=self._thinking_log
                )
        else:
            return AgentResponse(
                success=False,
                message="连接工具不可用",
                thinking_process=self._thinking_log
            )

    async def _auto_fetch_schema(self, connector_name: str) -> Optional[Dict[str, Any]]:
        """自动获取 Schema 信息"""
        try:
            from src.tools import tool_get_schema
            result = await tool_get_schema(connector_name, use_cache=False)
            if result.success:
                schema = result.data.get("schema", {})
                tables = schema.get("tables", [])
                return {
                    "table_count": len(tables),
                    "tables": [t.get("name") for t in tables[:5]],  # 只显示前 5 个
                    "has_more": len(tables) > 5
                }
        except Exception as e:
            self._log_thinking(f"获取 Schema 失败：{e}")
        return None

    async def _handle_disconnect(
        self,
        entities: Dict[str, Any],
        original_text: str
    ) -> AgentResponse:
        """处理断开连接意图"""
        self._log_thinking(f"断开数据源：name={entities.get('name')}")

        if "name" not in entities:
            return AgentResponse(
                success=False,
                message="请指定要断开的数据源名称",
                thinking_process=self._thinking_log
            )

        from src.tools import tool_disconnect_datasource
        result = await tool_disconnect_datasource(entities["name"])

        if result.success:
            return AgentResponse(
                success=True,
                message=f"已断开数据源 {entities['name']} 的连接",
                thinking_process=self._thinking_log
            )
        else:
            return AgentResponse(
                success=False,
                message=result.error or "断开连接失败",
                thinking_process=self._thinking_log
            )

    async def _handle_query(
        self,
        entities: Dict[str, Any],
        original_text: str
    ) -> AgentResponse:
        """处理查询意图"""
        self._log_thinking(f"执行查询：{original_text}")

        # 尝试执行自然语言查询
        from src.tools import tool_nl_query

        # 需要确定数据源
        connector_name = entities.get("connector_name")
        if not connector_name:
            # 尝试获取第一个可用的数据源
            connectors = await self._list_available_connectors()
            if connectors:
                connector_name = connectors[0].get("name")
                self._log_thinking(f"使用默认数据源：{connector_name}")
            else:
                return AgentResponse(
                    success=False,
                    message="没有找到已连接的数据源，请先连接数据源",
                    suggested_actions=["连接 MySQL 数据库", "连接 PostgreSQL 数据库"],
                    thinking_process=self._thinking_log
                )

        result = await tool_nl_query(
            connector_name=connector_name,
            natural_language=original_text
        )

        if result.success:
            data = result.data or []
            return AgentResponse(
                success=True,
                message=f"查询完成，返回 {len(data)} 条记录",
                data={"results": data, "metadata": result.metadata},
                suggested_actions=[
                    "查看更详细的结果",
                    "导出查询结果",
                    "保存这个查询"
                ],
                thinking_process=self._thinking_log
            )
        else:
            return AgentResponse(
                success=False,
                message=result.error or "查询执行失败",
                thinking_process=self._thinking_log
            )

    async def _handle_nl_query(
        self,
        entities: Dict[str, Any],
        original_text: str
    ) -> AgentResponse:
        """处理自然语言查询"""
        return await self._handle_query(entities, original_text)

    async def _handle_schema(
        self,
        entities: Dict[str, Any],
        original_text: str
    ) -> AgentResponse:
        """处理 Schema 查询意图"""
        self._log_thinking(f"获取 Schema：entities={entities}")

        connector_name = entities.get("connector_name")
        if not connector_name:
            connectors = await self._list_available_connectors()
            if connectors:
                connector_name = connectors[0].get("name")
            else:
                return AgentResponse(
                    success=False,
                    message="没有找到已连接的数据源",
                    suggested_actions=["连接一个数据源"],
                    thinking_process=self._thinking_log
                )

        from src.tools import tool_get_schema
        result = await tool_get_schema(connector_name)

        if result.success:
            schema = result.data.get("schema", {})
            tables = schema.get("tables", [])
            table_names = [t.get("name") for t in tables]

            return AgentResponse(
                success=True,
                message=f"数据源 {connector_name} 包含 {len(tables)} 个表",
                data={
                    "connector_name": connector_name,
                    "tables": table_names,
                    "schema": schema
                },
                suggested_actions=[
                    f"查看某个表的详细结构",
                    f"查询表中的数据",
                    "查看表之间的血缘关系"
                ],
                thinking_process=self._thinking_log
            )
        else:
            return AgentResponse(
                success=False,
                message=result.error or "获取 Schema 失败",
                thinking_process=self._thinking_log
            )

    async def _handle_lineage(
        self,
        entities: Dict[str, Any],
        original_text: str
    ) -> AgentResponse:
        """处理血缘查询意图"""
        self._log_thinking(f"查询血缘：entities={entities}")

        connector_name = entities.get("connector_name")
        table_name = entities.get("table_name")

        if not table_name:
            return AgentResponse(
                success=False,
                message="请指定要查询血缘的表名",
                thinking_process=self._thinking_log
            )

        from src.tools import tool_get_lineage
        result = await tool_get_lineage(connector_name or "default", table_name)

        if result.success:
            lineage = result.data or {}
            upstream = lineage.get("upstream", [])
            downstream = lineage.get("downstream", [])

            return AgentResponse(
                success=True,
                message=f"表 {table_name} 的血缘关系：{len(upstream)} 个上游依赖，{len(downstream)} 个下游依赖",
                data=lineage,
                suggested_actions=[
                    "查看上游依赖详情",
                    "查看下游依赖详情",
                    "分析变更影响"
                ],
                thinking_process=self._thinking_log
            )
        else:
            return AgentResponse(
                success=False,
                message=result.error or "获取血缘关系失败",
                thinking_process=self._thinking_log
            )

    async def _handle_list_connectors(
        self,
        entities: Dict[str, Any],
        original_text: str
    ) -> AgentResponse:
        """处理列出连接器意图"""
        self._log_thinking("列出所有连接器")

        connectors = await self._list_available_connectors()

        if connectors:
            connector_list = "\n".join([
                f"  - {c.get('name')} ({c.get('type')}) - {c.get('status', 'unknown')}"
                for c in connectors
            ])

            return AgentResponse(
                success=True,
                message=f"已连接 {len(connectors)} 个数据源:\n{connector_list}",
                data={"connectors": connectors, "count": len(connectors)},
                suggested_actions=[
                    "查看某个数据源的表结构",
                    "查询某个数据源的数据",
                    "连接新的数据源"
                ],
                thinking_process=self._thinking_log
            )
        else:
            return AgentResponse(
                success=True,
                message="当前没有已连接的数据源",
                data={"connectors": [], "count": 0},
                suggested_actions=[
                    "连接 MySQL 数据库",
                    "连接 PostgreSQL 数据库",
                    "连接 MongoDB 数据库"
                ],
                thinking_process=self._thinking_log
            )

    async def _list_available_connectors(self) -> List[Dict[str, Any]]:
        """获取可用的连接器列表"""
        try:
            from src.tools import tool_list_connectors
            result = await tool_list_connectors()
            if result.success:
                return result.data.get("sources", [])
        except Exception as e:
            self._log_thinking(f"获取连接器列表失败：{e}")
        return []

    def _generate_suggested_actions(
        self,
        intent: Intent,
        response: AgentResponse
    ) -> List[str]:
        """生成建议操作"""
        actions = []

        if intent.type == "connect":
            if response.success:
                actions.extend([
                    "查看表结构",
                    "执行查询",
                    "连接更多数据源"
                ])

        elif intent.type in ["query", "nl_query"]:
            if response.success:
                actions.extend([
                    "深入分析结果",
                    "可视化展示",
                    "导出结果"
                ])

        elif intent.type == "schema":
            if response.success:
                actions.extend([
                    "查询表数据",
                    "查看血缘关系",
                    "刷新 Schema"
                ])

        return actions

    async def chat(
        self,
        message: str,
        conversation_id: Optional[str] = None
    ) -> AgentResponse:
        """
        对话式交互入口

        参数:
            message: 用户消息
            conversation_id: 会话 ID（可选）

        返回:
            AgentResponse: Agent 响应
        """
        # 更新上下文
        if conversation_id:
            self._conversation_context["conversation_id"] = conversation_id

        # 调用 run 方法处理
        return await self.run(message, self._conversation_context)
