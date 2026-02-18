"""
Kok neden analizcisi modulu.

Kok neden analizi, saldiri zaman cizelgesi,
giris noktasi tespiti, yayilim takibi,
zafiyet iliskilendirme.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class IncidentRootCauseAnalyzer:
    """Kok neden analizcisi.

    Attributes:
        _analyses: Analiz kayitlari.
        _timelines: Zaman cizelgeleri.
        _entry_points: Giris noktalari.
        _propagations: Yayilim kayitlari.
        _vulnerabilities: Zafiyet kayitlari.
        _stats: Istatistikler.
    """

    CAUSE_CATEGORIES: list[str] = [
        "human_error",
        "software_bug",
        "configuration",
        "vulnerability",
        "social_engineering",
        "insider_threat",
        "supply_chain",
        "zero_day",
        "policy_violation",
        "infrastructure",
    ]

    def __init__(self) -> None:
        """Analizcivi baslatir."""
        self._analyses: dict[
            str, dict
        ] = {}
        self._timelines: dict[
            str, list[dict]
        ] = {}
        self._entry_points: dict[
            str, dict
        ] = {}
        self._propagations: dict[
            str, list[dict]
        ] = {}
        self._vulnerabilities: dict[
            str, dict
        ] = {}
        self._stats: dict[str, int] = {
            "analyses_completed": 0,
            "entry_points_found": 0,
            "propagations_tracked": 0,
            "vulnerabilities_linked": 0,
        }
        logger.info(
            "IncidentRootCauseAnalyzer "
            "baslatildi"
        )

    @property
    def analysis_count(self) -> int:
        """Analiz sayisi."""
        return len(self._analyses)

    def start_analysis(
        self,
        incident_id: str = "",
        title: str = "",
        description: str = "",
        analyst: str = "",
    ) -> dict[str, Any]:
        """Kok neden analizi baslatir.

        Args:
            incident_id: Olay ID.
            title: Baslik.
            description: Aciklama.
            analyst: Analist.

        Returns:
            Analiz bilgisi.
        """
        try:
            aid = f"rca_{uuid4()!s:.8}"
            self._analyses[aid] = {
                "analysis_id": aid,
                "incident_id": incident_id,
                "title": title,
                "description": description,
                "analyst": analyst,
                "status": "in_progress",
                "root_causes": [],
                "started_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }
            self._timelines[aid] = []

            return {
                "analysis_id": aid,
                "incident_id": incident_id,
                "started": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "started": False,
                "error": str(e),
            }

    def add_root_cause(
        self,
        analysis_id: str = "",
        category: str = "software_bug",
        description: str = "",
        confidence: float = 0.5,
        evidence: (
            list[str] | None
        ) = None,
    ) -> dict[str, Any]:
        """Kok neden ekler.

        Args:
            analysis_id: Analiz ID.
            category: Kategori.
            description: Aciklama.
            confidence: Guven puani.
            evidence: Kanitlar.

        Returns:
            Kok neden bilgisi.
        """
        try:
            a = self._analyses.get(
                analysis_id
            )
            if not a:
                return {
                    "added": False,
                    "error": (
                        "Analiz bulunamadi"
                    ),
                }

            if (
                category
                not in self.CAUSE_CATEGORIES
            ):
                return {
                    "added": False,
                    "error": (
                        f"Gecersiz: "
                        f"{category}"
                    ),
                }

            cid = f"rc_{uuid4()!s:.8}"
            cause = {
                "cause_id": cid,
                "category": category,
                "description": description,
                "confidence": max(
                    0.0, min(1.0, confidence)
                ),
                "evidence": evidence or [],
                "added_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }
            a["root_causes"].append(cause)

            return {
                "cause_id": cid,
                "category": category,
                "confidence": cause[
                    "confidence"
                ],
                "added": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "added": False,
                "error": str(e),
            }

    def build_timeline(
        self,
        analysis_id: str = "",
        timestamp: str = "",
        event: str = "",
        source: str = "",
        severity: str = "info",
    ) -> dict[str, Any]:
        """Zaman cizelgesine olay ekler.

        Args:
            analysis_id: Analiz ID.
            timestamp: Zaman damgasi.
            event: Olay aciklamasi.
            source: Kaynak.
            severity: Ciddiyet.

        Returns:
            Olay bilgisi.
        """
        try:
            if (
                analysis_id
                not in self._analyses
            ):
                return {
                    "added": False,
                    "error": (
                        "Analiz bulunamadi"
                    ),
                }

            tl = self._timelines.get(
                analysis_id, []
            )
            entry = {
                "event_id": (
                    f"te_{uuid4()!s:.8}"
                ),
                "timestamp": (
                    timestamp
                    or datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
                "event": event,
                "source": source,
                "severity": severity,
            }
            tl.append(entry)
            # Zamana gore sirala
            tl.sort(
                key=lambda x: x["timestamp"]
            )

            return {
                "event_id": entry["event_id"],
                "timeline_length": len(tl),
                "added": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "added": False,
                "error": str(e),
            }

    def identify_entry_point(
        self,
        incident_id: str = "",
        entry_type: str = "",
        target: str = "",
        method: str = "",
        details: str = "",
    ) -> dict[str, Any]:
        """Giris noktasi tanimlar.

        Args:
            incident_id: Olay ID.
            entry_type: Giris tipi.
            target: Hedef.
            method: Yontem.
            details: Detaylar.

        Returns:
            Giris noktasi bilgisi.
        """
        try:
            eid = f"ep_{uuid4()!s:.8}"
            self._entry_points[eid] = {
                "entry_id": eid,
                "incident_id": incident_id,
                "entry_type": entry_type,
                "target": target,
                "method": method,
                "details": details,
                "identified_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }
            self._stats[
                "entry_points_found"
            ] += 1

            return {
                "entry_id": eid,
                "entry_type": entry_type,
                "target": target,
                "identified": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "identified": False,
                "error": str(e),
            }

    def track_propagation(
        self,
        incident_id: str = "",
        from_system: str = "",
        to_system: str = "",
        method: str = "",
        timestamp: str = "",
    ) -> dict[str, Any]:
        """Yayilim takibi yapar.

        Args:
            incident_id: Olay ID.
            from_system: Kaynak sistem.
            to_system: Hedef sistem.
            method: Yayilim yontemi.
            timestamp: Zaman damgasi.

        Returns:
            Yayilim bilgisi.
        """
        try:
            pid = f"pp_{uuid4()!s:.8}"
            prop = {
                "propagation_id": pid,
                "from_system": from_system,
                "to_system": to_system,
                "method": method,
                "timestamp": (
                    timestamp
                    or datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }

            if incident_id not in (
                self._propagations
            ):
                self._propagations[
                    incident_id
                ] = []
            self._propagations[
                incident_id
            ].append(prop)
            self._stats[
                "propagations_tracked"
            ] += 1

            return {
                "propagation_id": pid,
                "from_system": from_system,
                "to_system": to_system,
                "tracked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "tracked": False,
                "error": str(e),
            }

    def link_vulnerability(
        self,
        incident_id: str = "",
        vuln_id: str = "",
        cve_id: str = "",
        severity: str = "medium",
        description: str = "",
        affected_component: str = "",
    ) -> dict[str, Any]:
        """Zafiyet iliskilendirir.

        Args:
            incident_id: Olay ID.
            vuln_id: Zafiyet ID.
            cve_id: CVE numarasi.
            severity: Ciddiyet.
            description: Aciklama.
            affected_component: Biles.

        Returns:
            Zafiyet bilgisi.
        """
        try:
            vid = (
                vuln_id
                or f"vl_{uuid4()!s:.8}"
            )
            self._vulnerabilities[vid] = {
                "vuln_id": vid,
                "incident_id": incident_id,
                "cve_id": cve_id,
                "severity": severity,
                "description": description,
                "affected_component": (
                    affected_component
                ),
                "linked_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }
            self._stats[
                "vulnerabilities_linked"
            ] += 1

            return {
                "vuln_id": vid,
                "cve_id": cve_id,
                "linked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "linked": False,
                "error": str(e),
            }

    def complete_analysis(
        self,
        analysis_id: str = "",
        conclusion: str = "",
    ) -> dict[str, Any]:
        """Analizi tamamlar.

        Args:
            analysis_id: Analiz ID.
            conclusion: Sonuc.

        Returns:
            Tamamlama bilgisi.
        """
        try:
            a = self._analyses.get(
                analysis_id
            )
            if not a:
                return {
                    "completed": False,
                    "error": (
                        "Analiz bulunamadi"
                    ),
                }

            a["status"] = "completed"
            a["conclusion"] = conclusion
            a["completed_at"] = (
                datetime.now(
                    timezone.utc
                ).isoformat()
            )
            self._stats[
                "analyses_completed"
            ] += 1

            return {
                "analysis_id": analysis_id,
                "root_causes": len(
                    a["root_causes"]
                ),
                "completed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "completed": False,
                "error": str(e),
            }

    def get_timeline(
        self,
        analysis_id: str = "",
    ) -> dict[str, Any]:
        """Zaman cizelgesi getirir.

        Args:
            analysis_id: Analiz ID.

        Returns:
            Cizelge bilgisi.
        """
        try:
            tl = self._timelines.get(
                analysis_id
            )
            if tl is None:
                return {
                    "retrieved": False,
                    "error": (
                        "Analiz bulunamadi"
                    ),
                }

            return {
                "analysis_id": analysis_id,
                "events": list(tl),
                "count": len(tl),
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
            by_cat: dict[str, int] = {}
            for a in (
                self._analyses.values()
            ):
                for c in a["root_causes"]:
                    cat = c["category"]
                    by_cat[cat] = (
                        by_cat.get(cat, 0)
                        + 1
                    )

            return {
                "total_analyses": len(
                    self._analyses
                ),
                "total_entry_points": len(
                    self._entry_points
                ),
                "total_vulnerabilities": (
                    len(self._vulnerabilities)
                ),
                "by_category": by_cat,
                "stats": dict(self._stats),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
