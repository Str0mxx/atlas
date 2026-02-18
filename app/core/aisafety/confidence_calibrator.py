"""
AI guven kalibratoru modulu.

Guven kalibrasyonu, asiri guven tespiti,
dusuk guven tespiti, Brier puani,
kalibrasyon egrileri.
"""

import logging
import math
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class AIConfidenceCalibrator:
    """AI guven kalibratoru.

    Attributes:
        _predictions: Tahminler.
        _calibrations: Kalibrasyonlar.
        _stats: Istatistikler.
    """

    CALIBRATION_STATES: list[str] = [
        "well_calibrated",
        "overconfident",
        "underconfident",
        "uncalibrated",
    ]

    def __init__(
        self,
        num_bins: int = 10,
        overconfidence_threshold: float = 0.15,
    ) -> None:
        """Kalibratoru baslatir.

        Args:
            num_bins: Bin sayisi.
            overconfidence_threshold: Esik.
        """
        self._num_bins = num_bins
        self._overconfidence_threshold = (
            overconfidence_threshold
        )
        self._predictions: list[dict] = []
        self._calibrations: dict[
            str, dict
        ] = {}
        self._stats: dict[str, int] = {
            "predictions_recorded": 0,
            "calibrations_done": 0,
            "overconfident_found": 0,
            "underconfident_found": 0,
        }
        logger.info(
            "AIConfidenceCalibrator "
            "baslatildi"
        )

    @property
    def prediction_count(self) -> int:
        """Tahmin sayisi."""
        return len(self._predictions)

    def record_prediction(
        self,
        predicted_confidence: float = 0.5,
        actual_outcome: bool = True,
        category: str = "",
        metadata: dict | None = None,
    ) -> dict[str, Any]:
        """Tahmin kaydeder.

        Args:
            predicted_confidence: Guven.
            actual_outcome: Gercek sonuc.
            category: Kategori.
            metadata: Ek veri.

        Returns:
            Kayit bilgisi.
        """
        try:
            pid = f"pred_{uuid4()!s:.8}"
            conf = max(
                0.0,
                min(
                    1.0,
                    predicted_confidence,
                ),
            )

            self._predictions.append({
                "prediction_id": pid,
                "confidence": conf,
                "outcome": actual_outcome,
                "category": category,
                "metadata": metadata or {},
                "recorded_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            })

            self._stats[
                "predictions_recorded"
            ] += 1

            return {
                "prediction_id": pid,
                "recorded": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "recorded": False,
                "error": str(e),
            }

    def calculate_brier_score(
        self,
        category: str = "",
    ) -> dict[str, Any]:
        """Brier puani hesaplar.

        Args:
            category: Filtre kategorisi.

        Returns:
            Brier puan bilgisi.
        """
        try:
            preds = self._predictions
            if category:
                preds = [
                    p
                    for p in preds
                    if p["category"]
                    == category
                ]

            if not preds:
                return {
                    "brier_score": None,
                    "count": 0,
                    "calculated": True,
                }

            total = sum(
                (
                    p["confidence"]
                    - (
                        1.0
                        if p["outcome"]
                        else 0.0
                    )
                )
                ** 2
                for p in preds
            )
            brier = total / len(preds)

            # Brier 0=mukemmel, 1=en kotu
            quality = (
                "excellent"
                if brier < 0.1
                else (
                    "good"
                    if brier < 0.2
                    else (
                        "fair"
                        if brier < 0.3
                        else "poor"
                    )
                )
            )

            return {
                "brier_score": round(
                    brier, 6
                ),
                "quality": quality,
                "count": len(preds),
                "calculated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "calculated": False,
                "error": str(e),
            }

    def build_calibration_curve(
        self,
        category: str = "",
    ) -> dict[str, Any]:
        """Kalibrasyon egrisi olusturur.

        Args:
            category: Filtre kategorisi.

        Returns:
            Egri bilgisi.
        """
        try:
            cid = f"cal_{uuid4()!s:.8}"

            preds = self._predictions
            if category:
                preds = [
                    p
                    for p in preds
                    if p["category"]
                    == category
                ]

            if not preds:
                return {
                    "calibration_id": cid,
                    "bins": [],
                    "count": 0,
                    "calibrated": True,
                }

            # Binlere ayir
            bins: list[dict] = []
            bin_size = 1.0 / self._num_bins

            for i in range(self._num_bins):
                lo = i * bin_size
                hi = (i + 1) * bin_size

                in_bin = [
                    p
                    for p in preds
                    if lo <= p["confidence"]
                    < hi
                    or (
                        i
                        == self._num_bins - 1
                        and p["confidence"]
                        == hi
                    )
                ]

                if in_bin:
                    avg_conf = sum(
                        p["confidence"]
                        for p in in_bin
                    ) / len(in_bin)
                    avg_outcome = sum(
                        1
                        for p in in_bin
                        if p["outcome"]
                    ) / len(in_bin)
                    gap = (
                        avg_conf
                        - avg_outcome
                    )
                else:
                    avg_conf = (lo + hi) / 2
                    avg_outcome = 0.0
                    gap = 0.0

                bins.append({
                    "bin_start": round(
                        lo, 2
                    ),
                    "bin_end": round(
                        hi, 2
                    ),
                    "count": len(in_bin),
                    "avg_confidence": round(
                        avg_conf, 4
                    ),
                    "avg_outcome": round(
                        avg_outcome, 4
                    ),
                    "gap": round(gap, 4),
                })

            # ECE hesapla
            total = len(preds)
            ece = sum(
                (b["count"] / total)
                * abs(b["gap"])
                for b in bins
                if b["count"] > 0
            )

            state = (
                self._get_calibration_state(
                    ece, bins
                )
            )

            self._calibrations[cid] = {
                "calibration_id": cid,
                "bins": bins,
                "ece": round(ece, 6),
                "state": state,
                "total_predictions": total,
                "calibrated_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }

            self._stats[
                "calibrations_done"
            ] += 1

            return {
                "calibration_id": cid,
                "bins": bins,
                "ece": round(ece, 6),
                "state": state,
                "count": total,
                "calibrated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "calibrated": False,
                "error": str(e),
            }

    def _get_calibration_state(
        self,
        ece: float,
        bins: list[dict],
    ) -> str:
        """Kalibrasyon durumu belirler."""
        if ece < 0.05:
            return "well_calibrated"

        # Yuksek guvenli binlerde
        # sonuc dusukse overconfident
        over_count = sum(
            1
            for b in bins
            if (
                b["count"] > 0
                and b["gap"]
                > self._overconfidence_threshold
            )
        )
        under_count = sum(
            1
            for b in bins
            if (
                b["count"] > 0
                and b["gap"]
                < -self._overconfidence_threshold
            )
        )

        if over_count > under_count:
            self._stats[
                "overconfident_found"
            ] += 1
            return "overconfident"
        if under_count > over_count:
            self._stats[
                "underconfident_found"
            ] += 1
            return "underconfident"
        return "uncalibrated"

    def detect_overconfidence(
        self,
        min_predictions: int = 10,
    ) -> dict[str, Any]:
        """Asiri guven tespiti.

        Args:
            min_predictions: Min tahmin.

        Returns:
            Tespit bilgisi.
        """
        try:
            if (
                len(self._predictions)
                < min_predictions
            ):
                return {
                    "detected": False,
                    "reason": (
                        "Yetersiz tahmin"
                    ),
                    "checked": True,
                }

            # Yuksek guvenli ama yanlis
            high_conf = [
                p
                for p in self._predictions
                if p["confidence"] >= 0.8
            ]
            if not high_conf:
                return {
                    "detected": False,
                    "high_conf_count": 0,
                    "checked": True,
                }

            wrong = [
                p
                for p in high_conf
                if not p["outcome"]
            ]
            error_rate = len(wrong) / len(
                high_conf
            )

            is_overconfident = (
                error_rate
                > self._overconfidence_threshold
            )

            return {
                "detected": (
                    is_overconfident
                ),
                "high_conf_count": len(
                    high_conf
                ),
                "error_rate": round(
                    error_rate, 4
                ),
                "wrong_count": len(wrong),
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }

    def detect_underconfidence(
        self,
        min_predictions: int = 10,
    ) -> dict[str, Any]:
        """Dusuk guven tespiti.

        Args:
            min_predictions: Min tahmin.

        Returns:
            Tespit bilgisi.
        """
        try:
            if (
                len(self._predictions)
                < min_predictions
            ):
                return {
                    "detected": False,
                    "reason": (
                        "Yetersiz tahmin"
                    ),
                    "checked": True,
                }

            # Dusuk guvenli ama dogru
            low_conf = [
                p
                for p in self._predictions
                if p["confidence"] <= 0.4
            ]
            if not low_conf:
                return {
                    "detected": False,
                    "low_conf_count": 0,
                    "checked": True,
                }

            correct = [
                p
                for p in low_conf
                if p["outcome"]
            ]
            success_rate = len(
                correct
            ) / len(low_conf)

            is_underconfident = (
                success_rate > 0.7
            )

            return {
                "detected": (
                    is_underconfident
                ),
                "low_conf_count": len(
                    low_conf
                ),
                "success_rate": round(
                    success_rate, 4
                ),
                "correct_count": len(
                    correct
                ),
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }

    def adjust_confidence(
        self,
        raw_confidence: float = 0.5,
    ) -> dict[str, Any]:
        """Guven degerini ayarlar.

        Args:
            raw_confidence: Ham guven.

        Returns:
            Ayarlanmis guven bilgisi.
        """
        try:
            if not self._predictions:
                return {
                    "adjusted": (
                        raw_confidence
                    ),
                    "adjustment": 0.0,
                    "method": "no_data",
                    "calibrated": True,
                }

            # Ortalama sapma hesapla
            gaps: list[float] = []
            for p in self._predictions:
                outcome_val = (
                    1.0
                    if p["outcome"]
                    else 0.0
                )
                gaps.append(
                    p["confidence"]
                    - outcome_val
                )

            avg_gap = sum(gaps) / len(gaps)
            adjusted = max(
                0.0,
                min(
                    1.0,
                    raw_confidence
                    - avg_gap * 0.5,
                ),
            )

            return {
                "raw": raw_confidence,
                "adjusted": round(
                    adjusted, 4
                ),
                "adjustment": round(
                    adjusted
                    - raw_confidence,
                    4,
                ),
                "avg_gap": round(
                    avg_gap, 4
                ),
                "method": "gap_correction",
                "calibrated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "calibrated": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir."""
        try:
            return {
                "total_predictions": len(
                    self._predictions
                ),
                "total_calibrations": len(
                    self._calibrations
                ),
                "stats": dict(self._stats),
                "retrieved": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
