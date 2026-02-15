"""ATLAS Iz Yoneticisi modulu.

Iz olusturma, span yonetimi,
baglam yayilimi, ornekleme stratejileri
ve iz korelasyonu.
"""

import hashlib
import logging
import time
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class TraceManager:
    """Iz yoneticisi.

    Dagitik izleri yonetir.

    Attributes:
        _traces: Aktif izler.
        _spans: Span verileri.
    """

    def __init__(
        self,
        sampling_rate: float = 1.0,
    ) -> None:
        """Iz yoneticisini baslatir.

        Args:
            sampling_rate: Ornekleme orani (0-1).
        """
        self._traces: dict[
            str, dict[str, Any]
        ] = {}
        self._spans: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._context: dict[
            str, dict[str, Any]
        ] = {}
        self._sampling_rate = max(
            0.0, min(1.0, sampling_rate),
        )
        self._completed: list[
            dict[str, Any]
        ] = []

        logger.info(
            "TraceManager baslatildi: rate=%.2f",
            self._sampling_rate,
        )

    def start_trace(
        self,
        name: str,
        attributes: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Yeni iz baslatir.

        Args:
            name: Iz adi.
            attributes: Nitelikler.

        Returns:
            Iz bilgisi.
        """
        # Ornekleme kontrolu
        if not self._should_sample(name):
            return {
                "trace_id": "",
                "sampled": False,
            }

        trace_id = str(uuid4())[:8]
        trace = {
            "trace_id": trace_id,
            "name": name,
            "status": "active",
            "attributes": attributes or {},
            "start_time": time.time(),
            "span_count": 0,
        }
        self._traces[trace_id] = trace
        self._spans[trace_id] = []

        return {
            "trace_id": trace_id,
            "sampled": True,
            "name": name,
        }

    def end_trace(
        self,
        trace_id: str,
        status: str = "completed",
    ) -> dict[str, Any]:
        """Izi sonlandirir.

        Args:
            trace_id: Iz ID.
            status: Son durum.

        Returns:
            Iz sonucu.
        """
        trace = self._traces.get(trace_id)
        if not trace:
            return {
                "status": "error",
                "reason": "not_found",
            }

        duration = time.time() - trace["start_time"]
        trace["status"] = status
        trace["duration_ms"] = duration * 1000
        trace["end_time"] = time.time()

        self._completed.append(dict(trace))
        del self._traces[trace_id]

        return {
            "trace_id": trace_id,
            "status": status,
            "duration_ms": trace["duration_ms"],
            "span_count": trace["span_count"],
        }

    def start_span(
        self,
        trace_id: str,
        name: str,
        parent_span_id: str | None = None,
    ) -> dict[str, Any]:
        """Yeni span baslatir.

        Args:
            trace_id: Iz ID.
            name: Span adi.
            parent_span_id: Ust span ID.

        Returns:
            Span bilgisi.
        """
        if trace_id not in self._traces:
            return {
                "status": "error",
                "reason": "trace_not_found",
            }

        span_id = str(uuid4())[:8]
        span = {
            "span_id": span_id,
            "trace_id": trace_id,
            "name": name,
            "parent_span_id": parent_span_id,
            "status": "active",
            "start_time": time.time(),
            "attributes": {},
            "events": [],
        }
        self._spans[trace_id].append(span)
        self._traces[trace_id]["span_count"] += 1

        return {
            "span_id": span_id,
            "trace_id": trace_id,
            "name": name,
        }

    def end_span(
        self,
        trace_id: str,
        span_id: str,
        status: str = "ok",
    ) -> dict[str, Any]:
        """Span sonlandirir.

        Args:
            trace_id: Iz ID.
            span_id: Span ID.
            status: Son durum.

        Returns:
            Span sonucu.
        """
        spans = self._spans.get(trace_id, [])
        for span in spans:
            if span["span_id"] == span_id:
                duration = (
                    time.time() - span["start_time"]
                )
                span["status"] = status
                span["duration_ms"] = duration * 1000
                span["end_time"] = time.time()
                return {
                    "span_id": span_id,
                    "status": status,
                    "duration_ms": span["duration_ms"],
                }

        return {
            "status": "error",
            "reason": "span_not_found",
        }

    def add_span_event(
        self,
        trace_id: str,
        span_id: str,
        event_name: str,
        attributes: dict[str, Any] | None = None,
    ) -> bool:
        """Span'a olay ekler.

        Args:
            trace_id: Iz ID.
            span_id: Span ID.
            event_name: Olay adi.
            attributes: Nitelikler.

        Returns:
            Basarili mi.
        """
        spans = self._spans.get(trace_id, [])
        for span in spans:
            if span["span_id"] == span_id:
                span["events"].append({
                    "name": event_name,
                    "attributes": attributes or {},
                    "timestamp": time.time(),
                })
                return True
        return False

    def set_context(
        self,
        trace_id: str,
        key: str,
        value: Any,
    ) -> None:
        """Baglam bilgisi ayarlar.

        Args:
            trace_id: Iz ID.
            key: Anahtar.
            value: Deger.
        """
        if trace_id not in self._context:
            self._context[trace_id] = {}
        self._context[trace_id][key] = value

    def get_context(
        self,
        trace_id: str,
    ) -> dict[str, Any]:
        """Baglam bilgisi getirir.

        Args:
            trace_id: Iz ID.

        Returns:
            Baglam bilgisi.
        """
        return dict(
            self._context.get(trace_id, {}),
        )

    def correlate(
        self,
        trace_id_a: str,
        trace_id_b: str,
        relation: str = "related",
    ) -> dict[str, Any]:
        """Izleri iliskilendirir.

        Args:
            trace_id_a: Iz A.
            trace_id_b: Iz B.
            relation: Iliski tipi.

        Returns:
            Korelasyon bilgisi.
        """
        a_exists = (
            trace_id_a in self._traces
            or any(
                t["trace_id"] == trace_id_a
                for t in self._completed
            )
        )
        b_exists = (
            trace_id_b in self._traces
            or any(
                t["trace_id"] == trace_id_b
                for t in self._completed
            )
        )

        return {
            "trace_a": trace_id_a,
            "trace_b": trace_id_b,
            "relation": relation,
            "valid": a_exists and b_exists,
        }

    def get_trace(
        self,
        trace_id: str,
    ) -> dict[str, Any] | None:
        """Iz bilgisi getirir.

        Args:
            trace_id: Iz ID.

        Returns:
            Iz bilgisi veya None.
        """
        if trace_id in self._traces:
            return dict(self._traces[trace_id])
        for t in self._completed:
            if t["trace_id"] == trace_id:
                return dict(t)
        return None

    def get_spans(
        self,
        trace_id: str,
    ) -> list[dict[str, Any]]:
        """Iz span'larini getirir.

        Args:
            trace_id: Iz ID.

        Returns:
            Span listesi.
        """
        return list(
            self._spans.get(trace_id, []),
        )

    def _should_sample(
        self,
        name: str,
    ) -> bool:
        """Ornekleme karari.

        Args:
            name: Iz adi.

        Returns:
            Orneklenmeli mi.
        """
        if self._sampling_rate >= 1.0:
            return True
        if self._sampling_rate <= 0.0:
            return False
        h = hashlib.md5(
            f"{name}:{time.time()}".encode(),
        ).hexdigest()
        bucket = int(h[:8], 16) % 100
        return bucket < (self._sampling_rate * 100)

    @property
    def active_trace_count(self) -> int:
        """Aktif iz sayisi."""
        return len(self._traces)

    @property
    def completed_trace_count(self) -> int:
        """Tamamlanmis iz sayisi."""
        return len(self._completed)

    @property
    def sampling_rate(self) -> float:
        """Ornekleme orani."""
        return self._sampling_rate
