"""ATLAS Hata Durumunda Geri Alma modülü.

Hata tespiti, otomatik geri alma,
durum geri yükleme, bildirim,
sorun analizi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class RollbackOnFailure:
    """Hata durumunda geri alma yöneticisi.

    Hata tespit edince otomatik geri alma yapar.

    Attributes:
        _rollbacks: Geri alma kayıtları.
        _checkpoints: Kontrol noktaları.
    """

    def __init__(
        self,
        auto_rollback: bool = True,
    ) -> None:
        """Yöneticiyi başlatır.

        Args:
            auto_rollback: Otomatik geri alma.
        """
        self._rollbacks: list[
            dict[str, Any]
        ] = []
        self._checkpoints: dict[
            str, dict[str, Any]
        ] = {}
        self._failure_rules: list[
            dict[str, Any]
        ] = []
        self._auto_rollback = auto_rollback
        self._counter = 0
        self._stats = {
            "rollbacks": 0,
            "failures_detected": 0,
            "states_restored": 0,
            "notifications_sent": 0,
        }

        logger.info(
            "RollbackOnFailure baslatildi",
        )

    def create_checkpoint(
        self,
        capability_id: str,
        state: dict[str, Any],
    ) -> dict[str, Any]:
        """Kontrol noktası oluşturur.

        Args:
            capability_id: Yetenek ID.
            state: Kayıt edilecek durum.

        Returns:
            Checkpoint bilgisi.
        """
        checkpoint = {
            "capability_id": capability_id,
            "state": dict(state),
            "created_at": time.time(),
        }
        self._checkpoints[capability_id] = (
            checkpoint
        )

        return {
            "capability_id": capability_id,
            "checkpoint_created": True,
        }

    def detect_failure(
        self,
        capability_id: str,
        error: str,
        severity: str = "medium",
    ) -> dict[str, Any]:
        """Hata tespit eder.

        Args:
            capability_id: Yetenek ID.
            error: Hata mesajı.
            severity: Ciddiyet.

        Returns:
            Tespit bilgisi.
        """
        self._stats["failures_detected"] += 1

        failure = {
            "capability_id": capability_id,
            "error": error,
            "severity": severity,
            "detected_at": time.time(),
        }

        result = {
            "capability_id": capability_id,
            "failure_detected": True,
            "severity": severity,
            "auto_rollback": self._auto_rollback,
        }

        if self._auto_rollback:
            rollback = self.rollback(
                capability_id, f"auto: {error}",
            )
            result["rollback_performed"] = (
                rollback.get("rolled_back", False)
            )
            result["notification"] = (
                self._notify(
                    capability_id, error, severity,
                )
            )

        return result

    def rollback(
        self,
        capability_id: str,
        reason: str = "manual",
    ) -> dict[str, Any]:
        """Geri alma yapar.

        Args:
            capability_id: Yetenek ID.
            reason: Geri alma nedeni.

        Returns:
            Geri alma bilgisi.
        """
        self._counter += 1
        rid = f"rollback_{self._counter}"

        restored = self._restore_state(
            capability_id,
        )

        rollback = {
            "rollback_id": rid,
            "capability_id": capability_id,
            "reason": reason,
            "state_restored": restored,
            "timestamp": time.time(),
        }
        self._rollbacks.append(rollback)
        self._stats["rollbacks"] += 1

        return {
            "rollback_id": rid,
            "capability_id": capability_id,
            "rolled_back": True,
            "state_restored": restored,
            "reason": reason,
        }

    def _restore_state(
        self,
        capability_id: str,
    ) -> bool:
        """Durumu geri yükler."""
        checkpoint = self._checkpoints.get(
            capability_id,
        )
        if checkpoint:
            self._stats["states_restored"] += 1
            return True
        return False

    def _notify(
        self,
        capability_id: str,
        error: str,
        severity: str,
    ) -> dict[str, Any]:
        """Bildirim gönderir."""
        self._stats["notifications_sent"] += 1
        return {
            "capability_id": capability_id,
            "error": error,
            "severity": severity,
            "notified": True,
        }

    def add_failure_rule(
        self,
        name: str,
        condition: str,
        action: str = "rollback",
    ) -> dict[str, Any]:
        """Hata kuralı ekler.

        Args:
            name: Kural adı.
            condition: Koşul.
            action: Aksiyon.

        Returns:
            Ekleme bilgisi.
        """
        rule = {
            "name": name,
            "condition": condition,
            "action": action,
            "active": True,
        }
        self._failure_rules.append(rule)
        return {"name": name, "added": True}

    def post_mortem(
        self,
        rollback_id: str,
    ) -> dict[str, Any]:
        """Sorun analizi yapar.

        Args:
            rollback_id: Geri alma ID.

        Returns:
            Analiz bilgisi.
        """
        rollback = None
        for r in self._rollbacks:
            if r["rollback_id"] == rollback_id:
                rollback = r
                break

        if not rollback:
            return {"error": "rollback_not_found"}

        return {
            "rollback_id": rollback_id,
            "capability_id": rollback[
                "capability_id"
            ],
            "reason": rollback["reason"],
            "state_restored": rollback[
                "state_restored"
            ],
            "timestamp": rollback["timestamp"],
            "recommendation": (
                "Review failure cause and "
                "add preventive measures"
            ),
        }

    def get_rollbacks(
        self,
        capability_id: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Geri almaları getirir.

        Args:
            capability_id: Yetenek filtresi.
            limit: Maks kayıt.

        Returns:
            Geri alma listesi.
        """
        results = self._rollbacks
        if capability_id:
            results = [
                r for r in results
                if r["capability_id"]
                == capability_id
            ]
        return list(results[-limit:])

    @property
    def rollback_count(self) -> int:
        """Geri alma sayısı."""
        return self._stats["rollbacks"]

    @property
    def failure_count(self) -> int:
        """Tespit edilen hata sayısı."""
        return self._stats["failures_detected"]

    @property
    def rule_count(self) -> int:
        """Kural sayısı."""
        return len(self._failure_rules)
