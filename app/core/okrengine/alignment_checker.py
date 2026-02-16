"""
OKR alignment checker modülü.

Bu modül OKR'lar arası dikey ve yatay uyumu kontrol eder,
boşlukları tespit eder ve çatışmaları belirler.
"""

from typing import Any
import logging

logger = logging.getLogger(__name__)


class AlignmentChecker:
    """
    OKR uyum kontrolcüsü.

    Dikey (parent-child) ve yatay (sibling) uyum kontrolü yapar,
    boşlukları tespit eder, çatışmaları belirler ve düzeltme önerileri sunar.
    """

    def __init__(self) -> None:
        """AlignmentChecker örneğini başlatır."""
        self._alignments: list[dict[str, Any]] = []
        self._stats: dict[str, int] = {
            "checks_performed": 0
        }
        logger.info("AlignmentChecker başlatıldı")

    @property
    def check_count(self) -> int:
        """
        Yapılan kontrol sayısını döndürür.

        Returns:
            Yapılan kontrol sayısı
        """
        return self._stats["checks_performed"]

    def check_vertical(
        self,
        child_id: str,
        parent_id: str,
        child_progress: float = 0.0,
        parent_progress: float = 0.0
    ) -> dict[str, Any]:
        """
        Parent-child arası dikey uyumu kontrol eder.

        Args:
            child_id: Alt hedef ID'si
            parent_id: Üst hedef ID'si
            child_progress: Alt hedef ilerleme yüzdesi (0-100)
            parent_progress: Üst hedef ilerleme yüzdesi (0-100)

        Returns:
            Dikey uyum kontrol sonucu
        """
        gap = abs(child_progress - parent_progress)
        aligned = gap < 20

        self._stats["checks_performed"] += 1

        result = {
            "child_id": child_id,
            "parent_id": parent_id,
            "child_progress": child_progress,
            "parent_progress": parent_progress,
            "gap": gap,
            "aligned": aligned,
            "alignment_type": "vertical",
            "checked": True
        }

        self._alignments.append(result)

        logger.debug(
            f"Dikey uyum kontrolü: {child_id} -> {parent_id}, "
            f"gap={gap:.1f}, aligned={aligned}"
        )

        return result

    def check_horizontal(
        self,
        objective_ids: list[str] | None = None,
        progress_values: list[float] | None = None
    ) -> dict[str, Any]:
        """
        Aynı seviyedeki hedeflerin yatay uyumunu kontrol eder.

        Args:
            objective_ids: Hedef ID'leri listesi
            progress_values: İlerleme değerleri listesi (0-100)

        Returns:
            Yatay uyum kontrol sonucu
        """
        if objective_ids is None:
            objective_ids = []
        if progress_values is None:
            progress_values = []

        if progress_values:
            avg = round(sum(progress_values) / len(progress_values), 1)
            max_gap = round(max(progress_values) - min(progress_values), 1)
        else:
            avg = 0.0
            max_gap = 0.0

        aligned = max_gap < 30

        self._stats["checks_performed"] += 1

        result = {
            "objective_count": len(objective_ids),
            "avg_progress": avg,
            "max_gap": max_gap,
            "aligned": aligned,
            "alignment_type": "horizontal",
            "checked": True
        }

        self._alignments.append(result)

        logger.debug(
            f"Yatay uyum kontrolü: {len(objective_ids)} hedef, "
            f"avg={avg:.1f}, max_gap={max_gap:.1f}, aligned={aligned}"
        )

        return result

    def detect_gaps(
        self,
        objectives: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        """
        Hedefler arasındaki boşlukları tespit eder.

        Args:
            objectives: Hedef bilgileri listesi

        Returns:
            Boşluk tespit sonucu
        """
        if objectives is None:
            objectives = []

        gaps = [o for o in objectives if o.get("progress", 0) < 30]
        gap_count = len(gaps)

        if gap_count > len(objectives) * 0.5:
            severity = "critical"
        elif gap_count > 0:
            severity = "moderate"
        else:
            severity = "none"

        result = {
            "total_objectives": len(objectives),
            "gap_count": gap_count,
            "severity": severity,
            "gaps": [g.get("name", "") for g in gaps],
            "detected": True
        }

        logger.info(
            f"Boşluk tespiti: {gap_count}/{len(objectives)} hedef "
            f"<30% ilerleme (severity={severity})"
        )

        return result

    def identify_conflicts(
        self,
        objectives: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        """
        Hedefler arası çatışmaları belirler.

        Args:
            objectives: Hedef bilgileri listesi

        Returns:
            Çatışma belirleme sonucu
        """
        if objectives is None:
            objectives = []

        conflicts: list[dict[str, str]] = []

        for i in range(len(objectives)):
            for j in range(i + 1, len(objectives)):
                obj_a = objectives[i]
                obj_b = objectives[j]

                # Aynı kaynak kullanımı varsa çatışma olarak işaretle
                if "resource" in obj_a and "resource" in obj_b:
                    if obj_a["resource"] == obj_b["resource"]:
                        conflicts.append({
                            "obj_a": obj_a.get("name", ""),
                            "obj_b": obj_b.get("name", ""),
                            "conflict_type": "resource_conflict"
                        })

        result = {
            "conflict_count": len(conflicts),
            "conflicts": conflicts,
            "has_conflicts": len(conflicts) > 0,
            "identified": True
        }

        logger.info(
            f"Çatışma tespiti: {len(conflicts)} çatışma bulundu "
            f"({len(objectives)} hedef içinde)"
        )

        return result

    def recommend_alignment(
        self,
        gap_count: int = 0,
        conflict_count: int = 0,
        avg_progress: float = 50.0
    ) -> dict[str, Any]:
        """
        Uyum iyileştirme önerileri sunar.

        Args:
            gap_count: Tespit edilen boşluk sayısı
            conflict_count: Tespit edilen çatışma sayısı
            avg_progress: Ortalama ilerleme yüzdesi

        Returns:
            Öneri sonucu
        """
        recommendations: list[str] = []

        if gap_count > 0:
            recommendations.append("address_lagging_objectives")

        if conflict_count > 0:
            recommendations.append("resolve_resource_conflicts")

        if avg_progress < 40:
            recommendations.append("review_targets")

        if not recommendations:
            recommendations.append("maintain_course")

        if gap_count == 0 and conflict_count == 0:
            health = "healthy"
        elif gap_count + conflict_count <= 2:
            health = "needs_attention"
        else:
            health = "critical"

        result = {
            "recommendations": recommendations,
            "recommendation_count": len(recommendations),
            "health": health,
            "recommended": True
        }

        logger.info(
            f"Uyum önerileri: {len(recommendations)} öneri, "
            f"sağlık={health} (gap={gap_count}, conflict={conflict_count}, "
            f"avg_progress={avg_progress:.1f})"
        )

        return result
