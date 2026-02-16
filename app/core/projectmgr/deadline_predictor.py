"""ATLAS Son Tarih Tahmincisi modülü.

Tamamlanma tahmini, risk faktörleri,
geçmiş analiz, tampon hesaplama,
güven puanlama.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class DeadlinePredictor:
    """Son tarih tahmincisi.

    Proje tamamlanma tarihlerini tahmin eder.

    Attributes:
        _predictions: Tahmin kayıtları.
        _history: Geçmiş veriler.
    """

    def __init__(self) -> None:
        """Tahmincisini başlatır."""
        self._predictions: list[
            dict[str, Any]
        ] = []
        self._history: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "predictions_made": 0,
            "risks_assessed": 0,
            "buffers_calculated": 0,
        }

        logger.info(
            "DeadlinePredictor baslatildi",
        )

    def predict_completion(
        self,
        project_id: str,
        progress: float,
        elapsed_days: float,
        remaining_tasks: int = 0,
        velocity: float = 0.0,
    ) -> dict[str, Any]:
        """Tamamlanma tahmin eder.

        Args:
            project_id: Proje ID.
            progress: İlerleme yüzdesi.
            elapsed_days: Geçen gün.
            remaining_tasks: Kalan görev.
            velocity: Hız (görev/gün).

        Returns:
            Tahmin bilgisi.
        """
        self._counter += 1
        pid = f"pred_{self._counter}"

        if progress > 0:
            estimated_total = round(
                elapsed_days
                / (progress / 100), 1,
            )
            remaining_days = round(
                estimated_total
                - elapsed_days, 1,
            )
        elif velocity > 0:
            remaining_days = round(
                remaining_tasks / velocity,
                1,
            )
            estimated_total = round(
                elapsed_days
                + remaining_days, 1,
            )
        else:
            remaining_days = 0.0
            estimated_total = elapsed_days

        confidence = min(
            progress * 0.8 + 20, 95,
        )

        prediction = {
            "prediction_id": pid,
            "project_id": project_id,
            "remaining_days": max(
                remaining_days, 0,
            ),
            "estimated_total": (
                estimated_total
            ),
            "confidence": round(
                confidence, 1,
            ),
            "progress": progress,
            "timestamp": time.time(),
        }
        self._predictions.append(prediction)
        self._stats[
            "predictions_made"
        ] += 1

        return {
            "prediction_id": pid,
            "remaining_days": max(
                remaining_days, 0,
            ),
            "estimated_total_days": (
                estimated_total
            ),
            "confidence": round(
                confidence, 1,
            ),
            "predicted": True,
        }

    def assess_risk_factors(
        self,
        project_id: str,
        factors: dict[str, Any]
        | None = None,
    ) -> dict[str, Any]:
        """Risk faktörlerini değerlendirir.

        Args:
            project_id: Proje ID.
            factors: Faktörler.

        Returns:
            Risk bilgisi.
        """
        factors = factors or {}

        risk_score = 0.0
        risks = []

        if factors.get(
            "scope_creep", False,
        ):
            risk_score += 25
            risks.append("scope_creep")

        if factors.get(
            "resource_shortage", False,
        ):
            risk_score += 20
            risks.append(
                "resource_shortage",
            )

        if factors.get(
            "technical_debt", False,
        ):
            risk_score += 15
            risks.append("technical_debt")

        if factors.get(
            "dependency_delay", False,
        ):
            risk_score += 20
            risks.append(
                "dependency_delay",
            )

        if factors.get(
            "team_turnover", False,
        ):
            risk_score += 20
            risks.append("team_turnover")

        delay_probability = min(
            risk_score, 100,
        )
        level = (
            "low" if risk_score < 25
            else "medium" if risk_score < 50
            else "high"
        )

        self._stats[
            "risks_assessed"
        ] += 1

        return {
            "project_id": project_id,
            "risk_score": round(
                risk_score, 1,
            ),
            "risk_level": level,
            "delay_probability": (
                delay_probability
            ),
            "risks": risks,
            "assessed": True,
        }

    def analyze_historical(
        self,
        project_type: str = "",
    ) -> dict[str, Any]:
        """Geçmiş analiz yapar.

        Args:
            project_type: Proje tipi.

        Returns:
            Analiz bilgisi.
        """
        if not self._history:
            return {
                "avg_delay": 0.0,
                "on_time_rate": 0.0,
                "data_points": 0,
                "analyzed": False,
            }

        records = self._history
        if project_type:
            records = [
                r for r in records
                if r.get("type")
                == project_type
            ]

        delays = [
            r.get("delay_days", 0)
            for r in records
        ]
        on_time = sum(
            1 for d in delays if d <= 0
        )

        return {
            "avg_delay": round(
                sum(delays)
                / max(len(delays), 1), 1,
            ),
            "on_time_rate": round(
                on_time
                / max(len(records), 1)
                * 100, 1,
            ),
            "data_points": len(records),
            "analyzed": True,
        }

    def add_historical(
        self,
        project_type: str,
        planned_days: float,
        actual_days: float,
    ) -> dict[str, Any]:
        """Geçmiş veri ekler.

        Args:
            project_type: Proje tipi.
            planned_days: Planlanan gün.
            actual_days: Gerçek gün.

        Returns:
            Ekleme bilgisi.
        """
        self._history.append({
            "type": project_type,
            "planned_days": planned_days,
            "actual_days": actual_days,
            "delay_days": round(
                actual_days - planned_days,
                1,
            ),
            "timestamp": time.time(),
        })

        return {
            "type": project_type,
            "delay": round(
                actual_days - planned_days,
                1,
            ),
            "added": True,
        }

    def calculate_buffer(
        self,
        estimated_days: float,
        risk_level: str = "medium",
        confidence: float = 80.0,
    ) -> dict[str, Any]:
        """Tampon hesaplar.

        Args:
            estimated_days: Tahmini gün.
            risk_level: Risk seviyesi.
            confidence: Güven yüzdesi.

        Returns:
            Tampon bilgisi.
        """
        # Risk bazlı çarpan
        multiplier = {
            "low": 0.10,
            "medium": 0.20,
            "high": 0.35,
        }.get(risk_level, 0.20)

        # Güven bazlı ayar
        if confidence < 60:
            multiplier *= 1.5
        elif confidence > 90:
            multiplier *= 0.7

        buffer_days = round(
            estimated_days * multiplier, 1,
        )
        total = round(
            estimated_days + buffer_days, 1,
        )

        self._stats[
            "buffers_calculated"
        ] += 1

        return {
            "estimated_days": estimated_days,
            "buffer_days": buffer_days,
            "buffer_percent": round(
                multiplier * 100, 1,
            ),
            "total_days": total,
            "risk_level": risk_level,
        }

    def score_confidence(
        self,
        progress: float,
        data_points: int = 0,
        risk_level: str = "medium",
    ) -> dict[str, Any]:
        """Güven puanlar.

        Args:
            progress: İlerleme.
            data_points: Veri noktası.
            risk_level: Risk seviyesi.

        Returns:
            Güven bilgisi.
        """
        base = min(progress * 0.6, 60)
        data_bonus = min(
            data_points * 5, 25,
        )
        risk_penalty = {
            "low": 0,
            "medium": 5,
            "high": 15,
        }.get(risk_level, 5)

        score = round(
            base + data_bonus
            - risk_penalty, 1,
        )
        score = max(5, min(95, score))

        level = (
            "high" if score >= 75
            else "medium" if score >= 50
            else "low"
        )

        return {
            "confidence_score": score,
            "level": level,
            "factors": {
                "progress_contrib": round(
                    base, 1,
                ),
                "data_contrib": data_bonus,
                "risk_penalty": risk_penalty,
            },
        }

    @property
    def prediction_count(self) -> int:
        """Tahmin sayısı."""
        return self._stats[
            "predictions_made"
        ]

    @property
    def history_count(self) -> int:
        """Geçmiş veri sayısı."""
        return len(self._history)
