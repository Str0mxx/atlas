"""
Clipboard Access modulu.

Pano okuma/yazma, gecmis, format yonetimi,
cross-platform destek.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ClipboardAccess:
    """Pano erisim yoneticisi.

    Attributes:
        _content: Mevcut pano icerigi.
        _format: Mevcut format.
        _history: Pano gecmisi.
        _max_history: Maksimum gecmis boyutu.
        _stats: Istatistikler.
    """

    SUPPORTED_FORMATS = frozenset({"text", "html", "rtf", "image", "files"})
    MAX_HISTORY = 50

    def __init__(self, max_history: int = 50) -> None:
        """Pano erisimini baslatir."""
        self._content: str = ""
        self._format: str = "text"
        self._history: list[dict] = []
        self._max_history: int = max(1, max_history)
        self._use_system: bool = self._try_import_clipboard()
        self._stats: dict[str, int] = {
            "reads": 0,
            "writes": 0,
            "clears": 0,
            "history_views": 0,
        }
        logger.info("ClipboardAccess baslatildi (system=%s)", self._use_system)

    @property
    def history_count(self) -> int:
        return len(self._history)

    @property
    def current_format(self) -> str:
        return self._format

    def read(self) -> dict[str, Any]:
        """Pano icerigini okur.

        Returns:
            Pano icerigi ve metaveri.
        """
        try:
            content = ""
            if self._use_system:
                try:
                    import pyperclip  # type: ignore
                    content = pyperclip.paste() or ""
                    self._content = content
                except Exception:
                    content = self._content
            else:
                content = self._content

            self._stats["reads"] += 1
            return {
                "read": True,
                "content": content,
                "format": self._format,
                "length": len(content),
            }
        except Exception as e:
            logger.error("Pano okuma hatasi: %s", e)
            return {"read": False, "error": str(e)}

    def write(self, content: str = "", fmt: str = "text") -> dict[str, Any]:
        """Panoya yazar.

        Args:
            content: Yazilacak icerik.
            fmt: Format (text/html/rtf/image/files).

        Returns:
            Yazma sonucu.
        """
        try:
            if fmt not in self.SUPPORTED_FORMATS:
                return {
                    "written": False,
                    "error": "desteklenmeyen_format",
                    "format": fmt,
                }

            old_content = self._content
            old_format = self._format
            self._content = content
            self._format = fmt

            if self._use_system and fmt == "text":
                try:
                    import pyperclip  # type: ignore
                    pyperclip.copy(content)
                except Exception:
                    pass

            # Onceki icerigi gecmise ekle
            if old_content:
                self._add_history(old_content, old_format)

            self._stats["writes"] += 1
            return {
                "written": True,
                "length": len(content),
                "format": fmt,
            }
        except Exception as e:
            logger.error("Pano yazma hatasi: %s", e)
            return {"written": False, "error": str(e)}

    def clear(self) -> dict[str, Any]:
        """Panoyu temizler.

        Returns:
            Temizleme sonucu.
        """
        try:
            if self._content:
                self._add_history(self._content, self._format)

            self._content = ""
            self._format = "text"

            if self._use_system:
                try:
                    import pyperclip  # type: ignore
                    pyperclip.copy("")
                except Exception:
                    pass

            self._stats["clears"] += 1
            return {"cleared": True}
        except Exception as e:
            logger.error("Pano temizleme hatasi: %s", e)
            return {"cleared": False, "error": str(e)}

    def get_history(self, limit: int = 10) -> dict[str, Any]:
        """Pano gecmisini dondurur.

        Args:
            limit: En son kac kayit dondurulsun.

        Returns:
            Gecmis listesi ve meta bilgileri.
        """
        try:
            self._stats["history_views"] += 1
            recent = self._history[-limit:] if limit > 0 else list(self._history)
            return {
                "retrieved": True,
                "history": recent,
                "total": len(self._history),
                "returned": len(recent),
            }
        except Exception as e:
            logger.error("Gecmis alma hatasi: %s", e)
            return {"retrieved": False, "error": str(e)}

    def get_format(self) -> dict[str, Any]:
        """Mevcut format bilgisini dondurur.

        Returns:
            Format bilgisi ve desteklenen formatlar.
        """
        try:
            return {
                "retrieved": True,
                "format": self._format,
                "supported_formats": sorted(self.SUPPORTED_FORMATS),
                "content_length": len(self._content),
            }
        except Exception as e:
            logger.error("Format alma hatasi: %s", e)
            return {"retrieved": False, "error": str(e)}

    def get_summary(self) -> dict[str, Any]:
        """Ozet bilgi dondurur.

        Returns:
            Durum ozeti.
        """
        try:
            return {
                "retrieved": True,
                "current_format": self._format,
                "content_length": len(self._content),
                "history_count": self.history_count,
                "system_clipboard": self._use_system,
                "stats": dict(self._stats),
            }
        except Exception as e:
            logger.error("Ozet hatasi: %s", e)
            return {"retrieved": False, "error": str(e)}

    # -- Ozel yardimci metodlar -----------------------------------------------

    def _try_import_clipboard(self) -> bool:
        """pyperclip kullanilabilirligini kontrol eder."""
        try:
            import pyperclip  # type: ignore
            pyperclip.paste()
            return True
        except Exception:
            return False

    def _add_history(self, content: str, fmt: str) -> None:
        """Gecmise yeni kayit ekler, maksimum boyutu asmazsa eski kaydolari siler."""
        self._history.append({
            "content": content[:200],  # ilk 200 karakter sakla
            "format": fmt,
            "timestamp": time.time(),
        })
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
