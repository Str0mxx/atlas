"""ATLAS Katkı Yöneticisi modülü.

Katkı takibi, inceleme iş akışı,
kalite puanlama, oyunlaştırma,
atıf.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class KBContributor:
    """Katkı yöneticisi.

    Bilgi tabanı katkılarını yönetir.

    Attributes:
        _contributors: Katkıcı kayıtları.
        _reviews: İnceleme kayıtları.
    """

    def __init__(self) -> None:
        """Katkı yöneticisini başlatır."""
        self._contributors: dict[
            str, dict[str, Any]
        ] = {}
        self._contributions: list[
            dict[str, Any]
        ] = []
        self._reviews: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "contributions_tracked": 0,
            "reviews_completed": 0,
        }

        logger.info(
            "KBContributor baslatildi",
        )

    def track_contribution(
        self,
        contributor: str,
        page_id: str,
        contribution_type: str = "edit",
        content_size: int = 0,
    ) -> dict[str, Any]:
        """Katkı takibi yapar.

        Args:
            contributor: Katkıcı.
            page_id: Sayfa kimliği.
            contribution_type: Katkı tipi.
            content_size: İçerik boyutu.

        Returns:
            Takip bilgisi.
        """
        self._counter += 1
        cid = f"ctr_{self._counter}"

        self._contributions.append({
            "contribution_id": cid,
            "contributor": contributor,
            "page_id": page_id,
            "type": contribution_type,
            "content_size": content_size,
            "timestamp": time.time(),
        })

        if (
            contributor
            not in self._contributors
        ):
            self._contributors[
                contributor
            ] = {
                "name": contributor,
                "contributions": 0,
                "points": 0,
                "badges": [],
                "quality_avg": 0.0,
            }

        profile = self._contributors[
            contributor
        ]
        profile["contributions"] += 1

        points_map = {
            "create": 10,
            "edit": 5,
            "review": 3,
            "delete": 1,
        }
        profile["points"] += points_map.get(
            contribution_type, 1,
        )

        self._stats[
            "contributions_tracked"
        ] += 1

        return {
            "contribution_id": cid,
            "contributor": contributor,
            "points_earned": (
                points_map.get(
                    contribution_type, 1,
                )
            ),
            "tracked": True,
        }

    def review_contribution(
        self,
        contribution_id: str = "",
        reviewer: str = "",
        verdict: str = "approved",
        feedback: str = "",
    ) -> dict[str, Any]:
        """Katkı inceler.

        Args:
            contribution_id: Katkı kimliği.
            reviewer: İnceleyici.
            verdict: Karar.
            feedback: Geri bildirim.

        Returns:
            İnceleme bilgisi.
        """
        self._counter += 1
        rid = f"rev_{self._counter}"

        self._reviews.append({
            "review_id": rid,
            "contribution_id": (
                contribution_id
            ),
            "reviewer": reviewer,
            "verdict": verdict,
            "feedback": feedback,
            "timestamp": time.time(),
        })

        self._stats[
            "reviews_completed"
        ] += 1

        return {
            "review_id": rid,
            "verdict": verdict,
            "reviewed": True,
        }

    def score_quality(
        self,
        contributor: str,
    ) -> dict[str, Any]:
        """Kalite puanlama yapar.

        Args:
            contributor: Katkıcı.

        Returns:
            Puanlama bilgisi.
        """
        profile = self._contributors.get(
            contributor,
        )
        if not profile:
            return {
                "contributor": contributor,
                "found": False,
            }

        total = profile["contributions"]
        reviews_for = [
            r for r in self._reviews
            if any(
                c["contributor"]
                == contributor
                for c in (
                    self._contributions
                )
                if c["contribution_id"]
                == r.get(
                    "contribution_id", "",
                )
            )
        ]

        approved = sum(
            1 for r in reviews_for
            if r["verdict"] == "approved"
        )
        quality = round(
            approved
            / max(len(reviews_for), 1),
            2,
        )

        profile["quality_avg"] = quality

        return {
            "contributor": contributor,
            "total_contributions": total,
            "quality_score": quality,
            "reviews_received": len(
                reviews_for,
            ),
            "scored": True,
        }

    def get_gamification(
        self,
        contributor: str,
    ) -> dict[str, Any]:
        """Oyunlaştırma bilgisi verir.

        Args:
            contributor: Katkıcı.

        Returns:
            Oyunlaştırma bilgisi.
        """
        profile = self._contributors.get(
            contributor,
        )
        if not profile:
            return {
                "contributor": contributor,
                "found": False,
            }

        points = profile["points"]
        badges = list(profile["badges"])

        if (
            points >= 50
            and "prolific" not in badges
        ):
            badges.append("prolific")
        if (
            points >= 100
            and "expert" not in badges
        ):
            badges.append("expert")
        if (
            profile["contributions"] >= 10
            and "dedicated"
            not in badges
        ):
            badges.append("dedicated")

        profile["badges"] = badges

        level = (
            "expert" if points >= 100
            else "intermediate"
            if points >= 50
            else "beginner"
        )

        return {
            "contributor": contributor,
            "points": points,
            "level": level,
            "badges": badges,
            "contributions": profile[
                "contributions"
            ],
            "retrieved": True,
        }

    def get_attribution(
        self,
        page_id: str,
    ) -> dict[str, Any]:
        """Atıf bilgisi verir.

        Args:
            page_id: Sayfa kimliği.

        Returns:
            Atıf bilgisi.
        """
        page_contribs = [
            c for c in self._contributions
            if c["page_id"] == page_id
        ]

        authors: dict[str, int] = {}
        for c in page_contribs:
            name = c["contributor"]
            authors[name] = (
                authors.get(name, 0) + 1
            )

        sorted_authors = sorted(
            authors.items(),
            key=lambda x: x[1],
            reverse=True,
        )

        return {
            "page_id": page_id,
            "authors": [
                {
                    "name": name,
                    "edits": count,
                }
                for name, count
                in sorted_authors
            ],
            "total_edits": len(
                page_contribs,
            ),
            "retrieved": True,
        }

    @property
    def contribution_count(self) -> int:
        """Katkı sayısı."""
        return self._stats[
            "contributions_tracked"
        ]

    @property
    def review_count(self) -> int:
        """İnceleme sayısı."""
        return self._stats[
            "reviews_completed"
        ]
