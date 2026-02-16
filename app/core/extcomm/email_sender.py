"""ATLAS Email Gönderici modülü.

SMTP entegrasyonu, teslimat takibi,
bounce yönetimi, rate limiting,
kuyruk yönetimi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class EmailSender:
    """Email gönderici.

    Email'leri gönderir ve takip eder.

    Attributes:
        _sent: Gönderilen email'ler.
        _queue: Gönderim kuyruğu.
    """

    def __init__(
        self,
        daily_limit: int = 100,
        rate_per_minute: int = 10,
    ) -> None:
        """Göndericiyı başlatır.

        Args:
            daily_limit: Günlük limit.
            rate_per_minute: Dakika limiti.
        """
        self._sent: list[
            dict[str, Any]
        ] = []
        self._queue: list[
            dict[str, Any]
        ] = []
        self._bounces: list[
            dict[str, Any]
        ] = []
        self._daily_limit = daily_limit
        self._rate_per_minute = rate_per_minute
        self._counter = 0
        self._daily_sent = 0
        self._stats = {
            "sent": 0,
            "failed": 0,
            "bounced": 0,
            "queued": 0,
        }

        logger.info(
            "EmailSender baslatildi",
        )

    def send(
        self,
        email_id: str,
        to: str,
        subject: str,
        body: str,
        sender: str = "atlas@example.com",
    ) -> dict[str, Any]:
        """Email gönderir.

        Args:
            email_id: Email ID.
            to: Alıcı.
            subject: Konu.
            body: Gövde.
            sender: Gönderici adresi.

        Returns:
            Gönderim bilgisi.
        """
        # Rate limit kontrolü
        if self._daily_sent >= self._daily_limit:
            return {
                "email_id": email_id,
                "sent": False,
                "error": "daily_limit_reached",
            }

        self._counter += 1
        sid = f"snd_{self._counter}"

        record = {
            "send_id": sid,
            "email_id": email_id,
            "to": to,
            "subject": subject,
            "sender": sender,
            "status": "sent",
            "sent_at": time.time(),
        }
        self._sent.append(record)
        self._daily_sent += 1
        self._stats["sent"] += 1

        return {
            "send_id": sid,
            "email_id": email_id,
            "to": to,
            "status": "sent",
            "sent": True,
        }

    def queue(
        self,
        email_id: str,
        to: str,
        subject: str,
        body: str,
        priority: int = 5,
        scheduled_at: float | None = None,
    ) -> dict[str, Any]:
        """Kuyruğa ekler.

        Args:
            email_id: Email ID.
            to: Alıcı.
            subject: Konu.
            body: Gövde.
            priority: Öncelik (1-10).
            scheduled_at: Zamanlama.

        Returns:
            Kuyruk bilgisi.
        """
        item = {
            "email_id": email_id,
            "to": to,
            "subject": subject,
            "body": body,
            "priority": priority,
            "scheduled_at": scheduled_at,
            "queued_at": time.time(),
        }
        self._queue.append(item)
        self._stats["queued"] += 1

        return {
            "email_id": email_id,
            "queued": True,
            "priority": priority,
            "position": len(self._queue),
        }

    def process_queue(
        self,
        max_items: int = 10,
    ) -> dict[str, Any]:
        """Kuyruğu işler.

        Args:
            max_items: İşlenecek maks kayıt.

        Returns:
            İşlem bilgisi.
        """
        # Önceliğe göre sırala
        self._queue.sort(
            key=lambda x: x["priority"],
        )

        processed = 0
        results = []
        now = time.time()

        while (
            self._queue
            and processed < max_items
        ):
            item = self._queue[0]

            # Zamanlanmış ama henüz vakti gelmemiş
            sched = item.get("scheduled_at")
            if sched and sched > now:
                break

            self._queue.pop(0)
            result = self.send(
                email_id=item["email_id"],
                to=item["to"],
                subject=item["subject"],
                body=item["body"],
            )
            results.append(result)
            processed += 1

        return {
            "processed": processed,
            "remaining": len(self._queue),
            "results": results,
        }

    def track_delivery(
        self,
        send_id: str,
    ) -> dict[str, Any]:
        """Teslimatı takip eder.

        Args:
            send_id: Gönderim ID.

        Returns:
            Takip bilgisi.
        """
        for record in self._sent:
            if record["send_id"] == send_id:
                return {
                    "send_id": send_id,
                    "email_id": record[
                        "email_id"
                    ],
                    "status": record["status"],
                    "to": record["to"],
                    "sent_at": record[
                        "sent_at"
                    ],
                    "delivered": record[
                        "status"
                    ]
                    == "delivered",
                }

        return {
            "error": "send_not_found",
        }

    def mark_delivered(
        self,
        send_id: str,
    ) -> dict[str, Any]:
        """Teslim edildi olarak işaretler.

        Args:
            send_id: Gönderim ID.

        Returns:
            Güncelleme bilgisi.
        """
        for record in self._sent:
            if record["send_id"] == send_id:
                record["status"] = "delivered"
                record["delivered_at"] = (
                    time.time()
                )
                return {
                    "send_id": send_id,
                    "status": "delivered",
                    "updated": True,
                }

        return {"error": "send_not_found"}

    def handle_bounce(
        self,
        send_id: str,
        reason: str = "",
        bounce_type: str = "soft",
    ) -> dict[str, Any]:
        """Bounce işler.

        Args:
            send_id: Gönderim ID.
            reason: Neden.
            bounce_type: Bounce tipi.

        Returns:
            Bounce bilgisi.
        """
        for record in self._sent:
            if record["send_id"] == send_id:
                record["status"] = "bounced"
                bounce = {
                    "send_id": send_id,
                    "email_id": record[
                        "email_id"
                    ],
                    "to": record["to"],
                    "reason": reason,
                    "bounce_type": bounce_type,
                    "bounced_at": time.time(),
                }
                self._bounces.append(bounce)
                self._stats["bounced"] += 1
                return {
                    "send_id": send_id,
                    "bounced": True,
                    "bounce_type": bounce_type,
                    "reason": reason,
                }

        return {"error": "send_not_found"}

    def get_stats(self) -> dict[str, Any]:
        """İstatistikleri döndürür."""
        return {
            **self._stats,
            "daily_sent": self._daily_sent,
            "daily_limit": self._daily_limit,
            "queue_size": len(self._queue),
            "bounce_rate": (
                self._stats["bounced"]
                / max(self._stats["sent"], 1)
            ),
        }

    def reset_daily_counter(self) -> None:
        """Günlük sayacı sıfırlar."""
        self._daily_sent = 0

    @property
    def sent_count(self) -> int:
        """Gönderilen sayısı."""
        return self._stats["sent"]

    @property
    def queue_size(self) -> int:
        """Kuyruk boyutu."""
        return len(self._queue)

    @property
    def bounce_count(self) -> int:
        """Bounce sayısı."""
        return self._stats["bounced"]
