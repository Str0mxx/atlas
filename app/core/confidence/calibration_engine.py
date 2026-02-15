"""ATLAS Kalibrasyon Motoru modulu.

Guven kalibrasyonu, asiri/eksik guven tespiti,
Brier skoru, guvenilirlik diyagrami, otomatik duzeltme.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class CalibrationEngine:
    """Kalibrasyon motoru.

    Guven puanlarini kalibre eder.

    Attributes:
        _samples: Kalibrasyon ornekleri.
        _corrections: Duzeltme gecmisi.
    """

    def __init__(
        self,
        bins: int = 10,
        recalibration_threshold: float = 0.15,
    ) -> None:
        """Kalibrasyon motorunu baslatir.

        Args:
            bins: Kutu sayisi.
            recalibration_threshold: Yeniden kalibrasyon esigi.
        """
        self._samples: list[
            dict[str, Any]
        ] = []
        self._corrections: list[
            dict[str, Any]
        ] = []
        self._bins = bins
        self._recalibration_threshold = (
            recalibration_threshold
        )
        self._correction_factor = 0.0
        self._stats = {
            "samples": 0,
            "recalibrations": 0,
        }

        logger.info(
            "CalibrationEngine baslatildi",
        )

    def add_sample(
        self,
        confidence: float,
        outcome: bool,
        domain: str = "",
    ) -> dict[str, Any]:
        """Kalibrasyon ornegi ekler.

        Args:
            confidence: Guven puani.
            outcome: Gercek sonuc.
            domain: Alan.

        Returns:
            Kayit bilgisi.
        """
        sample = {
            "confidence": confidence,
            "outcome": outcome,
            "domain": domain,
            "timestamp": time.time(),
        }

        self._samples.append(sample)
        self._stats["samples"] += 1

        return {
            "recorded": True,
            "total_samples": len(self._samples),
        }

    def compute_brier_score(
        self,
    ) -> float:
        """Brier skorunu hesaplar.

        Returns:
            Brier skoru (0=mukemmel, 1=en kotu).
        """
        if not self._samples:
            return 0.0

        brier = sum(
            (s["confidence"] - (1.0 if s["outcome"] else 0.0)) ** 2
            for s in self._samples
        ) / len(self._samples)

        return round(brier, 4)

    def reliability_diagram(
        self,
    ) -> list[dict[str, Any]]:
        """Guvenilirlik diyagrami olusturur.

        Returns:
            Kutu verileri.
        """
        if not self._samples:
            return []

        bins: dict[int, dict[str, Any]] = {}
        for s in self._samples:
            b = min(
                self._bins - 1,
                int(s["confidence"] * self._bins),
            )
            if b not in bins:
                bins[b] = {
                    "total": 0,
                    "positive": 0,
                    "confidence_sum": 0.0,
                }
            bins[b]["total"] += 1
            if s["outcome"]:
                bins[b]["positive"] += 1
            bins[b]["confidence_sum"] += (
                s["confidence"]
            )

        result = []
        for b in sorted(bins.keys()):
            data = bins[b]
            avg_conf = (
                data["confidence_sum"]
                / data["total"]
            )
            actual_rate = (
                data["positive"] / data["total"]
            )
            result.append({
                "bin": b,
                "avg_confidence": round(
                    avg_conf, 4,
                ),
                "actual_rate": round(
                    actual_rate, 4,
                ),
                "count": data["total"],
                "gap": round(
                    avg_conf - actual_rate, 4,
                ),
            })

        return result

    def detect_miscalibration(
        self,
    ) -> dict[str, Any]:
        """Kalibrasyon hatasini tespit eder.

        Returns:
            Tespit bilgisi.
        """
        if len(self._samples) < 20:
            return {
                "status": "insufficient_data",
                "count": len(self._samples),
            }

        diagram = self.reliability_diagram()
        if not diagram:
            return {
                "status": "no_bins",
            }

        # Ortalama gap
        total_gap = sum(
            d["gap"] * d["count"]
            for d in diagram
        )
        total_count = sum(
            d["count"] for d in diagram
        )
        avg_gap = total_gap / total_count

        brier = self.compute_brier_score()

        if abs(avg_gap) < 0.05:
            status = "well_calibrated"
        elif avg_gap > 0:
            status = "overconfident"
        else:
            status = "underconfident"

        needs_recalibration = (
            abs(avg_gap)
            > self._recalibration_threshold
        )

        return {
            "status": status,
            "avg_gap": round(avg_gap, 4),
            "brier_score": brier,
            "needs_recalibration": (
                needs_recalibration
            ),
            "sample_count": len(self._samples),
        }

    def auto_correct(
        self,
    ) -> dict[str, Any]:
        """Otomatik duzeltme uygular.

        Returns:
            Duzeltme bilgisi.
        """
        detection = self.detect_miscalibration()

        if detection.get("status") in (
            "insufficient_data", "no_bins",
        ):
            return {
                "corrected": False,
                "reason": detection["status"],
            }

        if not detection.get(
            "needs_recalibration",
        ):
            return {
                "corrected": False,
                "reason": "calibration_acceptable",
            }

        avg_gap = detection["avg_gap"]
        self._correction_factor = -avg_gap

        correction = {
            "old_factor": round(
                self._correction_factor + avg_gap,
                4,
            ),
            "new_factor": round(
                self._correction_factor, 4,
            ),
            "avg_gap": avg_gap,
            "timestamp": time.time(),
        }
        self._corrections.append(correction)
        self._stats["recalibrations"] += 1

        return {
            "corrected": True,
            "correction_factor": round(
                self._correction_factor, 4,
            ),
            "avg_gap": avg_gap,
        }

    def calibrate_score(
        self,
        raw_score: float,
    ) -> float:
        """Ham puani kalibre eder.

        Args:
            raw_score: Ham puan.

        Returns:
            Kalibre edilmis puan.
        """
        calibrated = (
            raw_score + self._correction_factor
        )
        return round(
            max(0.0, min(1.0, calibrated)), 4,
        )

    def get_correction_history(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Duzeltme gecmisini getirir.

        Args:
            limit: Limit.

        Returns:
            Gecmis kayitlari.
        """
        return list(self._corrections[-limit:])

    @property
    def sample_count(self) -> int:
        """Ornek sayisi."""
        return len(self._samples)

    @property
    def correction_factor(self) -> float:
        """Duzeltme faktoru."""
        return round(self._correction_factor, 4)

    @property
    def brier_score(self) -> float:
        """Brier skoru."""
        return self.compute_brier_score()
