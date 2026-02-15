"""ATLAS Aciklanabilirlik Orkestrator modulu.

Tam aciklama pipeline, talep uzerine aciklamalar,
proaktif aciklamalar, entegrasyon, analitik.
"""

import logging
import time
from typing import Any

from app.core.explainability.audit_formatter import (
    AuditFormatter,
)
from app.core.explainability.counterfactual_generator import (
    CounterfactualGenerator,
)
from app.core.explainability.decision_recorder import (
    DecisionRecorder,
)
from app.core.explainability.explanation_cache import (
    ExplanationCache,
)
from app.core.explainability.factor_analyzer import (
    FactorAnalyzer,
)
from app.core.explainability.natural_language_explainer import (
    NaturalLanguageExplainer,
)
from app.core.explainability.reasoning_tracer import (
    ReasoningTracer,
)
from app.core.explainability.visual_explainer import (
    VisualExplainer,
)

logger = logging.getLogger(__name__)


class ExplainabilityOrchestrator:
    """Aciklanabilirlik orkestrator.

    Tum aciklanabilirlik bilesenleri koordine eder.

    Attributes:
        recorder: Karar kaydedici.
        tracer: Akil yurutme izleyici.
        factor_analyzer: Faktor analizcisi.
        nl_explainer: Dogal dil aciklayici.
        visual: Gorsel aciklayici.
        counterfactual: Karsi-olgusal uretici.
        formatter: Denetim bicimleyici.
        cache: Aciklama onbellegi.
    """

    def __init__(
        self,
        default_language: str = "en",
        cache_enabled: bool = True,
        include_counterfactuals: bool = True,
    ) -> None:
        """Orkestratoru baslatir.

        Args:
            default_language: Varsayilan dil.
            cache_enabled: Onbellek aktif mi.
            include_counterfactuals: Karsi-olgusal dahil mi.
        """
        self.recorder = DecisionRecorder()
        self.tracer = ReasoningTracer()
        self.factor_analyzer = FactorAnalyzer()
        self.nl_explainer = (
            NaturalLanguageExplainer(
                default_language=default_language,
            )
        )
        self.visual = VisualExplainer()
        self.counterfactual = (
            CounterfactualGenerator()
        )
        self.formatter = AuditFormatter()
        self.cache = ExplanationCache()

        self._cache_enabled = cache_enabled
        self._include_counterfactuals = (
            include_counterfactuals
        )
        self._stats = {
            "explanations_generated": 0,
        }

        logger.info(
            "ExplainabilityOrchestrator "
            "baslatildi",
        )

    def explain_decision(
        self,
        decision_id: str,
        decision_data: dict[str, Any],
        depth: str = "standard",
        audience: str = "technical",
        language: str | None = None,
    ) -> dict[str, Any]:
        """Tam aciklama pipeline calistirir.

        Args:
            decision_id: Karar ID.
            decision_data: Karar verisi.
            depth: Aciklama derinligi.
            audience: Hedef kitle.
            language: Dil.

        Returns:
            Aciklama bilgisi.
        """
        # Onbellekten kontrol
        cache_key = (
            f"explain_{decision_id}"
            f"_{depth}_{audience}"
        )
        if self._cache_enabled:
            cached = self.cache.get(cache_key)
            if cached:
                return cached

        # Karar kaydet
        self.recorder.record_decision(
            decision_id,
            decision_type=decision_data.get(
                "decision_type", "",
            ),
            description=decision_data.get(
                "description", "",
            ),
            system=decision_data.get(
                "system", "",
            ),
        )

        # Girdi kaydet
        inputs = decision_data.get(
            "inputs", {},
        )
        if inputs:
            self.recorder.log_inputs(
                decision_id, inputs,
            )

        # Faktor analizi
        factors = decision_data.get(
            "factors", [],
        )
        factor_analysis = {}
        if factors:
            self.recorder.log_factors(
                decision_id, factors,
            )
            factor_analysis = (
                self.factor_analyzer
                .analyze_factors(
                    decision_id, factors,
                )
            )

        # Dogal dil aciklama
        nl_explanation = (
            self.nl_explainer.generate_summary(
                decision_id,
                decision_data,
                language=language,
                audience=audience,
            )
        )

        # Sonucu kaydet
        outcome = decision_data.get(
            "outcome", {},
        )
        if outcome:
            self.recorder.record_outcome(
                decision_id,
                outcome.get("result", ""),
                outcome.get("confidence", 0),
                outcome.get("rationale", ""),
            )

        result = {
            "decision_id": decision_id,
            "explanation": nl_explanation.get(
                "text", "",
            ),
            "factors": factor_analysis,
            "depth": depth,
            "audience": audience,
            "generated_at": time.time(),
        }

        # Karsi-olgusal (detayli mod)
        if (
            self._include_counterfactuals
            and depth in (
                "detailed", "full",
            )
            and factors
        ):
            cf = (
                self.counterfactual
                .find_minimal_change(
                    decision_id, factors,
                )
            )
            result["counterfactual"] = cf

        # Onbellege yaz
        if self._cache_enabled:
            self.cache.set(
                cache_key, result,
            )

        self._stats[
            "explanations_generated"
        ] += 1

        return result

    def get_reasoning_trace(
        self,
        decision_id: str,
    ) -> dict[str, Any]:
        """Akil yurutme izini getirir.

        Args:
            decision_id: Karar ID.

        Returns:
            Iz bilgisi.
        """
        return self.tracer.get_trace(
            decision_id,
        )

    def get_audit_report(
        self,
        decision_id: str,
        format_type: str = "compliance",
    ) -> dict[str, Any]:
        """Denetim raporu uretir.

        Args:
            decision_id: Karar ID.
            format_type: Format tipi.

        Returns:
            Rapor.
        """
        decision_data = (
            self.recorder.get_decision(
                decision_id,
            )
        )

        if "error" in decision_data:
            return decision_data

        if format_type == "compliance":
            return (
                self.formatter
                .format_compliance(
                    decision_id,
                    decision_data,
                )
            )
        elif format_type == "legal":
            return self.formatter.format_legal(
                decision_id,
                decision_data,
            )
        elif format_type == "executive":
            return (
                self.formatter
                .format_executive(
                    decision_id,
                    decision_data,
                )
            )
        else:
            return (
                self.formatter
                .format_technical(
                    decision_id,
                    decision_data,
                )
            )

    def get_status(self) -> dict[str, Any]:
        """Genel durum bilgisi.

        Returns:
            Durum bilgisi.
        """
        return {
            "decisions_recorded": (
                self.recorder.decision_count
            ),
            "traces": (
                self.tracer.trace_count
            ),
            "analyses": (
                self.factor_analyzer
                .analysis_count
            ),
            "explanations": (
                self.nl_explainer
                .explanation_count
            ),
            "visuals": (
                self.visual.visual_count
            ),
            "counterfactuals": (
                self.counterfactual
                .generated_count
            ),
            "formatted": (
                self.formatter.format_count
            ),
            "cache_size": self.cache.size,
            "cache_hit_rate": (
                self.cache.hit_rate
            ),
        }

    def get_analytics(self) -> dict[str, Any]:
        """Analitik raporu.

        Returns:
            Rapor.
        """
        cache_stats = self.cache.get_stats()

        return {
            "total_explanations": (
                self._stats[
                    "explanations_generated"
                ]
            ),
            "decisions_recorded": (
                self.recorder.decision_count
            ),
            "reasoning_traces": (
                self.tracer.trace_count
            ),
            "total_steps": (
                self.tracer.total_steps
            ),
            "factor_analyses": (
                self.factor_analyzer
                .analysis_count
            ),
            "cache_stats": cache_stats,
        }

    @property
    def explanations_generated(self) -> int:
        """Uretilen aciklama sayisi."""
        return self._stats[
            "explanations_generated"
        ]
