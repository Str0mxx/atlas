"""ATLAS Çok Kanal Orkestratörü modülü.

Tam çok kanal yönetimi,
Telegram + WhatsApp + Email + Voice,
birleşik deneyim, analitik, raporlama.
"""

import logging
from typing import Any

from app.core.multichannel.availability_tracker import (
    AvailabilityTracker,
)
from app.core.multichannel.channel_preference_engine import (
    ChannelPreferenceEngine,
)
from app.core.multichannel.channel_router import (
    ChannelRouter,
)
from app.core.multichannel.command_interpreter import (
    CommandInterpreter,
)
from app.core.multichannel.context_carrier import (
    ContextCarrier,
)
from app.core.multichannel.escalation_path_manager import (
    EscalationPathManager,
)
from app.core.multichannel.response_formatter import (
    ResponseFormatter,
)
from app.core.multichannel.unified_inbox import (
    UnifiedInbox,
)

logger = logging.getLogger(__name__)


class MultiChannelOrchestrator:
    """Çok kanal orkestratörü.

    Tüm kanal bileşenlerini koordine eder.

    Attributes:
        router: Kanal yönlendirici.
        context: Bağlam taşıyıcı.
        availability: Müsaitlik takipçisi.
        interpreter: Komut yorumlayıcı.
        formatter: Yanıt biçimleyici.
        preferences: Kanal tercih motoru.
        escalation: Eskalasyon yöneticisi.
        inbox: Birleşik gelen kutusu.
    """

    def __init__(
        self,
        default_channel: str = "telegram",
        auto_escalate: bool = True,
        context_timeout: int = 30,
    ) -> None:
        """Orkestratörü başlatır.

        Args:
            default_channel: Varsayılan kanal.
            auto_escalate: Otomatik eskalasyon.
            context_timeout: Bağlam zaman aşımı (dk).
        """
        self.router = ChannelRouter()
        self.context = ContextCarrier(
            timeout_minutes=context_timeout,
        )
        self.availability = AvailabilityTracker()
        self.interpreter = CommandInterpreter()
        self.formatter = ResponseFormatter()
        self.preferences = (
            ChannelPreferenceEngine()
        )
        self.escalation = EscalationPathManager(
            auto_escalate=auto_escalate,
        )
        self.inbox = UnifiedInbox()

        self._default_channel = default_channel
        self._stats = {
            "messages_processed": 0,
            "responses_sent": 0,
        }

        logger.info(
            "MultiChannelOrchestrator "
            "baslatildi",
        )

    def process_message(
        self,
        content: str,
        channel: str,
        sender: str = "",
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Mesaj işler.

        Args:
            content: Mesaj içeriği.
            channel: Kaynak kanal.
            sender: Gönderici.
            user_id: Kullanıcı ID.

        Returns:
            İşleme bilgisi.
        """
        uid = user_id or sender

        # 1) Gelen kutusuna ekle
        msg = self.inbox.receive_message(
            content=content,
            channel=channel,
            sender=sender,
        )

        # 2) Komutu yorumla
        command = self.interpreter.parse(
            content, channel,
        )

        # 3) Bağlam güncelle
        self.context.sync_state(uid, {
            "last_channel": channel,
            "last_message": content,
            "last_intent": command["intent"],
        })

        # 4) Müsaitlik güncelle
        self.availability.set_presence(
            uid, "online", channel,
        )

        # 5) Tercih öğren
        self.preferences.learn_preference(
            uid, channel,
        )

        self._stats["messages_processed"] += 1

        return {
            "message_id": msg["message_id"],
            "channel": channel,
            "intent": command["intent"],
            "params": command["params"],
            "user_id": uid,
        }

    def send_response(
        self,
        user_id: str,
        content: str,
        channel: str | None = None,
        urgency: str = "medium",
    ) -> dict[str, Any]:
        """Yanıt gönderir.

        Args:
            user_id: Kullanıcı ID.
            content: Yanıt içeriği.
            channel: Hedef kanal.
            urgency: Aciliyet.

        Returns:
            Gönderme bilgisi.
        """
        # Kanal belirleme
        if not channel:
            rec = self.preferences.recommend_channel(
                user_id, urgency=urgency,
            )
            channel = rec["recommended"]

        # Yanıtı biçimle
        formatted = self.formatter.format_response(
            content, channel,
        )

        # Yönlendir
        route = self.router.route_message(
            content=formatted["formatted"],
            target_channel=channel,
            priority=self._urgency_to_priority(
                urgency,
            ),
        )

        self._stats["responses_sent"] += 1

        return {
            "user_id": user_id,
            "channel": channel,
            "formatted_content": formatted[
                "formatted"
            ],
            "route_id": route.get("route_id"),
            "urgency": urgency,
        }

    def switch_channel(
        self,
        user_id: str,
        from_channel: str,
        to_channel: str,
    ) -> dict[str, Any]:
        """Kanal değiştirir.

        Args:
            user_id: Kullanıcı ID.
            from_channel: Kaynak kanal.
            to_channel: Hedef kanal.

        Returns:
            Değiştirme bilgisi.
        """
        transfer = self.context.transfer_context(
            user_id, from_channel, to_channel,
        )

        self.availability.set_presence(
            user_id, "online", to_channel,
        )

        return {
            "user_id": user_id,
            "from_channel": from_channel,
            "to_channel": to_channel,
            "context_transferred": transfer[
                "transferred"
            ],
        }

    def escalate_message(
        self,
        user_id: str,
        current_channel: str,
        reason: str = "no_response",
    ) -> dict[str, Any]:
        """Mesajı eskalasyon eder.

        Args:
            user_id: Kullanıcı ID.
            current_channel: Mevcut kanal.
            reason: Neden.

        Returns:
            Eskalasyon bilgisi.
        """
        esc = self.escalation.escalate(
            from_channel=current_channel,
            reason=reason,
        )

        # Bağlamı yeni kanala taşı
        self.context.transfer_context(
            user_id,
            current_channel,
            esc["to_channel"],
        )

        return {
            "user_id": user_id,
            "escalated_from": current_channel,
            "escalated_to": esc["to_channel"],
            "reason": reason,
        }

    def _urgency_to_priority(
        self,
        urgency: str,
    ) -> int:
        """Aciliyeti önceliğe çevirir."""
        mapping = {
            "critical": 10,
            "high": 8,
            "medium": 5,
            "low": 3,
            "routine": 1,
        }
        return mapping.get(urgency, 5)

    def get_analytics(self) -> dict[str, Any]:
        """Analitik raporu.

        Returns:
            Rapor.
        """
        return {
            "messages_processed": self._stats[
                "messages_processed"
            ],
            "responses_sent": self._stats[
                "responses_sent"
            ],
            "active_channels": (
                self.router.active_channel_count
            ),
            "total_routes": (
                self.router.routed_count
            ),
            "active_sessions": (
                self.context.active_session_count
            ),
            "context_transfers": (
                self.context.transfer_count
            ),
            "online_users": (
                self.availability
                .online_user_count
            ),
            "inbox_messages": (
                self.inbox.message_count
            ),
            "unread_messages": (
                self.inbox.unread_count
            ),
            "escalations": (
                self.escalation.escalation_count
            ),
            "commands_parsed": (
                self.interpreter.command_count
            ),
            "formats_applied": (
                self.formatter.format_count
            ),
        }

    def get_status(self) -> dict[str, Any]:
        """Durum bilgisi.

        Returns:
            Durum.
        """
        return {
            "messages_processed": self._stats[
                "messages_processed"
            ],
            "active_channels": (
                self.router.active_channel_count
            ),
            "active_sessions": (
                self.context.active_session_count
            ),
            "unread_messages": (
                self.inbox.unread_count
            ),
        }

    @property
    def messages_processed(self) -> int:
        """İşlenen mesaj sayısı."""
        return self._stats[
            "messages_processed"
        ]
