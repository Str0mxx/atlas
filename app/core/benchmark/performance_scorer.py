"""ATLAS Performans Puanlayici modulu.

Puan hesaplama, agirlikli puanlama,
normalizasyon, karsilastirma, siralama.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class PerformanceScorer:
    """Performans puanlayici.

    KPI degerlerini puanlar.

    Attributes:
        _scores: Puan kayitlari.
        _weights: KPI agirliklari.
    """

    def __init__(self) -> None:
        """Performans puanlayiciyi baslatir."""
        self._scores: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._weights: dict[str, float] = {}
        self._rankings: list[
            dict[str, Any]
        ] = []
        self._stats = {
            "scored": 0,
        }

        logger.info(
            "PerformanceScorer baslatildi",
        )

    def score(
        self,
        kpi_id: str,
        value: float,
        target: float,
        threshold: float | None = None,
    ) -> dict[str, Any]:
        """Puan hesaplar.

        Args:
            kpi_id: KPI ID.
            value: Guncel deger.
            target: Hedef deger.
            threshold: Esik deger.

        Returns:
            Puan bilgisi.
        """
        if target == 0:
            score = 1.0 if value == 0 else 0.0
        else:
            score = min(1.0, value / target)

        thresh = threshold or target * 0.8
        meets_target = value >= target
        meets_threshold = value >= thresh

        result = {
            "kpi_id": kpi_id,
            "value": value,
            "target": target,
            "score": round(score, 4),
            "meets_target": meets_target,
            "meets_threshold": meets_threshold,
            "timestamp": time.time(),
        }

        if kpi_id not in self._scores:
            self._scores[kpi_id] = []
        self._scores[kpi_id].append(result)
        self._stats["scored"] += 1

        return result

    def weighted_score(
        self,
        scores: dict[str, float],
        weights: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """Agirlikli puan hesaplar.

        Args:
            scores: KPI puanlari.
            weights: Agirliklar.

        Returns:
            Agirlikli puan.
        """
        w = weights or self._weights
        total_weight = 0.0
        weighted_sum = 0.0

        details = {}
        for kpi_id, score_val in scores.items():
            weight = w.get(kpi_id, 1.0)
            weighted_sum += score_val * weight
            total_weight += weight
            details[kpi_id] = {
                "score": score_val,
                "weight": weight,
                "weighted": round(
                    score_val * weight, 4,
                ),
            }

        overall = (
            weighted_sum / total_weight
            if total_weight > 0
            else 0.0
        )

        return {
            "overall_score": round(overall, 4),
            "details": details,
            "total_weight": total_weight,
        }

    def normalize(
        self,
        values: dict[str, float],
    ) -> dict[str, float]:
        """Degerleri normalize eder.

        Args:
            values: KPI degerleri.

        Returns:
            Normalize edilmis degerler.
        """
        if not values:
            return {}

        vals = list(values.values())
        min_v = min(vals)
        max_v = max(vals)
        range_v = max_v - min_v

        if range_v == 0:
            return {
                k: 1.0 for k in values
            }

        return {
            k: round((v - min_v) / range_v, 4)
            for k, v in values.items()
        }

    def compare(
        self,
        kpi_id: str,
        value_a: float,
        value_b: float,
        target: float = 0.0,
    ) -> dict[str, Any]:
        """Iki degeri karsilastirir.

        Args:
            kpi_id: KPI ID.
            value_a: Deger A.
            value_b: Deger B.
            target: Hedef.

        Returns:
            Karsilastirma sonucu.
        """
        diff = value_a - value_b
        if value_b != 0:
            pct_diff = (diff / abs(value_b)) * 100
        else:
            pct_diff = 100.0 if diff != 0 else 0.0

        winner = (
            "a" if value_a > value_b
            else "b" if value_b > value_a
            else "tie"
        )

        return {
            "kpi_id": kpi_id,
            "value_a": value_a,
            "value_b": value_b,
            "diff": round(diff, 4),
            "pct_diff": round(pct_diff, 2),
            "winner": winner,
        }

    def rank(
        self,
        scores: dict[str, float],
    ) -> list[dict[str, Any]]:
        """Puanlari siralar.

        Args:
            scores: Eleman puanlari.

        Returns:
            Siralama listesi.
        """
        sorted_items = sorted(
            scores.items(),
            key=lambda x: x[1],
            reverse=True,
        )

        ranking = []
        for i, (name, score_val) in enumerate(
            sorted_items,
        ):
            ranking.append({
                "rank": i + 1,
                "name": name,
                "score": score_val,
            })

        self._rankings = ranking
        return ranking

    def set_weight(
        self,
        kpi_id: str,
        weight: float,
    ) -> None:
        """Agirlik ayarlar.

        Args:
            kpi_id: KPI ID.
            weight: Agirlik.
        """
        self._weights[kpi_id] = weight

    def get_scores(
        self,
        kpi_id: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """KPI puan gecmisini getirir.

        Args:
            kpi_id: KPI ID.
            limit: Limit.

        Returns:
            Puan listesi.
        """
        return list(
            self._scores.get(kpi_id, [])[-limit:],
        )

    @property
    def scored_kpi_count(self) -> int:
        """Puanlanan KPI sayisi."""
        return len(self._scores)

    @property
    def total_scores(self) -> int:
        """Toplam puan sayisi."""
        return self._stats["scored"]
