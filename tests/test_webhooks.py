"""Webhook endpoint'leri unit testleri.

FastAPI TestClient ile webhook davranislari test edilir.
"""

import hashlib
import hmac
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.webhooks import (
    AlertSeverity,
    WebhookSource,
    _verify_signature,
    router,
)
from app.main import app


@pytest.fixture
def client() -> TestClient:
    """FastAPI test istemcisi."""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def webhook_secret() -> str:
    """Test webhook secret'i."""
    return "test-webhook-secret-key"


def _make_signature(body: bytes, secret: str) -> str:
    """Test icin HMAC-SHA256 imza olusturur."""
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


# === Imza dogrulama testleri ===


class TestVerifySignature:
    """HMAC-SHA256 imza dogrulama testleri."""

    def test_valid_signature(self) -> None:
        body = b'{"test": "data"}'
        secret = "my-secret"
        sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        assert _verify_signature(body, sig, secret)

    def test_valid_signature_with_prefix(self) -> None:
        body = b'{"test": "data"}'
        secret = "my-secret"
        sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        assert _verify_signature(body, sig, secret)

    def test_invalid_signature(self) -> None:
        body = b'{"test": "data"}'
        assert not _verify_signature(body, "invalid-sig", "my-secret")

    def test_empty_secret(self) -> None:
        body = b'{"test": "data"}'
        assert not _verify_signature(body, "any-sig", "")

    def test_tampered_body(self) -> None:
        secret = "my-secret"
        original = b'{"amount": 100}'
        tampered = b'{"amount": 999}'
        sig = hmac.new(secret.encode(), original, hashlib.sha256).hexdigest()
        assert not _verify_signature(tampered, sig, secret)


# === Webhook verify endpoint testleri ===


class TestVerifyEndpoint:
    """GET /webhooks/verify testleri."""

    def test_verify_no_secret(self, client: TestClient) -> None:
        """Secret ayarlanmamissa dogrulama basarili olmali."""
        with patch("app.api.webhooks.settings") as mock_settings:
            mock_settings.webhook_secret.get_secret_value.return_value = ""
            resp = client.get("/webhooks/verify", params={"challenge": "abc123"})
        assert resp.status_code == 200
        assert resp.json()["challenge"] == "abc123"
        assert resp.json()["status"] == "verified"

    def test_verify_valid_token(self, client: TestClient) -> None:
        with patch("app.api.webhooks.settings") as mock_settings:
            mock_settings.webhook_secret.get_secret_value.return_value = "mysecret"
            resp = client.get(
                "/webhooks/verify",
                params={"token": "mysecret", "challenge": "test"},
            )
        assert resp.status_code == 200
        assert resp.json()["status"] == "verified"

    def test_verify_invalid_token(self, client: TestClient) -> None:
        with patch("app.api.webhooks.settings") as mock_settings:
            mock_settings.webhook_secret.get_secret_value.return_value = "mysecret"
            resp = client.get(
                "/webhooks/verify",
                params={"token": "wrong"},
            )
        assert resp.status_code == 403


# === Telegram webhook testleri ===


