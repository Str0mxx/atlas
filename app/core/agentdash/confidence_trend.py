"""
Guven trendi modulu.

Guven takibi, kalibrasyon analizi,
asiri/dusuk guven, trend gorsellestirme,
uyarilar.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class ConfidenceTrend:
    """Guven trendi.

    Attributes:
        _records: Guven kayitlari.
        _stats: Istatistikler.
    """

    def __init__(self) -> None:
        """Trendi baslatir."""
        self._records: list[dict] = []
        self._stats: dict[str, int] = {
            "records_added": 0,
            "alerts_triggered": 0,
        }
        logger.info(
            "ConfidenceTrend baslatildi"
        )

    @property
    def record_count(self) -> int:
        """Kayit sayisi."""
        return len(self._records)

    def record_confidence(
        self,
        agent_id: str = "",
        predicted_confidence: float = 0.0,
        actual_outcome: bool = True,
        task_type: str = "general",
        period: str = "",
    ) -> dict[str, Any]:
        """Guven kaydeder.

        Args:
            agent_id: Agent ID.
            predicted_confidence: Tahmin guveni.
            actual_outcome: Gercek sonuc.
            task_type: Gorev turu.
            period: Donem.

        Returns:
            Kayit bilgisi.
        """
        try:
            cid = f"cf_{uuid4()!s:.8}"
            record = {
                "confidence_id": cid,
                "agent_id": agent_id,
                "predicted_confidence": (
                    predicted_confidence
                ),
                "actual_outcome": actual_outcome,
                "task_type": task_type,
                "period": period,
                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._records.append(record)
            self._stats["records_added"] += 1

            return {
                "confidence_id": cid,
                "agent_id": agent_id,
                "predicted_confidence": (
                    predicted_confidence
                ),
                "recorded": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "recorded": False,
                "error": str(e),
            }

    def get_calibration(
        self,
        agent_id: str = "",
    ) -> dict[str, Any]:
        """Kalibrasyon analizi yapar.

        Args:
            agent_id: Agent ID.

        Returns:
            Kalibrasyon bilgisi.
        """
        try:
            records = [
                r
                for r in self._records
                if not agent_id
                or r["agent_id"] == agent_id
            ]

            if not records:
                return {
                    "calibration_score": 0.0,
                    "analyzed": True,
                }

            buckets: dict[
                str, dict[str, Any]
            ] = {}
            for r in records:
                conf = r[
                    "predicted_confidence"
                ]
                bucket = (
                    f"{int(conf // 10) * 10}"
                    f"-"
                    f"{int(conf // 10) * 10 + 10}"
                )
                if bucket not in buckets:
                    buckets[bucket] = {
                        "total": 0,
                        "successes": 0,
                        "conf_sum": 0.0,
                    }
                buckets[bucket]["total"] += 1
                if r["actual_outcome"]:
                    buckets[bucket][
                        "successes"
                    ] += 1
                buckets[bucket][
                    "conf_sum"
                ] += conf

            calibration_data = []
            total_error = 0.0
            for bk, data in sorted(
                buckets.items()
            ):
                avg_conf = (
                    data["conf_sum"]
                    / data["total"]
                )
                actual_rate = (
                    data["successes"]
                    / data["total"]
                    * 100
                )
                error = abs(
                    avg_conf - actual_rate
                )
                total_error += error
                calibration_data.append({
                    "bucket": bk,
                    "avg_confidence": round(
                        avg_conf, 1
                    ),
                    "actual_success_rate": round(
                        actual_rate, 1
                    ),
                    "error": round(error, 1),
                    "count": data["total"],
                })

            cal_score = (
                100
                - total_error
                / len(buckets)
                if buckets
                else 0
            )

            return {
                "agent_id": agent_id or "all",
                "calibration_score": round(
                    max(cal_score, 0), 1
                ),
                "buckets": calibration_data,
                "total_records": len(records),
                "analyzed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "analyzed": False,
                "error": str(e),
            }

    def detect_over_under_confidence(
        self,
        agent_id: str = "",
    ) -> dict[str, Any]:
        """Asiri/dusuk guven tespit eder.

        Args:
            agent_id: Agent ID.

        Returns:
            Tespit bilgisi.
        """
        try:
            records = [
                r
                for r in self._records
                if not agent_id
                or r["agent_id"] == agent_id
            ]

            if not records:
                return {
                    "status": "no_data",
                    "detected": True,
                }

            over_confident = sum(
                1
                for r in records
                if r["predicted_confidence"]
                > 80
                and not r["actual_outcome"]
            )
            under_confident = sum(
                1
                for r in records
                if r["predicted_confidence"]
                < 40
                and r["actual_outcome"]
            )

            avg_conf = sum(
                r["predicted_confidence"]
                for r in records
            ) / len(records)
            actual_rate = (
                sum(
                    1
                    for r in records
                    if r["actual_outcome"]
                )
                / len(records)
                * 100
            )

            if avg_conf > actual_rate + 10:
                status = "over_confident"
            elif avg_conf < actual_rate - 10:
                status = "under_confident"
            else:
                status = "well_calibrated"

            return {
                "agent_id": agent_id or "all",
                "status": status,
                "avg_confidence": round(
                    avg_conf, 1
                ),
                "actual_success_rate": round(
                    actual_rate, 1
                ),
                "over_confident_count": (
                    over_confident
                ),
                "under_confident_count": (
                    under_confident
                ),
                "total_records": len(records),
                "detected": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "detected": False,
                "error": str(e),
            }

    def get_trend(
        self,
        agent_id: str = "",
    ) -> dict[str, Any]:
        """Guven trendi getirir.

        Args:
            agent_id: Agent ID.

        Returns:
            Trend bilgisi.
        """
        try:
            records = [
                r
                for r in self._records
                if not agent_id
                or r["agent_id"] == agent_id
            ]

            periods: dict[
                str, list[float]
            ] = {}
            for r in records:
                p = r.get("period") or "unknown"
                if p not in periods:
                    periods[p] = []
                periods[p].append(
                    r["predicted_confidence"]
                )

            trend_data = [
                {
                    "period": p,
                    "avg_confidence": round(
                        sum(vals)
                        / len(vals),
                        1,
                    ),
                    "count": len(vals),
                }
                for p, vals in sorted(
                    periods.items()
                )
            ]

            if len(trend_data) < 2:
                direction = (
                    "insufficient_data"
                )
            else:
                first = trend_data[0][
                    "avg_confidence"
                ]
                last = trend_data[-1][
                    "avg_confidence"
                ]
                diff = last - first
                if diff > 5:
                    direction = "increasing"
                elif diff < -5:
                    direction = "decreasing"
                else:
                    direction = "stable"

            return {
                "agent_id": agent_id or "all",
                "trend_data": trend_data,
                "direction": direction,
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def check_alerts(
        self,
        low_threshold: float = 30.0,
        high_threshold: float = 95.0,
    ) -> dict[str, Any]:
        """Uyarilari kontrol eder.

        Args:
            low_threshold: Dusuk esik.
            high_threshold: Yuksek esik.

        Returns:
            Uyari bilgisi.
        """
        try:
            agents: dict[
                str, list[dict]
            ] = {}
            for r in self._records:
                aid = r["agent_id"]
                if aid not in agents:
                    agents[aid] = []
                agents[aid].append(r)

            alerts = []
            for aid, recs in agents.items():
                recent = recs[-5:]
                avg_conf = sum(
                    r["predicted_confidence"]
                    for r in recent
                ) / len(recent)

                if avg_conf < low_threshold:
                    alerts.append({
                        "agent_id": aid,
                        "alert_type": (
                            "low_confidence"
                        ),
                        "avg_confidence": round(
                            avg_conf, 1
                        ),
                        "severity": "warning",
                    })
                elif avg_conf > high_threshold:
                    actual_ok = sum(
                        1
                        for r in recent
                        if r["actual_outcome"]
                    )
                    if (
                        actual_ok
                        < len(recent) * 0.7
                    ):
                        alerts.append({
                            "agent_id": aid,
                            "alert_type": (
                                "over_confident"
                            ),
                            "avg_confidence": (
                                round(
                                    avg_conf, 1
                                )
                            ),
                            "severity": (
                                "warning"
                            ),
                        })

            self._stats[
                "alerts_triggered"
            ] += len(alerts)

            return {
                "alerts": alerts,
                "alert_count": len(alerts),
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }
