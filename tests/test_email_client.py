"""EmailClient unit testleri.

Gmail API istemcisi davranislari mock'larla test edilir.
"""

import base64
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.tools.email_client import EmailClient


# === Fixture'lar ===


@pytest.fixture
def mock_settings():
    """Test icin settings mock'u."""
    with patch("app.tools.email_client.settings") as mock:
        mock.gmail_sender_name = "Test User"
        mock.gmail_sender_email = "test@example.com"
        mock.gmail_client_id = "test-client-id"
        mock.gmail_client_secret = MagicMock()
        mock.gmail_client_secret.get_secret_value.return_value = "test-client-secret"
        mock.gmail_refresh_token = MagicMock()
        mock.gmail_refresh_token.get_secret_value.return_value = "test-refresh-token"
        yield mock


@pytest.fixture
def email_client(mock_settings) -> EmailClient:
    """Yapilandirilmis EmailClient."""
    return EmailClient()


@pytest.fixture
def mock_gmail_service():
    """Gmail API servisi mock'u."""
    service = MagicMock()
    users = MagicMock()
    messages = MagicMock()
    service.users.return_value = users
    users.messages.return_value = messages
    return service, messages


# === Initialization testleri ===


class TestEmailClientInit:
    """EmailClient baslatma testleri."""

    def test_init_defaults(self, mock_settings) -> None:
        """Varsayilan yapilandirma."""
        client = EmailClient()
        assert client.sender_name == "Test User"
        assert client.sender_email == "test@example.com"
        assert client._gmail_service is None

    def test_lazy_service_init(self, mock_settings) -> None:
        """Gmail servisi lazy baslatilir."""
        client = EmailClient()
        assert client._gmail_service is None


# === Gmail Service testleri ===


class TestGetGmailService:
    """Gmail API servisi baslatma testleri."""

    @patch("app.tools.email_client.build")
    @patch("app.tools.email_client.Credentials")
    def test_service_created(
        self, mock_creds_cls, mock_build, email_client,
    ) -> None:
        """Gmail servisi olusturulur."""
        mock_creds = MagicMock()
        mock_creds_cls.return_value = mock_creds
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        result = email_client._get_gmail_service()

        assert result is mock_service
        mock_creds_cls.assert_called_once()
        mock_build.assert_called_once_with("gmail", "v1", credentials=mock_creds)

    @patch("app.tools.email_client.build")
    @patch("app.tools.email_client.Credentials")
    def test_service_cached(
        self, mock_creds_cls, mock_build, email_client,
    ) -> None:
        """Servis ikinci cagirimda cache'ten gelir."""
        mock_build.return_value = MagicMock()

        email_client._get_gmail_service()
        email_client._get_gmail_service()

        # build sadece 1 kez cagirilmali
        assert mock_build.call_count == 1

    def test_missing_refresh_token(self, mock_settings) -> None:
        """Refresh token yoksa ValueError."""
        mock_settings.gmail_refresh_token.get_secret_value.return_value = ""
        client = EmailClient()

        with pytest.raises(ValueError, match="refresh token"):
            client._get_gmail_service()


# === Send testleri ===


class TestSend:
    """E-posta gonderme testleri."""

    def test_send_basic(self, email_client, mock_gmail_service) -> None:
        """Basit e-posta gonderme."""
        service, messages = mock_gmail_service

        messages.send.return_value.execute.return_value = {
            "id": "msg-123",
            "threadId": "thread-456",
        }

        email_client._gmail_service = service

        result = email_client.send(
            to="recipient@example.com",
            subject="Test Konusu",
            body_html="<p>Merhaba</p>",
        )

        assert result.message_id == "msg-123"
        assert result.thread_id == "thread-456"
        assert result.to == "recipient@example.com"
        assert result.subject == "Test Konusu"
        assert result.is_sent is True
        assert result.sent_at is not None

    def test_send_with_thread_id(self, email_client, mock_gmail_service) -> None:
        """Thread reply olarak gonderme."""
        service, messages = mock_gmail_service

        messages.send.return_value.execute.return_value = {
            "id": "msg-reply",
            "threadId": "thread-existing",
        }

        email_client._gmail_service = service

        result = email_client.send(
            to="recipient@example.com",
            subject="Re: Test",
            body_html="<p>Yanit</p>",
            thread_id="thread-existing",
        )

        # send body'de threadId olmali
        send_call = messages.send.call_args
        send_body = send_call.kwargs.get("body") or send_call[1].get("body")
        assert send_body["threadId"] == "thread-existing"

    def test_send_with_text_body(self, email_client, mock_gmail_service) -> None:
        """Duz metin govde ile gonderme."""
        service, messages = mock_gmail_service

        messages.send.return_value.execute.return_value = {
            "id": "msg-text",
            "threadId": "thread-text",
        }

        email_client._gmail_service = service

        result = email_client.send(
            to="recipient@example.com",
            subject="Text Test",
            body_html="<p>HTML</p>",
            body_text="Plain text",
        )

        assert result.body_text == "Plain text"
        assert result.body_html == "<p>HTML</p>"


