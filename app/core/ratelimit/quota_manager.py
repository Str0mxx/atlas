"""ATLAS Kota Yoneticisi modulu.

Gunluk/aylik kotalar, kullanici kotalari,
API kotalari, sifirlama, kullanim takibi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

# Periyot -> saniye eslesmesi
_PERIOD_SECONDS = {
    "minute": 60,
    "hour": 3600,
    "day": 86400,
    "week": 604800,
    "month": 2592000,
}


class QuotaManager:
    """Kota yoneticisi.

    Kullanim kotalarini yonetir.

    Attributes:
        _quotas: Kota kayitlari.
        _usage: Kullanim kayitlari.
    """

    def __init__(
        self,
        reset_hour: int = 0,
    ) -> None:
        """Kota yoneticisini baslatir.

        Args:
            reset_hour: Gunluk sifirlama saati (UTC).
        """
        self._quotas: dict[
            str, dict[str, Any]
        ] = {}
        self._usage: dict[
            str, dict[str, int]
        ] = {}
        self._reset_hour = reset_hour
        self._stats = {
            "created": 0,
            "consumed": 0,
            "exceeded": 0,
            "resets": 0,
        }

        logger.info(
            "QuotaManager baslatildi",
        )

    def create_quota(
        self,
        quota_id: str,
        subject_id: str,
        limit: int,
        period: str = "day",
        resource: str = "",
    ) -> dict[str, Any]:
        """Kota olusturur.

        Args:
            quota_id: Kota ID.
            subject_id: Konu ID.
            limit: Limit.
            period: Periyot.
            resource: Kaynak.

        Returns:
            Kota bilgisi.
        """
        if quota_id in self._quotas:
            return {"error": "quota_exists"}

        period_secs = _PERIOD_SECONDS.get(
            period, 86400,
        )

        now = time.time()
        self._quotas[quota_id] = {
            "quota_id": quota_id,
            "subject_id": subject_id,
            "limit": limit,
            "period": period,
            "period_seconds": period_secs,
            "resource": resource,
            "used": 0,
            "reset_at": now + period_secs,
            "created_at": now,
        }

        self._stats["created"] += 1

        return {
            "quota_id": quota_id,
            "subject_id": subject_id,
            "limit": limit,
            "period": period,
            "status": "created",
        }

    def consume(
        self,
        quota_id: str,
        amount: int = 1,
    ) -> dict[str, Any]:
        """Kota tuketir.

        Args:
            quota_id: Kota ID.
            amount: Tuketim miktari.

        Returns:
            Tuketim sonucu.
        """
        quota = self._quotas.get(quota_id)
        if not quota:
            return {
                "allowed": False,
                "reason": "quota_not_found",
            }

        # Otomatik sifirlama kontrolu
        self._check_reset(quota_id)

        remaining = quota["limit"] - quota["used"]

        if amount > remaining:
            self._stats["exceeded"] += 1
            return {
                "allowed": False,
                "reason": "quota_exceeded",
                "used": quota["used"],
                "limit": quota["limit"],
                "remaining": remaining,
                "reset_at": quota["reset_at"],
            }

        quota["used"] += amount
        self._stats["consumed"] += amount

        # Konu bazli kullanim
        sid = quota["subject_id"]
        if sid not in self._usage:
            self._usage[sid] = {}
        res = quota.get("resource", "default")
        self._usage[sid][res] = (
            self._usage[sid].get(res, 0) + amount
        )

        return {
            "allowed": True,
            "used": quota["used"],
            "limit": quota["limit"],
            "remaining": (
                quota["limit"] - quota["used"]
            ),
        }

    def get_usage(
        self,
        quota_id: str,
    ) -> dict[str, Any]:
        """Kota kullanimini getirir.

        Args:
            quota_id: Kota ID.

        Returns:
            Kullanim bilgisi.
        """
        quota = self._quotas.get(quota_id)
        if not quota:
            return {"error": "quota_not_found"}

        self._check_reset(quota_id)

        return {
            "quota_id": quota_id,
            "used": quota["used"],
            "limit": quota["limit"],
            "remaining": (
                quota["limit"] - quota["used"]
            ),
            "percentage": round(
                quota["used"]
                / max(quota["limit"], 1)
                * 100,
                1,
            ),
            "reset_at": quota["reset_at"],
        }

    def get_subject_usage(
        self,
        subject_id: str,
    ) -> dict[str, int]:
        """Konu kullanimini getirir.

        Args:
            subject_id: Konu ID.

        Returns:
            Kaynak bazli kullanim.
        """
        return dict(
            self._usage.get(subject_id, {}),
        )

    def reset_quota(
        self,
        quota_id: str,
    ) -> dict[str, Any]:
        """Kotayi sifirlar.

        Args:
            quota_id: Kota ID.

        Returns:
            Sifirlama sonucu.
        """
        quota = self._quotas.get(quota_id)
        if not quota:
            return {"error": "quota_not_found"}

        quota["used"] = 0
        quota["reset_at"] = (
            time.time() + quota["period_seconds"]
        )
        self._stats["resets"] += 1

        return {
            "quota_id": quota_id,
            "status": "reset",
        }

    def update_quota(
        self,
        quota_id: str,
        limit: int | None = None,
        period: str | None = None,
    ) -> dict[str, Any]:
        """Kota gunceller.

        Args:
            quota_id: Kota ID.
            limit: Yeni limit.
            period: Yeni periyot.

        Returns:
            Guncelleme sonucu.
        """
        quota = self._quotas.get(quota_id)
        if not quota:
            return {"error": "quota_not_found"}

        if limit is not None:
            quota["limit"] = limit
        if period is not None:
            quota["period"] = period
            quota["period_seconds"] = (
                _PERIOD_SECONDS.get(period, 86400)
            )

        return {
            "quota_id": quota_id,
            "status": "updated",
        }

    def delete_quota(
        self,
        quota_id: str,
    ) -> bool:
        """Kotayi siler.

        Args:
            quota_id: Kota ID.

        Returns:
            Basarili mi.
        """
        if quota_id not in self._quotas:
            return False
        del self._quotas[quota_id]
        return True

    def get_quota(
        self,
        quota_id: str,
    ) -> dict[str, Any] | None:
        """Kota bilgisi getirir.

        Args:
            quota_id: Kota ID.

        Returns:
            Kota bilgisi veya None.
        """
        quota = self._quotas.get(quota_id)
        if not quota:
            return None
        self._check_reset(quota_id)
        return dict(quota)

    def list_quotas(
        self,
        subject_id: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Kotalari listeler.

        Args:
            subject_id: Konu filtresi.
            limit: Limit.

        Returns:
            Kota listesi.
        """
        quotas = list(self._quotas.values())

        if subject_id:
            quotas = [
                q for q in quotas
                if q["subject_id"] == subject_id
            ]

        return quotas[-limit:]

    def _check_reset(
        self,
        quota_id: str,
    ) -> None:
        """Sifirlama kontrolu yapar.

        Args:
            quota_id: Kota ID.
        """
        quota = self._quotas.get(quota_id)
        if not quota:
            return

        now = time.time()
        if now >= quota["reset_at"]:
            quota["used"] = 0
            quota["reset_at"] = (
                now + quota["period_seconds"]
            )
            self._stats["resets"] += 1

    @property
    def quota_count(self) -> int:
        """Kota sayisi."""
        return len(self._quotas)

    @property
    def consumed_total(self) -> int:
        """Toplam tuketim."""
        return self._stats["consumed"]

    @property
    def exceeded_count(self) -> int:
        """Asim sayisi."""
        return self._stats["exceeded"]
