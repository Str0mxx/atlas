"""ATLAS Denetim Bicimleyici modulu.

Uyumluluk formati, yasal format,
teknik format, yonetici formati, ozel sablonlar.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class AuditFormatter:
    """Denetim bicimleyici.

    Karar aciklamalarini denetim formatlarina donusturur.

    Attributes:
        _formats: Format kayitlari.
        _templates: Ozel sablonlar.
    """

    def __init__(self) -> None:
        """Denetim bicimleyiciyi baslatir."""
        self._formats: list[
            dict[str, Any]
        ] = []
        self._templates: dict[
            str, dict[str, Any]
        ] = {}
        self._stats = {
            "formatted": 0,
        }

        logger.info(
            "AuditFormatter baslatildi",
        )

    def format_compliance(
        self,
        decision_id: str,
        decision_data: dict[str, Any],
        standard: str = "general",
    ) -> dict[str, Any]:
        """Uyumluluk formati uretir.

        Args:
            decision_id: Karar ID.
            decision_data: Karar verisi.
            standard: Uyumluluk standardi.

        Returns:
            Uyumluluk raporu.
        """
        sections = []

        # Karar bilgisi
        sections.append({
            "section": "Decision Information",
            "content": {
                "decision_id": decision_id,
                "type": decision_data.get(
                    "decision_type", "",
                ),
                "description": decision_data.get(
                    "description", "",
                ),
                "timestamp": decision_data.get(
                    "recorded_at", 0,
                ),
            },
        })

        # Girdi verileri
        inputs = decision_data.get(
            "inputs", {},
        )
        if inputs:
            sections.append({
                "section": "Input Data",
                "content": inputs,
            })

        # Faktorler
        factors = decision_data.get(
            "factors", [],
        )
        if factors:
            sections.append({
                "section": "Decision Factors",
                "content": {
                    "factors": factors,
                    "count": len(factors),
                },
            })

        # Sonuc
        outcome = decision_data.get("outcome")
        if outcome:
            sections.append({
                "section": "Outcome",
                "content": outcome,
            })

        report = {
            "format": "compliance",
            "standard": standard,
            "decision_id": decision_id,
            "sections": sections,
            "section_count": len(sections),
            "generated_at": time.time(),
        }

        self._formats.append(report)
        self._stats["formatted"] += 1

        return report

    def format_legal(
        self,
        decision_id: str,
        decision_data: dict[str, Any],
        jurisdiction: str = "general",
    ) -> dict[str, Any]:
        """Yasal format uretir.

        Args:
            decision_id: Karar ID.
            decision_data: Karar verisi.
            jurisdiction: Yargi bolgesi.

        Returns:
            Yasal rapor.
        """
        sections = []

        # Karar adi
        sections.append({
            "section": "Matter",
            "content": (
                f"Decision {decision_id}: "
                f"{decision_data.get('description', '')}"
            ),
        })

        # Olgular
        inputs = decision_data.get(
            "inputs", {},
        )
        sections.append({
            "section": "Facts",
            "content": inputs,
        })

        # Degerlendirilen alternatifler
        alts = decision_data.get(
            "alternatives", [],
        )
        sections.append({
            "section": (
                "Alternatives Considered"
            ),
            "content": {
                "alternatives": alts,
                "count": len(alts),
            },
        })

        # Gerekce
        outcome = decision_data.get(
            "outcome", {},
        )
        sections.append({
            "section": "Rationale",
            "content": outcome.get(
                "rationale",
                outcome.get("result", ""),
            ),
        })

        # Sonuc
        sections.append({
            "section": "Conclusion",
            "content": outcome.get(
                "result", "",
            ),
        })

        report = {
            "format": "legal",
            "jurisdiction": jurisdiction,
            "decision_id": decision_id,
            "sections": sections,
            "section_count": len(sections),
            "generated_at": time.time(),
        }

        self._formats.append(report)
        self._stats["formatted"] += 1

        return report

    def format_technical(
        self,
        decision_id: str,
        decision_data: dict[str, Any],
        trace: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Teknik format uretir.

        Args:
            decision_id: Karar ID.
            decision_data: Karar verisi.
            trace: Akil yurutme izi.

        Returns:
            Teknik rapor.
        """
        sections = []

        # Sistem bilgisi
        sections.append({
            "section": "System Context",
            "content": {
                "system": decision_data.get(
                    "system", "",
                ),
                "type": decision_data.get(
                    "decision_type", "",
                ),
            },
        })

        # Girdi parametreleri
        sections.append({
            "section": "Input Parameters",
            "content": decision_data.get(
                "inputs", {},
            ),
        })

        # Akil yurutme izi
        if trace:
            sections.append({
                "section": "Reasoning Trace",
                "content": trace,
            })

        # Faktorler (teknik detay)
        factors = decision_data.get(
            "factors", [],
        )
        sections.append({
            "section": "Factor Analysis",
            "content": {
                "factors": factors,
                "count": len(factors),
            },
        })

        # Sonuc
        outcome = decision_data.get(
            "outcome", {},
        )
        sections.append({
            "section": "Decision Output",
            "content": {
                "result": outcome.get(
                    "result", "",
                ),
                "confidence": outcome.get(
                    "confidence", 0,
                ),
            },
        })

        report = {
            "format": "technical",
            "decision_id": decision_id,
            "sections": sections,
            "section_count": len(sections),
            "generated_at": time.time(),
        }

        self._formats.append(report)
        self._stats["formatted"] += 1

        return report

    def format_executive(
        self,
        decision_id: str,
        decision_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Yonetici formati uretir.

        Args:
            decision_id: Karar ID.
            decision_data: Karar verisi.

        Returns:
            Yonetici raporu.
        """
        outcome = decision_data.get(
            "outcome", {},
        )
        factors = decision_data.get(
            "factors", [],
        )
        top_factors = sorted(
            factors,
            key=lambda f: abs(
                f.get("contribution",
                       f.get("weight", 0)),
            ),
            reverse=True,
        )[:3]

        report = {
            "format": "executive",
            "decision_id": decision_id,
            "summary": decision_data.get(
                "description", "",
            ),
            "decision": outcome.get(
                "result", "",
            ),
            "confidence": outcome.get(
                "confidence", 0,
            ),
            "key_factors": [
                f.get("name", "")
                for f in top_factors
            ],
            "alternatives_considered": len(
                decision_data.get(
                    "alternatives", [],
                ),
            ),
            "generated_at": time.time(),
        }

        self._formats.append(report)
        self._stats["formatted"] += 1

        return report

    def add_template(
        self,
        template_name: str,
        sections: list[str],
        format_type: str = "custom",
    ) -> dict[str, Any]:
        """Ozel sablon ekler.

        Args:
            template_name: Sablon adi.
            sections: Bolum listesi.
            format_type: Format tipi.

        Returns:
            Ekleme bilgisi.
        """
        self._templates[template_name] = {
            "name": template_name,
            "sections": sections,
            "format_type": format_type,
            "created_at": time.time(),
        }

        return {
            "template": template_name,
            "sections": len(sections),
            "added": True,
        }

    def format_custom(
        self,
        decision_id: str,
        decision_data: dict[str, Any],
        template_name: str,
    ) -> dict[str, Any]:
        """Ozel formatta uretir.

        Args:
            decision_id: Karar ID.
            decision_data: Karar verisi.
            template_name: Sablon adi.

        Returns:
            Ozel rapor.
        """
        template = self._templates.get(
            template_name,
        )
        if not template:
            return {
                "error": "template_not_found",
            }

        sections = []
        for section_name in template[
            "sections"
        ]:
            content = decision_data.get(
                section_name.lower()
                .replace(" ", "_"),
                {},
            )
            sections.append({
                "section": section_name,
                "content": content,
            })

        report = {
            "format": "custom",
            "template": template_name,
            "decision_id": decision_id,
            "sections": sections,
            "section_count": len(sections),
            "generated_at": time.time(),
        }

        self._formats.append(report)
        self._stats["formatted"] += 1

        return report

    def get_formatted(
        self,
        format_type: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Formatlari getirir.

        Args:
            format_type: Format filtresi.
            limit: Limit.

        Returns:
            Format listesi.
        """
        formats = self._formats
        if format_type:
            formats = [
                f for f in formats
                if f.get("format")
                == format_type
            ]
        return formats[-limit:]

    @property
    def format_count(self) -> int:
        """Format sayisi."""
        return self._stats["formatted"]
