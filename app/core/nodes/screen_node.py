"""Screen Node - ekran dugum modulu.

Ekran goruntusu ve kayit islevleri.
"""

import logging
import time
import uuid
from typing import Optional

from app.models.nodes_models import NodesConfig, ScreenCapture

logger = logging.getLogger(__name__)


class ScreenNode:
    """Ekran dugumu yonetim sinifi."""

    def __init__(self, config: Optional[NodesConfig] = None) -> None:
        """ScreenNode baslatici."""
        self.config = config or NodesConfig()
        self._captures: dict[str, ScreenCapture] = {}
        self._active_recordings: dict[str, str] = {}
        self._history: list[dict] = []

    def _record_history(self, action: str, details: Optional[dict] = None) -> None:
        """Gecmis kaydina yeni bir giris ekler."""
        self._history.append({"action": action, "timestamp": time.time(), "details": details or {}})

    def get_history(self) -> list[dict]:
        return list(self._history)

    def get_stats(self) -> dict:
        return {"total_captures": len(self._captures), "active_recordings": len(self._active_recordings)}

    def screenshot(self, node_id: str, format: str = "png") -> ScreenCapture:
        """Ekran goruntusu alir."""
        cid = str(uuid.uuid4())
        c = ScreenCapture(capture_id=cid, node_id=node_id, capture_type="screenshot",
            filepath=f"{self.config.capture_dir}/{node_id}_screen_{cid}.{format}",
            width=1920, height=1080, timestamp=time.time(), format=format)
        self._captures[cid] = c
        self._record_history("screenshot", {"node_id": node_id, "capture_id": cid})
        return c

    def record(self, node_id: str, duration: float = 30.0) -> ScreenCapture:
        """Ekran kaydi baslatir."""
        cid = str(uuid.uuid4())
        c = ScreenCapture(capture_id=cid, node_id=node_id, capture_type="recording",
            filepath=f"{self.config.capture_dir}/{node_id}_rec_{cid}.mp4",
            width=1920, height=1080, duration=duration, timestamp=time.time(), format="mp4")
        self._captures[cid] = c
        self._active_recordings[node_id] = cid
        self._record_history("record", {"node_id": node_id, "duration": duration})
        return c

    def get_recordings(self, node_id: str) -> list[ScreenCapture]:
        """Dugumun ekran kayitlarini listeler."""
        return [c for c in self._captures.values() if c.node_id == node_id and c.capture_type == "recording"]

    def stop_recording(self, node_id: str) -> bool:
        """Aktif ekran kaydini durdurur."""
        if node_id in self._active_recordings:
            del self._active_recordings[node_id]
            self._record_history("stop_recording", {"node_id": node_id})
            return True
        return False
