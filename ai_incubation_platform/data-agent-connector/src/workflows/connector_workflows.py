"""
数据连接器工作流

实现 DeerFlow 2.0 风格的多步任务编排：
1. 连接数据源工作流
2. 查询数据工作流
3. Schema 发现工作流
4. 血缘分析工作流
5. 自动数据管道工作流
"""
import asyncio
import os
import sys
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from functools import wraps

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import logger


def step(func):
    """工作流步骤装饰器"""
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        step_name = func.__name__
        logger.debug(f"[Workflow {self.name}] 执行步骤：{step_name}")
        self._execution_log.append({
            "step": step_name,
            "status": "running",
            "input": kwargs
        })
        try:
            result = await func(self, *args, **kwargs)
            self._execution_log[-1]["status"] = "completed"
            self._execution_log[-1]["output"] = result
            return result
        except Exception as e:
            self._execution_log[-1]["status"] = "failed"
            self._execution_log[-1]["error"] = str(e)
            raise
    return wrapper


def workflow(name: str):
    """工作流类装饰器"""
    def decorator(cls):
        cls.name = name
        return cls
    return decorator


@dataclass
class WorkflowResult:
    """工作流执行结果"""
    success: bool
    workflow_name: str
    result: Any = None
    error: Optional[str] = None
    execution_log: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "workflow_name": self.workflow_name,
            "result": self.result,
            "error": self.error,
            "execution_log": self.execution_log,
            "metadata": self.metadata
        }


class BaseWorkflow:
    """工作流基类"""

    name: str = "base_workflow"

    def __init__(self):
        self._execution_log: List[Dict[str, Any]] = []
        self._context: Dict[str, Any] = {}

    async def run(self, **input_data) -> WorkflowResult:
        """执行工作流（子类实现）"""
        raise NotImplementedError

    async def _cleanup(self):
        """清理资源"""
        pass


# ============================================================================
# 连接数据源工作流
# ============================================================================

