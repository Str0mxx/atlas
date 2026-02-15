"""ATLAS SLA Izleyici modulu.

SLI/SLO takibi, hata butceleri,
uyumluluk raporlama, ihlal uyarilari
ve trend analizi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class SLAMonitor:
    """SLA izleyici.

    SLA/SLO/SLI metriklerini izler.

    Attributes:
        _slos: SLO tanimlari.
        _measurements: Olcumler.
    """

    def __init__(self) -> None:
        """SLA izleyiciyi baslatir."""
        self._slos: dict[
            str, dict[str, Any]
        ] = {}
        self._measurements: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._error_budgets: dict[
            str, dict[str, Any]
        ] = {}
        self._breaches: list[
            dict[str, Any]
        ] = []

        logger.info("SLAMonitor baslatildi")

    def define_slo(
        self,
        name: str,
        target: float,
        metric_type: str = "availability",
        window_days: int = 30,
        description: str = "",
    ) -> dict[str, Any]:
        """SLO tanimlar.

        Args:
            name: SLO adi.
            target: Hedef deger (yuzde).
            metric_type: Metrik tipi.
            window_days: Olcum penceresi (gun).
            description: Aciklama.

        Returns:
            SLO bilgisi.
        """
        slo = {
            "name": name,
            "target": target,
            "metric_type": metric_type,
            "window_days": window_days,
            "description": description,
            "created_at": time.time(),
        }
        self._slos[name] = slo
        self._measurements[name] = []

        # Hata butcesi hesapla
        error_budget = 100.0 - target
        self._error_budgets[name] = {
            "total": error_budget,
            "remaining": error_budget,
            "consumed": 0.0,
        }

        return {
            "name": name,
            "target": target,
            "error_budget": error_budget,
        }

    def remove_slo(
        self,
        name: str,
    ) -> bool:
        """SLO kaldirir.

        Args:
            name: SLO adi.

        Returns:
            Basarili mi.
        """
        if name in self._slos:
            del self._slos[name]
            self._measurements.pop(name, None)
            self._error_budgets.pop(name, None)
            return True
        return False

    def record_measurement(
        self,
        slo_name: str,
        value: float,
        success: bool = True,
    ) -> dict[str, Any]:
        """Olcum kaydeder.

        Args:
            slo_name: SLO adi.
            value: Olcum degeri.
            success: Basarili mi.

        Returns:
            Olcum sonucu.
        """
        if slo_name not in self._slos:
            return {
                "status": "error",
                "reason": "slo_not_found",
            }

        measurement = {
            "value": value,
            "success": success,
            "timestamp": time.time(),
        }
        self._measurements[slo_name].append(
            measurement,
        )

        # Hata butcesi guncelle
        if not success:
            budget = self._error_budgets.get(
                slo_name,
            )
            if budget:
                budget["consumed"] += 1
                budget["remaining"] = max(
                    0,
                    budget["total"]
                    - budget["consumed"],
                )

        # Ihlal kontrol
        compliance = self._calculate_compliance(
            slo_name,
        )
        slo = self._slos[slo_name]
        if compliance < slo["target"]:
            breach = {
                "slo": slo_name,
                "target": slo["target"],
                "actual": compliance,
                "gap": slo["target"] - compliance,
                "timestamp": time.time(),
            }
            self._breaches.append(breach)
            return {
                "status": "breach",
                "compliance": round(compliance, 2),
            }

        return {
            "status": "ok",
            "compliance": round(compliance, 2),
        }

    def _calculate_compliance(
        self,
        slo_name: str,
    ) -> float:
        """Uyumluluk hesaplar.

        Args:
            slo_name: SLO adi.

        Returns:
            Uyumluluk yuzdesi.
        """
        measurements = self._measurements.get(
            slo_name, [],
        )
        if not measurements:
            return 100.0

        success_count = sum(
            1 for m in measurements
            if m["success"]
        )
        return (
            success_count / len(measurements)
        ) * 100.0

    def get_compliance(
        self,
        slo_name: str,
    ) -> dict[str, Any]:
        """Uyumluluk raporu getirir.

        Args:
            slo_name: SLO adi.

        Returns:
            Uyumluluk bilgisi.
        """
        slo = self._slos.get(slo_name)
        if not slo:
            return {
                "status": "error",
                "reason": "not_found",
            }

        compliance = self._calculate_compliance(
            slo_name,
        )
        budget = self._error_budgets.get(
            slo_name, {},
        )
        measurements = self._measurements.get(
            slo_name, [],
        )

        return {
            "slo": slo_name,
            "target": slo["target"],
            "actual": round(compliance, 2),
            "compliant": compliance >= slo["target"],
            "error_budget_remaining": budget.get(
                "remaining", 0,
            ),
            "total_measurements": len(measurements),
        }

    def get_error_budget(
        self,
        slo_name: str,
    ) -> dict[str, Any] | None:
        """Hata butcesi getirir.

        Args:
            slo_name: SLO adi.

        Returns:
            Butce bilgisi veya None.
        """
        return self._error_budgets.get(slo_name)

    def get_breaches(
        self,
        slo_name: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Ihlalleri getirir.

        Args:
            slo_name: Filtre.
            limit: Limit.

        Returns:
            Ihlal listesi.
        """
        breaches = self._breaches
        if slo_name:
            breaches = [
                b for b in breaches
                if b["slo"] == slo_name
            ]
        return breaches[-limit:]

    def get_trend(
        self,
        slo_name: str,
        window: int = 10,
    ) -> dict[str, Any]:
        """Trend analizi yapar.

        Args:
            slo_name: SLO adi.
            window: Pencere boyutu.

        Returns:
            Trend bilgisi.
        """
        measurements = self._measurements.get(
            slo_name, [],
        )
        if len(measurements) < window:
            return {
                "trend": "unknown",
                "reason": "insufficient_data",
            }

        recent = measurements[-window:]
        first_half = recent[:window // 2]
        second_half = recent[window // 2:]

        rate_first = sum(
            1 for m in first_half if m["success"]
        ) / len(first_half) * 100

        rate_second = sum(
            1 for m in second_half if m["success"]
        ) / len(second_half) * 100

        diff = rate_second - rate_first
        if abs(diff) < 1.0:
            trend = "stable"
        elif diff > 0:
            trend = "improving"
        else:
            trend = "degrading"

        return {
            "slo": slo_name,
            "trend": trend,
            "change": round(diff, 2),
            "recent_rate": round(rate_second, 2),
        }

    def generate_report(self) -> dict[str, Any]:
        """Genel rapor olusturur.

        Returns:
            Rapor bilgisi.
        """
        slo_reports = []
        for name in self._slos:
            slo_reports.append(
                self.get_compliance(name),
            )

        compliant = sum(
            1 for r in slo_reports
            if r.get("compliant", False)
        )

        return {
            "total_slos": len(self._slos),
            "compliant": compliant,
            "non_compliant": (
                len(self._slos) - compliant
            ),
            "total_breaches": len(self._breaches),
            "slos": slo_reports,
            "timestamp": time.time(),
        }

    @property
    def slo_count(self) -> int:
        """SLO sayisi."""
        return len(self._slos)

    @property
    def breach_count(self) -> int:
        """Ihlal sayisi."""
        return len(self._breaches)

    @property
    def measurement_count(self) -> int:
        """Toplam olcum sayisi."""
        return sum(
            len(m)
            for m in self._measurements.values()
        )
