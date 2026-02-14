"""ATLAS Transfer Ogrenici modulu.

Alanlar arasi ogrenme, yetenek
transferi, bilgi yeniden kullanimi,
analoji tespiti ve adaptasyon kurallari.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class TransferLearner:
    """Transfer ogrenici.

    Bir alandaki bilgiyi baska alanlara
    transfer eder ve yeniden kullanir.

    Attributes:
        _domains: Alan kayitlari.
        _transfers: Transfer gecmisi.
        _analogies: Analoji deposu.
        _adaptation_rules: Adaptasyon kurallari.
    """

    def __init__(self) -> None:
        """Transfer ogrenicisini baslatir."""
        self._domains: dict[str, dict[str, Any]] = {}
        self._transfers: list[dict[str, Any]] = []
        self._analogies: list[dict[str, Any]] = []
        self._adaptation_rules: list[dict[str, Any]] = []

        logger.info("TransferLearner baslatildi")

    def register_domain(
        self,
        name: str,
        skills: list[str],
        knowledge: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Alan kaydeder.

        Args:
            name: Alan adi.
            skills: Yetenekler.
            knowledge: Bilgi tabani.

        Returns:
            Alan bilgisi.
        """
        domain = {
            "name": name,
            "skills": list(skills),
            "knowledge": knowledge or {},
            "transfer_count": 0,
        }
        self._domains[name] = domain
        return domain

    def find_transferable_skills(
        self,
        source_domain: str,
        target_domain: str,
    ) -> list[str]:
        """Transfer edilebilir yetenekleri bulur.

        Args:
            source_domain: Kaynak alan.
            target_domain: Hedef alan.

        Returns:
            Transfer edilebilir yetenekler.
        """
        source = self._domains.get(source_domain)
        target = self._domains.get(target_domain)
        if not source or not target:
            return []

        # Ortak yetenekler
        source_skills = set(source["skills"])
        target_skills = set(target["skills"])
        common = source_skills & target_skills

        # Benzer isimli (prefix/suffix eslesmesi)
        for s_skill in source_skills - common:
            for t_skill in target_skills - common:
                if (s_skill in t_skill or t_skill in s_skill):
                    common.add(s_skill)

        return list(common)

    def transfer_knowledge(
        self,
        source_domain: str,
        target_domain: str,
        knowledge_keys: list[str] | None = None,
    ) -> dict[str, Any]:
        """Bilgi transfer eder.

        Args:
            source_domain: Kaynak alan.
            target_domain: Hedef alan.
            knowledge_keys: Transfer edilecek anahtarlar.

        Returns:
            Transfer sonucu.
        """
        source = self._domains.get(source_domain)
        target = self._domains.get(target_domain)
        if not source or not target:
            return {
                "success": False,
                "error": "Alan bulunamadi",
            }

        keys = knowledge_keys or list(source["knowledge"].keys())
        transferred: dict[str, Any] = {}

        for key in keys:
            if key in source["knowledge"]:
                value = source["knowledge"][key]
                # Adaptasyon kurali uygula
                adapted = self._apply_adaptation(
                    key, value, source_domain, target_domain,
                )
                target["knowledge"][key] = adapted
                transferred[key] = adapted

        source["transfer_count"] += 1
        transfer_record = {
            "source": source_domain,
            "target": target_domain,
            "keys": list(transferred.keys()),
            "count": len(transferred),
        }
        self._transfers.append(transfer_record)

        return {
            "success": True,
            "transferred": len(transferred),
            "keys": list(transferred.keys()),
        }

    def detect_analogy(
        self,
        concept_a: str,
        domain_a: str,
        domain_b: str,
    ) -> dict[str, Any] | None:
        """Analoji tespit eder.

        Args:
            concept_a: Kaynak kavram.
            domain_a: Kaynak alan.
            domain_b: Hedef alan.

        Returns:
            Analoji bilgisi veya None.
        """
        da = self._domains.get(domain_a)
        db = self._domains.get(domain_b)
        if not da or not db:
            return None

        # Bilgi anahtarlarinda benzerlik ara
        target_match = None
        if concept_a in da.get("knowledge", {}):
            for key in db.get("knowledge", {}):
                if concept_a in key or key in concept_a:
                    target_match = key
                    break

        if not target_match:
            # Yetenek benzerligi
            for skill in db["skills"]:
                if concept_a in skill or skill in concept_a:
                    target_match = skill
                    break

        if target_match:
            analogy = {
                "source_concept": concept_a,
                "source_domain": domain_a,
                "target_concept": target_match,
                "target_domain": domain_b,
                "similarity": 0.7,
            }
            self._analogies.append(analogy)
            return analogy

        return None

    def add_adaptation_rule(
        self,
        source_pattern: str,
        target_pattern: str,
        transform: str = "direct",
    ) -> dict[str, Any]:
        """Adaptasyon kurali ekler.

        Args:
            source_pattern: Kaynak deseni.
            target_pattern: Hedef deseni.
            transform: Donusum turu.

        Returns:
            Kural bilgisi.
        """
        rule = {
            "source_pattern": source_pattern,
            "target_pattern": target_pattern,
            "transform": transform,
            "usage_count": 0,
        }
        self._adaptation_rules.append(rule)
        return rule

    def get_domain_similarity(
        self,
        domain_a: str,
        domain_b: str,
    ) -> float:
        """Alan benzerligini hesaplar.

        Args:
            domain_a: Birinci alan.
            domain_b: Ikinci alan.

        Returns:
            Benzerlik skoru (0.0-1.0).
        """
        da = self._domains.get(domain_a)
        db = self._domains.get(domain_b)
        if not da or not db:
            return 0.0

        skills_a = set(da["skills"])
        skills_b = set(db["skills"])

        if not skills_a and not skills_b:
            return 0.0

        union = skills_a | skills_b
        if not union:
            return 0.0

        intersection = skills_a & skills_b
        # Jaccard similarity
        return len(intersection) / len(union)

    def _apply_adaptation(
        self,
        key: str,
        value: Any,
        source_domain: str,
        target_domain: str,
    ) -> Any:
        """Adaptasyon kurali uygular.

        Args:
            key: Anahtar.
            value: Deger.
            source_domain: Kaynak alan.
            target_domain: Hedef alan.

        Returns:
            Adapte edilmis deger.
        """
        for rule in self._adaptation_rules:
            if rule["source_pattern"] in key:
                rule["usage_count"] += 1
                if rule["transform"] == "scale":
                    if isinstance(value, (int, float)):
                        return value * 0.8
                # Diger transformlar icin direkt kopyala
                return value
        return value

    @property
    def domain_count(self) -> int:
        """Alan sayisi."""
        return len(self._domains)

    @property
    def transfer_count(self) -> int:
        """Transfer sayisi."""
        return len(self._transfers)

    @property
    def analogy_count(self) -> int:
        """Analoji sayisi."""
        return len(self._analogies)

    @property
    def rule_count(self) -> int:
        """Adaptasyon kurali sayisi."""
        return len(self._adaptation_rules)