class TestTelegramWebhook:
    """POST /webhooks/telegram testleri."""

    def test_message_update(self, client: TestClient) -> None:
        update = {
            "update_id": 123,
            "message": {
                "message_id": 1,
                "from": {"id": 111, "first_name": "Fatih", "username": "fatih"},
                "chat": {"id": 222, "type": "private"},
                "text": "sunucu durumunu kontrol et",
            },
        }
        with patch("app.api.webhooks._get_webhook_secret", return_value=""):
            resp = client.post("/webhooks/telegram", json=update)
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"]
        assert data["source"] == "telegram"
        assert "222" in data["message"]

    def test_callback_query_update(self, client: TestClient) -> None:
        update = {
            "update_id": 124,
            "callback_query": {
                "id": "cb1",
                "data": "approve",
                "message": {
                    "message_id": 2,
                    "chat": {"id": 333, "type": "private"},
                },
                "from": {"id": 111, "first_name": "Fatih"},
            },
        }
        with patch("app.api.webhooks._get_webhook_secret", return_value=""):
            resp = client.post("/webhooks/telegram", json=update)
        assert resp.status_code == 200

    def test_invalid_json(self, client: TestClient) -> None:
        with patch("app.api.webhooks._get_webhook_secret", return_value=""):
            resp = client.post(
                "/webhooks/telegram",
                content=b"not json",
                headers={"Content-Type": "application/json"},
            )
        assert resp.status_code == 400

    def test_secret_token_validation(self, client: TestClient) -> None:
        update = {"update_id": 125, "message": {"chat": {"id": 1}, "text": "hi"}}
        with patch("app.api.webhooks._get_webhook_secret", return_value="secret123"):
            # Yanlis token
            resp = client.post(
                "/webhooks/telegram",
                json=update,
                headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"},
            )
        assert resp.status_code == 401

    def test_secret_token_valid(self, client: TestClient) -> None:
        update = {
            "update_id": 126,
            "message": {
                "message_id": 3,
                "from": {"id": 1, "first_name": "Test"},
                "chat": {"id": 1, "type": "private"},
                "text": "test",
            },
        }
        with patch("app.api.webhooks._get_webhook_secret", return_value="secret123"):
            resp = client.post(
                "/webhooks/telegram",
                json=update,
                headers={"X-Telegram-Bot-Api-Secret-Token": "secret123"},
            )
        assert resp.status_code == 200


# === Google Ads webhook testleri ===


class TestGoogleAdsWebhook:
    """POST /webhooks/google-ads testleri."""

    def test_campaign_status_change(self, client: TestClient) -> None:
        payload = {
            "customer_id": "123-456-7890",
            "change_type": "campaign_status",
            "campaign_id": "camp1",
            "campaign_name": "Mapa Health TR",
            "details": {"old_status": "ENABLED", "new_status": "PAUSED"},
        }
        with patch("app.api.webhooks._get_webhook_secret", return_value=""):
            resp = client.post("/webhooks/google-ads", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["source"] == "google_ads"
        assert "campaign_status" in data["message"]

    def test_ad_disapproved(self, client: TestClient) -> None:
        payload = {
            "customer_id": "123-456-7890",
            "change_type": "ad_disapproved",
            "campaign_id": "camp2",
            "campaign_name": "FTRK Store",
            "details": {"reason": "misleading_content"},
        }
        with patch("app.api.webhooks._get_webhook_secret", return_value=""):
            resp = client.post("/webhooks/google-ads", json=payload)
        assert resp.status_code == 200

    def test_budget_change(self, client: TestClient) -> None:
        payload = {
            "customer_id": "123-456-7890",
            "change_type": "budget_change",
            "campaign_name": "Test Campaign",
            "details": {"old_budget": 100, "new_budget": 200},
        }
        with patch("app.api.webhooks._get_webhook_secret", return_value=""):
            resp = client.post("/webhooks/google-ads", json=payload)
        assert resp.status_code == 200

    def test_invalid_change_type(self, client: TestClient) -> None:
        payload = {
            "customer_id": "123",
            "change_type": "invalid_type",
        }
        with patch("app.api.webhooks._get_webhook_secret", return_value=""):
            resp = client.post("/webhooks/google-ads", json=payload)
        assert resp.status_code == 422  # Pydantic validation error

    def test_with_hmac_signature(self, client: TestClient, webhook_secret: str) -> None:
        payload = {
            "customer_id": "123",
            "change_type": "performance_alert",
            "campaign_name": "Test",
        }
        body = json.dumps(payload).encode()
        sig = _make_signature(body, webhook_secret)
        with patch("app.api.webhooks._get_webhook_secret", return_value=webhook_secret):
            resp = client.post(
                "/webhooks/google-ads",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Webhook-Signature": sig,
                },
            )
        assert resp.status_code == 200

    def test_with_invalid_signature(self, client: TestClient) -> None:
        payload = {
            "customer_id": "123",
            "change_type": "budget_change",
            "campaign_name": "Test",
        }
        with patch("app.api.webhooks._get_webhook_secret", return_value="real-secret"):
            resp = client.post(
                "/webhooks/google-ads",
                json=payload,
                headers={"X-Webhook-Signature": "invalid"},
            )
        assert resp.status_code == 401


# === Gmail webhook testleri ===


