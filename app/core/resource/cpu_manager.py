"""ATLAS CPU Yoneticisi modulu.

CPU izleme, islem onceligi, cekirdek
tahsisi, kisitlama ve yuk dengeleme.
"""

import logging
from typing import Any

from app.models.resource import ResourceStatus

logger = logging.getLogger(__name__)


class CPUManager:
    """CPU yoneticisi.

    CPU kaynaklarini izler ve yonetir.

    Attributes:
        _processes: Islem kayitlari.
        _cores: Cekirdek tahsisleri.
        _usage_history: Kullanim gecmisi.
        _threshold: Uyari esigi.
    """

    def __init__(
        self,
        threshold: float = 0.8,
        total_cores: int = 4,
    ) -> None:
        """CPU yoneticisini baslatir.

        Args:
            threshold: Uyari esigi (0.0-1.0).
            total_cores: Toplam cekirdek.
        """
        self._processes: dict[str, dict[str, Any]] = {}
        self._cores: dict[int, str] = {}
        self._usage_history: list[float] = []
        self._threshold = max(0.1, min(1.0, threshold))
        self._total_cores = max(1, total_cores)
        self._throttled: set[str] = set()
        self._current_usage = 0.0

        logger.info(
            "CPUManager baslatildi (cores=%d, threshold=%.0f%%)",
            self._total_cores, self._threshold * 100,
        )

    def record_usage(self, usage: float) -> ResourceStatus:
        """CPU kullanimini kaydeder.

        Args:
            usage: Kullanim orani (0.0-1.0).

        Returns:
            Kaynak durumu.
        """
        usage = max(0.0, min(1.0, usage))
        self._current_usage = usage
        self._usage_history.append(usage)

        if usage >= 0.95:
            return ResourceStatus.CRITICAL
        if usage >= self._threshold:
            return ResourceStatus.WARNING
        return ResourceStatus.NORMAL

    def register_process(
        self,
        name: str,
        priority: int = 5,
        cpu_share: float = 0.0,
    ) -> dict[str, Any]:
        """Islem kaydeder.

        Args:
            name: Islem adi.
            priority: Oncelik (1-10, 10=en yuksek).
            cpu_share: CPU payi (0.0-1.0).

        Returns:
            Islem bilgisi.
        """
        proc = {
            "name": name,
            "priority": max(1, min(10, priority)),
            "cpu_share": max(0.0, min(1.0, cpu_share)),
            "core": None,
            "throttled": False,
        }
        self._processes[name] = proc
        return proc

    def set_priority(
        self,
        name: str,
        priority: int,
    ) -> bool:
        """Islem onceligini ayarlar.

        Args:
            name: Islem adi.
            priority: Yeni oncelik.

        Returns:
            Basarili ise True.
        """
        proc = self._processes.get(name)
        if not proc:
            return False
        proc["priority"] = max(1, min(10, priority))
        return True

    def allocate_core(
        self,
        process_name: str,
        core_id: int,
    ) -> bool:
        """Cekirdek tahsis eder.

        Args:
            process_name: Islem adi.
            core_id: Cekirdek ID.

        Returns:
            Basarili ise True.
        """
        if process_name not in self._processes:
            return False
        if core_id < 0 or core_id >= self._total_cores:
            return False
        if core_id in self._cores:
            return False

        self._cores[core_id] = process_name
        self._processes[process_name]["core"] = core_id
        return True

    def release_core(self, core_id: int) -> bool:
        """Cekirdek serbest birakir.

        Args:
            core_id: Cekirdek ID.

        Returns:
            Basarili ise True.
        """
        if core_id not in self._cores:
            return False
        proc_name = self._cores.pop(core_id)
        if proc_name in self._processes:
            self._processes[proc_name]["core"] = None
        return True

    def throttle(self, process_name: str) -> bool:
        """Islemi kisitlar.

        Args:
            process_name: Islem adi.

        Returns:
            Basarili ise True.
        """
        if process_name not in self._processes:
            return False
        self._throttled.add(process_name)
        self._processes[process_name]["throttled"] = True
        return True

    def unthrottle(self, process_name: str) -> bool:
        """Kisitlamayi kaldirir.

        Args:
            process_name: Islem adi.

        Returns:
            Basarili ise True.
        """
        if process_name not in self._processes:
            return False
        self._throttled.discard(process_name)
        self._processes[process_name]["throttled"] = False
        return True

    def get_load_balance_suggestion(self) -> list[dict[str, Any]]:
        """Yuk dengeleme onerisi verir.

        Returns:
            Oneriler.
        """
        suggestions: list[dict[str, Any]] = []
        unallocated = [
            n for n, p in self._processes.items()
            if p["core"] is None
        ]
        free_cores = [
            c for c in range(self._total_cores)
            if c not in self._cores
        ]

        for proc, core in zip(
            sorted(unallocated, key=lambda n: self._processes[n]["priority"], reverse=True),
            free_cores,
        ):
            suggestions.append({
                "process": proc,
                "suggested_core": core,
                "priority": self._processes[proc]["priority"],
            })

        return suggestions

    def get_avg_usage(self, window: int = 10) -> float:
        """Ortalama kullanimi hesaplar.

        Args:
            window: Pencere boyutu.

        Returns:
            Ortalama kullanim.
        """
        recent = self._usage_history[-window:]
        if not recent:
            return 0.0
        return sum(recent) / len(recent)

    @property
    def current_usage(self) -> float:
        """Mevcut kullanim."""
        return self._current_usage

    @property
    def process_count(self) -> int:
        """Islem sayisi."""
        return len(self._processes)

    @property
    def allocated_cores(self) -> int:
        """Tahsis edilen cekirdek sayisi."""
        return len(self._cores)

    @property
    def throttled_count(self) -> int:
        """Kisitlanan islem sayisi."""
        return len(self._throttled)

    @property
    def total_cores(self) -> int:
        """Toplam cekirdek sayisi."""
        return self._total_cores
