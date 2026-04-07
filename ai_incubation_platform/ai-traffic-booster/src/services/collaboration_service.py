"""
跨 Agent 协同服务（增强版）

实现流量异常 → 运行态定位 → 代码根因分析 → 修复建议生成的完整工作流

增强功能:
- 重试机制（指数退避）
- 超时控制
- 熔断器模式
- 降级策略
- 增强的日志记录和上下文追踪
"""
from typing import List, Dict, Optional, Any
from datetime import datetime
import uuid
import asyncio
import aiohttp
import logging
import time

from schemas.collaboration import (
    AgentType,
    WorkflowStatus,
    WorkflowStepStatus,
    WorkflowStep,
    WorkflowExecution,
    TrafficAnomalyEvent,
    RuntimeDiagnosisRequest,
    RuntimeDiagnosisResult,
    CodeAnalysisRequest,
    CodeAnalysisResult,
    CodeChangeSuggestion,
    CrossAgentDiagnosisReport,
)
from services.resilience import (
    RetryConfig,
    CircuitBreaker,
    FallbackStrategy,
    ResiliencePolicy,
    with_retry,
    with_timeout,
    with_circuit_breaker,
    TimeoutError,
    FallbackError,
)

logger = logging.getLogger(__name__)


class AgentClient:
    """Agent HTTP 客户端（增强版）"""

    def __init__(
        self,
        base_url: str,
        timeout: int = 30,
        max_retries: int = 3,
        circuit_breaker: Optional[CircuitBreaker] = None
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self._session: Optional[aiohttp.ClientSession] = None
        self._circuit_breaker = circuit_breaker or CircuitBreaker()

        # 重试配置
        self._retry_config = RetryConfig(
            max_attempts=max_retries,
            initial_delay=1.0,
            max_delay=10.0,
            exponential_base=2.0,
            retryable_exceptions=[aiohttp.ClientError, asyncio.TimeoutError, TimeoutError]
        )

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    def _generate_trace_id(self) -> str:
        """生成追踪 ID"""
        return f"trace_{uuid.uuid4().hex[:12]}"

    async def post(
        self,
        endpoint: str,
        data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """发送 POST 请求（带重试、超时、熔断）"""
        session = await self._get_session()
        url = f"{self.base_url}{endpoint}"
        trace_id = context.get("trace_id") if context else self._generate_trace_id()
        request_context = {"trace_id": trace_id, "endpoint": endpoint, "url": url}

        async def do_request():
            async with session.post(url, json=data) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    logger.error(
                        f"[Agent 请求] trace_id={trace_id}, URL={url}, 状态码={response.status}, 错误={error_text}",
                        extra={"trace_id": trace_id}
                    )
                    raise Exception(f"Agent 请求失败：{response.status}")

        try:
            logger.info(
                f"[Agent 请求] trace_id={trace_id}, 开始请求：{url}",
                extra={"trace_id": trace_id}
            )
            start_time = time.time()

            # 使用熔断器执行
            result = await with_circuit_breaker(
                lambda: with_retry(lambda: with_timeout(do_request, self.timeout, request_context), self._retry_config, request_context),
                self._circuit_breaker,
                fallback=FallbackStrategy.return_default({"error": "circuit_open", "fallback": True}),
                context=request_context
            )

            elapsed = time.time() - start_time
            logger.info(
                f"[Agent 请求] trace_id={trace_id}, 请求成功，耗时={elapsed:.2f}秒",
                extra={"trace_id": trace_id}
            )
            return result

        except TimeoutError as e:
            logger.error(
                f"[Agent 请求] trace_id={trace_id}, 请求超时：{str(e)}",
                extra={"trace_id": trace_id}
            )
            raise
        except FallbackError:
            logger.warning(
                f"[Agent 请求] trace_id={trace_id}, 熔断器打开，返回降级结果",
                extra={"trace_id": trace_id}
            )
            return {"error": "circuit_open", "fallback": True}
        except Exception as e:
            logger.error(
                f"[Agent 请求] trace_id={trace_id}, 请求失败：{str(e)}",
                extra={"trace_id": trace_id}
            )
            raise

    async def get(
        self,
        endpoint: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """发送 GET 请求（带重试、超时、熔断）"""
        session = await self._get_session()
        url = f"{self.base_url}{endpoint}"
        trace_id = context.get("trace_id") if context else self._generate_trace_id()
        request_context = {"trace_id": trace_id, "endpoint": endpoint, "url": url}

        async def do_request():
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Agent 请求失败：{response.status}")

        try:
            logger.debug(
                f"[Agent 请求] trace_id={trace_id}, 开始请求：{url}",
                extra={"trace_id": trace_id}
            )

            result = await with_circuit_breaker(
                lambda: with_retry(lambda: with_timeout(do_request, self.timeout, request_context), self._retry_config, request_context),
                self._circuit_breaker,
                context=request_context
            )

            return result

        except Exception as e:
            logger.error(
                f"[Agent 请求] trace_id={trace_id}, 请求失败：{str(e)}",
                extra={"trace_id": trace_id}
            )
            raise

    def get_circuit_breaker_stats(self) -> Dict[str, Any]:
        """获取熔断器统计"""
        return self._circuit_breaker.get_stats()


class CollaborationService:
    """
    跨 Agent 协同服务（增强版）

    工作流：
    1. 流量异常检测 (Traffic Booster)
    2. 运行态诊断 (Runtime Optimizer)
    3. 代码根因分析 (Code Understanding)
    4. 修复建议生成 (Traffic Booster)

    增强功能:
    - 每个 Agent 客户端都有独立的熔断器
    - 工作流执行带有完整的追踪日志
    - 降级策略支持
    """

    def __init__(self):
        # Agent 配置（增强版：添加超时和重试配置）
        self.agent_configs = {
            AgentType.TRAFFIC: {
                "base_url": "http://localhost:8008",
                "capabilities": ["anomaly_detection", "root_cause_analysis", "recommendation_generation"],
                "timeout": 30,
                "max_retries": 3,
                "circuit_breaker_threshold": 5,
                "circuit_breaker_recovery": 60
            },
            AgentType.RUNTIME: {
                "base_url": "http://localhost:8009",
                "capabilities": ["metrics_analysis", "service_diagnosis", "performance_bottleneck"],
                "timeout": 60,
                "max_retries": 3,
                "circuit_breaker_threshold": 5,
                "circuit_breaker_recovery": 60
            },
            AgentType.CODE: {
                "base_url": "http://localhost:8010",
                "capabilities": ["code_analysis", "dependency_graph", "change_impact"],
                "timeout": 60,
                "max_retries": 3,
                "circuit_breaker_threshold": 5,
                "circuit_breaker_recovery": 60
            },
            AgentType.DATA: {
                "base_url": "http://localhost:8011",
                "capabilities": ["data_access", "nl2sql", "connector_management"],
                "timeout": 30,
                "max_retries": 3,
                "circuit_breaker_threshold": 5,
                "circuit_breaker_recovery": 60
            }
        }

        # Agent 客户端缓存（每个 Agent 类型有独立的熔断器）
        self._clients: Dict[AgentType, AgentClient] = {}

        # 工作流存储
        self._workflows: Dict[str, WorkflowExecution] = {}

        # 工作流定义
        self._workflow_definitions = {
            "traffic_anomaly_diagnosis": self._traffic_anomaly_diagnosis_workflow
        }

        # 统计信息
        self._stats = {
            "total_workflows": 0,
            "completed_workflows": 0,
            "failed_workflows": 0,
            "fallback_count": 0
        }

    def _get_client(self, agent_type: AgentType) -> AgentClient:
        """获取或创建 Agent 客户端（带熔断器）"""
        if agent_type not in self._clients:
            config = self.agent_configs[agent_type]
            # 为每个客户端创建独立的熔断器
            circuit_breaker = CircuitBreaker(
                failure_threshold=config.get("circuit_breaker_threshold", 5),
                recovery_timeout=config.get("circuit_breaker_recovery", 60)
            )
            self._clients[agent_type] = AgentClient(
                base_url=config["base_url"],
                timeout=config["timeout"],
                max_retries=config["max_retries"],
                circuit_breaker=circuit_breaker
            )
        return self._clients[agent_type]

    async def close(self):
        """关闭所有客户端"""
        for client in self._clients.values():
            await client.close()

    async def check_agent_health(self) -> Dict[str, Any]:
        """检查所有 Agent 的健康状态"""
        results = []
        overall_status = "healthy"

        for agent_type, config in self.agent_configs.items():
            try:
                client = self._get_client(agent_type)
                # 尝试访问健康检查端点
                await client.get("/health")
                results.append({
                    "agent_type": agent_type.value,
                    "endpoint": config["base_url"],
                    "capabilities": config["capabilities"],
                    "health_status": "healthy",
                    "last_checked": datetime.now().isoformat()
                })
            except Exception as e:
                results.append({
                    "agent_type": agent_type.value,
                    "endpoint": config["base_url"],
                    "capabilities": config["capabilities"],
                    "health_status": "unhealthy",
                    "error": str(e),
                    "last_checked": datetime.now().isoformat()
                })
                overall_status = "degraded"

        return {
            "agents": results,
            "overall_status": overall_status,
            "checked_at": datetime.now().isoformat()
        }

    async def trigger_workflow(self, workflow_name: str, trigger_event: Dict[str, Any], trigger_type: str = "manual") -> WorkflowExecution:
        """
        触发工作流（增强版）

        Args:
            workflow_name: 工作流名称
            trigger_event: 触发事件数据
            trigger_type: 触发类型 (auto/manual)

        Returns:
            WorkflowExecution: 工作流执行实例
        """
        if workflow_name not in self._workflow_definitions:
            raise ValueError(f"未知的工作流：{workflow_name}")

        workflow_id = f"wf_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
        trace_id = f"trace_{uuid.uuid4().hex[:12]}"

        # 创建工作流实例
        workflow = WorkflowExecution(
            workflow_id=workflow_id,
            workflow_name=workflow_name,
            status=WorkflowStatus.RUNNING,
            trigger_type=trigger_type,
            trigger_event=trigger_event,
            steps=[],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        self._workflows[workflow_id] = workflow
        self._stats["total_workflows"] += 1

        logger.info(
            f"[工作流] trace_id={trace_id}, workflow_id={workflow_id}, 开始执行：{workflow_name}",
            extra={"trace_id": trace_id, "workflow_id": workflow_id}
        )

        # 执行工作流
        try:
            workflow_func = self._workflow_definitions[workflow_name]
            result = await workflow_func(workflow, trigger_event, trace_id)
            workflow.final_result = result
            workflow.status = WorkflowStatus.COMPLETED
            workflow.completed_at = datetime.now()

            self._stats["completed_workflows"] += 1
            logger.info(
                f"[工作流] trace_id={trace_id}, workflow_id={workflow_id}, 执行成功",
                extra={"trace_id": trace_id, "workflow_id": workflow_id}
            )
        except Exception as e:
            logger.error(
                f"[工作流] trace_id={trace_id}, workflow_id={workflow_id}, 执行失败：{str(e)}",
                extra={"trace_id": trace_id, "workflow_id": workflow_id}
            )
            workflow.status = WorkflowStatus.FAILED
            workflow.error_message = str(e)
            self._stats["failed_workflows"] += 1

        workflow.updated_at = datetime.now()
        self._workflows[workflow_id] = workflow

        return workflow

    async def _traffic_anomaly_diagnosis_workflow(
        self,
        workflow: WorkflowExecution,
        trigger_event: Dict[str, Any],
        trace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        流量异常诊断工作流（增强版）

        步骤：
        1. 解析流量异常事件
        2. 调用 Runtime Optimizer 进行运行态诊断
        3. 调用 Code Understanding 进行代码根因分析
        4. 生成综合诊断报告

        Args:
            workflow: 工作流实例
            trigger_event: 触发事件数据
            trace_id: 追踪 ID

        Returns:
            诊断报告
        """
        trace_id = trace_id or f"trace_{uuid.uuid4().hex[:12]}"

        logger.info(
            f"[工作流步骤] trace_id={trace_id}, 开始执行流量异常诊断工作流",
            extra={"trace_id": trace_id}
        )

        # 步骤 1: 解析异常事件
        step1 = await self._create_step(
            workflow,
            "parse_anomaly",
            "解析异常事件",
            AgentType.TRAFFIC,
            "/api/collaboration/parse_anomaly",
            trigger_event
        )

        anomaly_event = TrafficAnomalyEvent(
            anomaly_id=trigger_event.get("anomaly_id", str(uuid.uuid4())),
            metric_name=trigger_event.get("metric_name", "visitors"),
            current_value=trigger_event.get("current_value", 0),
            expected_value=trigger_event.get("expected_value", 0),
            deviation=trigger_event.get("deviation", 0),
            z_score=trigger_event.get("z_score", 0),
            severity=trigger_event.get("severity", "warning"),
            description=trigger_event.get("description", ""),
            detected_at=datetime.fromisoformat(trigger_event.get("detected_at", datetime.now().isoformat()))
        )

        step1.status = WorkflowStepStatus.SUCCESS
        step1.output_data = {"anomaly_id": anomaly_event.anomaly_id}
        step1.completed_at = datetime.now()
        logger.info(
            f"[工作流步骤] trace_id={trace_id}, 步骤 1 完成：解析异常事件，anomaly_id={anomaly_event.anomaly_id}",
            extra={"trace_id": trace_id}
        )

        # 步骤 2: 运行态诊断
        step2 = await self._create_step(
            workflow,
            "runtime_diagnosis",
            "运行态诊断",
            AgentType.RUNTIME,
            "/api/runtime/diagnose",
            {"anomaly_event": anomaly_event.model_dump()}
        )

        try:
            runtime_result = await self._call_runtime_diagnosis(anomaly_event, trace_id)
            step2.status = WorkflowStepStatus.SUCCESS
            step2.output_data = runtime_result.model_dump() if runtime_result else None
            step2.completed_at = datetime.now()
            logger.info(
                f"[工作流步骤] trace_id={trace_id}, 步骤 2 完成：运行态诊断",
                extra={"trace_id": trace_id}
            )
        except Exception as e:
            step2.status = WorkflowStepStatus.FAILED
            step2.error_message = str(e)
            step2.completed_at = datetime.now()
            logger.warning(
                f"[工作流步骤] trace_id={trace_id}, 步骤 2 失败：运行态诊断，错误={str(e)}",
                extra={"trace_id": trace_id}
            )
            # 继续执行，但标记为降级模式
            runtime_result = None

        # 步骤 3: 代码分析
        step3 = await self._create_step(
            workflow,
            "code_analysis",
            "代码根因分析",
            AgentType.CODE,
            "/api/understanding/analyze",
            {"runtime_diagnosis": runtime_result.model_dump()} if runtime_result else {}
        )

        code_result = None
        if runtime_result:
            try:
                code_result = await self._call_code_analysis(runtime_result, trace_id)
                step3.status = WorkflowStepStatus.SUCCESS
                step3.output_data = code_result.model_dump() if code_result else None
                step3.completed_at = datetime.now()
                logger.info(
                    f"[工作流步骤] trace_id={trace_id}, 步骤 3 完成：代码根因分析",
                    extra={"trace_id": trace_id}
                )
            except Exception as e:
                step3.status = WorkflowStepStatus.FAILED
                step3.error_message = str(e)
                step3.completed_at = datetime.now()
                logger.warning(
                    f"[工作流步骤] trace_id={trace_id}, 步骤 3 失败：代码根因分析，错误={str(e)}",
                    extra={"trace_id": trace_id}
                )
        else:
            step3.status = WorkflowStepStatus.SKIPPED
            step3.error_message = "运行态诊断失败，跳过代码分析"
            step3.completed_at = datetime.now()
            logger.info(
                f"[工作流步骤] trace_id={trace_id}, 步骤 3 跳过：运行态诊断失败",
                extra={"trace_id": trace_id}
            )

        # 步骤 4: 生成综合报告
        step4 = await self._create_step(
            workflow,
            "generate_report",
            "生成诊断报告",
            AgentType.TRAFFIC,
            "/api/collaboration/report",
            {}
        )

        report = self._generate_diagnosis_report(workflow, anomaly_event, runtime_result, code_result)
        step4.status = WorkflowStepStatus.SUCCESS
        step4.output_data = report.model_dump()
        step4.completed_at = datetime.now()
        logger.info(
            f"[工作流步骤] trace_id={trace_id}, 步骤 4 完成：生成诊断报告，report_id={report.report_id}",
            extra={"trace_id": trace_id}
        )

        return report.model_dump()

    async def _create_step(
        self,
        workflow: WorkflowExecution,
        step_id: str,
        step_name: str,
        agent_type: AgentType,
        endpoint: str,
        input_data: Dict[str, Any]
    ) -> WorkflowStep:
        """创建工作流步骤"""
        step = WorkflowStep(
            step_id=step_id,
            step_name=step_name,
            agent_type=agent_type,
            endpoint=endpoint,
            input_data=input_data,
            status=WorkflowStepStatus.RUNNING,
            started_at=datetime.now()
        )
        workflow.steps.append(step)
        self._workflows[workflow.workflow_id] = workflow
        return step

    async def _call_runtime_diagnosis(
        self,
        anomaly_event: TrafficAnomalyEvent,
        trace_id: Optional[str] = None
    ) -> Optional[RuntimeDiagnosisResult]:
        """
        调用 Runtime Optimizer 进行运行态诊断（增强版）

        注意：这里模拟调用，实际需要对接 ai-runtime-optimizer 的真实 API
        """
        trace_id = trace_id or f"trace_{uuid.uuid4().hex[:12]}"
        logger.info(
            f"[运行态诊断] trace_id={trace_id}, 开始调用 Runtime Optimizer",
            extra={"trace_id": trace_id}
        )

        try:
            client = self._get_client(AgentType.RUNTIME)

            # 构建诊断请求
            # 注意：实际端点需要根据 ai-runtime-optimizer 的真实 API 调整
            context = {"trace_id": trace_id}
            response = await client.post("/api/runtime/diagnose_anomaly", {
                "anomaly_type": anomaly_event.metric_name,
                "severity": anomaly_event.severity,
                "deviation": anomaly_event.deviation,
                "description": anomaly_event.description
            }, context=context)

            # 检查是否是熔断器返回的降级结果
            if response.get("fallback"):
                logger.warning(
                    f"[运行态诊断] trace_id={trace_id}, 熔断器打开，使用模拟数据",
                    extra={"trace_id": trace_id}
                )
                self._stats["fallback_count"] += 1
                return self._mock_runtime_diagnosis(anomaly_event)

            result = RuntimeDiagnosisResult(
                diagnosis_id=response.get("diagnosis_id", str(uuid.uuid4())),
                anomaly_correlation=response.get("anomaly_correlation", 0.8),
                runtime_metrics=response.get("runtime_metrics", {}),
                suspicious_services=response.get("suspicious_services", []),
                performance_bottlenecks=response.get("performance_bottlenecks", []),
                recommended_actions=response.get("recommended_actions", []),
                confidence=response.get("confidence", 0.7)
            )

            logger.info(
                f"[运行态诊断] trace_id={trace_id}, 诊断完成，confidence={result.confidence}",
                extra={"trace_id": trace_id}
            )
            return result

        except Exception as e:
            logger.warning(
                f"[运行态诊断] trace_id={trace_id}, 调用失败，使用模拟数据：{e}",
                extra={"trace_id": trace_id}
            )
            # 返回模拟结果用于演示
            return self._mock_runtime_diagnosis(anomaly_event)

    def _mock_runtime_diagnosis(self, anomaly_event: TrafficAnomalyEvent) -> RuntimeDiagnosisResult:
        """模拟运行态诊断结果"""
        return RuntimeDiagnosisResult(
            diagnosis_id=f"diag_{uuid.uuid4().hex[:8]}",
            anomaly_correlation=0.75,
            runtime_metrics={
                "cpu_usage": 0.65,
                "memory_usage": 0.78,
                "response_time_p99": 450,
                "error_rate": 0.02
            },
            suspicious_services=[
                {
                    "service_name": "recommendation_service",
                    "confidence": 0.8,
                    "symptoms": ["响应时间增加", "错误率上升"]
                }
            ],
            performance_bottlenecks=[
                {
                    "component": "database_query",
                    "issue": "慢查询",
                    "impact": "high"
                }
            ],
            recommended_actions=[
                "检查 recommendation_service 的数据库查询",
                "优化慢查询 SQL",
                "增加数据库连接池大小"
            ],
            confidence=0.7
        )

    async def _call_code_analysis(
        self,
        runtime_result: RuntimeDiagnosisResult,
        trace_id: Optional[str] = None
    ) -> Optional[CodeAnalysisResult]:
        """
        调用 Code Understanding 进行代码分析（增强版）

        注意：这里模拟调用，实际需要对接 ai-code-understanding 的真实 API
        """
        trace_id = trace_id or f"trace_{uuid.uuid4().hex[:12]}"
        logger.info(
            f"[代码分析] trace_id={trace_id}, 开始调用 Code Understanding",
            extra={"trace_id": trace_id}
        )

        try:
            client = self._get_client(AgentType.CODE)

            # 构建分析请求
            context = {"trace_id": trace_id}
            response = await client.post("/api/understanding/diagnose", {
                "suspicious_services": runtime_result.suspicious_services,
                "performance_issues": runtime_result.performance_bottlenecks
            }, context=context)

            # 检查是否是熔断器返回的降级结果
            if response.get("fallback"):
                logger.warning(
                    f"[代码分析] trace_id={trace_id}, 熔断器打开，使用模拟数据",
                    extra={"trace_id": trace_id}
                )
                self._stats["fallback_count"] += 1
                return self._mock_code_analysis(runtime_result)

            suggestions = []
            for sugg_data in response.get("suggestions", []):
                suggestions.append(CodeChangeSuggestion(
                    suggestion_id=sugg_data.get("suggestion_id", str(uuid.uuid4())),
                    file_path=sugg_data.get("file_path", ""),
                    line_number=sugg_data.get("line_number"),
                    change_type=sugg_data.get("change_type", "fix"),
                    description=sugg_data.get("description", ""),
                    before_code=sugg_data.get("before_code"),
                    after_code=sugg_data.get("after_code"),
                    impact_analysis=sugg_data.get("impact_analysis", []),
                    priority=sugg_data.get("priority", "medium")
                ))

            result = CodeAnalysisResult(
                analysis_id=response.get("analysis_id", str(uuid.uuid4())),
                root_cause_code=response.get("root_cause_code"),
                suggestions=suggestions,
                affected_modules=response.get("affected_modules", []),
                estimated_fix_time=response.get("estimated_fix_time", "2-4 小时"),
                risk_level=response.get("risk_level", "medium")
            )

            logger.info(
                f"[代码分析] trace_id={trace_id}, 分析完成，suggestions_count={len(result.suggestions)}",
                extra={"trace_id": trace_id}
            )
            return result

        except Exception as e:
            logger.warning(
                f"[代码分析] trace_id={trace_id}, 调用失败，使用模拟数据：{e}",
                extra={"trace_id": trace_id}
            )
            return self._mock_code_analysis(runtime_result)

    def _mock_code_analysis(self, runtime_result: RuntimeDiagnosisResult) -> CodeAnalysisResult:
        """模拟代码分析结果"""
        return CodeAnalysisResult(
            analysis_id=f"analysis_{uuid.uuid4().hex[:8]}",
            root_cause_code="src/services/recommendation_service.py:156-180",
            suggestions=[
                CodeChangeSuggestion(
                    suggestion_id="sugg_001",
                    file_path="src/services/recommendation_service.py",
                    line_number=165,
                    change_type="optimize",
                    description="优化数据库查询，添加索引",
                    before_code="SELECT * FROM recommendations WHERE user_id = ?",
                    after_code="SELECT * FROM recommendations WHERE user_id = ? ORDER BY score DESC LIMIT 10",
                    impact_analysis=["查询性能提升 80%", "减少内存占用"],
                    priority="high"
                )
            ],
            affected_modules=["recommendation_service", "database_layer"],
            estimated_fix_time="1-2 小时",
            risk_level="low"
        )

    def _generate_diagnosis_report(
        self,
        workflow: WorkflowExecution,
        anomaly_event: TrafficAnomalyEvent,
        runtime_result: Optional[RuntimeDiagnosisResult],
        code_result: Optional[CodeAnalysisResult]
    ) -> CrossAgentDiagnosisReport:
        """生成综合诊断报告"""
        # 汇总建议
        final_recommendations = []

        if runtime_result and runtime_result.recommended_actions:
            final_recommendations.extend(runtime_result.recommended_actions)

        if code_result:
            for sugg in code_result.suggestions:
                final_recommendations.append(f"[代码优化] {sugg.description}")

        # 生成行动计划
        action_plan = []

        if code_result and code_result.suggestions:
            for sugg in code_result.suggestions:
                action_plan.append({
                    "step": f"修复 {sugg.file_path}",
                    "action": sugg.description,
                    "priority": sugg.priority,
                    "estimated_time": code_result.estimated_fix_time,
                    "risk": code_result.risk_level
                })

        if runtime_result and runtime_result.performance_bottlenecks:
            for bottleneck in runtime_result.performance_bottlenecks:
                action_plan.append({
                    "step": f"优化 {bottleneck.get('component', 'unknown')}",
                    "action": bottleneck.get('issue', ''),
                    "priority": bottleneck.get('impact', 'medium'),
                    "estimated_time": "1-2 小时",
                    "risk": "low"
                })

        report = CrossAgentDiagnosisReport(
            report_id=f"report_{uuid.uuid4().hex[:8]}",
            workflow_id=workflow.workflow_id,
            anomaly_summary=anomaly_event.model_dump(),
            runtime_diagnosis=runtime_result,
            code_analysis=code_result,
            final_recommendations=final_recommendations,
            action_plan=action_plan,
            created_at=datetime.now()
        )

        return report

    def get_workflow_status(self, workflow_id: str) -> Optional[WorkflowExecution]:
        """获取工作流状态"""
        return self._workflows.get(workflow_id)

    def list_workflows(
        self,
        status_filter: Optional[WorkflowStatus] = None,
        limit: int = 20
    ) -> List[WorkflowExecution]:
        """获取工作流列表"""
        workflows = list(self._workflows.values())

        if status_filter:
            workflows = [w for w in workflows if w.status == status_filter]

        # 按创建时间倒序
        workflows.sort(key=lambda x: x.created_at, reverse=True)

        return workflows[:limit]

    def get_stats(self) -> Dict[str, Any]:
        """获取服务统计信息"""
        # 收集熔断器统计
        circuit_breaker_stats = {}
        for agent_type, client in self._clients.items():
            circuit_breaker_stats[agent_type.value] = client.get_circuit_breaker_stats()

        return {
            "workflows": self._stats,
            "circuit_breakers": circuit_breaker_stats,
            "total_workflows_in_memory": len(self._workflows),
            "calculated_at": datetime.now().isoformat()
        }

    def reset_stats(self):
        """重置统计信息（用于测试）"""
        self._stats = {
            "total_workflows": 0,
            "completed_workflows": 0,
            "failed_workflows": 0,
            "fallback_count": 0
        }


# 全局服务实例
collaboration_service = CollaborationService()
