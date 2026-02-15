"""ATLAS Ihlal Yoneticisi modulu.

Ihlal tespiti, yanit uretimi,
Retry-After, ceza sistemi, itiraz.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ViolationHandler:
    """Ihlal yoneticisi.

    Hiz siniri ihlallerini yonetir.

    Attributes:
        _violations: Ihlal kayitlari.
        _penalties: Ceza kayitlari.
    """

    def __init__(
        self,
        penalty_minutes: int = 15,
        max_violations_before_ban: int = 10,
        ban_duration_minutes: int = 60,
    ) -> None:
        """Ihlal yoneticisini baslatir.

        Args:
            penalty_minutes: Ceza suresi (dk).
            max_violations_before_ban: Ban oncesi maks ihlal.
            ban_duration_minutes: Ban suresi (dk).
        """
        self._violations: list[
            dict[str, Any]
        ] = []
        self._subject_violations: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._penalties: dict[
            str, dict[str, Any]
        ] = {}
        self._bans: dict[
            str, dict[str, Any]
        ] = {}
        self._appeals: list[
            dict[str, Any]
        ] = []
        self._penalty_minutes = penalty_minutes
        self._max_before_ban = (
            max_violations_before_ban
        )
        self._ban_duration = ban_duration_minutes
        self._stats = {
            "violations": 0,
            "penalties": 0,
            "bans": 0,
            "appeals": 0,
        }

        logger.info(
            "ViolationHandler baslatildi",
        )

    def record_violation(
        self,
        subject_id: str,
        violation_type: str = "rate_exceeded",
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Ihlal kaydeder.

        Args:
            subject_id: Konu ID.
            violation_type: Ihlal tipi.
            details: Detaylar.

        Returns:
            Ihlal bilgisi.
        """
        violation = {
            "subject_id": subject_id,
            "type": violation_type,
            "details": details or {},
            "timestamp": time.time(),
        }

        self._violations.append(violation)

        if subject_id not in self._subject_violations:
            self._subject_violations[
                subject_id
            ] = []
        self._subject_violations[subject_id].append(
            violation,
        )

        self._stats["violations"] += 1

        # Ceza kontrolu
        count = len(
            self._subject_violations[subject_id],
        )
        penalty = self._determine_penalty(
            subject_id, count,
        )

        return {
            "subject_id": subject_id,
            "type": violation_type,
            "violation_count": count,
            "penalty": penalty,
        }

    def check_banned(
        self,
        subject_id: str,
    ) -> dict[str, Any]:
        """Ban kontrolu yapar.

        Args:
            subject_id: Konu ID.

        Returns:
            Ban durumu.
        """
        ban = self._bans.get(subject_id)
        if not ban:
            return {
                "banned": False,
            }

        now = time.time()
        if now > ban["expires_at"]:
            del self._bans[subject_id]
            return {
                "banned": False,
                "was_banned": True,
            }

        return {
            "banned": True,
            "reason": ban.get("reason", ""),
            "expires_at": ban["expires_at"],
            "retry_after": int(
                ban["expires_at"] - now,
            ),
        }

    def get_penalty(
        self,
        subject_id: str,
    ) -> dict[str, Any] | None:
        """Aktif cezayi getirir.

        Args:
            subject_id: Konu ID.

        Returns:
            Ceza bilgisi veya None.
        """
        penalty = self._penalties.get(subject_id)
        if not penalty:
            return None

        now = time.time()
        if now > penalty.get("expires_at", 0):
            del self._penalties[subject_id]
            return None

        return dict(penalty)

    def generate_response(
        self,
        subject_id: str,
        violation_type: str = "rate_exceeded",
    ) -> dict[str, Any]:
        """Ihlal yaniti uretir.

        Args:
            subject_id: Konu ID.
            violation_type: Ihlal tipi.

        Returns:
            Yanit bilgisi.
        """
        # Ban kontrolu
        ban_info = self.check_banned(subject_id)
        if ban_info.get("banned"):
            return {
                "status_code": 403,
                "error": "forbidden",
                "message": "Account temporarily banned",
                "retry_after": ban_info[
                    "retry_after"
                ],
            }

        # Ceza kontrolu
        penalty = self.get_penalty(subject_id)
        if penalty:
            if penalty["action"] == "reject":
                now = time.time()
                return {
                    "status_code": 429,
                    "error": "too_many_requests",
                    "message": (
                        "Rate limit exceeded"
                    ),
                    "retry_after": int(
                        penalty["expires_at"] - now,
                    ),
                }

            if penalty["action"] == "delay":
                return {
                    "status_code": 200,
                    "throttled": True,
                    "delay_ms": penalty.get(
                        "delay_ms", 1000,
                    ),
                }

        # Varsayilan
        return {
            "status_code": 429,
            "error": "too_many_requests",
            "message": "Rate limit exceeded",
            "retry_after": self._penalty_minutes * 60,
        }

    def submit_appeal(
        self,
        subject_id: str,
        reason: str = "",
    ) -> dict[str, Any]:
        """Itiraz gonderir.

        Args:
            subject_id: Konu ID.
            reason: Itiraz nedeni.

        Returns:
            Itiraz bilgisi.
        """
        appeal = {
            "subject_id": subject_id,
            "reason": reason,
            "status": "pending",
            "submitted_at": time.time(),
        }

        self._appeals.append(appeal)
        self._stats["appeals"] += 1

        return {
            "subject_id": subject_id,
            "status": "submitted",
        }

    def resolve_appeal(
        self,
        subject_id: str,
        approved: bool = False,
    ) -> dict[str, Any]:
        """Itirazi cozumler.

        Args:
            subject_id: Konu ID.
            approved: Onaylandi mi.

        Returns:
            Cozumleme sonucu.
        """
        for appeal in self._appeals:
            if (
                appeal["subject_id"] == subject_id
                and appeal["status"] == "pending"
            ):
                appeal["status"] = (
                    "approved" if approved
                    else "rejected"
                )
                appeal["resolved_at"] = time.time()

                if approved:
                    self._bans.pop(
                        subject_id, None,
                    )
                    self._penalties.pop(
                        subject_id, None,
                    )

                return {
                    "subject_id": subject_id,
                    "approved": approved,
                    "status": "resolved",
                }

        return {"error": "appeal_not_found"}

    def clear_violations(
        self,
        subject_id: str,
    ) -> dict[str, Any]:
        """Ihlalleri temizler.

        Args:
            subject_id: Konu ID.

        Returns:
            Temizleme sonucu.
        """
        count = len(
            self._subject_violations.get(
                subject_id, [],
            ),
        )
        self._subject_violations.pop(
            subject_id, None,
        )
        self._penalties.pop(subject_id, None)
        self._bans.pop(subject_id, None)

        return {
            "subject_id": subject_id,
            "cleared": count,
        }

    def get_violations(
        self,
        subject_id: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Ihlalleri getirir.

        Args:
            subject_id: Konu filtresi.
            limit: Limit.

        Returns:
            Ihlal listesi.
        """
        if subject_id:
            items = self._subject_violations.get(
                subject_id, [],
            )
        else:
            items = self._violations
        return items[-limit:]

    def get_appeals(
        self,
        status: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Itirazlari getirir.

        Args:
            status: Durum filtresi.
            limit: Limit.

        Returns:
            Itiraz listesi.
        """
        appeals = self._appeals
        if status:
            appeals = [
                a for a in appeals
                if a["status"] == status
            ]
        return appeals[-limit:]

    def _determine_penalty(
        self,
        subject_id: str,
        violation_count: int,
    ) -> dict[str, Any]:
        """Cezayi belirler.

        Args:
            subject_id: Konu ID.
            violation_count: Ihlal sayisi.

        Returns:
            Ceza bilgisi.
        """
        now = time.time()

        if violation_count >= self._max_before_ban:
            self._bans[subject_id] = {
                "reason": "excessive_violations",
                "violation_count": violation_count,
                "banned_at": now,
                "expires_at": (
                    now + self._ban_duration * 60
                ),
            }
            self._stats["bans"] += 1
            return {
                "action": "ban",
                "duration_minutes": (
                    self._ban_duration
                ),
            }

        if violation_count >= 5:
            self._penalties[subject_id] = {
                "action": "reject",
                "expires_at": (
                    now + self._penalty_minutes * 60
                ),
            }
            self._stats["penalties"] += 1
            return {
                "action": "reject",
                "duration_minutes": (
                    self._penalty_minutes
                ),
            }

        if violation_count >= 3:
            self._penalties[subject_id] = {
                "action": "delay",
                "delay_ms": (
                    1000 * violation_count
                ),
                "expires_at": (
                    now + self._penalty_minutes * 60
                ),
            }
            self._stats["penalties"] += 1
            return {
                "action": "delay",
                "delay_ms": (
                    1000 * violation_count
                ),
            }

        return {"action": "warn"}

    @property
    def violation_count(self) -> int:
        """Ihlal sayisi."""
        return len(self._violations)

    @property
    def ban_count(self) -> int:
        """Ban sayisi."""
        return len(self._bans)

    @property
    def penalty_count(self) -> int:
        """Ceza sayisi."""
        return len(self._penalties)

    @property
    def appeal_count(self) -> int:
        """Itiraz sayisi."""
        return len(self._appeals)
