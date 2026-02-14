"""ATLAS Yansima Modulu.

Oz-degerlendirme, performans analizi,
onyargi tespiti, iyilestirme belirleme
ve ogrenme pekistirme.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.unified import ReflectionRecord, ReflectionType

logger = logging.getLogger(__name__)


class ReflectionModule:
    """Yansima modulu.

    Sistemin kendi performansini
    degerlendirir ve iyilestirir.

    Attributes:
        _records: Yansima kayitlari.
        _metrics: Performans metrikleri.
        _biases: Tespit edilen onyargilar.
        _improvements: Iyilestirme onerileri.
        _consolidations: Pekistirme kayitlari.
    """

    def __init__(self) -> None:
        """Yansima modulunu baslatir."""
        self._records: dict[str, ReflectionRecord] = {}
        self._metrics: dict[str, list[float]] = {}
        self._biases: list[dict[str, Any]] = []
        self._improvements: list[dict[str, Any]] = []
        self._consolidations: list[dict[str, Any]] = []

        logger.info("ReflectionModule baslatildi")

    def self_evaluate(
        self,
        subject: str,
        criteria: dict[str, float] | None = None,
    ) -> ReflectionRecord:
        """Oz-degerlendirme yapar.

        Args:
            subject: Degerlendirme konusu.
            criteria: Kriter -> puan eslesmesi.

        Returns:
            ReflectionRecord nesnesi.
        """
        effective_criteria = criteria or {}
        findings = []
        total_score = 0.0

        for criterion, score in effective_criteria.items():
            clamped = max(0.0, min(1.0, score))
            total_score += clamped
            if clamped >= 0.7:
                findings.append(f"{criterion}: iyi ({clamped:.1f})")
            elif clamped >= 0.4:
                findings.append(f"{criterion}: orta ({clamped:.1f})")
            else:
                findings.append(f"{criterion}: zayif ({clamped:.1f})")

        avg_score = (
            total_score / len(effective_criteria)
            if effective_criteria else 0.5
        )

        record = ReflectionRecord(
            reflection_type=ReflectionType.SELF_EVALUATION,
            subject=subject,
            findings=findings,
            score=round(avg_score, 3),
        )
        self._records[record.record_id] = record

        logger.info(
            "Oz-degerlendirme: %s (skor=%.2f)",
            subject, avg_score,
        )
        return record

    def analyze_performance(
        self,
        metric_name: str,
        values: list[float],
    ) -> ReflectionRecord:
        """Performans analizi yapar.

        Args:
            metric_name: Metrik adi.
            values: Degerler.

        Returns:
            ReflectionRecord nesnesi.
        """
        self._metrics.setdefault(metric_name, []).extend(values)

        findings = []
        improvements = []

        if values:
            avg = sum(values) / len(values)
            trend = "stabil"
            if len(values) >= 2:
                if values[-1] > values[0]:
                    trend = "yukselis"
                elif values[-1] < values[0]:
                    trend = "dusus"

            findings.append(f"Ortalama: {avg:.3f}")
            findings.append(f"Trend: {trend}")
            findings.append(f"Min: {min(values):.3f}, Max: {max(values):.3f}")

            if trend == "dusus":
                improvements.append(
                    f"{metric_name} dususu arastirilmali",
                )

            score = round(avg, 3) if 0 <= avg <= 1 else 0.5
        else:
            score = 0.5

        record = ReflectionRecord(
            reflection_type=ReflectionType.PERFORMANCE,
            subject=metric_name,
            findings=findings,
            improvements=improvements,
            score=score,
        )
        self._records[record.record_id] = record

        return record

    def detect_bias(
        self,
        context: str,
        observation: str,
        bias_type: str = "unknown",
        severity: float = 0.5,
    ) -> ReflectionRecord:
        """Onyargi tespit eder.

        Args:
            context: Baglam.
            observation: Gozlem.
            bias_type: Onyargi turu.
            severity: Ciddiyet (0-1).

        Returns:
            ReflectionRecord nesnesi.
        """
        bias = {
            "context": context,
            "observation": observation,
            "type": bias_type,
            "severity": max(0.0, min(1.0, severity)),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._biases.append(bias)

        record = ReflectionRecord(
            reflection_type=ReflectionType.BIAS_CHECK,
            subject=context,
            findings=[
                f"Onyargi turu: {bias_type}",
                f"Gozlem: {observation}",
                f"Ciddiyet: {severity:.1f}",
            ],
            score=round(1.0 - severity, 3),
        )
        self._records[record.record_id] = record

        logger.info("Onyargi tespit edildi: %s (%s)", context, bias_type)
        return record

    def identify_improvement(
        self,
        area: str,
        current_state: str,
        desired_state: str,
        priority: str = "medium",
        actions: list[str] | None = None,
    ) -> ReflectionRecord:
        """Iyilestirme firsati belirler.

        Args:
            area: Alan.
            current_state: Mevcut durum.
            desired_state: Hedeflenen durum.
            priority: Oncelik.
            actions: Aksiyon maddeleri.

        Returns:
            ReflectionRecord nesnesi.
        """
        improvement = {
            "area": area,
            "current": current_state,
            "desired": desired_state,
            "priority": priority,
            "actions": actions or [],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._improvements.append(improvement)

        record = ReflectionRecord(
            reflection_type=ReflectionType.IMPROVEMENT,
            subject=area,
            findings=[
                f"Mevcut: {current_state}",
                f"Hedef: {desired_state}",
            ],
            improvements=actions or [],
            score=0.5,
        )
        self._records[record.record_id] = record

        return record

    def consolidate_learning(
        self,
        topic: str,
        key_insights: list[str],
        confidence: float = 0.5,
    ) -> ReflectionRecord:
        """Ogrenme pekistirir.

        Args:
            topic: Konu.
            key_insights: Anahtar icegorular.
            confidence: Guven puani.

        Returns:
            ReflectionRecord nesnesi.
        """
        consolidation = {
            "topic": topic,
            "insights": key_insights,
            "confidence": max(0.0, min(1.0, confidence)),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._consolidations.append(consolidation)

        record = ReflectionRecord(
            reflection_type=ReflectionType.CONSOLIDATION,
            subject=topic,
            findings=key_insights,
            score=round(confidence, 3),
        )
        self._records[record.record_id] = record

        return record

    def get_record(
        self,
        record_id: str,
    ) -> ReflectionRecord | None:
        """Kayit getirir.

        Args:
            record_id: Kayit ID.

        Returns:
            ReflectionRecord veya None.
        """
        return self._records.get(record_id)

    def get_by_type(
        self,
        reflection_type: ReflectionType,
    ) -> list[ReflectionRecord]:
        """Ture gore kayitlari getirir.

        Args:
            reflection_type: Yansima turu.

        Returns:
            Kayit listesi.
        """
        return [
            r for r in self._records.values()
            if r.reflection_type == reflection_type
        ]

    def get_biases(self) -> list[dict[str, Any]]:
        """Onyargilari getirir.

        Returns:
            Onyargi listesi.
        """
        return list(self._biases)

    def get_improvements(
        self,
        priority: str = "",
    ) -> list[dict[str, Any]]:
        """Iyilestirmeleri getirir.

        Args:
            priority: Oncelik filtresi.

        Returns:
            Iyilestirme listesi.
        """
        if priority:
            return [
                i for i in self._improvements
                if i.get("priority") == priority
            ]
        return list(self._improvements)

    def get_overall_score(self) -> float:
        """Genel skoru hesaplar.

        Returns:
            Ortalama skor (0-1).
        """
        if not self._records:
            return 0.5

        total = sum(r.score for r in self._records.values())
        return round(total / len(self._records), 3)

    @property
    def total_records(self) -> int:
        """Toplam kayit sayisi."""
        return len(self._records)

    @property
    def bias_count(self) -> int:
        """Onyargi sayisi."""
        return len(self._biases)

    @property
    def improvement_count(self) -> int:
        """Iyilestirme sayisi."""
        return len(self._improvements)

    @property
    def consolidation_count(self) -> int:
        """Pekistirme sayisi."""
        return len(self._consolidations)
