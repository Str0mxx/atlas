"""Onay kapisi - is akisi adimlarinda onay mekanizmasi."""

import logging
import time
import uuid
from typing import Optional

from app.models.lobster_models import ApprovalRequest

logger = logging.getLogger(__name__)


class ApprovalGate:
    """Is akisi onay kapisi yoneticisi."""

    def __init__(self, approval_timeout: int = 3600) -> None:
        """ApprovalGate baslatici."""
        self.approval_timeout = approval_timeout
        self._requests: dict[str, ApprovalRequest] = {}
        self._history: list[dict] = []

    def _record_history(self, action: str, details: dict) -> None:
        """Gecmis kaydini tutar."""
        self._history.append({"action": action, "timestamp": time.time(), "details": details})

    def get_history(self) -> list[dict]:
        """Gecmis kayitlarini dondurur."""
        return list(self._history)

    def get_stats(self) -> dict:
        """Istatistikleri dondurur."""
        sc: dict[str, int] = {}
        for req in self._requests.values():
            sc[req.status] = sc.get(req.status, 0) + 1
        return {"total_requests": len(self._requests), "status_distribution": sc, "history_count": len(self._history), "approval_timeout": self.approval_timeout}

    def request_approval(self, workflow_id: str, step_id: str, description: str = "", approver: str = "") -> ApprovalRequest:
        """Onay istegi olusturur."""
        now = time.time()
        request_id = str(uuid.uuid4())
        request = ApprovalRequest(request_id=request_id, workflow_id=workflow_id, step_id=step_id, step_name=step_id, description=description, requested_at=now, expires_at=now + self.approval_timeout, status="pending", approver=approver)
        self._requests[request_id] = request
        self._record_history("request_approval", {"request_id": request_id, "workflow_id": workflow_id, "step_id": step_id})
        return request

    def approve(self, request_id: str, approver: str = "") -> bool:
        """Onay istegini onaylar."""
        request = self._requests.get(request_id)
        if not request or request.status != "pending":
            return False
        if self.is_expired(request_id):
            return False
        request.status = "approved"
        request.approver = approver or request.approver
        request.response = "approved"
        request.responded_at = time.time()
        self._record_history("approve", {"request_id": request_id, "approver": request.approver})
        return True

    def reject(self, request_id: str, approver: str = "", reason: str = "") -> bool:
        """Onay istegini reddeder."""
        request = self._requests.get(request_id)
        if not request or request.status != "pending":
            return False
        request.status = "rejected"
        request.approver = approver or request.approver
        request.response = reason or "rejected"
        request.responded_at = time.time()
        self._record_history("reject", {"request_id": request_id, "reason": reason})
        return True

    def get_pending(self) -> list[ApprovalRequest]:
        """Bekleyen onay isteklerini dondurur."""
        return [r for r in self._requests.values() if r.status == "pending" and not self.is_expired(r.request_id)]

    def is_approved(self, request_id: str) -> bool:
        """Istegin onaylanip onaylanmadigini kontrol eder."""
        request = self._requests.get(request_id)
        if not request:
            return False
        return request.status == "approved"

    def is_expired(self, request_id: str) -> bool:
        """Istegin suresi dolup dolmadigini kontrol eder."""
        request = self._requests.get(request_id)
        if not request:
            return True
        return time.time() > request.expires_at

    def cleanup_expired(self) -> int:
        """Suresi dolmus istekleri temizler."""
        now = time.time()
        expired: list[str] = []
        for rid, request in self._requests.items():
            if request.status == "pending" and now > request.expires_at:
                request.status = "expired"
                expired.append(rid)
        self._record_history("cleanup_expired", {"count": len(expired)})
        return len(expired)

    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """Onay istegini dondurur."""
        return self._requests.get(request_id)
