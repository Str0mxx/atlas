"""ATLAS Kolektif Hafiza modulu.

Paylasilan bilgi tabani, dagitik depolama,
olgular uzerinde konsensus ve hafiza senkronizasyonu.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class CollectiveMemory:
    """Kolektif hafiza sistemi.

    Surulerin paylasilan bilgi tabanini yonetir,
    catismalari cozer ve senkronizasyon saglar.

    Attributes:
        _knowledge: Bilgi tabani (key -> value).
        _contributors: Katkilar (key -> agent listesi).
        _confidence: Guven puanlari (key -> puan).
        _history: Degisiklik gecmisi.
    """

    def __init__(self) -> None:
        """Kolektif hafizayi baslatir."""
        self._knowledge: dict[str, Any] = {}
        self._contributors: dict[str, list[str]] = {}
        self._confidence: dict[str, float] = {}
        self._history: list[dict[str, Any]] = []

        logger.info("CollectiveMemory baslatildi")

    def store(
        self,
        key: str,
        value: Any,
        agent_id: str = "",
        confidence: float = 1.0,
    ) -> bool:
        """Bilgi depolar.

        Args:
            key: Anahtar.
            value: Deger.
            agent_id: Katkida bulunan agent.
            confidence: Guven puani.

        Returns:
            Basarili ise True.
        """
        is_new = key not in self._knowledge
        self._knowledge[key] = value
        self._confidence[key] = min(1.0, max(0.0, confidence))

        if key not in self._contributors:
            self._contributors[key] = []
        if agent_id and agent_id not in self._contributors[key]:
            self._contributors[key].append(agent_id)

        self._history.append({
            "action": "store",
            "key": key,
            "agent_id": agent_id,
            "is_new": is_new,
        })

        return True

    def retrieve(self, key: str) -> Any:
        """Bilgi getirir.

        Args:
            key: Anahtar.

        Returns:
            Deger veya None.
        """
        return self._knowledge.get(key)

    def retrieve_with_confidence(
        self, key: str,
    ) -> tuple[Any, float]:
        """Guven puaniyla bilgi getirir.

        Args:
            key: Anahtar.

        Returns:
            (deger, guven) ikilisi.
        """
        value = self._knowledge.get(key)
        confidence = self._confidence.get(key, 0.0)
        return value, confidence

    def delete(self, key: str) -> bool:
        """Bilgi siler.

        Args:
            key: Anahtar.

        Returns:
            Basarili ise True.
        """
        if key not in self._knowledge:
            return False

        del self._knowledge[key]
        self._confidence.pop(key, None)
        self._contributors.pop(key, None)
        return True

    def search(self, pattern: str) -> dict[str, Any]:
        """Kaliba gore arar.

        Args:
            pattern: Arama kalibi (icerir).

        Returns:
            Eslesen bilgiler.
        """
        results: dict[str, Any] = {}
        pattern_lower = pattern.lower()
        for key, value in self._knowledge.items():
            if pattern_lower in key.lower():
                results[key] = value
        return results

    def merge(
        self,
        other_knowledge: dict[str, Any],
        agent_id: str = "",
        conflict_strategy: str = "higher_confidence",
    ) -> int:
        """Baska bilgi tabanini birlestirir.

        Args:
            other_knowledge: Baska bilgi tabani.
            agent_id: Katkida bulunan agent.
            conflict_strategy: Catisma stratejisi.

        Returns:
            Birlestirilen bilgi sayisi.
        """
        merged = 0
        for key, value in other_knowledge.items():
            if key not in self._knowledge:
                self.store(key, value, agent_id)
                merged += 1
            elif conflict_strategy == "overwrite":
                self.store(key, value, agent_id)
                merged += 1
            elif conflict_strategy == "higher_confidence":
                # Yeni veri ekle, guven artir
                current_conf = self._confidence.get(key, 0.5)
                if current_conf < 0.8:
                    self.store(key, value, agent_id, current_conf + 0.1)
                    merged += 1

        return merged

    def vote_on_fact(
        self,
        key: str,
        proposals: dict[str, Any],
    ) -> Any:
        """Olgu uzerinde oylama yapar.

        Args:
            key: Anahtar.
            proposals: Agent -> onerilen deger.

        Returns:
            Kazanan deger.
        """
        if not proposals:
            return None

        # En cok oylanan degeri bul
        vote_count: dict[str, int] = {}
        value_map: dict[str, Any] = {}
        for agent_id, value in proposals.items():
            val_str = str(value)
            vote_count[val_str] = vote_count.get(val_str, 0) + 1
            value_map[val_str] = value

        winner_str = max(vote_count, key=vote_count.get)
        winner_value = value_map[winner_str]

        # Guven = oy orani
        confidence = vote_count[winner_str] / len(proposals)
        self.store(key, winner_value, confidence=confidence)

        return winner_value

    def get_contributors(self, key: str) -> list[str]:
        """Katkida bulunan agent'lari getirir.

        Args:
            key: Anahtar.

        Returns:
            Agent ID listesi.
        """
        return list(self._contributors.get(key, []))

    def get_high_confidence(
        self, threshold: float = 0.8,
    ) -> dict[str, Any]:
        """Yuksek guvenli bilgileri getirir.

        Args:
            threshold: Guven esigi.

        Returns:
            Bilgi sozlugu.
        """
        return {
            key: self._knowledge[key]
            for key, conf in self._confidence.items()
            if conf >= threshold and key in self._knowledge
        }

    def get_history(
        self, limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Degisiklik gecmisini getirir.

        Args:
            limit: Maks kayit.

        Returns:
            Gecmis listesi.
        """
        return self._history[-limit:]

    @property
    def size(self) -> int:
        """Bilgi tabani boyutu."""
        return len(self._knowledge)

    @property
    def avg_confidence(self) -> float:
        """Ortalama guven puani."""
        if not self._confidence:
            return 0.0
        return sum(self._confidence.values()) / len(self._confidence)
