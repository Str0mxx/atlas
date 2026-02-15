"""ATLAS Eksiklik Tespitcisi modulu.

Gorev analizi, gerekli yetenekler,
mevcut yetenekler, eksiklik belirleme, onceliklendirme.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class GapDetector:
    """Eksiklik tespitcisi.

    Yetenek eksikliklerini tespit eder.

    Attributes:
        _gaps: Tespit edilen eksiklikler.
        _requirements: Gereksinim kayitlari.
    """

    def __init__(self) -> None:
        """Eksiklik tespitcisini baslatir."""
        self._gaps: dict[
            str, dict[str, Any]
        ] = {}
        self._requirements: dict[
            str, list[str]
        ] = {}
        self._stats = {
            "detected": 0,
            "resolved": 0,
        }

        logger.info(
            "GapDetector baslatildi",
        )

    def analyze_task(
        self,
        task_id: str,
        task_description: str,
        required_capabilities: list[str],
    ) -> dict[str, Any]:
        """Gorev analizi yapar.

        Args:
            task_id: Gorev ID.
            task_description: Gorev aciklamasi.
            required_capabilities: Gerekli yetenekler.

        Returns:
            Analiz sonucu.
        """
        self._requirements[task_id] = list(
            required_capabilities,
        )

        return {
            "task_id": task_id,
            "description": task_description,
            "required": required_capabilities,
            "count": len(
                required_capabilities,
            ),
            "analyzed_at": time.time(),
        }

    def detect_gaps(
        self,
        task_id: str,
        required: list[str],
        available: list[str],
    ) -> dict[str, Any]:
        """Eksiklikleri tespit eder.

        Args:
            task_id: Gorev ID.
            required: Gerekli yetenekler.
            available: Mevcut yetenekler.

        Returns:
            Eksiklik bilgisi.
        """
        available_set = set(available)
        gaps = []

        for cap in required:
            if cap not in available_set:
                gap_id = (
                    f"gap_{task_id}_{cap}"
                )
                gap = {
                    "gap_id": gap_id,
                    "task_id": task_id,
                    "capability": cap,
                    "severity": (
                        self._assess_severity(
                            cap,
                        )
                    ),
                    "priority": (
                        self._calculate_priority(
                            cap, required,
                        )
                    ),
                    "detected_at": time.time(),
                }
                gaps.append(gap)
                self._gaps[gap_id] = gap
                self._stats["detected"] += 1

        return {
            "task_id": task_id,
            "total_required": len(required),
            "available": len(
                available_set
                & set(required),
            ),
            "gaps": gaps,
            "gap_count": len(gaps),
            "coverage": round(
                (len(required) - len(gaps))
                / max(len(required), 1) * 100,
                1,
            ),
        }

    def _assess_severity(
        self,
        capability: str,
    ) -> str:
        """Siddet degerlendirir.

        Args:
            capability: Yetenek adi.

        Returns:
            Siddet seviyesi.
        """
        critical_keywords = [
            "security", "auth", "core",
        ]
        high_keywords = [
            "api", "data", "process",
        ]

        cap_lower = capability.lower()
        for kw in critical_keywords:
            if kw in cap_lower:
                return "critical"
        for kw in high_keywords:
            if kw in cap_lower:
                return "high"
        return "medium"

    def _calculate_priority(
        self,
        capability: str,
        all_required: list[str],
    ) -> float:
        """Oncelik hesaplar.

        Args:
            capability: Yetenek adi.
            all_required: Tum gereksinimler.

        Returns:
            Oncelik skoru (0-1).
        """
        # Listedeki sira onceligi etkiler
        if capability in all_required:
            idx = all_required.index(
                capability,
            )
            position_score = 1.0 - (
                idx / max(
                    len(all_required), 1,
                )
            )
        else:
            position_score = 0.5

        severity = self._assess_severity(
            capability,
        )
        severity_scores = {
            "critical": 1.0,
            "high": 0.8,
            "medium": 0.5,
            "low": 0.3,
        }
        sev_score = severity_scores.get(
            severity, 0.5,
        )

        return round(
            (position_score + sev_score) / 2,
            2,
        )

    def prioritize_gaps(
        self,
        task_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Eksiklikleri onceliklendirir.

        Args:
            task_id: Gorev filtresi.

        Returns:
            Sirali eksiklik listesi.
        """
        gaps = list(self._gaps.values())
        if task_id:
            gaps = [
                g for g in gaps
                if g["task_id"] == task_id
            ]

        gaps.sort(
            key=lambda g: g["priority"],
            reverse=True,
        )
        return gaps

    def resolve_gap(
        self,
        gap_id: str,
    ) -> dict[str, Any]:
        """Eksikligi cozulmus olarak isaretle.

        Args:
            gap_id: Eksiklik ID.

        Returns:
            Isaret bilgisi.
        """
        gap = self._gaps.get(gap_id)
        if not gap:
            return {"error": "gap_not_found"}

        gap["resolved"] = True
        gap["resolved_at"] = time.time()
        self._stats["resolved"] += 1

        return {
            "gap_id": gap_id,
            "resolved": True,
        }

    def get_gap(
        self,
        gap_id: str,
    ) -> dict[str, Any]:
        """Eksiklik getirir.

        Args:
            gap_id: Eksiklik ID.

        Returns:
            Eksiklik bilgisi.
        """
        gap = self._gaps.get(gap_id)
        if not gap:
            return {"error": "gap_not_found"}
        return dict(gap)

    @property
    def gap_count(self) -> int:
        """Eksiklik sayisi."""
        return len(self._gaps)

    @property
    def unresolved_count(self) -> int:
        """Cozulmemis eksiklik sayisi."""
        return sum(
            1 for g in self._gaps.values()
            if not g.get("resolved", False)
        )
