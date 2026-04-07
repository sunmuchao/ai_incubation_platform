"""
外部系统集成适配器
包含CI、安全扫描等第三方系统的集成接口
"""

from .ci_integration import (
    CISystem,
    CIStatus,
    CICheckResult,
    CIIntegrationConfig,
    CIIntegration,
    ci_integration
)

from .security_scanner import (
    SeverityLevel,
    SecurityIssue,
    SecurityScanResult,
    SecurityScannerConfig,
    SecurityScanner,
    security_scanner
)

__all__ = [
    # CI集成
    "CISystem",
    "CIStatus",
    "CICheckResult",
    "CIIntegrationConfig",
    "CIIntegration",
    "ci_integration",

    # 安全扫描
    "SeverityLevel",
    "SecurityIssue",
    "SecurityScanResult",
    "SecurityScannerConfig",
    "SecurityScanner",
    "security_scanner"
]
