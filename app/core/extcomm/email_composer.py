"""ATLAS Email Yazıcı modülü.

Professional şablonlar, ton ayarı,
kişiselleştirme, konu optimizasyonu,
ek yönetimi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class EmailComposer:
    """Email yazıcı.

    Profesyonel email'ler oluşturur.

    Attributes:
        _emails: Email geçmişi.
        _templates: Şablon kütüphanesi.
    """

    TEMPLATES = {
        "introduction": {
            "subject": "Introduction: {sender}",
            "body": (
                "Dear {recipient},\n\n"
                "I hope this message finds you well. "
                "My name is {sender} and I am reaching "
                "out regarding {topic}.\n\n"
                "{body}\n\n"
                "Best regards,\n{sender}"
            ),
        },
        "follow_up": {
            "subject": "Following up: {topic}",
            "body": (
                "Dear {recipient},\n\n"
                "I wanted to follow up on our "
                "previous conversation about "
                "{topic}.\n\n"
                "{body}\n\n"
                "Looking forward to hearing "
                "from you.\n\n"
                "Best regards,\n{sender}"
            ),
        },
        "proposal": {
            "subject": "Proposal: {topic}",
            "body": (
                "Dear {recipient},\n\n"
                "Thank you for your interest. "
                "Please find below our proposal "
                "for {topic}.\n\n"
                "{body}\n\n"
                "Please let us know if you have "
                "any questions.\n\n"
                "Best regards,\n{sender}"
            ),
        },
        "thank_you": {
            "subject": "Thank you - {topic}",
            "body": (
                "Dear {recipient},\n\n"
                "Thank you for {topic}. "
                "We truly appreciate your "
                "time and consideration.\n\n"
                "{body}\n\n"
                "Warm regards,\n{sender}"
            ),
        },
        "meeting_request": {
            "subject": "Meeting Request: {topic}",
            "body": (
                "Dear {recipient},\n\n"
                "I would like to schedule a "
                "meeting to discuss {topic}.\n\n"
                "{body}\n\n"
                "Please let me know your "
                "availability.\n\n"
                "Best regards,\n{sender}"
            ),
        },
    }

    def __init__(self) -> None:
        """Yazıcıyı başlatır."""
        self._emails: list[
            dict[str, Any]
        ] = []
        self._templates: dict[
            str, dict[str, str]
        ] = dict(self.TEMPLATES)
        self._counter = 0
        self._stats = {
            "composed": 0,
            "personalized": 0,
            "template_used": 0,
        }

        logger.info(
            "EmailComposer baslatildi",
        )

    def compose(
        self,
        to: str,
        subject: str,
        body: str,
        tone: str = "professional",
        sender: str = "ATLAS",
        attachments: list[str] | None = None,
    ) -> dict[str, Any]:
        """Email oluşturur.

        Args:
            to: Alıcı.
            subject: Konu.
            body: Gövde.
            tone: Ton.
            sender: Gönderici.
            attachments: Ekler.

        Returns:
            Email bilgisi.
        """
        self._counter += 1
        eid = f"eml_{self._counter}"

        # Ton ayarla
        adjusted_body = self._adjust_tone(
            body, tone,
        )

        # Konu optimizasyonu
        optimized_subject = (
            self._optimize_subject(subject)
        )

        email = {
            "email_id": eid,
            "to": to,
            "subject": optimized_subject,
            "body": adjusted_body,
            "tone": tone,
            "sender": sender,
            "attachments": attachments or [],
            "word_count": len(
                adjusted_body.split()
            ),
            "created_at": time.time(),
        }
        self._emails.append(email)
        self._stats["composed"] += 1

        return {
            "email_id": eid,
            "to": to,
            "subject": optimized_subject,
            "body": adjusted_body,
            "tone": tone,
            "attachments": len(
                attachments or [],
            ),
            "word_count": email["word_count"],
            "composed": True,
        }

    def compose_from_template(
        self,
        template_name: str,
        to: str,
        variables: dict[str, str],
        tone: str = "professional",
    ) -> dict[str, Any]:
        """Şablondan email oluşturur.

        Args:
            template_name: Şablon adı.
            to: Alıcı.
            variables: Değişkenler.
            tone: Ton.

        Returns:
            Email bilgisi.
        """
        tmpl = self._templates.get(
            template_name,
        )
        if not tmpl:
            return {
                "error": "template_not_found",
            }

        subject = tmpl["subject"]
        body = tmpl["body"]

        for key, val in variables.items():
            subject = subject.replace(
                f"{{{key}}}", val,
            )
            body = body.replace(
                f"{{{key}}}", val,
            )

        self._stats["template_used"] += 1

        return self.compose(
            to=to,
            subject=subject,
            body=body,
            tone=tone,
            sender=variables.get(
                "sender", "ATLAS",
            ),
        )

    def personalize(
        self,
        email_id: str,
        recipient_info: dict[str, Any],
    ) -> dict[str, Any]:
        """Email'i kişiselleştirir.

        Args:
            email_id: Email ID.
            recipient_info: Alıcı bilgisi.

        Returns:
            Kişiselleştirme bilgisi.
        """
        email = None
        for e in self._emails:
            if e["email_id"] == email_id:
                email = e
                break

        if not email:
            return {"error": "email_not_found"}

        name = recipient_info.get("name", "")
        company = recipient_info.get(
            "company", "",
        )
        role = recipient_info.get("role", "")

        body = email["body"]
        if name:
            body = body.replace(
                "Dear ", f"Dear {name}, ",
                1,
            ) if "Dear ," not in body else body

        additions = []
        if company:
            additions.append(
                f"at {company}"
            )
        if role:
            additions.append(
                f"as {role}"
            )

        email["personalized"] = True
        email["recipient_info"] = recipient_info
        self._stats["personalized"] += 1

        return {
            "email_id": email_id,
            "personalized": True,
            "fields_used": list(
                recipient_info.keys(),
            ),
        }

    def _adjust_tone(
        self,
        text: str,
        tone: str,
    ) -> str:
        """Tonu ayarlar."""
        if tone == "formal":
            text = text.replace(
                "Hi ", "Dear ",
            )
            text = text.replace(
                "Thanks", "Thank you",
            )
        elif tone == "casual":
            text = text.replace(
                "Dear ", "Hi ",
            )
            text = text.replace(
                "Best regards",
                "Cheers",
            )
        elif tone == "urgent":
            if not text.startswith(
                "URGENT:"
            ):
                text = (
                    "This requires your "
                    "immediate attention.\n\n"
                    + text
                )
        return text

    def _optimize_subject(
        self,
        subject: str,
    ) -> str:
        """Konu satırını optimize eder."""
        # Karakter limiti
        if len(subject) > 60:
            subject = subject[:57] + "..."

        # Başlık stili
        if subject and not subject[0].isupper():
            subject = (
                subject[0].upper()
                + subject[1:]
            )

        return subject

    def add_template(
        self,
        name: str,
        subject: str,
        body: str,
    ) -> dict[str, Any]:
        """Şablon ekler.

        Args:
            name: Şablon adı.
            subject: Konu şablonu.
            body: Gövde şablonu.

        Returns:
            Ekleme bilgisi.
        """
        self._templates[name] = {
            "subject": subject,
            "body": body,
        }
        return {
            "name": name,
            "added": True,
            "total_templates": len(
                self._templates,
            ),
        }

    def get_templates(
        self,
    ) -> list[str]:
        """Şablon isimlerini döndürür."""
        return list(self._templates.keys())

    @property
    def compose_count(self) -> int:
        """Oluşturulan email sayısı."""
        return self._stats["composed"]

    @property
    def template_count(self) -> int:
        """Şablon sayısı."""
        return len(self._templates)
