"""
API kota takipçisi modülü.

Kota izleme, kullanım takibi,
sıfırlama zamanlaması, aşım uyarıları,
geçmiş kullanım.
"""

import logging
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class APIQuotaTracker:
    """API kota takipçisi.

    Attributes:
        _quotas: Kota kayıtları.
        _usage_history: Kullanım geçmişi.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Takipçiyi başlatır."""
        self._quotas: list[dict] = []
        self._usage_history: list[dict] = []
        self._stats: dict[str, int] = {
            "quotas_registered": 0,
            "overage_alerts": 0,
        }
        logger.info(
            "APIQuotaTracker baslatildi"
        )

    @property
    def quota_count(self) -> int:
        """Kota sayısı."""
        return len(self._quotas)

    def register_quota(
        self,
        api_name: str = "",
        daily_limit: int = 1000,
        monthly_limit: int = 30000,
        cost_per_call: float = 0.0,
    ) -> dict[str, Any]:
        """Kota kaydeder.

        Args:
            api_name: API adı.
            daily_limit: Günlük limit.
            monthly_limit: Aylık limit.
            cost_per_call: Çağrı başı maliyet.

        Returns:
            Kayıt bilgisi.
        """
        try:
            qid = f"qt_{uuid4()!s:.8}"

            record = {
                "quota_id": qid,
                "api_name": api_name,
                "daily_limit": daily_limit,
                "monthly_limit": monthly_limit,
                "daily_used": 0,
                "monthly_used": 0,
                "cost_per_call": cost_per_call,
                "status": "active",
            }
            self._quotas.append(record)
            self._stats[
                "quotas_registered"
            ] += 1

            return {
                "quota_id": qid,
                "api_name": api_name,
                "daily_limit": daily_limit,
                "monthly_limit": monthly_limit,
                "registered": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "registered": False,
                "error": str(e),
            }

    def track_usage(
        self,
        quota_id: str = "",
        calls: int = 1,
    ) -> dict[str, Any]:
        """Kullanım takibi yapar.

        Args:
            quota_id: Kota ID.
            calls: Çağrı sayısı.

        Returns:
            Takip bilgisi.
        """
        try:
            quota = None
            for q in self._quotas:
                if q["quota_id"] == quota_id:
                    quota = q
                    break

            if not quota:
                return {
                    "tracked": False,
                    "error": "quota_not_found",
                }

            quota["daily_used"] += calls
            quota["monthly_used"] += calls

            daily_pct = (
                quota["daily_used"]
                / quota["daily_limit"]
                * 100.0
            ) if quota["daily_limit"] > 0 else 0.0

            monthly_pct = (
                quota["monthly_used"]
                / quota["monthly_limit"]
                * 100.0
            ) if quota["monthly_limit"] > 0 else 0.0

            cost = (
                calls * quota["cost_per_call"]
            )

            overage = (
                daily_pct >= 100
                or monthly_pct >= 100
            )
            if overage:
                self._stats[
                    "overage_alerts"
                ] += 1

            self._usage_history.append({
                "quota_id": quota_id,
                "calls": calls,
                "daily_pct": round(
                    daily_pct, 1
                ),
                "monthly_pct": round(
                    monthly_pct, 1
                ),
            })

            return {
                "quota_id": quota_id,
                "calls_added": calls,
                "daily_used": quota[
                    "daily_used"
                ],
                "daily_remaining": max(
                    0,
                    quota["daily_limit"]
                    - quota["daily_used"],
                ),
                "daily_percent": round(
                    daily_pct, 1
                ),
                "monthly_percent": round(
                    monthly_pct, 1
                ),
                "cost": round(cost, 4),
                "overage": overage,
                "tracked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "tracked": False,
                "error": str(e),
            }

    def check_reset_timing(
        self,
        quota_id: str = "",
        hours_until_daily: int = 12,
        days_until_monthly: int = 15,
    ) -> dict[str, Any]:
        """Sıfırlama zamanlaması kontrol eder.

        Args:
            quota_id: Kota ID.
            hours_until_daily: Günlüğe kalan saat.
            days_until_monthly: Aylığa kalan gün.

        Returns:
            Zamanlama bilgisi.
        """
        try:
            quota = None
            for q in self._quotas:
                if q["quota_id"] == quota_id:
                    quota = q
                    break

            if not quota:
                return {
                    "checked": False,
                    "error": "quota_not_found",
                }

            daily_rate = (
                quota["daily_used"]
                / max(1, 24 - hours_until_daily)
            )
            projected_daily = (
                quota["daily_used"]
                + daily_rate * hours_until_daily
            )

            daily_at_risk = (
                projected_daily
                > quota["daily_limit"]
            )

            return {
                "quota_id": quota_id,
                "api_name": quota["api_name"],
                "hours_until_daily_reset": (
                    hours_until_daily
                ),
                "days_until_monthly_reset": (
                    days_until_monthly
                ),
                "daily_rate": round(
                    daily_rate, 1
                ),
                "projected_daily": round(
                    projected_daily, 0
                ),
                "daily_at_risk": daily_at_risk,
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }

    def check_overage(
        self,
    ) -> dict[str, Any]:
        """Aşım kontrol eder.

        Returns:
            Aşım bilgisi.
        """
        try:
            overages = []
            warnings = []

            for q in self._quotas:
                daily_pct = (
                    q["daily_used"]
                    / q["daily_limit"]
                    * 100.0
                ) if q["daily_limit"] > 0 else 0.0

                monthly_pct = (
                    q["monthly_used"]
                    / q["monthly_limit"]
                    * 100.0
                ) if q["monthly_limit"] > 0 else 0.0

                if (
                    daily_pct >= 100
                    or monthly_pct >= 100
                ):
                    overages.append({
                        "api_name": q[
                            "api_name"
                        ],
                        "daily_percent": round(
                            daily_pct, 1
                        ),
                        "monthly_percent": round(
                            monthly_pct, 1
                        ),
                    })
                elif (
                    daily_pct >= 80
                    or monthly_pct >= 80
                ):
                    warnings.append({
                        "api_name": q[
                            "api_name"
                        ],
                        "daily_percent": round(
                            daily_pct, 1
                        ),
                        "monthly_percent": round(
                            monthly_pct, 1
                        ),
                    })

            return {
                "overages": overages,
                "overage_count": len(overages),
                "warnings": warnings,
                "warning_count": len(warnings),
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }

    def get_usage_history(
        self,
        quota_id: str = "",
        limit: int = 10,
    ) -> dict[str, Any]:
        """Kullanım geçmişi getirir.

        Args:
            quota_id: Kota ID.
            limit: Limit.

        Returns:
            Geçmiş bilgisi.
        """
        try:
            if quota_id:
                filtered = [
                    h
                    for h
                    in self._usage_history
                    if h["quota_id"] == quota_id
                ]
            else:
                filtered = self._usage_history

            recent = filtered[-limit:]
            total_calls = sum(
                h["calls"] for h in recent
            )

            return {
                "history": recent,
                "entries": len(recent),
                "total_calls": total_calls,
                "quota_filter": quota_id,
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def reset_daily(
        self,
        quota_id: str = "",
    ) -> dict[str, Any]:
        """Günlük sayacı sıfırlar.

        Args:
            quota_id: Kota ID (boşsa hepsi).

        Returns:
            Sıfırlama bilgisi.
        """
        try:
            reset_count = 0
            for q in self._quotas:
                if (
                    not quota_id
                    or q["quota_id"] == quota_id
                ):
                    q["daily_used"] = 0
                    reset_count += 1

            return {
                "reset_count": reset_count,
                "quota_id": quota_id or "all",
                "reset": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "reset": False,
                "error": str(e),
            }
