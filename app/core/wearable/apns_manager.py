"""Apple Push Notification Service (APNs) yonetim modulu.

Push token kaydi, bildirim gonderimi, sessiz push
ve teslimat istatistikleri saglar.
"""

import logging
import time
import uuid
from typing import Any, Optional

from app.models.wearable_models import (
    APNsPayload,
    WearableConfig,
)

logger = logging.getLogger(__name__)


class APNsManager:
    """APNs bildirim yoneticisi.

    Push token yonetimi, bildirim gonderimi ve
    teslimat izleme islevleri saglar.
    """

    def __init__(self, config: Optional[WearableConfig] = None) -> None:
        """APNs yoneticisini baslatir.

        Args:
            config: Giyilebilir cihaz yapilandirmasi
        """
        self.config = config or WearableConfig()
        self._tokens: dict[str, str] = {}  # device_id -> token
        self._sent: list[dict] = []
        self._delivered: int = 0
        self._failed: int = 0
        self._history: list[dict] = []

    def _record_history(self, action: str, **kwargs) -> None:
        """Gecmis kaydina olay ekler."""
        self._history.append({
            "action": action,
            "timestamp": time.time(),
            **kwargs,
        })

    def register_token(self, device_id: str, token: str) -> bool:
        """Push token kaydeder.

        Args:
            device_id: Cihaz kimligi
            token: APNs push token

        Returns:
            Basarili ise True
        """
        if not token or len(token) < 10:
            logger.warning(f"Gecersiz token: {device_id}")
            return False
        self._tokens[device_id] = token
        self._record_history("register_token", device_id=device_id)
        logger.info(f"Token kaydedildi: {device_id}")
        return True

    def send_notification(
        self,
        device_id: str,
        title: str,
        body: str,
        data: Optional[dict[str, Any]] = None,
    ) -> Optional[str]:
        """Push bildirim gonderir.

        Args:
            device_id: Hedef cihaz kimligi
            title: Bildirim basligi
            body: Bildirim govdesi
            data: Ek veri

        Returns:
            Bildirim kimligi veya None
        """
        token = self._tokens.get(device_id)
        if not token:
            logger.warning(f"Token bulunamadi: {device_id}")
            return None

        notification_id = str(uuid.uuid4())
        payload = APNsPayload(
            device_token=token,
            alert_title=title,
            alert_body=body,
            custom_data=data or {},
        )

        record = {
            "notification_id": notification_id,
            "device_id": device_id,
            "payload": payload.model_dump(),
            "sent_at": time.time(),
            "status": "sent",
        }
        self._sent.append(record)
        self._delivered += 1
        self._record_history("send_notification", device_id=device_id, notification_id=notification_id)
        logger.info(f"Bildirim gonderildi: {notification_id} -> {device_id}")
        return notification_id

    def send_silent_push(
        self, device_id: str, data: Optional[dict[str, Any]] = None
    ) -> Optional[str]:
        """Sessiz push gonderir (cihazi uyandirmak icin).

        Args:
            device_id: Hedef cihaz kimligi
            data: Gonderilecek veri

        Returns:
            Bildirim kimligi veya None
        """
        token = self._tokens.get(device_id)
        if not token:
            return None

        notification_id = str(uuid.uuid4())
        payload = APNsPayload(
            device_token=token,
            is_silent=True,
            custom_data=data or {},
            sound="",
        )

        record = {
            "notification_id": notification_id,
            "device_id": device_id,
            "payload": payload.model_dump(),
            "sent_at": time.time(),
            "status": "sent",
            "is_silent": True,
        }
        self._sent.append(record)
        self._delivered += 1
        self._record_history("send_silent_push", device_id=device_id)
        return notification_id

    def validate_token(self, token: str) -> bool:
        """Token gecerliligi kontrol eder.

        Args:
            token: Dogrulanacak token

        Returns:
            Gecerli ise True
        """
        # Temel dogrulama: minimum uzunluk ve alfanumerik
        if not token or len(token) < 10:
            return False
        if not all(c.isalnum() for c in token):
            return False
        return True

    def get_delivery_stats(self) -> dict:
        """Teslimat istatistiklerini dondurur.

        Returns:
            Teslimat istatistikleri
        """
        return {
            "total_sent": len(self._sent),
            "delivered": self._delivered,
            "failed": self._failed,
            "success_rate": self._delivered / max(len(self._sent), 1),
            "registered_tokens": len(self._tokens),
        }

    def test_push(self, device_id: str) -> Optional[str]:
        """Test push gonderir.

        Args:
            device_id: Hedef cihaz kimligi

        Returns:
            Bildirim kimligi veya None
        """
        return self.send_notification(
            device_id=device_id,
            title="Test Bildirimi",
            body="ATLAS wearable baglantisi aktif.",
            data={"type": "test"},
        )

    def get_history(self) -> list[dict]:
        """Gecmis kayitlarini dondurur."""
        return list(self._history)

    def get_stats(self) -> dict:
        """Istatistikleri dondurur."""
        return {
            **self.get_delivery_stats(),
            "history_count": len(self._history),
        }
