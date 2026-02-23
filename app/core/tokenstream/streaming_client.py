"""Streaming Client.

SSE handling, WebSocket streaming, chunk isleme,
buffer yonetimi ve tamamlama tespiti saglar.
"""

import logging
import time
from typing import Any, AsyncIterator

from app.models.streaming_models import (
    StreamConfig,
    StreamEventType,
    StreamMetrics,
    StreamState,
    StreamingSnapshot,
)
from app.core.tokenstream.token_buffer import TokenBuffer
from app.core.tokenstream.stream_event_emitter import StreamEventEmitter
from app.core.tokenstream.provider_stream_adapter import ProviderStreamAdapter
from app.core.tokenstream.stream_error_handler import StreamErrorHandler

logger = logging.getLogger(__name__)


class StreamingClient:
    """Streaming Client.

    LLM saglayicilarindan token akisini yonetir,
    buffer/event/error islemlerini koordine eder.

    Attributes:
        _config: Yapilandirma.
        _buffer: Token buffer.
        _emitter: Olay yayicisi.
        _error_handler: Hata yoneticisi.
        _adapters: Saglayici adaptorler.
        _state: Mevcut durum.
        _active_streams: Aktif akim sayisi.
        _total_streams: Toplam akim sayisi.
        _total_tokens: Toplam token.
        _total_bytes: Toplam bayt.
        _metrics_history: Metrik gecmisi.
    """

    def __init__(
        self,
        buffer_size: int = 64,
        flush_interval_ms: int = 50,
        show_typing: bool = True,
        max_retries: int = 3,
        retry_delay_ms: int = 1000,
        backpressure_threshold: int = 100,
    ) -> None:
        """StreamingClient baslatir.

        Args:
            buffer_size: Buffer boyutu.
            flush_interval_ms: Flush araligi (ms).
            show_typing: Yazma gostergesi.
            max_retries: Maksimum yeniden deneme.
            retry_delay_ms: Yeniden deneme gecikmesi.
            backpressure_threshold: Geri basinc esigi.
        """
        self._config = StreamConfig(
            buffer_size=buffer_size,
            flush_interval_ms=flush_interval_ms,
            show_typing=show_typing,
            max_retries=max_retries,
            retry_delay_ms=retry_delay_ms,
            backpressure_threshold=backpressure_threshold,
        )

        self._buffer = TokenBuffer(
            max_size=buffer_size,
            flush_interval_ms=flush_interval_ms,
        )
        self._emitter = StreamEventEmitter(
            backpressure_threshold=backpressure_threshold,
        )
        self._error_handler = StreamErrorHandler(
            max_retries=max_retries,
            retry_delay_ms=retry_delay_ms,
        )
        self._adapters: dict[str, ProviderStreamAdapter] = {}

        self._state = StreamState.IDLE
        self._active_streams: int = 0
        self._total_streams: int = 0
        self._total_tokens: int = 0
        self._total_bytes: int = 0
        self._metrics_history: list[StreamMetrics] = []

        logger.info(
            "StreamingClient baslatildi: buffer=%d, interval=%dms",
            buffer_size, flush_interval_ms,
        )

    def _get_adapter(self, provider: str) -> ProviderStreamAdapter:
        """Saglayici adaptorunu getirir veya olusturur.

        Args:
            provider: Saglayici adi.

        Returns:
            Saglayici adaptoru.
        """
        if provider not in self._adapters:
            self._adapters[provider] = ProviderStreamAdapter(
                provider=provider,
            )
        return self._adapters[provider]

    async def stream_tokens(
        self,
        chunks: list[str],
        provider: str = "anthropic",
        model: str = "",
    ) -> AsyncIterator[str]:
        """Token akisi baslatir.

        Args:
            chunks: Ham akim parcalari.
            provider: Saglayici adi.
            model: Model adi.

        Yields:
            Flush edilen icerikler.
        """
        stream_id = f"stream_{self._total_streams}"
        self._total_streams += 1
        self._active_streams += 1
        self._state = StreamState.STREAMING

        adapter = self._get_adapter(provider)
        adapter.reset()

        self._emitter.set_stream_id(stream_id)
        self._emitter.emit_start(metadata={
            "provider": provider,
            "model": model,
        })

        start_time = time.time()
        first_token_time: float = 0.0
        token_count = 0

        try:
            for raw_chunk in chunks:
                tokens = adapter.parse_chunk(raw_chunk)

                for token in tokens:
                    if token.is_last and not token.content:
                        continue

                    if first_token_time == 0.0:
                        first_token_time = time.time()

                    token_count += 1
                    self._total_tokens += 1
                    self._total_bytes += len(token.content.encode("utf-8"))

                    self._emitter.emit_token(token.content)

                    flushed = self._buffer.add(token.content)
                    if flushed is not None:
                        self._emitter.emit_flush(flushed)
                        yield flushed

            # Kalan buffer'i bosalt
            remaining = self._buffer.flush_complete()
            if remaining:
                self._emitter.emit_flush(remaining)
                yield remaining

            self._state = StreamState.COMPLETED

        except Exception as e:
            self._state = StreamState.ERROR
            self._error_handler.handle_error(
                e,
                provider=provider,
                partial_content=self._buffer.peek(),
            )
            self._emitter.emit_error(str(e))

            remaining = self._buffer.flush()
            if remaining:
                yield remaining

        finally:
            self._active_streams -= 1

            duration = (time.time() - start_time) * 1000
            first_ms = (
                (first_token_time - start_time) * 1000
                if first_token_time > 0 else 0.0
            )
            tps = (
                token_count / (duration / 1000)
                if duration > 0 else 0.0
            )

            metrics = StreamMetrics(
                stream_id=stream_id,
                total_tokens=token_count,
                total_bytes=self._total_bytes,
                duration_ms=duration,
                first_token_ms=first_ms,
                tokens_per_second=tps,
                flush_count=self._buffer.get_stats()["flush_count"],
                error_count=self._error_handler.get_stats()["total_errors"],
                provider=provider,
                model=model,
            )
            self._metrics_history.append(metrics)

            self._emitter.emit_end(metadata={
                "duration_ms": duration,
                "total_tokens": token_count,
                "tokens_per_second": round(tps, 1),
            })

            if self._active_streams == 0:
                self._state = StreamState.IDLE

    async def stream_sse(
        self,
        sse_lines: list[str],
        provider: str = "openai",
        model: str = "",
    ) -> AsyncIterator[str]:
        """SSE akisi isler.

        Args:
            sse_lines: SSE satirlari.
            provider: Saglayici adi.
            model: Model adi.

        Yields:
            Flush edilen icerikler.
        """
        async for content in self.stream_tokens(
            sse_lines, provider=provider, model=model
        ):
            yield content

    def process_single_chunk(
        self,
        raw_data: str,
        provider: str = "anthropic",
    ) -> list[str]:
        """Tek chunk isler (senkron).

        Args:
            raw_data: Ham veri.
            provider: Saglayici adi.

        Returns:
            Flush edilen icerikler.
        """
        adapter = self._get_adapter(provider)
        tokens = adapter.parse_chunk(raw_data)
        results: list[str] = []

        for token in tokens:
            if token.is_last and not token.content:
                continue

            self._total_tokens += 1
            flushed = self._buffer.add(token.content)
            if flushed is not None:
                results.append(flushed)

        return results

    def flush(self) -> str:
        """Buffer'i zorla bosaltir.

        Returns:
            Kalan icerik.
        """
        return self._buffer.flush()

    @property
    def state(self) -> StreamState:
        """Mevcut durum."""
        return self._state

    @property
    def buffer(self) -> TokenBuffer:
        """Token buffer."""
        return self._buffer

    @property
    def emitter(self) -> StreamEventEmitter:
        """Olay yayicisi."""
        return self._emitter

    @property
    def error_handler(self) -> StreamErrorHandler:
        """Hata yoneticisi."""
        return self._error_handler

    def get_last_metrics(self) -> StreamMetrics | None:
        """Son akim metrigini dondurur.

        Returns:
            Son metrik veya None.
        """
        return self._metrics_history[-1] if self._metrics_history else None

    def get_snapshot(self) -> StreamingSnapshot:
        """Sistem snapshot'i dondurur.

        Returns:
            Sistem durumu.
        """
        avg_first_token = 0.0
        avg_tps = 0.0
        if self._metrics_history:
            firsts = [m.first_token_ms for m in self._metrics_history if m.first_token_ms > 0]
            avg_first_token = sum(firsts) / len(firsts) if firsts else 0.0
            tps_vals = [m.tokens_per_second for m in self._metrics_history if m.tokens_per_second > 0]
            avg_tps = sum(tps_vals) / len(tps_vals) if tps_vals else 0.0

        return StreamingSnapshot(
            active_streams=self._active_streams,
            total_streams=self._total_streams,
            total_tokens=self._total_tokens,
            total_bytes=self._total_bytes,
            total_errors=self._error_handler.get_stats()["total_errors"],
            avg_first_token_ms=round(avg_first_token, 2),
            avg_tokens_per_second=round(avg_tps, 1),
            subscribers=self._emitter.subscriber_count,
        )

    def get_stats(self) -> dict[str, Any]:
        """Istatistikleri dondurur.

        Returns:
            Istatistik sozlugu.
        """
        return {
            "state": self._state.value,
            "active_streams": self._active_streams,
            "total_streams": self._total_streams,
            "total_tokens": self._total_tokens,
            "total_bytes": self._total_bytes,
            "buffer": self._buffer.get_stats(),
            "emitter": self._emitter.get_stats(),
            "error_handler": self._error_handler.get_stats(),
            "adapters": list(self._adapters.keys()),
            "metrics_count": len(self._metrics_history),
        }
