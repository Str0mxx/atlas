"""ATLAS Esik Yoneticisi modulu.

Dinamik esikler, aksiyon/alan esikleri,
adaptif ayarlama, guvenlik marjlari.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ThresholdManager:
    """Esik yoneticisi.

    Guven esiklerini dinamik yonetir.

    Attributes:
        _thresholds: Esik kayitlari.
        _action_thresholds: Aksiyon esikleri.
    """

    def __init__(
        self,
        auto_execute: float = 0.8,
        suggest: float = 0.5,
        ask_human: float = 0.3,
        safety_margin: float = 0.05,
    ) -> None:
        """Esik yoneticisini baslatir.

        Args:
            auto_execute: Otomatik calistirma esigi.
            suggest: Onerme esigi.
            ask_human: Insana sorma esigi.
            safety_margin: Guvenlik marji.
        """
        self._defaults = {
            "auto_execute": auto_execute,
            "suggest": suggest,
            "ask_human": ask_human,
        }
        self._action_thresholds: dict[
            str, dict[str, float]
        ] = {}
        self._domain_thresholds: dict[
            str, dict[str, float]
        ] = {}
        self._adjustments: list[
            dict[str, Any]
        ] = []
        self._safety_margin = safety_margin
        self._stats = {
            "evaluations": 0,
            "adjustments": 0,
        }

        logger.info(
            "ThresholdManager baslatildi",
        )

    def get_threshold(
        self,
        action_type: str = "",
        domain: str = "",
    ) -> dict[str, float]:
        """Esik degerlerini getirir.

        Args:
            action_type: Aksiyon tipi.
            domain: Alan.

        Returns:
            Esik degerleri.
        """
        # Oncelik: aksiyon > alan > varsayilan
        if action_type in self._action_thresholds:
            return dict(
                self._action_thresholds[
                    action_type
                ],
            )
        if domain in self._domain_thresholds:
            return dict(
                self._domain_thresholds[domain],
            )
        return dict(self._defaults)

    def evaluate(
        self,
        score: float,
        action_type: str = "",
        domain: str = "",
    ) -> dict[str, Any]:
        """Guven puanini esiklere gore degerlendirir.

        Args:
            score: Guven puani.
            action_type: Aksiyon tipi.
            domain: Alan.

        Returns:
            Degerlendirme sonucu.
        """
        thresholds = self.get_threshold(
            action_type, domain,
        )
        margin = self._safety_margin

        self._stats["evaluations"] += 1

        if score >= thresholds["auto_execute"] + margin:
            action = "auto_execute"
        elif score >= thresholds["suggest"]:
            action = "suggest"
        elif score >= thresholds["ask_human"]:
            action = "ask_human"
        else:
            action = "reject"

        return {
            "score": score,
            "action": action,
            "thresholds": thresholds,
            "margin": margin,
        }

    def set_action_threshold(
        self,
        action_type: str,
        auto_execute: float | None = None,
        suggest: float | None = None,
        ask_human: float | None = None,
    ) -> dict[str, Any]:
        """Aksiyon esigi ayarlar.

        Args:
            action_type: Aksiyon tipi.
            auto_execute: Otomatik calistirma esigi.
            suggest: Onerme esigi.
            ask_human: Insana sorma esigi.

        Returns:
            Ayarlama bilgisi.
        """
        current = self._action_thresholds.get(
            action_type, dict(self._defaults),
        )
        if auto_execute is not None:
            current["auto_execute"] = auto_execute
        if suggest is not None:
            current["suggest"] = suggest
        if ask_human is not None:
            current["ask_human"] = ask_human

        self._action_thresholds[action_type] = (
            current
        )

        return {
            "action_type": action_type,
            "thresholds": current,
            "updated": True,
        }

    def set_domain_threshold(
        self,
        domain: str,
        auto_execute: float | None = None,
        suggest: float | None = None,
        ask_human: float | None = None,
    ) -> dict[str, Any]:
        """Alan esigi ayarlar.

        Args:
            domain: Alan.
            auto_execute: Otomatik calistirma esigi.
            suggest: Onerme esigi.
            ask_human: Insana sorma esigi.

        Returns:
            Ayarlama bilgisi.
        """
        current = self._domain_thresholds.get(
            domain, dict(self._defaults),
        )
        if auto_execute is not None:
            current["auto_execute"] = auto_execute
        if suggest is not None:
            current["suggest"] = suggest
        if ask_human is not None:
            current["ask_human"] = ask_human

        self._domain_thresholds[domain] = current

        return {
            "domain": domain,
            "thresholds": current,
            "updated": True,
        }

    def adaptive_adjust(
        self,
        domain: str,
        accuracy: float,
        direction: str = "auto",
    ) -> dict[str, Any]:
        """Adaptif ayarlama yapar.

        Args:
            domain: Alan.
            accuracy: Dogruluk orani.
            direction: Yon (tighten/loosen/auto).

        Returns:
            Ayarlama bilgisi.
        """
        current = self._domain_thresholds.get(
            domain, dict(self._defaults),
        )

        if direction == "auto":
            if accuracy < 0.7:
                direction = "tighten"
            elif accuracy > 0.9:
                direction = "loosen"
            else:
                return {
                    "domain": domain,
                    "adjusted": False,
                    "reason": "accuracy_acceptable",
                }

        step = 0.05
        if direction == "tighten":
            current["auto_execute"] = min(
                0.99,
                current["auto_execute"] + step,
            )
            current["suggest"] = min(
                current["auto_execute"] - 0.1,
                current["suggest"] + step,
            )
        elif direction == "loosen":
            current["auto_execute"] = max(
                0.5,
                current["auto_execute"] - step,
            )
            current["suggest"] = max(
                0.2,
                current["suggest"] - step,
            )

        self._domain_thresholds[domain] = current
        self._adjustments.append({
            "domain": domain,
            "direction": direction,
            "accuracy": accuracy,
            "new_thresholds": dict(current),
            "timestamp": time.time(),
        })
        self._stats["adjustments"] += 1

        return {
            "domain": domain,
            "direction": direction,
            "thresholds": current,
            "adjusted": True,
        }

    def set_safety_margin(
        self,
        margin: float,
    ) -> None:
        """Guvenlik marjini ayarlar.

        Args:
            margin: Marj degeri.
        """
        self._safety_margin = max(0.0, margin)

    @property
    def action_threshold_count(self) -> int:
        """Aksiyon esik sayisi."""
        return len(self._action_thresholds)

    @property
    def domain_threshold_count(self) -> int:
        """Alan esik sayisi."""
        return len(self._domain_thresholds)

    @property
    def adjustment_count(self) -> int:
        """Ayarlama sayisi."""
        return len(self._adjustments)
