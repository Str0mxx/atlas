"""ATLAS Varış Süresi Hesaplayıcı modülü.

ETA tahmini, geçmiş örüntüler,
trafik ayarlaması, gerçek zamanlı
güncelleme, gecikme tespiti.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ETACalculator:
    """Varış süresi hesaplayıcı.

    ETA tahmin ve güncelleme sağlar.

    Attributes:
        _estimates: Tahmin kayıtları.
        _patterns: Geçmiş örüntüler.
    """

    def __init__(self) -> None:
        """Hesaplayıcıyı başlatır."""
        self._estimates: dict[
            str, dict[str, Any]
        ] = {}
        self._patterns: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "estimates_made": 0,
            "delays_detected": 0,
        }

        logger.info(
            "ETACalculator baslatildi",
        )

    def predict_eta(
        self,
        distance_km: float,
        speed_kmh: float = 50.0,
        traffic_factor: float = 1.0,
    ) -> dict[str, Any]:
        """ETA tahmini yapar.

        Args:
            distance_km: Mesafe (km).
            speed_kmh: Hız (km/s).
            traffic_factor: Trafik çarpanı.

        Returns:
            Tahmin bilgisi.
        """
        self._counter += 1
        eid = f"eta_{self._counter}"

        if speed_kmh <= 0:
            speed_kmh = 1.0

        base_min = (
            distance_km / speed_kmh * 60
        )
        adjusted_min = (
            base_min * traffic_factor
        )

        self._estimates[eid] = {
            "eta_id": eid,
            "distance_km": distance_km,
            "base_min": round(
                base_min, 1,
            ),
            "adjusted_min": round(
                adjusted_min, 1,
            ),
            "traffic_factor": (
                traffic_factor
            ),
            "created_at": time.time(),
        }

        self._stats[
            "estimates_made"
        ] += 1

        return {
            "eta_id": eid,
            "base_min": round(
                base_min, 1,
            ),
            "adjusted_min": round(
                adjusted_min, 1,
            ),
            "confidence": (
                0.9
                if traffic_factor <= 1.2
                else 0.7
            ),
            "predicted": True,
        }

    def use_historical(
        self,
        route_key: str,
        hour_of_day: int = 12,
    ) -> dict[str, Any]:
        """Geçmiş örüntülerden tahmin yapar.

        Args:
            route_key: Rota anahtarı.
            hour_of_day: Günün saati.

        Returns:
            Tahmin bilgisi.
        """
        matching = [
            p
            for p in self._patterns
            if p["route_key"] == route_key
        ]

        if not matching:
            return {
                "route_key": route_key,
                "patterns_found": 0,
                "historical": False,
            }

        avg_min = sum(
            p["duration_min"]
            for p in matching
        ) / len(matching)

        if 7 <= hour_of_day <= 9:
            factor = 1.4
        elif 17 <= hour_of_day <= 19:
            factor = 1.5
        else:
            factor = 1.0

        adjusted = avg_min * factor

        return {
            "route_key": route_key,
            "patterns_found": len(
                matching,
            ),
            "avg_min": round(avg_min, 1),
            "adjusted_min": round(
                adjusted, 1,
            ),
            "peak_factor": factor,
            "historical": True,
        }

    def add_pattern(
        self,
        route_key: str,
        duration_min: float,
        hour_of_day: int = 12,
    ) -> dict[str, Any]:
        """Geçmiş örüntü ekler.

        Args:
            route_key: Rota anahtarı.
            duration_min: Süre (dakika).
            hour_of_day: Günün saati.

        Returns:
            Ekleme bilgisi.
        """
        self._patterns.append({
            "route_key": route_key,
            "duration_min": duration_min,
            "hour_of_day": hour_of_day,
            "recorded_at": time.time(),
        })

        return {
            "route_key": route_key,
            "duration_min": duration_min,
            "added": True,
        }

    def update_realtime(
        self,
        eta_id: str,
        remaining_km: float,
        current_speed_kmh: float = 50.0,
    ) -> dict[str, Any]:
        """Gerçek zamanlı ETA günceller.

        Args:
            eta_id: ETA kimliği.
            remaining_km: Kalan mesafe.
            current_speed_kmh: Anlık hız.

        Returns:
            Güncelleme bilgisi.
        """
        est = self._estimates.get(eta_id)
        if not est:
            return {
                "eta_id": eta_id,
                "found": False,
            }

        if current_speed_kmh <= 0:
            current_speed_kmh = 1.0

        new_min = (
            remaining_km
            / current_speed_kmh
            * 60
        )

        est["adjusted_min"] = round(
            new_min, 1,
        )

        return {
            "eta_id": eta_id,
            "remaining_km": remaining_km,
            "new_eta_min": round(
                new_min, 1,
            ),
            "updated": True,
        }

    def detect_delay(
        self,
        eta_id: str,
        elapsed_min: float,
        progress_pct: float,
    ) -> dict[str, Any]:
        """Gecikme tespiti yapar.

        Args:
            eta_id: ETA kimliği.
            elapsed_min: Geçen süre.
            progress_pct: İlerleme yüzdesi.

        Returns:
            Tespit bilgisi.
        """
        est = self._estimates.get(eta_id)
        if not est:
            return {
                "eta_id": eta_id,
                "found": False,
            }

        if progress_pct <= 0:
            progress_pct = 1.0

        expected_min = (
            elapsed_min
            / (progress_pct / 100)
        )
        delay_min = (
            expected_min
            - est["adjusted_min"]
        )

        delayed = delay_min > 5

        if delayed:
            self._stats[
                "delays_detected"
            ] += 1

        return {
            "eta_id": eta_id,
            "expected_total_min": round(
                expected_min, 1,
            ),
            "original_eta_min": est[
                "adjusted_min"
            ],
            "delay_min": round(
                max(delay_min, 0), 1,
            ),
            "delayed": delayed,
            "detected": True,
        }

    @property
    def estimate_count(self) -> int:
        """Tahmin sayısı."""
        return self._stats[
            "estimates_made"
        ]

    @property
    def delay_count(self) -> int:
        """Gecikme sayısı."""
        return self._stats[
            "delays_detected"
        ]
