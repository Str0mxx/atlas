"""ATLAS Yerellestirme Kalite Kontrolu modulu.

Ceviri kalitesi, tutarlilik kontrolu,
eksik ceviri tespiti, format dogrulama
ve kulturel uygunluk.
"""

import logging
import re
from typing import Any

from app.models.localization import QualityLevel

logger = logging.getLogger(__name__)


class LocalizationQualityChecker:
    """Yerellestirme kalite kontrolu.

    Cevirilerin kalitesini kontrol eder
    ve iyilestirme onerileri sunar.

    Attributes:
        _checks: Kontrol gecmisi.
        _rules: Kalite kurallari.
    """

    def __init__(self) -> None:
        """Kalite kontrolunu baslatir."""
        self._checks: list[dict[str, Any]] = []
        self._rules: dict[str, dict[str, Any]] = {}
        self._issues: list[dict[str, Any]] = []

        logger.info(
            "LocalizationQualityChecker baslatildi",
        )

    def check_translation(
        self,
        source: str,
        translated: str,
        source_lang: str = "en",
        target_lang: str = "tr",
    ) -> dict[str, Any]:
        """Ceviri kalitesini kontrol eder.

        Args:
            source: Kaynak metin.
            translated: Cevrilmis metin.
            source_lang: Kaynak dil.
            target_lang: Hedef dil.

        Returns:
            Kalite raporu.
        """
        issues: list[str] = []
        score = 1.0

        # Bos ceviri
        if not translated.strip():
            issues.append("empty_translation")
            score = 0.0

        # Ayni metin (cevrilmemis olabilir)
        elif translated == source and source_lang != target_lang:
            issues.append("untranslated")
            score *= 0.3

        # Uzunluk kontrolu
        if translated and source:
            ratio = len(translated) / max(1, len(source))
            if ratio > 3.0 or ratio < 0.3:
                issues.append("length_mismatch")
                score *= 0.7

        # Placeholder tutarliligi
        src_ph = set(re.findall(r"\{[\w]+\}", source))
        trn_ph = set(re.findall(r"\{[\w]+\}", translated))
        if src_ph != trn_ph:
            issues.append("placeholder_mismatch")
            score *= 0.6

        # Sayisal tutarlilik
        src_nums = set(re.findall(r"\d+", source))
        trn_nums = set(re.findall(r"\d+", translated))
        if src_nums and not src_nums.issubset(trn_nums):
            issues.append("number_mismatch")
            score *= 0.8

        level = self._score_to_level(score)

        result = {
            "source": source[:50],
            "translated": translated[:50],
            "score": round(score, 2),
            "level": level.value,
            "issues": issues,
        }
        self._checks.append(result)

        for issue in issues:
            self._issues.append({
                "type": issue,
                "source": source[:50],
                "translated": translated[:50],
            })

        return result

    def check_consistency(
        self,
        translations: dict[str, str],
        term: str,
    ) -> dict[str, Any]:
        """Tutarlilik kontrolu yapar.

        Args:
            translations: Dil -> ceviri eslesmesi.
            term: Terim.

        Returns:
            Kontrol sonucu.
        """
        unique_translations = set(translations.values())
        consistent = len(unique_translations) == len(
            translations,
        )

        return {
            "term": term,
            "languages": len(translations),
            "unique_translations": len(
                unique_translations,
            ),
            "consistent": consistent,
        }

    def check_missing(
        self,
        messages: dict[str, dict[str, str]],
        required_langs: list[str],
    ) -> dict[str, Any]:
        """Eksik cevirileri kontrol eder.

        Args:
            messages: Anahtar -> {dil: ceviri}.
            required_langs: Gerekli diller.

        Returns:
            Eksik ceviri raporu.
        """
        missing: dict[str, list[str]] = {}
        total_missing = 0

        for key, translations in messages.items():
            for lang in required_langs:
                if lang not in translations:
                    if key not in missing:
                        missing[key] = []
                    missing[key].append(lang)
                    total_missing += 1

        total_required = (
            len(messages) * len(required_langs)
        )
        coverage = (
            1.0 - total_missing / max(1, total_required)
        )

        return {
            "missing": missing,
            "total_missing": total_missing,
            "total_required": total_required,
            "coverage": round(coverage, 3),
        }

    def validate_format(
        self,
        text: str,
        expected_format: str,
    ) -> bool:
        """Format dogrulama.

        Args:
            text: Metin.
            expected_format: Beklenen format.

        Returns:
            Gecerli ise True.
        """
        format_patterns: dict[str, str] = {
            "date_iso": r"\d{4}-\d{2}-\d{2}",
            "email": r"^[^@]+@[^@]+\.[^@]+$",
            "phone": r"^\+?[\d\s\-()]+$",
            "url": r"^https?://",
            "number": r"^[\d.,]+$",
        }
        pattern = format_patterns.get(expected_format)
        if not pattern:
            return True
        return bool(re.match(pattern, text))

    def add_quality_rule(
        self,
        name: str,
        rule: dict[str, Any],
    ) -> None:
        """Kalite kurali ekler.

        Args:
            name: Kural adi.
            rule: Kural detaylari.
        """
        self._rules[name] = rule

    def get_quality_report(self) -> dict[str, Any]:
        """Kalite raporu getirir.

        Returns:
            Rapor.
        """
        if not self._checks:
            return {
                "total_checks": 0,
                "avg_score": 0.0,
                "level": QualityLevel.GOOD.value,
                "issues": [],
            }

        avg_score = sum(
            c["score"] for c in self._checks
        ) / len(self._checks)

        return {
            "total_checks": len(self._checks),
            "avg_score": round(avg_score, 2),
            "level": self._score_to_level(
                avg_score,
            ).value,
            "issues": self._issues[-10:],
        }

    def _score_to_level(
        self,
        score: float,
    ) -> QualityLevel:
        """Puani seviyeye cevirir.

        Args:
            score: Puan.

        Returns:
            Kalite seviyesi.
        """
        if score >= 0.9:
            return QualityLevel.EXCELLENT
        if score >= 0.7:
            return QualityLevel.GOOD
        if score >= 0.4:
            return QualityLevel.FAIR
        return QualityLevel.POOR

    @property
    def check_count(self) -> int:
        """Kontrol sayisi."""
        return len(self._checks)

    @property
    def issue_count(self) -> int:
        """Sorun sayisi."""
        return len(self._issues)

    @property
    def rule_count(self) -> int:
        """Kural sayisi."""
        return len(self._rules)
