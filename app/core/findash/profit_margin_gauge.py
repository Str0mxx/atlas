"""
Kar marji gostergesi modulu.

Marj hesaplama, gorsel gosterge,
hedef karsilastirma, trend gostergesi,
uyari esikleri.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class ProfitMarginGauge:
    """Kar marji gostergesi.

    Attributes:
        _records: Kar marji kayitlari.
        _targets: Hedefler.
        _stats: Istatistikler.
    """

    def __init__(self) -> None:
        """Gostergeyi baslatir."""
        self._records: list[dict] = []
        self._targets: list[dict] = []
        self._stats: dict[str, int] = {
            "records_added": 0,
            "alerts_triggered": 0,
        }
        logger.info(
            "ProfitMarginGauge baslatildi"
        )

    @property
    def record_count(self) -> int:
        """Kayit sayisi."""
        return len(self._records)

    def record_margin(
        self,
        revenue: float = 0.0,
        cost: float = 0.0,
        period: str = "",
        category: str = "overall",
    ) -> dict[str, Any]:
        """Kar marji kaydeder.

        Args:
            revenue: Gelir.
            cost: Maliyet.
            period: Donem.
            category: Kategori.

        Returns:
            Kayit bilgisi.
        """
        try:
            mid = f"mg_{uuid4()!s:.8}"
            profit = revenue - cost
            margin = (
                (profit / revenue * 100)
                if revenue > 0
                else 0.0
            )

            record = {
                "margin_id": mid,
                "revenue": revenue,
                "cost": cost,
                "profit": round(profit, 2),
                "margin_pct": round(
                    margin, 1
                ),
                "period": period,
                "category": category,
                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._records.append(record)
            self._stats["records_added"] += 1

            return {
                "margin_id": mid,
                "margin_pct": round(
                    margin, 1
                ),
                "profit": round(profit, 2),
                "recorded": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "recorded": False,
                "error": str(e),
            }

    def get_current_margin(
        self,
        category: str = "overall",
    ) -> dict[str, Any]:
        """Mevcut marji getirir.

        Args:
            category: Kategori.

        Returns:
            Marj bilgisi.
        """
        try:
            records = [
                r
                for r in self._records
                if r["category"] == category
            ]

            if not records:
                return {
                    "margin_pct": 0.0,
                    "category": category,
                    "retrieved": True,
                }

            latest = records[-1]

            return {
                "margin_pct": latest[
                    "margin_pct"
                ],
                "revenue": latest["revenue"],
                "cost": latest["cost"],
                "profit": latest["profit"],
                "period": latest["period"],
                "category": category,
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def set_target(
        self,
        category: str = "overall",
        target_pct: float = 20.0,
        min_pct: float = 10.0,
    ) -> dict[str, Any]:
        """Hedef belirler.

        Args:
            category: Kategori.
            target_pct: Hedef yuzde.
            min_pct: Minimum yuzde.

        Returns:
            Hedef bilgisi.
        """
        try:
            tid = f"tg_{uuid4()!s:.8}"
            target = {
                "target_id": tid,
                "category": category,
                "target_pct": target_pct,
                "min_pct": min_pct,
                "created_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._targets.append(target)

            return {
                "target_id": tid,
                "category": category,
                "target_pct": target_pct,
                "set": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "set": False,
                "error": str(e),
            }

    def compare_to_target(
        self,
        category: str = "overall",
    ) -> dict[str, Any]:
        """Hedefle karsilastirir.

        Args:
            category: Kategori.

        Returns:
            Karsilastirma bilgisi.
        """
        try:
            current = self.get_current_margin(
                category=category
            )
            curr_pct = current.get(
                "margin_pct", 0.0
            )

            targets = [
                t
                for t in self._targets
                if t["category"] == category
            ]

            if not targets:
                return {
                    "category": category,
                    "current_margin": curr_pct,
                    "target": None,
                    "compared": True,
                }

            target = targets[-1]
            gap = (
                curr_pct
                - target["target_pct"]
            )

            if curr_pct >= target["target_pct"]:
                status = "above_target"
            elif curr_pct >= target["min_pct"]:
                status = "acceptable"
            else:
                status = "below_minimum"

            return {
                "category": category,
                "current_margin": curr_pct,
                "target_pct": target[
                    "target_pct"
                ],
                "min_pct": target["min_pct"],
                "gap": round(gap, 1),
                "status": status,
                "compared": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "compared": False,
                "error": str(e),
            }

    def get_trend(
        self,
        category: str = "overall",
    ) -> dict[str, Any]:
        """Marj trendi getirir.

        Args:
            category: Kategori.

        Returns:
            Trend bilgisi.
        """
        try:
            records = [
                r
                for r in self._records
                if r["category"] == category
            ]

            if len(records) < 2:
                return {
                    "trend": (
                        "insufficient_data"
                    ),
                    "category": category,
                    "analyzed": True,
                }

            margins = [
                r["margin_pct"]
                for r in records
            ]
            avg_change = (
                margins[-1] - margins[0]
            ) / (len(margins) - 1)

            if avg_change > 1:
                direction = "improving"
            elif avg_change < -1:
                direction = "declining"
            else:
                direction = "stable"

            return {
                "category": category,
                "current_margin": margins[-1],
                "previous_margin": margins[-2],
                "avg_change": round(
                    avg_change, 1
                ),
                "direction": direction,
                "data_points": [
                    {
                        "period": r["period"],
                        "margin": r[
                            "margin_pct"
                        ],
                    }
                    for r in records
                ],
                "analyzed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "analyzed": False,
                "error": str(e),
            }

    def check_alerts(
        self,
        alert_threshold: float = 10.0,
    ) -> dict[str, Any]:
        """Uyarilari kontrol eder.

        Args:
            alert_threshold: Uyari esigi.

        Returns:
            Uyari bilgisi.
        """
        try:
            alerts = []
            categories = set(
                r["category"]
                for r in self._records
            )

            for cat in categories:
                records = [
                    r
                    for r in self._records
                    if r["category"] == cat
                ]
                if not records:
                    continue

                latest = records[-1]
                if (
                    latest["margin_pct"]
                    < alert_threshold
                ):
                    alerts.append({
                        "category": cat,
                        "margin_pct": latest[
                            "margin_pct"
                        ],
                        "threshold": (
                            alert_threshold
                        ),
                        "severity": (
                            "critical"
                            if latest[
                                "margin_pct"
                            ]
                            < 0
                            else "warning"
                        ),
                    })

            self._stats[
                "alerts_triggered"
            ] += len(alerts)

            return {
                "alerts": alerts,
                "alert_count": len(alerts),
                "threshold": alert_threshold,
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }
