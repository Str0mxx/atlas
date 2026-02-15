"""ATLAS Sorgu Genişletici modülü.

Eşanlamlı genişletme, ilgili terimler,
soru üretme, kapsam genişletme,
dil varyantları.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class QueryExpander:
    """Sorgu genişletici.

    Arama sorgularını genişletir ve zenginleştirir.

    Attributes:
        _expansions: Genişletme geçmişi.
        _synonyms: Eşanlamlı sözlük.
    """

    def __init__(self) -> None:
        """Genişleticiyi başlatır."""
        self._expansions: list[
            dict[str, Any]
        ] = []
        self._synonyms: dict[
            str, list[str]
        ] = {
            "buy": ["purchase", "acquire", "get"],
            "sell": ["offer", "market", "trade"],
            "price": ["cost", "rate", "fee"],
            "fast": ["quick", "rapid", "swift"],
            "good": ["quality", "excellent", "top"],
            "big": ["large", "major", "significant"],
            "new": ["latest", "recent", "modern"],
            "cheap": ["affordable", "budget", "low-cost"],
        }
        self._related_terms: dict[
            str, list[str]
        ] = {}
        self._counter = 0
        self._stats = {
            "expansions": 0,
            "synonyms_found": 0,
            "questions_generated": 0,
        }

        logger.info(
            "QueryExpander baslatildi",
        )

    def expand(
        self,
        query: str,
        include_synonyms: bool = True,
        include_questions: bool = True,
        include_variants: bool = True,
    ) -> dict[str, Any]:
        """Sorguyu genişletir.

        Args:
            query: Orijinal sorgu.
            include_synonyms: Eşanlamlılar.
            include_questions: Sorular.
            include_variants: Varyantlar.

        Returns:
            Genişletme bilgisi.
        """
        self._counter += 1
        eid = f"exp_{self._counter}"

        expanded_queries = [query]
        synonyms_used = []
        questions = []
        variants = []

        if include_synonyms:
            syn_result = (
                self._expand_synonyms(query)
            )
            expanded_queries.extend(
                syn_result["expanded"],
            )
            synonyms_used = syn_result[
                "synonyms"
            ]

        if include_questions:
            questions = (
                self._generate_questions(query)
            )
            expanded_queries.extend(questions)

        if include_variants:
            variants = (
                self._generate_variants(query)
            )
            expanded_queries.extend(variants)

        # Tekrarları temizle
        unique_queries = list(
            dict.fromkeys(expanded_queries),
        )

        result = {
            "expansion_id": eid,
            "original_query": query,
            "expanded_queries": unique_queries,
            "total_queries": len(unique_queries),
            "synonyms_used": synonyms_used,
            "questions": questions,
            "variants": variants,
            "timestamp": time.time(),
        }
        self._expansions.append(result)
        self._stats["expansions"] += 1

        return result

    def _expand_synonyms(
        self,
        query: str,
    ) -> dict[str, Any]:
        """Eşanlamlı genişletme yapar."""
        words = query.lower().split()
        expanded = []
        synonyms = []

        for word in words:
            syns = self._synonyms.get(word, [])
            if syns:
                synonyms.append({
                    "word": word,
                    "synonyms": syns,
                })
                self._stats[
                    "synonyms_found"
                ] += len(syns)
                for syn in syns:
                    new_query = query.lower().replace(
                        word, syn,
                    )
                    expanded.append(new_query)

        return {
            "expanded": expanded,
            "synonyms": synonyms,
        }

    def _generate_questions(
        self,
        query: str,
    ) -> list[str]:
        """Soru üretir."""
        prefixes = [
            "What is",
            "How does",
            "Why is",
            "What are the benefits of",
            "How to",
        ]
        questions = []
        for prefix in prefixes:
            questions.append(
                f"{prefix} {query}?",
            )
            self._stats[
                "questions_generated"
            ] += 1

        return questions

    def _generate_variants(
        self,
        query: str,
    ) -> list[str]:
        """Varyantlar üretir."""
        variants = []
        words = query.split()

        # Ters sıra
        if len(words) > 1:
            variants.append(
                " ".join(reversed(words)),
            )

        # Kısaltılmış
        if len(words) > 2:
            variants.append(
                " ".join(words[:2]),
            )
            variants.append(
                " ".join(words[-2:]),
            )

        return variants

    def add_synonym(
        self,
        word: str,
        synonyms: list[str],
    ) -> dict[str, Any]:
        """Eşanlamlı ekler.

        Args:
            word: Kelime.
            synonyms: Eşanlamlılar.

        Returns:
            Ekleme bilgisi.
        """
        existing = self._synonyms.get(word, [])
        merged = list(
            set(existing + synonyms),
        )
        self._synonyms[word] = merged
        return {
            "word": word,
            "synonyms": merged,
            "added": True,
        }

    def add_related_terms(
        self,
        topic: str,
        terms: list[str],
    ) -> dict[str, Any]:
        """İlgili terim ekler.

        Args:
            topic: Konu.
            terms: İlgili terimler.

        Returns:
            Ekleme bilgisi.
        """
        existing = (
            self._related_terms.get(topic, [])
        )
        merged = list(set(existing + terms))
        self._related_terms[topic] = merged
        return {
            "topic": topic,
            "terms": merged,
            "added": True,
        }

    def broaden_scope(
        self,
        query: str,
    ) -> dict[str, Any]:
        """Kapsam genişletir.

        Args:
            query: Sorgu.

        Returns:
            Genişletme bilgisi.
        """
        broader = []
        words = query.split()

        # Üst kavramlar
        if len(words) >= 2:
            broader.append(words[0])
            broader.append(words[-1])
            broader.append(
                f"{words[0]} industry",
            )
            broader.append(
                f"{words[0]} market",
            )

        # İlgili terimler
        for word in words:
            related = self._related_terms.get(
                word.lower(), [],
            )
            broader.extend(related)

        return {
            "original": query,
            "broader_queries": list(
                set(broader),
            ),
            "broadened": True,
        }

    def get_expansions(
        self,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Genişletmeleri getirir.

        Args:
            limit: Maks kayıt.

        Returns:
            Genişletme listesi.
        """
        return list(self._expansions[-limit:])

    @property
    def expansion_count(self) -> int:
        """Genişletme sayısı."""
        return self._stats["expansions"]

    @property
    def question_count(self) -> int:
        """Üretilen soru sayısı."""
        return self._stats[
            "questions_generated"
        ]
