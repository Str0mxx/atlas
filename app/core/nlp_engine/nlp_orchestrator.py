"""ATLAS NLP Orkestrator modulu.

Tum NLP alt sistemlerini orkestre eder:
Input -> Parse -> Plan -> Execute -> Report.
Hata kurtarma, etkilesimlerden ogrenme ve stil adaptasyonu.
"""

import logging
import time
from typing import Any

from app.core.nlp_engine.code_planner import CodePlanner
from app.core.nlp_engine.conversation_manager import ConversationManager
from app.core.nlp_engine.execution_translator import ExecutionTranslator
from app.core.nlp_engine.feedback_interpreter import FeedbackInterpreter
from app.core.nlp_engine.intent_parser import IntentParser
from app.core.nlp_engine.requirement_extractor import RequirementExtractor
from app.core.nlp_engine.spec_generator import SpecGenerator
from app.core.nlp_engine.task_decomposer import TaskDecomposer
from app.models.nlp_engine import (
    ConversationState,
    FeedbackType,
    IntentCategory,
    NLPPipelineResult,
    VerbosityLevel,
)

logger = logging.getLogger(__name__)

# Niyet kategorisine gore pipeline adimlari
_PIPELINE_STEPS: dict[IntentCategory, list[str]] = {
    IntentCategory.CREATE: ["parse", "decompose", "requirements", "spec", "plan", "translate", "feedback"],
    IntentCategory.MODIFY: ["parse", "decompose", "translate", "feedback"],
    IntentCategory.DELETE: ["parse", "translate", "feedback"],
    IntentCategory.QUERY: ["parse", "translate", "feedback"],
    IntentCategory.EXECUTE: ["parse", "translate", "feedback"],
    IntentCategory.CONFIGURE: ["parse", "translate", "feedback"],
    IntentCategory.ANALYZE: ["parse", "decompose", "requirements", "feedback"],
    IntentCategory.EXPLAIN: ["parse", "feedback"],
    IntentCategory.DEBUG: ["parse", "decompose", "translate", "feedback"],
    IntentCategory.UNKNOWN: ["parse", "feedback"],
}


