"""ATLAS Madde Çıkarıcı modülü.

Madde tanımlama, tip sınıflandırma,
anahtar terim çıkarma, yükümlülük tespiti,
hak haritalama.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ClauseExtractor:
    """Madde çıkarıcı.

    Sözleşme maddelerini çıkarır ve sınıflar.

    Attributes:
        _clauses: Madde kayıtları.
        _obligations: Yükümlülük kayıtları.
    """

    def __init__(self) -> None:
        """Çıkarıcıyı başlatır."""
        self._clauses: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._obligations: list[
            dict[str, Any]
        ] = []
        self._rights: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "clauses_extracted": 0,
            "obligations_detected": 0,
            "rights_mapped": 0,
        }

        logger.info(
            "ClauseExtractor baslatildi",
        )

    def identify_clause(
        self,
        contract_id: str,
        text: str,
        clause_type: str = "other",
        section: str = "",
    ) -> dict[str, Any]:
        """Madde tanımlar.

        Args:
            contract_id: Sözleşme ID.
            text: Madde metni.
            clause_type: Madde tipi.
            section: Bölüm.

        Returns:
            Madde bilgisi.
        """
        self._counter += 1
        clid = f"clause_{self._counter}"

        clause = {
            "clause_id": clid,
            "contract_id": contract_id,
            "text": text,
            "type": clause_type,
            "section": section,
            "key_terms": [],
            "timestamp": time.time(),
        }

        if (
            contract_id
            not in self._clauses
        ):
            self._clauses[
                contract_id
            ] = []
        self._clauses[
            contract_id
        ].append(clause)
        self._stats[
            "clauses_extracted"
        ] += 1

        return {
            "clause_id": clid,
            "type": clause_type,
            "section": section,
            "identified": True,
        }

    def classify_type(
        self,
        text: str,
    ) -> dict[str, Any]:
        """Tip sınıflandırır.

        Args:
            text: Madde metni.

        Returns:
            Sınıflandırma bilgisi.
        """
        lower = text.lower()

        keywords = {
            "obligation": [
                "shall", "must", "required",
                "obligated",
            ],
            "right": [
                "may", "entitled",
                "right to", "permission",
            ],
            "termination": [
                "terminate", "cancel",
                "end", "expire",
            ],
            "payment": [
                "pay", "fee", "cost",
                "price", "invoice",
            ],
            "liability": [
                "liable", "indemnify",
                "damage", "warranty",
            ],
        }

        scores: dict[str, int] = {}
        for ctype, words in (
            keywords.items()
        ):
            count = sum(
                1 for w in words
                if w in lower
            )
            if count > 0:
                scores[ctype] = count

        if scores:
            classified = max(
                scores, key=scores.get,
            )
            confidence = round(
                min(
                    max(scores.values())
                    / 3 * 100, 100,
                ), 1,
            )
        else:
            classified = "other"
            confidence = 0.0

        return {
            "classified_type": classified,
            "confidence": confidence,
            "scores": scores,
        }

    def extract_key_terms(
        self,
        text: str,
        max_terms: int = 10,
    ) -> dict[str, Any]:
        """Anahtar terim çıkarır.

        Args:
            text: Metin.
            max_terms: Maks terim.

        Returns:
            Terim bilgisi.
        """
        legal_terms = [
            "indemnification",
            "liability", "warranty",
            "termination", "confidential",
            "intellectual property",
            "force majeure", "arbitration",
            "jurisdiction", "governing law",
            "breach", "remedy", "damages",
            "representation", "covenant",
            "obligation", "assignment",
            "waiver", "amendment",
            "severability",
        ]

        lower = text.lower()
        found = [
            t for t in legal_terms
            if t in lower
        ][:max_terms]

        return {
            "terms": found,
            "count": len(found),
        }

    def detect_obligations(
        self,
        contract_id: str,
        party: str = "",
    ) -> dict[str, Any]:
        """Yükümlülük tespit eder.

        Args:
            contract_id: Sözleşme ID.
            party: Taraf.

        Returns:
            Yükümlülük bilgisi.
        """
        clauses = self._clauses.get(
            contract_id, [],
        )
        obligations = []

        for clause in clauses:
            if clause["type"] == "obligation":
                obligations.append({
                    "clause_id": clause[
                        "clause_id"
                    ],
                    "text": clause["text"],
                    "party": party,
                })

        self._stats[
            "obligations_detected"
        ] += len(obligations)

        return {
            "contract_id": contract_id,
            "obligations": obligations,
            "count": len(obligations),
        }

    def map_rights(
        self,
        contract_id: str,
        party: str = "",
    ) -> dict[str, Any]:
        """Hak haritalar.

        Args:
            contract_id: Sözleşme ID.
            party: Taraf.

        Returns:
            Hak bilgisi.
        """
        clauses = self._clauses.get(
            contract_id, [],
        )
        rights = []

        for clause in clauses:
            if clause["type"] == "right":
                rights.append({
                    "clause_id": clause[
                        "clause_id"
                    ],
                    "text": clause["text"],
                    "party": party,
                })

        self._stats[
            "rights_mapped"
        ] += len(rights)

        return {
            "contract_id": contract_id,
            "rights": rights,
            "count": len(rights),
        }

    def get_clauses(
        self,
        contract_id: str,
        clause_type: str = "",
    ) -> list[dict[str, Any]]:
        """Maddeleri listeler."""
        clauses = self._clauses.get(
            contract_id, [],
        )
        if clause_type:
            clauses = [
                c for c in clauses
                if c["type"] == clause_type
            ]
        return clauses

    @property
    def clause_count(self) -> int:
        """Madde sayısı."""
        return self._stats[
            "clauses_extracted"
        ]

    @property
    def obligation_count(self) -> int:
        """Yükümlülük sayısı."""
        return self._stats[
            "obligations_detected"
        ]
