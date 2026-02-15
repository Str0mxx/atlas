"""ATLAS Gezinti Kaydedici modülü.

Aksiyon kayıt, tekrar oynatma,
adım dokümantasyonu, hata kayıt,
denetim izi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class NavigationRecorder:
    """Gezinti kaydedici.

    Web gezinti adımlarını kaydeder ve
    tekrar oynatır.

    Attributes:
        _recordings: Kayıt geçmişi.
        _active: Aktif kayıtlar.
    """

    def __init__(self) -> None:
        """Kaydediciyi başlatır."""
        self._recordings: dict[
            str, dict[str, Any]
        ] = {}
        self._active_recording: str | None = (
            None
        )
        self._error_log: list[
            dict[str, Any]
        ] = []
        self._audit_trail: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "recordings_created": 0,
            "actions_recorded": 0,
            "replays": 0,
            "errors_logged": 0,
        }

        logger.info(
            "NavigationRecorder baslatildi",
        )

    def start_recording(
        self,
        name: str,
        description: str = "",
    ) -> dict[str, Any]:
        """Kayıt başlatır.

        Args:
            name: Kayıt adı.
            description: Açıklama.

        Returns:
            Kayıt bilgisi.
        """
        self._counter += 1
        rid = f"rec_{self._counter}"

        recording = {
            "recording_id": rid,
            "name": name,
            "description": description,
            "actions": [],
            "status": "recording",
            "started_at": time.time(),
            "completed_at": None,
        }
        self._recordings[rid] = recording
        self._active_recording = rid
        self._stats[
            "recordings_created"
        ] += 1

        self._audit("recording_started", {
            "recording_id": rid,
            "name": name,
        })

        return {
            "recording_id": rid,
            "name": name,
            "started": True,
        }

    def record_action(
        self,
        action_type: str,
        details: dict[str, Any],
        recording_id: str | None = None,
    ) -> dict[str, Any]:
        """Aksiyon kaydeder.

        Args:
            action_type: Aksiyon tipi.
            details: Detaylar.
            recording_id: Kayıt ID.

        Returns:
            Kayıt bilgisi.
        """
        rid = (
            recording_id
            or self._active_recording
        )
        if not rid or rid not in (
            self._recordings
        ):
            return {
                "error": "no_active_recording",
            }

        recording = self._recordings[rid]
        if recording["status"] != "recording":
            return {
                "error": "recording_not_active",
            }

        action = {
            "step": len(
                recording["actions"],
            ) + 1,
            "type": action_type,
            "details": details,
            "timestamp": time.time(),
        }
        recording["actions"].append(action)
        self._stats["actions_recorded"] += 1

        return {
            "recording_id": rid,
            "step": action["step"],
            "type": action_type,
            "recorded": True,
        }

    def stop_recording(
        self,
        recording_id: str | None = None,
    ) -> dict[str, Any]:
        """Kayıt durdurur.

        Args:
            recording_id: Kayıt ID.

        Returns:
            Durdurma bilgisi.
        """
        rid = (
            recording_id
            or self._active_recording
        )
        if not rid or rid not in (
            self._recordings
        ):
            return {
                "error": "recording_not_found",
            }

        recording = self._recordings[rid]
        recording["status"] = "completed"
        recording["completed_at"] = time.time()

        if self._active_recording == rid:
            self._active_recording = None

        self._audit("recording_stopped", {
            "recording_id": rid,
            "actions": len(
                recording["actions"],
            ),
        })

        return {
            "recording_id": rid,
            "action_count": len(
                recording["actions"],
            ),
            "stopped": True,
        }

    def replay(
        self,
        recording_id: str,
    ) -> dict[str, Any]:
        """Kayıt tekrar oynatır.

        Args:
            recording_id: Kayıt ID.

        Returns:
            Oynatma bilgisi.
        """
        recording = self._recordings.get(
            recording_id,
        )
        if not recording:
            return {
                "error": "recording_not_found",
            }

        actions = recording["actions"]
        replayed = []
        for action in actions:
            replayed.append({
                "step": action["step"],
                "type": action["type"],
                "executed": True,
            })

        self._stats["replays"] += 1
        self._audit("replay_executed", {
            "recording_id": recording_id,
            "steps": len(replayed),
        })

        return {
            "recording_id": recording_id,
            "steps_replayed": len(replayed),
            "replayed_actions": replayed,
            "success": True,
        }

    def log_error(
        self,
        error: str,
        step: int = 0,
        recording_id: str | None = None,
    ) -> dict[str, Any]:
        """Hata kaydeder.

        Args:
            error: Hata mesajı.
            step: Adım numarası.
            recording_id: Kayıt ID.

        Returns:
            Kayıt bilgisi.
        """
        error_record = {
            "error": error,
            "step": step,
            "recording_id": (
                recording_id
                or self._active_recording
            ),
            "timestamp": time.time(),
        }
        self._error_log.append(error_record)
        self._stats["errors_logged"] += 1

        return {
            "logged": True,
            "error": error,
            "step": step,
        }

    def get_documentation(
        self,
        recording_id: str,
    ) -> dict[str, Any]:
        """Adım dokümantasyonu getirir.

        Args:
            recording_id: Kayıt ID.

        Returns:
            Dokümantasyon bilgisi.
        """
        recording = self._recordings.get(
            recording_id,
        )
        if not recording:
            return {
                "error": "recording_not_found",
            }

        steps = []
        for action in recording["actions"]:
            steps.append({
                "step": action["step"],
                "description": (
                    f"{action['type']}: "
                    f"{action['details']}"
                ),
            })

        return {
            "recording_id": recording_id,
            "name": recording["name"],
            "total_steps": len(steps),
            "steps": steps,
        }

    def _audit(
        self,
        action: str,
        details: dict[str, Any],
    ) -> None:
        """Denetim kaydı ekler."""
        self._audit_trail.append({
            "action": action,
            "details": details,
            "timestamp": time.time(),
        })

    def get_recordings(
        self,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """Kayıtları getirir.

        Args:
            status: Durum filtresi.

        Returns:
            Kayıt listesi.
        """
        results = list(
            self._recordings.values(),
        )
        if status:
            results = [
                r for r in results
                if r["status"] == status
            ]
        return results

    def get_audit_trail(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Denetim izini getirir.

        Args:
            limit: Maks kayıt.

        Returns:
            Denetim listesi.
        """
        return list(self._audit_trail[-limit:])

    def get_error_log(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Hata kayıtlarını getirir.

        Args:
            limit: Maks kayıt.

        Returns:
            Hata listesi.
        """
        return list(self._error_log[-limit:])

    @property
    def recording_count(self) -> int:
        """Kayıt sayısı."""
        return self._stats[
            "recordings_created"
        ]

    @property
    def action_count(self) -> int:
        """Aksiyon sayısı."""
        return self._stats["actions_recorded"]

    @property
    def replay_count(self) -> int:
        """Tekrar oynatma sayısı."""
        return self._stats["replays"]

    @property
    def error_count(self) -> int:
        """Hata sayısı."""
        return self._stats["errors_logged"]
