"""ATLAS Webhook endpoint'leri.

Dis servislerden gelen bildirimleri karsilar ve Master Agent'a iletir:
- Telegram webhook (bot mesajlari)
- Google Ads webhook (kampanya degisiklikleri)
- Gmail webhook (yeni mail push bildirimi)
- Genel alert webhook (izleme/uyari sistemleri)

Tum webhook'lar HMAC-SHA256 imza dogrulamasi ile korunur.
"""

import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


# === Ortak modeller ===


class WebhookSource(str, Enum):
    """Webhook kaynak tanimlari."""

    TELEGRAM = "telegram"
    GOOGLE_ADS = "google_ads"
    GMAIL = "gmail"
    ALERT = "alert"
    CUSTOM = "custom"


class AlertSeverity(str, Enum):
    """Alert onem seviyesi."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class WebhookResponse(BaseModel):
    """Standart webhook yanit modeli."""

    ok: bool = True
    source: str = ""
    message: str = ""
    task_id: str | None = None


class AlertPayload(BaseModel):
    """Genel alert webhook istek govdesi.

    Attributes:
        source: Alert kaynagi (orn: uptime_monitor, grafana).
        severity: Onem seviyesi.
        title: Kisa baslik.
        message: Detayli aciklama.
        metadata: Ek veri (opsiyonel).
    """

    source: str
    severity: AlertSeverity = AlertSeverity.INFO
    title: str
    message: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


# === Guvenlik yardimcilari ===


def _verify_signature(
    payload_body: bytes,
    signature: str,
    secret: str,
) -> bool:
    """HMAC-SHA256 imza dogrulamasi yapar.

    Args:
        payload_body: Ham istek govdesi (bytes).
        signature: Gelen imza degeri (sha256=xxx veya dogrudan hex).
        secret: Paylasilan gizli anahtar.

    Returns:
        Imza gecerliyse True, degilse False.
    """
    if not secret:
        return False

    expected = hmac.new(
        secret.encode("utf-8"),
        payload_body,
        hashlib.sha256,
    ).hexdigest()

    # "sha256=..." formati destegi
    if signature.startswith("sha256="):
        signature = signature[7:]

    return hmac.compare_digest(expected, signature)


def _get_webhook_secret() -> str:
    """Webhook dogrulama anahtarini dondurur."""
    return settings.webhook_secret.get_secret_value()


async def _verify_webhook_request(
    request: Request,
    x_webhook_signature: str | None,
) -> bytes:
    """Webhook istegini dogrular ve ham govdeyi dondurur.

    Production ortaminda imza zorunlu, development'ta opsiyonel.

    Args:
        request: FastAPI istek nesnesi.
        x_webhook_signature: Istek imzasi header'i.

    Returns:
        Ham istek govdesi (bytes).

    Raises:
        HTTPException: Imza gecersizse (401) veya body okunamazsa (400).
    """
    try:
        body = await request.body()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Istek govdesi okunamadi: {exc}")

    secret = _get_webhook_secret()
    if not secret:
        # Secret ayarlanmamis: development modda imza kontrolunu atla
        logger.debug("Webhook secret ayarlanmamis, imza kontrolu atlandi")
        return body

    if not x_webhook_signature:
        raise HTTPException(
            status_code=401,
            detail="X-Webhook-Signature header'i gerekli",
        )

    if not _verify_signature(body, x_webhook_signature, secret):
        logger.warning(
            "Webhook imza dogrulamasi basarisiz: %s %s",
            request.method,
            request.url.path,
        )
        raise HTTPException(status_code=401, detail="Gecersiz webhook imzasi")

    return body


async def _dispatch_to_master(
    request: Request,
    task: dict[str, Any],
) -> str | None:
    """Gorevi Master Agent'a iletir.

    Args:
        request: FastAPI istek nesnesi (app.state erisimi icin).
        task: Gorev detaylari.

    Returns:
        Gorev ID'si veya None (Master Agent hazir degilse).
    """
    master_agent = getattr(request.app.state, "master_agent", None)
    if not master_agent:
        logger.warning("Master Agent hazir degil, gorev kuyruga alinamadi")
        return None

    result = await master_agent.run(task)
    logger.info(
        "Webhook gorev tamamlandi: source=%s, success=%s",
        task.get("source", "unknown"),
        result.success,
    )
    return task.get("task_id")


# === Telegram Webhook ===


@router.post("/telegram", response_model=WebhookResponse)
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> WebhookResponse:
    """Telegram Bot API webhook endpoint'i.

    Telegram'dan gelen Update JSON'larini isler.
    Bot'u polling yerine webhook modunda kullanmak icin.

    Dogrulama: Telegram'in secret_token mekanizmasi kullanilir.
    Bkz: https://core.telegram.org/bots/api#setwebhook

    Returns:
        WebhookResponse: Islem sonucu.
    """
    body = await request.body()

    # Telegram secret_token dogrulamasi
    secret = _get_webhook_secret()
    if secret and x_telegram_bot_api_secret_token != secret:
        raise HTTPException(status_code=401, detail="Gecersiz Telegram secret token")

    try:
        update_data = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Gecersiz JSON")

    # Mesaj icerigini cikar
    message = update_data.get("message", {})
    callback_query = update_data.get("callback_query", {})

    text = ""
    chat_id = ""
    from_user = ""

    if message:
        text = message.get("text", "")
        chat_info = message.get("chat", {})
        chat_id = str(chat_info.get("id", ""))
        from_info = message.get("from", {})
        from_user = from_info.get("username", from_info.get("first_name", ""))
    elif callback_query:
        text = callback_query.get("data", "")
        msg = callback_query.get("message", {})
        chat_info = msg.get("chat", {})
        chat_id = str(chat_info.get("id", ""))

    logger.info(
        "Telegram webhook: chat_id=%s, from=%s, text=%s",
        chat_id, from_user, text[:80],
    )

    # Telegram bot'a ilet (varsa)
    telegram_bot = getattr(request.app.state, "telegram_bot", None)
    if telegram_bot and telegram_bot.app:
        try:
            from telegram import Update as TelegramUpdate
            tg_update = TelegramUpdate.de_json(update_data, telegram_bot.app.bot)
            if tg_update:
                await telegram_bot.app.process_update(tg_update)
        except Exception as exc:
            logger.error("Telegram update isleme hatasi: %s", exc)

    # Master Agent'a da bildir
    await _dispatch_to_master(request, {
        "description": f"Telegram mesaji: {text[:200]}",
        "source": "telegram",
        "chat_id": chat_id,
        "from_user": from_user,
        "raw_update": update_data,
    })

    return WebhookResponse(
        source="telegram",
        message=f"Update islendi (chat: {chat_id})",
    )


# === Google Ads Webhook ===


class GoogleAdsChangeType(str, Enum):
    """Google Ads degisiklik tipleri."""

    CAMPAIGN_STATUS = "campaign_status"
    BUDGET_CHANGE = "budget_change"
    AD_DISAPPROVED = "ad_disapproved"
    BID_CHANGE = "bid_change"
    PERFORMANCE_ALERT = "performance_alert"


class GoogleAdsPayload(BaseModel):
    """Google Ads webhook istek govdesi.

    Attributes:
        customer_id: Google Ads musteri ID'si.
        change_type: Degisiklik tipi.
        campaign_id: Kampanya ID'si.
        campaign_name: Kampanya adi.
        details: Degisiklik detaylari.
    """

    customer_id: str
    change_type: GoogleAdsChangeType
    campaign_id: str = ""
    campaign_name: str = ""
    details: dict[str, Any] = Field(default_factory=dict)


@router.post("/google-ads", response_model=WebhookResponse)
async def google_ads_webhook(
    request: Request,
    payload: GoogleAdsPayload,
    x_webhook_signature: str | None = Header(default=None),
) -> WebhookResponse:
    """Google Ads kampanya degisiklik webhook'u.

    Kampanya durum degisiklikleri, butce alarmlari ve
    reklam reddedilme bildirimlerini karsilar.

    Args:
        request: FastAPI istek nesnesi.
        payload: Google Ads degisiklik verisi.
        x_webhook_signature: HMAC-SHA256 imzasi.

    Returns:
        WebhookResponse: Islem sonucu.
    """
    await _verify_webhook_request(request, x_webhook_signature)

    logger.info(
        "Google Ads webhook: customer=%s, type=%s, campaign=%s",
        payload.customer_id,
        payload.change_type.value,
        payload.campaign_name,
    )

    # Aciliyet belirleme
    risk = "low"
    urgency = "low"

    if payload.change_type == GoogleAdsChangeType.AD_DISAPPROVED:
        risk = "medium"
        urgency = "high"
    elif payload.change_type == GoogleAdsChangeType.BUDGET_CHANGE:
        risk = "medium"
        urgency = "medium"
    elif payload.change_type == GoogleAdsChangeType.PERFORMANCE_ALERT:
        risk = "medium"
        urgency = "medium"

    task_id = await _dispatch_to_master(request, {
        "description": (
            f"Google Ads: {payload.change_type.value} - "
            f"{payload.campaign_name or payload.campaign_id}"
        ),
        "source": "google_ads",
        "target_agent": "marketing",
        "risk": risk,
        "urgency": urgency,
        "google_ads_data": payload.model_dump(),
    })

    return WebhookResponse(
        source="google_ads",
        message=f"{payload.change_type.value}: {payload.campaign_name}",
        task_id=task_id,
    )


# === Gmail Webhook (Push Notification) ===


class GmailPayload(BaseModel):
    """Gmail push bildirim istek govdesi.

    Google Cloud Pub/Sub uzerinden gelir.
    Bkz: https://developers.google.com/gmail/api/guides/push

    Attributes:
        message: Pub/Sub mesaj verisi.
        subscription: Pub/Sub abonelik adi.
    """

    message: dict[str, Any]
    subscription: str = ""


@router.post("/gmail", response_model=WebhookResponse)
async def gmail_webhook(
    request: Request,
    payload: GmailPayload,
    x_webhook_signature: str | None = Header(default=None),
) -> WebhookResponse:
    """Gmail push bildirim webhook'u.

    Google Cloud Pub/Sub uzerinden gelen yeni mail bildirimlerini isler.
    Gmail API watch() methodu ile eslestirilerek kullanilir.

    Args:
        request: FastAPI istek nesnesi.
        payload: Pub/Sub mesaj verisi.
        x_webhook_signature: HMAC-SHA256 imzasi.

    Returns:
        WebhookResponse: Islem sonucu.
    """
    await _verify_webhook_request(request, x_webhook_signature)

    # Pub/Sub mesajindan email metadata cikar
    import base64

    pubsub_data = payload.message.get("data", "")
    decoded = ""
    email_address = ""
    history_id = ""

    if pubsub_data:
        try:
            decoded = base64.b64decode(pubsub_data).decode("utf-8")
            notification = json.loads(decoded)
            email_address = notification.get("emailAddress", "")
            history_id = str(notification.get("historyId", ""))
        except Exception as exc:
            logger.warning("Gmail Pub/Sub veri cozumleme hatasi: %s", exc)

    logger.info(
        "Gmail webhook: email=%s, history_id=%s, subscription=%s",
        email_address, history_id, payload.subscription,
    )

    task_id = await _dispatch_to_master(request, {
        "description": f"Gmail bildirim: yeni mesaj ({email_address})",
        "source": "gmail",
        "target_agent": "communication",
        "risk": "low",
        "urgency": "medium",
        "gmail_data": {
            "email_address": email_address,
            "history_id": history_id,
            "task_type": "read_inbox",
            "query": "is:unread",
        },
    })

    return WebhookResponse(
        source="gmail",
        message=f"Mail bildirimi alindi: {email_address}",
        task_id=task_id,
    )


# === Genel Alert Webhook ===


@router.post("/alert", response_model=WebhookResponse)
async def alert_webhook(
    request: Request,
    payload: AlertPayload,
    x_webhook_signature: str | None = Header(default=None),
) -> WebhookResponse:
    """Genel alert/uyari webhook'u.

    Izleme sistemleri (uptime monitor, Grafana, custom scripts)
    tarafindan gonderilen uyarilari karsilar.

    Args:
        request: FastAPI istek nesnesi.
        payload: Alert verisi.
        x_webhook_signature: HMAC-SHA256 imzasi.

    Returns:
        WebhookResponse: Islem sonucu.
    """
    await _verify_webhook_request(request, x_webhook_signature)

    logger.info(
        "Alert webhook: source=%s, severity=%s, title=%s",
        payload.source, payload.severity.value, payload.title,
    )

    # Severity -> risk/urgency eslestirmesi
    severity_map = {
        AlertSeverity.INFO: ("low", "low"),
        AlertSeverity.WARNING: ("medium", "medium"),
        AlertSeverity.CRITICAL: ("high", "high"),
    }
    risk, urgency = severity_map.get(payload.severity, ("low", "low"))

    # Kaynak bazli agent eslestirme
    target_agent = ""
    source_lower = payload.source.lower()
    if any(k in source_lower for k in ("server", "cpu", "ram", "disk", "uptime")):
        target_agent = "server_monitor"
    elif any(k in source_lower for k in ("security", "firewall", "intrusion", "ssl")):
        target_agent = "security"
    elif any(k in source_lower for k in ("ads", "campaign", "google_ads")):
        target_agent = "marketing"

    task_id = await _dispatch_to_master(request, {
        "description": f"Alert [{payload.severity.value}]: {payload.title}",
        "source": f"alert:{payload.source}",
        "target_agent": target_agent,
        "risk": risk,
        "urgency": urgency,
        "alert_data": payload.model_dump(),
    })

    # Kritik alertlerde Telegram bildirimi
    if payload.severity == AlertSeverity.CRITICAL:
        telegram_bot = getattr(request.app.state, "telegram_bot", None)
        if telegram_bot:
            try:
                await telegram_bot.send_message(
                    f"KRITIK ALERT\n"
                    f"Kaynak: {payload.source}\n"
                    f"Baslik: {payload.title}\n"
                    f"Detay: {payload.message[:500]}"
                )
            except Exception as exc:
                logger.error("Telegram bildirim hatasi: %s", exc)

    return WebhookResponse(
        source=f"alert:{payload.source}",
        message=f"[{payload.severity.value}] {payload.title}",
        task_id=task_id,
    )


# === Webhook dogrulama (GET) ===


@router.get("/verify")
async def verify_webhook(
    token: str = "",
    challenge: str = "",
) -> dict[str, str]:
    """Webhook dogrulama endpoint'i.

    Servislerin webhook URL'ini dogrulamak icin kullanilir.
    Ornegin Telegram setWebhook veya Google Pub/Sub abonelik dogrulamasi.

    Args:
        token: Dogrulama token'i (webhook_secret ile eslestirilir).
        challenge: Challenge string (ayni sekilde geri dondurulur).

    Returns:
        Dogrulama yaniti.
    """
    secret = _get_webhook_secret()

    if secret and token != secret:
        raise HTTPException(status_code=403, detail="Gecersiz dogrulama token'i")

    logger.info("Webhook dogrulamasi basarili")

    return {
        "status": "verified",
        "challenge": challenge,
    }
