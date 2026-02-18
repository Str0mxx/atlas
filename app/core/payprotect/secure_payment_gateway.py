"""
Guvenli odeme gecidi modulu.

Odeme isleme, gecit entegrasyonu,
yeniden deneme, hata yonetimi,
mutabakat.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class SecurePaymentGateway:
    """Guvenli odeme gecidi.

    Attributes:
        _gateways: Gecit tanimlari.
        _transactions: Islem kayitlari.
        _reconciliations: Mutabakat.
        _retries: Yeniden deneme.
        _stats: Istatistikler.
    """

    GATEWAY_TYPES: list[str] = [
        "stripe",
        "paypal",
        "iyzico",
        "payu",
        "garanti",
        "custom",
    ]

    TX_STATUSES: list[str] = [
        "pending",
        "processing",
        "completed",
        "failed",
        "refunded",
        "cancelled",
    ]

    def __init__(
        self,
        max_retries: int = 3,
        retry_delay_sec: int = 5,
    ) -> None:
        """Gecidi baslatir.

        Args:
            max_retries: Maks deneme.
            retry_delay_sec: Deneme arasi.
        """
        self._max_retries = max_retries
        self._retry_delay = retry_delay_sec
        self._gateways: dict[
            str, dict
        ] = {}
        self._transactions: dict[
            str, dict
        ] = {}
        self._reconciliations: list[
            dict
        ] = []
        self._retries: list[dict] = []
        self._stats: dict[str, int] = {
            "gateways_registered": 0,
            "transactions_processed": 0,
            "successful": 0,
            "failed": 0,
            "retries": 0,
            "refunds": 0,
            "reconciliations": 0,
        }
        logger.info(
            "SecurePaymentGateway "
            "baslatildi"
        )

    @property
    def transaction_count(self) -> int:
        """Islem sayisi."""
        return len(self._transactions)

    def register_gateway(
        self,
        name: str = "",
        gateway_type: str = "custom",
        api_endpoint: str = "",
        priority: int = 1,
        is_active: bool = True,
    ) -> dict[str, Any]:
        """Gecit kaydeder.

        Args:
            name: Gecit adi.
            gateway_type: Gecit tipi.
            api_endpoint: API adresi.
            priority: Oncelik.
            is_active: Aktif mi.

        Returns:
            Kayit bilgisi.
        """
        try:
            gid = f"gw_{uuid4()!s:.8}"
            self._gateways[name] = {
                "gateway_id": gid,
                "name": name,
                "gateway_type": gateway_type,
                "api_endpoint": api_endpoint,
                "priority": priority,
                "is_active": is_active,
                "success_rate": 1.0,
                "total_processed": 0,
            }
            self._stats[
                "gateways_registered"
            ] += 1

            return {
                "gateway_id": gid,
                "name": name,
                "registered": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "registered": False,
                "error": str(e),
            }

    def process_payment(
        self,
        amount: float = 0.0,
        currency: str = "TRY",
        token_id: str = "",
        merchant_id: str = "",
        gateway_name: str = "",
        metadata: dict | None = None,
    ) -> dict[str, Any]:
        """Odeme isler.

        Args:
            amount: Tutar.
            currency: Para birimi.
            token_id: Token ID.
            merchant_id: Isyeri ID.
            gateway_name: Gecit adi.
            metadata: Ek veri.

        Returns:
            Islem sonucu.
        """
        try:
            self._stats[
                "transactions_processed"
            ] += 1

            gw = self._gateways.get(
                gateway_name
            )
            if not gw:
                # Ilk aktif gecidi sec
                for g in sorted(
                    self._gateways.values(),
                    key=lambda x: x[
                        "priority"
                    ],
                ):
                    if g["is_active"]:
                        gw = g
                        break

            if not gw:
                self._stats["failed"] += 1
                return {
                    "processed": False,
                    "error": (
                        "Gecit bulunamadi"
                    ),
                }

            tid = f"tx_{uuid4()!s:.8}"
            # Simulasyon: basarili
            tx = {
                "transaction_id": tid,
                "amount": amount,
                "currency": currency,
                "token_id": token_id,
                "merchant_id": merchant_id,
                "gateway_name": gw["name"],
                "gateway_id": gw[
                    "gateway_id"
                ],
                "status": "completed",
                "metadata": metadata or {},
                "created_at": datetime.now(
                    timezone.utc
                ).isoformat(),
                "completed_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
                "retry_count": 0,
            }
            self._transactions[tid] = tx
            self._stats["successful"] += 1
            gw["total_processed"] += 1

            return {
                "transaction_id": tid,
                "amount": amount,
                "status": "completed",
                "gateway": gw["name"],
                "processed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            self._stats["failed"] += 1
            return {
                "processed": False,
                "error": str(e),
            }

    def retry_payment(
        self,
        transaction_id: str = "",
    ) -> dict[str, Any]:
        """Islemi yeniden dener.

        Args:
            transaction_id: Islem ID.

        Returns:
            Deneme sonucu.
        """
        try:
            tx = self._transactions.get(
                transaction_id
            )
            if not tx:
                return {
                    "retried": False,
                    "error": (
                        "Islem bulunamadi"
                    ),
                }

            if tx["status"] != "failed":
                return {
                    "retried": False,
                    "error": (
                        "Sadece basarisiz "
                        "islem denenebilir"
                    ),
                }

            if (
                tx["retry_count"]
                >= self._max_retries
            ):
                return {
                    "retried": False,
                    "error": (
                        "Maks deneme asildi"
                    ),
                }

            tx["retry_count"] += 1
            tx["status"] = "completed"
            tx["completed_at"] = (
                datetime.now(
                    timezone.utc
                ).isoformat()
            )
            self._stats["retries"] += 1
            self._retries.append({
                "transaction_id": (
                    transaction_id
                ),
                "attempt": tx[
                    "retry_count"
                ],
                "result": "success",
                "retried_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            })

            return {
                "transaction_id": (
                    transaction_id
                ),
                "attempt": tx[
                    "retry_count"
                ],
                "status": "completed",
                "retried": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retried": False,
                "error": str(e),
            }

    def refund_payment(
        self,
        transaction_id: str = "",
        amount: float | None = None,
        reason: str = "",
    ) -> dict[str, Any]:
        """Iade isler.

        Args:
            transaction_id: Islem ID.
            amount: Iade tutari.
            reason: Neden.

        Returns:
            Iade sonucu.
        """
        try:
            tx = self._transactions.get(
                transaction_id
            )
            if not tx:
                return {
                    "refunded": False,
                    "error": (
                        "Islem bulunamadi"
                    ),
                }

            if tx["status"] != "completed":
                return {
                    "refunded": False,
                    "error": (
                        "Sadece tamamlanmis "
                        "islem iade edilir"
                    ),
                }

            refund_amount = (
                amount
                if amount is not None
                else tx["amount"]
            )
            tx["status"] = "refunded"
            tx["refund_amount"] = (
                refund_amount
            )
            tx["refund_reason"] = reason
            self._stats["refunds"] += 1

            rid = f"rf_{uuid4()!s:.8}"
            return {
                "refund_id": rid,
                "transaction_id": (
                    transaction_id
                ),
                "refund_amount": (
                    refund_amount
                ),
                "refunded": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "refunded": False,
                "error": str(e),
            }

    def reconcile(
        self,
        gateway_name: str = "",
        expected_total: float = 0.0,
    ) -> dict[str, Any]:
        """Mutabakat yapar.

        Args:
            gateway_name: Gecit adi.
            expected_total: Beklenen.

        Returns:
            Mutabakat sonucu.
        """
        try:
            actual = sum(
                t["amount"]
                for t in (
                    self._transactions
                    .values()
                )
                if (
                    t.get("gateway_name")
                    == gateway_name
                    and t["status"]
                    == "completed"
                )
            )

            diff = abs(
                actual - expected_total
            )
            matched = diff < 0.01
            rid = f"rc_{uuid4()!s:.8}"

            rec = {
                "reconciliation_id": rid,
                "gateway_name": gateway_name,
                "expected": expected_total,
                "actual": round(actual, 2),
                "difference": round(diff, 2),
                "matched": matched,
                "reconciled_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }
            self._reconciliations.append(
                rec
            )
            self._stats[
                "reconciliations"
            ] += 1

            return {
                "reconciliation_id": rid,
                "matched": matched,
                "expected": expected_total,
                "actual": round(actual, 2),
                "difference": round(
                    diff, 2
                ),
                "reconciled": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "reconciled": False,
                "error": str(e),
            }

    def get_transaction(
        self,
        transaction_id: str = "",
    ) -> dict[str, Any]:
        """Islem bilgisi getirir."""
        try:
            tx = self._transactions.get(
                transaction_id
            )
            if not tx:
                return {
                    "found": False,
                    "error": (
                        "Islem bulunamadi"
                    ),
                }
            return {
                **tx,
                "found": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "found": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir."""
        try:
            return {
                "total_gateways": len(
                    self._gateways
                ),
                "total_transactions": len(
                    self._transactions
                ),
                "total_reconciliations": (
                    len(
                        self._reconciliations
                    )
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
