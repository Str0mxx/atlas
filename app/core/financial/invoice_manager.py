"""ATLAS Fatura Yöneticisi modülü.

Fatura oluşturma, ödeme takibi,
hatırlatma otomasyonu, gecikmiş yönetim,
mutabakat.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class InvoiceManager:
    """Fatura yöneticisi.

    Faturaları oluşturur ve takip eder.

    Attributes:
        _invoices: Fatura kayıtları.
        _payments: Ödeme kayıtları.
    """

    def __init__(
        self,
        currency: str = "TRY",
    ) -> None:
        """Yöneticiyi başlatır.

        Args:
            currency: Varsayılan para birimi.
        """
        self._invoices: dict[
            str, dict[str, Any]
        ] = {}
        self._payments: list[
            dict[str, Any]
        ] = []
        self._reminders: list[
            dict[str, Any]
        ] = []
        self._currency = currency
        self._counter = 0
        self._stats = {
            "invoices_created": 0,
            "invoices_paid": 0,
            "total_invoiced": 0.0,
            "total_collected": 0.0,
            "reminders_sent": 0,
        }

        logger.info(
            "InvoiceManager baslatildi",
        )

    def create_invoice(
        self,
        client: str,
        amount: float,
        due_days: int = 30,
        items: list[dict[str, Any]]
        | None = None,
        description: str = "",
    ) -> dict[str, Any]:
        """Fatura oluşturur.

        Args:
            client: Müşteri.
            amount: Tutar.
            due_days: Vade günü.
            items: Kalemler.
            description: Açıklama.

        Returns:
            Fatura bilgisi.
        """
        self._counter += 1
        iid = f"inv_{self._counter}"

        now = time.time()
        due_ts = now + (due_days * 86400)

        invoice = {
            "invoice_id": iid,
            "client": client,
            "amount": amount,
            "items": items or [],
            "description": description,
            "status": "sent",
            "paid_amount": 0.0,
            "currency": self._currency,
            "created_at": now,
            "due_at": due_ts,
            "due_days": due_days,
        }
        self._invoices[iid] = invoice
        self._stats["invoices_created"] += 1
        self._stats["total_invoiced"] += amount

        return {
            "invoice_id": iid,
            "client": client,
            "amount": amount,
            "due_days": due_days,
            "created": True,
        }

    def record_payment(
        self,
        invoice_id: str,
        amount: float,
        method: str = "transfer",
    ) -> dict[str, Any]:
        """Ödeme kaydeder.

        Args:
            invoice_id: Fatura ID.
            amount: Ödeme tutarı.
            method: Ödeme yöntemi.

        Returns:
            Ödeme bilgisi.
        """
        inv = self._invoices.get(invoice_id)
        if not inv:
            return {
                "error": "invoice_not_found",
            }

        self._counter += 1
        pid = f"pay_{self._counter}"

        payment = {
            "payment_id": pid,
            "invoice_id": invoice_id,
            "amount": amount,
            "method": method,
            "timestamp": time.time(),
        }
        self._payments.append(payment)

        inv["paid_amount"] += amount
        self._stats["total_collected"] += amount

        if inv["paid_amount"] >= inv["amount"]:
            inv["status"] = "paid"
            self._stats["invoices_paid"] += 1
        elif inv["paid_amount"] > 0:
            inv["status"] = "partial"

        return {
            "payment_id": pid,
            "invoice_id": invoice_id,
            "amount": amount,
            "status": inv["status"],
            "recorded": True,
        }

    def get_invoice(
        self,
        invoice_id: str,
    ) -> dict[str, Any]:
        """Fatura getirir.

        Args:
            invoice_id: Fatura ID.

        Returns:
            Fatura bilgisi.
        """
        inv = self._invoices.get(invoice_id)
        if not inv:
            return {
                "error": "invoice_not_found",
            }
        return dict(inv)

    def get_overdue(
        self,
    ) -> dict[str, Any]:
        """Gecikmiş faturaları getirir.

        Returns:
            Gecikmiş fatura bilgisi.
        """
        now = time.time()
        overdue = []

        for iid, inv in (
            self._invoices.items()
        ):
            if (
                inv["status"] not in (
                    "paid", "cancelled",
                )
                and inv["due_at"] < now
            ):
                inv["status"] = "overdue"
                days_overdue = int(
                    (now - inv["due_at"])
                    / 86400,
                )
                overdue.append({
                    "invoice_id": iid,
                    "client": inv["client"],
                    "amount": inv["amount"],
                    "paid": inv["paid_amount"],
                    "remaining": round(
                        inv["amount"]
                        - inv["paid_amount"],
                        2,
                    ),
                    "days_overdue": days_overdue,
                })

        return {
            "overdue": overdue,
            "count": len(overdue),
            "total_overdue": round(
                sum(
                    o["remaining"]
                    for o in overdue
                ),
                2,
            ),
        }

    def create_reminder(
        self,
        invoice_id: str,
        message: str = "",
    ) -> dict[str, Any]:
        """Hatırlatma oluşturur.

        Args:
            invoice_id: Fatura ID.
            message: Mesaj.

        Returns:
            Hatırlatma bilgisi.
        """
        inv = self._invoices.get(invoice_id)
        if not inv:
            return {
                "error": "invoice_not_found",
            }

        self._counter += 1
        rid = f"rem_{self._counter}"

        remaining = (
            inv["amount"] - inv["paid_amount"]
        )
        if not message:
            message = (
                f"Payment reminder: "
                f"{remaining:.2f} "
                f"{self._currency} due "
                f"for invoice {invoice_id}"
            )

        reminder = {
            "reminder_id": rid,
            "invoice_id": invoice_id,
            "client": inv["client"],
            "remaining": round(remaining, 2),
            "message": message,
            "sent_at": time.time(),
        }
        self._reminders.append(reminder)
        self._stats["reminders_sent"] += 1

        return {
            "reminder_id": rid,
            "invoice_id": invoice_id,
            "remaining": round(remaining, 2),
            "sent": True,
        }

    def reconcile(
        self,
    ) -> dict[str, Any]:
        """Mutabakat yapar.

        Returns:
            Mutabakat bilgisi.
        """
        total_invoiced = self._stats[
            "total_invoiced"
        ]
        total_collected = self._stats[
            "total_collected"
        ]
        outstanding = (
            total_invoiced - total_collected
        )

        by_status: dict[str, int] = {}
        for inv in self._invoices.values():
            s = inv["status"]
            by_status[s] = (
                by_status.get(s, 0) + 1
            )

        return {
            "total_invoiced": round(
                total_invoiced, 2,
            ),
            "total_collected": round(
                total_collected, 2,
            ),
            "outstanding": round(
                outstanding, 2,
            ),
            "collection_rate": round(
                total_collected
                / max(total_invoiced, 0.01)
                * 100,
                1,
            ),
            "by_status": by_status,
            "invoice_count": len(
                self._invoices,
            ),
        }

    def cancel_invoice(
        self,
        invoice_id: str,
    ) -> dict[str, Any]:
        """Fatura iptal eder."""
        inv = self._invoices.get(invoice_id)
        if not inv:
            return {
                "error": "invoice_not_found",
            }
        inv["status"] = "cancelled"
        return {
            "invoice_id": invoice_id,
            "cancelled": True,
        }

    @property
    def invoice_count(self) -> int:
        """Fatura sayısı."""
        return self._stats[
            "invoices_created"
        ]

    @property
    def paid_count(self) -> int:
        """Ödenen fatura sayısı."""
        return self._stats["invoices_paid"]

    @property
    def total_invoiced(self) -> float:
        """Toplam fatura tutarı."""
        return round(
            self._stats["total_invoiced"], 2,
        )

    @property
    def total_collected(self) -> float:
        """Toplam tahsilat."""
        return round(
            self._stats["total_collected"], 2,
        )
