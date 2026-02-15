"""ATLAS Bağlamsal Öncelik Puanlayıcı modülü.

Çok faktörlü puanlama, bağlam ağırlıklandırma,
aciliyet hesaplama, etki değerlendirme,
dinamik ayarlama.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ContextualPriorityScorer:
    """Bağlamsal öncelik puanlayıcı.

    Mesaj ve görevleri bağlama göre puanlar.

    Attributes:
        _weights: Faktör ağırlıkları.
        _scores: Puanlama geçmişi.
    """

    def __init__(
        self,
        urgency_weight: float = 0.3,
        impact_weight: float = 0.25,
        context_weight: float = 0.2,
        source_weight: float = 0.15,
        recency_weight: float = 0.1,
    ) -> None:
        """Puanlayıcıyı başlatır.

        Args:
            urgency_weight: Aciliyet ağırlığı.
            impact_weight: Etki ağırlığı.
            context_weight: Bağlam ağırlığı.
            source_weight: Kaynak ağırlığı.
            recency_weight: Yenilik ağırlığı.
        """
        self._weights = {
            "urgency": urgency_weight,
            "impact": impact_weight,
            "context": context_weight,
            "source": source_weight,
            "recency": recency_weight,
        }
        self._scores: list[
            dict[str, Any]
        ] = []
        self._source_priorities: dict[
            str, float
        ] = {
            "security": 1.0,
            "system": 0.8,
            "business": 0.6,
            "user": 0.5,
            "notification": 0.3,
        }
        self._adjustments: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "scores_calculated": 0,
            "adjustments_made": 0,
        }

        logger.info(
            "ContextualPriorityScorer "
            "baslatildi",
        )

    def score(
        self,
        message: str,
        source: str = "user",
        urgency: float = 0.5,
        impact: float = 0.5,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Öncelik puanı hesaplar.

        Args:
            message: Mesaj metni.
            source: Mesaj kaynağı.
            urgency: Aciliyet (0-1).
            impact: Etki (0-1).
            context: Bağlam bilgisi.

        Returns:
            Puanlama bilgisi.
        """
        self._counter += 1
        sid = f"score_{self._counter}"
        ctx = context or {}

        # Faktör puanları
        urgency_score = min(
            max(urgency, 0.0), 1.0,
        )
        impact_score = min(
            max(impact, 0.0), 1.0,
        )
        context_score = self._evaluate_context(
            ctx,
        )
        source_score = self._source_priorities.get(
            source, 0.4,
        )
        recency_score = 1.0  # Yeni mesaj

        # Ağırlıklı toplam
        total = (
            urgency_score
            * self._weights["urgency"]
            + impact_score
            * self._weights["impact"]
            + context_score
            * self._weights["context"]
            + source_score
            * self._weights["source"]
            + recency_score
            * self._weights["recency"]
        )
        total = round(
            min(max(total, 0.0), 1.0), 3,
        )

        # Seviye belirleme
        level = self._determine_level(total)

        score_record = {
            "score_id": sid,
            "message": message[:100],
            "source": source,
            "total_score": total,
            "level": level,
            "factors": {
                "urgency": round(
                    urgency_score, 3,
                ),
                "impact": round(
                    impact_score, 3,
                ),
                "context": round(
                    context_score, 3,
                ),
                "source": round(
                    source_score, 3,
                ),
                "recency": round(
                    recency_score, 3,
                ),
            },
            "timestamp": time.time(),
        }
        self._scores.append(score_record)
        self._stats["scores_calculated"] += 1

        return score_record

    def _evaluate_context(
        self,
        context: dict[str, Any],
    ) -> float:
        """Bağlam puanı hesaplar."""
        score = 0.5  # Varsayılan
        if context.get("deadline"):
            score += 0.2
        if context.get("financial"):
            score += 0.15
        if context.get("customer_facing"):
            score += 0.1
        if context.get("recurring"):
            score -= 0.1
        return min(max(score, 0.0), 1.0)

    def _determine_level(
        self,
        score: float,
    ) -> str:
        """Öncelik seviyesi belirler."""
        if score >= 0.8:
            return "critical"
        if score >= 0.6:
            return "high"
        if score >= 0.4:
            return "medium"
        if score >= 0.2:
            return "low"
        return "informational"

    def calculate_urgency(
        self,
        deadline_hours: float | None = None,
        severity: str = "medium",
        dependencies: int = 0,
    ) -> dict[str, Any]:
        """Aciliyet hesaplar.

        Args:
            deadline_hours: Kalan saat.
            severity: Ciddiyet.
            dependencies: Bağımlı öğe sayısı.

        Returns:
            Aciliyet bilgisi.
        """
        urgency = 0.5

        if deadline_hours is not None:
            if deadline_hours <= 1:
                urgency = 1.0
            elif deadline_hours <= 4:
                urgency = 0.8
            elif deadline_hours <= 24:
                urgency = 0.6
            elif deadline_hours <= 72:
                urgency = 0.4
            else:
                urgency = 0.2

        severity_map = {
            "critical": 0.3,
            "high": 0.2,
            "medium": 0.0,
            "low": -0.1,
        }
        urgency += severity_map.get(
            severity, 0.0,
        )

        # Bağımlılık etkisi
        urgency += min(dependencies * 0.05, 0.2)

        urgency = round(
            min(max(urgency, 0.0), 1.0), 3,
        )

        return {
            "urgency": urgency,
            "deadline_hours": deadline_hours,
            "severity": severity,
            "dependencies": dependencies,
        }

    def assess_impact(
        self,
        scope: str = "individual",
        reversible: bool = True,
        financial_impact: float = 0.0,
    ) -> dict[str, Any]:
        """Etki değerlendirmesi yapar.

        Args:
            scope: Etki kapsamı.
            reversible: Geri alınabilir mi.
            financial_impact: Mali etki.

        Returns:
            Etki bilgisi.
        """
        scope_map = {
            "organization": 1.0,
            "team": 0.7,
            "project": 0.5,
            "individual": 0.3,
        }
        impact = scope_map.get(scope, 0.3)

        if not reversible:
            impact += 0.2

        if financial_impact > 10000:
            impact += 0.3
        elif financial_impact > 1000:
            impact += 0.15
        elif financial_impact > 100:
            impact += 0.05

        impact = round(
            min(max(impact, 0.0), 1.0), 3,
        )

        return {
            "impact": impact,
            "scope": scope,
            "reversible": reversible,
            "financial_impact": financial_impact,
        }

    def adjust_weight(
        self,
        factor: str,
        new_weight: float,
    ) -> dict[str, Any]:
        """Ağırlık ayarlar.

        Args:
            factor: Faktör adı.
            new_weight: Yeni ağırlık.

        Returns:
            Ayarlama bilgisi.
        """
        if factor not in self._weights:
            return {
                "error": "unknown_factor",
                "valid_factors": list(
                    self._weights.keys(),
                ),
            }

        old = self._weights[factor]
        self._weights[factor] = round(
            min(max(new_weight, 0.0), 1.0), 3,
        )

        adjustment = {
            "factor": factor,
            "old_weight": old,
            "new_weight": self._weights[factor],
            "timestamp": time.time(),
        }
        self._adjustments.append(adjustment)
        self._stats["adjustments_made"] += 1

        return {
            "factor": factor,
            "old_weight": old,
            "new_weight": self._weights[factor],
            "adjusted": True,
        }

    def set_source_priority(
        self,
        source: str,
        priority: float,
    ) -> dict[str, Any]:
        """Kaynak önceliği ayarlar.

        Args:
            source: Kaynak adı.
            priority: Öncelik (0-1).

        Returns:
            Ayarlama bilgisi.
        """
        self._source_priorities[source] = round(
            min(max(priority, 0.0), 1.0), 3,
        )
        return {
            "source": source,
            "priority": self._source_priorities[
                source
            ],
            "set": True,
        }

    def get_scores(
        self,
        limit: int = 50,
        min_score: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Puanları getirir.

        Args:
            limit: Maks kayıt.
            min_score: Minimum puan.

        Returns:
            Puan listesi.
        """
        results = [
            s for s in self._scores
            if s["total_score"] >= min_score
        ]
        return list(results[-limit:])

    @property
    def scores_calculated(self) -> int:
        """Hesaplanan puan sayısı."""
        return self._stats["scores_calculated"]

    @property
    def adjustments_made(self) -> int:
        """Yapılan ayar sayısı."""
        return self._stats["adjustments_made"]
