"""ATLAS Log Toplayici modulu.

Coklu kaynak toplama, log birlestirme,
tekilsizlestirme, tamponlama
ve toplu iletme.
"""

import hashlib
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class LogAggregator:
    """Log toplayici.

    Birden fazla kaynaktan log toplar
    ve birlestirir.

    Attributes:
        _sources: Kaynak tanimlari.
        _buffer: Log tamponu.
    """

    def __init__(
        self,
        buffer_size: int = 1000,
        dedup_window: int = 60,
    ) -> None:
        """Log toplayiciyi baslatir.

        Args:
            buffer_size: Tampon boyutu.
            dedup_window: Tekilsizlestirme penceresi (sn).
        """
        self._buffer_size = buffer_size
        self._dedup_window = dedup_window
        self._sources: dict[
            str, dict[str, Any]
        ] = {}
        self._buffer: list[dict[str, Any]] = []
        self._seen_hashes: dict[
            str, float
        ] = {}
        self._forwarded: list[
            dict[str, Any]
        ] = []
        self._total_collected = 0
        self._duplicates_skipped = 0

        logger.info(
            "LogAggregator baslatildi",
        )

    def register_source(
        self,
        name: str,
        source_type: str = "application",
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Kaynak kaydeder.

        Args:
            name: Kaynak adi.
            source_type: Kaynak tipi.
            config: Yapilandirma.

        Returns:
            Kaynak bilgisi.
        """
        source = {
            "name": name,
            "type": source_type,
            "config": config or {},
            "log_count": 0,
        }
        self._sources[name] = source
        return source

    def collect(
        self,
        source: str,
        record: dict[str, Any],
    ) -> bool:
        """Log toplar.

        Args:
            source: Kaynak adi.
            record: Log kaydi.

        Returns:
            Toplandi ise True.
        """
        # Tekilsizlestirme
        hash_key = self._compute_hash(record)
        now = time.time()

        if hash_key in self._seen_hashes:
            last_seen = self._seen_hashes[hash_key]
            if now - last_seen < self._dedup_window:
                self._duplicates_skipped += 1
                return False

        self._seen_hashes[hash_key] = now
        self._total_collected += 1

        enriched = dict(record)
        enriched["_source"] = source
        enriched["_collected_at"] = now

        self._buffer.append(enriched)

        # Kaynak sayacini guncelle
        if source in self._sources:
            self._sources[source][
                "log_count"
            ] += 1

        # Tampon dolu ise ilet
        if len(self._buffer) >= self._buffer_size:
            self.flush()

        return True

    def _compute_hash(
        self, record: dict[str, Any],
    ) -> str:
        """Log hash hesaplar.

        Args:
            record: Log kaydi.

        Returns:
            Hash degeri.
        """
        msg = record.get("message", "")
        level = record.get("level", "")
        source = record.get("source", "")
        key = f"{level}:{source}:{msg}"
        return hashlib.md5(
            key.encode()
        ).hexdigest()

    def flush(self) -> list[dict[str, Any]]:
        """Tamponu bosaltir.

        Returns:
            Iletilen loglar.
        """
        batch = list(self._buffer)
        self._forwarded.extend(batch)
        self._buffer = []
        return batch

    def merge_logs(
        self,
        *log_lists: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Loglari birlestirir.

        Args:
            log_lists: Log listeleri.

        Returns:
            Birlesmis liste.
        """
        merged = []
        for logs in log_lists:
            merged.extend(logs)
        merged.sort(
            key=lambda x: x.get("timestamp", 0),
        )
        return merged

    def get_buffer(self) -> list[dict[str, Any]]:
        """Tampon icerigini getirir.

        Returns:
            Tampon listesi.
        """
        return list(self._buffer)

    def get_source_stats(
        self,
    ) -> dict[str, Any]:
        """Kaynak istatistikleri.

        Returns:
            Kaynak bilgileri.
        """
        return {
            name: {
                "type": s["type"],
                "log_count": s["log_count"],
            }
            for name, s in self._sources.items()
        }

    def cleanup_hashes(
        self, max_age: int = 300,
    ) -> int:
        """Eski hashleri temizler.

        Args:
            max_age: Maks yas (sn).

        Returns:
            Temizlenen sayi.
        """
        now = time.time()
        old_keys = [
            k for k, t in self._seen_hashes.items()
            if now - t > max_age
        ]
        for k in old_keys:
            del self._seen_hashes[k]
        return len(old_keys)

    @property
    def source_count(self) -> int:
        """Kaynak sayisi."""
        return len(self._sources)

    @property
    def buffer_count(self) -> int:
        """Tampon sayisi."""
        return len(self._buffer)

    @property
    def total_collected(self) -> int:
        """Toplam toplanan."""
        return self._total_collected

    @property
    def duplicates_skipped(self) -> int:
        """Atlanan tekrar sayisi."""
        return self._duplicates_skipped

    @property
    def forwarded_count(self) -> int:
        """Iletilen sayisi."""
        return len(self._forwarded)
