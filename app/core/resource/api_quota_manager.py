"""ATLAS API Kota Yoneticisi modulu.

API hiz takibi, kota tahsisi,
kullanim tahmini, maliyet optimizasyonu
ve limit zorlama.
"""

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class APIQuotaManager:
    """API kota yoneticisi.

    API kullanim kotalarini izler
    ve yonetir.

    Attributes:
        _quotas: Kota kayitlari.
        _usage: Kullanim gecmisi.
        _costs: API maliyetleri.
    """

    def __init__(self) -> None:
        """API kota yoneticisini baslatir."""
        self._quotas: dict[str, dict[str, Any]] = {}
        self._usage: dict[str, list[dict[str, Any]]] = {}
        self._costs: dict[str, float] = {}

        logger.info("APIQuotaManager baslatildi")

    def set_quota(
        self,
        service: str,
        limit: int,
        period: str = "daily",
        cost_per_call: float = 0.0,
    ) -> dict[str, Any]:
        """Kota ayarlar.

        Args:
            service: Servis adi.
            limit: Cagri limiti.
            period: Periyot (daily/hourly/monthly).
            cost_per_call: Cagri basi maliyet.

        Returns:
            Kota bilgisi.
        """
        quota = {
            "service": service,
            "limit": max(1, limit),
            "period": period,
            "cost_per_call": max(0.0, cost_per_call),
            "used": 0,
        }
        self._quotas[service] = quota
        self._costs[service] = cost_per_call
        return quota

    def record_call(
        self,
        service: str,
        tokens: int = 0,
    ) -> dict[str, Any]:
        """API cagrisi kaydeder.

        Args:
            service: Servis adi.
            tokens: Kullanilan token.

        Returns:
            Kayit sonucu.
        """
        quota = self._quotas.get(service)
        if not quota:
            return {"allowed": True, "no_quota": True}

        quota["used"] += 1
        within = quota["used"] <= quota["limit"]

        if service not in self._usage:
            self._usage[service] = []

        self._usage[service].append({
            "tokens": tokens,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        cost = self._costs.get(service, 0.0)
        return {
            "allowed": within,
            "used": quota["used"],
            "limit": quota["limit"],
            "remaining": max(0, quota["limit"] - quota["used"]),
            "cost": cost,
        }

    def check_quota(
        self,
        service: str,
    ) -> dict[str, Any]:
        """Kota durumunu kontrol eder.

        Args:
            service: Servis adi.

        Returns:
            Kota durumu.
        """
        quota = self._quotas.get(service)
        if not quota:
            return {"exists": False}

        used = quota["used"]
        limit = quota["limit"]
        ratio = used / limit if limit > 0 else 0.0

        return {
            "exists": True,
            "service": service,
            "used": used,
            "limit": limit,
            "remaining": max(0, limit - used),
            "usage_ratio": ratio,
            "exhausted": used >= limit,
        }

    def forecast_usage(
        self,
        service: str,
        periods_ahead: int = 1,
    ) -> dict[str, Any]:
        """Kullanim tahmini yapar.

        Args:
            service: Servis adi.
            periods_ahead: Kac periyot ileri.

        Returns:
            Tahmin sonucu.
        """
        usage_list = self._usage.get(service, [])
        if not usage_list:
            return {"forecast": 0, "sufficient": True}

        current_rate = len(usage_list)
        forecast = current_rate * (1 + periods_ahead)

        quota = self._quotas.get(service)
        limit = quota["limit"] if quota else float("inf")
        sufficient = forecast <= limit

        return {
            "current_usage": current_rate,
            "forecast": forecast,
            "limit": limit,
            "sufficient": sufficient,
            "periods_ahead": periods_ahead,
        }

    def optimize_cost(self) -> list[dict[str, Any]]:
        """Maliyet optimizasyonu onerir.

        Returns:
            Oneri listesi.
        """
        suggestions: list[dict[str, Any]] = []
        for service, quota in self._quotas.items():
            used = quota["used"]
            limit = quota["limit"]
            cost = self._costs.get(service, 0.0)

            if limit > 0 and used < limit * 0.3 and cost > 0:
                suggestions.append({
                    "service": service,
                    "suggestion": "downgrade_plan",
                    "current_limit": limit,
                    "suggested_limit": max(1, int(limit * 0.5)),
                    "potential_savings": cost * (limit - used),
                })
            elif used >= limit * 0.9:
                suggestions.append({
                    "service": service,
                    "suggestion": "upgrade_plan",
                    "current_limit": limit,
                    "usage_ratio": used / limit if limit > 0 else 0,
                })

        return suggestions

    def reset_quota(self, service: str) -> bool:
        """Kotayi sifirlar.

        Args:
            service: Servis adi.

        Returns:
            Basarili ise True.
        """
        quota = self._quotas.get(service)
        if not quota:
            return False
        quota["used"] = 0
        return True

    def get_total_cost(self) -> float:
        """Toplam maliyeti hesaplar.

        Returns:
            Toplam maliyet.
        """
        total = 0.0
        for service, quota in self._quotas.items():
            cost = self._costs.get(service, 0.0)
            total += cost * quota["used"]
        return total

    @property
    def quota_count(self) -> int:
        """Kota sayisi."""
        return len(self._quotas)

    @property
    def tracked_services(self) -> int:
        """Takip edilen servis sayisi."""
        return len(self._usage)
