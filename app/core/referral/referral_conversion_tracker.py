"""ATLAS Referans Dönüşüm Takipçisi.

Dönüşüm takibi, atıflandırma modelleme,
funnel analizi, süre ve kalite puanlama.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ReferralConversionTracker:
    """Referans dönüşüm takipçisi.

    Referans dönüşümlerini takip eder,
    atıflandırma yapar ve kalite puanlar.

    Attributes:
        _conversions: Dönüşüm kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Takipçiyi başlatır."""
        self._conversions: dict[
            str, dict
        ] = {}
        self._stats = {
            "conversions_tracked": 0,
            "funnels_analyzed": 0,
        }
        logger.info(
            "ReferralConversionTracker "
            "baslatildi",
        )

    @property
    def conversion_count(self) -> int:
        """Takip edilen dönüşüm sayısı."""
        return self._stats[
            "conversions_tracked"
        ]

    @property
    def funnel_count(self) -> int:
        """Analiz edilen funnel sayısı."""
        return self._stats[
            "funnels_analyzed"
        ]

    def track_conversion(
        self,
        referral_id: str,
        referrer_id: str = "",
        referred_id: str = "",
        value: float = 0.0,
    ) -> dict[str, Any]:
        """Dönüşüm takibi yapar.

        Args:
            referral_id: Referans kimliği.
            referrer_id: Referansçı kimliği.
            referred_id: Davet edilen kimliği.
            value: Dönüşüm değeri.

        Returns:
            Dönüşüm bilgisi.
        """
        cid = (
            f"conv_{len(self._conversions)}"
        )
        self._conversions[cid] = {
            "referral_id": referral_id,
            "referrer_id": referrer_id,
            "referred_id": referred_id,
            "value": value,
        }
        self._stats[
            "conversions_tracked"
        ] += 1

        return {
            "conversion_id": cid,
            "referral_id": referral_id,
            "value": value,
            "tracked": True,
        }

    def attribute_conversion(
        self,
        conversion_id: str,
        model: str = "last_click",
        touchpoints: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Atıflandırma modelleme yapar.

        Args:
            conversion_id: Dönüşüm kimliği.
            model: Atıflandırma modeli.
            touchpoints: Temas noktaları.

        Returns:
            Atıflandırma bilgisi.
        """
        if touchpoints is None:
            touchpoints = []

        if model == "last_click":
            attributed = (
                touchpoints[-1]
                if touchpoints
                else ""
            )
        elif model == "first_click":
            attributed = (
                touchpoints[0]
                if touchpoints
                else ""
            )
        else:
            attributed = (
                touchpoints[-1]
                if touchpoints
                else ""
            )

        return {
            "conversion_id": conversion_id,
            "model": model,
            "attributed_to": attributed,
            "touchpoint_count": len(
                touchpoints,
            ),
            "attributed": True,
        }

    def analyze_funnel(
        self,
        stages: dict[str, int]
        | None = None,
    ) -> dict[str, Any]:
        """Funnel analizi yapar.

        Args:
            stages: Aşama->sayı eşlemesi.

        Returns:
            Funnel bilgisi.
        """
        if stages is None:
            stages = {}

        values = list(stages.values())
        drop_offs = {}
        for i in range(1, len(values)):
            prev = values[i - 1] or 1
            rate = round(
                (1 - values[i] / prev) * 100,
                1,
            )
            stage_names = list(stages.keys())
            drop_offs[
                stage_names[i]
            ] = rate

        self._stats[
            "funnels_analyzed"
        ] += 1

        return {
            "stages": stages,
            "drop_offs": drop_offs,
            "analyzed": True,
        }

    def measure_time_to_convert(
        self,
        referral_id: str,
        hours_elapsed: float = 0.0,
    ) -> dict[str, Any]:
        """Dönüşüm süresi ölçer.

        Args:
            referral_id: Referans kimliği.
            hours_elapsed: Geçen saat.

        Returns:
            Süre bilgisi.
        """
        if hours_elapsed <= 24:
            speed = "fast"
        elif hours_elapsed <= 72:
            speed = "normal"
        elif hours_elapsed <= 168:
            speed = "slow"
        else:
            speed = "very_slow"

        return {
            "referral_id": referral_id,
            "hours_elapsed": hours_elapsed,
            "speed": speed,
            "measured": True,
        }

    def score_quality(
        self,
        referral_id: str,
        purchase_value: float = 0.0,
        retention_days: int = 0,
        activity_score: float = 0.0,
    ) -> dict[str, Any]:
        """Kalite puanlama yapar.

        Args:
            referral_id: Referans kimliği.
            purchase_value: Satın alma değeri.
            retention_days: Tutma günü.
            activity_score: Aktivite puanı.

        Returns:
            Kalite bilgisi.
        """
        value_score = min(
            purchase_value / 100, 1.0,
        )
        retention_score = min(
            retention_days / 90, 1.0,
        )
        quality = round(
            value_score * 0.4
            + retention_score * 0.35
            + activity_score * 0.25,
            2,
        )

        if quality >= 0.8:
            grade = "A"
        elif quality >= 0.6:
            grade = "B"
        elif quality >= 0.4:
            grade = "C"
        else:
            grade = "D"

        return {
            "referral_id": referral_id,
            "quality_score": quality,
            "grade": grade,
            "scored": True,
        }
