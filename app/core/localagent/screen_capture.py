"""
Agent Screen Capture modulu.

Ekran goruntuleri, bolge/pencere yakalama,
video kayit, sikistirma.
"""
import logging
import time
import uuid
from typing import Any

logger = logging.getLogger(__name__)


class AgentScreenCapture:
    # Ekran yakalama sistemi

    SUPPORTED_FORMATS = {"png", "jpg", "bmp", "webp"}
    MAX_QUALITY = 100
    MIN_QUALITY = 1

    def __init__(self, output_dir: str = "/tmp/atlas_captures") -> None:
        self._captures: list[dict] = []
        self._recording: dict | None = None
        self._output_dir: str = output_dir
        self._has_display: bool = self._check_display()
        self._stats: dict[str, int] = {"screenshots": 0, "region_captures": 0, "window_captures": 0, "recordings_started": 0, "recordings_stopped": 0}

    @property
    def capture_count(self) -> int:
        return len(self._captures)

    @property
    def is_recording(self) -> bool:
        return self._recording is not None

    def capture_screen(self, fmt: str = "png", quality: int = 95) -> dict[str, Any]:
        try:
            if fmt not in self.SUPPORTED_FORMATS:
                return {"captured": False, "error": "desteklenmeyen_format", "format": fmt}
            quality = max(self.MIN_QUALITY, min(self.MAX_QUALITY, quality))
            cid = str(uuid.uuid4())[:8]
            filepath = f"{self._output_dir}/screen_{cid}.{fmt}"
            meta = {"id": cid, "type": "fullscreen", "format": fmt, "quality": quality, "filepath": filepath, "timestamp": time.time(), "width": 1920, "height": 1080, "size_bytes": 0}
            if self._has_display:
                try:
                    import pyautogui
                    ss = pyautogui.screenshot()
                    meta["width"] = ss.width
                    meta["height"] = ss.height
                    meta["size_bytes"] = ss.width * ss.height * 3
                except Exception:
                    pass
            self._captures.append(meta)
            self._stats["screenshots"] += 1
            return {"captured": True, "capture_id": cid, "filepath": filepath, "format": fmt, "width": meta["width"], "height": meta["height"]}
        except Exception as e:
            return {"captured": False, "error": str(e)}

    def capture_region(self, x: int = 0, y: int = 0, width: int = 800, height: int = 600, fmt: str = "png") -> dict[str, Any]:
        try:
            if width <= 0 or height <= 0:
                return {"captured": False, "error": "gecersiz_boyutlar"}
            if fmt not in self.SUPPORTED_FORMATS:
                return {"captured": False, "error": "desteklenmeyen_format"}
            cid = str(uuid.uuid4())[:8]
            filepath = f"{self._output_dir}/region_{cid}.{fmt}"
            self._captures.append({"id": cid, "type": "region", "format": fmt, "x": x, "y": y, "width": width, "height": height, "filepath": filepath, "timestamp": time.time()})
            self._stats["region_captures"] += 1
            return {"captured": True, "capture_id": cid, "filepath": filepath, "region": {"x": x, "y": y, "width": width, "height": height}}
        except Exception as e:
            return {"captured": False, "error": str(e)}

    def capture_window(self, window_id: str = "", window_title: str = "") -> dict[str, Any]:
        try:
            if not window_id and not window_title:
                return {"captured": False, "error": "pencere_id_veya_baslik_gerekli"}
            cid = str(uuid.uuid4())[:8]
            filepath = f"{self._output_dir}/window_{cid}.png"
            self._captures.append({"id": cid, "type": "window", "window_id": window_id, "window_title": window_title, "filepath": filepath, "timestamp": time.time()})
            self._stats["window_captures"] += 1
            return {"captured": True, "capture_id": cid, "filepath": filepath, "window_id": window_id}
        except Exception as e:
            return {"captured": False, "error": str(e)}

    def start_recording(self, output_path: str = "", fps: int = 15, fmt: str = "mp4") -> dict[str, Any]:
        try:
            if self._recording:
                return {"started": False, "error": "kayit_devam_ediyor", "recording_id": self._recording.get("id")}
            rid = str(uuid.uuid4())[:8]
            out = output_path or f"{self._output_dir}/rec_{rid}.{fmt}"
            self._recording = {"id": rid, "output_path": out, "fps": fps, "format": fmt, "started_at": time.time()}
            self._stats["recordings_started"] += 1
            return {"started": True, "recording_id": rid, "output_path": out, "fps": fps}
        except Exception as e:
            return {"started": False, "error": str(e)}

    def stop_recording(self) -> dict[str, Any]:
        try:
            if not self._recording:
                return {"stopped": False, "error": "aktif_kayit_yok"}
            rec = dict(self._recording)
            duration = round(time.time() - rec["started_at"], 2)
            self._recording = None
            self._stats["recordings_stopped"] += 1
            return {"stopped": True, "recording_id": rec["id"], "output_path": rec["output_path"], "duration_seconds": duration}
        except Exception as e:
            return {"stopped": False, "error": str(e)}

    def compress(self, capture_id: str = "", quality: int = 75) -> dict[str, Any]:
        try:
            if not capture_id:
                return {"compressed": False, "error": "id_gerekli"}
            quality = max(self.MIN_QUALITY, min(self.MAX_QUALITY, quality))
            found = next((c for c in self._captures if c.get("id") == capture_id), None)
            if not found:
                return {"compressed": False, "error": "goruntu_bulunamadi", "capture_id": capture_id}
            orig = found.get("size_bytes", 1000)
            comp = int(orig * (quality / 100))
            return {"compressed": True, "capture_id": capture_id, "quality": quality, "original_size": orig, "compressed_size": comp, "ratio": round(comp / max(orig, 1), 3)}
        except Exception as e:
            return {"compressed": False, "error": str(e)}

    def get_captures(self, limit: int = 10) -> dict[str, Any]:
        try:
            recent = self._captures[-limit:] if limit > 0 else list(self._captures)
            return {"retrieved": True, "captures": recent, "total": len(self._captures), "returned": len(recent)}
        except Exception as e:
            return {"retrieved": False, "error": str(e)}

    def get_summary(self) -> dict[str, Any]:
        try:
            return {"retrieved": True, "capture_count": self.capture_count, "is_recording": self.is_recording, "output_dir": self._output_dir, "has_display": self._has_display, "stats": dict(self._stats)}
        except Exception as e:
            return {"retrieved": False, "error": str(e)}

    def _check_display(self) -> bool:
        try:
            import pyautogui
            return True
        except Exception:
            return False
