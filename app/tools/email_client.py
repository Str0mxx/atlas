"""ATLAS Gmail API istemci modulu.

Gmail API ile e-posta gonderme ve okuma islemlerini yoneten
yeniden kullanilabilir arac sinifi.

CommunicationAgent bu sinifi kullanarak Gmail islemlerini
gerceklestirebilir. Bagimsiz olarak da kullanilabilir.
"""

import base64
import logging
import re
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.config import settings
from app.models.communication import EmailMessage, InboxMessage

logger = logging.getLogger("atlas.tools.email_client")


class EmailClient:
    """Gmail API istemcisi.

    Gmail API ile e-posta gonderme ve okuma islemlerini yonetir.
    Lazy initialization ile Gmail servisini baslatir.

    Kullanim:
        client = EmailClient()
        sent = client.send(to="user@example.com", subject="Konu", body_html="<p>Merhaba</p>")
        inbox = client.read_inbox(query="is:unread", max_results=10)

    Attributes:
        sender_name: Gonderici adi (settings'ten alinir).
        sender_email: Gonderici e-posta adresi (settings'ten alinir).
    """

    def __init__(self) -> None:
        """EmailClient'i baslatir. Gmail servisi lazy yuklenir."""
        self._gmail_service: Any | None = None
        self.sender_name: str = settings.gmail_sender_name
        self.sender_email: str = settings.gmail_sender_email

    def _get_gmail_service(self) -> Any:
        """Gmail API servisini dondurur (lazy init).

        OAuth2 credentials ile Gmail API v1 servisi olusturur.

        Returns:
            Yapilandirilmis Gmail API servisi.

        Raises:
            ValueError: Gmail kimlik bilgileri eksikse.
        """
        if self._gmail_service is not None:
            return self._gmail_service

        client_id = settings.gmail_client_id
        client_secret = settings.gmail_client_secret.get_secret_value()
        refresh_token = settings.gmail_refresh_token.get_secret_value()

        if not refresh_token:
            raise ValueError("Gmail refresh token yapilandirilmamis.")

        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=["https://www.googleapis.com/auth/gmail.modify"],
        )
        self._gmail_service = build("gmail", "v1", credentials=creds)
        return self._gmail_service

    def send(
        self,
        to: str,
        subject: str,
        body_html: str,
        body_text: str = "",
        thread_id: str | None = None,
    ) -> EmailMessage:
        """Gmail API ile e-posta gonderir.

        Args:
            to: Alici e-posta adresi.
            subject: E-posta konusu.
            body_html: HTML govde icerigi.
            body_text: Duz metin govde icerigi (opsiyonel).
            thread_id: Reply icin Gmail thread ID'si (opsiyonel).

        Returns:
            Gonderilen e-postayi temsil eden EmailMessage.
        """
        service = self._get_gmail_service()

        sender = ""
        if self.sender_email:
            sender = (
                f"{self.sender_name} <{self.sender_email}>"
                if self.sender_name
                else self.sender_email
            )

        raw = self.build_mime(
            to=to,
            subject=subject,
            body_html=body_html,
            body_text=body_text,
            sender=sender,
        )

        send_body: dict[str, str] = {"raw": raw}
        if thread_id:
            send_body["threadId"] = thread_id

        sent_msg = (
            service.users()
            .messages()
            .send(userId="me", body=send_body)
            .execute()
        )

        logger.info("E-posta gonderildi: to=%s, subject=%s", to, subject)

        return EmailMessage(
            message_id=sent_msg.get("id", ""),
            thread_id=sent_msg.get("threadId", ""),
            to=to,
            subject=subject,
            body_html=body_html,
            body_text=body_text,
            sent_at=datetime.now(timezone.utc),
            is_sent=True,
        )

    def read_inbox(
        self,
        query: str = "is:unread",
        max_results: int = 20,
    ) -> list[InboxMessage]:
        """Gmail gelen kutusunu okur.

        Args:
            query: Gmail arama sorgusu (orn: "is:unread", "from:user@example.com").
            max_results: Okunacak maksimum mesaj sayisi.

        Returns:
            Okunan InboxMessage listesi.
        """
        service = self._get_gmail_service()

        result = (
            service.users()
            .messages()
            .list(userId="me", q=query, maxResults=max_results)
            .execute()
        )

        messages: list[InboxMessage] = []
        for msg_ref in result.get("messages", []):
            msg_data = (
                service.users()
                .messages()
                .get(userId="me", id=msg_ref["id"], format="full")
                .execute()
            )
            messages.append(self.parse_message(msg_data))

        logger.info(
            "Gelen kutusu okundu: query='%s', sonuc=%d",
            query,
            len(messages),
        )
        return messages

    def get_message(self, message_id: str) -> InboxMessage:
        """Belirli bir Gmail mesajini getirir.

        Args:
            message_id: Gmail API mesaj ID'si.

        Returns:
            Parse edilmis InboxMessage.
        """
        service = self._get_gmail_service()
        msg_data = (
            service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )
        return self.parse_message(msg_data)

    @staticmethod
    def build_mime(
        to: str,
        subject: str,
        body_html: str,
        body_text: str = "",
        sender: str = "",
    ) -> str:
        """MIME mesaj olusturur ve base64url olarak kodlar.

        Args:
            to: Alici e-posta adresi.
            subject: E-posta konusu.
            body_html: HTML govde.
            body_text: Duz metin govde (opsiyonel).
            sender: Gonderici (opsiyonel, "Ad <email>" formati).

        Returns:
            Base64url kodlanmis MIME mesaj string'i.
        """
        msg = MIMEMultipart("alternative")
        msg["To"] = to
        msg["Subject"] = subject
        if sender:
            msg["From"] = sender

        if body_text:
            msg.attach(MIMEText(body_text, "plain", "utf-8"))
        msg.attach(MIMEText(body_html or " ", "html", "utf-8"))

        return base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")

    @staticmethod
    def parse_message(msg_data: dict[str, Any]) -> InboxMessage:
        """Gmail API mesaj verisini InboxMessage'a donusturur.

        Args:
            msg_data: Gmail API'den gelen mesaj verisi.

        Returns:
            Parse edilmis InboxMessage.
        """
        headers = {
            h["name"].lower(): h["value"]
            for h in msg_data.get("payload", {}).get("headers", [])
        }

        # Govde icerigini ayikla
        body_text = ""
        payload = msg_data.get("payload", {})
        if payload.get("body", {}).get("data"):
            body_text = base64.urlsafe_b64decode(
                payload["body"]["data"],
            ).decode("utf-8", errors="replace")
        elif payload.get("parts"):
            for part in payload["parts"]:
                if (
                    part.get("mimeType") == "text/plain"
                    and part.get("body", {}).get("data")
                ):
                    body_text = base64.urlsafe_b64decode(
                        part["body"]["data"],
                    ).decode("utf-8", errors="replace")
                    break

        # From header parse: "Name <email>" formatini ayristir
        from_header = headers.get("from", "")
        from_match = re.match(r"(.*?)\s*<(.+?)>", from_header)
        from_name = (
            from_match.group(1).strip("\" ") if from_match else ""
        )
        from_email = from_match.group(2) if from_match else from_header

        return InboxMessage(
            message_id=msg_data.get("id", ""),
            thread_id=msg_data.get("threadId", ""),
            from_email=from_email,
            from_name=from_name,
            subject=headers.get("subject", ""),
            snippet=msg_data.get("snippet", ""),
            body_text=body_text,
            labels=msg_data.get("labelIds", []),
        )
