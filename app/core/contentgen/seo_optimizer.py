"""ATLAS SEO Optimizasyonu modülü.

Anahtar kelime entegrasyonu, meta etiketler,
okunabilirlik, yapı optimizasyonu,
puan hesaplama.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class SEOOptimizer:
    """SEO optimizasyonu.

    İçerik SEO optimizasyonu yapar.

    Attributes:
        _analyses: Analiz kayıtları.
    """

    def __init__(self) -> None:
        """Optimize ediciyi başlatır."""
        self._analyses: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "optimizations_done": 0,
            "meta_tags_created": 0,
            "scores_calculated": 0,
        }

        logger.info(
            "SEOOptimizer baslatildi",
        )

    def integrate_keywords(
        self,
        text: str,
        keywords: list[str]
        | None = None,
        density_target: float = 2.0,
    ) -> dict[str, Any]:
        """Anahtar kelime entegre eder.

        Args:
            text: Metin.
            keywords: Anahtar kelimeler.
            density_target: Hedef yoğunluk.

        Returns:
            Entegrasyon bilgisi.
        """
        keywords = keywords or []
        lower = text.lower()
        words = lower.split()
        total = max(len(words), 1)

        present = []
        missing = []
        for kw in keywords:
            if kw.lower() in lower:
                count = lower.count(kw.lower())
                density = round(
                    count / total * 100, 2,
                )
                present.append({
                    "keyword": kw,
                    "count": count,
                    "density": density,
                    "optimal": (
                        density <= density_target
                    ),
                })
            else:
                missing.append(kw)

        self._stats[
            "optimizations_done"
        ] += 1

        return {
            "present": present,
            "missing": missing,
            "present_count": len(present),
            "missing_count": len(missing),
            "density_target": density_target,
        }

    def generate_meta_tags(
        self,
        title: str,
        description: str = "",
        keywords: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Meta etiket üretir.

        Args:
            title: Başlık.
            description: Açıklama.
            keywords: Anahtar kelimeler.

        Returns:
            Meta etiket bilgisi.
        """
        keywords = keywords or []

        meta_title = title[:60]
        meta_desc = (
            description[:160]
            if description
            else f"{title} - Learn more."
        )
        meta_kw = ", ".join(keywords[:10])

        issues = []
        if len(title) > 60:
            issues.append(
                "Title exceeds 60 chars",
            )
        if (
            description
            and len(description) > 160
        ):
            issues.append(
                "Description exceeds 160 chars",
            )
        if not keywords:
            issues.append(
                "No keywords specified",
            )

        self._stats[
            "meta_tags_created"
        ] += 1

        return {
            "meta_title": meta_title,
            "meta_description": meta_desc,
            "meta_keywords": meta_kw,
            "issues": issues,
            "issue_count": len(issues),
        }

    def check_readability(
        self,
        text: str,
    ) -> dict[str, Any]:
        """Okunabilirlik kontrol eder.

        Args:
            text: Metin.

        Returns:
            Okunabilirlik bilgisi.
        """
        words = text.split()
        sentences = [
            s.strip()
            for s in text.replace(
                "!", ".",
            ).replace(
                "?", ".",
            ).split(".")
            if s.strip()
        ]

        word_count = len(words)
        sentence_count = max(
            len(sentences), 1,
        )
        avg_sentence_length = round(
            word_count / sentence_count, 1,
        )

        long_words = sum(
            1 for w in words if len(w) > 10
        )
        long_pct = round(
            long_words
            / max(word_count, 1) * 100, 1,
        )

        # Basit okunabilirlik puanı
        score = 100
        if avg_sentence_length > 20:
            score -= 20
        if avg_sentence_length > 30:
            score -= 20
        if long_pct > 20:
            score -= 15
        if word_count < 50:
            score -= 10
        score = max(score, 10)

        level = (
            "easy" if score >= 80
            else "moderate" if score >= 50
            else "difficult"
        )

        return {
            "word_count": word_count,
            "sentence_count": sentence_count,
            "avg_sentence_length": (
                avg_sentence_length
            ),
            "long_word_pct": long_pct,
            "readability_score": score,
            "level": level,
        }

    def optimize_structure(
        self,
        text: str,
        has_headings: bool = False,
        has_lists: bool = False,
        has_images: bool = False,
    ) -> dict[str, Any]:
        """Yapı optimizasyonu yapar.

        Args:
            text: Metin.
            has_headings: Başlık var mı.
            has_lists: Liste var mı.
            has_images: Görsel var mı.

        Returns:
            Yapı bilgisi.
        """
        suggestions = []

        if not has_headings:
            suggestions.append(
                "Add headings (H2, H3) "
                "for structure",
            )
        if not has_lists:
            suggestions.append(
                "Use bullet or numbered "
                "lists",
            )
        if not has_images:
            suggestions.append(
                "Include relevant images "
                "with alt text",
            )

        words = len(text.split())
        if words < 300:
            suggestions.append(
                "Increase content length "
                "to 300+ words",
            )
        if words > 2000:
            suggestions.append(
                "Consider splitting into "
                "multiple pages",
            )

        score = 100
        score -= len(suggestions) * 15
        score = max(score, 10)

        return {
            "word_count": words,
            "has_headings": has_headings,
            "has_lists": has_lists,
            "has_images": has_images,
            "suggestions": suggestions,
            "structure_score": score,
        }

    def calculate_score(
        self,
        text: str,
        keywords: list[str]
        | None = None,
        has_meta: bool = False,
        has_headings: bool = False,
    ) -> dict[str, Any]:
        """SEO puanı hesaplar.

        Args:
            text: Metin.
            keywords: Anahtar kelimeler.
            has_meta: Meta var mı.
            has_headings: Başlık var mı.

        Returns:
            Puan bilgisi.
        """
        keywords = keywords or []
        score = 0.0

        # Kelime sayısı puanı
        words = len(text.split())
        if words >= 300:
            score += 20
        elif words >= 100:
            score += 10

        # Anahtar kelime puanı
        lower = text.lower()
        found = sum(
            1 for kw in keywords
            if kw.lower() in lower
        )
        if keywords:
            kw_pct = found / len(keywords)
            score += kw_pct * 30

        # Meta puanı
        if has_meta:
            score += 20

        # Başlık puanı
        if has_headings:
            score += 15

        # Uzunluk bonusu
        if words >= 1000:
            score += 15

        score = round(
            min(score, 100), 1,
        )

        level = (
            "excellent" if score >= 80
            else "good" if score >= 60
            else "average" if score >= 40
            else "poor"
        )

        self._stats[
            "scores_calculated"
        ] += 1

        return {
            "seo_score": score,
            "level": level,
            "word_count": words,
            "keywords_found": found,
            "keywords_total": len(keywords),
            "has_meta": has_meta,
            "has_headings": has_headings,
        }

    @property
    def optimization_count(self) -> int:
        """Optimizasyon sayısı."""
        return self._stats[
            "optimizations_done"
        ]

    @property
    def score_count(self) -> int:
        """Puan sayısı."""
        return self._stats[
            "scores_calculated"
        ]
