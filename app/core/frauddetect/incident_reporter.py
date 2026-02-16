"""ATLAS Dolandırıcılık Olay Raporlayıcı modülü.

Olay belgeleme, kanıt toplama,
zaman çizelgesi, paydaş bildirimi,
uyumluluk raporlama.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class FraudIncidentReporter:
    """Dolandırıcılık olay raporlayıcı.

    Dolandırıcılık olaylarını raporlar.

    Attributes:
        _incidents: Olay kayıtları.
        _evidence: Kanıt kayıtları.
    """

    def __init__(self) -> None:
        """Raporlayıcıyı başlatır."""
        self._incidents: dict[
            str, dict[str, Any]
        ] = {}
        self._evidence: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._notifications: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "incidents_reported": 0,
            "evidence_collected": 0,
        }

        logger.info(
            "FraudIncidentReporter "
            "baslatildi",
        )

    def document_incident(
        self,
        title: str,
        severity: str = "medium",
        description: str = "",
        affected_entity: str = "",
    ) -> dict[str, Any]:
        """Olay belgeler.

        Args:
            title: Başlık.
            severity: Ciddiyet.
            description: Açıklama.
            affected_entity: Etkilenen varlık.

        Returns:
            Belge bilgisi.
        """
        self._counter += 1
        iid = f"finc_{self._counter}"

        self._incidents[iid] = {
            "incident_id": iid,
            "title": title,
            "severity": severity,
            "description": description,
            "affected_entity": (
                affected_entity
            ),
            "status": "open",
            "created_at": time.time(),
        }
        self._stats[
            "incidents_reported"
        ] += 1

        return {
            "incident_id": iid,
            "title": title,
            "severity": severity,
            "documented": True,
        }

    def collect_evidence(
        self,
        incident_id: str,
        evidence_type: str = "log",
        data: str = "",
        source: str = "",
    ) -> dict[str, Any]:
        """Kanıt toplar.

        Args:
            incident_id: Olay ID.
            evidence_type: Kanıt tipi.
            data: Veri.
            source: Kaynak.

        Returns:
            Kanıt bilgisi.
        """
        if incident_id not in (
            self._incidents
        ):
            return {
                "incident_id": incident_id,
                "collected": False,
            }

        if incident_id not in (
            self._evidence
        ):
            self._evidence[
                incident_id
            ] = []

        entry = {
            "type": evidence_type,
            "data": data,
            "source": source,
            "timestamp": time.time(),
        }
        self._evidence[
            incident_id
        ].append(entry)
        self._stats[
            "evidence_collected"
        ] += 1

        return {
            "incident_id": incident_id,
            "evidence_type": evidence_type,
            "total_evidence": len(
                self._evidence[incident_id],
            ),
            "collected": True,
        }

    def create_timeline(
        self,
        incident_id: str,
        events: list[dict[str, Any]]
        | None = None,
    ) -> dict[str, Any]:
        """Zaman çizelgesi oluşturur.

        Args:
            incident_id: Olay ID.
            events: Olaylar.

        Returns:
            Çizelge bilgisi.
        """
        if incident_id not in (
            self._incidents
        ):
            return {
                "incident_id": incident_id,
                "created": False,
            }

        events = events or []
        sorted_events = sorted(
            events,
            key=lambda e: e.get(
                "timestamp", 0,
            ),
        )

        duration = 0.0
        if len(sorted_events) >= 2:
            duration = round(
                sorted_events[-1].get(
                    "timestamp", 0,
                )
                - sorted_events[0].get(
                    "timestamp", 0,
                ),
                1,
            )

        return {
            "incident_id": incident_id,
            "event_count": len(
                sorted_events,
            ),
            "duration_sec": duration,
            "created": True,
        }

    def notify_stakeholders(
        self,
        incident_id: str,
        channels: list[str]
        | None = None,
        message: str = "",
    ) -> dict[str, Any]:
        """Paydaş bildirimi gönderir.

        Args:
            incident_id: Olay ID.
            channels: Kanallar.
            message: Mesaj.

        Returns:
            Bildirim bilgisi.
        """
        inc = self._incidents.get(
            incident_id,
        )
        if not inc:
            return {
                "incident_id": incident_id,
                "notified": False,
            }

        channels = channels or ["telegram"]
        auto_msg = message or (
            f"Fraud incident "
            f"{incident_id}: "
            f"{inc['severity']} - "
            f"{inc['title']}"
        )

        entry = {
            "incident_id": incident_id,
            "channels": channels,
            "message": auto_msg,
            "timestamp": time.time(),
        }
        self._notifications.append(entry)

        return {
            "incident_id": incident_id,
            "channels": channels,
            "notified": True,
        }

    def generate_compliance_report(
        self,
        incident_id: str,
    ) -> dict[str, Any]:
        """Uyumluluk raporu üretir.

        Args:
            incident_id: Olay ID.

        Returns:
            Rapor bilgisi.
        """
        inc = self._incidents.get(
            incident_id,
        )
        if not inc:
            return {
                "incident_id": incident_id,
                "generated": False,
            }

        evidence = self._evidence.get(
            incident_id, [],
        )

        return {
            "incident_id": incident_id,
            "title": inc["title"],
            "severity": inc["severity"],
            "evidence_count": len(evidence),
            "status": inc["status"],
            "generated": True,
        }

    @property
    def incident_count(self) -> int:
        """Olay sayısı."""
        return self._stats[
            "incidents_reported"
        ]

    @property
    def evidence_count(self) -> int:
        """Kanıt sayısı."""
        return self._stats[
            "evidence_collected"
        ]
