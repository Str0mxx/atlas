"""ATLAS Kullanici Iletisimi modulu.

Telegram uzerinden ilerleme guncellemeleri, eksik bilgi isteme,
deploy oncesi onay, hata aciklamalari ve basari bildirimleri.
"""

import logging
import time
from typing import Any

from app.models.jit import BuildPhase, BuildProgress, CapabilityStatus

logger = logging.getLogger(__name__)


class UserCommunicator:
    """Kullanici iletisim sistemi.

    JIT surecinde kullanici ile iletisim kurar:
    ilerleme bildirimleri, onay istekleri, hata
    aciklamalari ve basari bildirimleri.

    Attributes:
        _messages: Gonderilen mesajlar.
        _pending_approvals: Bekleyen onaylar.
        _progress_updates: Ilerleme guncellemeleri.
    """

    def __init__(self) -> None:
        """Kullanici iletisim sistemini baslatir."""
        self._messages: list[dict[str, Any]] = []
        self._pending_approvals: dict[str, dict[str, Any]] = {}
        self._progress_updates: list[BuildProgress] = []

        logger.info("UserCommunicator baslatildi")

    def send_progress(self, capability_name: str, phase: BuildPhase, progress_pct: float, message: str = "") -> BuildProgress:
        """Ilerleme guncellesi gonderir.

        Args:
            capability_name: Yetenek adi.
            phase: Insa asamasi.
            progress_pct: Ilerleme yuzdesi (0-100).
            message: Ek mesaj.

        Returns:
            BuildProgress nesnesi.
        """
        progress = BuildProgress(
            capability_name=capability_name,
            phase=phase,
            progress_pct=min(100.0, max(0.0, progress_pct)),
            message=message or f"{capability_name}: {phase.value} ({progress_pct:.0f}%)",
        )
        self._progress_updates.append(progress)

        msg = {
            "type": "progress",
            "capability": capability_name,
            "phase": phase.value,
            "progress": progress_pct,
            "message": progress.message,
            "timestamp": time.time(),
        }
        self._messages.append(msg)

        logger.info("Ilerleme: %s - %s (%.0f%%)", capability_name, phase.value, progress_pct)
        return progress

    def request_info(self, capability_name: str, question: str, options: list[str] | None = None) -> dict[str, Any]:
        """Kullanicidan bilgi ister.

        Args:
            capability_name: Yetenek adi.
            question: Soru.
            options: Secenekler (varsa).

        Returns:
            Istek bilgisi.
        """
        request = {
            "type": "info_request",
            "capability": capability_name,
            "question": question,
            "options": options or [],
            "timestamp": time.time(),
            "status": "pending",
        }
        self._messages.append(request)
        self._pending_approvals[f"info_{capability_name}"] = request

        logger.info("Bilgi istendi: %s - %s", capability_name, question)
        return request

    def request_approval(self, capability_name: str, description: str) -> dict[str, Any]:
        """Deploy oncesi onay ister.

        Args:
            capability_name: Yetenek adi.
            description: Ne onaylanacak.

        Returns:
            Onay istek bilgisi.
        """
        request = {
            "type": "approval",
            "capability": capability_name,
            "description": description,
            "timestamp": time.time(),
            "status": "pending",
        }
        self._messages.append(request)
        self._pending_approvals[f"deploy_{capability_name}"] = request

        logger.info("Onay istendi: %s", capability_name)
        return request

    def set_approval(self, key: str, approved: bool) -> bool:
        """Onay durumunu ayarlar.

        Args:
            key: Onay anahtari.
            approved: Onaylandi mi.

        Returns:
            Basarili mi.
        """
        if key not in self._pending_approvals:
            return False

        self._pending_approvals[key]["status"] = "approved" if approved else "rejected"
        return True

    def is_approved(self, key: str) -> bool:
        """Onayin verilip verilmedigini kontrol eder."""
        approval = self._pending_approvals.get(key)
        return approval is not None and approval.get("status") == "approved"

    def send_error(self, capability_name: str, error: str, suggestion: str = "") -> dict[str, Any]:
        """Hata aciklamasi gonderir.

        Args:
            capability_name: Yetenek adi.
            error: Hata mesaji.
            suggestion: Oneri.

        Returns:
            Mesaj bilgisi.
        """
        msg = {
            "type": "error",
            "capability": capability_name,
            "error": error,
            "suggestion": suggestion,
            "timestamp": time.time(),
        }
        self._messages.append(msg)

        logger.error("Hata bildirimi: %s - %s", capability_name, error)
        return msg

    def send_success(self, capability_name: str, summary: str) -> dict[str, Any]:
        """Basari bildirimi gonderir.

        Args:
            capability_name: Yetenek adi.
            summary: Ozet.

        Returns:
            Mesaj bilgisi.
        """
        msg = {
            "type": "success",
            "capability": capability_name,
            "summary": summary,
            "timestamp": time.time(),
        }
        self._messages.append(msg)

        logger.info("Basari bildirimi: %s", capability_name)
        return msg

    def get_messages(self, msg_type: str | None = None) -> list[dict[str, Any]]:
        """Mesajlari getirir.

        Args:
            msg_type: Filtre tipi (None = tumu).

        Returns:
            Mesaj listesi.
        """
        if msg_type:
            return [m for m in self._messages if m.get("type") == msg_type]
        return list(self._messages)

    @property
    def message_count(self) -> int:
        """Toplam mesaj sayisi."""
        return len(self._messages)

    @property
    def pending_approval_count(self) -> int:
        """Bekleyen onay sayisi."""
        return sum(1 for a in self._pending_approvals.values() if a.get("status") == "pending")

    @property
    def progress_history(self) -> list[BuildProgress]:
        """Ilerleme gecmisi."""
        return list(self._progress_updates)
