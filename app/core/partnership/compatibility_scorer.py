"""ATLAS Ortak Uyumluluk Puanlayıcı.

Uyumluluk puanlama, sinerji analizi,
risk değerlendirmesi ve stratejik uyum.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class PartnerCompatibilityScorer:
    """Ortak uyumluluk puanlayıcısı.

    Potansiyel ortakların uyumluluğunu
    çok boyutlu olarak puanlar.

    Attributes:
        _scores: Puan kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Puanlayıcıyı başlatır."""
        self._scores: dict[str, dict] = {}
        self._stats = {
            "scores_calculated": 0,
            "assessments_done": 0,
        }
        logger.info(
            "PartnerCompatibilityScorer "
            "baslatildi",
        )

    @property
    def score_count(self) -> int:
        """Hesaplanan puan sayısı."""
        return self._stats[
            "scores_calculated"
        ]

    @property
    def assessment_count(self) -> int:
        """Yapılan değerlendirme sayısı."""
        return self._stats[
            "assessments_done"
        ]

    def calculate_compatibility(
        self,
        partner_id: str,
        industry_match: float = 0.0,
        size_match: float = 0.0,
        capability_match: float = 0.0,
        cultural_fit: float = 0.0,
    ) -> dict[str, Any]:
        """Uyumluluk puanı hesaplar.

        Args:
            partner_id: Ortak kimliği.
            industry_match: Sektör uyumu (0-1).
            size_match: Boyut uyumu (0-1).
            capability_match: Yetenek uyumu.
            cultural_fit: Kültürel uyum.

        Returns:
            Uyumluluk bilgisi.
        """
        score = (
            industry_match * 0.3
            + size_match * 0.2
            + capability_match * 0.3
            + cultural_fit * 0.2
        )

        level = "low"
        if score >= 0.8:
            level = "excellent"
        elif score >= 0.6:
            level = "good"
        elif score >= 0.4:
            level = "moderate"

        self._scores[partner_id] = {
            "score": round(score, 2),
            "level": level,
        }
        self._stats[
            "scores_calculated"
        ] += 1

        logger.info(
            "Uyumluluk puani: %s -> %.2f (%s)",
            partner_id,
            score,
            level,
        )

        return {
            "partner_id": partner_id,
            "score": round(score, 2),
            "level": level,
            "calculated": True,
        }

    def analyze_synergy(
        self,
        partner_id: str,
        strengths_a: list[str] | None = None,
        strengths_b: list[str] | None = None,
    ) -> dict[str, Any]:
        """Sinerji analizi yapar.

        Args:
            partner_id: Ortak kimliği.
            strengths_a: A tarafı güçlü yanlar.
            strengths_b: B tarafı güçlü yanlar.

        Returns:
            Sinerji bilgisi.
        """
        if strengths_a is None:
            strengths_a = []
        if strengths_b is None:
            strengths_b = []

        set_a = set(strengths_a)
        set_b = set(strengths_b)
        complementary = set_a - set_b
        overlapping = set_a & set_b
        synergy = (
            len(complementary)
            / (len(set_a | set_b) or 1)
        )

        return {
            "partner_id": partner_id,
            "complementary": list(
                complementary,
            ),
            "overlapping": list(overlapping),
            "synergy_score": round(
                synergy, 2,
            ),
            "analyzed": True,
        }

    def assess_risk(
        self,
        partner_id: str,
        financial_risk: float = 0.0,
        reputation_risk: float = 0.0,
        dependency_risk: float = 0.0,
    ) -> dict[str, Any]:
        """Risk değerlendirmesi yapar.

        Args:
            partner_id: Ortak kimliği.
            financial_risk: Finansal risk (0-1).
            reputation_risk: İtibar riski.
            dependency_risk: Bağımlılık riski.

        Returns:
            Risk bilgisi.
        """
        overall = (
            financial_risk * 0.4
            + reputation_risk * 0.3
            + dependency_risk * 0.3
        )

        level = "low"
        if overall >= 0.7:
            level = "high"
        elif overall >= 0.4:
            level = "medium"

        self._stats[
            "assessments_done"
        ] += 1

        return {
            "partner_id": partner_id,
            "overall_risk": round(
                overall, 2,
            ),
            "risk_level": level,
            "assessed": True,
        }

    def evaluate_cultural_fit(
        self,
        partner_id: str,
        values_alignment: float = 0.0,
        work_style: float = 0.0,
        communication: float = 0.0,
    ) -> dict[str, Any]:
        """Kültürel uyum değerlendirir.

        Args:
            partner_id: Ortak kimliği.
            values_alignment: Değer uyumu.
            work_style: Çalışma tarzı uyumu.
            communication: İletişim uyumu.

        Returns:
            Kültürel uyum bilgisi.
        """
        fit = (
            values_alignment * 0.4
            + work_style * 0.3
            + communication * 0.3
        )

        return {
            "partner_id": partner_id,
            "cultural_fit": round(fit, 2),
            "evaluated": True,
        }

    def check_strategic_alignment(
        self,
        partner_id: str,
        goals_overlap: float = 0.0,
        market_overlap: float = 0.0,
        timeline_match: float = 0.0,
    ) -> dict[str, Any]:
        """Stratejik uyum kontrolü yapar.

        Args:
            partner_id: Ortak kimliği.
            goals_overlap: Hedef örtüşmesi.
            market_overlap: Pazar örtüşmesi.
            timeline_match: Zaman uyumu.

        Returns:
            Stratejik uyum bilgisi.
        """
        alignment = (
            goals_overlap * 0.4
            + market_overlap * 0.3
            + timeline_match * 0.3
        )
        aligned = alignment >= 0.5

        return {
            "partner_id": partner_id,
            "alignment": round(
                alignment, 2,
            ),
            "aligned": aligned,
            "checked": True,
        }
