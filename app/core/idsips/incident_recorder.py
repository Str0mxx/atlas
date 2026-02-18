"""
Olay kaydedici modulu.

Olay loglama, kanit toplama,
zaman cizelgesi, ciddiyet takibi,
raporlama.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class IDSIncidentRecorder:
    """Olay kaydedici.

    Attributes:
        _incidents: Olay kayitlari.
        _evidence: Kanit kayitlari.
        _stats: Istatistikler.
    """

    SEVERITY_LEVELS: list[str] = [
        "info",
        "low",
        "medium",
        "high",
        "critical",
    ]

    def __init__(self) -> None:
        """Kaydediciyi baslatir."""
        self._incidents: list[dict] = []
        self._evidence: dict[
            str, list[dict]
        ] = {}
        self._stats: dict[str, int] = {
            "incidents_recorded": 0,
            "evidence_collected": 0,
            "incidents_resolved": 0,
        }
        logger.info(
            "IDSIncidentRecorder baslatildi"
        )

    @property
    def incident_count(self) -> int:
        """Olay sayisi."""
        return len(self._incidents)

    def record_incident(
        self,
        incident_type: str = "",
        source_ip: str = "",
        target: str = "",
        severity: str = "medium",
        description: str = "",
        details: dict | None = None,
    ) -> dict[str, Any]:
        """Olay kaydeder.

        Args:
            incident_type: Olay turu.
            source_ip: Kaynak IP.
            target: Hedef.
            severity: Ciddiyet.
            description: Aciklama.
            details: Detaylar.

        Returns:
            Kayit bilgisi.
        """
        try:
            iid = f"in_{uuid4()!s:.8}"
            incident = {
                "incident_id": iid,
                "type": incident_type,
                "source_ip": source_ip,
                "target": target,
                "severity": severity,
                "description": description,
                "details": details or {},
                "status": "open",
                "created_at": datetime.now(
                    timezone.utc
                ).isoformat(),
                "timeline": [
                    {
                        "event": "created",
                        "timestamp": (
                            datetime.now(
                                timezone.utc
                            ).isoformat()
                        ),
                    }
                ],
            }
            self._incidents.append(incident)
            self._evidence[iid] = []
            self._stats[
                "incidents_recorded"
            ] += 1

            return {
                "incident_id": iid,
                "type": incident_type,
                "severity": severity,
                "recorded": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "recorded": False,
                "error": str(e),
            }

    def add_evidence(
        self,
        incident_id: str = "",
        evidence_type: str = "",
        data: str = "",
        source: str = "",
    ) -> dict[str, Any]:
        """Kanit ekler.

        Args:
            incident_id: Olay ID.
            evidence_type: Kanit turu.
            data: Kanit verisi.
            source: Kaynak.

        Returns:
            Ekleme bilgisi.
        """
        try:
            if (
                incident_id
                not in self._evidence
            ):
                return {
                    "added": False,
                    "error": "Olay bulunamadi",
                }

            eid = f"ev_{uuid4()!s:.8}"
            evidence = {
                "evidence_id": eid,
                "type": evidence_type,
                "data": data,
                "source": source,
                "collected_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._evidence[
                incident_id
            ].append(evidence)
            self._stats[
                "evidence_collected"
            ] += 1

            for i in self._incidents:
                if (
                    i["incident_id"]
                    == incident_id
                ):
                    i["timeline"].append({
                        "event": (
                            "evidence_added"
                        ),
                        "evidence_id": eid,
                        "timestamp": (
                            datetime.now(
                                timezone.utc
                            ).isoformat()
                        ),
                    })
                    break

            return {
                "evidence_id": eid,
                "incident_id": incident_id,
                "added": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "added": False,
                "error": str(e),
            }

    def get_timeline(
        self,
        incident_id: str = "",
    ) -> dict[str, Any]:
        """Zaman cizelgesi getirir.

        Args:
            incident_id: Olay ID.

        Returns:
            Cizelge bilgisi.
        """
        try:
            for i in self._incidents:
                if (
                    i["incident_id"]
                    == incident_id
                ):
                    return {
                        "incident_id": (
                            incident_id
                        ),
                        "timeline": i[
                            "timeline"
                        ],
                        "event_count": len(
                            i["timeline"]
                        ),
                        "retrieved": True,
                    }

            return {
                "retrieved": False,
                "error": "Olay bulunamadi",
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def update_severity(
        self,
        incident_id: str = "",
        severity: str = "",
    ) -> dict[str, Any]:
        """Ciddiyet gunceller.

        Args:
            incident_id: Olay ID.
            severity: Yeni ciddiyet.

        Returns:
            Guncelleme bilgisi.
        """
        try:
            for i in self._incidents:
                if (
                    i["incident_id"]
                    == incident_id
                ):
                    old = i["severity"]
                    i["severity"] = severity
                    i["timeline"].append({
                        "event": (
                            "severity_changed"
                        ),
                        "old": old,
                        "new": severity,
                        "timestamp": (
                            datetime.now(
                                timezone.utc
                            ).isoformat()
                        ),
                    })
                    return {
                        "incident_id": (
                            incident_id
                        ),
                        "old_severity": old,
                        "new_severity": (
                            severity
                        ),
                        "updated": True,
                    }

            return {
                "updated": False,
                "error": "Olay bulunamadi",
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "updated": False,
                "error": str(e),
            }

    def resolve_incident(
        self,
        incident_id: str = "",
        resolution: str = "",
    ) -> dict[str, Any]:
        """Olayi cozer.

        Args:
            incident_id: Olay ID.
            resolution: Cozum.

        Returns:
            Cozum bilgisi.
        """
        try:
            for i in self._incidents:
                if (
                    i["incident_id"]
                    == incident_id
                ):
                    i["status"] = "resolved"
                    i[
                        "resolution"
                    ] = resolution
                    i["timeline"].append({
                        "event": "resolved",
                        "resolution": (
                            resolution
                        ),
                        "timestamp": (
                            datetime.now(
                                timezone.utc
                            ).isoformat()
                        ),
                    })
                    self._stats[
                        "incidents_resolved"
                    ] += 1
                    return {
                        "incident_id": (
                            incident_id
                        ),
                        "resolved": True,
                    }

            return {
                "resolved": False,
                "error": "Olay bulunamadi",
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "resolved": False,
                "error": str(e),
            }

    def generate_report(
        self,
        incident_id: str = "",
    ) -> dict[str, Any]:
        """Rapor uretir.

        Args:
            incident_id: Olay ID.

        Returns:
            Rapor bilgisi.
        """
        try:
            for i in self._incidents:
                if (
                    i["incident_id"]
                    == incident_id
                ):
                    evidence = self._evidence.get(
                        incident_id, []
                    )
                    return {
                        "incident_id": (
                            incident_id
                        ),
                        "type": i["type"],
                        "severity": i[
                            "severity"
                        ],
                        "status": i["status"],
                        "source_ip": i[
                            "source_ip"
                        ],
                        "target": i["target"],
                        "description": i[
                            "description"
                        ],
                        "evidence_count": len(
                            evidence
                        ),
                        "timeline_events": len(
                            i["timeline"]
                        ),
                        "generated": True,
                    }

            return {
                "generated": False,
                "error": "Olay bulunamadi",
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "generated": False,
                "error": str(e),
            }

    def get_open_incidents(
        self,
    ) -> dict[str, Any]:
        """Acik olaylari getirir.

        Returns:
            Olay bilgisi.
        """
        try:
            open_incidents = [
                {
                    "incident_id": i[
                        "incident_id"
                    ],
                    "type": i["type"],
                    "severity": i["severity"],
                    "source_ip": i[
                        "source_ip"
                    ],
                    "created_at": i[
                        "created_at"
                    ],
                }
                for i in self._incidents
                if i["status"] == "open"
            ]

            return {
                "incidents": open_incidents,
                "count": len(open_incidents),
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
        """Ozet getirir.

        Returns:
            Ozet bilgisi.
        """
        try:
            open_count = sum(
                1
                for i in self._incidents
                if i["status"] == "open"
            )
            critical = sum(
                1
                for i in self._incidents
                if i["status"] == "open"
                and i["severity"]
                == "critical"
            )

            return {
                "total_incidents": len(
                    self._incidents
                ),
                "open": open_count,
                "critical": critical,
                "resolved": self._stats[
                    "incidents_resolved"
                ],
                "evidence_total": self._stats[
                    "evidence_collected"
                ],
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
