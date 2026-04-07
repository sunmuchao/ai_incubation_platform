"""
Signals and Diagnosis Models - Data models for Optimizer Agent

These models are shared between optimizer_agent, performance_tools,
and other modules to avoid circular imports.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class Signal:
    """A signal from the perception layer."""
    id: str
    source: str  # metrics, logs, tracing
    type: str  # anomaly, pattern, bottleneck
    severity: str  # low, medium, high, critical
    timestamp: datetime
    data: Dict[str, Any]
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Diagnosis:
    """Diagnosis result from the diagnosis agent."""
    id: str
    root_cause: str
    confidence: float
    evidence: List[Dict[str, Any]]
    affected_services: List[str]
    impact_assessment: Dict[str, Any]
    report: str
    recommended_actions: List[Dict[str, Any]]
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ExecutionResult:
    """Result of remediation or optimization execution."""
    success: bool
    action_type: str  # remediate, optimize
    action_name: str
    details: Dict[str, Any]
    validation_result: Optional[Dict[str, Any]] = None
    rollback_performed: bool = False
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
