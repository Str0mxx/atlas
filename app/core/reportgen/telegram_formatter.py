"""ATLAS Telegram Biçimleyici modülü.

Mesaj biçimlendirme, karakter limiti,
emoji kullanımı, inline butonlar,
çoklu mesaj bölme.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class TelegramFormatter:
    """Telegram biçimleyici.

    Raporları Telegram formatına dönüştürür.

    Attributes:
        _messages: Mesaj geçmişi.
    """

    TELEGRAM_MAX_LENGTH = 4096

    def __init__(
        self,
        use_emoji: bool = True,
    ) -> None:
        """Biçimleyiciyi başlatır.

        Args:
            use_emoji: Emoji kullan.
        """
        self._messages: list[
            dict[str, Any]
        ] = []
        self._use_emoji = use_emoji
        self._counter = 0
        self._stats = {
            "messages_formatted": 0,
            "messages_split": 0,
            "buttons_added": 0,
        }

        logger.info(
            "TelegramFormatter baslatildi",
        )

    def format_report(
        self,
        title: str,
        sections: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Raporu biçimlendirir.

        Args:
            title: Başlık.
            sections: Bölümler.

        Returns:
            Biçimlendirme bilgisi.
        """
        self._counter += 1
        mid = f"msg_{self._counter}"

        prefix = "\U0001f4ca " if (
            self._use_emoji
        ) else ""

        parts = [
            f"{prefix}<b>{title}</b>\n",
        ]
        for section in sections:
            sec_title = section.get("title", "")
            sec_content = section.get(
                "content", "",
            )
            emoji = self._section_emoji(
                sec_title,
            )
            parts.append(
                f"\n{emoji}<b>{sec_title}</b>\n"
                f"{sec_content}",
            )

        text = "\n".join(parts)

        message = {
            "message_id": mid,
            "text": text,
            "parse_mode": "HTML",
            "length": len(text),
            "needs_split": (
                len(text)
                > self.TELEGRAM_MAX_LENGTH
            ),
            "created_at": time.time(),
        }
        self._messages.append(message)
        self._stats[
            "messages_formatted"
        ] += 1

        return {
            "message_id": mid,
            "text": text,
            "parse_mode": "HTML",
            "length": len(text),
            "needs_split": message[
                "needs_split"
            ],
            "formatted": True,
        }

    def _section_emoji(
        self,
        title: str,
    ) -> str:
        """Bölüm emojisi seçer."""
        if not self._use_emoji:
            return ""

        title_lower = title.lower()
        emoji_map = {
            "summary": "\U0001f4dd ",
            "risk": "\u26a0\ufe0f ",
            "opportunity": "\U0001f31f ",
            "action": "\u2705 ",
            "comparison": "\U0001f4ca ",
            "insight": "\U0001f4a1 ",
            "warning": "\u26a0\ufe0f ",
        }
        for key, emoji in emoji_map.items():
            if key in title_lower:
                return emoji
        return "\U0001f539 "

    def split_message(
        self,
        text: str,
        max_length: int | None = None,
    ) -> dict[str, Any]:
        """Mesajı böler.

        Args:
            text: Metin.
            max_length: Maks uzunluk.

        Returns:
            Bölme bilgisi.
        """
        limit = (
            max_length
            or self.TELEGRAM_MAX_LENGTH
        )

        if len(text) <= limit:
            return {
                "parts": [text],
                "count": 1,
                "split": False,
            }

        parts = []
        remaining = text
        while remaining:
            if len(remaining) <= limit:
                parts.append(remaining)
                break

            # Satır sonundan böl
            split_pos = remaining.rfind(
                "\n", 0, limit,
            )
            if split_pos == -1:
                split_pos = limit

            parts.append(
                remaining[:split_pos],
            )
            remaining = remaining[
                split_pos:
            ].lstrip("\n")

        self._stats["messages_split"] += (
            len(parts) - 1
        )

        return {
            "parts": parts,
            "count": len(parts),
            "split": len(parts) > 1,
        }

    def add_inline_buttons(
        self,
        message_id: str,
        buttons: list[dict[str, str]],
    ) -> dict[str, Any]:
        """Inline buton ekler.

        Args:
            message_id: Mesaj ID.
            buttons: Buton listesi.

        Returns:
            Ekleme bilgisi.
        """
        keyboard = []
        row = []
        for btn in buttons:
            row.append({
                "text": btn.get("text", ""),
                "callback_data": btn.get(
                    "callback", "",
                ),
            })
            if len(row) >= 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)

        self._stats["buttons_added"] += len(
            buttons,
        )

        return {
            "message_id": message_id,
            "inline_keyboard": keyboard,
            "button_count": len(buttons),
            "added": True,
        }

    def format_summary(
        self,
        tldr: str,
        highlights: list[str],
        actions: list[str],
    ) -> dict[str, Any]:
        """Özet biçimlendirir.

        Args:
            tldr: TL;DR.
            highlights: Öne çıkanlar.
            actions: Aksiyonlar.

        Returns:
            Biçimlendirme bilgisi.
        """
        parts = []

        if self._use_emoji:
            parts.append(
                "\U0001f4dd <b>TL;DR</b>",
            )
        else:
            parts.append("<b>TL;DR</b>")
        parts.append(tldr)

        if highlights:
            parts.append(
                "\n\U0001f31f <b>Highlights</b>"
                if self._use_emoji
                else "\n<b>Highlights</b>",
            )
            for h in highlights:
                parts.append(f"• {h}")

        if actions:
            parts.append(
                "\n\u2705 <b>Actions</b>"
                if self._use_emoji
                else "\n<b>Actions</b>",
            )
            for a in actions:
                parts.append(f"→ {a}")

        text = "\n".join(parts)
        self._stats[
            "messages_formatted"
        ] += 1

        return {
            "text": text,
            "parse_mode": "HTML",
            "length": len(text),
        }

    def get_messages(
        self,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Mesajları getirir.

        Args:
            limit: Maks kayıt.

        Returns:
            Mesaj listesi.
        """
        return list(
            self._messages[-limit:],
        )

    @property
    def message_count(self) -> int:
        """Mesaj sayısı."""
        return self._stats[
            "messages_formatted"
        ]

    @property
    def button_count(self) -> int:
        """Buton sayısı."""
        return self._stats["buttons_added"]
