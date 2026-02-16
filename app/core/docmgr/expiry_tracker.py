"""ATLAS Doküman Süre Takipçisi modülü.

Son kullanma tarihleri, yenileme hatırlatıcıları,
uyumluluk son tarihleri, otomatik arşivleme,
uyarı üretimi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ExpiryTracker:
    """Doküman süre takipçisi.

    Doküman sürelerini izler ve uyarır.

    Attributes:
        _documents: Doküman süre kayıtları.
        _alerts: Uyarı kayıtları.
    """

    def __init__(
        self,
        alert_days: int = 30,
    ) -> None:
        """Takipçiyi başlatır.

        Args:
            alert_days: Uyarı gün sayısı.
        """
        self._documents: dict[
            str, dict[str, Any]
        ] = {}
        self._alerts: list[
            dict[str, Any]
        ] = []
        self._archived: list[str] = []
        self._alert_days = alert_days
        self._counter = 0
        self._stats = {
            "documents_tracked": 0,
            "alerts_generated": 0,
            "auto_archived": 0,
        }

        logger.info(
            "ExpiryTracker baslatildi",
        )

    def set_expiration(
        self,
        doc_id: str,
        days_until_expiry: int = 365,
        renewal_type: str = "manual",
    ) -> dict[str, Any]:
        """Son kullanma tarihi atar.

        Args:
            doc_id: Doküman kimliği.
            days_until_expiry: Kalan gün.
            renewal_type: Yenileme tipi.

        Returns:
            Atama bilgisi.
        """
        self._counter += 1
        eid = f"exp_{self._counter}"

        status = (
            "expired"
            if days_until_expiry <= 0
            else "expiring_soon"
            if days_until_expiry
            <= self._alert_days
            else "active"
        )

        self._documents[doc_id] = {
            "expiry_id": eid,
            "doc_id": doc_id,
            "days_until_expiry": (
                days_until_expiry
            ),
            "renewal_type": renewal_type,
            "status": status,
            "timestamp": time.time(),
        }
        self._stats[
            "documents_tracked"
        ] += 1

        return {
            "expiry_id": eid,
            "doc_id": doc_id,
            "status": status,
            "days_remaining": (
                days_until_expiry
            ),
            "set": True,
        }

    def check_renewals(
        self,
    ) -> dict[str, Any]:
        """Yenileme kontrolü yapar.

        Returns:
            Kontrol bilgisi.
        """
        needs_renewal = []
        expired = []

        for doc_id, doc in (
            self._documents.items()
        ):
            days = doc["days_until_expiry"]

            if days <= 0:
                expired.append(doc_id)
            elif days <= self._alert_days:
                needs_renewal.append({
                    "doc_id": doc_id,
                    "days_remaining": days,
                    "renewal_type": doc[
                        "renewal_type"
                    ],
                })

        return {
            "needs_renewal": needs_renewal,
            "expired": expired,
            "renewal_count": len(
                needs_renewal,
            ),
            "expired_count": len(expired),
            "checked": True,
        }

    def check_compliance(
        self,
        compliance_days: int = 90,
    ) -> dict[str, Any]:
        """Uyumluluk son tarihi kontrolü.

        Args:
            compliance_days: Uyumluluk günleri.

        Returns:
            Kontrol bilgisi.
        """
        at_risk = []
        compliant = []

        for doc_id, doc in (
            self._documents.items()
        ):
            days = doc["days_until_expiry"]

            if days <= compliance_days:
                at_risk.append({
                    "doc_id": doc_id,
                    "days_remaining": days,
                    "status": doc["status"],
                })
            else:
                compliant.append(doc_id)

        return {
            "at_risk": at_risk,
            "compliant_count": len(
                compliant,
            ),
            "at_risk_count": len(at_risk),
            "checked": True,
        }

    def auto_archive(
        self,
    ) -> dict[str, Any]:
        """Otomatik arşivleme yapar.

        Returns:
            Arşivleme bilgisi.
        """
        archived = []

        for doc_id, doc in list(
            self._documents.items()
        ):
            if doc["days_until_expiry"] <= 0:
                doc["status"] = "archived"
                self._archived.append(doc_id)
                archived.append(doc_id)
                self._stats[
                    "auto_archived"
                ] += 1

        return {
            "archived": archived,
            "count": len(archived),
            "performed": len(archived) > 0,
        }

    def generate_alerts(
        self,
    ) -> dict[str, Any]:
        """Uyarı üretir.

        Returns:
            Uyarı bilgisi.
        """
        alerts = []

        for doc_id, doc in (
            self._documents.items()
        ):
            days = doc["days_until_expiry"]

            if days <= 0:
                severity = "critical"
            elif days <= 7:
                severity = "high"
            elif days <= self._alert_days:
                severity = "medium"
            else:
                continue

            self._counter += 1
            alert = {
                "alert_id": (
                    f"alr_{self._counter}"
                ),
                "doc_id": doc_id,
                "days_remaining": days,
                "severity": severity,
                "timestamp": time.time(),
            }
            alerts.append(alert)
            self._alerts.append(alert)
            self._stats[
                "alerts_generated"
            ] += 1

        return {
            "alerts": alerts,
            "count": len(alerts),
            "generated": len(alerts) > 0,
        }

    @property
    def tracked_count(self) -> int:
        """Takip edilen doküman sayısı."""
        return self._stats[
            "documents_tracked"
        ]

    @property
    def alert_count(self) -> int:
        """Uyarı sayısı."""
        return self._stats[
            "alerts_generated"
        ]

    @property
    def archived_count(self) -> int:
        """Arşivlenen sayısı."""
        return self._stats[
            "auto_archived"
        ]
