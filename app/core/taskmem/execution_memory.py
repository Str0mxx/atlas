"""ATLAS Yürütme Hafızası modülü.

Yürütme geçmişi, başarı/başarısızlık takibi,
süre kalıpları, kaynak kullanımı,
optimizasyon ipuçları.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ExecutionMemory:
    """Yürütme hafızası.

    Görev yürütme geçmişini saklar ve analiz eder.

    Attributes:
        _executions: Yürütme kayıtları.
    """

    def __init__(self) -> None:
        """Hafızayı başlatır."""
        self._executions: list[
            dict[str, Any]
        ] = {}
        self._executions: list[
            dict[str, Any]
        ] = []
        self._hints: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "total_executions": 0,
            "successes": 0,
            "failures": 0,
            "hints_generated": 0,
        }

        logger.info(
            "ExecutionMemory baslatildi",
        )

    def record_execution(
        self,
        task_id: str,
        command: str,
        success: bool,
        duration_ms: float = 0.0,
        resource_usage: (
            dict[str, Any] | None
        ) = None,
        error: str = "",
    ) -> dict[str, Any]:
        """Yürütme kaydeder.

        Args:
            task_id: Görev ID.
            command: Komut.
            success: Başarılı mı.
            duration_ms: Süre (ms).
            resource_usage: Kaynak kullanımı.
            error: Hata mesajı.

        Returns:
            Kayıt bilgisi.
        """
        self._counter += 1
        eid = f"exec_{self._counter}"

        execution = {
            "execution_id": eid,
            "task_id": task_id,
            "command": command,
            "success": success,
            "duration_ms": duration_ms,
            "resource_usage": (
                resource_usage or {}
            ),
            "error": error,
            "timestamp": time.time(),
        }
        self._executions.append(execution)
        self._stats["total_executions"] += 1

        if success:
            self._stats["successes"] += 1
        else:
            self._stats["failures"] += 1

        return {
            "execution_id": eid,
            "task_id": task_id,
            "success": success,
            "duration_ms": duration_ms,
            "recorded": True,
        }

    def get_success_rate(
        self,
        command: str | None = None,
    ) -> dict[str, Any]:
        """Başarı oranını döndürür.

        Args:
            command: Komut filtresi.

        Returns:
            Oran bilgisi.
        """
        execs = self._executions
        if command:
            execs = [
                e for e in execs
                if e["command"] == command
            ]

        if not execs:
            return {
                "rate": 0.0,
                "total": 0,
                "successes": 0,
                "failures": 0,
            }

        successes = sum(
            1 for e in execs if e["success"]
        )
        failures = len(execs) - successes
        rate = successes / len(execs)

        return {
            "rate": round(rate, 3),
            "total": len(execs),
            "successes": successes,
            "failures": failures,
        }

    def get_duration_patterns(
        self,
        command: str | None = None,
    ) -> dict[str, Any]:
        """Süre kalıplarını döndürür.

        Args:
            command: Komut filtresi.

        Returns:
            Kalıp bilgisi.
        """
        execs = self._executions
        if command:
            execs = [
                e for e in execs
                if e["command"] == command
            ]

        durations = [
            e["duration_ms"]
            for e in execs
            if e["duration_ms"] > 0
        ]

        if not durations:
            return {
                "avg_ms": 0.0,
                "min_ms": 0.0,
                "max_ms": 0.0,
                "count": 0,
            }

        return {
            "avg_ms": round(
                sum(durations)
                / len(durations), 1,
            ),
            "min_ms": min(durations),
            "max_ms": max(durations),
            "count": len(durations),
        }

    def get_resource_usage(
        self,
        command: str | None = None,
    ) -> dict[str, Any]:
        """Kaynak kullanımını döndürür.

        Args:
            command: Komut filtresi.

        Returns:
            Kullanım bilgisi.
        """
        execs = self._executions
        if command:
            execs = [
                e for e in execs
                if e["command"] == command
            ]

        usages = [
            e["resource_usage"]
            for e in execs
            if e["resource_usage"]
        ]

        if not usages:
            return {
                "avg_resources": {},
                "count": 0,
            }

        # Tüm kaynak türlerini topla
        totals: dict[str, float] = {}
        for usage in usages:
            for key, val in usage.items():
                if isinstance(
                    val, (int, float),
                ):
                    totals[key] = (
                        totals.get(key, 0)
                        + val
                    )

        avg = {
            k: round(v / len(usages), 2)
            for k, v in totals.items()
        }

        return {
            "avg_resources": avg,
            "count": len(usages),
        }

    def generate_hints(
        self,
    ) -> dict[str, Any]:
        """Optimizasyon ipuçları üretir.

        Returns:
            İpucu bilgisi.
        """
        hints = []

        # Yavaş komutları bul
        cmd_durations: dict[
            str, list[float]
        ] = {}
        for e in self._executions:
            cmd = e["command"]
            if cmd not in cmd_durations:
                cmd_durations[cmd] = []
            if e["duration_ms"] > 0:
                cmd_durations[cmd].append(
                    e["duration_ms"],
                )

        for cmd, durations in (
            cmd_durations.items()
        ):
            if not durations:
                continue
            avg = sum(durations) / len(
                durations,
            )
            if avg > 5000:
                hints.append({
                    "type": "slow_command",
                    "command": cmd,
                    "avg_ms": round(avg, 1),
                    "hint": (
                        f"'{cmd}' is slow "
                        f"({avg:.0f}ms avg). "
                        f"Consider caching."
                    ),
                })

        # Sık başarısız komutlar
        cmd_failures: dict[
            str, int
        ] = {}
        cmd_totals: dict[str, int] = {}
        for e in self._executions:
            cmd = e["command"]
            cmd_totals[cmd] = (
                cmd_totals.get(cmd, 0) + 1
            )
            if not e["success"]:
                cmd_failures[cmd] = (
                    cmd_failures.get(cmd, 0)
                    + 1
                )

        for cmd, fails in (
            cmd_failures.items()
        ):
            total = cmd_totals.get(cmd, 1)
            rate = fails / total
            if rate > 0.3 and total >= 3:
                hints.append({
                    "type": "high_failure",
                    "command": cmd,
                    "failure_rate": round(
                        rate, 2,
                    ),
                    "hint": (
                        f"'{cmd}' has "
                        f"{rate:.0%} failure "
                        f"rate. Review logic."
                    ),
                })

        self._hints = hints
        self._stats[
            "hints_generated"
        ] = len(hints)

        return {
            "hints": hints,
            "count": len(hints),
        }

    def get_history(
        self,
        task_id: str | None = None,
        command: str | None = None,
        success: bool | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Yürütme geçmişini getirir."""
        results = self._executions
        if task_id:
            results = [
                e for e in results
                if e["task_id"] == task_id
            ]
        if command:
            results = [
                e for e in results
                if e["command"] == command
            ]
        if success is not None:
            results = [
                e for e in results
                if e["success"] == success
            ]
        return list(results[-limit:])

    @property
    def execution_count(self) -> int:
        """Yürütme sayısı."""
        return self._stats[
            "total_executions"
        ]

    @property
    def success_rate(self) -> float:
        """Başarı oranı."""
        total = self._stats[
            "total_executions"
        ]
        if total == 0:
            return 0.0
        return round(
            self._stats["successes"]
            / total,
            3,
        )