class NLPOrchestrator:
    """NLP orkestrator.

    Tum NLP alt sistemlerini koordine ederek dogal dil
    girislerini isler. Niyet analizi, gorev ayristirma,
    gereksinim cikarma, spesifikasyon uretimi, kod planlama,
    komut cevirisi ve geri bildirim dongusu orkestre eder.

    Attributes:
        parser: Niyet analiz sistemi.
        decomposer: Gorev ayristirma sistemi.
        extractor: Gereksinim cikarma sistemi.
        spec_gen: Spesifikasyon uretici.
        planner: Kod planlayici.
        translator: Calistirma cevirici.
        feedback: Geri bildirim yorumlayici.
        conversation: Diyalog yoneticisi.
        _results: Pipeline sonuclari.
        _interaction_count: Etkilesim sayisi.
        _error_count: Hata sayisi.
    """

    def __init__(
        self,
        clarification_threshold: float = 0.4,
        max_context_turns: int = 50,
        execution_confirmation: bool = True,
        verbosity_level: str = "normal",
    ) -> None:
        """NLP orkestratoru baslatir.

        Args:
            clarification_threshold: Belirsizlik esigi.
            max_context_turns: Maksimum baglam turu.
            execution_confirmation: Komut onay gerekliligi.
            verbosity_level: Ayrinti seviyesi.
        """
        try:
            verbosity = VerbosityLevel(verbosity_level)
        except ValueError:
            verbosity = VerbosityLevel.NORMAL

        self.parser = IntentParser(clarification_threshold=clarification_threshold)
        self.decomposer = TaskDecomposer()
        self.extractor = RequirementExtractor()
        self.spec_gen = SpecGenerator()
        self.planner = CodePlanner()
        self.translator = ExecutionTranslator(execution_confirmation=execution_confirmation)
        self.feedback = FeedbackInterpreter(verbosity=verbosity)
        self.conversation = ConversationManager(max_turns=max_context_turns)

        self._results: list[NLPPipelineResult] = []
        self._interaction_count: int = 0
        self._error_count: int = 0

        logger.info(
            "NLPOrchestrator baslatildi (clarify=%.2f, turns=%d, confirm=%s, verbose=%s)",
            clarification_threshold, max_context_turns, execution_confirmation, verbosity_level,
        )

    def process(self, text: str) -> NLPPipelineResult:
        """Dogal dil girisini tam pipeline ile isler.

        Input -> Parse -> Plan -> Execute -> Report

        Args:
            text: Dogal dil girisi.

        Returns:
            NLPPipelineResult nesnesi.
        """
        start_time = time.monotonic()
        self._interaction_count += 1
        self.conversation.set_state(ConversationState.PROCESSING)

        result = NLPPipelineResult(input_text=text)

        try:
            # 1. Parse
            self.conversation.add_user_turn(text)
            resolved_text = self.conversation.resolve_reference(text)
            intent = self.parser.parse(resolved_text)
            result.intent = intent

            # Belirsizlik varsa aciklama iste
            if not intent.resolved:
                clarification = self.feedback.request_clarification(
                    "Komutunuz belirsiz. Lutfen detaylandirir misiniz?",
                    context="; ".join(intent.ambiguities),
                )
                result.feedback = clarification
                self.conversation.set_state(ConversationState.CLARIFYING)
                result.processing_time_ms = (time.monotonic() - start_time) * 1000
                self._results.append(result)
                return result

            # Pipeline adimlarini belirle
            steps = _PIPELINE_STEPS.get(intent.category, _PIPELINE_STEPS[IntentCategory.UNKNOWN])

            # 2. Decompose
            if "decompose" in steps:
                decomposition = self.decomposer.decompose(text, intent)
                result.decomposition = decomposition

            # 3. Requirements
            if "requirements" in steps:
                requirements = self.extractor.extract(text)
                result.requirements = requirements

            # 4. Spec
            if "spec" in steps and result.requirements:
                spec = self.spec_gen.generate(
                    title=intent.action or text[:30],
                    requirements=result.requirements,
                    description=text,
                )
                result.spec = spec

            # 5. Plan
            if "plan" in steps and result.spec:
                code_plan = self.planner.plan(
                    title=intent.action or text[:30],
                    spec=result.spec,
                )
                result.code_plan = code_plan

            # 6. Translate
            if "translate" in steps:
                command = self.translator.translate(text, intent)
                result.commands = [command]

            # 7. Feedback
            if "feedback" in steps:
                if intent.category in (IntentCategory.EXPLAIN, IntentCategory.UNKNOWN):
                    fb = self.feedback.suggest(
                        f"'{text[:40]}' komutu analiz edildi",
                        reason=f"Kategori: {intent.category.value}",
                    )
                else:
                    fb = self.feedback.confirm_success(
                        action="executed",
                        entity=intent.action or "Komut",
                        detail=f"Kategori: {intent.category.value}",
                    )
                result.feedback = fb

            # Sistem yanitini ekle
            if result.feedback:
                self.conversation.add_system_turn(result.feedback.content)

            self.conversation.set_state(ConversationState.IDLE)

        except Exception as e:
            self._error_count += 1
            result.success = False
            result.error = str(e)
            result.feedback = self.feedback.explain_error(
                "generic", detail=str(e),
            )
            self.conversation.set_state(ConversationState.IDLE)
            logger.error("Pipeline hatasi: %s", e)

        result.processing_time_ms = (time.monotonic() - start_time) * 1000
        self._results.append(result)

        logger.info(
            "Pipeline tamamlandi: kategori=%s, basari=%s, sure=%.1fms",
            result.intent.category.value if result.intent else "?",
            result.success,
            result.processing_time_ms,
        )
        return result

    def recover_from_error(self, result_id: str, correction: str) -> NLPPipelineResult:
        """Hatadan kurtarma ile yeniden isler.

        Onceki hatal sonucu dikkate alarak duzeltilmis
        girisi isler.

        Args:
            result_id: Onceki sonuc ID.
            correction: Duzeltilmis giris.

        Returns:
            Yeni NLPPipelineResult nesnesi.
        """
        # Onceki sonucu bul
        prev = next((r for r in self._results if r.id == result_id), None)
        if prev:
            context = f"{prev.input_text} -> {prev.error}" if prev.error else prev.input_text
            self.parser.add_context("previous_error", context)

        logger.info("Hatadan kurtarma: %s -> %s", result_id[:8], correction[:30])
        return self.process(correction)

    def adapt_style(self, style: dict[str, str]) -> None:
        """Iletisim stilini adapte eder.

        Args:
            style: Stil ayarlari (tone, verbosity, language, vb).
        """
        if "verbosity" in style:
            try:
                level = VerbosityLevel(style["verbosity"])
                self.feedback.set_verbosity(level)
            except ValueError:
                pass

        logger.info("Stil adapte edildi: %s", style)

    def get_result(self, result_id: str) -> NLPPipelineResult | None:
        """Pipeline sonucu getirir.

        Args:
            result_id: Sonuc ID.

        Returns:
            NLPPipelineResult nesnesi veya None.
        """
        return next((r for r in self._results if r.id == result_id), None)

    @property
    def interaction_count(self) -> int:
        """Toplam etkilesim sayisi."""
        return self._interaction_count

    @property
    def error_count(self) -> int:
        """Toplam hata sayisi."""
        return self._error_count

    @property
    def success_rate(self) -> float:
        """Basari orani (0.0-1.0)."""
        if self._interaction_count == 0:
            return 1.0
        return (self._interaction_count - self._error_count) / self._interaction_count
