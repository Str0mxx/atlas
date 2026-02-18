"""
File Watcher modulu.

Dosya izleme, degisiklik tespiti,
debouncing, filtre kaliplari, olay yayimi.
"""

import fnmatch
import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)


class FileWatcher:
    """Dosya izleyici.

    Attributes:
        _watched: Izlenen dosya/dizin bilgileri.
        _callbacks: Olay dinleyicileri.
        _filters: Filtre kaliplari.
        _stats: Istatistikler.
    """

    def __init__(
        self,
        debounce_ms: int = 500,
    ) -> None:
        """Izleyiciyi baslatir.

        Args:
            debounce_ms: Debounce suresi (ms).
        """
        self._debounce_ms: int = debounce_ms
        self._watched: dict[str, dict] = {}
        self._callbacks: list[Any] = []
        self._filters: dict[str, list[str]] = {
            "include": [],
            "exclude": [],
        }
        self._pending: dict[str, float] = {}
        self._stats: dict[str, int] = {
            "files_watched": 0,
            "changes_detected": 0,
            "events_emitted": 0,
            "callbacks_registered": 0,
            "polls_run": 0,
        }
        logger.info("FileWatcher baslatildi (debounce=%dms)", debounce_ms)

    @property
    def watched_count(self) -> int:
        """Izlenen dosya sayisi."""
        return len(self._watched)

    @property
    def callback_count(self) -> int:
        """Kayitli callback sayisi."""
        return len(self._callbacks)

    def watch(
        self,
        path: str = "",
        recursive: bool = False,
    ) -> dict[str, Any]:
        """Dosya veya dizin izlemeye ekler.

        Args:
            path: Izlenecek yol.
            recursive: Alt dizinleri de izle.

        Returns:
            Izleme bilgisi.
        """
        try:
            if not path:
                return {"watching": False, "error": "yol_gerekli"}

            normalized = os.path.normpath(path)
            stat = self._get_stat(normalized)

            self._watched[normalized] = {
                "path": normalized,
                "recursive": recursive,
                "stat": stat,
                "added_at": time.time(),
            }
            self._stats["files_watched"] += 1

            logger.debug("Izlemeye eklendi: %s", normalized)
            return {
                "watching": True,
                "path": normalized,
                "recursive": recursive,
                "exists": stat is not None,
            }
        except Exception as e:
            logger.error("Izleme ekleme hatasi: %s", e)
            return {"watching": False, "error": str(e)}

    def unwatch(self, path: str = "") -> dict[str, Any]:
        """Dosyayi izlemeden cikarir.

        Args:
            path: Cikarilacak yol.

        Returns:
            Islem bilgisi.
        """
        try:
            if not path:
                return {"removed": False, "error": "yol_gerekli"}

            normalized = os.path.normpath(path)
            if normalized not in self._watched:
                return {"removed": False, "reason": "izlenmiyordu"}

            del self._watched[normalized]
            self._pending.pop(normalized, None)
            return {"removed": True, "path": normalized}
        except Exception as e:
            logger.error("Izleme kaldirma hatasi: %s", e)
            return {"removed": False, "error": str(e)}

    def add_filter(
        self,
        pattern: str = "",
        filter_type: str = "include",
    ) -> dict[str, Any]:
        """Filtre kalıbi ekler.

        Args:
            pattern: Glob kalıbi (orn: '*.env', '*.yaml').
            filter_type: 'include' veya 'exclude'.

        Returns:
            Filtre bilgisi.
        """
        try:
            if not pattern:
                return {"added": False, "error": "kalip_gerekli"}

            if filter_type not in ("include", "exclude"):
                return {"added": False, "error": "gecersiz_tip"}

            if pattern not in self._filters[filter_type]:
                self._filters[filter_type].append(pattern)

            return {
                "added": True,
                "pattern": pattern,
                "type": filter_type,
                "total": len(self._filters[filter_type]),
            }
        except Exception as e:
            logger.error("Filtre ekleme hatasi: %s", e)
            return {"added": False, "error": str(e)}

    def remove_filter(
        self,
        pattern: str = "",
        filter_type: str = "include",
    ) -> dict[str, Any]:
        """Filtre kalibini kaldirir.

        Args:
            pattern: Cikarilacak kalip.
            filter_type: 'include' veya 'exclude'.

        Returns:
            Islem bilgisi.
        """
        try:
            if filter_type not in ("include", "exclude"):
                return {"removed": False, "error": "gecersiz_tip"}

            if pattern in self._filters[filter_type]:
                self._filters[filter_type].remove(pattern)
                return {"removed": True, "pattern": pattern}

            return {"removed": False, "reason": "kalip_bulunamadi"}
        except Exception as e:
            logger.error("Filtre kaldirma hatasi: %s", e)
            return {"removed": False, "error": str(e)}

    def register_callback(self, callback: Any) -> dict[str, Any]:
        """Degisiklik olayı icin callback kaydeder.

        Args:
            callback: Cagrilacak fonksiyon (path, event_type).

        Returns:
            Kayit bilgisi.
        """
        try:
            if callback is None:
                return {"registered": False, "error": "callback_gerekli"}

            if callback not in self._callbacks:
                self._callbacks.append(callback)
                self._stats["callbacks_registered"] += 1

            return {
                "registered": True,
                "total_callbacks": len(self._callbacks),
            }
        except Exception as e:
            logger.error("Callback kayit hatasi: %s", e)
            return {"registered": False, "error": str(e)}

    def unregister_callback(self, callback: Any) -> dict[str, Any]:
        """Callback kaydini siler.

        Args:
            callback: Kaydi silinecek fonksiyon.

        Returns:
            Islem bilgisi.
        """
        try:
            if callback in self._callbacks:
                self._callbacks.remove(callback)
                return {"unregistered": True}
            return {"unregistered": False, "reason": "kayitli_degil"}
        except Exception as e:
            logger.error("Callback silme hatasi: %s", e)
            return {"unregistered": False, "error": str(e)}

    def poll(self) -> dict[str, Any]:
        """Degisiklikleri kontrol eder (manuel poll).

        Returns:
            Tespit edilen degisiklikler.
        """
        try:
            self._stats["polls_run"] += 1
            changes = []
            now = time.time()
            debounce_s = self._debounce_ms / 1000.0

            for path, info in list(self._watched.items()):
                new_stat = self._get_stat(path)
                old_stat = info.get("stat")

                changed, event_type = self._detect_change(
                    old_stat, new_stat
                )

                if changed:
                    # Debounce kontrolu
                    last_pending = self._pending.get(path, 0)
                    if now - last_pending >= debounce_s:
                        if self._passes_filters(path):
                            self._watched[path]["stat"] = new_stat
                            self._pending[path] = now
                            self._stats["changes_detected"] += 1
                            changes.append({
                                "path": path,
                                "event": event_type,
                                "timestamp": now,
                            })
                            self._emit(path, event_type)

            return {
                "polled": True,
                "changes": changes,
                "change_count": len(changes),
            }
        except Exception as e:
            logger.error("Poll hatasi: %s", e)
            return {"polled": False, "error": str(e)}

    def emit(
        self,
        path: str = "",
        event_type: str = "modified",
    ) -> dict[str, Any]:
        """Olay yayar (test/manuel tetiklemek icin).

        Args:
            path: Degisen dosya yolu.
            event_type: Olay tipi (created/modified/deleted).

        Returns:
            Yayin bilgisi.
        """
        try:
            if not path:
                return {"emitted": False, "error": "yol_gerekli"}

            self._emit(path, event_type)
            return {
                "emitted": True,
                "path": path,
                "event": event_type,
                "notified": len(self._callbacks),
            }
        except Exception as e:
            logger.error("Olay yayin hatasi: %s", e)
            return {"emitted": False, "error": str(e)}

    def get_watched_list(self) -> dict[str, Any]:
        """Izlenen dosya listesini dondurur.

        Returns:
            Izleme listesi.
        """
        try:
            entries = []
            for path, info in self._watched.items():
                entries.append({
                    "path": path,
                    "recursive": info.get("recursive", False),
                    "exists": info.get("stat") is not None,
                })
            return {
                "retrieved": True,
                "entries": entries,
                "count": len(entries),
            }
        except Exception as e:
            logger.error("Liste alma hatasi: %s", e)
            return {"retrieved": False, "error": str(e)}

    def get_summary(self) -> dict[str, Any]:
        """Ozet bilgi dondurur.

        Returns:
            Ozet.
        """
        try:
            return {
                "retrieved": True,
                "watched_count": self.watched_count,
                "callback_count": self.callback_count,
                "include_filters": len(self._filters["include"]),
                "exclude_filters": len(self._filters["exclude"]),
                "debounce_ms": self._debounce_ms,
                "stats": dict(self._stats),
            }
        except Exception as e:
            logger.error("Ozet hatasi: %s", e)
            return {"retrieved": False, "error": str(e)}

    # ── Ozel yardimci metodlar ────────────────────────────────────────────────

    def _get_stat(self, path: str) -> dict | None:
        """Dosya istatistigi alir."""
        try:
            st = os.stat(path)
            return {
                "mtime": st.st_mtime,
                "size": st.st_size,
            }
        except OSError:
            return None

    def _detect_change(
        self,
        old: dict | None,
        new: dict | None,
    ) -> tuple[bool, str]:
        """Degisiklik tipini tespit eder."""
        if old is None and new is not None:
            return True, "created"
        if old is not None and new is None:
            return True, "deleted"
        if old is not None and new is not None:
            if old["mtime"] != new["mtime"] or old["size"] != new["size"]:
                return True, "modified"
        return False, ""

    def _passes_filters(self, path: str) -> bool:
        """Dosyanin filtrelerden gecip gecmedigini kontrol eder."""
        filename = os.path.basename(path)

        # Exclude filtresi once kontrol edilir
        for pattern in self._filters["exclude"]:
            if fnmatch.fnmatch(filename, pattern):
                return False

        # Include filtresi: bos ise hepsi gecsin
        if not self._filters["include"]:
            return True

        for pattern in self._filters["include"]:
            if fnmatch.fnmatch(filename, pattern):
                return True

        return False

    def _emit(self, path: str, event_type: str) -> None:
        """Kayitli callback'leri cagırir."""
        self._stats["events_emitted"] += 1
        for cb in list(self._callbacks):
            try:
                cb(path, event_type)
            except Exception as e:
                logger.warning("Callback hatasi: %s", e)
