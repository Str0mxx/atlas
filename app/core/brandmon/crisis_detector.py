"""ATLAS Kriz Tespitçisi modülü.

Viral tespit, negatif artış,
etkileyici bahsedilmeleri, medya kapsamı,
erken uyarı.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class CrisisDetector:
    """Kriz tespitçisi.

    Marka krizlerini erken tespit eder.

    Attributes:
        _crises: Kriz kayıtları.
        _signals: Sinyal kayıtları.
    """

    def __init__(self) -> None:
        """Tespitçiyi başlatır."""
        self._crises: list[
            dict[str, Any]
        ] = []
        self._signals: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "crises_detected": 0,
            "warnings_issued": 0,
        }

        logger.info(
            "CrisisDetector baslatildi",
        )

    def detect_viral(
        self,
        brand: str,
        mention_count: int = 0,
        time_window_hours: float = 1.0,
        normal_rate: int = 10,
    ) -> dict[str, Any]:
        """Viral içerik tespit eder.

        Args:
            brand: Marka.
            mention_count: Bahsedilme sayısı.
            time_window_hours: Zaman penceresi.
            normal_rate: Normal oran.

        Returns:
            Tespit bilgisi.
        """
        rate = (
            mention_count
            / max(time_window_hours, 0.01)
        )
        is_viral = rate > normal_rate * 5

        if is_viral:
            self._counter += 1
            self._signals.append({
                "signal_id": (
                    f"sig_{self._counter}"
                ),
                "type": "viral",
                "brand": brand,
                "rate": round(rate, 1),
                "timestamp": time.time(),
            })

        return {
            "brand": brand,
            "mention_rate": round(rate, 1),
            "normal_rate": normal_rate,
            "is_viral": is_viral,
        }

    def detect_negative_spike(
        self,
        brand: str,
        negative_count: int = 0,
        total_count: int = 1,
        threshold: float = 0.4,
    ) -> dict[str, Any]:
        """Negatif artış tespit eder.

        Args:
            brand: Marka.
            negative_count: Negatif sayısı.
            total_count: Toplam sayı.
            threshold: Eşik.

        Returns:
            Tespit bilgisi.
        """
        ratio = (
            negative_count
            / max(total_count, 1)
        )
        is_spike = ratio > threshold

        if is_spike:
            self._counter += 1
            self._signals.append({
                "signal_id": (
                    f"sig_{self._counter}"
                ),
                "type": "negative_spike",
                "brand": brand,
                "ratio": round(ratio, 2),
                "timestamp": time.time(),
            })

        return {
            "brand": brand,
            "negative_ratio": round(
                ratio, 2,
            ),
            "threshold": threshold,
            "is_spike": is_spike,
        }

    def detect_influencer_mention(
        self,
        brand: str,
        influencer: str = "",
        followers: int = 0,
        sentiment: str = "neutral",
        min_followers: int = 10000,
    ) -> dict[str, Any]:
        """Etkileyici bahsedilmesi tespit eder.

        Args:
            brand: Marka.
            influencer: Etkileyici.
            followers: Takipçi sayısı.
            sentiment: Duygu.
            min_followers: Min takipçi.

        Returns:
            Tespit bilgisi.
        """
        is_significant = (
            followers >= min_followers
        )
        is_risky = (
            is_significant
            and sentiment == "negative"
        )

        if is_risky:
            self._counter += 1
            self._signals.append({
                "signal_id": (
                    f"sig_{self._counter}"
                ),
                "type": "influencer_negative",
                "brand": brand,
                "influencer": influencer,
                "followers": followers,
                "timestamp": time.time(),
            })

        return {
            "brand": brand,
            "influencer": influencer,
            "followers": followers,
            "is_significant": is_significant,
            "is_risky": is_risky,
        }

    def detect_media_coverage(
        self,
        brand: str,
        outlet_count: int = 0,
        sentiment: str = "neutral",
        tier: str = "local",
    ) -> dict[str, Any]:
        """Medya kapsamı tespit eder.

        Args:
            brand: Marka.
            outlet_count: Yayın sayısı.
            sentiment: Duygu.
            tier: Katman.

        Returns:
            Tespit bilgisi.
        """
        is_widespread = outlet_count >= 3
        is_crisis_risk = (
            is_widespread
            and sentiment == "negative"
            and tier in ("national", "global")
        )

        return {
            "brand": brand,
            "outlet_count": outlet_count,
            "sentiment": sentiment,
            "tier": tier,
            "is_widespread": is_widespread,
            "is_crisis_risk": is_crisis_risk,
        }

    def issue_early_warning(
        self,
        brand: str,
    ) -> dict[str, Any]:
        """Erken uyarı verir.

        Args:
            brand: Marka.

        Returns:
            Uyarı bilgisi.
        """
        brand_signals = [
            s for s in self._signals
            if s["brand"] == brand
        ]

        if not brand_signals:
            return {
                "brand": brand,
                "warning": False,
                "level": "none",
            }

        signal_count = len(brand_signals)
        level = (
            "critical" if signal_count >= 3
            else "high" if signal_count >= 2
            else "medium"
        )

        self._counter += 1
        cid = f"crisis_{self._counter}"
        self._crises.append({
            "crisis_id": cid,
            "brand": brand,
            "level": level,
            "signal_count": signal_count,
            "timestamp": time.time(),
        })
        self._stats[
            "crises_detected"
        ] += 1
        self._stats[
            "warnings_issued"
        ] += 1

        return {
            "brand": brand,
            "crisis_id": cid,
            "level": level,
            "signal_count": signal_count,
            "warning": True,
        }

    @property
    def crisis_count(self) -> int:
        """Kriz sayısı."""
        return self._stats[
            "crises_detected"
        ]

    @property
    def warning_count(self) -> int:
        """Uyarı sayısı."""
        return self._stats[
            "warnings_issued"
        ]
