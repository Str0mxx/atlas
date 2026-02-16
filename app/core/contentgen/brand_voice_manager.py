"""ATLAS Marka Sesi Yöneticisi modülü.

Ses tanımı, tutarlılık kontrolü,
ton kılavuzları, stil zorlama,
eğitim.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class BrandVoiceManager:
    """Marka sesi yöneticisi.

    Marka sesini tanımlar ve korur.

    Attributes:
        _voices: Marka sesi kayıtları.
    """

    def __init__(self) -> None:
        """Yöneticiyi başlatır."""
        self._voices: dict[
            str, dict[str, Any]
        ] = {}
        self._counter = 0
        self._stats = {
            "voices_defined": 0,
            "consistency_checks": 0,
            "trainings_done": 0,
        }

        logger.info(
            "BrandVoiceManager baslatildi",
        )

    def define_voice(
        self,
        brand_name: str,
        tone: str = "professional",
        personality: list[str]
        | None = None,
        do_words: list[str]
        | None = None,
        dont_words: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Marka sesi tanımlar.

        Args:
            brand_name: Marka adı.
            tone: Ton.
            personality: Kişilik özellikleri.
            do_words: Kullanılacak kelimeler.
            dont_words: Kaçınılacak kelimeler.

        Returns:
            Ses tanım bilgisi.
        """
        self._counter += 1
        vid = f"voice_{self._counter}"

        personality = personality or []
        do_words = do_words or []
        dont_words = dont_words or []

        voice = {
            "voice_id": vid,
            "brand_name": brand_name,
            "tone": tone,
            "personality": personality,
            "do_words": do_words,
            "dont_words": dont_words,
            "timestamp": time.time(),
        }
        self._voices[vid] = voice
        self._stats[
            "voices_defined"
        ] += 1

        return {
            "voice_id": vid,
            "brand_name": brand_name,
            "tone": tone,
            "personality_count": len(
                personality,
            ),
            "defined": True,
        }

    def check_consistency(
        self,
        voice_id: str,
        text: str,
    ) -> dict[str, Any]:
        """Tutarlılık kontrol eder.

        Args:
            voice_id: Ses ID.
            text: Metin.

        Returns:
            Tutarlılık bilgisi.
        """
        if voice_id not in self._voices:
            return {
                "voice_id": voice_id,
                "consistent": False,
                "reason": "Voice not found",
            }

        voice = self._voices[voice_id]
        lower = text.lower()
        issues = []

        # Kaçınılacak kelime kontrolü
        for word in voice["dont_words"]:
            if word.lower() in lower:
                issues.append(
                    f"Contains avoided word: "
                    f"{word}",
                )

        # Kullanılacak kelime kontrolü
        do_found = sum(
            1 for w in voice["do_words"]
            if w.lower() in lower
        )

        score = 100
        score -= len(issues) * 20
        if (
            voice["do_words"]
            and do_found == 0
        ):
            score -= 15
            issues.append(
                "No preferred words found",
            )
        score = max(score, 0)

        self._stats[
            "consistency_checks"
        ] += 1

        return {
            "voice_id": voice_id,
            "brand_name": voice[
                "brand_name"
            ],
            "consistency_score": score,
            "consistent": score >= 60,
            "issues": issues,
            "issue_count": len(issues),
        }

    def get_tone_guidelines(
        self,
        voice_id: str,
    ) -> dict[str, Any]:
        """Ton kılavuzlarını döndürür.

        Args:
            voice_id: Ses ID.

        Returns:
            Kılavuz bilgisi.
        """
        if voice_id not in self._voices:
            return {
                "voice_id": voice_id,
                "found": False,
            }

        voice = self._voices[voice_id]
        guidelines = []

        tone = voice["tone"]
        if tone == "professional":
            guidelines = [
                "Use formal language",
                "Avoid slang",
                "Be precise and clear",
            ]
        elif tone == "casual":
            guidelines = [
                "Use conversational tone",
                "Include contractions",
                "Be friendly and warm",
            ]
        elif tone == "humorous":
            guidelines = [
                "Use wit, not sarcasm",
                "Keep jokes relevant",
                "Stay positive",
            ]
        else:
            guidelines = [
                f"Follow {tone} tone",
                "Be consistent",
                "Match audience expectations",
            ]

        return {
            "voice_id": voice_id,
            "tone": tone,
            "guidelines": guidelines,
            "do_words": voice["do_words"],
            "dont_words": voice[
                "dont_words"
            ],
            "found": True,
        }

    def enforce_style(
        self,
        voice_id: str,
        text: str,
    ) -> dict[str, Any]:
        """Stil zorlar.

        Args:
            voice_id: Ses ID.
            text: Metin.

        Returns:
            Zorlama bilgisi.
        """
        if voice_id not in self._voices:
            return {
                "voice_id": voice_id,
                "enforced": False,
            }

        voice = self._voices[voice_id]
        modified = text
        changes = []

        # Kaçınılacak kelimeleri değiştir
        for word in voice["dont_words"]:
            if word.lower() in modified.lower():
                modified = modified.replace(
                    word, "[REMOVED]",
                )
                changes.append(
                    f"Removed: {word}",
                )

        return {
            "voice_id": voice_id,
            "original": text,
            "modified": modified,
            "changes": changes,
            "change_count": len(changes),
            "enforced": True,
        }

    def train(
        self,
        voice_id: str,
        examples: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Eğitim yapar.

        Args:
            voice_id: Ses ID.
            examples: Örnek metinler.

        Returns:
            Eğitim bilgisi.
        """
        examples = examples or []

        if voice_id not in self._voices:
            return {
                "voice_id": voice_id,
                "trained": False,
            }

        # Örneklerden kelime çıkarımı
        words_found: dict[str, int] = {}
        for ex in examples:
            for word in ex.lower().split():
                if len(word) > 3:
                    words_found[word] = (
                        words_found.get(
                            word, 0,
                        ) + 1
                    )

        frequent = sorted(
            words_found.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:5]

        self._stats[
            "trainings_done"
        ] += 1

        return {
            "voice_id": voice_id,
            "examples_used": len(examples),
            "frequent_words": [
                w for w, _ in frequent
            ],
            "trained": True,
        }

    def get_voice(
        self,
        voice_id: str,
    ) -> dict[str, Any] | None:
        """Ses döndürür."""
        return self._voices.get(voice_id)

    @property
    def voice_count(self) -> int:
        """Ses sayısı."""
        return self._stats[
            "voices_defined"
        ]

    @property
    def check_count(self) -> int:
        """Kontrol sayısı."""
        return self._stats[
            "consistency_checks"
        ]
