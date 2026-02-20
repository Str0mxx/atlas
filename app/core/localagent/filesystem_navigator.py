"""
File System Navigator modulu.

Dizin listeleme, dosya islemleri, arama,
izinler ve yol cozumleme.
"""

import fnmatch
import logging
import os
import shutil
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class FileSystemNavigator:
    """Dosya sistemi gezgini.

    Attributes:
        _base_path: Temel calisma yolu.
        _history: Islem gecmisi.
        _stats: Istatistikler.
    """

    MAX_SEARCH_RESULTS = 500
    MAX_FILE_READ_SIZE = 10 * 1024 * 1024  # 10 MB

    def __init__(self, base_path: str = "") -> None:
        self._base_path: str = base_path or os.getcwd()
        self._history: list[dict] = []
        self._stats: dict[str, int] = {
            "listings": 0,
            "reads": 0,
            "writes": 0,
            "deletes": 0,
            "searches": 0,
            "directories_created": 0,
        }
        logger.info("FileSystemNavigator baslatildi: %s", self._base_path)

    @property
    def base_path(self) -> str:
        return self._base_path

    @property
    def history_count(self) -> int:
        return len(self._history)

    def list_directory(self, path: str = "") -> dict[str, Any]:
        """Dizini listeler.

        Args:
            path: Listelenecek dizin yolu. Bos ise base_path kullanilir.

        Returns:
            Dizin icerigi.
        """
        try:
            target = self._resolve(path)
            if not os.path.isdir(target):
                return {"listed": False, "error": "dizin_bulunamadi", "path": target}

            entries = []
            for name in sorted(os.listdir(target)):
                full = os.path.join(target, name)
                try:
                    stat = os.stat(full)
                    entries.append({
                        "name": name,
                        "path": full,
                        "is_dir": os.path.isdir(full),
                        "size": stat.st_size,
                        "modified": stat.st_mtime,
                    })
                except OSError:
                    entries.append({"name": name, "path": full, "error": "erisim_hatasi"})

            self._stats["listings"] += 1
            self._log("list", target)
            return {
                "listed": True,
                "path": target,
                "entries": entries,
                "count": len(entries),
            }
        except Exception as e:
            logger.error("Dizin listeleme hatasi: %s", e)
            return {"listed": False, "error": str(e)}

    def read_file(self, path: str = "", encoding: str = "utf-8") -> dict[str, Any]:
        """Dosya icerigini okur.

        Args:
            path: Okunacak dosya yolu.
            encoding: Dosya kodlamasi.

        Returns:
            Dosya icerigi.
        """
        try:
            if not path:
                return {"read": False, "error": "yol_gerekli"}

            target = self._resolve(path)
            if not os.path.isfile(target):
                return {"read": False, "error": "dosya_bulunamadi", "path": target}

            size = os.path.getsize(target)
            if size > self.MAX_FILE_READ_SIZE:
                return {
                    "read": False,
                    "error": "dosya_cok_buyuk",
                    "size": size,
                    "max": self.MAX_FILE_READ_SIZE,
                }

            with open(target, "r", encoding=encoding, errors="replace") as f:
                content = f.read()

            self._stats["reads"] += 1
            self._log("read", target)
            return {
                "read": True,
                "path": target,
                "content": content,
                "size": size,
                "encoding": encoding,
            }
        except Exception as e:
            logger.error("Dosya okuma hatasi: %s", e)
            return {"read": False, "error": str(e)}

    def write_file(
        self,
        path: str = "",
        content: str = "",
        encoding: str = "utf-8",
        overwrite: bool = True,
    ) -> dict[str, Any]:
        """Dosyaya yazar.

        Args:
            path: Yazilacak dosya yolu.
            content: Yazilacak icerik.
            encoding: Dosya kodlamasi.
            overwrite: Mevcut dosyanin uzerine yazilsin mi.

        Returns:
            Yazma sonucu.
        """
        try:
            if not path:
                return {"written": False, "error": "yol_gerekli"}

            target = self._resolve(path)

            if os.path.exists(target) and not overwrite:
                return {"written": False, "error": "dosya_mevcut", "path": target}

            # Ust dizin yoksa olustur
            os.makedirs(os.path.dirname(target) or ".", exist_ok=True)

            with open(target, "w", encoding=encoding) as f:
                f.write(content)

            self._stats["writes"] += 1
            self._log("write", target)
            return {
                "written": True,
                "path": target,
                "size": len(content.encode(encoding)),
            }
        except Exception as e:
            logger.error("Dosya yazma hatasi: %s", e)
            return {"written": False, "error": str(e)}

    def delete(self, path: str = "", recursive: bool = False) -> dict[str, Any]:
        """Dosya veya dizini siler.

        Args:
            path: Silinecek yol.
            recursive: Dizinleri icerikleriyle sil.

        Returns:
            Silme sonucu.
        """
        try:
            if not path:
                return {"deleted": False, "error": "yol_gerekli"}

            target = self._resolve(path)
            if not os.path.exists(target):
                return {"deleted": False, "error": "yol_bulunamadi", "path": target}

            if os.path.isdir(target):
                if recursive:
                    shutil.rmtree(target)
                else:
                    os.rmdir(target)
            else:
                os.remove(target)

            self._stats["deletes"] += 1
            self._log("delete", target)
            return {"deleted": True, "path": target}
        except Exception as e:
            logger.error("Silme hatasi: %s", e)
            return {"deleted": False, "error": str(e)}

    def create_directory(self, path: str = "", parents: bool = True) -> dict[str, Any]:
        """Dizin olusturur.

        Args:
            path: Olusturulacak dizin yolu.
            parents: Ust dizinler de olusturulsun mu.

        Returns:
            Olusturma sonucu.
        """
        try:
            if not path:
                return {"created": False, "error": "yol_gerekli"}

            target = self._resolve(path)
            if os.path.exists(target):
                return {"created": False, "error": "zaten_mevcut", "path": target}

            os.makedirs(target, exist_ok=parents)
            self._stats["directories_created"] += 1
            self._log("mkdir", target)
            return {"created": True, "path": target}
        except Exception as e:
            logger.error("Dizin olusturma hatasi: %s", e)
            return {"created": False, "error": str(e)}

    def search(
        self,
        pattern: str = "*",
        root: str = "",
        max_results: int = 50,
    ) -> dict[str, Any]:
        """Dosya arar.

        Args:
            pattern: Arama deseni (glob).
            root: Arama koku. Bos ise base_path kullanilir.
            max_results: Maksimum sonuc sayisi.

        Returns:
            Arama sonuclari.
        """
        try:
            if not pattern:
                return {"searched": False, "error": "desen_gerekli"}

            search_root = self._resolve(root) if root else self._base_path
            if not os.path.isdir(search_root):
                return {"searched": False, "error": "dizin_bulunamadi", "root": search_root}

            results = []
            limit = min(max_results, self.MAX_SEARCH_RESULTS)

            for dirpath, dirnames, filenames in os.walk(search_root):
                for name in filenames + dirnames:
                    if fnmatch.fnmatch(name, pattern):
                        results.append(os.path.join(dirpath, name))
                        if len(results) >= limit:
                            break
                if len(results) >= limit:
                    break

            self._stats["searches"] += 1
            self._log("search", search_root)
            return {
                "searched": True,
                "pattern": pattern,
                "root": search_root,
                "results": results,
                "count": len(results),
                "truncated": len(results) >= limit,
            }
        except Exception as e:
            logger.error("Arama hatasi: %s", e)
            return {"searched": False, "error": str(e)}

    def get_permissions(self, path: str = "") -> dict[str, Any]:
        """Dosya izinlerini dondurur.

        Args:
            path: Kontrol edilecek yol.

        Returns:
            Izin bilgisi.
        """
        try:
            if not path:
                return {"retrieved": False, "error": "yol_gerekli"}

            target = self._resolve(path)
            if not os.path.exists(target):
                return {"retrieved": False, "error": "yol_bulunamadi", "path": target}

            stat = os.stat(target)
            mode = stat.st_mode

            return {
                "retrieved": True,
                "path": target,
                "mode": oct(mode),
                "readable": os.access(target, os.R_OK),
                "writable": os.access(target, os.W_OK),
                "executable": os.access(target, os.X_OK),
                "is_dir": os.path.isdir(target),
                "is_file": os.path.isfile(target),
                "size": stat.st_size,
                "modified": stat.st_mtime,
            }
        except Exception as e:
            logger.error("Izin alma hatasi: %s", e)
            return {"retrieved": False, "error": str(e)}

    def resolve_path(self, path: str = "") -> dict[str, Any]:
        """Yolu mutlak yola cozumler.

        Args:
            path: Cozumlenecek yol.

        Returns:
            Cozumleme sonucu.
        """
        try:
            if not path:
                return {"resolved": False, "error": "yol_gerekli"}

            resolved = self._resolve(path)
            return {
                "resolved": True,
                "original": path,
                "absolute": resolved,
                "exists": os.path.exists(resolved),
                "is_dir": os.path.isdir(resolved),
                "is_file": os.path.isfile(resolved),
            }
        except Exception as e:
            logger.error("Yol cozumleme hatasi: %s", e)
            return {"resolved": False, "error": str(e)}

    def copy(self, src: str = "", dst: str = "") -> dict[str, Any]:
        """Dosya veya dizini kopyalar.

        Args:
            src: Kaynak yol.
            dst: Hedef yol.

        Returns:
            Kopyalama sonucu.
        """
        try:
            if not src or not dst:
                return {"copied": False, "error": "kaynak_ve_hedef_gerekli"}

            src_path = self._resolve(src)
            dst_path = self._resolve(dst)

            if not os.path.exists(src_path):
                return {"copied": False, "error": "kaynak_bulunamadi", "src": src_path}

            if os.path.isdir(src_path):
                shutil.copytree(src_path, dst_path)
            else:
                shutil.copy2(src_path, dst_path)

            self._log("copy", f"{src_path} -> {dst_path}")
            return {"copied": True, "src": src_path, "dst": dst_path}
        except Exception as e:
            logger.error("Kopyalama hatasi: %s", e)
            return {"copied": False, "error": str(e)}

    def get_summary(self) -> dict[str, Any]:
        """Ozet bilgi dondurur.

        Returns:
            Ozet.
        """
        try:
            return {
                "retrieved": True,
                "base_path": self._base_path,
                "history_count": self.history_count,
                "stats": dict(self._stats),
            }
        except Exception as e:
            logger.error("Ozet hatasi: %s", e)
            return {"retrieved": False, "error": str(e)}

    # -- Ozel yardimci metodlar

    def _resolve(self, path: str) -> str:
        """Yolu base_path'e gore cozumler."""
        if not path:
            return self._base_path
        p = Path(path)
        if p.is_absolute():
            return str(p)
        return str(Path(self._base_path) / p)

    def _log(self, action: str, path: str) -> None:
        """Islem gecmisine ekler."""
        self._history.append({
            "action": action,
            "path": path,
            "timestamp": time.time(),
        })
