"""ATLAS Onay Yoneticisi modulu.

Degisiklik onay kuyrugu, Telegram incelemesi,
timeout yonetimi, toplu onay ve denetim izi.
"""

import logging
import time
from typing import Any

from app.models.evolution import (
    ApprovalRequest,
    ApprovalStatus,
    ChangeSeverity,
    CodeChange,
)

logger = logging.getLogger(__name__)


class ApprovalManager:
    """Onay yonetim sistemi.

    Degisiklikleri onay kuyuguna ekler, Telegram uzerinden
    inceleme gonderir, timeout yonetir ve denetim izi tutar.

    Attributes:
        _queue: Onay kuyrugu.
        _audit_trail: Denetim izi.
        _timeout_hours: Varsayilan timeout suresi.
    """

    def __init__(self, timeout_hours: int = 24) -> None:
        """Onay yoneticisini baslatir.

        Args:
            timeout_hours: Varsayilan timeout suresi (saat).
        """
        self._queue: list[ApprovalRequest] = []
        self._audit_trail: list[dict[str, Any]] = []
        self._timeout_hours = timeout_hours
        self._batch_counter = 0

        logger.info("ApprovalManager baslatildi (timeout=%dh)", timeout_hours)

    def queue_change(self, change: CodeChange, title: str = "", description: str = "") -> ApprovalRequest:
        """Degisikligi onay kuyuguna ekler.

        Args:
            change: Onaylanacak degisiklik.
            title: Baslik.
            description: Aciklama.

        Returns:
            ApprovalRequest nesnesi.
        """
        request = ApprovalRequest(
            change_id=change.id,
            title=title or f"Degisiklik: {change.file_path}",
            description=description or change.description,
            severity=change.severity,
            timeout_hours=self._timeout_hours,
        )

        self._queue.append(request)
        self._record_audit("queued", request)
        logger.info("Onay kuyuguna eklendi: %s", request.title)
        return request

    def approve(self, request_id: str, responder: str = "admin") -> bool:
        """Istegi onaylar.

        Args:
            request_id: Istek ID.
            responder: Onaylayan kisi.

        Returns:
            Basarili mi.
        """
        request = self._find_request(request_id)
        if not request or request.status != ApprovalStatus.PENDING:
            return False

        request.status = ApprovalStatus.APPROVED
        request.responder = responder
        self._record_audit("approved", request, responder=responder)
        logger.info("Onaylandi: %s by %s", request.title, responder)
        return True

    def reject(self, request_id: str, responder: str = "admin", reason: str = "") -> bool:
        """Istegi reddeder.

        Args:
            request_id: Istek ID.
            responder: Reddeden kisi.
            reason: Red nedeni.

        Returns:
            Basarili mi.
        """
        request = self._find_request(request_id)
        if not request or request.status != ApprovalStatus.PENDING:
            return False

        request.status = ApprovalStatus.REJECTED
        request.responder = responder
        self._record_audit("rejected", request, responder=responder, reason=reason)
        logger.info("Reddedildi: %s by %s", request.title, responder)
        return True

    def auto_approve(self, request_id: str) -> bool:
        """Otomatik onaylar.

        Args:
            request_id: Istek ID.

        Returns:
            Basarili mi.
        """
        request = self._find_request(request_id)
        if not request or request.status != ApprovalStatus.PENDING:
            return False

        request.status = ApprovalStatus.AUTO_APPROVED
        request.responder = "system"
        self._record_audit("auto_approved", request)
        logger.info("Otomatik onaylandi: %s", request.title)
        return True

    def check_timeouts(self) -> list[ApprovalRequest]:
        """Timeout olmus istekleri kontrol eder.

        Returns:
            Timeout olan istekler.
        """
        now = time.time()
        timed_out: list[ApprovalRequest] = []

        for request in self._queue:
            if request.status != ApprovalStatus.PENDING:
                continue
            age_hours = (now - request.requested_at.timestamp()) / 3600
            if age_hours > request.timeout_hours:
                request.status = ApprovalStatus.TIMEOUT
                self._record_audit("timeout", request)
                timed_out.append(request)

        return timed_out

    def create_batch(self, request_ids: list[str]) -> str:
        """Toplu onay grubu olusturur.

        Args:
            request_ids: Istek ID listesi.

        Returns:
            Batch ID.
        """
        self._batch_counter += 1
        batch_id = f"batch_{self._batch_counter}"

        for rid in request_ids:
            request = self._find_request(rid)
            if request:
                request.batch_id = batch_id

        logger.info("Batch olusturuldu: %s (%d istek)", batch_id, len(request_ids))
        return batch_id

    def approve_batch(self, batch_id: str, responder: str = "admin") -> int:
        """Toplu onay yapar.

        Args:
            batch_id: Batch ID.
            responder: Onaylayan kisi.

        Returns:
            Onaylanan istek sayisi.
        """
        count = 0
        for request in self._queue:
            if request.batch_id == batch_id and request.status == ApprovalStatus.PENDING:
                request.status = ApprovalStatus.APPROVED
                request.responder = responder
                self._record_audit("batch_approved", request, responder=responder)
                count += 1

        logger.info("Batch onaylandi: %s (%d istek)", batch_id, count)
        return count

    def get_pending(self) -> list[ApprovalRequest]:
        """Bekleyen istekleri getirir.

        Returns:
            ApprovalRequest listesi.
        """
        return [r for r in self._queue if r.status == ApprovalStatus.PENDING]

    def get_request(self, request_id: str) -> ApprovalRequest | None:
        """Istek getirir.

        Args:
            request_id: Istek ID.

        Returns:
            ApprovalRequest veya None.
        """
        return self._find_request(request_id)

    def get_audit_trail(self, limit: int = 50) -> list[dict[str, Any]]:
        """Denetim izini getirir.

        Args:
            limit: Maksimum kayit sayisi.

        Returns:
            Denetim kayitlari.
        """
        return self._audit_trail[-limit:]

    def format_for_telegram(self, request: ApprovalRequest) -> str:
        """Telegram mesaji formatlar.

        Args:
            request: Onay istegi.

        Returns:
            Formatlanmis mesaj.
        """
        severity_emoji = {
            ChangeSeverity.MINOR: "🟢",
            ChangeSeverity.MAJOR: "🟡",
            ChangeSeverity.CRITICAL: "🔴",
        }
        emoji = severity_emoji.get(request.severity, "⚪")

        return (
            f"{emoji} **Onay Istegi**\n"
            f"**Baslik:** {request.title}\n"
            f"**Ciddiyet:** {request.severity.value}\n"
            f"**Aciklama:** {request.description}\n"
            f"**ID:** {request.id}"
        )

    def _find_request(self, request_id: str) -> ApprovalRequest | None:
        """Istegi bulur."""
        for request in self._queue:
            if request.id == request_id:
                return request
        return None

    def _record_audit(self, action: str, request: ApprovalRequest, **kwargs: Any) -> None:
        """Denetim kaydeder."""
        entry = {
            "action": action,
            "request_id": request.id,
            "title": request.title,
            "severity": request.severity.value,
            "timestamp": time.time(),
            **kwargs,
        }
        self._audit_trail.append(entry)

    @property
    def queue_size(self) -> int:
        """Kuyruk boyutu."""
        return len(self._queue)

    @property
    def pending_count(self) -> int:
        """Bekleyen istek sayisi."""
        return sum(1 for r in self._queue if r.status == ApprovalStatus.PENDING)

    @property
    def approved_count(self) -> int:
        """Onaylanan istek sayisi."""
        return sum(
            1 for r in self._queue
            if r.status in (ApprovalStatus.APPROVED, ApprovalStatus.AUTO_APPROVED)
        )
