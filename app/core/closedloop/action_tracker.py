"""ATLAS Aksiyon Takipcisi modulu.

Aksiyon kaydi, calisma loglama,
zaman takibi, baglam yakalama, zincirleme.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ActionTracker:
    """Aksiyon takipcisi.

    Aksiyonlari kaydeder ve takip eder.

    Attributes:
        _actions: Aksiyon kayitlari.
        _chains: Aksiyon zincirleri.
    """

    def __init__(self) -> None:
        """Aksiyon takipcisini baslatir."""
        self._actions: dict[
            str, dict[str, Any]
        ] = {}
        self._chains: dict[
            str, list[str]
        ] = {}
        self._execution_logs: list[
            dict[str, Any]
        ] = []
        self._stats = {
            "registered": 0,
            "completed": 0,
            "failed": 0,
        }

        logger.info(
            "ActionTracker baslatildi",
        )

    def register_action(
        self,
        action_id: str,
        name: str,
        context: dict[str, Any] | None = None,
        parent_id: str = "",
    ) -> dict[str, Any]:
        """Aksiyon kaydeder.

        Args:
            action_id: Aksiyon ID.
            name: Aksiyon adi.
            context: Baglam bilgisi.
            parent_id: Ust aksiyon ID.

        Returns:
            Kayit bilgisi.
        """
        now = time.time()
        action = {
            "action_id": action_id,
            "name": name,
            "status": "pending",
            "context": context or {},
            "parent_id": parent_id,
            "created_at": now,
            "started_at": None,
            "completed_at": None,
            "duration_ms": 0,
            "logs": [],
        }

        self._actions[action_id] = action
        self._stats["registered"] += 1

        # Zincirleme
        if parent_id and parent_id in self._actions:
            if parent_id not in self._chains:
                self._chains[parent_id] = []
            self._chains[parent_id].append(
                action_id,
            )

        return {
            "action_id": action_id,
            "status": "registered",
        }

    def start_action(
        self,
        action_id: str,
    ) -> dict[str, Any]:
        """Aksiyonu baslatir.

        Args:
            action_id: Aksiyon ID.

        Returns:
            Baslangic bilgisi.
        """
        action = self._actions.get(action_id)
        if not action:
            return {"error": "action_not_found"}

        action["status"] = "running"
        action["started_at"] = time.time()

        self._log_execution(
            action_id, "started",
        )

        return {
            "action_id": action_id,
            "status": "running",
        }

    def complete_action(
        self,
        action_id: str,
        result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Aksiyonu tamamlar.

        Args:
            action_id: Aksiyon ID.
            result: Sonuc bilgisi.

        Returns:
            Tamamlanma bilgisi.
        """
        action = self._actions.get(action_id)
        if not action:
            return {"error": "action_not_found"}

        now = time.time()
        action["status"] = "completed"
        action["completed_at"] = now
        action["result"] = result or {}

        if action["started_at"]:
            action["duration_ms"] = int(
                (now - action["started_at"]) * 1000,
            )

        self._stats["completed"] += 1
        self._log_execution(
            action_id, "completed",
        )

        return {
            "action_id": action_id,
            "status": "completed",
            "duration_ms": action["duration_ms"],
        }

    def fail_action(
        self,
        action_id: str,
        error: str = "",
    ) -> dict[str, Any]:
        """Aksiyonu basarisiz isaretler.

        Args:
            action_id: Aksiyon ID.
            error: Hata mesaji.

        Returns:
            Basarisizlik bilgisi.
        """
        action = self._actions.get(action_id)
        if not action:
            return {"error": "action_not_found"}

        now = time.time()
        action["status"] = "failed"
        action["completed_at"] = now
        action["error"] = error

        if action["started_at"]:
            action["duration_ms"] = int(
                (now - action["started_at"]) * 1000,
            )

        self._stats["failed"] += 1
        self._log_execution(
            action_id, "failed",
        )

        return {
            "action_id": action_id,
            "status": "failed",
            "error": error,
        }

    def get_action(
        self,
        action_id: str,
    ) -> dict[str, Any] | None:
        """Aksiyonu getirir.

        Args:
            action_id: Aksiyon ID.

        Returns:
            Aksiyon bilgisi veya None.
        """
        action = self._actions.get(action_id)
        if action:
            return dict(action)
        return None

    def get_chain(
        self,
        parent_id: str,
    ) -> list[str]:
        """Aksiyon zincirini getirir.

        Args:
            parent_id: Ust aksiyon ID.

        Returns:
            Alt aksiyon ID listesi.
        """
        return list(
            self._chains.get(parent_id, []),
        )

    def get_actions_by_status(
        self,
        status: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Duruma gore aksiyonlari getirir.

        Args:
            status: Durum filtresi.
            limit: Limit.

        Returns:
            Aksiyon listesi.
        """
        result = [
            dict(a)
            for a in self._actions.values()
            if a["status"] == status
        ]
        return result[:limit]

    def get_context(
        self,
        action_id: str,
    ) -> dict[str, Any]:
        """Aksiyon baglamini getirir.

        Args:
            action_id: Aksiyon ID.

        Returns:
            Baglam bilgisi.
        """
        action = self._actions.get(action_id)
        if action:
            return dict(action.get("context", {}))
        return {}

    def _log_execution(
        self,
        action_id: str,
        event: str,
    ) -> None:
        """Calisma loglar.

        Args:
            action_id: Aksiyon ID.
            event: Olay.
        """
        entry = {
            "action_id": action_id,
            "event": event,
            "timestamp": time.time(),
        }
        self._execution_logs.append(entry)

        action = self._actions.get(action_id)
        if action:
            action["logs"].append(entry)

    @property
    def action_count(self) -> int:
        """Aksiyon sayisi."""
        return len(self._actions)

    @property
    def chain_count(self) -> int:
        """Zincir sayisi."""
        return len(self._chains)

    @property
    def log_count(self) -> int:
        """Log sayisi."""
        return len(self._execution_logs)
