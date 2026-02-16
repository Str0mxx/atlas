"""ATLAS Olay Sonrası Rapor Üretici modülü.

Zaman çizelgesi oluşturma, kök neden
analizi, etki değerlendirmesi,
eylem öğeleri, çıkarılan dersler.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class PostmortemGenerator:
    """Olay sonrası rapor üretici.

    Olaylardan öğrenme raporları üretir.

    Attributes:
        _postmortems: Rapor kayıtları.
        _lessons: Ders kayıtları.
    """

    def __init__(self) -> None:
        """Üreticiyi başlatır."""
        self._postmortems: dict[
            str, dict[str, Any]
        ] = {}
        self._lessons: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "reports_generated": 0,
            "lessons_captured": 0,
        }

        logger.info(
            "PostmortemGenerator baslatildi",
        )

    def create_timeline(
        self,
        incident_id: str,
        events: list[dict[str, Any]]
        | None = None,
    ) -> dict[str, Any]:
        """Zaman çizelgesi oluşturur.

        Args:
            incident_id: Olay ID.
            events: Olay listesi.

        Returns:
            Çizelge bilgisi.
        """
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
            "events": len(sorted_events),
            "duration_sec": duration,
            "timeline": sorted_events,
            "created": True,
        }

    def analyze_root_cause(
        self,
        incident_id: str,
        symptoms: list[str]
        | None = None,
        component: str = "",
        change_log: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Kök neden analizi yapar.

        Args:
            incident_id: Olay ID.
            symptoms: Belirtiler.
            component: Bileşen.
            change_log: Değişiklik günlüğü.

        Returns:
            Analiz bilgisi.
        """
        symptoms = symptoms or []
        change_log = change_log or []

        # Basit kök neden tahmini
        has_changes = len(change_log) > 0
        root_cause = (
            "recent_change"
            if has_changes
            else "resource_exhaustion"
            if any(
                "memory" in s or "cpu" in s
                for s in symptoms
            )
            else "dependency_failure"
            if any(
                "timeout" in s
                or "connection" in s
                for s in symptoms
            )
            else "unknown"
        )

        confidence = (
            0.8 if has_changes
            else 0.5
            if root_cause != "unknown"
            else 0.2
        )

        return {
            "incident_id": incident_id,
            "root_cause": root_cause,
            "confidence": confidence,
            "symptoms": len(symptoms),
            "changes": len(change_log),
            "component": component,
            "analyzed": True,
        }

    def assess_impact(
        self,
        incident_id: str,
        affected_users: int = 0,
        revenue_impact: float = 0.0,
        downtime_min: float = 0.0,
        affected_services: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Etki değerlendirmesi yapar.

        Args:
            incident_id: Olay ID.
            affected_users: Etkilenen kullanıcı.
            revenue_impact: Gelir etkisi.
            downtime_min: Kesinti (dk).
            affected_services: Servisler.

        Returns:
            Etki bilgisi.
        """
        affected_services = (
            affected_services or []
        )

        # Etki puanı
        user_score = min(
            affected_users / 100, 30,
        )
        revenue_score = min(
            revenue_impact / 1000, 30,
        )
        downtime_score = min(
            downtime_min / 10, 20,
        )
        service_score = min(
            len(affected_services) * 5, 20,
        )

        total = round(
            user_score + revenue_score
            + downtime_score + service_score,
            1,
        )

        severity = (
            "critical" if total >= 70
            else "high" if total >= 40
            else "medium" if total >= 15
            else "low"
        )

        return {
            "incident_id": incident_id,
            "impact_score": total,
            "severity": severity,
            "affected_users": affected_users,
            "revenue_impact": revenue_impact,
            "downtime_min": downtime_min,
            "services_affected": len(
                affected_services,
            ),
            "assessed": True,
        }

    def generate_action_items(
        self,
        incident_id: str,
        root_cause: str = "",
        severity: str = "medium",
    ) -> dict[str, Any]:
        """Eylem öğeleri oluşturur.

        Args:
            incident_id: Olay ID.
            root_cause: Kök neden.
            severity: Ciddiyet.

        Returns:
            Eylem bilgisi.
        """
        actions = []

        if root_cause == "recent_change":
            actions.extend([
                "Review recent deployments",
                "Add rollback procedure",
                "Improve change testing",
            ])
        elif root_cause == (
            "resource_exhaustion"
        ):
            actions.extend([
                "Increase resource limits",
                "Add auto-scaling rules",
                "Optimize resource usage",
            ])
        elif root_cause == (
            "dependency_failure"
        ):
            actions.extend([
                "Add circuit breakers",
                "Improve retry logic",
                "Add dependency monitoring",
            ])
        else:
            actions.extend([
                "Investigate further",
                "Add monitoring",
                "Document findings",
            ])

        if severity in (
            "critical", "high",
        ):
            actions.append(
                "Schedule follow-up review",
            )

        return {
            "incident_id": incident_id,
            "actions": actions,
            "action_count": len(actions),
            "priority": severity,
            "generated": True,
        }

    def capture_lessons(
        self,
        incident_id: str,
        what_worked: list[str]
        | None = None,
        what_failed: list[str]
        | None = None,
        improvements: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Çıkarılan dersleri kaydeder.

        Args:
            incident_id: Olay ID.
            what_worked: İşe yarayan.
            what_failed: Başarısız olan.
            improvements: İyileştirmeler.

        Returns:
            Ders bilgisi.
        """
        what_worked = what_worked or []
        what_failed = what_failed or []
        improvements = improvements or []

        lesson = {
            "incident_id": incident_id,
            "what_worked": what_worked,
            "what_failed": what_failed,
            "improvements": improvements,
            "timestamp": time.time(),
        }
        self._lessons.append(lesson)
        self._stats[
            "lessons_captured"
        ] += 1

        return {
            "incident_id": incident_id,
            "worked_count": len(
                what_worked,
            ),
            "failed_count": len(
                what_failed,
            ),
            "improvement_count": len(
                improvements,
            ),
            "captured": True,
        }

    def generate_report(
        self,
        incident_id: str,
        component: str = "",
        severity: str = "medium",
        symptoms: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Tam rapor üretir.

        Args:
            incident_id: Olay ID.
            component: Bileşen.
            severity: Ciddiyet.
            symptoms: Belirtiler.

        Returns:
            Rapor bilgisi.
        """
        self._counter += 1
        pid = f"pm_{self._counter}"

        root = self.analyze_root_cause(
            incident_id,
            symptoms=symptoms,
            component=component,
        )
        actions = (
            self.generate_action_items(
                incident_id,
                root_cause=root[
                    "root_cause"
                ],
                severity=severity,
            )
        )

        report = {
            "postmortem_id": pid,
            "incident_id": incident_id,
            "component": component,
            "severity": severity,
            "root_cause": root[
                "root_cause"
            ],
            "action_count": actions[
                "action_count"
            ],
            "timestamp": time.time(),
        }
        self._postmortems[pid] = report
        self._stats[
            "reports_generated"
        ] += 1

        return {
            "postmortem_id": pid,
            "incident_id": incident_id,
            "root_cause": root[
                "root_cause"
            ],
            "actions": actions[
                "action_count"
            ],
            "generated": True,
        }

    @property
    def report_count(self) -> int:
        """Rapor sayısı."""
        return self._stats[
            "reports_generated"
        ]

    @property
    def lesson_count(self) -> int:
        """Ders sayısı."""
        return self._stats[
            "lessons_captured"
        ]
