"""Canvas oturum yonetimi modulu.

Oturum olusturma, dogrulama, temizlik ve calisma dizini
guvenlik kontrolleri saglar.
"""

import logging
import time
import uuid
import os
from typing import Optional

from app.models.canvas_models import (
    CanvasConfig,
    CanvasSession,
    A2UIComponent,
)

logger = logging.getLogger(__name__)


class CanvasSessionManager:
    """Canvas oturum yoneticisi.

    Oturum yasam dongusu, calisma dizini yonetimi ve
    guvenlik dogrulamasi saglar.
    """

    def __init__(self, config: Optional[CanvasConfig] = None) -> None:
        """Oturum yoneticisini baslatir.

        Args:
            config: Canvas yapilandirmasi
        """
        self.config = config or CanvasConfig()
        self._sessions: dict[str, CanvasSession] = {}
        self._history: list[dict] = []

    def _record_history(self, action: str, **kwargs) -> None:
        """Gecmis kaydina olay ekler."""
        self._history.append({
            "action": action,
            "timestamp": time.time(),
            **kwargs,
        })

    def create_session(self) -> CanvasSession:
        """Yeni canvas oturumu olusturur.

        Returns:
            Olusturulan oturum
        """
        if len(self._sessions) >= self.config.max_sessions:
            raise RuntimeError(
                f"Maksimum oturum sayisina ulasildi: {self.config.max_sessions}"
            )
        session_id = str(uuid.uuid4())
        now = time.time()
        root_dir = f"{self.config.snapshot_dir}/{session_id}"
        session = CanvasSession(
            session_id=session_id,
            created_at=now,
            last_activity=now,
            root_dir=root_dir,
            is_active=True,
        )
        self._sessions[session_id] = session
        self._record_history("create_session", session_id=session_id)
        logger.info(f"Oturum olusturuldu: {session_id}")
        return session

    def get_session(self, session_id: str) -> Optional[CanvasSession]:
        """Oturum bilgisini dondurur."""
        session = self._sessions.get(session_id)
        if session and session.is_active:
            session.last_activity = time.time()
            return session
        return None

    def close_session(self, session_id: str) -> bool:
        """Oturumu kapatir ve temizler."""
        session = self._sessions.get(session_id)
        if not session:
            return False
        session.is_active = False
        self._record_history("close_session", session_id=session_id)
        logger.info(f"Oturum kapatildi: {session_id}")
        return True

    def validate_path(self, session_id: str, path: str) -> bool:
        """Dosya yolunun oturum sinirlarinda oldugunu dogrular."""
        session = self._sessions.get(session_id)
        if not session:
            return False
        if ".." in path:
            logger.warning(f"Dizin gecisi tespit edildi: {path}")
            return False
        normalized = os.path.normpath(path)
        root = os.path.normpath(session.root_dir)
        if not normalized.startswith(root):
            logger.warning(f"Yol oturum disinda: {path}")
            return False
        return True

    def cleanup_expired(self) -> int:
        """Suresi dolmus oturumlari temizler."""
        now = time.time()
        expired = []
        for sid, session in self._sessions.items():
            if session.is_active and (now - session.last_activity) > self.config.session_timeout:
                expired.append(sid)
        for sid in expired:
            self.close_session(sid)
        if expired:
            self._record_history("cleanup_expired", count=len(expired))
        return len(expired)

    def list_sessions(self) -> list[CanvasSession]:
        """Aktif oturumlari listeler."""
        return [s for s in self._sessions.values() if s.is_active]

    def get_history(self) -> list[dict]:
        """Gecmis kayitlarini dondurur."""
        return list(self._history)

    def get_stats(self) -> dict:
        """Istatistikleri dondurur."""
        active = [s for s in self._sessions.values() if s.is_active]
        closed = [s for s in self._sessions.values() if not s.is_active]
        return {
            "total_sessions": len(self._sessions),
            "active_sessions": len(active),
            "closed_sessions": len(closed),
            "max_sessions": self.config.max_sessions,
            "history_count": len(self._history),
        }
