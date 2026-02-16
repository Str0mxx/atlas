"""ATLAS İzleyici Segmentleyici.

Demografik, davranışsal, ilgi alanı,
değer tabanlı ve dinamik segmentasyon.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class AudienceSegmenter:
    """İzleyici segmentleyici.

    İzleyici kitlesini çeşitli kriterlere
    göre segmentlere ayırır.

    Attributes:
        _segments: Segment kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Segmentleyiciyi başlatır."""
        self._segments: dict[str, dict] = {}
        self._stats = {
            "segments_created": 0,
            "members_segmented": 0,
        }
        logger.info(
            "AudienceSegmenter baslatildi",
        )

    @property
    def segment_count(self) -> int:
        """Oluşturulan segment sayısı."""
        return self._stats["segments_created"]

    @property
    def segmented_count(self) -> int:
        """Segmentlenen üye sayısı."""
        return self._stats[
            "members_segmented"
        ]

    def segment_demographic(
        self,
        member_id: str,
        age: int = 0,
        gender: str = "",
        location: str = "",
    ) -> dict[str, Any]:
        """Demografik segmentasyon yapar.

        Args:
            member_id: Üye kimliği.
            age: Yaş.
            gender: Cinsiyet.
            location: Konum.

        Returns:
            Segment bilgisi.
        """
        if age < 18:
            group = "young"
        elif age < 35:
            group = "adult"
        elif age < 55:
            group = "middle_aged"
        else:
            group = "senior"

        seg_id = (
            f"demo_{len(self._segments)}"
        )
        self._segments[seg_id] = {
            "type": "demographic",
            "member_id": member_id,
            "group": group,
        }
        self._stats[
            "segments_created"
        ] += 1
        self._stats[
            "members_segmented"
        ] += 1

        logger.info(
            "Demografik segment: %s -> %s",
            member_id,
            group,
        )

        return {
            "segment_id": seg_id,
            "member_id": member_id,
            "group": group,
            "age": age,
            "gender": gender,
            "location": location,
            "segmented": True,
        }

    def segment_behavioral(
        self,
        member_id: str,
        visit_frequency: int = 0,
        purchase_count: int = 0,
        engagement_score: float = 0.0,
    ) -> dict[str, Any]:
        """Davranışsal segmentasyon yapar.

        Args:
            member_id: Üye kimliği.
            visit_frequency: Ziyaret sıklığı.
            purchase_count: Satın alma sayısı.
            engagement_score: Etkileşim puanı.

        Returns:
            Segment bilgisi.
        """
        total = (
            visit_frequency * 0.3
            + purchase_count * 0.4
            + engagement_score * 0.3
        )

        if total >= 8:
            behavior = "power_user"
        elif total >= 5:
            behavior = "active"
        elif total >= 2:
            behavior = "casual"
        else:
            behavior = "lurker"

        self._stats[
            "members_segmented"
        ] += 1

        return {
            "member_id": member_id,
            "behavior": behavior,
            "score": round(total, 2),
            "segmented": True,
        }

    def cluster_interests(
        self,
        member_id: str,
        interests: list[str] | None = None,
    ) -> dict[str, Any]:
        """İlgi alanı kümeleme yapar.

        Args:
            member_id: Üye kimliği.
            interests: İlgi alanları listesi.

        Returns:
            Kümeleme bilgisi.
        """
        if interests is None:
            interests = []

        tech = {
            "ai", "software", "data",
            "tech", "programming",
        }
        business = {
            "marketing", "finance",
            "startup", "business",
        }
        creative = {
            "design", "art", "music",
            "writing", "photography",
        }

        i_set = set(interests)
        clusters = []
        if i_set & tech:
            clusters.append("technology")
        if i_set & business:
            clusters.append("business")
        if i_set & creative:
            clusters.append("creative")
        if not clusters:
            clusters.append("general")

        return {
            "member_id": member_id,
            "clusters": clusters,
            "interest_count": len(interests),
            "clustered": True,
        }

    def segment_by_value(
        self,
        member_id: str,
        lifetime_value: float = 0.0,
        referral_count: int = 0,
    ) -> dict[str, Any]:
        """Değer tabanlı segmentasyon yapar.

        Args:
            member_id: Üye kimliği.
            lifetime_value: Yaşam boyu değer.
            referral_count: Referans sayısı.

        Returns:
            Segment bilgisi.
        """
        combined = (
            lifetime_value
            + referral_count * 100
        )

        if combined >= 5000:
            tier = "platinum"
        elif combined >= 2000:
            tier = "gold"
        elif combined >= 500:
            tier = "silver"
        else:
            tier = "bronze"

        return {
            "member_id": member_id,
            "tier": tier,
            "lifetime_value": lifetime_value,
            "referral_count": referral_count,
            "segmented": True,
        }

    def create_dynamic_group(
        self,
        group_name: str,
        criteria: dict[str, Any]
        | None = None,
    ) -> dict[str, Any]:
        """Dinamik grup oluşturur.

        Args:
            group_name: Grup adı.
            criteria: Grup kriterleri.

        Returns:
            Grup bilgisi.
        """
        if criteria is None:
            criteria = {}

        gid = (
            f"dyn_{len(self._segments)}"
        )
        self._segments[gid] = {
            "type": "dynamic",
            "name": group_name,
            "criteria": criteria,
        }
        self._stats[
            "segments_created"
        ] += 1

        return {
            "group_id": gid,
            "group_name": group_name,
            "criteria_count": len(criteria),
            "created": True,
        }
