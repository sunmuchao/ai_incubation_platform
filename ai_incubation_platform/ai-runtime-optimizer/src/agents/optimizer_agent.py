"""
Optimizer Agent - Core AI Agent for Runtime Optimization

This agent orchestrates performance analysis, bottleneck detection,
and autonomous optimization using DeerFlow 2.0 framework.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from .deerflow_client import DeerFlowClient, get_deerflow_client
from models.signals import Signal, Diagnosis, ExecutionResult

logger = logging.getLogger(__name__)


class AgentState(Enum):
    """Agent operational states."""
    IDLE = "idle"
    PERCEIVING = "perceiving"
    DIAGNOSING = "diagnosing"
    REMEDIATING = "remediating"
    OPTIMIZING = "optimizing"
    ERROR = "error"


class OptimizerAgent:
    """
    Main AI Agent for runtime optimization.

    This agent coordinates the perception, diagnosis, remediation,
    and optimization workflows using DeerFlow 2.0.
    """

    def __init__(
        self,
        deerflow_client: Optional[DeerFlowClient] = None,
        auto_execute_threshold: float = 0.9,
        audit_enabled: bool = True,
    ):
        """
        Initialize the Optimizer Agent.

        Args:
            deerflow_client: DeerFlow client instance
            auto_execute_threshold: Confidence threshold for auto-execution
            audit_enabled: Whether to enable audit logging
        """
        self.df_client = deerflow_client or get_deerflow_client()
        self.auto_execute_threshold = auto_execute_threshold
        self.audit_enabled = audit_enabled
        self._state = AgentState.IDLE
        self._local_workflows: Dict[str, callable] = {}
        self._tools: Dict[str, callable] = {}

        # Register local fallback workflows
        self._register_default_workflows()

    def _register_default_workflows(self):
        """Register default local fallback workflows."""
        self._local_workflows = {
            "analyze_performance": self._local_analyze_performance,
            "diagnose_issue": self._local_diagnose_issue,
            "execute_remediation": self._local_execute_remediation,
            "generate_optimization": self._local_generate_optimization,
            "validate_optimization": self._local_validate_optimization,
        }

    @property
    def state(self) -> AgentState:
        """Get current agent state."""
        return self._state

    @state.setter
    def state(self, value: AgentState):
        """Set agent state."""
        old_state = self._state
        self._state = value
        logger.info(f"Agent state changed: {old_state.value} -> {value.value}")

    async def perceive(self, service: Optional[str] = None) -> List[Signal]:
        """
        Perceive signals from the environment.

        This method collects metrics, logs, and tracing data,
        identifies anomalies and patterns.

        Args:
            service: Optional service filter

        Returns:
            List of detected signals
        """
        self.state = AgentState.PERCEIVING
        signals = []

        try:
            # Use DeerFlow workflow if available, otherwise use local fallback
            result = await self.df_client.run_workflow(
                "perceive_signals",
                service=service
            )
            signals = [
                Signal(
                    id=s["id"],
                    source=s["source"],
                    type=s["type"],
                    severity=s["severity"],
                    timestamp=datetime.fromisoformat(s["timestamp"]),
                    data=s["data"],
                    context=s.get("context", {})
                )
                for s in result.get("signals", [])
            ]
        except Exception as e:
            logger.warning(f"DeerFlow workflow failed, using local fallback: {e}")
            signals = await self._local_perceive(service)

        self.state = AgentState.IDLE
        logger.info(f"Perception complete: found {len(signals)} signals")
        return signals

    async def _local_perceive(self, service: Optional[str] = None) -> List[Signal]:
        """Local fallback for perception."""
        signals = []
        try:
            # Import performance tools for local analysis
            from tools.performance_tools import get_performance_analyzer

            analyzer = get_performance_analyzer()
            metrics_signals = await analyzer.detect_anomalies(service=service)
            signals.extend(metrics_signals)
        except Exception as e:
            logger.error(f"Local perception failed: {e}")

        return signals

    async def diagnose(self, signals: List[Signal]) -> Optional[Diagnosis]:
        """
        Diagnose the root cause from signals.

        This method coordinates multiple diagnostic agents to
        analyze signals and identify the root cause.

        Args:
            signals: List of signals to analyze

        Returns:
            Diagnosis result or None if no issue found
        """
        if not signals:
            return None

        self.state = AgentState.DIAGNOSING

        try:
            # Prepare signals for workflow
            signals_data = [
                {
                    "id": s.id,
                    "source": s.source,
                    "type": s.type,
                    "severity": s.severity,
                    "timestamp": s.timestamp.isoformat(),
                    "data": s.data,
                    "context": s.context,
                }
                for s in signals
            ]

            result = await self.df_client.run_workflow(
                "diagnose_signals",
                signals=signals_data
            )

            diagnosis = Diagnosis(
                id=result["id"],
                root_cause=result["root_cause"],
                confidence=result["confidence"],
                evidence=result.get("evidence", []),
                affected_services=result.get("affected_services", []),
                impact_assessment=result.get("impact_assessment", {}),
                report=result.get("report", ""),
                recommended_actions=result.get("recommended_actions", []),
            )

        except Exception as e:
            logger.warning(f"DeerFlow diagnosis failed, using local fallback: {e}")
            diagnosis = await self._local_diagnose(signals)

        self.state = AgentState.IDLE
        logger.info(f"Diagnosis complete: {diagnosis.root_cause} (confidence: {diagnosis.confidence:.2f})")
        return diagnosis

    async def _local_diagnose(self, signals: List[Signal]) -> Diagnosis:
        """Local fallback for diagnosis."""
        try:
            from tools.performance_tools import get_performance_analyzer

            analyzer = get_performance_analyzer()
            diagnosis_result = await analyzer.analyze_root_cause(signals)

            return Diagnosis(
                id=str(uuid.uuid4()),
                root_cause=diagnosis_result.get("root_cause", "Unknown"),
                confidence=diagnosis_result.get("confidence", 0.5),
                evidence=diagnosis_result.get("evidence", []),
                affected_services=diagnosis_result.get("affected_services", []),
                impact_assessment=diagnosis_result.get("impact_assessment", {}),
                report=diagnosis_result.get("report", ""),
                recommended_actions=diagnosis_result.get("recommended_actions", []),
            )
        except Exception as e:
            logger.error(f"Local diagnosis failed: {e}")
            return Diagnosis(
                id=str(uuid.uuid4()),
                root_cause="Unknown (diagnosis failed)",
                confidence=0.0,
                evidence=[],
                affected_services=[],
                impact_assessment={},
                report=f"Diagnosis failed: {str(e)}",
                recommended_actions=[],
            )

    async def remediate(
        self,
        diagnosis: Diagnosis,
        auto_execute: bool = True
    ) -> ExecutionResult:
        """
        Execute remediation actions.

        Args:
            diagnosis: Diagnosis result with recommended actions
            auto_execute: Whether to auto-execute high-confidence actions

        Returns:
            Execution result
        """
        self.state = AgentState.REMEDIATING

        # Check if auto-execution is appropriate
        should_auto_execute = (
            auto_execute and
            diagnosis.confidence >= self.auto_execute_threshold
        )

        if not should_auto_execute:
            logger.info(f"Confidence {diagnosis.confidence:.2f} below threshold {self.auto_execute_threshold}, skipping auto-remediation")
            self.state = AgentState.IDLE
            return ExecutionResult(
                success=False,
                action_type="remediate",
                action_name="pending_approval",
                details={"reason": "Low confidence, manual approval required"},
            )

        try:
            # Get the highest priority action
            if not diagnosis.recommended_actions:
                return ExecutionResult(
                    success=False,
                    action_type="remediate",
                    action_name="no_actions",
                    details={"reason": "No recommended actions"},
                )

            action = diagnosis.recommended_actions[0]

            result = await self.df_client.run_workflow(
                "execute_remediation",
                action=action,
                diagnosis_id=diagnosis.id
            )

            execution_result = ExecutionResult(
                success=result.get("success", False),
                action_type="remediate",
                action_name=action.get("name", "unknown"),
                details=result,
                validation_result=result.get("validation"),
                rollback_performed=result.get("rollback_performed", False),
            )

        except Exception as e:
            logger.error(f"Remediation execution failed: {e}")
            execution_result = ExecutionResult(
                success=False,
                action_type="remediate",
                action_name="error",
                details={},
                error_message=str(e),
            )

        self.state = AgentState.IDLE
        return execution_result

    async def optimize(self, context: Optional[Dict[str, Any]] = None) -> ExecutionResult:
        """
        Perform proactive optimization.

        Args:
            context: Optional context for optimization (service info, metrics, etc.)

        Returns:
            Execution result
        """
        self.state = AgentState.OPTIMIZING

        try:
            result = await self.df_client.run_workflow(
                "generate_optimization",
                context=context or {}
            )

            execution_result = ExecutionResult(
                success=result.get("success", False),
                action_type="optimize",
                action_name=result.get("optimization_name", "unknown"),
                details=result,
                validation_result=result.get("validation"),
            )

        except Exception as e:
            logger.error(f"Optimization failed: {e}")
            execution_result = ExecutionResult(
                success=False,
                action_type="optimize",
                action_name="error",
                details={},
                error_message=str(e),
            )

        self.state = AgentState.IDLE
        return execution_result

    async def analyze_and_optimize(
        self,
        service: Optional[str] = None,
        auto_execute: bool = True
    ) -> Dict[str, Any]:
        """
        Full autonomous optimization loop.

        This is the main entry point for AI-native operations:
        1. Perceive signals
        2. Diagnose root cause
        3. Execute remediation (if confidence is high enough)
        4. Generate optimization suggestions

        Args:
            service: Optional service filter
            auto_execute: Whether to auto-execute remediation

        Returns:
            Full analysis and optimization result
        """
        trace_id = str(uuid.uuid4())
        logger.info(f"Starting autonomous optimization loop (trace_id={trace_id})")

        result = {
            "trace_id": trace_id,
            "timestamp": datetime.now().isoformat(),
            "service": service,
            "signals": [],
            "diagnosis": None,
            "remediation": None,
            "optimization": None,
        }

        try:
            # Step 1: Perceive
            signals = await self.perceive(service=service)
            result["signals"] = [
                {"id": s.id, "source": s.source, "type": s.type, "severity": s.severity}
                for s in signals
            ]

            if not signals:
                logger.info("No signals detected, system appears healthy")
                return result

            # Step 2: Diagnose
            diagnosis = await self.diagnose(signals)
            if diagnosis:
                result["diagnosis"] = {
                    "id": diagnosis.id,
                    "root_cause": diagnosis.root_cause,
                    "confidence": diagnosis.confidence,
                    "report": diagnosis.report,
                    "affected_services": diagnosis.affected_services,
                }

                # Step 3: Remediate
                if auto_execute and diagnosis.confidence >= self.auto_execute_threshold:
                    remediation = await self.remediate(diagnosis, auto_execute=True)
                    result["remediation"] = {
                        "success": remediation.success,
                        "action": remediation.action_name,
                        "error": remediation.error_message,
                    }

            # Step 4: Optimize
            optimization = await self.optimize(context={"service": service})
            result["optimization"] = {
                "success": optimization.success,
                "action": optimization.action_name,
            }

        except Exception as e:
            logger.error(f"Autonomous optimization loop failed: {e}")
            result["error"] = str(e)

        logger.info(f"Autonomous optimization loop complete (trace_id={trace_id})")
        return result

    def register_tool(self, name: str, handler: callable):
        """Register a custom tool handler."""
        self._tools[name] = handler
        logger.info(f"Registered tool: {name}")

    def register_workflow(self, name: str, handler: callable):
        """Register a custom workflow handler for fallback mode."""
        self._local_workflows[name] = handler
        self.df_client.register_local_workflow(name, handler)
        logger.info(f"Registered workflow: {name}")

    # Local fallback workflow implementations
    async def _local_analyze_performance(self, **kwargs) -> Dict[str, Any]:
        """Local fallback for performance analysis workflow."""
        from tools.performance_tools import get_performance_analyzer
        analyzer = get_performance_analyzer()
        return await analyzer.analyze_service(kwargs.get("service"))

    async def _local_diagnose_issue(self, **kwargs) -> Dict[str, Any]:
        """Local fallback for issue diagnosis workflow."""
        signals_data = kwargs.get("signals", [])
        signals = [
            Signal(
                id=s["id"],
                source=s["source"],
                type=s["type"],
                severity=s["severity"],
                timestamp=datetime.fromisoformat(s["timestamp"]),
                data=s["data"],
            )
            for s in signals_data
        ]
        diagnosis = await self._local_diagnose(signals)
        return {
            "id": diagnosis.id,
            "root_cause": diagnosis.root_cause,
            "confidence": diagnosis.confidence,
            "report": diagnosis.report,
        }

    async def _local_execute_remediation(self, **kwargs) -> Dict[str, Any]:
        """Local fallback for remediation execution workflow."""
        # In local mode, we just simulate the execution
        action = kwargs.get("action", {})
        logger.info(f"[LOCAL MODE] Would execute remediation: {action.get('name')}")
        return {
            "success": True,
            "action": action.get("name"),
            "local_mode": True,
        }

    async def _local_generate_optimization(self, **kwargs) -> Dict[str, Any]:
        """Local fallback for optimization generation workflow."""
        # In local mode, we return a placeholder optimization
        context = kwargs.get("context", {})
        logger.info(f"[LOCAL MODE] Would generate optimization for: {context}")
        return {
            "success": True,
            "optimization_name": "local_placeholder",
            "local_mode": True,
        }

    async def _local_validate_optimization(self, **kwargs) -> Dict[str, Any]:
        """Local fallback for optimization validation workflow."""
        return {
            "success": True,
            "validated": True,
            "local_mode": True,
        }


# Global agent instance
_optimizer_agent: Optional[OptimizerAgent] = None


def get_optimizer_agent(
    deerflow_client: Optional[DeerFlowClient] = None,
    auto_execute_threshold: float = 0.9,
) -> OptimizerAgent:
    """
    Get or create the global Optimizer Agent instance.

    Args:
        deerflow_client: Optional DeerFlow client
        auto_execute_threshold: Confidence threshold for auto-execution

    Returns:
        Optimizer Agent instance
    """
    global _optimizer_agent
    if _optimizer_agent is None:
        _optimizer_agent = OptimizerAgent(
            deerflow_client=deerflow_client,
            auto_execute_threshold=auto_execute_threshold,
        )
    return _optimizer_agent


def reset_optimizer_agent():
    """Reset the global agent instance (useful for testing)."""
    global _optimizer_agent
    _optimizer_agent = None
