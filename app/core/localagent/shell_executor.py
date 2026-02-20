"""Shell Executor modulu.

Komut calistirma, cikti yakalama, hata yonetimi,
zaman asimi ve ortam yonetimi.
"""

import logging
import os
import subprocess
import time
import uuid
from typing import Any

logger = logging.getLogger(__name__)


class ShellExecutor:
    """Kabuk komutu yuruttucusu.

    Attributes:
        _cwd: Calisma dizini.
        _env: Ortam degiskenleri.
        _running: Calisiran islemler.
        _history: Komut gecmisi.
        _default_timeout: Varsayilan zaman asimi.
        _stats: Istatistikler.
    """

    DEFAULT_TIMEOUT = 30
    MAX_HISTORY = 100

    def __init__(self, default_timeout: int = 30) -> None:
        """Yuruttucuyu baslatir.

        Args:
            default_timeout: Varsayilan zaman asimi (saniye).
        """
        self._cwd: str = os.getcwd()
        self._env: dict[str, str] = dict(os.environ)
        self._running: dict[str, dict] = {}
        self._history: list[dict] = []
        self._default_timeout: int = default_timeout
        self._stats: dict[str, int] = {
            "commands_executed": 0,
            "commands_succeeded": 0,
            "commands_failed": 0,
            "commands_timeout": 0,
            "commands_cancelled": 0,
        }
        logger.info("ShellExecutor baslatildi (timeout=%ds)", default_timeout)

    @property
    def history_count(self) -> int:
        """Gecmis kayit sayisi."""
        return len(self._history)

    @property
    def running_count(self) -> int:
        """Calisiran komut sayisi."""
        return len(self._running)

    def execute(
        self,
        command: str = "",
        timeout: int | None = None,
        env_vars: dict[str, str] | None = None,
        capture_stderr: bool = True,
    ) -> dict[str, Any]:
        """Komutu calistirir ve ciktisini yakalar.

        Args:
            command: Calistirilacak komut.
            timeout: Zaman asimi (saniye). None ise varsayilan kullanilir.
            env_vars: Eklenecek ortam degiskenleri.
            capture_stderr: Hata ciktisi da yakalansin mi.

        Returns:
            Calistirma sonucu.
        """
        try:
            if not command:
                return {"executed": False, "error": "komut_gerekli"}

            effective_timeout = timeout if timeout is not None else self._default_timeout
            exec_env = dict(self._env)
            if env_vars:
                exec_env.update(env_vars)

            self._stats["commands_executed"] += 1
            start_time = time.time()

            try:
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=effective_timeout,
                    cwd=self._cwd,
                    env=exec_env,
                )
                elapsed = time.time() - start_time
                success = result.returncode == 0

                if success:
                    self._stats["commands_succeeded"] += 1
                else:
                    self._stats["commands_failed"] += 1

                record = {
                    "command": command,
                    "returncode": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr if capture_stderr else "",
                    "elapsed_seconds": round(elapsed, 3),
                    "timestamp": start_time,
                    "cwd": self._cwd,
                }
                self._add_history(record)

                return {
                    "executed": True,
                    "success": success,
                    "returncode": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr if capture_stderr else "",
                    "elapsed_seconds": round(elapsed, 3),
                    "command": command,
                }
            except subprocess.TimeoutExpired:
                self._stats["commands_timeout"] += 1
                elapsed = time.time() - start_time
                record = {
                    "command": command,
                    "returncode": -1,
                    "stdout": "",
                    "stderr": "timeout",
                    "elapsed_seconds": round(elapsed, 3),
                    "timestamp": start_time,
                    "cwd": self._cwd,
                }
                self._add_history(record)
                return {
                    "executed": False,
                    "error": "zaman_asimi",
                    "timeout_seconds": effective_timeout,
                    "command": command,
                }
        except Exception as e:
            logger.error("Komut calistirma hatasi: %s", e)
            return {"executed": False, "error": str(e)}

    def execute_simple(
        self,
        command: str = "",
        timeout: int | None = None,
    ) -> dict[str, Any]:
        """Basit komut calistirma (subprocess yerine simule).

        Args:
            command: Calistirilacak komut.
            timeout: Zaman asimi.

        Returns:
            Calistirma sonucu.
        """
        try:
            if not command:
                return {"executed": False, "error": "komut_gerekli"}

            exec_id = str(uuid.uuid4())[:8]
            self._stats["commands_executed"] += 1
            self._stats["commands_succeeded"] += 1

            record = {
                "id": exec_id,
                "command": command,
                "returncode": 0,
                "stdout": f"[simulated output for: {command}]",
                "stderr": "",
                "elapsed_seconds": 0.01,
                "timestamp": time.time(),
                "cwd": self._cwd,
            }
            self._add_history(record)

            return {
                "executed": True,
                "success": True,
                "execution_id": exec_id,
                "returncode": 0,
                "stdout": record["stdout"],
                "stderr": "",
                "command": command,
            }
        except Exception as e:
            logger.error("Basit komut hatasi: %s", e)
            return {"executed": False, "error": str(e)}

    def cancel(self, execution_id: str = "") -> dict[str, Any]:
        """Calisiran komutu iptal eder.

        Args:
            execution_id: Iptal edilecek islem ID.

        Returns:
            Iptal sonucu.
        """
        try:
            if not execution_id:
                return {"cancelled": False, "error": "id_gerekli"}

            if execution_id not in self._running:
                return {
                    "cancelled": False,
                    "reason": "islem_bulunamadi",
                    "execution_id": execution_id,
                }

            self._running.pop(execution_id)
            self._stats["commands_cancelled"] += 1

            return {"cancelled": True, "execution_id": execution_id}
        except Exception as e:
            logger.error("Iptal hatasi: %s", e)
            return {"cancelled": False, "error": str(e)}

    def set_working_directory(self, path: str = "") -> dict[str, Any]:
        """Calisma dizinini ayarlar.

        Args:
            path: Yeni calisma dizini.

        Returns:
            Ayarlama sonucu.
        """
        try:
            if not path:
                return {"set": False, "error": "yol_gerekli"}

            if not os.path.isdir(path):
                return {
                    "set": False,
                    "error": "dizin_bulunamadi",
                    "path": path,
                }

            old_cwd = self._cwd
            self._cwd = os.path.abspath(path)
            logger.info("Calisma dizini degistirildi: %s -> %s", old_cwd, self._cwd)

            return {
                "set": True,
                "old_cwd": old_cwd,
                "new_cwd": self._cwd,
            }
        except Exception as e:
            logger.error("Dizin ayarlama hatasi: %s", e)
            return {"set": False, "error": str(e)}

    def set_env_var(self, key: str = "", value: str = "") -> dict[str, Any]:
        """Ortam degiskeni ekler/gunceller.

        Args:
            key: Degisken adi.
            value: Degisken degeri.

        Returns:
            Ayarlama sonucu.
        """
        try:
            if not key:
                return {"set": False, "error": "anahtar_gerekli"}

            self._env[key] = value
            return {"set": True, "key": key, "value": value}
        except Exception as e:
            logger.error("Ortam degiskeni hatasi: %s", e)
            return {"set": False, "error": str(e)}

    def get_environment(self) -> dict[str, Any]:
        """Mevcut ortam degiskenlerini dondurur.

        Returns:
            Ortam bilgisi.
        """
        try:
            return {
                "retrieved": True,
                "cwd": self._cwd,
                "env_count": len(self._env),
                "env": dict(self._env),
            }
        except Exception as e:
            logger.error("Ortam alma hatasi: %s", e)
            return {"retrieved": False, "error": str(e)}

    def get_history(self, limit: int = 10) -> dict[str, Any]:
        """Komut gecmisini dondurur.

        Args:
            limit: En son kac kayit.

        Returns:
            Gecmis listesi.
        """
        try:
            recent = self._history[-limit:] if limit > 0 else self._history
            return {
                "retrieved": True,
                "history": recent,
                "total": len(self._history),
                "returned": len(recent),
            }
        except Exception as e:
            logger.error("Gecmis alma hatasi: %s", e)
            return {"retrieved": False, "error": str(e)}

    def get_summary(self) -> dict[str, Any]:
        """Ozet bilgi dondurur.

        Returns:
            Ozet.
        """
        try:
            return {
                "retrieved": True,
                "cwd": self._cwd,
                "running_count": self.running_count,
                "history_count": self.history_count,
                "default_timeout": self._default_timeout,
                "stats": dict(self._stats),
            }
        except Exception as e:
            logger.error("Ozet hatasi: %s", e)
            return {"retrieved": False, "error": str(e)}

    # -- Ozel yardimci metodlar ----------------------------------------

    def _add_history(self, record: dict) -> None:
        """Gecmise kayit ekler (MAX_HISTORY siniriyla)."""
        self._history.append(record)
        if len(self._history) > self.MAX_HISTORY:
            self._history = self._history[-self.MAX_HISTORY:]
