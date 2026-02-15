"""ATLAS Akis Isleyici modulu.

Map/filter/reduce, donusum zincirleri,
durumlu isleme, paralel isleme
ve hata yonetimi.
"""

import logging
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)


class StreamProcessor:
    """Akis isleyici.

    Olaylari donusturur ve isler.

    Attributes:
        _chains: Donusum zincirleri.
        _state: Durumlu isleme deposu.
    """

    def __init__(self) -> None:
        """Isleyiciyi baslatir."""
        self._chains: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._state: dict[str, Any] = {}
        self._error_handlers: dict[
            str,
            Callable[[dict[str, Any], Exception], Any],
        ] = {}
        self._stats = {
            "processed": 0,
            "errors": 0,
            "filtered": 0,
        }

        logger.info(
            "StreamProcessor baslatildi",
        )

    def add_map(
        self,
        chain: str,
        name: str,
        fn: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> dict[str, Any]:
        """Map islemcisi ekler.

        Args:
            chain: Zincir adi.
            name: Islemci adi.
            fn: Donusum fonksiyonu.

        Returns:
            Ekleme bilgisi.
        """
        if chain not in self._chains:
            self._chains[chain] = []

        self._chains[chain].append({
            "name": name,
            "type": "map",
            "fn": fn,
        })

        return {"chain": chain, "name": name}

    def add_filter(
        self,
        chain: str,
        name: str,
        predicate: Callable[[dict[str, Any]], bool],
    ) -> dict[str, Any]:
        """Filter islemcisi ekler.

        Args:
            chain: Zincir adi.
            name: Islemci adi.
            predicate: Filtre fonksiyonu.

        Returns:
            Ekleme bilgisi.
        """
        if chain not in self._chains:
            self._chains[chain] = []

        self._chains[chain].append({
            "name": name,
            "type": "filter",
            "fn": predicate,
        })

        return {"chain": chain, "name": name}

    def add_reduce(
        self,
        chain: str,
        name: str,
        fn: Callable[[Any, dict[str, Any]], Any],
        initial: Any = None,
    ) -> dict[str, Any]:
        """Reduce islemcisi ekler.

        Args:
            chain: Zincir adi.
            name: Islemci adi.
            fn: Birlestirme fonksiyonu.
            initial: Baslangic degeri.

        Returns:
            Ekleme bilgisi.
        """
        if chain not in self._chains:
            self._chains[chain] = []

        state_key = f"reduce_{chain}_{name}"
        self._state[state_key] = initial

        self._chains[chain].append({
            "name": name,
            "type": "reduce",
            "fn": fn,
            "state_key": state_key,
        })

        return {"chain": chain, "name": name}

    def process(
        self,
        chain: str,
        event: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Olayi isler.

        Args:
            chain: Zincir adi.
            event: Olay verisi.

        Returns:
            Islenmis olay veya None (filtrelendi).
        """
        steps = self._chains.get(chain, [])
        current = dict(event)

        for step in steps:
            try:
                if step["type"] == "map":
                    current = step["fn"](current)
                elif step["type"] == "filter":
                    if not step["fn"](current):
                        self._stats["filtered"] += 1
                        return None
                elif step["type"] == "reduce":
                    key = step["state_key"]
                    self._state[key] = step["fn"](
                        self._state[key], current,
                    )
                    current["_reduce_result"] = (
                        self._state[key]
                    )
            except Exception as e:
                self._stats["errors"] += 1
                handler = self._error_handlers.get(
                    chain,
                )
                if handler:
                    handler(current, e)
                logger.error(
                    "Isleme hatasi: %s", e,
                )
                return None

        self._stats["processed"] += 1
        return current

    def process_batch(
        self,
        chain: str,
        events: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Toplu isler.

        Args:
            chain: Zincir adi.
            events: Olaylar.

        Returns:
            Islenmis olaylar.
        """
        results: list[dict[str, Any]] = []
        for event in events:
            result = self.process(chain, event)
            if result is not None:
                results.append(result)
        return results

    def set_error_handler(
        self,
        chain: str,
        handler: Callable[
            [dict[str, Any], Exception], Any
        ],
    ) -> None:
        """Hata isleyici ayarlar.

        Args:
            chain: Zincir adi.
            handler: Hata fonksiyonu.
        """
        self._error_handlers[chain] = handler

    def set_state(
        self,
        key: str,
        value: Any,
    ) -> None:
        """Durum ayarlar.

        Args:
            key: Anahtar.
            value: Deger.
        """
        self._state[key] = value

    def get_state(
        self,
        key: str,
    ) -> Any:
        """Durum getirir.

        Args:
            key: Anahtar.

        Returns:
            Deger.
        """
        return self._state.get(key)

    def get_chain(
        self,
        chain: str,
    ) -> list[dict[str, Any]]:
        """Zincir bilgisini getirir.

        Args:
            chain: Zincir adi.

        Returns:
            Adim listesi.
        """
        steps = self._chains.get(chain, [])
        return [
            {"name": s["name"], "type": s["type"]}
            for s in steps
        ]

    def remove_chain(
        self,
        chain: str,
    ) -> bool:
        """Zinciri kaldirir.

        Args:
            chain: Zincir adi.

        Returns:
            Basarili mi.
        """
        if chain in self._chains:
            del self._chains[chain]
            return True
        return False

    def get_stats(self) -> dict[str, int]:
        """Istatistikleri getirir.

        Returns:
            Istatistikler.
        """
        return dict(self._stats)

    @property
    def chain_count(self) -> int:
        """Zincir sayisi."""
        return len(self._chains)

    @property
    def processed_count(self) -> int:
        """Islenen olay sayisi."""
        return self._stats["processed"]

    @property
    def error_count(self) -> int:
        """Hata sayisi."""
        return self._stats["errors"]

    @property
    def step_count(self) -> int:
        """Toplam adim sayisi."""
        return sum(
            len(c) for c in self._chains.values()
        )
