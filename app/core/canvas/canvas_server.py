"""Canvas sunucu modulu.

Ana canvas API yuzeyi. Push, reset, snapshot ve
oturum yonetimi islevlerini bir arada sunar.
"""

import logging
import time
import uuid
from typing import Any, Optional

from app.models.canvas_models import (
    A2UIComponent,
    CanvasCommand,
    CanvasConfig,
    CanvasPushRequest,
    CanvasSession,
    CanvasSnapshot,
)
from app.core.canvas.canvas_session import CanvasSessionManager
from app.core.canvas.websocket_manager import WebSocketManager
from app.core.canvas.component_renderer import ComponentRenderer
from app.core.canvas.a2ui_parser import A2UIParser

logger = logging.getLogger(__name__)


class CanvasServer:
    """Canvas sunucusu.

    Icerik push, oturum yonetimi, ekran goruntusu alma
    ve JavaScript calistirma islevlerini yonetir.
    """

    def __init__(self, config: Optional[CanvasConfig] = None) -> None:
        """Canvas sunucusunu baslatir.

        Args:
            config: Canvas yapilandirmasi
        """
        self.config = config or CanvasConfig()
        self.session_manager = CanvasSessionManager(config=self.config)
        self.ws_manager = WebSocketManager()
        self.renderer = ComponentRenderer()
        self.parser = A2UIParser(max_depth=self.config.max_component_depth)
        self._snapshots: dict[str, CanvasSnapshot] = {}
        self._history: list[dict] = []

    def _record_history(self, action: str, **kwargs) -> None:
        """Gecmis kaydina olay ekler."""
        self._history.append({
            "action": action,
            "timestamp": time.time(),
            **kwargs,
        })

    def push(self, session_id: str, html: str = "", components: Optional[list[A2UIComponent]] = None) -> bool:
        """Oturuma icerik gonderir.

        Args:
            session_id: Hedef oturum kimligi
            html: HTML icerigi
            components: A2UI bilesen listesi

        Returns:
            Basarili ise True
        """
        session = self.session_manager.get_session(session_id)
        if not session:
            logger.warning(f"Gecersiz oturum: {session_id}")
            return False

        # Bilesenler varsa render et
        rendered_html = html
        if components:
            parts = [self.renderer.render(c) for c in components]
            rendered_html = html + "".join(parts)
            session.components.extend(components)

        # WebSocket ile yayinla
        message = {
            "command": CanvasCommand.SURFACE_UPDATE.value,
            "html": rendered_html,
        }
        self.ws_manager.broadcast(session_id, message)
        self._record_history("push", session_id=session_id)
        logger.info(f"Icerik gonderildi: {session_id}")
        return True

    def reset(self, session_id: str) -> bool:
        """Canvas icerigini temizler.

        Args:
            session_id: Hedef oturum kimligi

        Returns:
            Basarili ise True
        """
        session = self.session_manager.get_session(session_id)
        if not session:
            return False

        session.components = []
        message = {"command": CanvasCommand.RESET.value}
        self.ws_manager.broadcast(session_id, message)
        self._record_history("reset", session_id=session_id)
        logger.info(f"Canvas sifirlandi: {session_id}")
        return True

    def eval_js(self, session_id: str, code: str) -> bool:
        """JavaScript kodunu calistirir (guvenlik kontrolu ile).

        Args:
            session_id: Hedef oturum kimligi
            code: Calistirilacak JS kodu

        Returns:
            Basarili ise True
        """
        if not self.config.enable_js_eval:
            logger.warning("JS eval devre disi birakilmis")
            return False

        session = self.session_manager.get_session(session_id)
        if not session:
            return False

        # Guvenlik kontrolu - tehlikeli kaliplari engelle
        dangerous_patterns = ["eval(", "Function(", "document.cookie", "window.location", "XMLHttpRequest"]
        for pattern in dangerous_patterns:
            if pattern.lower() in code.lower():
                logger.warning(f"Tehlikeli JS kalibi tespit edildi: {pattern}")
                return False

        message = {
            "command": CanvasCommand.EVAL.value,
            "js_code": code,
        }
        self.ws_manager.broadcast(session_id, message)
        self._record_history("eval_js", session_id=session_id)
        return True

    def snapshot(self, session_id: str) -> Optional[CanvasSnapshot]:
        """Canvas ekran goruntusu alir.

        Args:
            session_id: Hedef oturum kimligi

        Returns:
            Ekran goruntusu bilgisi veya None
        """
        session = self.session_manager.get_session(session_id)
        if not session:
            return None

        snapshot_id = str(uuid.uuid4())
        snap = CanvasSnapshot(
            session_id=session_id,
            snapshot_id=snapshot_id,
            filepath=f"{session.root_dir}/{snapshot_id}.png",
            timestamp=time.time(),
        )
        self._snapshots[snapshot_id] = snap

        # Istemcilere snapshot komutu gonder
        message = {
            "command": CanvasCommand.SNAPSHOT.value,
            "snapshot_id": snapshot_id,
        }
        self.ws_manager.broadcast(session_id, message)
        self._record_history("snapshot", session_id=session_id, snapshot_id=snapshot_id)
        logger.info(f"Ekran goruntusu istendi: {snapshot_id}")
        return snap

    def create_session(self) -> CanvasSession:
        """Yeni oturum olusturur.

        Returns:
            Olusturulan oturum
        """
        session = self.session_manager.create_session()
        self._record_history("create_session", session_id=session.session_id)
        return session

    def close_session(self, session_id: str) -> bool:
        """Oturumu kapatir.

        Args:
            session_id: Kapatilacak oturum kimligi

        Returns:
            Basarili ise True
        """
        result = self.session_manager.close_session(session_id)
        if result:
            self._record_history("close_session", session_id=session_id)
        return result

    def get_session(self, session_id: str) -> Optional[CanvasSession]:
        """Oturum bilgisini dondurur."""
        return self.session_manager.get_session(session_id)

    def list_sessions(self) -> list[CanvasSession]:
        """Aktif oturumlari listeler."""
        return self.session_manager.list_sessions()

    def get_history(self) -> list[dict]:
        """Gecmis kayitlarini dondurur."""
        return list(self._history)

    def get_stats(self) -> dict:
        """Istatistikleri dondurur."""
        return {
            "session_stats": self.session_manager.get_stats(),
            "ws_stats": self.ws_manager.get_stats(),
            "renderer_stats": self.renderer.get_stats(),
            "parser_stats": self.parser.get_stats(),
            "total_snapshots": len(self._snapshots),
            "history_count": len(self._history),
        }
