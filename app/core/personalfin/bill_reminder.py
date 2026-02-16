"""
Fatura hatırlatıcı modülü.

Fatura takibi, vade uyarıları, otomatik
ödeme, ödeme geçmişi ve gecikme
önleme sağlar.
"""

import logging
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class BillReminder:
    """Fatura hatırlatıcı.

    Faturaları takip eder, vade uyarıları
    gönderir ve gecikmeleri önler.

    Attributes:
        _bills: Fatura kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Hatırlatıcıyı başlatır."""
        self._bills: list[dict] = []
        self._stats: dict[str, int] = {
            "bills_tracked": 0,
        }
        logger.info(
            "BillReminder baslatildi"
        )

    @property
    def bill_count(self) -> int:
        """Takip edilen fatura sayısı."""
        return len(self._bills)

    def add_bill(
        self,
        name: str = "Utility Bill",
        amount: float = 0.0,
        due_day: int = 15,
        frequency: str = "monthly",
    ) -> dict[str, Any]:
        """Fatura ekler.

        Args:
            name: Fatura adı.
            amount: Tutar.
            due_day: Vade günü (1-28).
            frequency: Sıklık.

        Returns:
            Fatura bilgisi.
        """
        try:
            bid = f"bill_{uuid4()!s:.8}"
            bill = {
                "bill_id": bid,
                "name": name,
                "amount": amount,
                "due_day": min(
                    max(due_day, 1), 28
                ),
                "frequency": frequency,
                "auto_pay": False,
                "paid": False,
            }
            self._bills.append(bill)
            self._stats[
                "bills_tracked"
            ] += 1

            return {
                "bill_id": bid,
                "name": name,
                "amount": amount,
                "due_day": bill["due_day"],
                "frequency": frequency,
                "added": True,
            }

        except Exception as e:
            logger.error(
                f"Fatura ekleme hatasi: {e}"
            )
            return {
                "bill_id": "",
                "name": name,
                "added": False,
                "error": str(e),
            }

    def check_due(
        self,
        current_day: int = 1,
    ) -> dict[str, Any]:
        """Vadesi gelen faturaları kontrol.

        Args:
            current_day: Bugünün günü.

        Returns:
            Vade kontrol sonucu.
        """
        try:
            due_soon: list[dict] = []
            overdue: list[dict] = []

            for b in self._bills:
                if b["paid"]:
                    continue
                diff = (
                    b["due_day"] - current_day
                )
                if diff < 0:
                    overdue.append(
                        {
                            "name": b["name"],
                            "amount": b[
                                "amount"
                            ],
                            "days_late": abs(
                                diff
                            ),
                        }
                    )
                elif diff <= 3:
                    due_soon.append(
                        {
                            "name": b["name"],
                            "amount": b[
                                "amount"
                            ],
                            "days_until": diff,
                        }
                    )

            return {
                "due_soon": due_soon,
                "due_soon_count": len(
                    due_soon
                ),
                "overdue": overdue,
                "overdue_count": len(
                    overdue
                ),
                "checked": True,
            }

        except Exception as e:
            logger.error(
                f"Vade kontrol hatasi: {e}"
            )
            return {
                "due_soon": [],
                "overdue": [],
                "checked": False,
                "error": str(e),
            }

    def setup_auto_pay(
        self,
        bill_id: str,
    ) -> dict[str, Any]:
        """Otomatik ödeme ayarlar.

        Args:
            bill_id: Fatura ID.

        Returns:
            Ayar sonucu.
        """
        try:
            for b in self._bills:
                if b["bill_id"] == bill_id:
                    b["auto_pay"] = True
                    return {
                        "bill_id": bill_id,
                        "name": b["name"],
                        "auto_pay": True,
                        "setup": True,
                    }

            return {
                "bill_id": bill_id,
                "auto_pay": False,
                "setup": False,
                "error": "bill_not_found",
            }

        except Exception as e:
            logger.error(
                f"Otomatik odeme "
                f"hatasi: {e}"
            )
            return {
                "bill_id": bill_id,
                "setup": False,
                "error": str(e),
            }

    def record_payment(
        self,
        bill_id: str,
        amount_paid: float = 0.0,
    ) -> dict[str, Any]:
        """Ödeme kaydeder.

        Args:
            bill_id: Fatura ID.
            amount_paid: Ödenen tutar.

        Returns:
            Ödeme kaydı sonucu.
        """
        try:
            for b in self._bills:
                if b["bill_id"] == bill_id:
                    b["paid"] = True
                    expected = b["amount"]
                    diff = round(
                        amount_paid
                        - expected,
                        2,
                    )

                    return {
                        "bill_id": bill_id,
                        "name": b["name"],
                        "amount_paid": (
                            amount_paid
                        ),
                        "expected": expected,
                        "difference": diff,
                        "recorded": True,
                    }

            return {
                "bill_id": bill_id,
                "recorded": False,
                "error": "bill_not_found",
            }

        except Exception as e:
            logger.error(
                f"Odeme kayit hatasi: {e}"
            )
            return {
                "bill_id": bill_id,
                "recorded": False,
                "error": str(e),
            }

    def estimate_late_fees(
        self,
        amount: float = 0.0,
        days_late: int = 0,
        rate: float = 2.0,
    ) -> dict[str, Any]:
        """Gecikme ücretini hesaplar.

        Args:
            amount: Fatura tutarı.
            days_late: Gecikme gün sayısı.
            rate: Günlük oran (yüzde ‰).

        Returns:
            Gecikme ücreti bilgisi.
        """
        try:
            fee = round(
                amount
                * (rate / 1000)
                * days_late,
                2,
            )
            total = round(
                amount + fee, 2
            )

            if days_late == 0:
                risk = "none"
            elif days_late <= 7:
                risk = "low"
            elif days_late <= 30:
                risk = "medium"
            else:
                risk = "high"

            return {
                "amount": amount,
                "days_late": days_late,
                "late_fee": fee,
                "total_due": total,
                "risk_level": risk,
                "estimated": True,
            }

        except Exception as e:
            logger.error(
                f"Gecikme hesaplama "
                f"hatasi: {e}"
            )
            return {
                "amount": amount,
                "days_late": days_late,
                "late_fee": 0.0,
                "total_due": amount,
                "risk_level": "unknown",
                "estimated": False,
                "error": str(e),
            }
