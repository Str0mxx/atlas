"""
Prompt optimizasyon modulu.

Otomatik optimizasyon, uzunluk,
netlik iyilestirme, token azaltma,
kalite artirma.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class PromptOptimizer:
    """Prompt optimizasyonu.

    Attributes:
        _optimizations: Optimizasyonlar.
        _rules: Optimizasyon kurallari.
        _stats: Istatistikler.
    """

    OPTIMIZATION_TYPES: list[str] = [
        "length_reduction",
        "clarity_improvement",
        "token_optimization",
        "structure_enhancement",
        "specificity_boost",
        "redundancy_removal",
    ]

    def __init__(self) -> None:
        """Optimizasyonu baslatir."""
        self._optimizations: list[
            dict
        ] = []
        self._rules: dict[
            str, dict
        ] = {}
        self._stats: dict[str, int] = {
            "optimizations_run": 0,
            "tokens_saved": 0,
            "prompts_improved": 0,
        }
        logger.info(
            "PromptOptimizer baslatildi"
        )

    @property
    def optimization_count(self) -> int:
        """Optimizasyon sayisi."""
        return len(self._optimizations)

    def optimize(
        self,
        prompt: str = "",
        target_tokens: int = 0,
        optimization_types: (
            list[str] | None
        ) = None,
        preserve_intent: bool = True,
    ) -> dict[str, Any]:
        """Promptu optimize eder.

        Args:
            prompt: Prompt metni.
            target_tokens: Hedef token.
            optimization_types: Tipler.
            preserve_intent: Niyet koru.

        Returns:
            Optimizasyon sonucu.
        """
        try:
            oid = f"op_{uuid4()!s:.8}"
            types = (
                optimization_types
                or self.OPTIMIZATION_TYPES
            )

            original_len = len(prompt)
            original_words = len(
                prompt.split()
            )
            optimized = prompt

            applied = []

            # Uzunluk azaltma
            if "length_reduction" in types:
                optimized, changed = (
                    self._reduce_length(
                        optimized
                    )
                )
                if changed:
                    applied.append(
                        "length_reduction"
                    )

            # Fazlalik kaldir
            if (
                "redundancy_removal"
                in types
            ):
                optimized, changed = (
                    self._remove_redundancy(
                        optimized
                    )
                )
                if changed:
                    applied.append(
                        "redundancy_removal"
                    )

            # Netlik iyilestir
            if (
                "clarity_improvement"
                in types
            ):
                optimized, changed = (
                    self._improve_clarity(
                        optimized
                    )
                )
                if changed:
                    applied.append(
                        "clarity_improvement"
                    )

            # Yapi iyilestir
            if (
                "structure_enhancement"
                in types
            ):
                optimized, changed = (
                    self._enhance_structure(
                        optimized
                    )
                )
                if changed:
                    applied.append(
                        "structure_enhancement"
                    )

            # Token hedefi
            if (
                target_tokens > 0
                and "token_optimization"
                in types
            ):
                optimized = (
                    self._fit_tokens(
                        optimized,
                        target_tokens,
                    )
                )
                applied.append(
                    "token_optimization"
                )

            new_len = len(optimized)
            new_words = len(
                optimized.split()
            )
            saved = max(
                0,
                original_words - new_words,
            )

            record = {
                "optimization_id": oid,
                "original_length": (
                    original_len
                ),
                "optimized_length": new_len,
                "original_words": (
                    original_words
                ),
                "optimized_words": (
                    new_words
                ),
                "tokens_saved": saved,
                "applied": applied,
                "optimized_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }
            self._optimizations.append(
                record
            )
            self._stats[
                "optimizations_run"
            ] += 1
            self._stats[
                "tokens_saved"
            ] += saved
            if applied:
                self._stats[
                    "prompts_improved"
                ] += 1

            return {
                "optimization_id": oid,
                "optimized_prompt": (
                    optimized
                ),
                "original_words": (
                    original_words
                ),
                "optimized_words": (
                    new_words
                ),
                "tokens_saved": saved,
                "applied": applied,
                "optimized": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "optimized": False,
                "error": str(e),
            }

    def _reduce_length(
        self,
        text: str,
    ) -> tuple[str, bool]:
        """Uzunluk azaltir."""
        original = text

        # Coklu bosluk
        import re
        text = re.sub(
            r" {2,}", " ", text
        )
        # Coklu satir sonu
        text = re.sub(
            r"\n{3,}", "\n\n", text
        )
        # Bos satirlar
        text = text.strip()

        return text, text != original

    def _remove_redundancy(
        self,
        text: str,
    ) -> tuple[str, bool]:
        """Fazlaliklari kaldirir."""
        original = text

        # Tekrarlayan cumleler
        sentences = text.split(". ")
        seen: set[str] = set()
        unique = []
        for s in sentences:
            key = s.strip().lower()
            if key and key not in seen:
                seen.add(key)
                unique.append(s)

        text = ". ".join(unique)
        return text, text != original

    def _improve_clarity(
        self,
        text: str,
    ) -> tuple[str, bool]:
        """Netligi iyilestirir."""
        original = text

        # Belirsiz ifadeleri degistir
        replacements = {
            "kind of ": "",
            "sort of ": "",
            "maybe you could ": "",
            "I think you should ": "",
            "please try to ": "",
        }
        for old, new in (
            replacements.items()
        ):
            text = text.replace(old, new)

        return text, text != original

    def _enhance_structure(
        self,
        text: str,
    ) -> tuple[str, bool]:
        """Yapiyi iyilestirir."""
        # Icerik zaten yapilandirilmis
        # mi kontrol et
        if (
            "\n-" in text
            or "\n1." in text
            or "##" in text
        ):
            return text, False

        return text, False

    def _fit_tokens(
        self,
        text: str,
        target: int,
    ) -> str:
        """Token hedefine sigdirir."""
        words = text.split()
        # ~1.3 token/kelime tahmin
        target_words = int(target / 1.3)

        if len(words) <= target_words:
            return text

        return " ".join(
            words[:target_words]
        )

    def add_rule(
        self,
        name: str = "",
        rule_type: str = "",
        pattern: str = "",
        replacement: str = "",
        description: str = "",
    ) -> dict[str, Any]:
        """Kural ekler.

        Args:
            name: Kural adi.
            rule_type: Kural tipi.
            pattern: Kalip.
            replacement: Degistirme.
            description: Aciklama.

        Returns:
            Kural bilgisi.
        """
        try:
            self._rules[name] = {
                "name": name,
                "rule_type": rule_type,
                "pattern": pattern,
                "replacement": replacement,
                "description": description,
            }
            return {
                "name": name,
                "added": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "added": False,
                "error": str(e),
            }

    def analyze_prompt(
        self,
        prompt: str = "",
    ) -> dict[str, Any]:
        """Promptu analiz eder.

        Args:
            prompt: Prompt metni.

        Returns:
            Analiz sonucu.
        """
        try:
            words = len(prompt.split())
            chars = len(prompt)
            est_tokens = int(words * 1.3)
            sentences = len(
                [
                    s
                    for s in prompt.split(".")
                    if s.strip()
                ]
            )

            # Kalite puani
            score = 1.0
            issues = []

            if words < 5:
                score -= 0.3
                issues.append("too_short")
            if words > 2000:
                score -= 0.2
                issues.append("too_long")
            if "  " in prompt:
                score -= 0.1
                issues.append(
                    "extra_spaces"
                )
            if not prompt.strip():
                score = 0.0
                issues.append("empty")

            return {
                "word_count": words,
                "char_count": chars,
                "est_tokens": est_tokens,
                "sentence_count": sentences,
                "quality_score": round(
                    max(0, score), 2
                ),
                "issues": issues,
                "analyzed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "analyzed": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir."""
        try:
            return {
                "total_optimizations": len(
                    self._optimizations
                ),
                "total_rules": len(
                    self._rules
                ),
                "stats": dict(self._stats),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
