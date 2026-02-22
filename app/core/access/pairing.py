"""Eslestirme yoneticisi - DM eslestirme kodu uretimi ve dogrulama.

Kullanicilarin guvenlice eslestirme kodu ile cihaz baglamasini saglar.
Zaman asimli kodlar, deneme siniri ve engelleme mekanizmasi icerir.
"""

import json
import logging
import random
import string
import time
import uuid
from typing import Optional

from app.models.access_models import (
    AccessAuditEntry,
    ChannelType,
    PairedDevice,
    PairingRequest,
    PairingStatus,
)

logger = logging.getLogger(__name__)


class PairingManager:
    """Eslestirme kodu uretimi ve dogrulama yoneticisi.

    Cihaz eslestirme islemlerini yonetir. Kod uretimi, dogrulama,
    engelleme ve QR kod destegi saglar.
    """

    def __init__(self, code_length: int = 6, expiry_seconds: int = 300, max_attempts: int = 3, block_duration: int = 600) -> None:
        """PairingManager baslatici.

        Args:
            code_length: Eslestirme kodu uzunlugu
            expiry_seconds: Kodun gecerlilik suresi (saniye)
            max_attempts: Maksimum deneme sayisi
            block_duration: Engelleme suresi (saniye)
        """
        self.code_length = code_length
        self.expiry_seconds = expiry_seconds
        self.max_attempts = max_attempts
        self.block_duration = block_duration
        self._requests: dict[str, PairingRequest] = {}
        self._paired_devices: dict[str, PairedDevice] = {}
        self._blocked: dict[str, float] = {}
        self._history: list[dict] = []

    def _record_history(self, action: str, details: dict) -> None:
        """Gecmis kaydini tutar."""
        self._history.append({"action": action, "timestamp": time.time(), "details": details})

    def get_history(self) -> list[dict]:
        """Gecmis kayitlarini dondurur."""
        return list(self._history)

    def get_stats(self) -> dict:
        """Istatistikleri dondurur."""
        return {
            "total_requests": len(self._requests),
            "paired_devices": len(self._paired_devices),
            "active_devices": sum(1 for d in self._paired_devices.values() if d.is_active),
            "blocked_senders": len(self._blocked),
            "history_count": len(self._history),
            "pending_requests": sum(1 for r in self._requests.values() if r.status == PairingStatus.PENDING),
        }

    def _generate_pairing_code(self, length: int) -> str:
        """Rastgele eslestirme kodu uretir."""
        return "".join(random.choices(string.digits, k=length))

    def generate_code(self, sender_id: str, channel: ChannelType = ChannelType.GENERIC) -> PairingRequest:
        """Eslestirme kodu uretir."""
        if self.is_blocked(sender_id):
            raise ValueError(f"Sender {sender_id} is blocked")
        now = time.time()
        code = self._generate_pairing_code(self.code_length)
        request_id = str(uuid.uuid4())
        request = PairingRequest(request_id=request_id, sender_id=str(sender_id), channel=channel, pairing_code=code, created_at=now, expires_at=now + self.expiry_seconds, attempts=0, status=PairingStatus.PENDING)
        self._requests[sender_id] = request
        self._record_history("generate_code", {"sender_id": sender_id, "channel": channel.value, "request_id": request_id})
        logger.info(f"Eslestirme kodu uretildi: sender={sender_id}")
        return request

    def verify_code(self, sender_id: str, code: str) -> bool:
        """Eslestirme kodunu dogrular."""
        request = self._requests.get(sender_id)
        if not request:
            self._record_history("verify_code", {"sender_id": sender_id, "result": "no_request"})
            return False
        now = time.time()
        if now > request.expires_at:
            request.status = PairingStatus.EXPIRED
            self._record_history("verify_code", {"sender_id": sender_id, "result": "expired"})
            return False
        request.attempts += 1
        if request.attempts > self.max_attempts:
            request.status = PairingStatus.BLOCKED
            self._blocked[sender_id] = now + self.block_duration
            self._record_history("verify_code", {"sender_id": sender_id, "result": "blocked"})
            return False
        if request.pairing_code == code:
            request.status = PairingStatus.PAIRED
            device_id = str(uuid.uuid4())
            device = PairedDevice(device_id=device_id, sender_id=str(sender_id), channel=request.channel, paired_at=now, last_activity=now, is_active=True)
            self._paired_devices[device_id] = device
            self._record_history("verify_code", {"sender_id": sender_id, "result": "success", "device_id": device_id})
            logger.info(f"Eslestirme basarili: sender={sender_id}")
            return True
        self._record_history("verify_code", {"sender_id": sender_id, "result": "wrong_code", "attempts": request.attempts})
        return False

    def get_request(self, sender_id: str) -> Optional[PairingRequest]:
        """Bekleyen eslestirme istegini dondurur."""
        return self._requests.get(sender_id)

    def expire_old_requests(self) -> int:
        """Suresi dolmus istekleri temizler."""
        now = time.time()
        expired_count = 0
        for sender_id, request in list(self._requests.items()):
            if request.status == PairingStatus.PENDING and now > request.expires_at:
                request.status = PairingStatus.EXPIRED
                expired_count += 1
        self._record_history("expire_old_requests", {"count": expired_count})
        return expired_count

    def is_blocked(self, sender_id: str) -> bool:
        """Gondericinin engellenip engellenmedigini kontrol eder."""
        if sender_id not in self._blocked:
            return False
        now = time.time()
        if now > self._blocked[sender_id]:
            del self._blocked[sender_id]
            return False
        return True

    def unblock(self, sender_id: str) -> bool:
        """Gondericinin engelini kaldirir."""
        if sender_id in self._blocked:
            del self._blocked[sender_id]
            self._record_history("unblock", {"sender_id": sender_id})
            return True
        return False

    def get_paired_devices(self) -> list[PairedDevice]:
        """Tum eslestirilmis cihazlari dondurur."""
        return list(self._paired_devices.values())

    def unpair(self, device_id: str) -> bool:
        """Cihaz eslestirmesini kaldirir."""
        if device_id in self._paired_devices:
            device = self._paired_devices.pop(device_id)
            self._record_history("unpair", {"device_id": device_id, "sender_id": device.sender_id})
            return True
        return False

    def generate_qr_data(self, pairing_request: PairingRequest) -> str:
        """Eslestirme istegi icin QR kod verisi uretir."""
        qr_data = {"type": "atlas_pairing", "code": pairing_request.pairing_code, "sender_id": pairing_request.sender_id, "channel": pairing_request.channel.value, "expires_at": pairing_request.expires_at}
        result = json.dumps(qr_data)
        self._record_history("generate_qr_data", {"request_id": pairing_request.request_id})
        return result
