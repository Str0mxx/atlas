"""ATLAS Onleyici Bakim modulu.

Zamanlanmis bakim, temizlik rutinleri,
optimizasyon calismalari, saglik trend
analizi ve ongorusel bakim.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.diagnostic import MaintenanceType

logger = logging.getLogger(__name__)


class PreventiveCare:
    """Onleyici bakim.

    Sistem sagligini korumak icin
    periyodik bakim islemleri yonetir.

    Attributes:
        _schedules: Bakim zamanlari.
        _runs: Calistirma kayitlari.
        _health_trend: Saglik trendi.
        _cleanups: Temizlik kayitlari.
        _optimizations: Optimizasyon kayitlari.
    """

    def __init__(self) -> None:
        """Onleyici bakimi baslatir."""
        self._schedules: list[dict[str, Any]] = []
        self._runs: list[dict[str, Any]] = []
        self._health_trend: list[dict[str, Any]] = []
        self._cleanups: list[dict[str, Any]] = []
        self._optimizations: list[dict[str, Any]] = []

        logger.info("PreventiveCare baslatildi")

    def schedule_maintenance(
        self,
        name: str,
        maintenance_type: MaintenanceType,
        interval_hours: int = 24,
        description: str = "",
    ) -> dict[str, Any]:
        """Bakim zamanlar.

        Args:
            name: Bakim adi.
            maintenance_type: Bakim turu.
            interval_hours: Aralik (saat).
            description: Aciklama.

        Returns:
            Zamanlama bilgisi.
        """
        schedule = {
            "name": name,
            "type": maintenance_type.value,
            "interval_hours": interval_hours,
            "description": description,
            "enabled": True,
            "last_run": None,
            "run_count": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._schedules.append(schedule)

        logger.info(
            "Bakim zamanlandi: %s (her %d saat)",
            name, interval_hours,
        )
        return schedule

    def run_cleanup(
        self,
        target: str,
        items_cleaned: int = 0,
        space_freed_mb: float = 0.0,
    ) -> dict[str, Any]:
        """Temizlik calistirir.

        Args:
            target: Hedef.
            items_cleaned: Temizlenen oge sayisi.
            space_freed_mb: Serbest birakilan alan (MB).

        Returns:
            Temizlik kaydi.
        """
        cleanup = {
            "target": target,
            "items_cleaned": items_cleaned,
            "space_freed_mb": space_freed_mb,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._cleanups.append(cleanup)
        self._record_run("cleanup", target)

        logger.info(
            "Temizlik: %s (%d oge, %.1f MB)",
            target, items_cleaned, space_freed_mb,
        )
        return cleanup

    def run_optimization(
        self,
        target: str,
        improvement_percent: float = 0.0,
        description: str = "",
    ) -> dict[str, Any]:
        """Optimizasyon calistirir.

        Args:
            target: Hedef.
            improvement_percent: Iyilestirme %.
            description: Aciklama.

        Returns:
            Optimizasyon kaydi.
        """
        optimization = {
            "target": target,
            "improvement_percent": improvement_percent,
            "description": description,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._optimizations.append(optimization)
        self._record_run("optimization", target)

        return optimization

    def record_health(
        self,
        score: float,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Saglik puani kaydeder.

        Args:
            score: Saglik puani (0-1).
            details: Detaylar.
        """
        self._health_trend.append({
            "score": max(0.0, min(1.0, score)),
            "details": details or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def analyze_trend(self) -> dict[str, Any]:
        """Saglik trend analizi yapar.

        Returns:
            Trend analizi.
        """
        if len(self._health_trend) < 2:
            return {
                "trend": "insufficient_data",
                "data_points": len(self._health_trend),
            }

        scores = [h["score"] for h in self._health_trend]
        avg = sum(scores) / len(scores)
        recent = scores[-min(5, len(scores)):]
        recent_avg = sum(recent) / len(recent)

        if recent_avg > avg + 0.05:
            trend = "improving"
        elif recent_avg < avg - 0.05:
            trend = "declining"
        else:
            trend = "stable"

        return {
            "trend": trend,
            "overall_avg": round(avg, 3),
            "recent_avg": round(recent_avg, 3),
            "data_points": len(scores),
            "min": round(min(scores), 3),
            "max": round(max(scores), 3),
        }

    def predict_maintenance(self) -> list[dict[str, Any]]:
        """Ongorusel bakim onerileri verir.

        Returns:
            Oneri listesi.
        """
        predictions: list[dict[str, Any]] = []
        trend = self.analyze_trend()

        if trend["trend"] == "declining":
            predictions.append({
                "type": "health_declining",
                "urgency": "high",
                "recommendation": "Acil saglik kontrolu gerekli",
                "recent_avg": trend.get("recent_avg", 0),
            })

        # Uzun suredir calistirilmayan bakimlar
        for schedule in self._schedules:
            if not schedule["enabled"]:
                continue
            if schedule["run_count"] == 0:
                predictions.append({
                    "type": "never_run",
                    "urgency": "medium",
                    "recommendation": f"{schedule['name']} hic calistirilmamis",
                    "maintenance": schedule["name"],
                })

        # Temizlik onerisi
        if len(self._cleanups) == 0:
            predictions.append({
                "type": "no_cleanup",
                "urgency": "low",
                "recommendation": "Temizlik yapilmasi oneriliyor",
            })

        return predictions

    def get_due_maintenance(self) -> list[dict[str, Any]]:
        """Zamanı gelen bakimlari getirir.

        Returns:
            Bakim listesi.
        """
        now = datetime.now(timezone.utc)
        due: list[dict[str, Any]] = []

        for schedule in self._schedules:
            if not schedule["enabled"]:
                continue

            if schedule["last_run"] is None:
                due.append(schedule)
                continue

            last = datetime.fromisoformat(schedule["last_run"])
            hours_since = (now - last).total_seconds() / 3600
            if hours_since >= schedule["interval_hours"]:
                due.append(schedule)

        return due

    def disable_schedule(self, name: str) -> bool:
        """Zamanlama devre disi birakir.

        Args:
            name: Bakim adi.

        Returns:
            Basarili ise True.
        """
        for schedule in self._schedules:
            if schedule["name"] == name:
                schedule["enabled"] = False
                return True
        return False

    def enable_schedule(self, name: str) -> bool:
        """Zamanlama etkinlestirir.

        Args:
            name: Bakim adi.

        Returns:
            Basarili ise True.
        """
        for schedule in self._schedules:
            if schedule["name"] == name:
                schedule["enabled"] = True
                return True
        return False

    def _record_run(self, run_type: str, target: str) -> None:
        """Calistirma kaydeder.

        Args:
            run_type: Calistirma turu.
            target: Hedef.
        """
        run = {
            "type": run_type,
            "target": target,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._runs.append(run)

        # Zamanlama guncelle
        for schedule in self._schedules:
            if schedule["name"] == target:
                schedule["last_run"] = run["timestamp"]
                schedule["run_count"] += 1
                break

    @property
    def schedule_count(self) -> int:
        """Zamanlama sayisi."""
        return len(self._schedules)

    @property
    def run_count(self) -> int:
        """Calistirma sayisi."""
        return len(self._runs)

    @property
    def cleanup_count(self) -> int:
        """Temizlik sayisi."""
        return len(self._cleanups)

    @property
    def optimization_count(self) -> int:
        """Optimizasyon sayisi."""
        return len(self._optimizations)

    @property
    def health_data_points(self) -> int:
        """Saglik veri noktasi sayisi."""
        return len(self._health_trend)
