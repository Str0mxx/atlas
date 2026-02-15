"""ATLAS Sessiz Saat Yöneticisi modülü.

Sessiz dönem tanımlama, otomatik tespit,
geçersiz kılma kuralları, kademeli uyanma,
acil durum geçişi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class QuietHoursManager:
    """Sessiz saat yöneticisi.

    Sessiz saatleri yönetir ve uygular.

    Attributes:
        _periods: Sessiz dönemler.
        _overrides: Geçersiz kılma kuralları.
    """

    def __init__(
        self,
        default_start: str = "22:00",
        default_end: str = "08:00",
    ) -> None:
        """Yöneticiyi başlatır.

        Args:
            default_start: Varsayılan başlangıç.
            default_end: Varsayılan bitiş.
        """
        self._periods: list[
            dict[str, Any]
        ] = []
        self._overrides: list[
            dict[str, Any]
        ] = []
        self._emergency_bypasses: list[
            dict[str, Any]
        ] = []
        self._wakeup_config = {
            "enabled": True,
            "gradual_minutes": 30,
            "stages": [
                "low_priority",
                "medium_priority",
                "all",
            ],
        }
        self._counter = 0
        self._stats = {
            "periods_defined": 0,
            "checks_performed": 0,
            "overrides_triggered": 0,
            "emergencies_bypassed": 0,
        }

        # Varsayılan sessiz dönem ekle
        self.define_period(
            "default",
            default_start,
            default_end,
        )

        logger.info(
            "QuietHoursManager baslatildi",
        )

    def define_period(
        self,
        name: str,
        start: str,
        end: str,
        days: list[int] | None = None,
    ) -> dict[str, Any]:
        """Sessiz dönem tanımlar.

        Args:
            name: Dönem adı.
            start: Başlangıç saati (HH:MM).
            end: Bitiş saati (HH:MM).
            days: Geçerli günler (0-6).

        Returns:
            Tanımlama bilgisi.
        """
        self._counter += 1
        pid = f"qp_{self._counter}"

        period = {
            "period_id": pid,
            "name": name,
            "start": start,
            "end": end,
            "days": days or list(range(7)),
            "active": True,
            "created_at": time.time(),
        }
        self._periods.append(period)
        self._stats["periods_defined"] += 1

        return {
            "period_id": pid,
            "name": name,
            "start": start,
            "end": end,
            "defined": True,
        }

    def is_quiet_hours(
        self,
        hour: int,
        minute: int = 0,
        day_of_week: int = 0,
    ) -> dict[str, Any]:
        """Sessiz saatte mi kontrol eder.

        Args:
            hour: Saat (0-23).
            minute: Dakika (0-59).
            day_of_week: Haftanın günü.

        Returns:
            Kontrol bilgisi.
        """
        self._stats["checks_performed"] += 1
        current = hour * 60 + minute

        for period in self._periods:
            if not period["active"]:
                continue
            if day_of_week not in period["days"]:
                continue

            start_parts = period["start"].split(
                ":",
            )
            end_parts = period["end"].split(":")
            start_min = (
                int(start_parts[0]) * 60
                + int(start_parts[1])
            )
            end_min = (
                int(end_parts[0]) * 60
                + int(end_parts[1])
            )

            # Gece geçişi (ör: 22:00 - 08:00)
            if start_min > end_min:
                is_quiet = (
                    current >= start_min
                    or current < end_min
                )
            else:
                is_quiet = (
                    start_min
                    <= current
                    < end_min
                )

            if is_quiet:
                return {
                    "is_quiet": True,
                    "period_name": period["name"],
                    "period_id": period[
                        "period_id"
                    ],
                    "start": period["start"],
                    "end": period["end"],
                }

        return {
            "is_quiet": False,
            "period_name": None,
            "period_id": None,
        }

    def auto_detect(
        self,
        sleep_hours: list[int] | None = None,
    ) -> dict[str, Any]:
        """Sessiz saatleri otomatik tespit eder.

        Args:
            sleep_hours: Uyku saatleri listesi.

        Returns:
            Tespit bilgisi.
        """
        if sleep_hours is not None:
            hours = sleep_hours
        else:
            hours = list(
                range(23, 24),
            ) + list(range(0, 7))

        if not hours:
            return {
                "detected": False,
                "reason": "no_sleep_data",
            }

        start_hour = min(hours)
        end_hour = max(hours) + 1

        # Gece geçişi kontrolü
        if start_hour > 12:
            end_candidates = [
                h for h in hours if h < 12
            ]
            if end_candidates:
                end_hour = max(end_candidates) + 1
                start_hour = min(
                    h for h in hours if h >= 12
                )

        start_str = f"{start_hour:02d}:00"
        end_str = f"{end_hour:02d}:00"

        result = self.define_period(
            "auto_detected",
            start_str,
            end_str,
        )

        return {
            "detected": True,
            "start": start_str,
            "end": end_str,
            "period_id": result["period_id"],
        }

    def add_override(
        self,
        name: str,
        condition: str,
        allow_through: bool = True,
    ) -> dict[str, Any]:
        """Geçersiz kılma kuralı ekler.

        Args:
            name: Kural adı.
            condition: Koşul.
            allow_through: İzin ver.

        Returns:
            Ekleme bilgisi.
        """
        override = {
            "name": name,
            "condition": condition,
            "allow_through": allow_through,
            "active": True,
        }
        self._overrides.append(override)
        return {"name": name, "added": True}

    def check_override(
        self,
        priority: str = "medium",
        source: str = "user",
    ) -> dict[str, Any]:
        """Override kontrol eder.

        Args:
            priority: Öncelik.
            source: Kaynak.

        Returns:
            Kontrol bilgisi.
        """
        for override in self._overrides:
            if not override["active"]:
                continue
            cond = override["condition"]
            if (
                cond == f"priority:{priority}"
                or cond == f"source:{source}"
                or cond == "always"
            ):
                self._stats[
                    "overrides_triggered"
                ] += 1
                return {
                    "override_active": True,
                    "name": override["name"],
                    "allow_through": override[
                        "allow_through"
                    ],
                }

        return {
            "override_active": False,
            "allow_through": False,
        }

    def configure_wakeup(
        self,
        gradual_minutes: int = 30,
        stages: list[str] | None = None,
    ) -> dict[str, Any]:
        """Kademeli uyanma ayarlar.

        Args:
            gradual_minutes: Kademeli süre (dk).
            stages: Aşamalar.

        Returns:
            Ayarlama bilgisi.
        """
        self._wakeup_config[
            "gradual_minutes"
        ] = gradual_minutes
        if stages:
            self._wakeup_config["stages"] = (
                stages
            )

        return {
            "configured": True,
            "gradual_minutes": gradual_minutes,
            "stages": self._wakeup_config[
                "stages"
            ],
        }

    def get_wakeup_stage(
        self,
        minutes_until_end: int,
    ) -> dict[str, Any]:
        """Uyanma aşamasını belirler.

        Args:
            minutes_until_end: Bitime kalan dk.

        Returns:
            Aşama bilgisi.
        """
        gradual = self._wakeup_config[
            "gradual_minutes"
        ]
        stages = self._wakeup_config["stages"]

        if minutes_until_end > gradual:
            return {
                "in_wakeup": False,
                "stage": "quiet",
                "allow_priority": "critical",
            }

        if not stages:
            return {
                "in_wakeup": True,
                "stage": "all",
                "allow_priority": "all",
            }

        stage_duration = gradual / len(stages)
        elapsed = gradual - minutes_until_end
        stage_index = min(
            int(elapsed / stage_duration),
            len(stages) - 1,
        )

        return {
            "in_wakeup": True,
            "stage": stages[stage_index],
            "minutes_remaining": (
                minutes_until_end
            ),
            "allow_priority": stages[
                stage_index
            ],
        }

    def emergency_bypass(
        self,
        reason: str,
        source: str = "system",
    ) -> dict[str, Any]:
        """Acil durum geçişi yapar.

        Args:
            reason: Neden.
            source: Kaynak.

        Returns:
            Geçiş bilgisi.
        """
        bypass = {
            "reason": reason,
            "source": source,
            "timestamp": time.time(),
        }
        self._emergency_bypasses.append(bypass)
        self._stats[
            "emergencies_bypassed"
        ] += 1

        return {
            "bypassed": True,
            "reason": reason,
            "source": source,
        }

    def get_periods(
        self,
        active_only: bool = True,
    ) -> list[dict[str, Any]]:
        """Sessiz dönemleri getirir.

        Args:
            active_only: Sadece aktif.

        Returns:
            Dönem listesi.
        """
        if active_only:
            return [
                p for p in self._periods
                if p["active"]
            ]
        return list(self._periods)

    @property
    def period_count(self) -> int:
        """Dönem sayısı."""
        return self._stats["periods_defined"]

    @property
    def checks_performed(self) -> int:
        """Kontrol sayısı."""
        return self._stats["checks_performed"]

    @property
    def bypass_count(self) -> int:
        """Bypass sayısı."""
        return self._stats[
            "emergencies_bypassed"
        ]
