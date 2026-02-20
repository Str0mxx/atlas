"""
Process Manager modulu.

Islem listesi, baslat/durdur, kaynak kullanimi,
kill ve izleme.
"""

import logging
import os
import subprocess
import time
from typing import Any

logger = logging.getLogger(__name__)


class ProcessManager:
    """Islem yoneticisi.

    Attributes:
        _processes: Yonetilen islemler.
        _monitored: Izlenen islem PID'leri.
        _stats: Istatistikler.
    """

    def __init__(self) -> None:
        """Islem yoneticisini baslatir."""
        self._processes: dict[int, dict] = {}
        self._monitored: set[int] = set()
        self._stats: dict[str, int] = {
            "listed": 0,
            "started": 0,
            "stopped": 0,
            "killed": 0,
            "monitored": 0,
        }
        logger.info("ProcessManager baslatildi")

    @property
    def managed_count(self) -> int:
        """Yonetilen islem sayisi."""
        return len(self._processes)

    @property
    def monitored_count(self) -> int:
        """Izlenen islem sayisi."""
        return len(self._monitored)

    def list_processes(self) -> dict[str, Any]:
        """Calisiran islemleri listeler (platform bagimsiz).

        Returns:
            Islem listesi.
        """
        try:
            processes = []

            # Yalnizca yonetilen islemleri listele + mevcut prosesi ekle
            current_pid = os.getpid()
            processes.append({
                "pid": current_pid,
                "name": "atlas",
                "status": "running",
                "managed": False,
            })

            for pid, info in self._processes.items():
                processes.append({
                    "pid": pid,
                    "name": info.get("name", "unknown"),
                    "status": info.get("status", "unknown"),
                    "managed": True,
                    "started_at": info.get("started_at", 0),
                })

            self._stats["listed"] += 1
            return {
                "listed": True,
                "processes": processes,
                "count": len(processes),
                "current_pid": current_pid,
            }
        except Exception as e:
            logger.error("Islem listeleme hatasi: %s", e)
            return {"listed": False, "error": str(e)}

    def get_process(self, pid: int = 0) -> dict[str, Any]:
        """Belirli bir islemin bilgisini dondurur.

        Args:
            pid: Islem ID.

        Returns:
            Islem bilgisi.
        """
        try:
            if pid <= 0:
                return {"retrieved": False, "error": "gecersiz_pid"}

            if pid in self._processes:
                info = self._processes[pid]
                return {
                    "retrieved": True,
                    "pid": pid,
                    "name": info.get("name", "unknown"),
                    "status": info.get("status", "unknown"),
                    "managed": True,
                    "started_at": info.get("started_at", 0),
                }

            # Mevcut proses kontrolu
            if pid == os.getpid():
                return {
                    "retrieved": True,
                    "pid": pid,
                    "name": "atlas",
                    "status": "running",
                    "managed": False,
                }

            return {"retrieved": False, "error": "islem_bulunamadi", "pid": pid}
        except Exception as e:
            logger.error("Islem bilgisi hatasi: %s", e)
            return {"retrieved": False, "error": str(e)}

    def start_process(
        self,
        command: str = "",
        name: str = "",
        env: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Yeni bir islem baslatir.

        Args:
            command: Calistirilacak komut.
            name: Islem adi.
            env: Ortam degiskenleri.

        Returns:
            Baslama sonucu.
        """
        try:
            if not command:
                return {"started": False, "error": "komut_gerekli"}

            proc_name = name or command.split()[0]
            proc = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
            pid = proc.pid
            self._processes[pid] = {
                "name": proc_name,
                "command": command,
                "status": "running",
                "started_at": time.time(),
                "proc": proc,
            }
            self._stats["started"] += 1
            logger.info("Islem baslatildi: %s (PID=%d)", proc_name, pid)

            return {
                "started": True,
                "pid": pid,
                "name": proc_name,
                "command": command,
            }
        except Exception as e:
            logger.error("Islem baslama hatasi: %s", e)
            return {"started": False, "error": str(e)}

    def stop_process(self, pid: int = 0) -> dict[str, Any]:
        """Islemi duraklatir (SIGTERM).

        Args:
            pid: Durdurulacak islem ID.

        Returns:
            Durdurma sonucu.
        """
        try:
            if pid <= 0:
                return {"stopped": False, "error": "gecersiz_pid"}

            if pid not in self._processes:
                return {"stopped": False, "error": "islem_bulunamadi", "pid": pid}

            info = self._processes[pid]
            proc = info.get("proc")
            if proc:
                proc.terminate()
                info["status"] = "stopping"

            self._stats["stopped"] += 1
            logger.info("Islem durduruldu: PID=%d", pid)
            return {"stopped": True, "pid": pid, "name": info.get("name", "")}
        except Exception as e:
            logger.error("Islem durdurma hatasi: %s", e)
            return {"stopped": False, "error": str(e)}

    def kill_process(self, pid: int = 0) -> dict[str, Any]:
        """Islemi zorla sonlandirir (SIGKILL).

        Args:
            pid: Sonlandirilacak islem ID.

        Returns:
            Sonlandirma sonucu.
        """
        try:
            if pid <= 0:
                return {"killed": False, "error": "gecersiz_pid"}

            if pid not in self._processes:
                return {"killed": False, "error": "islem_bulunamadi", "pid": pid}

            info = self._processes[pid]
            proc = info.get("proc")
            if proc:
                proc.kill()
                info["status"] = "killed"

            self._processes.pop(pid)
            self._monitored.discard(pid)
            self._stats["killed"] += 1
            logger.warning("Islem zorla sonlandirildi: PID=%d", pid)

            return {"killed": True, "pid": pid, "name": info.get("name", "")}
        except Exception as e:
            logger.error("Islem sonlandirma hatasi: %s", e)
            return {"killed": False, "error": str(e)}

    def get_resource_usage(self, pid: int = 0) -> dict[str, Any]:
        """Islem kaynak kullanimi dondurur.

        Args:
            pid: Islem ID.

        Returns:
            Kaynak kullanim bilgisi.
        """
        try:
            if pid <= 0:
                return {"retrieved": False, "error": "gecersiz_pid"}

            # Simule edilmis kaynak bilgisi (psutil olmadan)
            known = pid in self._processes or pid == os.getpid()
            if not known:
                return {"retrieved": False, "error": "islem_bulunamadi", "pid": pid}

            return {
                "retrieved": True,
                "pid": pid,
                "cpu_percent": 0.0,
                "memory_mb": 0.0,
                "threads": 1,
                "status": self._processes.get(pid, {}).get("status", "running"),
                "note": "psutil_olmadan_simule",
            }
        except Exception as e:
            logger.error("Kaynak kullanim hatasi: %s", e)
            return {"retrieved": False, "error": str(e)}

    def monitor(self, pid: int = 0) -> dict[str, Any]:
        """Islemi izlemeye ekler.

        Args:
            pid: Izlenecek islem ID.

        Returns:
            Izleme baslama sonucu.
        """
        try:
            if pid <= 0:
                return {"monitoring": False, "error": "gecersiz_pid"}

            self._monitored.add(pid)
            self._stats["monitored"] += 1
            logger.info("Islem izlemeye alindi: PID=%d", pid)

            return {
                "monitoring": True,
                "pid": pid,
                "total_monitored": self.monitored_count,
            }
        except Exception as e:
            logger.error("Izleme baslama hatasi: %s", e)
            return {"monitoring": False, "error": str(e)}

    def unmonitor(self, pid: int = 0) -> dict[str, Any]:
        """Islemi izlemeden cikarir.

        Args:
            pid: Izlemeden cikarilacak islem ID.

        Returns:
            Cikarma sonucu.
        """
        try:
            if pid <= 0:
                return {"unmonitored": False, "error": "gecersiz_pid"}

            if pid not in self._monitored:
                return {"unmonitored": False, "error": "izlenmiyor", "pid": pid}

            self._monitored.discard(pid)
            return {"unmonitored": True, "pid": pid}
        except Exception as e:
            logger.error("Izleme cikari hatasi: %s", e)
            return {"unmonitored": False, "error": str(e)}

    def get_summary(self) -> dict[str, Any]:
        """Ozet bilgi dondurur.

        Returns:
            Ozet.
        """
        try:
            return {
                "retrieved": True,
                "managed_count": self.managed_count,
                "monitored_count": self.monitored_count,
                "current_pid": os.getpid(),
                "stats": dict(self._stats),
            }
        except Exception as e:
            logger.error("Ozet hatasi: %s", e)
            return {"retrieved": False, "error": str(e)}
