"""ATLAS Müzakere Hafızası modülü.

Geçmiş takibi, taraf profilleri,
geçmiş sonuçlar, örüntü öğrenme,
en iyi uygulamalar.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class NegotiationMemory:
    """Müzakere hafızası.

    Müzakere geçmişini saklar ve öğrenir.

    Attributes:
        _negotiations: Müzakere kayıtları.
        _party_profiles: Taraf profilleri.
    """

    def __init__(self) -> None:
        """Hafızayı başlatır."""
        self._negotiations: dict[
            str, dict[str, Any]
        ] = {}
        self._party_profiles: dict[
            str, dict[str, Any]
        ] = {}
        self._outcomes: list[
            dict[str, Any]
        ] = []
        self._best_practices: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "negotiations_stored": 0,
            "profiles_created": 0,
            "patterns_learned": 0,
            "practices_added": 0,
        }

        logger.info(
            "NegotiationMemory baslatildi",
        )

    def store_negotiation(
        self,
        negotiation_id: str,
        parties: list[str],
        outcome: str = "pending",
        strategy: str = "",
        final_value: float = 0.0,
        rounds: int = 0,
        notes: str = "",
    ) -> dict[str, Any]:
        """Müzakere kaydeder.

        Args:
            negotiation_id: Müzakere ID.
            parties: Taraflar.
            outcome: Sonuç.
            strategy: Strateji.
            final_value: Son değer.
            rounds: Tur sayısı.
            notes: Notlar.

        Returns:
            Kayıt bilgisi.
        """
        record = {
            "negotiation_id": (
                negotiation_id
            ),
            "parties": parties,
            "outcome": outcome,
            "strategy": strategy,
            "final_value": final_value,
            "rounds": rounds,
            "notes": notes,
            "timestamp": time.time(),
        }
        self._negotiations[
            negotiation_id
        ] = record

        if outcome != "pending":
            self._outcomes.append(record)

        self._stats[
            "negotiations_stored"
        ] += 1

        return {
            "negotiation_id": (
                negotiation_id
            ),
            "stored": True,
        }

    def create_party_profile(
        self,
        party_name: str,
        style: str = "unknown",
        preferences: (
            dict[str, Any] | None
        ) = None,
        history_summary: str = "",
    ) -> dict[str, Any]:
        """Taraf profili oluşturur.

        Args:
            party_name: Taraf adı.
            style: Müzakere stili.
            preferences: Tercihler.
            history_summary: Geçmiş özeti.

        Returns:
            Profil bilgisi.
        """
        profile = {
            "name": party_name,
            "style": style,
            "preferences": preferences or {},
            "history_summary": (
                history_summary
            ),
            "negotiations_count": 0,
            "win_rate": 0.0,
            "avg_concession": 0.0,
            "created_at": time.time(),
            "updated_at": time.time(),
        }
        self._party_profiles[
            party_name
        ] = profile
        self._stats[
            "profiles_created"
        ] += 1

        return {
            "name": party_name,
            "style": style,
            "created": True,
        }

    def update_party_profile(
        self,
        party_name: str,
        outcome: str = "",
        concession_avg: float = 0.0,
        new_insight: str = "",
    ) -> dict[str, Any]:
        """Profil günceller.

        Args:
            party_name: Taraf adı.
            outcome: Son sonuç.
            concession_avg: Ortalama taviz.
            new_insight: Yeni bilgi.

        Returns:
            Güncelleme bilgisi.
        """
        if (
            party_name
            not in self._party_profiles
        ):
            return {
                "name": party_name,
                "updated": False,
                "reason": "not_found",
            }

        profile = self._party_profiles[
            party_name
        ]
        profile[
            "negotiations_count"
        ] += 1
        profile[
            "updated_at"
        ] = time.time()

        if concession_avg > 0:
            old = profile["avg_concession"]
            count = profile[
                "negotiations_count"
            ]
            profile["avg_concession"] = (
                round(
                    (
                        old * (count - 1)
                        + concession_avg
                    )
                    / count, 2,
                )
            )

        if new_insight:
            insights = profile.get(
                "insights", [],
            )
            insights.append(new_insight)
            profile["insights"] = insights

        return {
            "name": party_name,
            "negotiations": profile[
                "negotiations_count"
            ],
            "updated": True,
        }

    def get_past_outcomes(
        self,
        party: str = "",
        strategy: str = "",
        limit: int = 10,
    ) -> dict[str, Any]:
        """Geçmiş sonuçları döndürür.

        Args:
            party: Taraf filtresi.
            strategy: Strateji filtresi.
            limit: Limit.

        Returns:
            Sonuç bilgisi.
        """
        results = self._outcomes

        if party:
            results = [
                r for r in results
                if party in r.get(
                    "parties", [],
                )
            ]

        if strategy:
            results = [
                r for r in results
                if r.get("strategy")
                == strategy
            ]

        results = results[-limit:]

        # İstatistikler
        total = len(results)
        won = sum(
            1 for r in results
            if r.get("outcome") == "won"
        )
        win_rate = round(
            won / max(total, 1) * 100, 1,
        )

        return {
            "outcomes": results,
            "total": total,
            "won": won,
            "win_rate": win_rate,
        }

    def learn_pattern(
        self,
        pattern_type: str,
        description: str,
        success_rate: float = 0.0,
        context: str = "",
    ) -> dict[str, Any]:
        """Örüntü öğrenir.

        Args:
            pattern_type: Örüntü tipi.
            description: Açıklama.
            success_rate: Başarı oranı.
            context: Bağlam.

        Returns:
            Örüntü bilgisi.
        """
        self._counter += 1
        pid = f"pattern_{self._counter}"

        pattern = {
            "pattern_id": pid,
            "type": pattern_type,
            "description": description,
            "success_rate": success_rate,
            "context": context,
            "observations": 1,
            "timestamp": time.time(),
        }

        self._stats[
            "patterns_learned"
        ] += 1

        return {
            "pattern_id": pid,
            "type": pattern_type,
            "success_rate": success_rate,
            "learned": True,
        }

    def add_best_practice(
        self,
        title: str,
        description: str,
        category: str = "general",
        effectiveness: float = 0.0,
    ) -> dict[str, Any]:
        """En iyi uygulama ekler.

        Args:
            title: Başlık.
            description: Açıklama.
            category: Kategori.
            effectiveness: Etkinlik.

        Returns:
            Uygulama bilgisi.
        """
        self._counter += 1
        bid = f"bp_{self._counter}"

        practice = {
            "practice_id": bid,
            "title": title,
            "description": description,
            "category": category,
            "effectiveness": effectiveness,
            "timestamp": time.time(),
        }
        self._best_practices.append(
            practice,
        )
        self._stats[
            "practices_added"
        ] += 1

        return {
            "practice_id": bid,
            "title": title,
            "added": True,
        }

    def get_party_profile(
        self,
        party_name: str,
    ) -> dict[str, Any] | None:
        """Taraf profili döndürür."""
        return self._party_profiles.get(
            party_name,
        )

    def get_negotiation(
        self,
        negotiation_id: str,
    ) -> dict[str, Any] | None:
        """Müzakere bilgisi döndürür."""
        return self._negotiations.get(
            negotiation_id,
        )

    @property
    def negotiation_count(self) -> int:
        """Müzakere sayısı."""
        return self._stats[
            "negotiations_stored"
        ]

    @property
    def profile_count(self) -> int:
        """Profil sayısı."""
        return self._stats[
            "profiles_created"
        ]

    @property
    def practice_count(self) -> int:
        """Uygulama sayısı."""
        return self._stats[
            "practices_added"
        ]
