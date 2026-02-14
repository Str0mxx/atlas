"""ATLAS Dagitik Kilit modulu.

Kilit edinme, serbest birakma,
zaman asimi, deadlock tespiti
ve reentrant kilitler.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class DistributedLock:
    """Dagitik kilit yoneticisi.

    Dagitik kaynak kilitleme saglar.

    Attributes:
        _locks: Aktif kilitler.
        _waiters: Bekleyenler.
    """

    def __init__(
        self,
        default_ttl: int = 30,
    ) -> None:
        """Dagitik kilidi baslatir.

        Args:
            default_ttl: Varsayilan yasam suresi (sn).
        """
        self._locks: dict[
            str, dict[str, Any]
        ] = {}
        self._waiters: dict[
            str, list[str]
        ] = {}
        self._history: list[
            dict[str, Any]
        ] = []
        self._default_ttl = default_ttl

        logger.info(
            "DistributedLock baslatildi",
        )

    def acquire(
        self,
        resource: str,
        owner: str,
        ttl: int | None = None,
        reentrant: bool = False,
    ) -> dict[str, Any]:
        """Kilit edinir.

        Args:
            resource: Kaynak adi.
            owner: Kilit sahibi.
            ttl: Yasam suresi (sn).
            reentrant: Yeniden girisli mi.

        Returns:
            Edinme sonucu.
        """
        ttl = ttl or self._default_ttl

        # Suresi dolmuslari temizle
        self._cleanup_expired()

        existing = self._locks.get(resource)

        if existing:
            # Reentrant kontrol
            if (
                reentrant
                and existing["owner"] == owner
            ):
                existing["reentry_count"] += 1
                return {
                    "resource": resource,
                    "acquired": True,
                    "reentrant": True,
                    "reentry_count": existing[
                        "reentry_count"
                    ],
                }

            # Baskasi tutuyor
            if resource not in self._waiters:
                self._waiters[resource] = []
            if owner not in self._waiters[resource]:
                self._waiters[resource].append(
                    owner,
                )
            return {
                "resource": resource,
                "acquired": False,
                "held_by": existing["owner"],
                "position": self._waiters[
                    resource
                ].index(owner) + 1,
            }

        # Kilitle
        lock = {
            "resource": resource,
            "owner": owner,
            "ttl": ttl,
            "acquired_at": time.time(),
            "reentry_count": 1,
        }
        self._locks[resource] = lock
        self._history.append({
            "action": "acquire",
            "resource": resource,
            "owner": owner,
            "timestamp": time.time(),
        })
        return {
            "resource": resource,
            "acquired": True,
            "reentrant": False,
            "ttl": ttl,
        }

    def release(
        self,
        resource: str,
        owner: str,
    ) -> dict[str, Any]:
        """Kilidi serbest birakir.

        Args:
            resource: Kaynak adi.
            owner: Kilit sahibi.

        Returns:
            Serbest birakma sonucu.
        """
        lock = self._locks.get(resource)
        if not lock:
            return {
                "resource": resource,
                "released": False,
                "reason": "not_locked",
            }

        if lock["owner"] != owner:
            return {
                "resource": resource,
                "released": False,
                "reason": "not_owner",
            }

        # Reentrant: sayaci azalt
        lock["reentry_count"] -= 1
        if lock["reentry_count"] > 0:
            return {
                "resource": resource,
                "released": False,
                "reentry_count": lock[
                    "reentry_count"
                ],
                "reason": "reentrant_pending",
            }

        del self._locks[resource]
        self._history.append({
            "action": "release",
            "resource": resource,
            "owner": owner,
            "timestamp": time.time(),
        })

        # Bekleyeni terfii et
        next_owner = self._promote_waiter(
            resource,
        )

        return {
            "resource": resource,
            "released": True,
            "next_owner": next_owner,
        }

    def _promote_waiter(
        self,
        resource: str,
    ) -> str | None:
        """Bekleyeni terfii ettirir.

        Args:
            resource: Kaynak adi.

        Returns:
            Terfii eden sahip veya None.
        """
        waiters = self._waiters.get(
            resource, [],
        )
        if not waiters:
            return None

        next_owner = waiters.pop(0)
        if not waiters:
            del self._waiters[resource]

        # Otomatik kilit ver
        self._locks[resource] = {
            "resource": resource,
            "owner": next_owner,
            "ttl": self._default_ttl,
            "acquired_at": time.time(),
            "reentry_count": 1,
        }
        return next_owner

    def _cleanup_expired(self) -> int:
        """Suresi dolmuslari temizler.

        Returns:
            Temizlenen sayi.
        """
        now = time.time()
        expired = []
        for resource, lock in self._locks.items():
            elapsed = now - lock["acquired_at"]
            if elapsed > lock["ttl"]:
                expired.append(resource)

        for resource in expired:
            del self._locks[resource]
            self._promote_waiter(resource)

        return len(expired)

    def detect_deadlock(
        self,
    ) -> dict[str, Any]:
        """Deadlock tespit eder.

        Returns:
            Tespit sonucu.
        """
        # Wait-for graf olustur
        wait_for: dict[str, str] = {}
        for resource, waiters in self._waiters.items():
            lock = self._locks.get(resource)
            if lock:
                holder = lock["owner"]
                for waiter in waiters:
                    wait_for[waiter] = holder

        # Dongu ara
        cycles = []
        for start in wait_for:
            visited = set()
            current = start
            path = []
            while current in wait_for:
                if current in visited:
                    cycle_start = path.index(
                        current,
                    )
                    cycles.append(
                        path[cycle_start:],
                    )
                    break
                visited.add(current)
                path.append(current)
                current = wait_for[current]

        return {
            "deadlock_detected": len(cycles) > 0,
            "cycles": cycles,
            "waiting_count": len(wait_for),
        }

    def force_release(
        self,
        resource: str,
    ) -> bool:
        """Zorla serbest birakir.

        Args:
            resource: Kaynak adi.

        Returns:
            Basarili mi.
        """
        if resource in self._locks:
            del self._locks[resource]
            self._promote_waiter(resource)
            self._history.append({
                "action": "force_release",
                "resource": resource,
                "timestamp": time.time(),
            })
            return True
        return False

    def get_lock_info(
        self,
        resource: str,
    ) -> dict[str, Any] | None:
        """Kilit bilgisi getirir.

        Args:
            resource: Kaynak adi.

        Returns:
            Kilit bilgisi veya None.
        """
        lock = self._locks.get(resource)
        if not lock:
            return None
        return {
            "resource": lock["resource"],
            "owner": lock["owner"],
            "ttl": lock["ttl"],
            "reentry_count": lock[
                "reentry_count"
            ],
            "held_for": round(
                time.time() - lock["acquired_at"],
                2,
            ),
        }

    @property
    def lock_count(self) -> int:
        """Aktif kilit sayisi."""
        return len(self._locks)

    @property
    def waiter_count(self) -> int:
        """Bekleyen sayisi."""
        return sum(
            len(w) for w in
            self._waiters.values()
        )

    @property
    def history_count(self) -> int:
        """Gecmis kayit sayisi."""
        return len(self._history)