# === BuildMime testleri ===


class TestBuildMime:
    """MIME mesaj olusturma testleri."""

    def test_basic_mime(self) -> None:
        """Temel MIME olusturma."""
        raw = EmailClient.build_mime(
            to="recipient@example.com",
            subject="Test",
            body_html="<p>Merhaba</p>",
        )

        # base64url kodlanmis olmali
        decoded = base64.urlsafe_b64decode(raw)
        content = decoded.decode("utf-8", errors="replace")
        assert "recipient@example.com" in content
        assert "Test" in content

    def test_mime_with_sender(self) -> None:
        """Sender bilgisi ile MIME."""
        raw = EmailClient.build_mime(
            to="recipient@example.com",
            subject="Test",
            body_html="<p>HTML</p>",
            sender="Fatih <fatih@example.com>",
        )

        decoded = base64.urlsafe_b64decode(raw)
        content = decoded.decode("utf-8", errors="replace")
        assert "fatih@example.com" in content

    def test_mime_with_text_body(self) -> None:
        """Duz metin ve HTML govde ile MIME."""
        raw = EmailClient.build_mime(
            to="recipient@example.com",
            subject="Test",
            body_html="<p>HTML</p>",
            body_text="Plain text",
        )

        decoded = base64.urlsafe_b64decode(raw)
        content = decoded.decode("utf-8", errors="replace")
        assert "Plain text" in content or "text/plain" in content

    def test_mime_returns_string(self) -> None:
        """Donusu string olmali."""
        raw = EmailClient.build_mime(
            to="test@test.com",
            subject="Test",
            body_html="<p>X</p>",
        )
        assert isinstance(raw, str)


# === ReadInbox testleri ===


class TestReadInbox:
    """Gelen kutusu okuma testleri."""

    def test_read_inbox_empty(self, email_client, mock_gmail_service) -> None:
        """Bos gelen kutusu."""
        service, messages = mock_gmail_service

        messages.list.return_value.execute.return_value = {"messages": []}

        email_client._gmail_service = service
        result = email_client.read_inbox(query="is:unread", max_results=10)

        assert result == []

    def test_read_inbox_no_messages_key(self, email_client, mock_gmail_service) -> None:
        """API'de messages anahtari olmayan yanit."""
        service, messages = mock_gmail_service

        messages.list.return_value.execute.return_value = {}

        email_client._gmail_service = service
        result = email_client.read_inbox()

        assert result == []

    def test_read_inbox_with_messages(self, email_client, mock_gmail_service) -> None:
        """Mesajli gelen kutusu."""
        service, messages = mock_gmail_service

        # list sonucu
        messages.list.return_value.execute.return_value = {
            "messages": [{"id": "msg-1"}, {"id": "msg-2"}],
        }

        # Her mesaj icin get sonucu
        body_data = base64.urlsafe_b64encode(b"Test body").decode()
        msg_detail = {
            "id": "msg-1",
            "threadId": "thread-1",
            "snippet": "Test snippet",
            "labelIds": ["INBOX", "UNREAD"],
            "payload": {
                "headers": [
                    {"name": "From", "value": "Sender <sender@example.com>"},
                    {"name": "Subject", "value": "Test Subject"},
                ],
                "body": {"data": body_data},
            },
        }

        messages.get.return_value.execute.return_value = msg_detail

        email_client._gmail_service = service
        result = email_client.read_inbox(query="is:unread", max_results=5)

        assert len(result) == 2
        assert result[0].message_id == "msg-1"
        assert result[0].subject == "Test Subject"
        assert result[0].from_email == "sender@example.com"


# === GetMessage testleri ===


