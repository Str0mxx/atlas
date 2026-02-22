"""Camera Node - kamera dugum modulu.

Kamera cihazlarindan goruntu ve video yakalama islevleri.
"""

import logging
import time
import uuid
from typing import Optional

from app.models.nodes_models import CameraCapture, NodesConfig

logger = logging.getLogger(__name__)


class CameraNode:
    """Kamera dugumu yonetim sinifi."""

    def __init__(self, config: Optional[NodesConfig] = None) -> None:
        """CameraNode baslatici."""
        self.config = config or NodesConfig()
        self._captures: dict[str, CameraCapture] = {}
        self._node_captures: dict[str, list[str]] = {}
        self._history: list[dict] = []

    def _record_history(self, action: str, details: Optional[dict] = None) -> None:
        """Gecmis kaydina yeni bir giris ekler."""
        self._history.append({"action": action, "timestamp": time.time(), "details": details or {}})

    def get_history(self) -> list[dict]:
        return list(self._history)

    def get_stats(self) -> dict:
        return {"total_captures": len(self._captures), "active_nodes": len(self._node_captures)}

    def snap(self, node_id: str, format: str = "jpg") -> CameraCapture:
        """Tek bir fotograf ceker."""
        cid = str(uuid.uuid4())
        c = CameraCapture(capture_id=cid, node_id=node_id, capture_type="snap",
            filepath=f"{self.config.capture_dir}/{node_id}_{cid}.{format}",
            width=1920, height=1080, timestamp=time.time(), format=format)
        self._captures[cid] = c
        self._node_captures.setdefault(node_id, []).append(cid)
        self._record_history("snap", {"node_id": node_id, "capture_id": cid})
        return c

    def clip(self, node_id: str, duration: float = 10.0, format: str = "mp4") -> CameraCapture:
        """Video klip kaydeder."""
        cid = str(uuid.uuid4())
        c = CameraCapture(capture_id=cid, node_id=node_id, capture_type="clip",
            filepath=f"{self.config.capture_dir}/{node_id}_{cid}.{format}",
            width=1920, height=1080, duration=duration, timestamp=time.time(), format=format)
        self._captures[cid] = c
        self._node_captures.setdefault(node_id, []).append(cid)
        self._record_history("clip", {"node_id": node_id, "duration": duration})
        return c

    def get_captures(self, node_id: str, limit: int = 10) -> list[CameraCapture]:
        """Dugumun yakalamalarini listeler."""
        ids = self._node_captures.get(node_id, [])[-limit:]
        return [self._captures[i] for i in ids if i in self._captures]

    def delete_capture(self, capture_id: str) -> bool:
        """Yakalama kaydini siler."""
        if capture_id not in self._captures:
            return False
        cap = self._captures.pop(capture_id)
        if cap.node_id in self._node_captures:
            self._node_captures[cap.node_id] = [c for c in self._node_captures[cap.node_id] if c != capture_id]
        self._record_history("delete_capture", {"capture_id": capture_id})
        return True

    def configure(self, node_id: str, settings: dict) -> dict:
        """Kamera ayarlarini yapilandirir."""
        self._record_history("configure", {"node_id": node_id, "settings": settings})
        return {"node_id": node_id, "applied": settings}
