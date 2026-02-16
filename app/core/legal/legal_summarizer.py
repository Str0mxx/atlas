"""ATLAS Hukuki Özetleyici modülü.

Yönetici özeti, anahtar noktalar,
sade dil, taraf yükümlülükleri,
finansal koşullar.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class LegalSummarizer:
    """Hukuki özetleyici.

    Sözleşmeleri özetler.

    Attributes:
        _summaries: Özet kayıtları.
    """

    def __init__(self) -> None:
        """Özetleyiciyi başlatır."""
        self._summaries: dict[
            str, dict[str, Any]
        ] = {}
        self._stats = {
            "summaries_created": 0,
            "key_points_extracted": 0,
        }

        logger.info(
            "LegalSummarizer baslatildi",
        )

    def create_executive_summary(
        self,
        contract_id: str,
        title: str = "",
        contract_type: str = "",
        parties: list[str]
        | None = None,
        key_terms: list[str]
        | None = None,
        value: float = 0.0,
        duration_months: int = 0,
    ) -> dict[str, Any]:
        """Yönetici özeti oluşturur.

        Args:
            contract_id: Sözleşme ID.
            title: Başlık.
            contract_type: Sözleşme tipi.
            parties: Taraflar.
            key_terms: Anahtar koşullar.
            value: Değer.
            duration_months: Süre (ay).

        Returns:
            Özet bilgisi.
        """
        parties = parties or []
        key_terms = key_terms or []

        summary = {
            "contract_id": contract_id,
            "title": title,
            "type": contract_type,
            "parties": parties,
            "party_count": len(parties),
            "key_terms": key_terms,
            "value": value,
            "duration_months": (
                duration_months
            ),
            "timestamp": time.time(),
        }
        self._summaries[
            contract_id
        ] = summary
        self._stats[
            "summaries_created"
        ] += 1

        return {
            "contract_id": contract_id,
            "title": title,
            "party_count": len(parties),
            "value": value,
            "created": True,
        }

    def extract_key_points(
        self,
        contract_id: str,
        clauses: list[dict[str, Any]]
        | None = None,
    ) -> dict[str, Any]:
        """Anahtar noktalar çıkarır.

        Args:
            contract_id: Sözleşme ID.
            clauses: Maddeler.

        Returns:
            Anahtar noktalar.
        """
        clauses = clauses or []
        points = []

        for clause in clauses:
            ctype = clause.get("type", "")
            text = clause.get("text", "")
            if ctype in (
                "obligation", "payment",
                "termination", "liability",
            ):
                points.append({
                    "type": ctype,
                    "summary": text[:100],
                })

        self._stats[
            "key_points_extracted"
        ] += len(points)

        return {
            "contract_id": contract_id,
            "points": points,
            "count": len(points),
        }

    def to_plain_language(
        self,
        text: str,
        audience: str = "business",
    ) -> dict[str, Any]:
        """Sade dile çevirir.

        Args:
            text: Hukuki metin.
            audience: Hedef kitle.

        Returns:
            Sade dil bilgisi.
        """
        # Basit sadeleştirme
        replacements = {
            "hereinafter": "from now on",
            "whereas": "since",
            "notwithstanding":
                "regardless of",
            "pursuant to":
                "according to",
            "shall": "will",
            "therein": "in it",
            "hereby": "by this",
        }

        simplified = text
        applied = 0
        for legal, plain in (
            replacements.items()
        ):
            if legal in simplified.lower():
                simplified = (
                    simplified.replace(
                        legal, plain,
                    )
                )
                applied += 1

        complexity = (
            "high" if applied >= 3
            else "medium" if applied >= 1
            else "low"
        )

        return {
            "original_length": len(text),
            "simplified_length": len(
                simplified,
            ),
            "simplifications": applied,
            "complexity": complexity,
            "audience": audience,
        }

    def extract_obligations(
        self,
        contract_id: str,
        parties: list[str]
        | None = None,
        clauses: list[dict[str, Any]]
        | None = None,
    ) -> dict[str, Any]:
        """Taraf yükümlülükleri çıkarır.

        Args:
            contract_id: Sözleşme ID.
            parties: Taraflar.
            clauses: Maddeler.

        Returns:
            Yükümlülük bilgisi.
        """
        parties = parties or []
        clauses = clauses or []

        obligations: dict[
            str, list[str]
        ] = {}
        for party in parties:
            obligations[party] = []

        for clause in clauses:
            if clause.get("type") == (
                "obligation"
            ):
                party = clause.get(
                    "party", "",
                )
                text = clause.get(
                    "text", "",
                )
                if party in obligations:
                    obligations[
                        party
                    ].append(text)
                elif parties:
                    obligations[
                        parties[0]
                    ].append(text)

        return {
            "contract_id": contract_id,
            "obligations": obligations,
            "party_count": len(parties),
            "total_obligations": sum(
                len(v)
                for v in obligations.values()
            ),
        }

    def extract_financial_terms(
        self,
        contract_id: str,
        total_value: float = 0.0,
        payment_schedule: str = "",
        penalties: list[str]
        | None = None,
        currency: str = "USD",
    ) -> dict[str, Any]:
        """Finansal koşulları çıkarır.

        Args:
            contract_id: Sözleşme ID.
            total_value: Toplam değer.
            payment_schedule: Ödeme takvimi.
            penalties: Cezalar.
            currency: Para birimi.

        Returns:
            Finansal bilgisi.
        """
        penalties = penalties or []

        return {
            "contract_id": contract_id,
            "total_value": total_value,
            "currency": currency,
            "payment_schedule": (
                payment_schedule
            ),
            "penalties": penalties,
            "penalty_count": len(
                penalties,
            ),
            "has_financial_terms": (
                total_value > 0
            ),
        }

    def get_summary(
        self,
        contract_id: str,
    ) -> dict[str, Any] | None:
        """Özet döndürür."""
        return self._summaries.get(
            contract_id,
        )

    @property
    def summary_count(self) -> int:
        """Özet sayısı."""
        return self._stats[
            "summaries_created"
        ]