class TestGetMessage:
    """Tek mesaj getirme testleri."""

    def test_get_message(self, email_client, mock_gmail_service) -> None:
        """Tek mesaj getirme."""
        service, messages = mock_gmail_service

        msg_detail = {
            "id": "msg-specific",
            "threadId": "thread-specific",
            "snippet": "Specific snippet",
            "labelIds": ["INBOX"],
            "payload": {
                "headers": [
                    {"name": "From", "value": "user@example.com"},
                    {"name": "Subject", "value": "Specific Subject"},
                ],
                "body": {},
            },
        }

        messages.get.return_value.execute.return_value = msg_detail

        email_client._gmail_service = service
        result = email_client.get_message("msg-specific")

        assert result.message_id == "msg-specific"
        assert result.subject == "Specific Subject"


# === ParseMessage testleri ===


class TestParseMessage:
    """Gmail API mesaj parse testleri."""

    def test_parse_basic_message(self) -> None:
        """Temel mesaj parse."""
        msg_data = {
            "id": "parse-test",
            "threadId": "thread-parse",
            "snippet": "Parse snippet",
            "labelIds": ["INBOX", "UNREAD"],
            "payload": {
                "headers": [
                    {"name": "From", "value": "Test User <test@example.com>"},
                    {"name": "Subject", "value": "Parse Test"},
                ],
                "body": {},
            },
        }

        result = EmailClient.parse_message(msg_data)

        assert result.message_id == "parse-test"
        assert result.thread_id == "thread-parse"
        assert result.from_email == "test@example.com"
        assert result.from_name == "Test User"
        assert result.subject == "Parse Test"
        assert result.snippet == "Parse snippet"
        assert "INBOX" in result.labels

    def test_parse_body_from_payload(self) -> None:
        """Govde payload body'den parse edilir."""
        body_text = "Test body content"
        encoded = base64.urlsafe_b64encode(body_text.encode()).decode()

        msg_data = {
            "id": "body-test",
            "threadId": "thread-body",
            "snippet": "",
            "labelIds": [],
            "payload": {
                "headers": [
                    {"name": "From", "value": "sender@test.com"},
                    {"name": "Subject", "value": "Body Test"},
                ],
                "body": {"data": encoded},
            },
        }

        result = EmailClient.parse_message(msg_data)
        assert result.body_text == "Test body content"

    def test_parse_multipart_body(self) -> None:
        """Multipart mesajdan text/plain govde cikarir."""
        body_text = "Multipart plain text"
        encoded = base64.urlsafe_b64encode(body_text.encode()).decode()

        msg_data = {
            "id": "multipart-test",
            "threadId": "thread-mp",
            "snippet": "",
            "labelIds": [],
            "payload": {
                "headers": [
                    {"name": "From", "value": "mp@test.com"},
                    {"name": "Subject", "value": "Multipart"},
                ],
                "body": {},
                "parts": [
                    {"mimeType": "text/html", "body": {"data": "html-data"}},
                    {"mimeType": "text/plain", "body": {"data": encoded}},
                ],
            },
        }

        result = EmailClient.parse_message(msg_data)
        assert result.body_text == "Multipart plain text"

    def test_parse_from_without_name(self) -> None:
        """Adsiz From header parse."""
        msg_data = {
            "id": "noname-test",
            "threadId": "thread-nn",
            "snippet": "",
            "labelIds": [],
            "payload": {
                "headers": [
                    {"name": "From", "value": "noname@test.com"},
                    {"name": "Subject", "value": "No Name"},
                ],
                "body": {},
            },
        }

        result = EmailClient.parse_message(msg_data)
        assert result.from_email == "noname@test.com"
        assert result.from_name == ""

    def test_parse_quoted_from_name(self) -> None:
        """Tirnak isaretli From adi."""
        msg_data = {
            "id": "quoted-test",
            "threadId": "thread-q",
            "snippet": "",
            "labelIds": [],
            "payload": {
                "headers": [
                    {"name": "From", "value": '"Quoted Name" <quoted@test.com>'},
                    {"name": "Subject", "value": "Quoted"},
                ],
                "body": {},
            },
        }

        result = EmailClient.parse_message(msg_data)
        assert result.from_email == "quoted@test.com"
        assert result.from_name == "Quoted Name"

    def test_parse_missing_headers(self) -> None:
        """Eksik header'larla parse."""
        msg_data = {
            "id": "minimal",
            "threadId": "thread-min",
            "snippet": "",
            "payload": {"headers": [], "body": {}},
        }

        result = EmailClient.parse_message(msg_data)
        assert result.message_id == "minimal"
        assert result.subject == ""
        assert result.from_email == ""
