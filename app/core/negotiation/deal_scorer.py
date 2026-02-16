"""ATLAS Anlaşma Puanlayıcı modülü.

Anlaşma değerlendirme, risk puanlama,
değer değerlendirme, alternatif karşılaştırma,
kabul/red önerisi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class DealScorer:
    """Anlaşma puanlayıcı.

    Anlaşmaları puanlar ve değerlendirir.

    Attributes:
        _scores: Puan kayıtları.
        _criteria: Değerlendirme kriterleri.
    """

    DEFAULT_WEIGHTS = {
        "value": 0.30,
        "risk": 0.25,
        "terms": 0.20,
        "relationship": 0.15,
        "strategic": 0.10,
    }

    def __init__(
        self,
        min_acceptable: float = 60.0,
    ) -> None:
        """Puanlayıcıyı başlatır.

        Args:
            min_acceptable: Minimum kabul puanı.
        """
        self._scores: list[
            dict[str, Any]
        ] = []
        self._criteria: dict[
            str, float
        ] = dict(self.DEFAULT_WEIGHTS)
        self._min_acceptable = (
            min_acceptable
        )
        self._counter = 0
        self._stats = {
            "deals_scored": 0,
            "comparisons_made": 0,
            "recommendations": 0,
        }

        logger.info(
            "DealScorer baslatildi",
        )

    def evaluate_deal(
        self,
        deal_value: float,
        target_value: float,
        risk_factors: (
            list[str] | None
        ) = None,
        terms_quality: float = 70.0,
        relationship_value: float = 70.0,
        strategic_fit: float = 70.0,
    ) -> dict[str, Any]:
        """Anlaşma değerlendirir.

        Args:
            deal_value: Anlaşma değeri.
            target_value: Hedef değer.
            risk_factors: Risk faktörleri.
            terms_quality: Koşul kalitesi.
            relationship_value: İlişki değeri.
            strategic_fit: Stratejik uyum.

        Returns:
            Değerlendirme bilgisi.
        """
        self._counter += 1
        sid = f"score_{self._counter}"

        risk_factors = risk_factors or []

        # Değer puanı
        value_ratio = (
            deal_value
            / max(target_value, 0.01)
        )
        value_score = min(
            value_ratio * 100, 100,
        )

        # Risk puanı (ters)
        base_risk = 80.0
        risk_penalty = len(
            risk_factors,
        ) * 15
        risk_score = max(
            base_risk - risk_penalty, 0,
        )

        # Ağırlıklı puan
        w = self._criteria
        overall = round(
            value_score * w["value"]
            + risk_score * w["risk"]
            + terms_quality * w["terms"]
            + relationship_value
            * w["relationship"]
            + strategic_fit
            * w["strategic"],
            1,
        )

        record = {
            "score_id": sid,
            "overall": overall,
            "value_score": round(
                value_score, 1,
            ),
            "risk_score": round(
                risk_score, 1,
            ),
            "terms_score": terms_quality,
            "relationship_score": (
                relationship_value
            ),
            "strategic_score": strategic_fit,
            "risk_factors": risk_factors,
            "timestamp": time.time(),
        }
        self._scores.append(record)
        self._stats["deals_scored"] += 1

        return record

    def score_risk(
        self,
        factors: list[str],
        severity: dict[str, float]
        | None = None,
    ) -> dict[str, Any]:
        """Risk puanlar.

        Args:
            factors: Risk faktörleri.
            severity: Ciddiyet seviyeleri.

        Returns:
            Risk bilgisi.
        """
        severity = severity or {}

        total_risk = 0.0
        details = []
        for f in factors:
            s = severity.get(f, 0.5)
            risk_contrib = s * 20
            total_risk += risk_contrib
            details.append({
                "factor": f,
                "severity": s,
                "contribution": round(
                    risk_contrib, 1,
                ),
            })

        total_risk = min(total_risk, 100)
        level = (
            "low" if total_risk < 30
            else "medium"
            if total_risk < 60
            else "high"
        )

        return {
            "total_risk": round(
                total_risk, 1,
            ),
            "level": level,
            "factors": details,
            "count": len(factors),
        }

    def assess_value(
        self,
        deal_value: float,
        market_value: float,
        cost: float = 0.0,
    ) -> dict[str, Any]:
        """Değer değerlendirir.

        Args:
            deal_value: Anlaşma değeri.
            market_value: Piyasa değeri.
            cost: Maliyet.

        Returns:
            Değer bilgisi.
        """
        vs_market = round(
            (deal_value - market_value)
            / max(market_value, 0.01)
            * 100, 1,
        )

        margin = 0.0
        if cost > 0:
            margin = round(
                (deal_value - cost)
                / deal_value * 100, 1,
            )

        rating = (
            "excellent" if vs_market >= 10
            else "good" if vs_market >= 0
            else "fair" if vs_market >= -10
            else "poor"
        )

        return {
            "deal_value": deal_value,
            "market_value": market_value,
            "vs_market_percent": vs_market,
            "margin": margin,
            "rating": rating,
        }

    def compare_alternatives(
        self,
        current_deal: dict[str, Any],
        alternatives: list[
            dict[str, Any]
        ],
    ) -> dict[str, Any]:
        """Alternatiflerle karşılaştırır.

        Args:
            current_deal: Mevcut anlaşma.
            alternatives: Alternatifler.

        Returns:
            Karşılaştırma bilgisi.
        """
        current_score = current_deal.get(
            "score", 0,
        )
        current_value = current_deal.get(
            "value", 0,
        )

        rankings = []
        for alt in alternatives:
            alt_score = alt.get("score", 0)
            alt_value = alt.get("value", 0)
            rankings.append({
                "name": alt.get(
                    "name", "unknown",
                ),
                "score": alt_score,
                "value": alt_value,
                "vs_current": round(
                    alt_score
                    - current_score, 1,
                ),
            })

        rankings.sort(
            key=lambda x: x["score"],
            reverse=True,
        )

        best_alt = (
            rankings[0] if rankings else None
        )
        current_is_best = (
            not best_alt
            or current_score
            >= best_alt["score"]
        )

        self._stats[
            "comparisons_made"
        ] += 1

        return {
            "current_score": current_score,
            "current_value": current_value,
            "rankings": rankings,
            "current_is_best": current_is_best,
            "best_alternative": (
                best_alt["name"]
                if best_alt
                else "none"
            ),
        }

    def recommend(
        self,
        overall_score: float,
        risk_level: str = "medium",
        batna_value: float = 0.0,
        deal_value: float = 0.0,
    ) -> dict[str, Any]:
        """Kabul/red önerisi yapar.

        Args:
            overall_score: Genel puan.
            risk_level: Risk seviyesi.
            batna_value: BATNA değeri.
            deal_value: Anlaşma değeri.

        Returns:
            Öneri bilgisi.
        """
        reasons = []

        # Puan bazlı
        if overall_score >= 80:
            base_action = "strong_accept"
            reasons.append("high_score")
        elif (
            overall_score
            >= self._min_acceptable
        ):
            base_action = "accept"
            reasons.append(
                "meets_minimum_score",
            )
        elif overall_score >= 50:
            base_action = "negotiate_more"
            reasons.append(
                "below_minimum_score",
            )
        else:
            base_action = "reject"
            reasons.append("low_score")

        # BATNA karşılaştırması
        if (
            batna_value > 0
            and deal_value > 0
        ):
            if deal_value < batna_value:
                base_action = "reject"
                reasons.append(
                    "below_batna",
                )
            elif (
                deal_value
                > batna_value * 1.2
            ):
                reasons.append(
                    "significantly_above_batna",
                )

        # Risk ayarı
        if risk_level == "high":
            if base_action == "accept":
                base_action = (
                    "accept_with_caution"
                )
            reasons.append("high_risk")

        confidence = min(
            overall_score, 95,
        )

        self._stats[
            "recommendations"
        ] += 1

        return {
            "recommendation": base_action,
            "reasons": reasons,
            "overall_score": overall_score,
            "confidence": round(
                confidence, 1,
            ),
        }

    def set_criteria_weight(
        self,
        criterion: str,
        weight: float,
    ) -> dict[str, Any]:
        """Kriter ağırlığı ayarlar."""
        if criterion in self._criteria:
            old = self._criteria[criterion]
            self._criteria[criterion] = (
                weight
            )
            return {
                "criterion": criterion,
                "old_weight": old,
                "new_weight": weight,
                "set": True,
            }
        return {
            "criterion": criterion,
            "set": False,
            "reason": "unknown_criterion",
        }

    @property
    def score_count(self) -> int:
        """Puan sayısı."""
        return self._stats[
            "deals_scored"
        ]

    @property
    def recommendation_count(self) -> int:
        """Öneri sayısı."""
        return self._stats[
            "recommendations"
        ]
