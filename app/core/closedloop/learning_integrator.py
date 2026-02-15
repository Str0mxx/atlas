"""ATLAS Ogrenme Entegratoru modulu.

Strateji guncelleme, basarilari pekistirme,
basarisizliklardan kacinma, kalip cikarma, bilgi guncelleme.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class LearningIntegrator:
    """Ogrenme entegratoru.

    Dongu sonuclarindan ogrenme cikarir.

    Attributes:
        _learnings: Ogrenme kayitlari.
        _strategies: Strateji kayitlari.
    """

    def __init__(
        self,
        min_confidence: float = 0.5,
    ) -> None:
        """Ogrenme entegratorunu baslatir.

        Args:
            min_confidence: Minimum guven esigi.
        """
        self._learnings: list[
            dict[str, Any]
        ] = []
        self._strategies: dict[
            str, dict[str, Any]
        ] = {}
        self._patterns: dict[
            str, dict[str, Any]
        ] = {}
        self._reinforcements: dict[
            str, dict[str, Any]
        ] = {}
        self._avoidances: dict[
            str, dict[str, Any]
        ] = {}
        self._knowledge: dict[
            str, dict[str, Any]
        ] = {}
        self._min_confidence = min_confidence
        self._stats = {
            "learnings": 0,
            "reinforced": 0,
            "avoided": 0,
            "patterns": 0,
        }

        logger.info(
            "LearningIntegrator baslatildi",
        )

    def record_learning(
        self,
        action_id: str,
        outcome_type: str,
        confidence: float,
        insight: str = "",
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Ogrenme kaydeder.

        Args:
            action_id: Aksiyon ID.
            outcome_type: Sonuc tipi.
            confidence: Guven.
            insight: Icegorü.
            data: Ek veri.

        Returns:
            Kayit bilgisi.
        """
        learning = {
            "action_id": action_id,
            "outcome_type": outcome_type,
            "confidence": confidence,
            "insight": insight,
            "data": data or {},
            "applied": False,
            "timestamp": time.time(),
        }

        self._learnings.append(learning)
        self._stats["learnings"] += 1

        # Otomatik pekistirme/kacinma
        if confidence >= self._min_confidence:
            if outcome_type == "success":
                self._reinforce(
                    action_id, confidence,
                )
            elif outcome_type == "failure":
                self._mark_avoidance(
                    action_id, confidence,
                )

        return {
            "action_id": action_id,
            "outcome_type": outcome_type,
            "confidence": confidence,
            "recorded": True,
        }

    def update_strategy(
        self,
        strategy_id: str,
        adjustments: dict[str, Any],
        reason: str = "",
    ) -> dict[str, Any]:
        """Strateji gunceller.

        Args:
            strategy_id: Strateji ID.
            adjustments: Ayarlamalar.
            reason: Neden.

        Returns:
            Guncelleme bilgisi.
        """
        if strategy_id not in self._strategies:
            self._strategies[strategy_id] = {
                "strategy_id": strategy_id,
                "adjustments": [],
                "version": 0,
                "created_at": time.time(),
            }

        strategy = self._strategies[strategy_id]
        strategy["adjustments"].append({
            "changes": adjustments,
            "reason": reason,
            "timestamp": time.time(),
        })
        strategy["version"] += 1
        strategy["last_updated"] = time.time()

        return {
            "strategy_id": strategy_id,
            "version": strategy["version"],
            "updated": True,
        }

    def reinforce_success(
        self,
        action_id: str,
        strength: float = 1.0,
    ) -> dict[str, Any]:
        """Basariyi pekistirir.

        Args:
            action_id: Aksiyon ID.
            strength: Pekistirme gucu.

        Returns:
            Pekistirme bilgisi.
        """
        return self._reinforce(
            action_id, strength,
        )

    def avoid_failure(
        self,
        action_id: str,
        severity: float = 1.0,
    ) -> dict[str, Any]:
        """Basarisizliktan kacinmayi kaydeder.

        Args:
            action_id: Aksiyon ID.
            severity: Ciddiyet.

        Returns:
            Kacinma bilgisi.
        """
        return self._mark_avoidance(
            action_id, severity,
        )

    def extract_pattern(
        self,
        pattern_name: str,
        action_ids: list[str],
        description: str = "",
    ) -> dict[str, Any]:
        """Kalip cikarir.

        Args:
            pattern_name: Kalip adi.
            action_ids: Aksiyon ID listesi.
            description: Aciklama.

        Returns:
            Kalip bilgisi.
        """
        # Ilgili ogrenimleri topla
        related = [
            l for l in self._learnings
            if l["action_id"] in action_ids
        ]

        success_count = sum(
            1
            for l in related
            if l["outcome_type"] == "success"
        )
        total = len(related) if related else 1
        success_rate = success_count / total

        avg_conf = (
            sum(l["confidence"] for l in related)
            / total
            if related
            else 0.0
        )

        pattern = {
            "pattern_name": pattern_name,
            "action_ids": action_ids,
            "description": description,
            "success_rate": round(
                success_rate, 2,
            ),
            "avg_confidence": round(avg_conf, 2),
            "sample_size": total,
            "created_at": time.time(),
        }

        self._patterns[pattern_name] = pattern
        self._stats["patterns"] += 1

        return {
            "pattern_name": pattern_name,
            "success_rate": pattern["success_rate"],
            "avg_confidence": pattern[
                "avg_confidence"
            ],
            "extracted": True,
        }

    def update_knowledge(
        self,
        key: str,
        value: Any,
        source: str = "learning",
    ) -> dict[str, Any]:
        """Bilgiyi gunceller.

        Args:
            key: Bilgi anahtari.
            value: Deger.
            source: Kaynak.

        Returns:
            Guncelleme bilgisi.
        """
        prev = self._knowledge.get(key)

        self._knowledge[key] = {
            "value": value,
            "source": source,
            "version": (
                prev["version"] + 1 if prev else 1
            ),
            "updated_at": time.time(),
        }

        return {
            "key": key,
            "version": self._knowledge[key][
                "version"
            ],
            "updated": True,
        }

    def get_knowledge(
        self,
        key: str,
    ) -> dict[str, Any] | None:
        """Bilgiyi getirir.

        Args:
            key: Bilgi anahtari.

        Returns:
            Bilgi veya None.
        """
        return self._knowledge.get(key)

    def get_reinforcements(
        self,
    ) -> dict[str, dict[str, Any]]:
        """Pekistirmeleri getirir.

        Returns:
            Pekistirme kayitlari.
        """
        return dict(self._reinforcements)

    def get_avoidances(
        self,
    ) -> dict[str, dict[str, Any]]:
        """Kacinmalari getirir.

        Returns:
            Kacinma kayitlari.
        """
        return dict(self._avoidances)

    def get_pattern(
        self,
        pattern_name: str,
    ) -> dict[str, Any] | None:
        """Kalibi getirir.

        Args:
            pattern_name: Kalip adi.

        Returns:
            Kalip verisi veya None.
        """
        return self._patterns.get(pattern_name)

    def _reinforce(
        self,
        action_id: str,
        strength: float,
    ) -> dict[str, Any]:
        """Basariyi pekistirir (dahili).

        Args:
            action_id: Aksiyon ID.
            strength: Guc.

        Returns:
            Pekistirme bilgisi.
        """
        if action_id in self._reinforcements:
            r = self._reinforcements[action_id]
            r["strength"] = min(
                1.0, r["strength"] + strength * 0.1,
            )
            r["count"] += 1
        else:
            self._reinforcements[action_id] = {
                "action_id": action_id,
                "strength": min(1.0, strength),
                "count": 1,
                "first_at": time.time(),
            }
            self._stats["reinforced"] += 1

        return {
            "action_id": action_id,
            "type": "reinforcement",
            "strength": self._reinforcements[
                action_id
            ]["strength"],
        }

    def _mark_avoidance(
        self,
        action_id: str,
        severity: float,
    ) -> dict[str, Any]:
        """Kacinma isaret eder (dahili).

        Args:
            action_id: Aksiyon ID.
            severity: Ciddiyet.

        Returns:
            Kacinma bilgisi.
        """
        if action_id in self._avoidances:
            a = self._avoidances[action_id]
            a["severity"] = min(
                1.0, a["severity"] + severity * 0.1,
            )
            a["count"] += 1
        else:
            self._avoidances[action_id] = {
                "action_id": action_id,
                "severity": min(1.0, severity),
                "count": 1,
                "first_at": time.time(),
            }
            self._stats["avoided"] += 1

        return {
            "action_id": action_id,
            "type": "avoidance",
            "severity": self._avoidances[
                action_id
            ]["severity"],
        }

    @property
    def learning_count(self) -> int:
        """Ogrenme sayisi."""
        return len(self._learnings)

    @property
    def strategy_count(self) -> int:
        """Strateji sayisi."""
        return len(self._strategies)

    @property
    def pattern_count(self) -> int:
        """Kalip sayisi."""
        return len(self._patterns)

    @property
    def knowledge_count(self) -> int:
        """Bilgi sayisi."""
        return len(self._knowledge)
