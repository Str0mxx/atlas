"""ATLAS Kok Varlik modulu.

Durum yonetimi, olay uygulama,
komut isleme, degismez dogrulama
ve surum takibi.
"""

import logging
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)


class AggregateRoot:
    """Kok varlik.

    Domain olay kaynaklama icin temel sinif.

    Attributes:
        aggregate_id: Aggregate ID.
        _state: Ic durum.
        _version: Surum.
    """

    def __init__(
        self,
        aggregate_id: str,
        aggregate_type: str = "default",
    ) -> None:
        """Kok varligi baslatir.

        Args:
            aggregate_id: Aggregate ID.
            aggregate_type: Aggregate tipi.
        """
        self.aggregate_id = aggregate_id
        self.aggregate_type = aggregate_type
        self._state: dict[str, Any] = {}
        self._version: int = 0
        self._uncommitted: list[
            dict[str, Any]
        ] = []
        self._command_handlers: dict[
            str, Callable[..., Any]
        ] = {}
        self._event_appliers: dict[
            str, Callable[..., Any]
        ] = {}
        self._invariants: list[
            Callable[..., bool]
        ] = []

        logger.info(
            "AggregateRoot olusturuldu: %s",
            aggregate_id,
        )

    def apply_event(
        self,
        event_type: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Olay uygular.

        Args:
            event_type: Olay tipi.
            data: Olay verisi.

        Returns:
            Olay kaydi.
        """
        self._version += 1

        event = {
            "event_type": event_type,
            "aggregate_id": self.aggregate_id,
            "data": data or {},
            "version": self._version,
            "timestamp": time.time(),
        }

        # Ozel uygulayici varsa cagir
        applier = self._event_appliers.get(
            event_type,
        )
        if applier:
            applier(self._state, data or {})
        else:
            # Varsayilan: veriyi duruma birlestir
            self._state.update(data or {})

        self._uncommitted.append(event)
        return event

    def handle_command(
        self,
        command_type: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Komut isler.

        Args:
            command_type: Komut tipi.
            payload: Komut verisi.

        Returns:
            Islem sonucu.

        Raises:
            ValueError: Gecersiz komut veya
                degismez ihlali.
        """
        handler = self._command_handlers.get(
            command_type,
        )
        if not handler:
            raise ValueError(
                f"Unknown command: {command_type}"
            )

        result = handler(payload or {})

        # Degismezleri dogrula
        for invariant in self._invariants:
            if not invariant(self._state):
                raise ValueError(
                    "Invariant violation"
                )

        return {
            "command_type": command_type,
            "aggregate_id": self.aggregate_id,
            "result": result,
            "version": self._version,
        }

    def register_command_handler(
        self,
        command_type: str,
        handler: Callable[..., Any],
    ) -> None:
        """Komut isleyici kaydeder.

        Args:
            command_type: Komut tipi.
            handler: Isleyici fonksiyon.
        """
        self._command_handlers[
            command_type
        ] = handler

    def register_event_applier(
        self,
        event_type: str,
        applier: Callable[..., Any],
    ) -> None:
        """Olay uygulayici kaydeder.

        Args:
            event_type: Olay tipi.
            applier: Uygulayici fonksiyon.
        """
        self._event_appliers[
            event_type
        ] = applier

    def add_invariant(
        self,
        check: Callable[..., bool],
    ) -> None:
        """Degismez ekler.

        Args:
            check: Kontrol fonksiyonu.
        """
        self._invariants.append(check)

    def get_uncommitted_events(
        self,
    ) -> list[dict[str, Any]]:
        """Kaydedilmemis olaylari getirir.

        Returns:
            Olay listesi.
        """
        return list(self._uncommitted)

    def clear_uncommitted(self) -> int:
        """Kaydedilmemisleri temizler.

        Returns:
            Temizlenen sayi.
        """
        count = len(self._uncommitted)
        self._uncommitted.clear()
        return count

    def load_from_history(
        self,
        events: list[dict[str, Any]],
    ) -> None:
        """Gecmisten yukler.

        Args:
            events: Olay gecmisi.
        """
        for event in events:
            event_type = event.get(
                "event_type", "",
            )
            data = event.get("data", {})

            applier = self._event_appliers.get(
                event_type,
            )
            if applier:
                applier(self._state, data)
            else:
                self._state.update(data)

            self._version = event.get(
                "version", self._version + 1,
            )

    def get_snapshot(self) -> dict[str, Any]:
        """Snapshot getirir.

        Returns:
            Snapshot bilgisi.
        """
        return {
            "aggregate_id": self.aggregate_id,
            "aggregate_type": self.aggregate_type,
            "state": dict(self._state),
            "version": self._version,
            "timestamp": time.time(),
        }

    def load_from_snapshot(
        self,
        snapshot: dict[str, Any],
    ) -> None:
        """Snapshot'tan yukler.

        Args:
            snapshot: Snapshot bilgisi.
        """
        self._state = dict(
            snapshot.get("state", {}),
        )
        self._version = snapshot.get(
            "version", 0,
        )

    @property
    def state(self) -> dict[str, Any]:
        """Mevcut durum."""
        return dict(self._state)

    @property
    def version(self) -> int:
        """Mevcut surum."""
        return self._version

    @property
    def uncommitted_count(self) -> int:
        """Kaydedilmemis olay sayisi."""
        return len(self._uncommitted)