class TestGmailWebhook:
    """POST /webhooks/gmail testleri."""

    def test_pubsub_notification(self, client: TestClient) -> None:
        import base64

        notification = json.dumps({
            "emailAddress": "fatih@example.com",
            "historyId": "12345",
        })
        encoded = base64.b64encode(notification.encode()).decode()

        payload = {
            "message": {
                "data": encoded,
                "messageId": "msg-1",
            },
            "subscription": "projects/atlas/subscriptions/gmail-push",
        }
        with patch("app.api.webhooks._get_webhook_secret", return_value=""):
            resp = client.post("/webhooks/gmail", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["source"] == "gmail"
        assert "fatih@example.com" in data["message"]

    def test_empty_pubsub_data(self, client: TestClient) -> None:
        payload = {
            "message": {"data": "", "messageId": "msg-2"},
            "subscription": "test-sub",
        }
        with patch("app.api.webhooks._get_webhook_secret", return_value=""):
            resp = client.post("/webhooks/gmail", json=payload)
        assert resp.status_code == 200

    def test_invalid_base64_data(self, client: TestClient) -> None:
        payload = {
            "message": {"data": "not-valid-base64!!!", "messageId": "msg-3"},
        }
        with patch("app.api.webhooks._get_webhook_secret", return_value=""):
            resp = client.post("/webhooks/gmail", json=payload)
        assert resp.status_code == 200  # Hata loglanir ama 200 doner


# === Alert webhook testleri ===


class TestAlertWebhook:
    """POST /webhooks/alert testleri."""

    def test_info_alert(self, client: TestClient) -> None:
        payload = {
            "source": "uptime_monitor",
            "severity": "info",
            "title": "Sunucu yanit suresi normal",
            "message": "Yanit suresi: 120ms",
        }
        with patch("app.api.webhooks._get_webhook_secret", return_value=""):
            resp = client.post("/webhooks/alert", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "info" in data["message"]

    def test_warning_alert(self, client: TestClient) -> None:
        payload = {
            "source": "server_monitor",
            "severity": "warning",
            "title": "CPU kullanimi yuksek",
            "message": "CPU: %85",
            "metadata": {"cpu_percent": 85, "server": "web1"},
        }
        with patch("app.api.webhooks._get_webhook_secret", return_value=""):
            resp = client.post("/webhooks/alert", json=payload)
        assert resp.status_code == 200

    def test_critical_alert(self, client: TestClient) -> None:
        payload = {
            "source": "security_scanner",
            "severity": "critical",
            "title": "Brute force saldirisi tespit edildi",
            "message": "192.168.1.100 IP'den 500+ basarisiz giris denemesi",
        }
        with patch("app.api.webhooks._get_webhook_secret", return_value=""):
            resp = client.post("/webhooks/alert", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "critical" in data["message"]

    def test_alert_with_metadata(self, client: TestClient) -> None:
        payload = {
            "source": "grafana",
            "severity": "warning",
            "title": "Disk dolmak uzere",
            "message": "/dev/sda1: %92 dolu",
            "metadata": {
                "disk_percent": 92,
                "mount_point": "/",
                "server": "db1",
            },
        }
        with patch("app.api.webhooks._get_webhook_secret", return_value=""):
            resp = client.post("/webhooks/alert", json=payload)
        assert resp.status_code == 200

    def test_missing_required_fields(self, client: TestClient) -> None:
        payload = {"severity": "info"}  # source ve title eksik
        with patch("app.api.webhooks._get_webhook_secret", return_value=""):
            resp = client.post("/webhooks/alert", json=payload)
        assert resp.status_code == 422

    def test_invalid_severity(self, client: TestClient) -> None:
        payload = {
            "source": "test",
            "severity": "extreme",  # Gecersiz
            "title": "Test",
        }
        with patch("app.api.webhooks._get_webhook_secret", return_value=""):
            resp = client.post("/webhooks/alert", json=payload)
        assert resp.status_code == 422

    def test_signature_required_when_secret_set(self, client: TestClient) -> None:
        payload = {
            "source": "test",
            "severity": "info",
            "title": "Test",
        }
        with patch("app.api.webhooks._get_webhook_secret", return_value="secret"):
            resp = client.post("/webhooks/alert", json=payload)
        assert resp.status_code == 401
