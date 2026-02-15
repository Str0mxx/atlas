"""ATLAS Nedensellik Analizcisi modulu.

Aksiyon-sonuc baglama, nedensel cikarim,
karmasik etken tespiti, atif modelleme, guven puani.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class CausalityAnalyzer:
    """Nedensellik analizcisi.

    Aksiyon-sonuc iliskilerini analiz eder.

    Attributes:
        _links: Nedensel baglar.
        _confounders: Karmasik etkenler.
    """

    def __init__(
        self,
        min_confidence: float = 0.5,
    ) -> None:
        """Nedensellik analizcisini baslatir.

        Args:
            min_confidence: Minimum guven esigi.
        """
        self._links: list[
            dict[str, Any]
        ] = []
        self._action_links: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._confounders: list[
            dict[str, Any]
        ] = []
        self._attributions: dict[
            str, dict[str, Any]
        ] = {}
        self._pattern_history: dict[
            str, list[float]
        ] = {}
        self._min_confidence = min_confidence
        self._stats = {
            "links_created": 0,
            "high_confidence": 0,
            "confounders_detected": 0,
        }

        logger.info(
            "CausalityAnalyzer baslatildi",
        )

    def link_action_outcome(
        self,
        action_id: str,
        outcome_id: str,
        confidence: float = 0.5,
        evidence: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Aksiyon-sonuc baglar.

        Args:
            action_id: Aksiyon ID.
            outcome_id: Sonuc ID.
            confidence: Guven degeri.
            evidence: Kanit bilgisi.

        Returns:
            Bag bilgisi.
        """
        link = {
            "action_id": action_id,
            "outcome_id": outcome_id,
            "confidence": confidence,
            "evidence": evidence or {},
            "created_at": time.time(),
        }

        self._links.append(link)
        if action_id not in self._action_links:
            self._action_links[action_id] = []
        self._action_links[action_id].append(link)

        self._stats["links_created"] += 1
        if confidence >= 0.8:
            self._stats["high_confidence"] += 1

        # Kalip gecmisine ekle
        pattern_key = f"action:{action_id}"
        if pattern_key not in self._pattern_history:
            self._pattern_history[pattern_key] = []
        self._pattern_history[pattern_key].append(
            confidence,
        )

        return {
            "action_id": action_id,
            "outcome_id": outcome_id,
            "confidence": confidence,
            "meets_threshold": (
                confidence >= self._min_confidence
            ),
        }

    def infer_causality(
        self,
        action_id: str,
        outcomes: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Nedensel cikarim yapar.

        Args:
            action_id: Aksiyon ID.
            outcomes: Sonuc listesi.

        Returns:
            Cikarim sonucu.
        """
        if not outcomes:
            return {
                "action_id": action_id,
                "causal": False,
                "reason": "no_outcomes",
            }

        # Zamanlama analizi
        confidences = []
        for outcome in outcomes:
            conf = self._compute_temporal_confidence(
                action_id, outcome,
            )
            confidences.append(conf)

        avg_conf = (
            sum(confidences) / len(confidences)
        )

        # Tekrarlanabilirlik
        history = self._pattern_history.get(
            f"action:{action_id}", [],
        )
        consistency = (
            1.0
            - (
                self._std_dev(history)
                if len(history) > 1
                else 0.5
            )
        )

        final_confidence = (
            avg_conf * 0.6 + consistency * 0.4
        )

        return {
            "action_id": action_id,
            "causal": (
                final_confidence
                >= self._min_confidence
            ),
            "confidence": round(
                final_confidence, 3,
            ),
            "temporal_score": round(avg_conf, 3),
            "consistency_score": round(
                consistency, 3,
            ),
            "outcome_count": len(outcomes),
        }

    def detect_confounder(
        self,
        action_id: str,
        factor_name: str,
        impact: float = 0.5,
        description: str = "",
    ) -> dict[str, Any]:
        """Karmasik etken tespit eder.

        Args:
            action_id: Aksiyon ID.
            factor_name: Etken adi.
            impact: Etki degeri.
            description: Aciklama.

        Returns:
            Tespit bilgisi.
        """
        confounder = {
            "action_id": action_id,
            "factor_name": factor_name,
            "impact": impact,
            "description": description,
            "detected_at": time.time(),
        }

        self._confounders.append(confounder)
        self._stats["confounders_detected"] += 1

        # Aksiyonun guvenini dusur
        links = self._action_links.get(
            action_id, [],
        )
        for link in links:
            link["confidence"] = max(
                0.0,
                link["confidence"] - impact * 0.3,
            )

        return {
            "action_id": action_id,
            "factor_name": factor_name,
            "impact": impact,
            "links_affected": len(links),
        }

    def compute_attribution(
        self,
        outcome_id: str,
        action_ids: list[str],
    ) -> dict[str, Any]:
        """Atif hesaplar.

        Args:
            outcome_id: Sonuc ID.
            action_ids: Aksiyon ID listesi.

        Returns:
            Atif bilgisi.
        """
        if not action_ids:
            return {
                "outcome_id": outcome_id,
                "attributions": {},
            }

        total_confidence = 0.0
        action_confs: dict[str, float] = {}

        for aid in action_ids:
            links = self._action_links.get(aid, [])
            conf = 0.0
            for link in links:
                if link["outcome_id"] == outcome_id:
                    conf = max(
                        conf, link["confidence"],
                    )
            action_confs[aid] = conf
            total_confidence += conf

        # Normalize
        attributions = {}
        for aid, conf in action_confs.items():
            share = (
                conf / total_confidence
                if total_confidence > 0
                else 1.0 / len(action_ids)
            )
            attributions[aid] = round(share, 3)

        self._attributions[outcome_id] = {
            "attributions": attributions,
            "computed_at": time.time(),
        }

        return {
            "outcome_id": outcome_id,
            "attributions": attributions,
            "total_confidence": round(
                total_confidence, 3,
            ),
        }

    def get_confidence_score(
        self,
        action_id: str,
    ) -> float:
        """Guven puanini getirir.

        Args:
            action_id: Aksiyon ID.

        Returns:
            Guven puani.
        """
        links = self._action_links.get(
            action_id, [],
        )
        if not links:
            return 0.0

        confs = [l["confidence"] for l in links]
        return round(
            sum(confs) / len(confs), 3,
        )

    def get_links(
        self,
        action_id: str,
    ) -> list[dict[str, Any]]:
        """Aksiyonun baglarini getirir.

        Args:
            action_id: Aksiyon ID.

        Returns:
            Bag listesi.
        """
        return list(
            self._action_links.get(action_id, []),
        )

    def _compute_temporal_confidence(
        self,
        action_id: str,
        outcome: dict[str, Any],
    ) -> float:
        """Zamansal guven hesaplar.

        Args:
            action_id: Aksiyon ID.
            outcome: Sonuc verisi.

        Returns:
            Guven degeri.
        """
        confidence = outcome.get(
            "confidence", 0.5,
        )
        return min(1.0, max(0.0, confidence))

    def _std_dev(
        self,
        values: list[float],
    ) -> float:
        """Standart sapma hesaplar.

        Args:
            values: Deger listesi.

        Returns:
            Standart sapma.
        """
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum(
            (v - mean) ** 2 for v in values
        ) / len(values)
        return variance**0.5

    @property
    def link_count(self) -> int:
        """Bag sayisi."""
        return len(self._links)

    @property
    def confounder_count(self) -> int:
        """Karmasik etken sayisi."""
        return len(self._confounders)
