"""
AI guvenlik orkestratoru modulu.

Tam AI guvenlik pipeline,
Uret -> Dogrula -> Isaretle -> Eskale,
Guvenilir AI, analitik.
"""

import logging
from typing import Any

from .confidence_calibrator import (
    AIConfidenceCalibrator,
)
from .consistency_analyzer import (
    ConsistencyAnalyzer,
)
from .fact_checker import FactChecker
from .hallucination_detector import (
    HallucinationDetector,
)
from .human_escalation_trigger import (
    HumanEscalationTrigger,
)
from .safety_boundary_enforcer import (
    SafetyBoundaryEnforcer,
)
from .source_verifier import (
    SourceVerifier,
)
from .uncertainty_flagger import (
    UncertaintyFlagger,
)

logger = logging.getLogger(__name__)


class AISafetyOrchestrator:
    """AI guvenlik orkestratoru.

    Attributes:
        _hallucination: Detektor.
        _fact_checker: Gercek kontrolcu.
        _source: Kaynak dogrulayici.
        _consistency: Tutarlilik.
        _calibrator: Kalibrator.
        _uncertainty: Belirsizlik.
        _escalation: Eskalasyon.
        _boundary: Sinir uygulayici.
    """

    def __init__(
        self,
        hallucination_check: bool = True,
        fact_checking: bool = True,
        auto_escalate: bool = True,
        safety_threshold: float = 0.5,
    ) -> None:
        """Orkestratoru baslatir.

        Args:
            hallucination_check: Kontrol.
            fact_checking: Gercek kontrol.
            auto_escalate: Otomatik.
            safety_threshold: Guvenlik.
        """
        self._hallucination_check = (
            hallucination_check
        )
        self._fact_checking = fact_checking
        self._auto_escalate = auto_escalate
        self._safety_threshold = (
            safety_threshold
        )

        self._hallucination = (
            HallucinationDetector(
                risk_threshold=(
                    safety_threshold
                )
            )
        )
        self._fact_checker = FactChecker()
        self._source = SourceVerifier()
        self._consistency = (
            ConsistencyAnalyzer()
        )
        self._calibrator = (
            AIConfidenceCalibrator()
        )
        self._uncertainty = (
            UncertaintyFlagger()
        )
        self._escalation = (
            HumanEscalationTrigger(
                auto_escalate=auto_escalate
            )
        )
        self._boundary = (
            SafetyBoundaryEnforcer()
        )

        logger.info(
            "AISafetyOrchestrator "
            "baslatildi"
        )

    def check_response(
        self,
        response_text: str = "",
        query: str = "",
        sources: list[str] | None = None,
        claims: list[str] | None = None,
        topic: str = "",
    ) -> dict[str, Any]:
        """Yaniti tam guvenlik kontrolu.

        Args:
            response_text: Yanit metni.
            query: Sorgu.
            sources: Kaynaklar.
            claims: Iddialar.
            topic: Konu.

        Returns:
            Tam kontrol bilgisi.
        """
        try:
            results: dict[str, Any] = {}

            # 1. Sinir kontrolu
            boundary_result = (
                self._boundary.check_content(
                    response_text
                )
            )
            results["boundary"] = (
                boundary_result
            )

            # Engellenmisse dur
            if (
                boundary_result.get(
                    "action"
                )
                == "block"
            ):
                return {
                    "safe": False,
                    "blocked": True,
                    "reason": (
                        "Guvenlik siniri "
                        "ihlali"
                    ),
                    "results": results,
                    "checked": True,
                }

            # 2. Halusinasyon kontrolu
            if self._hallucination_check:
                hal_result = (
                    self._hallucination.check_response(
                        response_text=(
                            response_text
                        ),
                        sources=sources,
                        claims=claims,
                    )
                )
                results["hallucination"] = (
                    hal_result
                )

            # 3. Gercek kontrolu
            if self._fact_checking:
                fact_result = (
                    self._fact_checker.check_text(
                        response_text,
                        sources=sources,
                    )
                )
                results["fact_check"] = (
                    fact_result
                )

            # 4. Tutarlilik kontrolu
            consistency_result = (
                self._consistency.check_internal_consistency(
                    response_text
                )
            )
            results["consistency"] = (
                consistency_result
            )

            # 5. Belirsizlik kontrolu
            uncertainty_result = (
                self._uncertainty.analyze_text(
                    response_text
                )
            )
            results["uncertainty"] = (
                uncertainty_result
            )

            # 6. Genel degerlendirme
            risk_score = (
                self._calculate_overall_risk(
                    results
                )
            )
            is_safe = (
                risk_score
                < self._safety_threshold
            )

            # 7. Eskalasyon kontrolu
            if (
                self._auto_escalate
                and not is_safe
            ):
                esc_check = (
                    self._escalation.check_escalation(
                        confidence=(
                            1.0 - risk_score
                        ),
                        risk_score=(
                            risk_score
                        ),
                        has_hallucination=(
                            results.get(
                                "hallucination",
                                {},
                            ).get(
                                "has_"
                                "hallucination",
                                False,
                            )
                        ),
                    )
                )
                results["escalation"] = (
                    esc_check
                )

                if esc_check.get(
                    "needs_escalation"
                ):
                    self._escalation.create_escalation(
                        reason=(
                            "auto_safety_check"
                        ),
                        priority=esc_check.get(
                            "priority",
                            "medium",
                        ),
                        description=(
                            "Otomatik guvenlik "
                            "kontrolu basarisiz"
                        ),
                    )

            return {
                "safe": is_safe,
                "blocked": False,
                "risk_score": round(
                    risk_score, 4
                ),
                "results": results,
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }

    def _calculate_overall_risk(
        self, results: dict
    ) -> float:
        """Genel risk hesaplar."""
        scores: list[float] = []

        # Halusinasyon riski
        hal = results.get(
            "hallucination", {}
        )
        if hal.get("checked"):
            scores.append(
                hal.get("risk_score", 0.0)
            )

        # Gercek kontrol riski
        fact = results.get(
            "fact_check", {}
        )
        if fact.get("checked"):
            overall = fact.get(
                "overall_score", 1.0
            )
            scores.append(1.0 - overall)

        # Tutarlilik riski
        con = results.get(
            "consistency", {}
        )
        if con.get("analyzed"):
            cscore = con.get(
                "consistency_score", 1.0
            )
            scores.append(1.0 - cscore)

        # Belirsizlik riski
        unc = results.get(
            "uncertainty", {}
        )
        if unc.get("analyzed"):
            scores.append(
                unc.get(
                    "uncertainty_score", 0.0
                )
                * 0.5
            )

        # Sinir ihlali
        bnd = results.get("boundary", {})
        if bnd.get("checked"):
            if not bnd.get(
                "is_safe", True
            ):
                scores.append(0.8)

        if not scores:
            return 0.0

        return sum(scores) / len(scores)

    def register_fact(
        self,
        statement: str = "",
        source: str = "",
        confidence: float = 1.0,
    ) -> dict[str, Any]:
        """Her iki sisteme gercek ekler.

        Args:
            statement: Ifade.
            source: Kaynak.
            confidence: Guven.

        Returns:
            Kayit bilgisi.
        """
        try:
            fc = (
                self._fact_checker.add_fact(
                    statement=statement,
                    source=source,
                    confidence=confidence,
                )
            )
            hd = (
                self._hallucination.register_fact(
                    statement=statement,
                    source=source,
                    confidence=confidence,
                )
            )
            return {
                "fact_checker": fc,
                "hallucination": hd,
                "registered": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "registered": False,
                "error": str(e),
            }

    def validate_output(
        self,
        output_text: str = "",
        query: str = "",
    ) -> dict[str, Any]:
        """Cikti dogrulamasi.

        Args:
            output_text: Cikti.
            query: Sorgu.

        Returns:
            Dogrulama bilgisi.
        """
        try:
            bnd_check = (
                self._boundary.validate_output(
                    output_text, query
                )
            )
            unc_check = (
                self._uncertainty.analyze_text(
                    output_text
                )
            )

            is_valid = bnd_check.get(
                "is_valid", True
            ) and unc_check.get(
                "level", "info"
            ) != "critical"

            return {
                "is_valid": is_valid,
                "boundary": bnd_check,
                "uncertainty": unc_check,
                "validated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "validated": False,
                "error": str(e),
            }

    def get_analytics(
        self,
    ) -> dict[str, Any]:
        """Analitik getirir."""
        try:
            return {
                "hallucination": (
                    self._hallucination.get_summary()
                ),
                "fact_checker": (
                    self._fact_checker.get_summary()
                ),
                "source_verifier": (
                    self._source.get_summary()
                ),
                "consistency": (
                    self._consistency.get_summary()
                ),
                "calibrator": (
                    self._calibrator.get_summary()
                ),
                "uncertainty": (
                    self._uncertainty.get_summary()
                ),
                "escalation": (
                    self._escalation.get_summary()
                ),
                "boundary": (
                    self._boundary.get_summary()
                ),
                "retrieved": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir."""
        try:
            return {
                "hallucination_check": (
                    self._hallucination_check
                ),
                "fact_checking": (
                    self._fact_checking
                ),
                "auto_escalate": (
                    self._auto_escalate
                ),
                "safety_threshold": (
                    self._safety_threshold
                ),
                "analytics": (
                    self.get_analytics()
                ),
                "retrieved": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
