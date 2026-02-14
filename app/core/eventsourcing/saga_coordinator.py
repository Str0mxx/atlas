"""ATLAS Saga Koordinatoru modulu.

Uzun sureli surecler, telafi mantigi,
durum makinesi, zaman asimi
ve kurtarma.
"""

import logging
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)


class SagaCoordinator:
    """Saga koordinatoru.

    Uzun sureli is sureclerini yonetir.

    Attributes:
        _sagas: Aktif sagalar.
        _definitions: Saga tanimlari.
    """

    def __init__(
        self,
        default_timeout: int = 3600,
    ) -> None:
        """Saga koordinatorunu baslatir.

        Args:
            default_timeout: Varsayilan zaman asimi (sn).
        """
        self._sagas: dict[
            str, dict[str, Any]
        ] = {}
        self._definitions: dict[
            str, dict[str, Any]
        ] = {}
        self._completed: list[
            dict[str, Any]
        ] = []
        self._default_timeout = default_timeout
        self._saga_counter: int = 0

        logger.info(
            "SagaCoordinator baslatildi",
        )

    def define_saga(
        self,
        saga_type: str,
        steps: list[dict[str, Any]],
        timeout: int | None = None,
    ) -> dict[str, Any]:
        """Saga tanimlar.

        Args:
            saga_type: Saga tipi.
            steps: Adim tanimlari.
            timeout: Zaman asimi (sn).

        Returns:
            Tanim bilgisi.
        """
        definition = {
            "saga_type": saga_type,
            "steps": steps,
            "timeout": timeout or self._default_timeout,
            "step_count": len(steps),
        }
        self._definitions[saga_type] = definition
        return definition

    def start_saga(
        self,
        saga_type: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Saga baslatir.

        Args:
            saga_type: Saga tipi.
            context: Baslangic baglami.

        Returns:
            Saga bilgisi.
        """
        definition = self._definitions.get(
            saga_type,
        )
        if not definition:
            return {
                "status": "error",
                "reason": "undefined_saga",
            }

        self._saga_counter += 1
        saga_id = f"saga_{self._saga_counter}"

        saga = {
            "saga_id": saga_id,
            "saga_type": saga_type,
            "state": "running",
            "current_step": 0,
            "steps_total": definition[
                "step_count"
            ],
            "steps_completed": 0,
            "context": context or {},
            "compensations": [],
            "started_at": time.time(),
            "timeout": definition["timeout"],
            "history": [],
        }
        self._sagas[saga_id] = saga
        return {
            "saga_id": saga_id,
            "saga_type": saga_type,
            "state": "running",
        }

    def advance_step(
        self,
        saga_id: str,
        result: dict[str, Any] | None = None,
        compensation: Callable[..., Any] | None = None,
    ) -> dict[str, Any]:
        """Bir adim ilerler.

        Args:
            saga_id: Saga ID.
            result: Adim sonucu.
            compensation: Telafi fonksiyonu.

        Returns:
            Ilerleme bilgisi.
        """
        saga = self._sagas.get(saga_id)
        if not saga:
            return {
                "status": "error",
                "reason": "saga_not_found",
            }

        if saga["state"] != "running":
            return {
                "saga_id": saga_id,
                "status": "error",
                "reason": f"invalid_state: {saga['state']}",
            }

        # Zaman asimi kontrolu
        elapsed = (
            time.time() - saga["started_at"]
        )
        if elapsed > saga["timeout"]:
            saga["state"] = "timed_out"
            return {
                "saga_id": saga_id,
                "status": "timed_out",
            }

        # Adim kaydini ekle
        saga["history"].append({
            "step": saga["current_step"],
            "result": result or {},
            "timestamp": time.time(),
        })

        if compensation:
            saga["compensations"].append(
                compensation,
            )

        saga["steps_completed"] += 1
        saga["current_step"] += 1

        # Tamamlandi mi?
        if (
            saga["steps_completed"]
            >= saga["steps_total"]
        ):
            saga["state"] = "completed"
            self._completed.append({
                "saga_id": saga_id,
                "saga_type": saga["saga_type"],
                "steps_completed": saga[
                    "steps_completed"
                ],
                "duration": (
                    time.time()
                    - saga["started_at"]
                ),
                "timestamp": time.time(),
            })

        return {
            "saga_id": saga_id,
            "state": saga["state"],
            "current_step": saga["current_step"],
            "steps_completed": saga[
                "steps_completed"
            ],
            "steps_total": saga["steps_total"],
        }

    def compensate(
        self,
        saga_id: str,
        reason: str = "",
    ) -> dict[str, Any]:
        """Telafi uygular.

        Args:
            saga_id: Saga ID.
            reason: Telafi sebebi.

        Returns:
            Telafi sonucu.
        """
        saga = self._sagas.get(saga_id)
        if not saga:
            return {
                "status": "error",
                "reason": "saga_not_found",
            }

        saga["state"] = "compensating"
        compensated = 0
        errors = 0

        # Ters sirada telafi
        for comp in reversed(
            saga["compensations"]
        ):
            try:
                comp(saga["context"])
                compensated += 1
            except Exception as e:
                errors += 1
                logger.warning(
                    "Telafi hatasi: %s", e,
                )

        saga["state"] = (
            "failed" if errors > 0
            else "completed"
        )

        return {
            "saga_id": saga_id,
            "state": saga["state"],
            "compensated": compensated,
            "errors": errors,
            "reason": reason,
        }

    def get_saga(
        self,
        saga_id: str,
    ) -> dict[str, Any] | None:
        """Saga bilgisini getirir.

        Args:
            saga_id: Saga ID.

        Returns:
            Saga bilgisi veya None.
        """
        saga = self._sagas.get(saga_id)
        if not saga:
            return None
        return {
            "saga_id": saga["saga_id"],
            "saga_type": saga["saga_type"],
            "state": saga["state"],
            "current_step": saga["current_step"],
            "steps_completed": saga[
                "steps_completed"
            ],
            "steps_total": saga["steps_total"],
            "started_at": saga["started_at"],
        }

    def check_timeouts(
        self,
    ) -> dict[str, Any]:
        """Zaman asimlarini kontrol eder.

        Returns:
            Kontrol sonucu.
        """
        timed_out = 0
        now = time.time()

        for saga in self._sagas.values():
            if saga["state"] != "running":
                continue
            elapsed = now - saga["started_at"]
            if elapsed > saga["timeout"]:
                saga["state"] = "timed_out"
                timed_out += 1

        return {
            "checked": len(self._sagas),
            "timed_out": timed_out,
        }

    def recover_saga(
        self,
        saga_id: str,
    ) -> dict[str, Any]:
        """Saga'yi kurtarir.

        Args:
            saga_id: Saga ID.

        Returns:
            Kurtarma sonucu.
        """
        saga = self._sagas.get(saga_id)
        if not saga:
            return {
                "status": "error",
                "reason": "saga_not_found",
            }

        if saga["state"] in (
            "timed_out", "compensating",
        ):
            saga["state"] = "running"
            saga["started_at"] = time.time()
            return {
                "saga_id": saga_id,
                "status": "recovered",
                "state": "running",
            }

        return {
            "saga_id": saga_id,
            "status": "no_recovery_needed",
            "state": saga["state"],
        }

    @property
    def active_count(self) -> int:
        """Aktif saga sayisi."""
        return sum(
            1 for s in self._sagas.values()
            if s["state"] == "running"
        )

    @property
    def completed_count(self) -> int:
        """Tamamlanan saga sayisi."""
        return len(self._completed)

    @property
    def total_count(self) -> int:
        """Toplam saga sayisi."""
        return len(self._sagas)

    @property
    def definition_count(self) -> int:
        """Tanim sayisi."""
        return len(self._definitions)
