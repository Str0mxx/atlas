"""ATLAS Takvim Çakışma Çözücü modülü.

Çakışma tespiti, öncelik değerlendirme,
yeniden zamanlama önerileri,
otomatik çözüm, bildirim.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class CalendarConflictResolver:
    """Takvim çakışma çözücü.

    Takvim çakışmalarını çözer.

    Attributes:
        _events: Etkinlik kayıtları.
        _conflicts: Çakışma kayıtları.
    """

    def __init__(self) -> None:
        """Çözücüyü başlatır."""
        self._events: list[
            dict[str, Any]
        ] = []
        self._conflicts: list[
            dict[str, Any]
        ] = []
        self._notifications: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "conflicts_detected": 0,
            "conflicts_resolved": 0,
        }

        logger.info(
            "CalendarConflictResolver "
            "baslatildi",
        )

    def add_event(
        self,
        event_id: str = "",
        title: str = "",
        start_hour: int = 9,
        end_hour: int = 10,
        priority: str = "medium",
    ) -> dict[str, Any]:
        """Etkinlik ekler.

        Args:
            event_id: Etkinlik kimliği.
            title: Başlık.
            start_hour: Başlangıç.
            end_hour: Bitiş.
            priority: Öncelik.

        Returns:
            Ekleme bilgisi.
        """
        self._counter += 1
        if not event_id:
            event_id = (
                f"ev_{self._counter}"
            )

        self._events.append({
            "event_id": event_id,
            "title": title,
            "start_hour": start_hour,
            "end_hour": end_hour,
            "priority": priority,
        })

        return {
            "event_id": event_id,
            "added": True,
        }

    def detect_conflicts(
        self,
    ) -> dict[str, Any]:
        """Çakışma tespit eder.

        Returns:
            Tespit bilgisi.
        """
        conflicts = []

        for i, a in enumerate(
            self._events,
        ):
            for b in self._events[i + 1:]:
                if (
                    a["start_hour"]
                    < b["end_hour"]
                    and b["start_hour"]
                    < a["end_hour"]
                ):
                    self._counter += 1
                    severity = (
                        "hard"
                        if (
                            a["start_hour"]
                            == b["start_hour"]
                        )
                        else "overlap"
                    )
                    conflict = {
                        "conflict_id": (
                            f"cf_"
                            f"{self._counter}"
                        ),
                        "event_a": a[
                            "event_id"
                        ],
                        "event_b": b[
                            "event_id"
                        ],
                        "severity": severity,
                    }
                    conflicts.append(
                        conflict,
                    )

        self._conflicts.extend(conflicts)
        self._stats[
            "conflicts_detected"
        ] += len(conflicts)

        return {
            "conflicts": conflicts,
            "count": len(conflicts),
            "detected": len(
                conflicts,
            ) > 0,
        }

    def evaluate_priority(
        self,
        event_a_id: str = "",
        event_b_id: str = "",
    ) -> dict[str, Any]:
        """Öncelik değerlendirir.

        Args:
            event_a_id: Etkinlik A.
            event_b_id: Etkinlik B.

        Returns:
            Değerlendirme bilgisi.
        """
        priority_order = {
            "critical": 0,
            "high": 1,
            "medium": 2,
            "low": 3,
        }

        event_a = None
        event_b = None

        for e in self._events:
            if e["event_id"] == event_a_id:
                event_a = e
            if e["event_id"] == event_b_id:
                event_b = e

        if not event_a or not event_b:
            return {
                "evaluated": False,
            }

        pa = priority_order.get(
            event_a["priority"], 2,
        )
        pb = priority_order.get(
            event_b["priority"], 2,
        )

        winner = (
            event_a_id if pa <= pb
            else event_b_id
        )
        loser = (
            event_b_id if pa <= pb
            else event_a_id
        )

        return {
            "winner": winner,
            "to_reschedule": loser,
            "evaluated": True,
        }

    def suggest_reschedule(
        self,
        event_id: str = "",
        work_start: int = 9,
        work_end: int = 18,
    ) -> dict[str, Any]:
        """Yeniden zamanlama önerir.

        Args:
            event_id: Etkinlik kimliği.
            work_start: İş başlangıcı.
            work_end: İş bitişi.

        Returns:
            Öneri bilgisi.
        """
        busy_hours: set[int] = set()
        target = None

        for e in self._events:
            if e["event_id"] == event_id:
                target = e
            else:
                for h in range(
                    e["start_hour"],
                    e["end_hour"],
                ):
                    busy_hours.add(h)

        if not target:
            return {
                "event_id": event_id,
                "suggested": False,
            }

        duration = (
            target["end_hour"]
            - target["start_hour"]
        )

        suggestions = []
        for h in range(
            work_start,
            work_end - duration + 1,
        ):
            slot_free = all(
                sh not in busy_hours
                for sh in range(
                    h, h + duration,
                )
            )
            if slot_free:
                suggestions.append({
                    "start_hour": h,
                    "end_hour": h + duration,
                })

        return {
            "event_id": event_id,
            "suggestions": suggestions[:3],
            "count": min(
                len(suggestions), 3,
            ),
            "suggested": len(
                suggestions,
            ) > 0,
        }

    def auto_resolve(
        self,
    ) -> dict[str, Any]:
        """Otomatik çözüm yapar.

        Returns:
            Çözüm bilgisi.
        """
        detection = self.detect_conflicts()
        resolved = []

        for conflict in detection.get(
            "conflicts", [],
        ):
            evaluation = (
                self.evaluate_priority(
                    conflict["event_a"],
                    conflict["event_b"],
                )
            )

            if evaluation.get("evaluated"):
                resolved.append({
                    "conflict_id": conflict[
                        "conflict_id"
                    ],
                    "kept": evaluation[
                        "winner"
                    ],
                    "rescheduled": evaluation[
                        "to_reschedule"
                    ],
                })
                self._stats[
                    "conflicts_resolved"
                ] += 1

        return {
            "resolved": resolved,
            "count": len(resolved),
            "auto_resolved": len(
                resolved,
            ) > 0,
        }

    def notify(
        self,
        event_id: str = "",
        message: str = "",
        recipients: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Bildirim gönderir.

        Args:
            event_id: Etkinlik kimliği.
            message: Mesaj.
            recipients: Alıcılar.

        Returns:
            Bildirim bilgisi.
        """
        recipients = recipients or []

        self._counter += 1
        nid = f"ntf_{self._counter}"

        notification = {
            "notification_id": nid,
            "event_id": event_id,
            "message": message,
            "recipients": recipients,
            "timestamp": time.time(),
        }
        self._notifications.append(
            notification,
        )

        return {
            "notification_id": nid,
            "recipients_count": len(
                recipients,
            ),
            "notified": True,
        }

    @property
    def conflict_count(self) -> int:
        """Çakışma sayısı."""
        return self._stats[
            "conflicts_detected"
        ]

    @property
    def resolved_count(self) -> int:
        """Çözülen sayısı."""
        return self._stats[
            "conflicts_resolved"
        ]
