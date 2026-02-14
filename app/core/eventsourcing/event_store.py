"""ATLAS Olay Deposu modulu.

Olay kaliciligi, akis yonetimi,
olay getirme, snapshot depolama
ve eszamanlilik kontrolu.
"""

import logging
import time
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class EventStore:
    """Olay deposu.

    Olaylari depolar ve yonetir.

    Attributes:
        _streams: Olay akislari.
        _snapshots: Snapshot deposu.
    """

    def __init__(
        self,
        max_stream_size: int = 10000,
    ) -> None:
        """Olay deposunu baslatir.

        Args:
            max_stream_size: Maks akis boyutu.
        """
        self._streams: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._snapshots: dict[
            str, dict[str, Any]
        ] = {}
        self._max_stream_size = max_stream_size
        self._global_position: int = 0

        logger.info("EventStore baslatildi")

    def append(
        self,
        stream_id: str,
        event_type: str,
        data: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        expected_version: int | None = None,
    ) -> dict[str, Any]:
        """Olak akisa ekler.

        Args:
            stream_id: Akis ID.
            event_type: Olay tipi.
            data: Olay verisi.
            metadata: Ust veri.
            expected_version: Beklenen surum.

        Returns:
            Olay kaydi.

        Raises:
            ValueError: Surum catismasi.
        """
        if stream_id not in self._streams:
            self._streams[stream_id] = []

        stream = self._streams[stream_id]
        current_version = len(stream)

        # Eszamanlilik kontrolu
        if (
            expected_version is not None
            and expected_version != current_version
        ):
            raise ValueError(
                f"Version conflict: expected "
                f"{expected_version}, "
                f"got {current_version}"
            )

        self._global_position += 1

        event = {
            "event_id": str(uuid4())[:8],
            "stream_id": stream_id,
            "event_type": event_type,
            "data": data or {},
            "metadata": metadata or {},
            "version": current_version + 1,
            "position": self._global_position,
            "timestamp": time.time(),
        }
        stream.append(event)

        # Boyut kontrolu
        if len(stream) > self._max_stream_size:
            half = len(stream) // 2
            self._streams[stream_id] = stream[half:]

        return event

    def read_stream(
        self,
        stream_id: str,
        from_version: int = 0,
        to_version: int | None = None,
    ) -> list[dict[str, Any]]:
        """Akisi okur.

        Args:
            stream_id: Akis ID.
            from_version: Baslangic surumu.
            to_version: Bitis surumu.

        Returns:
            Olay listesi.
        """
        stream = self._streams.get(
            stream_id, [],
        )
        result = [
            e for e in stream
            if e["version"] >= from_version
        ]
        if to_version is not None:
            result = [
                e for e in result
                if e["version"] <= to_version
            ]
        return result

    def read_all(
        self,
        from_position: int = 0,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Tum olaylari okur.

        Args:
            from_position: Baslangic pozisyonu.
            limit: Limit.

        Returns:
            Olay listesi.
        """
        all_events = []
        for events in self._streams.values():
            all_events.extend(events)

        all_events.sort(
            key=lambda e: e["position"],
        )

        filtered = [
            e for e in all_events
            if e["position"] >= from_position
        ]
        return filtered[:limit]

    def get_stream_version(
        self,
        stream_id: str,
    ) -> int:
        """Akis surumunu getirir.

        Args:
            stream_id: Akis ID.

        Returns:
            Surum numarasi.
        """
        stream = self._streams.get(
            stream_id, [],
        )
        if not stream:
            return 0
        return stream[-1]["version"]

    def save_snapshot(
        self,
        stream_id: str,
        state: dict[str, Any],
        version: int,
    ) -> dict[str, Any]:
        """Snapshot kaydeder.

        Args:
            stream_id: Akis ID.
            state: Durum.
            version: Surum.

        Returns:
            Snapshot bilgisi.
        """
        snapshot = {
            "stream_id": stream_id,
            "state": state,
            "version": version,
            "timestamp": time.time(),
        }
        self._snapshots[stream_id] = snapshot
        return snapshot

    def get_snapshot(
        self,
        stream_id: str,
    ) -> dict[str, Any] | None:
        """Snapshot getirir.

        Args:
            stream_id: Akis ID.

        Returns:
            Snapshot veya None.
        """
        return self._snapshots.get(stream_id)

    def delete_stream(
        self,
        stream_id: str,
    ) -> bool:
        """Akisi siler.

        Args:
            stream_id: Akis ID.

        Returns:
            Basarili mi.
        """
        if stream_id in self._streams:
            del self._streams[stream_id]
            self._snapshots.pop(stream_id, None)
            return True
        return False

    def get_streams(self) -> list[str]:
        """Akis listesini getirir.

        Returns:
            Akis ID listesi.
        """
        return list(self._streams.keys())

    @property
    def stream_count(self) -> int:
        """Akis sayisi."""
        return len(self._streams)

    @property
    def event_count(self) -> int:
        """Toplam olay sayisi."""
        return sum(
            len(s) for s in self._streams.values()
        )

    @property
    def snapshot_count(self) -> int:
        """Snapshot sayisi."""
        return len(self._snapshots)

    @property
    def global_position(self) -> int:
        """Global pozisyon."""
        return self._global_position
