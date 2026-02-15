"""ATLAS Bilgi Cikarici modulu.

Ogrenme cikarimi, kalip soyutlama,
basari faktorleri, basarisizlik dersleri, genellenebilir kurallar.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class KnowledgeExtractor:
    """Bilgi cikarici.

    Sistem deneyimlerinden bilgi cikarir.

    Attributes:
        _knowledge: Cikarilan bilgiler.
        _stats: Istatistikler.
    """

    def __init__(self) -> None:
        """Bilgi cikariciyi baslatir."""
        self._knowledge: dict[
            str, dict[str, Any]
        ] = {}
        self._counter = 0
        self._stats = {
            "extracted": 0,
        }

        logger.info(
            "KnowledgeExtractor baslatildi",
        )

    def extract_learning(
        self,
        source_system: str,
        experience: dict[str, Any],
        knowledge_type: str = "pattern",
    ) -> dict[str, Any]:
        """Ogrenme cikarir.

        Args:
            source_system: Kaynak sistem.
            experience: Deneyim verisi.
            knowledge_type: Bilgi tipi.

        Returns:
            Cikarilan bilgi.
        """
        self._counter += 1
        kid = f"k_{self._counter}"

        # Basari faktorlerini cikar
        success_factors = (
            self._extract_success_factors(
                experience,
            )
        )

        # Basarisizlik derslerini cikar
        failure_lessons = (
            self._extract_failure_lessons(
                experience,
            )
        )

        # Genellenebilir kurallar
        rules = self._generalize_rules(
            experience,
        )

        knowledge = {
            "knowledge_id": kid,
            "source_system": source_system,
            "knowledge_type": knowledge_type,
            "content": experience.get(
                "content", {},
            ),
            "success_factors": success_factors,
            "failure_lessons": failure_lessons,
            "rules": rules,
            "confidence": self._calc_confidence(
                experience,
            ),
            "tags": experience.get("tags", []),
            "extracted_at": time.time(),
        }

        self._knowledge[kid] = knowledge
        self._stats["extracted"] += 1

        return {
            "knowledge_id": kid,
            "source_system": source_system,
            "knowledge_type": knowledge_type,
            "confidence": knowledge[
                "confidence"
            ],
            "factors": len(success_factors),
            "lessons": len(failure_lessons),
            "rules": len(rules),
            "extracted": True,
        }

    def _extract_success_factors(
        self,
        experience: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Basari faktorlerini cikarir.

        Args:
            experience: Deneyim verisi.

        Returns:
            Faktor listesi.
        """
        factors = []
        outcome = experience.get("outcome", "")

        if outcome == "success":
            for key, value in experience.get(
                "parameters", {},
            ).items():
                factors.append({
                    "factor": key,
                    "value": value,
                    "impact": "positive",
                })

        return factors

    def _extract_failure_lessons(
        self,
        experience: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Basarisizlik derslerini cikarir.

        Args:
            experience: Deneyim verisi.

        Returns:
            Ders listesi.
        """
        lessons = []
        outcome = experience.get("outcome", "")

        if outcome == "failure":
            error = experience.get("error", "")
            if error:
                lessons.append({
                    "lesson": (
                        f"Avoid: {error}"
                    ),
                    "severity": "high",
                })
            causes = experience.get(
                "root_causes", [],
            )
            for cause in causes:
                lessons.append({
                    "lesson": cause,
                    "severity": "medium",
                })

        return lessons

    def _generalize_rules(
        self,
        experience: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Genellenebilir kurallar cikarir.

        Args:
            experience: Deneyim verisi.

        Returns:
            Kural listesi.
        """
        rules = []
        params = experience.get(
            "parameters", {},
        )
        outcome = experience.get("outcome", "")

        if params and outcome:
            rules.append({
                "condition": params,
                "outcome": outcome,
                "generalizability": (
                    "high"
                    if len(params) <= 3
                    else "medium"
                ),
            })

        return rules

    def _calc_confidence(
        self,
        experience: dict[str, Any],
    ) -> float:
        """Guven skoru hesaplar.

        Args:
            experience: Deneyim verisi.

        Returns:
            Guven skoru (0-1).
        """
        base = 0.5

        # Sonuc varsa guven artar
        if experience.get("outcome"):
            base += 0.2

        # Tekrar sayisi
        repeats = experience.get("repeats", 1)
        if repeats > 5:
            base += 0.2
        elif repeats > 1:
            base += 0.1

        return min(round(base, 2), 1.0)

    def abstract_pattern(
        self,
        knowledge_id: str,
    ) -> dict[str, Any]:
        """Kalip soyutlar.

        Args:
            knowledge_id: Bilgi ID.

        Returns:
            Soyut kalip.
        """
        k = self._knowledge.get(knowledge_id)
        if not k:
            return {
                "error": "knowledge_not_found",
            }

        return {
            "knowledge_id": knowledge_id,
            "abstract_pattern": {
                "type": k["knowledge_type"],
                "key_factors": [
                    f["factor"]
                    for f in k["success_factors"]
                ],
                "rules_count": len(k["rules"]),
                "source": k["source_system"],
            },
            "abstracted": True,
        }

    def get_knowledge(
        self,
        knowledge_id: str,
    ) -> dict[str, Any]:
        """Bilgi getirir.

        Args:
            knowledge_id: Bilgi ID.

        Returns:
            Bilgi verisi.
        """
        k = self._knowledge.get(knowledge_id)
        if not k:
            return {
                "error": "knowledge_not_found",
            }
        return dict(k)

    def list_by_source(
        self,
        source_system: str,
    ) -> list[dict[str, Any]]:
        """Kaynaga gore listeler.

        Args:
            source_system: Kaynak sistem.

        Returns:
            Bilgi listesi.
        """
        return [
            {
                "knowledge_id": k[
                    "knowledge_id"
                ],
                "knowledge_type": k[
                    "knowledge_type"
                ],
                "confidence": k["confidence"],
            }
            for k in self._knowledge.values()
            if k["source_system"]
            == source_system
        ]

    @property
    def knowledge_count(self) -> int:
        """Bilgi sayisi."""
        return self._stats["extracted"]
