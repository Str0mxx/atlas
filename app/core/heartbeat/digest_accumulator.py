"""Digest Accumulator - ozet derleme modulu.

Heartbeat sonuclarini biriktirir ve belirli araliklarla
ozet olarak derlemeye hazirlar.
"""

import logging
import time
import uuid
from typing import Optional

from app.models.heartbeat_models import (
    DigestEntry,
    HeartbeatConfig,
    HeartbeatResult,
    ImportanceLevel,
)

logger = logging.getLogger(__name__)


class DigestAccumulator:
    """Heartbeat sonuclarini biriktirip ozet derleyen sinif."""

    def __init__(self, config: Optional[HeartbeatConfig] = None) -> None:
        """DigestAccumulator baslatici."""
        self.config = config or HeartbeatConfig()
        self._entries: list[DigestEntry] = []
        self._last_compile_time: float = time.time()
        self._history: list[dict] = []

    def _record_history(self, action: str, details: Optional[dict] = None) -> None:
        """Gecmis kaydina yeni bir giris ekler."""
        self._history.append({"action": action, "timestamp": time.time(), "details": details or {}})

    def get_history(self) -> list[dict]:
        """Tum gecmis kayitlarini dondurur."""
        return list(self._history)

    def get_stats(self) -> dict:
        """Biriktirici istatistiklerini dondurur."""
        return {"pending_entries": len(self._entries), "max_digest_size": self.config.max_digest_size, "digest_interval": self.config.digest_interval_minutes, "last_compile": self._last_compile_time}

    def add(self, heartbeat_result: HeartbeatResult) -> bool:
        """Heartbeat sonucunu biriktirme listesine ekler."""
        if len(self._entries) >= self.config.max_digest_size:
            self._entries.pop(0)
        entry = DigestEntry(
            entry_id=str(uuid.uuid4()),
            heartbeat_id=heartbeat_result.heartbeat_id,
            importance=heartbeat_result.importance,
            summary=heartbeat_result.message[:200],
            timestamp=heartbeat_result.timestamp or time.time(),
        )
        self._entries.append(entry)
        self._record_history("add", {"heartbeat_id": heartbeat_result.heartbeat_id})
        return True

    def compile_digest(self) -> list[DigestEntry]:
        """Biriktirilmis girisleri derleyerek ozet olusturur."""
        importance_order = ["none", "low", "medium", "high", "critical"]
        compiled = sorted(self._entries, key=lambda e: importance_order.index(e.importance.value), reverse=True)
        self._last_compile_time = time.time()
        self._record_history("compile_digest", {"count": len(compiled)})
        return compiled

    def should_send(self) -> bool:
        """Ozet gonderme zamaninin gelip gelmedigini kontrol eder."""
        if not self._entries:
            return False
        elapsed = time.time() - self._last_compile_time
        return elapsed >= self.config.digest_interval_minutes * 60

    def clear(self) -> None:
        """Biriktirilmis girisleri temizler."""
        count = len(self._entries)
        self._entries.clear()
        self._record_history("clear", {"cleared_count": count})

    def get_pending(self) -> list[DigestEntry]:
        """Bekleyen girisleri dondurur."""
        return list(self._entries)

    def set_interval(self, minutes: int) -> None:
        """Ozet gonderme araligini ayarlar."""
        self.config.digest_interval_minutes = max(1, minutes)
        self._record_history("set_interval", {"minutes": minutes})

    def get_summary(self) -> dict:
        """Hizli ozet bilgisi dondurur."""
        importance_counts: dict[str, int] = {}
        for entry in self._entries:
            key = entry.importance.value
            importance_counts[key] = importance_counts.get(key, 0) + 1
        return {
            "total_pending": len(self._entries),
            "by_importance": importance_counts,
            "oldest": self._entries[0].timestamp if self._entries else None,
            "newest": self._entries[-1].timestamp if self._entries else None,
        }
