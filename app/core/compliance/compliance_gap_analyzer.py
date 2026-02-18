"""
Uyumluluk bosluk analizcisi modulu.

Bosluk tespiti, risk degerlendirme,
oncelik siralama, duzeltme yol haritasi,
ilerleme takibi.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class ComplianceGapAnalyzer:
    """Uyumluluk bosluk analizcisi.

    Attributes:
        _gaps: Bosluk kayitlari.
        _assessments: Degerlendirmeler.
        _roadmaps: Yol haritalari.
        _progress: Ilerleme kayitlari.
        _stats: Istatistikler.
    """

    GAP_SEVERITIES: list[str] = [
        "critical",
        "high",
        "medium",
        "low",
        "info",
    ]

    GAP_STATUSES: list[str] = [
        "identified",
        "in_progress",
        "remediated",
        "accepted",
        "deferred",
    ]

    def __init__(self) -> None:
        """Analizcyi baslatir."""
        self._gaps: dict[
            str, dict
        ] = {}
        self._assessments: dict[
            str, dict
        ] = {}
        self._roadmaps: dict[
            str, dict
        ] = {}
        self._progress: list[dict] = []
        self._stats: dict[str, int] = {
            "gaps_identified": 0,
            "assessments_run": 0,
            "roadmaps_created": 0,
            "gaps_remediated": 0,
        }
        logger.info(
            "ComplianceGapAnalyzer "
            "baslatildi"
        )

    @property
    def gap_count(self) -> int:
        """Acik bosluk sayisi."""
        return sum(
            1
            for g in self._gaps.values()
            if g["status"]
            in ("identified", "in_progress")
        )

    def identify_gap(
        self,
        framework_key: str = "",
        requirement_id: str = "",
        title: str = "",
        description: str = "",
        severity: str = "medium",
        category: str = "",
        current_state: str = "",
        target_state: str = "",
    ) -> dict[str, Any]:
        """Bosluk tespit eder.

        Args:
            framework_key: Cerceve.
            requirement_id: Gereksinim ID.
            title: Baslik.
            description: Aciklama.
            severity: Ciddiyet.
            category: Kategori.
            current_state: Mevcut durum.
            target_state: Hedef durum.

        Returns:
            Bosluk bilgisi.
        """
        try:
            if (
                severity
                not in self.GAP_SEVERITIES
            ):
                return {
                    "identified": False,
                    "error": (
                        f"Gecersiz: "
                        f"{severity}"
                    ),
                }

            gid = f"cg_{uuid4()!s:.8}"
            sev_scores = {
                "critical": 1.0,
                "high": 0.8,
                "medium": 0.6,
                "low": 0.4,
                "info": 0.2,
            }
            risk_score = sev_scores.get(
                severity, 0.5
            )

            self._gaps[gid] = {
                "gap_id": gid,
                "framework_key": (
                    framework_key
                ),
                "requirement_id": (
                    requirement_id
                ),
                "title": title,
                "description": description,
                "severity": severity,
                "category": category,
                "current_state": (
                    current_state
                ),
                "target_state": (
                    target_state
                ),
                "risk_score": risk_score,
                "status": "identified",
                "identified_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }
            self._stats[
                "gaps_identified"
            ] += 1

            return {
                "gap_id": gid,
                "severity": severity,
                "risk_score": risk_score,
                "identified": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "identified": False,
                "error": str(e),
            }

    def run_assessment(
        self,
        framework_key: str = "",
        controls: (
            list[dict] | None
        ) = None,
    ) -> dict[str, Any]:
        """Degerlendirme calistirir.

        Args:
            framework_key: Cerceve.
            controls: Kontrol listesi.

        Returns:
            Degerlendirme sonucu.
        """
        try:
            aid = f"ca_{uuid4()!s:.8}"
            ctrl_list = controls or []

            total = len(ctrl_list)
            passed = sum(
                1
                for c in ctrl_list
                if c.get("status")
                == "passed"
            )
            failed = sum(
                1
                for c in ctrl_list
                if c.get("status")
                == "failed"
            )
            partial = total - passed - failed

            score = (
                (passed / total * 100)
                if total > 0
                else 0.0
            )

            # Basarisizlar icin bosluk
            gaps_found = 0
            for c in ctrl_list:
                if c.get("status") in (
                    "failed",
                    "partial",
                ):
                    self.identify_gap(
                        framework_key=(
                            framework_key
                        ),
                        requirement_id=(
                            c.get("id", "")
                        ),
                        title=c.get(
                            "name", ""
                        ),
                        severity=c.get(
                            "severity",
                            "medium",
                        ),
                        category=c.get(
                            "category", ""
                        ),
                        current_state=(
                            c.get(
                                "status",
                                "",
                            )
                        ),
                        target_state=(
                            "passed"
                        ),
                    )
                    gaps_found += 1

            self._assessments[aid] = {
                "assessment_id": aid,
                "framework_key": (
                    framework_key
                ),
                "total_controls": total,
                "passed": passed,
                "failed": failed,
                "partial": partial,
                "score": round(score, 1),
                "gaps_found": gaps_found,
                "assessed_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }
            self._stats[
                "assessments_run"
            ] += 1

            return {
                "assessment_id": aid,
                "score": round(score, 1),
                "passed": passed,
                "failed": failed,
                "gaps_found": gaps_found,
                "assessed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "assessed": False,
                "error": str(e),
            }

    def create_roadmap(
        self,
        name: str = "",
        framework_key: str = "",
        gap_ids: (
            list[str] | None
        ) = None,
        target_date: str = "",
    ) -> dict[str, Any]:
        """Duzeltme yol haritasi olusturur.

        Args:
            name: Yol haritasi adi.
            framework_key: Cerceve.
            gap_ids: Bosluk ID listesi.
            target_date: Hedef tarih.

        Returns:
            Yol haritasi bilgisi.
        """
        try:
            rid = f"rm_{uuid4()!s:.8}"
            gids = gap_ids or []

            # Bosluklari onceliklendir
            prioritized = []
            for gid in gids:
                gap = self._gaps.get(gid)
                if gap:
                    prioritized.append({
                        "gap_id": gid,
                        "title": gap[
                            "title"
                        ],
                        "severity": gap[
                            "severity"
                        ],
                        "risk_score": gap[
                            "risk_score"
                        ],
                    })

            prioritized.sort(
                key=lambda x: x[
                    "risk_score"
                ],
                reverse=True,
            )

            self._roadmaps[rid] = {
                "roadmap_id": rid,
                "name": name,
                "framework_key": (
                    framework_key
                ),
                "gaps": prioritized,
                "target_date": target_date,
                "status": "active",
                "progress": 0.0,
                "created_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._stats[
                "roadmaps_created"
            ] += 1

            return {
                "roadmap_id": rid,
                "name": name,
                "gaps_count": len(
                    prioritized
                ),
                "created": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "created": False,
                "error": str(e),
            }

    def update_gap_status(
        self,
        gap_id: str = "",
        status: str = "in_progress",
        notes: str = "",
    ) -> dict[str, Any]:
        """Bosluk durumunu gunceller.

        Args:
            gap_id: Bosluk ID.
            status: Yeni durum.
            notes: Notlar.

        Returns:
            Guncelleme bilgisi.
        """
        try:
            gap = self._gaps.get(gap_id)
            if not gap:
                return {
                    "updated": False,
                    "error": (
                        "Bosluk bulunamadi"
                    ),
                }

            if (
                status
                not in self.GAP_STATUSES
            ):
                return {
                    "updated": False,
                    "error": (
                        f"Gecersiz: "
                        f"{status}"
                    ),
                }

            old_status = gap["status"]
            gap["status"] = status
            gap["updated_at"] = (
                datetime.now(
                    timezone.utc
                ).isoformat()
            )

            if status == "remediated":
                self._stats[
                    "gaps_remediated"
                ] += 1

            self._progress.append({
                "gap_id": gap_id,
                "old_status": old_status,
                "new_status": status,
                "notes": notes,
                "updated_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            })

            # Yol haritasi ilerlemesi
            self._update_roadmap_progress(
                gap_id
            )

            return {
                "gap_id": gap_id,
                "status": status,
                "updated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "updated": False,
                "error": str(e),
            }

    def _update_roadmap_progress(
        self,
        gap_id: str,
    ) -> None:
        """Yol haritasi ilerlemesini
        gunceller."""
        for rm in (
            self._roadmaps.values()
        ):
            gap_ids = [
                g["gap_id"]
                for g in rm["gaps"]
            ]
            if gap_id not in gap_ids:
                continue

            total = len(gap_ids)
            if total == 0:
                continue

            done = sum(
                1
                for gid in gap_ids
                if self._gaps.get(
                    gid, {}
                ).get("status")
                in (
                    "remediated",
                    "accepted",
                )
            )
            rm["progress"] = round(
                done / total * 100, 1
            )

    def get_gaps_by_severity(
        self,
        severity: str = "",
    ) -> dict[str, Any]:
        """Ciddiyete gore bosluklari getirir.

        Args:
            severity: Ciddiyet filtresi.

        Returns:
            Bosluk listesi.
        """
        try:
            if severity:
                filtered = [
                    g
                    for g in (
                        self._gaps.values()
                    )
                    if g["severity"]
                    == severity
                ]
            else:
                filtered = list(
                    self._gaps.values()
                )

            return {
                "gaps": filtered,
                "count": len(filtered),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_risk_summary(
        self,
    ) -> dict[str, Any]:
        """Risk ozeti getirir.

        Returns:
            Risk ozeti.
        """
        try:
            by_sev: dict[str, int] = {}
            open_gaps = []
            for g in self._gaps.values():
                sev = g["severity"]
                by_sev[sev] = (
                    by_sev.get(sev, 0) + 1
                )
                if g["status"] in (
                    "identified",
                    "in_progress",
                ):
                    open_gaps.append(g)

            avg_risk = 0.0
            if open_gaps:
                avg_risk = sum(
                    g["risk_score"]
                    for g in open_gaps
                ) / len(open_gaps)

            return {
                "total_gaps": len(
                    self._gaps
                ),
                "open_gaps": len(
                    open_gaps
                ),
                "by_severity": by_sev,
                "average_risk": round(
                    avg_risk, 2
                ),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir."""
        try:
            return {
                "total_gaps": len(
                    self._gaps
                ),
                "open_gaps": (
                    self.gap_count
                ),
                "total_assessments": len(
                    self._assessments
                ),
                "total_roadmaps": len(
                    self._roadmaps
                ),
                "progress_entries": len(
                    self._progress
                ),
                "stats": dict(self._stats),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
