"""Baglam sikistirma ve yonetim iyilestirmeleri.

Bootstrap cap yukseltme, truncation gorunurlugu,
tool result sikistirma ve otomatik sayfalama.
"""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class ContextCompactor:
    """Baglam sikistirma ve yonetim iyilestirmeleri.

    Attributes:
        BOOTSTRAP_CAP: Yeni bootstrap limiti.
        OLD_BOOTSTRAP_CAP: Eski bootstrap limiti.
        _total_cap: Aktif limit.
        _truncation_log: Kesme kayitlari.
    """

    BOOTSTRAP_CAP = 150_000
    OLD_BOOTSTRAP_CAP = 24_000

    def __init__(self) -> None:
        """ContextCompactor baslatir."""
        self._total_cap = self.BOOTSTRAP_CAP
        self._truncation_log: list[
            dict[str, Any]
        ] = []

    def raise_bootstrap_cap(self) -> int:
        """Bootstrap prompt cap'i yukseltir.

        24,000 -> 150,000 karakter.

        Returns:
            Yeni cap degeri.
        """
        self._total_cap = self.BOOTSTRAP_CAP
        return self.BOOTSTRAP_CAP

    def get_truncation_visibility(
        self,
        messages: list[dict[str, Any]],
        cap: int = 0,
    ) -> dict[str, Any]:
        """Total-cap + truncation gorunurlugu saglar.

        Args:
            messages: Mesaj listesi.
            cap: Karakter limiti.

        Returns:
            Truncation bilgisi.
        """
        effective_cap = cap or self._total_cap
        total_chars = sum(
            len(str(m.get("content", "")))
            for m in messages
        )

        truncated = total_chars > effective_cap
        kept_count = 0
        truncated_count = 0
        running = 0

        for m in reversed(messages):
            size = len(str(m.get("content", "")))
            if running + size <= effective_cap:
                running += size
                kept_count += 1
            else:
                truncated_count += 1

        ratio = 0.0
        if total_chars > 0:
            ratio = (
                truncated_count / len(messages)
                if messages
                else 0.0
            )

        return {
            "total_chars": total_chars,
            "cap": effective_cap,
            "truncated": truncated,
            "truncated_count": truncated_count,
            "kept_count": kept_count,
            "truncation_ratio": round(ratio, 4),
        }

    def compact_tool_results(
        self,
        tool_results: list[dict[str, Any]],
        budget: int,
    ) -> list[dict[str, Any]]:
        """Pre-model-call tool result sikistirmasi.

        Butceyi asan sonuclari ozetler.

        Args:
            tool_results: Arac sonuclari.
            budget: Karakter butcesi.

        Returns:
            Sikistirilmis sonuclar.
        """
        if not tool_results:
            return []

        total = sum(
            len(str(r.get("output", "")))
            for r in tool_results
        )
        if total <= budget:
            return list(tool_results)

        per_item = max(
            budget // len(tool_results), 100,
        )

        compacted: list[dict[str, Any]] = []
        for r in tool_results:
            output = str(r.get("output", ""))
            if len(output) > per_item:
                truncated_output = (
                    output[:per_item - 20]
                    + chr(10) + "... ["
                    + str(len(output) - per_item)
                    + " karakter kesildi]"
                )
                entry = dict(r)
                entry["output"] = truncated_output
                compacted.append(entry)
            else:
                compacted.append(dict(r))

        return compacted

    def auto_page_read(
        self,
        content: str,
        context_budget: int,
    ) -> list[str]:
        """Read tool icin otomatik sayfalama.

        Icerigi satir sinirlarina gore
        sayfalara boler.

        Args:
            content: Icerik metni.
            context_budget: Mevcut butce.

        Returns:
            Sayfa listesi.
        """
        if not content:
            return []

        if len(content) <= context_budget:
            return [content]

        page_size = max(context_budget, 1000)
        pages: list[str] = []
        lines = content.split("\n")
        current_page: list[str] = []
        current_size = 0

        for line in lines:
            line_size = len(line) + 1
            if (
                current_size + line_size
                > page_size
                and current_page
            ):
                pages.append(
                    "\n".join(current_page),
                )
                current_page = []
                current_size = 0

            current_page.append(line)
            current_size += line_size

        if current_page:
            pages.append(
                "\n".join(current_page),
            )

        return pages

    @staticmethod
    def compact_path(path: str) -> str:
        """Path'i ~ prefiksi ile kisaltir.

        Args:
            path: Dosya yolu.

        Returns:
            Kisaltilmis yol.
        """
        if not path:
            return path
        home = os.path.expanduser("~")
        if path.startswith(home):
            return "~" + path[len(home):]
        return path
