"""
Islem sinırlayici modulu.

Tutar limitleri, frekans limitleri,
hiz kontrolleri, override isleme,
uyari uretimi.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class TransactionLimiter:
    """Islem sinırlayici.

    Attributes:
        _limits: Limit tanimlari.
        _transactions: Islem kayitlari.
        _alerts: Uyari kayitlari.
        _overrides: Override kayitlari.
        _stats: Istatistikler.
    """

    LIMIT_TYPES: list[str] = [
        "single_amount",
        "daily_amount",
        "weekly_amount",
        "monthly_amount",
        "daily_count",
        "hourly_count",
    ]

    def __init__(self) -> None:
        """Sinırlayiciyi baslatir."""
        self._limits: dict[
            str, dict
        ] = {}
        self._transactions: dict[
            str, list
        ] = {}
        self._alerts: list[dict] = []
        self._overrides: list[dict] = []
        self._stats: dict[str, int] = {
            "limits_created": 0,
            "checks_run": 0,
            "blocked": 0,
            "allowed": 0,
            "alerts_generated": 0,
            "overrides_used": 0,
        }
        logger.info(
            "TransactionLimiter "
            "baslatildi"
        )

    @property
    def alert_count(self) -> int:
        """Uyari sayisi."""
        return len(self._alerts)

    def create_limit(
        self,
        name: str = "",
        limit_type: str = "single_amount",
        max_value: float = 0.0,
        currency: str = "TRY",
        merchant_id: str = "",
        user_id: str = "",
    ) -> dict[str, Any]:
        """Limit olusturur.

        Args:
            name: Limit adi.
            limit_type: Limit tipi.
            max_value: Maks deger.
            currency: Para birimi.
            merchant_id: Isyeri ID.
            user_id: Kullanici ID.

        Returns:
            Olusturma bilgisi.
        """
        try:
            if (
                limit_type
                not in self.LIMIT_TYPES
            ):
                return {
                    "created": False,
                    "error": (
                        f"Gecersiz: "
                        f"{limit_type}"
                    ),
                }

            lid = f"lm_{uuid4()!s:.8}"
            self._limits[name] = {
                "limit_id": lid,
                "name": name,
                "limit_type": limit_type,
                "max_value": max_value,
                "currency": currency,
                "merchant_id": merchant_id,
                "user_id": user_id,
                "active": True,
            }
            self._stats[
                "limits_created"
            ] += 1

            return {
                "limit_id": lid,
                "name": name,
                "max_value": max_value,
                "created": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "created": False,
                "error": str(e),
            }

    def check_transaction(
        self,
        user_id: str = "",
        amount: float = 0.0,
        currency: str = "TRY",
        merchant_id: str = "",
    ) -> dict[str, Any]:
        """Islemi kontrol eder.

        Args:
            user_id: Kullanici ID.
            amount: Tutar.
            currency: Para birimi.
            merchant_id: Isyeri ID.

        Returns:
            Kontrol sonucu.
        """
        try:
            self._stats["checks_run"] += 1
            violations: list[dict] = []

            for lname, limit in (
                self._limits.items()
            ):
                if not limit["active"]:
                    continue

                lt = limit["limit_type"]
                mv = limit["max_value"]

                # Tek islem limiti
                if (
                    lt == "single_amount"
                    and amount > mv
                ):
                    violations.append({
                        "limit": lname,
                        "type": lt,
                        "max": mv,
                        "actual": amount,
                        "severity": "high",
                    })

                # Gunluk toplam
                if lt == "daily_amount":
                    daily = (
                        self._get_period_total(
                            user_id, "daily"
                        )
                    )
                    if daily + amount > mv:
                        violations.append({
                            "limit": lname,
                            "type": lt,
                            "max": mv,
                            "actual": (
                                daily + amount
                            ),
                            "severity": (
                                "high"
                            ),
                        })

                # Gunluk sayi
                if lt == "daily_count":
                    count = (
                        self._get_period_count(
                            user_id, "daily"
                        )
                    )
                    if count + 1 > mv:
                        violations.append({
                            "limit": lname,
                            "type": lt,
                            "max": mv,
                            "actual": (
                                count + 1
                            ),
                            "severity": (
                                "medium"
                            ),
                        })

            blocked = len(violations) > 0
            if blocked:
                self._stats["blocked"] += 1
                for v in violations:
                    aid = (
                        f"al_{uuid4()!s:.8}"
                    )
                    self._alerts.append({
                        "alert_id": aid,
                        "user_id": user_id,
                        "amount": amount,
                        "limit": v["limit"],
                        "severity": v[
                            "severity"
                        ],
                        "created_at": (
                            datetime.now(
                                timezone.utc
                            ).isoformat()
                        ),
                    })
                    self._stats[
                        "alerts_generated"
                    ] += 1
            else:
                self._stats["allowed"] += 1
                self._record_transaction(
                    user_id, amount,
                    currency, merchant_id,
                )

            return {
                "user_id": user_id,
                "amount": amount,
                "allowed": not blocked,
                "violations": violations,
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }

    def _record_transaction(
        self,
        user_id: str,
        amount: float,
        currency: str,
        merchant_id: str,
    ) -> None:
        """Islem kaydeder."""
        if user_id not in (
            self._transactions
        ):
            self._transactions[
                user_id
            ] = []
        self._transactions[
            user_id
        ].append({
            "amount": amount,
            "currency": currency,
            "merchant_id": merchant_id,
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
        })

    def _get_period_total(
        self,
        user_id: str,
        period: str,
    ) -> float:
        """Donem toplamini getirir."""
        txns = self._transactions.get(
            user_id, []
        )
        return sum(
            t["amount"] for t in txns
        )

    def _get_period_count(
        self,
        user_id: str,
        period: str,
    ) -> int:
        """Donem sayisini getirir."""
        txns = self._transactions.get(
            user_id, []
        )
        return len(txns)

    def override_limit(
        self,
        user_id: str = "",
        amount: float = 0.0,
        reason: str = "",
        approved_by: str = "",
    ) -> dict[str, Any]:
        """Limit override yapar.

        Args:
            user_id: Kullanici ID.
            amount: Tutar.
            reason: Neden.
            approved_by: Onaylayan.

        Returns:
            Override bilgisi.
        """
        try:
            oid = f"ov_{uuid4()!s:.8}"
            self._overrides.append({
                "override_id": oid,
                "user_id": user_id,
                "amount": amount,
                "reason": reason,
                "approved_by": approved_by,
                "created_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            })
            self._stats[
                "overrides_used"
            ] += 1

            # Islemi kaydet
            self._record_transaction(
                user_id, amount,
                "TRY", "",
            )

            return {
                "override_id": oid,
                "amount": amount,
                "overridden": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "overridden": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir."""
        try:
            return {
                "total_limits": len(
                    self._limits
                ),
                "total_alerts": len(
                    self._alerts
                ),
                "total_overrides": len(
                    self._overrides
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
