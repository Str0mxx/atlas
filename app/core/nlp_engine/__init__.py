"""ATLAS Natural Language Programming alt sistemi.

Dogal dil ile kod ve sistem olusturma: niyet analizi,
gorev ayristirma, gereksinim cikarma, spesifikasyon uretimi,
kod planlama, calistirma cevirisi, geri bildirim ve diyalog.
"""

from app.core.nlp_engine.code_planner import CodePlanner
from app.core.nlp_engine.conversation_manager import ConversationManager
from app.core.nlp_engine.execution_translator import ExecutionTranslator
from app.core.nlp_engine.feedback_interpreter import FeedbackInterpreter
from app.core.nlp_engine.intent_parser import IntentParser
from app.core.nlp_engine.nlp_orchestrator import NLPOrchestrator
from app.core.nlp_engine.requirement_extractor import RequirementExtractor
from app.core.nlp_engine.spec_generator import SpecGenerator
from app.core.nlp_engine.task_decomposer import TaskDecomposer

__all__ = [
    "CodePlanner",
    "ConversationManager",
    "ExecutionTranslator",
    "FeedbackInterpreter",
    "IntentParser",
    "NLPOrchestrator",
    "RequirementExtractor",
    "SpecGenerator",
    "TaskDecomposer",
]
