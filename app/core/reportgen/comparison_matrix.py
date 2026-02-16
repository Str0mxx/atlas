"""ATLAS Karşılaştırma Matrisi modülü.

Özellik karşılaştırma, puanlama matrisi,
ağırlıklı analiz, görsel tablo,
kazanan vurgulama.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ComparisonMatrix:
    """Karşılaştırma matrisi.

    Öğeleri kriterlere göre karşılaştırır.

    Attributes:
        _comparisons: Karşılaştırma geçmişi.
    """

    def __init__(self) -> None:
        """Matrisi başlatır."""
        self._comparisons: list[
            dict[str, Any]
        ] = {}
        self._counter = 0
        self._stats = {
            "comparisons_created": 0,
            "items_compared": 0,
            "winners_determined": 0,
        }

        logger.info(
            "ComparisonMatrix baslatildi",
        )

    def create_comparison(
        self,
        title: str,
        items: list[str],
        criteria: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Karşılaştırma oluşturur.

        Args:
            title: Başlık.
            items: Karşılaştırılacak öğeler.
            criteria: Kriter listesi.

        Returns:
            Oluşturma bilgisi.
        """
        self._counter += 1
        cid = f"cmp_{self._counter}"

        comparison = {
            "comparison_id": cid,
            "title": title,
            "items": items,
            "criteria": criteria,
            "scores": {},
            "winner": None,
            "created_at": time.time(),
        }
        self._comparisons[cid] = comparison
        self._stats["comparisons_created"] += 1
        self._stats["items_compared"] += len(
            items,
        )

        return {
            "comparison_id": cid,
            "title": title,
            "items_count": len(items),
            "criteria_count": len(criteria),
            "created": True,
        }

    def set_scores(
        self,
        comparison_id: str,
        scores: dict[str, dict[str, float]],
    ) -> dict[str, Any]:
        """Puanları ayarlar.

        Args:
            comparison_id: Karşılaştırma ID.
            scores: Puan matrisi
                {item: {criterion: score}}.

        Returns:
            Ayar bilgisi.
        """
        comparison = self._comparisons.get(
            comparison_id,
        )
        if not comparison:
            return {
                "error": "comparison_not_found",
            }

        comparison["scores"] = scores

        return {
            "comparison_id": comparison_id,
            "items_scored": len(scores),
            "set": True,
        }

    def calculate_weighted(
        self,
        comparison_id: str,
    ) -> dict[str, Any]:
        """Ağırlıklı analiz yapar.

        Args:
            comparison_id: Karşılaştırma ID.

        Returns:
            Analiz bilgisi.
        """
        comparison = self._comparisons.get(
            comparison_id,
        )
        if not comparison:
            return {
                "error": "comparison_not_found",
            }

        scores = comparison["scores"]
        criteria = comparison["criteria"]

        # Ağırlık haritası
        weights = {}
        for c in criteria:
            weights[c["name"]] = c.get(
                "weight", 1.0,
            )

        # Ağırlıklı puan hesapla
        weighted_totals = {}
        for item, item_scores in scores.items():
            total = 0.0
            for crit, score in (
                item_scores.items()
            ):
                w = weights.get(crit, 1.0)
                total += score * w
            weighted_totals[item] = round(
                total, 2,
            )

        # Kazanan
        winner = None
        if weighted_totals:
            winner = max(
                weighted_totals,
                key=weighted_totals.get,
            )
            comparison["winner"] = winner
            self._stats[
                "winners_determined"
            ] += 1

        return {
            "comparison_id": comparison_id,
            "weighted_scores": weighted_totals,
            "winner": winner,
            "method": "weighted",
        }

    def generate_table(
        self,
        comparison_id: str,
    ) -> dict[str, Any]:
        """Görsel tablo üretir.

        Args:
            comparison_id: Karşılaştırma ID.

        Returns:
            Tablo bilgisi.
        """
        comparison = self._comparisons.get(
            comparison_id,
        )
        if not comparison:
            return {
                "error": "comparison_not_found",
            }

        headers = ["Item"] + [
            c["name"]
            for c in comparison["criteria"]
        ] + ["Total"]

        rows = []
        scores = comparison["scores"]
        for item in comparison["items"]:
            row = [item]
            total = 0.0
            item_scores = scores.get(item, {})
            for c in comparison["criteria"]:
                s = item_scores.get(
                    c["name"], 0,
                )
                row.append(s)
                total += s
            row.append(round(total, 2))
            rows.append(row)

        return {
            "comparison_id": comparison_id,
            "headers": headers,
            "rows": rows,
            "winner": comparison.get("winner"),
            "row_count": len(rows),
        }

    def highlight_winner(
        self,
        comparison_id: str,
    ) -> dict[str, Any]:
        """Kazananı vurgular.

        Args:
            comparison_id: Karşılaştırma ID.

        Returns:
            Vurgulama bilgisi.
        """
        comparison = self._comparisons.get(
            comparison_id,
        )
        if not comparison:
            return {
                "error": "comparison_not_found",
            }

        winner = comparison.get("winner")
        if not winner:
            return {
                "comparison_id": comparison_id,
                "winner": None,
                "message": "No winner determined",
            }

        winner_scores = comparison[
            "scores"
        ].get(winner, {})
        strengths = []
        for crit, score in (
            winner_scores.items()
        ):
            if score >= 4.0:
                strengths.append(crit)

        return {
            "comparison_id": comparison_id,
            "winner": winner,
            "winner_scores": winner_scores,
            "strengths": strengths,
            "highlighted": True,
        }

    def get_comparison(
        self,
        comparison_id: str,
    ) -> dict[str, Any]:
        """Karşılaştırma getirir.

        Args:
            comparison_id: Karşılaştırma ID.

        Returns:
            Karşılaştırma bilgisi.
        """
        comparison = self._comparisons.get(
            comparison_id,
        )
        if not comparison:
            return {
                "error": "comparison_not_found",
            }
        return dict(comparison)

    def get_comparisons(
        self,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Karşılaştırmaları getirir.

        Args:
            limit: Maks kayıt.

        Returns:
            Karşılaştırma listesi.
        """
        results = list(
            self._comparisons.values(),
        )
        return results[-limit:]

    @property
    def comparison_count(self) -> int:
        """Karşılaştırma sayısı."""
        return self._stats[
            "comparisons_created"
        ]

    @property
    def winner_count(self) -> int:
        """Kazanan sayısı."""
        return self._stats[
            "winners_determined"
        ]
