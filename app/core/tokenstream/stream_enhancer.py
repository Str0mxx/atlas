"""Akim ve teslimat iyilestirmeleri.

Reasoning/answer serit ayirimi,
native streaming ve sticky threading.
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

_THINKING_RE = re.compile(
    r"<thinking>(.*?)</thinking>",
    re.DOTALL,
)


class StreamEnhancer:
    """Akim ve teslimat iyilestirmeleri.

    Attributes:
        _lane_buffers: Serit tamponlari.
        _block_streaming_default: Varsayilan blok akis.
        _partial_active: Kismi aktif durumu.
    """

    def __init__(self) -> None:
        """StreamEnhancer baslatir."""
        self._lane_buffers: dict[
            str, list[str]
        ] = {
            "reasoning": [],
            "answer": [],
        }
        self._block_streaming_default = True
        self._partial_active = False

    def separate_reasoning_lanes(
        self,
        content: str,
    ) -> dict[str, str]:
        """Reasoning/answer seritlerini ayirir.

        <thinking> etiketleri reasoning seridine,
        geri kalani answer seridine gider.

        Args:
            content: Ham icerik.

        Returns:
            {"reasoning": ..., "answer": ...}
        """
        thinking_parts = _THINKING_RE.findall(
            content,
        )
        reasoning = "\n".join(thinking_parts)

        answer = _THINKING_RE.sub("", content)
        answer = answer.strip()

        return {
            "reasoning": reasoning,
            "answer": answer,
        }

    @staticmethod
    def native_single_message_stream(
        chunks: list[str],
    ) -> str:
        """Slack native tek mesaj akisi.

        Tum parcalari birlestirir
        (ayni mesaji gunceller).

        Args:
            chunks: Akim parcalari.

        Returns:
            Birlesmis mesaj.
        """
        return "".join(chunks)

    def honor_block_streaming_default(
        self,
        config: dict[str, Any],
    ) -> bool:
        """blockStreamingDefault config'ini uygular.

        Args:
            config: Yapilandirma.

        Returns:
            Block streaming aktif ise True.
        """
        val = config.get(
            "blockStreamingDefault",
            True,
        )
        self._block_streaming_default = bool(val)
        return self._block_streaming_default

    def keep_partial_during_reasoning(
        self,
        is_reasoning: bool,
    ) -> bool:
        """Reasoning sirasinda kismi aktif tutar.

        Args:
            is_reasoning: Reasoning asamasinda mi.

        Returns:
            Kismi aktif durumu.
        """
        if is_reasoning:
            self._partial_active = True
        return self._partial_active

    @staticmethod
    def sticky_reply_threading(
        chunks: list[str],
        thread_id: str,
    ) -> list[dict[str, str]]:
        """Split chunk'lar arasinda sticky threading.

        Tum parcalar ayni thread_id'yi korur.

        Args:
            chunks: Mesaj parcalari.
            thread_id: Is parcacigi kimlik.

        Returns:
            Thread bilgili parcalar.
        """
        return [
            {
                "content": chunk,
                "thread_id": thread_id,
                "chunk_index": str(i),
            }
            for i, chunk in enumerate(chunks)
        ]

    def reset_lanes(self) -> None:
        """Serit tamponlarini sifirlar."""
        self._lane_buffers = {
            "reasoning": [],
            "answer": [],
        }
        self._partial_active = False
