"""ATLAS Akis Birlestirici modulu.

Inner/outer join, temporal join,
zenginlestirme join, coklu akis
ve anahtar tabanli birlestirme.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class StreamJoiner:
    """Akis birlestirici.

    Farkli akislari birlestirir.

    Attributes:
        _buffers: Akis tamponlari.
        _join_configs: Join konfigurasyonlari.
    """

    def __init__(self) -> None:
        """Birlestiriciyi baslatir."""
        self._buffers: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._join_configs: dict[
            str, dict[str, Any]
        ] = {}
        self._results: list[
            dict[str, Any]
        ] = []
        self._enrichment_tables: dict[
            str, dict[str, dict[str, Any]]
        ] = {}

        logger.info(
            "StreamJoiner baslatildi",
        )

    def register_stream(
        self,
        name: str,
    ) -> dict[str, Any]:
        """Akis kaydeder.

        Args:
            name: Akis adi.

        Returns:
            Kayit bilgisi.
        """
        self._buffers[name] = []
        return {"name": name, "status": "registered"}

    def add_event(
        self,
        stream: str,
        event: dict[str, Any],
    ) -> dict[str, Any]:
        """Akisa olay ekler.

        Args:
            stream: Akis adi.
            event: Olay.

        Returns:
            Ekleme bilgisi.
        """
        if stream not in self._buffers:
            return {"error": "stream_not_found"}

        event["_stream"] = stream
        event.setdefault(
            "timestamp", time.time(),
        )
        self._buffers[stream].append(event)

        return {
            "stream": stream,
            "buffered": len(self._buffers[stream]),
        }

    def inner_join(
        self,
        left: str,
        right: str,
        key: str,
    ) -> list[dict[str, Any]]:
        """Inner join yapar.

        Args:
            left: Sol akis.
            right: Sag akis.
            key: Birlestirme anahtari.

        Returns:
            Birlesmis olaylar.
        """
        left_events = self._buffers.get(left, [])
        right_events = self._buffers.get(right, [])

        # Sag tarafi indexle
        right_idx: dict[
            Any, list[dict[str, Any]]
        ] = {}
        for e in right_events:
            k = e.get(key)
            if k is not None:
                right_idx.setdefault(k, []).append(e)

        results: list[dict[str, Any]] = []
        for le in left_events:
            k = le.get(key)
            if k in right_idx:
                for re in right_idx[k]:
                    merged = {
                        **{f"left_{lk}": lv for lk, lv in le.items()},
                        **{f"right_{rk}": rv for rk, rv in re.items()},
                        "join_key": k,
                        "join_type": "inner",
                    }
                    results.append(merged)

        self._results.extend(results)
        return results

    def left_join(
        self,
        left: str,
        right: str,
        key: str,
    ) -> list[dict[str, Any]]:
        """Left join yapar.

        Args:
            left: Sol akis.
            right: Sag akis.
            key: Birlestirme anahtari.

        Returns:
            Birlesmis olaylar.
        """
        left_events = self._buffers.get(left, [])
        right_events = self._buffers.get(right, [])

        right_idx: dict[
            Any, list[dict[str, Any]]
        ] = {}
        for e in right_events:
            k = e.get(key)
            if k is not None:
                right_idx.setdefault(k, []).append(e)

        results: list[dict[str, Any]] = []
        for le in left_events:
            k = le.get(key)
            matches = right_idx.get(k, [])
            if matches:
                for re in matches:
                    merged = {
                        **{f"left_{lk}": lv for lk, lv in le.items()},
                        **{f"right_{rk}": rv for rk, rv in re.items()},
                        "join_key": k,
                        "join_type": "left",
                    }
                    results.append(merged)
            else:
                merged = {
                    **{f"left_{lk}": lv for lk, lv in le.items()},
                    "join_key": k,
                    "join_type": "left",
                    "right_matched": False,
                }
                results.append(merged)

        self._results.extend(results)
        return results

    def outer_join(
        self,
        left: str,
        right: str,
        key: str,
    ) -> list[dict[str, Any]]:
        """Outer join yapar.

        Args:
            left: Sol akis.
            right: Sag akis.
            key: Birlestirme anahtari.

        Returns:
            Birlesmis olaylar.
        """
        left_events = self._buffers.get(left, [])
        right_events = self._buffers.get(right, [])

        left_keys: set[Any] = set()
        right_idx: dict[
            Any, list[dict[str, Any]]
        ] = {}
        for e in right_events:
            k = e.get(key)
            if k is not None:
                right_idx.setdefault(k, []).append(e)

        results: list[dict[str, Any]] = []

        # Sol tarafi isle
        for le in left_events:
            k = le.get(key)
            left_keys.add(k)
            matches = right_idx.get(k, [])
            if matches:
                for re in matches:
                    merged = {
                        **{f"left_{lk}": lv for lk, lv in le.items()},
                        **{f"right_{rk}": rv for rk, rv in re.items()},
                        "join_key": k,
                        "join_type": "outer",
                    }
                    results.append(merged)
            else:
                results.append({
                    **{f"left_{lk}": lv for lk, lv in le.items()},
                    "join_key": k,
                    "join_type": "outer",
                })

        # Sadece sagda olan
        for k, evts in right_idx.items():
            if k not in left_keys:
                for re in evts:
                    results.append({
                        **{f"right_{rk}": rv for rk, rv in re.items()},
                        "join_key": k,
                        "join_type": "outer",
                    })

        self._results.extend(results)
        return results

    def temporal_join(
        self,
        left: str,
        right: str,
        key: str,
        window_seconds: float = 10.0,
    ) -> list[dict[str, Any]]:
        """Zamansal join yapar.

        Args:
            left: Sol akis.
            right: Sag akis.
            key: Birlestirme anahtari.
            window_seconds: Zaman penceresi.

        Returns:
            Birlesmis olaylar.
        """
        left_events = self._buffers.get(left, [])
        right_events = self._buffers.get(right, [])

        results: list[dict[str, Any]] = []
        for le in left_events:
            lk = le.get(key)
            lt = le.get("timestamp", 0)
            for re in right_events:
                rk = re.get(key)
                rt = re.get("timestamp", 0)
                if (
                    lk == rk
                    and abs(lt - rt) <= window_seconds
                ):
                    merged = {
                        **{f"left_{k2}": v2 for k2, v2 in le.items()},
                        **{f"right_{k2}": v2 for k2, v2 in re.items()},
                        "join_key": lk,
                        "join_type": "temporal",
                        "time_diff": abs(lt - rt),
                    }
                    results.append(merged)

        self._results.extend(results)
        return results

    def set_enrichment_table(
        self,
        name: str,
        data: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        """Zenginlestirme tablosu ayarlar.

        Args:
            name: Tablo adi.
            data: Anahtar-deger eslesmesi.

        Returns:
            Ayar bilgisi.
        """
        self._enrichment_tables[name] = data
        return {
            "name": name,
            "entries": len(data),
        }

    def enrich(
        self,
        stream: str,
        table: str,
        key: str,
    ) -> list[dict[str, Any]]:
        """Akisi zenginlestirir.

        Args:
            stream: Akis adi.
            table: Tablo adi.
            key: Birlestirme anahtari.

        Returns:
            Zenginlestirilmis olaylar.
        """
        events = self._buffers.get(stream, [])
        lookup = self._enrichment_tables.get(
            table, {},
        )

        results: list[dict[str, Any]] = []
        for event in events:
            k = event.get(key)
            enrichment = lookup.get(str(k), {})
            enriched = {
                **event,
                "enrichment": enrichment,
                "enriched": bool(enrichment),
            }
            results.append(enriched)

        return results

    def clear_buffer(
        self,
        stream: str,
    ) -> int:
        """Tamponu temizler.

        Args:
            stream: Akis adi.

        Returns:
            Silinen olay sayisi.
        """
        buf = self._buffers.get(stream, [])
        count = len(buf)
        self._buffers[stream] = []
        return count

    def get_results(
        self,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Sonuclari getirir.

        Args:
            limit: Limit.

        Returns:
            Sonuc listesi.
        """
        return self._results[-limit:]

    @property
    def stream_count(self) -> int:
        """Akis sayisi."""
        return len(self._buffers)

    @property
    def result_count(self) -> int:
        """Sonuc sayisi."""
        return len(self._results)

    @property
    def enrichment_table_count(self) -> int:
        """Zenginlestirme tablosu sayisi."""
        return len(self._enrichment_tables)

    @property
    def total_buffered(self) -> int:
        """Toplam tamponlanmis olay."""
        return sum(
            len(b) for b in self._buffers.values()
        )
