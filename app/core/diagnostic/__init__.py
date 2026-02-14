"""Self-Diagnostic & Auto-Repair sistemi."""

from app.core.diagnostic.auto_fixer import AutoFixer
from app.core.diagnostic.bottleneck_detector import BottleneckDetector
from app.core.diagnostic.dependency_checker import DependencyChecker
from app.core.diagnostic.diagnostic_orchestrator import DiagnosticOrchestrator
from app.core.diagnostic.diagnostic_reporter import DiagnosticReporter
from app.core.diagnostic.error_analyzer import ErrorAnalyzer
from app.core.diagnostic.health_scanner import HealthScanner
from app.core.diagnostic.preventive_care import PreventiveCare
from app.core.diagnostic.recovery_manager import RecoveryManager

__all__ = [
    "AutoFixer",
    "BottleneckDetector",
    "DependencyChecker",
    "DiagnosticOrchestrator",
    "DiagnosticReporter",
    "ErrorAnalyzer",
    "HealthScanner",
    "PreventiveCare",
    "RecoveryManager",
]
