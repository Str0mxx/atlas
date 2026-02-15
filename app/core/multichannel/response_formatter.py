"""ATLAS Yanıt Biçimleyici modülü.

Kanala özel biçimleme, zengin medya,
uzunluk adaptasyonu, Markdown/HTML dönüşümü,
ek yönetimi.
"""

import logging
import re
import time
from typing import Any

logger = logging.getLogger(__name__)


class ResponseFormatter:
    """Yanıt biçimleyici.

    Yanıtları kanala uygun biçimlendirir.

    Attributes:
        _formats: Format kayıtları.
        _channel_limits: Kanal uzunluk limitleri.
    """

    def __init__(self) -> None:
        """Biçimleyiciyi başlatır."""
        self._formats: list[
            dict[str, Any]
        ] = []
        self._channel_limits: dict[str, int] = {
            "telegram": 4096,
            "whatsapp": 4096,
            "email": 100000,
            "sms": 160,
            "voice": 500,
        }
        self._counter = 0
        self._stats = {
            "formatted": 0,
            "truncated": 0,
        }

        logger.info(
            "ResponseFormatter baslatildi",
        )

    def format_response(
        self,
        content: str,
        channel: str = "telegram",
        format_type: str = "auto",
    ) -> dict[str, Any]:
        """Yanıt biçimlendirir.

        Args:
            content: İçerik.
            channel: Hedef kanal.
            format_type: Format tipi.

        Returns:
            Biçimleme bilgisi.
        """
        self._counter += 1
        fid = f"fmt_{self._counter}"

        if format_type == "auto":
            format_type = self._detect_format(
                channel,
            )

        formatted = self._apply_format(
            content, channel, format_type,
        )

        # Uzunluk adaptasyonu
        limit = self._channel_limits.get(
            channel, 4096,
        )
        truncated = False
        if len(formatted) > limit:
            formatted = formatted[: limit - 3] + "..."
            truncated = True
            self._stats["truncated"] += 1

        result = {
            "format_id": fid,
            "original": content,
            "formatted": formatted,
            "channel": channel,
            "format_type": format_type,
            "truncated": truncated,
            "length": len(formatted),
            "timestamp": time.time(),
        }
        self._formats.append(result)
        self._stats["formatted"] += 1

        return result

    def _detect_format(
        self,
        channel: str,
    ) -> str:
        """Kanal için format tespit eder.

        Args:
            channel: Kanal.

        Returns:
            Format tipi.
        """
        format_map = {
            "telegram": "markdown",
            "whatsapp": "plain",
            "email": "html",
            "sms": "minimal",
            "voice": "plain",
        }
        return format_map.get(channel, "plain")

    def _apply_format(
        self,
        content: str,
        channel: str,
        format_type: str,
    ) -> str:
        """Format uygular.

        Args:
            content: İçerik.
            channel: Kanal.
            format_type: Format tipi.

        Returns:
            Biçimlenmiş içerik.
        """
        if format_type == "html":
            return self._to_html(content)
        if format_type == "markdown":
            return content
        if format_type == "minimal":
            return self._to_minimal(content)
        return self._strip_formatting(content)

    def to_markdown(
        self,
        content: str,
    ) -> str:
        """Markdown'a dönüştürür.

        Args:
            content: İçerik.

        Returns:
            Markdown metin.
        """
        return content

    def to_html(
        self,
        content: str,
    ) -> str:
        """HTML'e dönüştürür.

        Args:
            content: İçerik.

        Returns:
            HTML metin.
        """
        return self._to_html(content)

    def _to_html(
        self,
        content: str,
    ) -> str:
        """İç HTML dönüşümü."""
        html = content
        html = re.sub(
            r"\*\*(.+?)\*\*",
            r"<strong>\1</strong>",
            html,
        )
        html = re.sub(
            r"\*(.+?)\*",
            r"<em>\1</em>",
            html,
        )
        html = html.replace("\n", "<br>")
        return html

    def _to_minimal(
        self,
        content: str,
    ) -> str:
        """Minimal formata dönüştürür."""
        text = self._strip_formatting(content)
        return text[:157] + "..." if len(text) > 160 else text

    def _strip_formatting(
        self,
        content: str,
    ) -> str:
        """Biçimlendirmeyi kaldırır."""
        text = re.sub(r"\*+", "", content)
        text = re.sub(r"_+", "", text)
        text = re.sub(r"`+", "", text)
        text = re.sub(r"#+\s*", "", text)
        return text.strip()

    def handle_attachment(
        self,
        attachment_type: str,
        url: str,
        channel: str = "telegram",
    ) -> dict[str, Any]:
        """Ek yönetir.

        Args:
            attachment_type: Ek tipi.
            url: Ek URL.
            channel: Kanal.

        Returns:
            Ek bilgisi.
        """
        supported = {
            "telegram": [
                "image", "document", "video",
                "audio",
            ],
            "whatsapp": [
                "image", "document", "video",
            ],
            "email": [
                "image", "document", "video",
                "audio", "archive",
            ],
            "sms": ["link"],
            "voice": [],
        }

        channel_types = supported.get(
            channel, [],
        )
        is_supported = (
            attachment_type in channel_types
        )

        return {
            "attachment_type": attachment_type,
            "url": url,
            "channel": channel,
            "supported": is_supported,
            "fallback": (
                "link"
                if not is_supported
                else None
            ),
        }

    def set_channel_limit(
        self,
        channel: str,
        limit: int,
    ) -> dict[str, Any]:
        """Kanal limitini ayarlar.

        Args:
            channel: Kanal.
            limit: Karakter limiti.

        Returns:
            Ayar bilgisi.
        """
        self._channel_limits[channel] = limit
        return {
            "channel": channel,
            "limit": limit,
        }

    @property
    def format_count(self) -> int:
        """Biçimleme sayısı."""
        return self._stats["formatted"]
