"""ATLAS Dış İletişim Orkestratörü modülü.

Tam iletişim pipeline'ı,
Compose → Send → Track → Follow-up → Analyze,
çok kanallı outreach, analitik.
"""

import logging
from typing import Any

from app.core.extcomm.campaign_manager import (
    CampaignManager,
)
from app.core.extcomm.contact_database import (
    ContactDatabase,
)
from app.core.extcomm.email_composer import (
    EmailComposer,
)
from app.core.extcomm.email_sender import (
    EmailSender,
)
from app.core.extcomm.followup_manager import (
    FollowUpManager,
)
from app.core.extcomm.linkedin_connector import (
    LinkedInConnector,
)
from app.core.extcomm.response_handler import (
    ResponseHandler,
)
from app.core.extcomm.tone_adapter import (
    ToneAdapter,
)

logger = logging.getLogger(__name__)


class ExtCommOrchestrator:
    """Dış iletişim orkestratörü.

    Tüm iletişim bileşenlerini koordine eder.

    Attributes:
        composer: Email yazıcı.
        sender: Email gönderici.
        linkedin: LinkedIn bağlayıcı.
        followup: Takip yöneticisi.
        responses: Yanıt işleyici.
        contacts: İletişim veritabanı.
        tone: Ton adaptörü.
        campaigns: Kampanya yöneticisi.
    """

    def __init__(
        self,
        default_tone: str = "professional",
        daily_send_limit: int = 100,
        followup_days: int = 3,
    ) -> None:
        """Orkestratörü başlatır.

        Args:
            default_tone: Varsayılan ton.
            daily_send_limit: Günlük limit.
            followup_days: Takip günü.
        """
        self.composer = EmailComposer()
        self.sender = EmailSender(
            daily_limit=daily_send_limit,
        )
        self.linkedin = LinkedInConnector()
        self.followup = FollowUpManager(
            default_days=followup_days,
        )
        self.responses = ResponseHandler()
        self.contacts = ContactDatabase()
        self.tone = ToneAdapter(
            default_tone=default_tone,
        )
        self.campaigns = CampaignManager()

        self._stats = {
            "outreach_completed": 0,
            "pipelines_run": 0,
            "errors": 0,
        }

        logger.info(
            "ExtCommOrchestrator baslatildi",
        )

    def outreach(
        self,
        contact_name: str,
        contact_email: str,
        subject: str,
        body: str,
        company: str = "",
        tone: str | None = None,
        auto_followup: bool = True,
        channel: str = "email",
    ) -> dict[str, Any]:
        """Tam outreach pipeline'ı çalıştırır.

        Args:
            contact_name: Kişi adı.
            contact_email: Kişi email.
            subject: Konu.
            body: Gövde.
            company: Şirket.
            tone: Ton.
            auto_followup: Otomatik takip.
            channel: Kanal.

        Returns:
            Outreach bilgisi.
        """
        # 1) Kişi ekle/güncelle
        contact = self.contacts.add_contact(
            name=contact_name,
            email=contact_email,
            company=company,
            channel=channel,
        )
        contact_id = contact["contact_id"]

        # 2) Ton analizi
        used_tone = tone or "professional"
        if not tone:
            analysis = (
                self.tone.analyze_recipient(
                    name=contact_name,
                    company=company,
                )
            )
            used_tone = analysis[
                "recommended_tone"
            ]

        # 3) Email oluştur
        composed = self.composer.compose(
            to=contact_email,
            subject=subject,
            body=body,
            tone=used_tone,
            sender="ATLAS",
        )
        email_id = composed["email_id"]

        # 4) Kişiselleştir
        self.composer.personalize(
            email_id=email_id,
            recipient_info={
                "name": contact_name,
                "company": company,
            },
        )

        # 5) Gönder
        sent = self.sender.send(
            email_id=email_id,
            to=contact_email,
            subject=composed["subject"],
            body=composed["body"],
        )

        # 6) Etkileşim kaydet
        self.contacts.log_interaction(
            contact_id=contact_id,
            interaction_type="email_sent",
            description=subject,
        )

        # 7) Takip planla
        followup_id = None
        if auto_followup and sent.get(
            "sent"
        ):
            fu = self.followup.schedule_followup(
                contact_id=contact_id,
                email_id=email_id,
            )
            followup_id = fu["followup_id"]

        self._stats[
            "outreach_completed"
        ] += 1
        self._stats["pipelines_run"] += 1

        return {
            "success": True,
            "contact_id": contact_id,
            "email_id": email_id,
            "send_id": sent.get("send_id"),
            "sent": sent.get("sent", False),
            "tone": used_tone,
            "followup_id": followup_id,
            "channel": channel,
        }

    def process_incoming(
        self,
        email_id: str,
        from_addr: str,
        subject: str,
        body: str,
    ) -> dict[str, Any]:
        """Gelen yanıtı işler.

        Args:
            email_id: İlgili email ID.
            from_addr: Gönderen.
            subject: Konu.
            body: Gövde.

        Returns:
            İşlem bilgisi.
        """
        # Yanıtı işle
        result = (
            self.responses.process_response(
                email_id=email_id,
                from_addr=from_addr,
                subject=subject,
                body=body,
            )
        )

        # İlişki puanı güncelle
        sentiment = result.get("sentiment")
        contacts = (
            self.contacts.search_contacts(
                from_addr, limit=1,
            )
        )
        if contacts:
            cid = contacts[0]["contact_id"]
            delta = {
                "positive": 10.0,
                "neutral": 1.0,
                "negative": -5.0,
            }.get(sentiment, 0.0)

            self.contacts.update_relationship_score(
                cid, delta,
            )

            self.contacts.log_interaction(
                contact_id=cid,
                interaction_type=(
                    "response_received"
                ),
                description=subject,
                outcome=sentiment,
            )

        return {
            "response_id": result[
                "response_id"
            ],
            "sentiment": sentiment,
            "intent": result.get("intent"),
            "category": result.get(
                "category",
            ),
            "processed": True,
        }

    def launch_campaign(
        self,
        name: str,
        contact_ids: list[str],
        subject: str,
        body: str,
        tone: str = "professional",
    ) -> dict[str, Any]:
        """Kampanya başlatır.

        Args:
            name: Kampanya adı.
            contact_ids: Kişi ID'leri.
            subject: Konu.
            body: Gövde.
            tone: Ton.

        Returns:
            Kampanya bilgisi.
        """
        campaign = (
            self.campaigns.create_campaign(
                name=name,
                contact_ids=contact_ids,
            )
        )
        campaign_id = campaign["campaign_id"]

        sent_count = 0
        for cid in contact_ids:
            contact = self.contacts.get_contact(
                cid,
            )
            if "error" in contact:
                continue

            composed = self.composer.compose(
                to=contact["email"],
                subject=subject,
                body=body,
                tone=tone,
            )

            result = self.sender.send(
                email_id=composed["email_id"],
                to=contact["email"],
                subject=composed["subject"],
                body=composed["body"],
            )

            if result.get("sent"):
                self.campaigns.record_send(
                    campaign_id, cid,
                )
                sent_count += 1

        return {
            "campaign_id": campaign_id,
            "name": name,
            "contacts": len(contact_ids),
            "sent": sent_count,
            "launched": True,
        }

    def get_analytics(
        self,
    ) -> dict[str, Any]:
        """Analitik raporu.

        Returns:
            Rapor.
        """
        return {
            "outreach_completed": (
                self._stats[
                    "outreach_completed"
                ]
            ),
            "pipelines_run": self._stats[
                "pipelines_run"
            ],
            "emails_composed": (
                self.composer.compose_count
            ),
            "emails_sent": (
                self.sender.sent_count
            ),
            "linkedin_connections": (
                self.linkedin.connection_count
            ),
            "linkedin_messages": (
                self.linkedin.message_count
            ),
            "followups_pending": (
                self.followup.pending_count
            ),
            "responses_processed": (
                self.responses.response_count
            ),
            "contacts_total": (
                self.contacts.contact_count
            ),
            "campaigns_active": (
                self.campaigns.active_count
            ),
            "tone_adaptations": (
                self.tone.adaptation_count
            ),
            "errors": self._stats["errors"],
        }

    def get_status(self) -> dict[str, Any]:
        """Durum bilgisi.

        Returns:
            Durum.
        """
        return {
            "outreach_completed": (
                self._stats[
                    "outreach_completed"
                ]
            ),
            "emails_sent": (
                self.sender.sent_count
            ),
            "contacts": (
                self.contacts.contact_count
            ),
            "campaigns": (
                self.campaigns.campaign_count
            ),
            "pending_followups": (
                self.followup.pending_count
            ),
        }

    @property
    def outreach_count(self) -> int:
        """Outreach sayısı."""
        return self._stats[
            "outreach_completed"
        ]