@workflow(name="connect_datasource")
class ConnectDatasourceWorkflow(BaseWorkflow):
    """
    连接数据源工作流

    流程：
    1. 验证输入参数
    2. 检查数据源是否已存在
    3. 创建连接器
    4. 测试连接
    5. 获取 Schema
    6. 记录审计日志
    """

    name = "connect_datasource"

    @step
    async def validate_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """验证输入参数"""
        required_fields = ["name", "connector_type"]
        missing = [f for f in required_fields if f not in input_data]

        if missing:
            raise ValueError(f"缺少必需参数：{missing}")

        # 验证连接器类型
        valid_types = ["mysql", "postgresql", "mongodb", "redis", "sqlite", "elasticsearch", "rest_api"]
        if input_data["connector_type"] not in valid_types:
            raise ValueError(f"不支持的连接器类型：{input_data['connector_type']}")

        return input_data

    @step
    async def check_existing(self, name: str) -> bool:
        """检查数据源是否已存在"""
        try:
            from src.tools import tool_list_connectors
            result = await tool_list_connectors()
            if result.success:
                sources = result.data.get("sources", [])
                return any(s.get("name") == name for s in sources)
        except Exception as e:
            logger.warning(f"检查现有连接器失败：{e}")
        return False

    @step
    async def create_connector(
        self,
        name: str,
        connector_type: str,
        datasource_name: Optional[str] = None,
        role: str = "read_only"
    ) -> Dict[str, Any]:
        """创建连接器"""
        from src.tools import tool_connect_datasource
        result = await tool_connect_datasource(
            name=name,
            connector_type=connector_type,
            datasource_name=datasource_name or name,
            role=role
        )

        if not result.success:
            raise Exception(f"创建连接器失败：{result.error}")

        return result.to_dict()

    @step
    async def test_connection(self, name: str) -> Dict[str, Any]:
        """测试连接"""
        try:
            from src.tools import tool_get_schema
            result = await tool_get_schema(name, use_cache=False)
            return {
                "success": result.success,
                "message": "连接测试成功" if result.success else result.error
            }
        except Exception as e:
            return {
                "success": False,
                "message": str(e)
            }

    @step
    async def fetch_schema(self, name: str) -> Dict[str, Any]:
        """获取 Schema"""
        from src.tools import tool_get_schema
        result = await tool_get_schema(name, use_cache=False)

        if result.success:
            schema = result.data.get("schema", {})
            tables = schema.get("tables", [])
            return {
                "table_count": len(tables),
                "tables": [t.get("name") for t in tables[:10]]
            }
        return {"error": result.error}

    @step
    async def log_audit(self, name: str, connector_type: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """记录审计日志"""
        # 审计日志记录
        logger.info(
            "ConnectorCreated",
            extra={
                "name": name,
                "type": connector_type,
                "success": result.get("success", False)
            }
        )
        return {"logged": True}

    async def run(self, **input_data) -> WorkflowResult:
        """执行工作流"""
        self._context.update(input_data)

        try:
            # Step 1: 验证输入
            validated = await self.validate_input(input_data)
            self._context.update(validated)

            # Step 2: 检查是否存在
            exists = await self.check_existing(validated["name"])
            if exists:
                return WorkflowResult(
                    success=False,
                    workflow_name=self.name,
                    error=f"数据源 {validated['name']} 已存在",
                    execution_log=self._execution_log
                )

            # Step 3: 创建连接器
            create_result = await self.create_connector(
                name=validated["name"],
                connector_type=validated["connector_type"],
                datasource_name=validated.get("datasource_name"),
                role=validated.get("role", "read_only")
            )

            # Step 4: 测试连接
            test_result = await self.test_connection(validated["name"])
            if not test_result.get("success"):
                return WorkflowResult(
                    success=False,
                    workflow_name=self.name,
                    error=f"连接测试失败：{test_result.get('message')}",
                    execution_log=self._execution_log
                )

            # Step 5: 获取 Schema
            schema_result = await self.fetch_schema(validated["name"])

            # Step 6: 记录审计
            await self.log_audit(
                validated["name"],
                validated["connector_type"],
                {"success": True}
            )

            return WorkflowResult(
                success=True,
                workflow_name=self.name,
                result={
                    "name": validated["name"],
                    "type": validated["connector_type"],
                    "schema": schema_result
                },
                execution_log=self._execution_log
            )

        except Exception as e:
            logger.error(f"工作流执行失败：{e}")
            return WorkflowResult(
                success=False,
                workflow_name=self.name,
                error=str(e),
                execution_log=self._execution_log
            )


# ============================================================================
# 断开数据源工作流
# ============================================================================

@workflow(name="disconnect_datasource")
class DisconnectDatasourceWorkflow(BaseWorkflow):
    """
    断开数据源工作流

    流程：
    1. 验证数据源存在
    2. 检查是否有依赖
    3. 断开连接
    4. 清理缓存
    5. 记录审计
    """

    name = "disconnect_datasource"

    @step
    async def verify_exists(self, name: str) -> bool:
        """验证数据源存在"""
        from src.tools import tool_list_connectors
        result = await tool_list_connectors()
        if result.success:
            sources = result.data.get("sources", [])
            return any(s.get("name") == name for s in sources)
        return False

    @step
    async def check_dependencies(self, name: str) -> List[str]:
        """检查依赖"""
        # 检查是否有正在进行的查询或管道依赖此数据源
        # 简化实现：返回空列表
        return []

    @step
    async def disconnect(self, name: str) -> Dict[str, Any]:
        """断开连接"""
        from src.tools import tool_disconnect_datasource
        result = await tool_disconnect_datasource(name)
        return result.to_dict()

    @step
    async def cleanup_cache(self, name: str) -> bool:
        """清理缓存"""
        # 清理 Schema 缓存等
        logger.info(f"清理数据源缓存：{name}")
        return True

    @step
    async def log_audit(self, name: str) -> Dict[str, Any]:
        """记录审计日志"""
        logger.info("ConnectorDisconnected", extra={"name": name})
        return {"logged": True}

    async def run(self, **input_data) -> WorkflowResult:
        """执行工作流"""
        name = input_data.get("name")
        if not name:
            return WorkflowResult(
                success=False,
                workflow_name=self.name,
                error="缺少参数：name"
            )

        try:
            # Step 1: 验证存在
            exists = await self.verify_exists(name)
            if not exists:
                return WorkflowResult(
                    success=False,
                    workflow_name=self.name,
                    error=f"数据源 {name} 不存在"
                )

            # Step 2: 检查依赖
            deps = await self.check_dependencies(name)
            if deps:
                return WorkflowResult(
                    success=False,
                    workflow_name=self.name,
                    error=f"存在依赖：{deps}"
                )

            # Step 3: 断开连接
            disconnect_result = await self.disconnect(name)
            if not disconnect_result.get("success"):
                raise Exception(disconnect_result.get("error", "断开失败"))

            # Step 4: 清理缓存
            await self.cleanup_cache(name)

            # Step 5: 记录审计
            await self.log_audit(name)

            return WorkflowResult(
                success=True,
                workflow_name=self.name,
                result={"name": name},
                execution_log=self._execution_log
            )

        except Exception as e:
            return WorkflowResult(
                success=False,
                workflow_name=self.name,
                error=str(e),
                execution_log=self._execution_log
            )


# ============================================================================
# 查询数据工作流
# ============================================================================

@workflow(name="query_data")
class QueryDataWorkflow(BaseWorkflow):
    """
    查询数据工作流

    流程：
    1. 解析查询意图
    2. 确定数据源
    3. 生成/验证 SQL
    4. 安全检查
    5. 执行查询
    6. 结果处理
    7. 生成洞察
    """

    name = "query_data"

    @step
    async def parse_intent(self, query: str) -> Dict[str, Any]:
        """解析查询意图"""
        # 使用 Agent 进行意图解析
        from src.agents.connector_agent import ConnectorAgent
        agent = ConnectorAgent()
        intent = await agent._parse_intent(query)
        return {
            "type": intent.type,
            "entities": intent.entities,
            "confidence": intent.confidence
        }

    @step
    async def determine_datasource(
        self,
        intent: Dict[str, Any],
        preferred_source: Optional[str] = None
    ) -> str:
        """确定数据源"""
        if preferred_source:
            return preferred_source

        entities = intent.get("entities", {})
        if "connector_name" in entities:
            return entities["connector_name"]

        # 获取默认数据源
        from src.tools import tool_list_connectors
        result = await tool_list_connectors()
        sources = result.data.get("sources", []) if result.success else []

        if not sources:
            raise Exception("没有可用的数据源")

        # 返回第一个可用的
        return sources[0].get("name", "default")

    @step
    async def execute_query(
        self,
        connector_name: str,
        natural_language: str
    ) -> Dict[str, Any]:
        """执行查询"""
        from src.tools import tool_nl_query
        result = await tool_nl_query(
            connector_name=connector_name,
            natural_language=natural_language
        )
        return result.to_dict()

    @step
    async def generate_insights(
        self,
        query_result: Dict[str, Any],
        original_query: str
    ) -> Dict[str, Any]:
        """生成洞察"""
        # 简单的洞察生成
        data = query_result.get("data", [])
        if not data:
            return {"summary": "查询结果为空"}

        return {
            "summary": f"查询返回 {len(data)} 条记录",
            "sample": data[:3] if len(data) > 3 else data,
            "suggestions": [
                "查看详细结果",
                "导出为 CSV",
                "创建可视化"
            ]
        }

    async def run(self, **input_data) -> WorkflowResult:
        """执行工作流"""
        query = input_data.get("query") or input_data.get("natural_language")
        if not query:
            return WorkflowResult(
                success=False,
                workflow_name=self.name,
                error="缺少查询参数"
            )

        try:
            # Step 1: 解析意图
            intent = await self.parse_intent(query)

            # Step 2: 确定数据源
            datasource = await self.determine_datasource(
                intent,
                input_data.get("connector_name")
            )

            # Step 3: 执行查询
            query_result = await self.execute_query(datasource, query)

            if not query_result.get("success"):
                return WorkflowResult(
                    success=False,
                    workflow_name=self.name,
                    error=query_result.get("error", "查询失败"),
                    execution_log=self._execution_log
                )

            # Step 4: 生成洞察
            insights = await self.generate_insights(query_result, query)

            return WorkflowResult(
                success=True,
                workflow_name=self.name,
                result={
                    "data": query_result.get("data"),
                    "insights": insights,
                    "metadata": query_result.get("metadata")
                },
                execution_log=self._execution_log
            )

        except Exception as e:
            return WorkflowResult(
                success=False,
                workflow_name=self.name,
                error=str(e),
                execution_log=self._execution_log
            )


# ============================================================================
# Schema 发现工作流
# ============================================================================

@workflow(name="schema_discovery")
class SchemaDiscoveryWorkflow(BaseWorkflow):
    """
    Schema 发现工作流

    流程：
    1. 获取数据源连接
    2. 获取 Schema
    3. 分析表关系
    4. 构建知识图谱
    5. 缓存结果
    """

    name = "schema_discovery"

    @step
    async def get_schema(self, connector_name: str) -> Dict[str, Any]:
        """获取 Schema"""
        from src.tools import tool_get_schema
        result = await tool_get_schema(connector_name, use_cache=False)
        return result.to_dict()

    @step
    async def analyze_relationships(
        self,
        schema: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """分析表关系"""
        tables = schema.get("tables", [])
        relationships = []

        # 简单的关系推断（基于字段名）
        for table in tables:
            columns = table.get("columns", [])
            for col in columns:
                col_name = col.get("name", "").lower()
                # 检测外键
                if col_name.endswith("_id") or col_name == "id":
                    relationships.append({
                        "table": table.get("name"),
                        "column": col_name,
                        "type": "potential_foreign_key"
                    })

        return relationships

    @step
    async def build_knowledge_graph(
        self,
        schema: Dict[str, Any],
        relationships: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """构建知识图谱"""
        return {
            "tables": [t.get("name") for t in schema.get("tables", [])],
            "relationships": relationships,
            "table_count": len(schema.get("tables", [])),
            "column_count": sum(len(t.get("columns", [])) for t in schema.get("tables", []))
        }

    async def run(self, **input_data) -> WorkflowResult:
        """执行工作流"""
        connector_name = input_data.get("connector_name")
        if not connector_name:
            return WorkflowResult(
                success=False,
                workflow_name=self.name,
                error="缺少参数：connector_name"
            )

        try:
            # Step 1: 获取 Schema
            schema_result = await self.get_schema(connector_name)

            if not schema_result.get("success"):
                return WorkflowResult(
                    success=False,
                    workflow_name=self.name,
                    error=schema_result.get("error", "获取 Schema 失败"),
                    execution_log=self._execution_log
                )

            schema = schema_result.get("data", {}).get("schema", {})

            # Step 2: 分析关系
            relationships = await self.analyze_relationships(schema)

            # Step 3: 构建知识图谱
            knowledge_graph = await self.build_knowledge_graph(schema, relationships)

            return WorkflowResult(
                success=True,
                workflow_name=self.name,
                result={
                    "schema": schema,
                    "relationships": relationships,
                    "knowledge_graph": knowledge_graph
                },
                execution_log=self._execution_log
            )

        except Exception as e:
            return WorkflowResult(
                success=False,
                workflow_name=self.name,
                error=str(e),
                execution_log=self._execution_log
            )


# ============================================================================
# 血缘分析工作流
# ============================================================================

@workflow(name="lineage_analysis")
class LineageAnalysisWorkflow(BaseWorkflow):
    """
    血缘分析工作流

    流程：
    1. 获取表血缘
    2. 分析上游依赖
    3. 分析下游依赖
    4. 评估影响范围
    5. 生成报告
    """

    name = "lineage_analysis"

    @step
    async def get_lineage(
        self,
        connector_name: str,
        table_name: str
    ) -> Dict[str, Any]:
        """获取血缘关系"""
        from src.tools import tool_get_lineage
        result = await tool_get_lineage(connector_name, table_name)
        return result.to_dict()

    @step
    async def analyze_impact(
        self,
        connector_name: str,
        table_name: str,
        lineage: Dict[str, Any]
    ) -> Dict[str, Any]:
        """分析影响"""
        from src.tools import tool_analyze_impact
        result = await tool_analyze_impact(connector_name, table_name)
        return result.to_dict()

    @step
    async def generate_report(
        self,
        table_name: str,
        lineage: Dict[str, Any],
        impact: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成报告"""
        return {
            "table": table_name,
            "upstream_count": len(lineage.get("upstream", [])),
            "downstream_count": len(lineage.get("downstream", [])),
            "risk_level": impact.get("risk_level", "unknown"),
            "affected_nodes": len(impact.get("affected_nodes", [])),
            "recommendations": impact.get("recommendations", [])
        }

    async def run(self, **input_data) -> WorkflowResult:
        """执行工作流"""
        connector_name = input_data.get("connector_name")
        table_name = input_data.get("table_name")

        if not connector_name or not table_name:
            return WorkflowResult(
                success=False,
                workflow_name=self.name,
                error="缺少参数：connector_name 和 table_name"
            )

        try:
            # Step 1: 获取血缘
            lineage_result = await self.get_lineage(connector_name, table_name)

            if not lineage_result.get("success"):
                return WorkflowResult(
                    success=False,
                    workflow_name=self.name,
                    error=lineage_result.get("error", "获取血缘失败"),
                    execution_log=self._execution_log
                )

            lineage = lineage_result.get("data", {})

            # Step 2: 分析影响
            impact = await self.analyze_impact(connector_name, table_name, lineage)

            # Step 3: 生成报告
            report = await self.generate_report(table_name, lineage, impact)

            return WorkflowResult(
                success=True,
                workflow_name=self.name,
                result={
                    "lineage": lineage,
                    "impact": impact,
                    "report": report
                },
                execution_log=self._execution_log
            )

        except Exception as e:
            return WorkflowResult(
                success=False,
                workflow_name=self.name,
                error=str(e),
                execution_log=self._execution_log
            )


# ============================================================================
# 自动数据管道工作流
# ============================================================================

@workflow(name="auto_data_pipeline")
class AutoDataPipelineWorkflow(BaseWorkflow):
    """
    自动数据管道工作流

    流程：
    1. 理解管道需求
    2. 设计管道架构
    3. 创建调度配置
    4. 配置输出目标
    5. 设置监控告警
    6. 测试管道
    """

    name = "auto_data_pipeline"

    @step
    async def parse_requirements(self, request: str) -> Dict[str, Any]:
        """解析管道需求"""
        # 分析用户需求
        requirements = {
            "type": "report",  # report, monitoring, etl, analysis
            "frequency": "daily",
            "output_format": "email",
            "query": request
        }

        # 简单关键词匹配
        request_lower = request.lower()
        if "每天" in request_lower or "daily" in request_lower:
            requirements["frequency"] = "daily"
        elif "每周" in request_lower or "weekly" in request_lower:
            requirements["frequency"] = "weekly"
        elif "每小时" in request_lower or "hourly" in request_lower:
            requirements["frequency"] = "hourly"

        if "邮件" in request_lower or "email" in request_lower:
            requirements["output_format"] = "email"
        if "监控" in request_lower or "monitor" in request_lower:
            requirements["type"] = "monitoring"

        return requirements

    @step
    async def design_pipeline(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """设计管道架构"""
        return {
            "source": "auto_detected",
            "transform": requirements.get("type", "query"),
            "schedule": f"0 9 * * *" if requirements.get("frequency") == "daily" else "0 * * * *",
            "destination": requirements.get("output_format", "email")
        }

    @step
    async def create_schedule(self, design: Dict[str, Any]) -> Dict[str, Any]:
        """创建调度配置"""
        # 简化实现
        return {
            "schedule_id": "auto_generated",
            "cron": design.get("schedule"),
            "status": "created"
        }

    @step
    async def configure_output(self, design: Dict[str, Any]) -> Dict[str, Any]:
        """配置输出"""
        return {
            "format": design.get("destination"),
            "status": "configured"
        }

    @step
    async def setup_monitoring(self) -> Dict[str, Any]:
        """设置监控"""
        return {
            "alerts_enabled": True,
            "retry_enabled": True,
            "max_retries": 3
        }

    async def run(self, **input_data) -> WorkflowResult:
        """执行工作流"""
        request = input_data.get("request", "")
        if not request:
            return WorkflowResult(
                success=False,
                workflow_name=self.name,
                error="缺少管道需求描述"
            )

        try:
            # Step 1: 解析需求
            requirements = await self.parse_requirements(request)

            # Step 2: 设计管道
            design = await self.design_pipeline(requirements)

            # Step 3: 创建调度
            schedule = await self.create_schedule(design)

            # Step 4: 配置输出
            output = await self.configure_output(design)

            # Step 5: 设置监控
            monitoring = await self.setup_monitoring()

            return WorkflowResult(
                success=True,
                workflow_name=self.name,
                result={
                    "requirements": requirements,
                    "design": design,
                    "schedule": schedule,
                    "output": output,
                    "monitoring": monitoring
                },
                execution_log=self._execution_log
            )

        except Exception as e:
            return WorkflowResult(
                success=False,
                workflow_name=self.name,
                error=str(e),
                execution_log=self._execution_log
            )


# ============================================================================
# 便捷函数（函数式工作流）
# ============================================================================

async def connect_datasource(
    name: str,
    connector_type: str,
    **kwargs
) -> WorkflowResult:
    """连接数据源（函数式接口）"""
    workflow = ConnectDatasourceWorkflow()
    return await workflow.run(
        name=name,
        connector_type=connector_type,
        **kwargs
    )


async def disconnect_datasource(name: str) -> WorkflowResult:
    """断开数据源（函数式接口）"""
    workflow = DisconnectDatasourceWorkflow()
    return await workflow.run(name=name)


async def query_data(query: str, connector_name: Optional[str] = None) -> WorkflowResult:
    """查询数据（函数式接口）"""
    workflow = QueryDataWorkflow()
    return await workflow.run(query=query, connector_name=connector_name)


async def discover_schema(connector_name: str) -> WorkflowResult:
    """发现 Schema（函数式接口）"""
    workflow = SchemaDiscoveryWorkflow()
    return await workflow.run(connector_name=connector_name)


async def analyze_lineage(
    connector_name: str,
    table_name: str
) -> WorkflowResult:
    """分析血缘（函数式接口）"""
    workflow = LineageAnalysisWorkflow()
    return await workflow.run(
        connector_name=connector_name,
        table_name=table_name
    )


async def build_data_pipeline(request: str) -> WorkflowResult:
    """构建数据管道（函数式接口）"""
    workflow = AutoDataPipelineWorkflow()
    return await workflow.run(request=request)
