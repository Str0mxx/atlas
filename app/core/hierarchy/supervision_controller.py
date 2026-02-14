"""ATLAS Denetim Kontrolcusu modulu.

Alt agent izleme, ilerleme takibi,
mudahale tetikleyicileri, eskalasyon kurallari ve performans geri bildirimi.
"""

import logging
from typing import Any

from app.models.hierarchy import (
    AgentNode,
    SupervisionEvent,
)

logger = logging.getLogger(__name__)


class SupervisionController:
    """Denetim kontrol sistemi.

    Alt agent'lari izler, ilerlemeyi takip eder
    ve gerektiginde mudahale eder.

    Attributes:
        _events: Denetim olaylari.
        _progress: Agent ilerleme takibi.
        _performance: Agent performans puanlari.
        _escalation_threshold: Eskalasyon esigi.
    """

    def __init__(self, escalation_timeout: int = 300) -> None:
        """Denetim kontrolcusunu baslatir.

        Args:
            escalation_timeout: Eskalasyon zaman asimi (saniye).
        """
        self._events: list[SupervisionEvent] = []
        self._progress: dict[str, dict[str, Any]] = {}
        self._performance: dict[str, list[float]] = {}
        self._escalation_timeout = escalation_timeout

        logger.info(
            "SupervisionController baslatildi (timeout=%d)",
            escalation_timeout,
        )

    def monitor(
        self,
        agent_id: str,
        event_type: str,
        details: str = "",
        severity: str = "info",
    ) -> SupervisionEvent:
        """Agent olayini kaydeder.

        Args:
            agent_id: Agent ID.
            event_type: Olay tipi.
            details: Detaylar.
            severity: Ciddiyet (info/warning/error/critical).

        Returns:
            SupervisionEvent nesnesi.
        """
        requires_intervention = severity in ("error", "critical")

        event = SupervisionEvent(
            agent_id=agent_id,
            event_type=event_type,
            details=details,
            severity=severity,
            requires_intervention=requires_intervention,
        )

        self._events.append(event)

        if requires_intervention:
            logger.warning(
                "Mudahale gerekli: agent=%s, tip=%s, detay=%s",
                agent_id, event_type, details,
            )

        return event

    def track_progress(
        self,
        agent_id: str,
        task_id: str,
        progress: float,
        status: str = "in_progress",
    ) -> dict[str, Any]:
        """Ilerlemeyi takip eder.

        Args:
            agent_id: Agent ID.
            task_id: Gorev ID.
            progress: Ilerleme (0-1).
            status: Durum.

        Returns:
            Ilerleme bilgisi.
        """
        key = f"{agent_id}:{task_id}"
        self._progress[key] = {
            "agent_id": agent_id,
            "task_id": task_id,
            "progress": min(max(progress, 0.0), 1.0),
            "status": status,
        }

        return self._progress[key]

    def get_progress(
        self, agent_id: str, task_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Ilerleme bilgisi getirir.

        Args:
            agent_id: Agent ID.
            task_id: Gorev ID (opsiyonel).

        Returns:
            Ilerleme listesi.
        """
        results: list[dict[str, Any]] = []
        for key, info in self._progress.items():
            if info["agent_id"] == agent_id:
                if task_id is None or info["task_id"] == task_id:
                    results.append(info)
        return results

    def check_intervention(self, agent_id: str) -> dict[str, Any]:
        """Mudahale gerekip gerekmedigi kontrol eder.

        Args:
            agent_id: Agent ID.

        Returns:
            Mudahale bilgisi.
        """
        agent_events = [
            e for e in self._events
            if e.agent_id == agent_id and e.requires_intervention
        ]

        # Ilerleme durumu
        stalled = False
        progress_list = self.get_progress(agent_id)
        for p in progress_list:
            if p["status"] == "in_progress" and p["progress"] < 0.1:
                stalled = True

        needs_intervention = len(agent_events) > 0 or stalled

        return {
            "agent_id": agent_id,
            "needs_intervention": needs_intervention,
            "pending_events": len(agent_events),
            "stalled": stalled,
            "recommendation": self._get_recommendation(
                agent_events, stalled,
            ),
        }

    def should_escalate(
        self,
        agent_id: str,
        error_count: int = 0,
        stall_time_seconds: int = 0,
    ) -> bool:
        """Eskalasyon gerekip gerekmedigini kontrol eder.

        Args:
            agent_id: Agent ID.
            error_count: Hata sayisi.
            stall_time_seconds: Duraksama suresi.

        Returns:
            Eskalasyon gerekiyorsa True.
        """
        # Cok fazla hata
        if error_count >= 3:
            return True

        # Zaman asimi
        if stall_time_seconds > self._escalation_timeout:
            return True

        # Kritik olay var mi
        critical = [
            e for e in self._events
            if e.agent_id == agent_id and e.severity == "critical"
        ]
        if critical:
            return True

        return False

    def record_performance(
        self,
        agent_id: str,
        score: float,
    ) -> float:
        """Performans puani kaydeder.

        Args:
            agent_id: Agent ID.
            score: Puan (0-1).

        Returns:
            Ortalama puan.
        """
        if agent_id not in self._performance:
            self._performance[agent_id] = []

        self._performance[agent_id].append(min(max(score, 0.0), 1.0))

        # Son 20 kayit tut
        if len(self._performance[agent_id]) > 20:
            self._performance[agent_id] = self._performance[agent_id][-20:]

        return self.get_avg_performance(agent_id)

    def get_avg_performance(self, agent_id: str) -> float:
        """Ortalama performansi getirir.

        Args:
            agent_id: Agent ID.

        Returns:
            Ortalama puan.
        """
        scores = self._performance.get(agent_id, [])
        if not scores:
            return 0.0
        return sum(scores) / len(scores)

    def get_events(
        self,
        agent_id: str | None = None,
        severity: str | None = None,
    ) -> list[SupervisionEvent]:
        """Olaylari getirir.

        Args:
            agent_id: Agent filtresi.
            severity: Ciddiyet filtresi.

        Returns:
            SupervisionEvent listesi.
        """
        results = self._events
        if agent_id:
            results = [e for e in results if e.agent_id == agent_id]
        if severity:
            results = [e for e in results if e.severity == severity]
        return results

    def _get_recommendation(
        self,
        events: list[SupervisionEvent],
        stalled: bool,
    ) -> str:
        """Mudahale onerisi olusturur."""
        if not events and not stalled:
            return "Mudahale gerekmiyor"

        parts: list[str] = []
        if stalled:
            parts.append("Gorev durmus, yeniden baslat veya devret")

        critical = [e for e in events if e.severity == "critical"]
        errors = [e for e in events if e.severity == "error"]

        if critical:
            parts.append(f"{len(critical)} kritik olay, hemen mudahale")
        if errors:
            parts.append(f"{len(errors)} hata, kontrol et")

        return "; ".join(parts) if parts else "Izle"

    @property
    def event_count(self) -> int:
        """Olay sayisi."""
        return len(self._events)

    @property
    def intervention_count(self) -> int:
        """Mudahale gerektiren olay sayisi."""
        return sum(1 for e in self._events if e.requires_intervention)
