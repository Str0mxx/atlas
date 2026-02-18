"""
Guvenlik olay tespitcisi modulu.

Olay tespiti, ciddiyet siniflandirma,
kalip esleme, korelasyon,
uyari uretimi.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class IncidentDetector:
    """Guvenlik olay tespitcisi.

    Attributes:
        _incidents: Olay kayitlari.
        _patterns: Kalip kayitlari.
        _alerts: Uyari kayitlari.
        _correlations: Korelasyonlar.
        _stats: Istatistikler.
    """

    SEVERITY_LEVELS: list[str] = [
        "critical",
        "high",
        "medium",
        "low",
        "info",
    ]

    INCIDENT_TYPES: list[str] = [
        "malware",
        "phishing",
        "data_breach",
        "unauthorized_access",
        "dos_attack",
        "insider_threat",
        "ransomware",
        "supply_chain",
        "zero_day",
        "social_engineering",
    ]

    def __init__(self) -> None:
        """Tespitciyi baslatir."""
        self._incidents: dict[
            str, dict
        ] = {}
        self._patterns: dict[
            str, dict
        ] = {}
        self._alerts: list[dict] = []
        self._correlations: list[
            dict
        ] = []
        self._stats: dict[str, int] = {
            "incidents_detected": 0,
            "patterns_defined": 0,
            "alerts_generated": 0,
            "correlations_found": 0,
        }
        logger.info(
            "IncidentDetector baslatildi"
        )

    @property
    def incident_count(self) -> int:
        """Aktif olay sayisi."""
        return sum(
            1
            for i in (
                self._incidents.values()
            )
            if i["status"] == "active"
        )

    def define_pattern(
        self,
        name: str = "",
        pattern_type: str = "",
        indicators: (
            list[str] | None
        ) = None,
        threshold: int = 1,
        severity: str = "medium",
        description: str = "",
    ) -> dict[str, Any]:
        """Tespit kalibi tanimlar.

        Args:
            name: Kalip adi.
            pattern_type: Kalip tipi.
            indicators: Gostergeler.
            threshold: Esik.
            severity: Ciddiyet.
            description: Aciklama.

        Returns:
            Kalip bilgisi.
        """
        try:
            pid = f"pt_{uuid4()!s:.8}"
            self._patterns[pid] = {
                "pattern_id": pid,
                "name": name,
                "pattern_type": (
                    pattern_type
                ),
                "indicators": (
                    indicators or []
                ),
                "threshold": threshold,
                "severity": severity,
                "description": description,
                "is_active": True,
                "match_count": 0,
                "created_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }
            self._stats[
                "patterns_defined"
            ] += 1

            return {
                "pattern_id": pid,
                "name": name,
                "created": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "created": False,
                "error": str(e),
            }

    def detect_incident(
        self,
        title: str = "",
        incident_type: str = "malware",
        severity: str = "medium",
        source: str = "",
        description: str = "",
        indicators: (
            list[str] | None
        ) = None,
        affected_systems: (
            list[str] | None
        ) = None,
    ) -> dict[str, Any]:
        """Olay tespit eder.

        Args:
            title: Olay basligi.
            incident_type: Olay tipi.
            severity: Ciddiyet.
            source: Kaynak.
            description: Aciklama.
            indicators: Gostergeler.
            affected_systems: Etkilenenler.

        Returns:
            Olay bilgisi.
        """
        try:
            if (
                incident_type
                not in self.INCIDENT_TYPES
            ):
                return {
                    "detected": False,
                    "error": (
                        f"Gecersiz tip: "
                        f"{incident_type}"
                    ),
                }

            if (
                severity
                not in self.SEVERITY_LEVELS
            ):
                return {
                    "detected": False,
                    "error": (
                        f"Gecersiz: "
                        f"{severity}"
                    ),
                }

            iid = f"inc_{uuid4()!s:.8}"
            ind_list = indicators or []

            # Kalip esleme
            matched = (
                self._match_patterns(
                    ind_list
                )
            )

            self._incidents[iid] = {
                "incident_id": iid,
                "title": title,
                "incident_type": (
                    incident_type
                ),
                "severity": severity,
                "source": source,
                "description": description,
                "indicators": ind_list,
                "affected_systems": (
                    affected_systems or []
                ),
                "matched_patterns": matched,
                "status": "active",
                "detected_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }
            self._stats[
                "incidents_detected"
            ] += 1

            # Uyari uret
            self._generate_alert(
                iid, title, severity
            )

            return {
                "incident_id": iid,
                "severity": severity,
                "matched_patterns": len(
                    matched
                ),
                "detected": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "detected": False,
                "error": str(e),
            }

    def _match_patterns(
        self,
        indicators: list[str],
    ) -> list[str]:
        """Kalip eslestirir."""
        matched = []
        ind_set = set(indicators)
        for pid, pat in (
            self._patterns.items()
        ):
            if not pat["is_active"]:
                continue
            pat_ind = set(pat["indicators"])
            overlap = ind_set & pat_ind
            if len(overlap) >= pat[
                "threshold"
            ]:
                matched.append(pid)
                pat["match_count"] += 1
        return matched

    def _generate_alert(
        self,
        incident_id: str,
        title: str,
        severity: str,
    ) -> None:
        """Uyari uretir."""
        self._alerts.append({
            "alert_id": (
                f"al_{uuid4()!s:.8}"
            ),
            "incident_id": incident_id,
            "title": title,
            "severity": severity,
            "generated_at": (
                datetime.now(
                    timezone.utc
                ).isoformat()
            ),
        })
        self._stats[
            "alerts_generated"
        ] += 1

    def correlate_incidents(
        self,
        incident_ids: (
            list[str] | None
        ) = None,
    ) -> dict[str, Any]:
        """Olaylari iliskilendirir.

        Args:
            incident_ids: Olay ID listesi.

        Returns:
            Korelasyon bilgisi.
        """
        try:
            ids = incident_ids or []
            incidents = [
                self._incidents[iid]
                for iid in ids
                if iid in self._incidents
            ]
            if len(incidents) < 2:
                return {
                    "correlated": False,
                    "error": (
                        "En az 2 olay gerekli"
                    ),
                }

            # Ortak gosterge bul
            all_ind = [
                set(i["indicators"])
                for i in incidents
            ]
            common = all_ind[0]
            for s in all_ind[1:]:
                common = common & s

            # Ortak sistem bul
            all_sys = [
                set(
                    i["affected_systems"]
                )
                for i in incidents
            ]
            common_sys = all_sys[0]
            for s in all_sys[1:]:
                common_sys = common_sys & s

            cid = f"cr_{uuid4()!s:.8}"
            corr = {
                "correlation_id": cid,
                "incident_ids": ids,
                "common_indicators": list(
                    common
                ),
                "common_systems": list(
                    common_sys
                ),
                "strength": (
                    len(common) / max(
                        max(
                            len(s)
                            for s in all_ind
                        ),
                        1,
                    )
                ),
                "correlated_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }
            self._correlations.append(corr)
            self._stats[
                "correlations_found"
            ] += 1

            return {
                "correlation_id": cid,
                "common_indicators": len(
                    common
                ),
                "common_systems": len(
                    common_sys
                ),
                "strength": corr[
                    "strength"
                ],
                "correlated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "correlated": False,
                "error": str(e),
            }

    def update_status(
        self,
        incident_id: str = "",
        status: str = "",
    ) -> dict[str, Any]:
        """Olay durumunu gunceller.

        Args:
            incident_id: Olay ID.
            status: Yeni durum.

        Returns:
            Guncelleme bilgisi.
        """
        try:
            inc = self._incidents.get(
                incident_id
            )
            if not inc:
                return {
                    "updated": False,
                    "error": (
                        "Olay bulunamadi"
                    ),
                }

            valid = [
                "active",
                "contained",
                "investigating",
                "recovering",
                "resolved",
                "closed",
            ]
            if status not in valid:
                return {
                    "updated": False,
                    "error": (
                        f"Gecersiz: "
                        f"{status}"
                    ),
                }

            inc["status"] = status
            inc["updated_at"] = (
                datetime.now(
                    timezone.utc
                ).isoformat()
            )

            return {
                "incident_id": incident_id,
                "status": status,
                "updated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "updated": False,
                "error": str(e),
            }

    def get_alerts(
        self,
        severity: str = "",
    ) -> dict[str, Any]:
        """Uyarilari getirir.

        Args:
            severity: Ciddiyet filtresi.

        Returns:
            Uyari listesi.
        """
        try:
            if severity:
                filtered = [
                    a
                    for a in self._alerts
                    if a["severity"]
                    == severity
                ]
            else:
                filtered = list(
                    self._alerts
                )

            return {
                "alerts": filtered,
                "count": len(filtered),
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
            by_sev: dict[str, int] = {}
            for i in (
                self._incidents.values()
            ):
                s = i["severity"]
                by_sev[s] = (
                    by_sev.get(s, 0) + 1
                )

            return {
                "total_incidents": len(
                    self._incidents
                ),
                "active_incidents": (
                    self.incident_count
                ),
                "total_patterns": len(
                    self._patterns
                ),
                "total_alerts": len(
                    self._alerts
                ),
                "by_severity": by_sev,
                "stats": dict(self._stats),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
