"""
Optimizer Workflows - Core Workflows for AI Native Operations

This module defines the main workflows for the AI Native runtime optimizer:
1. perceive_signals - Collect and analyze signals from the environment
2. diagnose_signals - Multi-agent diagnosis of detected issues
3. execute_remediation - Safe execution of remediation actions
4. generate_optimization - Proactive optimization generation
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class OptimizerWorkflows:
    """
    Core workflow definitions for the AI Native runtime optimizer.

    These workflows are designed to be executed by DeerFlow 2.0 framework,
    with local fallback implementations for standalone operation.
    """

    def __init__(self):
        self._workflow_definitions: Dict[str, Dict[str, Any]] = {}
        self._register_workflows()

    def _register_workflows(self):
        """Register all workflow definitions."""
        self._workflow_definitions = {
            "perceive_signals": {
                "name": "perceive_signals",
                "description": "Collect signals from metrics, logs, and tracing data",
                "version": "1.0.0",
                "steps": [
                    "collect_metrics",
                    "collect_logs",
                    "collect_traces",
                    "fuse_signals",
                    "filter_anomalies",
                ],
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "service": {
                            "type": "string",
                            "description": "Optional service filter"
                        },
                        "time_window": {
                            "type": "integer",
                            "description": "Time window in seconds",
                            "default": 300
                        }
                    }
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "signals": {
                            "type": "array",
                            "items": {"type": "object"}
                        },
                        "summary": {"type": "object"}
                    }
                }
            },
            "diagnose_signals": {
                "name": "diagnose_signals",
                "description": "Multi-agent diagnosis to identify root cause",
                "version": "1.0.0",
                "steps": [
                    "build_causal_graph",
                    "metrics_agent_analysis",
                    "logs_agent_analysis",
                    "traces_agent_analysis",
                    "consolidate_hypotheses",
                    "build_evidence_chain",
                    "generate_report",
                ],
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "signals": {
                            "type": "array",
                            "items": {"type": "object"},
                            "description": "List of signals to analyze"
                        }
                    },
                    "required": ["signals"]
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "root_cause": {"type": "string"},
                        "confidence": {"type": "number"},
                        "evidence": {"type": "array"},
                        "report": {"type": "string"},
                        "recommended_actions": {"type": "array"}
                    }
                }
            },
            "execute_remediation": {
                "name": "execute_remediation",
                "description": "Execute remediation action with safety checks",
                "version": "1.0.0",
                "steps": [
                    "assess_risk",
                    "check_approval",
                    "create_snapshot",
                    "execute_action",
                    "validate_result",
                    "cleanup_or_rollback",
                ],
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "object",
                            "description": "Remediation action to execute"
                        },
                        "diagnosis_id": {
                            "type": "string",
                            "description": "Associated diagnosis ID"
                        }
                    },
                    "required": ["action"]
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "action": {"type": "string"},
                        "validation": {"type": "object"},
                        "rollback_performed": {"type": "boolean"}
                    }
                }
            },
            "generate_optimization": {
                "name": "generate_optimization",
                "description": "Generate proactive optimization recommendations",
                "version": "1.0.0",
                "steps": [
                    "analyze_bottlenecks",
                    "generate_code_suggestions",
                    "estimate_impact",
                    "create_pull_request",
                ],
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "context": {
                            "type": "object",
                            "description": "Optimization context (service info, metrics, etc.)"
                        }
                    }
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "optimization_name": {"type": "string"},
                        "recommendations": {"type": "array"},
                        "pr_url": {"type": "string"}
                    }
                }
            }
        }

    def get_workflow(self, name: str) -> Optional[Dict[str, Any]]:
        """Get workflow definition by name."""
        return self._workflow_definitions.get(name)

    def list_workflows(self) -> List[Dict[str, Any]]:
        """List all available workflows."""
        return list(self._workflow_definitions.values())

    # =========================================================
    # Local Fallback Implementations
    # =========================================================

    async def perceive_signals(
        self,
        service: Optional[str] = None,
        time_window: int = 300
    ) -> Dict[str, Any]:
        """
        Local fallback: Collect signals from the environment.

        This is the local implementation used when DeerFlow is unavailable.
        """
        logger.info(f"[WORKFLOW] perceive_signals: service={service}, time_window={time_window}s")

        try:
            # Use absolute import for package
            try:
                from src.tools.performance_tools import get_performance_analyzer
            except ImportError:
                from tools.performance_tools import get_performance_analyzer

            analyzer = get_performance_analyzer()

            # Detect anomalies
            signals = await analyzer.detect_anomalies(service, time_window)

            return {
                "signals": [
                    {
                        "id": s.id if hasattr(s, "id") else str(uuid.uuid4()),
                        "source": s.source if hasattr(s, "source") else "metrics",
                        "type": s.type if hasattr(s, "type") else "anomaly",
                        "severity": s.severity if hasattr(s, "severity") else "medium",
                        "timestamp": s.timestamp.isoformat() if hasattr(s, "timestamp") else datetime.now().isoformat(),
                        "data": s.data if hasattr(s, "data") else s,
                    }
                    for s in signals
                ],
                "summary": {
                    "total_signals": len(signals),
                    "by_severity": self._count_by_severity(signals),
                }
            }

        except Exception as e:
            logger.error(f"[WORKFLOW] perceive_signals failed: {e}")
            return {"signals": [], "summary": {"error": str(e)}}

    async def diagnose_signals(self, signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Local fallback: Diagnose root cause from signals.

        This is the local implementation used when DeerFlow is unavailable.
        """
        logger.info(f"[WORKFLOW] diagnose_signals: analyzing {len(signals)} signals")

        try:
            # Use absolute import for package
            try:
                from src.tools.performance_tools import get_performance_analyzer
                from src.agents.optimizer_agent import Signal
            except ImportError:
                from tools.performance_tools import get_performance_analyzer
                from agents.optimizer_agent import Signal

            analyzer = get_performance_analyzer()

            # Convert to Signal objects
            signal_objects = []
            for s in signals:
                signal_objects.append(Signal(
                    id=s.get("id", str(uuid.uuid4())),
                    source=s.get("source", "metrics"),
                    type=s.get("type", "anomaly"),
                    severity=s.get("severity", "medium"),
                    timestamp=datetime.fromisoformat(s.get("timestamp", datetime.now().isoformat())),
                    data=s.get("data", {}),
                ))

            result = await analyzer.analyze_root_cause(signal_objects)

            return {
                "id": str(uuid.uuid4()),
                "root_cause": result.get("root_cause", "Unknown"),
                "confidence": result.get("confidence", 0.5),
                "evidence": result.get("evidence", []),
                "affected_services": result.get("affected_services", []),
                "impact_assessment": result.get("impact_assessment", {}),
                "report": result.get("report", "Analysis completed."),
                "recommended_actions": result.get("recommended_actions", []),
            }

        except Exception as e:
            logger.error(f"[WORKFLOW] diagnose_signals failed: {e}")
            return {
                "id": str(uuid.uuid4()),
                "root_cause": "Unknown (diagnosis failed)",
                "confidence": 0.0,
                "evidence": [],
                "report": f"Diagnosis failed: {str(e)}",
                "recommended_actions": [],
            }

    async def execute_remediation(
        self,
        action: Dict[str, Any],
        diagnosis_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Local fallback: Execute remediation action.

        This is the local implementation used when DeerFlow is unavailable.
        """
        action_name = action.get("name", "unknown")
        logger.info(f"[WORKFLOW] execute_remediation: action={action_name}")

        # In local fallback mode, we simulate execution
        # In production, this would connect to the real remediation engine

        return {
            "success": True,
            "action": action_name,
            "validation": {"passed": True, "metrics_improved": True},
            "rollback_performed": False,
            "local_mode": True,
            "message": f"Simulated execution of {action_name}",
        }

    async def generate_optimization(
        self,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Local fallback: Generate optimization recommendations.

        This is the local implementation used when DeerFlow is unavailable.
        """
        logger.info(f"[WORKFLOW] generate_optimization: context={context}")

        try:
            # Use absolute import for package
            try:
                from src.tools.performance_tools import get_performance_analyzer
            except ImportError:
                from tools.performance_tools import get_performance_analyzer

            analyzer = get_performance_analyzer()
            service = context.get("service", "unknown") if context else "unknown"
            metrics = context or {}

            recommendations = await analyzer.get_optimization_recommendations(service, metrics)

            return {
                "success": True,
                "optimization_name": f"opt_{service}_{uuid.uuid4().hex[:8]}",
                "recommendations": recommendations,
                "local_mode": True,
            }

        except Exception as e:
            logger.error(f"[WORKFLOW] generate_optimization failed: {e}")
            return {
                "success": False,
                "optimization_name": "error",
                "error": str(e),
            }

    def _count_by_severity(self, signals: List) -> Dict[str, int]:
        """Count signals by severity level."""
        counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        for s in signals:
            severity = s.severity if hasattr(s, "severity") else s.get("severity", "medium")
            if severity in counts:
                counts[severity] += 1
        return counts


# Global instance
_optimizer_workflows: Optional[OptimizerWorkflows] = None


def get_optimizer_workflows() -> OptimizerWorkflows:
    """Get or create the global OptimizerWorkflows instance."""
    global _optimizer_workflows
    if _optimizer_workflows is None:
        _optimizer_workflows = OptimizerWorkflows()
    return _optimizer_workflows


def register_optimizer_workflows(agent=None):
    """
    Register optimizer workflows with an agent.

    Args:
        agent: OptimizerAgent instance to register workflows with
    """
    workflows = get_optimizer_workflows()

    if agent:
        # Register local fallback workflows
        agent.register_workflow("perceive_signals", workflows.perceive_signals)
        agent.register_workflow("diagnose_signals", workflows.diagnose_signals)
        agent.register_workflow("execute_remediation", workflows.execute_remediation)
        agent.register_workflow("generate_optimization", workflows.generate_optimization)

    logger.info("Optimizer workflows registered")
    return workflows
