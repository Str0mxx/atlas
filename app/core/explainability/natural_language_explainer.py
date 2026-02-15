"""ATLAS Dogal Dil Aciklayici modulu.

Insana okunur aciklamalar, sablon tabanli,
baglam duyarli, cok dilli, hedef kitleye uygun.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class NaturalLanguageExplainer:
    """Dogal dil aciklayici.

    Karar aciklamalarini dogal dilde uretir.

    Attributes:
        _templates: Aciklama sablonlari.
        _explanations: Aciklama gecmisi.
    """

    def __init__(
        self,
        default_language: str = "en",
    ) -> None:
        """Dogal dil aciklayiciyi baslatir.

        Args:
            default_language: Varsayilan dil.
        """
        self._default_language = default_language
        self._templates: dict[
            str, dict[str, str]
        ] = {
            "decision": {
                "en": (
                    "The decision '{decision}' "
                    "was made because {reason}."
                ),
                "tr": (
                    "'{decision}' karari "
                    "{reason} nedeniyle alindi."
                ),
            },
            "factor": {
                "en": (
                    "The factor '{name}' "
                    "contributed {pct}% "
                    "to the decision."
                ),
                "tr": (
                    "'{name}' faktoru karara "
                    "%{pct} oraninda "
                    "katki sagladi."
                ),
            },
            "alternative": {
                "en": (
                    "'{alt}' was considered "
                    "but rejected because "
                    "{reason}."
                ),
                "tr": (
                    "'{alt}' degerlendirild "
                    "ama {reason} nedeniyle "
                    "reddedildi."
                ),
            },
            "outcome": {
                "en": (
                    "The outcome is '{outcome}' "
                    "with {confidence}% confidence."
                ),
                "tr": (
                    "Sonuc '{outcome}' "
                    "(%{confidence} guven)."
                ),
            },
        }
        self._custom_templates: dict[
            str, dict[str, str]
        ] = {}
        self._explanations: list[
            dict[str, Any]
        ] = []
        self._stats = {
            "generated": 0,
        }

        logger.info(
            "NaturalLanguageExplainer "
            "baslatildi",
        )

    def explain_decision(
        self,
        decision_id: str,
        decision_name: str,
        reason: str,
        language: str | None = None,
    ) -> dict[str, Any]:
        """Karari dogal dilde aciklar.

        Args:
            decision_id: Karar ID.
            decision_name: Karar adi.
            reason: Sebep.
            language: Dil.

        Returns:
            Aciklama bilgisi.
        """
        lang = language or self._default_language
        template = self._templates.get(
            "decision", {},
        ).get(lang)

        if not template:
            template = self._templates[
                "decision"
            ]["en"]

        text = template.format(
            decision=decision_name,
            reason=reason,
        )

        explanation = {
            "decision_id": decision_id,
            "type": "decision",
            "text": text,
            "language": lang,
            "generated_at": time.time(),
        }

        self._explanations.append(explanation)
        self._stats["generated"] += 1

        return explanation

    def explain_factors(
        self,
        decision_id: str,
        factors: list[dict[str, Any]],
        language: str | None = None,
    ) -> dict[str, Any]:
        """Faktorleri dogal dilde aciklar.

        Args:
            decision_id: Karar ID.
            factors: Faktorler.
            language: Dil.

        Returns:
            Aciklama bilgisi.
        """
        lang = language or self._default_language
        template = self._templates.get(
            "factor", {},
        ).get(lang)

        if not template:
            template = self._templates[
                "factor"
            ]["en"]

        texts = []
        for f in factors:
            text = template.format(
                name=f.get("name", ""),
                pct=round(
                    f.get("weight_pct", 0), 1,
                ),
            )
            texts.append(text)

        explanation = {
            "decision_id": decision_id,
            "type": "factors",
            "texts": texts,
            "summary": " ".join(texts),
            "language": lang,
            "generated_at": time.time(),
        }

        self._explanations.append(explanation)
        self._stats["generated"] += 1

        return explanation

    def explain_alternative(
        self,
        decision_id: str,
        alternative: str,
        reason: str,
        language: str | None = None,
    ) -> dict[str, Any]:
        """Alternatifi dogal dilde aciklar.

        Args:
            decision_id: Karar ID.
            alternative: Alternatif.
            reason: Red sebebi.
            language: Dil.

        Returns:
            Aciklama bilgisi.
        """
        lang = language or self._default_language
        template = self._templates.get(
            "alternative", {},
        ).get(lang)

        if not template:
            template = self._templates[
                "alternative"
            ]["en"]

        text = template.format(
            alt=alternative,
            reason=reason,
        )

        explanation = {
            "decision_id": decision_id,
            "type": "alternative",
            "text": text,
            "language": lang,
            "generated_at": time.time(),
        }

        self._explanations.append(explanation)
        self._stats["generated"] += 1

        return explanation

    def explain_outcome(
        self,
        decision_id: str,
        outcome: str,
        confidence: float,
        language: str | None = None,
    ) -> dict[str, Any]:
        """Sonucu dogal dilde aciklar.

        Args:
            decision_id: Karar ID.
            outcome: Sonuc.
            confidence: Guven yuzdesi.
            language: Dil.

        Returns:
            Aciklama bilgisi.
        """
        lang = language or self._default_language
        template = self._templates.get(
            "outcome", {},
        ).get(lang)

        if not template:
            template = self._templates[
                "outcome"
            ]["en"]

        text = template.format(
            outcome=outcome,
            confidence=round(confidence, 1),
        )

        explanation = {
            "decision_id": decision_id,
            "type": "outcome",
            "text": text,
            "language": lang,
            "generated_at": time.time(),
        }

        self._explanations.append(explanation)
        self._stats["generated"] += 1

        return explanation

    def add_template(
        self,
        template_name: str,
        language: str,
        template: str,
    ) -> dict[str, Any]:
        """Sablon ekler.

        Args:
            template_name: Sablon adi.
            language: Dil.
            template: Sablon metni.

        Returns:
            Ekleme bilgisi.
        """
        if template_name not in (
            self._custom_templates
        ):
            self._custom_templates[
                template_name
            ] = {}

        self._custom_templates[
            template_name
        ][language] = template

        return {
            "template": template_name,
            "language": language,
            "added": True,
        }

    def generate_summary(
        self,
        decision_id: str,
        decision_data: dict[str, Any],
        language: str | None = None,
        audience: str = "technical",
    ) -> dict[str, Any]:
        """Ozet aciklama uretir.

        Args:
            decision_id: Karar ID.
            decision_data: Karar verisi.
            language: Dil.
            audience: Hedef kitle.

        Returns:
            Ozet aciklama.
        """
        lang = language or self._default_language

        parts = []

        # Karar aciklamasi
        desc = decision_data.get(
            "description", "",
        )
        if desc:
            parts.append(desc)

        # Faktorler
        factors = decision_data.get(
            "factors", [],
        )
        if factors:
            factor_names = [
                f.get("name", "")
                for f in factors[:3]
            ]
            if lang == "tr":
                parts.append(
                    "Ana faktorler: "
                    + ", ".join(factor_names),
                )
            else:
                parts.append(
                    "Key factors: "
                    + ", ".join(factor_names),
                )

        # Sonuc
        outcome = decision_data.get("outcome")
        if outcome:
            result = outcome.get("result", "")
            conf = outcome.get("confidence", 0)
            if lang == "tr":
                parts.append(
                    f"Sonuc: {result} "
                    f"(%{conf} guven)",
                )
            else:
                parts.append(
                    f"Outcome: {result} "
                    f"({conf}% confidence)",
                )

        # Kitle uyarlamasi
        if audience == "executive":
            summary = ". ".join(parts[:2])
        elif audience == "end_user":
            summary = parts[0] if parts else ""
        else:
            summary = ". ".join(parts)

        explanation = {
            "decision_id": decision_id,
            "type": "summary",
            "text": summary,
            "language": lang,
            "audience": audience,
            "generated_at": time.time(),
        }

        self._explanations.append(explanation)
        self._stats["generated"] += 1

        return explanation

    def get_explanations(
        self,
        decision_id: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Aciklamalari getirir.

        Args:
            decision_id: Karar filtresi.
            limit: Limit.

        Returns:
            Aciklama listesi.
        """
        exps = self._explanations
        if decision_id:
            exps = [
                e for e in exps
                if e.get("decision_id")
                == decision_id
            ]
        return exps[-limit:]

    @property
    def explanation_count(self) -> int:
        """Aciklama sayisi."""
        return self._stats["generated"]

    @property
    def supported_languages(self) -> list[str]:
        """Desteklenen diller."""
        langs = set()
        for templates in (
            self._templates.values()
        ):
            langs.update(templates.keys())
        return sorted(langs)
