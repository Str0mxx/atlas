"""ATLAS Terminoloji Yoneticisi modulu.

Alan sozlukleri, tutarli terminoloji,
terim cikarma, es anlam yonetimi
ve ozel sozlukler.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class TerminologyManager:
    """Terminoloji yoneticisi.

    Alan-ozel terimleri yonetir ve
    tutarli terminoloji saglar.

    Attributes:
        _glossaries: Alan sozlukleri.
        _synonyms: Es anlam esleri.
        _custom_dicts: Ozel sozlukler.
    """

    def __init__(self) -> None:
        """Terminoloji yoneticisini baslatir."""
        self._glossaries: dict[
            str, dict[str, dict[str, str]]
        ] = {}
        self._synonyms: dict[str, list[str]] = {}
        self._custom_dicts: dict[
            str, dict[str, str]
        ] = {}
        self._preferred_terms: dict[str, str] = {}

        logger.info("TerminologyManager baslatildi")

    def add_term(
        self,
        domain: str,
        term: str,
        translations: dict[str, str],
    ) -> dict[str, Any]:
        """Terim ekler.

        Args:
            domain: Alan.
            term: Terim.
            translations: Dil -> ceviri eslesmesi.

        Returns:
            Terim bilgisi.
        """
        if domain not in self._glossaries:
            self._glossaries[domain] = {}
        self._glossaries[domain][term] = translations

        return {
            "domain": domain,
            "term": term,
            "translations": translations,
        }

    def get_term(
        self,
        domain: str,
        term: str,
        lang: str = "en",
    ) -> str | None:
        """Terim cevirisini getirir.

        Args:
            domain: Alan.
            term: Terim.
            lang: Hedef dil.

        Returns:
            Ceviri veya None.
        """
        glossary = self._glossaries.get(domain, {})
        translations = glossary.get(term, {})
        return translations.get(lang)

    def search_term(
        self,
        query: str,
        domain: str | None = None,
    ) -> list[dict[str, Any]]:
        """Terim arar.

        Args:
            query: Arama sorgusu.
            domain: Alan filtresi.

        Returns:
            Bulunan terimler.
        """
        results: list[dict[str, Any]] = []
        query_lower = query.lower()

        domains = (
            {domain: self._glossaries[domain]}
            if domain and domain in self._glossaries
            else self._glossaries
        )

        for dom, glossary in domains.items():
            for term, translations in glossary.items():
                if query_lower in term.lower():
                    results.append({
                        "domain": dom,
                        "term": term,
                        "translations": translations,
                    })
                    continue
                for lang, trans in translations.items():
                    if query_lower in trans.lower():
                        results.append({
                            "domain": dom,
                            "term": term,
                            "translations": translations,
                        })
                        break

        return results

    def add_synonym(
        self,
        term: str,
        synonyms: list[str],
    ) -> None:
        """Es anlam ekler.

        Args:
            term: Ana terim.
            synonyms: Es anlamlar.
        """
        existing = self._synonyms.get(term, [])
        for syn in synonyms:
            if syn not in existing:
                existing.append(syn)
        self._synonyms[term] = existing

    def get_synonyms(self, term: str) -> list[str]:
        """Es anlamlari getirir.

        Args:
            term: Terim.

        Returns:
            Es anlam listesi.
        """
        return self._synonyms.get(term, [])

    def set_preferred(
        self,
        term: str,
        preferred: str,
    ) -> None:
        """Tercih edilen terimi ayarlar.

        Args:
            term: Orijinal terim.
            preferred: Tercih edilen terim.
        """
        self._preferred_terms[term] = preferred

    def get_preferred(self, term: str) -> str:
        """Tercih edilen terimi getirir.

        Args:
            term: Terim.

        Returns:
            Tercih edilen veya orijinal terim.
        """
        return self._preferred_terms.get(term, term)

    def create_custom_dict(
        self,
        name: str,
        entries: dict[str, str],
    ) -> dict[str, Any]:
        """Ozel sozluk olusturur.

        Args:
            name: Sozluk adi.
            entries: Girisler.

        Returns:
            Sozluk bilgisi.
        """
        self._custom_dicts[name] = entries
        return {
            "name": name,
            "entries": len(entries),
        }

    def lookup_custom(
        self,
        name: str,
        term: str,
    ) -> str | None:
        """Ozel sozlukte arar.

        Args:
            name: Sozluk adi.
            term: Terim.

        Returns:
            Ceviri veya None.
        """
        dictionary = self._custom_dicts.get(name, {})
        return dictionary.get(term)

    def extract_terms(
        self,
        text: str,
        domain: str,
    ) -> list[str]:
        """Metinden terimleri cikarir.

        Args:
            text: Metin.
            domain: Alan.

        Returns:
            Bulunan terimler.
        """
        glossary = self._glossaries.get(domain, {})
        text_lower = text.lower()
        found: list[str] = []

        for term in glossary:
            if term.lower() in text_lower:
                found.append(term)

        return found

    def get_glossary(
        self,
        domain: str,
    ) -> dict[str, dict[str, str]]:
        """Sozluk getirir.

        Args:
            domain: Alan.

        Returns:
            Sozluk.
        """
        return self._glossaries.get(domain, {})

    def remove_term(
        self,
        domain: str,
        term: str,
    ) -> bool:
        """Terim siler.

        Args:
            domain: Alan.
            term: Terim.

        Returns:
            Basarili ise True.
        """
        glossary = self._glossaries.get(domain, {})
        if term in glossary:
            del glossary[term]
            return True
        return False

    @property
    def glossary_count(self) -> int:
        """Sozluk sayisi."""
        return len(self._glossaries)

    @property
    def total_terms(self) -> int:
        """Toplam terim sayisi."""
        return sum(
            len(g) for g in self._glossaries.values()
        )

    @property
    def synonym_count(self) -> int:
        """Es anlam grubu sayisi."""
        return len(self._synonyms)

    @property
    def dict_count(self) -> int:
        """Ozel sozluk sayisi."""
        return len(self._custom_dicts)
