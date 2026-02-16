"""ATLAS Oyunlaştırma Motoru.

Puan sistemi, rozetler ve seviyeler,
sıralama tabloları, meydan okumalar ve ödüller.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class EngagementGamifier:
    """Oyunlaştırma motoru.

    Topluluk etkileşimini oyunlaştırma
    mekanikleri ile artırır.

    Attributes:
        _members: Üye oyun verileri.
        _challenges: Meydan okuma kayıtları.
        _badges: Rozet tanımları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Motoru başlatır."""
        self._members: dict[str, dict] = {}
        self._challenges: dict[str, dict] = {}
        self._badges: dict[str, dict] = {}
        self._stats = {
            "points_awarded": 0,
            "badges_awarded": 0,
            "challenges_created": 0,
        }
        logger.info(
            "EngagementGamifier baslatildi",
        )

    @property
    def total_points(self) -> int:
        """Verilen toplam puan."""
        return self._stats["points_awarded"]

    @property
    def badge_count(self) -> int:
        """Verilen rozet sayısı."""
        return self._stats["badges_awarded"]

    @property
    def challenge_count(self) -> int:
        """Oluşturulan meydan okuma sayısı."""
        return self._stats[
            "challenges_created"
        ]

    def award_points(
        self,
        member_id: str,
        points: int = 0,
        reason: str = "",
    ) -> dict[str, Any]:
        """Puan verir.

        Args:
            member_id: Üye kimliği.
            points: Puan miktarı.
            reason: Neden.

        Returns:
            Puan bilgisi.
        """
        if member_id not in self._members:
            self._members[member_id] = {
                "points": 0,
                "level": 1,
                "badges": [],
            }

        self._members[member_id][
            "points"
        ] += points
        total = self._members[member_id][
            "points"
        ]
        self._stats[
            "points_awarded"
        ] += points

        # Seviye hesapla
        level = total // 100 + 1
        self._members[member_id][
            "level"
        ] = level

        logger.info(
            "Puan verildi: %s +%d (%s)",
            member_id,
            points,
            reason,
        )

        return {
            "member_id": member_id,
            "points_added": points,
            "total_points": total,
            "level": level,
            "awarded": True,
        }

    def award_badge(
        self,
        member_id: str,
        badge_name: str,
        badge_type: str = "achievement",
    ) -> dict[str, Any]:
        """Rozet verir.

        Args:
            member_id: Üye kimliği.
            badge_name: Rozet adı.
            badge_type: Rozet tipi.

        Returns:
            Rozet bilgisi.
        """
        if member_id not in self._members:
            self._members[member_id] = {
                "points": 0,
                "level": 1,
                "badges": [],
            }

        self._members[member_id][
            "badges"
        ].append(badge_name)
        self._stats["badges_awarded"] += 1

        return {
            "member_id": member_id,
            "badge_name": badge_name,
            "badge_type": badge_type,
            "total_badges": len(
                self._members[member_id][
                    "badges"
                ],
            ),
            "awarded": True,
        }

    def get_leaderboard(
        self,
        limit: int = 10,
        metric: str = "points",
    ) -> dict[str, Any]:
        """Sıralama tablosu döndürür.

        Args:
            limit: Limit.
            metric: Sıralama metriği.

        Returns:
            Sıralama bilgisi.
        """
        sorted_members = sorted(
            self._members.items(),
            key=lambda x: x[1].get(
                metric, 0,
            ),
            reverse=True,
        )

        board = [
            {
                "rank": i + 1,
                "member_id": mid,
                metric: data.get(metric, 0),
            }
            for i, (mid, data) in enumerate(
                sorted_members[:limit],
            )
        ]

        return {
            "metric": metric,
            "entries": board,
            "total_members": len(
                self._members,
            ),
            "retrieved": True,
        }

    def create_challenge(
        self,
        challenge_name: str,
        target_action: str = "",
        target_count: int = 1,
        reward_points: int = 50,
    ) -> dict[str, Any]:
        """Meydan okuma oluşturur.

        Args:
            challenge_name: Meydan okuma adı.
            target_action: Hedef aksiyon.
            target_count: Hedef sayı.
            reward_points: Ödül puanı.

        Returns:
            Meydan okuma bilgisi.
        """
        cid = (
            f"ch_{len(self._challenges)}"
        )
        self._challenges[cid] = {
            "name": challenge_name,
            "target_action": target_action,
            "target_count": target_count,
            "reward_points": reward_points,
            "status": "active",
        }
        self._stats[
            "challenges_created"
        ] += 1

        return {
            "challenge_id": cid,
            "name": challenge_name,
            "target_action": target_action,
            "target_count": target_count,
            "reward_points": reward_points,
            "created": True,
        }

    def claim_reward(
        self,
        member_id: str,
        reward_type: str = "discount",
        points_cost: int = 0,
    ) -> dict[str, Any]:
        """Ödül talep eder.

        Args:
            member_id: Üye kimliği.
            reward_type: Ödül tipi.
            points_cost: Puan maliyeti.

        Returns:
            Ödül bilgisi.
        """
        current = self._members.get(
            member_id, {},
        ).get("points", 0)
        affordable = current >= points_cost

        if affordable and member_id in (
            self._members
        ):
            self._members[member_id][
                "points"
            ] -= points_cost

        return {
            "member_id": member_id,
            "reward_type": reward_type,
            "points_cost": points_cost,
            "affordable": affordable,
            "remaining_points": (
                self._members.get(
                    member_id, {},
                ).get("points", 0)
            ),
            "claimed": affordable,
        }
