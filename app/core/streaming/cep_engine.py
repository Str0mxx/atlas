"""ATLAS Karmasik Olay Isleme modulu.

Desen eslestirme, sira tespiti,
korelasyon kurallari, zaman kisitlari
ve alarm uretimi.
"""

import logging
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)


class CEPEngine:
    """Karmasik olay isleme motoru.

    Olay desenlerini tespit eder ve alarm uretir.

    Attributes:
        _patterns: Desen tanimlari.
        _alerts: Uretilen alarmlar.
    """

    def __init__(self) -> None:
        """Motoru baslatir."""
        self._patterns: dict[
            str, dict[str, Any]
        ] = {}
        self._sequences: dict[
            str, dict[str, Any]
        ] = {}
        self._correlations: dict[
            str, dict[str, Any]
        ] = {}
        self._event_buffer: list[
            dict[str, Any]
        ] = []
        self._alerts: list[
            dict[str, Any]
        ] = []
        self._stats = {
            "events_processed": 0,
            "patterns_matched": 0,
            "alerts_generated": 0,
        }

        logger.info("CEPEngine baslatildi")

    def add_pattern(
        self,
        name: str,
        condition: Callable[
            [dict[str, Any]], bool
        ],
        alert_level: str = "warning",
        window_seconds: float = 60.0,
    ) -> dict[str, Any]:
        """Desen ekler.

        Args:
            name: Desen adi.
            condition: Kosul fonksiyonu.
            alert_level: Alarm seviyesi.
            window_seconds: Zaman penceresi.

        Returns:
            Ekleme bilgisi.
        """
        self._patterns[name] = {
            "name": name,
            "condition": condition,
            "alert_level": alert_level,
            "window": window_seconds,
            "match_count": 0,
            "created_at": time.time(),
        }

        return {
            "name": name,
            "alert_level": alert_level,
        }

    def add_sequence(
        self,
        name: str,
        steps: list[Callable[
            [dict[str, Any]], bool
        ]],
        timeout: float = 60.0,
        alert_level: str = "warning",
    ) -> dict[str, Any]:
        """Sira deseni ekler.

        Args:
            name: Sira adi.
            steps: Adim kosullari.
            timeout: Zaman asimi.
            alert_level: Alarm seviyesi.

        Returns:
            Ekleme bilgisi.
        """
        self._sequences[name] = {
            "name": name,
            "steps": steps,
            "timeout": timeout,
            "alert_level": alert_level,
            "current_step": 0,
            "started_at": None,
            "completed": False,
        }

        return {
            "name": name,
            "steps": len(steps),
        }

    def add_correlation(
        self,
        name: str,
        event_types: list[str],
        key_field: str,
        window_seconds: float = 60.0,
        min_count: int = 2,
        alert_level: str = "warning",
    ) -> dict[str, Any]:
        """Korelasyon kurali ekler.

        Args:
            name: Kural adi.
            event_types: Olay tipleri.
            key_field: Anahtar alani.
            window_seconds: Pencere.
            min_count: Minimum olay sayisi.
            alert_level: Alarm seviyesi.

        Returns:
            Ekleme bilgisi.
        """
        self._correlations[name] = {
            "name": name,
            "event_types": event_types,
            "key_field": key_field,
            "window": window_seconds,
            "min_count": min_count,
            "alert_level": alert_level,
            "buckets": {},
        }

        return {
            "name": name,
            "types": len(event_types),
        }

    def process_event(
        self,
        event: dict[str, Any],
    ) -> dict[str, Any]:
        """Olayi isler.

        Args:
            event: Olay verisi.

        Returns:
            Isleme sonucu.
        """
        self._stats["events_processed"] += 1
        event.setdefault(
            "timestamp", time.time(),
        )
        self._event_buffer.append(event)

        matches: list[str] = []
        alerts: list[dict[str, Any]] = []

        # Desen eslestirme
        for name, pattern in self._patterns.items():
            try:
                if pattern["condition"](event):
                    pattern["match_count"] += 1
                    matches.append(name)
                    self._stats[
                        "patterns_matched"
                    ] += 1

                    alert = self._generate_alert(
                        name,
                        pattern["alert_level"],
                        event,
                    )
                    alerts.append(alert)
            except Exception:
                pass

        # Sira tespiti
        for name, seq in self._sequences.items():
            if seq["completed"]:
                continue

            step_idx = seq["current_step"]
            if step_idx < len(seq["steps"]):
                try:
                    if seq["steps"][step_idx](event):
                        if step_idx == 0:
                            seq["started_at"] = (
                                time.time()
                            )
                        seq["current_step"] += 1

                        if seq["current_step"] >= len(
                            seq["steps"]
                        ):
                            seq["completed"] = True
                            matches.append(
                                f"seq:{name}",
                            )
                            alert = (
                                self._generate_alert(
                                    f"sequence:{name}",
                                    seq["alert_level"],
                                    event,
                                )
                            )
                            alerts.append(alert)
                except Exception:
                    pass

            # Zaman asimi kontrolu
            if (
                seq["started_at"]
                and not seq["completed"]
            ):
                elapsed = (
                    time.time() - seq["started_at"]
                )
                if elapsed > seq["timeout"]:
                    seq["current_step"] = 0
                    seq["started_at"] = None

        # Korelasyon kontrolu
        for name, corr in self._correlations.items():
            etype = event.get("type", "")
            if etype in corr["event_types"]:
                key = event.get(
                    corr["key_field"], "",
                )
                if key:
                    bucket = corr["buckets"].setdefault(
                        key, [],
                    )
                    bucket.append(event)

                    # Pencere ici kontrol
                    now = time.time()
                    bucket[:] = [
                        e for e in bucket
                        if now - e.get(
                            "timestamp", 0,
                        ) <= corr["window"]
                    ]

                    if len(bucket) >= corr["min_count"]:
                        matches.append(
                            f"corr:{name}",
                        )
                        alert = (
                            self._generate_alert(
                                f"correlation:{name}",
                                corr["alert_level"],
                                event,
                            )
                        )
                        alerts.append(alert)
                        corr["buckets"][key] = []

        return {
            "matches": matches,
            "alerts": len(alerts),
            "total_processed": self._stats[
                "events_processed"
            ],
        }

    def _generate_alert(
        self,
        pattern: str,
        level: str,
        event: dict[str, Any],
    ) -> dict[str, Any]:
        """Alarm uretir.

        Args:
            pattern: Desen adi.
            level: Seviye.
            event: Tetikleyen olay.

        Returns:
            Alarm bilgisi.
        """
        alert = {
            "pattern": pattern,
            "level": level,
            "event": event,
            "timestamp": time.time(),
        }
        self._alerts.append(alert)
        self._stats["alerts_generated"] += 1
        return alert

    def get_alerts(
        self,
        level: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Alarmlari getirir.

        Args:
            level: Seviye filtresi.
            limit: Limit.

        Returns:
            Alarm listesi.
        """
        alerts = self._alerts
        if level:
            alerts = [
                a for a in alerts
                if a["level"] == level
            ]
        return alerts[-limit:]

    def reset_sequence(
        self,
        name: str,
    ) -> bool:
        """Sirayi sifirlar.

        Args:
            name: Sira adi.

        Returns:
            Basarili mi.
        """
        seq = self._sequences.get(name)
        if seq:
            seq["current_step"] = 0
            seq["started_at"] = None
            seq["completed"] = False
            return True
        return False

    def get_pattern(
        self,
        name: str,
    ) -> dict[str, Any] | None:
        """Desen bilgisini getirir.

        Args:
            name: Desen adi.

        Returns:
            Desen bilgisi veya None.
        """
        p = self._patterns.get(name)
        if not p:
            return None
        return {
            "name": p["name"],
            "alert_level": p["alert_level"],
            "match_count": p["match_count"],
        }

    def get_stats(self) -> dict[str, int]:
        """Istatistikleri getirir.

        Returns:
            Istatistikler.
        """
        return dict(self._stats)

    @property
    def pattern_count(self) -> int:
        """Desen sayisi."""
        return len(self._patterns)

    @property
    def sequence_count(self) -> int:
        """Sira sayisi."""
        return len(self._sequences)

    @property
    def correlation_count(self) -> int:
        """Korelasyon sayisi."""
        return len(self._correlations)

    @property
    def alert_count(self) -> int:
        """Alarm sayisi."""
        return len(self._alerts)

    @property
    def event_count(self) -> int:
        """Islenen olay sayisi."""
        return self._stats["events_processed"]
