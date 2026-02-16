"""ATLAS Dolandırıcılık Risk Puanlayıcı modülü.

Risk hesaplama, çok faktörlü puanlama,
güven seviyeleri, eşik yönetimi,
puan açıklaması.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class FraudRiskScorer:
    """Dolandırıcılık risk puanlayıcı.

    Çok faktörlü risk puanı hesaplar.

    Attributes:
        _scores: Puan kayıtları.
        _thresholds: Eşik kayıtları.
    """

    def __init__(self) -> None:
        """Puanlayıcıyı başlatır."""
        self._scores: dict[
            str, dict[str, Any]
        ] = {}
        self._thresholds = {
            "critical": 85.0,
            "high": 65.0,
            "medium": 40.0,
            "low": 20.0,
        }
        self._counter = 0
        self._stats = {
            "scores_calculated": 0,
            "high_risk_flagged": 0,
        }

        logger.info(
            "FraudRiskScorer baslatildi",
        )

    def calculate_risk(
        self,
        entity: str,
        factors: dict[str, float]
        | None = None,
    ) -> dict[str, Any]:
        """Risk hesaplar.

        Args:
            entity: Varlık.
            factors: Faktörler.

        Returns:
            Risk bilgisi.
        """
        factors = factors or {}
        if not factors:
            return {
                "entity": entity,
                "calculated": False,
            }

        score = round(
            sum(factors.values())
            / len(factors),
            1,
        )

        level = (
            "critical"
            if score >= self._thresholds[
                "critical"
            ]
            else "high"
            if score >= self._thresholds[
                "high"
            ]
            else "medium"
            if score >= self._thresholds[
                "medium"
            ]
            else "low"
            if score >= self._thresholds[
                "low"
            ]
            else "negligible"
        )

        self._scores[entity] = {
            "entity": entity,
            "score": score,
            "level": level,
            "factors": factors,
            "timestamp": time.time(),
        }
        self._stats[
            "scores_calculated"
        ] += 1

        if level in ("critical", "high"):
            self._stats[
                "high_risk_flagged"
            ] += 1

        return {
            "entity": entity,
            "score": score,
            "level": level,
            "calculated": True,
        }

    def score_multifactor(
        self,
        entity: str,
        anomaly_score: float = 0.0,
        pattern_score: float = 0.0,
        behavior_score: float = 0.0,
        history_score: float = 0.0,
    ) -> dict[str, Any]:
        """Çok faktörlü puan hesaplar.

        Args:
            entity: Varlık.
            anomaly_score: Anomali puanı.
            pattern_score: Kalıp puanı.
            behavior_score: Davranış puanı.
            history_score: Geçmiş puanı.

        Returns:
            Puan bilgisi.
        """
        weighted = round(
            anomaly_score * 0.3
            + pattern_score * 0.25
            + behavior_score * 0.25
            + history_score * 0.2,
            1,
        )

        return self.calculate_risk(
            entity,
            factors={
                "anomaly": anomaly_score,
                "pattern": pattern_score,
                "behavior": behavior_score,
                "history": history_score,
                "_weighted": weighted,
            },
        )

    def get_confidence(
        self,
        entity: str,
    ) -> dict[str, Any]:
        """Güven seviyesi döndürür.

        Args:
            entity: Varlık.

        Returns:
            Güven bilgisi.
        """
        record = self._scores.get(entity)
        if not record:
            return {
                "entity": entity,
                "found": False,
            }

        factors = record["factors"]
        count = len([
            v for k, v in factors.items()
            if not k.startswith("_")
        ])

        # Daha fazla faktör = daha yüksek güven
        confidence = min(
            round(count * 20, 1), 95.0,
        )

        level = (
            "high" if confidence >= 70
            else "medium"
            if confidence >= 40
            else "low"
        )

        return {
            "entity": entity,
            "confidence": confidence,
            "level": level,
            "factor_count": count,
            "found": True,
        }

    def set_threshold(
        self,
        level: str,
        value: float,
    ) -> dict[str, Any]:
        """Eşik ayarlar.

        Args:
            level: Seviye.
            value: Değer.

        Returns:
            Ayarlama bilgisi.
        """
        if level not in self._thresholds:
            return {
                "level": level,
                "set": False,
            }

        old = self._thresholds[level]
        self._thresholds[level] = value

        return {
            "level": level,
            "old": old,
            "new": value,
            "set": True,
        }

    def explain_score(
        self,
        entity: str,
    ) -> dict[str, Any]:
        """Puan açıklaması yapar.

        Args:
            entity: Varlık.

        Returns:
            Açıklama bilgisi.
        """
        record = self._scores.get(entity)
        if not record:
            return {
                "entity": entity,
                "explained": False,
            }

        factors = record["factors"]
        explanations = []

        for key, val in sorted(
            factors.items(),
            key=lambda x: x[1],
            reverse=True,
        ):
            if key.startswith("_"):
                continue
            contribution = (
                "major" if val >= 70
                else "moderate"
                if val >= 40
                else "minor"
            )
            explanations.append({
                "factor": key,
                "value": val,
                "contribution": contribution,
            })

        return {
            "entity": entity,
            "score": record["score"],
            "level": record["level"],
            "explanations": explanations,
            "explained": True,
        }

    @property
    def score_count(self) -> int:
        """Puan sayısı."""
        return self._stats[
            "scores_calculated"
        ]

    @property
    def high_risk_count(self) -> int:
        """Yüksek risk sayısı."""
        return self._stats[
            "high_risk_flagged"
        ]
