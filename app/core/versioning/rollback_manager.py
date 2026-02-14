"""ATLAS Geri Alma Yoneticisi modulu.

Noktasal geri alma, secimli geri alma,
asamali geri alma, dogrulama ve
geri almayi geri alma.
"""

import logging
import time
from typing import Any

from app.models.versioning import RollbackType

logger = logging.getLogger(__name__)


class RollbackManager:
    """Geri alma yoneticisi.

    Sistem durumunu onceki bir
    noktaya dondurur.

    Attributes:
        _rollbacks: Geri alma gecmisi.
        _checkpoints: Kontrol noktalari.
    """

    def __init__(self) -> None:
        """Geri alma yoneticisini baslatir."""
        self._rollbacks: list[
            dict[str, Any]
        ] = []
        self._checkpoints: dict[
            str, dict[str, Any]
        ] = {}
        self._undo_stack: list[
            dict[str, Any]
        ] = []

        logger.info(
            "RollbackManager baslatildi",
        )

    def create_checkpoint(
        self,
        name: str,
        state: dict[str, Any],
    ) -> dict[str, Any]:
        """Kontrol noktasi olusturur.

        Args:
            name: Checkpoint adi.
            state: Durum verisi.

        Returns:
            Checkpoint bilgisi.
        """
        checkpoint = {
            "name": name,
            "state": dict(state),
            "at": time.time(),
        }
        self._checkpoints[name] = checkpoint
        return checkpoint

    def rollback_to_checkpoint(
        self,
        name: str,
    ) -> dict[str, Any]:
        """Kontrol noktasina geri doner.

        Args:
            name: Checkpoint adi.

        Returns:
            Geri alma sonucu.
        """
        checkpoint = self._checkpoints.get(name)
        if not checkpoint:
            return {
                "success": False,
                "reason": "checkpoint_not_found",
            }

        rollback = {
            "type": RollbackType.POINT_IN_TIME.value,
            "checkpoint": name,
            "state": checkpoint["state"],
            "at": time.time(),
        }
        self._rollbacks.append(rollback)
        self._undo_stack.append(rollback)

        return {
            "success": True,
            "type": RollbackType.POINT_IN_TIME.value,
            "checkpoint": name,
            "state": checkpoint["state"],
        }

    def selective_rollback(
        self,
        keys: list[str],
        source_state: dict[str, Any],
    ) -> dict[str, Any]:
        """Secimli geri alma yapar.

        Args:
            keys: Geri alinacak anahtarlar.
            source_state: Kaynak durum.

        Returns:
            Geri alma sonucu.
        """
        restored: dict[str, Any] = {}
        for key in keys:
            if key in source_state:
                restored[key] = source_state[key]

        rollback = {
            "type": RollbackType.SELECTIVE.value,
            "keys": keys,
            "restored": restored,
            "at": time.time(),
        }
        self._rollbacks.append(rollback)
        self._undo_stack.append(rollback)

        return {
            "success": True,
            "type": RollbackType.SELECTIVE.value,
            "restored_keys": list(restored.keys()),
            "restored": restored,
        }

    def staged_rollback(
        self,
        stages: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Asamali geri alma yapar.

        Args:
            stages: Asamalar listesi.

        Returns:
            Geri alma sonucu.
        """
        results: list[dict[str, Any]] = []
        for stage in stages:
            name = stage.get("name", "")
            state = stage.get("state", {})

            results.append({
                "stage": name,
                "success": True,
                "state": state,
            })

        rollback = {
            "type": RollbackType.STAGED.value,
            "stages": len(stages),
            "results": results,
            "at": time.time(),
        }
        self._rollbacks.append(rollback)
        self._undo_stack.append(rollback)

        return {
            "success": True,
            "type": RollbackType.STAGED.value,
            "stages_completed": len(results),
            "results": results,
        }

    def validate_rollback(
        self,
        target_state: dict[str, Any],
        current_state: dict[str, Any],
    ) -> dict[str, Any]:
        """Geri almayi dogrular.

        Args:
            target_state: Hedef durum.
            current_state: Guncel durum.

        Returns:
            Dogrulama sonucu.
        """
        conflicts: list[str] = []
        missing: list[str] = []

        for key in target_state:
            if key in current_state:
                if (
                    type(target_state[key])
                    != type(current_state[key])
                ):
                    conflicts.append(key)
            else:
                missing.append(key)

        safe = len(conflicts) == 0
        return {
            "safe": safe,
            "conflicts": conflicts,
            "missing_keys": missing,
            "target_keys": len(target_state),
            "current_keys": len(current_state),
        }

    def undo_last_rollback(
        self,
    ) -> dict[str, Any]:
        """Son geri almayi geri alir.

        Returns:
            Geri alma sonucu.
        """
        if not self._undo_stack:
            return {
                "success": False,
                "reason": "no_rollback_to_undo",
            }

        last = self._undo_stack.pop()
        return {
            "success": True,
            "undone_type": last["type"],
            "at": time.time(),
        }

    def get_history(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Geri alma gecmisi getirir.

        Args:
            limit: Limit.

        Returns:
            Geri alma listesi.
        """
        return self._rollbacks[-limit:]

    def get_checkpoint(
        self,
        name: str,
    ) -> dict[str, Any] | None:
        """Kontrol noktasi getirir.

        Args:
            name: Checkpoint adi.

        Returns:
            Checkpoint veya None.
        """
        return self._checkpoints.get(name)

    def delete_checkpoint(
        self,
        name: str,
    ) -> bool:
        """Kontrol noktasi siler.

        Args:
            name: Checkpoint adi.

        Returns:
            Basarili ise True.
        """
        if name in self._checkpoints:
            del self._checkpoints[name]
            return True
        return False

    @property
    def rollback_count(self) -> int:
        """Geri alma sayisi."""
        return len(self._rollbacks)

    @property
    def checkpoint_count(self) -> int:
        """Checkpoint sayisi."""
        return len(self._checkpoints)

    @property
    def undo_count(self) -> int:
        """Undo stack boyutu."""
        return len(self._undo_stack)
