"""ATLAS Self-Evolution sistemi.

Kendi kendini gelistiren otonom AI: performans izleme,
zayiflik tespiti, iyilestirme planlama, kod evrimi,
guvenlik koruma, deney yonetimi, onay ve ogrenme.
"""

from app.core.evolution.approval_manager import ApprovalManager
from app.core.evolution.code_evolver import CodeEvolver
from app.core.evolution.evolution_controller import EvolutionController
from app.core.evolution.experiment_runner import ExperimentRunner
from app.core.evolution.improvement_planner import ImprovementPlanner
from app.core.evolution.knowledge_learner import KnowledgeLearner
from app.core.evolution.performance_monitor import PerformanceMonitor
from app.core.evolution.safety_guardian import SafetyGuardian
from app.core.evolution.weakness_detector import WeaknessDetector

__all__ = [
    "ApprovalManager",
    "CodeEvolver",
    "EvolutionController",
    "ExperimentRunner",
    "ImprovementPlanner",
    "KnowledgeLearner",
    "PerformanceMonitor",
    "SafetyGuardian",
    "WeaknessDetector",
]
