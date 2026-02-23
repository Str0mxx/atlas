"""Saglayici akim adaptoru.

Saglayiciya ozel akim ayristirma, format
normalizasyonu ve delta cikarma saglar.
"""

import json
import logging
from typing import Any

from app.models.streaming_models import (
    ProviderFormat,
    StreamToken,
)

logger = logging.getLogger(__name__)


class ProviderStreamAdapter:
    """Saglayici akim adaptoru.

    Farkli LLM saglayicilarindan gelen akim
    verilerini normallestirir.

    Attributes:
        _provider: Saglayici adi.
        _format: Akim formati.
        _token_index: Token indeksi.
        _total_parsed: Toplam ayristirilan.
        _errors: Hata sayisi.
        _metadata: Birikimli metadata.
    """

    # Saglayici format haritasi
    _PROVIDER_FORMATS: dict[str, ProviderFormat] = {
        "anthropic": ProviderFormat.SSE,
        "openai": ProviderFormat.SSE,
        "gemini": ProviderFormat.NDJSON,
        "ollama": ProviderFormat.NDJSON,
        "openrouter": ProviderFormat.SSE,
    }

    def __init__(
        self,
        provider: str = "anthropic",
        custom_format: ProviderFormat | None = None,
    ) -> None:
        """ProviderStreamAdapter baslatir.

        Args:
            provider: Saglayici adi.
            custom_format: Ozel format (otomatik tespit yerine).
        """
        self._provider = provider
        self._format = custom_format or self._PROVIDER_FORMATS.get(
            provider, ProviderFormat.RAW
        )
        self._token_index: int = 0
        self._total_parsed: int = 0
        self._errors: int = 0
        self._metadata: dict[str, Any] = {}
        self._buffer: str = ""

        logger.info(
            "ProviderStreamAdapter baslatildi: provider=%s, format=%s",
            provider, self._format.value,
        )

    def parse_chunk(self, raw_data: str) -> list[StreamToken]:
        """Ham akim verisini ayristirir.

        Args:
            raw_data: Ham veri.

        Returns:
            Ayristirilmis token listesi.
        """
        if self._format == ProviderFormat.SSE:
            return self._parse_sse(raw_data)
        elif self._format == ProviderFormat.NDJSON:
            return self._parse_ndjson(raw_data)
        elif self._format == ProviderFormat.WEBSOCKET:
            return self._parse_websocket(raw_data)
        else:
            return self._parse_raw(raw_data)

    def _parse_sse(self, raw_data: str) -> list[StreamToken]:
        """SSE formatini ayristirir.

        Args:
            raw_data: SSE verisi.

        Returns:
            Token listesi.
        """
        tokens: list[StreamToken] = []
        self._buffer += raw_data

        lines = self._buffer.split("\n")
        self._buffer = ""

        # Son satir tamamlanmamis olabilir
        if not raw_data.endswith("\n"):
            self._buffer = lines[-1]
            lines = lines[:-1]

        for line in lines:
            line = line.strip()

            if not line:
                continue

            if line.startswith("data: "):
                data = line[6:]

                if data == "[DONE]":
                    tokens.append(self._create_token("", is_last=True))
                    continue

                content = self._extract_content_sse(data)
                if content:
                    tokens.append(self._create_token(content))

        return tokens

    def _parse_ndjson(self, raw_data: str) -> list[StreamToken]:
        """NDJSON formatini ayristirir.

        Args:
            raw_data: NDJSON verisi.

        Returns:
            Token listesi.
        """
        tokens: list[StreamToken] = []
        self._buffer += raw_data

        lines = self._buffer.split("\n")
        self._buffer = ""

        if not raw_data.endswith("\n"):
            self._buffer = lines[-1]
            lines = lines[:-1]

        for line in lines:
            line = line.strip()
            if not line:
                continue

            try:
                obj = json.loads(line)
                content = self._extract_content_json(obj)
                is_done = obj.get("done", False)

                if content:
                    tokens.append(self._create_token(
                        content, is_last=is_done
                    ))
                elif is_done:
                    tokens.append(self._create_token("", is_last=True))

            except json.JSONDecodeError:
                self._errors += 1
                logger.debug("JSON ayristirma hatasi: %s", line[:50])

        return tokens

    def _parse_websocket(self, raw_data: str) -> list[StreamToken]:
        """WebSocket formatini ayristirir.

        Args:
            raw_data: WebSocket verisi.

        Returns:
            Token listesi.
        """
        tokens: list[StreamToken] = []

        try:
            obj = json.loads(raw_data)
            content = self._extract_content_json(obj)
            is_done = obj.get("done", False) or obj.get("finished", False)

            if content or is_done:
                tokens.append(self._create_token(
                    content or "", is_last=is_done
                ))

        except json.JSONDecodeError:
            # Duz metin olarak isle
            if raw_data.strip():
                tokens.append(self._create_token(raw_data))

        return tokens

    def _parse_raw(self, raw_data: str) -> list[StreamToken]:
        """Ham formati ayristirir.

        Args:
            raw_data: Ham veri.

        Returns:
            Token listesi.
        """
        if raw_data:
            return [self._create_token(raw_data)]
        return []

    def _extract_content_sse(self, data: str) -> str:
        """SSE verisinden icerik cikarir.

        Args:
            data: SSE data alani.

        Returns:
            Cikarilan icerik.
        """
        try:
            obj = json.loads(data)
            return self._extract_content_json(obj)
        except json.JSONDecodeError:
            return data

    def _extract_content_json(self, obj: dict[str, Any]) -> str:
        """JSON'dan icerik cikarir (saglayiciya ozel).

        Args:
            obj: JSON nesnesi.

        Returns:
            Cikarilan icerik.
        """
        content = ""

        if self._provider == "anthropic":
            # Anthropic: delta.text veya content_block.text
            delta = obj.get("delta", {})
            content = delta.get("text", "")
            if not content:
                content = obj.get("text", "")

            # Metadata kaydet
            if "usage" in obj:
                self._metadata["usage"] = obj["usage"]

        elif self._provider == "openai":
            # OpenAI: choices[0].delta.content
            choices = obj.get("choices", [])
            if choices:
                delta = choices[0].get("delta", {})
                content = delta.get("content", "") or ""

                # finish_reason kontrol
                fr = choices[0].get("finish_reason")
                if fr:
                    self._metadata["finish_reason"] = fr

            if "usage" in obj:
                self._metadata["usage"] = obj["usage"]

        elif self._provider == "gemini":
            # Gemini: candidates[0].content.parts[0].text
            candidates = obj.get("candidates", [])
            if candidates:
                c_content = candidates[0].get("content", {})
                parts = c_content.get("parts", [])
                if parts:
                    content = parts[0].get("text", "")

        elif self._provider == "ollama":
            # Ollama: message.content veya response
            msg = obj.get("message", {})
            content = msg.get("content", "")
            if not content:
                content = obj.get("response", "")

        elif self._provider == "openrouter":
            # OpenRouter: OpenAI uyumlu
            choices = obj.get("choices", [])
            if choices:
                delta = choices[0].get("delta", {})
                content = delta.get("content", "") or ""

        else:
            # Genel: content, text, message alanlarini dene
            content = (
                obj.get("content", "")
                or obj.get("text", "")
                or obj.get("message", "")
            )

        return content

    def _create_token(
        self, content: str, is_last: bool = False
    ) -> StreamToken:
        """StreamToken olusturur.

        Args:
            content: Token icerigi.
            is_last: Son token mu.

        Returns:
            Yeni StreamToken.
        """
        is_first = self._token_index == 0
        token = StreamToken(
            content=content,
            index=self._token_index,
            is_first=is_first,
            is_last=is_last,
        )
        self._token_index += 1
        self._total_parsed += 1
        return token

    def reset(self) -> None:
        """Adaptoru sifirlar."""
        self._token_index = 0
        self._metadata.clear()
        self._buffer = ""

    @property
    def provider(self) -> str:
        """Saglayici adi."""
        return self._provider

    @property
    def format(self) -> ProviderFormat:
        """Akim formati."""
        return self._format

    @property
    def metadata(self) -> dict[str, Any]:
        """Birikimli metadata."""
        return dict(self._metadata)

    def get_stats(self) -> dict[str, Any]:
        """Istatistikleri dondurur.

        Returns:
            Istatistik sozlugu.
        """
        return {
            "provider": self._provider,
            "format": self._format.value,
            "total_parsed": self._total_parsed,
            "token_index": self._token_index,
            "errors": self._errors,
            "buffer_size": len(self._buffer),
            "metadata_keys": list(self._metadata.keys()),
        }
