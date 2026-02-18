"""
Otomatik cevreleme modulu.

Otomatik izolasyon, ag karantina,
hesap askiya alma, servis kapatma,
hasar sinirlandirma.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class AutoContainment:
    """Otomatik cevreleme.

    Attributes:
        _actions: Aksiyon kayitlari.
        _quarantines: Karantina kayitlari.
        _suspensions: Askiya alma kayit.
        _stats: Istatistikler.
    """

    ACTION_TYPES: list[str] = [
        "network_isolate",
        "account_suspend",
        "service_shutdown",
        "port_block",
        "ip_block",
        "process_kill",
        "file_quarantine",
        "credential_revoke",
    ]

    def __init__(
        self,
        auto_contain: bool = True,
    ) -> None:
        """Cevrelemeyi baslatir.

        Args:
            auto_contain: Otomatik cevreleme.
        """
        self._auto_contain = auto_contain
        self._actions: list[dict] = []
        self._quarantines: dict[
            str, dict
        ] = {}
        self._suspensions: dict[
            str, dict
        ] = {}
        self._stats: dict[str, int] = {
            "actions_taken": 0,
            "systems_quarantined": 0,
            "accounts_suspended": 0,
            "services_shutdown": 0,
            "actions_reversed": 0,
        }
        logger.info(
            "AutoContainment baslatildi"
        )

    @property
    def active_quarantines(self) -> int:
        """Aktif karantina sayisi."""
        return sum(
            1
            for q in (
                self._quarantines.values()
            )
            if q["status"] == "active"
        )

    def contain_incident(
        self,
        incident_id: str = "",
        actions: (
            list[str] | None
        ) = None,
        targets: (
            list[str] | None
        ) = None,
        reason: str = "",
    ) -> dict[str, Any]:
        """Olayi cevreler.

        Args:
            incident_id: Olay ID.
            actions: Aksiyon listesi.
            targets: Hedef listesi.
            reason: Sebep.

        Returns:
            Cevreleme bilgisi.
        """
        try:
            if not self._auto_contain:
                return {
                    "contained": False,
                    "error": (
                        "Otomatik cevreleme "
                        "devre disi"
                    ),
                }

            act_list = actions or []
            tgt_list = targets or []
            results = []

            for action in act_list:
                if (
                    action
                    not in self.ACTION_TYPES
                ):
                    continue

                for target in tgt_list:
                    r = self._execute_action(
                        incident_id,
                        action,
                        target,
                        reason,
                    )
                    results.append(r)

            return {
                "incident_id": incident_id,
                "actions_taken": len(
                    results
                ),
                "results": results,
                "contained": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "contained": False,
                "error": str(e),
            }

    def _execute_action(
        self,
        incident_id: str,
        action: str,
        target: str,
        reason: str,
    ) -> dict:
        """Aksiyon yurutur."""
        aid = f"ca_{uuid4()!s:.8}"
        record = {
            "action_id": aid,
            "incident_id": incident_id,
            "action_type": action,
            "target": target,
            "reason": reason,
            "status": "executed",
            "executed_at": (
                datetime.now(
                    timezone.utc
                ).isoformat()
            ),
        }
        self._actions.append(record)
        self._stats["actions_taken"] += 1

        if action == "network_isolate":
            self._quarantine_system(
                incident_id, target
            )
        elif action == "account_suspend":
            self._suspend_account(
                incident_id, target
            )
        elif action == "service_shutdown":
            self._stats[
                "services_shutdown"
            ] += 1

        return {
            "action_id": aid,
            "action": action,
            "target": target,
            "executed": True,
        }

    def _quarantine_system(
        self,
        incident_id: str,
        system: str,
    ) -> None:
        """Sistemi karantinaya alir."""
        qid = f"qr_{uuid4()!s:.8}"
        self._quarantines[qid] = {
            "quarantine_id": qid,
            "incident_id": incident_id,
            "system": system,
            "status": "active",
            "quarantined_at": (
                datetime.now(
                    timezone.utc
                ).isoformat()
            ),
        }
        self._stats[
            "systems_quarantined"
        ] += 1

    def _suspend_account(
        self,
        incident_id: str,
        account: str,
    ) -> None:
        """Hesabi askiya alir."""
        sid = f"sp_{uuid4()!s:.8}"
        self._suspensions[sid] = {
            "suspension_id": sid,
            "incident_id": incident_id,
            "account": account,
            "status": "active",
            "suspended_at": (
                datetime.now(
                    timezone.utc
                ).isoformat()
            ),
        }
        self._stats[
            "accounts_suspended"
        ] += 1

    def release_quarantine(
        self,
        quarantine_id: str = "",
        reason: str = "",
    ) -> dict[str, Any]:
        """Karantinayi kaldirir.

        Args:
            quarantine_id: Karantina ID.
            reason: Sebep.

        Returns:
            Kaldirma bilgisi.
        """
        try:
            q = self._quarantines.get(
                quarantine_id
            )
            if not q:
                return {
                    "released": False,
                    "error": (
                        "Karantina bulunamadi"
                    ),
                }

            q["status"] = "released"
            q["release_reason"] = reason
            q["released_at"] = (
                datetime.now(
                    timezone.utc
                ).isoformat()
            )
            self._stats[
                "actions_reversed"
            ] += 1

            return {
                "quarantine_id": (
                    quarantine_id
                ),
                "released": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "released": False,
                "error": str(e),
            }

    def reinstate_account(
        self,
        suspension_id: str = "",
        reason: str = "",
    ) -> dict[str, Any]:
        """Hesabi geri yukler.

        Args:
            suspension_id: Askiya alma ID.
            reason: Sebep.

        Returns:
            Geri yukleme bilgisi.
        """
        try:
            s = self._suspensions.get(
                suspension_id
            )
            if not s:
                return {
                    "reinstated": False,
                    "error": (
                        "Askiya alma "
                        "bulunamadi"
                    ),
                }

            s["status"] = "reinstated"
            s["reinstate_reason"] = reason
            s["reinstated_at"] = (
                datetime.now(
                    timezone.utc
                ).isoformat()
            )
            self._stats[
                "actions_reversed"
            ] += 1

            return {
                "suspension_id": (
                    suspension_id
                ),
                "reinstated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "reinstated": False,
                "error": str(e),
            }

    def get_actions(
        self,
        incident_id: str = "",
    ) -> dict[str, Any]:
        """Aksiyonlari getirir.

        Args:
            incident_id: Olay ID filtresi.

        Returns:
            Aksiyon listesi.
        """
        try:
            if incident_id:
                filtered = [
                    a
                    for a in self._actions
                    if a["incident_id"]
                    == incident_id
                ]
            else:
                filtered = list(
                    self._actions
                )

            return {
                "actions": filtered,
                "count": len(filtered),
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
        """Ozet getirir."""
        try:
            return {
                "total_actions": len(
                    self._actions
                ),
                "active_quarantines": (
                    self.active_quarantines
                ),
                "active_suspensions": sum(
                    1
                    for s in (
                        self._suspensions
                        .values()
                    )
                    if s["status"]
                    == "active"
                ),
                "auto_contain": (
                    self._auto_contain
                ),
                "stats": dict(self._stats),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
