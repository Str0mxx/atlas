"""Mesaj ozetleyici.

Konusma ozeti, anahtar nokta cikarma
ve kademeli ozetleme.
"""

import logging
import time
from typing import Any

from app.models.contextwindow_models import (
    MessagePriority,
    SummaryLevel,
    SummaryResult,
)

logger = logging.getLogger(__name__)

# Varsayilan ayarlar
_MAX_SUMMARIES = 5000
_MAX_KEY_POINTS = 20
_BRIEF_RATIO = 0.15
_STANDARD_RATIO = 0.30
_DETAILED_RATIO = 0.50


class MessageSummarizer:
    """Mesaj ozetleyici.

    Konusma ozeti, anahtar nokta cikarma
    ve kademeli ozetleme.

    Attributes:
        _summaries: Ozet kayitlari.
        _templates: Ozet sablonlari.
    """

    def __init__(
        self,
        default_level: SummaryLevel = (
            SummaryLevel.STANDARD
        ),
    ) -> None:
        """MessageSummarizer baslatir.

        Args:
            default_level: Varsayilan seviye.
        """
        self._default_level: SummaryLevel = (
            default_level
        )
        self._summaries: dict[
            str, SummaryResult
        ] = {}
        self._templates: dict[
            str, str
        ] = {}
        self._total_summarized: int = 0
        self._total_tokens_saved: int = 0

        logger.info(
            "MessageSummarizer baslatildi",
        )

    # ---- Ozetleme ----

    def summarize(
        self,
        messages: list[dict[str, str]],
        level: SummaryLevel | None = None,
        max_tokens: int = 0,
    ) -> SummaryResult:
        """Mesajlari ozetler.

        Args:
            messages: Mesaj listesi.
            level: Ozet seviyesi.
            max_tokens: Maks token siniri.

        Returns:
            Ozet sonucu.
        """
        lvl = level or self._default_level
        ratio = self._get_ratio(lvl)

        # Orijinal token sayimi
        original_tokens = sum(
            self._estimate_tokens(
                m.get("content", ""),
            )
            for m in messages
        )

        # Hedef token
        target = (
            max_tokens
            if max_tokens > 0
            else int(original_tokens * ratio)
        )

        # Anahtar noktalar cikar
        key_points = self._extract_key_points(
            messages,
        )

        # Ozet olustur
        summary_text = self._build_summary(
            messages, key_points, target,
        )

        summary_tokens = (
            self._estimate_tokens(
                summary_text,
            )
        )

        comp_ratio = (
            summary_tokens
            / original_tokens
            if original_tokens > 0
            else 0.0
        )

        result = SummaryResult(
            original_tokens=original_tokens,
            summary_tokens=summary_tokens,
            compression_ratio=comp_ratio,
            summary_text=summary_text,
            key_points=key_points,
            preserved_count=len(key_points),
            dropped_count=max(
                0,
                len(messages) - len(key_points),
            ),
            level=lvl,
        )

        self._summaries[
            result.summary_id
        ] = result
        self._total_summarized += 1
        self._total_tokens_saved += max(
            0,
            original_tokens - summary_tokens,
        )

        if len(self._summaries) > _MAX_SUMMARIES:
            oldest = sorted(
                self._summaries.keys(),
            )[:100]
            for k in oldest:
                del self._summaries[k]

        return result

    def summarize_progressive(
        self,
        messages: list[dict[str, str]],
        rounds: int = 2,
    ) -> SummaryResult:
        """Kademeli ozetleme yapar.

        Args:
            messages: Mesaj listesi.
            rounds: Ozet turu sayisi.

        Returns:
            Son ozet sonucu.
        """
        rounds = max(1, min(rounds, 5))
        current = list(messages)

        result = self.summarize(
            current, SummaryLevel.DETAILED,
        )

        for _ in range(rounds - 1):
            if not result.summary_text:
                break

            current = [
                {
                    "role": "summary",
                    "content": (
                        result.summary_text
                    ),
                },
            ]
            result = self.summarize(
                current, SummaryLevel.BRIEF,
            )

        return result

    def summarize_by_role(
        self,
        messages: list[dict[str, str]],
    ) -> dict[str, SummaryResult]:
        """Role gore ozetler.

        Args:
            messages: Mesaj listesi.

        Returns:
            Rol-ozet eslesmesi.
        """
        by_role: dict[
            str, list[dict[str, str]]
        ] = {}

        for m in messages:
            role = m.get("role", "unknown")
            if role not in by_role:
                by_role[role] = []
            by_role[role].append(m)

        results: dict[
            str, SummaryResult
        ] = {}
        for role, role_msgs in by_role.items():
            results[role] = self.summarize(
                role_msgs,
            )

        return results

    # ---- Anahtar Nokta ----

    def extract_key_points(
        self,
        messages: list[dict[str, str]],
        max_points: int = 10,
    ) -> list[str]:
        """Anahtar noktalari cikarir.

        Args:
            messages: Mesaj listesi.
            max_points: Maks nokta sayisi.

        Returns:
            Anahtar noktalar.
        """
        points = self._extract_key_points(
            messages,
        )
        return points[:min(
            max_points, _MAX_KEY_POINTS,
        )]

    def _extract_key_points(
        self,
        messages: list[dict[str, str]],
    ) -> list[str]:
        """Anahtar nokta cikarma mantigi.

        Args:
            messages: Mesaj listesi.

        Returns:
            Anahtar noktalar.
        """
        points: list[str] = []

        for m in messages:
            content = m.get("content", "")
            if not content:
                continue

            role = m.get("role", "")

            # Cumlelere ayir
            sentences = self._split_sentences(
                content,
            )

            for s in sentences:
                s = s.strip()
                if not s or len(s) < 10:
                    continue

                # Onemli cumle tespiti
                if self._is_important(
                    s, role,
                ):
                    prefix = (
                        f"[{role}] "
                        if role
                        else ""
                    )
                    point = f"{prefix}{s}"
                    if (
                        point not in points
                        and len(points)
                        < _MAX_KEY_POINTS
                    ):
                        points.append(point)

        return points

    def _is_important(
        self,
        sentence: str,
        role: str,
    ) -> bool:
        """Cumlenin onemini belirler.

        Args:
            sentence: Cumle.
            role: Rol.

        Returns:
            Onemli ise True.
        """
        lower = sentence.lower()

        # Sistem mesajlari her zaman onemli
        if role == "system":
            return True

        # Soru isaretli cumleler
        if "?" in sentence:
            return True

        # Anahtar kelimeler
        keywords = [
            "important", "onemli",
            "must", "gerekli",
            "error", "hata",
            "warning", "uyari",
            "action", "aksiyon",
            "decision", "karar",
            "result", "sonuc",
            "todo", "yapilacak",
            "deadline", "son tarih",
            "please", "lutfen",
            "critical", "kritik",
        ]

        return any(
            kw in lower for kw in keywords
        )

    # ---- Sablon ----

    def add_template(
        self,
        name: str,
        template: str,
    ) -> bool:
        """Ozet sablonu ekler.

        Args:
            name: Sablon adi.
            template: Sablon metni.

        Returns:
            Eklendi ise True.
        """
        if not name or not template:
            return False

        self._templates[name] = template
        return True

    def get_template(
        self, name: str,
    ) -> str | None:
        """Sablon dondurur.

        Args:
            name: Sablon adi.

        Returns:
            Sablon veya None.
        """
        return self._templates.get(name)

    def remove_template(
        self, name: str,
    ) -> bool:
        """Sablon siler.

        Args:
            name: Sablon adi.

        Returns:
            Silindi ise True.
        """
        if name not in self._templates:
            return False
        del self._templates[name]
        return True

    def list_templates(
        self,
    ) -> dict[str, str]:
        """Sablonlari dondurur.

        Returns:
            Sablon sozlugu.
        """
        return dict(self._templates)

    # ---- Ozet Yonetimi ----

    def get_summary(
        self, summary_id: str,
    ) -> SummaryResult | None:
        """Ozet dondurur.

        Args:
            summary_id: Ozet ID.

        Returns:
            Ozet veya None.
        """
        return self._summaries.get(summary_id)

    def list_summaries(
        self, limit: int = 50,
    ) -> list[SummaryResult]:
        """Ozetleri listeler.

        Args:
            limit: Maks sonuc.

        Returns:
            Ozet listesi.
        """
        items = list(
            self._summaries.values(),
        )
        return items[-limit:]

    def clear_summaries(self) -> int:
        """Ozetleri temizler.

        Returns:
            Temizlenen sayi.
        """
        count = len(self._summaries)
        self._summaries = {}
        return count

    # ---- Yardimci ----

    def _build_summary(
        self,
        messages: list[dict[str, str]],
        key_points: list[str],
        target_tokens: int,
    ) -> str:
        """Ozet metni olusturur.

        Args:
            messages: Mesaj listesi.
            key_points: Anahtar noktalar.
            target_tokens: Hedef token.

        Returns:
            Ozet metni.
        """
        parts: list[str] = []

        # Anahtar noktalar
        if key_points:
            parts.append(
                "Key points: "
                + " | ".join(key_points),
            )

        # Mesaj ozetleri
        for m in messages:
            content = m.get("content", "")
            role = m.get("role", "")
            if not content:
                continue

            # Kisa ozet
            short = content[:200]
            if len(content) > 200:
                short += "..."

            parts.append(
                f"[{role}] {short}",
            )

        text = "\n".join(parts)

        # Token limitine kir
        while (
            self._estimate_tokens(text)
            > target_tokens
            and len(parts) > 1
        ):
            parts.pop()
            text = "\n".join(parts)

        return text

    @staticmethod
    def _split_sentences(
        text: str,
    ) -> list[str]:
        """Metni cumlelere ayirir.

        Args:
            text: Metin.

        Returns:
            Cumle listesi.
        """
        separators = [".", "!", "?", "\n"]
        sentences: list[str] = [text]

        for sep in separators:
            new_sentences: list[str] = []
            for s in sentences:
                parts = s.split(sep)
                new_sentences.extend(parts)
            sentences = new_sentences

        return [
            s.strip()
            for s in sentences
            if s.strip()
        ]

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Token tahmin eder.

        Args:
            text: Metin.

        Returns:
            Tahmini token.
        """
        if not text:
            return 0
        return max(1, len(text) // 4)

    @staticmethod
    def _get_ratio(
        level: SummaryLevel,
    ) -> float:
        """Seviyeye gore oran dondurur.

        Args:
            level: Ozet seviyesi.

        Returns:
            Sikistirma orani.
        """
        if level == SummaryLevel.BRIEF:
            return _BRIEF_RATIO
        if level == SummaryLevel.DETAILED:
            return _DETAILED_RATIO
        return _STANDARD_RATIO

    # ---- Istatistikler ----

    def get_stats(
        self,
    ) -> dict[str, Any]:
        """Istatistikleri dondurur.

        Returns:
            Istatistik sozlugu.
        """
        return {
            "default_level": (
                self._default_level.value
            ),
            "total_summaries": len(
                self._summaries,
            ),
            "total_summarized": (
                self._total_summarized
            ),
            "total_tokens_saved": (
                self._total_tokens_saved
            ),
            "templates": len(
                self._templates,
            ),
        }
